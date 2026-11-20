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

## Use

Check the identity first when it matters, then run the command:

```bash
ssh m5 'hostname; sysctl -n machdep.cpu.brand_string'
ssh m5 'cd ~/code/personal/repo && git status --short'
ssh m5 'zsh -s' < /absolute/path/to/script.sh      # multi-line script, no quoting problems
scp ./file m1:~/Downloads/                        # copy files (rsync -a works too)
ssh -N -L 4097:127.0.0.1:4096 m5                  # forward a port, e.g. another Mac's OpenCode server
```

The first connection takes about 10 to 15 seconds; later ones reuse it for 10 minutes.
Remote commands get a minimal PATH (no Homebrew, no nvm). Wrap them in the user's interactive shell to get the normal tools: `ssh m3 'zsh -lic "opencode --version"'`. `opencode` lives in Homebrew on M1 and M5 and under nvm on M3.

## Rules

- Work inside the user's request. Reaching a Mac is not permission for unrelated changes there.
- A failure before the command starts (`Connection closed by UNKNOWN port 65535`, `timed out`) means the tunnel or the target is down. Retry once. If a state-changing command may have started, check its result on the target before running it again.
- `Connection refused` or no answer from one Mac usually means it is asleep, offline, or has Remote Login turned off. Tell the user which Mac; do not switch to another remote channel.
- Never print, copy or commit `~/.config/cf-access/mac-ssh.env` (the Cloudflare Access service token) or any private key.

## How it works (for repairs)

- Each Mac runs `cloudflared` as a LaunchAgent with an outbound tunnel to Cloudflare: `com.user.cloudflared-home-ssh` on M3, `com.user.cloudflared-mac-ssh` on M1 and M5. Configs and logs are in `~/.cloudflared/`. Restart with `launchctl kickstart -k gui/$(id -u)/<label>`.
- The tunnels use `protocol: http2` and `edge-ip-version: "4"`; QUIC over UDP and the IPv6 path dropped connections on some networks.
- Cloudflare Access rejects connections that do not carry the service token. `~/.local/bin/cf-ssh-proxy` is the ssh `ProxyCommand`: it loads the token file and clears proxy variables, because `cloudflared` cannot use an `https://` proxy.
- `~/.ssh/config` holds a managed `Host m1 m3 m5` block (delete the block to undo). Each Mac logs in with `~/.ssh/id_ed25519_macmesh`, and every Mac's `authorized_keys` lists all three public keys.
- `sudo ~/.local/bin/macmesh-harden` makes a Mac accept SSH keys only and turns on Remote Login if it is off.
