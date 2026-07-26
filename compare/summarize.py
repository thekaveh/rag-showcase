#!/usr/bin/env python3
"""Build deterministic JSON summary views from canonical evaluation JSONL."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from compare.evaluation_summary import write_summary, write_summary_csv  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=Path, required=True, help="canonical evidence JSONL")
    parser.add_argument("--output", type=Path, required=True, help="summary JSON output")
    parser.add_argument("--csv-output", type=Path, help="optional long-form CSV view")
    parser.add_argument("--judgments", type=Path, help="optional legacy judge-panel JSON")
    args = parser.parse_args()
    summary = write_summary(args.rows, args.output, args.judgments)
    print(f"wrote {args.output}")
    if args.csv_output is not None:
        write_summary_csv(summary, args.csv_output)
        print(f"wrote {args.csv_output}")


if __name__ == "__main__":
    main()
