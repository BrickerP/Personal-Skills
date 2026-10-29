# Form pitfalls and requisition examples

The filename is retained for existing links. These examples originated in the
October 2026 application run; they are not current counts, approved answers or
permanent company-wide rules. Use the live form and existing records to verify
what applies now. [POLICY](POLICY.md) and [FROZEN](workflows/04-universal-web-apply.md)
own decisions and facts; this reference only helps diagnose UI behavior.

---

## 0. Form simplicity does not establish job fit

Some inspected Figure, Tenstorrent and SambaNova requisitions had short forms.
That does not establish applicant volume, hiring difficulty, callback rates or
fit with the user's experience. Read the JD before applying. Hardware/robotics
companies can be useful sources of software roles; a clean form is not a reason
to apply to an unrelated support, hardware, language-specific or IT role.

Fields are configured per requisition. A blocker on one role does not block
every role at that employer. The explicit company blocklist remains binding.

---

## 1. Check existing facts before asking again

- Salary, motivation essays, unfamiliar legal commitments and undisclosed
  personal information follow POLICY's human-decision rules.
- Total experience, education, GPA and Discipline are not blanket blockers:
  FROZEN already contains confirmed facts and a Discipline preference. Use them
  only for the exact supported question. Total tenure does not prove the same
  years in each technology; unrecorded start dates or skill tenure stay unresolved.
- A simple factual free-text answer is different from a motivation essay. Read
  the actual wording, options and required state before classifying it.
- Do not promise that one answer unlocks a fixed number of roles. Check each
  still-open requisition for additional blockers first.
- If blocked/manual probes dominate the first approximately 10 daily-50 probes,
  stop volume work under POLICY and report only the genuinely missing decisions.

---

## 2. Silent failure modes

1. **Validity is not success.** A form can report `bad:0` without submitting.
   Require a final role-specific success state or matching receipt. A security
   code is verification pending, not a submission receipt.
2. **Stale errors.** Old error nodes can remain after final success. Verify the
   success state before interpreting them; never submit again after success.
3. **Generic acknowledgements.** Controls labelled "Acknowledge/Confirm" require
   reading the surrounding policy. The same label can mean privacy, a legal
   waiver or an AI attestation. Locate the current control, use real UI input,
   then verify selection. Read-only DOM inspection may help find its label.
4. **Fields missed before submit.** Vercel review-confirmation and Upstart
   location-preference controls have surfaced during validation. Inspect the
   full form first; after an explicit missing-field error, correct an approved
   answer once and re-run the gate. An unknown submit outcome is not retryable.
5. **Text field versus combobox.** A React Select search box is also an `input`.
   Typing "Yes" into it does not select an option. Use its role, current options
   and selected label to diagnose it. A DOM value alone cannot establish a React
   bug; persistent failure after one deliberate UI correction is ManualFinish.
6. **Checkbox groups.** Some forms mark each member required. Read the group
   instructions and actual checked state; follow the read-only gate's verdict
   instead of bypassing an invalid result or clicking the same box repeatedly.
7. **Empty city search input.** The input can clear when the selected city is
   rendered elsewhere. Verify the selected label/chip and gate. This does not
   mean the required location may be omitted. Applicant location is from FROZEN,
   never copied from the posting's office city.
8. **Two country controls.** Distinguish phone dial code from residence using
   surrounding labels. Correcting one does not fill the other.
9. **Expanded country listbox.** If it intercepts clicks, select/dismiss it with
   real UI input and re-snapshot. Do not dispatch events or manipulate state.
10. **Threaded code mail.** Inspect the newest matching message, including a
    collapsed thread's last message. Never print codes or phone numbers.
    Missing mail alone does not establish company-specific throttling; respect
    visible rate limits and do not repeatedly request codes.
11. **Tab-close warnings.** An untracked-tab warning is not proof that the target
    application tab closed. Verify the agent-owned tab's absence with `tab list`;
    do not close unrelated or user-kept tabs to clear a warning.
12. **Session hang.** Follow the
    [browser reference](../job-search/references/browser-apply.md#uncertainty-and-session-hygiene)
    for a fresh pinned session. Do not restart another bot's browser or retry
    a dead session repeatedly. A tool-version mismatch is a hypothesis to check.

---

## 3. Board fingerprints

### 3.1 Previously short forms — inspect the current requisition

> **Gate that overrides everything below:** any company key in
> `data/blocked-companies.json` (canonical `~/job-hunt/data/blocked-companies.json`)
> is a hard skip, **even if its form is clean**. The list exists to stop
> over-application; check it *before* opening a form. As of 2026-10-25 it contains
> 84 keys including `twilio`, `abnormal`, `elastic`, `affirm`, `databricks`,
> `togetherai`, `pinterest`, `nuro`, `samsara`, `scaleai`, `gitlab`, `okta`.

| Board | Observed form shape, not a reusable answer map |
|---|---|
| **Figure** (figureai) | Several roles used contact, resume, city and profile links; other roles added industry-experience questions |
| **Tenstorrent** | Contact/profile links plus an export-control-statement acknowledgement; read the statement |
| **SambaNova** | name/email/phone/city/LinkedIn/website only |
| **Mercury** | Portfolio/website, intended working location and visa question |
| **Twilio** | Form shape is clean (preferred name, LinkedIn, 2 acks, how-did-you-hear) **but** company key `twilio` is in `data/blocked-companies.json` (over-apply / policy). **Always check the blocked list first**; if listed → Skip `company-blocked`, do not re-probe. Do not delete the key. |
| **Starburst** | Privacy acknowledgement, intended work state, support experience and timezone questions; answers require evidence |
| **Buildkite / Ketch / PathAI / PlanetScale** | Contact/profile fields and company-specific factual questions; inspect each one |

### 3.2 Per-role variations to look for

- **DoorDash:** authorization, separate current/future sponsorship, employment
  history, privacy, messaging consent and demographics. Some roles add ETL or
  JavaScript/JVM tenure and engineering-blog questions. FROZEN says SMS consent
  is No and demographics should be declined where possible; historical choices
  are not approved defaults.
- **Relativity:** export status, sponsorship and sometimes F1/OPT, onsite or
  start-date questions. Distinguish a U.S. person from a U.S. citizen. Verify
  availability/onsite preferences rather than defaulting to Yes.
- **New Relic:** phone country, residence and state are separate controls. Some
  roles additionally ask about degree and language-specific experience.
- **Upstart:** current-location and familiarity selects plus a location-preference
  checkbox group. Choose from approved facts/preferences, not previous answers.
- **Cloudflare:** referral-source text, location/relocation, sponsorship and an
  acknowledgement. Identify the actual hub from the JD; "Hybrid" is not a city.
- **Abnormal:** preferred name, postal code, current company and eligibility;
  some roles add production-code/language questions. Resolve company aliases
  against the blocklist before probing.
- **GitLab:** self-ratings and location choices. Prior Linux/Git/MVC ratings in a
  transcript are not facts or user-approved self-assessments.
- **Calendly:** work-state options and interview-recording consent. Read the
  exact wording and current preference; gender labels differ across employers.

### 3.3 Previously encountered questions, not permanent board bans

For an allowed company, inspect the current requisition. These examples do not
override FROZEN or justify calling every employer's form unfillable. Explicit
company blocks and live anti-bot warnings still stop work.

| Scope | Blocker |
|---|---|
| **SpaceX** | GPA, standardized test scores and clearance; use only supported facts |
| **Tailscale** | "Why Tailscale" essay and street address on inspected roles |
| **Coinbase** | Education Discipline; compare options to FROZEN |
| **Anthropic** | "Why Anthropic?" on inspected roles |
| **Klaviyo** | Discipline + required AI-usage free text |
| **Airbnb** | Candidate AI Usage Attestation (interview-process) |
| **Stripe** | Full-time industry-experience wording; compare the exact question to FROZEN |
| **Samsara / SoFi / Coalition / Glean** | General or skill-specific tenure; total experience does not prove skill tenure |
| **Lithic** | numeric salary + a puzzle ("cracked the code") |
| **Arize** | An arithmetic question was observed; inspect its context under policy rather than inferring an AI prohibition from arithmetic alone |
| **AssemblyAI** | 3 essays + activation-function challenge |
| **Ashby examples** | No final success was observed on several attempts; that is not proof of a permanent platform-wide outage |
| **Intercom** | Current Location select appeared uncommitted; inspect selected labels/options before diagnosing a bug |
| **Natera** | Work-history date controls; inspect for a current-role checkbox, never invent an end date |

---

## 4. Discovery checks

| Source | Status |
|---|---|
| Greenhouse board discovery | Prefer links from official careers pages over guessing slugs; failed guesses do not establish market exhaustion |
| Public hiring posts | Parse actual link targets, not truncated display text; recheck that each requisition is still open |
| Hardware/robotics/chip companies | Evaluate software roles against actual experience; form length is not a fit score |
| `skip-email-verification` rows | Inspect existing proof and current preflight before revisiting; `submit-unverified` requires reconciliation |
| Gmail outcomes | Use the authorized Review stage; report the actual query/date window and separate acknowledgements, assessments and interview invites |

HN extraction gotcha: Algolia returns HTML-escaped text (`https:&#x2F;&#x2F;…`).
`html.unescape(text)` **before** the regex, or you get 0 matches and wrongly conclude the thread is empty.

---

## 5. Bookkeeping that survives 1,200 rows

- `record-application.py` **refuses** to overwrite an already-applied requisition (exit 2,
  `DUPLICATE SKIPPED`). That refusal is a stop sign, not a bug. `--force` only for a knowing resubmission.
- Keys are `gh:<job id>` / `ashby:<uuid>` / `lever:<uuid>` / `hn:<id>` / cleaned URL — so
  `/jobs/<id>` and `/embed/job_app?token=<id>` collide correctly.
- Audit current records by ATS identity after a batch. A Greenhouse-only regex
  does not prove zero duplicates across Ashby, Lever or other URLs.
- `ManualFinish` rows are debt, not failure. Keep the reason in `Notes` so a later session can group them
  and ask the user for the *one* answer that unlocks the group.
- If tracker and ledger disagree, preserve confirmed submission evidence and
  report the discrepancy. Reconcile only under an authorized record-update task.
- The preflight helper unifies ATS URL variants, counts Ack/Rejected as applied,
  and emits one verdict. Timeout/read-error means no permission to apply; it does
  not prove a particular filesystem root cause. See [Apply](../job-search/workflows/apply.md#required-check-for-every-role).
- During Apply, mailbox access is for the current application's verification code or receipt. Use [Review](../job-search/workflows/review.md) for an authorized outcomes review; status-only produces proposals, and record changes require the current explicit update/reconcile request or confirmation. **Do not** send follow-ups on auto-ack mail.

---

## 6. Pre-run checklist (daily ~50 zero-gate)

Use [COLD-START](COLD-START.md)
and [Apply](../job-search/workflows/apply.md). This reference adds no alternate
preflight, answer table, pacing rule or permission to submit.

---

## 7. Handoff

Session-level state, environment facts and the open decisions live in **`~/job-hunt/HANDOFF.md`**.
Read it when present when picking this up cold: it may hold counts, Chrome session/profile
facts, unresolved policy gates and ranked actions. If absent, use the existing records and current
preflight; do not invent missing handoff facts or block an otherwise valid request merely on absence.
