#!/usr/bin/env python3
import argparse
import csv
import json
import re
from pathlib import Path


TRACKER = Path.home() / "job-hunt" / "tracker.csv"
LEDGER = Path.home() / "job-hunt" / "application-ledger.md"
CANONICAL_BLOCKLIST = Path.home() / "job-hunt" / "data" / "blocked-companies.json"
SKILL_BLOCKLIST = Path(__file__).resolve().parent.parent / "data" / "blocked-companies.json"


def load_blocked_company_keys() -> set[str]:
    for path in (CANONICAL_BLOCKLIST, SKILL_BLOCKLIST):
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        keys = data.get("blocked_company_keys") or data.get("keys")
        if keys:
            return {str(k).casefold() for k in keys}
    raise FileNotFoundError(
        f"blocked-companies.json not found in {CANONICAL_BLOCKLIST} or {SKILL_BLOCKLIST}"
    )


BLOCKED_COMPANY_KEYS = load_blocked_company_keys()


def norm_url(value: str) -> str:
    value = (value or "").strip()
    value = re.sub(r"[?#].*$", "", value)
    value = value.rstrip("/")
    value = re.sub(r"/apply$", "", value)
    return value.lower()


def norm_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip()).lower()


def company_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").casefold())


def match_text(match: dict) -> str:
    return json.dumps(match, ensure_ascii=False)


def is_retryable_non_submitted_duplicate(matches: list[dict]) -> bool:
    """Allow retry only when prior same-URL records prove no submission happened.

    This exists for script-gap recovery: after we teach a runner a previously
    unsupported safe field, the same URL must be retryable. It must not weaken
    the duplicate guard for submitted rows or human/account-risk blockers.
    """
    if not matches:
        return False

    hard_stop = re.compile(
        r"\|\s*Submitted\s*\||"
        r'"submitted"\s*:\s*true|'
        r'"status"\s*:\s*"(Submitted|DuplicateSubmitted)"|'
        r"phone-required|platform-anti-bot|captcha|hcaptcha|turnstile|"
        r"possible spam|verify your application|wrong-window|stale-job",
        re.I,
    )
    retryable = re.compile(
        r"script-gap:(resume-input-not-found|greenhouse-invalid-required-fields|greenhouse-fill-timeout|fill-failed-returncode-1)|"
        r"unsupported-required-question:unsupported-required:|"
        r"manual-finish-needed:unsupported-required:|"
        r"manual-finish-needed:(fill-failed|pre-submit-check-failed|submit-unverified|submit-failed|invalid-required-fields|unhandled-required|greenhouse-fill-timeout)|form-not-loaded",
        re.I,
    )

    saw_retryable = False
    for match in matches:
        text = match_text(match)
        if match.get("submitted") is True:
            return False
        if match.get("status") in {"Submitted", "DuplicateSubmitted"}:
            return False
        if hard_stop.search(text):
            return False
        if retryable.search(text):
            saw_retryable = True
        if match.get("source") == "tracker" and match.get("status") == "ManualFinish" and not match.get("submitted"):
            saw_retryable = True
        if match.get("source") == "ledger" and re.search(r"\|\s*ManualFinish\s*\|", match.get("line", "")):
            saw_retryable = True
    return saw_retryable


def main() -> int:
    parser = argparse.ArgumentParser(description="Prevent duplicate job applications.")
    parser.add_argument("--company", required=True)
    parser.add_argument("--role", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--company-cap", type=int, default=20)
    args = parser.parse_args()

    target_url = norm_url(args.url)
    target_company = norm_text(args.company)
    target_company_key = company_key(args.company)
    target_role = norm_text(args.role)

    if target_company_key in load_blocked_company_keys():
        print(
            json.dumps(
                {
                    "ok": False,
                    "code": "company-blocked",
                    "company": args.company,
                    "role": args.role,
                    "url": args.url,
                    "reason": "hard-blocked-after-overapplication",
                },
                ensure_ascii=False,
            )
        )
        return 20

    exact_matches = []
    company_matches = []
    company_submitted_count = 0

    if TRACKER.exists():
        with TRACKER.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                row_url = norm_url(row.get("JD_URL", ""))
                row_company = norm_text(row.get("Company", ""))
                row_company_key = company_key(row.get("Company", ""))
                row_role = norm_text(row.get("Role", ""))
                submitted = row.get("Application_Submitted") == "Yes"
                status = row.get("Response_Status", "")
                if row_url and row_url == target_url:
                    exact_matches.append(
                        {
                            "source": "tracker",
                            "date": row.get("Date", ""),
                            "company": row.get("Company", ""),
                            "role": row.get("Role", ""),
                            "status": status,
                            "submitted": submitted,
                            "url": row.get("JD_URL", ""),
                        }
                    )
                if (
                    target_company_key
                    and row_company_key == target_company_key
                    and submitted
                    and status in {"Submitted", "DuplicateSubmitted"}
                ):
                    company_submitted_count += 1
                    company_matches.append(
                        {
                            "source": "tracker",
                            "date": row.get("Date", ""),
                            "company": row.get("Company", ""),
                            "role": row.get("Role", ""),
                            "status": status,
                            "url": row.get("JD_URL", ""),
                            "same_role": row_role == target_role,
                        }
                    )

    if LEDGER.exists():
        for line in LEDGER.read_text(encoding="utf-8").splitlines():
            if target_url and target_url in norm_url(line):
                exact_matches.append({"source": "ledger", "line": line[:500]})

    if exact_matches and is_retryable_non_submitted_duplicate(exact_matches):
        print(
            json.dumps(
                {
                    "ok": True,
                    "code": "retryable-non-submitted-duplicate",
                    "company": args.company,
                    "role": args.role,
                    "url": args.url,
                    "matches": exact_matches,
                },
                ensure_ascii=False,
            )
        )
    elif exact_matches:
        print(
            json.dumps(
                {
                    "ok": False,
                    "code": "duplicate-url",
                    "company": args.company,
                    "role": args.role,
                    "url": args.url,
                    "matches": exact_matches,
                },
                ensure_ascii=False,
            )
        )
        return 20

    if args.company_cap > 0 and company_submitted_count >= args.company_cap:
        print(
            json.dumps(
                {
                    "ok": False,
                    "code": "company-cap-reached",
                    "company": args.company,
                    "role": args.role,
                    "url": args.url,
                    "submitted_count": company_submitted_count,
                    "company_cap": args.company_cap,
                    "matches": company_matches[:10],
                },
                ensure_ascii=False,
            )
        )
        return 20

    same_role_matches = [match for match in company_matches if match.get("same_role")]
    if same_role_matches:
        print(
            json.dumps(
                {
                    "ok": False,
                    "code": "duplicate-role",
                    "company": args.company,
                    "role": args.role,
                    "url": args.url,
                    "matches": same_role_matches,
                },
                ensure_ascii=False,
            )
        )
        return 20

    print(
        json.dumps(
            {
                "ok": True,
                "company": args.company,
                "role": args.role,
                "url": args.url,
                "same_company_submitted_matches": company_matches[:10],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
