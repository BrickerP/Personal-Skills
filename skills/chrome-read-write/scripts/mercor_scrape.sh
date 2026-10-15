#!/usr/bin/env bash
# Scrape listing IDs from current Mercor explore page. Usage: mercor_scrape.sh <target_id>
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
"$SCRIPT_DIR/chrome_eval.sh" "$1" "$SCRIPT_DIR/mercor_scrape_listings.js"
