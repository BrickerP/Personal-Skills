#!/usr/bin/env bash
# Deactivate all active promotion codes except allowlist, then issue new one-time codes and save (codes only).
#
# Usage:
#   export STRIPE_API_KEY=sk_live_...
#   ./stripe-reissue-and-save.sh <out_file> [count] [amount_usd] [expires_minutes] [allow_code]
#
# Example (100 × $30 off, 24h, keep STAFF):
#   ./stripe-reissue-and-save.sh ~/Downloads/Quant/stripe_codes_2026-04-15.txt 100 30 1440 STAFF

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
OUT="${1:?out_file required}"
COUNT="${2:-100}"
AMOUNT="${3:-30}"
MINUTES="${4:-1440}"
ALLOW="${5:-STAFF}"

export STRIPE_PROMO_ALLOWLIST="$ALLOW"

bash "$ROOT/stripe-deactivate-active-promos.sh" "$ALLOW"

TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT
bash "$ROOT/stripe-issue-promo-codes.sh" amount "$COUNT" "$AMOUNT" "$MINUTES" >"$TMP"

# First stdout line is the literal header "code" from issue script; drop it for a plain list.
tail -n +2 "$TMP" >"$OUT"

echo "Wrote $COUNT codes to $OUT" >&2
