---
name: stripe-cli-ops
description: >-
  Operates Stripe coupons and promotion codes via Stripe CLI and REST (curl):
  batch issue one-time codes, list/deactivate active codes, inspect codes. Use
  when the user mentions Stripe, promotion codes, coupons, sk_live/sk_test,
  bulk codes, disabling promos, or replacing Dashboard clicks with shell/API.
---

# Stripe CLI + API ops

## Defaults

1. **Auth**: `export STRIPE_API_KEY=sk_live_...` or `sk_test_...`. Never commit keys; never paste keys into repos or skills.
2. **Execute**: Run the scripts in this skill with bash; prefer them over retyping long curl.
3. **Dashboard parity**: Promotion codes cannot be deleted—set `active=false`. `expires_at`, `max_redemptions`, and core coupon amounts/duration are immutable after creation; issue **new** codes from a new or existing coupon to change expiry/value.

## Scripts (source of truth)

| Script | Role |
|--------|------|
| `scripts/stripe-issue-promo-codes.sh` | Create one new coupon + N one-time `promotion_code`s (`max_redemptions=1`, `expires_at` now + minutes). Modes: `percent` or `amount` (USD). Stdout: header line `code` then one code per line; stderr: progress. |
| `scripts/stripe-deactivate-active-promos.sh` | List `promotion_codes` with `active=true` (paginated). Keeps allowlist code (default `STAFF`, case-insensitive); sets `active=false` on the rest. Retries on 429/5xx. |
| `scripts/stripe-reissue-and-save.sh` | Deactivate-all-except-allowlist, then issue batch; writes **codes only** (drops the `code` header) to the path you pass. |

Paths are relative to the skill directory:

`/Users/yupeng/.cursor/skills/stripe-cli-ops/`

Mirror copy (optional): `~/.local/bin/stripe.sh` matches `stripe-issue-promo-codes.sh`.

## Common commands

**Issue (example: 100 codes, $30 off, 24 h)**

```bash
export STRIPE_API_KEY=sk_live_...
/Users/yupeng/.cursor/skills/stripe-cli-ops/scripts/stripe-issue-promo-codes.sh amount 100 30 1440
```

**Deactivate every active code except staff**

```bash
export STRIPE_API_KEY=sk_live_...
/Users/yupeng/.cursor/skills/stripe-cli-ops/scripts/stripe-deactivate-active-promos.sh STAFF
```

**One shot: deactivate (keep `STAFF`) + 100 × $30 + 24 h → file**

```bash
export STRIPE_API_KEY=sk_live_...
/Users/yupeng/.cursor/skills/stripe-cli-ops/scripts/stripe-reissue-and-save.sh \
  "~/projects/personal/quant/stripe_codes_2026-04-15.txt" 100 30 1440 STAFF
```

## Caveats

- **Amount-off caveat** (amount mode): discount caps at invoice amount; if the order total is below the dollar-off face value, the code is still consumed and there is no leftover credit.
- **100%-off caveat**: when a coupon/promo brings the checkout total to $0, Stripe creates **no PaymentIntent** — only the Checkout Session exists. Implications:
  - No `pi_xxx` in webhook payloads; no `charge.succeeded`, no fee.
  - `promotion_codes.times_redeemed` still increments → use that (not PI counts / webhook counts) to count redemptions.
  - In your own ledger, `paymentIntentId IS NULL AND sessionId IS NOT NULL` on a checkout-credit row is the structural marker of a 100%-off redemption. **Don't reach for the Stripe API to distinguish paid vs freebie — your DB already has the answer.**

## REST (curl) — when CLI is wrong tool

Auth on every request: `-u "$STRIPE_API_KEY:"` (colon, empty password).

- List active promotion codes: `GET /v1/promotion_codes?active=true&limit=100` (paginate with `starting_after=<last id>`).
- Update code: `POST /v1/promotion_codes/<id>` with `active=false`.
- Retrieve by code string: `GET /v1/promotion_codes?code=<CODE>&limit=1` (then read `data[0]` for `expires_at`, `max_redemptions`, `times_redeemed`, `active`).

## Agent checklist

1. Confirm `STRIPE_API_KEY` is set in the shell (or ask the user to export—do not hardcode).
2. For bulk changes: run `stripe-deactivate-active-promos.sh` with explicit allowlist, then `stripe-issue-promo-codes.sh` or `stripe-reissue-and-save.sh`.
3. On Stripe `500`/`429`: scripts retry; if still failing, short sleep and retry the step—large batches can hit transient errors.
4. Before querying Stripe API for "who paid / who used a promo": check if your own ledger already encodes it (see 100%-off caveat). Local DB wins on latency and data freshness.

## Requirements

- `stripe` CLI + `jq` for issuance script; `curl` + `jq` for deactivate script.
