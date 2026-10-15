---
name: lavayou-author-lens
description: Use when Codex needs to analyze Chinese social issues, internet narratives, policy debates, family/gender conflicts, money/career choices, culture/history questions, or media events through a framework distilled from the public free articles on i.lavayou.cn. Supports source-card retrieval, topic mapping, and author-derived reasoning patterns. Do not use for impersonation, style mimicry, paid-content reconstruction, or verbatim reproduction of the author's articles.
---

# Lavayou Author Lens

Use this skill as an author-derived analysis lens, not as a style clone. The corpus is the site's public free article category, distilled into non-fulltext source cards, topic maps, and reusable reasoning frames.

## Quick Start

1. Read `references/00-overview.md` for the corpus basis and high-level lens.
2. For an actual analysis answer, also read `references/01-operating-frame.md` and `references/03-response-playbook.md`.
3. For topic-specific work, read `references/02-topic-map.md`.
4. Use `scripts/search_source_index.py` to find relevant source cards before making strong claims:

```bash
python3 scripts/search_source_index.py "工资 职场 收入" --limit 8
python3 scripts/search_source_index.py --topic media-epistemics --limit 8
python3 scripts/search_source_index.py --pattern follow-the-money --limit 8
```

## Core Workflow

1. Identify the surface narrative: what the user or public debate appears to be saying.
2. Search the source index for at least 3 relevant cards unless the user only wants a general framework.
3. Apply the operating frame: missing variables, money/incentives, common-sense feasibility, motive/effect split, material conditions, and long-run consequences.
4. Answer in clean analytical language. Preserve the framework; do not reproduce abusive rhetoric, protected-class insults, or the author's exact prose.
5. Separate evidence from inference. Cite source-card titles/URLs when using corpus-derived support.

## Boundaries

- Do not claim to be the author or write "as the author."
- Do not imitate the author's distinctive prose, insults, cadence, or catchphrase-heavy style.
- Do not reconstruct paid articles or bypass access controls.
- Do not include long quotations from public articles. Prefer paraphrase and source-card links.
- When the lens points toward a sensitive claim, state uncertainty and required missing facts instead of presenting speculation as fact.
- If the user asks for exact article content, fetch the public URL if necessary and summarize within normal copyright limits.

## Resources

- `data/source-index.jsonl`: 1005 public-free article cards with URL, title, date, categories, tags, derived topics, derived reasoning patterns, keyword signals, and character counts. It does not contain article full text.
- `data/corpus-stats.json`: corpus-level counts and distribution evidence.
- `scripts/ingest_public_free_articles.py`: regenerate derived cards from the public WordPress API.
- `scripts/search_source_index.py`: retrieve relevant source cards without loading the whole index.
- `scripts/audit_skill.py`: verify required files, index count, and absence of fulltext-like fields in source cards.
- `scripts/export_yuanqi.py`: generate `mobile-export/yuanqi/` with prompt and knowledge files for Tencent Yuanqi/mobile use.
