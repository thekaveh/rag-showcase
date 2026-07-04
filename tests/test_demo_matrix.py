import httpx
import pytest

import compare.run_matrix as run_matrix
from conftest import KEY, LITELLM

MODELS = ["vanilla-rag", "hybrid-rag", "contextual-rag",
          "graph-rag", "agentic-rag", "n8n-adaptive-rag"]


def _ask(model: str, query: str) -> str:
    r = httpx.post(f"{LITELLM}/v1/chat/completions",
                   headers={"Authorization": f"Bearer {KEY}"},
                   json={"model": model, "messages": [{"role": "user", "content": query}]},
                   timeout=180)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def test_all_models_registered(litellm_up) -> None:
    r = httpx.get(f"{LITELLM}/v1/models",
                  headers={"Authorization": f"Bearer {KEY}"}, timeout=10)
    r.raise_for_status()
    data = r.json()
    ids = {m["id"] for m in data["data"]}
    for m in MODELS:
        assert m in ids, f"{m} not registered in LiteLLM"


def test_keyword_query_hybrid_finds_gold(litellm_up) -> None:
    answer = _ask("hybrid-rag",
                  "What does error code WIDGET-ERR-7741 mean and how do I reset it?")
    assert "WIDGET-ERR-7741" in answer or "thermal" in answer.lower()


@pytest.mark.parametrize("model", MODELS)
def test_every_model_answers(litellm_up, model) -> None:
    content = _ask(model, "Give a one sentence summary of the corpus.")
    # build_response always appends the metrics footer, so len(content) > 0 held
    # unconditionally for any 200 — parse the payload and assert the parts instead.
    parsed = run_matrix.parse_content(content)
    assert parsed["metrics"] is not None, "metrics footer missing or unparseable"
    assert parsed["answer"], "empty answer body (footer-only response)"
