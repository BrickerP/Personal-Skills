# Topic Map

The source index assigns multiple derived topics per article. Counts below are corpus-level signal counts, not exclusive buckets.

## Corpus Topic Counts

- `culture-values`: 897
- `history-geopolitics`: 618
- `money-career-class`: 511
- `political-economy`: 414
- `family-parenting`: 402
- `science-technology`: 251
- `media-epistemics`: 239
- `health-medicine`: 223
- `gender-intimacy`: 183

## Media And Internet Narratives

Use `media-epistemics` when the user asks about news framing, online outrage, public-opinion reversals, platform traffic, or missing context.

Default questions:

- What information would a neutral report include?
- Which omitted detail would change the emotional direction?
- Who benefits from a first-wave narrative and who benefits from a reversal?
- Is the story written to inform, mobilize, shame, sell, or bait?

Search examples:

```bash
python3 scripts/search_source_index.py --topic media-epistemics --limit 8
python3 scripts/search_source_index.py "新闻 流量 反转" --limit 8
```

## Political Economy And State Capacity

Use `political-economy` for policy, socialism/capitalism, governance, productive forces, class, institutions, and China/West comparisons.

Default questions:

- Does the proposal improve production, organization, public welfare, or institutional competence?
- Is discourse a symptom of the economic base?
- What can a state, market, firm, household, or platform actually execute?
- What long-run incentives will this policy create?

Search examples:

```bash
python3 scripts/search_source_index.py --topic political-economy --limit 8
python3 scripts/search_source_index.py "生产力 社会主义 经济基础" --limit 8
```

## Money, Career, And Class

Use `money-career-class` for salary, job choices, workplace incentives, investment, consumption, pricing, and class mobility.

Default questions:

- What does the money flow reveal that the stated story hides?
- Is the user's goal income, status, security, optionality, or capability?
- Which KPI belongs to the institution, and which outcome belongs to the person?
- What is the price of this choice in time, risk, learning, and bargaining power?

Search examples:

```bash
python3 scripts/search_source_index.py --topic money-career-class --limit 8
python3 scripts/search_source_index.py "工资 职场 收入 风险" --limit 8
```

## Family, Parenting, And Intimacy

Use `family-parenting` and `gender-intimacy` for marriage, relatives, caregiving, children, filial duty, dating, gender conflict, and intimate bargaining.

Default questions:

- Who has legal, emotional, financial, and caregiving obligation?
- Which absent family member or prior relationship changes the case?
- What hidden dependency or bargaining power exists?
- Are moral claims being used to shift cost or risk?

Guardrail: keep the analysis structural. Do not copy abusive wording from the source corpus. Avoid group blame; analyze the specific incentive setup.

Search examples:

```bash
python3 scripts/search_source_index.py --topic family-parenting --limit 8
python3 scripts/search_source_index.py --topic gender-intimacy --limit 8
python3 scripts/search_source_index.py "婚姻 父母 子女 钱" --limit 8
```

## Health, Medicine, Science, And Technology

Use `health-medicine` and `science-technology` for medical claims, public health, AI, products, engineering, and technical/scientific controversies.

Default questions:

- What is the material mechanism rather than the slogan?
- Who has expertise, who has incentives, and who has execution capacity?
- Does the intervention improve real capability or merely change discourse?
- What practical constraints make a technically correct claim useless or useful?

Search examples:

```bash
python3 scripts/search_source_index.py --topic health-medicine --limit 8
python3 scripts/search_source_index.py --topic science-technology --limit 8
python3 scripts/search_source_index.py "医学 科学 技术 产品" --limit 8
```

## Culture, History, And Values

Use `culture-values` and `history-geopolitics` for tradition, civilization, language, books, film, history, geopolitics, nationalism, and ideology.

Default questions:

- What material structure produced this culture or value?
- Is the argument about real continuity or status signaling?
- Which historical analogy is operationally relevant rather than decorative?
- Does the cultural claim strengthen capability or freeze a dead form?

Search examples:

```bash
python3 scripts/search_source_index.py --topic culture-values --limit 8
python3 scripts/search_source_index.py --topic history-geopolitics --limit 8
python3 scripts/search_source_index.py "历史 文明 文化 传统" --limit 8
```
