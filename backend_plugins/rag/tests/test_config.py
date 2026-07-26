import pytest
from rag.common import config


@pytest.fixture(autouse=True)
def _clear_config_cache():
    # The role cache is process-global; clear it before AND after each test so a
    # populated cache never leaks across tests (or test modules). Reset both the
    # cache and the loaded-sentinel so a prior test's (negative) load can't mask
    # this test's RAG_ROLES_FILE.
    config._CACHE.clear()
    config._LOADED = False
    yield
    config._CACHE.clear()
    config._LOADED = False


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


def test_missing_roles_file_is_cached_negatively(tmp_path, monkeypatch):
    # A missing/empty roles file yields a falsy (empty) cache; the load must be
    # remembered via the _LOADED sentinel so it isn't re-stat + re-warn on every
    # role lookup (2+ per request).
    monkeypatch.setenv("RAG_ROLES_FILE", str(tmp_path / "absent.yaml"))
    config._load()
    assert config._LOADED is True
    assert config._CACHE == {}
    # Even if the file later appears, the one-time negative result stays cached.
    (tmp_path / "absent.yaml").write_text("light_gen: late\n", encoding="utf-8")
    config._load()
    assert config._CACHE == {}
