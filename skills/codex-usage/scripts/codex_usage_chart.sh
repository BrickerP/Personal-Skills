#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 /path/to/codex-usage.json" >&2
  exit 2
fi

json_path="$1"
if [[ ! -f "$json_path" ]]; then
  echo "missing json: $json_path" >&2
  exit 2
fi

if ! command -v gnuplot >/dev/null 2>&1; then
  echo "missing tool: gnuplot" >&2
  exit 2
fi

if ! command -v imgcat >/dev/null 2>&1; then
  echo "missing tool: imgcat" >&2
  exit 2
fi

tsv_path="/tmp/codex-usage.tsv"
top5_path="/tmp/codex-usage-top5.md"
png_path="/tmp/codex-usage-month.png"
gp_path="/tmp/codex-usage.gp"

python3 - <<'PY' "$json_path" "$tsv_path" "$top5_path"
import json
import datetime as dt
import sys

json_path = sys.argv[1]
tsv_path = sys.argv[2]
top5_path = sys.argv[3]

with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

daily = data.get("daily", [])
model_names = sorted({m for d in daily for m in d.get("models", {}).keys()})

rows = []
cum = 0.0
for d in daily:
    date_raw = d.get("date", "")
    try:
        date = dt.datetime.strptime(date_raw, "%b %d, %Y").strftime("%Y-%m-%d")
    except ValueError:
        date = date_raw
    cost = float(d.get("costUSD", 0) or 0)
    cum += cost
    input_tokens = int(d.get("inputTokens", 0) or 0)
    cached = int(d.get("cachedInputTokens", 0) or 0)
    output_tokens = int(d.get("outputTokens", 0) or 0)
    reasoning = int(d.get("reasoningOutputTokens", 0) or 0)
    total_tokens = int(d.get("totalTokens", 0) or 0)
    cache_ratio = cached / input_tokens if input_tokens else 0.0
    model_tokens = [int(d.get("models", {}).get(m, {}).get("totalTokens", 0)) for m in model_names]
    rows.append([date, cost, cum, input_tokens, cached, output_tokens, reasoning, total_tokens, cache_ratio] + model_tokens)

with open(tsv_path, "w", encoding="utf-8") as f:
    header = ["date", "cost", "cum_cost", "input", "cached", "output", "reasoning", "total", "cache_ratio"] + model_names
    f.write("\t".join(header) + "\n")
    for r in rows:
        f.write("\t".join(str(x) for x in r) + "\n")

top_days = sorted(daily, key=lambda d: float(d.get("costUSD", 0) or 0), reverse=True)[:5]
lines = [
    "Top 5 Days by Cost (USD)",
    "| Date | Cost USD | Total Tokens | Input Tokens | Cached Input Tokens | Output Tokens | Reasoning Output Tokens |",
    "| --- | --- | --- | --- | --- | --- | --- |",
]
for d in top_days:
    date_raw = d.get("date", "")
    try:
        date = dt.datetime.strptime(date_raw, "%b %d, %Y").strftime("%Y-%m-%d")
    except ValueError:
        date = date_raw
    cost = float(d.get("costUSD", 0) or 0)
    total_tokens = int(d.get("totalTokens", 0) or 0)
    input_tokens = int(d.get("inputTokens", 0) or 0)
    cached = int(d.get("cachedInputTokens", 0) or 0)
    output_tokens = int(d.get("outputTokens", 0) or 0)
    reasoning = int(d.get("reasoningOutputTokens", 0) or 0)
    lines.append(
        f"| {date} | {cost:.4f} | {total_tokens} | {input_tokens} | {cached} | {output_tokens} | {reasoning} |"
    )

with open(top5_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
PY

cat > "$gp_path" <<'GP'
set terminal pngcairo size 2200,1400 enhanced font 'Menlo,14'
set output '/tmp/codex-usage-month.png'
set datafile separator '\t'
set timefmt '%Y-%m-%d'
set xdata time
set format x '%m-%d'
set tics scale 0.5
set grid back lc rgb '#dddddd'

set title 'Codex Monthly Usage (Asia/Shanghai)'
set ylabel 'USD'
set y2label 'Cumulative USD'
set y2tics
set boxwidth 0.7*24*3600
set style fill solid 0.6 border -1
plot '/tmp/codex-usage.tsv' using 1:2 with boxes lc rgb '#2b7a78' title 'Daily cost', \
     '' using 1:3 with lines lw 2 lc rgb '#17252a' axes x1y2 title 'Cumulative cost'
GP

gnuplot "$gp_path"
imgcat "$png_path" >/dev/null
cat "$top5_path"
echo "$png_path"
