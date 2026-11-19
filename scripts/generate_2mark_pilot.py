
"""'''
The pilot uses only exact excerpts already present in the retrieval corpus and
chapter-context artifacts. It does not call a model or invent textbook facts.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from training.corpus import load_chunks, normalize_text, read_jsonl, write_jsonl
from training.schemas import QACandidate, ValidationResult
from training.validate_qa import validate_candidate


ROOT = Path(__file__).resolve().parents[1]
APPROVED = ROOT / "data" / "qa" / "human_approved_chapter_mapped.jsonl"
CORPUS = ROOT / "data" / "retrieval_corpus_initial.jsonl"
CHAPTER_CONTEXTS = ROOT / "data" / "derived" / "chapter_contexts.jsonl"
OUTPUTS = {
    "candidate_ready": ROOT / "data" / "qa" / "2mark_pilot_candidates.jsonl",
    "pending_review": ROOT / "data" / "qa" / "2mark_pilot_pending.jsonl",
    "rejected": ROOT / "data" / "qa" / "2mark_pilot_rejected.jsonl",
    "summary": ROOT / "data" / "qa" / "2mark_pilot_summary.json",
}


# Every answer is copied from an exact textbook excerpt. The match text is
# searched in the selected corpus chunk; no outside facts are introduced.
PILOT_SPECS: tuple[dict[str, str | int], ...] = (
    {
        "chapter": "Rational Numbers", "subject": "Mathematics", "page": 25,
        "match": "When the number ‘0’ is added to any rational number, the rational number remains the same.",
        "question": "What happens when 0 is added to any rational number?",
    },
    {
        "chapter": "Rational Numbers", "subject": "Mathematics", "page": 26,
        "match": "We say that ‘1’ is the multiplicative identity for rational numbers",
        "question": "What is the multiplicative identity for rational numbers?",
    },
    {
        "chapter": "Rational Numbers", "subject": "Mathematics", "page": 27,
        "match": "Any two numbers whose product is ‘1’ are called the multiplicative inverses of each other.",
        "question": "What are multiplicative inverses?",
    },
    {
        "chapter": "Oliver Asks for More", "subject": "English", "page": 27,
        "match": "Oliver was frightened at the sight of so many gentlemen, which made him tremble.",
        "question": "Why did Oliver tremble in the white-washed room?",
    },
    {
        "chapter": "Oliver Asks for More", "subject": "English", "page": 28,
        "match": "The boys polished them with their spoons till they shone again.",
        "question": "How did the boys polish their basins?",
    },
    {
        "chapter": "Oliver Asks for More", "subject": "English", "page": 31,
        "match": "The word ‘red-faced’ is called a Compound Adjective.",
        "question": "What kind of adjective is ‘red-faced’?",
    },
    {
        "chapter": "Force", "subject": "Physical Sciences", "page": 28,
        "match": "Force is a push or a pull.",
        "question": "What is force?",
    },
    {
        "chapter": "Force", "subject": "Physical Sciences", "page": 28,
        "match": "Friction is the force that opposes relative motion of surfaces in contact.",
        "question": "What is friction?",
    },
    {
        "chapter": "Force", "subject": "Physical Sciences", "page": 28,
        "match": "The force exerted by a charged body on other charged body is known as electrostatic force.",
        "question": "What is electrostatic force?",
    },
    {
        "chapter": "Synthetic Fibres and Plastics", "subject": "Physical Sciences", "page": 45,
        "match": "Each small unit in the chain is known as monomer units.",
        "question": "What is a monomer?",
    },
    {
        "chapter": "Synthetic Fibres and Plastics", "subject": "Physical Sciences", "page": 45,
        "match": "Many small, identical units monomers combine to form a large unit called polymer.",
        "question": "What is a polymer?",
    },
    {
        "chapter": "Synthetic Fibres and Plastics", "subject": "Physical Sciences", "page": 46,
        "match": "Nylon is a polymer made of chemical units called polyamides.",
        "question": "What is nylon made of?",
    },
    {
        "chapter": "Cell – The Basic Unit of Life", "subject": "Biology", "page": 37,
        "match": "In the early days, there used to be just a single lens in the microscope. This is known as the simple microscope.",
        "question": "What is a simple microscope?",
    },
    {
        "chapter": "Cell – The Basic Unit of Life", "subject": "Biology", "page": 38,
        "match": "The study material to be viewed under a compound microscope is mounted on a slide.",
        "question": "Where is study material mounted for viewing under a compound microscope?",
    },
    {
        "chapter": "Cell – The Basic Unit of Life", "subject": "Biology", "page": 38,
        "match": "Microscopic slide is prepared on a 2mm thick, 3cm X 8cm rectangular strip of clear and clean glass piece called slide.",
        "question": "What is a microscopic slide prepared on?",
    },
    {
        "chapter": "Reproduction in Animals", "subject": "Biology", "page": 72,
        "match": "When the embryo develops fully and all other parts are distinct, it is called a foetus.",
        "question": "What is a foetus?",
    },
    {
        "chapter": "Reproduction in Animals", "subject": "Biology", "page": 72,
        "match": "The period from which zygote fully develops into foetus is called “Pregnancy period\".",
        "question": "What is the pregnancy period?",
    },
    {
        "chapter": "Reproduction in Animals", "subject": "Biology", "page": 72,
        "match": "Then the fusion of sperm and ovum takes place, which is called “Fertilization”.",
        "question": "What is fertilization?",
    },
    {
        "chapter": "The Polar Regions", "subject": "Social Studies", "page": 50,
        "match": "The region which lies near the poles is called the “polar region”.",
        "question": "What is the polar region?",
    },
    {
        "chapter": "The Polar Regions", "subject": "Social Studies", "page": 50,
        "match": "This is known as the ‘Arctic Circle’.",
        "question": "What is the boundary of the polar region called?",
    },
    {
        "chapter": "The Polar Regions", "subject": "Social Studies", "page": 50,
        "match": "a unique type of vegetation known as the ‘Tundra Vegetation’.",
        "question": "What is Tundra Vegetation?",
    },
)


def _candidate_id(source_id: str, question: str) -> str:
    return hashlib.sha256(f"{source_id}|{question}".encode("utf-8")).hexdigest()[:16]


def _question_key(subject: str, question: str) -> tuple[str, str]:
    return subject.casefold(), normalize_text(question).casefold()


def _chapter_context_by_source(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        for source_id in row.get("source_ids", []):
            result.setdefault(str(source_id), row)
    return result


def _find_chunk(spec: dict[str, str | int], chunks: list[Any]) -> tuple[Any | None, str]:
    subject = str(spec["subject"])
    page = int(spec["page"])
    expected = normalize_text(str(spec["match"]))
    matches = [
        chunk for chunk in chunks
        if chunk.subject == subject and int(chunk.page) == page
        and expected.casefold() in normalize_text(chunk.text).casefold()
    ]
    if not matches:
        return None, "source_excerpt_not_found"
    if len(matches) > 1:
        return None, "source_excerpt_ambiguous"
    return matches[0], ""


def build_pilot_rows(
    approved_rows: list[dict[str, Any]],
    chapter_rows: list[dict[str, Any]],
    chunks: list[Any],
) -> tuple[list[dict[str, Any]], list[dict[str, str | int]]]:
    context_by_source = _chapter_context_by_source(chapter_rows)
    rows: list[dict[str, Any]] = []
    skipped: list[dict[str, str | int]] = []
    for spec in PILOT_SPECS:
        chunk, reason = _find_chunk(spec, chunks)
        if chunk is None:
            skipped.append({"chapter": spec["chapter"], "subject": spec["subject"], "page": spec["page"], "reason": reason})
            continue
        chapter_context = context_by_source.get(chunk.source_id)
        if chapter_context is None:
            skipped.append({"chapter": spec["chapter"], "subject": spec["subject"], "page": spec["page"], "reason": "chapter_context_not_found"})
            continue

        answer = str(spec["match"])
        candidate = QACandidate(
            subject=chunk.subject,
            grade=8,
            marks=2,
            question=str(spec["question"]),
            answer=answer,
            context=str(chapter_context.get("text") or chunk.text),
            source_pages=[chunk.page],
            source_ids=[chunk.source_id],
            supporting_quotes=[answer],
            chapter=str(spec["chapter"]),
            generation_method="deterministic_2mark_pilot",
            candidate_id=_candidate_id(chunk.source_id, str(spec["question"])),
            fixture=False,
        )
        rows.append(candidate.to_dict())
    return rows, skipped


def classify_rows(rows: list[dict[str, Any]], approved_rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    approved_keys = {
        _question_key(str(row.get("subject") or ""), str(row.get("question") or ""))
        for row in approved_rows
    }
    seen = set(approved_keys)
    output = {"candidate_ready": [], "pending_review": [], "rejected": []}
    for row in rows:
        candidate = QACandidate(**{key: row[key] for key in QACandidate.__dataclass_fields__})
        key = _question_key(candidate.subject, candidate.question)
        if key in seen:
            result = ValidationResult(candidate.candidate_id, "rejected", ["duplicate_question"], {})
        else:
            seen.add(key)
            result = validate_candidate(candidate)
        enriched = copy.deepcopy(row)
        enriched["pilot_status"] = {
            "accepted": "candidate_ready",
            "pending": "pending_review",
            "rejected": "rejected",
        }[result.status]
        enriched["validation"] = result.to_dict()
        output[enriched["pilot_status"]].append(enriched)
    return output


def main() -> None:
    for path in OUTPUTS.values():
        if path.exists():
            raise FileExistsError(f"Refusing to overwrite existing output: {path}")

    approved_rows = read_jsonl(APPROVED)
    chapter_rows = read_jsonl(CHAPTER_CONTEXTS)
    chunks = load_chunks(CORPUS)
    raw_rows, skipped = build_pilot_rows(approved_rows, chapter_rows, chunks)
    classified = classify_rows(raw_rows, approved_rows)

    for status in ("candidate_ready", "pending_review", "rejected"):
        write_jsonl(OUTPUTS[status], classified[status])

    chapter_counts = Counter(str(row["chapter"]) for row in raw_rows)
    status_by_chapter: dict[str, dict[str, int]] = {}
    for status, status_rows in classified.items():
        for row in status_rows:
            status_by_chapter.setdefault(str(row["chapter"]), Counter())[status] += 1
    report = {
        "status": "pilot_only",
        "generation_method": "deterministic_2mark_pilot",
        "candidate_count": len(raw_rows),
        "candidate_count_by_chapter": dict(chapter_counts),
        "status_counts": {key: len(value) for key, value in classified.items()},
        "status_counts_by_chapter": status_by_chapter,
        "skipped_specs": skipped,
        "mapped_chapters": sorted(chapter_counts),
        "existing_approved_records_used_for_duplicate_detection": len(approved_rows),
        "human_approved_automatically": False,
        "source_files": [str(CORPUS.relative_to(ROOT)), str(CHAPTER_CONTEXTS.relative_to(ROOT))],
    }
    OUTPUTS["summary"].write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
