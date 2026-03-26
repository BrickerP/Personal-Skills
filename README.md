# Gmail AI Daily Ops

Public source repository for the Gmail AI Daily Ops Codex skill and its local Gmail worker.

## Repository layout

- `skills/gmail-ai-daily-ops/SKILL.md`: the skill behavior and orchestration contract
- `tools/gmail-ai-worker/`: the local Gmail API worker used by the skill
- `docs/第一次使用文档.md`: a Chinese first-use guide

## Privacy boundary

This repository is intentionally sanitized for public sharing.

It does not include:

- Gmail tokens
- connected mailbox data
- Gmail OAuth client secrets
- refresh caches
- run reports
- daily progress history
- logs

The worker runtime directory only contains safe starter templates.

## Quick start

1. Clone this repository.
2. Open `tools/gmail-ai-worker`.
3. Place your own Google Desktop OAuth client JSON at `tools/gmail-ai-worker/runtime/oauth_client.json` locally.
4. Do not commit that OAuth client JSON or any generated runtime state.
5. Run `Start Gmail AI Ops.command` to install dependencies and connect the first mailbox.
6. Run `Install Gmail Refresh Scheduler.command` if you want the local refresh/apply jobs on macOS.

## Notes

- `tools/gmail-ai-worker/secrets/` is local-only.
- `tools/gmail-ai-worker/runtime/latest_*` and `tools/gmail-ai-worker/runtime/mailboxes.json` should be treated as local working state after setup.
- The committed runtime files are only starter placeholders for first-time setup.
- After local setup, treat changes under `tools/gmail-ai-worker/runtime/` as machine-local state.
