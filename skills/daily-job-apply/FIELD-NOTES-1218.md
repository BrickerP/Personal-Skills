# Field notes from 1,218 submitted applications

**Window**: through 2026-10-25. **Ledger**: `~/job-hunt/tracker.csv` (1,218 applied / 216 ManualFinish / 7 Blocked / 0 duplicate ATS keys).

This file is the *empirical* layer. `SKILL.md` says what is allowed; this file says what actually happens
on the page after you have filled 1,200 of them. Read it before a run, and update it whenever a
fingerprint below stops being true.

---

## 0. The single most important finding

**Form difficulty is inversely correlated with applicant volume.**

| Company type | Form shape | Why |
|---|---|---|
| Consumer SaaS (Stripe, Airbnb, Box, Klaviyo) | essay + numeric salary + years + education Discipline | thousands of applicants, so they filter hard |
| AI chips / robotics / space (Tenstorrent, Figure, SambaNova, Relativity) | name, email, phone, city, one export-control ack | few applicants, so the form is open |

Practical rule: **when the well runs dry, change industry, not keyword.** Dozens of "AI startup" boards
are exhausted; the same effort spent on "software roles at hardware companies" still yields clean forms.

---

## 1. The four policy gates (these dominate everything)

At 1,218 applications the remaining unfilled pool is gated almost entirely by four things. Each is a
**policy** decision, not a technical one, so the agent must not guess:

| Gate | ManualFinish count | What unblocks it |
|---|---|---|
| Essay / required free-text | 44 | user writes or approves a draft |
| Numeric years of experience | 21 | one number ("3") |
| Numeric salary expectation | 17 | one range |
| Education **Discipline** | 10 | one major name |

Plus smaller gates: street address (13), citizenship (7), GPA/SAT (4), arbitration (3), AI-challenge/puzzle (3).

**Corollary**: if a run is producing mostly ManualFinish rows, stop applying and ask for these four
answers. Continuing to probe produces zero submissions per hour.

> **Daily-50 rule**: if ManualFinish / Blocked outnumber verified submits in the first 10 probes of a run, stop sourcing volume and surface the four gates. Continuing produces ~0 submits/hour.

---

## 2. Silent failure modes (the expensive ones)

Each of these *looks* fine and wastes a submission or an hour. Ordered by cost.

1. **Placeholder submit that never lands.** Greenhouse "Submit application" can no-op while every field
   reports valid. Always confirm the URL contains `/confirmation`, or the security-code field appears.
   A green `bad:0` is *not* proof of submission.
2. **Stale error text after a successful submit.** After the code step, `p[id$=-error]` often still shows
   the pre-submit errors. Trust `/confirmation`, not the error nodes.
3. **Hidden required checkbox named only "Acknowledge/Confirm".** Cloudflare, Everpure/Pure Storage and
   Vercel all ship one with no visible label text. It is invisible to `snapshot` grep by label; you find it
   via `document.querySelectorAll('input,[type=checkbox]')` → `checkValidity()` → then
   `el.scrollIntoView({block:'center'})` + real click. Plain `element.click()` often no-ops.
4. **A required dropdown that only appears *after* the first submit** (Vercel: "Please double-check all the
   information provided above"; Upstart: "Location Preference"). Pattern: submit → read errors by label →
   fill the newly revealed field → submit again.
5. **React-controlled text inputs that `fill` cannot commit** (Relativity "able to start within 30-60 days",
   Intercom "Current Location"). `fill` writes the DOM value but React state stays empty, so validation
   fails forever. Click the field and use `keyboard type` (real keystrokes); if that still fails, record
   ManualFinish — do not burn 10 turns.
6. **Multi-checkbox groups always report invalid.** Greenhouse marks *every* box in a group required.
   One selection is enough; `bad` count is a false signal. Known groups: "How did you hear", "Which
   locations", "Languages".
7. **Location autocomplete that never commits but does not block submission** (Brex, SingleStore).
   `#candidate-location` stays `""` and the form still submits. Do not loop on it.
8. **Two "Country" dropdowns.** The first is the phone dial code, the second is residence country.
   Filling the wrong one leaves the real field empty and the submit silently fails on phone.
9. **`intl-tel-input` country listbox stays expanded** and swallows every click on the page. If clicks stop
   landing, check `#iti-0__country-listbox` visibility, select the country, or dispatch `mousedown`.
10. **Greenhouse code throttling is per company.** A third request in a day may never arrive (Braze).
    Re-read the *last* `.a3s` body; the thread collapses and the newest code is at the bottom.
11. **City / `#candidate-location` commit.** `type → ArrowDown → Enter` often leaves the field empty and surfaces `candidate-location-error`. Prefer: type city text → **click the matching list option** (or chrome-use `pick` when it works) → re-read the value. If still empty and the board historically submits anyway (Brex/SingleStore), submit once and trust errors / `/confirmation`.
12. **Session hang / chrome-use version pin.** If `jobapply2` sticky-hangs, open a new session name with the same `--browser` instead of retrying the dead one. `pick` may be flaky; installed chrome-use version can differ from the binary still running until the extension/daemon restarts. See `job-apply-automation` → "Session hygiene". The retired session name `jobapply` is not reused.

---

## 3. Board fingerprints

### 3.1 Clean forms — fill these without hesitation

> **Gate that overrides everything below:** any company key in
> `data/blocked-companies.json` (canonical `~/job-hunt/data/blocked-companies.json`)
> is a hard skip, **even if its form is clean**. The list exists to stop
> over-application; check it *before* opening a form. As of 2026-10-25 it contains
> 84 keys including `twilio`, `abnormal`, `elastic`, `affirm`, `databricks`,
> `togetherai`, `pinterest`, `nuro`, `samsara`, `scaleai`, `gitlab`, `okta`.

| Board | Fields actually required |
|---|---|
| **Figure** (figureai) | name, email, phone, country, Location (City), LinkedIn, Website. Nothing else. 6/7 reqs submitted |
| **Tenstorrent** | same + one "I have read and understand the Export Control statement" = Yes + optional EEO |
| **SambaNova** | name/email/phone/city/LinkedIn/website only |
| **Mercury** | + Portfolio, "From where do you intend to work?", visa=No |
| **Twilio** | Form shape is clean (preferred name, LinkedIn, 2 acks, how-did-you-hear) **but** company key `twilio` is in `data/blocked-companies.json` (over-apply / policy). **Always check the blocked list first**; if listed → Skip `company-blocked`, do not re-probe. Do not delete the key. |
| **Starburst** | + Privacy "Acknowledge/Confirm", intended work location (state), support-experience=Yes, PST=Yes |
| **Buildkite / Ketch / PathAI / PlanetScale** | name/email/phone/city + a few free-texts that are *prefilled-able* facts |

### 3.2 Forms with a standard, known-good sequence (high volume)

**DoorDash** (`doordashusa`) — essay-free, ~10 required controls, demographics mandatory:
authorized=Yes · sponsor-now=No · sponsor-future=No · worked-at-DD=No · privacy=Yes · SMS=Yes ·
Gender=Male · transgender=No · Hispanic=No · Race=Asian · Veteran="I am not a protected veteran" ·
Disability="No, I don't have a disability". Some reqs inject **extra** questions
("3+ years professional experience", "3+ years ETL", "blog influence 1-5", "JS+JVM 3 yrs") — always probe
per requisition, never batch by company.

**Relativity Space** — EXPORT COMPLIANCE = "I am currently a U.S. Person" (green card qualifies),
onsite-5-days=Yes, hear-about is a checkbox group (one click), some reqs add F1/OPT=No and a
free-text "if your location differs…" that must be typed, not filled.

**New Relic** — all three reqs share one field set: Country=US dial, residence=US, State=CA,
employed-before=No, currently-working=No, authorized=Yes, sponsor=No, privacy=Yes, hear=LinkedIn,
Gender/Hispanic/Veteran/Race.

**Upstart** — two custom comboboxes (current location, familiarity) + a "Location Preference" checkbox
group that only appears after the first submit. Remote is the correct pick for remote reqs.

**Cloudflare** — "How did you hear" free text + relocate pick + immigration=No + the hidden
Acknowledge checkbox. Reqs whose location is Austin/London/Lisbon are **relocation-gated** and must be
skipped under the no-relocation rule.

**Abnormal Security** — Preferred first/last name, Zip 94105, Current Company, eligible=Yes, sponsor=No,
current employee=No, previously=No + full demographics. Some reqs add
"shipping production code as IC"=Yes and "primary language"=Python.

**GitLab (AMER)** — three self-rating dropdowns Poor/Fair/Average/Good/Excellent
(Linux=Good, Git=Excellent, MVC=Good) + location picker Canada/US/None + country of residence.

**Calendly** — gender options are "Man/Woman/…", state picker = California, ZIP 94105,
interview-recording opt-out is allowed.

### 3.3 Board-level or company-level blockers (do not re-probe)

| Scope | Blocker |
|---|---|
| **SpaceX** (all reqs) | GPA (UG/grad/doc) + SAT + ACT + GRE + clearance |
| **Tailscale** (all US reqs) | "Why Tailscale" essay + street address |
| **Coinbase** (all reqs) | education **Discipline** required |
| **Anthropic** (all reqs) | "Why Anthropic?" required on every requisition |
| **Klaviyo** | Discipline + required AI-usage free text |
| **Airbnb** | Candidate AI Usage Attestation (interview-process) |
| **Stripe** | no address field, but numeric "years of experience as a software engineer" on every req |
| **Samsara / SoFi / Coalition / Glean** | numeric years-of-experience questions |
| **Lithic** | numeric salary + a puzzle ("cracked the code") |
| **Arize** | AI-challenge ("What is 10 times 10?") |
| **AssemblyAI** | 3 essays + activation-function challenge |
| **Ashby platform-wide** | form validates, captcha token present, Submit no-ops (Baseten/Sierra/Decagon/Ramp). ~469 candidates unreachable |
| **Intercom** | custom `Current Location` select never commits |
| **Natera** | work-history end month with no "Present" option |

---

## 4. Discovery: what still yields, what is exhausted

| Source | Status |
|---|---|
| Greenhouse slug guessing | **exhausted** — a 161-domain probe returned 6 candidates, mostly non-US |
| "AI startup" boards | **exhausted** — the 30 best-known boards are all applied out |
| HN "Who is hiring" | **low yield** — October thread has 56 Greenhouse links; after `html.unescape()` only 32 are new and nearly all are Senior/Staff/Principal |
| **Software roles at hardware/robotics/chip companies** | **best remaining** — Tenstorrent (5), Figure (7), SambaNova, Relativity |
| Tracker rows marked `skip-email-verification` | **retryable** — 10 existed, 2 recovered for free (Upstart, Vercel); the rest re-checked and found to require essays or were Senior |
| Gmail for outcomes | must be swept per run — but through 1,218 applications there have been **zero interview invites** from this funnel |

HN extraction gotcha: Algolia returns HTML-escaped text (`https:&#x2F;&#x2F;…`).
`html.unescape(text)` **before** the regex, or you get 0 matches and wrongly conclude the thread is empty.

---

## 5. Bookkeeping that survives 1,200 rows

- `record-application.py` **refuses** to overwrite an already-applied requisition (exit 2,
  `DUPLICATE SKIPPED`). That refusal is a stop sign, not a bug. `--force` only for a knowing resubmission.
- Keys are `gh:<job id>` / `ashby:<uuid>` / `lever:<uuid>` / `hn:<id>` / cleaned URL — so
  `/jobs/<id>` and `/embed/job_app?token=<id>` collide correctly.
- Run the duplicate audit after every batch: parse `(?:jobs/|token=)(\d{4,})` out of `JD_URL` and count.
  Current state: **0 duplicates**.
- `ManualFinish` rows are debt, not failure. Keep the reason in `Notes` so a later session can group them
  and ask the user for the *one* answer that unlocks the group.
- Ledger vs tracker drift is real: a later ManualFinish upsert can overwrite a real submission. When a
  count looks wrong, grep the ledger for the company and repair the tracker row.
- After a batch: optional Gmail sweep mapping reject/ack → tracker `Rejected` / `Ack` (one email → one row). **Do not** send follow-ups on auto-ack mail.

---

## 6. Pre-run checklist (daily ~50 zero-gate)

Mirror of `COLD-START.md` → Daily ~50 zero-gate preflight. Do not start volume until all of these pass:

1. Chrome-use probe: `chrome-use browsers` and `chrome-use --session jobapply2 --browser yplmicro@gmail.com tab list --full` → **Lu (Profile 2, yplmicro@gmail.com)**. `TZ=Asia/Shanghai date`.
2. Reconnect or new session name if hung (same `--browser`). Never grant chrome-use `auth always`.
3. PDF hash vs `pdf-hashes.txt`. STOP on drift.
4. Profile Lu confirmed whenever `profile:` prints.
5. `data/blocked-companies.json` loaded. Twilio (`twilio`) if listed = Skip `company-blocked`. `JOB_APPLY_PHONE` exists in env (never echo).
6. Dedupe by `(?:jobs/|token=)(\d{4,})` before open. boards / job-boards / embed token are one job.
7. Zero-gate Greenhouse queue only for this routine.
8. ≥90s between verified submits.
9. Close the tab after each verified record. One active apply tab. After navigation, re-snapshot before the next click (refs and viewport are stale).
10. Stop early if ManualFinish / Blocked dominate the first ~10 probes.
11. Proof only `/confirmation` or a security-code field. CAPTCHA/SMS stay user blockers → ManualFinish.
12. Deliver the run summary in the Grok Bot chat.

Recorded bio facts only: DOB `1999-08-03` when asked; OSU graduation `2021`. Years floor stays **3**. Do not invent any other bio field. Before ending a run: duplicate audit. New fingerprints belong in a commit to Personal-Skills, not only in local notes.

---

## 7. Handoff

Session-level state, environment facts and the open decisions live in **`~/job-hunt/HANDOFF.md`**.
Read it first when picking this up cold: it holds the current counts, the Chrome session/profile
facts, the four policy gates that need the user, and the ranked next actions.
