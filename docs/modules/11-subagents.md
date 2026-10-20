# 子代理 subagents

> 对应 Muse 设计站章节：ch07 子代理编排

## 职责
子代理是一个完整的 Agent 实例，为一件自包含任务而生：派生时拿到父上下文的**全量快照副本**（深拷贝，不是共享引用、不是切片），做完以「事件 + 返回值」交回，父上下文不被子代理改动。深度默认上限 2。

## 对外接口
- SubagentManager(parent_session, max_depth=2).spawn(task) -> SubagentResult
- 事件：subagent.spawned / subagent.finished

## 与谁交互、传什么
runtime/agent 同构复用（子代理内部还是同一个 Agent 循环）；通过 EventBus 向父会话报告。

## 数据与状态
输入是任务简报字符串 + 快照；输出是 SubagentResult(task, output, session_id, ok)。

## 边界与代价
进程内实现是参考形态：长任务应换线程/进程/远程执行器，接口不变。子代理之间不直接通信，一切经主代理中转。

## ADK 落地方式

两条 ADK 路径并存，都真实可用：(1) **代理树**——worker 是根代理的 `sub_agents`，模型发 `transfer_to_agent` 即可委派，ADK 把完整会话交给 worker，等价于原版的全量快照语义（框架托管）；(2) **隔离 spawn**——SubagentManager 用独立 Runner + 独立 ADK session 跑 worker，简报内嵌父会话快照的文本渲染，父 session 零污染，CLI 与测试走这条。另备 `as_agent_tool()` 把 worker 包成 AgentTool 供工具式委派。深度上限与 SubagentResult 形状与原版一致。
