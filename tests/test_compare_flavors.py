from pathlib import Path

import pytest
import yaml

from compare import flavors


def test_load_flavors_includes_default_profiles(tmp_path) -> None:
    missing = tmp_path / "missing.yaml"

    profiles = flavors.load_flavors(missing)

    assert profiles["graph-rag"].alias == "graph-rag"
    assert profiles["graph-rag"].base == "graph-rag"
    assert profiles["graph-rag"].flavor == "default"
    assert profiles["graph-rag"].requires_reingest is False


def test_expand_selection_supports_default_and_aliases(tmp_path) -> None:
    f = tmp_path / "flavors.yaml"
    f.write_text(
        """
flavors:
  - alias: graph-rag-wide
    base: graph-rag
    requires_reingest: false
  - alias: contextual-rag-rechunked
    base: contextual-rag
    flavor: rechunked
    requires_reingest: true
""",
        encoding="utf-8",
    )

    selected = flavors.expand_selection(["default", "graph-rag-wide"], manifest=f)

    assert [p.alias for p in selected][:6] == flavors.BASE_APPROACHES
    assert selected[-1].alias == "graph-rag-wide"
    assert selected[-1].base == "graph-rag"


def test_profile_for_model_reports_alias_metadata(tmp_path) -> None:
    f = tmp_path / "flavors.yaml"
    f.write_text(
        """
flavors:
  - alias: contextual-rag-rechunked
    base: contextual-rag
    flavor: rechunked
    requires_reingest: true
""",
        encoding="utf-8",
    )

    profile = flavors.profile_for_model("contextual-rag-rechunked", manifest=f)

    assert profile.alias == "contextual-rag-rechunked"
    assert profile.base == "contextual-rag"
    assert profile.flavor == "rechunked"
    assert profile.requires_reingest is True


def test_backend_and_compare_flavors_have_same_aliases() -> None:
    root = Path(__file__).resolve().parents[1]
    backend = yaml.safe_load((root / "backend_plugins/rag/flavors.yaml").read_text(encoding="utf-8"))
    compare = yaml.safe_load((root / "compare/flavors.yaml").read_text(encoding="utf-8"))

    backend_aliases = {row["alias"] for row in backend["flavors"]}
    compare_aliases = {row["alias"] for row in compare["flavors"]}

    assert backend_aliases == compare_aliases

    # base + params must also match per alias, not just the alias set. Otherwise a
    # tuning change in one manifest (e.g. graph-rag-wide.top_k) silently diverges the
    # deployed backend from the benchmark harness while this test stays green — the
    # exact drift the aliases-only check misses.
    backend_by_alias = {
        row["alias"]: (row["base"], row.get("params") or {}) for row in backend["flavors"]
    }
    compare_by_alias = {
        row["alias"]: (row["base"], row.get("params") or {}) for row in compare["flavors"]
    }

    assert backend_by_alias == compare_by_alias


def test_expand_selection_expands_base_name_to_all_its_flavors(tmp_path) -> None:
    # The ladder's --flavors graph-rag relies on a base NAME expanding to the base
    # plus every flavor bound to it (documented in approach-flavor-tuning.md §5).
    f = tmp_path / "flavors.yaml"
    f.write_text(
        """
flavors:
  - alias: graph-rag-wide
    base: graph-rag
  - alias: graph-rag-fast
    base: graph-rag
  - alias: hybrid-rag-fast
    base: hybrid-rag
""",
        encoding="utf-8",
    )

    selected = flavors.expand_selection(["graph-rag"], manifest=f)

    assert [p.alias for p in selected] == ["graph-rag", "graph-rag-wide", "graph-rag-fast"]


def test_unknown_model_raises_key_error(tmp_path) -> None:
    with pytest.raises(KeyError, match="nope-rag"):
        flavors.profile_for_model("nope-rag", manifest=tmp_path / "missing.yaml")


@pytest.mark.parametrize("manifest_text, err", [
    ("- alias: x-rag\n  base: graph-rag\n", "mapping"),              # top-level list (forgot the flavors: key)
    ("flavors: 42\n", "list under 'flavors'"),                       # non-list flavors
    ("flavors:\n  - 17\n", "non-object"),                            # non-object row
    ("flavors:\n  - base: graph-rag\n", "without alias"),            # missing alias
    ("flavors:\n  - alias: x-rag\n    base: nope\n", "unknown base"),  # unknown base
    ("flavors:\n  - alias: x\n    base: graph-rag\n    params: [1]\n", "params"),  # non-dict params
    ("flavors:\n  - alias: vanilla-rag\n    base: hybrid-rag\n", "shadows"),  # base shadow
    ("flavors:\n  - alias: g-x\n    base: graph-rag\n  - alias: g-x\n    base: graph-rag\n",
     "duplicate"),                                                    # duplicate alias
    ("flavors:\n  - alias: h-x\n    base: hybrid-rag\n    params:\n      retrieve_k: \"4o\"\n",
     "retrieve_k"),                                                   # non-numeric numeric param
    ("flavors:\n  - alias: h-y\n    base: hybrid-rag\n    params:\n      rerank: \"false\"\n",
     "rerank"),                                                       # quoted bool would invert intent
    ("flavors:\n  - alias: h-a\n    base: hybrid-rag\n    params:\n      alpha: 1.5\n",
     "alpha"),                                                        # out-of-range weighting
    ("flavors:\n  - alias: h-t\n    base: hybrid-rag\n    params:\n      top_n: 0\n",
     ">= 1"),                                                         # zero/negative limit
])
def test_both_loaders_reject_the_same_malformed_manifests(
        tmp_path, monkeypatch, manifest_text: str, err: str) -> None:
    # The two flavor loaders (compare-side pure loader, backend-side cached loader)
    # are deliberately separate implementations; their manifest DATA is sync-tested
    # elsewhere, but validation SEMANTICS can drift silently — one loader accepting
    # a row shape the other rejects. Feed both the same malformed manifests.
    from rag.common import flavors as backend_flavors

    f = tmp_path / "flavors.yaml"
    f.write_text(manifest_text, encoding="utf-8")

    with pytest.raises((ValueError, KeyError), match=err):
        flavors.load_flavors(f)

    monkeypatch.setenv("RAG_FLAVORS_FILE", str(f))
    backend_flavors._CACHE.clear()
    try:
        with pytest.raises((ValueError, KeyError), match=err):
            backend_flavors.get("vanilla-rag")
    finally:
        backend_flavors._CACHE.clear()


def test_canonical_six_names_agree_across_modules() -> None:
    # The host-side and backend loaders must agree on the stable base aliases.
    from rag.common import flavors as backend_flavors

    assert backend_flavors.BASE_APPROACHES == set(flavors.BASE_APPROACHES)
    assert len(flavors.BASE_APPROACHES) == 6
