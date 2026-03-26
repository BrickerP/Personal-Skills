"""Install local launchd jobs for Gmail refresh and plan apply."""

from __future__ import annotations

import argparse
import os
import plistlib
import subprocess
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gmail_ai_worker.config import PACKAGE_ROOT


DEFAULT_REFRESH_LABEL = "com.gmail-ai-daily-ops.refresh"
DEFAULT_APPLY_LABEL = "com.gmail-ai-daily-ops.apply"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install launchd Gmail local jobs.")
    parser.add_argument("--refresh-minute", type=int, default=55)
    parser.add_argument("--apply-minute", type=int, default=5)
    return parser.parse_args()


def _install_job(
    *,
    label: str,
    shell_command: str,
    minute_of_hour: int,
    launch_agents_dir: Path,
    log_dir: Path,
) -> Path:
    plist_path = launch_agents_dir / f"{label}.plist"
    domain_target = f"gui/{os.getuid()}"
    plist_payload = {
        "Label": label,
        "ProgramArguments": ["/bin/zsh", "-lc", shell_command],
        "RunAtLoad": True,
        "StartCalendarInterval": [
            {"Hour": hour, "Minute": minute_of_hour} for hour in range(24)
        ],
        "WorkingDirectory": str(PACKAGE_ROOT),
        "StandardOutPath": str(log_dir / f"{label}.stdout.log"),
        "StandardErrorPath": str(log_dir / f"{label}.stderr.log"),
    }
    with plist_path.open("wb") as handle:
        plistlib.dump(plist_payload, handle)
    subprocess.run(
        ["launchctl", "bootout", domain_target, str(plist_path)],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    subprocess.run(["launchctl", "bootstrap", domain_target, str(plist_path)], check=True)
    return plist_path


def main() -> int:
    args = parse_args()
    launch_agents_dir = Path.home() / "Library" / "LaunchAgents"
    launch_agents_dir.mkdir(parents=True, exist_ok=True)
    log_dir = PACKAGE_ROOT / "runtime" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    refresh_command = (
        f"cd {PACKAGE_ROOT} && "
        "if [ ! -d .venv ]; then python3 -m venv .venv; fi && "
        "source .venv/bin/activate && "
        "python -m pip install -r requirements.txt >/tmp/gmail-ai-worker-install.log 2>&1 && "
        "python scripts/refresh_active_mailboxes.py"
    )
    apply_command = (
        f"cd {PACKAGE_ROOT} && "
        "source .venv/bin/activate && "
        "python scripts/apply_action_plan.py"
    )

    refresh_plist = _install_job(
        label=DEFAULT_REFRESH_LABEL,
        shell_command=refresh_command,
        minute_of_hour=args.refresh_minute,
        launch_agents_dir=launch_agents_dir,
        log_dir=log_dir,
    )
    apply_plist = _install_job(
        label=DEFAULT_APPLY_LABEL,
        shell_command=apply_command,
        minute_of_hour=args.apply_minute,
        launch_agents_dir=launch_agents_dir,
        log_dir=log_dir,
    )
    print(refresh_plist)
    print(apply_plist)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
