---
name: echo-helper
description: 示例 skill：演示 SKILL.md 的结构（frontmatter + 正文 playbook）
triggers: echo, 示例
---
# Echo Helper（示例 skill）

这是一个最小示例，用来说明 skill 的写法：

1. frontmatter 里写 `name`、`description`、`triggers`。
2. 正文是给 agent 照着做的 playbook，写步骤，不写空话。
3. 需要验证工具链时，调用 `echo` 工具把给定文本原样返回，再向用户复述结果。

真实 skill 应把一个可复用的工作流沉淀在这里：何时触发、步骤、检查点、交付格式。
