"""Modify one Gmail thread with labels or archive semantics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gmail_ai_worker.config import WorkerConfig
from gmail_ai_worker.gmail_client import build_gmail_service, resolve_label_id
from gmail_ai_worker.mailboxes import resolve_token_path


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    defaults = WorkerConfig.from_env()
    parser = argparse.ArgumentParser(description="Modify one Gmail thread.")
    parser.add_argument("--thread-id", required=True)
    parser.add_argument("--add-label", action="append", default=[])
    parser.add_argument("--remove-label", action="append", default=[])
    parser.add_argument(
        "--archive",
        action="store_true",
        help="Archive by removing the INBOX label.",
    )
    parser.add_argument("--token-path", default=str(defaults.token_path))
    parser.add_argument("--mailbox", default=None, help="Connected mailbox key.")
    return parser.parse_args()


def main() -> int:
    """Modify the Gmail thread and print the API response."""
    args = parse_args()
    token_path = resolve_token_path(
        mailbox_key=args.mailbox,
        fallback_token_path=Path(args.token_path),
    )
    service = build_gmail_service(token_path)
    add_labels = [resolve_label_id(service, label) for label in args.add_label]
    remove_labels = [resolve_label_id(service, label) for label in args.remove_label]
    if args.archive and "INBOX" not in remove_labels:
        remove_labels.append("INBOX")
    response = (
        service.users()
        .threads()
        .modify(
            userId="me",
            id=args.thread_id,
            body={
                "addLabelIds": add_labels,
                "removeLabelIds": remove_labels,
            },
        )
        .execute()
    )
    result = {
        "thread_id": args.thread_id,
        "added_labels": add_labels,
        "removed_labels": remove_labels,
        "response": response,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
