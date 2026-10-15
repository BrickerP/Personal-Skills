# ATS Self-Evolution Loop

**Role**: Platform adapter **registry** + harvest/batch failure logging (what platforms exist, adapter paths, promotion lifecycle).

**Ops notes** (Ashby boolean handlers, GH verification quirks): `~/job-hunt/ATS-EVOLUTION.md` — read that for field-level runbook detail; this file stays the registry + harvest contract.

Persistent registry + harvest + batch failure logging so LinkedIn external and direct ATS batches improve over time without duplicating adapter logic.

Machine-local field notes (Ashby booleans, Greenhouse verification): [~/job-hunt/ATS-EVOLUTION.md](file:///Users/yupeng/job-hunt/ATS-EVOLUTION.md).

## Artifacts

| Path | Role |
|------|------|
| `data/ats-adapter-registry.json` | Canonical platform definitions (domain patterns, adapter script, status, field mappings, stats) |
| `~/job-hunt/ats-adapter-registry.json` | Mirror written by `ats_registry.save_registry()` |
| `~/job-hunt/ats-evolution-log.jsonl` | Append-only attempt/failure events (primary) |
| `data/ats-evolution-log.jsonl` | Mirror of evolution log |
| `~/job-hunt/candidate-pools/linkedin-external-harvest-YYYY-MM-DD.csv` | Discovery-only harvest output |

## Registry status lifecycle

```
experimental ──(adapter + ≥3 successes, success_rate ≥0.5)──► production
     │                                                              │
     └─ blockers accumulate ──► stays experimental                 │
                                                                    ▼
unsupported-direct ◄── intermediate aggregators (jackandjill, jobright, remotehunter)
```

- **production**: `apply_allowed=true` when `adapter_script` is set. Batch runners may auto-apply.
- **experimental**: classified but no trusted adapter; harvest marks `needs-parse`; logged for evolution.
- **unsupported-direct**: skip in harvest and batch; never inline-apply on LinkedIn redirect.

Promotion to **production** is manual: set `status`, confirm `adapter_script`, review `blockers_seen` in the registry JSON.

## Harvest → adapter flow

1. **Harvest** (`linkedin_external_harvest.py`): CDP scrape LinkedIn external-apply cards, resolve safety URLs, classify via `ats_platform_classify.classify_url()`.
2. **CSV columns**: `url`, `platform`, `adapter_route`, `status` where status is one of:
   - `routable` — production platform with adapter
   - `unsupported-direct` — registry skip (aggregators)
   - `needs-parse` — unknown/custom or unresolved greenhouse embed
3. **Batch** (`linkedin_external_batch.py`): loads only `routable` rows; re-classifies URL before apply; skips anything registry marks non-routable.
4. **Adapters**: ashby → `ashby_apply_applescript.py`; greenhouse → `greenhouse_playwright_apply.cjs`; lever → `lever_playwright_apply.cjs`.

Run harvest only:

```bash
python3 ~/.codex/skills/daily-job-apply/scripts/linkedin_external_harvest.py --source-limit 40
```

Apply from today's harvest pool:

```bash
python3 ~/Downloads/.omx/linkedin_external_batch.py --from-harvest ~/job-hunt/candidate-pools/linkedin-external-harvest-$(date +%F).csv --limit 15
```

## Evolution on failure

`ats_evolution_log.evolve_from_attempt()` appends JSONL and updates registry stats (`attempts`, `successes`, `blockers_seen`, optional `field_mappings`).

Hooked on failure in:

- `linkedin_external_batch.py` — blocked/skipped/manual/blocked adapter outcomes
- `ashby_apply_batch.py` — non-submit return codes
- `greenhouse_playwright_batch.py` — non-submit payload statuses

CLI for manual logging:

```bash
python3 ~/.codex/skills/daily-job-apply/scripts/ats_evolution_log.py \
  --platform greenhouse --url 'https://...' --status Blocked --blocker phone-required-no-active-number
```

## Adding a new platform

1. Harvest surfaces URLs with `needs-parse` and `platform=custom` or new domain.
2. Inspect `~/job-hunt/ats-evolution-log.jsonl` for repeated domains/blockers.
3. Add entry to `ats-adapter-registry.json`: `domain_patterns`, `adapter_script`, `status=experimental`.
4. Implement adapter under `~/Downloads/.omx/`; wire `adapter_script` path.
5. Re-run harvest; confirm rows flip to `routable`.
6. After stable submits, set `status=production`.

## Greenhouse embed resolution

Embed URLs (`app.greenhouse.io/embed/job_app?token=…`) require `greenhouse_url_resolver.py` before apply. Unresolved embeds stay `needs-parse` even when platform is greenhouse.
