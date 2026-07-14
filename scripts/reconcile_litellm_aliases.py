#!/usr/bin/env python3
"""Reconcile Atlas-owned LiteLLM aliases with pre-manifest database rows.

Atlas compiles the authoritative rows from ``atlas.consumer.yml`` before
LiteLLM starts. This compatibility check removes only exact, unowned duplicates
created by the retired registration script, then verifies ownership and model
discovery. It is safe and intentional to run on every showcase startup.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import httpx
import yaml


def load_expected(path: Path) -> dict[str, dict[str, str]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    expected: dict[str, dict[str, str]] = {}
    for row in data.get("model_list") or []:
        info = row.get("model_info") or {}
        params = row.get("litellm_params") or {}
        if info.get("atlas_owner") != "rag-showcase" or info.get("atlas_managed") is not True:
            continue
        name = row.get("model_name")
        model = params.get("model")
        api_base = params.get("api_base")
        if name and model and api_base:
            expected[str(name)] = {"model": str(model), "api_base": str(api_base)}
    if not expected:
        raise ValueError(f"no Atlas-owned rag-showcase models found in {path}")
    return expected


def _legacy_api_bases(current: str) -> set[str]:
    bases = {current.rstrip("/")}
    # Issue #26 moved every plugin route from /<approach>/v1 to
    # /rag/<approach>/v1. Direct upgrades can retain either DB row shape.
    if "/rag/" in current:
        bases.add(current.replace("/rag/", "/", 1).rstrip("/"))
    return bases


def legacy_ids(rows: list[dict], expected: dict[str, dict[str, str]]) -> list[str]:
    ids: list[str] = []
    for row in rows:
        name = row.get("model_name")
        wanted = expected.get(name)
        if wanted is None:
            continue
        info = row.get("model_info") or {}
        params = row.get("litellm_params") or {}
        model_id = info.get("id")
        api_base = str(params.get("api_base", "")).rstrip("/")
        if (
            not info.get("atlas_owner")
            and model_id
            and params.get("model") == wanted["model"]
            and api_base in _legacy_api_bases(wanted["api_base"])
        ):
            ids.append(str(model_id))
    return ids


def _missing_owned(rows: list[dict], expected: dict[str, dict[str, str]]) -> list[str]:
    found: set[str] = set()
    for row in rows:
        name = row.get("model_name")
        wanted = expected.get(name)
        if wanted is None:
            continue
        info = row.get("model_info") or {}
        params = row.get("litellm_params") or {}
        if (
            info.get("atlas_owner") == "rag-showcase"
            and info.get("atlas_managed") is True
            and params.get("model") == wanted["model"]
            and str(params.get("api_base", "")).rstrip("/")
            == wanted["api_base"].rstrip("/")
        ):
            found.add(str(name))
    return sorted(set(expected) - found)


def reconcile(base_url: str, api_key: str, expected: dict[str, dict[str, str]]) -> int:
    headers = {"Authorization": f"Bearer {api_key}"}
    with httpx.Client(base_url=base_url.rstrip("/"), headers=headers, timeout=30.0) as client:
        response = client.get("/model/info")
        response.raise_for_status()
        rows = response.json().get("data", [])
        if missing := _missing_owned(rows, expected):
            raise RuntimeError(f"Atlas-owned rows missing or mismatched: {', '.join(missing)}")

        ids = legacy_ids(rows, expected)
        for model_id in ids:
            deleted = client.post("/model/delete", json={"id": model_id})
            deleted.raise_for_status()

        listed = client.get("/v1/models")
        listed.raise_for_status()
        discovered = {str(row.get("id")) for row in listed.json().get("data", [])}
        if missing := sorted(set(expected) - discovered):
            raise RuntimeError(f"LiteLLM aliases missing from /v1/models: {', '.join(missing)}")
    return len(ids)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models-file", type=Path, required=True)
    parser.add_argument(
        "--changed-file",
        type=Path,
        help="write the number of deleted DB rows for startup restart handling",
    )
    args = parser.parse_args()

    base_url = os.environ.get("LITELLM_BASE_URL")
    api_key = os.environ.get("LITELLM_MASTER_KEY")
    if not base_url or not api_key:
        raise SystemExit("LITELLM_BASE_URL and LITELLM_MASTER_KEY are required")

    count = reconcile(base_url, api_key, load_expected(args.models_file))
    if args.changed_file:
        args.changed_file.write_text(f"{count}\n", encoding="utf-8")
    print(f"Verified all Atlas-owned aliases; removed {count} legacy row(s).")


if __name__ == "__main__":
    main()
