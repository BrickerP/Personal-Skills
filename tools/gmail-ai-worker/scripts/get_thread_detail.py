"""Fetch one Gmail thread with full detail for Codex to inspect."""

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
    get_profile_email,
    write_json,
)
from gmail_ai_worker.mailboxes import resolve_token_path


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    defaults = WorkerConfig.from_env()
    parser = argparse.ArgumentParser(description="Fetch one Gmail thread in detail.")
    parser.add_argument("--thread-id", required=True)
    parser.add_argument("--output", default=None)
    parser.add_argument("--token-path", default=str(defaults.token_path))
    parser.add_argument("--mailbox", default=None, help="Connected mailbox key.")
    parser.add_argument(
        "--messages-per-thread",
        type=int,
        default=defaults.messages_per_thread,
    )
    parser.add_argument("--excerpt-chars", type=int, default=defaults.excerpt_chars)
    return parser.parse_args()


def main() -> int:
    """Fetch, print, and optionally save a single thread snapshot."""
    args = parse_args()
    config = WorkerConfig.from_env()
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
        messages_per_thread=args.messages_per_thread,
        excerpt_chars=args.excerpt_chars,
    )
    payload = snapshot.to_dict()
    if args.output:
        write_json(Path(args.output).expanduser(), payload)
        print(f"Saved thread detail: {args.output}")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
