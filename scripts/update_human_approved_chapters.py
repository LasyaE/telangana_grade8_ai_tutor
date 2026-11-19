"""Apply verified chapter names to human-approved QA records."""

from __future__ import annotations

import copy
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "qa" / "human_approved.jsonl"
OUTPUT = ROOT / "data" / "qa" / "human_approved_chapter_mapped.jsonl"
REPORT = ROOT / "data" / "qa" / "human_approved_chapter_mapping_summary.json"

# Keys are deliberately subject + source page so the script verifies both
# fields before changing chapter metadata.
VERIFIED_MAPPINGS = {
    ("Mathematics", 28): "Rational Numbers",
    ("Mathematics", 40): "Rational Numbers",
    ("English", 32): "Oliver Asks for More",
    ("Physical Sciences", 28): "Force",
    ("Physical Sciences", 48): "Synthetic Fibres and Plastics",
    ("Biology", 38): "Cell – The Basic Unit of Life",
    ("Biology", 39): "Cell – The Basic Unit of Life",
    ("Biology", 73): "Reproduction in Animals",
    ("Social Studies", 50): "The Polar Regions",
}


def read_jsonl(path: Path) -> list[dict]:
    records: list[dict] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON on line {line_number} of {path}") from exc
        if not isinstance(record, dict):
            raise ValueError(f"Expected an object on line {line_number} of {path}")
        records.append(record)
    return records


def main() -> None:
    source_records = read_jsonl(INPUT)
    if len(source_records) != 10:
        raise ValueError(f"Expected 10 human-approved records, found {len(source_records)}")

    mapped_records: list[dict] = []
    applied: list[dict] = []
    for record in source_records:
        subject = record.get("subject")
        pages = record.get("source_pages")
        if not isinstance(pages, list) or len(pages) != 1 or not isinstance(pages[0], int):
            raise ValueError(
                f"Expected exactly one integer source page for {record.get('candidate_id')}"
            )

        page = pages[0]
        mapping_key = (subject, page)
        if mapping_key not in VERIFIED_MAPPINGS:
            raise ValueError(
                f"No verified mapping for subject={subject!r}, source_page={page!r}, "
                f"candidate_id={record.get('candidate_id')}"
            )

        mapped = copy.deepcopy(record)
        mapped["chapter"] = VERIFIED_MAPPINGS[mapping_key]
        mapped_records.append(mapped)
        applied.append(
            {
                "candidate_id": record.get("candidate_id"),
                "subject": subject,
                "source_pages": pages,
                "chapter": mapped["chapter"],
            }
        )

    OUTPUT.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in mapped_records),
        encoding="utf-8",
    )

    report = {
        "source_file": str(INPUT.relative_to(ROOT)),
        "output_file": str(OUTPUT.relative_to(ROOT)),
        "records_read": len(source_records),
        "records_mapped": len(mapped_records),
        "mapping_verification": "subject_and_source_page_verified",
        "subject_counts": dict(Counter(record["subject"] for record in mapped_records)),
        "chapter_counts": dict(Counter(record["chapter"] for record in mapped_records)),
        "applied_mappings": applied,
        "all_other_fields_preserved": True,
        "source_file_not_overwritten": True,
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(mapped_records)} mapped records to {OUTPUT.relative_to(ROOT)}")
    print(f"Wrote summary to {REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
