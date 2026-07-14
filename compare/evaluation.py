"""Consumer-owned evaluation contracts and execution primitives.

Atlas supplies OpenAI-compatible approach aliases and per-record Ragas scoring.
This module owns only the showcase-specific experiment schema and evidence
normalization. It deliberately imports no Atlas implementation modules.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Literal

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
    models: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_enabled_models(self) -> "JudgePanelSpec":
        if self.enabled and not self.models:
            raise ValueError("judge panel models must not be empty when enabled")
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
