#!/usr/bin/env bash
# Set active=false on all *active* promotion codes except an allowlisted code (case-insensitive).
# Stripe does not support deleting promotion codes; disabling is the supported removal path.
#
# Usage:
#   export STRIPE_API_KEY=sk_live_...
#   ./stripe-deactivate-active-promos.sh [ALLOW_CODE]
#
# Env:
#   STRIPE_PROMO_ALLOWLIST  default STAFF (override first arg)

set -euo pipefail

if [[ -z "${STRIPE_API_KEY:-}" ]]; then
  echo "STRIPE_API_KEY is not set." >&2
  exit 1
fi
if ! command -v curl >/dev/null 2>&1 || ! command -v jq >/dev/null 2>&1; then
  echo "Requires curl and jq." >&2
  exit 1
fi

ALLOW_RAW="${1:-${STRIPE_PROMO_ALLOWLIST:-STAFF}}"
ALLOW_LC="$(printf '%s' "$ALLOW_RAW" | tr '[:upper:]' '[:lower:]')"

stripe_curl_retry() {
  local method="$1"
  local url="$2"
  local data="${3:-}"
  local attempt=0
  local max=10
  local tmp
  tmp="$(mktemp)"
  while (( attempt < max )); do
    local http
    if [[ "$method" == "GET" ]]; then
      http=$(curl -sS -u "$STRIPE_API_KEY:" -o "$tmp" -w "%{http_code}" "$url")
    else
      http=$(curl -sS -u "$STRIPE_API_KEY:" -o "$tmp" -w "%{http_code}" -X POST "$url" -d "$data")
    fi
    if [[ "$http" == "200" ]]; then
      cat "$tmp"
      rm -f "$tmp"
      return 0
    fi
    if [[ "$http" == "429" || "$http" == "500" || "$http" == "502" || "$http" == "503" ]]; then
      local w=$((2 ** attempt))
      [[ "$w" -gt 60 ]] && w=60
      echo "HTTP $http — retry in ${w}s (attempt $((attempt + 1))/$max)..." >&2
      sleep "$w"
      attempt=$((attempt + 1))
      continue
    fi
    echo "Stripe HTTP $http:" >&2
    cat "$tmp" >&2
    rm -f "$tmp"
    return 1
  done
  echo "Stripe: max retries exceeded (last HTTP $http)" >&2
  cat "$tmp" >&2
  rm -f "$tmp"
  return 1
}

starting_after=""
total=0
kept=0
disabled=0

while true; do
  q="https://api.stripe.com/v1/promotion_codes?active=true&limit=100"
  if [[ -n "$starting_after" ]]; then
    q="${q}&starting_after=${starting_after}"
  fi
  page="$(stripe_curl_retry GET "$q")"
  err="$(printf '%s' "$page" | jq -r '.error.message // empty')"
  if [[ -n "$err" ]]; then
    echo "List error: $err" >&2
    exit 1
  fi
  n="$(printf '%s' "$page" | jq '.data | length')"
  i=0
  while (( i < n )); do
    row="$(printf '%s' "$page" | jq -c ".data[$i]")"
    pid="$(printf '%s' "$row" | jq -r .id)"
    code="$(printf '%s' "$row" | jq -r .code)"
    code_lc="$(printf '%s' "$code" | tr '[:upper:]' '[:lower:]')"
    total=$((total + 1))
    if [[ "$code_lc" == "$ALLOW_LC" ]]; then
      echo "keep  $code  ($pid)" >&2
      kept=$((kept + 1))
    else
      echo "off   $code  ($pid)" >&2
      out="$(stripe_curl_retry POST "https://api.stripe.com/v1/promotion_codes/${pid}" "active=false")"
      e2="$(printf '%s' "$out" | jq -r '.error.message // empty')"
      if [[ -n "$e2" ]]; then
        echo "Deactivate failed for $code: $e2" >&2
        exit 1
      fi
      disabled=$((disabled + 1))
    fi
    i=$((i + 1))
  done
  has_more="$(printf '%s' "$page" | jq -r .has_more)"
  if [[ "$has_more" != "true" ]]; then
    break
  fi
  last_id="$(printf '%s' "$page" | jq -r '.data[-1].id')"
  starting_after="$last_id"
done

echo "---- summary: scanned=$total kept=$kept disabled=$disabled allowlist=$ALLOW_RAW ----" >&2
