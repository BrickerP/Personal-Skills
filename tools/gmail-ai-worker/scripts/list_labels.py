"""List Gmail labels for the current mailbox."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gmail_ai_worker.config import WorkerConfig
from gmail_ai_worker.gmail_client import build_gmail_service, list_labels
from gmail_ai_worker.mailboxes import resolve_token_path


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    defaults = WorkerConfig.from_env()
    parser = argparse.ArgumentParser(description="List Gmail labels.")
    parser.add_argument("--token-path", default=str(defaults.token_path))
    parser.add_argument("--mailbox", default=None, help="Connected mailbox key.")
    return parser.parse_args()


def main() -> int:
    """Print Gmail labels as JSON."""
    args = parse_args()
    token_path = resolve_token_path(
        mailbox_key=args.mailbox,
        fallback_token_path=Path(args.token_path),
    )
    service = build_gmail_service(token_path)
    payload = {
        "labels": [
            {
                "id": label.get("id"),
                "name": label.get("name"),
                "type": label.get("type"),
                "messages_total": label.get("messagesTotal"),
                "messages_unread": label.get("messagesUnread"),
                "threads_total": label.get("threadsTotal"),
                "threads_unread": label.get("threadsUnread"),
            }
            for label in list_labels(service)
        ]
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
