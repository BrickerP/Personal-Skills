#!/usr/bin/env bash
# Personal Skills installer — symlink this repo's skills into local agent tool directories.
# Usage: ./scripts/install.sh [--status]
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGETS=("$HOME/.codex/skills" "$HOME/.claude/skills" "$HOME/.cursor/skills" "$HOME/.agents/skills")

status() {
  local missing=0
  for skill in "$REPO"/skills/*/; do
    name="$(basename "$skill")"
    for t in "${TARGETS[@]}"; do
      p="$t/$name"
      if [ -L "$p" ] && [ "$(readlink "$p")" = "${skill%/}" ]; then :; else
        echo "  not linked: $p"; missing=$((missing+1))
      fi
    done
  done
  if [ "$missing" -eq 0 ]; then
    echo "OK: $(ls -d "$REPO"/skills/*/ | wc -l | tr -d ' ') skills linked into ${#TARGETS[@]} tool dirs"
  else
    echo "$missing missing links — run install to fix" >&2; exit 1
  fi
}

install() {
  local count=0
  for skill in "$REPO"/skills/*/; do
    name="$(basename "$skill")"
    [ -f "$skill/SKILL.md" ] || continue
    for t in "${TARGETS[@]}"; do
      mkdir -p "$t"
      p="$t/$name"
      if [ -e "$p" ] && [ ! -L "$p" ]; then
        echo "SKIP (real dir exists, resolve manually): $p" >&2
        continue
      fi
      ln -sfn "${skill%/}" "$p"
    done
    count=$((count+1))
  done
  echo "linked $count skills into ${#TARGETS[@]} tool dirs"
  echo
  echo "Optional deps (first use):"
  echo "  daily-job-apply adapters: (cd \"$REPO/skills/daily-job-apply/adapters\" && npm install)"
  echo "  pdf-sanitize: creates its own .venv on first run"
}

case "${1:-install}" in
  --status|status) status ;;
  *) install ;;
esac
