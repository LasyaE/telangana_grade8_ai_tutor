"""Separate accepted, rejected and pending QA records and write a report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from training.corpus import read_jsonl, write_jsonl
from training.validate_qa import validate_candidates


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/qa/candidates.jsonl")
    parser.add_argument("--output-dir", default="data/qa")
    args = parser.parse_args()
    rows = read_jsonl(args.input)
    enriched, report = validate_candidates(rows)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(output_dir / "approved.jsonl", (row for row in enriched if row["validation"]["status"] == "accepted"))
    write_jsonl(output_dir / "rejected.jsonl", (row for row in enriched if row["validation"]["status"] == "rejected"))
    write_jsonl(output_dir / "pending.jsonl", (row for row in enriched if row["validation"]["status"] == "pending"))
    (output_dir / "quality_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
