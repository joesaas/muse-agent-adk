# 安全与凭证 security

> 对应 Muse 设计站章节：ch12 安全设计 / ch13 数据与隐私

## 职责
三条落到代码的规矩：凭证只按名字在调用时从环境取、永不落盘进记忆/日志/快照；输出有 redact() 兜底脱敏；托管运行时可用 surrogate（替身凭证）模式——agent 进程只拿替身、出口代理换真值，接口不变。

## 对外接口
- `CredentialStore(mode='env'|'surrogate').get(name) / has(name)`
- `redact(text) -> str`

## 与谁交互、传什么
llm adapter 与 connectors 按名取凭证；CLI 输出与日志可过 redact。

## 数据与状态
只流通凭证的「名字」，值只在真正发请求的一瞬间存在于局部变量。

## 边界与代价
redact 是第二道防线不是边界本身：真正的边界是「不存储」。surrogate 模式在本仓库是集成缝，需要宿主提供 broker 客户端后实现 get()。

## ADK 落地方式

本模块无 ADK 接点，规矩一条不变：凭证按名在调用时取（llm 工厂构建 LiteLlm/Gemini 时经 CredentialStore 按环境变量名取，值不进 config/日志/快照）、输出 redact 兜底、surrogate 仍是集成缝。ADK 侧注意一点：session state 会被框架持久化，所以 state 里只放 memory 索引这类可公开数据，永不放凭证值——本项目已遵守。
