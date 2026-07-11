import pytest
from rag.common import config


@pytest.fixture(autouse=True)
def _clear_config_cache():
    # The role cache is process-global; clear it before AND after each test so a
    # populated cache never leaks across tests (or test modules).
    config._CACHE.clear()
    yield
    config._CACHE.clear()


def test_role_resolves_from_yaml(tmp_path, monkeypatch):
    f = tmp_path / "roles.yaml"
    f.write_text("light_gen: my-model\nembed: my-embed\n", encoding="utf-8")
    monkeypatch.setenv("RAG_ROLES_FILE", str(f))
    assert config.role("light_gen") == "my-model"
    assert config.role("embed") == "my-embed"


def test_role_unknown_raises(tmp_path, monkeypatch):
    f = tmp_path / "roles.yaml"
    f.write_text("light_gen: x\n", encoding="utf-8")
    monkeypatch.setenv("RAG_ROLES_FILE", str(f))
    with pytest.raises(KeyError):
        config.role("nope")
