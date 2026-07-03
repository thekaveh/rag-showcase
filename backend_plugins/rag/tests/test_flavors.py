import pytest

from rag.common import flavors


@pytest.fixture(autouse=True)
def _clear_flavor_cache():
    flavors._CACHE.clear()
    yield
    flavors._CACHE.clear()


def test_get_returns_default_profile_for_canonical_approach(tmp_path, monkeypatch):
    monkeypatch.setenv("RAG_FLAVORS_FILE", str(tmp_path / "missing.yaml"))

    profile = flavors.get("graph-rag")

    assert profile.alias == "graph-rag"
    assert profile.base == "graph-rag"
    assert profile.label == "Default"
    assert profile.requires_reingest is False
    assert profile.params == {}


def test_get_resolves_alias_from_yaml(tmp_path, monkeypatch):
    f = tmp_path / "flavors.yaml"
    f.write_text(
        """
flavors:
  - alias: graph-rag-wide
    base: graph-rag
    label: Wide Graph
    description: Use wider graph and chunk fanout.
    requires_reingest: false
    params:
      mode: hybrid
      top_k: 30
      chunk_top_k: 12
      max_total_tokens: 24000
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("RAG_FLAVORS_FILE", str(f))

    profile = flavors.get("graph-rag-wide")

    assert profile.alias == "graph-rag-wide"
    assert profile.base == "graph-rag"
    assert profile.label == "Wide Graph"
    assert profile.description == "Use wider graph and chunk fanout."
    assert profile.requires_reingest is False
    assert profile.params == {
        "mode": "hybrid",
        "top_k": 30,
        "chunk_top_k": 12,
        "max_total_tokens": 24000,
    }


def test_get_returns_a_copy(tmp_path, monkeypatch):
    f = tmp_path / "flavors.yaml"
    f.write_text(
        """
flavors:
  - alias: hybrid-rag-high-recall
    base: hybrid-rag
    params:
      retrieve_k: 40
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("RAG_FLAVORS_FILE", str(f))

    flavors.get("hybrid-rag-high-recall").params["retrieve_k"] = 1

    assert flavors.get("hybrid-rag-high-recall").params == {"retrieve_k": 40}


def test_aliases_for_base_includes_canonical_and_configured_aliases(tmp_path, monkeypatch):
    f = tmp_path / "flavors.yaml"
    f.write_text(
        """
flavors:
  - alias: graph-rag-wide
    base: graph-rag
  - alias: graph-rag-fast
    base: graph-rag
  - alias: hybrid-rag-high-recall
    base: hybrid-rag
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("RAG_FLAVORS_FILE", str(f))

    assert flavors.aliases_for_base("graph-rag") == [
        "graph-rag",
        "graph-rag-wide",
        "graph-rag-fast",
    ]


def test_unknown_base_raises_key_error(tmp_path, monkeypatch):
    monkeypatch.setenv("RAG_FLAVORS_FILE", str(tmp_path / "missing.yaml"))

    with pytest.raises(KeyError):
        flavors.get("not-a-rag-approach")
