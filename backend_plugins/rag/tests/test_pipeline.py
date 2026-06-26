from rag.common.pipeline import stuff
from rag.common.vectors import Hit


def test_stuff_formats_numbered_context_with_delimiters():
    prompt = stuff("my question", [Hit("Title A", "text-a"), Hit("Title B", "text-b")])
    assert "[1] Title A: text-a" in prompt
    assert "[2] Title B: text-b" in prompt
    assert "=== CONTEXT ===" in prompt and "=== QUESTION ===" in prompt
    assert "my question" in prompt
