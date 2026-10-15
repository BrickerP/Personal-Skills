# INSTALL.md — daily-job-apply self-contained skill

All runtime scripts live under `~/.codex/skills/daily-job-apply/`. No `~/Downloads/.omx` or scattered `~/job-hunt/scripts` required for new installs.

---

## Fresh install (recommended)

```bash
unzip cookiy-job-apply-skill-FULL-20260617.zip -d /tmp/job-apply-pack
cp -R /tmp/job-apply-pack/skills/daily-job-apply ~/.codex/skills/
cp -R /tmp/job-apply-pack/skills/chrome-read-write ~/.codex/skills/    # optional but recommended
cp -R /tmp/job-apply-pack/skills/job-search-orchestrator ~/.codex/skills/  # optional
chmod +x ~/.codex/skills/daily-job-apply/runtime/run-next.sh
chmod +x ~/.codex/skills/daily-job-apply/bin/chrome-debug.sh
```

### Profile + tracker

```bash
cp ~/.codex/skills/daily-job-apply/data/profile.json.example \
   ~/.codex/skills/daily-job-apply/data/profile.json
# Edit name, email, LinkedIn, resume_paths

mkdir -p ~/.config/daily-job-apply
cat > ~/.config/daily-job-apply/env << 'EOF'
# Optional overrides (all paths expand ~)
DAILY_JOB_APPLY_PDF_DIR=~/Documents/resumes
CHROME_PROFILE=Profile 2
GMAIL_PROFILE=Profile 2
# DAILY_JOB_APPLY_WORK_DIR=~/job-hunt
# DAILY_JOB_APPLY_TRACKER=~/.codex/skills/daily-job-apply/state/tracker.csv
EOF
```

### Node adapters

```bash
cd ~/.codex/skills/daily-job-apply/adapters && npm install
npx playwright install chromium
```

### Chrome Debug symlink (optional convenience)

```bash
mkdir -p ~/bin
ln -sf ~/.codex/skills/daily-job-apply/bin/chrome-debug.sh ~/bin/chrome-debug.sh
```

### Verify

```bash
python3 ~/.codex/skills/daily-job-apply/runtime/read_manifest.py
bash -n ~/.codex/skills/daily-job-apply/runtime/run-next.sh
~/.codex/skills/daily-job-apply/bin/chrome-debug.sh
curl -s http://127.0.0.1:9222/json/version | head -c 80
```

---

## Migration from old layout (Yupeng / existing users)

If you already have `~/job-hunt/` with tracker, pools, and ledger:

1. **Keep** `~/job-hunt/` as work directory (pools, logs, ledger stay there).
2. **Replace** `~/job-hunt/run-next.sh` with the thin wrapper (forwards to skill).
3. **Stop using** `~/Downloads/.omx` — adapters are now `~/.codex/skills/daily-job-apply/adapters/`.
4. Add to `~/.config/daily-job-apply/env`:

```bash
DAILY_JOB_APPLY_WORK_DIR=~/job-hunt
DAILY_JOB_APPLY_TRACKER=~/job-hunt/tracker.csv
DAILY_JOB_APPLY_PDF_DIR=~/Documents/Obsidian\ Vault/Resume_YupengLu/application-ai-agent
CHROME_PROFILE=Profile 2
```

5. `~/job-hunt/ROUND-MANIFEST.yaml` is deprecated; canonical manifest is `$SKILL_ROOT/ROUND-MANIFEST.yaml`.

### Path map (old → new)

| Old | New |
|-----|-----|
| `~/Downloads/.omx/*.py` | `~/.codex/skills/daily-job-apply/adapters/` |
| `~/job-hunt/run_greenhouse_round18.py` | `.../runtime/greenhouse/run_round18.py` |
| `~/job-hunt/scripts/round110-batch.sh` | `.../runtime/ashby/round110-batch.sh` |
| `~/job-hunt/scripts/manual-retry-runner.py` | `.../runtime/manual/manual-retry-runner.py` |
| `~/job-hunt/ROUND-MANIFEST.yaml` | `.../ROUND-MANIFEST.yaml` |
| `~/job-hunt/data/*.json` | `.../data/*.json` (skill root) |
| `~/bin/chrome-debug.sh` | `.../bin/chrome-debug.sh` |

---

## macOS requirements (honest)

- **Google Chrome** with a dedicated Debug profile (`Chrome-Debug` user-data-dir)
- **CDP port 9222** reachable on localhost
- **AppleScript / `open -g`** for Chrome launch (macOS only today)
- **Python 3.10+**, **Node.js** for Playwright adapters

Linux/Windows: read Chrome tabs via CDP is possible; `bin/chrome-debug.sh` and Gmail window isolation are macOS-specific.

---

## Cursor / Claude symlinks

```bash
mkdir -p ~/.cursor/skills ~/.claude/skills
ln -sf ~/.codex/skills/daily-job-apply ~/.cursor/skills/daily-job-apply
ln -sf ~/.codex/skills/daily-job-apply ~/.claude/skills/daily-job-apply
```
