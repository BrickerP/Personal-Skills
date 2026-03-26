"""Set which connected mailboxes are active for automation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gmail_ai_worker.mailboxes import MailboxRegistry


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Set active connected mailboxes.")
    parser.add_argument("--mailbox", action="append", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    registry = MailboxRegistry()
    for mailbox_key in args.mailbox:
        if registry.find_mailbox(mailbox_key) is None:
            raise KeyError(f"Unknown mailbox key: {mailbox_key}")
    registry.set_active_mailboxes(args.mailbox)
    registry.save()
    print(json.dumps({"active_mailboxes": args.mailbox}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
