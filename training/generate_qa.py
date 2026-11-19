"""Small model-free QA generation pilot.

This intentionally generates only definition-style 2-mark candidates from
textbook sentences. It is a safe smoke test for provenance and validation,
not a substitute for a language-model generation run.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import replace

from .schemas import QACandidate, TextbookChunk


DEFINITION = re.compile(
    r"^\s*([A-Za-z][A-Za-z0-9()'’\-/ ]{2,80}?)\s+(means|refers to|is defined as|are defined as|is known as)\s+(.{8,220})[.!?]?\s*$",
    re.I,
)

CALLED_DEFINITION = re.compile(
    r"^\s*(.{8,180})\s+(?:is|are)\s+called\s+([A-Za-z][A-Za-z0-9()'’\-/ ]{2,60})[.!?]?\s*$",
    re.I,
)

BOILERPLATE = re.compile(
    r"copyright|prior permission|free distribution|given in the textbook|"
    r"curriculum frame|the syllabus|teaching job|mixed class room|"
    r"if you are facing|there is a scope|by any means|which it|copy right|"
    r"special features|chapters are|attempts are|theorem|exercises are|"
    r"entire syllabus|support is",
    re.I,
)

GENERIC_TERMS = {
    "approach", "any", "form", "if", "illustrations", "in", "it", "that",
    "there", "what", "which", "you",
}

BAD_TERM_WORDS = {"a", "at", "by", "for", "in", "of", "on", "or", "the", "to"}
BAD_ENDINGS = (" a", " an", " and", " as", " at", " by", " for", " in", " of", " on", " or", " the", " to")


def _candidate_id(question: str, source_id: str) -> str:
    return hashlib.sha256(f"{source_id}|{question}".encode()).hexdigest()[:16]


def _sentences(text: str) -> list[str]:
    values: list[str] = []
    for line in text.splitlines():
        line = " ".join(line.split()).strip()
        if not line:
            continue
        for sentence in re.split(r"(?<=[.!?])\s+", line):
            sentence = sentence.strip()
            if sentence:
                values.append(sentence)
    return values


def generate_definition_candidates(
    chunks: list[TextbookChunk],
    limit: int = 12,
) -> list[QACandidate]:
    candidates: list[QACandidate] = []
    seen: set[tuple[str, str]] = set()
    buckets: dict[str, list[TextbookChunk]] = {}
    for chunk in chunks:
        try:
            page_number = int(chunk.page)
        except (TypeError, ValueError):
            page_number = 999
        if page_number <= 12:
            continue
        buckets.setdefault(chunk.subject, []).append(chunk)

    subjects = sorted(buckets)
    positions = {subject: 0 for subject in subjects}
    while subjects and len(candidates) < limit:
        progressed = False
        for subject in list(subjects):
            bucket = buckets[subject]
            if positions[subject] >= len(bucket):
                subjects.remove(subject)
                continue
            chunk = bucket[positions[subject]]
            positions[subject] += 1
            progressed = True
            for sentence in _sentences(chunk.text):
                if sentence[-1:] not in ".?!":
                    continue
                if not sentence[:1].isupper():
                    continue
                called_match = CALLED_DEFINITION.match(sentence)
                match = DEFINITION.match(sentence)
                if called_match:
                    term = called_match.group(2).strip(" .:-")
                elif match:
                    term = match.group(1).strip(" .:-")
                else:
                    continue
                term = re.sub(r"^the\s+term\s+", "", term, flags=re.I)
                term = re.sub(r"^the\s+", "", term, flags=re.I)
                if len(term.split()) > 12:
                    continue
                term_words = set(re.findall(r"[a-z]+", term.lower()))
                if (
                    term.lower() in GENERIC_TERMS
                    or term_words & BAD_TERM_WORDS
                    or term.lower().endswith(BAD_ENDINGS)
                    or BOILERPLATE.search(sentence)
                    or sentence.lower().rstrip(".?!").endswith(BAD_ENDINGS)
                ):
                    continue
                question = f"What is {term.lower()}?"
                key = (chunk.subject, question.lower())
                if key in seen:
                    continue
                seen.add(key)
                candidates.append(
                    QACandidate(
                        candidate_id=_candidate_id(question, chunk.source_id),
                        subject=chunk.subject,
                        grade=8,
                        marks=2,
                        question=question,
                        answer=sentence,
                        context=chunk.text,
                        source_pages=[chunk.page],
                        source_ids=[chunk.source_id],
                        supporting_quotes=[sentence],
                    )
                )
                break
            if len(candidates) >= limit:
                return candidates
        if not progressed:
            break
    return candidates


def add_validation_fixtures(candidates: list[QACandidate]) -> list[QACandidate]:
    """Add clearly labelled negative controls for the pilot validator only."""

    if not candidates:
        return candidates
    seed = candidates[0]
    term = seed.question.removeprefix("What is ").rstrip("?")
    return candidates + [
        replace(
            seed,
            candidate_id=f"{seed.candidate_id}-pending",
            question=f"How is {term} defined?",
            supporting_quotes=[],
            generation_method="pilot_pending_fixture",
            fixture=True,
        ),
        replace(
            seed,
            candidate_id=f"{seed.candidate_id}-rejected",
            question=f"What unsupported claim is associated with {term}?",
            answer=f"{seed.answer} This statement is about an unsupported blue elephant.",
            generation_method="pilot_rejected_fixture",
            fixture=True,
        ),
    ]
