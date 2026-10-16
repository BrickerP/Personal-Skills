# End-of-run checklist | 投递结束清单

Use after every external ATS run (roles applied one by one with `chrome-use`, per `workflows/04-universal-web-apply.md`). **No conversation context required** — all paths are absolute.

Related: `COLD-START.md` (preflight), `SKILL.md` (policy), `workflows/04-universal-web-apply.md` (per-role procedure, FROZEN answers, pre-submit gate).

---

## 1. Report template（终端汇报）

Emit in the final response:

- Date/time window (BJT)
- Channels used (Ashby / Greenhouse / Lever / other)
- Submitted / ManualFinish / Blocked / Skipped counts
- Curated PDF hash check: pass / drift
- `~/job-hunt/tracker.csv` rows touched
- `~/job-hunt/application-ledger.md` rows appended
- Vault archive paths (`applications/<channel>-batch-YYYY-MM-DD.md`) if Submitted
- **Manual finish pages** — tabs handed to the user with `keep`: company, role, URL, tab label (`chrome-use --session jobapply tab <label>` re-selects a kept tab from the same session), remaining action

---

## 2. ManualFinish retry CSV schema

Legacy format of the ManualFinish retry queue files. The CSV queue itself is retired: the old runner `runtime/manual/manual-retry-runner.py` (and any `~/job-hunt/scripts/` copy) is orphaned — it calls the retired `archive/2026-10-cdp-retired/adapters/ashby_apply_applescript.py` — so do not run it. The schema stays here so existing queue files can still be read.

| Column | Required | Meaning |
|--------|----------|---------|
| `status` | yes | `auto_candidate` for agent apply; `manual` = review only |
| `company` | yes | Display company name |
| `role` | yes | Job title (commas OK — parser handles quoted CSV) |
| `url` | yes | Canonical application URL |
| `variant` | no | Resume bucket; legacy `AI Agent Infra` / `Backend Platform` / `General SWE` → 1P EN PDF |
| `blocker` | no | e.g. `platform-anti-bot`, `invalid-required-fields`, `skip-email-verification` |
| `action` | no | `apply` (default), `skip`, `mark-submitted` |
| `slug` | no | Ashby slug key |
| `posting_id` | no | Ashby posting UUID |
| `location` | no | Free text |
| `published` / `updated` | no | Metadata |

Example queue path: `~/job-hunt/candidate-pools/manual-retry-YYYYMMDD.csv`

An existing file is only a candidate list: the agent applies its `auto_candidate` rows role by role (`workflows/04-universal-web-apply.md`). ManualFinish tabs are handed to the user with `keep` and stay open until the user closes them (see "ManualFinish handoff" in that workflow).

---

## 3. Greenhouse email verification chain

Some Greenhouse boards ask for an email security code after Submit (`ATS-GREENHOUSE.md` §2.8). The agent solves it itself; hand off as `ManualFinish` (blocker `skip-email-verification`) only if Gmail cannot be read.

1. The connected profile is the gate: every `profile:` line `chrome-use` prints (the first command of a new or restarted session) must read `Lu (Profile 2, yplmicro@gmail.com)` (`COLD-START.md` step 3). chrome-use exposes no per-tab window id, so **profile identity, not window identity, is the gate** — a Gmail tab in another Chrome profile is not acceptable.
2. Read the code from the `yplmicro@gmail.com` Gmail Inbox only (sender `no-reply@us.greenhouse-mail.io`, subject `Security code for your application to <company>`). It is an 8-character alphanumeric code.
3. Select the application tab and enter the code:

```bash
chrome-use --session jobapply tab <label>        # re-select the application tab (refs belong to the active tab)
chrome-use --session jobapply snapshot -i        # find the security-input-N cells
chrome-use --session jobapply fill @eN <char>    # one character per security-input-N cell, in order
```

   Greenhouse splits the code into `security-input-1` … `security-input-N` on some boards and uses a single security/code field on others; a single field takes the whole code. If the submit button stays disabled after the last cell, set the cells the way `ATS-GREENHOUSE.md` §2.8 describes.
4. The submit button enables after the last cell. Run the pre-submit gate (`workflows/04-universal-web-apply.md`, "Pre-submit gate"); submit only when `ok` is true.
5. On verified confirmation → tracker upsert + ledger + archive + close tab (§4).

---

## 4. Close Submitted tabs

After **verified** confirmation page or confirmation email:

1. Upsert tracker + append ledger (see §6).
2. `job_archive.py emit` for non-LinkedIn channels.
3. **Close** only your own application tab: `chrome-use --session jobapply tab close <label>`.

Hand a tab to the user only for `ManualFinish` (CAPTCHA, SMS, anti-spam, unknown final step): select it (`chrome-use --session jobapply tab <label>`), then run a bare `chrome-use --session jobapply keep`. chrome-use reports a kept tab as left for the user and exempt from auto-close; it leaves the session and survives `close` and `session stop`. The user closes it, never the agent. Do not add `--as handoff` (fails on chrome-use 1.5.186). A ManualFinish tab that was not kept still belongs to the session, so `close`, `session stop` or the daemon's idle shutdown can take it away: keep it before moving on.

---

## 5. Wrong-profile cleanup

The only identity gate is the `profile:` line `chrome-use` prints whenever a session starts or restarts (closing a session's last tab ends it, so this can recur mid-run); it must read `Lu (Profile 2, yplmicro@gmail.com)`. Every command that can start the session carries `--browser yplmicro@gmail.com`. If a line reads anything else (`wrong-profile`), **STOP the whole run**. It is a run-level stop, not a ledger row:

1. **Do not fill or submit.**
2. Close only the tabs this run opened: `chrome-use --session jobapply tab close <label>`.
3. Fix the connection: `chrome-use browsers` must show `Lu` as CONNECTED.
4. Report the stop. A new run re-opens the JD/application URL with `chrome-use --session jobapply --browser yplmicro@gmail.com tab new --label <platform>-<company> "<url>"` so it lands under the connected profile.

Keep **one** application tab in the session at a time (a tab handed over with `keep` has left the session and no longer counts). Do not bulk-create tabs — extra tabs are how a page ends up under a profile you are not watching.

---

## 6. Tracker upsert field mapping

Canonical file: `~/job-hunt/tracker.csv` (it does not exist today; the empty shipped template is `state/tracker.csv`). The header shapes in use differ, so map the columns below **by name** and leave out any column the file's header lacks:

- 10-column template (`state/tracker.csv`): `Date,Company,Role,JD_URL,Channel,Stage,Application_Submitted,Response_Status,Resume_Variant,Notes`
- 13/14-column backups (`~/job-hunt/tracker.csv.bak.*`): the table below, with a trailing `Status` in the 14-column form

Which header becomes canonical is still open. `job_dedupe_check.py` reads `Date`, `Company`, `Role`, `JD_URL`, `Application_Submitted`, `Response_Status` and `Notes` by name.

| CSV column | Submitted example | ManualFinish example |
|------------|-------------------|----------------------|
| `Date` | `YYYY-MM-DD HH:MM:SS CST` | same |
| `Company` | company name | same |
| `Role` | role title | same |
| `JD_URL` | normalized URL (no trailing `/application`) | same |
| `Channel` | `Ashby Direct` / `Greenhouse official` / `Lever official` | same |
| `Referrer_Name` | `""` | `""` |
| `Referrer_LinkedIn` | `""` | `""` |
| `Message_Sent` | `No` | `No` |
| `Application_Submitted` | `Yes` | `No` |
| `Response_Status` | `Submitted` / `DuplicateSubmitted` | `ManualFinish` / `Blocked` |
| `Stage` | same as Response_Status | same |
| `Last_Updated` | same as Date | same |
| `Notes` | note + `resume=<variant>` | blocker code + `resume=<variant>` |

`DuplicateSubmitted` is the retired adapter's value for "already applied"; `job_dedupe_check.py` still honors it in old rows. New runs record an already-applied role as `Skipped` (`workflows/04-universal-web-apply.md`); the dedupe guard treats both as duplicates.

**Upsert key**: normalized `JD_URL` — update existing row if URL matches, else append.

**Ledger append** (`~/job-hunt/application-ledger.md`):

```
- YYYY-MM-DD HH:MM:SS CST | Submitted | Company - Role | <url> | <notes>
- YYYY-MM-DD HH:MM:SS CST | ManualFinish | Company - Role | <url> | manual-finish-needed:<blocker>
```

Keep a `|` on both sides of the status word: `job_dedupe_check.py` finds ManualFinish lines by `| ManualFinish |` and reads the blocker from the notes (`platform-anti-bot`, `phone-rejected` and CAPTCHA blockers then block the URL as a duplicate; `skip-email-verification`, `invalid-required-fields` and `unsupported-required:<label>` stay retryable). Escape `|` inside role titles.

**Vault archive** (Submitted only, non-LinkedIn):

```bash
python3 ~/.codex/skills/daily-job-apply/scripts/job_archive.py emit \
  --channel "<Channel>" \
  --date "$(TZ=Asia/Shanghai date +%Y-%m-%d)" \
  --status Submitted \
  --company "<Company>" \
  --role "<Role>" \
  --jd-url "<JD_URL>"
```

---

## 7. Do not create

- `~/job-hunt/manual-finish.md` — print open tabs in terminal/final response instead.

---

## 8. Email account

Job-search mailbox: **`yplmicro@gmail.com`** only. Never `ycd@cookiy.com` or `yupeng@cookiy.com` for applications.
