# Lark CLI IM Export Reference

Use `npx -y @larksuite/cli@latest` unless `lark-cli` is already on PATH.

## Auth

Check state:

```bash
npx -y @larksuite/cli@latest auth status --json
```

Initialize config when missing:

```bash
npx -y @larksuite/cli@latest config init --new --brand lark
```

Authorize user IM scopes:

```bash
npx -y @larksuite/cli@latest auth login \
  --scope "im:chat:read im:message:readonly im:message.reactions:read im:message.group_msg:get_as_user im:message.p2p_msg:get_as_user contact:user.base:readonly" \
  --no-wait --json
```

Then finish with:

```bash
npx -y @larksuite/cli@latest auth login --device-code <device_code>
```

## List Chats

```bash
npx -y @larksuite/cli@latest im +chat-list \
  --as user \
  --types p2p,group \
  --sort active_time \
  --page-size 100 \
  --format json
```

`p2p` requires user identity. Bot identity can list groups only.

## List Messages

```bash
npx -y @larksuite/cli@latest im +chat-messages-list \
  --as user \
  --chat-id oc_xxx \
  --start 2020-01-01 \
  --end 2026-06-21 \
  --order asc \
  --page-size 50 \
  --download-resources \
  --format json
```

Pagination uses `has_more` and `page_token`. The maximum message page size is 50.

For a Markdown-first run, omit resource and reaction enrichment:

```bash
python3 ~/.codex/skills/lark-history-exporter/scripts/export_lark_history.py export \
  --output ~/assets/lark-export \
  --types p2p,group \
  --continue-on-error \
  --cli-timeout 120 \
  --message-page-retries 5 \
  --no-download-resources \
  --no-reactions
```

Retry failed chats only:

```bash
python3 ~/.codex/skills/lark-history-exporter/scripts/export_lark_history.py retry-failed \
  --output ~/assets/lark-export \
  --continue-on-error \
  --cli-timeout 120 \
  --message-page-retries 5 \
  --no-download-resources \
  --no-reactions
```

## Useful Scopes

- `im:chat:read`: list/read chat metadata.
- `im:message:readonly`: read message history and resources.
- `im:message.reactions:read`: reaction enrichment when not using `--no-reactions`.
- `im:message.group_msg:get_as_user`: read group message history as the user.
- `im:message.p2p_msg:get_as_user`: read p2p/direct message history as the user.
- `contact:user.base:readonly`: resolve sender/contact names.
