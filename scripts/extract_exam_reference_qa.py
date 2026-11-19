"""Extract provenance-preserving QA examples from the examination PDFs.

This script is intentionally conservative. It uses only pypdf text extraction,
does not correct source wording, and never infers missing answers. Records that
are image-only, corrupted, question-only, or structurally ambiguous are kept
outside the candidate file for human review.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_DIR = ROOT / "data" / "exam_reference" / "source_pdfs"
DEFAULT_OUTPUT_DIR = ROOT / "data" / "exam_reference"

PDF_SPECS: dict[str, dict[str, str]] = {
    "biology_sa1.pdf": {"subject": "Biology", "language": "English"},
    "english_sa1.pdf": {"subject": "English", "language": "English"},
    "hindi_sa1.pdf": {"subject": "Hindi", "language": "Hindi"},
    "mathematics_sa1_2016.pdf": {"subject": "Mathematics", "language": "English"},
    "physical_science_sa1.pdf": {"subject": "Physical Science", "language": "English"},
    "social_studies_sa1.pdf": {"subject": "Social Studies", "language": "English"},
    "telugu_sa1.pdf": {"subject": "Telugu", "language": "Telugu"},
}

QUESTION_RE = re.compile(
    r"(?im)^\s*(?:[•▪]\s*)?((?:Question|Q)\s*\d+\s*[.)]?|\d+\s*[.)])\s*"
)
ANSWER_RE = re.compile(r"(?im)^\s*(Answer|उत्तर|उɠर|జĂњ)\s*:?\s*")
NON_LATIN_Q_RE = re.compile(r"(?im)^\s*(ʪశȼ|ಪ್ರಶ్న)\s*[^\n]*")
NON_LATIN_A_RE = re.compile(r"(?im)^\s*(జĂњ|జవాబు|ಉɠర)\s*\.?\s*")
PAGE_HEADER_RE = re.compile(
    r"(?im)^\s*(?:8th Class .*?schools360\.in.*|www\.schools360\.in.*|"
    r"Ts SA1 .*|Page\s*\d+|English\s*$|\-+\s*\d+\s*\-+\s*)\s*$"
)


@dataclass(frozen=True)
class Page:
    number: int
    text: str
    image_count: int


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _normalise_for_duplicate(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def _record_id(source_file: str, page: int, question: str, answer: str) -> str:
    payload = "|".join((source_file, str(page), question, answer)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def _read_pages(path: Path) -> list[Page]:
    reader = PdfReader(str(path))
    pages: list[Page] = []
    for number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        try:
            image_count = len(page.images)
        except Exception:  # pragma: no cover - depends on malformed PDF objects
            image_count = 0
        pages.append(Page(number, text, image_count))
    return pages


def _strip_headers(text: str) -> str:
    return PAGE_HEADER_RE.sub("", text).strip()


def _warnings(page: Page, text: str, language: str) -> list[str]:
    warnings: list[str] = []
    if page.image_count:
        warnings.append("page_contains_embedded_images")
    if not text.strip():
        warnings.append("no_text_layer")
    if language in {"Hindi", "Telugu"}:
        warnings.append("script_encoding_or_ocr_requires_review")
    if re.search(r"[�ƟȜʪĂњ]", text):
        warnings.append("replacement_or_legacy_encoded_characters")
    if "\n\n" not in text and len(text) > 1000:
        warnings.append("layout_boundaries_may_be_ambiguous")
    return warnings


def _make_record(
    *,
    spec: dict[str, str],
    source_file: str,
    page: Page,
    question: str,
    answer: str,
    question_number: str | None,
    status: str,
    confidence: str,
    notes: list[str],
    source_type: str,
) -> dict[str, Any]:
    question = question.strip()
    answer = answer.strip()
    return {
        "id": _record_id(source_file, page.number, question, answer),
        "subject": spec["subject"],
        "language": spec["language"],
        "chapter": None,
        "question": question,
        "answer": answer,
        "source_file": source_file,
        "source_page": page.number,
        "question_number": question_number,
        "source_type": source_type,
        "extraction_status": status,
        "extraction_confidence": confidence,
        "review_notes": notes,
    }


def _extract_marked_pairs(page: Page, spec: dict[str, str], source_file: str) -> list[dict[str, Any]]:
    text = _strip_headers(page.text)
    matches = list(QUESTION_RE.finditer(text))
    records: list[dict[str, Any]] = []
    for index, marker in enumerate(matches):
        section_end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        section = text[marker.end() : section_end].strip()
        answer_match = ANSWER_RE.search(section)
        if answer_match:
            question = section[: answer_match.start()].strip()
            answer = section[answer_match.end() :].strip()
            notes = _warnings(page, page.text, spec["language"])
            status = "candidate_ready"
            confidence = "high"
            if not question or not answer:
                status, confidence = "pending_review", "low"
                notes.append("incomplete_question_answer_boundary")
            if spec["language"] in {"Hindi", "Telugu"}:
                status, confidence = "pending_review", "low"
            records.append(_make_record(
                spec=spec, source_file=source_file, page=page,
                question=question, answer=answer,
                question_number=marker.group(1), status=status,
                confidence=confidence, notes=notes,
                source_type="question_answer_compilation",
            ))
        else:
            records.append(_make_record(
                spec=spec, source_file=source_file, page=page,
                question=section, answer="", question_number=marker.group(1),
                status="pending_review", confidence="low",
                notes=_warnings(page, page.text, spec["language"])
                + ["question_without_identifiable_answer"],
                source_type="question_bank_or_exam_reference",
            ))
    return records


def _extract_script_pairs(page: Page, spec: dict[str, str], source_file: str) -> list[dict[str, Any]]:
    text = _strip_headers(page.text)
    q_matches = list(NON_LATIN_Q_RE.finditer(text))
    a_matches = list(NON_LATIN_A_RE.finditer(text))
    if not q_matches or not a_matches:
        return []
    records: list[dict[str, Any]] = []
    for index, answer_match in enumerate(a_matches):
        prior_questions = [q for q in q_matches if q.start() < answer_match.start()]
        if not prior_questions:
            continue
        q_match = prior_questions[-1]
        next_boundary = a_matches[index + 1].start() if index + 1 < len(a_matches) else len(text)
        question = text[q_match.start() : answer_match.start()].strip()
        answer = text[answer_match.end() : next_boundary].strip()
        notes = _warnings(page, page.text, spec["language"])
        notes.append("legacy_script_boundary_requires_manual_review")
        records.append(_make_record(
            spec=spec, source_file=source_file, page=page,
            question=question, answer=answer, question_number=None,
            status="pending_review", confidence="low", notes=notes,
            source_type="question_answer_compilation",
        ))
    return records


def _extract_question_only_english(page: Page, spec: dict[str, str], source_file: str) -> list[dict[str, Any]]:
    if spec["subject"] != "English":
        return []
    text = _strip_headers(page.text)
    matches = list(re.finditer(r"(?im)^\s*([a-z])\)\s+(.+)$", text))
    if not matches:
        return []
    records: list[dict[str, Any]] = []
    for match in matches:
        question = f"{match.group(1)}) {match.group(2).strip()}"
        if len(question) < 8 or question.endswith(":"):
            continue
        records.append(_make_record(
            spec=spec, source_file=source_file, page=page,
            question=question, answer="", question_number=match.group(1),
            status="pending_review", confidence="medium",
            notes=_warnings(page, page.text, spec["language"])
            + ["question_without_model_answer"],
            source_type="question_bank_or_exam_reference",
        ))
    return records


def _extract_pdf(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    spec = PDF_SPECS[path.name]
    pages = _read_pages(path)
    records: list[dict[str, Any]] = []
    for page in pages:
        page_records = _extract_marked_pairs(page, spec, path.name)
        page_records.extend(_extract_script_pairs(page, spec, path.name))
        if not page_records:
            page_records.extend(_extract_question_only_english(page, spec, path.name))
        records.extend(page_records)
    if not any(record["source_file"] == path.name for record in records):
        if spec["subject"] == "Mathematics":
            for page in pages:
                records.append(_make_record(
                    spec=spec, source_file=path.name, page=page,
                    question="", answer="", question_number=None,
                    status="rejected", confidence="none",
                    notes=["image_only_page", "no_identifiable_question_or_answer_without_ocr"],
                    source_type="image_only_reference",
                ))
    metadata = {
        "subject": spec["subject"],
        "language": spec["language"],
        "source_file": path.name,
        "source_sha256": _sha256(path),
        "page_count": len(pages),
        "pages_with_text": sum(bool(page.text.strip()) for page in pages),
        "pages_with_images": sum(bool(page.image_count) for page in pages),
        "pages_with_embedded_images": [page.number for page in pages if page.image_count],
    }
    return records, metadata


def _deduplicate(records: Iterable[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    seen: dict[tuple[str, str], dict[str, Any]] = {}
    candidates: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for record in records:
        key = (
            _normalise_for_duplicate(record["question"]),
            _normalise_for_duplicate(record["answer"]),
        )
        if key != ("", "") and key in seen:
            duplicate = dict(record)
            duplicate["extraction_status"] = "rejected"
            duplicate["extraction_confidence"] = "high"
            duplicate["review_notes"] = list(record["review_notes"]) + [
                f"duplicate_of:{seen[key]['id']}"
            ]
            rejected.append(duplicate)
        else:
            if key != ("", ""):
                seen[key] = record
            if record["extraction_status"] == "candidate_ready":
                candidates.append(record)
            elif record["extraction_status"] == "rejected":
                rejected.append(record)
    return candidates, rejected


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    with path.open("x", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def run(source_dir: Path = DEFAULT_SOURCE_DIR, output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    paths = [source_dir / filename for filename in PDF_SPECS]
    missing = [path.name for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing expected PDFs: {', '.join(missing)}")
    output_paths = [
        output_dir / "qa_candidates.jsonl",
        output_dir / "qa_pending.jsonl",
        output_dir / "qa_rejected.jsonl",
        output_dir / "extraction_summary.json",
    ]
    existing = [path for path in output_paths if path.exists()]
    if existing:
        raise FileExistsError("Refusing to overwrite: " + ", ".join(str(path) for path in existing))

    all_records: list[dict[str, Any]] = []
    pdf_metadata: list[dict[str, Any]] = []
    for path in paths:
        records, metadata = _extract_pdf(path)
        all_records.extend(records)
        pdf_metadata.append(metadata)

    candidates, deduplicated_rejected = _deduplicate(all_records)
    pending = [record for record in all_records if record["extraction_status"] == "pending_review"]
    rejected = deduplicated_rejected

    safe_candidates: list[dict[str, Any]] = []
    for record in candidates:
        if not record["question"] or not record["answer"] or record["extraction_confidence"] != "high":
            record = dict(record)
            record["extraction_status"] = "pending_review"
            record["review_notes"] = list(record["review_notes"]) + ["candidate_quality_gate_failed"]
            pending.append(record)
        else:
            safe_candidates.append(record)

    by_subject: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for record in [*safe_candidates, *pending, *rejected]:
        by_subject[record["subject"]][record["extraction_status"]] += 1
    summary = {
        "source_directory": str(source_dir),
        "source_files": pdf_metadata,
        "records": {
            "candidate": len(safe_candidates),
            "pending": len(pending),
            "rejected": len(rejected),
            "total_classified": len(safe_candidates) + len(pending) + len(rejected),
        },
        "subject_counts": {subject: dict(counts) for subject, counts in sorted(by_subject.items())},
        "duplicate_records_rejected": sum(
            any(note.startswith("duplicate_of:") for note in record["review_notes"])
            for record in rejected
        ),
        "limitations": [
            "Extraction uses pypdf text layers only; no OCR or additional packages were used.",
            "Mathematics pages are image-only and therefore rejected without inventing text.",
            "Hindi and Telugu legacy-script extraction is retained verbatim and placed in pending review.",
            "Question-bank prompts without model answers are pending rather than treated as QA pairs.",
            "No record is marked human-approved.",
        ],
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_jsonl(output_paths[0], safe_candidates)
    _write_jsonl(output_paths[1], pending)
    _write_jsonl(output_paths[2], rejected)
    with output_paths[3].open("x", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    summary = run(args.source_dir, args.output_dir)
    print(json.dumps(summary["records"], indent=2))


if __name__ == "__main__":
    main()
