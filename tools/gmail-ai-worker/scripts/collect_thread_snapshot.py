"""Collect Gmail thread context for Codex-driven inbox triage."""

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
    collect_snapshot_bundle,
    get_profile_email,
    write_json,
)
from gmail_ai_worker.mailboxes import resolve_token_path


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for snapshot collection."""
    defaults = WorkerConfig.from_env()
    parser = argparse.ArgumentParser(
        description="Collect a Gmail inbox snapshot for Codex triage."
    )
    parser.add_argument("--query", default=defaults.gmail_query)
    parser.add_argument("--max-threads", type=int, default=defaults.max_threads)
    parser.add_argument(
        "--messages-per-thread",
        type=int,
        default=defaults.messages_per_thread,
    )
    parser.add_argument("--excerpt-chars", type=int, default=defaults.excerpt_chars)
    parser.add_argument("--output", default=None)
    parser.add_argument("--token-path", default=str(defaults.token_path))
    parser.add_argument("--mailbox", default=None, help="Connected mailbox key.")
    return parser.parse_args()


def main() -> int:
    """Collect and print the latest inbox snapshot."""
    args = parse_args()
    config = WorkerConfig.from_env()
    config.ensure_runtime_directories()
    token_path = resolve_token_path(
        mailbox_key=args.mailbox,
        fallback_token_path=Path(args.token_path),
    )
    service = build_gmail_service(token_path)
    self_email = get_profile_email(service)
    bundle = collect_snapshot_bundle(
        service,
        self_email=self_email,
        query=args.query,
        max_threads=args.max_threads,
        messages_per_thread=args.messages_per_thread,
        excerpt_chars=args.excerpt_chars,
    )
    if args.output:
        write_json(Path(args.output).expanduser(), bundle)
    print(json.dumps(bundle, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
