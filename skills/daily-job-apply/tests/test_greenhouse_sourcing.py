"""Tests for the Greenhouse sourcing question classifier.

Stdlib unittest only; the curl helpers are mocked, so nothing touches the network.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

SKILL_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_DIR / "scripts"))

import greenhouse_sourcing as sourcing  # noqa: E402

JOB_URL = "https://boards.greenhouse.io/acme/jobs/1"


def question(label: str, required: bool = True, field_type: str = "input_text") -> dict:
    return {"label": label, "required": required, "fields": [{"type": field_type}]}


def classify(questions: list[dict]) -> dict:
    job = {"board": "acme", "id": "1", "url": JOB_URL}
    with mock.patch.object(sourcing, "curl_json", return_value={"questions": questions}), mock.patch.object(
        sourcing, "curl_text", return_value=""
    ):
        return sourcing.classify_questions(job)


class ClassifyQuestions(unittest.TestCase):
    def test_required_phone_is_a_caution_not_a_blocker(self):
        job = classify([question("Phone")])
        self.assertEqual(job["status"], "auto_candidate")
        self.assertEqual(job["blockers"], "")
        self.assertEqual(job["cautions"].split(","), ["phone-required"])

    def test_optional_phone_has_no_caution(self):
        job = classify([question("Phone", required=False)])
        self.assertEqual(job["status"], "auto_candidate")
        self.assertEqual(job["cautions"], "")

    def test_required_cover_letter_still_blocks(self):
        job = classify([question("Cover Letter", field_type="textarea")])
        self.assertEqual(job["status"], "manual")
        self.assertIn("cover-letter-required", job["blockers"].split(","))

    def test_required_select_still_blocks_but_phone_does_not(self):
        job = classify([question("Phone"), question("Country", field_type="multi_value_single_select")])
        self.assertEqual(job["status"], "manual")
        self.assertEqual(job["blockers"].split(","), ["required-react-selects:1"])

    def test_questions_unavailable_is_a_source_error(self):
        job = {"board": "acme", "id": "1", "url": JOB_URL}
        with mock.patch.object(sourcing, "curl_json", return_value=None):
            result = sourcing.classify_questions(job)
        self.assertEqual(result["status"], "source_error")
        self.assertEqual(result["blockers"], "questions-unavailable")


class EmbedSkipImport(unittest.TestCase):
    def test_embed_skip_resolves_inside_the_skill(self):
        module_file = Path(sys.modules["greenhouse_embed_skip"].__file__).resolve()
        self.assertEqual(module_file.parent, SKILL_DIR / "adapters")


if __name__ == "__main__":
    unittest.main()
