import pytest
from rag.common import config


@pytest.fixture(autouse=True)
def _clear_config_cache():
    # The role and models caches are process-global; clear both before AND after
    # each test so a populated cache never leaks across tests (or test modules).
    config._CACHE.clear()
    config._MODELS_CACHE.clear()
    yield
    config._CACHE.clear()
    config._MODELS_CACHE.clear()


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


def test_model_params_returns_props_for_listed_model(tmp_path, monkeypatch):
    f = tmp_path / "models.yaml"
    f.write_text("qwen3.6:latest:\n  think: false\n", encoding="utf-8")
    monkeypatch.setenv("RAG_MODELS_FILE", str(f))
    assert config.model_params("qwen3.6:latest") == {"think": False}


def test_model_params_scoped_to_listed_models(tmp_path, monkeypatch):
    # The merge must be scoped: a model not in models.yaml (e.g. a role later flipped
    # to a cloud model) gets nothing extra — so think:false never leaks to it.
    f = tmp_path / "models.yaml"
    f.write_text("qwen3.6:latest:\n  think: false\n", encoding="utf-8")
    monkeypatch.setenv("RAG_MODELS_FILE", str(f))
    assert config.model_params("claude-sonnet-4-6") == {}


def test_model_params_empty_when_file_absent(tmp_path, monkeypatch):
    monkeypatch.setenv("RAG_MODELS_FILE", str(tmp_path / "missing.yaml"))
    assert config.model_params("qwen3.6:latest") == {}


def test_model_params_returns_a_copy(tmp_path, monkeypatch):
    # Callers mutate the returned dict (litellm.chat merges into it); a caller must
    # never be able to corrupt the process-global cache for the next request.
    f = tmp_path / "models.yaml"
    f.write_text("m:\n  think: false\n", encoding="utf-8")
    monkeypatch.setenv("RAG_MODELS_FILE", str(f))
    config.model_params("m")["think"] = True
    assert config.model_params("m") == {"think": False}
