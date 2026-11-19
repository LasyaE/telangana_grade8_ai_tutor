"""Read-only textbook corpus utilities with stable source identifiers."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable

from .schemas import TextbookChunk


def normalize_text(value: str) -> str:
    """Collapse whitespace for comparisons without changing stored source text."""

    return re.sub(r"\s+", " ", str(value)).strip()


def source_id(subject: str, page: str | int, text: str) -> str:
    payload = f"{subject}|{page}|{normalize_text(text)}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    file_path = Path(path)
    rows: list[dict[str, Any]] = []
    with file_path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number} of {file_path}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"Expected an object on line {line_number} of {file_path}")
            rows.append(value)
    return rows


def load_chunks(path: str | Path) -> list[TextbookChunk]:
    chunks: list[TextbookChunk] = []
    for row in read_jsonl(path):
        text = str(row.get("text") or row.get("content") or "").strip()
        subject = str(row.get("subject") or "").strip()
        page = row.get("page", "")
        if not subject or not text:
            continue
        chunks.append(
            TextbookChunk(
                subject=subject,
                page=page,
                text=text,
                source_file=str(row.get("source_file") or ""),
                chunk_index=row.get("chunk_index"),
                source_id=source_id(subject, page, text),
                metadata=dict(row.get("metadata") or {}),
            )
        )
    return chunks


def write_jsonl(path: str | Path, rows: Iterable[dict[str, Any]]) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
