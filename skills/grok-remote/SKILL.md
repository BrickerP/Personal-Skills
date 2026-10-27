---
name: grok-remote
description: Reuse the macOS Grok Bot login and its existing device channel to discover computers, verify their identity, and execute authorized remote terminal commands. Use for Grok-connected Macs, including machines on other networks.
metadata:
  opencode/autoinvoke: false
---

# Grok Remote

Run terminal commands on a computer already registered and online in Grok Bot. The bundled Python CLI uses the existing desktop login and Grok's cloud relay; SSH, a VPN, and inbound ports are not required for this channel.

Requirements: macOS, Python 3.9+, an existing signed-in Grok Bot desktop app, and Grok running on the target computer. Authentication may show the normal macOS Keychain prompt for the existing Grok Bot Safe Storage item. Credentials stay in process memory.

## Use

Run these commands from this skill's directory, resolving its installed location first.

```bash
python3 scripts/grok_remote.py list
python3 scripts/grok_remote.py probe --machine 'Laptop'
python3 scripts/grok_remote.py exec --machine 'Laptop' --command 'pwd' --timeout 30
```

Select one online computer by its exact label or full machine ID from `list`. Duplicate labels require the ID. Before a first execution, or when the requested hardware identity matters, use `probe` to verify the CPU and hostname; labels alone do not establish the chip model. Keep private device IDs and hostnames out of shared examples and commits.

For a multiline command, use a local UTF-8 file so shell quoting cannot change its contents:

```bash
python3 scripts/grok_remote.py exec --machine 'Laptop' --command-file /absolute/path/to/command.sh --timeout 60
```

`--cwd` selects an absolute remote working directory. Without it, Grok chooses the working directory. `--timeout` is in seconds, from 1 to 300. See `--help` for the available options.

Results are JSON on stdout. Exit status `0` means discovery succeeded (`status: ok`) or the command completed successfully (`status: completed`); `1` means failure or uncertain execution (`status: failed` or `unknown`); `2` means invalid CLI input. Execution results include `requestId`, `submittedRequestId`, `idempotencyKey`, `stdout`, `stderr`, and `exitCode` when known. Grok can replace the submitted ID with a server-assigned request ID; preserve both for reconciliation. Output is bounded to 1 MiB; exceeding that limit leaves execution uncertain.

## Execution boundaries

- Execute the user's requested remote work within its existing scope. Access to a device does not grant authority for unrelated actions.
- Use the helper's normal server authorization path. It deliberately omits approval IDs and authorization assertions. Do not add `authorizedByStanding`, `authorizedByApproval`, or `skipApproval`, change device permissions, or fabricate approvals to make a rejected request work.
- Read the JSON execution status and remote exit code. A streamed output chunk alone does not prove completion; a successful command needs its exit frame and a clean end of stream.
- An interrupted connection, timeout, or malformed stream after submission leaves execution uncertain. Preserve the request ID and idempotency key, report the uncertainty, and reconcile the remote state before any retry. The helper never automatically retries an execution or claims that closing the client killed the remote process.
- Keep command output private when it contains user data. Never print or persist the session token, Keychain secret, signed credentials, or raw authentication responses.

This skill currently provides device discovery and terminal execution. Browser control, desktop control, Grok cloud tools, and bot messaging are separate capabilities and are not implemented by this helper.

## Maintenance

This is an adapter for an internal Grok Bot protocol, verified against desktop version 0.71.2 on 2026-10-18. It depends on the existing login, device availability, and server permissions; it is not a supported public Grok SDK.

For protocol changes, authentication failures, or stream errors, read [references/protocol.md](references/protocol.md). Inspect the installed client to confirm changed fields, update focused tests, and run:

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile scripts/grok_remote.py
```

Use `list` and `probe` for live validation. Do not run a mutating remote command solely to test the transport. Keep runtime state, account exports, captured streams, app bundles, and real credentials outside this skill repository.
