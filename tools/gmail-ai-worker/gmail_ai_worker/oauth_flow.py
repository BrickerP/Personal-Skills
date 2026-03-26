"""Reusable Gmail OAuth helpers."""

from __future__ import annotations

from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow


DEFAULT_SCOPE = "https://www.googleapis.com/auth/gmail.modify"


def build_flow(client_secrets_path: Path, scopes: list[str]) -> InstalledAppFlow:
    """Create an installed-app OAuth flow.

    Args:
        client_secrets_path: Path to Desktop OAuth client JSON.
        scopes: OAuth scopes to request.

    Returns:
        Configured OAuth flow.
    """
    return InstalledAppFlow.from_client_secrets_file(
        str(client_secrets_path),
        scopes=scopes,
    )


def run_manual_flow(flow: InstalledAppFlow) -> object:
    """Complete the OAuth flow by pasting the redirected localhost URL.

    Args:
        flow: Configured installed-app flow.

    Returns:
        OAuth credentials object.
    """
    flow.redirect_uri = "http://localhost"
    authorization_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
    )
    print("Open this URL in your browser and complete the Google consent flow:")
    print(authorization_url)
    print(
        "\nAfter Google redirects to a blank localhost page, copy the full "
        "URL from the browser address bar and paste it below."
    )
    redirected_url = input("Redirected URL: ").strip()
    if "code=" not in redirected_url:
        raise RuntimeError(
            "No authorization code was found in the pasted URL. Make sure you "
            "paste the full localhost redirect URL from the browser."
        )
    authorization_response = redirected_url.replace("http://", "https://", 1)
    flow.fetch_token(authorization_response=authorization_response)
    return flow.credentials


def run_oauth_flow(
    *,
    client_secrets_path: Path,
    scopes: list[str],
    mode: str,
) -> object:
    """Run the Gmail installed-app OAuth flow.

    Args:
        client_secrets_path: Path to Desktop OAuth client JSON.
        scopes: OAuth scopes to request.
        mode: `localserver` or `manual`.

    Returns:
        OAuth credentials object.
    """
    flow = build_flow(client_secrets_path, scopes)
    if mode == "manual":
        return run_manual_flow(flow)
    return flow.run_local_server(
        host="localhost",
        port=0,
        access_type="offline",
        prompt="consent",
        authorization_prompt_message=(
            "A browser window has been opened for Gmail authorization.\n"
            "If it did not open automatically, visit this URL:\n"
            "{url}\n"
        ),
        success_message=(
            "Authorization completed. You can close this tab and return "
            "to the terminal."
        ),
    )
