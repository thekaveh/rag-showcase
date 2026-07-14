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
import sys
from pathlib import Path

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


def evaluation_manifest_file() -> Path:
    path = Path(os.environ.get("MATRIX_MANIFEST_FILE", str(DEFAULT_EVALUATION_MANIFEST)))
    return path if path.is_absolute() else ROOT / path


def _csv_env(name: str) -> list[str]:
    return [m.strip() for m in os.environ.get(name, "").split(",") if m.strip()]


def flavors_file() -> Path:
    return Path(os.environ.get("MATRIX_FLAVORS_FILE", str(flavor_config.DEFAULT_MANIFEST)))


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
    }
    return {
        name: digest
        for name, path in paths.items()
        if (digest := _sha256_file(path if path.is_absolute() else ROOT / path))
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
    question_specs = [QuestionSpec.model_validate(query) for query in queries]
    profiles = selected_profiles()
    approaches = _selected_approaches(manifest, profiles)
    dataset = _dataset_for(manifest, query_path)
    run_id = os.environ.get("MATRIX_RUN_ID") or results_file().stem
    canonical = canonical_file()
    RESULTS.mkdir(parents=True, exist_ok=True)
    out: dict = {"base": base, "models": [p.alias for p in profiles],
                 "model_profiles": [
                     {
                         "model": p.alias,
                         "base_model": p.base,
                         "flavor": p.flavor,
                         "requires_reingest": p.requires_reingest,
                     }
                     for p in profiles
                 ],
                 "queries_file": str(queries_file()),
                 "run_id": run_id,
                 "dataset_id": dataset.id,
                 "canonical_rows_file": str(canonical),
                 "queries": [{k: q.get(k) for k in ("id", "query", "expect_winner", "rationale")}
                             for q in queries],
                 "cells": []}
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
                json={"model": model, "messages": [{"role": "user", "content": query}]},
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
                ingestion={
                    "profile": os.environ.get("MATRIX_INGESTION_PROFILE"),
                    "revision": os.environ.get("MATRIX_INGESTION_REVISION"),
                    "job_id": os.environ.get("MATRIX_INGESTION_JOB_ID"),
                    "mode": os.environ.get("MATRIX_INGESTION_MODE", "showcase-managed"),
                },
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
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {output} ({len(out['cells'])} cells); canonical rows: {canonical}")


if __name__ == "__main__":
    import argparse

    # Zero-option parser: config is env-var-only, but this makes --help safe (it used
    # to start a real matrix run and overwrite results) and rejects stray arguments.
    argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Configured via env vars: MATRIX_MANIFEST_FILE, MATRIX_DATASET_ID, "
               "MATRIX_RUN_ID, MATRIX_QUERIES_FILE, MATRIX_RESULTS_FILE, "
               "MATRIX_CANONICAL_FILE, MATRIX_MODELS, MATRIX_FLAVORS, "
               "MATRIX_FLAVORS_FILE, MATRIX_EVALUATOR_URL.",
    ).parse_args()
    main()
