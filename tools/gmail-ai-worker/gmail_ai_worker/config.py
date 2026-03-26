"""Configuration helpers for the local Gmail AI worker."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TOKEN_PATH = PACKAGE_ROOT / "secrets" / "gmail_token.json"
DEFAULT_RUNTIME_DIR = PACKAGE_ROOT / "runtime"
DEFAULT_RUN_REPORT_PATH = DEFAULT_RUNTIME_DIR / "latest_run_report.md"
DEFAULT_REFRESH_CACHE_PATH = DEFAULT_RUNTIME_DIR / "latest_refresh_cache.json"
DEFAULT_REFRESH_STATUS_PATH = DEFAULT_RUNTIME_DIR / "latest_refresh_status.json"
DEFAULT_ACTION_PLAN_PATH = DEFAULT_RUNTIME_DIR / "latest_action_plan.json"
DEFAULT_APPLY_STATUS_PATH = DEFAULT_RUNTIME_DIR / "latest_apply_status.json"
DEFAULT_APPLY_STATE_PATH = DEFAULT_RUNTIME_DIR / "apply_state.json"
DEFAULT_GMAIL_QUERY = (
    "label:inbox newer_than:14d -category:promotions -category:social "
    "-in:drafts -in:sent"
)
DEFAULT_MAX_THREADS = 200
DEFAULT_MESSAGES_PER_THREAD = 4
DEFAULT_EXCERPT_CHARS = 2200
DEFAULT_TIMEZONE = "Asia/Shanghai"


@dataclass(slots=True)
class WorkerConfig:
    """Runtime configuration for Gmail worker commands."""

    token_path: Path = DEFAULT_TOKEN_PATH
    runtime_dir: Path = DEFAULT_RUNTIME_DIR
    run_report_path: Path = DEFAULT_RUN_REPORT_PATH
    refresh_cache_path: Path = DEFAULT_REFRESH_CACHE_PATH
    refresh_status_path: Path = DEFAULT_REFRESH_STATUS_PATH
    action_plan_path: Path = DEFAULT_ACTION_PLAN_PATH
    apply_status_path: Path = DEFAULT_APPLY_STATUS_PATH
    apply_state_path: Path = DEFAULT_APPLY_STATE_PATH
    gmail_query: str = DEFAULT_GMAIL_QUERY
    max_threads: int = DEFAULT_MAX_THREADS
    messages_per_thread: int = DEFAULT_MESSAGES_PER_THREAD
    excerpt_chars: int = DEFAULT_EXCERPT_CHARS
    timezone: str = DEFAULT_TIMEZONE

    @classmethod
    def from_env(cls) -> "WorkerConfig":
        """Build configuration from environment variables.

        Returns:
            Worker configuration with environment overrides applied.
        """
        runtime_dir = Path(
            os.environ.get("GMAIL_AI_RUNTIME_DIR", str(DEFAULT_RUNTIME_DIR))
        ).expanduser()
        return cls(
            token_path=Path(
                os.environ.get("GMAIL_AI_TOKEN_PATH", str(DEFAULT_TOKEN_PATH))
            ).expanduser(),
            runtime_dir=runtime_dir,
            run_report_path=Path(
                os.environ.get(
                    "GMAIL_AI_RUN_REPORT_PATH",
                    str(runtime_dir / "latest_run_report.md"),
                )
            ).expanduser(),
            refresh_cache_path=Path(
                os.environ.get(
                    "GMAIL_AI_REFRESH_CACHE_PATH",
                    str(runtime_dir / "latest_refresh_cache.json"),
                )
            ).expanduser(),
            refresh_status_path=Path(
                os.environ.get(
                    "GMAIL_AI_REFRESH_STATUS_PATH",
                    str(runtime_dir / "latest_refresh_status.json"),
                )
            ).expanduser(),
            action_plan_path=Path(
                os.environ.get(
                    "GMAIL_AI_ACTION_PLAN_PATH",
                    str(runtime_dir / "latest_action_plan.json"),
                )
            ).expanduser(),
            apply_status_path=Path(
                os.environ.get(
                    "GMAIL_AI_APPLY_STATUS_PATH",
                    str(runtime_dir / "latest_apply_status.json"),
                )
            ).expanduser(),
            apply_state_path=Path(
                os.environ.get(
                    "GMAIL_AI_APPLY_STATE_PATH",
                    str(runtime_dir / "apply_state.json"),
                )
            ).expanduser(),
            gmail_query=os.environ.get(
                "GMAIL_AI_QUERY",
                DEFAULT_GMAIL_QUERY,
            ),
            max_threads=int(os.environ.get("GMAIL_AI_MAX_THREADS", DEFAULT_MAX_THREADS)),
            messages_per_thread=int(
                os.environ.get(
                    "GMAIL_AI_MESSAGES_PER_THREAD", DEFAULT_MESSAGES_PER_THREAD
                )
            ),
            excerpt_chars=int(
                os.environ.get("GMAIL_AI_EXCERPT_CHARS", DEFAULT_EXCERPT_CHARS)
            ),
            timezone=os.environ.get("GMAIL_AI_TIMEZONE", DEFAULT_TIMEZONE),
        )

    def ensure_runtime_directories(self) -> None:
        """Create runtime parent directories if needed."""
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.run_report_path.parent.mkdir(parents=True, exist_ok=True)
        self.refresh_cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.refresh_status_path.parent.mkdir(parents=True, exist_ok=True)
        self.action_plan_path.parent.mkdir(parents=True, exist_ok=True)
        self.apply_status_path.parent.mkdir(parents=True, exist_ok=True)
        self.apply_state_path.parent.mkdir(parents=True, exist_ok=True)
