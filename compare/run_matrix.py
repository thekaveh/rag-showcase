#!/usr/bin/env python3
"""Run a RAG query matrix through Atlas and persist resumable evaluation rows.

The append-safe JSONL evidence log is canonical. The historical matrix JSON remains
a compatibility view for the judge panel, reports, and committed snapshots.

    uv run python compare/run_matrix.py
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import httpx
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from compare import flavors as flavor_config  # noqa: E402
from compare.evaluation import (  # noqa: E402
    AtlasEvaluationClient,
    DatasetSpec,
    JsonlStore,
    QuestionSpec,
    SelectedApproach,
    completion_evidence,
    datasets,
    evidence_for_base,
    load_dataset,
    load_manifest,
    run_evaluation,
)
from compare.evaluation_summary import write_summary  # noqa: E402

RESULTS = ROOT / "compare" / "results"
# The six base approaches ("models" because that is the OpenAI-API field name at the
# gateway boundary). Derived, not copied — compare/flavors.py owns the display order.
ALL_MODELS = list(flavor_config.BASE_APPROACHES)

DEFAULT_EVALUATION_MANIFEST = ROOT / "compare" / "evaluation.yaml"


def envval(key: str, default: str = "") -> str:
    env = ROOT / "infra" / ".env"
    val = default
    if env.is_file():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith(key + "="):
                val = line.split("=", 1)[1].strip()  # last assignment wins
    return val


def queries_file() -> Path:
    return Path(os.environ.get("MATRIX_QUERIES_FILE", "demo/queries.yaml"))


def results_file() -> Path:
    return RESULTS / os.environ.get("MATRIX_RESULTS_FILE", "matrix.json")


def canonical_file() -> Path:
    configured = os.environ.get("MATRIX_CANONICAL_FILE")
    if configured:
        path = Path(configured)
        return path if path.is_absolute() else RESULTS / path
    return results_file().with_suffix(".jsonl")


def summary_file() -> Path:
    configured = os.environ.get("MATRIX_SUMMARY_FILE")
    if configured:
        path = Path(configured)
        return path if path.is_absolute() else RESULTS / path
    result = results_file()
    return result.with_name(f"{result.stem}-summary.json")


def evaluation_manifest_file() -> Path:
    path = Path(os.environ.get("MATRIX_MANIFEST_FILE", str(DEFAULT_EVALUATION_MANIFEST)))
    return path if path.is_absolute() else ROOT / path


def _csv_env(name: str) -> list[str]:
    return [m.strip() for m in os.environ.get(name, "").split(",") if m.strip()]


def flavors_file() -> Path:
    return Path(os.environ.get("MATRIX_FLAVORS_FILE", str(flavor_config.DEFAULT_MANIFEST)))


def ingestion_metadata() -> dict[str, str]:
    job_id = os.environ.get("MATRIX_INGESTION_JOB_ID") or os.environ.get(
        "MATRIX_INGESTION_ID", ""
    )
    fields = {
        "id": os.environ.get("MATRIX_INGESTION_ID", "") or job_id,
        "job_id": job_id,
        "profile": os.environ.get("MATRIX_INGESTION_PROFILE", ""),
        "revision": os.environ.get("MATRIX_INGESTION_REVISION", ""),
        "content_digest": os.environ.get("MATRIX_INGESTION_CONTENT_DIGEST", ""),
        "mode": os.environ.get("MATRIX_INGESTION_MODE", "showcase-managed"),
    }
    return {key: value for key, value in fields.items() if value}


def selected_profiles() -> list[flavor_config.FlavorProfile]:
    if models := _csv_env("MATRIX_MODELS"):
        return [flavor_config.profile_for_model(model, manifest=flavors_file()) for model in models]
    if selection := _csv_env("MATRIX_FLAVORS"):
        return flavor_config.expand_selection(selection, manifest=flavors_file())
    return [flavor_config.profile_for_model(model, manifest=flavors_file()) for model in ALL_MODELS]


def parse_content(content: str) -> dict:
    """Compatibility parser for callers that have only rendered answer text."""
    evidence = completion_evidence({"choices": [{"message": {"content": content}}]})
    return {
        "answer": evidence["answer"],
        "sources": evidence["sources"],
        "metrics": evidence["server_metrics"],
    }


def _sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _config_hashes(query_path: Path) -> dict[str, str]:
    paths = {
        "evaluation_manifest": evaluation_manifest_file(),
        "dataset_questions": query_path,
        "flavors": ROOT / flavors_file(),
        "roles": ROOT / "backend_plugins" / "rag" / "roles.yaml",
        "models": ROOT / "backend_plugins" / "rag" / "models.yaml",
        "consumer_manifest": ROOT / "atlas.consumer.yml",
        "atlas_env_user": ROOT / "config" / "atlas.env.user",
        "runtime_model_inventory": ROOT / "infra" / "volumes" / "litellm" / "consumer-models.yaml",
        "lightrag_query_profiles": ROOT / "infra" / "volumes" / "backend" / "lightrag-query-profiles.json",
    }
    return {
        name: digest
        for name, path in paths.items()
        if (digest := _sha256_file(path if path.is_absolute() else ROOT / path))
    }


def _git_state(path: Path) -> dict[str, str | bool]:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=path, text=True, capture_output=True, check=True
    ).stdout.strip()
    tree = subprocess.run(
        ["git", "rev-parse", "HEAD^{tree}"],
        cwd=path,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=path,
        capture_output=True,
        check=True,
    ).stdout
    tracked_patch = subprocess.run(
        ["git", "diff", "--binary", "HEAD", "--", "."],
        cwd=path,
        capture_output=True,
        check=True,
    ).stdout
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "-z"],
        cwd=path,
        capture_output=True,
        check=True,
    ).stdout.split(b"\0")

    digest = hashlib.sha256()
    digest.update(b"tracked-patch\0")
    digest.update(len(tracked_patch).to_bytes(8, "big"))
    digest.update(tracked_patch)
    digest.update(b"untracked-files\0")
    for relative_bytes in sorted(item for item in untracked if item):
        relative = Path(os.fsdecode(relative_bytes))
        absolute = path / relative
        content = (
            os.fsencode(os.readlink(absolute))
            if absolute.is_symlink()
            else absolute.read_bytes()
        )
        digest.update(len(relative_bytes).to_bytes(8, "big"))
        digest.update(relative_bytes)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)

    return {
        "commit": commit,
        "tree": tree,
        "dirty": bool(status.strip()),
        "patch_sha256": digest.hexdigest(),
        "patch_capture": "exact",
    }


def _runtime_file(path: Path, *, kind: str) -> dict[str, Any]:
    digest = _sha256_file(path)
    if not digest:
        raise RuntimeError(f"required generated runtime file is missing: {path}")
    if kind == "models":
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        entries = [row.get("model_name") for row in payload.get("model_list", [])]
    else:
        payload = json.loads(path.read_text(encoding="utf-8"))
        entries = [row.get("name") for row in payload.get("profiles", [])]
    return {
        "path": str(path.relative_to(ROOT)),
        "sha256": digest,
        "entries": sorted(str(entry) for entry in entries if entry),
    }


def _runtime_provenance(manifest=None) -> dict[str, Any]:
    manifest = manifest or load_manifest(evaluation_manifest_file())
    panel = manifest.metrics.judge_panel
    judge_models = _csv_env("JUDGE_MODELS") or list(panel.models)
    judge_endpoint = os.environ.get("JUDGE_ENDPOINT") or panel.endpoint
    if panel.enabled and not judge_models:
        raise ValueError(
            "enabled judge panel requires deployment-specific model aliases in "
            "JUDGE_MODELS before matrix execution"
        )
    judge_thinking = panel.thinking if judge_endpoint == "atlas-litellm" else None
    if "JUDGE_THINK" in os.environ:
        normalized = os.environ["JUDGE_THINK"].strip().lower()
        if normalized == "omit":
            judge_thinking = None
        elif normalized in {"true", "false"}:
            judge_thinking = normalized == "true"
        else:
            raise ValueError("JUDGE_THINK must be true, false, or omit")
    base_port = envval("BASE_PORT")
    if not base_port:
        litellm_port = envval("LITELLM_PORT")
        base_port = str(int(litellm_port) - 40) if litellm_port else "0"
    return {
        "project": envval("PROJECT_NAME", "rag-showcase"),
        "base_port": int(base_port),
        "provider_sources": {
            "llm": envval("LLM_PROVIDER_SOURCE", "unspecified"),
            "comfyui": envval("COMFYUI_SOURCE", "unspecified"),
        },
        "rag_showcase": _git_state(ROOT),
        "atlas": _git_state(ROOT / "infra"),
        "judge_panel": {
            "endpoint": judge_endpoint,
            "models": judge_models if panel.enabled else [],
            "thinking": judge_thinking,
        },
        "runtime_files": {
            "model_inventory": _runtime_file(
                ROOT / "infra" / "volumes" / "litellm" / "consumer-models.yaml",
                kind="models",
            ),
            "lightrag_query_profiles": _runtime_file(
                ROOT / "infra" / "volumes" / "backend" / "lightrag-query-profiles.json",
                kind="profiles",
            ),
        },
    }


def _dataset_for(manifest, query_path: Path) -> DatasetSpec:
    if dataset_id := os.environ.get("MATRIX_DATASET_ID"):
        return load_dataset(manifest, dataset_id)
    resolved = query_path.resolve()
    matches = [dataset for dataset in datasets(manifest) if dataset.questions_file == resolved]
    if len(matches) == 1:
        return matches[0]
    return DatasetSpec(
        id=query_path.stem,
        label=f"Ad hoc dataset ({query_path.name})",
        complexity_level=1,
        status="ad_hoc",
        corpus_path=ROOT,
        questions_file=resolved,
        graph_nature="unspecified",
    )


def _selected_approaches(manifest, profiles) -> list[SelectedApproach]:
    return [
        SelectedApproach(
            model=profile.alias,
            base_model=profile.base,
            flavor=profile.flavor,
            evidence=evidence_for_base(manifest, profile.base),
            requires_reingest=profile.requires_reingest,
        )
        for profile in profiles
    ]


def _legacy_cell(row: dict) -> dict:
    operational = row["metrics"]["operational"]
    evidence = row["evidence"]
    cell = {
        "query_id": row["question"]["id"],
        "model": row["approach"]["model"],
        "base_model": row["approach"]["base_model"],
        "flavor": row["approach"]["flavor"],
        "requires_reingest": row["approach"]["requires_reingest"],
        "ok": row["status"] == "ok",
        "latency_s": round(operational["latency_ms"] / 1000, 1),
    }
    if cell["ok"]:
        cell.update(
            {
                "raw": evidence["raw_content"],
                "answer": evidence["answer"],
                "sources": [
                    {"title": source["title"], "score": source.get("score")}
                    for source in evidence["sources"]
                ],
                "metrics": evidence["server_metrics"],
            }
        )
        if metadata := evidence.get("approach_metadata"):
            cell["approach_metadata"] = metadata
    else:
        error = row.get("error") or {}
        cell["error"] = f"{error.get('type', 'Error')}: {error.get('message', '')}"
    return cell


def main() -> None:
    port, key = envval("LITELLM_PORT"), envval("LITELLM_MASTER_KEY")
    if not port or not key:
        # Without these the run would grind through every cell against
        # "http://localhost:" and exit 0 with a 100%-error matrix.
        raise SystemExit("LITELLM_PORT / LITELLM_MASTER_KEY not found in infra/.env — "
                         "run scripts/start-all.sh first")
    base = f"http://localhost:{port}"
    manifest = load_manifest(evaluation_manifest_file())
    query_path = ROOT / queries_file()
    queries = yaml.safe_load(query_path.read_text(encoding="utf-8")) or []
    if not queries:
        raise SystemExit(f"{query_path}: no query rows")
    # Validate rows up front: a malformed row discovered mid-run used to abort the
    # matrix after real cells were already paid for, losing all of them.
    bad = [i for i, q in enumerate(queries)
           if not (isinstance(q, dict) and q.get("id") and q.get("query"))]
    if bad:
        raise SystemExit(f"{query_path}: query rows missing id/query at indices {bad}")
    seen_ids: set[str] = set()
    duplicate_ids: set[str] = set()
    for query in queries:
        query_id = str(query["id"])
        if query_id in seen_ids:
            duplicate_ids.add(query_id)
        seen_ids.add(query_id)
    if duplicate_ids:
        raise SystemExit(
            f"{query_path}: duplicate query id(s): {', '.join(sorted(duplicate_ids))}"
        )
    question_specs = [QuestionSpec.model_validate(query) for query in queries]
    profiles = selected_profiles()
    approaches = _selected_approaches(manifest, profiles)
    dataset = _dataset_for(manifest, query_path)
    run_id = os.environ.get("MATRIX_RUN_ID") or results_file().stem
    canonical = canonical_file()
    summary = summary_file()
    RESULTS.mkdir(parents=True, exist_ok=True)
    runtime_provenance = _runtime_provenance(manifest)
    out: dict = {"base": base, "models": [p.alias for p in profiles],
                 "model_profiles": [
                     {
                         "model": p.alias,
                         "base_model": p.base,
                         "flavor": p.flavor,
                         "requires_reingest": p.requires_reingest,
                         "experimental": p.base in flavor_config.EXPERIMENTAL_APPROACHES,
                     }
                     for p in profiles
                 ],
                 "queries_file": str(queries_file()),
                 "run_id": run_id,
                 "dataset_id": dataset.id,
                 "canonical_rows_file": str(canonical),
                 "evaluation_summary_file": str(summary),
                 "queries": [{k: q.get(k) for k in ("id", "query", "expect_winner", "rationale")}
                             for q in queries],
                 "runtime": runtime_provenance,
                 "cells": []}
    ingestion = ingestion_metadata()
    if ingestion:
        out["ingestion"] = ingestion
    print(f"matrix: {len(queries)} queries x {len(profiles)} approaches/flavors @ {base}")
    backend_port = envval("BACKEND_PORT")
    evaluator_endpoint = os.environ.get("MATRIX_EVALUATOR_URL")
    if not evaluator_endpoint and backend_port:
        evaluator_endpoint = f"http://localhost:{backend_port}/api/rag/evaluate"
    if manifest.metrics.ragas and not evaluator_endpoint:
        raise SystemExit(
            "BACKEND_PORT not found in infra/.env and MATRIX_EVALUATOR_URL is unset"
        )
    evaluator_headers = {}
    if evaluator_key := os.environ.get("MATRIX_EVALUATOR_API_KEY"):
        evaluator_headers[os.environ.get("MATRIX_EVALUATOR_API_KEY_HEADER", "apikey")] = evaluator_key

    with httpx.Client() as client:
        def invoke(model: str, query: str, timeout_s: float) -> dict:
            response = client.post(
                f"{base}/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": query}],
                    "cache": {"no-cache": True, "no-store": True},
                },
                timeout=httpx.Timeout(timeout_s, connect=10.0),
            )
            response.raise_for_status()
            return response.json()

        evaluator = (
            AtlasEvaluationClient(
                evaluator_endpoint,
                timeout_s=manifest.run.evaluator_timeout_s,
                retries=manifest.run.retries,
                headers=evaluator_headers,
            )
            if evaluator_endpoint and manifest.metrics.ragas
            else None
        )
        try:
            rows = run_evaluation(
                manifest=manifest,
                run_id=run_id,
                dataset=dataset,
                questions=question_specs,
                approaches=approaches,
                invoke=invoke,
                evaluator=evaluator,
                store=JsonlStore(canonical),
                config_hashes=_config_hashes(query_path),
                ingestion=ingestion,
                runtime_provenance=runtime_provenance,
            )
        finally:
            if evaluator is not None:
                evaluator.close()

    out["cells"] = [_legacy_cell(row) for row in rows]
    for cell in out["cells"]:
        tag = "ok " if cell.get("ok") else "ERR"
        ans = (cell.get("answer") or cell.get("error") or "")[:60].replace("\n", " ")
        print(
            f"  [{tag}] {cell['query_id']:14} {cell['model']:18} "
            f"{cell['latency_s']:6}s  {ans}",
            flush=True,
        )
    output = results_file()
    write_summary(canonical, summary)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(
        f"\nwrote {output} ({len(out['cells'])} cells); "
        f"canonical rows: {canonical}; summary: {summary}"
    )


if __name__ == "__main__":
    import argparse

    # Zero-option parser: config is env-var-only, but this makes --help safe (it used
    # to start a real matrix run and overwrite results) and rejects stray arguments.
    argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Configured via env vars: MATRIX_MANIFEST_FILE, MATRIX_DATASET_ID, "
               "MATRIX_RUN_ID, MATRIX_QUERIES_FILE, MATRIX_RESULTS_FILE, "
               "MATRIX_CANONICAL_FILE, MATRIX_SUMMARY_FILE, MATRIX_MODELS, MATRIX_FLAVORS, "
               "MATRIX_FLAVORS_FILE, MATRIX_EVALUATOR_URL, and MATRIX_INGESTION_* "
               "provenance fields.",
    ).parse_args()
    main()
