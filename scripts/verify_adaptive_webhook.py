#!/usr/bin/env python3
"""Require a real structured response from the adaptive RAG workflow."""
from __future__ import annotations

import argparse
import sys
from typing import Any

import httpx


ALLOWED_APPROACHES = {"vanilla-rag", "agentic-rag"}


def is_valid_payload(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    extension = payload.get("rag_showcase")
    return (
        isinstance(payload.get("answer"), str)
        and bool(payload["answer"].strip())
        and payload.get("approach") in ALLOWED_APPROACHES
        and isinstance(extension, dict)
        and extension.get("schema_version") == 1
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, help="Adaptive RAG production webhook URL")
    parser.add_argument("--timeout", type=float, default=240.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    response = httpx.post(
        args.url,
        json={"query": "What is retrieval-augmented generation?"},
        timeout=args.timeout,
    )
    response.raise_for_status()
    payload = response.json()
    if is_valid_payload(payload):
        return 0
    print(f"Invalid adaptive-rag response: {payload!r}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
