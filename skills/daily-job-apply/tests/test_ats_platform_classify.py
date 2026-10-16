"""Tests for the ATS platform classifier, harvest rows and registry stats.

They run against the real data/ats-adapter-registry.json so a registry edit that
de-routes ashby/greenhouse/lever fails here. Stdlib unittest only; no network.
"""

from __future__ import annotations

import copy
import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SKILL_DIR = Path(__file__).resolve().parent.parent
REGISTRY_PATH = SKILL_DIR / "data" / "ats-adapter-registry.json"
sys.path.insert(0, str(SKILL_DIR / "scripts"))

import ats_platform_classify as classify  # noqa: E402
import ats_registry  # noqa: E402
import greenhouse_url_resolver  # noqa: E402
import linkedin_external_harvest as harvest  # noqa: E402

ASHBY_URL = "https://jobs.ashbyhq.com/acme/00000000-0000-0000-0000-000000000000/application"
LEVER_URL = "https://jobs.lever.co/acme/00000000-0000-0000-0000-000000000000"
GREENHOUSE_URL = "https://boards.greenhouse.io/acme/jobs/1234567"
GREENHOUSE_JOB_BOARDS_URL = "https://job-boards.greenhouse.io/acme/jobs/1234567"

# (label, url, platform_id, playbook, expected adapter_route)
PLAYBOOK_CASES = (
    ("greenhouse-boards", GREENHOUSE_URL, "greenhouse", "ATS-GREENHOUSE.md", "greenhouse:acme/1234567"),
    ("greenhouse-job-boards", GREENHOUSE_JOB_BOARDS_URL, "greenhouse", "ATS-GREENHOUSE.md", "greenhouse:acme/1234567"),
    ("ashby", ASHBY_URL, "ashby", "ATS-ASHBY.md", "playbook:ashby"),
    ("lever", LEVER_URL, "lever", "workflows/04-universal-web-apply.md", "playbook:lever"),
)
PLAYBOOK_PLATFORMS = ("ashby", "greenhouse", "lever")


class PlaybookPlatformRouting(unittest.TestCase):
    def test_urls_are_applyable_and_routable_without_adapter_script(self):
        for label, url, platform_id, playbook, _ in PLAYBOOK_CASES:
            with self.subTest(label):
                route = classify.classify_url(url)
                self.assertEqual(route["platform_id"], platform_id)
                self.assertEqual(route["status"], "playbook")
                self.assertTrue(route["apply_allowed"])
                self.assertIsNone(route["skip_reason"])
                self.assertIsNone(route["adapter_script"])
                self.assertEqual(route["playbook"], playbook)
                self.assertEqual(classify.harvest_status_from_route(route), "routable")

    def test_route_string_is_non_empty(self):
        for label, url, _, _, expected in PLAYBOOK_CASES:
            with self.subTest(label):
                adapter_route = classify.adapter_route_from_route(classify.classify_url(url))
                self.assertIsInstance(adapter_route, str)
                self.assertTrue(adapter_route)
                self.assertEqual(adapter_route, expected)

    def test_greenhouse_url_resolves_board_and_job(self):
        for url in (GREENHOUSE_URL, GREENHOUSE_JOB_BOARDS_URL):
            with self.subTest(url):
                route = classify.classify_url(url)
                self.assertEqual((route["board"], route["job_id"]), ("acme", "1234567"))
                self.assertEqual(route["resolved_url"], GREENHOUSE_JOB_BOARDS_URL)

    def test_subdomains_and_uppercase_hosts_still_match(self):
        cases = (
            ("https://eu.jobs.lever.co/acme/1", "lever"),
            ("https://JOBS.LEVER.CO:443/acme/1", "lever"),
            ("https://boards.eu.greenhouse.io/acme/jobs/1234567", "greenhouse"),
            ("https://jobs.ashbyhq.com?x=1", "ashby"),
            ("jobs.ashbyhq.com/acme", "ashby"),
        )
        for url, platform_id in cases:
            with self.subTest(url):
                self.assertEqual(classify.classify_url(url)["platform_id"], platform_id)

    def test_route_string_priority(self):
        build = classify.adapter_route_from_route
        greenhouse = {
            "platform_id": "greenhouse",
            "apply_allowed": True,
            "board": "acme",
            "job_id": "7",
            "playbook": "ATS-GREENHOUSE.md",
        }
        self.assertEqual(build(greenhouse), "greenhouse:acme/7")
        self.assertEqual(
            build({"platform_id": "ashby", "apply_allowed": True, "playbook": "ATS-ASHBY.md"}), "playbook:ashby"
        )
        self.assertEqual(build({"platform_id": "ashby", "apply_allowed": True, "playbook": None}), "ashby")
        self.assertEqual(
            build({"platform_id": "greenhouse", "apply_allowed": True, "adapter_script": "/opt/gh.cjs"}),
            "/opt/gh.cjs",
        )
        self.assertEqual(build({}), "custom")

    def test_demoted_route_falls_back_to_the_bare_platform(self):
        demoted = {
            "platform_id": "greenhouse",
            "apply_allowed": False,
            "board": "acme",
            "job_id": "7",
            "adapter_script": "/opt/gh.cjs",
            "playbook": "ATS-GREENHOUSE.md",
        }
        self.assertEqual(classify.adapter_route_from_route(demoted), "greenhouse")


class RealRegistry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.platforms = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))["platforms"]

    def test_playbook_platforms_use_chrome_use_and_existing_playbook_files(self):
        for platform_id in PLAYBOOK_PLATFORMS:
            with self.subTest(platform_id):
                entry = self.platforms[platform_id]
                self.assertEqual(entry["status"], "playbook")
                self.assertEqual(entry["adapter_type"], "chrome-use")
                self.assertIsNone(entry["adapter_script"])
                self.assertTrue((SKILL_DIR / entry["playbook"]).is_file())

    def test_legacy_batch_counts_are_not_reported_as_outcomes(self):
        for platform_id in PLAYBOOK_PLATFORMS:
            with self.subTest(platform_id):
                entry = self.platforms[platform_id]
                self.assertEqual(entry["attempts"], 0)
                self.assertEqual(entry["successes"], 0)
                self.assertIsNone(entry["success_rate"])
                self.assertIsInstance(entry["legacy_batch_attempts"], int)
                self.assertIn("Retired CDP/Playwright batch engine", entry["legacy_batch_note"])

    def test_no_stale_omx_paths(self):
        self.assertNotIn(".omx", REGISTRY_PATH.read_text(encoding="utf-8"))


class NotApplyable(unittest.TestCase):
    def assert_not_applyable(self, route, harvest_status):
        self.assertFalse(route["apply_allowed"])
        self.assertEqual(classify.harvest_status_from_route(route), harvest_status)

    def test_unsupported_direct_aggregators(self):
        cases = (
            ("https://jackandjill.ai/jobs/123", "jackandjill"),
            ("https://jobright.ai/jobs/info/abc", "jobright"),
            ("https://remotehunter.com/apply/xyz", "remotehunter"),
        )
        for url, platform_id in cases:
            with self.subTest(platform_id):
                route = classify.classify_url(url)
                self.assertEqual(route["platform_id"], platform_id)
                self.assertEqual(route["skip_reason"], f"unsupported-platform:{platform_id}")
                self.assert_not_applyable(route, "unsupported-direct")
                self.assertEqual(classify.adapter_route_from_route(route), platform_id)

    def test_every_unsupported_direct_registry_domain_is_skipped(self):
        platforms = ats_registry.load_registry(REGISTRY_PATH)["platforms"]
        checked = 0
        for platform_id, entry in platforms.items():
            if entry.get("status") != "unsupported-direct":
                continue
            for domain in entry["domain_patterns"]:
                checked += 1
                with self.subTest(domain):
                    route = classify.classify_url(f"https://{domain}/jobs/1")
                    self.assertEqual(route["platform_id"], platform_id)
                    self.assert_not_applyable(route, "unsupported-direct")
        self.assertGreater(checked, 0)

    def test_unknown_host(self):
        route = classify.classify_url("https://careers.example.org/jobs/42")
        self.assertEqual(route["platform_id"], "custom")
        self.assertEqual(route["skip_reason"], "unknown-platform")
        self.assert_not_applyable(route, "needs-parse")
        self.assertEqual(classify.adapter_route_from_route(route), "custom")

    def test_experimental_platform_still_needs_parse(self):
        route = classify.classify_url("https://apply.workable.com/acme/j/ABC123/")
        self.assertEqual(route["platform_id"], "workable")
        self.assert_not_applyable(route, "needs-parse")
        self.assertEqual(classify.adapter_route_from_route(route), "workable")

    def test_unresolved_greenhouse_url_is_demoted_despite_playbook(self):
        route = classify.classify_url("https://boards.greenhouse.io/acme")
        self.assertEqual(route["platform_id"], "greenhouse")
        self.assertEqual(route["status"], "playbook")
        self.assertEqual(route["skip_reason"], "unresolved-greenhouse-url")
        self.assert_not_applyable(route, "needs-parse")
        self.assertEqual(classify.adapter_route_from_route(route), "greenhouse")

    def test_lookalike_hosts_are_not_routed_to_a_platform(self):
        for url in (
            "https://clever.com/jobs/1",
            "https://jobs.lever.co.example.org/acme/1",
            "https://lever.co@example.org/acme/1",
            "https://notashbyhq.com/acme/1",
            "https://notgreenhouse.io/acme/jobs/1234567",
            "https://example.com/redirect?to=greenhouse.io/acme/jobs/1234567",
        ):
            with self.subTest(url):
                route = classify.classify_url(url)
                self.assertEqual(route["platform_id"], "custom")
                self.assert_not_applyable(route, "needs-parse")

    def test_unresolved_greenhouse_embed_stays_needs_parse(self):
        offline = mock.patch.object(greenhouse_url_resolver, "fetch_embed_html", side_effect=RuntimeError("offline"))
        with offline:
            route = classify.classify_url("https://app.greenhouse.io/embed/job_app?token=1234567")
        self.assertEqual(route["platform_id"], "greenhouse")
        self.assertTrue(route["skip_reason"].startswith("embed-fetch-failed"))
        self.assert_not_applyable(route, "needs-parse")


class SyntheticRegistry(unittest.TestCase):
    URL = "https://jobs.acme-ats.example/acme/42"

    def classify_entry(self, **fields):
        entry = {"platform_id": "acme", "domain_patterns": ["acme-ats.example"], **fields}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "registry.json"
            path.write_text(json.dumps({"version": 1, "platforms": {"acme": entry}}), encoding="utf-8")
            return classify.classify_url(self.URL, registry_path=path)

    def test_playbook_status_without_playbook_is_not_applyable(self):
        cases = (
            ("missing", {}),
            ("null", {"playbook": None}),
            ("empty", {"playbook": ""}),
            ("blank", {"playbook": "   "}),
        )
        for label, extra in cases:
            with self.subTest(label):
                route = self.classify_entry(status="playbook", **extra)
                self.assertEqual(route["platform_id"], "acme")
                self.assertFalse(route["apply_allowed"])
                self.assertEqual(classify.harvest_status_from_route(route), "needs-parse")
                self.assertEqual(classify.adapter_route_from_route(route), "acme")

    def test_production_status_without_adapter_script_is_not_applyable(self):
        cases = (
            ("missing", {}),
            ("null", {"adapter_script": None}),
            ("empty", {"adapter_script": ""}),
            ("blank", {"adapter_script": "  "}),
            ("playbook-is-no-substitute", {"playbook": "ATS-ACME.md"}),
        )
        for label, extra in cases:
            with self.subTest(label):
                route = self.classify_entry(status="production", **extra)
                self.assertFalse(route["apply_allowed"])
                self.assertEqual(classify.harvest_status_from_route(route), "needs-parse")

    def test_production_status_with_adapter_script_stays_applyable(self):
        route = self.classify_entry(status="production", adapter_script="/opt/adapters/acme.py")
        self.assertTrue(route["apply_allowed"])
        self.assertIsNone(route["playbook"])
        self.assertEqual(classify.harvest_status_from_route(route), "routable")
        self.assertEqual(classify.adapter_route_from_route(route), "/opt/adapters/acme.py")

    def test_playbook_status_with_playbook_is_applyable(self):
        route = self.classify_entry(status="playbook", playbook="ATS-ACME.md")
        self.assertTrue(route["apply_allowed"])
        self.assertIsNone(route["adapter_script"])
        self.assertEqual(classify.harvest_status_from_route(route), "routable")
        self.assertEqual(classify.adapter_route_from_route(route), "playbook:acme")

    def test_other_statuses_are_never_applyable(self):
        for status in (None, "experimental", "unsupported", "unsupported-direct", "bogus"):
            with self.subTest(status):
                route = self.classify_entry(
                    status=status, adapter_script="/opt/adapters/acme.py", playbook="ATS-ACME.md"
                )
                self.assertFalse(route["apply_allowed"])


class HarvestRows(unittest.TestCase):
    @staticmethod
    def row_for(url):
        return harvest.harvest_row({"company": "Acme"}, {"company": "Acme", "externalUrl": url})

    def test_playbook_platform_rows_are_kept_routable_and_written(self):
        rows = []
        for label, url, platform_id, _, expected_route in PLAYBOOK_CASES:
            with self.subTest(label):
                row = self.row_for(url)
                self.assertIsNotNone(row)
                self.assertEqual(row["platform"], platform_id)
                self.assertEqual(row["status"], "routable")
                self.assertEqual(row["adapter_route"], expected_route)
                rows.append(row)
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "harvest.csv"
            harvest.write_csv(rows, out_path)
            with out_path.open(newline="", encoding="utf-8") as handle:
                written = list(csv.DictReader(handle))
        self.assertEqual(len(written), len(PLAYBOOK_CASES))
        for row in written:
            self.assertTrue(row["adapter_route"])
            self.assertEqual(row["status"], "routable")

    def test_unsupported_direct_row_is_kept_but_not_routable(self):
        row = self.row_for("https://jobright.ai/jobs/info/abc")
        self.assertIsNotNone(row)
        self.assertEqual(row["platform"], "jobright")
        self.assertEqual(row["status"], "unsupported-direct")

    def test_unknown_host_row_needs_parse(self):
        row = self.row_for("https://careers.example.org/jobs/42")
        self.assertEqual(row["status"], "needs-parse")
        self.assertEqual(row["adapter_route"], "custom")


class UpdatePlatformStats(unittest.TestCase):
    def update(self, entry_fields, **kwargs):
        registry = {"version": 1, "platforms": {"acme": {"platform_id": "acme", **entry_fields}}}
        return ats_registry.update_platform_stats(registry, "acme", **kwargs)["platforms"]["acme"]

    def assert_stats(self, entry, attempts, successes, success_rate):
        self.assertEqual(
            (entry["attempts"], entry["successes"], entry["success_rate"]),
            (attempts, successes, success_rate),
        )

    def test_null_counters_count_as_zero(self):
        entry = self.update({"attempts": None, "successes": None, "success_rate": None}, success=True)
        self.assert_stats(entry, 1, 1, 1.0)

    def test_missing_counters_survive_a_failed_attempt(self):
        self.assert_stats(self.update({}, success=False), 1, 0, 0.0)

    def test_success_rate_is_null_when_there_are_no_attempts(self):
        entry = self.update({"attempts": None, "successes": None, "success_rate": 0.0}, blocker="phone-required")
        self.assert_stats(entry, 0, 0, None)
        self.assertEqual(entry["blockers_seen"], ["phone-required"])

    def test_malformed_counters_count_as_zero(self):
        entry = self.update({"attempts": "n/a", "successes": -3}, success=True)
        self.assert_stats(entry, 1, 1, 1.0)

    def test_success_rate_is_rounded_ratio(self):
        entry = self.update({"attempts": 2, "successes": 1}, success=False)
        self.assert_stats(entry, 3, 1, 0.333)

    def test_unknown_platform_gets_a_fresh_entry(self):
        registry = ats_registry.update_platform_stats({"version": 1, "platforms": {}}, "newplat", success=False)
        self.assert_stats(registry["platforms"]["newplat"], 1, 0, 0.0)

    def test_real_registry_playbook_platform_counts_from_zero(self):
        registry = ats_registry.load_registry(REGISTRY_PATH)
        before = copy.deepcopy(registry)
        entry = ats_registry.update_platform_stats(registry, "ashby", success=True)["platforms"]["ashby"]
        self.assert_stats(entry, 1, 1, 1.0)
        self.assertEqual(entry["legacy_batch_attempts"], before["platforms"]["ashby"]["legacy_batch_attempts"])
        self.assertEqual(registry, before)

    def test_success_rate_never_exceeds_one(self):
        entry = self.update({"attempts": 2, "successes": 5}, success=False)
        self.assert_stats(entry, 3, 5, 1.0)

    def test_last_attempt_moves_only_when_an_attempt_is_recorded(self):
        entry = self.update({"last_attempt": "2026-01-01"}, blocker="platform-anti-bot")
        self.assertEqual(entry["last_attempt"], "2026-01-01")
        entry = self.update({"last_attempt": "2026-01-01"}, success=False)
        self.assertNotEqual(entry["last_attempt"], "2026-01-01")


if __name__ == "__main__":
    unittest.main()
