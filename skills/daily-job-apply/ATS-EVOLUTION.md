# ATS Self-Evolution Loop

**Role**: Platform **registry** + harvest and failure logging (what platforms exist, how each is applied, promotion lifecycle).

**Ops notes** (Ashby boolean handlers, GH verification quirks): `~/job-hunt/ATS-EVOLUTION.md` — read that for field-level runbook detail; this file stays the registry + harvest contract.

Persistent registry + harvest + failure logging so LinkedIn-external and direct ATS applications (applied role by role with `chrome-use`, `workflows/04-universal-web-apply.md`) improve over time.

Machine-local field notes (Ashby booleans, Greenhouse verification): [~/job-hunt/ATS-EVOLUTION.md](file:///Users/yupeng/job-hunt/ATS-EVOLUTION.md).

## Artifacts

| Path | Role |
|------|------|
| `data/ats-adapter-registry.json` | Canonical platform definitions (domain patterns, `playbook` or `adapter_script`, status, field mappings, stats) |
| `~/job-hunt/ats-adapter-registry.json` | Mirror written by `ats_registry.save_registry()` |
| `~/job-hunt/ats-evolution-log.jsonl` | Append-only attempt/failure events (primary) |
| `data/ats-evolution-log.jsonl` | Mirror of evolution log |
| `~/job-hunt/candidate-pools/linkedin-external-harvest-YYYY-MM-DD.csv` | Discovery-only harvest output |

## Registry status lifecycle

```
experimental ──(playbook file + playbook field)─────────────────► playbook
     │
     ├──(adapter_script + ≥3 successes, success_rate ≥0.5)─────► production
     │
     └─ blockers accumulate ──► stays experimental

unsupported-direct ◄── intermediate aggregators (jackandjill, jobright, remotehunter)
```

- **playbook**: applyable (the entry needs a `playbook` field). The agent applies it role by role with `chrome-use`, following that file. Today: ashby (`ATS-ASHBY.md`), greenhouse (`ATS-GREENHOUSE.md`), lever (`workflows/04-universal-web-apply.md`).
- **production**: applyable with a trusted `adapter_script` (the entry needs that field). None today: the batch engine is retired.
- **experimental**: classified but no trusted route; harvest marks `needs-parse`; logged for evolution. Today: workable, workday, custom (`custom` is never applyable).
- **unsupported-direct**: skip in harvest and apply; never inline-apply on LinkedIn redirect. Today: jackandjill, jobright, remotehunter.

Promotion is manual: set `status` and its matching field (`playbook` or `adapter_script`), review `blockers_seen` in the registry JSON.

Counters (`attempts`, `successes`, `success_rate`) were reset when the batch engine was retired (2026-10-15); the old batch-engine counts live under `legacy_batch_attempts`. Those legacy counts are failure-log rows, not outcomes (`ATS-BLOCKERS.md` §1.1).

## Harvest → apply flow

1. **Harvest** (`linkedin_external_harvest.py`): opens its own `chrome-use` session (`harvest`, pinned to the `yplmicro@gmail.com` profile via `CHROME_USE_SESSION` / `CHROME_USE_BROWSER`), so it needs no pre-opened tab and never touches the user's own tabs. It scrapes LinkedIn external-apply cards, resolves safety URLs and classifies via `ats_platform_classify.classify_url()`. It exits 2 when chrome-use fails, LinkedIn needs sign-in or redirects away from `linkedin.com` (the `www.linkedin.cn` redirect counts), and 3 when no cards were found; three detail-page failures abort it (also exit 2). Not verified end to end against real LinkedIn (HTTP 999 / redirect when tested). It is read-only, but it does open LinkedIn job pages, and the LinkedIn freeze in `SKILL.md` bars external-apply launch flows and allows reading LinkedIn only when the user asks: while the freeze stands, run it only on the user's request.
2. **CSV columns**: `url`, `platform`, `adapter_route`, `status` where status is one of:
   - `routable` — platform with an applyable route (`playbook` or `production`)
   - `unsupported-direct` — registry skip (aggregators)
   - `needs-parse` — unknown/custom or unresolved greenhouse embed

   `adapter_route` is the `adapter_script` path, `greenhouse:<board>/<job_id>`, or `playbook:<platform_id>` for an applyable row, and the bare platform id (`greenhouse`, `custom`, `jackandjill` …) when the row is not applyable (`unsupported-direct`, `needs-parse`).
3. **Apply**: the agent works the `routable` rows one at a time via `workflows/04-universal-web-apply.md`, re-classifying each URL first and skipping anything the registry marks non-routable. The old batch driver `.omx/linkedin_external_batch.py` is retired (it lived outside this repo).
4. **Playbooks**: ashby → `ATS-ASHBY.md`; greenhouse → `ATS-GREENHOUSE.md`; lever → `workflows/04-universal-web-apply.md` (no `ATS-LEVER.md`). The old apply adapters are retired under `archive/2026-10-cdp-retired/adapters/`.

Run harvest:

```bash
python3 ~/.codex/skills/daily-job-apply/scripts/linkedin_external_harvest.py --source-limit 40
```

## Evolution on failure

`ats_evolution_log.evolve_from_attempt()` appends JSONL and updates registry stats (`attempts`, `successes`, `blockers_seen`, optional `field_mappings`).

Apart from the CLI below, its only in-repo callers are the orphaned `adapters/ashby_apply_batch.py` and `adapters/greenhouse_playwright_batch.py`, so nothing logs automatically any more. Record outcomes by hand:

```bash
python3 ~/.codex/skills/daily-job-apply/scripts/ats_evolution_log.py \
  --platform greenhouse --url 'https://...' --status Blocked --blocker phone-rejected
```

## Adding a new platform

1. Harvest surfaces URLs with `needs-parse` and `platform=custom` or new domain.
2. Inspect `~/job-hunt/ats-evolution-log.jsonl` for repeated domains/blockers.
3. Add entry to `ats-adapter-registry.json`: `domain_patterns`, `status=experimental`.
4. Write a playbook (`ATS-<PLATFORM>.md`), then set `status=playbook` and the `playbook` field.
5. Re-run harvest; confirm rows flip to `routable`.
6. `production` needs a trusted `adapter_script` and ≥3 successes (success_rate ≥0.5); there is none today.

## Greenhouse embed resolution

Embed URLs (`app.greenhouse.io/embed/job_app?token=…`) require `greenhouse_url_resolver.py` before apply. Unresolved embeds stay `needs-parse` even when platform is greenhouse.
