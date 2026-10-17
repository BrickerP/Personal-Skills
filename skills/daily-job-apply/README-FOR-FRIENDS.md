# Cookiy Job Apply Skill — FULL package (friends)

> One zip, one skill tree, no `~/Downloads/.omx` scatter.

---

## 3-step start

### 1. Unzip → skill home

```bash
unzip cookiy-job-apply-skill-FULL-20260617.zip -d /tmp/job-apply-pack
cp -R /tmp/job-apply-pack/skills/daily-job-apply ~/.codex/skills/
cp -R /tmp/job-apply-pack/skills/chrome-use ~/.codex/skills/
```

Browser work uses the `chrome-use` CLI (drives your real, already-logged-in Chrome). Install the binary if you don't have it:

```bash
curl -fsSL https://raw.githubusercontent.com/leeguooooo/chrome-use/main/install.sh | sh
```

### 2. Customize config only

```bash
cp ~/.codex/skills/daily-job-apply/data/profile.json.example \
   ~/.codex/skills/daily-job-apply/data/profile.json
# Edit profile.json: your name, email (example: yplmicro@gmail.com), LinkedIn, resume_paths
```

Optional env overrides: `~/.config/daily-job-apply/env` — see `INSTALL.md`. Your phone number goes only there (`JOB_APPLY_PHONE`), never in the repo.

The standard application answers (identity, contact, location, work authorization, years, education, AI usage) live in the FROZEN section of `workflows/04-universal-web-apply.md` (stealth retired 2026-10-18 — real names allowed). The shipped values are the original author's — edit that section to match you before applying.

### 3. Agent reads COLD-START.md, then applies

Tell your agent to read `~/.codex/skills/daily-job-apply/COLD-START.md` first (PDF hash check, `chrome-use` profile check), then to apply role by role with `chrome-use` following `workflows/04-universal-web-apply.md`. There is no batch command: `runtime/run-next.sh` is a retired stub that exits 2.

---

## What's inside

| Path | Role |
|------|------|
| `SKILL.md` | Full agent rules |
| `COLD-START.md` | Context-free cold start |
| `INSTALL.md` | Install + migration |
| `END-OF-RUN.md` | End-of-run checklist (tracker, ledger, tabs) |
| `workflows/04-universal-web-apply.md` | Role-by-role apply procedure, FROZEN answers, pre-submit gate |
| `ATS-GREENHOUSE.md`, `ATS-ASHBY.md`, `ATS-BLOCKERS.md` | Per-platform playbooks and blocker codes |
| `data/` | Block lists, skip slugs, `profile.json.example` |
| `state/tracker.csv` | Empty template (no PII) |

Bundled companion skills (optional):

- `skills/job-search-orchestrator/` — morning triage dashboard
- `skills/chrome-use/` — real-Chrome control via the `chrome-use` CLI

---

## macOS-only today

- `chrome-use` driving the real Chrome (profile `Lu` / `yplmicro@gmail.com`)
- The `profile:` check (the connected profile must read `Lu (Profile 2, yplmicro@gmail.com)`)

Everything else (Python helpers, tracker and ledger paths) is path-portable via `$SKILL_ROOT`.

---

## Not included (by design)

- Real `tracker.csv` rows / `application-ledger.md`
- `profile.json` with real PII (use `.example`)
- `ats-evolution-log.jsonl`
- `node_modules/` (only the optional sourcing helper needs it: `npm install` in `adapters/`, see `INSTALL.md`)

See `INSTALL.md` for migration from the old `~/job-hunt` + `~/.omx` layout.
