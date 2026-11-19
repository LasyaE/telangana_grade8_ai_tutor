"""Deterministic validation and report generation for QA candidates."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from .corpus import normalize_text
from .schemas import QACandidate, ValidationResult


TOKEN = re.compile(r"[a-z0-9]+", re.I)


def _tokens(text: str) -> set[str]:
    return set(TOKEN.findall(normalize_text(text).lower()))


def candidate_from_dict(row: dict[str, Any]) -> QACandidate:
    return QACandidate(
        candidate_id=str(row.get("candidate_id") or ""),
        subject=str(row.get("subject") or ""),
        grade=int(row.get("grade") or 0),
        marks=int(row.get("marks") or 0),
        question=str(row.get("question") or ""),
        answer=str(row.get("answer") or ""),
        context=str(row.get("context") or ""),
        source_pages=list(row.get("source_pages") or []),
        source_ids=list(row.get("source_ids") or []),
        supporting_quotes=list(row.get("supporting_quotes") or []),
        chapter=str(row.get("chapter") or ""),
        generation_method=str(row.get("generation_method") or ""),
        fixture=bool(row.get("fixture", False)),
    )


def validate_candidate(candidate: QACandidate) -> ValidationResult:
    reasons: list[str] = []
    checks: dict[str, Any] = {}
    if not candidate.subject:
        reasons.append("missing_subject")
    if candidate.grade != 8:
        reasons.append("unsupported_grade")
    if candidate.marks not in {2, 4, 8}:
        reasons.append("unsupported_mark_value")
    if not candidate.question.strip():
        reasons.append("missing_question")
    if not candidate.answer.strip():
        reasons.append("missing_answer")
    if not candidate.context.strip():
        reasons.append("missing_context")
    if not candidate.source_pages or not candidate.source_ids:
        reasons.append("missing_source_traceability")

    normalized_context = normalize_text(candidate.context).lower()
    quote_matches = [
        normalize_text(quote).lower() in normalized_context
        for quote in candidate.supporting_quotes
        if normalize_text(quote)
    ]
    checks["supporting_quote_exact"] = bool(quote_matches) and all(quote_matches)
    if not checks["supporting_quote_exact"]:
        reasons.append("supporting_quote_not_found")

    unsupported = sorted(_tokens(candidate.answer) - _tokens(candidate.context))
    checks["unsupported_answer_tokens"] = unsupported
    if unsupported:
        reasons.append("answer_contains_tokens_not_in_context")

    word_count = len(candidate.answer.split())
    checks["answer_word_count"] = word_count
    limits = {2: (1, 60), 4: (15, 140), 8: (30, 280)}
    minimum, maximum = limits.get(candidate.marks, (1, 0))
    if word_count < minimum:
        reasons.append("answer_too_short_for_mark_level")
    if maximum and word_count > maximum:
        reasons.append("answer_too_long_for_mark_level")

    status = "accepted" if not reasons else "rejected"
    if reasons == ["supporting_quote_not_found"]:
        status = "pending"
    return ValidationResult(candidate.candidate_id, status, reasons, checks)


def validate_candidates(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    accepted: list[dict[str, Any]] = []
    pending: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    rejection_reasons: Counter[str] = Counter()
    pending_reasons: Counter[str] = Counter()
    for row in rows:
        candidate = candidate_from_dict(row)
        key = (candidate.subject.lower(), normalize_text(candidate.question).lower())
        if key in seen:
            result = ValidationResult(candidate.candidate_id, "rejected", ["duplicate_question"], {})
        else:
            seen.add(key)
            result = validate_candidate(candidate)
        enriched = {**candidate.to_dict(), "validation": result.to_dict()}
        for reason in result.reasons:
            if result.status == "pending":
                pending_reasons[reason] += 1
            else:
                rejection_reasons[reason] += 1
        if result.status == "accepted":
            accepted.append(enriched)
        elif result.status == "pending":
            pending.append(enriched)
        else:
            rejected.append(enriched)

    report = {
        "candidates_generated": len(rows),
        "accepted": len(accepted),
        "rejected": len(rejected),
        "pending": len(pending),
        "rejection_reasons": dict(rejection_reasons),
        "pending_reasons": dict(pending_reasons),
        "status": "pilot_only",
    }
    return accepted + pending + rejected, report
