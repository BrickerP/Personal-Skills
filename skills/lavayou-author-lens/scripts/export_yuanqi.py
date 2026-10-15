#!/usr/bin/env python3
"""Export the Lavayou author lens into Tencent Yuanqi-friendly files."""

from __future__ import annotations

import csv
import json
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = SKILL_ROOT / "data"
REF_DIR = SKILL_ROOT / "references"
EXPORT_DIR = SKILL_ROOT / "mobile-export" / "yuanqi"
KNOWLEDGE_DIR = EXPORT_DIR / "knowledge"

TOPIC_LABELS = {
    "media-epistemics": "媒体叙事与互联网舆论",
    "political-economy": "政治经济与制度能力",
    "money-career-class": "钱、职业与阶层",
    "gender-intimacy": "两性、亲密关系与婚姻",
    "family-parenting": "家庭、亲子与义务",
    "health-medicine": "健康、医学与公共卫生",
    "history-geopolitics": "历史、地缘与文明叙事",
    "science-technology": "科学、技术与产品",
    "culture-values": "文化、价值观与读书",
    "general-observation": "通用观察",
}

PATTERN_LABELS = {
    "follow-the-money": "跟着钱和风险走",
    "missing-variable-audit": "缺失变量审计",
    "base-and-productivity": "生产力/经济基础测试",
    "motive-vs-effect": "动机与效果分离",
    "anti-traffic-frame": "媒体流量框架",
    "binary-dissolver": "拆掉二元问题",
    "common-sense-stress-test": "常识压力测试",
    "plain-argument": "普通论证",
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def copy_reference_knowledge() -> None:
    mapping = {
        "00-overview.md": "00-author-overview.md",
        "01-operating-frame.md": "01-operating-frame.md",
        "02-topic-map.md": "02-topic-map.md",
        "03-response-playbook.md": "03-response-playbook.md",
        "04-corpus-audit.md": "04-corpus-audit.md",
    }
    for src_name, dst_name in mapping.items():
        text = (REF_DIR / src_name).read_text(encoding="utf-8")
        write(KNOWLEDGE_DIR / dst_name, text)


def render_card(row: dict[str, Any]) -> str:
    topics = "、".join(TOPIC_LABELS.get(item, item) for item in row.get("topics", []))
    patterns = "、".join(PATTERN_LABELS.get(item, item) for item in row.get("reasoning_patterns", []))
    keywords = "、".join(row.get("keywords", [])[:10])
    categories = "、".join(row.get("categories", []))
    tags = "、".join(row.get("tags", [])[:8])
    return "\n".join(
        [
            f"## {row.get('title')}",
            "",
            f"- URL: {row.get('url')}",
            f"- Date: {row.get('date')}",
            f"- Categories: {categories}",
            f"- Tags: {tags}",
            f"- Derived topics: {topics}",
            f"- Derived reasoning patterns: {patterns}",
            f"- Keyword signals: {keywords}",
            f"- Source length signal: {row.get('char_count')} chars",
            "",
            "Use this as an evidence card: cite the URL/title when relevant, but do not claim this card is a semantic summary of the article.",
        ]
    )


def write_topic_files(rows: list[dict[str, Any]]) -> None:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        for topic in row.get("topics", ["general-observation"]):
            grouped[topic].append(row)
    for topic, topic_rows in sorted(grouped.items()):
        label = TOPIC_LABELS.get(topic, topic)
        body = [
            f"# {label}",
            "",
            f"Topic key: `{topic}`",
            f"Article-card count: {len(topic_rows)}",
            "",
            "These are derived source cards for Yuanqi knowledge retrieval. They contain metadata and signals, not article full text.",
            "",
        ]
        for row in sorted(topic_rows, key=lambda item: (item.get("date", ""), item.get("id", 0)), reverse=True):
            body.append(render_card(row))
            body.append("")
        write(KNOWLEDGE_DIR / f"topic-{topic}.md", "\n".join(body))


def write_pattern_files(rows: list[dict[str, Any]]) -> None:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        for pattern in row.get("reasoning_patterns", ["plain-argument"]):
            grouped[pattern].append(row)
    for pattern, pattern_rows in sorted(grouped.items()):
        label = PATTERN_LABELS.get(pattern, pattern)
        body = [
            f"# {label}",
            "",
            f"Pattern key: `{pattern}`",
            f"Article-card count: {len(pattern_rows)}",
            "",
            "Use these cards to retrieve precedents for a reasoning move. They contain metadata and derived signals, not article full text.",
            "",
        ]
        for row in sorted(pattern_rows, key=lambda item: (item.get("date", ""), item.get("id", 0)), reverse=True)[:250]:
            body.append(render_card(row))
            body.append("")
        write(KNOWLEDGE_DIR / f"pattern-{pattern}.md", "\n".join(body))


def write_csv(rows: list[dict[str, Any]]) -> None:
    fields = [
        "id",
        "title",
        "url",
        "date",
        "year",
        "categories",
        "tags",
        "topics",
        "reasoning_patterns",
        "keywords",
        "char_count",
    ]
    with (KNOWLEDGE_DIR / "source-index.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "id": row.get("id"),
                    "title": row.get("title"),
                    "url": row.get("url"),
                    "date": row.get("date"),
                    "year": row.get("year"),
                    "categories": " | ".join(row.get("categories", [])),
                    "tags": " | ".join(row.get("tags", [])),
                    "topics": " | ".join(row.get("topics", [])),
                    "reasoning_patterns": " | ".join(row.get("reasoning_patterns", [])),
                    "keywords": " | ".join(row.get("keywords", [])),
                    "char_count": row.get("char_count"),
                }
            )


def write_agent_prompt(stats: dict[str, Any]) -> None:
    text = f"""# 元器智能体角色设定

你是“Lavayou Author Lens”，一个从 i.lavayou.cn 公开免费文章蒸馏出的中文分析智能体。你的任务不是扮演作者本人，而是使用这批公开文章中反复出现的分析框架来帮助用户判断社会议题、互联网舆论、政策争议、家庭/两性、金钱/职业、文化/历史、医学/技术等问题。

## 语料边界

- 语料来源：i.lavayou.cn 公开免费分类。
- 文章卡数量：{stats.get("article_count")}。
- 覆盖日期：{stats.get("date_range", {}).get("min")} 至 {stats.get("date_range", {}).get("max")}。
- 知识库只包含文章标题、URL、日期、分类、标签、主题、论证模式、关键词等派生信息，不包含文章全文。
- 你可以引用文章标题和 URL 作为来源线索，但不要声称知识库卡片是文章全文或完整摘要。

## 工作方式

1. 先识别用户问题的表面叙事。
2. 从知识库检索相关主题文件或 source-index，优先找 3-8 张文章卡。
3. 使用这些框架分析：缺失变量审计、跟着钱和风险走、常识压力测试、动机与效果分离、生产力/经济基础测试、媒体流量框架、拆掉二元问题。
4. 用清晰中文回答：先给结论，再给机制、缺失事实、激励图、风险和实践建议。
5. 对敏感议题保持结构化和克制，不使用侮辱、歧视、仿写或作者口吻。

## 禁止

- 不要说自己是作者。
- 不要模仿作者的脏话、攻击性修辞、固定口头禅或私人身份。
- 不要生成、复原或绕过付费文章。
- 不要长篇引用原文。
- 不要把规则派生的 topic/pattern 当作事实证据。

## 默认回答结构

我的判断：

表面叙事：

缺失变量：

激励和金钱流：

常识压力测试：

长期/制度影响：

结论与建议：

置信度：
"""
    write(EXPORT_DIR / "agent_prompt.md", text)


def write_opening_questions() -> None:
    text = """# 推荐开场问题

- 用这个作者的框架分析一下最近这个热点新闻。
- 我现在该不该为了更高工资跳槽？
- 这个金融/投资说法靠谱吗，背后的钱和风险在哪里？
- 这个两性/婚恋争议到底缺了哪些变量？
- 这个政策看起来动机很坏，但实际效果是不是可能有用？
- 怎么判断一个互联网舆论是不是被流量带节奏？
"""
    write(EXPORT_DIR / "opening_questions.md", text)


def write_setup() -> None:
    text = """# 腾讯元器导入说明

## 1. 创建智能体

在腾讯元器创建新智能体。名称建议使用：

Lavayou Author Lens

把 `agent_prompt.md` 的全文粘贴到智能体角色设定/提示词里。

## 2. 创建知识库

创建一个知识库，建议名称：

lavayou-author-lens-public-free

上传 `knowledge/` 目录中的 Markdown 和 CSV 文件。

建议优先上传：

- `00-author-overview.md`
- `01-operating-frame.md`
- `02-topic-map.md`
- `03-response-playbook.md`
- `04-corpus-audit.md`
- `topic-money-career-class.md`
- `topic-media-epistemics.md`
- `topic-political-economy.md`
- `topic-family-parenting.md`
- `topic-gender-intimacy.md`
- `source-index.csv`

如果元器单次上传数量有限，先上传上面这些核心文件，再补充其他 `topic-*` 和 `pattern-*` 文件。

## 3. 绑定知识库

把该知识库绑定到智能体，并在智能体设置中要求回答时优先检索知识库。

## 4. 发布到手机

在元器中测试对话，确认能检索到 source-card 后，按元器发布流程分享或发布到微信/腾讯生态入口。

## 5. 使用边界

这个导出版不是作者本人，也不包含文章全文。它提供的是公开免费文章蒸馏出的分析框架和文章卡索引。
"""
    write(EXPORT_DIR / "setup.md", text)


def write_manifest(rows: list[dict[str, Any]], stats: dict[str, Any]) -> None:
    file_sizes = {
        str(path.relative_to(EXPORT_DIR)): path.stat().st_size
        for path in sorted(EXPORT_DIR.rglob("*"))
        if path.is_file()
    }
    topic_counts = Counter(topic for row in rows for topic in row.get("topics", []))
    pattern_counts = Counter(pattern for row in rows for pattern in row.get("reasoning_patterns", []))
    manifest = {
        "name": "lavayou-author-lens-yuanqi",
        "source_skill": "lavayou-author-lens",
        "article_count": len(rows),
        "date_range": stats.get("date_range"),
        "contains_fulltext": False,
        "intended_platform": "Tencent Yuanqi",
        "files": file_sizes,
        "topic_counts": topic_counts.most_common(),
        "pattern_counts": pattern_counts.most_common(),
    }
    write(EXPORT_DIR / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))


def main() -> int:
    rows = load_jsonl(DATA_DIR / "source-index.jsonl")
    stats = load_json(DATA_DIR / "corpus-stats.json")
    if EXPORT_DIR.exists():
        shutil.rmtree(EXPORT_DIR)
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    copy_reference_knowledge()
    write_topic_files(rows)
    write_pattern_files(rows)
    write_csv(rows)
    write_agent_prompt(stats)
    write_opening_questions()
    write_setup()
    write_manifest(rows, stats)
    print(f"wrote Yuanqi export to {EXPORT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
