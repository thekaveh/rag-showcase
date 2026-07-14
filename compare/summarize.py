#!/usr/bin/env python3
"""Build deterministic JSON summary views from canonical evaluation JSONL."""
from __future__ import annotations

import argparse
from pathlib import Path

from compare.evaluation_summary import write_summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=Path, required=True, help="canonical evidence JSONL")
    parser.add_argument("--output", type=Path, required=True, help="summary JSON output")
    parser.add_argument("--judgments", type=Path, help="optional legacy judge-panel JSON")
    args = parser.parse_args()
    write_summary(args.rows, args.output, args.judgments)
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
