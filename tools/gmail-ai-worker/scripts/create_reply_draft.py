"""Create one Gmail reply draft for a specific thread."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gmail_ai_worker.config import WorkerConfig
from gmail_ai_worker.gmail_client import (
    build_gmail_service,
    build_thread_snapshot,
    create_reply_draft,
    get_profile_email,
)
from gmail_ai_worker.mailboxes import resolve_token_path


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    defaults = WorkerConfig.from_env()
    parser = argparse.ArgumentParser(description="Create one Gmail reply draft.")
    parser.add_argument("--thread-id", required=True)
    body_group = parser.add_mutually_exclusive_group(required=True)
    body_group.add_argument("--body-file")
    body_group.add_argument("--body")
    parser.add_argument("--subject", default=None)
    parser.add_argument("--to", action="append", default=[])
    parser.add_argument("--cc", action="append", default=[])
    parser.add_argument("--token-path", default=str(defaults.token_path))
    parser.add_argument("--mailbox", default=None, help="Connected mailbox key.")
    return parser.parse_args()


def main() -> int:
    """Create a reply draft and persist a concise result artifact."""
    args = parse_args()
    config = WorkerConfig.from_env()
    config.ensure_runtime_directories()
    token_path = resolve_token_path(
        mailbox_key=args.mailbox,
        fallback_token_path=Path(args.token_path),
    )
    service = build_gmail_service(token_path)
    self_email = get_profile_email(service)
    snapshot = build_thread_snapshot(
        service,
        args.thread_id,
        self_email=self_email,
        messages_per_thread=config.messages_per_thread,
        excerpt_chars=config.excerpt_chars,
    )
    if args.body is not None:
        body_text = args.body
    else:
        body_text = Path(args.body_file).expanduser().read_text(encoding="utf-8")
    to = args.to or snapshot.default_reply_to
    cc = args.cc or []
    draft = create_reply_draft(
        service,
        thread_id=args.thread_id,
        subject=args.subject or snapshot.subject,
        body_text=body_text,
        to=to,
        cc=cc,
        reference_message_id=snapshot.reference_message_id,
    )
    result = {
        "thread_id": args.thread_id,
        "subject": args.subject or snapshot.subject,
        "to": to,
        "cc": cc,
        "draft_id": draft.get("id"),
        "latest_message_id": snapshot.latest_message_id,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
