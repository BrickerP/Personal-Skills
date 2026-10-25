# ATS Blocker Log — how to read it (and how not to)

> For **live** ops blockers and silent failures, prefer `FIELD-NOTES-1218.md` + `ATS-GREENHOUSE.md`. This file remains a decoder for the 2026-06 failure log only.

**Source**: `data/ats-evolution-log.jsonl`, cross-checked against `adapters/logs/*.jsonl`.
Analysis dated 2026-10-15.

This file exists because the log is **easy to misread**. Read this before quoting any number out of it.

---

## 1. What the log is

| Property | Value |
|---|---|
| Rows | 688 (685 attempt rows + 3 round_summary/fix rows) |
| Window | 2026-06-11 → 2026-06-21 (**06-19 missing**) |
| Coverage | 243 companies, 512 distinct URLs, 685 attempts |
| Row shape | `platform`, `url`, `status`, `blocker`, `fields_missing`, `company`, `role`, `channel`, `timestamp`, `dom_snippet` |
| Status values present | `Blocked`, `ManualFinish`, `Skipped`, `ClassifierProbe` |

### 1.1 It is a failure corpus — there is no success signal in it

**Zero rows have status `Submitted` or `Applied`.** Any "success rate" computed from this file is meaningless.
It records what went wrong, never what worked.

### 1.2 Blocker names are classifier output, not page facts

The two platforms emit blockers through **different mechanisms**, so a shared name does not mean a shared cause:

- **Ashby side**: substring matching over the whole captured stdout — e.g. `"phone" in output` — with
  `returncode-<exit>` as the fallback bucket.
- **Greenhouse side**: a structured blockers array derived from actual DOM checks.

Cross-platform comparison of these numbers is therefore invalid. The combined ranking below is an artifact of
two vocabularies stitched together.

---

## 2. Frequency table (as labelled)

| # | blocker | total | share | ashby | greenhouse |
|---|---|---:|---:|---:|---:|
| 1 | `phone-required-no-active-number` | 324 | 47.3% | 323 | 1 |
| 2 | `returncode-20` | 150 | 21.9% | 150 | 0 |
| 3 | `answer-blockers` | 88 | 12.8% | 0 | 88 |
| 4 | `page-load-or-form-timeout` | 38 | 5.5% | 0 | 38 |
| 5 | `submit-unverified` | 28 | 4.1% | 0 | 28 |
| 6 | `resume-upload-missing` | 13 | 1.9% | 13 | 0 |
| 7 | `returncode-1` | 11 | 1.6% | 11 | 0 |
| 8 | `duplicate-url` | 10 | 1.5% | 0 | 10 |
| 9 | `invalid-or-unhandled-required` | 8 | 1.2% | 0 | 8 |
| 10 | `manualfinish` | 5 | 0.7% | 1 | 4 |
| 11 | `blocked` | 5 | 0.7% | 3 | 2 |
| 12 | `platform-anti-bot` | 2 | 0.3% | 2 | 0 |
| 13 | `runner-exception` | 2 | 0.3% | 0 | 2 |
| 14 | `current-location-required`, `phone-…` | 1 | 0.1% | 1 | 0 |
| | **total** | **685** | | **504** | **181** |

There is no 15th name. The platforms barely overlap: Ashby only emits 1/2/6/7, Greenhouse only 3/4/5/8/9.

---

## 3. Decoder — what each label really contains

**`phone-required-no-active-number` (324)** — mixes two very different mechanisms. Greenhouse's version is
precise (required field named `phone` is empty). Ashby's fires whenever the string `phone` appears anywhere in
the output. Reading the true last stage out of 324 tail snippets: `submit-button-not-found` 29,
`form-not-loaded` 23, `duplicate-url` 13, `invalid-required-fields` 3 (10 rows showed
`_systemfield_resume` = "Please select a file."), `danger-text` 1, and 255 rows with no code at all.
→ **Look at the tail code before acting.** The only confirmed root cause was `basics.phone = null`. Since
2026-10-15 the US number is filled from `~/.config/daily-job-apply/env` (FROZEN → Phone in
`workflows/04-universal-web-apply.md`), so this label should now be rare.

**`returncode-20` (150, Ashby only)** — pure fallback bucket. True sub-causes: `duplicate-url` 54 +
`duplicate-role` 7 (**61 rows are successful skips, not failures**), `cdp-auth-click-failed` 28,
`company-blocked` 13 (all Decagon, and genuinely on the block list), `cdp-file-upload-failed` 6,
`keyboard-verify-failed` 3, `type-target-not-found` 3, `hear-about-reinforce-failed` 3, no-code 33.

**`answer-blockers` (88, Greenhouse only)** — "a required question had no submittable answer". The row status is
`Blocked` only when phone is among the blockers; otherwise `ManualFinish`. Real sub-causes (from structured
arrays): Coinbase-style AI-usage declarations and "how do you use AI tools today" dropdowns (≈27), long
experience free-text (K8s/AWS/CI-CD/observability/on-call ≈20), US-citizen/export-control statements (≈12),
"future roles" email opt-ins (6), timezone/work-location/country (8), years/GPA/degree (7), cover letter (6),
company trivia (2).

**`page-load-or-form-timeout` (38, Greenhouse only)** — Playwright `locator.waitFor` timed out waiting for
`#first_name`: the form never rendered. Concentrated in SambaNova 5, LogicGate 3, Coinbase 3, Mark43 3.
Retrying is worthwhile — Hyphen Connect and Virtu Financial later show `Submitted`.

**`submit-unverified` (28, Greenhouse only)** — no confirmation page after submit. Tails show reCAPTCHA
Enterprise plus a POST to boards.greenhouse.io returning **428**, alongside 8 single-character
`security-input-*` boxes = the email security-code challenge. 21 of 28 rows fall in 06-16→06-17
(lilasciences, allencontrolsystems). Not bypassable ⇒ ManualFinish. **Check whether the submission actually
landed before retrying, or you risk a double application.**

**`resume-upload-missing` (13, Ashby only)** — pre-submit validation reported `_systemfield_resume` =
"Please select a file." All five resume paths in `profile.json` exist, so the file was never the problem — the
attachment upload failed (consistent with the 6 `cdp-file-upload-failed` rows).

**`returncode-1` (11, Ashby only)** — a **local environment** failure, not an ATS one: `BlockingIOError:
[Errno 35] Resource temporarily unavailable` (fork/exec) and `subprocess.TimeoutExpired: Command ['osascript']
timed out after 30 seconds`. Lower concurrency, restart Chrome, retry later.

**`duplicate-url` (10, Greenhouse only, all Skipped)** — expected dedupe hit. Example: DataCamp's Principal AI
Engineer had job ids 7619315/7619318/7619320, already submitted via 7481117.

---

## 4. `fields_missing` is not a null check

| Field | Count | Share |
|---|---:|---:|
| Location | 337 | 49.2% |
| state | 170 | 24.8% |
| city | 99 | 14.5% |
| Phone Number | 43 | 6.3% |
| Are you authorized | 23 | 3.4% |
| Resume / "Please select a file." | 5 / 5 | 0.7% each |

The Ashby side only matches five fixed labels and records "this text appeared near the tail of the output" —
**not** "this field was empty". Location at 49% almost certainly over-reports. 249 rows (36%) have an empty
`fields_missing`.

**Only Phone Number had a confirmed root cause** (`basics.phone = null`; fixed 2026-10-15, the number now comes
from the env file). Location/state/city/authorization all have real values in `profile.json`, so those are
matching problems, not missing data.

---

## 5. Platform distribution — and the one real denominator

Row composition:

| platform | rows | Blocked | ManualFinish | Skipped/other |
|---|---:|---|---|---|
| ashby | 505 | 441 (87.3%) | 60 (11.9%) | 3 ClassifierProbe + 1 no-status |
| greenhouse | 181 | 91 (50.3%) | 80 (44.2%) | 10 Skipped (5.5%) |

**These are failure-mix percentages, not success rates** (no successes are recorded here). The Ashby count here includes one status-less row; §2 counts attempt rows only (504 + 181 = 685).

The only place a denominator exists is the Greenhouse section of `adapters/logs` (06-19→06-21, 141 distinct
roles):

```
Submitted 33 (23.4%) · Blocked 68 (48%) · ManualFinish 33 · Skipped 7
```

> ⚠️ This is why any claim of "the batch engine never submitted anything" is **wrong**. The adapter logs show 33
> Greenhouse submissions while `ats-adapter-registry.json` used to record `successes: 0`. On 2026-10-16 the
> registry counters were reset to 0 (`success_rate: null`) and the old row counts moved to `legacy_batch_attempts`;
> from now on they count chrome-use runs only. Trust the adapter logs for history.

The Ashby adapter logs carry no status, only a cumulative counter, so **no Ashby success rate can be computed**.

**Comparability**: the two platforms never ran in the same period (Ashby 06-11→06-15, Greenhouse mostly after
06-16), so no platform-vs-platform comparison is valid.

**Diagnosability** is the fair comparison: 94.3% of Ashby rows collapse into two over-aggregated labels
(and 61 of them are just dedupe skips), so you cannot tell a real Ashby failure from a duplicate skip. Greenhouse
labels are granular and map directly to an action.

---

## 6. Timeline — phases track the tooling, not the platforms

| Phase | Rows | Mix | Dominant blockers |
|---|---:|---|---|
| A 06-11→06-15 | 498 | ashby 489 / gh 9 | `phone-required` 319 + `returncode-20` 150 (= 94.3%) |
| B 06-16→06-18 | 44 | gh 42 / ashby 2 | `submit-unverified` 21 + `page-load` 13 |
| C 06-20→06-21 | 143 | gh 130 / ashby 13 | `answer-blockers` 86 + `page-load` 25, new `returncode-1` 10 |

- 06-12 is the single-day peak (211 rows), with `returncode-20` spiking by 82 (mostly dedupe skips).
- 06-16 is simply **when the run switched to Greenhouse** — the whole label vocabulary changes there.
- The 06-20 `answer-blockers` surge (86 rows in two days) coincides with `submit-unverified` disappearing. Two
  days is too small to attribute this to an ATS change; **insufficient data**.
- 06-19 has zero rows here, though `adapters/logs` shows two small batches that day — that day ran but was not
  written to this log.
- `returncode-1` (local resource exhaustion) appears only in phase C, consistent with higher concurrency, but
  n=11 is too small to conclude.

---

## 7. Limitations (quote these when citing the log)

1. **Failure-only**: zero `Submitted` rows. No success rate is derivable from this file.
2. **Labels are code artifacts, not page facts**: Ashby's `"phone" in output` misfires; `returncode-20` is a
   catch-all. The same name means different things per platform.
3. **`dom_snippet` is not an evidence chain**: it is a 220–800 char tail truncation of stdout, so the actual
   first failure is invisible. It can also **contradict the row**: 11 rows contain a `recorded-submitted /
   Submitted` stage while their status says Blocked/ManualFinish. **"Blocked" does not mean the submission was
   rejected.**
4. **`fields_missing` is text matching over five hardcoded labels**, not empty-value detection. The Location
   figure is noise.
5. **Names merge multiple causes**: `returncode-20` = dedupe skip + CDP click/upload failure + company block
   list. `answer-blockers` = unanswerable required questions + non-US location + required cover letter. Always
   open the tail to split them.
6. **Time and platform are collinear**: each platform only ran in its own window, so no controlled comparison is
   possible and no change can be attributed to an ATS redesign.
7. **Granularity is "attempt", not "job"**: 685 rows map to 512 URLs; one role appears up to 8 times.
8. **ManualFinish (140 rows) has no follow-up state**, so the log only covers the automated portion.
9. **Cross-reference is narrow**: `adapters/logs` covers only 06-19→06-21 and only Greenhouse has
   status/returncode; the Ashby side cannot be cross-validated.
