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

import csv
import json
import os
import re
import subprocess
import base64
import sys
import urllib.parse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

JOB_HUNT = WORK_DIR
TRACKER = TRACKER_CSV
POOL = JOB_HUNT / "candidate-pools"
LOG = JOB_HUNT / "greenhouse-round13.log"
DATE = datetime.now().strftime("%Y%m%d")
BOARDS_OUT = POOL / f"greenhouse-round13-boards-{DATE}.txt"
SOURCED = POOL / f"greenhouse-round13-sourced-{DATE}.csv"
PHONE_OK = POOL / f"greenhouse-round13-phone-optional-{DATE}.csv"
READY = POOL / f"greenhouse-round13-ready-{DATE}.csv"
SUMMARY = JOB_HUNT / f"greenhouse-round13-summary-{DATE}.json"

OMX = ADAPTERS_DIR
SOURCING = OMX / "greenhouse_current_sourcing.cjs"
APPLY = OMX / "greenhouse_playwright_apply.cjs"
BATCH = OMX / "greenhouse_playwright_batch.py"
SOURCING_PY = SCRIPTS_DIR / 'greenhouse_sourcing.py'

from greenhouse_embed_skip import is_embed_career_site_url  # noqa: E402
NODE_PATH = os.environ.get('NODE_PATH', str(NODE_MODULES))

MAX_ATTEMPTS = 5
MAX_READY_PER_BOARD = 2

ROUND4_BOARDS = {
    "launchdarkly", "iterable", "discord", "honeycomb", "postman", "vercel",
    "clickhouse", "figma", "intercom", "checkr", "brex", "airtable", "robinhood",
    "gleanwork", "stackblitz", "yugabyte", "6sense", "axon", "qualia", "justworks",
    "twilio", "truework", "humaninterest", "tailscale", "zuora", "logicgate",
}
ROUND5_BOARDS = ["zocdoc", "tripactions", "pathai", "sumologic", "thoughtworks", "veriff"]
ROUND5_SKIP_ENTIRELY = {"veriff"}
EXTRA_EXCLUDED = {"tailscale", "zuora", "logicgate", "lilasciences"}

# Round7/13: skip boards with heavy duplicate-url or security-code failures.
ROUND13_SKIP_BOARDS = {"lilasciences", "defenseunicorns", "vardaspace", "newsbreak", "singlestore", "sambanovasystems"}

ROUND13_PRIORITY_BOARDS = [
    "mozilla", "coinbase", "startree", "telnyx54", "coupanginternal",
]

# Prior-star boards (round11/12): exclude submitted URLs, deprioritize in precheck.
PRIOR_STAR_BOARDS = {"zone5technologies", "labelbox", "wonderschool", "heygen", "appomni", "avepoint", "glossgenius"}

# Zero tracker history — round13: mozilla/coinbase/startree/telnyx/coupang first; wonderschool custom-Q blocked.
ZERO_HISTORY_PRIORITY = ROUND13_PRIORITY_BOARDS + [
    "radiantsecurity", "vectranetworks", "billcom", "afresh", "bridgewater89", "defcon",
    "goodfire", "haizelabs", "instawork", "trace3", "wasabi", "wehrtyou",
    "geniussports", "qualtrics", "virtu", "radixuniversity", "relativity", "rfsmart",
    "sixthstreet", "sonyinteractiveentertainmentglobal", "tavily", "point72", "agency",
    "hellofresh", "dvtrading", "foliahealth", "mthreerecruitingportal", "xtxmarketstechnologies",
    "wonderschool", "heygen",
]

EXPAND_SEED_SLUGS = [
    "mozilla", "coinbase", "startree", "telnyx54", "coupanginternal", "radiantsecurity",
    "vectranetworks", "billcom", "geniussports", "qualtrics", "virtu", "relativity", "tavily",
    "point72", "agency", "hellofresh", "cohere", "mistral", "together", "fireworksai",
    "groq", "deepgram", "elevenlabs", "langchain", "pinecone", "qdrant", "modal",
    "livekit", "browserbase", "harvey", "perplexityai",
]

GH_SEARCH_QUERIES = (
    "boards.greenhouse.io software engineer",
    "grnh.se engineer",
    "site:greenhouse.io embed job_app",
    "boards.greenhouse.io platform engineer remote",
    "boards.greenhouse.io AI infrastructure",
    "boards.greenhouse.io machine learning engineer",
    "boards.greenhouse.io backend remote united states",
    "job-boards.greenhouse.io software",
    "boards.greenhouse.io staff engineer remote",
    "boards.greenhouse.io site reliability engineer",
    "boards.greenhouse.io founding engineer",
    "job-boards.greenhouse.io infrastructure",
    "boards.greenhouse.io applied AI",
    "boards.greenhouse.io distributed systems",
    "boards.greenhouse.io data platform engineer",
    "boards.greenhouse.io developer tools",
    "boards.greenhouse.io full stack remote",
    "boards.greenhouse.io observability engineer",
    "boards.greenhouse.io llm engineer remote",
    "job-boards.greenhouse.io agent infrastructure",
)

SEED_SLUGS = """
ramp mercury rippling scale notion mongodb datadog snowflake stripe supabase temporal
render replicate retool sourcegraph warp writer cartesia cerebras deepgram elevenlabs
fireworksai groq harvey langchain perplexityai pinecone plaid reddit sentry anyscale
assemblyai calendly cloudflare cohere elastic gusto huggingface instacart mixpanel
modal livekit railway browserbase fal highnote openly nuro toast planetscale watershed
abnormalsecurity benchling dbtlabs fivetran hashicorp jellyfish klaviyo lucidchart
motive navan olo opendoor pagerduty pathai personio redis rubrik snyk spotify
squarespace stubhub sumologic tecton thebrowsercompany thoughtworks tinder tripactions
udemy upgrade veriff vimeo zapier zipline zocdoc
baseten character cursor deepinfra fixie generalistai hebbia imbue inflection
inworld jasper krea laminar lumalabs magic magicdev mistral modular nomic
openrouter phind pika poolside qdrant reka runpod sierra skild snorkel
sweep synopsys tavily together trellis unlearn valence voyage wandb xai
affinity ambient anduril appliedintuition arkenstone astranis axiom biofourmis
brex1 canopy carta celonis chime commure convoy databricks decagon descript
diamondfoundry doordash duolingo eightsleep embed fi figment flexport flywheel
formlabs front genesis ginkgo gopuff grammarly greenhouse guild guildeducation
headway hebbia helion hex hyper hyperlane imc imcfinancial inscribe
ironclad klarity klarityhealth labelbox lattice lemni lightmatter lob
loom lumafield lumos lyft mainstreet materialize medplum mem mercury
metabase modern treasury monzo mosaic narmi neko neon netlify newfront
notion1 nuance o1 openai opensea opensea1 opensea2 opensea3 opensea4
opentrons oscar palantir palantirtechnologies parallel paxos peerlogic
persona phoenix pipedrive plaid1 polychain prod perfect postscript
prefect prisma procore purestorage quora ramp1 reddit1 retool1 rippling1
robinhood1 rokt rubrik1 runai samsara1 scale scale1 segment sendbird
sentilink shieldai sigmacomputing sila singular snaplogic snowflake1
sofi sorare spacex splice spoton square square1 stackadapt statisfy
stitchfix stripe1 stripe2 stripe3 stripe4 stripe5 stripe6 stripe7
substack superhuman synchronicity tailscale1 talon tecton1 tenstorrent
thefarmersdog thumbtack titan titan1 titan2 titan3 titan4 titan5
toast1 toptal trade republic transfix tropic twilio1 uniswap upstart
valon veeva vercel1 vercel2 vercel3 vercel4 vercel5 vercel6 vercel7
verkada vicarious vimeo1 vimeo2 vimeo3 vimeo4 vimeo5 vimeo6 vimeo7
voyage1 wandb1 weave webflow wellth whiterabbit wing wisp wolt
workato workday workday1 workday2 workday3 workday4 workday5 workday6
workday7 workday8 workday9 workday10 workday11 workday12 workday13
workday14 workday15 workday16 workday17 workday18 workday19 workday20
ycombinator yelp yext zapier1 zepto zeta zipline1 zocdoc1 zoom zoom1
""".split()

PHONE_RE = re.compile(r"\bphone\b", re.I)
GH_URL_RE = re.compile(
    r"https?://(?:boards|job-boards)\.greenhouse\.io/([a-z0-9_-]+)",
    re.I,
)
TITLE_ALLOW = re.compile(
    r"\b(software engineer|backend|back end|platform|infrastructure|infra|"
    r"site reliability|sre|devops|full[- ]?stack|machine learning|ml engineer|"
    r"ai engineer|distributed systems|cloud engineer|developer productivity|"
    r"data platform|data engineer|systems engineer|security engineer)\b",
    re.I,
)
TITLE_BLOCK = re.compile(
    r"\b(manager|director|vp|head|product manager|designer|researcher|"
    r"solutions engineer|sales engineer|intern|internship|android|ios|hardware)\b",
    re.I,
)
US_RX = re.compile(
    r"remote\s*-?\s*(us|usa|u\.s\.|united states)|united states|usa\b|u\.s\.|"
    r"san francisco|bay area|california|new york|seattle|boston|austin|denver|"
    r"remote - us|remote \(united states\)|remote \(us\)|mountain view",
    re.I,
)
NON_US_RX = re.compile(
    r"\b(canada|india|bangalore|emea|apac|united kingdom|\buk\b|london|israel|"
    r"singapore|japan|australia|ireland|netherlands|germany|france|colombia|chile|"
    r"vietnam|spain|poland|brazil|mexico|latam|korea|estonia|greece)\b",
    re.I,
)


def log(msg: str) -> None:
    line = f"{msg}\n"
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(line)
    print(msg, flush=True)


def norm_url(value: str) -> str:
    value = (value or "").strip()
    value = re.sub(r"[?#].*$", "", value).rstrip("/")
    value = re.sub(r"/(?:application|confirmation|apply|thanks)$", "", value, flags=re.I)
    return value.replace("https://boards.greenhouse.io/", "https://job-boards.greenhouse.io/").lower()


def tracker_stats() -> tuple[int, int, int]:
    rows = list(csv.DictReader(TRACKER.open(newline="", encoding="utf-8")))
    verified = sum(1 for r in rows if (r.get("Application_Submitted") or "").strip() == "Yes")
    manual = sum(1 for r in rows if (r.get("Response_Status") or "").strip() == "ManualFinish")
    blocked = sum(1 for r in rows if (r.get("Response_Status") or "").strip() == "Blocked")
    return verified, manual, blocked


def today_submitted_count() -> int:
    count_date = datetime.now().strftime("%Y-%m-%d")
    return sum(
        1
        for row in csv.DictReader(TRACKER.open(newline="", encoding="utf-8"))
        if row.get("Application_Submitted") == "Yes"
        and (row.get("Date") or "").split()[0] == count_date
    )


def load_known_urls() -> set[str]:
    known: set[str] = set()
    if not TRACKER.exists():
        return known
    for row in csv.DictReader(TRACKER.open(newline="", encoding="utf-8")):
        if row.get("JD_URL"):
            known.add(norm_url(row["JD_URL"]))
    return known


def load_round13_excluded_urls() -> set[str]:
    """Exclude submitted URLs from prior-star boards and round12 submitted boards."""
    excluded_boards = {"datacamp", "newsbreak", "singlestore"} | PRIOR_STAR_BOARDS
    urls: set[str] = set()
    if not TRACKER.exists():
        return urls
    for row in csv.DictReader(TRACKER.open(newline="", encoding="utf-8")):
        if row.get("Application_Submitted") != "Yes":
            continue
        url = row.get("JD_URL") or ""
        match = GH_URL_RE.search(url)
        if match and match.group(1).lower() in excluded_boards:
            urls.add(norm_url(url))
    return urls


def board_tracker_counts() -> dict[str, int]:
    counts: dict[str, int] = {}
    if not TRACKER.exists():
        return counts
    for row in csv.DictReader(TRACKER.open(newline="", encoding="utf-8")):
        url = row.get("JD_URL") or ""
        match = GH_URL_RE.search(url)
        if match:
            board = match.group(1).lower()
            counts[board] = counts.get(board, 0) + 1
    return counts


def load_blocked_keys() -> set[str]:
    keys: set[str] = set()
    if not SOURCING_PY.exists():
        return keys
    text = SOURCING_PY.read_text(encoding="utf-8")
    block = re.search(r"BLOCKED_COMPANY_KEYS\s*=\s*\{([^}]+)\}", text, re.S)
    if block:
        keys |= {m.group(1).lower() for m in re.finditer(r'"([a-z0-9]+)"', block.group(1))}
    default = re.search(r'DEFAULT_BOARDS\s*=\s*"""(.*?)"""', text, re.S)
    if default:
        keys |= set(default.group(1).split())
    return keys


def load_classified_boards() -> set[str]:
    boards: set[str] = set()
    for path in POOL.glob("greenhouse-classified*.csv"):
        try:
            for row in csv.DictReader(path.open(newline="", encoding="utf-8")):
                board = (row.get("board") or "").strip().lower()
                if board and re.fullmatch(r"[a-z0-9][a-z0-9_-]{1,48}", board):
                    boards.add(board)
        except OSError:
            continue
    return boards


def build_exclude_pool() -> set[str]:
    exclude: set[str] = set(ROUND4_BOARDS)
    exclude |= load_blocked_keys()
    exclude |= {re.sub(r"[^a-z0-9]+", "", s) for s in exclude}
    exclude |= ROUND13_SKIP_BOARDS

    if TRACKER.exists():
        for row in csv.DictReader(TRACKER.open(newline="", encoding="utf-8")):
            url = row.get("JD_URL") or ""
            match = GH_URL_RE.search(url)
            if match:
                exclude.add(match.group(1).lower())
            company = re.sub(r"[^a-z0-9]+", "", (row.get("Company") or "").casefold())
            if company:
                exclude.add(company)

    for path in POOL.glob("greenhouse-classified-2026-06-03*.csv"):
        for row in csv.DictReader(path.open(newline="", encoding="utf-8")):
            board = (row.get("board") or "").strip().lower()
            if board:
                exclude.add(board)

    return exclude


def gh_search_slugs(query: str, fetch_content: bool = True) -> set[str]:
    slugs: set[str] = set()
    encoded = urllib.parse.quote(query, safe="")
    try:
        proc = subprocess.run(
            ["gh", "api", "-X", "GET", f"search/code?q={encoded}&per_page=30"],
            capture_output=True, text=True, timeout=90,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return slugs
    if proc.returncode != 0:
        log(f"gh search failed for {query!r}: {(proc.stderr or proc.stdout)[:200]}")
        return slugs
    try:
        payload = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return slugs

    for item in payload.get("items") or []:
        blob = json.dumps(item, ensure_ascii=False)
        for match in GH_URL_RE.finditer(blob):
            slugs.add(match.group(1).lower())
        if not fetch_content:
            continue
        repo = (item.get("repository") or {}).get("full_name") or ""
        path = item.get("path") or ""
        if not repo or not path:
            continue
        text = ""
        try:
            content_proc = subprocess.run(
                ["gh", "api", f"repos/{repo}/contents/{urllib.parse.quote(path, safe='/')}"],
                capture_output=True, text=True, timeout=30,
            )
            if content_proc.returncode == 0:
                content_payload = json.loads(content_proc.stdout or "{}")
                if content_payload.get("encoding") == "base64":
                    text = base64.b64decode(content_payload.get("content") or "").decode("utf-8", "replace")
        except (subprocess.TimeoutExpired, json.JSONDecodeError, ValueError):
            text = ""
        for match in GH_URL_RE.finditer(text):
            slugs.add(match.group(1).lower())

    log(f"gh search {query!r} -> {len(slugs)} slugs")
    return slugs


def curl_json(url: str, timeout: int = 8) -> dict | None:
    try:
        proc = subprocess.run(
            ["curl", "-fsSL", "--max-time", str(timeout), url],
            capture_output=True, text=True, timeout=timeout + 3,
        )
    except subprocess.TimeoutExpired:
        return None
    if proc.returncode != 0:
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None


def us_job(title: str, location: str) -> bool:
    blob = f"{title} {location}"
    if TITLE_BLOCK.search(title):
        return False
    if not TITLE_ALLOW.search(title):
        return False
    if NON_US_RX.search(blob) and not US_RX.search(blob):
        return False
    return bool(US_RX.search(blob))


def us_candidate_row(row: dict) -> bool:
    blob = f"{row.get('role', '')} {row.get('location', '')}"
    if NON_US_RX.search(blob) and not US_RX.search(blob):
        return False
    return bool(US_RX.search(blob))


def variant_for(company: str, role: str, url: str) -> str:
    blob = f"{company} {role} {url}"
    if re.search(r"\b(ai|llm|agent|machine learning|ml|inference|model)\b", blob, re.I):
        return "AI Agent Infra"
    if re.search(
        r"\b(backend|platform|infra|infrastructure|devops|sre|cloud|distributed|data|security)\b",
        blob,
        re.I,
    ):
        return "Backend Platform"
    return "General SWE"


def api_source_board(slug: str, known_urls: set[str], max_jobs: int = 40) -> list[dict]:
    data = curl_json(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=false")
    if not data or "jobs" not in data:
        return []
    company = slug
    rows: list[dict] = []
    checked = 0
    for job in data.get("jobs") or []:
        title = job.get("title") or ""
        location = ((job.get("location") or {}).get("name") or "")
        url = norm_url(job.get("absolute_url") or "")
        if not us_job(title, location):
            continue
        job_id = str(job.get("id") or "")
        if not job_id:
            continue
        if url and url in known_urls:
            continue
        if not rows and data.get("jobs"):
            company = (data["jobs"][0].get("company_name") or slug)
        rows.append(
            {
                "status": "rendered_current",
                "ats": "greenhouse",
                "company": company,
                "role": title,
                "location": location,
                "url": job.get("absolute_url") or url,
                "variant": variant_for(company, title, url),
                "board": slug,
                "id": job_id,
                "source_text": f"api: {title} {location}"[:500],
            }
        )
        checked += 1
        if checked >= max_jobs:
            break
    return rows


def merge_api_priority_sourcing(boards: list[str], known_urls: set[str]) -> None:
    fieldnames = [
        "status", "ats", "company", "role", "location", "url", "variant", "board", "id", "source_text",
    ]
    rows = list(csv.DictReader(SOURCED.open(newline="", encoding="utf-8"))) if SOURCED.exists() else []
    if rows:
        fieldnames = list(rows[0].keys())
    boards_set = set(boards)
    appended = 0
    for slug in ROUND13_PRIORITY_BOARDS:
        if slug not in boards_set:
            continue
        has_rendered = any(
            r.get("status") == "rendered_current" and (r.get("board") or "").lower() == slug
            for r in rows
        )
        if has_rendered:
            continue
        api_rows = api_source_board(slug, known_urls, max_jobs=40)
        if api_rows:
            log(f"api_priority_sourcing board={slug} rows={len(api_rows)}")
            rows.extend(api_rows)
            appended += len(api_rows)
    if appended:
        with SOURCED.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)


def job_phone_required(board: str, job_id: str) -> bool | None:
    detail = curl_json(
        f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs/{job_id}?questions=true"
    )
    if not detail:
        return None
    for question in detail.get("questions") or []:
        if not question.get("required"):
            continue
        label = (question.get("label") or "").strip()
        for field in question.get("fields") or []:
            name = (field.get("name") or "").lower()
            if name == "phone" or PHONE_RE.search(label):
                return True
    return False


def probe_board_phone_optional(
    slug: str,
    known_urls: set[str],
    max_jobs: int = 25,
    *,
    round5_reprobe: bool = False,
) -> dict | None:
    data = curl_json(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=false")
    if not data or "jobs" not in data:
        return None

    company = slug
    fresh_phone_opt = 0
    fresh_phone_req = 0
    any_phone_opt = 0
    checked = 0

    for job in data.get("jobs") or []:
        title = job.get("title") or ""
        location = ((job.get("location") or {}).get("name") or "")
        url = norm_url(job.get("absolute_url") or "")
        if not us_job(title, location):
            continue
        job_id = str(job.get("id") or "")
        if not job_id:
            continue
        is_fresh = not (url and url in known_urls)
        checked += 1
        phone_req = job_phone_required(slug, job_id)
        if phone_req is True:
            if is_fresh:
                fresh_phone_req += 1
        elif phone_req is False:
            any_phone_opt += 1
            if is_fresh:
                fresh_phone_opt += 1
        if checked >= max_jobs:
            break

    include = any_phone_opt > 0 if round5_reprobe else fresh_phone_opt > 0
    if not include:
        return None

    if data.get("jobs"):
        company = (data["jobs"][0].get("company_name") or slug)
    return {
        "slug": slug,
        "company": company,
        "fresh_phone_optional": fresh_phone_opt,
        "fresh_phone_required": fresh_phone_req,
        "any_phone_optional": any_phone_opt,
        "round5_reprobe": round5_reprobe,
        "jobs_checked": checked,
    }


def discover_boards(
    exclude: set[str],
    known_urls: set[str],
    extra_candidates: set[str] | None = None,
) -> tuple[list[str], dict]:
    candidates: set[str] = set(SEED_SLUGS)
    candidates |= load_classified_boards()
    candidates |= set(ZERO_HISTORY_PRIORITY)
    if extra_candidates:
        candidates |= {s.lower().strip() for s in extra_candidates if s}
    for q in GH_SEARCH_QUERIES:
        candidates |= gh_search_slugs(q)

    round5_slugs = [s for s in ROUND5_BOARDS if s not in ROUND5_SKIP_ENTIRELY]

    candidates = {
        s.lower().strip()
        for s in candidates
        if s and re.fullmatch(r"[a-z0-9][a-z0-9_-]{1,48}", s.lower())
    }
    candidates -= exclude
    candidates -= {re.sub(r"[^a-z0-9]+", "", s) for s in exclude}
    candidates -= ROUND13_SKIP_BOARDS

    # Re-include zero-history priority boards even if in exclude pool from tracker company names.
    for slug in ZERO_HISTORY_PRIORITY:
        if slug not in ROUND13_SKIP_BOARDS:
            candidates.add(slug)

    new_candidates = candidates - set(round5_slugs)
    log(
        f"probe_candidates={len(new_candidates)} round5_reprobe={round5_slugs} "
        f"exclude_pool={len(exclude)} seed_count={len(SEED_SLUGS)}"
    )

    alive: list[dict] = []
    with ThreadPoolExecutor(max_workers=12) as pool:
        round5_futures = {
            pool.submit(probe_board_phone_optional, slug, known_urls, 40, round5_reprobe=True): slug
            for slug in round5_slugs
        }
        new_futures = {
            pool.submit(probe_board_phone_optional, slug, known_urls): slug
            for slug in sorted(new_candidates)
        }
        for future in as_completed({**round5_futures, **new_futures}):
            result = future.result()
            if result:
                alive.append(result)

    tracker_counts = board_tracker_counts()
    priority_rank = {slug: idx for idx, slug in enumerate(ZERO_HISTORY_PRIORITY)}

    def sort_key(row: dict) -> tuple:
        slug = row["slug"]
        zero_hist = 0 if tracker_counts.get(slug, 0) == 0 else 1
        pri = priority_rank.get(slug, 999)
        return (zero_hist, pri, -row["fresh_phone_optional"], slug)

    alive.sort(key=sort_key)
    slugs = [row["slug"] for row in alive[:40]]
    board_meta = {row["slug"]: row for row in alive}

    BOARDS_OUT.parent.mkdir(parents=True, exist_ok=True)
    BOARDS_OUT.write_text("\n".join(slugs) + ("\n" if slugs else ""), encoding="utf-8")
    log(f"boards_phone_optional={len(slugs)} slugs={slugs}")
    return slugs, board_meta


def merge_sourced_into_primary(extra_path: Path) -> None:
    if not extra_path.exists():
        return
    primary = list(csv.DictReader(SOURCED.open(newline="", encoding="utf-8"))) if SOURCED.exists() else []
    extra = list(csv.DictReader(extra_path.open(newline="", encoding="utf-8")))
    if not extra and not primary:
        return
    fieldnames = list((primary or extra)[0].keys())
    seen_urls = {norm_url(r.get("url") or "") for r in primary if r.get("url")}
    merged = list(primary)
    for row in extra:
        url = norm_url(row.get("url") or "")
        if url and url in seen_urls:
            continue
        if url:
            seen_urls.add(url)
        merged.append(row)
    with SOURCED.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(merged)
    log(f"merged_sourced extra_rows={len(extra)} total={len(merged)}")


def run_sourcing(boards: list[str], out_path: Path | None = None) -> None:
    dest = out_path or SOURCED
    if not boards:
        dest.write_text("status,ats,company,role,location,url,variant,board,id,source_text\n", encoding="utf-8")
        return
    env = os.environ.copy()
    env["NODE_PATH"] = NODE_PATH
    cmd = [
        "node", str(SOURCING),
        "--boards", *boards,
        "--max-per-board", "40",
        "--out", str(dest),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900, env=env)
    log(f"sourcing_rc={proc.returncode} stderr={(proc.stderr or '')[-500:]}")
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)


def filter_phone_optional_sourced() -> dict:
    rows = list(csv.DictReader(SOURCED.open(newline="", encoding="utf-8"))) if SOURCED.exists() else []
    kept: list[dict] = []
    skipped_phone = 0
    skipped_board = 0
    api_errors = 0

    for row in rows:
        if row.get("status") != "rendered_current":
            continue
        board = (row.get("board") or "").lower()
        if board in EXTRA_EXCLUDED or board in ROUND13_SKIP_BOARDS:
            skipped_board += 1
            continue
        if not us_candidate_row(row):
            continue
        job_id = row.get("id") or ""
        if not board or not job_id:
            continue
        phone_req = job_phone_required(board, job_id)
        if phone_req is None:
            api_errors += 1
            continue
        if phone_req:
            skipped_phone += 1
            continue
        kept.append(row)

    if kept:
        with PHONE_OK.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=kept[0].keys())
            writer.writeheader()
            writer.writerows(kept)
    elif PHONE_OK.exists():
        PHONE_OK.unlink()

    return {
        "sourced_total": len(rows),
        "phone_optional_kept": len(kept),
        "skipped_phone_required": skipped_phone,
        "skipped_board": skipped_board,
        "api_errors": api_errors,
    }


def security_precheck(company: str, role: str, board: str, job_id: str, url: str, variant: str, location: str) -> dict:
    env = os.environ.copy()
    env["NODE_PATH"] = NODE_PATH
    proc = subprocess.run(
        [
            "node", str(APPLY),
            "--company", company, "--role", role, "--board", board,
            "--job-id", job_id, "--url", url, "--variant", variant,
            "--location", location, "--precheck-security-only",
        ],
        capture_output=True, text=True, timeout=120, env=env,
    )
    try:
        return json.loads((proc.stdout or "").strip() or "{}")
    except json.JSONDecodeError:
        return {"status": "Skipped", "code": "security-precheck-parse-error", "stdout": (proc.stdout or "")[-400:]}


def sort_rows_for_precheck(rows: list[dict], tracker_counts: dict[str, int]) -> list[dict]:
    priority_rank = {slug: idx for idx, slug in enumerate(ZERO_HISTORY_PRIORITY)}

    def key(row: dict) -> tuple:
        board = (row.get("board") or "").lower()
        zero_hist = 0 if tracker_counts.get(board, 0) == 0 else 1
        pri = priority_rank.get(board, 999)
        return (zero_hist, pri, board)

    return sorted(rows, key=key)


def precheck(max_ready: int = MAX_ATTEMPTS, known_urls: set[str] | None = None) -> dict:
    env = os.environ.copy()
    env["NODE_PATH"] = NODE_PATH
    source_path = PHONE_OK if PHONE_OK.exists() else SOURCED
    rows = list(csv.DictReader(source_path.open(newline="", encoding="utf-8"))) if source_path.exists() else []
    tracker_counts = board_tracker_counts()
    rows = sort_rows_for_precheck(rows, tracker_counts)

    kept: list[dict] = []
    probed = 0
    skipped_dup = 0
    skipped_embed = 0
    blocker_counts: Counter[str] = Counter()
    sample_blockers: list[dict] = []
    known = known_urls or set()
    known |= load_round13_excluded_urls()

    board_ready_counts: dict[str, int] = {}

    for row in rows:
        if row.get("status") != "rendered_current":
            continue
        board = (row.get("board") or "").lower()
        if board in EXTRA_EXCLUDED or board in ROUND13_SKIP_BOARDS:
            continue
        if not us_candidate_row(row):
            continue
        url = row.get("url") or ""
        if url and norm_url(url) in known:
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
                "node", str(APPLY),
                "--company", company, "--role", role, "--board", board,
                "--job-id", job_id, "--url", url, "--variant", variant,
                "--location", location, "--precheck-only", "--allow-manual-retry",
            ],
            capture_output=True, text=True, timeout=120, env=env,
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
                sample_blockers.append({
                    "company": company,
                    "role": role[:80],
                    "status": payload.get("status"),
                    "blockers": payload.get("blockers") or [payload.get("code")],
                })
            continue
        answers = payload.get("answersPreview") or payload.get("questions") or []
        required = [q.get("label", "") for q in answers if q.get("required")]
        if any("phone" in (r or "").lower() for r in required):
            blocker_counts["phone-required-playwright"] += 1
            continue

        sec = security_precheck(company, role, board, job_id, url, variant, location)
        sec_code = sec.get("code") or ""
        if sec_code in ("needsSecurityCode", "skip-email-verification") or sec.get("status") != "SecurityPrecheckOk":
            blocker_counts[sec_code or "skip-email-verification"] += 1
            if len(sample_blockers) < 8:
                sample_blockers.append({
                    "company": company,
                    "role": role[:80],
                    "status": sec.get("status"),
                    "blockers": [sec_code or "skip-email-verification"],
                })
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
        1 for r in rows
        if r.get("status") == "rendered_current"
        and (r.get("board") or "").lower() not in EXTRA_EXCLUDED
        and (r.get("board") or "").lower() not in ROUND13_SKIP_BOARDS
        and us_candidate_row(r)
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
    }


def run_batch(max_attempts: int = MAX_ATTEMPTS) -> tuple[int, list[str]]:
    if not READY.exists():
        return 0, []
    env = os.environ.copy()
    env["NODE_PATH"] = NODE_PATH
    before, _, _ = tracker_stats()
    before_counts = board_tracker_counts()
    today_count = today_submitted_count()
    target_submitted = today_count + max_attempts
    log(f"batch_cap today_count={today_count} max_attempts={max_attempts} target_submitted={target_submitted}")
    proc = subprocess.run(
        [
            "python3", str(BATCH),
            "--csv", str(READY),
            "--max-attempts", str(max_attempts),
            "--target-submitted", str(target_submitted),
            "--company-cap", "20",
            "--allow-manual-retry",
        ],
        capture_output=True, text=True, timeout=3600, env=env,
    )
    log(proc.stdout[-4000:] if proc.stdout else "")
    if proc.stderr:
        log(proc.stderr[-2000:])
    after, _, _ = tracker_stats()
    after_counts = board_tracker_counts()
    new_boards = [
        b for b, c in after_counts.items()
        if c > before_counts.get(b, 0) and before_counts.get(b, 0) == 0
    ]
    return max(0, after - before), new_boards


def main() -> int:
    POOL.mkdir(parents=True, exist_ok=True)
    log(f"=== greenhouse round13 {datetime.now()} start ===")
    baseline_v, baseline_m, baseline_b = tracker_stats()
    log(f"baseline_verified={baseline_v} manualfinish={baseline_m} blocked={baseline_b}")
    log(f"skip_boards={sorted(ROUND13_SKIP_BOARDS)} priority_boards={ROUND13_PRIORITY_BOARDS} max_ready_per_board={MAX_READY_PER_BOARD} zero_history_priority={ZERO_HISTORY_PRIORITY[:8]}...")

    exclude = build_exclude_pool()
    known_urls = load_known_urls()
    round13_excluded = load_round13_excluded_urls()
    log(f"round13_excluded_urls={len(round13_excluded)} gh_search_queries={len(GH_SEARCH_QUERIES)}")

    new_boards, board_meta = discover_boards(exclude, known_urls)
    run_sourcing(new_boards)
    merge_api_priority_sourcing(new_boards, known_urls)
    phone_filter = filter_phone_optional_sourced()
    if phone_filter.get("phone_optional_kept", 0) < 12:
        log("pool_thin expanding")
        expand_boards, board_meta_expand = discover_boards(
            exclude,
            known_urls,
            extra_candidates=set(EXPAND_SEED_SLUGS),
        )
        board_meta.update(board_meta_expand)
        only_new = [b for b in expand_boards if b not in new_boards]
        if only_new:
            expand_sourced = POOL / f"greenhouse-round13-sourced-expand-{DATE}.csv"
            run_sourcing(only_new, out_path=expand_sourced)
            merge_sourced_into_primary(expand_sourced)
            merge_api_priority_sourcing(new_boards + only_new, known_urls)
            new_boards = list(dict.fromkeys(new_boards + only_new))
        phone_filter = filter_phone_optional_sourced()
    log(f"phone_filter={json.dumps(phone_filter, ensure_ascii=False)}")

    probe = precheck(max_ready=MAX_ATTEMPTS, known_urls=known_urls)
    log(f"probe={json.dumps(probe, ensure_ascii=False)}")

    submitted = 0
    new_submit_boards: list[str] = []
    if probe["ready"] > 0 and READY.exists():
        submitted, new_submit_boards = run_batch(max_attempts=MAX_ATTEMPTS)
    else:
        log('{"ready": 0, "note": "0 PrecheckReady jobs; batch skipped"}')

    final_v, final_m, final_b = tracker_stats()
    log(f"final_verified={final_v} manualfinish={final_m} blocked={final_b}")

    phone_optional_boards = [
        {
            "slug": slug,
            "tracker_count": board_tracker_counts().get(slug, 0),
            "fresh_phone_optional": board_meta.get(slug, {}).get("fresh_phone_optional"),
            "any_phone_optional": board_meta.get(slug, {}).get("any_phone_optional"),
        }
        for slug in new_boards
    ]
    summary = {
        "boards_discovered": new_boards,
        "boards_skipped": sorted(ROUND13_SKIP_BOARDS),
        "zero_history_priority": ZERO_HISTORY_PRIORITY,
        "prior_star_boards": sorted(PRIOR_STAR_BOARDS),
        "round13_excluded_urls": sorted(round13_excluded),
        "gh_search_queries": len(GH_SEARCH_QUERIES),
        "max_ready_per_board": MAX_READY_PER_BOARD,
        "phone_optional_boards": phone_optional_boards,
        "exclude_pool_count": len(exclude),
        "seed_candidates": len(SEED_SLUGS) + len(load_classified_boards()),
        "phone_filter": phone_filter,
        "sourced": probe["sourced"],
        "us_candidates": probe["us_candidates"],
        "probed": probe["probed"],
        "ready": probe["ready"],
        "ready_boards": probe.get("ready_boards"),
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
    log(f"=== greenhouse round13 {datetime.now()} done ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
