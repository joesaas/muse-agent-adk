# 设计站 19 章 → 本项目模块映射（ADK 版）

材料：Muse 设计站《Muse 核心设计全解》（https://joesaas.github.io/muse-design-site/）

| 章 | 主题 | 落到的模块 | 状态 |
|---|---|---|---|
| ch01 | 整体架构 | core / runtime / 本文档分层 | 已实现最小版 |
| ch02 | 运维设计 | context 恢复快照、事件流、doctor | 已实现最小版（快照/事件/doctor） |
| ch03 | LLM 设计 | llm（ADK BaseLlm 工厂） | 已实现（MockLlm + Gemini + LiteLlm） |
| ch04 | 上下文工程 | prompts 分段、context 预算与压缩 | 已实现最小版 |
| ch05 | Agent 循环 | runtime/agent（ADK Runner） | 已实现（框架托管内圈） |
| ch06 | 审批与认证（HITL） | approval（风险分级 + 回调） | 已实现 |
| ch07 | 子代理编排 | subagents（sub_agents 树 + 隔离 run、深度上限） | 已实现 |
| ch08 | Skills 技能系统 | skills（SKILL.md、索引注入、关键词触发） | 已实现最小版 |
| ch09 | 连接器生态 | connectors（status/call 契约） | 接口 + 参考实现 |
| ch10 | 文件架构 | home（家目录布局）、identity（站立文件） | 已实现 |
| ch11 | 定时与后台 | scheduling（CronSpec/Scheduler/HookRegistry） | 判定已实现，托管未做 |
| ch12 | 安全设计 | security（凭证按名、redact、surrogate 缝） | 已实现最小版 |
| ch13 | 数据与隐私 | security 脱敏、数据全在用户目录 | 已实现最小版 |
| ch14 | 页面交互与多端 | cli 是第一个前端；多端是未来前端层 | 仅 CLI |
| ch15 | Memory 设计 | memory（两层文件记忆 + 关键词检索） | 已实现最小版 |
| ch16 | 身份与对齐 | identity + prompts/core 段 | 已实现 |
| ch17 | Feed 设计 | 属于内容产品层，不进 agent 核心；可作为 skill + cron 组合实现 | 设计说明（见 roadmap） |
| ch18 | Goals 与 Ideas | goals（目标与跟踪项）；Ideas 属于产品层，同 Feed 处理 | goals 已实现最小版 |
| ch19 | 一次真实交互的全程解剖 | runtime 流程 + 事件流（turn/tool/context/subagent 事件） | 已实现（事件可追踪全程） |

模块级设计文档在 [modules/](modules/) 下，每篇在原五节（职责 / 对外接口 / 与谁交互传什么 / 数据与状态 / 边界与代价）之后加一节「ADK 落地方式」，说明该模块在本项目里如何接到 ADK。
