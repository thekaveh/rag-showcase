#!/usr/bin/env python3
"""Run measured dataset-ladder evaluations end to end.

For each measured dataset in compare/datasets.yaml, this script can cold-reset the
Atlas stack, start rag-showcase without the default demo ingest, ingest exactly
that dataset, wait for LightRAG indexing to drain, run the six-way matrix, run the
local judge panel, snapshot results under docs/results, update the manifest, and
regenerate docs/dataset-complexity-report.md.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
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
             "Defaults to all six approaches.",
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
    return parser.parse_args()


def run(cmd: list[str], *, env: dict[str, str] | None = None) -> None:
    print(f"$ {' '.join(cmd)}", flush=True)
    subprocess.run(cmd, cwd=ROOT, env=env, check=True)


def capture_json(cmd: list[str]) -> dict[str, Any]:
    result = subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(result.stdout)


def load_manifest() -> dict[str, Any]:
    return yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))


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
    print("$ ./stop.sh --cold", flush=True)
    subprocess.run(["./stop.sh", "--cold"], cwd=ROOT / "infra", check=True)


def start_service_only() -> None:
    env = os.environ.copy()
    env["RAG_SHOWCASE_SKIP_DEFAULT_INGEST"] = "1"
    run(["./scripts/start-all.sh"], env=env)


def ingest_dataset(dataset: dict[str, Any]) -> None:
    corpus_path = Path(dataset["corpus_path"])
    if not (ROOT / corpus_path).is_dir():
        raise FileNotFoundError(f"dataset corpus not found: {corpus_path}")
    run(
        [
            "docker",
            "exec",
            "-e",
            "PYTHONPATH=/app/plugins",
            f"{project_name()}-backend",
            "python",
            "/app/ingest/ingest.py",
            f"/app/{corpus_path.as_posix()}",
        ]
    )


def _lightrag_get(path: str, timeout: int) -> dict[str, Any]:
    """GET a LightRAG endpoint from inside the backend container (in-network URL +
    the container's LIGHTRAG_API_KEY), returning the parsed JSON."""
    code = f"""
import json, os, httpx
r = httpx.get(
    "http://lightrag:9621{path}",
    headers={{"X-API-Key": os.environ.get("LIGHTRAG_API_KEY", "")}},
    timeout={timeout},
)
r.raise_for_status()
print(json.dumps(r.json()))
"""
    return capture_json(["docker", "exec", f"{project_name()}-backend", "python", "-c", code])


def lightrag_status() -> dict[str, Any]:
    return _lightrag_get("/documents/pipeline_status", timeout=10)


def lightrag_documents() -> dict[str, Any]:
    return _lightrag_get("/documents", timeout=20)


def wait_for_lightrag(dataset_id: str, timeout_s: int = 3600) -> None:
    deadline = time.monotonic() + timeout_s
    last = ""
    poll_failures = 0
    while time.monotonic() < deadline:
        try:
            # Both probes share the flakiness profile (docker exec + in-network
            # HTTP), so both live inside the same tolerance window.
            status = lightrag_status()
            busy = bool(status.get("busy") or status.get("request_pending"))
            docs = lightrag_documents() if not busy else None
            poll_failures = 0
        except (subprocess.CalledProcessError, ValueError) as exc:
            # One flaky poll must not abort a multi-hour ladder run; three in a
            # row means something is genuinely wrong. CalledProcessError's str()
            # omits the captured stderr, so surface it explicitly.
            poll_failures += 1
            detail = ((getattr(exc, "stderr", "") or "")[-300:]).strip()
            if poll_failures >= 3:
                raise RuntimeError(
                    f"LightRAG status poll failed {poll_failures} times in a row "
                    f"for {dataset_id}: {exc} {detail}") from exc
            print(f"[{dataset_id}] LightRAG status poll failed "
                  f"({poll_failures}/3), retrying: {exc} {detail}", flush=True)
            time.sleep(15)
            continue
        message = str(status.get("latest_message") or "")
        progress = (
            f"busy={busy} docs={status.get('docs')} "
            f"batch={status.get('cur_batch')}/{status.get('batchs')} {message[:96]}"
        )
        if progress != last:
            print(f"[{dataset_id}] LightRAG {progress}", flush=True)
            last = progress
        if not busy:
            statuses = (docs or {}).get("statuses", {}) or {}
            failed = statuses.get("failed") or statuses.get("FAILED")
            if failed:
                raise RuntimeError(f"LightRAG reported failed documents for {dataset_id}: {failed}")
            pending = (statuses.get("pending") or statuses.get("PENDING")
                       or statuses.get("processing") or statuses.get("PROCESSING"))
            if pending:
                # Not-busy gap between enqueue and pipeline pickup: documents are
                # still queued, so this is not drained yet.
                time.sleep(15)
                continue
            return
        time.sleep(15)
    raise TimeoutError(f"LightRAG did not drain for {dataset_id} within {timeout_s}s")


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


def validate_judgments(judgments: dict[str, Any], *, dataset_id: str) -> None:
    """Reject a judge run with unusable verdicts before it is snapshotted.

    judge.py exits 0 even when every call failed (e.g. host Ollama down), writing
    judgments whose per-query mean_by_approach is empty — previously committed as
    "measured" with no scores. Symmetric counterpart to validate_matrix_cells.
    """
    queries = judgments.get("queries", [])
    if not queries:
        raise RuntimeError(f"Judgments for {dataset_id} contain no queries")
    bad = [q.get("query_id", "?") for q in queries if not q.get("mean_by_approach")]
    if bad:
        preview = ", ".join(bad[:5]) + ("" if len(bad) <= 5 else f", ... {len(bad) - 5} more")
        raise RuntimeError(
            f"Judgments for {dataset_id} have no valid verdicts for: {preview} "
            "(is the host Ollama judge panel running?)"
        )


def run_matrix_and_judge(
    dataset: dict[str, Any], date_stamp: str, approaches: str, flavors: str
) -> tuple[Path, Path]:
    dataset_id = dataset["id"]
    matrix_name = f"live-{date_stamp}-{dataset_id}-matrix.json"
    judgments_name = f"live-{date_stamp}-{dataset_id}-judgments.json"
    env = os.environ.copy()
    # Exported MATRIX_MODELS/MATRIX_FLAVORS (e.g. left over from the documented
    # manual run_matrix.py workflow) must not govern the run: they'd bypass
    # validate_selections() and silently narrow the snapshot. Only the validated
    # CLI flags set them — MATRIX_FLAVORS_FILE inheritance, by contrast, is
    # deliberate and mirrored by validation.
    env.pop("MATRIX_MODELS", None)
    env.pop("MATRIX_FLAVORS", None)
    env["MATRIX_QUERIES_FILE"] = dataset["queries_file"]
    env["MATRIX_RESULTS_FILE"] = matrix_name
    if approaches:
        env["MATRIX_MODELS"] = approaches
    if flavors:
        env["MATRIX_FLAVORS"] = flavors
    run(["uv", "run", "python", "compare/run_matrix.py"], env=env)
    matrix_src = RESULTS / matrix_name
    validate_matrix_cells(json.loads(matrix_src.read_text(encoding="utf-8")), dataset_id=dataset_id)

    env = os.environ.copy()
    env["JUDGE_MATRIX_FILE"] = matrix_name
    env["JUDGE_RESULTS_FILE"] = judgments_name
    run(["uv", "run", "python", "compare/judge.py"], env=env)
    judgments_src = RESULTS / judgments_name
    validate_judgments(json.loads(judgments_src.read_text(encoding="utf-8")),
                       dataset_id=dataset_id)

    DOC_RESULTS.mkdir(parents=True, exist_ok=True)
    matrix_dst = DOC_RESULTS / matrix_name
    judgments_dst = DOC_RESULTS / judgments_name
    shutil.copy2(matrix_src, matrix_dst)
    shutil.copy2(judgments_src, judgments_dst)
    return matrix_dst, judgments_dst


def update_dataset_snapshots(dataset_id: str, matrix_path: Path, judgments_path: Path) -> None:
    manifest = load_manifest()
    for dataset in manifest["datasets"]:
        if dataset["id"] == dataset_id:
            dataset["matrix_snapshot"] = str(matrix_path.relative_to(ROOT))
            dataset["judgment_snapshot"] = str(judgments_path.relative_to(ROOT))
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


def main() -> None:
    args = parse_args()
    if args.approaches and args.flavors:
        raise SystemExit("--approaches and --flavors are mutually exclusive")
    validate_selections(args.approaches, args.flavors)
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
        start_service_only()
        ingest_dataset(dataset)
        wait_for_lightrag(dataset["id"])
        matrix, judgments = run_matrix_and_judge(
            dataset, args.date_stamp, args.approaches, args.flavors)
        update_dataset_snapshots(dataset["id"], matrix, judgments)
        regenerate_report()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
