# Gmail AI Worker

Local Gmail API primitives for a prompt-driven Codex Gmail skill. Gmail API is only the read/write channel. Codex interprets the user's goal, reads `runtime/skill_settings.json`, and decides what to do.

## Simplest Local Setup

For the easiest local setup:

1. clone this repository
2. place your own Desktop OAuth client JSON at `runtime/oauth_client.json` locally
3. tell the user to double-click:

```text
Start Gmail AI Ops.command
```

That launcher creates the virtual environment if needed, installs dependencies, and walks the user through the first mailbox connection.

## Recommended Architecture

Use two layers:

1. a local short-lived refresh job that talks to Gmail directly and exits
2. Codex skill / automation runs that read the latest local cache, reason over it, and write a structured action plan
3. a local short-lived apply job that reads the latest action plan and performs Gmail writes

Do not rely on Codex app automation to perform every live Gmail API call. Background automation environments may have network or filesystem restrictions.

## Step 1: Create a virtual environment

```bash
cd <worker-root>
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Step 2: Exchange Desktop OAuth credentials for a refresh token

Advanced / manual path only. Most users should use:

```text
Start Gmail AI Ops.command
```

```bash
python scripts/oauth_bootstrap.py \
  --client-secrets <path-to-desktop-oauth-client-json>
```

This opens a browser window, asks the signed-in Google account to approve Gmail access, and stores the resulting token JSON at `tools/gmail-ai-worker/secrets/gmail_token.json`.

If the browser ends on a blank localhost page and the script does not finish, use manual mode:

```bash
python scripts/oauth_bootstrap.py \
  --mode manual \
  --client-secrets <path-to-desktop-oauth-client-json>
```

After approval, copy the full redirected `http://localhost/...` URL from the browser address bar and paste it into the terminal.

## Step 2.5: Connect a mailbox for regular use

```bash
python scripts/connect_mailbox.py
```

This stores the mailbox token locally and registers the mailbox under `runtime/mailboxes.json`.

List connected mailboxes:

```bash
python scripts/list_connected_mailboxes.py
```

Choose which mailbox is active by default:

```bash
python scripts/set_active_mailboxes.py --mailbox <MAILBOX_KEY>
```

## Step 2.6: Install local periodic Gmail refresh

For the most stable setup on macOS:

```text
Install Gmail Refresh Scheduler.command
```

or:

```bash
python scripts/install_launchd_refresh.py
```

This installs two `launchd` jobs:

- a refresh job that wakes up periodically, refreshes active mailboxes, writes `runtime/latest_refresh_cache.json`, then exits
- an apply job that wakes up periodically, reads `runtime/latest_action_plan.json`, performs Gmail draft/archive/label actions, then exits

Neither job stays resident in memory.

## Step 3: Keep the token file private

- Do not commit anything under `tools/gmail-ai-worker/secrets/`.
- Rotate the token if it is ever copied into chat, docs, or logs.

## Step 4: Run a Gmail read smoke test

```bash
python scripts/gmail_smoke_test.py
```

This refreshes the saved token if needed, reads your Gmail profile, and lists a few inbox threads from the last day without writing anything back.

## Step 5: Search candidate threads

```bash
python scripts/collect_thread_snapshot.py --query "label:inbox newer_than:2d"
```

This prints JSON to stdout. It does not create a persistent log unless you explicitly redirect the output somewhere.

## Step 5.1: Refresh active mailboxes now

```bash
python scripts/refresh_active_mailboxes.py
```

This is the one-shot local Gmail fetch job. It writes:

- `runtime/latest_refresh_cache.json`
- `runtime/latest_refresh_status.json`

and then exits.

## Step 5.2: Apply the latest action plan now

```bash
python scripts/apply_action_plan.py
```

This is the one-shot local Gmail write job. It reads `runtime/latest_action_plan.json`, applies pending actions, writes:

- `runtime/latest_apply_status.json`
- `runtime/daily_progress_YYYY-MM-DD.md`

and then exits.

## Step 5.5: Review active skill settings

```bash
open <worker-root>/runtime/skill_settings.json
```

This file defines which orchestrated capabilities are active by default.
It also defines the broad scan window for automation runs and the rule that daily review should focus on active sessions rather than closed threads.

## Step 6: Inspect one thread in detail

```bash
python scripts/get_thread_detail.py --thread-id <THREAD_ID>
```

Use this after reviewing the candidate snapshot. Codex should inspect important threads one by one before deciding to act.

## Step 7: Create one Gmail reply draft

```bash
python scripts/create_reply_draft.py --thread-id <THREAD_ID> --body "Plain-text reply"
```

This creates exactly one Gmail draft. It does not send mail and does not write a result file by default.

## Step 8: Modify one thread

Archive:

```bash
python scripts/modify_thread.py --thread-id <THREAD_ID> --archive
```

Add a label:

```bash
python scripts/modify_thread.py --thread-id <THREAD_ID> --add-label IMPORTANT
```

List labels:

```bash
python scripts/list_labels.py
```

All mailbox-facing commands support `--mailbox <MAILBOX_KEY>`. If there is exactly one active connected mailbox, that mailbox is used automatically.

## Internal Continuity Note

This workflow may overwrite:

```bash
<worker-root>/runtime/latest_run_report.md
```

That file is for Codex's working continuity between runs. Users are expected to interact with Codex in chat, not by manually reading the file.

The preferred automation data source is:

```bash
<worker-root>/runtime/latest_refresh_cache.json
```

The preferred local Gmail write handoff is:

```bash
<worker-root>/runtime/latest_action_plan.json
```

## Notes

- Default scope is `https://www.googleapis.com/auth/gmail.modify`.
- The script forces `access_type=offline` and `prompt=consent` so Google returns a refresh token for scheduled runs.
- If Google does not return a refresh token, revoke the prior app grant for the account and run the bootstrap again.
- Default Gmail query is:
  `label:inbox newer_than:2d -category:promotions -category:social -in:drafts -in:sent`
- `create_reply_draft.py` creates one draft at a time so Codex stays in control of the exact reply content.
- The recommended usage is: Codex reads stdout, decides in real time, answers the user in chat, and may overwrite `runtime/latest_run_report.md` as a compact working note.
- `modify_thread.py` accepts label names, not just Gmail label ids. Missing user labels are created automatically when added.
- `runtime/skill_settings.json` is the supported place to activate or deactivate orchestrated capabilities and automation defaults.
- `runtime/mailboxes.json` is the supported place to track connected mailboxes and default active mailbox selection.
- `max_candidate_threads_scan` means scan breadth, not "the only threads worth reviewing." Codex should scan broadly, then focus the report on active sessions.
- `refresh_active_mailboxes.py` is a short-lived fetch job, not a daemon. It should be launched by `launchd` or manually, then exit.
- `apply_action_plan.py` is also a short-lived job. It performs Gmail draft/archive/label writes locally based on Codex's latest structured plan.
