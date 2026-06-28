import pytest
from rag.common.openai_io import build_response, Source, Metrics, ChatRequest


def test_build_response_shapes_openai_and_embeds_sources():
    resp = build_response(
        model="vanilla-rag",
        answer="The answer.",
        sources=[Source(title="Doc A", snippet="alpha", score=0.9)],
        metrics=Metrics(seconds=1.2, chunks=1, llm_calls=1, cloud_calls=0),
    )
    assert resp["object"] == "chat.completion"
    assert resp["model"] == "vanilla-rag"
    content = resp["choices"][0]["message"]["content"]
    assert "The answer." in content
    assert "Doc A" in content and "alpha" in content
    assert "1.2s" in content and "1 chunk" in content
    assert "1 LLM call" in content  # footer renders the llm_calls field (guards _render_footer)
    # a non-None score must RENDER (positive assertion — the only other score test
    # checks the None case shows nothing). Drop/invert the score block and per-source
    # relevance silently disappears from this comparison surface, with tests green.
    assert "score 0.900" in content


def test_build_response_handles_empty_sources():
    resp = build_response("m", "ans", [], Metrics(0.5, 0, 1, 0))
    assert resp["object"] == "chat.completion"
    content = resp["choices"][0]["message"]["content"]
    assert "ans" in content


def test_build_response_source_without_score():
    resp = build_response("m", "ans", [Source("T", "snip")], Metrics(0.5, 1, 1, 0))
    content = resp["choices"][0]["message"]["content"]
    assert "T" in content and "snip" in content
    # When score is None, the rendered source block must not contain "score"
    details_start = content.find("<details>")
    details_end = content.find("</details>")
    source_block = content[details_start:details_end + len("</details>")]
    assert "score" not in source_block


def test_chat_request_last_user():
    req = ChatRequest(model="x", messages=[
        {"role": "system", "content": "s"},
        {"role": "user", "content": "first"},
        {"role": "user", "content": "second"},
    ])
    assert req.last_user() == "second"


def test_chat_request_last_user_empty_when_no_user_message():
    req = ChatRequest(model="x", messages=[{"role": "assistant", "content": "hi"}])
    assert req.last_user() == ""


@pytest.mark.parametrize("bad_answer", [{"x": 1}, [1, 2], 42, None])
def test_build_response_coerces_non_string_answer(bad_answer):
    # a non-string answer (operator-built n8n body, or structured content) must
    # not raise `dict/list/int + str` -> 500; it degrades to an empty answer.
    resp = build_response("m", bad_answer, [], Metrics(0.5, 0, 1, 0))
    assert resp["object"] == "chat.completion"
    assert isinstance(resp["choices"][0]["message"]["content"], str)
