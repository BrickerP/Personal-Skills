# Personal Skills

Yupeng 的个人 skills 单一来源库（mono repo）。**一份内容，多工具共享** —— 通过 symlink 安装到各 AI 工具目录（Codex / Claude Code / Cursor / OpenCode / 其他 agents 兼容层）。

- 本 repo 是这些 skills 的**唯一 canonical 位置**：直接在这里编辑，各工具即时生效。
- OpenCode 通过 `~/.config/opencode/opencode.json` 的 `skills` 配置继承本库（经工具目录链接）。

## 结构

```
skills/<id>/SKILL.md    # 每个 skill 一个目录，目录名 = skill ID
scripts/install.sh      # 安装器（symlink 到 ~/.codex/skills、~/.claude/skills、~/.cursor/skills、~/.agents/skills）
```

## 新机器 / 恢复安装

```bash
git clone https://github.com/BrickerP/Personal-Skills.git ~/projects/personal/skills
~/projects/personal/skills/scripts/install.sh            # 建立全部 symlink
~/projects/personal/skills/scripts/install.sh --status   # 检查链接完整性
```

## 可选依赖（首次使用对应 skill 时）

```bash
# 求职流水线（Ashby/Greenhouse 适配器的 node 依赖）
cd skills/daily-job-apply/adapters && npm install

# pdf-sanitize 首次运行自动创建自己的 .venv（PyMuPDF 等）
```

## 约定

- 不进库（.gitignore）：`node_modules/`、`.venv/`、`logs/`、`cache/`、`__pycache__/`
- 数据与运行状态（如 `~/job-hunt/`）**不**在本库；本库只放 skill 本体代码。
- OMX 框架自带 skills（autopilot/ralph/ultrawork/team 等 26 个）不在本库 —— 由 `omx setup` 管理。
- OpenCode 内置 skills（opencode/report/playwright 等）不在本库。

## Skills 清单（32）

**求职**：daily-job-apply · job-search-orchestrator · linkedin-application-agent · gh-resume-builder
**生活/订阅**：dating-time · daily-read · ai-daily · fs-street
**浏览器**：chrome-use · browser-use · chrome-read-write · browser-control
**云/支付/运维**：cf-cli · aws-cli · stripe-cli-ops · codex-usage · codex-wallpaper
**内容/资料**：obsidian · lark-history-exporter · gmail-ai-daily-ops · lavayou-author-lens
**创作/前端**：creative · draw-something · astryx-frontend · imagegen
**文档**：pdf · pdf-sanitize
**其他**：opentrain-application-agent · migrate-to-codex · gh-address-comments · gh-fix-ci · openai-docs
