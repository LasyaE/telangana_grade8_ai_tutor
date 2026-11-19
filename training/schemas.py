"""Small, serialisable records shared by the preparation pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class TextbookChunk:
    subject: str
    page: str | int
    text: str
    source_file: str = ""
    chunk_index: int | None = None
    source_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ChapterContext:
    chapter_id: str
    subject: str
    title: str
    status: str
    source_pages: list[str | int]
    source_ids: list[str]
    text: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class QACandidate:
    subject: str
    grade: int
    marks: int
    question: str
    answer: str
    context: str
    source_pages: list[str | int]
    source_ids: list[str]
    supporting_quotes: list[str]
    chapter: str = ""
    generation_method: str = "deterministic_pilot"
    candidate_id: str = ""
    fixture: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ValidationResult:
    candidate_id: str
    status: str
    reasons: list[str]
    checks: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
