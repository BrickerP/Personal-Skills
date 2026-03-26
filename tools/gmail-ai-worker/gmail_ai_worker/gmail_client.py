"""Gmail API helpers for local Codex-driven triage."""

from __future__ import annotations

import base64
import json
import re
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import getaddresses, parseaddr
from html import unescape
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource, build

from gmail_ai_worker.models import MessageSummary, ThreadSnapshot


HTML_TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")


def load_credentials(token_path: Path) -> Credentials:
    """Load Gmail OAuth credentials and refresh them if needed.

    Args:
        token_path: Stored Gmail token JSON path.

    Returns:
        Valid Gmail credentials.
    """
    credentials = Credentials.from_authorized_user_file(str(token_path))
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        token_path.write_text(credentials.to_json(), encoding="utf-8")
    return credentials


def build_gmail_service(token_path: Path) -> Resource:
    """Construct a Gmail API service.

    Args:
        token_path: Stored Gmail token JSON path.

    Returns:
        Gmail service resource.
    """
    credentials = load_credentials(token_path)
    return build("gmail", "v1", credentials=credentials)


def get_profile_email(service: Resource) -> str:
    """Return the current Gmail profile email address."""
    profile = service.users().getProfile(userId="me").execute()
    return str(profile["emailAddress"])


def list_threads(service: Resource, query: str, max_results: int) -> list[dict[str, Any]]:
    """List candidate Gmail threads for a query."""
    response = (
        service.users()
        .threads()
        .list(userId="me", q=query, maxResults=max_results)
        .execute()
    )
    return list(response.get("threads", []))


def list_labels(service: Resource) -> list[dict[str, Any]]:
    """List Gmail labels for the current user.

    Args:
        service: Gmail API service.

    Returns:
        Gmail label objects.
    """
    response = service.users().labels().list(userId="me").execute()
    return list(response.get("labels", []))


def get_thread(service: Resource, thread_id: str) -> dict[str, Any]:
    """Fetch a full Gmail thread."""
    return (
        service.users()
        .threads()
        .get(userId="me", id=thread_id, format="full")
        .execute()
    )


def _decode_body_data(data: str | None) -> str:
    if not data:
        return ""
    decoded_bytes = base64.urlsafe_b64decode(data.encode("utf-8"))
    return decoded_bytes.decode("utf-8", errors="replace")


def _html_to_text(raw_html: str) -> str:
    text = HTML_TAG_RE.sub(" ", raw_html)
    return WHITESPACE_RE.sub(" ", unescape(text)).strip()


def _extract_best_body(payload: dict[str, Any]) -> str:
    mime_type = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data")
    if mime_type == "text/plain" and body_data:
        return _decode_body_data(body_data)
    if mime_type == "text/html" and body_data:
        return _html_to_text(_decode_body_data(body_data))

    parts = payload.get("parts", [])
    for part in parts:
        best_text = _extract_best_body(part)
        if best_text:
            return best_text
    return ""


def _get_header(headers: list[dict[str, str]], name: str) -> str:
    lowered_name = name.lower()
    for header in headers:
        if header.get("name", "").lower() == lowered_name:
            return header.get("value", "")
    return ""


def _compact_text(text: str, max_chars: int) -> str:
    normalized = WHITESPACE_RE.sub(" ", text).strip()
    if len(normalized) <= max_chars:
        return normalized
    return normalized[: max_chars - 3].rstrip() + "..."


def _parse_addresses(raw_value: str, self_email: str) -> list[str]:
    participants: list[str] = []
    for _, email_address in getaddresses([raw_value]):
        lowered = email_address.strip().lower()
        if lowered and lowered != self_email.lower() and lowered not in participants:
            participants.append(lowered)
    return participants


def _default_reply_targets(message_headers: list[dict[str, str]], self_email: str) -> list[str]:
    sender_name, sender_email = parseaddr(_get_header(message_headers, "From"))
    del sender_name
    sender_email = sender_email.strip().lower()
    if sender_email and sender_email != self_email.lower():
        return [sender_email]
    to_header = _get_header(message_headers, "To")
    return _parse_addresses(to_header, self_email)


def _reply_subject(subject: str) -> str:
    subject = subject.strip()
    if not subject:
        return "Re:"
    if subject.lower().startswith("re:"):
        return subject
    return f"Re: {subject}"


def _message_to_summary(message: dict[str, Any], excerpt_chars: int) -> MessageSummary:
    payload = message.get("payload", {})
    headers = payload.get("headers", [])
    body_text = _compact_text(_extract_best_body(payload), excerpt_chars)
    return MessageSummary(
        gmail_message_id=str(message.get("id", "")),
        internet_message_id=_get_header(headers, "Message-ID") or None,
        from_header=_get_header(headers, "From"),
        to_header=_get_header(headers, "To"),
        cc_header=_get_header(headers, "Cc"),
        subject=_get_header(headers, "Subject"),
        sent_at=_get_header(headers, "Date"),
        internal_date_ms=str(message.get("internalDate", "")),
        label_ids=list(message.get("labelIds", [])),
        body_excerpt=body_text,
    )


def build_thread_snapshot(
    service: Resource,
    thread_id: str,
    *,
    self_email: str,
    messages_per_thread: int,
    excerpt_chars: int,
) -> ThreadSnapshot:
    """Build a structured thread snapshot for Codex reasoning."""
    thread = get_thread(service, thread_id)
    messages = thread.get("messages", [])
    if not messages:
        raise ValueError(f"Thread {thread_id} contained no messages.")

    sorted_messages = sorted(
        messages,
        key=lambda item: int(item.get("internalDate", "0")),
    )
    latest_message = sorted_messages[-1]
    latest_headers = latest_message.get("payload", {}).get("headers", [])
    unread_count = sum(
        1 for message in sorted_messages if "UNREAD" in message.get("labelIds", [])
    )
    has_draft_message = any(
        "DRAFT" in message.get("labelIds", []) for message in sorted_messages
    )
    message_summaries = [
        _message_to_summary(message, excerpt_chars)
        for message in sorted_messages[-messages_per_thread:]
    ]
    participants: list[str] = []
    for message in sorted_messages:
        payload_headers = message.get("payload", {}).get("headers", [])
        for header_name in ("From", "To", "Cc"):
            participants.extend(
                [
                    email
                    for email in _parse_addresses(
                        _get_header(payload_headers, header_name),
                        self_email,
                    )
                    if email not in participants
                ]
            )

    reference_message_id = None
    reference_targets: list[str] = []
    for message in reversed(sorted_messages):
        payload_headers = message.get("payload", {}).get("headers", [])
        default_targets = _default_reply_targets(payload_headers, self_email)
        if default_targets:
            reference_message_id = _get_header(payload_headers, "Message-ID") or None
            reference_targets = default_targets
            break
    if reference_message_id is None:
        reference_message_id = _get_header(latest_headers, "Message-ID") or None
    if not reference_targets:
        reference_targets = _default_reply_targets(latest_headers, self_email)

    return ThreadSnapshot(
        thread_id=thread_id,
        history_id=thread.get("historyId"),
        subject=_get_header(latest_headers, "Subject") or thread.get("snippet", ""),
        snippet=str(thread.get("snippet", "")),
        latest_message_id=str(latest_message.get("id", "")),
        latest_internal_date_ms=str(latest_message.get("internalDate", "")),
        latest_from=_get_header(latest_headers, "From"),
        latest_to=_get_header(latest_headers, "To"),
        latest_sent_at=_get_header(latest_headers, "Date"),
        unread_message_count=unread_count,
        has_draft_message=has_draft_message,
        participants=participants,
        default_reply_to=reference_targets,
        reference_message_id=reference_message_id,
        messages=message_summaries,
    )


def collect_snapshot_bundle(
    service: Resource,
    *,
    self_email: str,
    query: str,
    max_threads: int,
    messages_per_thread: int,
    excerpt_chars: int,
) -> dict[str, Any]:
    """Collect a thread snapshot bundle for one Codex automation run."""
    bundle_threads = [
        build_thread_snapshot(
            service,
            thread["id"],
            self_email=self_email,
            messages_per_thread=messages_per_thread,
            excerpt_chars=excerpt_chars,
        )
        for thread in list_threads(service, query=query, max_results=max_threads)
    ]
    bundle_threads.sort(key=lambda item: int(item.latest_internal_date_ms), reverse=True)
    return {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "self_email": self_email,
        "query": query,
        "thread_count": len(bundle_threads),
        "threads": [thread.to_dict() for thread in bundle_threads],
    }


def create_reply_draft(
    service: Resource,
    *,
    thread_id: str,
    subject: str,
    body_text: str,
    to: list[str],
    cc: list[str],
    reference_message_id: str | None,
) -> dict[str, Any]:
    """Create a Gmail draft reply in an existing thread."""
    message = EmailMessage()
    message["To"] = ", ".join(to)
    if cc:
        message["Cc"] = ", ".join(cc)
    message["Subject"] = _reply_subject(subject)
    if reference_message_id:
        message["In-Reply-To"] = reference_message_id
        message["References"] = reference_message_id
    message.set_content(body_text)

    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    return (
        service.users()
        .drafts()
        .create(
            userId="me",
            body={
                "message": {
                    "threadId": thread_id,
                    "raw": encoded_message,
                }
            },
        )
        .execute()
    )


def ensure_label(service: Resource, label_name: str) -> dict[str, Any]:
    """Resolve a Gmail label by name, creating a user label if needed.

    Args:
        service: Gmail API service.
        label_name: Gmail label name or system label id.

    Returns:
        Gmail label object.
    """
    normalized_name = label_name.strip()
    for label in list_labels(service):
        if label.get("id") == normalized_name or label.get("name") == normalized_name:
            return label

    return (
        service.users()
        .labels()
        .create(
            userId="me",
            body={
                "name": normalized_name,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
            },
        )
        .execute()
    )


def resolve_label_id(service: Resource, label_spec: str) -> str:
    """Resolve a user-provided label spec to a Gmail label id.

    Args:
        service: Gmail API service.
        label_spec: Gmail label id or label name.

    Returns:
        Gmail label id.
    """
    normalized_spec = label_spec.strip()
    for label in list_labels(service):
        if label.get("id") == normalized_spec or label.get("name") == normalized_spec:
            return str(label["id"])
    return str(ensure_label(service, normalized_spec)["id"])


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Persist JSON payload to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
