from __future__ import annotations

import unittest
from collections import Counter

from scripts.generate_2mark_pilot import PILOT_SPECS, classify_rows


class TwoMarkPilotTests(unittest.TestCase):
    def test_specs_cover_only_the_seven_mapped_chapters(self) -> None:
        chapters = Counter(str(spec["chapter"]) for spec in PILOT_SPECS)
        self.assertEqual(len(chapters), 7)
        self.assertTrue(all(2 <= count <= 5 for count in chapters.values()))

    def test_duplicate_against_approved_records_is_rejected(self) -> None:
        row = {
            "subject": "Mathematics",
            "grade": 8,
            "marks": 2,
            "question": "What is an existing question?",
            "answer": "This is a textbook answer.",
            "context": "This is a textbook answer.",
            "source_pages": [28],
            "source_ids": ["source-1"],
            "supporting_quotes": ["This is a textbook answer."],
            "chapter": "Rational Numbers",
            "generation_method": "deterministic_2mark_pilot",
            "candidate_id": "candidate-1",
            "fixture": False,
        }
        result = classify_rows([row], [{"subject": row["subject"], "question": row["question"]}])
        self.assertEqual(len(result["rejected"]), 1)
        self.assertEqual(result["rejected"][0]["validation"]["reasons"], ["duplicate_question"])

    def test_pending_and_rejected_are_separate(self) -> None:
        pending = {
            "subject": "Mathematics", "grade": 8, "marks": 2,
            "question": "What is a pending definition?", "answer": "A textbook answer.",
            "context": "A textbook answer.", "source_pages": [28], "source_ids": ["s1"],
            "supporting_quotes": [], "chapter": "Rational Numbers",
            "generation_method": "deterministic_2mark_pilot", "candidate_id": "pending-1", "fixture": False,
        }
        rejected = dict(pending)
        rejected.update({
            "question": "What is a rejected definition?",
            "answer": "A blue elephant answer.",
            "supporting_quotes": ["A blue elephant answer."],
            "candidate_id": "rejected-1",
        })
        result = classify_rows([pending, rejected], [])
        self.assertEqual(len(result["pending_review"]), 1)
        self.assertEqual(len(result["rejected"]), 1)
        self.assertEqual(result["pending_review"][0]["pilot_status"], "pending_review")
        self.assertEqual(result["rejected"][0]["pilot_status"], "rejected")


if __name__ == "__main__":
    unittest.main()
