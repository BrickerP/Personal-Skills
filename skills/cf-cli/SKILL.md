---
name: cf-cli
description: >-
  Operates Yupeng's Cloudflare account with the official cf CLI (zones, DNS,
  tunnels, Workers, R2, D1). Use when the user mentions Cloudflare, cf, DNS
  records, zones, Workers, R2, tunnels, oakrelay, or cloudflared.
---

# Cloudflare cf CLI

Use `cf`. Do not use Wrangler unless the repo has `wrangler.toml` or `wrangler.jsonc` and no `cloudflare.config.ts`.

## This account

Logged in as `yplmicro@gmail.com`. One account, one zone. Confirmed with `cf auth whoami` and `cf zones list` on 2026-10-10.

- Account: `Yplmicro@gmail.com's Account` — `0fb0cd080737aa25896598941a71dccf`
- Zone: `oakrelay.dpdns.org` — `fcba66c7402c5c23c50fa657db00a482` — active, Free Website
- DNS: `CNAME ssh.oakrelay.dpdns.org` → `58cae6c4-7981-4b01-ada0-991e152997c9.cfargotunnel.com` (proxied)
- Tunnel ID: `58cae6c4-7981-4b01-ada0-991e152997c9` → `ssh://127.0.0.1:22`
- cloudflared config: `~/.cloudflared/config.yml`
- Tunnel credential file: `~/.cloudflared/58cae6c4-7981-4b01-ada0-991e152997c9.json`
- Stored login: `~/Library/Preferences/cloudflare/config/default.json`

Never print `TunnelSecret`, `cert.pem`, API tokens, or OAuth URLs.

`cf` does not reuse Wrangler or cloudflared logins. If a command is unauthenticated, run `cf auth login --no-device` and let the user approve the browser prompt. The device-code flow (`cf auth login` without `--no-device`) fails on the Baidu office network with `fetch failed`. API calls from that network often take 10–25 seconds. Pass `--zone oakrelay.dpdns.org` unless the user names another zone.

## Binary

Global npm package `cf` 1.0.0-beta.14. Requires Node.js 22.18+. If `cf` is not on PATH:

```bash
export PATH="$HOME/.nvm/versions/node/v22.22.1/bin:$PATH"
```

`cloudflared` is only the tunnel daemon.

## Run a command

1. Find it with one quoted phrase. Do not put names, domains, account IDs, or tokens in the query.

```bash
cf cli search "list dns records"
```

2. Read that command once: `<command> --help`. For the API shape, `cf schema <command without the leading cf>`.
3. Preview mutations with `--dry-run`, then run the real command.
4. Parse stdout only. It is indented JSON. Status and errors go to stderr.
5. A delete without `--force` in a non-interactive shell prints `Aborted.` and exits 0. Read stderr before calling that success.
6. Zone commands take `--zone <domain-or-id>`. Prefer the zone the user named. If they did not name one, list zones and use the zone that owns `oakrelay.dpdns.org`.
7. If a command needs an account and none is saved, pass account `0fb0cd080737aa25896598941a71dccf`.

Do not explore by chaining `--help`. Search first.

## Workers repos

Do not run `cf dev`, `cf build`, or `cf deploy` when the repo has a Wrangler config and no `cloudflare.config.ts`. Preview with `cf migrate --dry-run`, then `cf migrate`, and ask the user about any `TODO(@cloudflare)` item you cannot resolve.

## Credentials

`CLOUDFLARE_API_TOKEN` overrides the stored login. Do not write tokens into this skill, shell rc files, or git. Do not commit `.env`.
