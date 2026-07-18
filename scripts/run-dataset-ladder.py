#!/usr/bin/env python3
"""Run measured dataset-ladder evaluations end to end.

For each measured dataset in compare/datasets.yaml, this script can cold-reset the
Atlas stack, start rag-showcase without the default demo ingest, ingest exactly
that dataset, wait for LightRAG indexing to drain, run the selected base matrix and
optional non-base flavor tier, run the local judge panel, snapshot results under
docs/results, update the manifest, and regenerate the dataset report.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "compare" / "datasets.yaml"
RESULTS = ROOT / "compare" / "results"
DOC_RESULTS = ROOT / "docs" / "results"

# Make compare/ importable when run as a plain script (sys.path[0] is scripts/).
# Guarded: tests exec this module repeatedly and must not stack duplicate entries.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from compare.run_matrix import envval, flavors_file  # noqa: E402 — shared .env parser + manifest resolution
from compare import flavors as flavor_config  # noqa: E402 — selection validation
from compare.evaluation import load_manifest as load_evaluation_manifest  # noqa: E402


class _IndentedDumper(yaml.SafeDumper):
    def increase_indent(self, flow: bool = False, indentless: bool = False) -> None:
        return super().increase_indent(flow, False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        action="append",
        help="Measured dataset id to run. Repeat for multiple ids; defaults to all measured datasets.",
    )
    parser.add_argument(
        "--date-stamp",
        default=date.today().isoformat(),
        help="Date stamp for docs/results snapshots. Defaults to today.",
    )
    parser.add_argument(
        "--no-cold-reset",
        action="store_true",
        help="Reuse the current stack instead of cold-resetting before each dataset.",
    )
    parser.add_argument(
        "--approaches",
        default="",
        help="Comma-separated approach or flavor alias list (sets MATRIX_MODELS). "
             "Defaults to the canonical six approaches; --include-flavor-tier "
             "adds the experimental lazy-graph family.",
    )
    parser.add_argument(
        "--flavors",
        default="",
        help="Comma-separated MATRIX_FLAVORS selection, e.g. default,graph-rag-wide.",
    )
    parser.add_argument(
        "--include-candidates",
        action="store_true",
        help="Allow --dataset to select candidate datasets with committed/generated corpus paths.",
    )
    parser.add_argument(
        "--include-flavor-tier",
        action="store_true",
        help="Run all seven base approaches, then every non-base flavor alias against "
             "the same ingestion using separate result artifacts.",
    )
    return parser.parse_args()


def run(cmd: list[str], *, env: dict[str, str] | None = None) -> None:
    print(f"$ {' '.join(cmd)}", flush=True)
    subprocess.run(cmd, cwd=ROOT, env=env, check=True)


def capture_json(
    cmd: list[str], *, env: dict[str, str] | None = None
) -> dict[str, Any]:
    result = subprocess.run(
        cmd,
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "no child output"
        raise RuntimeError(
            f"command failed with exit {result.returncode}: {' '.join(cmd)}\n{detail}"
        )
    return json.loads(result.stdout)


def load_manifest() -> dict[str, Any]:
    return yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))


def evaluation_contract(env: dict[str, str]) -> tuple[set[str], list[str]]:
    raw_path = env.get("MATRIX_MANIFEST_FILE") or str(ROOT / "compare" / "evaluation.yaml")
    path = Path(raw_path)
    if not path.is_absolute():
        path = ROOT / path
    manifest = load_evaluation_manifest(path)
    judges = []
    if manifest.metrics.judge_panel.enabled:
        configured = env.get("JUDGE_MODELS", "")
        judges = (
            list(dict.fromkeys(item.strip() for item in configured.split(",") if item.strip()))
            if configured
            else list(manifest.metrics.judge_panel.models)
        )
        if not judges:
            raise RuntimeError(
                "enabled judge panel requires deployment-specific model aliases in "
                "JUDGE_MODELS (or models in MATRIX_MANIFEST_FILE)"
            )
    return set(manifest.metrics.ragas), judges


def write_manifest(manifest: dict[str, Any]) -> None:
    MANIFEST.write_text(
        yaml.dump(manifest, Dumper=_IndentedDumper, sort_keys=False, width=1000),
        encoding="utf-8",
    )


def project_name() -> str:
    name = envval("PROJECT_NAME")
    if not name:
        raise RuntimeError("PROJECT_NAME not found in infra/.env")
    return name


def cold_reset() -> None:
    print("$ ./scripts/stop-all.sh --cold", flush=True)
    subprocess.run(
        ["./scripts/stop-all.sh", "--cold"],
        cwd=ROOT,
        check=True,
    )


def start_service_only(dataset: dict[str, Any]) -> None:
    env = os.environ.copy()
    env["RAG_SHOWCASE_SKIP_DEFAULT_INGEST"] = "1"
    profile = dataset["ingestion_profile"]
    env["RAG_INGESTION_PROFILE"] = profile
    env["RAG_BASE_COLLECTION"] = f"RagBase_{profile}"
    env["RAG_CONTEXTUAL_COLLECTION"] = f"RagContextual_{profile}"
    run(["./scripts/start-all.sh"], env=env)


def ingest_dataset(dataset: dict[str, Any]) -> dict[str, Any]:
    corpus_path = Path(dataset["corpus_path"])
    if not (ROOT / corpus_path).is_dir():
        raise FileNotFoundError(f"dataset corpus not found: {corpus_path}")
    backend_port = envval("BACKEND_PORT")
    if not backend_port:
        raise RuntimeError("BACKEND_PORT not found in infra/.env")
    backend_token = envval("BACKEND_INTERNAL_API_TOKEN")
    if not backend_token:
        raise RuntimeError("BACKEND_INTERNAL_API_TOKEN not found in infra/.env")
    job_env = os.environ.copy()
    job_env["BACKEND_INTERNAL_API_TOKEN"] = backend_token
    record = capture_json(
        [
            "uv",
            "run",
            "python",
            "-m",
            "ingest.atlas_job",
            "--profile",
            dataset["ingestion_profile"],
            "--base-url",
            f"http://127.0.0.1:{backend_port}",
        ],
        env=job_env,
    )
    run(
        [
            "docker",
            "exec",
            "-e",
            "PYTHONPATH=/app/plugins:/app",
            f"{project_name()}-backend",
            "python",
            "-m",
            "ingest.contextual",
        ]
    )
    n8n_port = envval("N8N_PORT")
    if not n8n_port:
        raise RuntimeError("N8N_PORT not found in infra/.env")
    run(
        [
            "uv",
            "run",
            "python",
            "scripts/verify_adaptive_webhook.py",
            "--url",
            f"http://127.0.0.1:{n8n_port}/webhook/adaptive-rag",
        ]
    )
    return record


def validate_matrix_cells(matrix: dict[str, Any], *, dataset_id: str) -> None:
    failed = [cell for cell in matrix.get("cells", []) if not cell.get("ok")]
    if not failed:
        return
    preview = "; ".join(
        f"{cell.get('query_id', '?')}/{cell.get('model', '?')}: {cell.get('error', 'unknown error')}"
        for cell in failed[:5]
    )
    suffix = "" if len(failed) <= 5 else f"; ... {len(failed) - 5} more"
    raise RuntimeError(
        f"Matrix had {len(failed)} failed cells for {dataset_id}: {preview}{suffix}"
    )


def validate_judgments(
    judgments: dict[str, Any],
    *,
    dataset_id: str,
    expected_queries: set[str],
    expected_approaches: set[str],
    expected_judges: list[str],
) -> None:
    """Reject a judge run with unusable verdicts before it is snapshotted.

    judge.py exits 0 even when every call failed (e.g. host Ollama down), writing
    judgments whose per-query mean_by_approach is empty — previously committed as
    "measured" with no scores. Symmetric counterpart to validate_matrix_cells.
    """
    if judgments.get("status") == "disabled":
        if expected_judges:
            raise RuntimeError(f"Judgments for {dataset_id} were unexpectedly disabled")
        return
    queries = judgments.get("queries", [])
    if not queries:
        raise RuntimeError(f"Judgments for {dataset_id} contain no queries")
    bad = [q.get("query_id", "?") for q in queries if not q.get("mean_by_approach")]
    if bad:
        preview = ", ".join(bad[:5]) + ("" if len(bad) <= 5 else f", ... {len(bad) - 5} more")
        raise RuntimeError(
            f"Judgments for {dataset_id} have no valid verdicts for: {preview} "
            "(is the configured judge endpoint available?)"
        )
    if judgments.get("status") != "ok":
        raise RuntimeError(f"Judgments for {dataset_id} do not have status=ok")
    if judgments.get("judges") != expected_judges:
        raise RuntimeError(
            f"Judgments for {dataset_id} have unexpected judges: "
            f"{judgments.get('judges')} != {expected_judges}"
        )
    actual_queries = {str(query.get("query_id")) for query in queries}
    if actual_queries != expected_queries:
        raise RuntimeError(
            f"Judgments for {dataset_id} have incomplete query coverage: "
            f"{sorted(actual_queries)} != {sorted(expected_queries)}"
        )
    for query in queries:
        query_id = query.get("query_id", "?")
        means = set((query.get("mean_by_approach") or {}).keys())
        per_judge = query.get("per_judge") or {}
        if means != expected_approaches:
            raise RuntimeError(
                f"Judgments for {dataset_id}/{query_id} have incomplete approach coverage"
            )
        if list(per_judge) != expected_judges:
            raise RuntimeError(
                f"Judgments for {dataset_id}/{query_id} have incomplete judge coverage"
            )
        for judge in expected_judges:
            verdict = per_judge[judge]
            if verdict.get("error") or set((verdict.get("scores") or {}).keys()) != expected_approaches:
                raise RuntimeError(
                    f"Judgments for {dataset_id}/{query_id} have incomplete judge coverage "
                    f"for {judge}"
                )
    runtime = judgments.get("runtime")
    if not isinstance(runtime, dict) or not runtime.get("backend") or not runtime.get("endpoint"):
        raise RuntimeError(f"Judgments for {dataset_id} are missing judge runtime provenance")


def validate_canonical_rows(
    rows: list[dict[str, Any]],
    *,
    dataset_id: str,
    expected_cells: int,
    expected_queries: set[str],
    expected_approaches: set[str],
    expected_ragas: set[str],
) -> None:
    if len(rows) != expected_cells:
        raise RuntimeError(
            f"Canonical rows for {dataset_id}: expected {expected_cells}, found {len(rows)}"
        )
    row_ids = [row.get("row_id") for row in rows]
    if len(set(row_ids)) != len(row_ids):
        raise RuntimeError(f"Canonical rows for {dataset_id} contain duplicate row ids")
    wrong_dataset = [
        row_id
        for row_id, row in zip(row_ids, rows)
        if row.get("dataset", {}).get("id") != dataset_id
    ]
    if wrong_dataset:
        raise RuntimeError(
            f"Canonical rows for {dataset_id} contain rows from another dataset: "
            f"{wrong_dataset[:5]}"
        )
    expected_pairs = {
        (query_id, approach)
        for query_id in expected_queries
        for approach in expected_approaches
    }
    actual_pairs = {
        (str(row.get("question", {}).get("id")), str(row.get("approach", {}).get("model")))
        for row in rows
    }
    if actual_pairs != expected_pairs:
        raise RuntimeError(
            f"Canonical rows for {dataset_id} have incomplete query/approach coverage"
        )

    required_hashes = {
        "evaluation_manifest", "dataset_questions", "flavors", "roles",
        "consumer_manifest", "atlas_env_user", "runtime_model_inventory",
        "lightrag_query_profiles",
    }
    runtime_values: list[dict[str, Any]] = []
    hash_values: list[dict[str, str]] = []
    for row in rows:
        reproducibility = row.get("reproducibility") or {}
        hashes = reproducibility.get("config_hashes") or {}
        runtime = reproducibility.get("runtime") or {}
        if not required_hashes <= set(hashes):
            raise RuntimeError(
                f"Canonical rows for {dataset_id} are missing required provenance hashes"
            )
        runtime_files = runtime.get("runtime_files") or {}
        judge_panel = runtime.get("judge_panel") or {}
        rag_showcase = runtime.get("rag_showcase") or {}
        atlas = runtime.get("atlas") or {}
        runtime_complete = (
            runtime.get("project")
            and isinstance(runtime.get("base_port"), int)
            and (runtime.get("provider_sources") or {}).get("llm")
            and (runtime.get("provider_sources") or {}).get("comfyui")
            and rag_showcase.get("commit")
            and rag_showcase.get("tree")
            and rag_showcase.get("patch_sha256")
            and rag_showcase.get("patch_capture") in {"exact", "retrospective-known-scope"}
            and atlas.get("commit")
            and atlas.get("tree")
            and atlas.get("patch_sha256")
            and atlas.get("patch_capture") in {"exact", "retrospective-known-scope"}
            and judge_panel.get("endpoint")
            and isinstance(judge_panel.get("models"), list)
            and (runtime_files.get("model_inventory") or {}).get("sha256")
            and (runtime_files.get("lightrag_query_profiles") or {}).get("sha256")
        )
        if not runtime_complete:
            raise RuntimeError(
                f"Canonical rows for {dataset_id} are missing runtime provenance"
            )
        runtime_values.append(runtime)
        hash_values.append(hashes)

        if row.get("status") != "ok":
            continue
        ragas = (row.get("metrics") or {}).get("ragas") or {}
        if set(ragas.get("requested") or []) != expected_ragas:
            raise RuntimeError(
                f"Canonical row {row.get('row_id')} has unexpected Ragas metric coverage"
            )
        if ragas.get("status") not in {"ok", "partial", "not_evaluable", "error", "disabled"}:
            raise RuntimeError(
                f"Canonical row {row.get('row_id')} has non-terminal Ragas status"
            )
        if expected_ragas and ragas.get("status") == "disabled":
            raise RuntimeError(
                f"Canonical row {row.get('row_id')} has Ragas unexpectedly disabled"
            )
        covered = (
            set((ragas.get("scores") or {}).keys())
            | set((ragas.get("not_evaluable") or {}).keys())
            | set((ragas.get("metric_errors") or {}).keys())
        )
        if ragas.get("status") == "error" and ragas.get("error"):
            covered |= expected_ragas
        if ragas.get("status") != "disabled" and covered != expected_ragas:
            raise RuntimeError(
                f"Canonical row {row.get('row_id')} has incomplete Ragas metric coverage"
            )
    if any(value != runtime_values[0] for value in runtime_values[1:]):
        raise RuntimeError(f"Canonical rows for {dataset_id} have mixed runtime provenance")
    if any(value != hash_values[0] for value in hash_values[1:]):
        raise RuntimeError(f"Canonical rows for {dataset_id} have mixed config provenance")


def validate_evaluation_summary(
    summary: dict[str, Any],
    *,
    dataset_id: str,
    expected_cells: int,
    expected_status_counts: dict[str, int],
    expected_judges: list[str] | None = None,
    expected_query_count: int | None = None,
) -> None:
    if summary.get("schema_version") != 1:
        raise RuntimeError(f"Evaluation summary for {dataset_id} has unsupported schema version")
    dataset = summary.get("datasets", {}).get(dataset_id)
    if not isinstance(dataset, dict):
        raise RuntimeError(f"Evaluation summary is missing dataset {dataset_id}")
    coverage = dataset.get("coverage", {})
    actual = coverage.get("total_rows")
    if actual != expected_cells:
        raise RuntimeError(
            f"Evaluation summary for {dataset_id}: expected {expected_cells} rows, found {actual}"
        )
    if any(coverage.get(key) != value for key, value in expected_status_counts.items()):
        raise RuntimeError(
            f"Evaluation summary for {dataset_id} coverage does not match canonical rows"
        )
    if expected_judges is not None:
        judge = dataset.get("judge_panel") or {}
        if judge.get("models") != expected_judges:
            raise RuntimeError(
                f"Evaluation summary for {dataset_id} has unexpected judge models"
            )
        if expected_query_count is not None and (
            judge.get("evaluated_queries") != expected_query_count
            or judge.get("total_queries") != expected_query_count
        ):
            raise RuntimeError(
                f"Evaluation summary for {dataset_id} has incomplete judge coverage"
            )


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"{path}:{line_number}: invalid JSONL: {exc}") from exc
    return rows


def run_matrix_and_judge(
    dataset: dict[str, Any],
    ingestion: dict[str, Any],
    date_stamp: str,
    approaches: str,
    flavors: str,
    *,
    fresh_ingestion: bool = False,
    artifact_tier: str = "",
) -> tuple[Path, Path, Path, Path]:
    dataset_id = dataset["id"]
    if artifact_tier and artifact_tier != "flavors":
        raise ValueError(f"unsupported artifact tier: {artifact_tier}")
    stem = f"live-{date_stamp}-{dataset_id}"
    if artifact_tier:
        stem += f"-{artifact_tier}"
    run_id = stem
    matrix_name = f"{stem}-matrix.json"
    judgments_name = f"{stem}-judgments.json"
    evidence_name = f"{stem}-evidence.jsonl"
    evaluation_name = f"{stem}-evaluation.json"
    working_paths = [
        RESULTS / matrix_name,
        RESULTS / judgments_name,
        RESULTS / evidence_name,
        RESULTS / evaluation_name,
    ]
    if fresh_ingestion:
        for path in working_paths:
            path.unlink(missing_ok=True)
    env = os.environ.copy()
    # Exported MATRIX_MODELS/MATRIX_FLAVORS (e.g. left over from the documented
    # manual run_matrix.py workflow) must not govern the run: they'd bypass
    # validate_selections() and silently narrow the snapshot. Only the validated
    # CLI flags set them — MATRIX_FLAVORS_FILE inheritance, by contrast, is
    # deliberate and mirrored by validation.
    env.pop("MATRIX_MODELS", None)
    env.pop("MATRIX_FLAVORS", None)
    for key in (
        "MATRIX_INGESTION_ID",
        "MATRIX_INGESTION_JOB_ID",
        "MATRIX_INGESTION_PROFILE",
        "MATRIX_INGESTION_REVISION",
        "MATRIX_INGESTION_CONTENT_DIGEST",
        "MATRIX_INGESTION_MODE",
    ):
        env.pop(key, None)
    env["MATRIX_QUERIES_FILE"] = dataset["queries_file"]
    env["MATRIX_RESULTS_FILE"] = matrix_name
    env["MATRIX_CANONICAL_FILE"] = evidence_name
    env["MATRIX_SUMMARY_FILE"] = evaluation_name
    env["MATRIX_DATASET_ID"] = dataset_id
    env["MATRIX_RUN_ID"] = run_id
    env["MATRIX_INGESTION_ID"] = str(ingestion["id"])
    env["MATRIX_INGESTION_JOB_ID"] = str(ingestion["id"])
    env["MATRIX_INGESTION_PROFILE"] = str(ingestion["profile"])
    env["MATRIX_INGESTION_REVISION"] = str(ingestion["revision"])
    env["MATRIX_INGESTION_CONTENT_DIGEST"] = str(ingestion["content_digest"])
    env["MATRIX_INGESTION_MODE"] = "atlas-job"
    backend_token = envval("BACKEND_INTERNAL_API_TOKEN")
    if not backend_token:
        raise RuntimeError("BACKEND_INTERNAL_API_TOKEN not found in infra/.env")
    env["MATRIX_EVALUATOR_API_KEY_HEADER"] = "Authorization"
    env["MATRIX_EVALUATOR_API_KEY"] = f"Bearer {backend_token}"
    if approaches:
        env["MATRIX_MODELS"] = approaches
    if flavors:
        env["MATRIX_FLAVORS"] = flavors
    run(["uv", "run", "python", "compare/run_matrix.py"], env=env)
    matrix_src = RESULTS / matrix_name
    matrix_payload = json.loads(matrix_src.read_text(encoding="utf-8"))
    validate_matrix_cells(matrix_payload, dataset_id=dataset_id)
    expected_cells = len(matrix_payload.get("cells", []))
    expected_queries = {str(query["id"]) for query in matrix_payload.get("queries", [])}
    expected_approaches = set(matrix_payload.get("models", []))
    expected_ragas, expected_judges = evaluation_contract(env)
    evidence_src = RESULTS / evidence_name
    evaluation_src = RESULTS / evaluation_name
    canonical_rows = _load_jsonl(evidence_src)
    validate_canonical_rows(
        canonical_rows,
        dataset_id=dataset_id,
        expected_cells=expected_cells,
        expected_queries=expected_queries,
        expected_approaches=expected_approaches,
        expected_ragas=expected_ragas,
    )
    status_counts = {
        "ok": sum(row.get("status") == "ok" for row in canonical_rows),
        "errors": sum(row.get("status") == "error" for row in canonical_rows),
        "timeouts": sum(row.get("status") == "timeout" for row in canonical_rows),
    }
    validate_evaluation_summary(
        json.loads(evaluation_src.read_text(encoding="utf-8")),
        dataset_id=dataset_id,
        expected_cells=expected_cells,
        expected_status_counts=status_counts,
    )

    env = os.environ.copy()
    env["JUDGE_MATRIX_FILE"] = matrix_name
    env["JUDGE_RESULTS_FILE"] = judgments_name
    if manifest_path := os.environ.get("MATRIX_MANIFEST_FILE"):
        env["JUDGE_MANIFEST_FILE"] = manifest_path
    run(["uv", "run", "python", "compare/judge.py"], env=env)
    judgments_src = RESULTS / judgments_name
    validate_judgments(
        json.loads(judgments_src.read_text(encoding="utf-8")),
        dataset_id=dataset_id,
        expected_queries=expected_queries,
        expected_approaches=expected_approaches,
        expected_judges=expected_judges,
    )
    run([
        "uv", "run", "python", "compare/summarize.py",
        "--rows", str(evidence_src),
        "--judgments", str(judgments_src),
        "--output", str(evaluation_src),
    ])
    validate_evaluation_summary(
        json.loads(evaluation_src.read_text(encoding="utf-8")),
        dataset_id=dataset_id,
        expected_cells=expected_cells,
        expected_status_counts=status_counts,
        expected_judges=expected_judges,
        expected_query_count=len(expected_queries),
    )

    DOC_RESULTS.mkdir(parents=True, exist_ok=True)
    matrix_dst = DOC_RESULTS / matrix_name
    judgments_dst = DOC_RESULTS / judgments_name
    evidence_dst = DOC_RESULTS / evidence_name
    evaluation_dst = DOC_RESULTS / evaluation_name
    shutil.copy2(matrix_src, matrix_dst)
    shutil.copy2(judgments_src, judgments_dst)
    shutil.copy2(evidence_src, evidence_dst)
    shutil.copy2(evaluation_src, evaluation_dst)
    return matrix_dst, judgments_dst, evidence_dst, evaluation_dst


def update_dataset_snapshots(
    dataset_id: str,
    matrix_path: Path,
    judgments_path: Path,
    evidence_path: Path,
    evaluation_path: Path,
    *,
    flavor_paths: tuple[Path, Path, Path, Path] | None = None,
) -> None:
    manifest = load_manifest()
    for dataset in manifest["datasets"]:
        if dataset["id"] == dataset_id:
            dataset["matrix_snapshot"] = str(matrix_path.relative_to(ROOT))
            dataset["judgment_snapshot"] = str(judgments_path.relative_to(ROOT))
            dataset["evidence_snapshot"] = str(evidence_path.relative_to(ROOT))
            dataset["evaluation_snapshot"] = str(evaluation_path.relative_to(ROOT))
            if flavor_paths:
                flavor_matrix, flavor_judgments, flavor_evidence, flavor_evaluation = flavor_paths
                dataset["flavor_matrix_snapshot"] = str(flavor_matrix.relative_to(ROOT))
                dataset["flavor_judgment_snapshot"] = str(flavor_judgments.relative_to(ROOT))
                dataset["flavor_evidence_snapshot"] = str(flavor_evidence.relative_to(ROOT))
                dataset["flavor_evaluation_snapshot"] = str(flavor_evaluation.relative_to(ROOT))
            dataset["status"] = "measured"
            break
    else:
        raise KeyError(dataset_id)
    write_manifest(manifest)


def regenerate_report() -> None:
    run(["uv", "run", "python", "compare/report_datasets.py", "--output", "docs/dataset-complexity-report.md"])


def selected_datasets(
    ids: list[str] | None, *, include_candidates: bool = False
) -> list[dict[str, Any]]:
    allowed = {"measured", "candidate"} if include_candidates else {"measured"}
    datasets = [d for d in load_manifest()["datasets"] if d["status"] in allowed]
    if not ids:
        # No explicit selection: run only measured datasets. --include-candidates
        # widens what --dataset may NAME (per its help text); it must not silently
        # expand the default run set to every candidate rung.
        return [d for d in datasets if d["status"] == "measured"]
    wanted = set(ids)
    found = {d["id"] for d in datasets}
    missing = sorted(wanted - found)
    if missing:
        hint = "" if include_candidates else " (candidate ids need --include-candidates)"
        raise SystemExit(f"Unknown or unselectable dataset id(s): {', '.join(missing)}{hint}")
    return [d for d in datasets if d["id"] in wanted]


def validate_selections(approaches: str, flavors_csv: str) -> None:
    """Fail fast on unknown approach/flavor aliases BEFORE any destructive step
    (mirrors the corpus pre-validation): a typo otherwise aborts only when
    run_matrix launches — after the cold reset, full stack start, ingest, and
    LightRAG drain have already been paid."""
    # Resolve the manifest exactly as run_matrix will (MATRIX_FLAVORS_FILE wins):
    # validating against a different manifest would either falsely reject a
    # custom alias or let a bad one through to the post-reset KeyError. run()
    # launches run_matrix with cwd=ROOT, so a relative value resolves against the
    # repo root there — resolve identically here even when the ladder is launched
    # from another cwd (a missing manifest silently degrades to base-only
    # profiles, which would falsely reject the custom alias).
    manifest = flavors_file()
    if not manifest.is_absolute():
        manifest = ROOT / manifest
    try:
        for model in [m.strip() for m in approaches.split(",") if m.strip()]:
            flavor_config.profile_for_model(model, manifest=manifest)
        if flavors_csv:
            flavor_config.expand_selection(
                [t.strip() for t in flavors_csv.split(",") if t.strip()],
                manifest=manifest)
    except KeyError as exc:
        raise SystemExit(
            f"invalid --approaches/--flavors selection: {exc.args[0]}") from exc


def flavor_tier_models() -> list[str]:
    """Return every declared tuning alias, excluding all base-family routes."""
    manifest = flavors_file()
    if not manifest.is_absolute():
        manifest = ROOT / manifest
    profiles = flavor_config.load_flavors(manifest)
    bases = set(flavor_config.SUPPORTED_APPROACHES)
    return [profile.alias for profile in profiles.values() if profile.alias not in bases]


def main() -> None:
    args = parse_args()
    if args.approaches and args.flavors:
        raise SystemExit("--approaches and --flavors are mutually exclusive")
    if args.include_flavor_tier and (args.approaches or args.flavors):
        raise SystemExit(
            "--include-flavor-tier cannot be combined with --approaches or --flavors"
        )
    validate_selections(args.approaches, args.flavors)
    try:
        evaluation_contract(os.environ.copy())
    except (ValueError, RuntimeError) as exc:
        raise SystemExit(str(exc)) from exc
    tier_models = flavor_tier_models() if args.include_flavor_tier else []
    if tier_models:
        validate_selections(",".join(tier_models), "")
    datasets = selected_datasets(args.dataset, include_candidates=args.include_candidates)
    # Validate every selected corpus BEFORE the first cold reset: cold_reset() wipes
    # stack volumes, and discovering a missing generated corpus only after a full
    # multi-minute stack start destroys state for nothing.
    absent = [d["id"] for d in datasets if not (ROOT / d["corpus_path"]).is_dir()]
    if absent:
        raise SystemExit(
            f"dataset corpus dir(s) not found: {', '.join(absent)} — generate them first "
            "(corpus/README.md §1 for the curated baseline via fetch_corpus.py; "
            "corpus/adapters/README.md for candidate exports); "
            "refusing to touch the running stack")
    if args.no_cold_reset and len(datasets) > 1:
        # ingest.run() swaps the Weaviate collections per dataset but LightRAG only
        # accumulates — without a cold reset, graph-rag/agentic-rag would answer from
        # the union of all previously ingested corpora while the chunk approaches see
        # only the latest, silently skewing the comparison.
        raise SystemExit("--no-cold-reset supports a single dataset only; drop it or "
                         "run one --dataset at a time")
    for index, dataset in enumerate(datasets, start=1):
        print(f"\n==> Dataset {index}/{len(datasets)}: {dataset['id']}", flush=True)
        if not args.no_cold_reset:
            cold_reset()
        start_service_only(dataset)
        ingestion = ingest_dataset(dataset)
        base_approaches = args.approaches
        if args.include_flavor_tier:
            base_approaches = ",".join(flavor_config.SUPPORTED_APPROACHES)
        matrix, judgments, evidence, evaluation = run_matrix_and_judge(
            dataset,
            ingestion,
            args.date_stamp,
            base_approaches,
            args.flavors,
            fresh_ingestion=not args.no_cold_reset,
        )
        flavor_paths = None
        if tier_models:
            flavor_paths = run_matrix_and_judge(
                dataset,
                ingestion,
                args.date_stamp,
                ",".join(tier_models),
                "",
                fresh_ingestion=not args.no_cold_reset,
                artifact_tier="flavors",
            )
        update_dataset_snapshots(
            dataset["id"], matrix, judgments, evidence, evaluation,
            flavor_paths=flavor_paths,
        )
        regenerate_report()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
