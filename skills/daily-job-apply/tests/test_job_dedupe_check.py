"""Tests for the duplicate guard (job_dedupe_check.py).

Stdlib unittest only; the tracker, ledger and Vault archive are redirected to a temp dir.
"""

from __future__ import annotations

import contextlib
import io
import json
import signal
import sys
import tempfile
import time
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
EMBED_URL = "https://job-boards.greenhouse.io/embed/job_app?for=acme&token=100"


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
            ("CANONICAL_BLOCKLIST", self.root / "blocked-companies.json"),
            ("SKILL_BLOCKLIST", self.root / "skill-blocked-companies.json"),
        ):
            patcher = mock.patch.object(dedupe, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        dedupe.SKILL_BLOCKLIST.write_text(json.dumps({"keys": ["blocked-example"]}))

    def batch(self, name: str, rows: list[str], header: str = HEADER) -> None:
        (self.archive / name).write_text("# batch\n\n" + header + "".join(rows), encoding="utf-8")

    def check(self, url: str = URL, role: str = "Backend Engineer", cap: int = 20,
              company: str = "Acme", extra: tuple[str, ...] = ()) -> tuple[int, dict]:
        """Every invocation must emit exactly one final verdict."""
        argv = ["job_dedupe_check.py", "--company", company, "--role", role,
                "--url", url, "--company-cap", str(cap), *extra]
        out = io.StringIO()
        with mock.patch.object(sys, "argv", argv), contextlib.redirect_stdout(out):
            code = dedupe.main()
        lines = out.getvalue().splitlines()
        self.assertEqual(len(lines), 1, out.getvalue())
        return code, json.loads(lines[0])

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

    def test_greenhouse_url_variants_identify_one_requisition(self):
        self.batch("greenhouse-batch-2026-06-21.md", [row(1, "Submitted", URL)])
        for url in (
            EMBED_URL,
            "https://app.greenhouse.io/embed/job_app?token=100&for=acme",
            "https://boards.greenhouse.io/acme/jobs/100/application?gh_src=test",
        ):
            with self.subTest(url=url):
                code, result = self.check(url=url, role="Different display title")
                self.assertEqual((code, result["code"]), (20, "duplicate-url"))

    def test_distinct_embed_tokens_are_not_duplicates(self):
        self.batch("greenhouse-batch-2026-06-21.md", [row(1, "Submitted", EMBED_URL)])
        code, result = self.check(url=EMBED_URL.replace("token=100", "token=200"), role="SRE")
        self.assertEqual(code, 0)
        self.assertTrue(result["ok"])

    def test_nontracking_query_parameters_preserve_identity(self):
        for base in ("https://news.ycombinator.com/item", "https://careers.example/job"):
            with self.subTest(base=base):
                self.batch("greenhouse-batch-2026-06-21.md", [row(1, "Submitted", base + "?id=100")])
                code, result = self.check(url=base + "?id=200", role="SRE")
                self.assertEqual(code, 0)
                self.assertTrue(result["ok"])

    def test_ashby_application_suffix_identifies_same_job(self):
        url = "https://jobs.ashbyhq.com/acme/01234567-89ab-cdef-0123-456789abcdef"
        self.batch("ashby-batch-2026-06-21.md", [row(1, "Submitted", url)])
        code, result = self.check(url=url + "/application", role="Different title")
        self.assertEqual((code, result["code"]), (20, "duplicate-url"))

    def test_lookalike_ats_host_is_not_a_job_id_match(self):
        self.batch("greenhouse-batch-2026-06-21.md", [row(1, "Submitted", URL)])
        code, result = self.check(url="https://greenhouse.io.example/acme/jobs/100", role="SRE")
        self.assertEqual(code, 0)
        self.assertTrue(result["ok"])

    def test_ledger_url_match_is_not_a_prefix_match(self):
        dedupe.LEDGER.write_text(
            f"- 2026-10-16 | Submitted | Acme - Backend Engineer | {URL}0 | verified\n"
        )
        code, result = self.check(role="SRE")
        self.assertEqual(code, 0)
        self.assertTrue(result["ok"])

    def test_ledger_embed_identity_matches_path_url(self):
        dedupe.LEDGER.write_text(
            f"- 2026-10-16 | Submitted | Acme - Backend Engineer | {EMBED_URL} | verified\n"
        )
        code, result = self.check()
        self.assertEqual((code, result["code"]), (20, "duplicate-url"))

    def test_outcome_statuses_count_even_if_submission_flag_drifted(self):
        for status in ("Ack", "Rejected"):
            with self.subTest(status=status):
                dedupe.TRACKER.write_text(
                    TRACKER_HEADER + f"2026-06-21,Acme,Backend Engineer,{URL},Greenhouse official,{status},No,{status},1P,\n"
                )
                code, result = self.check(url=OTHER_URL, role="SRE", cap=1)
                self.assertEqual((code, result["code"]), (20, "company-cap-reached"))

    def test_ledger_only_submissions_count_toward_cap(self):
        dedupe.LEDGER.write_text(
            f"- 2026-10-16 | Submitted | Acme - Backend Engineer | {URL} | verified\n"
        )
        code, result = self.check(url=OTHER_URL, role="SRE", cap=1)
        self.assertEqual((code, result["code"]), (20, "company-cap-reached"))

    def test_url_variants_across_sources_count_once(self):
        dedupe.TRACKER.write_text(
            TRACKER_HEADER + f"2026-06-21,Acme,Backend Engineer,{URL},Greenhouse official,Submitted,Yes,Submitted,1P,\n"
        )
        self.batch("greenhouse-batch-2026-06-21.md", [row(1, "Submitted", EMBED_URL)])
        code, result = self.check(url=OTHER_URL, role="SRE", cap=2)
        self.assertEqual(code, 0)
        self.assertEqual(len(result["same_company_submitted_matches"]), 1)

    def test_unverified_submit_is_not_automatically_retryable(self):
        dedupe.TRACKER.write_text(
            TRACKER_HEADER + f"2026-06-21,Acme,Backend Engineer,{URL},Greenhouse official,ManualFinish,No,ManualFinish,1P,submit-unverified\n"
        )
        code, result = self.check()
        self.assertEqual((code, result["code"]), (20, "duplicate-url"))

    def test_known_duplicate_does_not_wait_for_archive(self):
        dedupe.TRACKER.write_text(
            TRACKER_HEADER + f"2026-06-21,Acme,Backend Engineer,{URL},Greenhouse official,Submitted,Yes,Submitted,1P,\n"
        )
        with mock.patch.object(dedupe, "archive_submitted_rows", side_effect=OSError("unavailable")) as archive:
            code, result = self.check()
        self.assertEqual((code, result["code"]), (20, "duplicate-url"))
        archive.assert_not_called()

    def test_blocked_board_cannot_be_bypassed_with_company_display_name(self):
        dedupe.CANONICAL_BLOCKLIST.write_text(json.dumps({"keys": ["acme"]}))
        code, result = self.check(company="Acme Incorporated")
        self.assertEqual((code, result["code"]), (20, "company-blocked"))

    def test_nonempty_canonical_blocklist_takes_precedence(self):
        dedupe.CANONICAL_BLOCKLIST.write_text(json.dumps({"keys": ["different-company"]}))
        dedupe.SKILL_BLOCKLIST.write_text(json.dumps({"keys": ["acme"]}))
        code, result = self.check()
        self.assertEqual(code, 0)
        self.assertTrue(result["ok"])

    def test_bad_blocklist_fails_closed_without_falling_back(self):
        for payload in ("not-json", '{"keys":"acme"}', '{"keys":[42]}'):
            with self.subTest(payload=payload):
                dedupe.CANONICAL_BLOCKLIST.write_text(payload)
                code, result = self.check()
                self.assertNotEqual(code, 0)
                self.assertFalse(result["ok"])
                self.assertEqual(result["code"], "dedupe-check-error")

    def test_missing_lists_fail_closed(self):
        dedupe.SKILL_BLOCKLIST.unlink()
        code, result = self.check()
        self.assertNotEqual(code, 0)
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "dedupe-check-error")

    def test_archive_read_error_cannot_allow_a_new_role(self):
        with mock.patch.object(dedupe, "archive_submitted_rows", side_effect=OSError("unavailable")):
            code, result = self.check()
        self.assertNotEqual(code, 0)
        self.assertEqual(result["code"], "dedupe-check-error")
        self.assertFalse(result["ok"])

    def test_archive_path_is_a_file_fails_closed(self):
        self.archive.rmdir()
        self.archive.write_text("not a directory")
        code, result = self.check()
        self.assertEqual(code, 21)
        self.assertEqual(result["code"], "dedupe-check-error")

    def test_unreadable_canonical_list_does_not_use_skill_fallback(self):
        read_text = Path.read_text

        def read(path, *args, **kwargs):
            if path == dedupe.CANONICAL_BLOCKLIST:
                raise PermissionError("canonical list unreadable")
            return read_text(path, *args, **kwargs)

        with mock.patch.object(Path, "read_text", read):
            code, result = self.check()
        self.assertEqual(code, 21)
        self.assertFalse(result["ok"])

    def test_malformed_tracker_fails_closed(self):
        dedupe.TRACKER.write_text("wrong,headers\nnot,a tracker\n")
        code, result = self.check()
        self.assertEqual(code, 21)
        self.assertEqual(result["code"], "dedupe-check-error")

    def test_invalid_timeout_cannot_disable_the_deadline(self):
        for value in ("0", "-1", "nan", "inf"):
            with self.subTest(value=value), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    self.check(extra=("--timeout", value))
                self.assertEqual(error.exception.code, 2)

    def test_retryable_record_cannot_override_submission_in_archive(self):
        dedupe.TRACKER.write_text(
            TRACKER_HEADER + f"2026-06-21,Acme,Backend Engineer,{URL},Greenhouse official,ManualFinish,No,ManualFinish,1P,form-not-loaded\n"
        )
        self.batch("greenhouse-batch-2026-06-21.md", [row(1, "Submitted", EMBED_URL)])
        code, result = self.check()
        self.assertEqual((code, result["code"]), (20, "duplicate-url"))

    def test_retryable_record_cannot_override_company_cap(self):
        dedupe.TRACKER.write_text(
            TRACKER_HEADER + f"2026-06-21,Acme,Backend Engineer,{URL},Greenhouse official,ManualFinish,No,ManualFinish,1P,form-not-loaded\n"
        )
        self.batch("greenhouse-batch-2026-06-21.md", [row(1, "Submitted", OTHER_URL, role="SRE")])
        code, result = self.check(cap=1)
        self.assertEqual((code, result["code"]), (20, "company-cap-reached"))

    @unittest.skipUnless(hasattr(signal, "setitimer"), "POSIX deadline")
    def test_slow_archive_times_out_with_one_negative_verdict(self):
        with mock.patch.object(dedupe, "archive_submitted_rows", side_effect=lambda _: time.sleep(1)):
            start = time.monotonic()
            code, result = self.check(extra=("--timeout", "0.03"))
        self.assertLess(time.monotonic() - start, 0.8)
        self.assertNotEqual(code, 0)
        self.assertEqual(result["code"], "dedupe-check-timeout")
        self.assertFalse(result["ok"])
        self.assertEqual(signal.getitimer(signal.ITIMER_REAL), (0.0, 0.0))


if __name__ == "__main__":
    unittest.main()
