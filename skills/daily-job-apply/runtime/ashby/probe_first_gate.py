#!/usr/bin/env python3
"""Round74 probe-first gate: probe auto rows enter pool directly; metadata only for probe-miss slugs."""

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
    SCRIPTS_DIR,
    SKILL_ROOT,
    WORK_DIR,
    TRACKER_CSV,
)

sys.path.insert(0, str(ADAPTERS_DIR))
sys.path.insert(0, str(SCRIPTS_DIR))

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path


def norm_key(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (s or "").casefold())


def load_fresh_keys(path: Path) -> set[str]:
    keys: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            keys.add(norm_key(s))
    return keys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe-csv", required=True)
    parser.add_argument("--sourced-csv", default="")
    parser.add_argument("--fresh-slugs", required=True)
    parser.add_argument("--merged-out", required=True)
    parser.add_argument("--gate-json", required=True)
    parser.add_argument("--exclude-slugs", default="")
    parser.add_argument("--source-path", default="probe_first")
    args = parser.parse_args()

    probe_path = Path(args.probe_csv)
    sourced_path = Path(args.sourced_csv) if args.sourced_csv else None
    fresh_keys = load_fresh_keys(Path(args.fresh_slugs))
    exclude = {s.strip().lower() for s in args.exclude_slugs.split() if s.strip()}

    fields = [
        "status", "company", "role", "location", "url", "slug", "posting_id",
        "variant", "blocker", "published", "updated", "gate", "probe_status",
        "probe_blocker", "metadata_blocker",
    ]

    probe_auto: dict[str, dict] = {}
    probe_by_slug: Counter[str] = Counter()
    for row in csv.DictReader(probe_path.open()):
        if row.get("status") != "auto_candidate":
            continue
        url = row.get("url", "")
        slug = (row.get("slug") or "").lower()
        if slug in exclude or norm_key(slug) not in fresh_keys:
            continue
        probe_auto[url] = row
        probe_by_slug[slug] += 1

    rows: list[dict] = []
    seen: set[str] = set()
    gate_stats: Counter[str] = Counter()
    detail: list[dict] = []

    for url, probe in probe_auto.items():
        out_row = dict(probe)
        out_row["gate"] = "probe_pass"
        out_row["probe_status"] = "auto_candidate"
        out_row["probe_blocker"] = probe.get("blocker", "")
        out_row["metadata_blocker"] = ""
        seen.add(url)
        gate_stats["probe_pass"] += 1
        rows.append(out_row)
        detail.append({
            "slug": probe.get("slug"),
            "url": url,
            "role": probe.get("role"),
            "gate": "probe_pass",
            "probe_status": "auto_candidate",
            "metadata_blocker": "",
        })

    metadata_auto = 0
    if sourced_path and sourced_path.exists() and sourced_path.stat().st_size > 0:
        for row in csv.DictReader(sourced_path.open()):
            if row.get("status") != "auto_candidate":
                continue
            slug = (row.get("slug") or "").lower()
            if slug in exclude or norm_key(slug) not in fresh_keys:
                continue
            url = row.get("url", "")
            if url in seen:
                continue
            probe = probe_auto.get(url)
            if probe:
                gate = "dual_pass"
            else:
                gate = "metadata_only"
            gate_stats[gate] += 1
            metadata_auto += 1
            out_row = dict(row)
            out_row["gate"] = gate
            out_row["probe_status"] = (probe or {}).get("status") or "missing"
            out_row["probe_blocker"] = (probe or {}).get("blocker", "")
            out_row["metadata_blocker"] = row.get("blocker", "")
            seen.add(url)
            rows.append(out_row)
            detail.append({
                "slug": row.get("slug"),
                "url": url,
                "role": row.get("role"),
                "gate": gate,
                "probe_status": out_row["probe_status"],
                "metadata_blocker": out_row["metadata_blocker"][:80],
            })

    merged_path = Path(args.merged_out)
    with merged_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    gate_path = Path(args.gate_json)
    gate_path.write_text(json.dumps({
        "probe_pass": gate_stats.get("probe_pass", 0),
        "dual_pass": gate_stats.get("dual_pass", 0),
        "metadata_only": gate_stats.get("metadata_only", 0),
        "merged_total": len(rows),
        "probe_auto_urls": len(probe_auto),
        "metadata_auto": metadata_auto,
        "fresh_slug_keys": len(fresh_keys),
        "source_path": args.source_path,
        "probe_first": True,
        "rows": detail[:40],
    }, indent=2), encoding="utf-8")

    print(json.dumps({
        "merged": len(rows),
        "probe_pass": gate_stats.get("probe_pass", 0),
        "dual_pass": gate_stats.get("dual_pass", 0),
        "metadata_only": gate_stats.get("metadata_only", 0),
        "probe_auto_urls": len(probe_auto),
        "metadata_auto": metadata_auto,
        "source_path": args.source_path,
        "out": str(merged_path),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
