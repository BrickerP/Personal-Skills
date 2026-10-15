#!/usr/bin/env python3
"""Post-migration fix: normalize paths bootstrap in migrated Python files."""

from __future__ import annotations

import re
from pathlib import Path

SKILL = Path.home() / ".codex" / "skills" / "daily-job-apply"

STANDARD_BOOTSTRAP = '''from __future__ import annotations

import os
import sys
from pathlib import Path

_RUNTIME = Path(__file__).resolve().parents[{runtime_depth}]
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

_LOCAL_DIR = Path(__file__).resolve().parent
if str(_LOCAL_DIR) not in sys.path:
    sys.path.insert(0, str(_LOCAL_DIR))
sys.path.insert(0, str(ADAPTERS_DIR))
sys.path.insert(0, str(SCRIPTS_DIR))
if NODE_PATH:
    os.environ.setdefault("NODE_PATH", NODE_PATH)

'''

GH_EXTRA = "OMX = ADAPTERS_DIR\n"


def runtime_depth_for(path: Path) -> int:
    rel = path.relative_to(SKILL)
    # runtime/foo.py -> parents[1]=runtime
    # runtime/greenhouse/foo.py -> parents[2]=runtime
    # adapters/foo.py -> parents[1]=skill, need runtime via parents[1]/../runtime - use depth to skill+1
    parts = rel.parts
    if parts[0] == "adapters":
        return 1  # will point to skill root; fix below
    if parts[0] == "runtime":
        return len(parts) - 2  # file in runtime/x -> 1, runtime/greenhouse/x -> 2
    return 1


def bootstrap_for(path: Path) -> str:
    rel = path.relative_to(SKILL)
    if rel.parts[0] == "adapters":
        return STANDARD_BOOTSTRAP.replace(
            "parents[{runtime_depth}]",
            'parents[1] / "runtime"',
        ).replace("_LOCAL_DIR = Path(__file__).resolve().parent", "_LOCAL_DIR = Path(__file__).resolve().parent")
    depth = runtime_depth_for(path)
    return STANDARD_BOOTSTRAP.format(runtime_depth=depth)


def strip_old_bootstrap(text: str) -> str:
    # Remove duplicate future imports and old bootstrap blocks
    text = re.sub(r"from __future__ import annotations\n+", "", text)
    text = re.sub(
        r"import os\nimport sys\nfrom pathlib import Path\n\n_RUNTIME = Path\(__file__\).*?os\.environ\.setdefault\(\"NODE_PATH\", NODE_PATH\)\n\n",
        "",
        text,
        flags=re.DOTALL,
    )
    text = re.sub(r"_GH_DIR = Path\(__file__\).*?os\.environ\.setdefault\(\"NODE_PATH\", NODE_PATH\)\n\n", "", text, flags=re.DOTALL)
    return text


def fix_python_file(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = strip_old_bootstrap(text)

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

    boot = bootstrap_for(path)
    if "greenhouse" in str(path) and path.name.startswith("run_round"):
        boot += GH_EXTRA

    new_text = "".join(lines[:insert_at]) + boot + "".join(lines[insert_at:])
    # Clean stale inline assignments that reference undefined names before bootstrap
    new_text = re.sub(r"^HOME = Path\.home\(\)\n", "", new_text, flags=re.M)
    new_text = re.sub(r"^JOB_HUNT = WORK_DIR\n", "JOB_HUNT = WORK_DIR\n", new_text, flags=re.M)
    path.write_text(new_text, encoding="utf-8")


def fix_round110_sh() -> None:
    path = SKILL / "runtime/ashby/round110-batch.sh"
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        "MINE=$WORK_DIR/scripts/ashby_mine_round110_sources.py",
        'MINE="$RUNTIME_ROOT/ashby/ashby_mine_round110_sources.py"',
    )
    text = text.replace(
        "REPO_MINE=$WORK_DIR/scripts/ashby_mine_github_repos.py",
        'REPO_MINE="$RUNTIME_ROOT/ashby/ashby_mine_github_repos.py"',
    )
    text = text.replace(
        "PROBE_HELPER=$WORK_DIR/scripts/ashby_form_probe_gate.py",
        'PROBE_HELPER="$RUNTIME_ROOT/ashby/ashby_form_probe_gate.py"',
    )
    text = text.replace(
        "PROBE_FIRST_GATE=$WORK_DIR/scripts/probe_first_gate.py",
        'PROBE_FIRST_GATE="$RUNTIME_ROOT/ashby/probe_first_gate.py"',
    )
    text = text.replace(
        'Path(os.environ.get("WORK_DIR", str(WORK_DIR)) + "/.round110-batch.lockdir")',
        'Path(f"{os.environ.get(\'WORK_DIR\', \'\')}" or str(WORK_DIR)) / ".round110-batch.lockdir"',
    )
    path.write_text(text, encoding="utf-8")


def main() -> None:
    targets = list((SKILL / "runtime").rglob("*.py"))
    targets += list((SKILL / "adapters").rglob("*.py"))
    for path in targets:
        if path.name == "paths.py":
            continue
        fix_python_file(path)
        print(f"fixed {path.relative_to(SKILL)}")

    fix_round110_sh()
    print("round110-batch.sh paths fixed")


if __name__ == "__main__":
    main()
