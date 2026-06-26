import os
import yaml
import httpx
import pytest

LITELLM = os.environ.get("LITELLM_BASE_URL", "http://localhost:4000")
KEY = os.environ.get("LITELLM_MASTER_KEY", "")
MODELS = ["vanilla-rag", "hybrid-rag", "contextual-rag",
          "graph-rag", "agentic-rag", "n8n-adaptive-rag"]


def _ask(model: str, query: str) -> str:
    r = httpx.post(f"{LITELLM}/v1/chat/completions",
                   headers={"Authorization": f"Bearer {KEY}"},
                   json={"model": model, "messages": [{"role": "user", "content": query}]},
                   timeout=180)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def test_all_models_registered(litellm_up):
    data = httpx.get(f"{LITELLM}/v1/models",
                     headers={"Authorization": f"Bearer {KEY}"}, timeout=10).json()
    ids = {m["id"] for m in data["data"]}
    for m in MODELS:
        assert m in ids, f"{m} not registered in LiteLLM"


def test_keyword_query_hybrid_finds_gold(litellm_up):
    answer = _ask("hybrid-rag",
                  "What does error code WIDGET-ERR-7741 mean and how do I reset it?")
    assert "WIDGET-ERR-7741" in answer or "thermal" in answer.lower()


@pytest.mark.parametrize("model", MODELS)
def test_every_model_answers(litellm_up, model):
    answer = _ask(model, "Give a one sentence summary of the corpus.")
    assert isinstance(answer, str) and len(answer) > 0
