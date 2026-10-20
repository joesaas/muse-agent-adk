# 运行时 runtime

> 对应 Muse 设计站章节：ch05 Agent 循环 / ch19 一次真实交互的全程解剖 / ch02 运维设计

## 职责
两件事：session 组装（唯一装配点：按固定顺序加载身份、记忆、skills、tools、连接器，拼系统提示词，建上下文）与 agent 循环（内圈：压缩检查→问模型→审批→执行工具→结果回注→再问，直到最终文本或步数上限；外圈：事件唤醒、打断优先）。每步发事件、存快照。

## 对外接口
- `build_session(config, approver, extra_skill_dirs) -> Session`
- `Agent(session, provider).run_turn(text) -> str / interrupt()`

## 与谁交互、传什么
所有前端（CLI、未来的聊天/API）都经 build_session；循环内部调用 llm、context、tools、approval、subagents。

## 数据与状态
Session 是装配结果对象；run_turn 的输入输出都是纯文本 + 上下文副作用，事件流是可观测面。

## 边界与代价
步数上限是硬保险：达到上限返回未完成说明并保存进度，而不是无限循环。打断是协作式的（每步检查标记），不强杀工具。

## ADK 落地方式

这是 ADK 换血最彻底的模块。原版 `Agent.run_turn` 的手写内圈（问模型→审批→执行→回注）删除，改由 ADK `Runner` + `LlmAgent` 树托管；runtime/agent 保留的是外圈职责：run 前调 context bridge 做预算检查与压缩轮换、以 state_delta 刷新 memory 索引、run 中把 ADK 事件适配回 core 总线、run 后存恢复快照。对外仍是同步 `run_turn(text) -> str`：Agent 持有一个自有事件循环，所有 ADK 调用都在其上执行，避免 session 服务跨 loop。打断走 Runner 的 abort_signal + 协作检查。原版的 max_steps 硬保险由 ADK 框架的调用上限接管，config 字段保留作口径对齐（已在 architecture 的差异表标注）。
