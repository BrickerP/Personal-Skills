# ATS Playbook — Ashby

**Provenance**: extracted 2026-10-15 from `archive/2026-10-cdp-retired/adapters/ashby_apply_applescript.py`
(4184 lines), plus `adapters/ashby_apply_batch.py`, `adapters/ashby_pool_dedupe.py`, `runtime/ashby/*`, and
`data/ashby-skip-slugs.json`.

This file is the knowledge; the automation is gone. Drive Ashby forms interactively with `chrome-use`
(see `workflows/04-universal-web-apply.md` for the procedure).

> **Read this first**: before 2026-10-15 most answers below were **hardcoded in the retired adapter**, not read
> from `data/profile.json`. The identity / phone / location / work-authorization / years / education / AI-usage
> answers are now **frozen in the FROZEN section of `workflows/04-universal-web-apply.md`**, and every row
> below that touches them defers to it. All other answers here are adapter-era knowledge; keep them in sync
> deliberately.

---

## 0. Entry form — the single most important rule

**Always open the full-page application form directly:**

```
https://jobs.ashbyhq.com/{slug}/{posting_id}/application
```

The retired adapter never clicked the job page's Apply button and never handled iframes. It stripped
`/application` for dedupe, then re-appended it for navigation. Do the same by hand: bypass the company-site
embedded card and land on the `/application` full page.

---

## 1. Field mapping

| Field as it appears | Value | Source | Trap |
|---|---|---|---|
| `input[name="_systemfield_name"]` | Yupeng Lu | hardcoded | — |
| `input[name="_systemfield_email"]` | yplmicro@gmail.com | hardcoded | — |
| First Name / Last Name (label exactly) | Yupeng / Lu | `basics.name` split on space | Must match `^first name$` exactly — suffixed labels are missed |
| Phone (`input[type=tel]`, `name*=phone`) | `$JOB_APPLY_PHONE` (US) | FROZEN → Phone; `~/.config/daily-job-apply/env` | Fill last, right before the gate, with `fill --from-env JOB_APPLY_PHONE` from the sourcing subshell (FROZEN → Phone); never type digits. Historically the top blocker label (323 log rows), but mostly a classifier artifact (`ATS-BLOCKERS.md` §3). Never the CN or the retired `+1-510` number. Form rejects it or demands +86 ⇒ ManualFinish |
| LinkedIn Profile / URL | `https://www.linkedin.com/in/yupeng-lu-845a0b411/` | `basics.linkedin` | React StringField — must **Tab out / blur** or submit fails with `Missing entry for required field: LinkedIn Profile` |
| Current Company / Most Recent Employer | `Baidu — MeDo` may be named (stealth retired 2026-10-18); the generic label `VC-backed Voice AI Platform Startup` remains optional wording. A required or lookup-style company field still needs the real name to match the CV ⇒ if unsure, ManualFinish (§6.3) | FROZEN → Company naming; `positioning.current_company_public_label` | Real employer allowed; the old stealth label is optional only. `input[name*="company" i]` is a broad match that writes into **any** input containing "company" |
| Current Job Title / Role | AI Agent Engineer | `experience[0].title` | Fill only when the field is empty |
| Current Location / Where are you currently located | `San Francisco Bay Area` (free text); autocomplete: type `San Francisco, CA`, click the match | FROZEN → Location | The retired adapter typed `San Francisco Bay Area, CA`, and its dropdown flow had to reach `San Francisco Bay Area, California, United States`. Granularity is still open (§6.2) |
| Desired Location / Location for employment | `Remote, United States` | hardcoded | — |
| Country of Residence / current country | `United States` | FROZEN → Location | — |
| Passport Country / Nationality / Citizenship | **Not frozen ⇒ ManualFinish** | — | The retired adapter typed a value inferred from `positioning.target_geo` (`profile.json` has no country key). The user never confirmed it |
| City, State | `San Francisco, California` | FROZEN → Location | Materialize-style "city/state String" was still blocked historically |
| GitHub Username / Handle | `BrickerP` (default) | FROZEN → Identity | `yupeng-dev` (work identity) may also be used — both appear on the canonical CV |
| Portfolio / GitHub URL / Website (`type=url`) | GitHub field: `https://github.com/BrickerP`. Website / Portfolio: blank unless required, then the same URL | FROZEN → Identity | The retired adapter put the GitHub URL into every `type=url` input |
| How did you hear about us | `LinkedIn` | `HEAR_ABOUT_TEXT_DEFAULT` | Option variant searches in order: LinkedIn → Online → Other → Company careers page → Company website → Job board; fallback text `Company careers page` |
| Work Authorization / Authorized to work | Yes; status dropdowns pick the Permanent-Resident family; the full `work_authorization` sentence is only for free text | FROZEN → Work authorization | Dropdown-value style (Citizen/Permanent Resident/Visa Holder) and Yes/No style are different DOM |
| Will you now or in the future require sponsorship | No | FROZEN → Work authorization | **Answer work-auth first, then sponsorship** |
| U.S. citizen | No | FROZEN → Work authorization | — |
| Age 18+ / Background check consent / Relocation / Travel | Yes | hardcoded | — |
| Previously employed / Current employee / Felony | No | hardcoded | — |
| SMS / text-message consent | No | FROZEN → Phone | An SMS **verification** step is ManualFinish |
| U.S. person (EAR, 15 CFR 772.1) | Yes. Other export-licence / foreign-person / legal-status wording ⇒ ManualFinish. Clearance-required or ITAR citizen-only roles: skip | FROZEN → Work authorization | The retired adapter answered Yes to "U.S. person" but No to EAR/export questions; a question containing both was undefined |
| Comp range aligns / Office days | Yes | hardcoded | — |
| Preferred Pronouns | He/Him | hardcoded | Only when that exact option exists |
| Favorite video game / most played game | **deliberately not filled** | `AUTHENTIC_SHORTTEXT_SKIP_RX` | Classified as a human-only field ⇒ ManualFinish |
| College / University | Boston University; The Ohio State University | FROZEN → Education | Matches `profile.education`. Any start/end date other than the master's graduation year (2023) ⇒ ManualFinish `education-date-required-unverified`; never invent dates |
| Years of experience | `floor(years since 2023-04)` = 3 as of 2026-10; "N+ years?" ⇒ Yes iff N ≤ 3 | FROZEN → Years of experience | The retired adapter hardcoded `5+`, which overstated the real figure. Never round up |
| Free-text textarea with no matching FROZEN answer | `profile.summary`, only for generic intro prompts ("about you", "additional information", "anything else"). Optional and unrelated ⇒ leave blank. Required and question-specific (why this company, a project story, salary reasoning) ⇒ ManualFinish `unsupported-required:<label>` | `profile.summary` | The retired adapter pasted `profile.summary` into every textarea. A generic summary under a specific question is not a truthful answer |
| Resume upload | `_systemfield_resume`, default 1-page PDF | `resume_paths.default_1p_en` | The page has a **second** file input (top "Autofill" block); picking it yields 0 files |

---

## 2. Flow (application page → submit)

1. **Dedupe gate** — `job_dedupe_check.py --company-cap 20`. Dimensions: same JD_URL, ≥20 submissions for the
   company, blocked-companies list, same company+role. Retryable exceptions: `ManualFinish` and not submitted,
   `form-not-loaded`, `resume-upload-missing`, non-submitting duplicates.
   **`platform-anti-bot` / `phone-rejected` / already-submitted never retry.**
2. **Role filter** — `\bAI Trainer\b` ⇒ Skipped.
3. **Open** — `chrome-use --session jobapply --browser yplmicro@gmail.com tab new --label ashby-<company> "<url>/application"`,
   then wait for the page (`workflows/04-universal-web-apply.md` step 3); reuse the labelled tab if it already exists.
4. **Identity guard** — the retired script required a Gmail tab for the `yplmicro@gmail.com` account in the
   same window as the application. It is now a check on every `profile:` line chrome-use prints (the first
   command of a new or restarted session): it must read `Lu (Profile 2, yplmicro@gmail.com)`, otherwise STOP
   (`wrong-profile`, `END-OF-RUN.md` §5).
5. **First fill pass** — all fields are lazily rendered: scroll the whole form top→bottom→top first. Fill text,
   then handle location dropdowns, extended booleans, and sponsorship separately.
6. **`form-not-loaded`** → wait 15s and refill once.
7. **Phone** → fill `$JOB_APPLY_PHONE` last, right before the gate (FROZEN → Phone: `fill --from-env`, snapshot
   masking). A form that rejects it or demands +86 ⇒ ManualFinish `phone-rejected`.
8. **`invalid-required-fields`** → refill verbatim once; still failing ⇒ ManualFinish
   `manual-finish-needed:invalid-required-fields`.
9. **Three pre-submit reinforcements** — core reinforce → auth booleans (9 serial sub-steps; any failure ⇒
   ManualFinish) → the pre-submit gate (`scripts/ats_pre_submit_gate.js`, see `workflows/04-universal-web-apply.md`:
   danger text, invalid required items). The old profile/window consistency check is now the `profile:` check
   in step 4.
10. **Submit** — blur+Tab the hear-about/LinkedIn fields first, then click the button whose text is exactly
    **`Submit Application`** (the page also has `Upload file` / `Replace` / `Yes` / `No`).
11. **Poll for result** — 18s → 6s → 6s. Success = URL contains `/application-submitted` or `/application/success`;
    or the page stays on `/application` with the submit button gone plus `Application Success` /
    `Your application was successfully submitted` / `We'll contact you if there are next steps` /
    `Thank you for your interest` / `We received your application`.
12. **Already applied** → `already submitted your application|you have already applied` ⇒ record `Skipped`
    (the retired batch layer called this `DuplicateSubmitted`).
13. **Failure** → on an S3 upload error, re-pick the resume and click Submit again only after the upload finished
    and the gate is clean. Never click again after a danger/anti-bot message: ManualFinish with `platform-anti-bot`
    (danger), before-code, or `submit-unverified:ashby`.
14. **Exit-code semantics** (retired batch layer, kept only to decode old logs): `0` success · `1` submit
    unverified · `10` window check · `13-15` pre-submit checks · `20` blocked · `22` role skipped ·
    `124-125` timeout/exception.

---

## 3. Blockers

| Detection signal | Blocker | Handling |
|---|---|---|
| body contains `possible spam` / `error verifying` / `verify your application` / `unusual traffic` / `are you a robot` / `too many attempts` / `hcaptcha` / `phone verification` / `sms verification` | `danger-text` / `platform-anti-bot` | **Stop immediately**: ManualFinish (`platform-anti-bot`), do not click Submit again on that page; add the slug to the skip list |
| `We couldn't submit your application … flagged as possible spam … please submit your application again` (observed in round100) | `platform-anti-bot` | Do not click again in this run. A human may retry once by hand later; if it fails again, switch companies — do not click repeatedly |
| `job not found` / `no longer accepting` / `position has been closed` | `stale-job` | Close, mark Blocked |
| required label contains phone/mobile/sms/texting, or `validationMessage` points at phone | `phone-rejected` (was `phone-required-no-active-number`) | Fill `$JOB_APPLY_PHONE` (FROZEN → Phone). Only if the form rejects it or demands +86 ⇒ ManualFinish; never substitute the CN or the retired `+1-510` number |
| required field contains `cover letter` | `cover-letter-required` | Human writes one, or skip |
| required field matches current location / currently residing / current country / tax residence / city,state | `current-location-required` → `manual-finish-needed:current-location-residence-required` | Must select a **city-level** option; re-read the input value to confirm |
| body shows `Missing entry for required field: <label>` | `invalid-required-fields` | Re-answer: click the real control, then confirm the error text disappears |
| required item matches only favorite video game / most played game | `manual-finish-needed:authentic-shorttext` | Human fills it (deliberately reserved for a human) |
| `document.body.innerText` < 100 chars, no `_systemfield_name/email/resume`, no visible submit | `form-not-loaded` | Wait 15s+ and retry; repeated failure ⇒ Blocked |
| zero visible, enabled buttons whose text contains submit | `submit-button-not-found` | Check whether it was already submitted / the page errored |
| file input exists but `files.length === 0` | `resume-upload-missing` | Re-pick the PDF and wait for the S3 upload to finish |
| required field is neither in the safe allowlist nor a known trap | `unknown-required:<label>` | Human judgement — usually needs long-form text or extra documents |
| form JSON contains `frobscottle` / `ai protection` / `ai assistant` / `bots?:` / `ignore previous` / `disregard` | `anti-ai-or-prompt-injection-form` | Skip — the company actively blocks AI agents |
| form contains `talk to jack` / `spoken to jack` | `jack-jill-gate-required` | Unbypassable — skip that board |
| same URL submitted / ≥20 at the company / on blocked-companies | `duplicate-url` / `company-cap` / `company-blocked` / `duplicate-role` | Do not apply |
| `Submit Application` clicked, no success text and no danger text | `submit-unverified:ashby` | Human re-checks whether the tab actually submitted |
| `profile:` line of the session is not `Lu (Profile 2, yplmicro@gmail.com)` | `wrong-profile` (old batch labels: `yplmicro-gmail-not-found` / `wrong-window`) | STOP the run, reconnect chrome-use to the yplmicro profile, then start again (`END-OF-RUN.md` §5) |

**Status split (important)**: `{stale-job, form-not-loaded, submit-button-not-found, resume-upload-missing}` =
**Blocked** (the page could not be prepared; do not touch it again). Everything else, including
`invalid-required-fields` (after one verbatim refill), `phone-rejected` and `platform-anti-bot`, = **ManualFinish**
(the form is prepared but the final step is blocked: hand the tab to the user with a bare `keep`, see
`workflows/04-universal-web-apply.md` → ManualFinish handoff). `wrong-profile` is not a row: it stops the run.

---

## 4. Gotchas (symptom → cause → response)

| Symptom | Cause | Response |
|---|---|---|
| Field looks filled, submit still says `Missing entry for required field` | Ashby is React-controlled; assigning `.value` never enters form state | Native setter + `input/change/blur`; otherwise real keyboard (⌘A → Backspace → insertText), then Tab out |
| Yes/No looks highlighted but server state is empty | Many boards use `<button role=...>`, not native radios | Click the button found by label text; re-read `aria-checked/aria-pressed/data-state` or `input:checked`, and confirm `this field is required` disappears |
| A radio exists but the wanted option never selects | Ashby uses opaque `value="on"` radios — matching must be by label text | Match by label; if `value==='on'` and the label doesn't match, **clear** it first, then select |
| City/country typed but still empty | These are comboboxes — only a real option selection counts | Open → type → wait ~1.2s for `[role=option]` → ArrowDown+Enter or click; then re-read `input.value` |
| Country lands on Dominican/Brazil/Ireland/Germany/Canada | The option list retains a previous selection | After selecting, verify the text matches `United States\|San Francisco\|Bay Area\|Remote`; otherwise clear and redo |
| A valid boolean group "is missing" | Lazy rendering — unscrolled entries do not exist | Scroll the whole form to the bottom and back to the top before filling/clicking |
| LinkedIn / how-did-you-hear filled but still reported missing | React StringField needs blur/Tab to commit | focus → blur → a real Tab per field |
| `ERROR Resume_...pdf failed to upload` + `Failed to fetch (ashbyhq-infra-prd-…s3…)` | Ashby uploads directly to S3 and it failed | Reset the file input (up to 3 tries with a cross-selector fallback), wait 3–5s, then verify `files.length` |
| `WARNING We're updating your application (e.g. uploading files), please try again when they're finished` | Submitted before the upload landed | Wait until the upload indicator/attachment completes, then click Submit Application |
| The attachment went somewhere else / 0 files | Two file inputs: top "Autofill from resume" (`Upload file`/`Replace`) and the real `#_systemfield_resume` | Only use `#_systemfield_resume`; fall back to the single `input[type=file]` if absent |
| Top shows `Autofill completed! Please review the information we filled in for you below` | Uploading the resume triggered autofill | Review every field — autofilled values may not match this project's wording |
| Wrong button clicked / Upload got clicked | The submit button must be exactly `Submit Application` | Never use position or "the first button"; distinguish `Yes`/`No`/`Replace`/`Upload file` |
| False "submitted" verdict | `We couldn't submit` / `flagged as possible spam` also contain the word "application" | Exclude `couldn't submit\|unable to submit\|already applied\|received your application before` first |
| A previously applied role gets re-applied | — | `you have already applied` ⇒ record `Skipped`, stop |
| Repeated retries make the form worse | Clicking does not guarantee convergence | **Max 3 retries per boolean question**, then ManualFinish |

---

## 5. Skip lists

**`data/ashby-skip-slugs.json`** — 267 entries (262 unique) in the skill's own `data/` (`DATA_DIR` in
`runtime/paths.py`; the retired layout kept the canonical copy in `~/job-hunt/data/`).
Matching normalises slugs by stripping non-alphanumerics and casefolding, so `Plaud/plaud`, `GitBook/gitbook`,
`red-oak/redoak`, `klarity-ai/klarityai`, `periodic-labs/periodiclabs`, `twelve-labs/twelvelabs`, `g2i/g2iinc`,
`heidihealth/heidihealth.com.au` are two spellings of the same entry.

Four documented reasons to skip:

1. **Anti-bot cooldown** — `scribe`, `pearl`, `scrunch`, `afterquery`, `aida` (annotated
   `platform-anti-bot spam flag/cooldown 24h`); `physicalintelligence`, `govdash` added dynamically mid-run.
2. **Human gate** — `jack-jill-external-ats` = the "Talk to Jack" gate (six consecutive failures in round16).
3. **Saturated / already applied** — OpenAI, Anthropic, Scale AI, Together AI, Cognition, Okta, Pinterest,
   Samsara, Verkada, Decagon and similar.
4. **Hard exclusion constants** — `EXCLUDE_SLUGS="beacons numeric parspec"` plus round additions
   `primeintellect langdock kiso-technology`.

**`data/blocked-companies.json`** — company keys hard-blocked (`hard-blocked-after-overapplication`; read the file for the current list),
complementing the 20-submissions-per-company cap. **Role-level**: `\bAI Trainer\b` ⇒ Skipped.

> `data/embed-career-domains.json` (vectra/zipline/sambanova/`careers.*`) is **Greenhouse-only** — do not mix it
> into Ashby.

---

## 6. Resolved and still-open questions

### Resolved (the answers live in the FROZEN section of `workflows/04-universal-web-apply.md`)

- **GitHub identity** → `BrickerP` is the form default; `yupeng-dev` may also be used (both on the canonical CV).
- **Years of experience** → derived from `professional_since` (2023-04): `3+` as of 2026-10, never `5+`.
- **EAR / "U.S. person"** → only the 15 CFR 772.1 wording is Yes (citizen = No, active clearance = No). Any other
  export-licence / foreign-person / legal-status wording ⇒ ManualFinish; clearance-required and ITAR citizen-only
  roles are skipped.
- **Phone** → the US number from `~/.config/daily-job-apply/env` in every phone field. The CN and retired
  numbers are never used; a form that rejects the US number ⇒ ManualFinish `phone-rejected`.

### Still open (need a human decision; until then the fallback in brackets applies)

1. **Nationality / passport / citizenship country.** Not recorded anywhere; the retired adapter inferred a value
   from `positioning.target_geo`. [ManualFinish.] "Country of residence" is settled: `United States`.
2. **Current-location granularity.** FROZEN fixes the free text (`San Francisco Bay Area`) and the autocomplete
   query (`San Francisco, CA`), but Materialize's city/state String still failed historically when a dropdown
   only accepts a city. Needs a live test, and the user's say-so on which city to claim. [Use the FROZEN value;
   a dropdown that offers neither ⇒ ManualFinish.]
3. ~~**Stealth wording.**~~ **Resolved 2026-10-18:** stealth retired — the real employer (`Baidu — MeDo`) may be used anywhere, including required/lookup company fields; match the CV. The generic label remains optional wording. [Fallback: if a lookup field rejects the real name, ManualFinish.]
4. **Email verification is an uncovered path.** `verify your application` and `Sign in` matched **zero** times in
   the retired adapter — there is no evidence of an Ashby email-verification flow. If one appears, it is new
   territory (the Greenhouse flow in `END-OF-RUN.md` §3 is the nearest model). [Email codes are agent-solvable per
   `SKILL.md`: read the code from the yplmicro Gmail tab; a visible CAPTCHA or SMS check ⇒ ManualFinish.]
5. **The stale-job regex contains a bare `not found`**, which can misfire on normal copy. Verify by hand rather
   than abandoning.
6. **Most of the 267 skip slugs have no recorded reason** — only a few comments in `ashby_apply_batch.py` are
   explicit. The rest need reverse-lookup in the tracker (already applied / flagged).
7. **No ManualFinish time limit is defined** — the convention is "hand the tab to the user with a bare `keep`,
   record after success", but there is no rule for when to give up.
