from __future__ import annotations

import json

import pytest

from rag.common import lightrag


@pytest.fixture(autouse=True)
def _clear_profile_cache():
    # Reset both the cache and the loaded-sentinel before AND after each test so
    # one test's (possibly empty) load can't mask the next test's env override.
    lightrag._PROFILE_CACHE.clear()
    lightrag._PROFILES_LOADED = False
    yield
    lightrag._PROFILE_CACHE.clear()
    lightrag._PROFILES_LOADED = False


def _write(tmp_path, monkeypatch, profiles: list[dict]) -> None:
    path = tmp_path / "profiles.json"
    path.write_text(
        json.dumps({
            "version": 1,
            "precedence": ["request", "profile", "service_env_default"],
            "profiles": profiles,
        }),
        encoding="utf-8",
    )
    monkeypatch.setenv("LIGHTRAG_QUERY_PROFILES_FILE", str(path))


def test_profile_overrides_service_defaults_and_request_overrides_profile(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("LIGHTRAG_QUERY_TOP_K", "7")
    monkeypatch.setenv("LIGHTRAG_QUERY_CHUNK_TOP_K", "3")
    _write(tmp_path, monkeypatch, [{
        "name": "graph-wide",
        "mode": "mix",
        "top_k": 30,
        "chunk_top_k": 12,
        "max_total_tokens": 24000,
        "enable_rerank": True,
    }])

    payload = lightrag._query_payload(
        "question", profile="graph-wide", options={"top_k": 42}
    )

    assert payload == {
        "query": "question",
        "mode": "mix",
        "enable_rerank": True,
        "top_k": 42,
        "chunk_top_k": 12,
        "max_total_tokens": 24000,
    }


def test_profile_omitted_values_inherit_service_defaults(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LIGHTRAG_QUERY_TOP_K", "7")
    monkeypatch.setenv("LIGHTRAG_QUERY_MAX_TOTAL_TOKENS", "4096")
    _write(tmp_path, monkeypatch, [{"name": "graph-local", "mode": "local"}])

    payload = lightrag._query_payload("question", profile="graph-local")

    assert payload["mode"] == "local"
    assert payload["top_k"] == 7
    assert payload["max_total_tokens"] == 4096


def test_unknown_profile_fails_before_calling_lightrag(tmp_path, monkeypatch) -> None:
    _write(tmp_path, monkeypatch, [{"name": "known", "mode": "hybrid"}])

    with pytest.raises(ValueError, match="unknown LightRAG query profile.*missing"):
        lightrag._query_payload("question", profile="missing")


def test_duplicate_profiles_are_rejected(tmp_path, monkeypatch) -> None:
    _write(tmp_path, monkeypatch, [
        {"name": "duplicate", "mode": "hybrid"},
        {"name": "duplicate", "mode": "local"},
    ])

    with pytest.raises(ValueError, match="duplicate LightRAG query profile"):
        lightrag._query_payload("question", profile="duplicate")


def test_empty_profiles_list_is_cached_negatively(tmp_path, monkeypatch) -> None:
    # A valid-but-empty profiles list yields an empty _PROFILE_CACHE, which is
    # falsy — the load must be remembered via _PROFILES_LOADED so a request-path
    # profile lookup doesn't re-open and re-parse the file on every call.
    _write(tmp_path, monkeypatch, [])

    with pytest.raises(ValueError, match="unknown LightRAG query profile"):
        lightrag._query_payload("question", profile="anything")

    assert lightrag._PROFILES_LOADED is True
    assert lightrag._PROFILE_CACHE == {}

    # Even if a profile later appears in the file, the one-time (empty) load
    # stays cached until the process restarts — same contract as config._load.
    _write(tmp_path, monkeypatch, [{"name": "late", "mode": "hybrid"}])
    with pytest.raises(ValueError, match="unknown LightRAG query profile"):
        lightrag._query_payload("question", profile="late")
