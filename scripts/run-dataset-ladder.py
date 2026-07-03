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
        help="Comma-separated MATRIX_MODELS override. Defaults to all six approaches.",
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


def envval(key: str) -> str:
    env = ROOT / "infra" / ".env"
    val = ""
    if env.is_file():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith(key + "="):
                val = line.split("=", 1)[1].strip()
    return val


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


def lightrag_status() -> dict[str, Any]:
    code = """
import json, os, httpx
r = httpx.get(
    "http://lightrag:9621/documents/pipeline_status",
    headers={"X-API-Key": os.environ.get("LIGHTRAG_API_KEY", "")},
    timeout=10,
)
r.raise_for_status()
print(json.dumps(r.json()))
"""
    return capture_json(["docker", "exec", f"{project_name()}-backend", "python", "-c", code])


def lightrag_documents() -> dict[str, Any]:
    code = """
import json, os, httpx
r = httpx.get(
    "http://lightrag:9621/documents",
    headers={"X-API-Key": os.environ.get("LIGHTRAG_API_KEY", "")},
    timeout=20,
)
r.raise_for_status()
print(json.dumps(r.json()))
"""
    return capture_json(["docker", "exec", f"{project_name()}-backend", "python", "-c", code])


def wait_for_lightrag(dataset_id: str, timeout_s: int = 3600) -> None:
    deadline = time.monotonic() + timeout_s
    last = ""
    while time.monotonic() < deadline:
        status = lightrag_status()
        busy = bool(status.get("busy") or status.get("request_pending"))
        message = str(status.get("latest_message") or "")
        progress = (
            f"busy={busy} docs={status.get('docs')} "
            f"batch={status.get('cur_batch')}/{status.get('batchs')} {message[:96]}"
        )
        if progress != last:
            print(f"[{dataset_id}] LightRAG {progress}", flush=True)
            last = progress
        if not busy:
            docs = lightrag_documents()
            failed = docs.get("statuses", {}).get("failed") or docs.get("statuses", {}).get("FAILED")
            if failed:
                raise RuntimeError(f"LightRAG reported failed documents for {dataset_id}: {failed}")
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


def run_matrix_and_judge(
    dataset: dict[str, Any], date_stamp: str, approaches: str, flavors: str
) -> tuple[Path, Path]:
    dataset_id = dataset["id"]
    matrix_name = f"live-{date_stamp}-{dataset_id}-matrix.json"
    judgments_name = f"live-{date_stamp}-{dataset_id}-judgments.json"
    env = os.environ.copy()
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

    DOC_RESULTS.mkdir(parents=True, exist_ok=True)
    judgments_src = RESULTS / judgments_name
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
    run(["python3", "compare/report_datasets.py", "--output", "docs/dataset-complexity-report.md"])


def selected_datasets(
    ids: list[str] | None, *, include_candidates: bool = False
) -> list[dict[str, Any]]:
    allowed = {"measured", "candidate"} if include_candidates else {"measured"}
    datasets = [d for d in load_manifest()["datasets"] if d["status"] in allowed]
    if not ids:
        return datasets
    wanted = set(ids)
    found = {d["id"] for d in datasets}
    missing = sorted(wanted - found)
    if missing:
        raise SystemExit(f"Unknown or unmeasured dataset id(s): {', '.join(missing)}")
    return [d for d in datasets if d["id"] in wanted]


def main() -> None:
    args = parse_args()
    if args.approaches and args.flavors:
        raise SystemExit("--approaches and --flavors are mutually exclusive")
    datasets = selected_datasets(args.dataset, include_candidates=args.include_candidates)
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
