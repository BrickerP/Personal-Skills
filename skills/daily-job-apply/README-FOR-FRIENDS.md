# Cookiy Job Apply Skill — FULL package (friends)

> One zip, one skill tree, no `~/Downloads/.omx` scatter.

---

## 3-step start

### 1. Unzip → skill home

```bash
unzip cookiy-job-apply-skill-FULL-20260617.zip -d /tmp/job-apply-pack
cp -R /tmp/job-apply-pack/skills/daily-job-apply ~/.codex/skills/
cp -R /tmp/job-apply-pack/skills/chrome-read-write ~/.codex/skills/
chmod +x ~/.codex/skills/daily-job-apply/runtime/run-next.sh
chmod +x ~/.codex/skills/daily-job-apply/bin/chrome-debug.sh
```

### 2. Customize config only

```bash
cp ~/.codex/skills/daily-job-apply/data/profile.json.example \
   ~/.codex/skills/daily-job-apply/data/profile.json
# Edit profile.json: your name, email (example: yplmicro@gmail.com), LinkedIn, resume_paths

cd ~/.codex/skills/daily-job-apply/adapters && npm install && npx playwright install chromium
```

Optional env overrides: `~/.config/daily-job-apply/env` — see `INSTALL.md`.

### 3. Agent reads COLD-START.md, then run

```bash
# Agent: read ~/.codex/skills/daily-job-apply/COLD-START.md first
~/.codex/skills/daily-job-apply/runtime/run-next.sh
```

Modes: `gh` | `ashby` | `manual` | `auto` (default).

---

## What's inside

| Path | Role |
|------|------|
| `SKILL.md` | Full agent rules |
| `COLD-START.md` | Context-free cold start |
| `INSTALL.md` | Install + migration |
| `ROUND-MANIFEST.yaml` | Active Ashby/GH rounds |
| `runtime/run-next.sh` | **Single entry command** |
| `adapters/` | Ashby + Greenhouse apply scripts |
| `data/` | Block lists, skip slugs, `profile.json.example` |
| `state/tracker.csv` | Empty template (no PII) |
| `bin/chrome-debug.sh` | macOS Chrome CDP launcher |

Bundled companion skills (optional):

- `skills/job-search-orchestrator/` — morning triage dashboard
- `skills/chrome-read-write/` — CDP tab helpers

---

## macOS-only today

- Chrome Debug on **:9222** with isolated profile (`CHROME_PROFILE`, default `Profile 2`)
- Gmail **windowId** gate (same Chrome window as job-search Gmail tab)

Everything else (Python sourcing, manifest routing, adapters) is path-portable via `$SKILL_ROOT`.

---

## Not included (by design)

- Real `tracker.csv` rows / `application-ledger.md`
- `profile.json` with real PII (use `.example`)
- `ats-evolution-log.jsonl`
- `node_modules/` (run `npm install` in `adapters/`)

See `INSTALL.md` for migration from the old `~/job-hunt` + `~/.omx` layout.
