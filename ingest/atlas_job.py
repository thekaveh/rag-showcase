"""Submit one declared Atlas RAG ingestion profile and wait for completion."""
from __future__ import annotations

import argparse
import json
import time
from collections.abc import Callable
from typing import Any

import httpx


_TERMINAL = frozenset({"completed", "failed", "cancelled"})


def _failure_detail(record: dict[str, Any]) -> str:
    errors = record.get("errors") or []
    if not errors:
        return f"Atlas ingestion ended with status {record.get('status', 'unknown')}"
    return "; ".join(
        "/".join(
            str(value)
            for value in (
                error.get("phase"),
                error.get("service"),
                error.get("file"),
                error.get("message"),
            )
            if value
        )
        for error in errors
    )


def run_ingestion(
    profile: str,
    *,
    base_url: str,
    corpus_path: str | None = None,
    timeout_seconds: float = 7200,
    poll_seconds: float = 5,
    client: httpx.Client | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """Submit a profile and return Atlas's terminal phase record."""
    owned_client = client is None
    http = client or httpx.Client(timeout=httpx.Timeout(120.0, connect=10.0))
    try:
        response = http.post(
            f"{base_url.rstrip('/')}/api/rag/ingestions",
            params={"async_job": "true"},
            json={"profile": profile, "corpus_path": corpus_path},
            # Atlas runs synchronously in-request when its Celery tier is disabled.
            # Keep the submission alive for the same budget as the job itself.
            timeout=timeout_seconds + 60,
        )
        response.raise_for_status()
        queued = response.json()
        ingestion_id = str(queued["ingestion_id"])
        deadline = time.monotonic() + timeout_seconds
        while True:
            status_response = http.get(
                f"{base_url.rstrip('/')}/api/rag/ingestions/{ingestion_id}"
            )
            status_response.raise_for_status()
            record = status_response.json()
            status = str(record.get("status") or "")
            if status == "completed":
                return record
            if status in _TERMINAL:
                raise RuntimeError(_failure_detail(record))
            if time.monotonic() >= deadline:
                raise TimeoutError(
                    f"Atlas ingestion {ingestion_id} for profile {profile!r} did not "
                    f"finish within {timeout_seconds:g}s (last status: {status or 'unknown'})"
                )
            sleep(poll_seconds)
    finally:
        if owned_client:
            http.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--corpus-path")
    parser.add_argument("--timeout-seconds", type=float, default=7200)
    parser.add_argument("--poll-seconds", type=float, default=5)
    args = parser.parse_args()
    record = run_ingestion(
        args.profile,
        base_url=args.base_url,
        corpus_path=args.corpus_path,
        timeout_seconds=args.timeout_seconds,
        poll_seconds=args.poll_seconds,
    )
    print(json.dumps(record, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
