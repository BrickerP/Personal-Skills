# OpenTrain — reject / decline / disqualification log

**Purpose:** Persistent memory so the Agent (and you) do not repeat the same failed applications.

**When to add a row**

- OpenTrain UI or email shows **Rejected / Declined / Not selected**.
- **Live chat** ends because of an honest capability mismatch (language, accent, student-only, geo, hours, etc.).
- You **self-skip** after reading requirements (same as a reject for future runs).
- **Automation** yields `agent_chat_timeout`, `timeout`, or obvious **resume vs. claim** friction in chat (treat as *likely* post-review decline if you push through).

**How to add (append only, newest at bottom)**

Copy a table row into the log below:

```markdown
| YYYY-MM-DD | Job (short) | Type | Cause / signal | Prevention (what we do next) |
|------------|-------------|------|----------------|------------------------------|
```

**Type** examples: `platform_decline` · `chat_disqualify` · `self_skip` · `closed_listing` · `no_proposal_cta` · `automation_fail` · `likely_post_review_decline`

---

## Log

| Date | Job (short) | Type | Cause / signal | Prevention (what we do next) |
|------|-------------|------|----------------|------------------------------|
| 2026-05-14 | LLM Trainer – Accent Recognition (Fintech) | chat_disqualify | Native **American accent** required for banking-style voice. | Skip **`accent_us_voice`** family; see bucket index. |
| 2026-05-14 | Korean Digital Content Data Collection | likely_post_review_decline | Chat **challenged Korean vs. resume** (warned on false/exaggerated info). Strong English/Mandarin story but **Korean line not on resume** → client review risk. | Skip **`digital_content_lang_non_resume`** unless OpenTrain profile + resume explicitly list that **human language** at required level. Prefer **EN/ZH + engineering/eval** roles. |
| 2026-05-14 | Portuguese / Hindi / Japanese / German / Italian / French … Digital Content Collection | automation_fail / bid_ui | **`agent_chat_timeout`** (PT) or **`skipped_bid_no_input`** / no completed proposal on cohort. | Don’t bulk blind-apply **“*Language* Digital Content Data Collection”** without Agent handoff every turn and bid UI check; or **exclude** on-site filters. |
| 2026-05-14 | Chinese Digital Content Data Collection | automation_fail | Long **`unknown`** phase → **`timeout`** in `mass_apply` (`state.js` gap). | Open job **manually**, fix `state.js` if recurring, or skip until DOM pattern known. |
| 2026-05-14 | Native Dutch Voice Actor (Pro Recording Setup) | self_skip / mixed | Listing requires **native Dutch + pro VO**; honest answer was **not native Dutch**—downstream **proposal_clicked_verify** still risks **platform_decline**. | Skip **`voice_native_actor`** for languages that aren’t **native on resume/profile**. |
| 2026-05-14 | Professional Voice Actor (Native Fluency) | mixed | Resume is **engineering-first**; chat asked about **VO history**—answered via **LiveKit/Tavus/voice product** truthfully; may still be **`platform_decline`** if client wants union-style VO credits. | Treat **VO-primary** listings as **high scrutiny**; only pursue if user confirms booth + credits story; else prefer **non-VO** tasks. |
| 2026-05-14 | Mathematics Expert with Python / similar STEM | bid_ui | **`skipped_bid_no_input`** — proposal pay UI not handled by `fill_max_bid_submit.js`. | Inspect page once; extend script or **manual bid** for that template. |
| 2026-05-14 | African-English … Native Fluency Required | closed_listing / lang | **Native fluency** gate; often **`closed`** in batch. | Skip **`lang_X_native`** when X isn’t user’s native stack (resume/profile). |
| 2026-05-14 | Pathology / Arabic / English Digital / Spanish Safety / Image Annotation QC | closed_listing | Logged as **`closed`** during run. | Normal churn; no action unless recurring errors. |
| 2026-05-19 | Italian-English AI Data Annotator | chat_disqualify | Stated **no professional Italian**; interview ended; proposal still submitted then likely poor fit. | Skip **Italian-English** / **`lang_X_native`** when X not on resume. |
| 2026-05-19 | Odia-English Biology/Science Content Labeling | platform_decline | Honest **no Odia**; chat completed; listing **Declined** after submit. | Skip **`digital_content_lang_non_resume`** for Odia and similar. |
| 2026-05-19 | Mathematics Expert with Python Experience | geo_ineligible | Proposal modal shows **`Country not eligible`**; **Submit Proposal** disabled (listing: USA, Germany). | Skip **`geo_ineligible`**; not a click/DOM bug. |

---

## Bucket index (quick scan)

Scan these **before** a long `mass_apply` / `apply_until_delta` run:

| Tag | Meaning | Action |
|-----|---------|--------|
| **`accent_us_voice`** | “American accent”, US consumer voice testing | **Skip** unless user is native US accent |
| **`lang_X_native`** | Title/body: **Native** / **native fluency** in language X | **Skip** if resume/profile don’t support native X |
| **`digital_content_lang_non_resume`** | “**{Lang} Digital Content Data Collection**” | **Skip** if that human language isn’t evidenced on resume **and** profile |
| **`voice_native_actor`** | **Voice actor**, **VO**, **recording setup** | **Skip** unless user confirms native language + booth story |
| **`student_only`** | Student ID / enrolment | Skip if not student |
| **`geo_ineligible`** | Location / authorization | Use green card / US facts only; skip mismatched geo |
| **`employment_status`** | “2025 active employment”, employer locks | Read listing; skip if hard fail |
| **`closed`** | No longer accepting | Skip |
| **`bid_ui`** | `skipped_bid_*` | Inspect DOM; extend script or manual submit |
| **`automation_unknown`** | `unknown` loop / `timeout` | Fix `state.js` or drive job manually |
| **`handoff_timeout`** | `agent_chat_timeout` | Never leave batch **unattended**; lower `--max` or single-job mode |

_Add new tags when a pattern repeats._
