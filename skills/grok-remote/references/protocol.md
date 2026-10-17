# Grok desktop device protocol

Verified against the installed macOS Grok Bot 0.71.2 on 2026-10-18. These are internal endpoints discovered from the desktop client, not a public compatibility contract. The backend hostname is `api2.cursor.sh`, even though the installed application is named Grok Bot.

## Authentication and discovery

The desktop profile defaults to `~/Library/Application Support/Grok Bot`. Its `sand-secrets.json` contains a JSON-encoded `cursor-accounts` object with an active account and an encrypted `cursor-access-token`.

The helper reads the existing `Grok Bot Safe Storage` Keychain item with `security`, derives the existing Chromium v10 key (PBKDF2-HMAC-SHA1, salt `saltysalt`, 1003 rounds, 16 bytes), and uses the macOS system crypto library to decrypt the AES-CBC payload in memory. The SHA-256 of the JWT subject must match the active account scope. This scope comparison is a consistency check; the backend authenticates the token.

All requests use the fixed HTTPS backend, `Authorization: Bearer <existing-session>`, and `Connect-Protocol-Version: 1`. Redirects must fail rather than forward the bearer token elsewhere. Do not add an alternate backend or command-line token argument.

`POST /aiserver.v1.DashboardService/ListSandMachines` takes ordinary JSON `{}` with `Content-Type: application/json`. Relevant device fields are `machineId`, `label`, `connected`, `isCurrent`, `kind`, and `localToolPermission`. Discover devices afresh; do not ship cached account-specific IDs.

## Executing a terminal command

`POST /aiserver.v1.GrokBotService/OpenGrokBotUserComputerRequest` uses `Content-Type: application/connect+json`. Its body is a Connect envelope:

```text
flags byte (0) | JSON byte length (uint32 big endian) | UTF-8 JSON
```

Request shape, with independently generated UUIDs:

```json
{
  "machineId": "<discovered-machine-id>",
  "idempotencyKey": "<fresh-uuid>",
  "frame": {
    "requestId": "<fresh-uuid>",
    "exec": {
      "serverMessageJson": "<JSON-encoded ExecServerMessage>"
    }
  }
}
```

The embedded `ExecServerMessage` is:

```json
{
  "shellStreamArgs": {
    "command": "pwd",
    "workingDirectory": "",
    "timeout": 30000,
    "toolCallId": "<fresh-uuid>",
    "closeStdin": true
  }
}
```

The remote timeout is in milliseconds. An empty working directory leaves the default to Grok. The desktop daemon rewrites its internal execution ID.

Leave `approvalId`, `authorizedByStanding`, `authorizedByApproval`, and `skipApproval` absent. A server-authoritative daemon checks the authorization delivered through Grok. The registry's `localToolPermission=always` is not permission for an adapter to manufacture authorization flags. Live tests with all of those fields omitted successfully read the CPU and hostname on two existing registered Macs.

## Reading results

Responses use the same envelope layout. Flag `0` carries an ordinary JSON message; flag `2` is the end-stream JSON, which may include an `error`. Compression or other flag combinations require a protocol update rather than silent acceptance.

Grok may assign a new `requestId` for the operation. It need not match the submitted `frame.requestId` or `toolCallId`. Latch the first response ID, require subsequent response IDs to agree, and retain both the canonical ID and the submitted ID in results. The ordinary response has either:

- `client.messageJson`: a JSON-encoded client message. Its `shellStream` can contain `start`, `stdout.data`, `stderr.data`, or `exit`.
- `control.messageJson`: a control event such as `streamClose`.

The terminal field is `shellStream.exit.code` (uint32), with protobuf default zero when `code` is absent from an actual `exit` object. An absent `exit` object does not establish success. A clean end-stream is still required. Treat explicit server errors, missing exit, truncated envelopes, output limits, and network failure as unsuccessful observations; after dispatch, execution may have happened even when the final result is unavailable.

There is no automatic execution retry. Keep the submitted request ID, any server-assigned request ID, and the idempotency key in the local result for reconciliation. Closing the HTTP stream is not proof that the remote process stopped. The helper does not claim to implement cancellation, file-transfer frames, general local-tool frames, browser automation, or desktop control.

## Updating the adapter

The installed bundle's `app.asar` contains the protocol definitions under `dist/electron-main/proto.cjs` and the execution handler under `dist/local-exec-daemon/main.cjs`. Useful search terms are `OpenGrokBotUserComputerRequest`, `ShellArgs`, `ShellStream`, `handleExecRequest`, and `serverAuthoritative`.

Inspect only the relevant definitions. Do not commit extracted application code, token material, private roster snapshots, or raw account transcripts. Maintain synthetic fragmented-stream and failure fixtures, then verify the actual helper with a read-only `probe` on an explicitly selected device.
