"""Exchange Gmail Desktop OAuth credentials for a refresh token.

This script supports two authorization modes:

1. `localserver`: Starts a temporary localhost callback server and completes
   the OAuth flow automatically after the browser redirects back.
2. `manual`: Prints the authorization URL and asks the user to paste the final
   redirected localhost URL from the browser address bar. This is useful when
   the browser reaches a blank localhost page and the callback does not finish.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from gmail_ai_worker.config import PACKAGE_ROOT
from gmail_ai_worker.oauth_flow import DEFAULT_SCOPE, run_oauth_flow


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments.

    Args:
        argv: Optional explicit argument list.

    Returns:
        Parsed CLI namespace.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Run the Gmail Desktop OAuth flow and save the resulting refresh "
            "token for local development."
        )
    )
    parser.add_argument(
        "--client-secrets",
        required=True,
        help="Absolute path to the downloaded Desktop OAuth client JSON.",
    )
    parser.add_argument(
        "--token-output",
        default=str(PACKAGE_ROOT / "secrets" / "gmail_token.json"),
        help="Where to write the resulting token JSON.",
    )
    parser.add_argument(
        "--scope",
        dest="scopes",
        action="append",
        default=None,
        help=(
            "OAuth scope to request. Repeat this flag to add more scopes. "
            f"Defaults to {DEFAULT_SCOPE}."
        ),
    )
    parser.add_argument(
        "--mode",
        choices=("localserver", "manual"),
        default="localserver",
        help=(
            "Authorization mode. Use 'manual' if the browser reaches a blank "
            "localhost page and does not return to the script."
        ),
    )
    return parser.parse_args(argv)


def ensure_parent_directory(file_path: Path) -> None:
    """Create the output directory if it does not exist.

    Args:
        file_path: Destination file path.
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)


def mask_secret(value: str) -> str:
    """Return a lightly masked representation for terminal output.

    Args:
        value: Secret string to mask.

    Returns:
        Masked string safe for confirmation output.
    """
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"


def main(argv: Sequence[str] | None = None) -> int:
    """Run the installed-app OAuth flow and save the resulting token JSON.

    Args:
        argv: Optional explicit argument list.

    Returns:
        Process exit code.
    """
    args = parse_args(argv)
    client_secrets_path = Path(args.client_secrets).expanduser().resolve()
    token_output_path = Path(args.token_output).expanduser().resolve()
    scopes = args.scopes or [DEFAULT_SCOPE]

    ensure_parent_directory(token_output_path)

    credentials = run_oauth_flow(
        client_secrets_path=client_secrets_path,
        scopes=scopes,
        mode=args.mode,
    )

    if not credentials.refresh_token:
        raise RuntimeError(
            "Google completed the OAuth flow but did not return a refresh "
            "token. Revoke the app grant for this account and rerun the "
            "script with prompt=consent."
        )

    token_output_path.write_text(credentials.to_json(), encoding="utf-8")

    saved_payload = json.loads(token_output_path.read_text(encoding="utf-8"))
    masked_refresh_token = mask_secret(saved_payload["refresh_token"])

    print("Saved Gmail token JSON.")
    print(f"Output path: {token_output_path}")
    print(f"Scopes: {', '.join(scopes)}")
    print(f"Refresh token: {masked_refresh_token}")
    print("Keep this file private and do not commit it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
