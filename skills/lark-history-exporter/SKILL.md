---
name: lark-history-exporter
description: Export visible Lark/Feishu IM chat history from the official lark-cli into local Markdown files, with managed raw JSON checkpoints and downloaded message resources. Use when the user asks to back up, archive, save, download, or convert Lark/Feishu chat history, group chats, p2p/direct messages, message resources, or "only final MDs" into the local filesystem.
---

# Lark History Exporter

## Goal

Export Lark/Feishu chats through the official `lark-cli` IM APIs, keep raw API pages and resources managed inside an export directory, and show the user only the final Markdown files unless troubleshooting is required.

Do not scrape the Mac app cache as the primary path. The local app stores may be encrypted or implementation-private. Prefer official OpenAPI access through `lark-cli`.

## Default Output

Use `~/assets/lark-export` unless the user asks for another directory.

Final user-facing files:

```text
<output>/md/index.md
<output>/md/chats/*.md
```

Managed internal files:

```text
<output>/
  raw/chats.json
  raw/chat_pages.json
  raw/messages/<chat-id>.jsonl
  lark-im-resources/
  logs/
  export_state.json
```

Do not expose raw chat names, ids, or message content in progress updates. Report aggregate counts and final paths.

## Full Workflow

1. Check local CLI/auth state:
   ```bash
   python3 ~/.codex/skills/lark-history-exporter/scripts/export_lark_history.py doctor
   ```
2. If config is missing, initialize the Lark profile:
   ```bash
   npx -y @larksuite/cli@latest config init --new --brand lark
   ```
3. If auth is missing or scopes are incomplete, start device auth:
   ```bash
   npx -y @larksuite/cli@latest auth login \
     --scope "im:chat:read im:message:readonly im:message.reactions:read im:message.group_msg:get_as_user im:message.p2p_msg:get_as_user contact:user.base:readonly" \
     --no-wait --json
   ```
   Give the user the verification URL and user code. After the user completes browser authorization, finish with:
   ```bash
   npx -y @larksuite/cli@latest auth login --device-code <device_code>
   ```
   Auth is credential-gated; do not claim export completion until the user has authorized and the CLI reports success.
3. Run a small sample first:
   ```bash
   python3 ~/.codex/skills/lark-history-exporter/scripts/export_lark_history.py export \
     --output ~/assets/lark-export \
     --types group \
     --limit-chats 1 \
     --start 2026-01-01
   ```
4. Run the real export with the requested chat kind/filter:
   ```bash
   mkdir -p ~/assets/lark-export/logs
   python3 ~/.codex/skills/lark-history-exporter/scripts/export_lark_history.py export \
     --output ~/assets/lark-export \
     --types p2p,group \
     --continue-on-error \
     --cli-timeout 120 \
     --message-page-retries 5 \
     --no-download-resources \
     --no-reactions \
     > ~/assets/lark-export/logs/export.stdout.log \
     2> ~/assets/lark-export/logs/export.stderr.log
   ```
5. If `export_state.json` shows failed chats, retry only the failed chats:
   ```bash
   python3 ~/.codex/skills/lark-history-exporter/scripts/export_lark_history.py retry-failed \
     --output ~/assets/lark-export \
     --continue-on-error \
     --cli-timeout 120 \
     --message-page-retries 5 \
     --no-download-resources \
     --no-reactions \
     > ~/assets/lark-export/logs/retry_failed.stdout.log \
     2> ~/assets/lark-export/logs/retry_failed.stderr.log
   ```
6. Verify completion:
   ```bash
   python3 - <<'PY'
   import json
   from pathlib import Path
   base = Path.home() / "assets" / "lark-export"
   state = json.loads((base / "export_state.json").read_text())
   chats = state.get("chats", [])
   md_chats = list((base / "md" / "chats").glob("*.md"))
   print({
       "selected_chats": state.get("selected_chats"),
       "processed": len(chats),
       "ok": sum(1 for c in chats if c.get("ok")),
       "failed": sum(1 for c in chats if c.get("ok") is False),
       "messages_total": sum(int(c.get("messages") or 0) for c in chats if c.get("ok")),
       "md_index_exists": (base / "md" / "index.md").exists(),
       "md_chat_files": len(md_chats),
   })
   PY
   ```
7. Report only the final Markdown paths and aggregate counts:
   - `<output>/md/index.md`
   - `<output>/md/chats/`

## Chat Selection

Use the smallest filter that matches the user's request:

- `--types group` for groups only.
- `--types p2p` for direct messages only; requires `--as user`.
- `--types p2p,group` for all user-visible conversations.
- `--include-chat-regex` and `--exclude-chat-regex` for name-based subsets.
- `--exclude-muted` to skip muted chats under user identity.
- `--limit-chats N` only for samples or debugging.

The exporter writes one Markdown file per selected chat and groups the index by `chat_mode`.

To regenerate Markdown without calling Lark again:

```bash
python3 ~/.codex/skills/lark-history-exporter/scripts/render_lark_markdown.py \
  --output ~/assets/lark-export
```

## Permissions And Identity

Use `--as user` for the user's own visible history. Bot identity cannot enumerate p2p chats and only sees chats/resources visible to the bot.

Required scopes for full user-visible chat history export are:

```text
im:chat:read im:message:readonly im:message.reactions:read im:message.group_msg:get_as_user im:message.p2p_msg:get_as_user contact:user.base:readonly
```

The base read scopes authorize chat listing, while `group_msg` / `p2p_msg` authorize message-history reads and `contact:user.base:readonly` lets the CLI resolve sender names.

If the user does not want reactions, pass `--no-reactions`; the exporter may still keep `im:message.reactions:read` in the preflight scope list because it is harmless and avoids partial enrichment failures.

For narrower troubleshooting, the base chat-list scopes are:

```text
im:chat:read im:message:readonly
```

If resources must be downloaded, keep `--download-resources`; the CLI saves resources under `lark-im-resources/` relative to the export directory.

## Troubleshooting

- Repeated authorization prompts usually mean the verification URL/user code/device code are from different auth attempts. Restart `auth login --no-wait --json`, use only the newest verification URL, then finish with the matching `device_code`.
- `required scopes are missing` means the current token lacks one of the required scopes. Run device auth again with the full scope string above.
- `network timeout` on `im +chat-messages-list` is usually transient. Let the export finish with `--continue-on-error`, then run `retry-failed`.
- If final Markdown is missing but raw files exist, run `render_lark_markdown.py --output <output>`.
- For exact `lark-cli` command shapes and scope notes, read `references/lark-cli-im.md`.

## Scripts

- `scripts/export_lark_history.py`: checks auth, lists chats, paginates messages, downloads resources, writes raw checkpoints, and renders Markdown.
- `scripts/render_lark_markdown.py`: rebuilds Markdown from existing raw checkpoints.
- `references/lark-cli-im.md`: concise command/scopes reference captured from the installed CLI behavior.

## Completion Standard

Before saying the export is done:

- Confirm the exporter exited successfully.
- Confirm `md/index.md` exists.
- Confirm at least the expected selected chat Markdown files exist.
- Mention auth/permission gaps explicitly if the run stopped before export.
