#!/usr/bin/env python3
"""Clean re-patch ashby + manual runtime scripts."""

from __future__ import annotations

import re
import stat
from pathlib import Path

SKILL = Path.home() / ".codex" / "skills" / "daily-job-apply"
JH = Path.home() / "job-hunt"

BOOTSTRAP = '''from __future__ import annotations

import os
import sys
from pathlib import Path

_RUNTIME = Path(__file__).resolve().parents[{depth}]
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

sys.path.insert(0, str(ADAPTERS_DIR))
sys.path.insert(0, str(SCRIPTS_DIR))

'''


def patch_py(src: Path, dst: Path, depth: int = 1) -> None:
    text = src.read_text(encoding="utf-8")
    text = re.sub(r"^#!/usr/bin/env python3\n", "", text)
    doc = ""
    m = re.search(r'^"""[\s\S]*?"""\n\n', text)
    if m:
        doc = m.group(0)
        text = text[len(doc) :]
    text = re.sub(r"^from __future__ import annotations\n\n", "", text)
    subs = [
        (r'HOME = Path\.home\(\)\n', ""),
        (r'DEFAULT_LOG = HOME / "job-hunt[^"]*"', "DEFAULT_LOG = WORK_DIR / 'manual-retry.log'"),
        (r'DEFAULT_LOCKDIR = HOME / "job-hunt[^"]*"', "DEFAULT_LOCKDIR = WORK_DIR / '.ashby-apply.lockdir'"),
        (r'DEDUPE = HOME / "\.codex[^"]*"', "DEDUPE = SCRIPTS_DIR / 'job_dedupe_check.py'"),
        (r'APPLY = HOME / "Downloads[^"]*"', "APPLY = ADAPTERS_DIR / 'ashby_apply_applescript.py'"),
        (r'TRACKER = HOME / "job-hunt" / "tracker\.csv"', "TRACKER = TRACKER_CSV"),
        (r'/Users/yupeng/Downloads/\.omx', "str(ADAPTERS_DIR)"),
        (r'/Users/yupeng/job-hunt', "str(WORK_DIR)"),
        (r'/Users/yupeng/\.codex/skills/daily-job-apply', "str(SKILL_ROOT)"),
    ]
    for pat, repl in subs:
        text = re.sub(pat, repl, text)
    out = "#!/usr/bin/env python3\n" + doc + BOOTSTRAP.format(depth=depth) + text.lstrip()
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(out, encoding="utf-8")
    dst.chmod(0o755)


def patch_round110_sh() -> None:
    src = JH / "scripts/round110-batch.sh"
    text = src.read_text(encoding="utf-8")
    header = '''#!/usr/bin/env bash
set -euo pipefail
_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$_SCRIPT_DIR/../skill_paths.sh"

'''
    text = re.sub(r"^#!/usr/bin/env bash\n", "", text)
    text = re.sub(r"^set -euo pipefail\n", "", text)
    repl = [
        ("/Users/yupeng/job-hunt", "$WORK_DIR"),
        ("/Users/yupeng/Downloads/.omx", "$ADAPTERS_DIR"),
        ("/Users/yupeng/.codex/skills/daily-job-apply", "$SKILL_ROOT"),
        ("$HOME/.codex/skills/daily-job-apply", "$SKILL_ROOT"),
        ("$HOME/job-hunt/scripts/ashby_mine_round110_sources.py", "$RUNTIME_ROOT/ashby/ashby_mine_round110_sources.py"),
        ("$HOME/job-hunt/scripts/ashby_mine_github_repos.py", "$RUNTIME_ROOT/ashby/ashby_mine_github_repos.py"),
        ("$HOME/job-hunt/scripts/ashby_form_probe_gate.py", "$RUNTIME_ROOT/ashby/ashby_form_probe_gate.py"),
        ("$HOME/job-hunt/scripts/round80_probe_first_gate.py", "$RUNTIME_ROOT/ashby/probe_first_gate.py"),
    ]
    for old, new in repl:
        text = text.replace(old, new)
    dst = SKILL / "runtime/ashby/round110-batch.sh"
    dst.write_text(header + text, encoding="utf-8")
    dst.chmod(0o755)


def main() -> None:
    mapping = [
        (JH / "scripts/manual-retry-runner.py", SKILL / "runtime/manual/manual-retry-runner.py", 2),
        (JH / "scripts/ashby_form_probe_gate.py", SKILL / "runtime/ashby/ashby_form_probe_gate.py", 2),
        (JH / "scripts/round80_probe_first_gate.py", SKILL / "runtime/ashby/probe_first_gate.py", 2),
        (JH / "scripts/ashby_mine_round110_sources.py", SKILL / "runtime/ashby/ashby_mine_round110_sources.py", 2),
        (JH / "scripts/ashby_mine_github_repos.py", SKILL / "runtime/ashby/ashby_mine_github_repos.py", 2),
    ]
    for src, dst, depth in mapping:
        patch_py(src, dst, depth)
        print(f"OK {dst.relative_to(SKILL)}")
    patch_round110_sh()
    print("OK runtime/ashby/round110-batch.sh")


if __name__ == "__main__":
    main()
