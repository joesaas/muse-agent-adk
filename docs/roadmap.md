# Roadmap

原则：不追求速度。每一阶段都先稳接口与数据，再加能力。

## 阶段 0（本仓库，已完成）
- 模块骨架与全部接口契约（沿用 muse-agent），执行层换 Google ADK：LlmAgent 树 + Runner + BaseLlm + FunctionTool
- MockLlm 离线跑通：对话、工具往返、审批放行/拒绝、压缩轮换、子代理（transfer + 隔离 spawn）
- pytest 全离线测试（23 项）

## 阶段 1：真实模型体验
- OpenAI 兼容 adapter 加流式与 usage 统计
- LLM 摘要器替换抽取式默认（实现 Summarizer 接口）
- 会话恢复命令（resume 指定 session 快照继续）

## 阶段 2：能力扩展
- 工具：文件写入（write 风险）、受控命令执行（exec 风险 + 审批）
- 连接器：邮箱、日历各一个真实实现，按 connectors 契约
- Skills：语义触发（替换关键词 match 的实现，格式不变）

## 阶段 3：长期运行
- 调度托管进程：tick 循环、cron 任务持久化、hook 轮询托管
- 子代理线程/进程执行器（接口不变），并发上限与取消
- 多端前端：聊天端一个（事件进、渲染出，审批走卡片回调）

## 阶段 4：产品层（不进核心）
- Feed / Ideas 类内容产品：以 skill + cron + goals 组合实现，验证「能力是数据」这条原则
