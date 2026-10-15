#!/usr/bin/env python3
"""Shared Ashby form-probe gate — classify_form(detail['posting']), not the API wrapper."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_RUNTIME = Path(__file__).resolve().parents[2]
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

import argparse
import csv
import json
import sys
import urllib.parse
from collections import defaultdict
from pathlib import Path

OMX = Path.home() / "Downloads" / ".omx"
sys.path.insert(0, str(OMX))

from ashby_sourcing import ashby_get, choose_variant, classify_form, title_ok_engineering  # noqa: E402

FIELDS = [
    "status",
    "company",
    "role",
    "location",
    "url",
    "slug",
    "posting_id",
    "variant",
    "blocker",
    "published",
    "updated",
    "pool_source",
]


def load_slugs(path: Path) -> list[str]:
    slugs: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        slugs.append(s)
    return slugs


def run_probe(
    slugs: list[str],
    *,
    max_postings_per_slug: int,
    probe_csv: Path,
    form_hit_slugs: Path,
    pool_source: str = "form-probe",
    pick_csv: Path | None = None,
) -> dict:
    rows: list[dict] = []
    pick_rows: list[dict] = []
    slug_stats: dict[str, dict] = defaultdict(
        lambda: {"auto": 0, "phone": 0, "other_manual": 0, "checked": 0}
    )

    for slug in slugs:
        slug = slug.strip()
        if not slug:
            continue
        data = ashby_get(urllib.parse.quote(slug, safe="-._~%"), retries=2, timeout=20)
        if not data or data.get("_error"):
            slug_stats[slug]["board_error"] = 1
            continue
        org = ((data.get("organization") or {}).get("name") or slug).strip()
        postings = (data.get("jobBoard") or {}).get("jobPostings") or []
        checked = 0
        first_auto: dict | None = None
        for posting in postings:
            if checked >= max_postings_per_slug:
                break
            title = (posting.get("title") or "").strip()
            dept = (posting.get("departmentName") or posting.get("departmentExternalName") or "").strip()
            if not title_ok_engineering(title, dept, metadata_only=True):
                continue
            pid = posting.get("id")
            detail = ashby_get(urllib.parse.quote(slug, safe="-._~%"), pid, retries=2, timeout=20)
            if not detail or detail.get("_error"):
                continue
            posting_obj = detail.get("posting") or {}
            status, blocker = classify_form(posting_obj)
            checked += 1
            slug_stats[slug]["checked"] += 1
            if status == "auto_candidate":
                slug_stats[slug]["auto"] += 1
            elif "phone-required" in blocker:
                slug_stats[slug]["phone"] += 1
            else:
                slug_stats[slug]["other_manual"] += 1
            row = {
                "status": status,
                "company": org,
                "role": title,
                "location": "",
                "url": f"https://jobs.ashbyhq.com/{slug}/{pid}",
                "slug": slug,
                "posting_id": pid,
                "variant": choose_variant(title, posting_obj.get("descriptionPlainText") or ""),
                "blocker": blocker,
                "published": "",
                "updated": "",
                "pool_source": pool_source,
            }
            rows.append(row)
            if status == "auto_candidate" and first_auto is None:
                first_auto = dict(row)
        if first_auto and pick_csv is not None:
            pick_rows.append(first_auto)

    form_hit: list[str] = []
    phone_heavy: list[str] = []
    no_hit: list[str] = []
    for slug, st in slug_stats.items():
        if st.get("auto", 0) > 0:
            form_hit.append(slug)
        elif st.get("checked", 0) > 0 and st.get("phone", 0) == st.get("checked", 0):
            phone_heavy.append(slug)
        else:
            no_hit.append(slug)

    probe_csv.parent.mkdir(parents=True, exist_ok=True)
    with probe_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    form_hit_slugs.parent.mkdir(parents=True, exist_ok=True)
    form_hit_slugs.write_text("\n".join(form_hit) + ("\n" if form_hit else ""), encoding="utf-8")

    if pick_csv is not None:
        with pick_csv.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
            w.writeheader()
            w.writerows(pick_rows)

    summary = {
        "probe_rows": len(rows),
        "form_hit_slugs": form_hit,
        "phone_heavy_skipped": phone_heavy,
        "no_simple_form": no_hit,
        "form_hit_count": len(form_hit),
        "phone_heavy_count": len(phone_heavy),
        "classify_form_target": "detail['posting']",
        "mine_pick_rows": len(pick_rows) if pick_csv is not None else None,
    }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slugs-file", required=True)
    parser.add_argument("--probe-csv", required=True)
    parser.add_argument("--form-hit-slugs", required=True)
    parser.add_argument("--max-postings-per-slug", type=int, default=40)
    parser.add_argument("--pool-source", default="form-probe")
    parser.add_argument("--pick-csv")
    args = parser.parse_args()

    slugs = load_slugs(Path(args.slugs_file))
    summary = run_probe(
        slugs,
        max_postings_per_slug=args.max_postings_per_slug,
        probe_csv=Path(args.probe_csv),
        form_hit_slugs=Path(args.form_hit_slugs),
        pool_source=args.pool_source,
        pick_csv=Path(args.pick_csv) if args.pick_csv else None,
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
