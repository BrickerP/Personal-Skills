"""Run a minimal Gmail API smoke test using the saved OAuth token.

The goal is to prove that the stored refresh token works end-to-end:

- load saved credentials
- refresh them when expired
- read the current Gmail profile
- list a few recent inbox threads
"""

from __future__ import annotations

import json
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from gmail_ai_worker.config import PACKAGE_ROOT
TOKEN_PATH = PACKAGE_ROOT / "secrets" / "gmail_token.json"


def load_credentials(token_path: Path) -> Credentials:
    """Load and refresh Gmail OAuth credentials from disk.

    Args:
        token_path: File containing the Gmail OAuth token payload.

    Returns:
        Valid Gmail credentials.
    """
    credentials = Credentials.from_authorized_user_file(str(token_path))
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        token_path.write_text(credentials.to_json(), encoding="utf-8")
    return credentials


def main() -> int:
    """Run the Gmail profile and recent-thread smoke test."""
    if not TOKEN_PATH.exists():
        raise FileNotFoundError(
            f"Token file not found: {TOKEN_PATH}. Run oauth_bootstrap.py first."
        )

    credentials = load_credentials(TOKEN_PATH)
    service = build("gmail", "v1", credentials=credentials)

    profile = service.users().getProfile(userId="me").execute()
    threads_response = (
        service.users()
        .threads()
        .list(
            userId="me",
            q="label:inbox newer_than:1d",
            maxResults=5,
        )
        .execute()
    )
    threads = threads_response.get("threads", [])

    result = {
        "emailAddress": profile["emailAddress"],
        "messagesTotal": profile["messagesTotal"],
        "threadsTotal": profile["threadsTotal"],
        "sampleThreadCount": len(threads),
        "sampleThreadIds": [thread["id"] for thread in threads],
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
