"""The ADK seam for approval: a before_tool_callback.

ADK calls ``before_tool_callback(tool, args, tool_context)`` before
executing any tool. Returning ``None`` lets execution proceed;
returning a dict skips execution and uses that dict as the tool's
result. The gate maps the ADK tool back to the registry's risk level,
asks ApprovalPolicy, publishes the decision on the core event bus
(same ``tool.requested`` event the original runtime emitted), and on
DENY returns an explanatory result dict — the agent loop continues
with that as data instead of the action running, exactly like the
original loop's behaviour.

Framework-internal tools (e.g. transfer_to_agent) have no registry
entry; they are not user-facing actions and pass ungated.
"""
from __future__ import annotations

from typing import Any

from muse_agent_adk.approval.policy import ApprovalPolicy, Decision
from muse_agent_adk.core.events import EventBus
from muse_agent_adk.core.types import ToolCall
from muse_agent_adk.tools.registry import ToolRegistry


class ApprovalGate:
    def __init__(self, policy: ApprovalPolicy, registry: ToolRegistry,
                 bus: EventBus) -> None:
        self.policy = policy
        self.registry = registry
        self.bus = bus

    def before_tool(self, tool: Any, args: dict[str, Any],
                    tool_context: Any) -> dict[str, Any] | None:
        entry = self.registry.find(tool.name)
        if entry is None:
            return None
        call = ToolCall(name=tool.name, arguments=dict(args or {}))
        decision = self.policy.check(call, entry.spec.risk)
        self.bus.emit("tool.requested", name=tool.name,
                      decision=decision.value, risk=entry.spec.risk)
        if decision is Decision.DENY:
            return {
                "error": (f"approval denied for tool {tool.name}; "
                          "the action was not run"),
                "approved": False,
            }
        return None
