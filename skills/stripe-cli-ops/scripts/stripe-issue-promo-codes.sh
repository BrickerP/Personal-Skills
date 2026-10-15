#!/usr/bin/env bash
# Issue N one-time Stripe promotion codes via CLI + STRIPE_API_KEY env var.
#
# Usage:
#   export STRIPE_API_KEY=sk_live_...
#   ./scripts/stripe-issue-promo-codes.sh percent <count> <percent_off> <expires_in_minutes>
#   ./scripts/stripe-issue-promo-codes.sh amount  <count> <amount_usd>  <expires_in_minutes>
#
# Modes:
#   percent  each code gives <percent_off>% off (1-100)
#   amount   each code gives <amount_usd> USD off; if the user's charge is
#            lower than amount_usd, Stripe caps the discount at the charge
#            (user pays $0) and the code is still consumed — leftover value
#            is NOT refunded or carried over.
#
# Examples:
#   ./scripts/stripe-issue-promo-codes.sh percent 5  15  60     # 5 codes, 15% off, expire in 60 min
#   ./scripts/stripe-issue-promo-codes.sh percent 1  100 1440   # 1 code,  100% off (free), 1 day
#   ./scripts/stripe-issue-promo-codes.sh amount  10 30  120    # 10 codes, $30 off each, 2 hours
#   ./scripts/stripe-issue-promo-codes.sh amount  20 30  1655   # 20 codes, $30 off, until US West 00:00

set -euo pipefail

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  sed -n '2,21p' "$0"
  exit 0
fi

if [[ -z "${STRIPE_API_KEY:-}" ]]; then
  echo "STRIPE_API_KEY is not set. Run: export STRIPE_API_KEY=sk_live_..." >&2
  exit 1
fi

if ! command -v stripe >/dev/null 2>&1; then
  echo "stripe CLI not found. Install: https://stripe.com/docs/stripe-cli" >&2
  exit 1
fi
if ! command -v jq >/dev/null 2>&1; then
  echo "jq not found. Install: brew install jq" >&2
  exit 1
fi

MODE="${1:?usage: $0 <percent|amount> <count> <value> <expires_in_minutes>}"
COUNT="${2:?count required}"
VALUE="${3:?value required (percent_off for percent mode, amount_usd for amount mode)}"
MINUTES="${4:?expires_in_minutes required (>=1)}"

case "$MODE" in
  percent|amount) ;;
  *) echo "mode must be 'percent' or 'amount' (got '$MODE')" >&2; exit 1 ;;
esac

[[ "$COUNT"   =~ ^[1-9][0-9]*$ ]]   || { echo "count must be a positive integer" >&2; exit 1; }
[[ "$VALUE"   =~ ^[0-9]+\.?[0-9]*$ ]] || { echo "value must be a positive number" >&2; exit 1; }
[[ "$MINUTES" =~ ^[1-9][0-9]*$ ]]   || { echo "expires_in_minutes must be >= 1" >&2; exit 1; }

NOW_ISO="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

if [[ "$MODE" == "percent" ]]; then
  awk -v p="$VALUE" 'BEGIN { exit !(p > 0 && p <= 100) }' \
    || { echo "percent_off must be 0 < x <= 100" >&2; exit 1; }
  DISPLAY="${VALUE}% off"
  COUPON_NAME="promo ${NOW_ISO} ${VALUE}%off"
  COUPON_ARGS=( --percent-off="$VALUE" --duration=once --name="$COUPON_NAME" )
else
  awk -v a="$VALUE" 'BEGIN { exit !(a > 0) }' \
    || { echo "amount_usd must be > 0" >&2; exit 1; }
  # USD dollars -> integer cents (Stripe amount_off uses smallest currency unit).
  AMOUNT_CENTS="$(awk -v a="$VALUE" 'BEGIN { printf "%.0f", a * 100 }')"
  [[ "$AMOUNT_CENTS" =~ ^[1-9][0-9]*$ ]] \
    || { echo "amount_usd must be >= 0.01 (got $VALUE -> $AMOUNT_CENTS cents)" >&2; exit 1; }
  DISPLAY="\$${VALUE} off (USD)"
  COUPON_NAME="promo ${NOW_ISO} \$${VALUE}off"
  COUPON_ARGS=( --amount-off="$AMOUNT_CENTS" --currency=usd --duration=once --name="$COUPON_NAME" )
fi

EXPIRES_AT=$(( $(date +%s) + MINUTES * 60 ))

if date -r "$EXPIRES_AT" '+%Y-%m-%d %H:%M %z' >/dev/null 2>&1; then
  HUMAN_EXP="$(date -r "$EXPIRES_AT" '+%Y-%m-%d %H:%M %z')"
else
  HUMAN_EXP="unix $EXPIRES_AT"
fi

SEP="=========================================================="
HR="----------------------------------------------------------"

{
  echo "$SEP"
  echo " Stripe Promo Code Issuance"
  echo "$SEP"
  printf "  Mode         : %s\n" "$MODE"
  printf "  Discount     : %s (per code)\n" "$DISPLAY"
  printf "  Count        : %s code(s)\n" "$COUNT"
  printf "  Redemption   : one-time use per code (max_redemptions=1)\n"
  printf "  Expires in   : %s minute(s)\n" "$MINUTES"
  printf "  Expires at   : %s\n" "$HUMAN_EXP"
  printf "  Stripe key   : %s (last4)\n" "${STRIPE_API_KEY: -4}"
  echo "$HR"
} >&2

echo "[1/2] Creating coupon on Stripe..." >&2
COUPON_JSON="$(stripe coupons create \
  --api-key="$STRIPE_API_KEY" \
  -c \
  "${COUPON_ARGS[@]}"
)"

COUPON_ID="$(printf '%s' "$COUPON_JSON" | jq -r .id)"
if [[ -z "$COUPON_ID" || "$COUPON_ID" == "null" ]]; then
  echo "      FAILED to create coupon. Stripe response:" >&2
  printf '%s\n' "$COUPON_JSON" >&2
  exit 1
fi
printf "      -> Coupon created: %s\n" "$COUPON_ID" >&2
printf "         Name: %s\n" "$COUPON_NAME" >&2
echo "" >&2

echo "[2/2] Creating $COUNT promotion code(s)..." >&2
echo "      (printing codes to stdout; everything else to stderr)" >&2
echo "code"

i=0
for _ in $(seq 1 "$COUNT"); do
  i=$(( i + 1 ))
  OUT="$(stripe promotion_codes create \
    --api-key="$STRIPE_API_KEY" \
    -c \
    --promotion.type=coupon \
    --promotion.coupon="$COUPON_ID" \
    --max-redemptions=1 \
    --expires-at="$EXPIRES_AT"
  )"
  CODE="$(printf '%s' "$OUT" | jq -r .code)"
  if [[ -z "$CODE" || "$CODE" == "null" ]]; then
    printf "      [%d/%d] FAILED. Stripe response:\n" "$i" "$COUNT" >&2
    printf '%s\n' "$OUT" >&2
    exit 1
  fi
  printf "      [%d/%d] %s\n" "$i" "$COUNT" "$CODE" >&2
  printf '%s\n' "$CODE"
done

{
  echo "$HR"
  echo " Done."
  printf "  Codes issued : %s\n" "$COUNT"
  printf "  Discount     : %s per code\n" "$DISPLAY"
  printf "  Expires      : %s (in %s min)\n" "$HUMAN_EXP" "$MINUTES"
  printf "  Coupon ID    : %s\n" "$COUPON_ID"
  printf "  Redemption   : one-time use per code\n"
  echo "$SEP"
} >&2
