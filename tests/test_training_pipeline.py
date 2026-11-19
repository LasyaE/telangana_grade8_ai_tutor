from __future__ import annotations

import unittest

from training.chapter_contexts import build_chapter_contexts
from training.generate_qa import add_validation_fixtures, generate_definition_candidates
from training.schemas import QACandidate, TextbookChunk
from training.validate_qa import validate_candidate, validate_candidates


class TrainingPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.chunk = TextbookChunk(
            subject="Physical Sciences",
            page=88,
            text="The maximum displacement of a vibrating body from its mean position is called amplitude.",
            source_file="Science.pdf",
            source_id="source-1",
        )

    def test_definition_pilot_preserves_source_traceability(self) -> None:
        candidates = generate_definition_candidates([self.chunk], limit=5)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].source_pages, [88])
        self.assertEqual(candidates[0].source_ids, ["source-1"])

    def test_definition_pilot_skips_boilerplate(self) -> None:
        boilerplate = TextbookChunk(
            subject="Mathematics", page=2,
            text="Illustrations are given in the textbook.", source_id="boilerplate",
        )
        self.assertEqual(generate_definition_candidates([boilerplate]), [])

    def test_supported_candidate_is_accepted(self) -> None:
        candidate = generate_definition_candidates([self.chunk])[0]
        result = validate_candidate(candidate)
        self.assertEqual(result.status, "accepted")
        self.assertEqual(result.reasons, [])

    def test_unsupported_answer_is_rejected(self) -> None:
        candidate = QACandidate(
            subject="Physical Sciences", grade=8, marks=2,
            question="What is amplitude?",
            answer="Amplitude is the maximum displacement of a blue elephant.",
            context=self.chunk.text, source_pages=[88], source_ids=["source-1"],
            supporting_quotes=[self.chunk.text], candidate_id="bad-1",
        )
        result = validate_candidate(candidate)
        self.assertEqual(result.status, "rejected")
        self.assertIn("answer_contains_tokens_not_in_context", result.reasons)

    def test_missing_quote_is_pending(self) -> None:
        candidate = add_validation_fixtures(generate_definition_candidates([self.chunk]))[1]
        result = validate_candidate(candidate)
        self.assertEqual(result.status, "pending")

    def test_duplicate_questions_are_rejected(self) -> None:
        rows = [generate_definition_candidates([self.chunk])[0].to_dict()] * 2
        enriched, report = validate_candidates(rows)
        self.assertEqual(report["accepted"], 1)
        self.assertEqual(report["rejected"], 1)
        self.assertIn("duplicate_question", enriched[1]["validation"]["reasons"])

    def test_unmapped_context_is_explicitly_flagged(self) -> None:
        contexts = build_chapter_contexts([self.chunk])
        self.assertEqual(len(contexts), 1)
        self.assertEqual(contexts[0].status, "needs_review")
        self.assertEqual(contexts[0].source_pages, [88])


if __name__ == "__main__":
    unittest.main()
