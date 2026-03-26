"""Connect a mailbox and register it for the local Gmail skill."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gmail_ai_worker.gmail_client import build_gmail_service, get_profile_email
from gmail_ai_worker.mailboxes import MailboxRegistry
from gmail_ai_worker.oauth_flow import DEFAULT_SCOPE, run_oauth_flow


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Connect a Gmail mailbox locally.")
    parser.add_argument("--label", default=None, help="User-facing mailbox label.")
    parser.add_argument("--mailbox-key", default=None, help="Stable mailbox key.")
    parser.add_argument(
        "--client-secrets",
        default=None,
        help="Override the Desktop OAuth client JSON path.",
    )
    parser.add_argument(
        "--mode",
        choices=("localserver", "manual"),
        default="localserver",
        help="Authorization mode.",
    )
    parser.add_argument(
        "--scope",
        dest="scopes",
        action="append",
        default=None,
        help=f"OAuth scope to request. Defaults to {DEFAULT_SCOPE}.",
    )
    return parser.parse_args()


def main() -> int:
    """Run OAuth, register the mailbox, and print the registry record."""
    args = parse_args()
    registry = MailboxRegistry()
    if args.client_secrets:
        registry.set_client_secrets_path(Path(args.client_secrets).expanduser())
        registry.save()

    client_secrets_path = registry.get_client_secrets_path()
    scopes = args.scopes or [DEFAULT_SCOPE]
    credentials = run_oauth_flow(
        client_secrets_path=client_secrets_path,
        scopes=scopes,
        mode=args.mode,
    )

    email_probe_path = PROJECT_ROOT / "secrets" / ".tmp_connect_probe.json"
    email_probe_path.parent.mkdir(parents=True, exist_ok=True)
    email_probe_path.write_text(credentials.to_json(), encoding="utf-8")
    service = build_gmail_service(email_probe_path)
    email_address = get_profile_email(service)

    mailbox_key = args.mailbox_key or None
    token_path = PROJECT_ROOT / "secrets" / "mailboxes" / (
        (mailbox_key or email_address.replace("@", "_at_").replace(".", "_")) + ".json"
    )
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(credentials.to_json(), encoding="utf-8")
    email_probe_path.unlink(missing_ok=True)

    record = registry.upsert_mailbox(
        email=email_address,
        token_path=token_path,
        label=args.label,
        mailbox_key=mailbox_key,
    )
    registry.save()
    print(json.dumps({"connected_mailbox": record}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
