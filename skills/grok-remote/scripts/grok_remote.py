#!/usr/bin/env python3
"""Use the installed Grok Bot session to address one connected remote Mac."""

from __future__ import annotations

import argparse
import base64
import ctypes
import hashlib
import http.client
import json
import os
import struct
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any, BinaryIO, Iterable


BASE_URL = "https://api2.cursor.sh"
LIST_PATH = "/aiserver.v1.DashboardService/ListSandMachines"
EXEC_PATH = "/aiserver.v1.GrokBotService/OpenGrokBotUserComputerRequest"
DATA_ROOT = Path.home() / "Library/Application Support/Grok Bot"
MAX_FRAME_BYTES = 1024 * 1024
MAX_OUTPUT_BYTES = 1024 * 1024
PROBE_COMMAND = (
    "set -e; /usr/sbin/sysctl -n machdep.cpu.brand_string; "
    "/bin/hostname; /usr/bin/uname -a"
)


class LocalError(RuntimeError):
    """A local, authentication, selection, or pre-submission error."""


class UsageError(ValueError):
    """Invalid command-line input."""


class ExecutionError(RuntimeError):
    def __init__(
        self,
        message: str,
        status: str,
        submitted_request_id: str,
        idempotency_key: str,
        stdout: str = "",
        stderr: str = "",
        exit_code: int | None = None,
        request_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status = status
        self.submitted_request_id = submitted_request_id
        self.request_id = request_id
        self.idempotency_key = idempotency_key
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code

    def __str__(self) -> str:
        return self.message


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


def _opener() -> urllib.request.OpenerDirector:
    return urllib.request.build_opener(_NoRedirect)


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _account_scope(token: str) -> str | None:
    """Hash a JWT subject for provenance; this does not authenticate the token."""
    try:
        encoded = token.split(".")[1]
        claims = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
        subject = claims["sub"]
        if not isinstance(subject, str) or not subject:
            return None
        return hashlib.sha256(subject.encode()).hexdigest()
    except (IndexError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None


def access_token(data_root: Path = DATA_ROOT) -> str:
    """Decrypt the installed app's active token in memory using its Keychain item."""
    try:
        outer = json.loads((Path(data_root) / "sand-secrets.json").read_text())
        accounts = json.loads(outer["cursor-accounts"])
        active = accounts["active"]
        encrypted = accounts["accounts"][active]["cursor-access-token"]
        payload = base64.b64decode(encrypted, validate=True)
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        raise LocalError("The installed Grok Bot session is unavailable") from None
    if not payload.startswith(b"v10"):
        raise LocalError("Unsupported app credential format; no credentials were exported")

    try:
        result = subprocess.run(
            ["/usr/bin/security", "find-generic-password", "-ws", "Grok Bot Safe Storage"],
            capture_output=True,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise LocalError(
            "macOS Keychain access failed; allow the existing Grok Bot session read and retry"
        ) from None
    if result.returncode:
        raise LocalError("The existing Grok Bot Keychain entry is unavailable")

    try:
        key = hashlib.pbkdf2_hmac("sha1", result.stdout.rstrip(b"\n"), b"saltysalt", 1003, 16)
        lib = ctypes.CDLL("/usr/lib/libSystem.B.dylib")
        lib.CCCrypt.argtypes = [
            ctypes.c_uint,
            ctypes.c_uint,
            ctypes.c_uint,
            ctypes.c_void_p,
            ctypes.c_size_t,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_size_t,
            ctypes.c_void_p,
            ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_size_t),
        ]
        ciphertext = payload[3:]
        output = ctypes.create_string_buffer(len(ciphertext) + 16)
        output_size = ctypes.c_size_t()
        status = lib.CCCrypt(
            1,
            0,
            1,
            key,
            len(key),
            b" " * 16,
            ciphertext,
            len(ciphertext),
            output,
            len(output),
            ctypes.byref(output_size),
        )
        if status:
            raise ValueError
        token = output.raw[: output_size.value].decode("utf-8")
    except (AttributeError, OSError, UnicodeDecodeError, ValueError):
        raise LocalError("Could not decrypt the existing Grok Bot session") from None
    if _account_scope(token) != active:
        raise LocalError("Stored active account does not match the existing login token")
    return token


def _request(
    path: str,
    token: str,
    body: bytes,
    content_type: str,
) -> urllib.request.Request:
    return urllib.request.Request(
        BASE_URL + path,
        data=body,
        method="POST",
        headers={
            "Authorization": "Bearer " + token,
            "Content-Type": content_type,
            "Connect-Protocol-Version": "1",
            "Accept-Encoding": "identity",
        },
    )


def _safe_http_error(action: str, error: urllib.error.HTTPError) -> LocalError:
    if 300 <= error.code < 400:
        return LocalError(f"{action}: redirect refused")
    return LocalError(f"{action}: HTTP {error.code}")


def list_machines(
    token: str,
    *,
    opener: urllib.request.OpenerDirector | Any | None = None,
    timeout: float = 30,
) -> list[dict[str, Any]]:
    request = _request(LIST_PATH, token, b"{}", "application/json")
    try:
        with (opener or _opener()).open(request, timeout=timeout) as response:
            raw = response.read(MAX_FRAME_BYTES + 1)
    except urllib.error.HTTPError as error:
        raise _safe_http_error("list", error) from None
    except (OSError, TimeoutError, urllib.error.URLError, http.client.HTTPException):
        raise LocalError("list: network unavailable") from None
    if len(raw) > MAX_FRAME_BYTES:
        raise LocalError("list: response exceeds size limit")
    try:
        decoded = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise LocalError("list: invalid server response") from None
    candidates = (
        decoded.get("machines", decoded.get("sandMachines"))
        if isinstance(decoded, dict)
        else None
    )
    if not isinstance(candidates, list):
        raise LocalError("list: machine roster is missing")
    result = []
    fields = (
        "machineId",
        "label",
        "isCurrent",
        "kind",
        "localToolPermission",
        "messagesEnabled",
        "connected",
        "lastRegisteredAtMs",
    )
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        result.append({field: candidate.get(field) for field in fields})
    return result


def resolve_machine(machines: Iterable[dict[str, Any]], selector: str) -> dict[str, Any]:
    exact_ids = [machine for machine in machines if machine.get("machineId") == selector]
    matches = exact_ids or [machine for machine in machines if machine.get("label") == selector]
    if not matches:
        raise LocalError(f"No machine matches {selector!r}")
    if len(matches) != 1:
        raise LocalError(f"Machine selector {selector!r} is ambiguous")
    machine = matches[0]
    if machine.get("connected") is not True:
        raise LocalError(f"Machine {selector!r} is offline")
    machine_id = machine.get("machineId")
    if not isinstance(machine_id, str) or not machine_id:
        raise LocalError(f"Machine {selector!r} has no usable ID")
    return machine


def _connect_frame(flag: int, value: Any) -> bytes:
    payload = _json_bytes(value)
    if len(payload) > MAX_FRAME_BYTES:
        raise UsageError("request exceeds frame size limit")
    return bytes([flag]) + struct.pack(">I", len(payload)) + payload


def _read_connect_frames(stream: BinaryIO, deadline: float):
    buffer = bytearray()
    ended = False
    read = getattr(stream, "read1", stream.read)
    while not ended:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError
        _set_read_timeout(stream, remaining)
        chunk = read(64 * 1024)
        if not chunk:
            if buffer:
                raise ValueError("truncated Connect frame")
            break
        buffer.extend(chunk)
        while len(buffer) >= 5:
            flag = buffer[0]
            length = struct.unpack(">I", buffer[1:5])[0]
            if length > MAX_FRAME_BYTES:
                raise ValueError("Connect frame exceeds size limit")
            if len(buffer) < 5 + length:
                break
            payload = bytes(buffer[5 : 5 + length])
            del buffer[: 5 + length]
            if flag not in (0, 2):
                raise ValueError(f"unsupported Connect flag {flag}")
            try:
                value = json.loads(payload)
            except (UnicodeDecodeError, json.JSONDecodeError):
                raise ValueError("invalid Connect JSON") from None
            yield flag, value
            if flag == 2:
                if buffer:
                    raise ValueError("data after Connect end frame")
                ended = True
                break


def _set_read_timeout(stream: BinaryIO, seconds: float) -> None:
    """Best-effort socket deadline tightening for urllib HTTP response streams."""
    fp = getattr(stream, "fp", None)
    raw = getattr(fp, "raw", None)
    candidates = (stream, getattr(stream, "raw", None), raw, getattr(raw, "_sock", None))
    for candidate in candidates:
        setter = getattr(candidate, "settimeout", None)
        if setter is not None:
            try:
                setter(max(0.001, seconds))
            except OSError:
                pass
            return


def _append_output(parts: list[str], data: Any, current_bytes: int) -> int:
    if not isinstance(data, str):
        raise ValueError("shell output is not text")
    size = len(data.encode("utf-8"))
    if current_bytes + size > MAX_OUTPUT_BYTES:
        raise ValueError("remote output exceeds size limit")
    parts.append(data)
    return current_bytes + size


def _contains_error(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            ("error" in str(key).lower() and bool(item)) or _contains_error(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_error(item) for item in value)
    return False


def _is_clear_rejection(error: Any) -> bool:
    if not isinstance(error, dict):
        return False
    code = error.get("code")
    if isinstance(code, str):
        return code.lower().replace("-", "_") in {
            "invalid_argument",
            "not_found",
            "permission_denied",
            "failed_precondition",
            "unimplemented",
            "unauthenticated",
        }
    return isinstance(code, int) and not isinstance(code, bool) and code in {3, 5, 7, 9, 12, 16}


def execute(
    token: str,
    machine_id: str,
    command: str,
    *,
    cwd: str = "",
    timeout: int = 30,
    opener: urllib.request.OpenerDirector | Any | None = None,
    uuid_factory=uuid.uuid4,
) -> dict[str, Any]:
    if not command:
        raise UsageError("command must not be empty")
    if cwd and not os.path.isabs(cwd):
        raise UsageError("remote working directory must be absolute")
    if not 1 <= timeout <= 300:
        raise UsageError("timeout must be between 1 and 300 seconds")

    request_id = str(uuid_factory())
    idempotency_key = str(uuid_factory())
    tool_call_id = str(uuid_factory())
    server_message = {
        "shellStreamArgs": {
            "command": command,
            "workingDirectory": cwd,
            "timeout": timeout * 1000,
            "toolCallId": tool_call_id,
            "closeStdin": True,
        }
    }
    payload = {
        "machineId": machine_id,
        "idempotencyKey": idempotency_key,
        "frame": {
            "requestId": request_id,
            "exec": {"serverMessageJson": json.dumps(server_message, separators=(",", ":"))},
        },
    }
    body = _connect_frame(0, payload)
    request = _request(EXEC_PATH, token, body, "application/connect+json")
    stdout_parts: list[str] = []
    stderr_parts: list[str] = []
    output_bytes = 0
    exit_event: dict[str, Any] | None = None
    clean_end = False
    execution_seen = False
    response_request_id: str | None = None
    deadline = time.monotonic() + timeout + 5

    try:
        response = (opener or _opener()).open(request, timeout=timeout + 5)
        with response:
            for flag, envelope in _read_connect_frames(response, deadline):
                if flag == 2:
                    if not isinstance(envelope, dict):
                        raise ValueError("invalid Connect end frame")
                    if envelope.get("error"):
                        clear_rejection = not execution_seen and _is_clear_rejection(
                            envelope["error"]
                        )
                        raise ExecutionError(
                            "Remote service rejected the execution"
                            if clear_rejection
                            else "Execution ended with a server error; remote status is unknown",
                            "failed" if clear_rejection else "unknown",
                            request_id,
                            idempotency_key,
                            "".join(stdout_parts),
                            "".join(stderr_parts),
                        )
                    clean_end = True
                    continue
                if not isinstance(envelope, dict):
                    raise ValueError("invalid execution envelope")
                incoming_request_id = envelope.get("requestId")
                if incoming_request_id:
                    if not isinstance(incoming_request_id, str):
                        raise ValueError("invalid execution response request ID")
                    if response_request_id is None:
                        response_request_id = incoming_request_id
                    elif incoming_request_id != response_request_id:
                        raise ValueError("execution response request ID mismatch")
                if envelope.get("error"):
                    raise ExecutionError(
                        "Execution stream reported an error; remote status is unknown",
                        "unknown",
                        request_id,
                        idempotency_key,
                        "".join(stdout_parts),
                        "".join(stderr_parts),
                    )
                control = envelope.get("control")
                if control is not None:
                    if not isinstance(control, dict) or not isinstance(
                        control.get("messageJson"), str
                    ):
                        raise ValueError("invalid control message")
                    try:
                        control_message = json.loads(control["messageJson"])
                    except json.JSONDecodeError:
                        raise ValueError("invalid control message JSON") from None
                    if not isinstance(control_message, dict):
                        raise ValueError("invalid control message payload")
                    if _contains_error(control_message):
                        raise ExecutionError(
                            "Execution control stream reported an error; remote status is unknown",
                            "unknown",
                            request_id,
                            idempotency_key,
                            "".join(stdout_parts),
                            "".join(stderr_parts),
                        )
                client = envelope.get("client")
                if not isinstance(client, dict) or not isinstance(client.get("messageJson"), str):
                    continue
                try:
                    message = json.loads(client["messageJson"])
                except json.JSONDecodeError:
                    raise ValueError("invalid client message JSON") from None
                shell_stream = message.get("shellStream") if isinstance(message, dict) else None
                if not isinstance(shell_stream, dict):
                    continue
                execution_seen = execution_seen or any(
                    key in shell_stream for key in ("start", "stdout", "stderr", "exit")
                )
                if "stdout" in shell_stream:
                    if exit_event is not None:
                        raise ValueError("stdout received after shell exit")
                    if not isinstance(shell_stream["stdout"], dict):
                        raise ValueError("invalid stdout event")
                    output_bytes = _append_output(
                        stdout_parts, shell_stream["stdout"].get("data"), output_bytes
                    )
                elif "stderr" in shell_stream:
                    if exit_event is not None:
                        raise ValueError("stderr received after shell exit")
                    if not isinstance(shell_stream["stderr"], dict):
                        raise ValueError("invalid stderr event")
                    output_bytes = _append_output(
                        stderr_parts, shell_stream["stderr"].get("data"), output_bytes
                    )
                elif "exit" in shell_stream:
                    if exit_event is not None:
                        raise ValueError("duplicate shell exit event")
                    if not isinstance(shell_stream["exit"], dict):
                        raise ValueError("invalid shell exit event")
                    exit_event = shell_stream["exit"]
                elif "rejected" in shell_stream or "permissionDenied" in shell_stream:
                    raise ExecutionError(
                        "Remote execution was rejected",
                        "failed",
                        request_id,
                        idempotency_key,
                        "".join(stdout_parts),
                        "".join(stderr_parts),
                    )
    except ExecutionError as error:
        if error.request_id is None:
            error.request_id = response_request_id
        raise
    except urllib.error.HTTPError as error:
        if error.code >= 500:
            raise ExecutionError(
                f"Execution request failed (HTTP {error.code}); remote status is unknown",
                "unknown",
                request_id,
                idempotency_key,
                request_id=response_request_id,
            ) from None
        message = (
            "Execution redirect refused"
            if 300 <= error.code < 400
            else f"Remote service rejected the execution (HTTP {error.code})"
        )
        raise ExecutionError(
            message,
            "failed",
            request_id,
            idempotency_key,
            request_id=response_request_id,
        ) from None
    except KeyboardInterrupt:
        raise ExecutionError(
            "Execution was interrupted locally; remote status is unknown",
            "unknown",
            request_id,
            idempotency_key,
            "".join(stdout_parts),
            "".join(stderr_parts),
            request_id=response_request_id,
        ) from None
    except (
        OSError,
        TimeoutError,
        urllib.error.URLError,
        http.client.HTTPException,
        ValueError,
    ):
        raise ExecutionError(
            "Execution stream failed; remote status is unknown",
            "unknown",
            request_id,
            idempotency_key,
            "".join(stdout_parts),
            "".join(stderr_parts),
            request_id=response_request_id,
        ) from None

    if not clean_end or exit_event is None:
        raise ExecutionError(
            "Execution stream ended without a confirmed exit; remote status is unknown",
            "unknown",
            request_id,
            idempotency_key,
            "".join(stdout_parts),
            "".join(stderr_parts),
            request_id=response_request_id,
        )
    code = exit_event.get("code", 0)
    if not isinstance(code, int) or isinstance(code, bool) or code < 0:
        raise ExecutionError(
            "Remote exit code was invalid; remote status is unknown",
            "unknown",
            request_id,
            idempotency_key,
            "".join(stdout_parts),
            "".join(stderr_parts),
            request_id=response_request_id,
        )
    result = {
        "status": "completed" if code == 0 and not exit_event.get("aborted") else "failed",
        "requestId": response_request_id,
        "submittedRequestId": request_id,
        "idempotencyKey": idempotency_key,
        "exitCode": code,
        "cwd": exit_event.get("cwd", ""),
        "stdout": "".join(stdout_parts),
        "stderr": "".join(stderr_parts),
    }
    if code != 0 or exit_event.get("aborted"):
        reason = (
            "Remote command was aborted"
            if exit_event.get("aborted")
            else f"Remote command exited with code {code}"
        )
        raise ExecutionError(
            reason,
            "failed",
            request_id,
            idempotency_key,
            result["stdout"],
            result["stderr"],
            code,
            response_request_id,
        )
    return result


def _emit(value: dict[str, Any]) -> None:
    print(json.dumps(value, ensure_ascii=False, separators=(",", ":")))


class _JSONArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise UsageError(message)


def _parser() -> argparse.ArgumentParser:
    parser = _JSONArgumentParser(prog="grok_remote.py")
    subparsers = parser.add_subparsers(dest="action", required=True)
    subparsers.add_parser("list", help="list the current Grok Bot machine roster")

    probe = subparsers.add_parser("probe", help="run a fixed identity probe")
    probe.add_argument("--machine", required=True)
    probe.add_argument("--timeout", type=int, default=30)

    execute_parser = subparsers.add_parser("exec", help="run one remote shell command")
    execute_parser.add_argument("--machine", required=True)
    command_group = execute_parser.add_mutually_exclusive_group(required=True)
    command_group.add_argument("--command")
    command_group.add_argument("--command-file", metavar="PATH", help="read command from PATH or -")
    execute_parser.add_argument("--cwd", default="")
    execute_parser.add_argument("--timeout", type=int, default=30)
    return parser


def _command_from_args(args: argparse.Namespace) -> str:
    if args.command is not None:
        return args.command
    try:
        if args.command_file == "-":
            return sys.stdin.read()
        return Path(args.command_file).read_text()
    except (OSError, UnicodeError):
        raise UsageError("could not read command file") from None


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    try:
        args = parser.parse_args(argv)
        command = None
        if args.action != "list" and not 1 <= args.timeout <= 300:
            raise UsageError("timeout must be between 1 and 300 seconds")
        if args.action == "exec":
            command = _command_from_args(args)
            if not command:
                raise UsageError("command must not be empty")
            if args.cwd and not os.path.isabs(args.cwd):
                raise UsageError("remote working directory must be absolute")
        token = access_token()
        machines = list_machines(token)
        if args.action == "list":
            _emit({"status": "ok", "machines": machines})
            return 0
        machine = resolve_machine(machines, args.machine)
        command = PROBE_COMMAND if args.action == "probe" else command
        assert command is not None
        result = execute(
            token,
            machine["machineId"],
            command,
            cwd=getattr(args, "cwd", ""),
            timeout=args.timeout,
        )
        result["machine"] = {"machineId": machine["machineId"], "label": machine.get("label")}
        _emit(result)
        return 0
    except UsageError as error:
        _emit({"status": "usage_error", "error": str(error)})
        return 2
    except ExecutionError as error:
        payload = {
                "status": error.status,
                "error": error.message,
                "requestId": error.request_id,
                "submittedRequestId": error.submitted_request_id,
                "idempotencyKey": error.idempotency_key,
                "stdout": error.stdout,
                "stderr": error.stderr,
            }
        if error.exit_code is not None:
            payload["exitCode"] = error.exit_code
        _emit(payload)
        return 1
    except LocalError as error:
        _emit({"status": "failed", "error": str(error)})
        return 1
    except KeyboardInterrupt:
        _emit({"status": "failed", "error": "Interrupted before execution submission"})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
