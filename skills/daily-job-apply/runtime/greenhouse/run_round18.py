#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path

_RUNTIME = Path(__file__).resolve().parents[1]
if str(_RUNTIME) not in sys.path:
    sys.path.insert(0, str(_RUNTIME))
from paths import (  # noqa: E402
    ADAPTERS_DIR,
    DATA_DIR,
    JOB_HUNT,
    JOB_HUNT_DATA,
    NODE_MODULES,
    NODE_PATH,
    SCRIPTS_DIR,
    SKILL_DATA,
    SKILL_ROOT,
    WORK_DIR,
    TRACKER_CSV,
    PDF_DIR,
    resume_pdf,
)

_GH_DIR = Path(__file__).resolve().parent
if str(_GH_DIR) not in sys.path:
    sys.path.insert(0, str(_GH_DIR))
sys.path.insert(0, str(ADAPTERS_DIR))
sys.path.insert(0, str(SCRIPTS_DIR))
if NODE_PATH:
    os.environ.setdefault("NODE_PATH", NODE_PATH)

OMX = ADAPTERS_DIR

import argparse
import csv
import json
import os
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

JOB_HUNT = WORK_DIR
OMX = ADAPTERS_DIR
JOB_HUNT_DATA = JOB_HUNT / "data"
SKILL_DATA = Path.home() / ".codex" / "skills" / "daily-job-apply" / "data"



import run_round13 as r13
from greenhouse_embed_skip import EMBED_CAREER_SITE_DOMAINS, is_embed_career_site_url


def _resolve_data_file(job_hunt_name: str, skill_name: str) -> Path:
    job_hunt_path = JOB_HUNT_DATA / job_hunt_name
    if job_hunt_path.exists():
        return job_hunt_path
    return SKILL_DATA / skill_name


def load_board_list(filename: str, skill_name: str | None = None, key: str = "boards") -> list[str]:
    path = _resolve_data_file(filename, skill_name or filename)
    data = json.loads(path.read_text(encoding="utf-8"))
    values = data.get(key) or data.get("skip_boards") or data.get("boards") or data.get(key.replace("_", "-"))
    if values is None and key != "boards":
        values = data.get("boards")
    if values is None:
        values = data.get(key, data)
    return list(values)


def load_board_set(filename: str, skill_name: str | None = None, key: str = "boards") -> set[str]:
    return {b.casefold() for b in load_board_list(filename, skill_name, key)}

DATE = datetime.now().strftime("%Y%m%d")
LOG = JOB_HUNT / "greenhouse-round18.log"
POOL = JOB_HUNT / "candidate-pools"
BOARDS_OUT = POOL / f"greenhouse-round18-boards-{DATE}.txt"
SOURCED = POOL / f"greenhouse-round18-sourced-{DATE}.csv"
PHONE_OK = POOL / f"greenhouse-round18-phone-optional-{DATE}.csv"
READY = POOL / f"greenhouse-round18-ready-{DATE}.csv"
SUMMARY = JOB_HUNT / f"greenhouse-round18-summary-{DATE}.json"

MAX_ATTEMPTS = 5
MAX_READY_PER_BOARD = 2
JOB_TIMEOUT = 360

ROUND18_SKIP_BOARDS = load_board_set("greenhouse-skip-boards.json", "gh-skip-boards.json", "skip_boards")
ROUND18_PRIORITY_BOARDS = load_board_list("gh-priority-boards.json")

ZERO_HISTORY_PRIORITY = ROUND18_PRIORITY_BOARDS + [
    "mozilla",
    "coinbase",
    "startree",
    "billcom",
    "afresh",
    "bridgewater89",
    "instawork",
    "trace3",
    "wasabi",
    "wehrtyou",
    "geniussports",
    "qualtrics",
    "virtu",
    "radixuniversity",
    "relativity",
    "rfsmart",
    "sixthstreet",
    "sonyinteractiveentertainmentglobal",
    "tavily",
    "point72",
    "agency",
    "hellofresh",
    "dvtrading",
    "foliahealth",
    "mthreerecruitingportal",
    "xtxmarketstechnologies",
    "altruist",
    "futuresecureai",
    "hpiq",
    "ripple",
    "rockstargames",
    "aevexaerospace",
    "allencontrolsystems",
    "harnessinc",
    "pdtpartners",
]

EXPAND_SEED_SLUGS = list(
    dict.fromkeys(
        ROUND18_PRIORITY_BOARDS
        + [
            "mozilla",
            "coinbase",
            "together",
            "fireworksai",
            "groq",
            "deepgram",
            "elevenlabs",
            "langchain",
            "pinecone",
            "qdrant",
            "modal",
            "livekit",
            "browserbase",
            "harvey",
            "perplexityai",
            "cohere",
            "mistral",
        ]
    )
)

EXTRA_GH_QUERIES = (
    "boards.greenhouse.io hyphen connect engineer",
    "boards.greenhouse.io nexhealth software engineer",
    "boards.greenhouse.io ngrok engineer",
    "boards.greenhouse.io nebius AI engineer",
    "boards.greenhouse.io gradial engineer",
    "boards.greenhouse.io layer health engineer",
    "job-boards.greenhouse.io staff software remote us",
    "boards.greenhouse.io systems engineer AI startup",
    "job-boards.greenhouse.io platform engineer bay area",
)

r13.LOG = LOG
r13.BOARDS_OUT = BOARDS_OUT
r13.SOURCED = SOURCED
r13.PHONE_OK = PHONE_OK
r13.READY = READY
r13.ROUND13_SKIP_BOARDS = ROUND18_SKIP_BOARDS
r13.ROUND13_PRIORITY_BOARDS = ROUND18_PRIORITY_BOARDS
r13.ZERO_HISTORY_PRIORITY = ZERO_HISTORY_PRIORITY
r13.EXPAND_SEED_SLUGS = EXPAND_SEED_SLUGS
r13.GH_SEARCH_QUERIES = r13.GH_SEARCH_QUERIES + EXTRA_GH_QUERIES
r13.MAX_READY_PER_BOARD = MAX_READY_PER_BOARD


def log(msg: str) -> None:
    r13.log(msg)


def load_round18_excluded_urls() -> set[str]:
    """Exclude all submitted URLs (covers round16-17 submits)."""
    urls: set[str] = set()
    if not r13.TRACKER.exists():
        return urls
    for row in csv.DictReader(r13.TRACKER.open(newline="", encoding="utf-8")):
        if row.get("Application_Submitted") != "Yes":
            continue
        url = row.get("JD_URL") or ""
        if url:
            urls.add(r13.norm_url(url))
    return urls


r13.load_round13_excluded_urls = load_round18_excluded_urls


def precheck(max_ready: int = MAX_ATTEMPTS, known_urls: set[str] | None = None) -> dict:
    """Round18 precheck: skip embed career-site URLs before Playwright probe."""
    env = os.environ.copy()
    env["NODE_PATH"] = r13.NODE_PATH
    source_path = PHONE_OK if PHONE_OK.exists() else SOURCED
    rows = list(csv.DictReader(source_path.open(newline="", encoding="utf-8"))) if source_path.exists() else []
    tracker_counts = r13.board_tracker_counts()
    rows = r13.sort_rows_for_precheck(rows, tracker_counts)

    kept: list[dict] = []
    probed = 0
    skipped_dup = 0
    skipped_embed = 0
    blocker_counts: Counter[str] = Counter()
    sample_blockers: list[dict] = []
    known = known_urls or set()
    known |= load_round18_excluded_urls()
    board_ready_counts: dict[str, int] = {}

    for row in rows:
        if row.get("status") != "rendered_current":
            continue
        board = (row.get("board") or "").lower()
        if board in r13.EXTRA_EXCLUDED or board in ROUND18_SKIP_BOARDS:
            continue
        if not r13.us_candidate_row(row):
            continue
        url = row.get("url") or ""
        if url and r13.norm_url(url) in known:
            skipped_dup += 1
            blocker_counts["duplicate-url-tracker"] += 1
            continue
        if is_embed_career_site_url(url):
            skipped_embed += 1
            blocker_counts["embed-career-site-url"] += 1
            continue

        company = row.get("company") or ""
        role = row.get("role") or ""
        job_id = row.get("id") or ""
        location = row.get("location") or ""
        variant = row.get("variant") or "General SWE"
        if not all([company, role, board, job_id, url]):
            continue

        proc = subprocess.run(
            [
                "node",
                str(r13.APPLY),
                "--company",
                company,
                "--role",
                role,
                "--board",
                board,
                "--job-id",
                job_id,
                "--url",
                url,
                "--variant",
                variant,
                "--location",
                location,
                "--precheck-only",
                "--allow-manual-retry",
            ],
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
        )
        probed += 1
        try:
            payload = json.loads((proc.stdout or "").strip() or "{}")
        except json.JSONDecodeError:
            continue
        if payload.get("status") != "PrecheckReady":
            for blocker in payload.get("blockers") or [payload.get("code") or payload.get("status")]:
                blocker_counts[str(blocker)] += 1
            if len(sample_blockers) < 8:
                sample_blockers.append(
                    {
                        "company": company,
                        "role": role[:80],
                        "status": payload.get("status"),
                        "blockers": payload.get("blockers") or [payload.get("code")],
                    }
                )
            continue
        answers = payload.get("answersPreview") or payload.get("questions") or []
        required = [q.get("label", "") for q in answers if q.get("required")]
        if any("phone" in (r or "").lower() for r in required):
            blocker_counts["phone-required-playwright"] += 1
            continue

        sec = r13.security_precheck(company, role, board, job_id, url, variant, location)
        sec_code = sec.get("code") or ""
        if sec_code in ("needsSecurityCode", "skip-email-verification") or sec.get("status") != "SecurityPrecheckOk":
            blocker_counts[sec_code or "skip-email-verification"] += 1
            if len(sample_blockers) < 8:
                sample_blockers.append(
                    {
                        "company": company,
                        "role": role[:80],
                        "status": sec.get("status"),
                        "blockers": [sec_code or "skip-email-verification"],
                    }
                )
            continue

        if board_ready_counts.get(board, 0) >= MAX_READY_PER_BOARD:
            blocker_counts["board-ready-cap"] += 1
            continue

        kept.append(row)
        board_ready_counts[board] = board_ready_counts.get(board, 0) + 1
        if len(kept) >= max_ready:
            break

    if kept:
        with READY.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=kept[0].keys())
            writer.writeheader()
            writer.writerows(kept)
    elif READY.exists():
        READY.unlink()

    phone_opt_count = sum(
        1
        for r in rows
        if r.get("status") == "rendered_current"
        and (r.get("board") or "").lower() not in r13.EXTRA_EXCLUDED
        and (r.get("board") or "").lower() not in ROUND18_SKIP_BOARDS
        and r13.us_candidate_row(r)
        and not is_embed_career_site_url(r.get("url") or "")
    )
    return {
        "sourced": len(rows),
        "us_candidates": phone_opt_count,
        "probed": probed,
        "ready": len(kept),
        "skipped_duplicate_tracker": skipped_dup,
        "skipped_embed_career_site": skipped_embed,
        "out": str(READY),
        "blocker_top": blocker_counts.most_common(12),
        "sample_blockers": sample_blockers,
        "ready_boards": list({(r.get("board") or "").lower() for r in kept}),
        "board_ready_counts": board_ready_counts,
    }


def run_batch(max_attempts: int = MAX_ATTEMPTS) -> tuple[int, list[str]]:
    if not READY.exists():
        return 0, []
    env = os.environ.copy()
    env["NODE_PATH"] = r13.NODE_PATH
    before, _, _ = r13.tracker_stats()
    before_counts = r13.board_tracker_counts()
    today_count = r13.today_submitted_count()
    dynamic_cap = min(max_attempts, sum(1 for _ in csv.DictReader(READY.open(newline="", encoding="utf-8"))))
    target_submitted = today_count + dynamic_cap
    log(
        f"batch_cap today_count={today_count} dynamic_cap={dynamic_cap} "
        f"target_submitted={target_submitted} job_timeout={JOB_TIMEOUT} csv={READY}"
    )
    proc = subprocess.run(
        [
            "python3",
            str(r13.BATCH),
            "--csv",
            str(READY),
            "--max-attempts",
            str(dynamic_cap),
            "--target-submitted",
            str(target_submitted),
            "--count-date",
            datetime.now().strftime("%Y-%m-%d"),
            "--company-cap",
            "20",
            "--allow-manual-retry",
            "--job-timeout",
            str(JOB_TIMEOUT),
        ],
        capture_output=True,
        text=True,
        timeout=3600,
        env=env,
    )
    log(proc.stdout[-6000:] if proc.stdout else "")
    if proc.stderr:
        log(proc.stderr[-2000:])
    after, _, _ = r13.tracker_stats()
    after_counts = r13.board_tracker_counts()
    new_boards = [
        b for b, c in after_counts.items() if c > before_counts.get(b, 0) and before_counts.get(b, 0) == 0
    ]
    return max(0, after - before), new_boards


def ready_row_count() -> int:
    if not READY.exists():
        return 0
    return sum(1 for _ in csv.DictReader(READY.open(newline="", encoding="utf-8")))


def main() -> int:
    parser = argparse.ArgumentParser(description="Greenhouse Round 18 apply runner")
    parser.add_argument(
        "--batch-only",
        action="store_true",
        help="Skip discover/source/precheck; apply existing ready CSV (retry after network failure)",
    )
    args = parser.parse_args()

    os.chdir(JOB_HUNT)
    POOL.mkdir(parents=True, exist_ok=True)
    log(f"=== greenhouse round18 {datetime.now()} start batch_only={args.batch_only} ===")
    baseline_v, baseline_m, baseline_b = r13.tracker_stats()
    log(
        f"baseline_verified={baseline_v} manualfinish={baseline_m} blocked={baseline_b} "
        f"skip_boards={sorted(ROUND18_SKIP_BOARDS)} priority={ROUND18_PRIORITY_BOARDS} "
        f"embed_skip_domains={list(EMBED_CAREER_SITE_DOMAINS)} "
        f"max_ready_per_board={MAX_READY_PER_BOARD} max_attempts={MAX_ATTEMPTS}"
    )

    submitted_urls = load_round18_excluded_urls()
    known_urls = submitted_urls
    new_boards: list[str] = []
    board_meta: dict = {}
    phone_filter: dict = {"batch_only": args.batch_only}
    exclude_pool_count = 0

    if args.batch_only:
        ready_n = ready_row_count()
        log(f"batch_only ready_rows={ready_n} csv={READY}")
        if ready_n == 0:
            log('{"ready": 0, "note": "batch-only but ready CSV missing or empty"}')
            probe = {
                "sourced": 0,
                "us_candidates": 0,
                "probed": 0,
                "ready": 0,
                "skipped_duplicate_tracker": 0,
                "skipped_embed_career_site": 0,
                "blocker_top": [],
                "sample_blockers": [],
                "ready_boards": [],
                "board_ready_counts": {},
            }
        else:
            probe = {
                "sourced": ready_n,
                "us_candidates": ready_n,
                "probed": ready_n,
                "ready": min(ready_n, MAX_ATTEMPTS),
                "skipped_duplicate_tracker": 0,
                "skipped_embed_career_site": 0,
                "blocker_top": [],
                "sample_blockers": [],
                "ready_boards": list(
                    {
                        (row.get("board") or "").lower()
                        for row in csv.DictReader(READY.open(newline="", encoding="utf-8"))
                    }
                ),
                "board_ready_counts": {},
            }
            for row in csv.DictReader(READY.open(newline="", encoding="utf-8")):
                board = (row.get("board") or "").lower()
                probe["board_ready_counts"][board] = probe["board_ready_counts"].get(board, 0) + 1
                log(f"  ready {row.get('company')} {(row.get('role') or '')[:70]} id={row.get('id')}")
    else:
        exclude = r13.build_exclude_pool()
        exclude_pool_count = len(exclude)
        log(
            f"all_submitted_excluded_urls={len(submitted_urls)} prior_star_boards={sorted(r13.PRIOR_STAR_BOARDS)} "
            f"gh_search_queries={len(r13.GH_SEARCH_QUERIES)} expanded={len(EXTRA_GH_QUERIES)}"
        )

        new_boards, board_meta = r13.discover_boards(exclude, known_urls)
        r13.run_sourcing(new_boards)
        r13.merge_api_priority_sourcing(new_boards, known_urls)
        phone_filter = r13.filter_phone_optional_sourced()
        if phone_filter.get("phone_optional_kept", 0) < 12:
            log("pool_thin expanding")
            expand_boards, board_meta_expand = r13.discover_boards(
                exclude,
                known_urls,
                extra_candidates=set(EXPAND_SEED_SLUGS),
            )
            board_meta.update(board_meta_expand)
            only_new = [b for b in expand_boards if b not in new_boards]
            if only_new:
                expand_sourced = POOL / f"greenhouse-round18-sourced-expand-{DATE}.csv"
                r13.run_sourcing(only_new, out_path=expand_sourced)
                r13.merge_sourced_into_primary(expand_sourced)
                r13.merge_api_priority_sourcing(new_boards + only_new, known_urls)
                new_boards = list(dict.fromkeys(new_boards + only_new))
            phone_filter = r13.filter_phone_optional_sourced()
        log(f"phone_filter={json.dumps(phone_filter, ensure_ascii=False)}")

        probe = precheck(max_ready=MAX_ATTEMPTS, known_urls=known_urls)
        log(f"probe={json.dumps(probe, ensure_ascii=False)}")
        for row in csv.DictReader(READY.open(newline="", encoding="utf-8")) if READY.exists() else []:
            log(f"  ready {row.get('company')} {(row.get('role') or '')[:70]} id={row.get('id')}")

    submitted = 0
    new_submit_boards: list[str] = []
    if probe["ready"] > 0 and READY.exists():
        submitted, new_submit_boards = run_batch(MAX_ATTEMPTS)
    else:
        log('{"ready": 0, "note": "0 PrecheckReady jobs; batch skipped"}')

    final_v, final_m, final_b = r13.tracker_stats()
    log(f"final_verified={final_v} manualfinish={final_m} blocked={final_b}")

    phone_optional_boards = [
        {
            "slug": slug,
            "tracker_count": r13.board_tracker_counts().get(slug, 0),
            "fresh_phone_optional": board_meta.get(slug, {}).get("fresh_phone_optional"),
            "any_phone_optional": board_meta.get(slug, {}).get("any_phone_optional"),
        }
        for slug in new_boards
    ]
    summary = {
        "boards_discovered": new_boards,
        "boards_skipped": sorted(ROUND18_SKIP_BOARDS),
        "priority_boards": ROUND18_PRIORITY_BOARDS,
        "zero_history_priority": ZERO_HISTORY_PRIORITY,
        "prior_star_boards": sorted(r13.PRIOR_STAR_BOARDS),
        "embed_career_site_domains": list(EMBED_CAREER_SITE_DOMAINS),
        "all_submitted_excluded_urls": len(submitted_urls),
        "gh_search_queries": len(r13.GH_SEARCH_QUERIES),
        "max_ready_per_board": MAX_READY_PER_BOARD,
        "job_timeout": JOB_TIMEOUT,
        "phone_optional_boards": phone_optional_boards,
        "exclude_pool_count": exclude_pool_count,
        "phone_filter": phone_filter,
        "sourced": probe["sourced"],
        "us_candidates": probe["us_candidates"],
        "probed": probe["probed"],
        "ready": probe["ready"],
        "ready_boards": probe.get("ready_boards"),
        "board_ready_counts": probe.get("board_ready_counts"),
        "skipped_embed_career_site": probe.get("skipped_embed_career_site", 0),
        "submitted": submitted,
        "new_boards_with_submits": new_submit_boards,
        "blocker_top": probe["blocker_top"],
        "sample_blockers": probe.get("sample_blockers"),
        "baseline_verified": baseline_v,
        "final_verified": final_v,
        "verified_delta": final_v - baseline_v,
        "yield_ready": round(submitted / probe["ready"], 3) if probe["ready"] else 0.0,
        "yield_probed": round(submitted / probe["probed"], 3) if probe["probed"] else 0.0,
    }
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    log(f"SUMMARY_JSON={json.dumps(summary, ensure_ascii=False)}")
    log(f"=== greenhouse round18 {datetime.now()} done ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
