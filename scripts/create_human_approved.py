"""Create the final human-review dataset without changing source datasets."""

from __future__ import annotations

import copy
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "qa" / "proposed_reviewed.jsonl"
OUTPUT = ROOT / "data" / "qa" / "human_approved.jsonl"
REPORT = ROOT / "data" / "qa" / "human_approved_summary.json"

# These names are directly visible in the original textbook contexts or are
# verified by the shared chapter mapping for the Force context.
VERIFIED_CHAPTERS = {
    "dc28ca697e3e871c": ("Force", "original_context_heading"),
    "f20c5e8f69db1a2a": ("Force", "shared_chapter_context_heading"),
    "e5adc95b90b9e968": ("Synthetic Fibres and Plastics", "original_context_heading"),
}


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number} of {path}") from exc
    return rows


def main() -> None:
    proposed = read_jsonl(INPUT)
    if len(proposed) != 10:
        raise ValueError(f"Expected 10 proposed records, found {len(proposed)}")

    records = []
    for source_record in proposed:
        record = copy.deepcopy(source_record)
        candidate_id = record["candidate_id"]
        chapter_info = VERIFIED_CHAPTERS.get(candidate_id)

        if chapter_info:
            record["chapter"] = chapter_info[0]
            chapter_status = "verified"
            chapter_source = chapter_info[1]
        else:
            record["chapter"] = ""
            chapter_status = "requires_chapter_mapping"
            chapter_source = "no_reliable_chapter_name_in_available_metadata"

        human_review = copy.deepcopy(record.get("human_review", {}))
        human_review["decision"] = "ACCEPT"
        human_review["chapter_status"] = chapter_status
        human_review["chapter_source"] = chapter_source
        human_review["source_preserved"] = True
        record["human_review"] = human_review
        records.append(record)

    OUTPUT.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )

    report = {
        "source_file": str(INPUT.relative_to(ROOT)),
        "output_file": str(OUTPUT.relative_to(ROOT)),
        "records": len(records),
        "decisions": dict(Counter(record["human_review"]["decision"] for record in records)),
        "subject_counts": dict(Counter(record["subject"] for record in records)),
        "chapter_status_counts": dict(
            Counter(record["human_review"]["chapter_status"] for record in records)
        ),
        "excluded_rejected_records": 2,
        "validation_statuses_preserved": True,
        "source_provenance_preserved": True,
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(records)} records to {OUTPUT.relative_to(ROOT)}")
    print(f"Wrote summary to {REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
