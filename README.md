# Gmail AI Daily Ops

## 这是什么

Gmail AI Daily Ops 是一套给 Codex 使用的 Gmail 日常处理方案。

它的目标是：

1. 定时读取 Gmail 最新状态
2. 让 Codex 理解你的邮件工作流并持续整理重点
3. 自动准备 draft、归档和标签等低风险整理动作
4. 让你平时只需要：
   - 在 Codex 里问“今日活动进度”
   - 在 Gmail 里查看 draft 和整理结果

仓库主要包含三部分：

- `skills/gmail-ai-daily-ops/SKILL.md`
  - Codex 技能定义
- `tools/gmail-ai-worker/`
  - 本地 Gmail worker
- `docs/第一次使用文档.md`
  - 首次使用说明原稿

## 隐私边界

这个仓库已经做过公开化清理，不包含以下内容：

- Gmail token
- 已连接邮箱信息
- 本地 OAuth client 文件
- 历史 refresh cache
- 历史 run report
- 历史 daily progress
- 日志
- `secrets/` 下任何私有文件

你需要在本地自己提供：

- `tools/gmail-ai-worker/runtime/oauth_client.json`

这个文件不要提交到 GitHub。

## 首次安装

先 clone 仓库，然后进入 worker 目录：

```bash
cd tools/gmail-ai-worker
chmod +x "Start Gmail AI Ops.command" "Install Gmail Refresh Scheduler.command"
./Start\ Gmail\ AI\ Ops.command
```

这一步会：

- 安装依赖
- 检查本地 OAuth client 文件
- 引导第一次连接邮箱

如果提示缺少 OAuth client，请把你自己的 Google Desktop OAuth client JSON 放到：

```text
tools/gmail-ai-worker/runtime/oauth_client.json
```

然后重新运行：

```bash
./Start\ Gmail\ AI\ Ops.command
```

## 安装本地定时任务

继续执行：

```bash
cd tools/gmail-ai-worker
./Install\ Gmail\ Refresh\ Scheduler.command
```

默认调度节奏是：

- 每小时 `55` 分：本地刷新 Gmail
- 每小时 `00` 分：Codex automation 读取缓存并做判断
- 每小时 `05` 分：本地执行 draft / 归档 / 标签等写操作

如果你自己配置 Codex automation，推荐把 automation 挂在每小时整点执行。

## 重新安装前，先清除旧版本

如果你要彻底重装，先执行：

### 1. 卸载本地定时任务

```bash
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.gmail-ai-daily-ops.refresh.plist 2>/dev/null || true
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.gmail-ai-daily-ops.apply.plist 2>/dev/null || true
rm -f ~/Library/LaunchAgents/com.gmail-ai-daily-ops.refresh.plist
rm -f ~/Library/LaunchAgents/com.gmail-ai-daily-ops.apply.plist
```

### 2. 删除本地安装的 worker 和 skill

```bash
rm -rf ~/.codex/gmail-ai-daily-ops
rm -rf ~/.codex/skills/gmail-ai-daily-ops
```

### 3. 确认已经清干净

```bash
ls -la ~/.codex/skills | rg gmail-ai-daily-ops || true
ls -la ~/.codex | rg gmail-ai-daily-ops || true
launchctl list | rg 'com.gmail-ai-daily-ops.(refresh|apply)' || true
```

如果这些命令没有输出，说明已经基本清干净了。

### 4. 重新安装

```bash
cd tools/gmail-ai-worker
chmod +x "Start Gmail AI Ops.command" "Install Gmail Refresh Scheduler.command"
./Start\ Gmail\ AI\ Ops.command
./Install\ Gmail\ Refresh\ Scheduler.command
```

## 新增邮箱

以后如果要新增邮箱，执行：

```bash
cd ~/.codex/gmail-ai-daily-ops/gmail-ai-worker
source .venv/bin/activate
python scripts/connect_mailbox.py
```

查看已连接邮箱：

```bash
python scripts/list_connected_mailboxes.py
```

只启用一个邮箱：

```bash
python scripts/set_active_mailboxes.py --mailbox <MAILBOX_KEY>
```

同时启用多个邮箱：

```bash
python scripts/set_active_mailboxes.py --mailbox <MAILBOX_KEY_1> --mailbox <MAILBOX_KEY_2>
```

新增邮箱后默认会自动加入活跃邮箱列表。

## 修改定时节奏

例如改成：

- 每小时 `50` 分刷新
- 每小时 `10` 分执行写操作

执行：

```bash
cd ~/.codex/gmail-ai-daily-ops/gmail-ai-worker
source .venv/bin/activate
python scripts/install_launchd_refresh.py --refresh-minute 50 --apply-minute 10
```

## 手动前台跑一轮

如果你不想等后台定时任务，现在就想立即跑一轮：

先刷新 Gmail：

```bash
cd ~/.codex/gmail-ai-daily-ops/gmail-ai-worker
source .venv/bin/activate
python scripts/refresh_active_mailboxes.py
```

如果 Codex 已经写好了最新 action plan，要立刻执行 Gmail 写操作：

```bash
python scripts/apply_action_plan.py
```

## 查看定时任务是否运行

```bash
launchctl list | rg 'com.gmail-ai-daily-ops.(refresh|apply)'
```

## Codex App 使用要求

Codex app 需要在下面这个路径开一个 session 窗口来执行 automation：

```text
~/.codex/gmail-ai-daily-ops/gmail-ai-worker
```

也就是说，真正运行 automation 的工作目录应该是安装后的本地目录，不是这个 Git 仓库目录。

## 用户日常怎么使用

用户日常只需要两件事：

1. 在 Codex 里提问，例如：
   - `今日活动进度`
   - `今天有哪些 draft 已经准备好了`
   - `有哪些 active sessions 还在推进`
   - `今天我需要自己判断什么`

2. 去 Gmail 里查看：
   - draft
   - 已归档邮件
   - 已整理状态

## 报告与进度

系统会持续维护“今日累计进度”。

- 用户问 `今日活动进度` 时，Codex 应该直接回答当天累计的工作进度
- 用户不需要自己看日志，也不需要自己查看内部文件
- 每日进度按北京时间（`Asia/Shanghai`）切分
- 系统只保留最近 31 天的每日进度

## 什么时候需要重新配置

只有这几类情况才需要你手动操作：

- 新增邮箱
- 更改哪些邮箱参与处理
- 修改定时节奏
- 调整默认策略

其他时候，用户直接和 Codex 对话即可。
