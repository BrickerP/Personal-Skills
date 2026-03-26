"""Mailbox registry helpers for multi-account local use."""

from __future__ import annotations

import json
import re
from glob import glob
from pathlib import Path
from typing import Any

from gmail_ai_worker.config import PACKAGE_ROOT


DEFAULT_REGISTRY_PATH = PACKAGE_ROOT / "runtime" / "mailboxes.json"
DEFAULT_CLIENT_SECRETS_PATH = PACKAGE_ROOT / "runtime" / "oauth_client.json"


def _discover_client_secrets_path() -> Path:
    """Find a plausible Desktop OAuth client JSON path.

    Returns:
        Best-effort client secret path.
    """
    explicit_env = Path(
        __import__("os").environ.get("GMAIL_AI_CLIENT_SECRETS_PATH", "")
    ).expanduser()
    if str(explicit_env) and explicit_env.exists():
        return explicit_env

    candidate_paths = [
        PACKAGE_ROOT / "runtime" / "oauth_client.json",
        PACKAGE_ROOT / "secrets" / "oauth_client.json",
        Path.home() / "Downloads" / "oauth_client.json",
    ]
    for candidate in candidate_paths:
        if candidate.exists():
            return candidate

    download_matches = sorted(
        glob(str(Path.home() / "Downloads" / "client_secret_*.json"))
    )
    if download_matches:
        return Path(download_matches[-1])

    return DEFAULT_CLIENT_SECRETS_PATH


def _default_registry_data() -> dict[str, Any]:
    """Build the default mailbox registry payload."""
    return {
        "version": 1,
        "client_secrets_path": str(_discover_client_secrets_path()),
        "active_mailboxes": [],
        "mailboxes": [],
    }


def _resolve_registry_path(path_value: str) -> Path:
    """Resolve a stored registry path value.

    Relative paths are interpreted relative to the worker package root so the
    committed template registry can stay portable across machines.
    """
    if not path_value.strip():
        return _discover_client_secrets_path()
    resolved = Path(path_value).expanduser()
    if resolved.is_absolute():
        return resolved
    return (PACKAGE_ROOT / resolved).resolve()


def _slugify(value: str) -> str:
    lowered = value.strip().lower()
    lowered = re.sub(r"[^a-z0-9]+", "-", lowered)
    lowered = re.sub(r"-{2,}", "-", lowered).strip("-")
    return lowered or "mailbox"


class MailboxRegistry:
    """JSON-backed mailbox registry for local skill users."""

    def __init__(self, path: Path = DEFAULT_REGISTRY_PATH) -> None:
        self.path = path
        self.data = self._load()

    def _load(self) -> dict[str, Any]:
        default_data = _default_registry_data()
        if not self.path.exists():
            return default_data
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        merged = {**default_data, **payload}
        merged["active_mailboxes"] = list(merged.get("active_mailboxes", []))
        merged["mailboxes"] = list(merged.get("mailboxes", []))
        if not merged.get("client_secrets_path"):
            merged["client_secrets_path"] = default_data["client_secrets_path"]
        return merged

    def save(self) -> None:
        """Persist the registry to disk."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self.data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def get_client_secrets_path(self) -> Path:
        """Return the configured OAuth client JSON path."""
        return _resolve_registry_path(str(self.data.get("client_secrets_path", "")))

    def set_client_secrets_path(self, path: Path) -> None:
        """Update the OAuth client JSON path."""
        self.data["client_secrets_path"] = str(path.expanduser())

    def list_mailboxes(self) -> list[dict[str, Any]]:
        """Return all connected mailboxes."""
        return list(self.data.get("mailboxes", []))

    def find_mailbox(self, mailbox_key: str) -> dict[str, Any] | None:
        """Look up one mailbox by key."""
        for mailbox in self.list_mailboxes():
            if mailbox["key"] == mailbox_key:
                return mailbox
        return None

    def upsert_mailbox(
        self,
        *,
        email: str,
        token_path: Path,
        label: str | None = None,
        mailbox_key: str | None = None,
    ) -> dict[str, Any]:
        """Insert or update a mailbox definition.

        Args:
            email: Mailbox email address.
            token_path: Token JSON path.
            label: Optional user-facing label.
            mailbox_key: Optional explicit mailbox key.

        Returns:
            Stored mailbox record.
        """
        key = mailbox_key or _slugify(email)
        existing = self.find_mailbox(key)
        payload = {
            "key": key,
            "email": email,
            "label": label or email,
            "token_path": str(token_path.expanduser()),
        }
        if existing:
            existing.update(payload)
        else:
            self.data.setdefault("mailboxes", []).append(payload)
        if key not in self.data.setdefault("active_mailboxes", []):
            self.data["active_mailboxes"].append(key)
        return payload

    def set_active_mailboxes(self, mailbox_keys: list[str]) -> None:
        """Replace the active mailbox list."""
        self.data["active_mailboxes"] = mailbox_keys

    def resolve_mailbox(self, mailbox_key: str | None) -> dict[str, Any]:
        """Resolve the target mailbox using explicit or active selection.

        Args:
            mailbox_key: Optional mailbox key.

        Returns:
            Mailbox record.
        """
        if mailbox_key:
            mailbox = self.find_mailbox(mailbox_key)
            if mailbox is None:
                raise KeyError(f"Unknown mailbox key: {mailbox_key}")
            return mailbox

        active = list(self.data.get("active_mailboxes", []))
        if len(active) == 1:
            mailbox = self.find_mailbox(active[0])
            if mailbox is None:
                raise KeyError(f"Active mailbox not found: {active[0]}")
            return mailbox
        if not active:
            raise RuntimeError(
                "No active mailbox configured. Connect a mailbox first."
            )
        raise RuntimeError(
            "Multiple active mailboxes are configured. Specify --mailbox explicitly."
        )


def resolve_token_path(
    *,
    mailbox_key: str | None,
    fallback_token_path: Path,
) -> Path:
    """Resolve the token path from mailbox selection or fallback.

    Args:
        mailbox_key: Optional connected mailbox key.
        fallback_token_path: Legacy direct token path.

    Returns:
        Token path to use.
    """
    registry = MailboxRegistry()
    if mailbox_key:
        return Path(registry.resolve_mailbox(mailbox_key)["token_path"]).expanduser()
    try:
        return Path(registry.resolve_mailbox(None)["token_path"]).expanduser()
    except Exception:
        return fallback_token_path.expanduser()
