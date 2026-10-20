# 压缩与恢复 context

> 对应 Muse 设计站章节：ch04 上下文工程 / ch02 运维设计

## 职责
两个保命机制：上下文超预算时把中段旧消息换成一条带标记的摘要；每一步后把完整上下文快照落盘，进程死了也能在新进程恢复。

## 对外接口
- `Compressor.compress_if_needed(ctx) -> bool`
- `Summarizer 协议（默认 ExtractiveSummarizer：抽取式、离线、确定性）`
- `save_snapshot(home, session_id, ctx) / load_snapshot(...)`

## 与谁交互、传什么
runtime/agent 在每步调用压缩、每步后存快照；subagents 在派生时深拷贝快照。

## 数据与状态
快照是 JSON：session_id + 全部消息。摘要消息带 metadata.compressed=True 与 removed_count。

## 边界与代价
抽取式摘要必然丢信息：它保住的是「聊过什么」，不是细节。耐久事实应写进 memory，而不是指望压缩无损。LLM 摘要器可替换 Summarizer 接口接入。

## ADK 落地方式

压缩算法（Compressor/Summarizer）原样保留，执行方式因 ADK 而变：ADK session 的 events 只追加、不可改写，所以 bridge 在 **run 之间**做「镜像 → 压缩 → 轮换」：新建一个 ADK session，state 带上 `context_summary` 与移除计数，events 只播种 [摘要事件 + 最近消息]，runtime 后续在新 session 上跑。旧 session 保留在 SessionService 中作审计。恢复快照仍是原 JSON 格式、按逻辑 session id 落盘，轮换不影响恢复。
