---
name: creative
description: >
  Unified creative thinking skill that routes to one of five modes: grill (Socratic
  interrogation of plans), critique (pre-mortem / red-team / ATAM stress-test),
  arch (Ousterhout deep-module architecture review → RFC), audit (deepen shallow
  codebase modules), or research (横纵分析法 deep product/company research → PDF).
  Use when the user says creative, /creative, grill me, design critique, stress-test,
  arch-lens, deep module, codebase audit, 横纵分析, deep research a product/company,
  or wants idea/architecture/product creative work without naming a sub-skill.
---

# Creative

One entrypoint. Five modes. Pick a mode, then **load and follow that mode’s `MODE.md` exactly** (including its `references/` and `scripts/`).

Mode root: `~/.agents/skills/creative/modes/<mode>/`

## Mode router

| Mode | Directory | When |
|------|-----------|------|
| **grill** | `modes/grill-master/` | Requirements unclear; grill/interview until shared understanding; no plan yet |
| **critique** | `modes/design-critique/` | Have a plan/design already; stress-test with pre-mortem / red team / ATAM |
| **arch** | `modes/arch-lens/` | Codebase architectural friction; deep modules; competing interfaces → RFC file |
| **audit** | `modes/deep-codebase-audit/` | Broad “deepen shallow modules” audit; testability / AI-navigability |
| **research** | `modes/hv-analysis/` | Product/company/concept deep research (横纵分析) → long PDF report |

### How to choose

1. If user names a mode (`grill` / `critique` / `arch` / `audit` / `research` / Chinese aliases below) → that mode.
2. Else:
   - Unclear idea / “帮我想清楚” / before planning → **grill**
   - “压测/挑战这个方案” / already have a design → **critique**
   - “浅层模块 / deep module / 出 RFC” → **arch**
   - “审计仓库架构 / 更可测” → **audit**
   - “调研/竞品/横纵分析/这公司怎么回事” → **research**
3. If still ambiguous: ask **one** question:  
   `grill / critique / arch / audit / research — 哪个？`

### Aliases

- grill: `/grill`, grill-me, 拷问一下, 追问到清楚
- critique: design-critique, stress-test, pre-mortem, red team, 红队, 压测方案
- arch: arch-lens, Ousterhout, deep module, 架构 RFC
- audit: deep-codebase-audit, `/deep-audit`, 代码库加深
- research: hv-analysis, 横纵分析, deep research, 竞品调研

## Execution contract

1. **Announce mode** in one line: `Creative → <mode>`.
2. **Read** `~/.agents/skills/creative/modes/<mode>/MODE.md` (and any files it tells you to load).
3. **Follow that skill’s workflow and rules** — do not invent a hybrid mid-flight.
4. Do not run two modes in parallel unless the user explicitly asks for a sequence (e.g. grill → critique).
5. Suggested sequences:
   - New idea: **grill** → (optional) **critique** → plan/implement
   - Existing codebase: **audit** or **arch**
   - Market/product understanding: **research**

## Out of scope

- Simple coding tasks, bugfixes, or “just implement X” — do not force Creative.
- Simple dictionary definitions — use normal chat, not **research**.
- Replacing `$ralplan` / `$ralph` execution — Creative clarifies or audits; hand off to planning/implementation after.
