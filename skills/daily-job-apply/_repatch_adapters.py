#!/usr/bin/env python3
"""Clean re-patch adapter scripts from OMX source."""

from __future__ import annotations

import re
import shutil
import stat
from pathlib import Path

SKILL = Path.home() / ".codex" / "skills" / "daily-job-apply"
OMX = Path.home() / "Downloads" / ".omx"

ADAPTER_PY = [
    "ashby_apply_applescript.py",
    "ashby_apply_batch.py",
    "ashby_pool_dedupe.py",
    "greenhouse_playwright_batch.py",
    "greenhouse_embed_skip.py",
]

BOOTSTRAP = '''from __future__ import annotations

import os
import sys
from pathlib import Path

_RUNTIME = Path(__file__).resolve().parents[1] / "runtime"
if str(_RUNTIME) not in sys.path:
    sys.path.insert(0, str(_RUNTIME))
from paths import (  # noqa: E402
    ADAPTERS_DIR,
    DATA_DIR,
    SCRIPTS_DIR,
    SKILL_ROOT,
    WORK_DIR,
    TRACKER_CSV,
    PDF_DIR,
    resume_pdf,
)

sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(ADAPTERS_DIR))

'''


def patch_adapter(name: str) -> None:
    src = OMX / name
    dst = SKILL / "adapters" / name
    text = src.read_text(encoding="utf-8")
    text = re.sub(r"^#!/usr/bin/env python3\n", "", text)
    text = re.sub(r'^"""[\s\S]*?"""\n\n', "", text, count=1)
    text = re.sub(r"^from __future__ import annotations\n\n", "", text)

    doc = ""
    m = re.search(r'^"""[\s\S]*?"""\n\n', src.read_text(encoding="utf-8"))
    if m:
        doc = m.group(0)

    subs = [
        (r'Path\("/Users/yupeng/Downloads/\.omx/ashby_apply_applescript\.py"\)', "ADAPTERS_DIR / 'ashby_apply_applescript.py'"),
        (r'APPLY = Path\("/Users/yupeng/Downloads/\.omx/ashby_apply_applescript\.py"\)', "APPLY = ADAPTERS_DIR / 'ashby_apply_applescript.py'"),
        (r'Path\("/Users/yupeng/Downloads/\.omx/logs"\)', "ADAPTERS_DIR / 'logs'"),
        (r'HOME = Path\.home\(\)\n', ""),
        (r'TRACKER = HOME / "job-hunt" / "tracker\.csv"', "TRACKER = TRACKER_CSV"),
        (r'DEFAULT_CSV = HOME / "job-hunt" / "candidate-pools[^"]*"', "DEFAULT_CSV = WORK_DIR / 'candidate-pools' / 'ashby-fresh.csv'"),
        (r'SKILL_SCRIPTS = Path\.home\(\) / "\.codex" / "skills" / "daily-job-apply" / "scripts"', "SKILL_SCRIPTS = SCRIPTS_DIR"),
        (r'sys\.path\.insert\(0, str\(SKILL_SCRIPTS\)\)', ""),
        (r'EMBED_DATA_JSON = Path\.home\(\) / "job-hunt" / "data" / "embed-career-domains\.json"', "EMBED_DATA_JSON = DATA_DIR / 'embed-career-domains.json'"),
        (r'/Users/yupeng/Downloads/\.omx', "str(ADAPTERS_DIR)"),
        (r'/Users/yupeng/job-hunt', "str(WORK_DIR)"),
        (r'/Users/yupeng/\.codex/skills/daily-job-apply', "str(SKILL_ROOT)"),
    ]
    for pat, repl in subs:
        text = re.sub(pat, repl, text)

    out = "#!/usr/bin/env python3\n" + doc + BOOTSTRAP + text.lstrip()
    dst.write_text(out, encoding="utf-8")
    dst.chmod(0o755)
    print(f"OK adapters/{name}")


def patch_cjs(name: str) -> None:
    src = OMX / name
    dst = SKILL / "adapters" / name
    text = src.read_text(encoding="utf-8")
    helper = '''
function skillRoot() { return require('path').resolve(__dirname, '..'); }
function workDir() { return process.env.DAILY_JOB_APPLY_WORK_DIR || require('path').join(require('os').homedir(), 'job-hunt'); }
function dataDir() { return require('path').join(skillRoot(), 'data'); }
function pdfDir() {
  if (process.env.DAILY_JOB_APPLY_PDF_DIR) return process.env.DAILY_JOB_APPLY_PDF_DIR;
  try {
    const profile = JSON.parse(require('fs').readFileSync(require('path').join(dataDir(), 'profile.json'), 'utf8'));
    const rp = profile.resume_paths || {};
    const p = rp.ai_agent_1p_en || rp.default_en;
    if (p) return require('path').dirname(p);
  } catch (_) {}
  return require('path').join(require('os').homedir(), 'Documents', 'resumes');
}
'''
    if "function skillRoot()" not in text:
        text = text.replace("#!/usr/bin/env node\n", "#!/usr/bin/env node\n" + helper)
    text = text.replace(
        "const TRACKER = path.join(HOME, 'job-hunt', 'tracker.csv');",
        "const TRACKER = (() => { const st = path.join(skillRoot(), 'state', 'tracker.csv'); const wd = path.join(workDir(), 'tracker.csv'); return require('fs').existsSync(wd) && (!require('fs').existsSync(st) || require('fs').statSync(st).size < 80) ? wd : st; })();",
    )
    text = text.replace("const LEDGER = path.join(HOME, 'job-hunt', 'application-ledger.md');", "const LEDGER = path.join(workDir(), 'application-ledger.md');")
    text = text.replace("const SKILL = path.join(HOME, '.codex', 'skills', 'daily-job-apply');", "const SKILL = skillRoot();")
    text = text.replace("const APP_DIR = '/Users/yupeng/Documents/Obsidian Vault/Resume_YupengLu/application-ai-agent';", "const APP_DIR = pdfDir();")
    text = text.replace("const NODE_PATH_HINT = '/Users/yupeng/.npm/_npx/9833c18b2d85bc59/node_modules';", "const NODE_PATH_HINT = process.env.NODE_PATH || path.join(skillRoot(), 'adapters', 'node_modules');")
    text = text.replace("/Users/yupeng/Downloads/.omx", "path.join(skillRoot(), 'adapters')")
    text = text.replace("/Users/yupeng/job-hunt", "workDir()")
    dst.write_text(text, encoding="utf-8")
    dst.chmod(0o755)
    print(f"OK adapters/{name}")


def main() -> None:
    for name in ADAPTER_PY:
        patch_adapter(name)
    for name in ["greenhouse_playwright_apply.cjs", "greenhouse_enter_security_code.cjs", "greenhouse_current_sourcing.cjs"]:
        patch_cjs(name)
    for name in ["package.json", "package-lock.json"]:
        shutil.copy2(OMX / name, SKILL / "adapters" / name)
    print("adapters done")


if __name__ == "__main__":
    main()
