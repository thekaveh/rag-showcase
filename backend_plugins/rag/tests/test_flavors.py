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


def test_experimental_approach_resolves_without_changing_canonical_set(tmp_path, monkeypatch):
    monkeypatch.setenv("RAG_FLAVORS_FILE", str(tmp_path / "missing.yaml"))

    profile = flavors.get("lazy-graph-rag")

    assert profile.base == "lazy-graph-rag"
    assert "lazy-graph-rag" in flavors.EXPERIMENTAL_APPROACHES
    assert "lazy-graph-rag" not in flavors.BASE_APPROACHES
    assert len(flavors.BASE_APPROACHES) == 6


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


def test_get_strips_litellm_openai_prefix(tmp_path, monkeypatch):
    # LiteLLM registers our endpoints as openai/-provider models; a gateway that
    # forwards the prefixed name must still resolve.
    monkeypatch.setenv("RAG_FLAVORS_FILE", str(tmp_path / "missing.yaml"))
    assert flavors.get("openai/vanilla-rag").base == "vanilla-rag"


def test_get_for_base_rejects_flavor_of_another_base(tmp_path, monkeypatch):
    # e.g. model=hybrid-rag posted to the vanilla endpoint: must raise, not
    # silently run vanilla with foreign params.
    monkeypatch.setenv("RAG_FLAVORS_FILE", str(tmp_path / "missing.yaml"))
    with pytest.raises(KeyError, match="hybrid-rag"):
        flavors.get_for_base("hybrid-rag", "vanilla-rag")


def test_alias_shadowing_a_canonical_base_is_rejected(tmp_path, monkeypatch):
    # The module contract: the canonical six always resolve to their default
    # profile. A manifest row named like a base would silently redefine a stable
    # endpoint (and a cross-base shadow would 500 it outright).
    f = tmp_path / "flavors.yaml"
    f.write_text(
        """
flavors:
  - alias: vanilla-rag
    base: hybrid-rag
    params: {}
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("RAG_FLAVORS_FILE", str(f))
    with pytest.raises(ValueError, match="shadows a canonical base"):
        flavors.get("vanilla-rag")


def test_duplicate_alias_is_rejected(tmp_path, monkeypatch):
    f = tmp_path / "flavors.yaml"
    f.write_text(
        """
flavors:
  - alias: graph-rag-x
    base: graph-rag
    params: {}
  - alias: graph-rag-x
    base: graph-rag
    params: {}
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("RAG_FLAVORS_FILE", str(f))
    with pytest.raises(ValueError, match="duplicate flavor alias"):
        flavors.get("graph-rag-x")


def test_non_numeric_param_value_fails_at_load_not_per_request(tmp_path, monkeypatch):
    # Handlers coerce these with int()/float() per request; a typo'd value must
    # fail fast at load with a self-describing error, not become an unexplained
    # per-request 500 hours after the manifest edit.
    f = tmp_path / "flavors.yaml"
    f.write_text(
        """
flavors:
  - alias: hybrid-rag-typo
    base: hybrid-rag
    params:
      retrieve_k: "4o"
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("RAG_FLAVORS_FILE", str(f))
    with pytest.raises(ValueError, match="retrieve_k"):
        flavors.get("hybrid-rag-typo")
    # numeric strings are fine — they coerce at load
    f.write_text(
        """
flavors:
  - alias: hybrid-rag-str
    base: hybrid-rag
    params:
      retrieve_k: "40"
""",
        encoding="utf-8",
    )
    flavors._CACHE.clear()
    assert flavors.get("hybrid-rag-str").params["retrieve_k"] == 40


def test_bool_numeric_param_fails_at_load(tmp_path, monkeypatch):
    # bool is an int subclass — int(True)==1/float(False)==0.0 would silently
    # pass both the cast and the range check (0.0/1.0 are legitimate alpha
    # values), turning a manifest typo like `retrieve_k: true` into a
    # wrong-but-valid-looking parameter instead of the load-time ValueError
    # this loader promises. Mirrors compare/flavors.py's own drift-guard test.
    f = tmp_path / "flavors.yaml"
    f.write_text(
        """
flavors:
  - alias: hybrid-rag-bool
    base: hybrid-rag
    params:
      retrieve_k: true
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("RAG_FLAVORS_FILE", str(f))
    flavors._CACHE.clear()
    with pytest.raises(ValueError, match="retrieve_k"):
        flavors.get("hybrid-rag-bool")


@pytest.mark.parametrize("alpha", [1.5, -0.1])
def test_alpha_out_of_range_fails_at_load(tmp_path, monkeypatch, alpha):
    # alpha passes the float() type gate but is meaningless outside [0, 1] —
    # must fail loud at load, not become a per-request 500 downstream.
    f = tmp_path / "flavors.yaml"
    f.write_text(
        f"""
flavors:
  - alias: hybrid-rag-bad-alpha
    base: hybrid-rag
    params:
      alpha: {alpha}
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("RAG_FLAVORS_FILE", str(f))
    flavors._CACHE.clear()
    with pytest.raises(ValueError, match=r"alpha.*within \[0, 1\]"):
        flavors.get("hybrid-rag-bad-alpha")


@pytest.mark.parametrize("retrieve_k", [0, -5])
def test_non_alpha_numeric_param_below_one_fails_at_load(tmp_path, monkeypatch, retrieve_k):
    # A zero/negative retrieve_k (or any non-alpha numeric param) passes the
    # int() type gate but is meaningless — must fail loud at load.
    f = tmp_path / "flavors.yaml"
    f.write_text(
        f"""
flavors:
  - alias: hybrid-rag-bad-k
    base: hybrid-rag
    params:
      retrieve_k: {retrieve_k}
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("RAG_FLAVORS_FILE", str(f))
    flavors._CACHE.clear()
    with pytest.raises(ValueError, match=r"retrieve_k.*must be >= 1"):
        flavors.get("hybrid-rag-bad-k")
