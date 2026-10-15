#!/usr/bin/env python3
"""Render Lark history Markdown from raw exporter checkpoints."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any


def sanitize_filename(value: str, fallback: str = "chat") -> str:
    value = re.sub(r"[\\/:*?\"<>|\x00-\x1f]+", "-", value).strip()
    value = re.sub(r"\s+", " ", value)
    value = value.strip(". ")
    return (value[:100] or fallback)


def parse_json_maybe(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text or text[0] not in "[{":
        return value
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return value


def extract_text_from_post(node: Any) -> str:
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        parts = [extract_text_from_post(item) for item in node]
        return "".join(part for part in parts if part)
    if isinstance(node, dict):
        tag = node.get("tag")
        if "text" in node:
            return str(node.get("text") or "")
        if "name" in node and tag in {"at", "mention"}:
            return "@" + str(node.get("name") or "")
        if "href" in node and "text" in node:
            return f"[{node.get('text')}]({node.get('href')})"
        children = node.get("children") or node.get("content")
        text = extract_text_from_post(children)
        if tag in {"p", "div"} and text:
            return text + "\n"
        return text
    return str(node)


def markdown_escape_table(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def timestamp_to_text(value: Any) -> str:
    if value in (None, ""):
        return ""
    raw = str(value)
    try:
        number = int(float(raw))
    except ValueError:
        return raw
    if number > 10_000_000_000:
        number = number // 1000
    try:
        return dt.datetime.fromtimestamp(number).astimezone().isoformat(timespec="seconds")
    except (OverflowError, OSError, ValueError):
        return raw


def sender_name(message: dict[str, Any]) -> str:
    sender = message.get("sender") or message.get("from") or {}
    if isinstance(sender, dict):
        for key in ("name", "sender_name", "display_name", "id", "sender_id", "open_id"):
            if sender.get(key):
                return str(sender[key])
    return str(sender or "unknown")


def message_content(message: dict[str, Any]) -> str:
    msg_type = str(message.get("msg_type") or message.get("message_type") or "message")
    content = parse_json_maybe(message.get("content", ""))

    if message.get("deleted") is True:
        return "[deleted]"

    if isinstance(content, dict):
        if msg_type == "text":
            return str(content.get("text") or content.get("content") or "")
        if msg_type == "post":
            title = content.get("title")
            body = extract_text_from_post(content.get("content"))
            return "\n".join(part for part in (str(title or ""), body.strip()) if part)
        if msg_type == "image":
            key = content.get("image_key") or content.get("key") or content.get("file_key")
            return f"![Image]({key})" if key else "[image]"
        if msg_type in {"file", "audio", "video", "media"}:
            name = content.get("file_name") or content.get("name") or content.get("title") or msg_type
            key = content.get("file_key") or content.get("key")
            return f"[{msg_type}: {name} {key or ''}]".strip()
        if msg_type == "interactive":
            return "```json\n" + json.dumps(content, ensure_ascii=False, indent=2) + "\n```"
        for key in ("text", "content", "title"):
            if content.get(key):
                return str(content[key])
        return "```json\n" + json.dumps(content, ensure_ascii=False, indent=2) + "\n```"

    if isinstance(content, list):
        return extract_text_from_post(content).strip()

    return str(content or "")


def resource_links(message: dict[str, Any], chat_md_path: Path, output_dir: Path) -> list[str]:
    links: list[str] = []
    for resource in message.get("resources") or []:
        if not isinstance(resource, dict):
            continue
        local_path = resource.get("local_path")
        if not local_path:
            continue
        target = output_dir / str(local_path)
        try:
            rel = os.path.relpath(target, chat_md_path.parent)
        except ValueError:
            rel = str(target)
        label = resource.get("type") or resource.get("key") or "resource"
        links.append(f"[{label}]({rel})")
    return links


def extract_chats(raw_chats: Any) -> list[dict[str, Any]]:
    if isinstance(raw_chats, list):
        return [item for item in raw_chats if isinstance(item, dict)]
    if not isinstance(raw_chats, dict):
        return []
    candidates = [
        raw_chats.get("chats"),
        raw_chats.get("items"),
        raw_chats.get("data", {}).get("chats") if isinstance(raw_chats.get("data"), dict) else None,
        raw_chats.get("data", {}).get("items") if isinstance(raw_chats.get("data"), dict) else None,
    ]
    for candidate in candidates:
        if isinstance(candidate, list):
            return [item for item in candidate if isinstance(item, dict)]
    return []


def extract_messages(page: Any) -> list[dict[str, Any]]:
    if not isinstance(page, dict):
        return []
    data = page.get("data") if isinstance(page.get("data"), dict) else page
    for key in ("messages", "items"):
        value = data.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def chat_id(chat: dict[str, Any]) -> str:
    return str(chat.get("chat_id") or chat.get("id") or "unknown-chat")


def chat_name(chat: dict[str, Any]) -> str:
    return str(chat.get("name") or chat.get("chat_name") or chat_id(chat))


def chat_mode(chat: dict[str, Any]) -> str:
    return str(chat.get("chat_mode") or chat.get("type") or "unknown")


def render_chat(chat: dict[str, Any], messages: list[dict[str, Any]], output_dir: Path) -> Path:
    md_dir = output_dir / "md" / "chats"
    md_dir.mkdir(parents=True, exist_ok=True)
    cid = chat_id(chat)
    filename = f"{sanitize_filename(chat_name(chat))}--{cid}.md"
    path = md_dir / filename

    lines = [
        f"# {chat_name(chat)}",
        "",
        f"- Chat ID: `{cid}`",
        f"- Chat mode: `{chat_mode(chat)}`",
        f"- Messages: `{len(messages)}`",
        f"- Rendered at: `{dt.datetime.now().astimezone().isoformat(timespec='seconds')}`",
        "",
        "## Messages",
        "",
    ]

    for message in sorted(messages, key=lambda item: str(item.get("create_time") or "")):
        mid = str(message.get("message_id") or "")
        time_text = timestamp_to_text(message.get("create_time"))
        sender = sender_name(message)
        body = message_content(message).strip()
        if message.get("updated") is True and message.get("update_time"):
            body += f"\n\n_edited {timestamp_to_text(message.get('update_time'))}_"
        links = resource_links(message, path, output_dir)
        if links:
            body += "\n\nResources: " + ", ".join(links)
        thread_id = message.get("thread_id")
        if thread_id:
            body += f"\n\nThread: `{thread_id}`"

        lines.extend([
            f"### {time_text or 'unknown time'} - {sender}",
            "",
            body or f"[{message.get('msg_type') or 'message'}]",
            "",
        ])
        if mid:
            lines.extend([f"`{mid}`", ""])

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def load_messages(raw_path: Path) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    if not raw_path.exists():
        return messages
    with raw_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            page = json.loads(line)
            messages.extend(extract_messages(page))
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for message in messages:
        mid = str(message.get("message_id") or id(message))
        if mid in seen:
            continue
        seen.add(mid)
        unique.append(message)
    return unique


def render_index(chats: list[dict[str, Any]], paths: dict[str, Path], counts: dict[str, int], output_dir: Path) -> Path:
    index_path = output_dir / "md" / "index.md"
    index_path.parent.mkdir(parents=True, exist_ok=True)

    by_mode: dict[str, list[dict[str, Any]]] = {}
    for chat in chats:
        by_mode.setdefault(chat_mode(chat), []).append(chat)

    lines = [
        "# Lark Chat History Export",
        "",
        f"Rendered at `{dt.datetime.now().astimezone().isoformat(timespec='seconds')}`.",
        "",
    ]

    for mode in sorted(by_mode):
        lines.extend([f"## {mode}", "", "| Chat | Messages | Chat ID |", "|---|---:|---|"])
        for chat in sorted(by_mode[mode], key=lambda item: chat_name(item).lower()):
            cid = chat_id(chat)
            path = paths.get(cid)
            if path:
                rel = os.path.relpath(path, index_path.parent)
                title = f"[{markdown_escape_table(chat_name(chat))}]({rel})"
            else:
                title = markdown_escape_table(chat_name(chat))
            lines.append(f"| {title} | {counts.get(cid, 0)} | `{cid}` |")
        lines.append("")

    index_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return index_path


def render_output(output_dir: Path) -> tuple[Path, list[Path]]:
    chats_file = output_dir / "raw" / "chats.json"
    if not chats_file.exists():
        raise FileNotFoundError(f"missing {chats_file}")

    raw_chats = json.loads(chats_file.read_text(encoding="utf-8"))
    chats = extract_chats(raw_chats)
    paths: dict[str, Path] = {}
    counts: dict[str, int] = {}

    for chat in chats:
        cid = chat_id(chat)
        messages = load_messages(output_dir / "raw" / "messages" / f"{cid}.jsonl")
        paths[cid] = render_chat(chat, messages, output_dir)
        counts[cid] = len(messages)

    index = render_index(chats, paths, counts, output_dir)
    return index, list(paths.values())


def write_self_test_fixture(output_dir: Path) -> None:
    raw_dir = output_dir / "raw" / "messages"
    raw_dir.mkdir(parents=True, exist_ok=True)
    chats = [
        {
            "chat_id": "oc_sample",
            "name": "Sample Group",
            "chat_mode": "group",
        }
    ]
    (output_dir / "raw" / "chats.json").write_text(json.dumps(chats), encoding="utf-8")
    page = {
        "data": {
            "messages": [
                {
                    "message_id": "om_sample",
                    "msg_type": "text",
                    "create_time": "1760000000000",
                    "sender": {"name": "Alice"},
                    "content": json.dumps({"text": "hello from Lark"}, ensure_ascii=False),
                }
            ]
        }
    }
    (raw_dir / "oc_sample.jsonl").write_text(json.dumps(page, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Export directory containing raw/chats.json")
    parser.add_argument("--self-test", action="store_true", help="Render a temporary fixture and validate output")
    args = parser.parse_args()

    if args.self_test:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            write_self_test_fixture(out)
            index, chats = render_output(out)
            assert index.exists(), index
            assert chats and chats[0].exists(), chats
            print(index)
            print(chats[0])
        return 0

    if not args.output:
        parser.error("--output is required unless --self-test is used")
    index, chats = render_output(args.output.expanduser().resolve())
    print(f"index: {index}")
    print(f"chat_markdown_files: {len(chats)}")
    for path in chats:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
