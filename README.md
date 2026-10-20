# muse-agent-adk

[muse-agent](https://github.com/joesaas/muse-agent) 的 **Google ADK 重构版**：整体思路、模块划分与数据格式保持不变，底层执行换成 [Google ADK](https://google.github.io/adk-docs/) 2.x——Agent 循环、模型调用、工具分发、子代理委派不再手写，交给框架的 `LlmAgent` / `Runner` / `BaseLlm` / `FunctionTool`。

原项目是照 **Muse 的设计思想** 复刻的 super agent（材料是 [Muse 设计站 19 章](https://joesaas.github.io/muse-design-site/)），目的是通过复刻来学习架构。本项目在它之上再学一件事：**同一套架构落到一个真实 Agent 框架上，接缝在哪里、哪些东西框架替你做了、哪些仍然要自己守。**

- 语言：Python 3.11+；依赖：`google-adk>=2,<3`（OpenAI 兼容端点另需可选 extra `litellm`）
- 默认 MockLlm：继承 ADK `BaseLlm` 的离线确定性模型，无 API Key 即可跑通全系统与全部测试
- 真实模型：Gemini 原生；任意 OpenAI 兼容端点经 ADK 的 LiteLlm 包装接入

## 快速开始

### 方式一：离线 demo（不需要任何 Key）

```bash
git clone https://github.com/joesaas/muse-agent-adk
cd muse-agent-adk
python3 -m venv .venv && .venv/bin/pip install -e ".[test]"

.venv/bin/muse-agent-adk --home /tmp/muse-agent-adk-demo demo
```

demo 输出（mock 模型，确定性）：

```
— 1) 普通对话
（mock 回复）我收到了：你能做什么？。接入真实模型后，这里会是模型的回答。
— 2) 工具调用（echo）
工具结果：echo -> 工具调用走通了
— 3) 工具调用（now）
工具结果：now -> 2026-10-20T08:41:40+00:00
— 4) 子代理
工具结果：echo -> 我是子代理，我完成了任务
— demo 完成
```

其他命令（与原项目对齐）：

```bash
muse-agent-adk init      # 在 ~/.muse-agent-adk 生成家目录
muse-agent-adk doctor    # 看模块、skills、tools、连接器状态
muse-agent-adk run "你好"
muse-agent-adk chat      # 交互模式
muse-agent-adk prompt    # 打印拼装出的系统提示词
muse-agent-adk skills    # 列出已发现的 skills
muse-agent-adk memory 时区   # 搜索文件记忆
muse-agent-adk subagent "echo: 替我确认子代理能工作"
```

### 方式二：配 Gemini

```bash
export GOOGLE_API_KEY=<你的 key>
export MUSE_AGENT_ADK_PROVIDER=gemini        # 默认模型 gemini-2.5-flash
# export MUSE_AGENT_ADK_MODEL=gemini-2.5-pro # 可选
muse-agent-adk run "你好"
```

### 方式三：配 OpenAI 兼容端点

```bash
pip install "muse-agent-adk[litellm]"        # LiteLlm 是可选 extra
export OPENAI_API_KEY=<你的 key>
export MUSE_AGENT_ADK_PROVIDER=openai-compatible
export MUSE_AGENT_ADK_MODEL=your-model
# export MUSE_AGENT_ADK_BASE_URL=https://your-endpoint/v1   # 非 OpenAI 官方端点时改
muse-agent-adk run "你好"
```

凭证只按**名字**从环境变量取（`MUSE_AGENT_ADK_API_KEY_ENV` 可改变量名），永不写进 config 或落盘——与原项目 security 模块同一条规矩。

## 架构：什么没变，什么换了

模块划分与原项目一一对应（core / llm / prompts / identity / context / memory / skills / tools / connectors / subagents / approval / security / scheduling / goals / runtime / home + cli），每篇模块文档在原五节之后加了一节「ADK 落地方式」。总览见 [docs/architecture.md](docs/architecture.md)，19 章映射见 [docs/chapter-map.md](docs/chapter-map.md)。

| 模块 | 原项目（手写） | 本项目（ADK） |
|---|---|---|
| llm | 自家 `LLMProvider` 协议 + urllib adapter | ADK `BaseLlm`：MockLlm / Gemini / LiteLlm，工厂 `build_model()` |
| runtime | 手写 agent 循环（问模型→审批→执行→回注） | `Runner` 驱动 `LlmAgent` 树；runtime 只管外圈（压缩检查、事件适配、快照、打断） |
| tools | 注册表 + 循环内直调 handler | 注册表仍是唯一事实源，每项自动合成 `FunctionTool`（签名由 ToolSpec 的 schema 生成） |
| subagents | 进程内深拷贝快照 + 同构 Agent | 双路径：`sub_agents` 树（模型 transfer 委派）+ 隔离 Runner spawn（简报内嵌快照文本）；另备 AgentTool 形态 |
| approval | 循环内 `policy.check()` | 策略不变，执行点换成 ADK `before_tool_callback`；DENY 返回结果 dict 跳过执行 |
| context | ContextManager 直接持有消息 | 对话活在 ADK session events 里；bridge 在 run 之间镜像、算预算、压缩并**轮换 session** |
| memory | 两层文件记忆 | 文件格式不变；加 state 桥（索引进 session state、每轮 state_delta 刷新）与工具面（memory_search / remember） |
| skills | 索引进提示词、正文触发加载 | 索引进 LlmAgent instruction；正文经 `load_skill` 工具按需加载 |
| connectors | status/call 契约 | 契约不变；能力以 `connector_<name>` 工具暴露给模型 |

## 与原版的差异（如实列出）

完整版见 [docs/architecture.md](docs/architecture.md) 的差异表，最重要的三条：

1. **审批默认从 fail-open 改为 fail-closed（刻意修正）。** 原版评审发现：未传 approver 的 session 会静默落到 auto_approver。本项目 `ApprovalPolicy` 在没有 approver 时对 write/exec 一律拒绝——前端（CLI/聊天端/测试）必须显式传入同意来源。可以直接验证：不带 approver 组装 session，让它 `remember: 任意内容`，工具会被拒且不落盘。
2. **`max_steps` 不再直接生效。** 原版靠它给自家循环上保险；ADK 循环由框架管理，该 config 字段保留仅作口径对齐。打断改为 Runner 的 abort_signal + 协作检查。
3. **压缩的实现形态变了。** ADK session 的 events 只追加不可改，压缩因此是「新 session 播种摘要 + 最近事件」的轮换；旧 session 保留作审计，快照格式与恢复路径不变。

## 测试

```bash
.venv/bin/python -m pytest tests/ -q     # 或 make test
```

23 项，全离线（MockLlm 驱动真实 Runner）：组装、工具往返、审批放行/拒绝、子代理委派（隔离 spawn 与 transfer 两条）、memory 落盘读写与 state 桥、上下文压缩触发与轮换、快照格式，以及从原版沿用的 cron/脱敏/goals 等单测。

## 家目录（运行时数据，归用户所有，与原版格式兼容）

```
~/.muse-agent-adk/
  IDENTITY.md  SOUL.md  USER.md  AGENTS.md   站立文件
  MEMORY.md                                  精选长期记忆
  memory/                                    每日笔记
  skills/                                    用户 skills
  sessions/                                  恢复快照（原 JSON 格式）
  goals.json                                 目标与跟踪项
  config.toml                                可选配置（秘密永不写这里）
```

## 诚实边界

这是学习性复刻：借鉴的是 Muse 公开可归纳的设计思想，本项目只采用设计思想并标注取舍。ADK 侧的占位与降级如实写在 [docs/architecture.md](docs/architecture.md)：连接器只有参考实现、SessionService 用进程内版、调度只判定不托管（与原版一致）、子代理快照是文本渲染版。
