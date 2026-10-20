# 核心契约 core

> 对应 Muse 设计站章节：ch01 整体架构 / ch10 文件架构

## 职责
定义全系统唯一跨模块流通的数据形状（Message / ToolCall / ToolResult / ToolSpec / Event）和统一错误类型、事件总线。任何模块只能依赖 core，不能反向依赖业务模块——这是长期可维护的地基。

## 对外接口
- `Message / ToolCall / ToolResult / ToolSpec / Event 数据类`
- `EventBus.subscribe(type, handler) / publish(event) / emit(type, **payload)`
- `MuseAgentError / ToolError / ApprovalDenied / ConfigError`

## 与谁交互、传什么
所有模块都与 core 交互；EventBus 被 runtime、scheduling、subagents 共同使用。

## 数据与状态
纯数据，无状态（EventBus 的 history 除外）。事件带 id 与时间戳，便于追踪一次交互的全程（对照 ch19）。

## 边界与代价
契约一旦发布就应保持向后兼容；新增字段必须可选。事件总线是进程内实现，跨进程事件需要换传输层（接口不变）。

## ADK 落地方式

本模块**不接 ADK**，这是刻意的：core 的数据类与事件总线与原项目逐字一致，ADK 的 Event/Content 只出现在接缝模块（runtime、context.bridge、llm、approval.gate、tools.adk）并在边界处适配成 core 类型。这样换框架版本、甚至换框架，业务模块都不用动。runtime/agent 的 `_adapt()` 是唯一的 ADK 事件 → core 事件翻译点。
