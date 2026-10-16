"""Tests for the duplicate guard (job_dedupe_check.py).

Stdlib unittest only; the tracker, ledger and Vault archive are redirected to a temp dir.
"""

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SKILL_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_DIR / "scripts"))

import job_dedupe_check as dedupe  # noqa: E402

HEADER = "| # | Status | Company | Role | JD_URL |\n|---|---|---|---|---|\n"
LINKEDIN_HEADER = "| # | Status | Company | Role | Job ID | Link | Notes |\n|---|---|---|---|---|---|---|\n"
TRACKER_HEADER = "Date,Company,Role,JD_URL,Channel,Stage,Application_Submitted,Response_Status,Resume_Variant,Notes\n"
URL = "https://job-boards.greenhouse.io/acme/jobs/100"
OTHER_URL = "https://job-boards.greenhouse.io/acme/jobs/200"


def row(number: int, status: str, url: str, role: str = "Backend Engineer", company: str = "Acme") -> str:
    return f"| {number} | {status} | {company} | {role} | {url} |\n"


class DedupeCheck(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.archive = self.root / "applications"
        self.archive.mkdir()
        for name, value in (
            ("TRACKER", self.root / "tracker.csv"),
            ("LEDGER", self.root / "ledger.md"),
            ("ARCHIVE_DIR", self.archive),
        ):
            patcher = mock.patch.object(dedupe, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def batch(self, name: str, rows: list[str], header: str = HEADER) -> None:
        (self.archive / name).write_text("# batch\n\n" + header + "".join(rows), encoding="utf-8")

    def check(self, url: str = URL, role: str = "Backend Engineer", cap: int = 20) -> tuple[int, dict]:
        """Run main() and return (exit code, first JSON line); a retryable duplicate prints a second verdict line."""
        argv = ["job_dedupe_check.py", "--company", "Acme", "--role", role, "--url", url, "--company-cap", str(cap)]
        out = io.StringIO()
        with mock.patch.object(sys, "argv", argv), contextlib.redirect_stdout(out):
            code = dedupe.main()
        return code, json.loads(out.getvalue().splitlines()[0])

    def test_submitted_archive_row_is_a_duplicate_even_with_tracking_params(self):
        for status in ("Submitted", "DuplicateSubmitted"):
            with self.subTest(status=status):
                self.batch("greenhouse-batch-2026-06-21.md", [row(1, status, URL)])
                code, result = self.check(url=URL + "?gh_src=abc")
                self.assertEqual(code, 20)
                self.assertEqual(result["code"], "duplicate-url")
                self.assertEqual(result["matches"][0]["source"], "archive")
                self.assertEqual(result["matches"][0]["date"], "2026-06-21")

    def test_linkedin_layout_matches_on_the_link_column(self):
        link = "https://www.linkedin.com/jobs/view/4422828560/"
        line = f"| 1 | Submitted | Acme | Backend Engineer \\| Remote | 4422828560 | {link} | Easy Apply |\n"
        self.batch("linkedin-batch-2026-06-07.md", [line], header=LINKEDIN_HEADER)
        code, result = self.check(url=link)
        self.assertEqual(code, 20)
        self.assertEqual(result["code"], "duplicate-url")
        self.assertEqual(result["matches"][0]["role"], "Backend Engineer | Remote")

    def test_other_statuses_prove_no_submission_and_stay_retryable(self):
        rows = [row(n, status, URL) for n, status in enumerate(("Blocked", "Skipped", "Candidate", "ManualFinish"), 1)]
        self.batch("greenhouse-batch-2026-06-21.md", rows)
        code, result = self.check()
        self.assertEqual(code, 0)
        self.assertTrue(result["ok"])
        self.assertEqual(result["same_company_submitted_matches"], [])

    def test_same_company_submissions_count_toward_the_cap(self):
        self.batch("greenhouse-batch-2026-06-21.md", [row(1, "Submitted", URL), row(2, "Submitted", OTHER_URL, role="SRE")])
        code, result = self.check(url="https://job-boards.greenhouse.io/acme/jobs/300", role="Data Engineer", cap=2)
        self.assertEqual(code, 20)
        self.assertEqual(result["code"], "company-cap-reached")
        self.assertEqual(result["submitted_count"], 2)

    def test_one_application_in_two_batch_files_counts_once(self):
        self.batch("greenhouse-batch-2026-06-20.md", [row(1, "Submitted", URL)])
        self.batch("greenhouse-batch-2026-06-21.md", [row(1, "Submitted", URL)])
        code, result = self.check(url=OTHER_URL, role="SRE", cap=2)
        self.assertEqual(code, 0)
        self.assertEqual(len(result["same_company_submitted_matches"]), 1)

    def test_tracker_and_archive_do_not_double_count(self):
        tracker = self.root / "tracker.csv"
        tracker.write_text(
            TRACKER_HEADER + f"2026-06-21,Acme,Backend Engineer,{URL},Greenhouse official,Submitted,Yes,Submitted,1P,\n",
            encoding="utf-8",
        )
        self.batch("greenhouse-batch-2026-06-21.md", [row(1, "Submitted", URL)])
        code, result = self.check(url=OTHER_URL, role="SRE", cap=2)
        self.assertEqual(code, 0)
        self.assertEqual(len(result["same_company_submitted_matches"]), 1)

    def test_same_role_at_the_same_company_is_a_duplicate_role(self):
        self.batch("greenhouse-batch-2026-06-21.md", [row(1, "Submitted", URL)])
        code, result = self.check(url=OTHER_URL, role="backend  engineer")
        self.assertEqual(code, 20)
        self.assertEqual(result["code"], "duplicate-role")

    def test_missing_archive_directory_is_a_no_op(self):
        with mock.patch.object(dedupe, "ARCHIVE_DIR", self.root / "does-not-exist"):
            code, result = self.check()
        self.assertEqual(code, 0)
        self.assertTrue(result["ok"])

    def test_phone_rejected_never_retries_but_form_not_loaded_does(self):
        ledger = self.root / "ledger.md"
        ledger.write_text(f"- 2026-10-16 10:00:00 CST | ManualFinish | Acme - Backend Engineer | {URL} | phone-rejected\n", encoding="utf-8")
        code, result = self.check()
        self.assertEqual((code, result["code"]), (20, "duplicate-url"))

        ledger.write_text(f"- 2026-10-16 10:00:00 CST | ManualFinish | Acme - Backend Engineer | {URL} | form-not-loaded\n", encoding="utf-8")
        code, result = self.check()
        self.assertEqual((code, result["code"]), (0, "retryable-non-submitted-duplicate"))

    def test_tracker_notes_decide_whether_a_manual_finish_row_retries(self):
        tracker = self.root / "tracker.csv"
        for note, expected in (
            ("manual-finish-needed:platform-anti-bot", (20, "duplicate-url")),
            ("manual-finish-needed:phone-rejected", (20, "duplicate-url")),
            ("manual-finish-needed:skip-email-verification", (0, "retryable-non-submitted-duplicate")),
        ):
            with self.subTest(note=note):
                tracker.write_text(
                    TRACKER_HEADER
                    + f"2026-10-16,Acme,Backend Engineer,{URL},Greenhouse official,ManualFinish,No,ManualFinish,1P,{note}\n",
                    encoding="utf-8",
                )
                code, result = self.check()
                self.assertEqual((code, result["code"]), expected)


if __name__ == "__main__":
    unittest.main()
