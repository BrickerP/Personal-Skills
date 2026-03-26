---
name: gmail-ai-daily-ops
description: Operate Gmail inboxes with Codex in the driver seat using the local `gmail-ai-worker` package. Use when the user wants Codex to read Gmail, prioritize threads, inspect context in real time, draft replies, archive or label messages, or run inbox automations without handing control to a rigid script workflow.
---

# Gmail AI Daily Ops

This skill is for **prompt-driven, automation-friendly Gmail operations** where Codex stays in charge of reasoning and Gmail API only provides read/write channels.

Treat the **worker root** as the local `tools/gmail-ai-worker` directory in the current workspace, or equivalently the package root that contains `gmail_ai_worker/config.py`.

## First-Use Presentation Contract

When the skill is used for the first meaningful time, or when the user input is empty / underspecified, do **not** start operating on Gmail immediately.

Instead, do a short **mailbox discovery pass** first:

1. inspect the connected mailbox list,
2. sample a meaningful historical window from the active mailboxes,
3. infer the user's likely mailbox profile,
4. then present a capability menu tailored to that profile.

Examples of mailbox profile signals:

- engineering-heavy mailbox
- marketing / growth mailbox
- founder / operator mailbox
- vendor / finance-heavy mailbox
- support / customer-conversation mailbox

After that, present a short capability menu in plain language with these sections:

1. `What I can do`
2. `What I will not do automatically`
3. `What you can configure`
4. `What I recommend automating for you`
5. `Recommended automation prompt`
6. `What I need from you now`

The first-use explanation should be concise but explicit enough that a non-technical user can understand the boundaries.

Use this structure:

- `What I can do`
  - read connected Gmail mailboxes
  - prioritize important threads
  - inspect one thread in detail
  - draft replies but not send them
  - archive or label low-risk mail when configured
  - produce a latest-run report

- `What I will not do automatically`
  - send email
  - make final business decisions for the user
  - auto-handle sensitive mail unless the user explicitly allows it

- `What you can configure`
  - which mailboxes are active
  - which capabilities are enabled
  - what kinds of mail to clean up
  - how broad the review window should be
  - whether drafts should be created automatically

- `What I need from you now`
  - choose whether to adopt the recommended automation prompt
  - choose one-time task vs long-term automation
  - confirm whether to change defaults
  - connect a mailbox if none is connected

Also include one short line explaining the inferred mailbox profile, for example:

- `Your active mailboxes currently look engineering- and vendor-heavy, so I can help most with notification cleanup, important thread triage, and draft preparation.`

After the menu, always provide:

1. a concise recommendation of what should be automated long-term for this user,
2. a complete suggested automation prompt that the user can adopt,
3. a short list of concrete next steps.

Do not stop at "here are my abilities." The first-use response should proactively answer:

- what I think I should take over for you,
- how I would automate it,
- and what you should do next.

Only after that should you offer optional next steps such as running one immediate triage pass.

The Python scripts are only transport primitives:

- search candidate threads
- inspect one thread in detail
- create one Gmail draft
- modify one thread's labels or inbox status
- list available labels
- connect a mailbox locally
- choose which connected mailboxes are active
- refresh active mailboxes locally

Codex is responsible for:

- interpreting the user's prompt,
- deciding what matters
- deciding which Gmail query to run
- deciding which threads deserve deeper inspection
- deciding whether a reply should be drafted
- writing the actual reply body
- deciding whether to archive, label, or leave untouched
- writing a readable run summary for the user

## Supported Orchestrated Capabilities

These are the built-in capabilities this skill should advertise and orchestrate.

1. Priority triage
   - rank threads into `urgent`, `high`, `normal`, `low`
   - explain why each important thread matters

2. Draft generation
   - draft replies for clear, low-risk threads
   - never send directly
   - prefer leaving a thread untouched over inventing a reply

3. Email session tracking
   - treat ongoing important threads as sessions
   - keep track of whether a session is waiting on the user, waiting on the other side, or has a draft ready
   - surface stale drafts when a newer message changes the situation
   - exclude clearly closed sessions from daily review unless the user explicitly asks for retrospective cleanup

4. Notification cleanup
   - archive or label low-value GitHub, npm, and similar notification threads
   - keep truly risky or decision-heavy mail visible

5. Daily review
   - summarize important progress, blocked sessions, and draft-ready threads
   - help the user scan Gmail and focus on the most useful drafts first

6. Vendor and account monitoring
   - surface usage, billing, security, password, OTP, and account-access messages
   - never auto-clean or auto-reply to sensitive security mail

7. Prompt-driven one-off tasks
   - user can still ask ad hoc things like "only inspect invoice mail" or "draft firm follow-ups"
   - Codex should adapt its query and actions to the request instead of forcing a fixed routine

## Capability Boundaries

This skill is designed to help the user stay on top of email without losing final control.

It is good at:

- inbox triage
- session tracking
- reply drafting
- low-risk cleanup
- daily or hourly review

It is not meant to:

- fully replace the user's judgment
- auto-send external communication
- silently apply hidden policies the user did not ask for
- assume engineering-specific cleanup rules for every user

## User Control Surface

This skill should always read:

```text
~/.codex/gmail-ai-daily-ops/gmail-ai-worker/runtime/skill_settings.json
```

That file is the user-facing activation surface. If the user wants to turn capabilities on or off, tighten risk tolerance, or change cleanup policy, Codex should update that file instead of baking hidden assumptions into the run.

If the file is missing, Codex should use the default policy described there and may recreate it.

The user may also edit `skill_settings.json` manually at any time. Codex should treat user edits as authoritative.

For mailbox connectivity, this skill should also manage:

```text
~/.codex/gmail-ai-daily-ops/gmail-ai-worker/runtime/mailboxes.json
```

That file tracks connected mailboxes and which ones are active by default.

For Codex's own bounded working memory, this skill may also overwrite:

```text
~/.codex/gmail-ai-daily-ops/gmail-ai-worker/runtime/latest_run_report.md
```

This file is for Codex's internal continuity only. It is not the primary user interface.

This skill should also prefer reading:

```text
~/.codex/gmail-ai-daily-ops/gmail-ai-worker/runtime/latest_refresh_cache.json
~/.codex/gmail-ai-daily-ops/gmail-ai-worker/runtime/latest_refresh_status.json
```

Those files are the preferred source of recent Gmail state during automation. They should be produced by a local short-lived refresh job, not by a long-running daemon.

This skill may also write:

```text
~/.codex/gmail-ai-daily-ops/gmail-ai-worker/runtime/latest_action_plan.json
~/.codex/gmail-ai-daily-ops/gmail-ai-worker/runtime/latest_apply_status.json
```

`latest_action_plan.json` is the structured handoff from Codex reasoning to the local Gmail apply job.
`latest_apply_status.json` is the latest local execution result after Gmail writes are attempted.

For user questions like:

- "今日活动进度"
- "今天进展如何"
- "今天做了什么"
- "有哪些 draft 准备好了"

this skill should first read:

```text
~/.codex/gmail-ai-daily-ops/gmail-ai-worker/runtime/daily_progress_YYYY-MM-DD.md
~/.codex/gmail-ai-daily-ops/gmail-ai-worker/runtime/latest_apply_status.json
~/.codex/gmail-ai-daily-ops/gmail-ai-worker/runtime/latest_refresh_status.json
```

and answer from those files before deciding whether any fresh Gmail read is needed.

## Proactive Configuration Prompting

This skill should proactively ask the user whether they want to adjust key settings in these situations:

1. the first meaningful time the skill is used,
2. when automation is being enabled,
3. when the observed inbox pattern suggests the defaults are not a good fit.

Ask briefly and concretely. Do not ask open-ended broad setup questions if a small set of knobs will do.

The main settings worth surfacing are:

- candidate scan breadth
- hourly recent query window
- daily review window
- whether low-value notification cleanup is enabled
- whether draft generation is enabled
- whether closed sessions should ever appear in review
- whether local refresh scheduling is already installed

Use recommended defaults first, but explicitly offer the user a chance to change them.

## Guardrails

- Never send email directly. Drafts only.
- Prefer reading a thread in detail before drafting.
- Treat billing, legal, HR, credentials, and ambiguous partner/customer asks as human-review-first.
- Avoid replying to notification-only mail unless the user explicitly wants that.
- If context is incomplete, stop at summary plus recommendation instead of inventing facts.

## Workspace

- Root: `~/.codex/gmail-ai-daily-ops/gmail-ai-worker`
- Runtime dir: `~/.codex/gmail-ai-daily-ops/gmail-ai-worker/runtime`
- Only persistent run artifact: `~/.codex/gmail-ai-daily-ops/gmail-ai-worker/runtime/latest_run_report.md`

## Primitive Commands

Always start in:

```bash
cd ~/.codex/gmail-ai-daily-ops/gmail-ai-worker
source .venv/bin/activate
```

Search threads with an arbitrary Gmail query:

```bash
python scripts/collect_thread_snapshot.py --query "<GMAIL_QUERY>"
```

If no query is given, the default inbox query is used.

Inspect one thread in detail:

```bash
python scripts/get_thread_detail.py --thread-id <THREAD_ID>
```

Create one Gmail draft from a plain-text body file:

```bash
python scripts/create_reply_draft.py --thread-id <THREAD_ID> --body "<plain text reply>"
```

Modify one thread:

Archive:

```bash
python scripts/modify_thread.py --thread-id <THREAD_ID> --archive
```

Apply labels:

```bash
python scripts/modify_thread.py --thread-id <THREAD_ID> --add-label "waiting-customer"
```

List labels:

```bash
python scripts/list_labels.py
```

Refresh all active mailboxes locally:

```bash
python scripts/refresh_active_mailboxes.py
```

Install the local macOS refresh scheduler:

```bash
python scripts/install_launchd_refresh.py
```

Apply the latest action plan locally:

```bash
python scripts/apply_action_plan.py
```

Connect a mailbox:

```bash
python scripts/connect_mailbox.py
```

List connected mailboxes:

```bash
python scripts/list_connected_mailboxes.py
```

Choose active mailboxes:

```bash
python scripts/set_active_mailboxes.py --mailbox <MAILBOX_KEY>
```

All Gmail primitives may also accept `--mailbox <MAILBOX_KEY>`. If omitted, the active mailbox is used automatically when there is exactly one active mailbox.

## How To Use This Skill

The user can give any mailbox-oriented goal in plain language. Codex should translate that goal into Gmail queries plus the minimum necessary actions.

Examples of valid user intents:

- "Look for anything I must reply to today and draft replies."
- "Only inspect emails about billing, invoices, or contracts."
- "Clean up GitHub noreply notifications and archive low-value ones."
- "Find English emails from real humans and prioritize them."
- "Draft short, polite follow-ups for anything waiting on the other side."
- "Do not change Gmail state, only tell me what matters."
- "Use a firmer tone for overdue follow-ups."
- "Connect another mailbox and include it in daily review."

If no explicit user prompt is provided during an automation run, Codex should fall back to the enabled capabilities in `skill_settings.json`.

If fresh local cache files exist, prefer them over live Gmail reads during automation. Only fall back to direct Gmail reads when:

- the user explicitly asks for a refresh now, or
- local refresh has not been installed yet.

## Intent Routing

Before doing work, classify the user's request into one of these modes:

1. `report-only`
2. `front-run`
3. `strategy-or-setup`
4. `mailbox-management`
5. `automation-maintenance`

### `report-only`

Use this when the user asks things like:

- `今日活动进度`
- `今天做了什么`
- `现在有哪些 draft`
- `最新报告`
- `今天有哪些 active sessions`

Behavior:

- do not trigger a fresh Gmail scan by default
- first read the latest local progress and status files
- answer directly from:

```text
~/.codex/gmail-ai-daily-ops/gmail-ai-worker/runtime/daily_progress_YYYY-MM-DD.md
~/.codex/gmail-ai-daily-ops/gmail-ai-worker/runtime/latest_apply_status.json
~/.codex/gmail-ai-daily-ops/gmail-ai-worker/runtime/latest_refresh_status.json
~/.codex/gmail-ai-daily-ops/gmail-ai-worker/runtime/latest_run_report.md
```

- only suggest a fresh refresh if the cached data is obviously stale or missing

### `front-run`

Use this when the user wants to manually run the workflow right now, for example:

- `现在跑一轮`
- `现在帮我扫描邮箱`
- `立即刷新并处理`
- `前台执行一遍`

Behavior:

- this is explicitly supported
- first run a local refresh:

```bash
cd ~/.codex/gmail-ai-daily-ops/gmail-ai-worker
source .venv/bin/activate
python scripts/refresh_active_mailboxes.py
```

- then reason over the fresh cache
- if Gmail mutations are needed, write `latest_action_plan.json`
- if the user wants the changes applied immediately, run:

```bash
python scripts/apply_action_plan.py
```

### `strategy-or-setup`

Use this when the user is asking:

- what the skill can do
- how to collaborate with it
- how to design automation
- how to configure defaults

Behavior:

- explain capabilities and boundaries
- propose settings changes
- do not perform Gmail mutations unless the user explicitly asks

### `mailbox-management`

Use this when the user wants to:

- connect a mailbox
- add another mailbox
- list mailboxes
- change active mailboxes

Behavior:

- use the mailbox-management commands
- do not run full triage unless the user also asks for it

### `automation-maintenance`

Use this when the user wants to:

- install or modify local refresh/apply schedulers
- change timing
- inspect whether background tasks are running

Behavior:

- focus on the local scheduler and worker state
- do not do full Gmail analysis unless requested

## Session Rules

For automation defaults, the skill should reason in terms of **active sessions**, not just raw message counts.

Treat a thread as likely active when it still has open coordination value, for example:

- someone is waiting for the user's reply
- the user is waiting for the other side and a follow-up may be needed
- a draft is ready but unsent
- there is unresolved project, billing, customer, vendor, or internal coordination context

Treat a thread as likely closed when it is clearly done, for example:

- GitHub merge / approval / push notifications with no human ask
- package publish success notices
- thank-you-only closures with no pending action
- resolved informational alerts with no follow-up path

Daily review should focus on active sessions only. Closed sessions may still be auto-cleaned if cleanup policy allows, but they should not dominate the review report.

## Operating Principle

Do not force the user into a fixed workflow. Instead:

1. Understand the user's goal and constraints.
2. Pick or construct the right Gmail query.
3. Read candidate threads.
4. Dive deeper only where needed.
5. Decide which Gmail changes should happen.
6. Write `latest_action_plan.json` whenever local Gmail writes should be performed.
7. Overwrite `latest_run_report.md` with the result of this run only.

When automated, the skill should also:

- maintain the user's ability to make final decisions,
- keep important threads visible,
- shift repetitive low-risk work onto Codex,
- and ensure the user primarily reviews Gmail drafts rather than hand-writing everything from scratch.
- scan broadly enough to rediscover older but still-active sessions that the user may have forgotten.
- prefer using the latest local refresh cache instead of asking Codex automation to perform live Gmail access in a restricted backend environment.

## Reporting Contract

At the end of each run, overwrite this file:

```text
~/.codex/gmail-ai-daily-ops/gmail-ai-worker/runtime/latest_run_report.md
```

The report is an internal Codex working note, not a user-facing destination.

The note must contain only the latest run and should include:

- the user goal for this run,
- the currently enabled capabilities,
- priority ordering,
- exactly what Gmail operations were performed,
- which threads were drafted, archived, labeled, or skipped,
- and any human-review items that remain.

Keep it bounded and compact:

- overwrite every run
- do not accumulate long historical logs
- keep only what Codex needs to maintain continuity into the next run

## Hourly Automation Behavior

When this skill is used from Codex automation, the automation prompt defines the task. Codex should not silently substitute a generic inbox routine unless the prompt asks for one.

Codex should:

- treat the automation prompt as the source of truth,
- or, if the automation prompt is generic, derive the task from `skill_settings.json`,
- prefer cache-consumption mode for Codex app automation,
- scan a broad candidate set first, then narrow by active-session reasoning,
- write `latest_action_plan.json` when drafts, archive operations, or labels should be applied locally,
- avoid relying on Codex automation itself for direct Gmail writes when a local apply job is available,
- prefer minimal safe actions,
- remove or overwrite temporary files it created during the run,
- always update `latest_run_report.md`.

## Preferred Output Style

In chat, always answer the user directly.

Do not tell the user to open the markdown report unless they explicitly ask for the underlying file.

Use the markdown note only as Codex's internal working memory between runs.
