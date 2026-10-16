"""Tests for the LinkedIn external-apply harvest's chrome-use layer.

chrome-use is mocked (subprocess.run or the page helpers), so no browser or network is needed.
Stdlib unittest only.
"""

from __future__ import annotations

import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SKILL_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_DIR / "scripts"))

import linkedin_external_harvest as harvest  # noqa: E402

JOB_PAGE = "https://www.linkedin.com/jobs/view/1/"
SAFETY_URL = "https://www.linkedin.com/safety/go/?url=https%3A%2F%2Fjob-boards.greenhouse.io%2Facme%2Fjobs%2F1"


def envelope(data=None, *, success=True, error=None) -> str:
    return json.dumps({"success": success, "data": data, "error": error, "code": None if success else "command_failed"})


def completed(stdout="", stderr="", returncode=0) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=["chrome-use"], returncode=returncode, stdout=stdout, stderr=stderr)


class NoSleep(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(harvest.time, "sleep")
        patcher.start()
        self.addCleanup(patcher.stop)


class ChromeUseCommand(unittest.TestCase):
    def test_command_pins_session_and_profile_and_returns_data(self):
        with mock.patch.object(harvest.subprocess, "run", return_value=completed(envelope({"result": "ok"}))) as run:
            data = harvest._chrome_use(["eval", "1+1"])
        self.assertEqual(data, {"result": "ok"})
        cmd = run.call_args.args[0]
        pinned = ["--session", harvest.CHROME_USE_SESSION, "--browser", harvest.CHROME_USE_BROWSER, "--json", "eval"]
        self.assertEqual(cmd[1:7], pinned)
        self.assertEqual(cmd[-1], "1+1")

    def test_notice_lines_around_the_envelope_are_ignored(self):
        notice = "chrome-use 1.5.219 is available (you have 1.5.186). Upgrade: chrome-use upgrade\n"
        with mock.patch.object(harvest.subprocess, "run", return_value=completed(notice + envelope({"x": 1}) + "\n")):
            self.assertEqual(harvest._chrome_use(["tab", "list"]), {"x": 1})

    def test_failed_envelope_raises_with_the_chrome_use_error(self):
        failed = completed(envelope(None, success=False, error="Evaluation error: boom"), returncode=1)
        with mock.patch.object(harvest.subprocess, "run", return_value=failed):
            with self.assertRaisesRegex(harvest.ChromeUseError, "boom"):
                harvest._chrome_use(["eval", "x"])

    def test_missing_envelope_raises_with_stderr(self):
        with mock.patch.object(harvest.subprocess, "run", return_value=completed("", "daemon unreachable", 1)):
            with self.assertRaisesRegex(harvest.ChromeUseError, "no JSON envelope: daemon unreachable"):
                harvest._chrome_use(["eval", "x"])

    def test_missing_binary_and_timeout_raise_chrome_use_error(self):
        for exc, pattern in (
            (FileNotFoundError(), "not found"),
            (subprocess.TimeoutExpired(cmd="chrome-use", timeout=5), "timed out"),
        ):
            with self.subTest(pattern):
                with mock.patch.object(harvest.subprocess, "run", side_effect=exc):
                    with self.assertRaisesRegex(harvest.ChromeUseError, pattern):
                        harvest._chrome_use(["open", JOB_PAGE])


class PageHelpers(NoSleep):
    def test_page_json_decodes_a_json_string_and_rejects_anything_else(self):
        with mock.patch.object(harvest, "_chrome_use", return_value={"result": '{"a": 1}'}):
            self.assertEqual(harvest.page_json("js"), {"a": 1})
        with mock.patch.object(harvest, "_chrome_use", return_value={"result": "scrolled"}):
            with self.assertRaisesRegex(harvest.ChromeUseError, "did not return JSON"):
                harvest.page_json("js")

    def test_navigate_opens_the_page_before_evaluating(self):
        with mock.patch.object(harvest, "_chrome_use", return_value={"result": "{}"}) as chrome_use:
            harvest.page_json("js", navigate=JOB_PAGE)
        self.assertEqual([call.args[0][0] for call in chrome_use.call_args_list], ["open", "eval"])

    def test_pages_that_are_not_a_signed_in_linkedin_are_rejected(self):
        for href in (
            "",
            "chrome-error://chromewebdata/",
            "https://www.linkedin.cn/error",
            "https://notlinkedin.com/jobs",
            "https://www.linkedin.com/authwall?trk=x",
            "https://www.linkedin.com/login",
            "https://www.linkedin.com/uas/login",
            "https://www.linkedin.com/checkpoint/challenge/abc",
        ):
            with self.subTest(href):
                with self.assertRaises(harvest.ChromeUseError):
                    harvest.require_linkedin_page(href)
        harvest.require_linkedin_page("https://www.linkedin.com/jobs/search/?keywords=x")


class ScrapeAndDetail(NoSleep):
    @staticmethod
    def scrape(payload):
        with mock.patch.object(harvest, "page_eval"), mock.patch.object(harvest, "page_json", return_value=payload):
            return harvest.scrape_search("AI+Agent")

    def test_scrape_returns_the_cards_of_a_linkedin_search_page(self):
        jobs = [{"linkedinUrl": JOB_PAGE, "hasEasyApply": False}]
        self.assertEqual(self.scrape({"href": "https://www.linkedin.com/jobs/search/?keywords=x", "jobs": jobs}), jobs)

    def test_an_empty_card_list_on_a_linkedin_page_is_not_an_error(self):
        self.assertEqual(self.scrape({"href": "https://www.linkedin.com/jobs/search/", "jobs": []}), [])

    def test_scrape_fails_loudly_instead_of_returning_no_cards(self):
        cases = (
            ("redirected", {"href": "https://www.linkedin.cn/error", "jobs": []}),
            ("sign-in wall", {"href": "https://www.linkedin.com/authwall", "jobs": []}),
            ("bare string", "oops"),
            ("missing jobs", {"href": "https://www.linkedin.com/jobs/"}),
            ("no payload", None),
        )
        for label, payload in cases:
            with self.subTest(label):
                with self.assertRaises(harvest.ChromeUseError):
                    self.scrape(payload)

    def test_apply_button_rendering_late_gets_a_second_look(self):
        early = {"href": JOB_PAGE, "applyHref": "", "easyApply": False}
        late = {**early, "applyHref": SAFETY_URL}
        with mock.patch.object(harvest, "page_json", side_effect=[early, late]) as page_json:
            detail = harvest.extract_apply_url(JOB_PAGE)
        self.assertEqual(page_json.call_count, 2)
        self.assertEqual(detail["externalUrl"], "https://job-boards.greenhouse.io/acme/jobs/1")
        self.assertEqual(detail["linkedinUrl"], JOB_PAGE)

    def test_easy_apply_pages_are_read_once(self):
        page = {"href": JOB_PAGE, "applyHref": "", "easyApply": True}
        with mock.patch.object(harvest, "page_json", side_effect=[page]) as page_json:
            detail = harvest.extract_apply_url(JOB_PAGE)
        self.assertEqual(page_json.call_count, 1)
        self.assertTrue(detail["easyApply"])

    def test_detail_page_that_bounces_to_sign_in_or_returns_junk_raises(self):
        bounced = {"href": "https://www.linkedin.com/authwall", "applyHref": "", "easyApply": False}
        for label, payloads in (("sign-in", [bounced, bounced]), ("junk", ["oops"])):
            with self.subTest(label):
                with mock.patch.object(harvest, "page_json", side_effect=payloads):
                    with self.assertRaises(harvest.ChromeUseError):
                        harvest.extract_apply_url(JOB_PAGE)


def card(number: int, easy: bool = False) -> dict:
    return {"linkedinUrl": f"https://www.linkedin.com/jobs/view/{number}/", "company": "Acme", "hasEasyApply": easy}


def detail_for(number: int) -> dict:
    return {"company": "Acme", "easyApply": False, "externalUrl": f"https://job-boards.greenhouse.io/acme/jobs/{1000 + number}"}


class Main(NoSleep):
    def setUp(self):
        super().setUp()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.out = Path(tmp.name) / "harvest.csv"
        patcher = mock.patch.object(harvest, "close_session")
        self.close_session = patcher.start()
        self.addCleanup(patcher.stop)

    def run_main(self, *, cards=None, search_error=None, details=None):
        scrape = mock.patch.object(harvest, "scrape_search", return_value=cards or [], side_effect=search_error)
        extract = mock.patch.object(harvest, "extract_apply_url", side_effect=details)
        argv = ["linkedin_external_harvest.py", "--source-limit", "5", "--out", str(self.out)]
        stdout, stderr = io.StringIO(), io.StringIO()
        with scrape, extract as extract_mock, mock.patch.object(sys, "argv", argv):
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = harvest.main()
        return code, stdout.getvalue(), stderr.getvalue(), extract_mock

    def test_successful_run_writes_the_csv_and_closes_the_session(self):
        code, stdout, _, _ = self.run_main(cards=[card(1), card(2, easy=True)], details=[detail_for(1)])
        self.assertEqual(code, 0)
        summary = json.loads(stdout)
        self.assertEqual((summary["sourced"], summary["routable"], summary["detail_errors"]), (1, 1, 0))
        self.assertIn("job-boards.greenhouse.io/acme/jobs/1001", self.out.read_text(encoding="utf-8"))
        self.close_session.assert_called_once()

    def test_no_job_cards_anywhere_is_an_error_not_an_empty_success(self):
        code, stdout, stderr, _ = self.run_main(cards=[])
        self.assertEqual(code, 3)
        self.assertEqual(stdout, "")
        self.assertIn("no job cards", stderr)
        self.assertFalse(self.out.exists())
        self.close_session.assert_called_once()

    def test_chrome_use_failure_aborts_with_exit_2(self):
        code, _, stderr, _ = self.run_main(search_error=harvest.ChromeUseError("LinkedIn is asking for sign-in"))
        self.assertEqual(code, 2)
        self.assertIn("harvest aborted: LinkedIn is asking for sign-in", stderr)
        self.assertFalse(self.out.exists())
        self.close_session.assert_called_once()

    def test_one_bad_job_page_is_skipped_but_counted(self):
        details = [harvest.ChromeUseError("timed out"), detail_for(2)]
        code, stdout, stderr, _ = self.run_main(cards=[card(1), card(2)], details=details)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout)["detail_errors"], 1)
        self.assertIn("warning: skipped", stderr)

    def test_repeated_job_page_failures_abort_the_run(self):
        failures = [harvest.ChromeUseError("timed out")] * 5
        code, _, stderr, extract = self.run_main(cards=[card(n) for n in range(1, 6)], details=failures)
        self.assertEqual(code, 2)
        self.assertEqual(extract.call_count, harvest.MAX_DETAIL_ERRORS)
        self.assertIn("harvest aborted", stderr)
        self.close_session.assert_called_once()


if __name__ == "__main__":
    unittest.main()
