---
name: opentrain-application-agent
description: Use when the user wants Codex to operate OpenTrain in their real Chrome profile (profile, jobs, live chat, proposals). Scripts implement only the stable navigation flow; all interview text, MC choices, and job choices come from the Agent (handoff files or step-by-step tools). A numeric-only message N means batch target +N on All Proposals via apply_until_delta.
---

# Operator contract (batch applications)

When the user sends **only a positive integer N** (e.g. `10`, `20`), treat it as **one batch run** whose goal is to raise **`All Proposals`** on [Proposals (AI trainer)](https://app.opentrain.ai/ai-trainer?q=proposals) by **at least N** vs the pre-run snapshot. Rejected/declined rows still count if they appear in `All Proposals`.

**Canonical command:**

```bash
python3 /Users/yupeng/.codex/skills/opentrain-application-agent/scripts/apply_until_delta.py N
```

Optional: `OPENTRAIN_MAX_ROUNDS=200`. Report: `/tmp/opentrain_apply_until_last_report.json` and stdout `=== OpenTrain batch report ===`.

## What the scripts do (fixed flow only)

`mass_apply.py` implements **mechanical** steps only:

1. **`/find-job`** — scroll and collect **every** job card `extract_jobs.js` returns (**no** keyword/position filter). **`--max K`** limits how many are processed per round; ordering is feed order.
2. **Per job** — navigate, `state.js` phases: resume confirm, start chat, next step, submit/continue proposal, fill bid from **visible numeric/range copy** (`fill_max_bid_submit.js`), etc.
3. **Live Chat free-text** — script **never** authors answers. It prints **`AGENT_CHAT_WAITING`** and waits for **`/tmp/opentrain_chat_agent_reply.txt`** (plain text). Context: **`/tmp/opentrain_chat_handoff.json`** (`lastBot`, URL, title).
4. **Live Chat multiple-choice** — script **never** picks an option. It prints **`AGENT_MC_WAITING`** and waits for **`/tmp/opentrain_agent_mc_reply.txt`** with **one line**: the **exact** visible button label to click. Options listed in **`/tmp/opentrain_mc_handoff.json`** (`buttonLabels`).
5. **Proposals verification** — `apply_until_delta.py` re-reads `proposals_stats.js` between rounds.

**Handoff timeout** (chat + MC): **`OPENTRAIN_AGENT_HANDOFF_TIMEOUT_SEC`** (default **900**), or legacy **`OPENTRAIN_CHAT_TIMEOUT_SEC`**.

**Injection helpers** (Agent may also call these outside `mass_apply`):

- `scripts/emit_chat_reply_js.py` — textarea + Send.
- `scripts/emit_button_click_js.py` — click button/`[role=button]` with exact label.

## Authoritative sources (resume + OpenTrain profile)

When authoring **any** screening answer, proposal blurb, or chat reply for this user:

1. **English resume (read before long runs or when details matter):**  
   `/Users/yupeng/Documents/Obsidian Vault/resume_yupeng_en.md`  
   Use titles, employers, dates, skills, and metrics from here as the **primary written record** on disk.

2. **OpenTrain profile (source of truth on-platform):** Before claiming something “on my OpenTrain profile,” **pull current text from the live profile** (e.g. onboarding / public profile URLs in `references/opentrain-playbook.md`). Use **`page_summary.js`** / **`profile_form_state.js`** on those pages after navigating in Chrome. What the UI shows **wins** over memory if the resume and profile ever diverge—**prefer aligning wording with the profile** when both are in scope.

3. **Elaboration rule:** You may **自圆其说**—consistent, qualification-forward detail that extends beyond a bullet on the profile or resume—**as long as it does not contradict** the resume, the live OpenTrain profile, or **hard facts** (e.g. green card, employment status). Do not invent employers, degrees, or credentials that aren’t supported by those sources unless the user explicitly adds them in-chat.

## User copy preferences (screening & chat)

Default wording for OpenTrain **profile, live chat, and MC** is in **`references/user-copy-preferences.md`**: **US + New York** framing (avoid leading with China/CA); **English = native**, **Chinese = native** when relevant; **IT skills at max tier**; **no humble/self-disqualifying hedges**; objective is **pass qualification**, not exploratory chat.

When the user reports **post‑hoc rejects** (e.g. count is up but many listings are **Declined**), **separate “new rows” from “still a bad fit,”** append rows to the log, and tighten **bucket** rules so the next run **doesn’t trade raw count for obvious mismatches**.

## Pre-flight: cut obvious rejects (before bulk)

**Goal:** Prefer **fewer, fit‑matched** applications over spraying roles that chat or reviewers will **obviously** knock out.

1. **Read** [`references/reject-and-decline-log.md`](references/reject-and-decline-log.md) **bucket index** (2 min).
2. **Agent pre-scan** queued titles (from `extract_jobs.js`, dry-run, or user‑set `/find-job` filters) and **skip** when:
   - **`digital_content_lang_non_resume`**: “**{Lang} Digital Content Data Collection**” (or similar) where **that language is not** clearly on **resume + live OpenTrain profile**.
   - **`voice_native_actor`**, **`accent_us_voice`**, **`lang_X_native`**: native voice/accel/lang gates that don’t match **native EN/Mandarin + engineering** positioning.
   - **`closed`** / **`student_only`** / hard geo when applicable.
3. **Operational:** any run with **`AGENT_CHAT_WAITING`** must have **continuous Agent handoff**—otherwise **`agent_chat_timeout`** creates **wasted proposals** that **clog** review and feel like “random rejects.”

## Learning from rejects (mandatory upkeep)

Whenever the user (or OpenTrain) **rejects**, **declines**, or chat **disqualifies** a line of pursuit, append one row to **`references/reject-and-decline-log.md`** using the table format there. Before new applications, **skim that file** and the **bucket index**.

## Agent behavior (mandatory)

### Interview: read the other side **every single turn** (non‑negotiable)

Before **any** write to **`/tmp/opentrain_chat_agent_reply.txt`**:

1. **`Read`** **`/tmp/opentrain_chat_handoff.json`** in full (tool read, not memory, not a truncated log line).
2. Treat **`lastBot`** as the **only** question to answer this turn. If `lastBot` is empty or file missing, **re-read after 1–2s** or pull `state.js`—**do not** guess from an old turn.
3. **Log lines lie by omission:** `AGENT_CHAT_WAITING | q=…` is **truncated**. Never compose from `q=` alone.

Before **any** write to **`/tmp/opentrain_agent_mc_reply.txt`**:

1. **`Read`** **`/tmp/opentrain_mc_handoff.json`**; use **`buttonLabels`** + any **`lastBot`** text. Pick **one exact label** string only.

**If you answer the wrong slot** (e.g. **hours/week** vs **country**), you **failed** this rule—there is no excuse; the fix is always **re-read `lastBot` first**.

- **No detached batch runs:** Do **not** use `nohup`, shell `&` backgrounding, `disown`, or “fire-and-forget” for `apply_until_delta.py` / `mass_apply.py`. The Agent **starts** these and **owns** the run until it exits or you agree to stop—same chat session, no orphan processes.
- **Foreground execution:** Use **`python3 -u`** so lines flush immediately. **`2>&1 | tee /tmp/opentrain_last_run.log`** is allowed for a trace; it is **not** “background” as long as the process stays attached to the Agent-invoked foreground command you started.
- If one invocation would hit tool time limits, use **chunked foreground runs** (e.g. smaller `--max` per call, or fewer `apply_until_delta` rounds per call) instead of detaching a long job.
- While a batch runs, **watch** stdout / the tee log only to notice **`AGENT_CHAT_WAITING`** / **`AGENT_MC_WAITING`**; **every reply** still starts by **`Read` handoff JSON** (section above)—never paste from a stale plan or from truncated `q=`.
- **Job selection:** There is **no** built-in role allowlist. To “filter,” either limit with **`--max`**, have the user set filters **on the site’s `/find-job` UI** before the run, or **do not use** bulk apply for discovery—open listings manually and drive a single job with tools + `state.js`.
- **Do not** start a second `apply_until_delta.py` while the lock **`/tmp/opentrain_apply_until.lock`** is held.
- **After exit**, report baseline vs final numbers from the batch report JSON.

### Troubleshooting checklist

| Symptom | Likely cause | What to try |
|---------|----------------|-------------|
| `agent_chat_timeout` / `agent_mc_timeout` | Agent did not write the reply file in time | Watch the log; increase timeout env var. |
| `skipped_bid_*` | No parsable rate / no fillable control | Agent inspects proposal UI; extend `fill_max_bid_submit.js` if DOM shape is new. |
| `unknown` + `timeout` | `state.js` didn’t classify page (often a new DOM) | Drive that **job manually** once; patch `state.js`; see **`automation_unknown`** in reject log. |
| Obvious **platform rejects** after chat pressed resume/language | Title was **native foreign language / VO** or **digital content in L** without L on resume | Follow **Pre-flight** + **`reject-and-decline-log` buckets**; stop optimizing for count alone. |

## Browser control (multi-window safety)

- `chrome_eval.sh` must **only** use `execute active tab of window id <WINDOW_ID>`. **Never** `execute active tab of front window`.
- Optional safety: `CHROME_EVAL_URL_MUST_CONTAIN=app.opentrain.ai` / `scripts/chrome_eval_opentrain.sh`.
- **Auto-pick:** `scripts/chrome_resolve_opentrain.sh` → `<window_id> <tab_index>`.
- **Pin window:** `OPENTRAIN_CHROME_WINDOW_ID` + `chrome_resolve_opentrain_in_window.sh`, or `--window` / `--tab`.
- **Conceal:** default off-screen during `mass_apply`; use `CHROME_EVAL_CONCEAL=0` for snapshots. **Restore:** `scripts/chrome_restore_opentrain_window.sh <window_id>`.
- **Chrome:** `View → Developer → Allow JavaScript from Apple Events`.

```applescript
tell application "Google Chrome"
  execute active tab of window id <WINDOW_ID> javascript "<JavaScript string>"
end tell
```

**Scripts:** `chrome_tabs.sh`, `chrome_eval.sh`, `chrome_eval_opentrain.sh`, `select_tab.sh`, `mass_apply.py`, `apply_until_delta.py`; see `references/opentrain-playbook.md`.

## Scope (non-batch)

- Verify account/session on `app.opentrain.ai`.
- Profile: `labeler-onboarding`, resume-driven edits, public profile check.
- **Job merit and fit** are always **Agent judgment**—scripts do not encode “good” roles.

Read `references/opentrain-playbook.md` for tab listings and snippet paths.
