import pytest
from rag.common import config


def test_role_resolves_from_yaml(tmp_path, monkeypatch):
    f = tmp_path / "roles.yaml"
    f.write_text("light_gen: my-model\nembed: my-embed\n")
    monkeypatch.setenv("RAG_ROLES_FILE", str(f))
    config._CACHE.clear()
    assert config.role("light_gen") == "my-model"
    assert config.role("embed") == "my-embed"


def test_role_unknown_raises(tmp_path, monkeypatch):
    f = tmp_path / "roles.yaml"
    f.write_text("light_gen: x\n")
    monkeypatch.setenv("RAG_ROLES_FILE", str(f))
    config._CACHE.clear()
    with pytest.raises(KeyError):
        config.role("nope")
