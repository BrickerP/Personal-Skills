# End-of-run checklist | 跑批结束清单

Use after every external ATS batch (`run-next.sh`, round scripts, or manual-retry). **No conversation context required** — all paths are absolute.

Related: `COLD-START.md` (preflight), `SKILL.md` (policy), `~/job-hunt/ROUND-MANIFEST.yaml` (active rounds).

---

## 1. Report template（终端汇报）

Emit in the final response:

- Date/time window (BJT)
- Channels used (Ashby / Greenhouse / manual-retry)
- Submitted / ManualFinish / Blocked / Skipped counts
- Curated PDF hash check: pass / drift
- `~/job-hunt/tracker.csv` rows touched
- `~/job-hunt/application-ledger.md` rows appended
- Vault archive paths (`applications/<channel>-batch-YYYY-MM-DD.md`) if Submitted
- **Manual finish pages** — open tabs with company, role, URL, remaining action

---

## 2. ManualFinish retry CSV schema

Used by `~/job-hunt/scripts/manual-retry-runner.py` and Ashby probe pools.

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

Run:

```bash
python3 ~/job-hunt/scripts/manual-retry-runner.py \
  --queue ~/job-hunt/candidate-pools/manual-retry-YYYYMMDD.csv \
  --allow-manual-retry
```

---

## 3. Greenhouse email verification chain

**Batch runs**: precheck marks `skip-email-verification` — not a batch slot.

**ManualFinish cleanup** (user explicitly requests or `manual` mode):

1. Confirm application tab + `yplmicro@gmail.com` Gmail share the same CDP `windowId`.
2. Read verification code from Gmail Inbox (`yplmicro@gmail.com` only).
3. Enter code:

```bash
node ~/Downloads/.omx/greenhouse_enter_security_code.cjs <target_id> <6-digit-code>
```

4. Re-run `ats_pre_submit_check.cjs` on the target; submit only if `{"ok":true,...}`.
5. On verified confirmation → tracker upsert + ledger + archive + close tab.

`greenhouse_enter_security_code.cjs` handles split `security-input-N` fields and single security/code fields via CDP `Runtime.evaluate`.

---

## 4. Close Submitted tabs

After **verified** confirmation page or confirmation email:

1. Upsert tracker + append ledger (see §5).
2. `job_archive.py emit` for non-LinkedIn channels.
3. **Close** the application Chrome tab (adapters call `close_success_tab` / `cdp_close_target`).

Leave tabs **open** only for `ManualFinish` (CAPTCHA, SMS, anti-spam, unknown final step).

---

## 5. Wrong-window cleanup

If `ats_pre_submit_check.cjs` returns `wrong-window`, `gmail-window-not-found`, or `cookiy-gmail-in-window`:

1. **Do not submit.**
2. Close the wrong-profile/wrong-window application tab copy.
3. Re-open the JD/application URL from the verified yplmicro Gmail window (`Browser.getWindowForTarget` match).
4. Re-fill or queue as `ManualFinish` if state was lost.

Never use `CDP.New` / bulk new-tab creation for application tabs (wrong profile risk).

---

## 6. Tracker upsert field mapping

Canonical file: `~/job-hunt/tracker.csv`

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
| `Notes` | adapter note + `resume=<variant>` | blocker code + `resume=<variant>` |

**Upsert key**: normalized `JD_URL` — update existing row if URL matches, else append.

**Ledger append** (`~/job-hunt/application-ledger.md`):

```
- YYYY-MM-DD HH:MM:SS CST | Submitted | Company - Role | <url> | <notes>
```

Escape `|` inside role titles.

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
