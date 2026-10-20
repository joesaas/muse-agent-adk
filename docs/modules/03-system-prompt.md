# 系统提示词 prompts

> 对应 Muse 设计站章节：ch04 上下文工程

## 职责
把系统提示词做成「分段注册表」而不是一整段字符串：每段一个 id、一个职责、一个顺序，可单独查看、禁用和测试。

## 对外接口
- `Section(id, title, order, render)`
- `PromptBuilder.build(PromptContext) -> str`
- `PromptContext：profile_text / memory_text / skill_lines / tool_lines`
- CLI：muse-agent prompt 打印拼装结果

## 与谁交互、传什么
runtime/session 在组装时调用；内容来源是 identity（站立文件）、memory（索引）、skills（索引行）、tools（规格行）。

## 数据与状态
输出是 ContextManager 中被钉住的 system 消息。分段函数只渲染、不做 I/O——所有加载在 session 组装期完成。

## 边界与代价
分段不是越多越好：一段一个职责。未证实的 Muse 内部提示词细节不写进来，本项目只借鉴其分层与注入方式。

## ADK 落地方式

分段注册表原样保留，拼装结果的去向变了：它成为 ADK `LlmAgent.instruction`（根代理与 worker 共用同一份拼装，worker 另加 Subagent mode 段）。工具行来自注册表 specs——与 FunctionTool 的声明同源，不会漂移。CLI `prompt` 子命令仍可打印全文做检查。
