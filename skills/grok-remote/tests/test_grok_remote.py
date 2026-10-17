import importlib.util
import io
import json
import struct
import tempfile
import unittest
import urllib.error
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "grok_remote.py"
SPEC = importlib.util.spec_from_file_location("grok_remote", SCRIPT)
grok_remote = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(grok_remote)


def frame(flag, value):
    payload = json.dumps(value, separators=(",", ":")).encode()
    return bytes([flag]) + struct.pack(">I", len(payload)) + payload


def event(request_id, shell_stream):
    return {
        "requestId": request_id,
        "client": {"messageJson": json.dumps({"id": "event", "shellStream": shell_stream})},
    }


class FakeResponse:
    def __init__(self, chunks):
        self.chunks = list(chunks)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, _size=-1):
        return self.chunks.pop(0) if self.chunks else b""


class FakeOpener:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.requests = []

    def open(self, request, timeout=None):
        self.requests.append((request, timeout))
        if self.error:
            raise self.error
        return self.response


class GrokRemoteTests(unittest.TestCase):
    def uuids(self):
        values = iter(["submitted-request", "idempotency", "tool"])
        return lambda: next(values)

    def test_fragmented_happy_stream_and_auth_flags_omitted(self):
        stream = b"".join(
            [
                frame(0, event("server-request", {"start": {}})),
                frame(0, event("server-request", {"stdout": {"data": "hello\n"}})),
                frame(0, event("server-request", {"stderr": {"data": "note\n"}})),
                frame(0, event("server-request", {"exit": {"cwd": "/tmp"}})),
                frame(2, {}),
            ]
        )
        chunks = [stream[:2], stream[2:9], stream[9:31], stream[31:]]
        opener = FakeOpener(FakeResponse(chunks))
        result = grok_remote.execute(
            "secret", "machine", "printf hello", opener=opener, uuid_factory=self.uuids()
        )
        self.assertEqual(result["exitCode"], 0)
        self.assertEqual(result["stdout"], "hello\n")
        self.assertEqual(result["stderr"], "note\n")
        self.assertEqual(result["requestId"], "server-request")
        self.assertEqual(result["submittedRequestId"], "submitted-request")
        request = opener.requests[0][0]
        self.assertEqual(
            request.full_url,
            "https://api2.cursor.sh/aiserver.v1.GrokBotService/OpenGrokBotUserComputerRequest",
        )
        self.assertEqual(len(opener.requests), 1)
        payload = json.loads(request.data[5:])
        self.assertEqual(payload["idempotencyKey"], "idempotency")
        serialized = request.data.decode("utf-8", errors="ignore")
        for forbidden in (
            "approvalId",
            "authorizedByStanding",
            "authorizedByApproval",
            "skipApproval",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_nonzero_exit_is_failed(self):
        body = frame(0, event("request", {"exit": {"code": 7}})) + frame(2, {})
        with self.assertRaises(grok_remote.ExecutionError) as caught:
            grok_remote.execute(
                "token",
                "machine",
                "false",
                opener=FakeOpener(FakeResponse([body])),
                uuid_factory=self.uuids(),
            )
        self.assertEqual(caught.exception.status, "failed")
        self.assertIn("code 7", caught.exception.message)
        self.assertEqual(caught.exception.exit_code, 7)

    def test_end_error_is_failed(self):
        body = frame(2, {"error": {"code": "permission_denied"}})
        with self.assertRaises(grok_remote.ExecutionError) as caught:
            grok_remote.execute(
                "token",
                "machine",
                "true",
                opener=FakeOpener(FakeResponse([body])),
                uuid_factory=self.uuids(),
            )
        self.assertEqual(caught.exception.status, "failed")

    def test_internal_end_error_before_activity_is_unknown(self):
        body = frame(2, {"error": {"code": "internal"}})
        with self.assertRaises(grok_remote.ExecutionError) as caught:
            grok_remote.execute(
                "token",
                "machine",
                "true",
                opener=FakeOpener(FakeResponse([body])),
                uuid_factory=self.uuids(),
            )
        self.assertEqual(caught.exception.status, "unknown")

    def test_http_rejection_is_failed_without_retry(self):
        error = urllib.error.HTTPError("https://redacted", 403, "denied", {}, io.BytesIO())
        opener = FakeOpener(error=error)
        with self.assertRaises(grok_remote.ExecutionError) as caught:
            grok_remote.execute(
                "token", "machine", "true", opener=opener, uuid_factory=self.uuids()
            )
        self.assertEqual(caught.exception.status, "failed")
        self.assertEqual(len(opener.requests), 1)

    def test_http_5xx_is_unknown_without_retry(self):
        error = urllib.error.HTTPError("https://redacted", 503, "unavailable", {}, io.BytesIO())
        opener = FakeOpener(error=error)
        with self.assertRaises(grok_remote.ExecutionError) as caught:
            grok_remote.execute(
                "token", "machine", "true", opener=opener, uuid_factory=self.uuids()
            )
        self.assertEqual(caught.exception.status, "unknown")
        self.assertEqual(len(opener.requests), 1)

    def test_redirect_is_refused_without_retry(self):
        error = urllib.error.HTTPError("https://redacted", 302, "redirect", {}, io.BytesIO())
        opener = FakeOpener(error=error)
        with self.assertRaises(grok_remote.ExecutionError) as caught:
            grok_remote.execute(
                "token", "machine", "true", opener=opener, uuid_factory=self.uuids()
            )
        self.assertIn("redirect refused", caught.exception.message)
        self.assertEqual(len(opener.requests), 1)

    def test_no_exit_and_unclean_eof_are_unknown(self):
        for body in (
            frame(2, {}),
            frame(0, event("request", {"exit": {}})),
        ):
            with self.subTest(body=body):
                with self.assertRaises(grok_remote.ExecutionError) as caught:
                    grok_remote.execute(
                        "token",
                        "machine",
                        "true",
                        opener=FakeOpener(FakeResponse([body])),
                        uuid_factory=self.uuids(),
                    )
                self.assertEqual(caught.exception.status, "unknown")

    def test_end_error_after_output_is_unknown_and_retains_output(self):
        body = (
            frame(0, event("request", {"stdout": {"data": "partial"}}))
            + frame(2, {"error": {"code": "internal"}})
        )
        with self.assertRaises(grok_remote.ExecutionError) as caught:
            grok_remote.execute(
                "token",
                "machine",
                "true",
                opener=FakeOpener(FakeResponse([body])),
                uuid_factory=self.uuids(),
            )
        self.assertEqual(caught.exception.status, "unknown")
        self.assertEqual(caught.exception.stdout, "partial")

    def test_control_error_is_unknown(self):
        control = {
            "control": {
                "messageJson": json.dumps({"streamClose": {"error": {"code": 1}}})
            }
        }
        with self.assertRaises(grok_remote.ExecutionError) as caught:
            grok_remote.execute(
                "token",
                "machine",
                "true",
                opener=FakeOpener(FakeResponse([frame(0, control)])),
                uuid_factory=self.uuids(),
            )
        self.assertEqual(caught.exception.status, "unknown")

    def test_invalid_utf8_command_file_is_structured_usage_error(self):
        with tempfile.NamedTemporaryFile() as command_file:
            command_file.write(b"\xff")
            command_file.flush()
            args = type("Args", (), {"command": None, "command_file": command_file.name})()
            with self.assertRaises(grok_remote.UsageError):
                grok_remote._command_from_args(args)

    def test_mismatched_response_request_id_is_unknown(self):
        body = (
            frame(0, event("server-request", {"start": {}}))
            + frame(0, event("different-request", {"exit": {}}))
            + frame(2, {})
        )
        with self.assertRaises(grok_remote.ExecutionError) as caught:
            grok_remote.execute(
                "token",
                "machine",
                "true",
                opener=FakeOpener(FakeResponse([body])),
                uuid_factory=self.uuids(),
            )
        self.assertEqual(caught.exception.status, "unknown")

    def test_fragment_truncation_is_unknown(self):
        partial = bytes([0]) + struct.pack(">I", 10) + b"{}"
        with self.assertRaises(grok_remote.ExecutionError) as caught:
            grok_remote.execute(
                "token",
                "machine",
                "true",
                opener=FakeOpener(FakeResponse([partial])),
                uuid_factory=self.uuids(),
            )
        self.assertEqual(caught.exception.status, "unknown")

    def test_output_limit_is_unknown(self):
        chunk = "x" * (grok_remote.MAX_OUTPUT_BYTES // 2 + 1)
        body = (
            frame(0, event("request", {"stdout": {"data": chunk}}))
            + frame(0, event("request", {"stdout": {"data": chunk}}))
        )
        with self.assertRaises(grok_remote.ExecutionError) as caught:
            grok_remote.execute(
                "token",
                "machine",
                "true",
                opener=FakeOpener(FakeResponse([body])),
                uuid_factory=self.uuids(),
            )
        self.assertEqual(caught.exception.status, "unknown")

    def test_aborted_exit_is_failed_even_when_code_is_omitted(self):
        body = frame(0, event("request", {"exit": {"aborted": True}})) + frame(2, {})
        with self.assertRaises(grok_remote.ExecutionError) as caught:
            grok_remote.execute(
                "token",
                "machine",
                "true",
                opener=FakeOpener(FakeResponse([body])),
                uuid_factory=self.uuids(),
            )
        self.assertEqual(caught.exception.status, "failed")
        self.assertEqual(caught.exception.exit_code, 0)

    def test_cli_usage_error_is_structured(self):
        output = io.StringIO()
        old_stdout = grok_remote.sys.stdout
        grok_remote.sys.stdout = output
        try:
            code = grok_remote.main(["exec", "--machine", "example"])
        finally:
            grok_remote.sys.stdout = old_stdout
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output.getvalue())["status"], "usage_error")

    def test_frame_limit_is_unknown(self):
        oversized_header = bytes([0]) + struct.pack(">I", grok_remote.MAX_FRAME_BYTES + 1)
        with self.assertRaises(grok_remote.ExecutionError) as caught:
            grok_remote.execute(
                "token",
                "machine",
                "true",
                opener=FakeOpener(FakeResponse([oversized_header])),
                uuid_factory=self.uuids(),
            )
        self.assertEqual(caught.exception.status, "unknown")

    def test_machine_resolution_unknown_ambiguous_and_offline(self):
        machines = [
            {"machineId": "id-1", "label": "same", "connected": True},
            {"machineId": "id-2", "label": "same", "connected": True},
            {"machineId": "id-3", "label": "off", "connected": False},
        ]
        with self.assertRaisesRegex(grok_remote.LocalError, "No machine"):
            grok_remote.resolve_machine(machines, "missing")
        with self.assertRaisesRegex(grok_remote.LocalError, "ambiguous"):
            grok_remote.resolve_machine(machines, "same")
        with self.assertRaisesRegex(grok_remote.LocalError, "offline"):
            grok_remote.resolve_machine(machines, "off")
        self.assertEqual(grok_remote.resolve_machine(machines, "id-1")["label"], "same")

    def test_list_normalizes_roster_and_does_not_expose_extra_fields(self):
        body = json.dumps(
            {
                "machines": [
                    {
                        "machineId": "example-id",
                        "label": "example-label",
                        "connected": True,
                        "kind": "darwin",
                        "secretField": "never-output",
                    }
                ]
            }
        ).encode()
        machines = grok_remote.list_machines("token", opener=FakeOpener(FakeResponse([body])))
        self.assertEqual(machines[0]["machineId"], "example-id")
        self.assertNotIn("secretField", machines[0])


if __name__ == "__main__":
    unittest.main()
