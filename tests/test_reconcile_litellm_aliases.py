from __future__ import annotations

import httpx
import pytest
import respx

from scripts import reconcile_litellm_aliases as reconciliation


EXPECTED = {
    "vanilla-rag": {
        "model": "openai/vanilla-rag",
        "api_base": "http://backend:8000/rag/vanilla-rag/v1",
    }
}


def _row(
    model_id: str,
    *,
    name: str = "vanilla-rag",
    model: str = "openai/vanilla-rag",
    api_base: str = "http://backend:8000/rag/vanilla-rag/v1",
    owner: str | None = None,
    managed: bool | None = None,
) -> dict:
    info = {"id": model_id}
    if owner is not None:
        info["atlas_owner"] = owner
    if managed is not None:
        info["atlas_managed"] = managed
    return {
        "model_name": name,
        "litellm_params": {"model": model, "api_base": api_base},
        "model_info": info,
    }


MANAGED = _row("managed", owner="rag-showcase", managed=True)


def test_legacy_ids_selects_current_and_pre_route_prefix_rows_only() -> None:
    rows = [
        _row("legacy-current"),
        _row("legacy-pre-prefix", api_base="http://backend:8000/vanilla-rag/v1"),
        MANAGED,
        _row("foreign-owner", owner="another-consumer"),
        _row("wrong-route", api_base="http://backend:8000/rag/hybrid-rag/v1"),
        _row("wrong-model", model="openai/something-else"),
        _row("unrelated", name="private-model"),
    ]

    assert reconciliation.legacy_ids(rows, EXPECTED) == [
        "legacy-current",
        "legacy-pre-prefix",
    ]


def test_legacy_ids_ignores_rows_without_deletable_ids() -> None:
    row = _row("legacy")
    row["model_info"].pop("id")

    assert reconciliation.legacy_ids([row], EXPECTED) == []


@respx.mock
def test_reconcile_deletes_only_legacy_rows_and_verifies_declared_aliases() -> None:
    info = respx.get("http://litellm:4000/model/info").mock(
        return_value=httpx.Response(200, json={"data": [_row("legacy"), MANAGED]})
    )
    delete = respx.post("http://litellm:4000/model/delete").mock(
        return_value=httpx.Response(200, json={})
    )
    models = respx.get("http://litellm:4000/v1/models").mock(
        return_value=httpx.Response(200, json={"data": [{"id": "vanilla-rag"}]})
    )

    assert reconciliation.reconcile("http://litellm:4000", "secret", EXPECTED) == 1
    assert info.call_count == 1
    assert delete.calls[0].request.content == b'{"id":"legacy"}'
    assert models.called


@respx.mock
def test_reconcile_is_idempotent_when_only_managed_rows_exist() -> None:
    info = respx.get("http://litellm:4000/model/info").mock(
        return_value=httpx.Response(200, json={"data": [MANAGED]})
    )
    delete = respx.post("http://litellm:4000/model/delete").mock(
        return_value=httpx.Response(200, json={})
    )
    respx.get("http://litellm:4000/v1/models").mock(
        return_value=httpx.Response(200, json={"data": [{"id": "vanilla-rag"}]})
    )

    assert reconciliation.reconcile("http://litellm:4000", "secret", EXPECTED) == 0
    assert info.call_count == 1
    assert not delete.called


@respx.mock
def test_reconcile_surfaces_delete_failures_without_continuing() -> None:
    respx.get("http://litellm:4000/model/info").mock(
        return_value=httpx.Response(200, json={"data": [_row("legacy"), MANAGED]})
    )
    respx.post("http://litellm:4000/model/delete").mock(
        return_value=httpx.Response(500, json={"error": "db locked"})
    )
    models = respx.get("http://litellm:4000/v1/models").mock(
        return_value=httpx.Response(200, json={"data": [{"id": "vanilla-rag"}]})
    )

    with pytest.raises(httpx.HTTPStatusError):
        reconciliation.reconcile("http://litellm:4000", "secret", EXPECTED)
    assert not models.called


@respx.mock
def test_reconcile_rejects_missing_owned_or_discoverable_aliases() -> None:
    respx.get("http://litellm:4000/model/info").mock(
        return_value=httpx.Response(200, json={"data": []})
    )

    with pytest.raises(RuntimeError, match="Atlas-owned rows missing"):
        reconciliation.reconcile("http://litellm:4000", "secret", EXPECTED)


@respx.mock
def test_reconcile_rejects_owned_alias_missing_from_model_discovery() -> None:
    respx.get("http://litellm:4000/model/info").mock(
        return_value=httpx.Response(200, json={"data": [MANAGED]})
    )
    respx.get("http://litellm:4000/v1/models").mock(
        return_value=httpx.Response(200, json={"data": []})
    )

    with pytest.raises(RuntimeError, match="missing from /v1/models"):
        reconciliation.reconcile("http://litellm:4000", "secret", EXPECTED)
