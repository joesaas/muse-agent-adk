# 上下文管理 context

> 对应 Muse 设计站章节：ch04 上下文工程

## 职责
拥有一轮会话的全部消息：顺序、token 预算、哪些可以被压缩。系统提示词钉在首位，永不压缩。

## 对外接口
- `ContextManager.set_system / add / add_user`
- `estimate_tokens(text)（约 4 字符/token，中文约 1.5）`
- `over_budget() / compressible_range() / total_tokens()`

## 与谁交互、传什么
runtime/agent 每步读写；compression 消费 compressible_range；recovery 序列化整个 ContextManager。

## 数据与状态
Message 列表 + 预算参数。估算故意做得粗糙：预算决策不需要精确计数，精确计数属于供应商层。

## 边界与代价
预算是软上限：单条超长消息不会被切碎，压缩只处理中间段。

## ADK 落地方式

ContextManager 本身不变，但在 ADK 里它不再是运行时状态本体，而是**镜像**：真实对话活在 ADK session 的 events 里。context/bridge.py 的 `events_to_messages()` 把 events（user/model 文本、function_call、function_response）翻成 core 消息，镜像供预算计算、压缩与快照使用。token 估算函数与预算语义与原版一致。
