"""Consumer-owned evaluation contracts and execution primitives.

Atlas supplies OpenAI-compatible approach aliases and per-record Ragas scoring.
This module owns only the showcase-specific experiment schema and evidence
normalization. It deliberately imports no Atlas implementation modules.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO, Callable, Iterator, Literal, Protocol

import httpx
import yaml
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, PrivateAttr, model_validator


RagasMetric = Literal[
    "faithfulness",
    "answer_relevancy",
    "context_precision",
    "context_recall",
]
EvidenceCapability = Literal["answer_only", "answer_with_contexts"]

_FOOTER = re.compile(
    r"📊\s*([\d.]+)s\s*·\s*(\d+)\s*chunks?\s*·\s*(\d+)\s*LLM calls?\s*·\s*(\d+)\s*cloud"
)
_SOURCE_MARK = "<details><summary>🔎 Retrieved context"
_SOURCE_BLOCK = re.compile(
    r"\*\*(\d+)\.\s*(.+?)\*\*"
    r"(?:\s*·\s*score\s*([\d.]+))?\s*\n\n>\s?(.*?)"
    r"(?=\n\n\*\*\d+\.|\n\n</details>)",
    re.DOTALL,
)


class ApproachSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str = Field(min_length=1)
    evidence: EvidenceCapability


class JudgePanelSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    endpoint: str | None = None
    temperature: float = Field(default=0, ge=0, le=2)
    thinking: bool | None = None
    models: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_enabled_models(self) -> "JudgePanelSpec":
        if self.enabled and not self.models:
            raise ValueError("judge panel models must not be empty when enabled")
        if self.enabled and not self.endpoint:
            raise ValueError("judge panel endpoint must not be empty when enabled")
        if len(self.models) != len(set(self.models)):
            raise ValueError("judge panel models must be unique")
        return self


class MetricsSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ragas: list[RagasMetric] = Field(default_factory=list)
    judge_panel: JudgePanelSpec = Field(default_factory=JudgePanelSpec)


class RunSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    retries: int = Field(default=1, ge=0, le=10)
    timeout_s: float = Field(default=420, gt=0, le=3600)
    evaluator_timeout_s: float = Field(default=420, gt=0, le=3600)
    concurrency: int = Field(default=1, ge=1, le=32)
    seed: str = Field(default="rag-showcase-v1", min_length=1)


class DatasetSpec(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    complexity_level: int = Field(ge=1)
    status: str = Field(min_length=1)
    corpus_path: Path
    questions_file: Path = Field(validation_alias=AliasChoices("questions_file", "queries_file"))
    graph_nature: str = ""


class QuestionSpec(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str = Field(min_length=1)
    query: str = Field(min_length=1)
    ground_truth: str | None = Field(
        default=None, validation_alias=AliasChoices("ground_truth", "reference")
    )
    rationale: str | None = None
    expect_winner: str | None = None


@dataclass(frozen=True)
class SelectedApproach:
    model: str
    base_model: str
    flavor: str
    evidence: EvidenceCapability
    requires_reingest: bool = False


class EvaluationManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: Literal[1]
    root: Path = Path(".")
    datasets_file: Path
    approaches: list[ApproachSpec] = Field(min_length=1)
    metrics: MetricsSpec
    run: RunSettings

    _source_path: Path = PrivateAttr()
    _datasets: dict[str, DatasetSpec] = PrivateAttr(default_factory=dict)

    @model_validator(mode="after")
    def unique_approaches(self) -> "EvaluationManifest":
        names = [row.model for row in self.approaches]
        duplicates = sorted({name for name in names if names.count(name) > 1})
        if duplicates:
            raise ValueError(f"duplicate approach model(s): {', '.join(duplicates)}")
        return self


def _read_yaml(path: Path) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"cannot read {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ValueError(f"invalid YAML in {path}: {exc}") from exc


def load_manifest(path: Path) -> EvaluationManifest:
    """Load the versioned matrix manifest and its referenced dataset catalog."""
    source = path.expanduser().resolve()
    raw = _read_yaml(source)
    if not isinstance(raw, dict):
        raise ValueError(f"{source}: evaluation manifest must be a mapping")
    manifest = EvaluationManifest.model_validate(raw)
    root = (source.parent / manifest.root).resolve()
    datasets_file = (source.parent / manifest.datasets_file).resolve()
    catalog = _read_yaml(datasets_file)
    rows = catalog.get("datasets") if isinstance(catalog, dict) else None
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"{datasets_file}: datasets must be a non-empty list")

    ids = [str(row.get("id") or "") for row in rows if isinstance(row, dict)]
    duplicates = sorted({dataset_id for dataset_id in ids if ids.count(dataset_id) > 1})
    if duplicates:
        raise ValueError(f"duplicate dataset id(s): {', '.join(duplicates)}")

    datasets: dict[str, DatasetSpec] = {}
    for raw_dataset in rows:
        dataset = DatasetSpec.model_validate(raw_dataset)
        dataset.corpus_path = (root / dataset.corpus_path).resolve()
        dataset.questions_file = (root / dataset.questions_file).resolve()
        datasets[dataset.id] = dataset

    manifest.root = root
    manifest.datasets_file = datasets_file
    manifest._source_path = source
    manifest._datasets = datasets
    return manifest


def load_dataset(manifest: EvaluationManifest, dataset_id: str) -> DatasetSpec:
    try:
        return manifest._datasets[dataset_id].model_copy(deep=True)
    except KeyError as exc:
        raise ValueError(f"unknown dataset id: {dataset_id}") from exc


def datasets(manifest: EvaluationManifest) -> list[DatasetSpec]:
    return [dataset.model_copy(deep=True) for dataset in manifest._datasets.values()]


def evidence_for_base(manifest: EvaluationManifest, base: str) -> EvidenceCapability:
    for approach in manifest.approaches:
        if approach.model == base:
            return approach.evidence
    raise ValueError(f"no evidence capability declared for base approach: {base}")


def _rendered_evidence(content: str) -> dict[str, Any]:
    footers = list(_FOOTER.finditer(content))
    metrics = None
    body = content
    if footers:
        last = footers[-1]
        metrics = {
            "seconds": float(last.group(1)),
            "chunks": int(last.group(2)),
            "llm_calls": int(last.group(3)),
            "cloud_calls": int(last.group(4)),
        }
        body = content[:footers[0].start()].rstrip("\n").rstrip("-").rstrip("\n")
    source_index = body.find(_SOURCE_MARK)
    answer = body[:source_index].rstrip() if source_index != -1 else body
    sources = [
        {
            "title": title.strip(),
            "snippet": snippet.strip(),
            "score": float(score) if score else None,
        }
        for _, title, score, snippet in _SOURCE_BLOCK.findall(content)
    ]
    return {
        "answer": answer.strip(),
        "sources": sources,
        "contexts": [row["snippet"] for row in sources if row["snippet"]],
        "server_metrics": metrics,
    }


def completion_evidence(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize one OpenAI-compatible completion into the evidence contract.

    LiteLLM may preserve the plugin's structured extension, but the rendered answer
    remains the compatibility boundary. Parse both and prefer structured evidence.
    """
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("completion is missing choices[0].message.content") from exc
    if not isinstance(content, str):
        raise ValueError("completion content must be a string")

    normalized = _rendered_evidence(content)
    extension = payload.get("rag_showcase")
    transport = "rendered"
    if isinstance(extension, dict) and extension.get("schema_version") == 1:
        if isinstance(extension.get("answer"), str):
            normalized["answer"] = extension["answer"]
        raw_sources = extension.get("sources")
        if isinstance(raw_sources, list):
            sources = []
            for raw in raw_sources:
                if not isinstance(raw, dict) or not isinstance(raw.get("snippet"), str):
                    continue
                sources.append(
                    {
                        "title": str(raw.get("title") or ""),
                        "snippet": raw["snippet"],
                        "score": raw.get("score"),
                    }
                )
            normalized["sources"] = sources
            normalized["contexts"] = [row["snippet"] for row in sources if row["snippet"]]
        if isinstance(extension.get("metrics"), dict):
            normalized["server_metrics"] = dict(extension["metrics"])
        approach_metadata = {
            key: value
            for key, value in extension.items()
            if key not in {"schema_version", "answer", "sources", "metrics"}
        }
        if approach_metadata:
            normalized["approach_metadata"] = approach_metadata
        transport = "structured"

    usage = payload.get("usage")
    normalized.update(
        {
            "token_usage": dict(usage) if isinstance(usage, dict) else {},
            "response_id": payload.get("id"),
            "response_model": payload.get("model"),
            "raw_content": content,
            "transport": transport,
        }
    )
    return normalized


def stable_row_id(run_id: str, dataset_id: str, question_id: str, model: str) -> str:
    identity = {
        "run_id": run_id,
        "dataset_id": dataset_id,
        "question_id": question_id,
        "model": model,
        "schema_version": 1,
    }
    encoded = json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class JsonlStore:
    """Append-only canonical row store with strict duplicate detection."""

    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.Lock()
        self._loaded: list[dict[str, Any]] | None = None
        self._ids: set[str] = set()

    @property
    def _data_lock_path(self) -> Path:
        return self.path.with_name(f".{self.path.name}.lock")

    def _read_disk(self) -> tuple[list[dict[str, Any]], set[str]]:
        rows: list[dict[str, Any]] = []
        ids: set[str] = set()
        if not self.path.is_file():
            return rows, ids
        for line_number, line in enumerate(
            self.path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"{self.path}:{line_number}: invalid JSONL row: {exc}"
                ) from exc
            row_id = row.get("row_id") if isinstance(row, dict) else None
            if not isinstance(row_id, str) or not row_id:
                raise ValueError(f"{self.path}:{line_number}: row_id is required")
            if row_id in ids:
                raise ValueError(f"{self.path}: duplicate row_id {row_id}")
            ids.add(row_id)
            rows.append(row)
        return rows, ids

    def rows(self, *, refresh: bool = False) -> list[dict[str, Any]]:
        with self._lock:
            if self._loaded is not None and not refresh:
                return [dict(row) for row in self._loaded]
            with _exclusive_path_lock(self._data_lock_path):
                rows, ids = self._read_disk()
            self._loaded = rows
            self._ids = ids
            return [dict(row) for row in rows]

    def completed_ids(self, *, refresh: bool = False) -> set[str]:
        self.rows(refresh=refresh)
        with self._lock:
            return set(self._ids)

    @contextmanager
    def claim(self, row_id: str) -> Iterator[bool]:
        """Claim one cell across processes until its durable append completes."""
        if not row_id:
            raise ValueError("row_id is required for a claim")
        claim_key = hashlib.sha256(row_id.encode("utf-8")).hexdigest()
        claim_path = self.path.with_name(f".{self.path.name}.claims") / claim_key
        with _exclusive_path_lock(claim_path):
            yield row_id not in self.completed_ids(refresh=True)

    def append(self, row: dict[str, Any]) -> None:
        row_id = row.get("row_id")
        if not isinstance(row_id, str) or not row_id:
            raise ValueError("canonical row requires row_id")
        encoded = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            with _exclusive_path_lock(self._data_lock_path):
                disk_rows, disk_ids = self._read_disk()
                if row_id in disk_ids:
                    raise ValueError(f"refusing to append duplicate row_id {row_id}")
                with self.path.open("a", encoding="utf-8") as handle:
                    handle.write(encoded + "\n")
                    handle.flush()
                    os.fsync(handle.fileno())
            self._loaded = [*disk_rows, dict(row)]
            self._ids = {*disk_ids, row_id}


@contextmanager
def _exclusive_path_lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"\0")
            handle.flush()
        handle.seek(0)
        with _exclusive_file_lock(handle):
            yield


@contextmanager
def _exclusive_file_lock(handle: BinaryIO) -> Iterator[None]:
    """Serialize a sidecar lock file without assuming a particular host OS."""
    if os.name == "nt":
        import msvcrt

        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        try:
            yield
        finally:
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        return

    import fcntl

    fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
    try:
        yield
    finally:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


class Evaluator(Protocol):
    def evaluate(
        self,
        *,
        question: str,
        answer: str,
        contexts: list[str],
        reference: str | None,
        metrics: list[str],
        metadata: dict[str, Any],
    ) -> dict[str, Any]: ...


class AtlasEvaluationClient:
    """HTTP-only client for Atlas' generic per-record Ragas surface."""

    _CONTEXT_METRICS = {"faithfulness", "context_precision", "context_recall"}
    _REFERENCE_METRICS = {"context_precision", "context_recall"}

    def __init__(
        self,
        endpoint: str,
        *,
        timeout_s: float,
        retries: int = 0,
        headers: dict[str, str] | None = None,
        client: httpx.Client | None = None,
    ):
        self.endpoint = endpoint
        self.retries = retries
        self._owns_client = client is None
        self._client = client or httpx.Client(timeout=httpx.Timeout(timeout_s, connect=10.0))
        self._headers = dict(headers or {})

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "AtlasEvaluationClient":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def evaluate(
        self,
        *,
        question: str,
        answer: str,
        contexts: list[str],
        reference: str | None,
        metrics: list[str],
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        requested = list(dict.fromkeys(metrics))
        base: dict[str, Any] = {
            "requested": requested,
            "scores": {},
            "metric_errors": {},
            "not_evaluable": {},
            "evaluator_model": None,
            "embeddings_model": None,
        }
        if not requested:
            return {**base, "status": "disabled"}
        not_evaluable: dict[str, str] = {}
        if not contexts:
            not_evaluable.update(
                {
                    metric: "retrieved_contexts_required"
                    for metric in requested
                    if metric in self._CONTEXT_METRICS
                }
            )
        if not reference:
            for metric in requested:
                if metric in self._REFERENCE_METRICS:
                    not_evaluable.setdefault(metric, "ground_truth_required")
        eligible = [metric for metric in requested if metric not in not_evaluable]
        base["not_evaluable"] = not_evaluable
        if not eligible:
            return {**base, "status": "not_evaluable"}

        body = {
            "records": [
                {
                    "question": question,
                    "answer": answer,
                    "contexts": contexts,
                    "ground_truth": reference,
                    "metadata": metadata,
                }
            ],
            "metrics": eligible,
        }
        last_error: Exception | None = None
        for _ in range(self.retries + 1):
            try:
                response = self._client.post(self.endpoint, headers=self._headers, json=body)
                response.raise_for_status()
                payload = response.json()
                result = payload["results"][0]
                raw_scores = result.get("scores") or {}
                scores: dict[str, float] = {}
                metric_errors: dict[str, str] = {}
                for metric in eligible:
                    value = raw_scores.get(metric)
                    if value is None:
                        metric_errors[metric] = "score_missing_or_null"
                        continue
                    try:
                        score = float(value)
                    except (TypeError, ValueError):
                        metric_errors[metric] = "score_not_numeric"
                        continue
                    if not math.isfinite(score):
                        metric_errors[metric] = "score_not_finite"
                        continue
                    scores[metric] = score
                if metric_errors:
                    status = "partial" if scores else "error"
                else:
                    status = "partial" if not_evaluable else "ok"
                return {
                    **base,
                    "status": status,
                    "scores": scores,
                    "metric_errors": metric_errors,
                    "evaluator_model": payload.get("evaluator_model"),
                    "embeddings_model": payload.get("embeddings_model"),
                    "metadata": payload.get("metadata", {}),
                }
            except Exception as exc:  # noqa: BLE001 - preserve remote evaluator failures.
                last_error = exc
        assert last_error is not None
        return {
            **base,
            "status": "error",
            "error_type": type(last_error).__name__,
            "error": f"{type(last_error).__name__}: {last_error}",
        }


def _error_row(
    base: dict[str, Any], exc: Exception, latency_ms: int, attempts: int, judge_status: str
) -> dict[str, Any]:
    timeout = isinstance(exc, (httpx.TimeoutException, TimeoutError))
    return {
        **base,
        "status": "timeout" if timeout else "error",
        "evidence": {
            "answer": "",
            "contexts": [],
            "sources": [],
            "token_usage": {},
            "server_metrics": None,
            "response_id": None,
            "response_model": None,
            "raw_content": "",
            "transport": None,
        },
        "metrics": {
            "operational": {"latency_ms": latency_ms, "attempts": attempts},
            "ragas": {"status": "not_run", "requested": [], "scores": {}},
            "judge_panel": {"status": judge_status},
        },
        "error": {"type": type(exc).__name__, "message": str(exc)},
    }


def _base_row(
    *,
    manifest: EvaluationManifest,
    run_id: str,
    dataset: DatasetSpec,
    question: QuestionSpec,
    approach: SelectedApproach,
    row_id: str,
    config_hashes: dict[str, str],
    ingestion: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "runner_version": 1,
        "run_id": run_id,
        "row_id": row_id,
        "dataset": {
            "id": dataset.id,
            "label": dataset.label,
            "complexity_level": dataset.complexity_level,
            "questions_file": str(dataset.questions_file),
            "corpus_path": str(dataset.corpus_path),
        },
        "question": {
            "id": question.id,
            "query": question.query,
            "ground_truth": question.ground_truth,
            "rationale": question.rationale,
            "expect_winner": question.expect_winner,
        },
        "approach": {
            "model": approach.model,
            "base_model": approach.base_model,
            "flavor": approach.flavor,
            "evidence_capability": approach.evidence,
            "requires_reingest": approach.requires_reingest,
            "provider": "atlas-litellm",
        },
        "reproducibility": {
            "seed": manifest.run.seed,
            "config_hashes": dict(config_hashes),
            "ingestion": dict(ingestion),
        },
    }


def _run_cell(
    *,
    manifest: EvaluationManifest,
    run_id: str,
    dataset: DatasetSpec,
    question: QuestionSpec,
    approach: SelectedApproach,
    invoke: Callable[[str, str, float], dict[str, Any]],
    evaluator: Evaluator | None,
    config_hashes: dict[str, str],
    ingestion: dict[str, Any],
) -> dict[str, Any]:
    row_id = stable_row_id(run_id, dataset.id, question.id, approach.model)
    base = _base_row(
        manifest=manifest,
        run_id=run_id,
        dataset=dataset,
        question=question,
        approach=approach,
        row_id=row_id,
        config_hashes=config_hashes,
        ingestion=ingestion,
    )
    judge_status = "pending" if manifest.metrics.judge_panel.enabled else "disabled"
    started = time.perf_counter()
    payload: dict[str, Any] | None = None
    last_error: Exception | None = None
    attempts = 0
    for attempts in range(1, manifest.run.retries + 2):
        try:
            payload = invoke(approach.model, question.query, manifest.run.timeout_s)
            last_error = None
            break
        except Exception as exc:  # noqa: BLE001 - every failed cell is durable evidence.
            last_error = exc
    latency_ms = round((time.perf_counter() - started) * 1000)
    if last_error is not None or payload is None:
        assert last_error is not None
        return _error_row(base, last_error, latency_ms, attempts, judge_status)

    try:
        evidence = completion_evidence(payload)
    except Exception as exc:  # noqa: BLE001 - malformed provider response is a cell error.
        return _error_row(base, exc, latency_ms, attempts, judge_status)
    if approach.evidence == "answer_only":
        evidence["contexts"] = []

    if evaluator is None:
        ragas = {
            "status": "disabled",
            "requested": list(manifest.metrics.ragas),
            "scores": {},
            "not_evaluable": {},
            "evaluator_model": None,
            "embeddings_model": None,
        }
    else:
        ragas = evaluator.evaluate(
            question=question.query,
            answer=evidence["answer"],
            contexts=list(evidence["contexts"]),
            reference=question.ground_truth,
            metrics=list(manifest.metrics.ragas),
            metadata={"row_id": row_id, "run_id": run_id, "dataset_id": dataset.id},
        )
    return {
        **base,
        "status": "ok",
        "evidence": evidence,
        "metrics": {
            "operational": {
                "latency_ms": latency_ms,
                "attempts": attempts,
                "token_usage": evidence["token_usage"],
                "server": evidence["server_metrics"],
            },
            "ragas": ragas,
            "judge_panel": {"status": judge_status},
        },
        "error": None,
    }


def run_evaluation(
    *,
    manifest: EvaluationManifest,
    run_id: str,
    dataset: DatasetSpec,
    questions: list[QuestionSpec],
    approaches: list[SelectedApproach],
    invoke: Callable[[str, str, float], dict[str, Any]],
    evaluator: Evaluator | None,
    store: JsonlStore,
    config_hashes: dict[str, str] | None = None,
    ingestion: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Run and durably append missing cells, returning requested rows in stable order."""
    config_hashes = dict(config_hashes or {})
    ingestion = dict(ingestion or {})
    existing_rows = store.rows()
    existing = {row["row_id"]: row for row in existing_rows}
    tasks = [(question, approach) for question in questions for approach in approaches]

    def validate_resume_row(
        row: dict[str, Any], question: QuestionSpec, approach: SelectedApproach
    ) -> None:
        row_id = row["row_id"]
        reproducibility = row.get("reproducibility", {})
        changed = (
            row.get("question", {}).get("query") != question.query
            or row.get("approach", {}).get("base_model") != approach.base_model
            or row.get("approach", {}).get("flavor") != approach.flavor
            or reproducibility.get("seed") != manifest.run.seed
            or reproducibility.get("config_hashes", {}) != config_hashes
            or reproducibility.get("ingestion", {}) != ingestion
        )
        if changed:
            raise ValueError(
                f"resume row {row_id} does not match the current configuration; "
                "use a new MATRIX_RUN_ID or remove the stale canonical file"
            )

    for question, approach in tasks:
        row_id = stable_row_id(run_id, dataset.id, question.id, approach.model)
        if row := existing.get(row_id):
            validate_resume_row(row, question, approach)
    missing = [
        (question, approach)
        for question, approach in tasks
        if stable_row_id(run_id, dataset.id, question.id, approach.model) not in existing
    ]

    def execute(question: QuestionSpec, approach: SelectedApproach) -> dict[str, Any]:
        return _run_cell(
            manifest=manifest,
            run_id=run_id,
            dataset=dataset,
            question=question,
            approach=approach,
            invoke=invoke,
            evaluator=evaluator,
            config_hashes=config_hashes,
            ingestion=ingestion,
        )

    def execute_claimed(
        question: QuestionSpec, approach: SelectedApproach
    ) -> dict[str, Any]:
        row_id = stable_row_id(run_id, dataset.id, question.id, approach.model)
        with store.claim(row_id) as claimed:
            if not claimed:
                refreshed = {row["row_id"]: row for row in store.rows(refresh=True)}
                row = refreshed[row_id]
                validate_resume_row(row, question, approach)
                return row
            row = execute(question, approach)
            store.append(row)
            return row

    if manifest.run.concurrency == 1:
        for question, approach in missing:
            row = execute_claimed(question, approach)
            existing[row["row_id"]] = row
    else:
        with ThreadPoolExecutor(max_workers=manifest.run.concurrency) as executor:
            futures = {
                executor.submit(execute_claimed, question, approach): (question, approach)
                for question, approach in missing
            }
            for future in as_completed(futures):
                row = future.result()
                existing[row["row_id"]] = row

    return [
        existing[stable_row_id(run_id, dataset.id, question.id, approach.model)]
        for question, approach in tasks
    ]
