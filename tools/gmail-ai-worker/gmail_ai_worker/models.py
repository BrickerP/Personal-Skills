"""Shared data models for Gmail thread summaries."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class MessageSummary:
    """Compact representation of a Gmail message."""

    gmail_message_id: str
    internet_message_id: str | None
    from_header: str
    to_header: str
    cc_header: str
    subject: str
    sent_at: str
    internal_date_ms: str
    label_ids: list[str]
    body_excerpt: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize the message summary to JSON."""
        return asdict(self)


@dataclass(slots=True)
class ThreadSnapshot:
    """Structured snapshot of a Gmail thread for Codex reasoning."""

    thread_id: str
    history_id: str | None
    subject: str
    snippet: str
    latest_message_id: str
    latest_internal_date_ms: str
    latest_from: str
    latest_to: str
    latest_sent_at: str
    unread_message_count: int
    has_draft_message: bool
    participants: list[str]
    default_reply_to: list[str]
    reference_message_id: str | None
    messages: list[MessageSummary] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the thread snapshot to JSON."""
        payload = asdict(self)
        payload["messages"] = [message.to_dict() for message in self.messages]
        return payload


@dataclass(slots=True)
class PlannedAction:
    """Structured Gmail action produced by Codex from cached data."""

    action_id: str
    mailbox_key: str
    thread_id: str
    latest_message_id: str
    kind: str
    reason: str
    needs_human_review: bool = False
    subject: str | None = None
    to: list[str] = field(default_factory=list)
    cc: list[str] = field(default_factory=list)
    body: str | None = None
    add_labels: list[str] = field(default_factory=list)
    remove_labels: list[str] = field(default_factory=list)
    archive: bool = False

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PlannedAction":
        """Deserialize one planned action."""
        return cls(
            action_id=str(payload["action_id"]),
            mailbox_key=str(payload["mailbox_key"]),
            thread_id=str(payload["thread_id"]),
            latest_message_id=str(payload["latest_message_id"]),
            kind=str(payload["kind"]),
            reason=str(payload.get("reason", "")),
            needs_human_review=bool(payload.get("needs_human_review", False)),
            subject=payload.get("subject"),
            to=list(payload.get("to", [])),
            cc=list(payload.get("cc", [])),
            body=payload.get("body"),
            add_labels=list(payload.get("add_labels", [])),
            remove_labels=list(payload.get("remove_labels", [])),
            archive=bool(payload.get("archive", False)),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the action to JSON."""
        return asdict(self)


@dataclass(slots=True)
class ActionPlan:
    """Codex-authored plan consumed by the local apply job."""

    generated_at: str
    goal: str
    actions: list[PlannedAction]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ActionPlan":
        """Deserialize a plan payload."""
        return cls(
            generated_at=str(payload.get("generated_at", "")),
            goal=str(payload.get("goal", "")),
            actions=[
                PlannedAction.from_dict(item)
                for item in payload.get("actions", [])
            ],
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize plan to JSON."""
        return {
            "generated_at": self.generated_at,
            "goal": self.goal,
            "actions": [action.to_dict() for action in self.actions],
        }
