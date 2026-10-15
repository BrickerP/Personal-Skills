#!/usr/bin/env python3
"""Re-patch greenhouse round runners cleanly."""

from __future__ import annotations

import re
from pathlib import Path

SKILL = Path.home() / ".codex" / "skills" / "daily-job-apply"
JOB_HUNT = Path.home() / "job-hunt"

BOOTSTRAP = '''from __future__ import annotations

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

OMX = ADAPTERS_DIR

'''


def patch_gh(src_name: str, dst_name: str) -> None:
    src = JOB_HUNT / src_name
    dst = SKILL / "runtime/greenhouse" / dst_name
    text = src.read_text(encoding="utf-8")
    text = re.sub(r"^#!/usr/bin/env python3\n", "", text)
    text = re.sub(r'^"""[\s\S]*?"""\n\n', "", text, count=1)
    text = re.sub(r"^from __future__ import annotations\n\n", "", text)

    subs = [
        (r'Path\("/Users/yupeng/Downloads/\.omx"\)', "ADAPTERS_DIR"),
        (r'OMX = Path\("/Users/yupeng/Downloads/\.omx"\)', "OMX = ADAPTERS_DIR"),
        (r'OMX = Path\.home\(\) / "Downloads" / "\.omx"', "OMX = ADAPTERS_DIR"),
        (r'JOB_HUNT = Path\.home\(\) / "job-hunt"', "JOB_HUNT = WORK_DIR"),
        (r'JOB_HUNT = HOME / "job-hunt"', "JOB_HUNT = WORK_DIR"),
        (r'HOME = Path\.home\(\)\n', ""),
        (r'TRACKER = JOB_HUNT / "tracker\.csv"', "TRACKER = TRACKER_CSV"),
        (r'NODE_PATH = "/Users/yupeng/\.npm/_npx/9833c18b2d85bc59/node_modules"', "NODE_PATH = os.environ.get('NODE_PATH', str(NODE_MODULES))"),
        (r'SOURCING_PY = Path\.home\(\) / "\.codex/skills/daily-job-apply/scripts/greenhouse_sourcing\.py"', "SOURCING_PY = SCRIPTS_DIR / 'greenhouse_sourcing.py'"),
        (r'sys\.path\.insert\(0, str\(OMX\)\)', ""),
        (r'sys\.path\.insert\(0, str\(JOB_HUNT\)\)', ""),
        (r'import run_greenhouse_round13 as r13', "import run_round13 as r13"),
    ]
    for pat, repl in subs:
        text = re.sub(pat, repl, text)

    doc = ""
    m = re.search(r'^"""[\s\S]*?"""\n\n', src.read_text(encoding="utf-8"))
    if m:
        doc = m.group(0)

    out = "#!/usr/bin/env python3\n" + doc + BOOTSTRAP + text.lstrip()
    dst.write_text(out, encoding="utf-8")
    dst.chmod(0o755)
    print(f"OK {dst}")


def main() -> None:
    patch_gh("run_greenhouse_round13.py", "run_round13.py")
    patch_gh("run_greenhouse_round18.py", "run_round18.py")


if __name__ == "__main__":
    main()
