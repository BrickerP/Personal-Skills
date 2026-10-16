# INSTALL.md — daily-job-apply self-contained skill

All runtime scripts live under `~/.codex/skills/daily-job-apply/`. No `~/Downloads/.omx` or scattered `~/job-hunt/scripts` required for new installs.

---

## Fresh install (recommended)

```bash
unzip cookiy-job-apply-skill-FULL-20260617.zip -d /tmp/job-apply-pack
cp -R /tmp/job-apply-pack/skills/daily-job-apply ~/.codex/skills/
cp -R /tmp/job-apply-pack/skills/chrome-use ~/.codex/skills/            # browser control
cp -R /tmp/job-apply-pack/skills/job-search-orchestrator ~/.codex/skills/  # optional
```

### chrome-use CLI

`chrome-use` is a standalone CLI, not only a skill directory — install the binary and connect it to the real Chrome once:

```bash
curl -fsSL https://raw.githubusercontent.com/leeguooooo/chrome-use/main/install.sh | sh
chrome-use browsers     # needs profile `Lu` (yplmicro@gmail.com) to show CONNECTED
```

`chrome-use` drives the user's real, already-logged-in Chrome; applications run in its named session `jobapply` (`workflows/04-universal-web-apply.md`).

### Profile + tracker

```bash
cp ~/.codex/skills/daily-job-apply/data/profile.json.example \
   ~/.codex/skills/daily-job-apply/data/profile.json
# Edit name, email, LinkedIn, resume_paths

mkdir -p ~/.config/daily-job-apply
cat > ~/.config/daily-job-apply/env << 'EOF'
# Optional overrides (all paths expand ~)
DAILY_JOB_APPLY_PDF_DIR=~/Documents/resumes
# DAILY_JOB_APPLY_WORK_DIR=~/job-hunt
# DAILY_JOB_APPLY_TRACKER=~/.codex/skills/daily-job-apply/state/tracker.csv
# CHROME_USE_BIN=chrome-use
# Phone numbers live only in this file, never in the repo — fill them in:
JOB_APPLY_PHONE=
JOB_APPLY_PHONE_CN=
EOF
```

`cat >` overwrites an existing env file (which may already hold your phone numbers): if one exists, edit it instead.

### Optional: Greenhouse sourcing helper

Applying uses `chrome-use`, not Playwright. Only `adapters/greenhouse_current_sourcing.cjs` (job sourcing, not applying) still needs Node: it imports `playwright` and launches its own headless system Chrome (`channel: 'chrome'`). Not verified end to end.

```bash
cd ~/.codex/skills/daily-job-apply/adapters && npm install
```

### Verify

```bash
python3 ~/.codex/skills/daily-job-apply/scripts/ats_platform_classify.py \
  --url "https://jobs.ashbyhq.com/acme/00000000-0000-0000-0000-000000000000/application"   # expect "status": "playbook", "apply_allowed": true
chrome-use browsers                            # profile `Lu` shows CONNECTED
chrome-use --session jobapply tab list --full  # must print: profile: Lu (Profile 2, yplmicro@gmail.com)
```

---

## Migration from old layout (Yupeng / existing users)

If you already have `~/job-hunt/` with tracker, pools, and ledger:

1. **Keep** `~/job-hunt/` as work directory (pools, logs, ledger stay there).
2. **Stop using** `~/job-hunt/run-next.sh` and `runtime/run-next.sh`: the batch engine is retired (`runtime/run-next.sh` is a stub that exits 2). Roles are applied one at a time with `chrome-use` (`workflows/04-universal-web-apply.md`).
3. **Stop using** `~/Downloads/.omx` — the old CDP/Playwright apply scripts are retired. The author's checkout keeps reference copies under `archive/2026-10-cdp-retired/`; that folder is not part of the friends' zip. The platform knowledge now lives in `ATS-GREENHOUSE.md`, `ATS-ASHBY.md` and `ATS-BLOCKERS.md`.
4. Add to `~/.config/daily-job-apply/env` (append; do not overwrite your phone numbers):

```bash
DAILY_JOB_APPLY_WORK_DIR=~/job-hunt
DAILY_JOB_APPLY_TRACKER=~/job-hunt/tracker.csv
DAILY_JOB_APPLY_PDF_DIR=~/Documents/Obsidian\ Vault/Resume_YupengLu/application-ai-agent
```

5. `ROUND-MANIFEST.yaml` and `runtime/read_manifest.py` are orphaned: they only fed the retired batch engine.

### Path map (old → new)

| Old | New |
|-----|-----|
| `~/Downloads/.omx/*.py` | apply scripts retired (reference copies only in the author's checkout under `archive/2026-10-cdp-retired/`, not in the friends' zip); other helpers in `.../adapters/` |
| `~/job-hunt/data/*.json` | `.../data/*.json` (skill root) |

Orphaned (non-functional, never run them): `ROUND-MANIFEST.yaml`, `runtime/read_manifest.py`, `adapters/ashby_apply_batch.py`, `adapters/greenhouse_playwright_batch.py`, `runtime/greenhouse/run_round13.py`, `runtime/greenhouse/run_round18.py`, `runtime/manual/manual-retry-runner.py`, `runtime/ashby/round110-batch.sh`.

---

## macOS requirements (honest)

- **Google Chrome** running with the user's real, already-logged-in profile (this machine: `Lu` / `yplmicro@gmail.com`)
- **chrome-use** CLI installed and connected to that profile
- **Python 3.10+**; **Node.js** only for the optional Greenhouse sourcing helper

Linux/Windows: `chrome-use` is portable, but the `profile:` check described in `COLD-START.md` has only been validated on macOS.

---

## Cursor / Claude symlinks

```bash
mkdir -p ~/.cursor/skills ~/.claude/skills
ln -sf ~/.codex/skills/daily-job-apply ~/.cursor/skills/daily-job-apply
ln -sf ~/.codex/skills/daily-job-apply ~/.claude/skills/daily-job-apply
```
