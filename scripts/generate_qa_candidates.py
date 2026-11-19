"""Run the bounded, model-free QA generation pilot."""

from __future__ import annotations

import argparse
from pathlib import Path

from training.corpus import load_chunks, write_jsonl
from training.generate_qa import add_validation_fixtures, generate_definition_candidates


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", default="data/retrieval_corpus_initial.jsonl")
    parser.add_argument("--output", default="data/qa/candidates.jsonl")
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--include-validation-fixtures", action="store_true")
    args = parser.parse_args()
    candidates = generate_definition_candidates(load_chunks(args.corpus), limit=args.limit)
    if args.include_validation_fixtures:
        candidates = add_validation_fixtures(candidates)
    write_jsonl(args.output, (candidate.to_dict() for candidate in candidates))
    print(f"Generated {len(candidates)} deterministic pilot candidates at {Path(args.output)}")


if __name__ == "__main__":
    main()
