# 工具 tools

> 对应 Muse 设计站章节：ch05 Agent 循环

## 职责
工具 = ToolSpec（模型看到的名/描述/参数/风险等级）+ handler（真正执行的函数）。注册表是唯一入口，运行时不直调 handler。内置工具刻意少而稳，且文件类工具被限制在 sandbox 根目录内。

## 对外接口
- `Tool / ToolRegistry.register / get / specs / execute(call) -> ToolResult`
- `builtin_tools(sandbox_root)：echo / now / list_dir / read_file`

## 与谁交互、传什么
runtime/agent 按 LLM 的 ToolCall 调用；approval 按 ToolSpec.risk 先行裁决；prompts 注入工具行。

## 数据与状态
调用参数是 JSON 风格 dict；结果统一为字符串输出 + ok 标记。工具异常被捕获为 ok=False 的结果交回循环，而不是崩掉会话。

## 边界与代价
新增工具的纪律：名唯一、描述写清何时用、风险如实标。写/执行类工具必须标 write/exec，让审批层有据可依。

## ADK 落地方式

注册表仍是唯一事实源（名/描述/参数 schema/风险）。ADK 接点在 tools/adk.py：每条注册项合成一个 `FunctionTool`——参数签名由 ToolSpec 的 JSON schema 生成（必填在前），函数体回调用 `ToolRegistry.execute()`，所以执行、异常兜底（错误作数据返回）与原版完全同路。审批、提示词工具行、CLI 列表读的都是同一份 spec。新增工具 load_skill、memory_search、remember、connector_<name> 也都是普通注册项。
