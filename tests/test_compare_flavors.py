from pathlib import Path

import yaml

from compare import flavors


def test_load_flavors_includes_default_profiles(tmp_path):
    missing = tmp_path / "missing.yaml"

    profiles = flavors.load_flavors(missing)

    assert profiles["graph-rag"].alias == "graph-rag"
    assert profiles["graph-rag"].base == "graph-rag"
    assert profiles["graph-rag"].flavor == "default"
    assert profiles["graph-rag"].requires_reingest is False


def test_expand_selection_supports_default_and_aliases(tmp_path):
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


def test_profile_for_model_reports_alias_metadata(tmp_path):
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


def test_backend_and_compare_flavors_have_same_aliases():
    root = Path(__file__).resolve().parents[1]
    backend = yaml.safe_load((root / "backend_plugins/rag/flavors.yaml").read_text())
    compare = yaml.safe_load((root / "compare/flavors.yaml").read_text())

    backend_aliases = {row["alias"] for row in backend["flavors"]}
    compare_aliases = {row["alias"] for row in compare["flavors"]}

    assert backend_aliases == compare_aliases
