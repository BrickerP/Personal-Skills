# ATS Playbook — Greenhouse

**Provenance**: extracted 2026-10-15 from `archive/2026-10-cdp-retired/adapters/greenhouse_playwright_apply.cjs`
(1941 lines) and `archive/2026-10-cdp-retired/adapters/greenhouse_enter_security_code.cjs`, plus
`adapters/greenhouse_current_sourcing.cjs`, `adapters/greenhouse_embed_skip.py`,
`adapters/greenhouse_playwright_batch.py`, `runtime/greenhouse/run_round13.py` / `run_round18.py`,
`scripts/greenhouse_sourcing.py`, `scripts/greenhouse_url_resolver.py`, and `data/*.json`.

This file is the knowledge; the automation is gone. Drive Greenhouse forms interactively with `chrome-use`
(see `workflows/04-universal-web-apply.md` for the procedure).

[POLICY.md](POLICY.md) governs the current workflow. Selectors below are diagnostic
hints from observed pages, not a fixed fill map. Use fresh snapshots and real UI
actions; never execute retired adapters, inject setters or loop submission attempts.

> **Read this first**: before 2026-10-15 most answers below were **hardcoded in the retired adapter**, not read
> from `data/profile.json`. The identity / phone / location / work-authorization / years / education / AI-usage
> answers are now **frozen in the FROZEN section of `workflows/04-universal-web-apply.md`**, and every row
> below that touches them defers to it. All other answers here are adapter-era knowledge; keep them in sync
> deliberately.

---

## 1. Field mapping

### 1.1 Standard fields

| Control | Selector / name | Value | Source | Trap |
|---|---|---|---|---|
| First Name | `#first_name` | `Yupeng` | hardcoded | **The readiness anchor** — wait for it before touching anything else |
| Last Name | `last_name` | `Lu` | hardcoded | — |
| Preferred Name | `preferred_name` | `Yupeng` | hardcoded | — |
| Email | `email` | `yplmicro@gmail.com` | `basics.email` | — |
| Phone | `phone` | `$JOB_APPLY_PHONE` (US) | FROZEN → Phone; `~/.config/daily-job-apply/env` | Fill last, right before the gate, with `fill --from-env JOB_APPLY_PHONE` from the sourcing subshell (FROZEN → Phone); never type digits. Never the CN or the retired `+1-510` number. Form rejects it or demands +86 ⇒ ManualFinish |
| Resume upload | `input[type=file]#resume` | `Resume_YupengLu_AI_Agent_Engineer_1P_EN.pdf` | `resume_paths.default_1p_en` | Only after `/presigned_fields` fires; re-read the page afterwards to confirm the filename / `Remove\|Replace\|Attached` |
| Cover Letter upload | `#cover_letter` | blank | — | Required ⇒ ManualFinish |
| `resume_text` | textarea | blank | — | Required with no resume file field ⇒ ManualFinish |
| Location (City) | `#candidate-location` | type `San Francisco, CA`, then **click** the matching option | hardcoded | React-Select autocomplete — filling the value without selecting the option does nothing |
| School (edu 0) | `#school--0` | `Boston University` | `education[0].school` | Fill only if required-and-empty |
| Degree (edu 0) | `#degree--0` | `Master's Degree` → `Masters` → `Master` | `education[0].degree` | Option wording varies per board |
| Discipline (edu 0) | `#discipline--0` | FROZEN preference only when an exact truthful option exists; otherwise **ManualFinish** | open human gate | Preference order in FROZEN (`Mathematics` → `Finance` → `Physics`) is not a universal dropdown string. Do not invent a label |
| Education years | `start-year--0` / `end-year--0` | recorded graduation end years only: BU `2023`, OSU `2021` | FROZEN → Education | Start year/month or any other date ⇒ ManualFinish (`education-date-required-unverified`). Never invent a start year. DOB, if asked: `1999-08-03`. Years-of-experience floor stays `3` |
| Demographic dropdowns | `.demographic--container input.select__input[id]` | one of the 8 decline variants | — | Required demographics block submission |
| Required checkboxes | `input[type=checkbox][required]` | tick `consent\|privacy\|processing of personal data\|gdpr_(demographic_data\|processing)_consent_given\|certify\|acknowledge\|terms` | — | **Never tick** `future job opportunities\|talent community\|marketing` |
| Submit | `button[type=submit]` with text `Submit application` | — | — | After a security-code page, take the **last** button containing Submit |

### 1.2 Custom questions (`name` is `question_<id>`)

Type comes from the Greenhouse API: `input_text` / `textarea` / `multi_value_single_select` /
`multi_value_multi_select` / `input_file`. Match on label:

| Question topic | Answer |
|---|---|
| Work authorization / visa / sponsorship / citizen / permanent resident / "U.S. person" / clearance | FROZEN → Work authorization: authorized **Yes**, sponsorship **No**, U.S. citizen **No**, permanent resident **Yes**, U.S. person (EAR) **Yes**, active clearance **No**. Free text: `US Permanent Resident — No sponsorship required, now or in the future` |
| Nationality / country of citizenship / passport / country of birth | **Not frozen — ManualFinish** until the user answers |
| Current company / title | FROZEN → Company naming: `Baidu — MeDo` (current), `Cookiy AI` (past) / `AI Agent Engineer`. Stealth retired 2026-10-18. The old `VC-backed Voice AI Platform Startup` label is optional wording only, not the default |
| Location / city / state / zip | `San Francisco Bay Area` / California / `94105` |
| LinkedIn / GitHub | `.../in/yupeng-lu-845a0b411/` / `https://github.com/BrickerP` |
| Degree / major | `Master's degree` / `Mathematical Finance and FinTech` |
| Programming / interview language | Use verified profile/current user facts for the exact question; otherwise ManualFinish. Never inherit the retired proficiency sentence |
| Timezone | Use the exact verified user preference; otherwise ManualFinish. Do not infer physical timezone from the resume location |
| Salary | **ManualFinish** — numeric range is a user gate. Do not invent a number or a market sentence |
| How did you hear | Use the actual discovery source and matching option; unknown required source ⇒ ManualFinish. Never invent a referral or reuse an adapter default |
| Referral / prior employment / relatives / non-compete | Only exact confirmed facts; agreements and unverified legal/conflict answers are ManualFinish |
| Sanctions / restricted-country questions | ManualFinish unless the exact legal-status question has a confirmed FROZEN answer |
| SMS consent | **No** |
| Age / work eligibility threshold | Compare the exact threshold with confirmed DOB or FROZEN authorization; unsupported/ambiguous wording ⇒ ManualFinish |
| Years of experience | FROZEN → Years: derived from `professional_since` (3 as of 2026-10). `N+` ⇒ Yes iff N ≤ 3; numeric ⇒ `3`; free text ⇒ `3+ years`; buckets ⇒ highest with lower bound ≤ 3. **4+/5+/6+/7+/10+ ⇒ No** |
| Onsite / relocation | Use the current user preference for the actual location/commitment; unknown is ManualFinish |
| On-call / 24-7 | User preference, never the retired blanket Yes; unknown is ManualFinish |
| Degree thresholds (STEM/bachelor etc.) | Compare the exact requirement with confirmed FROZEN education; unsupported/ambiguous threshold ⇒ ManualFinish. Never infer every qualification from a generic STEM label |
| Policy acknowledgement ("I confirm this application / these materials are my own work"; authenticity attestation that does **not** ask about AI tools) | **Tick / Yes** (user policy A, 2026-10). Point at workflows/04 FROZEN → AI acknowledgements |
| "Do you use AI tools" | FROZEN → the one approved sentence in workflows/04. Employer bans AI ⇒ ManualFinish |
| AI-usage disclosure / "was this AI-assisted" / "did you use AI to write this" / interview AI attestation | **ManualFinish** — do not invent (policy A split) |
| Why us / anything else | **ManualFinish** — essay gate. Do not invent a template sentence |
| **Anti-AI / challenge questions** | **Do not answer — go straight to ManualFinish** |

---

## 2. Flow (job page → submit)

1. **URL normalisation** — `boards.greenhouse.io/<board>/jobs/<id>` **301s** to `job-boards.greenhouse.io/...`;
   treat both as the same job for dedupe. Strip tracking query noise (`gh_src`, UTM) and trailing `/application|/confirmation|/apply|/thanks`.
   **Dedupe identity / `norm_url` caveats:**
   - Keep `token=<jobId>` and path `jobs/<id>` as the ATS key. Never treat `?gh_src=` / UTM variants as distinct jobs.
   - `boards.greenhouse.io/<board>/jobs/<id>` ≡ `job-boards.greenhouse.io/...` ≡ `.../embed/job_app?for=<board>&token=<id>` for dedupe. Prefer opening the embed or job-boards form URL that actually hydrates `#first_name`.
   - Do **not** use board-root URLs as apply URLs (they 302 to the careers site).
   - If a `norm_url` helper and the tracker disagree, trust the job-id regex `(?:jobs/|token=)(\d{4,})` plus `record-application.py` refusal (exit 2).
2. **A board root path is not proof of Greenhouse** — `job-boards.greenhouse.io/nebius` **302s** to
   `careers.nebius.com`. Always take the canonical URL from the job page / resolver, never from a board root.
3. **Embedded detection** — URL contains `gh_jid=`, **or** the URL is not on a `greenhouse.io` domain.
   Embedded pages are slower: goto timeout 60s (vs 45s), form wait 60s (vs 30s).
   Resolver order: `job-boards.greenhouse.io/<board>/jobs/<id>` regex → else scrape
   `app.greenhouse.io/embed/job_app?token=<jid>` for `<board>/jobs/<id>` → else build from `?for=<board>`.
   **Direct-form fallback**: `https://boards.greenhouse.io/embed/job_app?for=<board>&token=<jobId>`.
   If `#first_name` never appears, fall back to this URL.
4. **Wait for hydration** — `#first_name` present **or** the `/presigned_fields` network response fired.
   **Do not start filling on page load.**
5. **Two prechecks** (informational for a human)
   - security-only: ≥4 `input[id^="security-input-"]` or body text matching
     `security code|verification code|check your email` ⇒ verification pending;
     follow §2.8. Use `skip-email-verification` only if the mailbox/code cannot be read.
   - full: compute answer blockers, then look for required `start-year--*` / `end-year--*`.
6. **Fill order** — resume upload → custom answers (React-Select by clicking) → location + education +
   demographics → required checkboxes → validate with a visible-invalid scan.
7. **Submit** — run the pre-submit gate first (`scripts/ats_pre_submit_gate.js`, `workflows/04-universal-web-apply.md` →
   Pre-submit gate); only when it returns `ok: true`, click `Submit application` once, then wait 6.5–10.5s.
8. **Email security-code branch** — page shows ≥4 single-character `security-input-*` cells. Read an
   **8-character alphanumeric** code from Gmail (body like `application: XXXXXXXX`, sender
   `no-reply@us.greenhouse-mail.io`, subject `Security code for your application to <company>`).
   Same company → same Gmail thread; always take the **newest** body.
   This page is **verification pending**, not Submitted. Take a fresh snapshot and
   use real UI input: one character per split cell, or the entire code in a single
   field, as the current page requests. Never use injected/native setters. If the
   value will not commit after one keyboard/Tab correction, ManualFinish. Recheck
   the current step and gate before its authorized confirmation action.
9. **Confirmation test** — require the final role-specific application-success
   page/state (such as `/confirmation`) or a matching application-received email.
   Read the message in context: a generic “thank you”, code field/code-delivery
   email or button state alone is not proof. Complete any email step first.

---

## 3. Blockers

| Detection signal | Blocker | Status | What to do |
|---|---|---|---|
| body `captcha\|hcaptcha\|possible spam\|error verifying\|verify your application\|unusual traffic\|automated queries\|are you a robot\|too many attempts\|security verification\|phone/sms verification` | `platform-anti-bot` | ManualFinish | **Do not retry submit**; hand the page to the user (`keep`) |
| body `404\|not found\|no longer accepting\|job is no longer available\|position has been closed` | `stale-job` | **Blocked** | Close the page |
| form rejects the US number, or demands +86 | `phone-rejected` | ManualFinish | Never use the CN or the retired `+1-510` number |
| required cover letter | `cover-letter-required` | ManualFinish | Human writes it |
| required `resume_text`, no resume file field | `manual-resume-text-required` | ManualFinish | Human pastes |
| required but no answer matched | `unsupported-required:<name>:<label>` | ManualFinish | Human answers (highest-frequency real blocker) |
| label matches anti-AI wording | `authentic-human-answer-or-challenge:<label>` | ManualFinish | Never auto-answer |
| non-US location | `non-us-location` | ManualFinish | Skip |
| required `start-year--*` / `end-year--*` | `education-date-required-unverified` | ManualFinish | Human fills years |
| resume upload not reflected within 18s | `resume-upload-not-reflected` | ManualFinish | Human uploads |
| no `#resume` on the page | `resume-input-not-found` | ManualFinish | This board may not accept a resume |
| still-invalid required fields after fill | `invalid-or-unhandled-required` | ManualFinish | Human reads the red text |
| ≥4 `security-input-*` or needs security code | `skip-email-verification` (batch label; the retired batch recorded it as Skipped) | not a blocker | Run the §2.8 email-code flow (`END-OF-RUN.md` §3); only if Gmail cannot be read ⇒ ManualFinish with this blocker |
| submit still disabled 15s after the code | `security-code-submit-disabled` | ManualFinish | Human inspects |
| no confirmation after click | `submit-unverified` | ManualFinish | Human verifies; check the tracker/mailbox before retrying (avoid double-submit) |
| company on `data/blocked-companies.json` (the retired runner also had a few in-code names) or ≥ `--company-cap` (default 20) | `company-blocked` / `company-cap-reached` | Skipped | Over-applied already |
| dedupe hit, not retryable | `duplicate-url` | Skipped | Expected |
| dedupe error | `dedupe-error:<n>` | ManualFinish | Human inspects |
| the session's `profile:` line is not `Lu (Profile 2, yplmicro@gmail.com)` | `wrong-profile` | **STOP the whole run** (not a per-role result) | Cleanup: `END-OF-RUN.md` §5 |
| goto / locator timeout | `page-load-or-form-timeout` | **Blocked** | Slow embed — retry off the canonical URL |
| any other exception | `runner-exception` | **Blocked** | — |

**Exit-code semantics from the retired runner** (keep these names, they are used in the ledger):
`0` = Submitted / DryRunReady / PrecheckReady · `10` = ManualFinish · `20` = Skipped · `30` = Blocked.

**Sourcing-stage signals** (queue filtering, *not* runtime results — same names, different meaning):
`questions-unavailable`, `required-react-selects:<n>`, `many-required-react-select-mirrors:<n>`,
`voluntary-self-id-required-react-selects`, `current-employer-title-required`,
`phone-required-…` (obsolete: a US number exists now), `cover-letter-required`, `authentic-human-answer-or-challenge`.

---

## 4. Gotchas (symptom → cause → response)

1. **Embedded page times out** → company site embeds Greenhouse in an iframe / slow → use the canonical
   `job-boards.greenhouse.io/<board>/jobs/<id>` or `/embed/job_app?for=&token=`.
2. **Resume looks uploaded but did not attach** → Greenhouse uses S3 presigned fields; injecting the file
   before hydration completes loses it → wait for `/presigned_fields`; re-read the page for the filename.
3. **React-Select value set but React state is fake** → plain `fill` passes HTML validity while the component
   ignores it → really click `[role="option"], [id^="react-select-"][id*="-option-"], .select__option`
   (or `ArrowDown`+`Enter`), then re-read `.select__container` text. **Pages with required React-Select
   mirrors should not be auto-submitted.**
4. **Required-ness hides in a mirror input** → check `required`, `aria-required`,
   `input.remix-css-1a0ro4n-requiredInput`, and a literal `*` in the label together.
5. **No reaction after submit** → three distinct cases: danger words = anti-bot; `security-input-*` = email
   code needed; neither = `submit-unverified` → ManualFinish: hand the page to the user (`keep`), **do not retry submit repeatedly**.
6. **Dedupe follows evidence** → obey the current helper’s explicit retryable
   verdict, not a regex over old labels. Do not retry an unverified final submit
   in the same run. `submitted:true / phone-rejected / platform-anti-bot / captcha /
   danger-text` never justify an automatic retry.
7. **Security code is split per cell** → one character per `security-input-N`; the submit button enables only
   after the last cell.
8. **Company-level over-application** → `data/blocked-companies.json` (the retired runner also hard-coded a few names); hard cap of
   20 submissions/company. Apply the current blocked list and POLICY, not an old ready/board counter.
9. **Required demographics block submit** → use the decline family.
10. **Required consent boxes block submit** → tick consent/privacy/GDPR/terms only, never marketing.
11. **Phone comes from the env file** → `$JOB_APPLY_PHONE` (US) per FROZEN → Phone, filled with `fill --from-env` last, right before the gate (a later `snapshot -i` echoes the typed digits, so mask it as FROZEN → Phone says). A form that rejects it or demands +86 ⇒ ManualFinish (`phone-rejected`); never fall back to the CN or the retired `+1-510` number.
12. **Education years** → graduation years are recorded and confirmed (BU `2023`, OSU `2021`) and are filled wherever asked; any other date (start year/month) ⇒ ManualFinish (`education-date-required-unverified`).
13. **`boards.` and `job-boards.` are the same job** → normalise or you will double-apply.
14. **Board root 302s to the company site** → never infer the form location from a board root.
15. **Anti-AI questions are traps** → `no ai-generated / if you're an AI tool / activation function / application challenge / do not use AI / human-written` ⇒ stop, do not answer. A policy acknowledgement that does not ask about AI tools ("I confirm these materials are my own work") is **Tick / Yes** (policy A). AI-usage disclosure is ManualFinish. See workflows/04 FROZEN.
16. **Company naming** → stealth retired 2026-10-18: the real employer may be named (`Baidu — MeDo` current; `Cookiy AI` past). The old label `VC-backed Voice AI Platform Startup` is optional wording only. Still avoid non-public internal specifics (client names under NDA, codenames, revenue details).
17. **`--system-chrome` had a window guard** → the application tab had to share a window with the
    `yplmicro@gmail.com` Gmail tab. chrome-use has no window id; the equivalent gate is now
    "same connected profile" (see `END-OF-RUN.md` §3/§5). Session for examples is `jobapply2` (`--browser yplmicro@gmail.com`).
18. **`pick` may be unavailable or flaky** on some chrome-use versions → fall back to clicking the option or keyboard. Do not stall the run waiting for a Greenhouse site adapter. `#candidate-location`: type the city, then click the matching option; `ArrowDown → Enter` often leaves the field empty.
19. **Security-code mail** stacks in one thread per company. Always take the **newest** body, not the first code in the thread.

---

## 5. Skip / priority lists

| File | Contents | Rule |
|---|---|---|
| `data/embed-career-domains.json` | 4 patterns: `vectra.ai`, `zipline.com`, `sambanova.ai`, `careers.` | Skip at sourcing/precheck — these company sites embed Greenhouse and time out |
| `data/gh-priority-boards.json` | 6 boards: `gradial, hyphenconnect, layerhealth, nebius, nexhealth, ngrokinc` | Sort key `(zero_history, priority_index, board)` — zero-history boards first, then priority |
| `data/gh-skip-boards.json` | 11 boards: `bessemerventurepartners, defenseunicorns, flyzipline, inversionspace, lilasciences, newsbreak, sambanovasystems, singlestore, telnyx54, vardaspace, vectranetworks` | Excluded at discover + precheck — these repeatedly hit duplicate-url or security-code failures |
| `data/blocked-companies.json` | company keys (read the file for the current list) | Hard skip — already over-applied |
| (in-code) | `tailscale, zuora, logicgate, lilasciences` | Extra exclusions |

---

## 6. Open questions

**Resolved 2026-10-15** (details in the FROZEN section of `workflows/04-universal-web-apply.md`):

- Phone: the temporary US number is filled everywhere, from `~/.config/daily-job-apply/env`.
- 2P resume trigger: the agent decides per role (user-flagged high-priority, referral, manual review ⇒ 2P; else 1P).
- "Do you use AI tools": daily coding agents, human-verified; an employer that bans AI ⇒ ManualFinish.
- GitHub: `BrickerP` (default for forms); `yupeng-dev` may also be used (both on the canonical CV). Years: derived from `professional_since` (`3+` now). U.S.-person (EAR) wording answered.
- Education: graduation years confirmed — BU `2023`, OSU `2021`; fill them. Start dates/months remain unrecorded.

**Still open (need a human decision)**:

1. **Education dates.** Graduation **end** years are frozen (BU `2023`, OSU `2021`) and DOB `1999-08-03` may be filled when a form asks. Start years/months and any other bio field are not recorded — ManualFinish. Do not invent them. Years-of-experience floor stays `3`.
2. **Nationality / country of citizenship / passport.** Not frozen, so ManualFinish until the user answers.
3. **Candidate location granularity.** `#candidate-location` typed `San Francisco` while the profile says
   `San Francisco Bay Area`. If a board's dropdown has no `San Francisco` option the old adapter stalled at
   `location-option-not-verified`; a human must choose sensibly. Los Angeles / Diamond Bar vs Bay Area is the user's call.
4. **Self-ratings** (AWS / Ansible / Bash proficiency questions) have no prepared answers. Decide truthful wording once.
5. **Remaining adapter-era hardcodes** (timezone, how-did-you-hear) were never read from `profile.json`. Company naming defers to FROZEN (`Baidu — MeDo`). Numeric salary is ManualFinish — do not revive the old market-competitive sentence.
6. **`gh-priority-boards.json` has no `canonical_path`** while the other two point at `~/job-hunt/data/`.
   Confirm which copy is authoritative.
7. **`submit-unverified` is ambiguous** — one verified case had neither anti-bot text nor security inputs,
   just no confirmation page. Whether that submission actually landed can only be checked in the tracker /
   mailbox.
8. **How often does `job-boards.greenhouse.io/<board>` 302 to a company site?** Only `nebius` was verified.

