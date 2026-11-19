"""Create a human-review proposal from the existing accepted QA records.

This script is deliberately source-preserving: it reads the existing approved
records, keeps their full contexts, source IDs, pages and validation objects,
and writes a separate proposal file. It does not generate new questions.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path


APPROVED = Path("data/qa/approved.jsonl")
OUTPUT = Path("data/qa/proposed_reviewed.jsonl")

REJECTED_IDS = {
    "9e0c5f53a5bb0a0f",  # inversion
    "765ff29d8a3cef4f",  # Adam's apple
}

REVISIONS = {
    "c1fb0f9125ff4f35": {
        "question": "What is the distributive law over subtraction?",
        "answer": (
            "For rational numbers a, b and c, a(b − c) = ab − ac. "
            "This property is called the distributive law over subtraction."
        ),
        "supporting_quotes": [
            "a (b − c) = ab − ac",
            "This property is called the distributive law over subtraction.",
        ],
        "decision": "REVIEW",
        "notes": "Added the formula present in the same textbook passage.",
    },
    "fc5b6f5d00209ec1": {
        "question": "What are Yes/No questions?",
        "answer": "Such questions are called Yes/No questions.",
        "supporting_quotes": ["Such questions are called Yes / No questions."],
        "decision": "ACCEPT",
        "notes": "Corrected grammar and slash spacing only.",
    },
    "f20c5e8f69db1a2a": {
        "question": "What is pressure?",
        "answer": (
            "The force acting perpendicularly on a unit area of a surface "
            "is called pressure."
        ),
        "supporting_quotes": [
            "The force acting perpendecularly on a unit area of a surface is called pressure."
        ],
        "decision": "REVIEW",
        "notes": "Corrected the OCR spelling ‘perpendecularly’ to ‘perpendicularly’.",
    },
    "feba4ff86e0de854": {
        "question": "What is the period of a non-terminating recurring decimal?",
        "answer": (
            "The set of digits that repeats in a non-terminating recurring "
            "decimal is called the period."
        ),
        "supporting_quotes": [
            "The set of digits which repeats in non-terminating recurring decimal is called period."
        ],
        "decision": "ACCEPT",
        "notes": "Corrected grammar without changing the definition.",
    },
    "32e71f996bae1686": {
        "question": "What is focusing when using a microscope?",
        "answer": (
            "Focusing is moving the lens up and down until the image looks sharp."
        ),
        "supporting_quotes": [
            "You have to move lens up and down till image looks sharp, this is called focussing."
        ],
        "decision": "REVIEW",
        "notes": "Rewrote the microscope instruction as a standalone definition.",
    },
    "58379bd4523e65ba": {
        "question": "What is staining?",
        "answer": (
            "These colouring agents are known as stains, and the process is called staining."
        ),
        "supporting_quotes": [
            "These colouring agents are known as stains and the process is called staining."
        ],
        "decision": "ACCEPT",
        "notes": "Corrected punctuation only.",
    },
    "dc28ca697e3e871c": {
        "question": "What is gravitational force?",
        "answer": (
            "The attractive force between any two massive objects is called gravitational force."
        ),
        "supporting_quotes": [
            "The attractive force between any two massive objects is called gravitational force."
        ],
        "decision": "ACCEPT",
        "notes": "Textbook wording retained.",
    },
    "e5adc95b90b9e968": {
        "question": "What is rayon?",
        "answer": (
            "Rayon is a new fibre made by chemically processing cellulose from "
            "wood or bamboo pulp. The process produces silk-like threads."
        ),
        "supporting_quotes": [
            "The cellulose that was collected from wood or bamboo pulp, is treated with several chemicals.",
            "This gives us silk like threads.",
            "This new fibre is called rayon.",
        ],
        "decision": "REVIEW",
        "notes": "Added the textbook-supported source material and production description.",
    },
    "4beb9e1573137cd5": {
        "question": "What is the Tundra region?",
        "answer": (
            "The northern part of the continents within the polar region is "
            "known as the Tundra. The word Tundra means very cold."
        ),
        "supporting_quotes": [
            "The northern part of the continents within the polar region is known as the Tundra.",
            "Tundra means very cold.",
        ],
        "decision": "REVIEW",
        "notes": "Added the geographic definition omitted from the original answer.",
    },
    "659a42abd0a28dc2": {
        "question": "What are test tube babies?",
        "answer": (
            "Babies born after in vitro fertilization, in which fertilization occurs "
            "outside the body and the developing zygote is placed in the mother's "
            "uterus, are called test tube babies. The textbook notes that this term "
            "is misleading because babies do not grow in test tubes."
        ),
        "supporting_quotes": [
            "In case fertilization occurs, the zygote is allowed to develop for about a week and then it is placed in the mother’s uterus.",
            "Babies born through this technique are called test tube babies.",
            "This term is actually misleading because babies cannot grow in test tubes.",
        ],
        "decision": "REVIEW",
        "notes": "Added the IVF context and the textbook clarification about the misleading term.",
    },
}


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def main() -> None:
    rows = read_jsonl(APPROVED)
    if len(rows) != 12:
        raise ValueError(f"Expected 12 approved records, found {len(rows)}")

    proposals: list[dict] = []
    for original in rows:
        candidate_id = original["candidate_id"]
        if candidate_id in REJECTED_IDS:
            continue
        if candidate_id not in REVISIONS:
            raise ValueError(f"No human-review decision configured for {candidate_id}")

        proposal = copy.deepcopy(original)
        revision = REVISIONS[candidate_id]
        proposal["question"] = revision["question"]
        proposal["answer"] = revision["answer"]
        proposal["supporting_quotes"] = revision["supporting_quotes"]
        proposal["human_review"] = {
            "decision": revision["decision"],
            "notes": revision["notes"],
            "source_preserved": True,
        }
        proposals.append(proposal)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8") as handle:
        for proposal in proposals:
            handle.write(json.dumps(proposal, ensure_ascii=False) + "\n")
    print(f"Wrote {len(proposals)} proposed reviewed records to {OUTPUT}")


if __name__ == "__main__":
    main()
