"""Conservative chapter/context derivation from the existing corpus."""

from __future__ import annotations

import re
from collections import defaultdict

from .schemas import ChapterContext, TextbookChunk


CHAPTER_MARKER = re.compile(r"(?:^|\n)\s*(?:chapter\s+\d+\.?\s*)?([A-Z][A-Za-z0-9][^\n]{2,100})\s*(?:\n|$)", re.I)


def _title_from_chunk(text: str) -> str | None:
    for line in text.splitlines():
        candidate = " ".join(line.split()).strip(" .:-")
        if not candidate or len(candidate) < 4 or len(candidate) > 100:
            continue
        if re.search(r"\bchapter\s+\d+\b", candidate, re.I):
            return re.sub(r"^.*?chapter\s+\d+\.?\s*", "", candidate, flags=re.I).strip(" .:-") or candidate
        if candidate.isupper() and not re.search(r"free distribution|government|index", candidate, re.I):
            return candidate.title()
    return None


def build_chapter_contexts(chunks: list[TextbookChunk]) -> list[ChapterContext]:
    """Group consecutive chunks without inventing chapter membership.

    When no chapter marker is found, the result is explicitly marked
    ``needs_review`` and uses a subject-level unmapped context title.
    """

    grouped: dict[str, list[TextbookChunk]] = defaultdict(list)
    for chunk in chunks:
        grouped[chunk.subject].append(chunk)

    contexts: list[ChapterContext] = []
    for subject, subject_chunks in grouped.items():
        current_title = "Unmapped context"
        current: list[TextbookChunk] = []
        context_number = 0

        def flush() -> None:
            nonlocal context_number, current
            if not current:
                return
            context_number += 1
            title = current_title
            status = "ready_for_review" if title != "Unmapped context" else "needs_review"
            chapter_id = f"{subject.lower().replace(' ', '_')}:context_{context_number}"
            contexts.append(
                ChapterContext(
                    chapter_id=chapter_id,
                    subject=subject,
                    title=title,
                    status=status,
                    source_pages=list(dict.fromkeys(chunk.page for chunk in current)),
                    source_ids=[chunk.source_id for chunk in current],
                    text="\n\n".join(chunk.text for chunk in current),
                )
            )
            current = []

        for chunk in subject_chunks:
            marker = _title_from_chunk(chunk.text)
            if marker and current and marker.lower() != current_title.lower():
                flush()
            if marker:
                current_title = marker
            current.append(chunk)
        flush()

    return contexts
