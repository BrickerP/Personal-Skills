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

## 求职入口与执行方式

- **统一入口**：[job-search](skills/job-search/SKILL.md)。按意图进入搜索、筛选、简历、申请材料、投递、面试或复盘，只读取当前阶段需要的 Markdown。
- **页面驱动**：agent 读当前页面、判断下一步、用 chrome-use 逐步操作并回读验证。没有填表/上传/提交批量脚本，也不复活退休 CDP/Playwright 引擎。
- **辅助工具**：去重、公共岗位 API、哈希与只读有效性校验、确认后的记账可使用既有 helpers；不能由脚本决定答案或自动提交。
- `daily-50` 是投递阶段的例行预设，不是另一个 skill 或 runner。定时器、真实身份、FROZEN 答案和提交门禁保持原有规则。
- `daily-job-apply`、`job-apply-automation`、`job-search-orchestrator` 保留为旧调用的兼容入口，Codex metadata 关闭其隐式调用。其他工具不支持该 metadata 时，仍由兼容说明转到统一入口。
- `linkedin-application-agent` 仅保留冻结说明；`gh-resume-builder` 继续作为独立的经历证据/展示工具，在简历阶段按需调用。
- 安装求职能力需要 `job-search` 与 `daily-job-apply` 资源目录一起存在。现有 [安装器](scripts/install.sh) 会链接它们；只复制一个旧 skill 的旧 zip 不再是完整安装。

求职浏览器操作需要已连接真实 Chrome 的 chrome-use。无需安装旧 adapters 的 Node/Playwright 依赖；旧脚本留作历史，不进入活动工作流。pdf-sanitize 首次运行仍按自己的 skill 创建 .venv。

## 约定

- 不进库（.gitignore）：`node_modules/`、`.venv/`、`logs/`、`cache/`、`__pycache__/`
- 数据与运行状态（如 `~/job-hunt/`）**不**在本库；本库只放 skill 本体代码。
- OMX 框架自带 skills（autopilot/ralph/ultrawork/team 等 26 个）不在本库 —— 由 `omx setup` 管理。
- OpenCode 内置 skills（opencode/report/playwright 等）不在本库。

## Skills 清单

**求职**：[job-search](skills/job-search/SKILL.md)（生命周期入口）· gh-resume-builder（证据/展示）；旧求职名字只作兼容，LinkedIn 包冻结
**生活/订阅**：dating-time · daily-read · ai-daily · fs-street
**浏览器**：chrome-use · browser-use · browser-control
**云/支付/运维**：cf-cli · aws-cli · stripe-cli-ops · codex-usage · codex-wallpaper · [grok-remote](skills/grok-remote/SKILL.md)
**外观/终端**：wezterm-wallpaper（WezTerm 壁纸选择器 + 柔和模式）
**内容/资料**：obsidian · lark-history-exporter · gmail-ai-daily-ops · lavayou-author-lens
**创作/前端**：creative · draw-something · astryx-frontend · imagegen
**文档**：pdf · pdf-sanitize
**沟通**：ask-questions
**其他**：opentrain-application-agent · migrate-to-codex · gh-address-comments · gh-fix-ci · openai-docs
