# 审批与认证 approval

> 对应 Muse 设计站章节：ch06 审批与认证（HITL）

## 职责
按风险分级的人机协同闸门：read 自动放行，write 默认要批，exec 必须明确批。批准者是一个回调——CLI 在终端问、聊天端弹卡片、测试注入自动同意/拒绝，策略层不关心形态。

## 对外接口
- `ApprovalPolicy.check(call, risk) -> Decision`
- `RiskLevel(read/write/exec) / Approver 回调协议`
- `auto_approver / deny_approver（测试与无人值守用）`

## 与谁交互、传什么
runtime/agent 在每次工具执行前调用；工具的 risk 来自 ToolSpec。

## 数据与状态
输入 ToolCall + 风险等级，输出 ALLOW/DENY。被拒绝时循环收到一条说明结果，不中断整轮对话。

## 边界与代价
无人值守（非 tty）默认拒绝需要审批的调用：宁可没做成，不可擅自做。auto_approve_write 是显式配置，不做隐含默认。

## ADK 落地方式

策略层（ApprovalPolicy、RiskLevel、Approver 回调）与原版同构；执行点换成 ADK 的 `before_tool_callback`：approval/gate.py 按工具名查注册表风险 → 策略裁决 → 在 core 总线发 `tool.requested` 事件；DENY 时返回结果 dict，ADK 据此跳过执行并把拒绝说明作工具结果回注（与原版循环行为一致）。**刻意修正**：原版未传 approver 时默认 auto_approver（fail-open，原版评审已指出）；本项目 approver=None 对 write/exec 一律 DENY，前端必须显式接线同意来源。
