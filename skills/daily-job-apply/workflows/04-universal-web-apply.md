# Channel 4: Universal web / official ATS workflow

Use after LinkedIn Easy Apply hits a limit, or when a LinkedIn job opens an external application page. Goal: high-volume broad-funnel applications across company career sites and ATS platforms while preserving truthful/stealth answers.

## Priority order

1. Agent / AI Infra / ML Systems seed roles first.
2. Then broad Backend / Full-stack / Platform / Infra / General SWE roles.
3. Prefer official company/ATS pages over staffing mirrors when both exist, but do not over-filter in high-volume mode.

## Adapter model

- LinkedIn Easy Apply: use `linkedin-application-agent`; stop at LinkedIn limit.
- LinkedIn external apply: open the external URL in Chrome Debug, classify ATS/platform, then use the matching adapter below.
- Resume upload selection:
  - Default / high-volume official ATS applications -> `Resume_YupengLu_AI_Agent_Engineer_1P_EN.pdf`.
  - Explicit high-priority, referral, or manual-review applications -> `Resume_YupengLu_AI_Agent_Engineer_2P_EN.pdf`.
  - Older buckets (`AI Agent Infra`, `Backend Platform`, `General SWE`) must resolve to the 1P English PDF unless the user explicitly asks for 2P.
  - Absolute base path: `/Users/yupeng/Documents/Obsidian Vault/Resume_YupengLu/application-ai-agent/`.
- Lever: stable adapter; supports resume upload, standard fields, location, authorization, demographic decline/prefer-not, and common text/radio/dropdown questions.
- Greenhouse: standard adapter; fill standard fields, upload resume. **Batch runs skip email-verification boards** (`skip-email-verification` at precheck). ManualFinish cleanup may use Gmail + `greenhouse_enter_security_code.cjs`. Allow official hidden/invisible reCAPTCHA token generation. Stop on visible graphical CAPTCHA/hCaptcha, SMS/phone verification, or impossible hidden validation.
- Ashby: partial adapter; fill standard fields, but stop on possible-spam / anti-bot / CAPTCHA.
- Workday: session-heavy/manual adapter; use only when logged in and form is simple, otherwise record blocked with exact blocker.
- Custom/company form: generic adapter can fill standard fields and upload resume, but classify unknown required questions before submit.

## Script ownership (canonical paths)

| Layer | Path | Role |
|-------|------|------|
| Legacy / sourcing | `~/.codex/skills/daily-job-apply/scripts/` | Classifiers (`greenhouse_sourcing.py`), dedupe, archive, pre-submit checks |
| Apply adapters | `~/Downloads/.omx/` | `ashby_apply_applescript.py`, `greenhouse_playwright_apply.cjs`, batch runners |
| Round orchestration | `~/job-hunt/` + `~/job-hunt/scripts/` | `run_greenhouse_round18.py`, `round{N}-batch.sh`, `manual-retry-runner.py` |

**Single entry**: `~/job-hunt/run-next.sh` (auto-routes GH when Ashby saturated).

## External ATS batch playbooks

### Ashby

```bash
bash ~/job-hunt/scripts/round110-batch.sh   # when exclude_known <= 1500
```

- `round{N}-batch.sh` pattern with probe-first gate (`ashby_form_probe_gate.py`, `round80_probe_first_gate.py`).
- Preflight: `--gh-global-rotate N` before dict mine when GH fallback enabled.
- ManualFinish: `python3 ~/job-hunt/scripts/manual-retry-runner.py --queue <csv> --allow-manual-retry`.

**Saturation**: when tracker unique URLs > 1500, run GH round18 first, then Lever; skip dict-only Ashby mine.

### Greenhouse

```bash
python3 ~/job-hunt/run_greenhouse_round18.py
python3 ~/job-hunt/run_greenhouse_round18.py --batch-only   # retry ready CSV
```

Template features: phone-optional API filter, per-board cap 2, embed skip (`greenhouse_embed_skip.py`), dynamic cap, `--batch-only`.

**Email verification** (`security-input-*`, POST 428): batch precheck marks `skip-email-verification` — treat as **ManualFinish**, not a batch slot. Optional cleanup via Gmail + `greenhouse_enter_security_code.cjs`.

### ManualFinish

```bash
python3 ~/job-hunt/scripts/manual-retry-runner.py --queue ~/job-hunt/candidate-pools/manual-retry-*.csv --allow-manual-retry
```

## Failure classification

Record every touched role in `~/job-hunt/application-ledger.md` and `~/job-hunt/tracker.csv` using one of:

- `Submitted`: confirmation page / submitted state verified.
- `ManualFinish`: agent completed the heavy work and left a filled page open for visible CAPTCHA/hCaptcha, SMS/phone verification, platform anti-spam, login, or unknown final confirmation; print detailed handoff in terminal/final response, not a separate Markdown queue.
- `Blocked`: cannot safely proceed or prepare the page. Include one of: `platform-anti-bot`, `account/platform-limit`, `stale-job`, `skill-gap`, `network/page-load`, `unsafe-question`, `login-required`.
- `Skipped`: duplicate, clearly irrelevant, current-company risk, or already applied.
- `ReferralContacted`: referral/HR contact sent.
- `ReferralBlocked`: contact path unavailable or limit reached.

## Archive emission

For every `Submitted` external ATS role, write the normal tracker/ledger records and then emit the Obsidian batch archive row:

```bash
python3 /Users/yupeng/.codex/skills/daily-job-apply/scripts/job_archive.py emit \
  --channel "<Channel from tracker, e.g. Lever official>" \
  --date "$(TZ=Asia/Shanghai date +%Y-%m-%d)" \
  --status Submitted \
  --company "<Company>" \
  --role "<Role>" \
  --jd-url "<JD_URL>"
```

This is required for Lever, Greenhouse, Ashby, Workday, company/direct, and other non-LinkedIn submissions. The helper normalizes channel names and is idempotent, so it is safe to re-run after tracker/ledger retries. Do not emit archive rows before a verified confirmation page or confirmation email.

## Standard truthful answers

- Email: `yplmicro@gmail.com`.
- Phone: leave blank when optional. If a phone number is mandatory, do not submit an inactive or unreachable number; record `ManualFinish` / `Blocked` with `phone-required-no-active-number`.
- Current company when optional or text-only: `VC-backed Voice AI Platform Startup`.
- Location: `San Francisco Bay Area` or `San Francisco, CA, United States`. Do **not** add "relocating from Beijing" in resume header or form free-text (privacy; curated PDFs omit it). Only discuss current physical location when a recruiter directly asks.
- Work authorization: authorized in US = Yes; sponsorship now/future = No; U.S. citizen = No; U.S. permanent resident = Yes.
- Demographics/veteran/disability: Prefer not to answer / decline where possible.
- Do not invent exact years, clearance, credentials, referrals, or employer names.

## Manual-finish terminal handoff

Email verification codes are agent-solvable when the relevant mailbox is available/logged in (for this search, `yplmicro@gmail.com`) **during ManualFinish cleanup**, not during high-volume GH batch slots. Batch precheck skips `security-input-*` boards as `skip-email-verification`. For ManualFinish pages, read Gmail, extract the code via `greenhouse_enter_security_code.cjs` or adapter logic, and submit if all other fields are safe.


When the form is filled but blocked at final human verification or final submit:

1. Do **not** close the Chrome tab.
2. Do **not** keep retrying or bypassing visible CAPTCHA/graphical anti-bot/SMS-phone checks. Ordinary email code retrieval and official invisible-reCAPTCHA token submission are allowed.
3. Record `ManualFinish | <company> — <role> | <url>` in `~/job-hunt/application-ledger.md` and add tracker notes with `manual-finish-needed`.
4. Print the page in the terminal/final response under `Manual finish pages`, including remaining action such as: `solve graphical CAPTCHA/hCaptcha`, `complete SMS/phone verification`, `login required`, or `answer an unsafe/unknown required question`. Do not write a separate `manual-finish.md`; do not list ordinary email code entry unless Gmail access/code generation failed.
5. Continue to the next role.

This is successful delegation: the agent did the heavy work (find role, open form, fill fields, upload resume); the user can do the light final action. Count it as `ManualFinish` in the ledger, not `Submitted`.

## Stop rules

Stop and record blocker rather than bypassing: visible CAPTCHA, hCaptcha, graphical reCAPTCHA challenge, SMS/phone verification, suspicious graphical anti-spam page, current-company risk, legally sensitive unknown, or required question that cannot be answered truthfully from `data/profile.json`. Do not stop for mailbox email codes or invisible reCAPTCHA tokens that the official page can generate without a graphical challenge.

## Batch output

At the end of a run, report counts by channel and by failure classification, plus the ledger/tracker paths and any `applications/<channel>-batch-YYYY-MM-DD.md` archive paths touched.
