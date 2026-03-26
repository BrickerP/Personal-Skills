"""Friendly first-run entrypoint for non-technical users."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gmail_ai_worker.config import PACKAGE_ROOT
from gmail_ai_worker.mailboxes import MailboxRegistry


def _run_connect_mailbox() -> int:
    """Launch the mailbox connection flow."""
    command = [sys.executable, str(PROJECT_ROOT / "scripts" / "connect_mailbox.py")]
    return subprocess.call(command, cwd=str(PROJECT_ROOT))


def main() -> int:
    """Guide the user through the simplest possible first-run flow."""
    registry = MailboxRegistry()
    client_secrets_path = registry.get_client_secrets_path()

    print("Gmail AI Daily Ops")
    print()

    if not client_secrets_path.exists():
        print("This package is missing the Gmail OAuth client file.")
        print("Expected path:")
        print(f"  {client_secrets_path}")
        print()
        print("Place your own Desktop OAuth client JSON at that path")
        print("and then run this launcher again.")
        return 1

    connected = registry.list_mailboxes()
    if not connected:
        print("No mailbox is connected yet.")
        print("A browser window will open so you can sign in to Gmail once.")
        print()
        exit_code = _run_connect_mailbox()
        if exit_code != 0:
            print()
            print("Mailbox connection did not finish successfully.")
            return exit_code
        registry = MailboxRegistry()
        connected = registry.list_mailboxes()

    print("Connected mailboxes:")
    for mailbox in connected:
        marker = (
            "*"
            if mailbox["key"] in registry.data.get("active_mailboxes", [])
            else "-"
        )
        print(f"{marker} {mailbox['label']} ({mailbox['email']})")

    print()
    print("This package is ready to use.")
    print("You can now ask Codex things like:")
    print('- "Look for anything I should reply to today."')
    print('- "Draft replies for important emails but do not send them."')
    print('- "Clean up low-value notifications if I have enabled that policy."')
    print()
    print("Your mailbox configuration is stored locally in:")
    print(f"  {PACKAGE_ROOT / 'runtime' / 'mailboxes.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
