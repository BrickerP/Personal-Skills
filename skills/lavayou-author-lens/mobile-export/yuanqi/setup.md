# 腾讯元器导入说明

## 1. 创建智能体

在腾讯元器创建新智能体。名称建议使用：

Lavayou Author Lens

把 `agent_prompt.md` 的全文粘贴到智能体角色设定/提示词里。

## 2. 创建知识库

创建一个知识库，建议名称：

lavayou-author-lens-public-free

上传 `knowledge/` 目录中的 Markdown 和 CSV 文件。

建议优先上传：

- `00-author-overview.md`
- `01-operating-frame.md`
- `02-topic-map.md`
- `03-response-playbook.md`
- `04-corpus-audit.md`
- `topic-money-career-class.md`
- `topic-media-epistemics.md`
- `topic-political-economy.md`
- `topic-family-parenting.md`
- `topic-gender-intimacy.md`
- `source-index.csv`

如果元器单次上传数量有限，先上传上面这些核心文件，再补充其他 `topic-*` 和 `pattern-*` 文件。

## 3. 绑定知识库

把该知识库绑定到智能体，并在智能体设置中要求回答时优先检索知识库。

## 4. 发布到手机

在元器中测试对话，确认能检索到 source-card 后，按元器发布流程分享或发布到微信/腾讯生态入口。

## 5. 使用边界

这个导出版不是作者本人，也不包含文章全文。它提供的是公开免费文章蒸馏出的分析框架和文章卡索引。
