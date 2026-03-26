"""List locally connected Gmail mailboxes."""

from __future__ import annotations

import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gmail_ai_worker.mailboxes import MailboxRegistry


def main() -> int:
    """Print connected mailbox registry as JSON."""
    registry = MailboxRegistry()
    print(json.dumps(registry.data, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
