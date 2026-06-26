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


def test_chat_request_last_user():
    req = ChatRequest(model="x", messages=[
        {"role": "system", "content": "s"},
        {"role": "user", "content": "first"},
        {"role": "user", "content": "second"},
    ])
    assert req.last_user() == "second"
