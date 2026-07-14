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
    assert resp["rag_showcase"] == {
        "schema_version": 1,
        "sources": [{"title": "Doc A", "snippet": "alpha", "score": 0.9}],
        "metrics": {"seconds": 1.2, "chunks": 1, "llm_calls": 1, "cloud_calls": 0},
    }


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


def test_build_response_includes_optional_approach_metadata():
    response = build_response(
        "lazy-graph-rag",
        "answer",
        [],
        Metrics(seconds=0.1, chunks=2, llm_calls=2, cloud_calls=0),
        metadata={"lazy_graph": {"cache_hit": True, "relevance_tests": 3}},
    )

    extension = response["rag_showcase"]
    assert extension["schema_version"] == 1
    assert extension["sources"] == []
    assert extension["metrics"]["chunks"] == 2
    assert extension["lazy_graph"] == {"cache_hit": True, "relevance_tests": 3}


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


def test_build_response_carries_created_and_unique_ids():
    # `created` is required by the OpenAI chat.completion schema (strict SDK
    # consumers reject its absence) and ids must not repeat across responses.
    a = build_response("m", "x", [], Metrics(0.5, 0, 1, 0))
    b = build_response("m", "x", [], Metrics(0.5, 0, 1, 0))
    assert isinstance(a["created"], int) and a["created"] > 0
    assert a["id"] != b["id"]
    assert a["id"].startswith("ragshow-m-")


def test_chat_request_last_user_null_content_is_empty_not_none_string():
    req = ChatRequest(model="x", messages=[{"role": "user", "content": None}])
    assert req.last_user() == ""  # not the literal string "None"


def test_chat_request_last_user_joins_multimodal_text_parts():
    # OpenAI content-parts arrays must yield the text, not a Python repr —
    # this string drives embedding, BM25, and the LLM prompt.
    req = ChatRequest(model="x", messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "what is"},
            {"type": "image_url", "image_url": {"url": "http://img"}},
            {"type": "text", "text": "alpha?"},
        ],
    }])
    assert req.last_user() == "what is alpha?"


@pytest.mark.asyncio
async def test_build_stream_response_emits_single_chunk_sse():
    import json as _json
    from rag.common.openai_io import build_stream_response

    sr = build_stream_response("m", "hello", [Source("T", "snip")],
                               Metrics(0.5, 1, 1, 0))
    assert sr.media_type == "text/event-stream"
    events = [part async for part in sr.body_iterator]
    assert events[-1] == "data: [DONE]\n\n"
    first = _json.loads(events[0].removeprefix("data: ").strip())
    assert first["object"] == "chat.completion.chunk"
    assert first["choices"][0]["finish_reason"] == "stop"
    content = first["choices"][0]["delta"]["content"]
    assert "hello" in content and "T" in content  # full rendered body in one chunk
    assert isinstance(first["created"], int)
    assert first["rag_showcase"]["sources"][0]["snippet"] == "snip"


@pytest.mark.asyncio
async def test_build_stream_response_preserves_evidence_and_approach_metadata():
    import json as _json
    from rag.common.openai_io import build_stream_response

    response = build_stream_response(
        "lazy-graph-rag",
        "hello",
        [Source("Doc", "context")],
        Metrics(0.5, 1, 2, 0),
        metadata={"lazy_graph": {"cache_hit": False}},
    )
    first_event = [part async for part in response.body_iterator][0]
    payload = _json.loads(first_event.removeprefix("data: ").strip())

    extension = payload["rag_showcase"]
    assert extension["schema_version"] == 1
    assert extension["sources"][0]["snippet"] == "context"
    assert extension["metrics"]["llm_calls"] == 2
    assert extension["lazy_graph"] == {"cache_hit": False}
