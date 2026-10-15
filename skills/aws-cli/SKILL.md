---
name: aws-cli
description: Load AWS credentials and run aws CLI commands. Yupeng has separate AWS accounts — personal (Quant / trading), former-work (retired 2026-07), dating (Get-Date-Love), plus a small trade-ai-prod account. Use whenever the user asks to run AWS commands, query AWS resources, or mentions AWS services (S3, EC2, Lambda, IAM, etc.). **Always confirm which account before running.** For Quant live EC2 operations, use SSM Run Command — no SSH or security-group edits needed.
---

# AWS CLI

Separate AWS accounts. **Never mix them.** If the request doesn't make it obvious which account, ask before running.

Use `bash` (not `zsh` — zsh's aws wrapper mangles variable-expanded args).

---

## Account 1 — PERSONAL (Quant / trading)

- Account: `890968193131` (2026-10 migration target; the old account `376791751748` is RETIRED — every old key returns InvalidClientTokenId, never use it)
- IAM user: `cli-admin` (AdministratorAccess)
- Region: `us-east-1`
- Credentials: macOS Keychain `AWS-Personal-Quant` is the source of truth. `~/.aws/credentials [default]` and the repo `.env` are synced replicas.

Re-sync any time (safe; upserts only `[default]`, never clobbers other profiles):

```bash
bash ~/projects/personal/quant/quant-trading/scripts/sync_aws_creds_from_keychain.sh
```

Then bare `aws` works (default profile = this account):

```bash
bash <<'EOF'
unset AWS_PROFILE
aws <service> <command> --no-cli-pager
EOF
```

`--profile neal` also exists and points at the same account (legacy alias — prefer the default profile).

### Quant live server — always via SSM

- Instance: `quant-trading-live-01` = `i-06caa12820c64dcf6` (t3.small, us-east-1). Re-verify before assuming:

  ```bash
  aws ec2 describe-instances --filters Name=instance-state-name,Values=running \
    --query 'Reservations[].Instances[].[InstanceId,Tags[?Key==`Name`].Value|[0]]' --output table
  ```

- **No Elastic IP**: the public IP changes on every boot. Do not SSH. Use SSM Run Command (check `PingStatus: Online` via `aws ssm describe-instance-information`).
- Lifecycle: starts ~07:45 ET weekdays (`quant-live-start` → Lambda `quant-ec2-sleeper`); stops when idle ~17:20 ET.
- Repo on the box: `/home/ubuntu/quant-trading`; strategy service `quant-strategy` (`journalctl -u quant-strategy`).
- SSM caveat: commands run as **root**; for git inside the repo use `sudo -u ubuntu git -C /home/ubuntu/quant-trading ...` (root hits git's "dubious ownership" guard).

```bash
bash <<'EOF'
unset AWS_PROFILE
CMD_ID=$(aws ssm send-command --instance-ids i-06caa12820c64dcf6 \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=["hostname; systemctl is-active quant-strategy"]' \
  --query 'Command.CommandId' --output text --no-cli-pager)
sleep 6
aws ssm get-command-invocation --command-id "$CMD_ID" \
  --instance-id i-06caa12820c64dcf6 --no-cli-pager
EOF
```

- Buckets: `quant-trading-assets-890968193131` (private: backups / strategy logs / env relay), `quant-dashboard-890968193131` (public dashboard output).
- Dashboard served by CloudFront `E3D84JACRKK7SB` from the dashboard bucket.

Triggers: "personal", "quant", "trading", "my EC2", "个人", "自己的 aws".

---

## Account 2 — FORMER WORK (retired 2026-07)

- Account: `360783618989`, IAM user `yupeng` (AdministratorAccess), region `us-east-1`
- Credentials: named profile `yupeng` at `~/.aws/credentials`
- ⚠️ This account is RETIRED (2026-07). Stored keys invalid (rotated upstream); the Keychain entry was deleted 2026-10-15. Do not use.

```bash
aws <service> <command> --profile yupeng --no-cli-pager
```

Triggers: "work", "工作", "前公司给的 aws", "yupeng profile", "360783618989".

---

## Account 3 — DATING (Get-Date-Love project)

- Account: `412381772524`
- IAM user: `ClaudeCLI` (AdministratorAccess)
- Region: `us-east-2` (servers live here)
- Credentials: named profile `dating` at `~/.aws/credentials` (chmod 600)
- Known servers: `i-04c09f2e25a2631c9` (t3.large "Oversea Match", prod), `i-03b8c2b97963444dd` (t2.micro "devServer") — verify with describe-instances before assuming

Use `--profile dating`:

```bash
aws <service> <command> --profile dating --no-cli-pager
```

Or for a whole session:

```bash
export AWS_PROFILE=dating
aws sts get-caller-identity
```

Triggers: "dating", "get-date-love", "getdatelove", "约会项目", "dating server", "Oversea Match", "412381772524".

---

## Account 4 — TRADE-AI-PROD (small side account)

- Account: `781646710808`, IAM user `tradeai-app` (**limited permissions** — e.g. no `ec2:DescribeAddresses`), region `us-east-1`
- Credentials: named profile `trade-ai-prod` at `~/.aws/credentials`
- Known instance: `tradeai-app` = `i-06db4b07dc749962a` (t3.micro, us-east-1f). Purpose is not documented in this skill — confirm intent with Yupeng before doing anything beyond read-only inspection.

Triggers: "tradeai", "trade-ai", "trade-ai-prod", "781646710808".

---

## Safety rules (do not violate)

1. **Environment variables beat profiles silently.** An exported `AWS_ACCESS_KEY_ID` (or a stale `source`d env file) overrides `--profile` for the whole shell. Run cross-account work in fresh `bash <<'EOF' ... EOF` blocks.
2. **Always run `aws sts get-caller-identity` first** if there's any doubt which account is active.
3. **Ambiguous request → ask.** Don't guess. "Delete the S3 bucket X" is dangerous if the wrong account is active.
4. **No cross-account operations** unless the user explicitly asks. Different owners, different billing, different blast radius.

---

## Quick reference

| User says | Mechanism | Account |
|---|---|---|
| "quant" / "my personal EC2" / "trading" | bare `aws` (default profile) | 890968193131 |
| "work" / "前公司 aws" | `--profile yupeng` (keys currently invalid) | 360783618989 |
| "dating" / "get-date-love" / "Oversea Match" | `--profile dating` | 412381772524 |
| "tradeai" / "trade-ai" | `--profile trade-ai-prod` | 781646710808 |
| Just "aws" with no context | default = quant; confirm first if destructive | 890968193131 |

---

## Disaster recovery — macOS Keychain backup

All credentials are duplicated in Yupeng's login Keychain as a backup against local file loss. Retrieve via `security find-generic-password -s <service> -a <account> -w`.

| Service | Accounts stored | State |
|---|---|---|
| `AWS-Personal-Quant` | `access_key_id`, `secret_access_key` | ✅ current (account 890968193131) |
| `AWS-Dating-GetDateLove` | `access_key_id`, `secret_access_key` | ✅ current |
| `Quant-Trading-APIs` | `alpaca_api_key`, `alpaca_secret_key`, `polygon_api_key` | ✅ used by prewarm/scripts |

- Quant rehydrate: run the sync script above (Keychain → `[default]` + repo `.env`).
- Dating rehydrate if `~/.aws/credentials` is lost:

```bash
mkdir -p ~/.aws && chmod 700 ~/.aws
cat > ~/.aws/credentials <<CRED
[dating]
aws_access_key_id = $(security find-generic-password -s AWS-Dating-GetDateLove -a access_key_id -w)
aws_secret_access_key = $(security find-generic-password -s AWS-Dating-GetDateLove -a secret_access_key -w)
CRED
chmod 600 ~/.aws/credentials
```

- A pre-cleanup snapshot of `~/.aws` (2026-10-14; includes the retired account's keys) lives at `~/.aws-backup-20261014.tgz` — safe to delete once the new setup has proven itself.

**Never print retrieved secrets into the conversation.** Only use `security find-generic-password ... -w` values to (1) write back into local config files, or (2) pipe directly into `aws ...` invocations.
