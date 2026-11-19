"""Build derived chapter/context artifacts without changing the source corpus."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from training.chapter_contexts import build_chapter_contexts
from training.corpus import load_chunks, write_jsonl


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", default="data/retrieval_corpus_initial.jsonl")
    parser.add_argument("--output-dir", default="data/derived")
    args = parser.parse_args()
    chunks = load_chunks(args.corpus)
    contexts = build_chapter_contexts(chunks)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(output_dir / "chapter_contexts.jsonl", (context.to_dict() for context in contexts))
    chapter_map = [
        {
            "chapter_id": context.chapter_id,
            "subject": context.subject,
            "title": context.title,
            "status": context.status,
            "source_pages": context.source_pages,
            "source_ids": context.source_ids,
        }
        for context in contexts
    ]
    (output_dir / "chapter_map.json").write_text(json.dumps(chapter_map, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "provenance_manifest.json").write_text(
        json.dumps({"source": str(Path(args.corpus)), "chunks": len(chunks), "contexts": len(contexts)}, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({"chunks": len(chunks), "contexts": len(contexts), "output_dir": str(output_dir)}))


if __name__ == "__main__":
    main()
