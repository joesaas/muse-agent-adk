# muse-agent-adk 总架构

一句话：**muse-agent 的架构与模块划分原样保留，底层执行换成 Google ADK 2.x。** 原项目（joesaas/muse-agent）用标准库手写了 Agent 循环、provider 协议与工具分发；本项目把这三件事交给 ADK 的 `LlmAgent` / `Runner` / `BaseLlm` / `FunctionTool`，其余模块——core 契约、prompts 分段、context 预算与压缩、memory 文件记忆、skills、approval 策略、scheduling 判定、goals、home 布局——保持原设计与原接口，在 ADK 的接缝处对接。

本项目同样是学习性复刻：借鉴的是 Muse 公开可归纳的设计（19 章设计站），不是对 Muse 未公开内部实现的断言。ADK 是 Google 的开源 Agent 框架，本项目用它替换的是「执行层」，不是「设计思想」。

## 技术选型

| 选择 | 决定 | 理由 |
|---|---|---|
| 语言 | Python 3.11+ | 与原项目一致 |
| 框架 | **Google ADK >=2,<3** | Agent 循环、工具分发、子代理委派、session 管理都是框架的一等能力，不再手写 |
| 模型 | 默认 MockLlm（离线、确定性，继承 ADK `BaseLlm`） | 无 Key 即可运行与测试全系统 |
| 模型（真实） | Gemini 原生（ADK `Gemini`）；OpenAI 兼容端点经 ADK `LiteLlm`（可选 extra） | 供应商差异收敛到 llm/factory 一个工厂函数 |
| 存储 | 纯文本文件（md / json / toml），与原项目同格式 | 用户拥有、可读、可备份、可与原项目互迁 |
| 测试 | pytest（全离线，MockLlm 驱动真实 Runner） | 测的是真框架路径，不是替身 |

## 分层（与原项目同构，标注 ADK 接点）

```
前端层      CLI（本仓库） · 聊天端 / API（未来，只做入口与渲染）
              │  build_session()
运行时层    runtime/session（唯一装配点） · runtime/agent（Runner 封装）
              │  ADK Runner + InMemorySessionService 驱动 LlmAgent 树
              │  事件适配 → core/events 总线（turn/tool/subagent 事件）
能力层      llm（BaseLlm 工厂） · prompts · context（桥接 ADK session）
            memory（文件 + session state 桥） · skills · tools（FunctionTool）
            connectors（能力以工具暴露） · subagents（sub_agents 树 + 隔离 run）
治理层      approval（策略 + before_tool_callback 闸门） · security
            scheduling（cron / hooks，只判定） · goals（目标与跟踪）
地基层      core（数据契约 + 事件 + 错误） · identity（站立文件） · home（目录布局）
            config（环境 + config.toml，秘密永不进配置）
```

依赖方向与原项目同一条规矩：**上层可以依赖下层，同层经 core 契约通信，core 不依赖任何业务包；ADK 类型只出现在 llm/runtime/tools/context.bridge/approval.gate 这几个接缝模块里，不渗进业务模块。**

## 一次交互的流程（对照设计站 ch19）

1. 前端收到用户消息 → `build_session()`（或复用已有 Session）
2. Session 组装：home 布局 → 身份文件 → 精选记忆 → skills 索引 → tools 规格 → 系统提示词分段拼装 → 构建 ADK 模型 → 创建 ADK session（state 播种 memory 索引）
3. `Agent.run_turn()` 在自有事件循环上跑一轮：
   - context bridge 先行：把 ADK session events 镜像为 core 消息，超预算 → 压缩并**轮换** ADK session（新 session 只带摘要事件 + 最近消息），发 `context.compressed` 事件
   - 以 `state_delta` 刷新 memory 索引，调 `Runner.run_async()` 进入 ADK 内圈：模型 →（工具调用 → before_tool_callback 过审批闸门 → FunctionTool 执行 → 结果回注）→ 最终文本
   - ADK 事件被适配回 core 总线（`turn.started/finished`、`tool.called/finished`）
   - 落恢复快照（原 JSON 格式，按逻辑 session id 存，轮换不丢）
4. 外圈与原项目一致：cron 到期、hook 命中、子代理完成都以事件唤醒同一个循环。scheduling 仍只判定不托管。
5. 子代理两条 ADK 路径：模型驱动时 transfer 到 `sub_agents` 里的 worker（ADK 把完整会话交给它，等价于全量快照）；程序驱动（CLI/测试）时 SubagentManager 用独立 Runner + 独立 ADK session 跑 worker，简报文本内嵌父会话快照渲染，父 session 零污染。

## 设计原则（继承原项目）

1. **模块只经接口说话**：跨模块只流通 core 的数据类；ADK 对象只在接缝层出现。
2. **数据归用户**：记忆、身份、目标、skills 都是用户目录里的纯文本，格式与原项目兼容。
3. **提示词是注册表**：分段、编号、有序、可禁用、可单测——拼装结果作为 LlmAgent 的 instruction。
4. **能力是数据**：skill 是 Markdown（索引进 instruction、正文经 load_skill 工具按需加载），工具是注册项（自动变 FunctionTool），连接器是适配器（能力以工具暴露）。
5. **治理内建**：审批是策略 + 回调闸门，不是约定；**无人值守默认拒绝需审批动作（本项目对原版的刻意修正，见下）**。
6. **可观测与可恢复内建**：事件流 + 每轮快照，崩溃后能续、事后能查。
7. **不追求速度，追求边界正确**：先模块与契约，后优化与规模。

## 与原版 muse-agent 的差异（如实列出）

| # | 差异 | 说明 |
|---|---|---|
| 1 | **审批默认改为 fail-closed** | 原版评审发现：未传 approver 的 session 默认落到 auto_approver（fail-open）。本项目 ApprovalPolicy 在 approver=None 时对 write/exec 一律 DENY；CLI 等前端必须显式传入 approver。README 与 approval 模块文档均有标注。 |
| 2 | Agent 循环由 ADK Runner 托管 | 原版 `max_steps` 是自家循环的硬保险；ADK 的循环步数由框架管理，config 中保留该字段仅作口径对齐，不再直接生效。打断改为 Runner 的 abort_signal + 协作式检查。 |
| 3 | 上下文压缩改为 session 轮换 | ADK session 的 events 只追加不可改写；压缩因此实现为「镜像 → 压缩 → 新 session 播种摘要与最近事件」。旧 session 留在 SessionService 中作审计，不删除。 |
| 4 | provider 协议换成 ADK BaseLlm | 原版 `LLMProvider.complete()` 协议删除；`build_model(config)` 返回 ADK 模型对象（MockLlm / Gemini / LiteLlm）。OpenAI 兼容不再走自家 urllib adapter，改走 LiteLlm（可选 extra）。 |
| 5 | 工具多了一层签名合成 | 注册表仍是唯一事实源；FunctionTool 的参数签名由 ToolSpec 的 JSON schema 合成，执行仍回注册表 `execute()`，错误仍作数据返回。 |
| 6 | 新增三个工具 | load_skill（skills 渐进披露的加载口）、memory_search / remember（memory 的工具面；remember 是 write，受审批闸门管辖）、connector_<name>（连接器能力暴露）。原版这些能力只在 CLI/规划中存在。 |
| 7 | 包名与家目录改名 | 包 `muse_agent_adk`、命令 `muse-agent-adk`、默认 home `~/.muse-agent-adk`、环境变量前缀 `MUSE_AGENT_ADK_`，与原版可并存。 |

## 与设计站 19 章的对应

见 [chapter-map.md](chapter-map.md)：每章 → 落到哪个模块 → 当前状态。

## 当前状态与诚实边界

- 已实现并测试：ADK 运行时全链路（对话、工具往返、审批放行/拒绝、子代理 transfer 与隔离 spawn、skills 按需加载、memory 落盘与 state 桥、上下文压缩轮换、快照恢复格式），pytest 全离线 23 项通过。
- 占位/参考：连接器仅 EchoConnector 参考实现；SessionService 用进程内 InMemory 版（可换 ADK 的持久化实现，接口不变）；调度只判定不托管（与原版一致）；子代理隔离 spawn 的快照是文本渲染版（原版是消息深拷贝——语义等价、形态不同，超长时截断并标注）。
- 未做：多端前端、向量检索、LLM 摘要器（Summarizer 接口已留）、ADK 插件生态接入。
