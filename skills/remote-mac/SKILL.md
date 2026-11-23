---
name: remote-mac
description: Use when a task needs a shell, files, a port, or an OpenCode/Codex session on one of Yupeng's other Macs (M1, M3, M5), from any network. Connects with plain `ssh m1`, `ssh m3` or `ssh m5` through each Mac's Cloudflare Tunnel; no VPN and no shared Wi-Fi needed. Trigger phrases include 在 M1 上执行, 去 M5 跑, 远程跑命令, 另一台 Mac, 查 M5 的 opencode 会话, 把文件拷到 M1, run this on M5, ssh to M1.
---

# Remote Mac

`ssh m1`, `ssh m3` and `ssh m5` reach each Mac from any network. Each Mac keeps an outbound Cloudflare Tunnel, so nothing depends on the Macs sharing a Wi-Fi network or a VPN.

| Alias | Hardware | Notes |
|---|---|---|
| `m1` | Apple M1, 8 GB | Slow; use for light work |
| `m3` | Apple M3 | Personal machine |
| `m5` | Apple M5 | Work machine, managed by the employer |

## What each Mac needs

- Outbound HTTPS to Cloudflare. The Macs do not need the same network, a VPN, a public IP or an open port, and the tunnel works alongside DuLink, WARP and Clash Verge.
- Awake. A sleeping Mac drops its tunnel. On power, M5 and M1 sleep after 30 idle minutes (`pmset -g`); M3 is set never to sleep. Run long remote jobs under `caffeinate -i` so the target stays awake until they finish.
- Logged in. `cloudflared` runs as a LaunchAgent and FileVault is on, so after a restart the Mac stays unreachable until someone logs in at its screen.
- Remote Login on, keys only (`sudo ~/.local/bin/macmesh-harden`).

## Use

Check the identity first when it matters, then run the command:

```bash
ssh m5 'hostname; sysctl -n machdep.cpu.brand_string'
ssh m5 'cd ~/code/personal/repo && git status --short'
ssh m5 'zsh -s' < /absolute/path/to/script.sh      # multi-line script, no quoting problems
scp ./file m1:~/Downloads/                        # copy files (rsync -a works too)
ssh -N -L 4097:127.0.0.1:4096 m5                  # forward a port, e.g. another Mac's OpenCode server
```

The first connection takes about 7 seconds; later commands reuse it for 10 minutes and take about 1.3 seconds. Traffic relays through Cloudflare (the tunnels connect in Los Angeles), so copies are slow: a 2 MiB transfer took 12 to 35 seconds in the 2026-11-20 test.
Remote commands get a minimal PATH (no Homebrew, no nvm). Wrap them in the user's interactive shell to get the normal tools: `ssh m3 'zsh -lic "opencode --version"'`. `opencode` lives in Homebrew on M1 and M5 and under nvm on M3.

## Keychain: `gui-run`

Plain SSH sessions cannot use the login Keychain, so `git`/`gh` over HTTPS, `security`, and other Keychain-backed tools fail there with "User interaction is not allowed" or a credential prompt. Wrap those commands in `gui-run`, which runs them in the Mac's logged-in GUI session and returns their output and exit code:

```bash
ssh m5 'gui-run --cwd ~/code/personal/repo "git pull --ff-only && gh pr list"'
```

`gui-run` needs someone logged in at that Mac's screen (the normal state) and adds about 2 seconds.

## Rules

- Work inside the user's request. Reaching a Mac is not permission for unrelated changes there.
- A failure before the command starts (`websocket: bad handshake`, `Connection closed by UNKNOWN port 65535`, `timed out`) means the tunnel or the target is down: usually the Mac is asleep, offline, or restarted and not logged in. Retry once. If a state-changing command may have started, check its result on the target before running it again. On M3, `cloudflared tunnel list` shows which Macs' tunnels are connected.
- `Connection refused` or no answer from one Mac usually means it is asleep, offline, or has Remote Login turned off. Tell the user which Mac; do not switch to another remote channel.
- Never print, copy or commit `~/.config/cf-access/mac-ssh.env` (the Cloudflare Access service token) or any private key.

## How it works (for repairs)

- Each Mac runs `cloudflared` as a LaunchAgent with an outbound tunnel to Cloudflare: `com.user.cloudflared-home-ssh` on M3, `com.user.cloudflared-mac-ssh` on M1 and M5. Configs and logs are in `~/.cloudflared/`. Restart with `launchctl kickstart -k gui/$(id -u)/<label>`.
- The tunnels use `protocol: http2` and `edge-ip-version: "4"`; QUIC over UDP and the IPv6 path dropped connections on some networks.
- Cloudflare Access rejects connections that do not carry the service token. `cf-ssh-proxy` is the ssh `ProxyCommand`: it loads `~/.config/cf-access/mac-ssh.env` and clears proxy variables, because `cloudflared` cannot use an `https://` proxy.
- `~/.ssh/config` holds a managed `Host m1 m3 m5` block (delete the block to undo). Each Mac logs in with `~/.ssh/id_ed25519_macmesh`, and every Mac's `authorized_keys` lists all three public keys.
- The scripts live in this skill's `scripts/` directory and are symlinked into `~/.local/bin`: `cf-ssh-proxy`, `gui-run`, `macmesh-harden` (run once with sudo: SSH keys only, Remote Login on).
- The hostnames sit under `oakrelay.dpdns.org`, a free DigitalPlat FreeDomain name that is registered for a year at a time and renewed in the DigitalPlat dashboard. If it lapses, every `ssh m1|m3|m5` fails.

## Set up another Mac

Needs a tunnel and DNS name for the new Mac in the Cloudflare account, added to the Access application.

1. Symlink `scripts/cf-ssh-proxy`, `scripts/gui-run` and `scripts/macmesh-harden` into `~/.local/bin`.
2. Run `scripts/ssh-config-block.py <tunnel domain>`; copy the domain from `HostName` in another Mac's `~/.ssh/config`.
3. Copy the token file from a working Mac: `ssh m3 'cat ~/.config/cf-access/mac-ssh.env' > ~/.config/cf-access/mac-ssh.env` (mode 600).
4. Create `~/.ssh/id_ed25519_macmesh` and add its public key to every Mac's `authorized_keys`; run `sudo ~/.local/bin/macmesh-harden`.
