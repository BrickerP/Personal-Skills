#!/usr/bin/env python3
"""Ingest public free Lavayou posts into derived cards and corpus statistics.

The default output intentionally excludes full article text. Use
--keep-working-fulltext only for local analysis; do not ship that file in the
skill package.
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


API_ROOT = "https://i.lavayou.cn/wp-json/wp/v2"
FREE_CATEGORY_ID = 226
USER_AGENT = "Mozilla/5.0 (compatible; CodexSkillBuilder/1.0; +local)"


TOPIC_RULES: dict[str, list[str]] = {
    "media-epistemics": [
        "媒体",
        "新闻",
        "小编",
        "带节奏",
        "流量",
        "舆论",
        "标题",
        "反转",
        "热搜",
        "互联网",
        "带心上网",
    ],
    "political-economy": [
        "生产力",
        "经济基础",
        "上层建筑",
        "社会主义",
        "资本主义",
        "共产党",
        "阶级",
        "国家",
        "治理",
        "政策",
    ],
    "money-career-class": [
        "钱",
        "工资",
        "收入",
        "职场",
        "工作",
        "加班",
        "买房",
        "投资",
        "基金",
        "房价",
        "消费",
        "成本",
        "收益",
    ],
    "gender-intimacy": [
        "男性",
        "女性",
        "女权",
        "男权",
        "两性",
        "婚姻",
        "恋爱",
        "相亲",
        "丈夫",
        "妻子",
        "舔狗",
        "性别",
    ],
    "family-parenting": [
        "父母",
        "孩子",
        "子女",
        "家庭",
        "亲子",
        "育儿",
        "教育",
        "原生家庭",
        "孝",
        "女儿",
        "儿子",
    ],
    "health-medicine": [
        "医学",
        "医疗",
        "医院",
        "医生",
        "健康",
        "疾病",
        "药",
        "中医",
        "癌",
        "疫苗",
        "禁烟",
    ],
    "history-geopolitics": [
        "历史",
        "美国",
        "欧洲",
        "俄罗斯",
        "日本",
        "香港",
        "台湾",
        "战争",
        "军事",
        "国际",
        "文明",
    ],
    "science-technology": [
        "科学",
        "技术",
        "互联网",
        "产品",
        "AI",
        "算法",
        "工程",
        "物理",
        "化学",
        "数学",
    ],
    "culture-values": [
        "文化",
        "三观",
        "价值观",
        "文明",
        "传统",
        "道德",
        "哲学",
        "宗教",
        "读书",
        "书",
    ],
}


PATTERN_RULES: dict[str, list[str]] = {
    "follow-the-money": ["跟着钱走", "钱不骗人", "利益", "成本", "收益", "风险", "价格", "谁出钱"],
    "missing-variable-audit": ["为什么不", "没有提", "不提", "关键", "细节", "新闻六要素", "反常", "有鬼"],
    "base-and-productivity": ["生产力", "经济基础", "上层建筑", "客观规律", "社会经济发展"],
    "motive-vs-effect": ["动机", "目的", "幌子", "结果", "长期来看", "短期", "本身对不对"],
    "anti-traffic-frame": ["带节奏", "流量", "舆论", "小编", "媒体", "热搜", "反转"],
    "binary-dissolver": ["是，也不是", "一边", "另一边", "不是说", "而是说", "问题不在于"],
    "common-sense-stress-test": ["常识", "要是你", "换成", "正常人", "合理性", "不可能"],
}


SERIES_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("A-series", re.compile(r"^A\d+")),
    ("numbered-essay", re.compile(r"^\d{1,4}\s")),
    ("带心上网", re.compile(r"带心上网")),
]


class TextExtractor(HTMLParser):
    BLOCK_TAGS = {"p", "div", "li", "ul", "ol", "blockquote", "br", "h1", "h2", "h3", "h4"}
    SKIP_TAGS = {"script", "style", "noscript"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.SKIP_TAGS:
            self.skip_depth += 1
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.SKIP_TAGS and self.skip_depth:
            self.skip_depth -= 1
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self.skip_depth:
            return
        self.parts.append(data)

    def text(self) -> str:
        raw = "".join(self.parts)
        raw = html.unescape(raw).replace("\xa0", " ")
        lines = []
        for line in raw.splitlines():
            line = re.sub(r"\s+", " ", line).strip()
            if not line or line == ".":
                continue
            lines.append(line)
        return "\n".join(lines)


def strip_html(value: str) -> str:
    parser = TextExtractor()
    parser.feed(value or "")
    return parser.text()


def normalize_title(value: Any) -> str:
    if isinstance(value, dict):
        value = value.get("rendered", "")
    return strip_html(str(value)).strip()


def fetch_json(url: str, retries: int = 4) -> tuple[Any, dict[str, str]]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Accept-Encoding": "identity",
        },
    )
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                body = response.read().decode("utf-8")
                headers = {k.lower(): v for k, v in response.headers.items()}
                return json.loads(body), headers
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
            time.sleep(min(2**attempt, 8))
    raise RuntimeError(f"Failed to fetch {url}: {last_error}")


def paginated(endpoint: str, params: dict[str, Any], delay_s: float) -> list[dict[str, Any]]:
    all_items: list[dict[str, Any]] = []
    page = 1
    total_pages = None
    while True:
        query = dict(params)
        query.setdefault("per_page", 100)
        query["page"] = page
        url = f"{API_ROOT}/{endpoint}?{urllib.parse.urlencode(query, doseq=True)}"
        data, headers = fetch_json(url)
        if not isinstance(data, list):
            raise RuntimeError(f"Expected list from {url}, got {type(data).__name__}")
        all_items.extend(data)
        if total_pages is None:
            total_pages = int(headers.get("x-wp-totalpages") or "1")
        print(f"{endpoint}: page {page}/{total_pages}, items={len(data)}", file=sys.stderr)
        if page >= total_pages or not data:
            break
        page += 1
        time.sleep(delay_s)
    return all_items


def count_terms(text: str, terms: list[str]) -> int:
    lowered = text.lower()
    count = 0
    for term in terms:
        needle = term.lower()
        if not needle:
            continue
        count += lowered.count(needle)
    return count


def classify(text: str, title: str, category_names: list[str], tag_names: list[str]) -> tuple[list[str], list[str]]:
    haystack = "\n".join([title, " ".join(category_names), " ".join(tag_names), text])
    topic_scores = {
        topic: count_terms(haystack, terms)
        for topic, terms in TOPIC_RULES.items()
    }
    pattern_scores = {
        pattern: count_terms(haystack, terms)
        for pattern, terms in PATTERN_RULES.items()
    }
    topics = [topic for topic, score in sorted(topic_scores.items(), key=lambda item: (-item[1], item[0])) if score > 0][:4]
    patterns = [pattern for pattern, score in sorted(pattern_scores.items(), key=lambda item: (-item[1], item[0])) if score > 0][:4]
    if not topics:
        topics = ["general-observation"]
    if not patterns:
        patterns = ["plain-argument"]
    return topics, patterns


def extract_series(title: str) -> list[str]:
    series = [name for name, pattern in SERIES_PATTERNS if pattern.search(title)]
    return series or ["unseriesed"]


def pick_keywords(text: str, title: str, category_names: list[str], tag_names: list[str]) -> list[str]:
    candidates: collections.Counter[str] = collections.Counter()
    for tag in tag_names:
        if tag != "全文免费":
            candidates[tag] += 8
    for cat in category_names:
        if cat not in {"所有", "全文免费"}:
            candidates[cat] += 6
    haystack = title + "\n" + text
    for topic_terms in TOPIC_RULES.values():
        for term in topic_terms:
            hits = haystack.count(term)
            if hits:
                candidates[term] += hits
    for pattern_terms in PATTERN_RULES.values():
        for term in pattern_terms:
            hits = haystack.count(term)
            if hits:
                candidates[term] += hits
    return [term for term, _ in candidates.most_common(12)]


def auto_summary(topics: list[str], patterns: list[str], keywords: list[str], char_count: int) -> str:
    topic_text = ", ".join(topics[:3])
    pattern_text = ", ".join(patterns[:2])
    keyword_text = ", ".join(keywords[:6])
    return (
        f"derived from full-text scan: topics={topic_text}; "
        f"patterns={pattern_text}; signals={keyword_text}; chars={char_count}"
    )


def make_card(
    post: dict[str, Any],
    categories_by_id: dict[int, str],
    tags_by_id: dict[int, str],
) -> tuple[dict[str, Any], str]:
    title = normalize_title(post.get("title"))
    excerpt = strip_html((post.get("excerpt") or {}).get("rendered", ""))
    content_html = (post.get("content") or {}).get("rendered", "")
    text = strip_html(content_html)
    category_ids = [int(item) for item in post.get("categories", [])]
    tag_ids = [int(item) for item in post.get("tags", [])]
    category_names = [categories_by_id.get(item, str(item)) for item in category_ids]
    tag_names = [tags_by_id.get(item, str(item)) for item in tag_ids]
    topics, patterns = classify(text, title, category_names, tag_names)
    keywords = pick_keywords(text, title, category_names, tag_names)
    date = str(post.get("date", ""))[:10]
    year = date[:4] if date else "unknown"
    card = {
        "id": int(post["id"]),
        "url": post.get("link", ""),
        "date": date,
        "modified": str(post.get("modified", ""))[:10],
        "title": title,
        "excerpt_present": bool(excerpt),
        "categories": category_names,
        "tags": tag_names,
        "topics": topics,
        "reasoning_patterns": patterns,
        "series": extract_series(title),
        "keywords": keywords,
        "char_count": len(text),
        "year": year,
        "summary_auto": auto_summary(topics, patterns, keywords, len(text)),
    }
    return card, text


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def summarize(cards: list[dict[str, Any]], categories: list[dict[str, Any]], tags: list[dict[str, Any]]) -> dict[str, Any]:
    topic_counts: collections.Counter[str] = collections.Counter()
    pattern_counts: collections.Counter[str] = collections.Counter()
    tag_counts: collections.Counter[str] = collections.Counter()
    category_counts: collections.Counter[str] = collections.Counter()
    year_counts: collections.Counter[str] = collections.Counter()
    series_counts: collections.Counter[str] = collections.Counter()
    keyword_counts: collections.Counter[str] = collections.Counter()
    total_chars = 0
    for card in cards:
        topic_counts.update(card["topics"])
        pattern_counts.update(card["reasoning_patterns"])
        tag_counts.update(card["tags"])
        category_counts.update(card["categories"])
        year_counts.update([card["year"]])
        series_counts.update(card["series"])
        keyword_counts.update(card["keywords"])
        total_chars += int(card["char_count"])
    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source": {
            "site": "https://i.lavayou.cn",
            "api": API_ROOT,
            "free_category_id": FREE_CATEGORY_ID,
        },
        "article_count": len(cards),
        "total_extracted_chars": total_chars,
        "average_extracted_chars": round(total_chars / len(cards), 1) if cards else 0,
        "date_range": {
            "min": min((card["date"] for card in cards if card["date"]), default=None),
            "max": max((card["date"] for card in cards if card["date"]), default=None),
        },
        "topic_counts": topic_counts.most_common(),
        "reasoning_pattern_counts": pattern_counts.most_common(),
        "category_counts": category_counts.most_common(),
        "tag_counts": tag_counts.most_common(80),
        "year_counts": sorted(year_counts.items()),
        "series_counts": series_counts.most_common(),
        "keyword_counts": keyword_counts.most_common(100),
        "category_catalog_count": len(categories),
        "tag_catalog_count": len(tags),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=str(Path(__file__).resolve().parents[1] / "data"))
    parser.add_argument("--delay", type=float, default=0.35)
    parser.add_argument("--keep-working-fulltext", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    categories = paginated("categories", {"_fields": "id,count,name,parent,link,description"}, args.delay)
    tags = paginated("tags", {"_fields": "id,count,name,slug"}, args.delay)
    posts = paginated(
        "posts",
        {
            "categories": FREE_CATEGORY_ID,
            "_fields": "id,date,modified,link,title,excerpt,content,categories,tags",
        },
        args.delay,
    )
    categories_by_id = {int(item["id"]): item.get("name", str(item["id"])) for item in categories}
    tags_by_id = {int(item["id"]): item.get("name", str(item["id"])) for item in tags}
    cards: list[dict[str, Any]] = []
    full_rows: list[dict[str, Any]] = []
    for post in posts:
        card, text = make_card(post, categories_by_id, tags_by_id)
        cards.append(card)
        if args.keep_working_fulltext:
            full_rows.append({"id": card["id"], "url": card["url"], "title": card["title"], "date": card["date"], "text": text})
    cards.sort(key=lambda row: (row["date"], row["id"]), reverse=True)
    write_jsonl(output_dir / "source-index.jsonl", cards)
    write_json(output_dir / "corpus-stats.json", summarize(cards, categories, tags))
    write_json(output_dir / "category-catalog.json", categories)
    write_json(output_dir / "tag-catalog.json", tags)
    if args.keep_working_fulltext:
        work_dir = output_dir / "_work"
        work_dir.mkdir(parents=True, exist_ok=True)
        write_jsonl(work_dir / "free-articles-fulltext.jsonl", full_rows)
    print(f"wrote {len(cards)} cards to {output_dir / 'source-index.jsonl'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
