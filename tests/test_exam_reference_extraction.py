from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.extract_exam_reference_qa import run


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_FIELDS = {
    "id", "subject", "language", "chapter", "question", "answer",
    "source_file", "source_page", "question_number", "source_type",
    "extraction_status", "extraction_confidence", "review_notes",
}


class ExamReferenceExtractionTests(unittest.TestCase):
    def test_extraction_outputs_are_separate_and_provenanced(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            summary = run(ROOT / "data" / "exam_reference" / "source_pdfs", output_dir)
            self.assertGreater(summary["records"]["candidate"], 0)
            for filename in ("qa_candidates.jsonl", "qa_pending.jsonl", "qa_rejected.jsonl"):
                rows = [json.loads(line) for line in (output_dir / filename).read_text(encoding="utf-8").splitlines()]
                for row in rows:
                    self.assertEqual(set(row), EXPECTED_FIELDS)
                    self.assertIn(row["source_file"], {
                        "biology_sa1.pdf", "english_sa1.pdf", "hindi_sa1.pdf",
                        "mathematics_sa1_2016.pdf", "physical_science_sa1.pdf",
                        "social_studies_sa1.pdf", "telugu_sa1.pdf",
                    })
                    self.assertGreaterEqual(row["source_page"], 1)
                    self.assertNotEqual(row["extraction_status"], "human_approved")

    def test_image_only_mathematics_is_not_promoted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            run(ROOT / "data" / "exam_reference" / "source_pdfs", output_dir)
            candidates = (output_dir / "qa_candidates.jsonl").read_text(encoding="utf-8")
            self.assertNotIn("mathematics_sa1_2016.pdf", candidates)
            rejected = [json.loads(line) for line in (output_dir / "qa_rejected.jsonl").read_text(encoding="utf-8").splitlines()]
            math_rows = [row for row in rejected if row["source_file"] == "mathematics_sa1_2016.pdf"]
            self.assertEqual(len(math_rows), 6)
            self.assertTrue(all("image_only_page" in row["review_notes"] for row in math_rows))

    def test_no_duplicate_candidate_question_answer_keys(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            run(ROOT / "data" / "exam_reference" / "source_pdfs", output_dir)
            rows = [json.loads(line) for line in (output_dir / "qa_candidates.jsonl").read_text(encoding="utf-8").splitlines()]
            keys = {(row["question"].casefold(), row["answer"].casefold()) for row in rows}
            self.assertEqual(len(keys), len(rows))


if __name__ == "__main__":
    unittest.main()
