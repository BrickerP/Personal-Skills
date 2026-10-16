#!/usr/bin/env bash
# RETIRED 2026-10-15: the batch entry point no longer exists.
# The CDP / Playwright / AppleScript engine it drove is archived under
# archive/2026-10-cdp-retired/ (reference only). Apply role by role with chrome-use:
# see workflows/04-universal-web-apply.md.
set -euo pipefail

SKILL_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cat >&2 <<EOF
[run-next] RETIRED (2026-10-15): there is no batch mode any more.
Apply role by role with chrome-use:
  ${SKILL_ROOT}/workflows/04-universal-web-apply.md
Platform playbooks: ATS-GREENHOUSE.md, ATS-ASHBY.md, ATS-BLOCKERS.md
Retired engine (reference only): ${SKILL_ROOT}/archive/2026-10-cdp-retired/
EOF
exit 2
