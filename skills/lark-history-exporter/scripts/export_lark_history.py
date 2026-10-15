#!/usr/bin/env python3
"""Export visible Lark/Feishu chat history to local Markdown."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import signal
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

import render_lark_markdown


DEFAULT_SCOPES = (
    "im:chat:read im:message:readonly im:message.reactions:read "
    "im:message.group_msg:get_as_user im:message.p2p_msg:get_as_user contact:user.base:readonly"
)


class ExportError(RuntimeError):
    pass


def cli_base() -> list[str]:
    found = shutil.which("lark-cli")
    if found:
        return [found]
    return ["npx", "-y", "@larksuite/cli@latest"]


def run_cli(
    args: list[str],
    cwd: Path | None = None,
    check: bool = True,
    timeout: float | None = None,
) -> subprocess.CompletedProcess[str]:
    argv = cli_base() + args
    proc = subprocess.Popen(
        argv,
        cwd=str(cwd) if cwd else None,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            stdout, stderr = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            stdout, stderr = proc.communicate()
        raise ExportError(f"lark-cli timed out after {timeout}s: {' '.join(args)}") from exc
    proc_result = subprocess.CompletedProcess(argv, proc.returncode, stdout, stderr)
    if check and proc_result.returncode != 0:
        detail = proc_result.stderr.strip() or proc_result.stdout.strip()
        raise ExportError(f"lark-cli failed ({proc.returncode}): {' '.join(args)}\n{detail}")
    return proc_result


def parse_stdout_json(proc: subprocess.CompletedProcess[str]) -> Any:
    text = proc.stdout.strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ExportError(f"lark-cli returned non-JSON output:\n{text[:1000]}") from exc


def json_data(envelope: Any) -> Any:
    if isinstance(envelope, dict) and "data" in envelope:
        return envelope["data"]
    return envelope


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() == "true"
    return bool(value)


def next_page_token(envelope: Any) -> str:
    data = json_data(envelope)
    if isinstance(data, dict):
        token = data.get("page_token") or data.get("next_page_token")
        return str(token or "")
    return ""


def has_more(envelope: Any) -> bool:
    data = json_data(envelope)
    if isinstance(data, dict):
        return bool_value(data.get("has_more"))
    return False


def extract_chats(envelope: Any) -> list[dict[str, Any]]:
    return render_lark_markdown.extract_chats(json_data(envelope))


def extract_messages(envelope: Any) -> list[dict[str, Any]]:
    return render_lark_markdown.extract_messages(envelope)


def command_string(args: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in cli_base() + args)


def is_retryable_cli_error(exc: ExportError) -> bool:
    text = str(exc).lower()
    return (
        "timed out" in text
        or '"subtype": "timeout"' in text
        or '"type": "network"' in text
        or "subtype=timeout" in text
    )


def auth_status() -> tuple[bool, str, Any]:
    proc = run_cli(["auth", "status", "--json"], check=False)
    payload: Any = {}
    if proc.stdout.strip():
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError:
            payload = {"raw_stdout": proc.stdout}
    if proc.returncode == 0:
        return True, "ok", payload
    error = payload.get("error", {}) if isinstance(payload, dict) else {}
    subtype = error.get("subtype") or error.get("type") or "error"
    message = error.get("message") or proc.stderr.strip() or proc.stdout.strip()
    return False, f"{subtype}: {message}", payload


def print_auth_help() -> None:
    print("Lark CLI is not ready for export.")
    print("")
    print("Configure the app/profile:")
    print(command_string(["config", "init", "--new", "--brand", "lark"]))
    print("")
    print("Authorize IM read scopes:")
    print(command_string(["auth", "login", "--scope", DEFAULT_SCOPES, "--no-wait", "--json"]))
    print("")
    print("After opening the verification URL and approving, finish with:")
    print(command_string(["auth", "login", "--device-code", "<device_code>"]))


def check_auth_or_raise() -> None:
    ok, message, _payload = auth_status()
    if ok:
        return
    print_auth_help()
    raise ExportError(f"auth not ready: {message}")


def check_scopes(scopes: str) -> None:
    proc = run_cli(["auth", "check", "--scope", scopes, "--json"], check=False)
    if proc.returncode == 0:
        return
    detail = proc.stderr.strip() or proc.stdout.strip()
    raise ExportError(f"required scopes are missing or unverifiable:\n{detail}")


def list_chats(args: argparse.Namespace, output_dir: Path) -> list[dict[str, Any]]:
    all_chats: list[dict[str, Any]] = []
    pages: list[Any] = []
    page_token = ""
    while True:
        cli_args = [
            "im",
            "+chat-list",
            "--as",
            args.identity,
            "--types",
            args.types,
            "--sort",
            args.sort,
            "--page-size",
            str(args.chat_page_size),
            "--format",
            "json",
        ]
        if args.exclude_muted:
            cli_args.append("--exclude-muted")
        if page_token:
            cli_args.extend(["--page-token", page_token])

        payload = parse_stdout_json(run_cli(cli_args, cwd=output_dir, timeout=args.cli_timeout))
        pages.append(payload)
        all_chats.extend(extract_chats(payload))
        if not has_more(payload):
            break
        page_token = next_page_token(payload)
        if not page_token:
            break
        time.sleep(args.sleep)

    return filter_chats(all_chats, args), pages


def filter_chats(chats: list[dict[str, Any]], args: argparse.Namespace) -> list[dict[str, Any]]:
    include = re.compile(args.include_chat_regex, re.I) if args.include_chat_regex else None
    exclude = re.compile(args.exclude_chat_regex, re.I) if args.exclude_chat_regex else None
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()

    for chat in chats:
        cid = render_lark_markdown.chat_id(chat)
        if cid in seen:
            continue
        seen.add(cid)
        name = render_lark_markdown.chat_name(chat)
        mode = render_lark_markdown.chat_mode(chat)
        haystack = f"{name}\n{cid}\n{mode}"
        if include and not include.search(haystack):
            continue
        if exclude and exclude.search(haystack):
            continue
        selected.append(chat)

    if args.limit_chats:
        selected = selected[: args.limit_chats]
    return selected


def fetch_messages_for_chat(chat: dict[str, Any], args: argparse.Namespace, output_dir: Path) -> int:
    cid = render_lark_markdown.chat_id(chat)
    raw_path = output_dir / "raw" / "messages" / f"{cid}.jsonl"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    if raw_path.exists() and not args.force:
        return len(render_lark_markdown.load_messages(raw_path))

    page_token = ""
    total = 0
    pages = 0
    with raw_path.open("w", encoding="utf-8") as handle:
        while True:
            cli_args = [
                "im",
                "+chat-messages-list",
                "--as",
                args.identity,
                "--chat-id",
                cid,
                "--order",
                "asc",
                "--page-size",
                str(args.message_page_size),
                "--format",
                "json",
            ]
            if args.start:
                cli_args.extend(["--start", args.start])
            if args.end:
                cli_args.extend(["--end", args.end])
            if args.no_reactions:
                cli_args.append("--no-reactions")
            attempted_resource_download = False
            if args.download_resources:
                cli_args.append("--download-resources")
                attempted_resource_download = True
            if page_token:
                cli_args.extend(["--page-token", page_token])

            message_page_retries = getattr(args, "message_page_retries", 3)
            page_attempt = 0
            while True:
                page_attempt += 1
                try:
                    payload = parse_stdout_json(run_cli(cli_args, cwd=output_dir, timeout=args.cli_timeout))
                    break
                except ExportError as exc:
                    if attempted_resource_download and "timed out" in str(exc):
                        retry_args = [part for part in cli_args if part != "--download-resources"]
                        print(
                            "warning: message page resource download timed out; retrying page without resources",
                            file=sys.stderr,
                        )
                        payload = parse_stdout_json(run_cli(retry_args, cwd=output_dir, timeout=args.cli_timeout))
                        break
                    if page_attempt > message_page_retries or not is_retryable_cli_error(exc):
                        raise
                    print(
                        f"warning: message page request failed transiently; retry {page_attempt}/{message_page_retries}",
                        file=sys.stderr,
                    )
                    time.sleep(max(args.sleep, 1.0) * page_attempt)
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
            messages = extract_messages(payload)
            total += len(messages)
            pages += 1
            if args.max_pages_per_chat and pages >= args.max_pages_per_chat:
                break
            if not has_more(payload):
                break
            page_token = next_page_token(payload)
            if not page_token:
                break
            time.sleep(args.sleep)

    return total


def write_state(output_dir: Path, state: dict[str, Any]) -> None:
    state["updated_at"] = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    (output_dir / "export_state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def export(args: argparse.Namespace) -> int:
    output_dir = args.output.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "raw").mkdir(exist_ok=True)

    check_auth_or_raise()
    if args.check_scopes:
        check_scopes(args.required_scopes)

    chats, pages = list_chats(args, output_dir)
    raw_chats = output_dir / "raw" / "chats.json"
    raw_chats.write_text(json.dumps(chats, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "raw" / "chat_pages.json").write_text(json.dumps(pages, ensure_ascii=False, indent=2), encoding="utf-8")

    state: dict[str, Any] = {
        "output": str(output_dir),
        "identity": args.identity,
        "types": args.types,
        "start": args.start,
        "end": args.end,
        "selected_chats": len(chats),
        "download_resources": args.download_resources,
        "chats": [],
    }

    for index, chat in enumerate(chats, start=1):
        cid = render_lark_markdown.chat_id(chat)
        name = render_lark_markdown.chat_name(chat)
        print(f"[{index}/{len(chats)}] {name} ({cid})", file=sys.stderr)
        try:
            count = fetch_messages_for_chat(chat, args, output_dir)
            state["chats"].append({"chat_id": cid, "name": name, "messages": count, "ok": True})
        except Exception as exc:  # noqa: BLE001 - keep long exports moving.
            state["chats"].append({"chat_id": cid, "name": name, "ok": False, "error": str(exc)})
            if not args.continue_on_error:
                write_state(output_dir, state)
                raise
        write_state(output_dir, state)

    index_path, chat_paths = render_lark_markdown.render_output(output_dir)
    print(f"index: {index_path}")
    print(f"chat_markdown_files: {len(chat_paths)}")
    for path in chat_paths:
        print(path)
    return 0


def retry_failed(args: argparse.Namespace) -> int:
    output_dir = args.output.expanduser().resolve()
    check_auth_or_raise()
    if args.check_scopes:
        check_scopes(args.required_scopes)

    state_path = output_dir / "export_state.json"
    chats_path = output_dir / "raw" / "chats.json"
    if not state_path.exists():
        raise ExportError(f"missing state file: {state_path}")
    if not chats_path.exists():
        raise ExportError(f"missing chat list: {chats_path}")

    state = json.loads(state_path.read_text(encoding="utf-8"))
    chats = json.loads(chats_path.read_text(encoding="utf-8"))
    failed_ids = {
        item.get("chat_id")
        for item in state.get("chats", [])
        if item.get("ok") is False and item.get("chat_id")
    }
    if args.chat_ids:
        requested_ids = {part.strip() for part in args.chat_ids.split(",") if part.strip()}
        failed_ids = failed_ids & requested_ids if failed_ids else requested_ids
    if not failed_ids:
        print("failed_chats: 0")
        index_path, chat_paths = render_lark_markdown.render_output(output_dir)
        print(f"index: {index_path}")
        print(f"chat_markdown_files: {len(chat_paths)}")
        return 0

    by_id = {render_lark_markdown.chat_id(chat): chat for chat in chats}
    missing_ids = sorted(cid for cid in failed_ids if cid not in by_id)
    if missing_ids:
        raise ExportError(f"failed chat ids missing from raw chat list: {', '.join(missing_ids)}")

    updated = {item.get("chat_id"): dict(item) for item in state.get("chats", []) if item.get("chat_id")}
    retry_args = argparse.Namespace(**vars(args))
    retry_args.force = True

    for index, cid in enumerate(sorted(failed_ids), start=1):
        print(f"[retry {index}/{len(failed_ids)}] {cid}", file=sys.stderr)
        try:
            count = fetch_messages_for_chat(by_id[cid], retry_args, output_dir)
            item = updated.get(cid, {"chat_id": cid})
            item.update({"messages": count, "ok": True})
            item.pop("error", None)
            updated[cid] = item
        except Exception as exc:  # noqa: BLE001 - keep retry batch moving.
            item = updated.get(cid, {"chat_id": cid})
            item.update({"ok": False, "error": str(exc)})
            updated[cid] = item
            if not args.continue_on_error:
                state["chats"] = list(updated.values())
                write_state(output_dir, state)
                raise
        state["chats"] = list(updated.values())
        write_state(output_dir, state)

    index_path, chat_paths = render_lark_markdown.render_output(output_dir)
    print(f"retried_chats: {len(failed_ids)}")
    print(f"index: {index_path}")
    print(f"chat_markdown_files: {len(chat_paths)}")
    return 0


def doctor(_args: argparse.Namespace) -> int:
    print("CLI command:")
    print(command_string(["--help"]))
    print("")
    ok, message, payload = auth_status()
    print(f"auth: {'ok' if ok else 'not ready'}")
    if not ok:
        print(message)
        print("")
        print_auth_help()
        return 2
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    doctor_parser = sub.add_parser("doctor", help="Check lark-cli and auth readiness")
    doctor_parser.set_defaults(func=doctor)

    export_parser = sub.add_parser("export", help="Export selected chats and render Markdown")
    export_parser.add_argument("--output", type=Path, required=True, help="Export directory")
    export_parser.add_argument("--identity", choices=["user", "bot"], default="user")
    export_parser.add_argument("--types", default="p2p,group", help="Chat types: group, p2p, or p2p,group")
    export_parser.add_argument("--sort", choices=["create_time", "active_time"], default="active_time")
    export_parser.add_argument("--start", help="Start time/date accepted by lark-cli, e.g. 2020-01-01")
    export_parser.add_argument("--end", help="End time/date accepted by lark-cli")
    export_parser.add_argument("--include-chat-regex", help="Only export chats whose name/id/mode matches")
    export_parser.add_argument("--exclude-chat-regex", help="Skip chats whose name/id/mode matches")
    export_parser.add_argument("--exclude-muted", action="store_true", help="Skip muted chats under user identity")
    export_parser.add_argument("--limit-chats", type=int, help="Sample or cap selected chats")
    export_parser.add_argument("--max-pages-per-chat", type=int, help="Sample or cap message pages per chat")
    export_parser.add_argument("--chat-page-size", type=int, default=100)
    export_parser.add_argument("--message-page-size", type=int, default=50)
    export_parser.add_argument("--sleep", type=float, default=0.2, help="Pause between paginated calls")
    export_parser.add_argument("--cli-timeout", type=float, default=120.0, help="Seconds to wait for each lark-cli call")
    export_parser.add_argument("--message-page-retries", type=int, default=3)
    export_parser.add_argument("--download-resources", action=argparse.BooleanOptionalAction, default=True)
    export_parser.add_argument("--no-reactions", action="store_true")
    export_parser.add_argument("--force", action="store_true", help="Overwrite existing raw message checkpoints")
    export_parser.add_argument("--continue-on-error", action="store_true", help="Continue when one chat fails")
    export_parser.add_argument("--check-scopes", action=argparse.BooleanOptionalAction, default=True)
    export_parser.add_argument("--required-scopes", default=DEFAULT_SCOPES)
    export_parser.set_defaults(func=export)

    retry_parser = sub.add_parser("retry-failed", help="Retry failed chats from an existing export state")
    retry_parser.add_argument("--output", type=Path, required=True, help="Export directory")
    retry_parser.add_argument("--identity", choices=["user", "bot"], default="user")
    retry_parser.add_argument("--start", help="Start time/date accepted by lark-cli, e.g. 2020-01-01")
    retry_parser.add_argument("--end", help="End time/date accepted by lark-cli")
    retry_parser.add_argument("--message-page-size", type=int, default=50)
    retry_parser.add_argument("--sleep", type=float, default=0.2, help="Pause between paginated calls")
    retry_parser.add_argument("--cli-timeout", type=float, default=120.0, help="Seconds to wait for each lark-cli call")
    retry_parser.add_argument("--message-page-retries", type=int, default=3)
    retry_parser.add_argument("--download-resources", action=argparse.BooleanOptionalAction, default=True)
    retry_parser.add_argument("--no-reactions", action="store_true")
    retry_parser.add_argument("--max-pages-per-chat", type=int, help="Sample or cap message pages per chat")
    retry_parser.add_argument("--chat-ids", help="Comma-separated chat ids to retry instead of all failed chats")
    retry_parser.add_argument("--continue-on-error", action="store_true", help="Continue when one chat retry fails")
    retry_parser.add_argument("--check-scopes", action=argparse.BooleanOptionalAction, default=True)
    retry_parser.add_argument("--required-scopes", default=DEFAULT_SCOPES)
    retry_parser.set_defaults(func=retry_failed)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return int(args.func(args))
    except ExportError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
