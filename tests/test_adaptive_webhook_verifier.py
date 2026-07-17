from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_module():
    path = ROOT / "scripts" / "verify_adaptive_webhook.py"
    spec = importlib.util.spec_from_file_location("verify_adaptive_webhook", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_verifier_requires_structured_rag_extension() -> None:
    module = _load_module()

    assert module.is_valid_payload(
        {
            "answer": "Grounded answer",
            "approach": "vanilla-rag",
            "rag_showcase": {"schema_version": 1},
        }
    )
    assert module.is_valid_payload(
        {
            "answer": "Synthesized answer",
            "approach": "agentic-rag",
            "rag_showcase": {"schema_version": 1},
        }
    )
    assert not module.is_valid_payload(
        {"answer": "fallback", "approach": "vanilla-rag", "rag_showcase": None}
    )
    assert not module.is_valid_payload(
        {
            "answer": "wrong route",
            "approach": "graph-rag",
            "rag_showcase": {"schema_version": 1},
        }
    )
