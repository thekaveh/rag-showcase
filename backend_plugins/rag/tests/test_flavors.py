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


def test_malformed_flavor_row_raises_consistently_not_just_once(tmp_path, monkeypatch):
    # A bad row must raise on EVERY call. The regression this guards: seeding _CACHE
    # before validation let the first call raise while later calls hit the `if _CACHE`
    # short-circuit and silently returned a partial table (dropping every flavor after
    # the bad row). The parse must be atomic — nothing published unless the whole file
    # validates.
    f = tmp_path / "flavors.yaml"
    f.write_text(
        """
flavors:
  - alias: good-one
    base: hybrid-rag
  - alias: bad-one
    base: not-a-real-base
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("RAG_FLAVORS_FILE", str(f))

    with pytest.raises(KeyError):
        flavors.get("good-one")
    # second call must ALSO raise — the cache was not poisoned with a partial table
    with pytest.raises(KeyError):
        flavors.get("good-one")
    assert flavors._CACHE == {}  # nothing published on the failed parse
