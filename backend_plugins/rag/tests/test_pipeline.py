import pytest

from rag.common import pipeline
from rag.common.pipeline import answer_from_context, stuff
from rag.common.vectors import Hit


def test_stuff_formats_numbered_context_with_delimiters():
    prompt = stuff("my question", [Hit("Title A", "text-a"), Hit("Title B", "text-b")])
    assert "[1] Title A: text-a" in prompt
    assert "[2] Title B: text-b" in prompt
    assert "=== CONTEXT ===" in prompt and "=== QUESTION ===" in prompt
    assert "my question" in prompt


@pytest.mark.asyncio
async def test_answer_from_context_returns_model_content(monkeypatch):
    async def fake_chat(model, messages):
        assert model == "m"
        # the single user message carries the stuffed prompt (question + context)
        assert "my q" in messages[0]["content"] and "ctx-text" in messages[0]["content"]
        return {"choices": [{"message": {"content": "the answer"}}]}

    monkeypatch.setattr(pipeline.litellm, "chat", fake_chat)
    answer, calls = await answer_from_context("m", "my q", [Hit("T", "ctx-text")])
    assert answer == "the answer"
    assert calls == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("resp", [
    {"choices": []},                                # gateway returned no choices
    {},                                             # malformed: no choices key at all
    {"choices": [{"message": {"content": None}}]},  # choice present, null content
    {"choices": [{"message": {}}]},                 # choice present, no content key
])
async def test_answer_from_context_degrades_to_empty_string(monkeypatch, resp):
    # the degrade branch (pipeline.py:20-21) must yield "" — never None, never raise —
    # so callers can always concatenate/return the answer safely.
    async def fake_chat(model, messages): return resp

    monkeypatch.setattr(pipeline.litellm, "chat", fake_chat)
    answer, calls = await answer_from_context("m", "q", [Hit("T", "x")])
    assert answer == ""
    assert calls == 1
