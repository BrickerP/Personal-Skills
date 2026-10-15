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

_LOCAL_DIR = Path(__file__).resolve().parent
if str(_LOCAL_DIR) not in sys.path:
    sys.path.insert(0, str(_LOCAL_DIR))
sys.path.insert(0, str(ADAPTERS_DIR))
sys.path.insert(0, str(SCRIPTS_DIR))
if NODE_PATH:
    os.environ.setdefault("NODE_PATH", NODE_PATH)

