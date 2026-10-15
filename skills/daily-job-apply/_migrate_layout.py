#!/usr/bin/env python3
"""One-shot layout migration: copy runtime scripts into skill tree and patch paths."""

from __future__ import annotations

import re
import shutil
import stat
from pathlib import Path

SKILL = Path.home() / ".codex" / "skills" / "daily-job-apply"
JOB_HUNT = Path.home() / "job-hunt"
OMX = Path.home() / "Downloads" / ".omx"

ADAPTER_FILES = [
    "ashby_apply_applescript.py",
    "ashby_apply_batch.py",
    "ashby_pool_dedupe.py",
    "greenhouse_playwright_apply.cjs",
    "greenhouse_playwright_batch.py",
    "greenhouse_embed_skip.py",
    "greenhouse_enter_security_code.cjs",
    "greenhouse_current_sourcing.cjs",
    "package.json",
    "package-lock.json",
]

GH_FILES = {
    JOB_HUNT / "run_greenhouse_round13.py": SKILL / "runtime/greenhouse/run_round13.py",
    JOB_HUNT / "run_greenhouse_round18.py": SKILL / "runtime/greenhouse/run_round18.py",
}

ASHBY_FILES = {
    JOB_HUNT / "scripts/round110-batch.sh": SKILL / "runtime/ashby/round110-batch.sh",
    JOB_HUNT / "scripts/ashby_mine_round110_sources.py": SKILL / "runtime/ashby/ashby_mine_round110_sources.py",
    JOB_HUNT / "scripts/ashby_mine_github_repos.py": SKILL / "runtime/ashby/ashby_mine_github_repos.py",
    JOB_HUNT / "scripts/ashby_form_probe_gate.py": SKILL / "runtime/ashby/ashby_form_probe_gate.py",
    JOB_HUNT / "scripts/round80_probe_first_gate.py": SKILL / "runtime/ashby/probe_first_gate.py",
}

MANUAL_FILES = {
    JOB_HUNT / "scripts/manual-retry-runner.py": SKILL / "runtime/manual/manual-retry-runner.py",
}

PATH_REPLACEMENTS = [
    (r'Path\("/Users/yupeng/Downloads/\.omx"\)', "ADAPTERS_DIR"),
    (r'Path\.home\(\) / "Downloads" / "\.omx"', "ADAPTERS_DIR"),
    (r'Path\.home\(\) / "job-hunt" / "data"', "DATA_DIR"),
    (r'Path\.home\(\) / "job-hunt"', "WORK_DIR"),
    (r'Path\.home\(\) / "\.codex" / "skills" / "daily-job-apply"', "SKILL_ROOT"),
    (r'Path\.home\(\) / "\.codex" / "skills" / "daily-job-apply" / "data"', "DATA_DIR"),
    (r'Path\.home\(\) / "\.codex" / "skills" / "daily-job-apply" / "scripts"', "SCRIPTS_DIR"),
    (r'HOME / "job-hunt"', "WORK_DIR"),
    (r'HOME / "Downloads" / "\.omx"', "ADAPTERS_DIR"),
    (r'"/Users/yupeng/Downloads/\.omx"', '"$ADAPTERS_DIR"'),
    (r'"/Users/yupeng/job-hunt"', '"$WORK_DIR"'),
    (r'/Users/yupeng/job-hunt', "$WORK_DIR"),
    (r'/Users/yupeng/Downloads/\.omx', "$ADAPTERS_DIR"),
    (r'/Users/yupeng/\.codex/skills/daily-job-apply', "$SKILL_ROOT"),
    (
        r'/Users/yupeng/Documents/Obsidian Vault/Resume_YupengLu/application-ai-agent',
        "${DAILY_JOB_APPLY_PDF_DIR:-$HOME/Documents/resumes}",
    ),
    (r'"/Users/yupeng/\.npm/_npx/9833c18b2d85bc59/node_modules"', '"$NODE_PATH"'),
    (r'NODE_PATH = "/Users/yupeng/\.npm/_npx/9833c18b2d85bc59/node_modules"', "NODE_PATH = os.environ.get('NODE_PATH', str(NODE_MODULES))"),
    (r'OMX = Path\.home\(\) / "Downloads" / "\.omx"', "OMX = ADAPTERS_DIR"),
    (r'JOB_HUNT = Path\.home\(\) / "job-hunt"', "JOB_HUNT = WORK_DIR"),
    (r'JOB_HUNT_DATA = JOB_HUNT / "data"', "JOB_HUNT_DATA = DATA_DIR"),
    (r'SKILL_DATA = Path\.home\(\) / "\.codex" / "skills" / "daily-job-apply" / "data"', "SKILL_DATA = DATA_DIR"),
    (r'EMBED_DATA_JSON = Path\.home\(\) / "job-hunt" / "data" / "embed-career-domains\.json"', "EMBED_DATA_JSON = DATA_DIR / 'embed-career-domains.json'"),
    (r'import run_greenhouse_round13 as r13', "import run_round13 as r13  # noqa: E402"),
    (r'from run_greenhouse_round13 import', "from run_round13 import"),
    (r'sys\.path\.insert\(0, str\(JOB_HUNT\)\)', "# JOB_HUNT path via paths module"),
    (r'sys\.path\.insert\(0, str\(OMX\)\)', "# ADAPTERS_DIR path via paths module"),
    (r'round80_probe_first_gate', "probe_first_gate"),
    (r'PROBE_FIRST_GATE=/Users/yupeng/job-hunt/scripts/round80_probe_first_gate\.py', 'PROBE_FIRST_GATE="$RUNTIME_ROOT/ashby/probe_first_gate.py"'),
]

PY_PATHS_BOOTSTRAP = '''\
from __future__ import annotations

import os
import sys
from pathlib import Path

_RUNTIME = Path(__file__).resolve().parents[1]
if str(_RUNTIME) not in sys.path:
    sys.path.insert(0, str(_RUNTIME))
from paths import (  # noqa: E402
    ADAPTERS_DIR,
    DATA_DIR,
    JOB_HUNT,
    JOB_HUNT_DATA,
    NODE_MODULES,
    NODE_PATH,
    SCRIPTS_DIR,
    SKILL_DATA,
    SKILL_ROOT,
    WORK_DIR,
    TRACKER_CSV,
    PDF_DIR,
    resume_pdf,
)

_GH_DIR = Path(__file__).resolve().parent
if str(_GH_DIR) not in sys.path:
    sys.path.insert(0, str(_GH_DIR))
sys.path.insert(0, str(ADAPTERS_DIR))
sys.path.insert(0, str(SCRIPTS_DIR))
if NODE_PATH:
    os.environ.setdefault("NODE_PATH", NODE_PATH)

'''


def patch_python(text: str, depth: int = 2) -> str:
    if "from paths import" not in text:
        # Insert bootstrap after module docstring / shebang
        lines = text.splitlines(keepends=True)
        insert_at = 0
        if lines and lines[0].startswith("#!"):
            insert_at = 1
        if insert_at < len(lines) and lines[insert_at].startswith('"""'):
            i = insert_at + 1
            while i < len(lines):
                if '"""' in lines[i]:
                    insert_at = i + 1
                    break
                i += 1
        bootstrap = PY_PATHS_BOOTSTRAP.replace(
            "parents[1]", f"parents[{depth}]"
        )
        lines.insert(insert_at, bootstrap)
        text = "".join(lines)
    for pattern, repl in PATH_REPLACEMENTS:
        text = re.sub(pattern, repl, text)
    return text


def patch_bash(text: str) -> str:
    if "skill_paths.sh" not in text:
        header = '''#!/usr/bin/env bash
set -euo pipefail
_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../skill_paths.sh
source "$_SCRIPT_DIR/../skill_paths.sh"

'''
        # strip existing shebang + set -euo
        text = re.sub(r'^#!/usr/bin/env bash\n', "", text)
        text = re.sub(r'^set -euo pipefail\n', "", text)
        text = header + text
    for pattern, repl in PATH_REPLACEMENTS:
        text = re.sub(pattern, repl, text)
    # Fix hardcoded LOG paths
    text = re.sub(
        r'LOG=/Users/yupeng/job-hunt/round110\.log',
        'LOG="$WORK_DIR/round110.log"',
        text,
    )
    text = re.sub(
        r'POOL_DIR=/Users/yupeng/job-hunt/candidate-pools',
        'POOL_DIR="$CANDIDATE_POOLS_DIR"',
        text,
    )
    text = re.sub(
        r'LOCKDIR=/Users/yupeng/job-hunt/\.round110-batch\.lockdir',
        'LOCKDIR="$WORK_DIR/.round110-batch.lockdir"',
        text,
    )
    text = re.sub(
        r'APPLY_LOCKDIR=/Users/yupeng/job-hunt/\.ashby-apply\.lockdir',
        'APPLY_LOCKDIR="$WORK_DIR/.ashby-apply.lockdir"',
        text,
    )
    text = re.sub(
        r'Path\("/Users/yupeng/job-hunt/\.round110-batch\.lockdir"\)',
        'Path(os.environ.get("WORK_DIR", str(WORK_DIR)) + "/.round110-batch.lockdir")',
        text,
    )
    return text


def patch_cjs(text: str) -> str:
    bootstrap = '''const path = require('path');
const os = require('os');
const fs = require('fs');

function skillRoot() {
  return path.resolve(__dirname, '..');
}
function workDir() {
  return process.env.DAILY_JOB_APPLY_WORK_DIR || path.join(os.homedir(), 'job-hunt');
}
function dataDir() {
  return path.join(skillRoot(), 'data');
}
function pdfDir() {
  if (process.env.DAILY_JOB_APPLY_PDF_DIR) return process.env.DAILY_JOB_APPLY_PDF_DIR;
  try {
    const profile = JSON.parse(fs.readFileSync(path.join(dataDir(), 'profile.json'), 'utf8'));
    const rp = profile.resume_paths || {};
    const p = rp.ai_agent_1p_en || rp.default_en;
    if (p) return path.dirname(p);
  } catch (_) {}
  return path.join(os.homedir(), 'Documents', 'resumes');
}

'''
    if "function skillRoot()" not in text:
        # after shebang
        text = re.sub(r"(#!/usr/bin/env node\n)", r"\1" + bootstrap, text, count=1)
    text = text.replace(
        "const TRACKER = path.join(HOME, 'job-hunt', 'tracker.csv');",
        "const TRACKER = process.env.DAILY_JOB_APPLY_TRACKER || path.join(skillRoot(), 'state', 'tracker.csv');\n"
        "if (!fs.existsSync(TRACKER) && fs.existsSync(path.join(workDir(), 'tracker.csv'))) { /* use work */ }",
    )
    text = re.sub(
        r"const TRACKER = path\.join\(HOME, 'job-hunt', 'tracker\.csv'\);",
        "const TRACKER = (() => { const st = path.join(skillRoot(), 'state', 'tracker.csv'); const wd = path.join(workDir(), 'tracker.csv'); return fs.existsSync(wd) && (!fs.existsSync(st) || fs.statSync(st).size < 80) ? wd : st; })();",
        text,
    )
    text = re.sub(
        r"const LEDGER = path\.join\(HOME, 'job-hunt', 'application-ledger\.md'\);",
        "const LEDGER = path.join(workDir(), 'application-ledger.md');",
        text,
    )
    text = re.sub(
        r"const SKILL = path\.join\(HOME, '\.codex', 'skills', 'daily-job-apply'\);",
        "const SKILL = skillRoot();",
        text,
    )
    text = re.sub(
        r"const APP_DIR = '/Users/yupeng/Documents/Obsidian Vault/Resume_YupengLu/application-ai-agent';",
        "const APP_DIR = pdfDir();",
        text,
    )
    text = re.sub(
        r"const NODE_PATH_HINT = '/Users/yupeng/\.npm/_npx/9833c18b2d85bc59/node_modules';",
        "const NODE_PATH_HINT = process.env.NODE_PATH || path.join(skillRoot(), 'adapters', 'node_modules');",
        text,
    )
    text = text.replace("/Users/yupeng/Downloads/.omx", "path.join(skillRoot(), 'adapters')")
    text = text.replace("/Users/yupeng/job-hunt", "workDir()")
    text = text.replace("/Users/yupeng/.codex/skills/daily-job-apply", "skillRoot()")
    return text


def copy_and_patch(src: Path, dst: Path, kind: str) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    text = src.read_text(encoding="utf-8")
    if kind == "py":
        depth = len(dst.relative_to(SKILL).parts) - 1
        text = patch_python(text, depth=depth)
    elif kind == "sh":
        text = patch_bash(text)
    elif kind == "cjs":
        text = patch_cjs(text)
    dst.write_text(text, encoding="utf-8")
    if src.suffix in {".sh", ".py"} or src.name.endswith(".cjs"):
        dst.chmod(dst.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def main() -> None:
    for name in ADAPTER_FILES:
        src = OMX / name
        if src.exists():
            kind = "cjs" if name.endswith(".cjs") else "py" if name.endswith(".py") else "raw"
            dst = SKILL / "adapters" / name
            if kind == "raw":
                shutil.copy2(src, dst)
            else:
                copy_and_patch(src, dst, kind)

    for mapping in (GH_FILES, ASHBY_FILES, MANUAL_FILES):
        for src, dst in mapping.items():
            if not src.exists():
                print(f"SKIP missing {src}")
                continue
            kind = "sh" if src.suffix == ".sh" else "py"
            copy_and_patch(src, dst, kind)
            print(f"OK {dst.relative_to(SKILL)}")

    # __init__.py for greenhouse package
    (SKILL / "runtime/greenhouse/__init__.py").write_text("", encoding="utf-8")
    print("Migration copy+patch done.")


if __name__ == "__main__":
    main()
