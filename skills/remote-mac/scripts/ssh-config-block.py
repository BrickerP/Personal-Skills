"""Idempotently install the managed `Host m1 m3 m5` block in ~/.ssh/config and point any
`Host home` ProxyCommand at the cf-ssh-proxy wrapper.

Usage: ssh-config-block.py <tunnel domain>   (the domain under which m1/m3/m5 are published)
"""
import os
import re
import sys
import time

if len(sys.argv) != 2 or "." not in sys.argv[1]:
    sys.exit("usage: ssh-config-block.py <tunnel domain>")
DOMAIN = sys.argv[1]

path = os.path.expanduser("~/.ssh/config")
begin, end = "# >>> mac-mesh (managed; delete this block to undo) >>>", "# <<< mac-mesh <<<"
block = "\n".join([
    begin,
    "Host m1 m3 m5",
    f"  HostName %h.{DOMAIN}",
    "  User yupeng",
    "  IdentityFile ~/.ssh/id_ed25519_macmesh",
    "  IdentitiesOnly yes",
    "  ProxyCommand ~/.local/bin/cf-ssh-proxy %h",
    "  ConnectTimeout 30",
    "  ServerAliveInterval 30",
    "  ServerAliveCountMax 4",
    "  ControlMaster auto",
    "  ControlPath ~/.ssh/cm-%C",
    "  ControlPersist 10m",
    "  StrictHostKeyChecking accept-new",
    "  UserKnownHostsFile ~/.ssh/known_hosts_macmesh",
    end,
    "",
])
text = open(path).read() if os.path.exists(path) else ""
original = text
text = re.sub(re.escape(begin) + r".*?" + re.escape(end) + r"\n?", "", text, flags=re.S)
lines, in_home, changed_home = text.split("\n"), False, 0
for i, line in enumerate(lines):
    stripped = line.strip()
    if re.match(r"(?i)^(host|match)\s", stripped):
        in_home = re.match(r"(?i)^host\s+(.*\s)?home(\s|$)", stripped) is not None
    elif in_home and re.match(r"(?i)^proxycommand\s.*cloudflared\s+access\s+ssh", stripped):
        indent = line[: len(line) - len(line.lstrip())]
        lines[i] = indent + "ProxyCommand ~/.local/bin/cf-ssh-proxy %h"
        changed_home += 1
text = "\n".join(lines).rstrip("\n")
text = (text + "\n\n" if text else "") + block
if text != original:
    if original:
        backup = path + ".bak-macmesh-" + time.strftime("%Y%m%d-%H%M%S")
        with open(backup, "w") as f:
            f.write(original)
        os.chmod(backup, 0o600)
    with open(path, "w") as f:
        f.write(text)
    os.chmod(path, 0o600)
print(f"ssh config: managed block installed; Host home ProxyCommand updated: {changed_home}")
