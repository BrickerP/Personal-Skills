#!/usr/bin/env python3
"""Validate SKILL.md files in this repo.

Checks (per skills/<id>/SKILL.md):
  1. SKILL.md exists
  2. frontmatter present (file starts with --- ... ---)
  3. frontmatter is valid YAML mapping
  4. has non-empty `name`
  5. has non-empty `description`  (no description = skill is invisible to models)
  6. directory id is lowercase kebab-case

Usage: python3 scripts/validate.py [root]
Exit code 0 = all good, 1 = problems found.
"""
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: pyyaml required (pip install pyyaml)", file=sys.stderr)
    sys.exit(2)

FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)
ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
MAX_DESC = 2000


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent
    skills_dir = root / "skills"
    if not skills_dir.is_dir():
        print(f"ERROR: {skills_dir} not found", file=sys.stderr)
        return 2

    errors: list[str] = []
    checked = 0

    for d in sorted(skills_dir.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        checked += 1
        name = d.name

        if not ID_RE.match(name):
            errors.append(f"{name}: directory name is not lowercase kebab-case")

        skill_md = d / "SKILL.md"
        if not skill_md.exists():
            errors.append(f"{name}: missing SKILL.md")
            continue

        text = skill_md.read_text(encoding="utf-8", errors="replace")
        m = FM_RE.match(text)
        if not m:
            errors.append(f"{name}: no frontmatter (must start with --- ... ---)")
            continue

        try:
            fm = yaml.safe_load(m.group(1))
        except Exception as e:  # noqa: BLE001
            errors.append(f"{name}: invalid YAML in frontmatter: {e}")
            continue

        if not isinstance(fm, dict):
            errors.append(f"{name}: frontmatter is not a YAML mapping")
            continue

        if not fm.get("name"):
            errors.append(f"{name}: missing 'name'")
        desc = str(fm.get("description") or "").strip()
        if not desc:
            errors.append(f"{name}: missing 'description' (skill would be invisible)")
        elif len(desc) > MAX_DESC:
            errors.append(f"{name}: description too long ({len(desc)} > {MAX_DESC} chars)")

    print(f"checked {checked} skills")
    if errors:
        print(f"\n{len(errors)} problem(s):")
        for e in errors:
            print(f"  x {e}")
        return 1
    print("all SKILL.md files OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
