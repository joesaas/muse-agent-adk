"""The registry is the single place tools are added or replaced.
Names are unique; the runtime never calls a handler directly."""
from __future__ import annotations

from muse_agent_adk.core.errors import ToolError
from muse_agent_adk.core.types import ToolCall, ToolResult, ToolSpec
from muse_agent_adk.tools.base import Tool


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ToolError(f"duplicate tool name: {tool.name}")
        self._tools[tool.name] = tool

    def find(self, name: str) -> Tool | None:
        """Soft lookup for gates/introspection: None instead of raising."""
        return self._tools.get(name)

    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError:
            raise ToolError(f"unknown tool: {name}") from None

    def specs(self) -> list[ToolSpec]:
        return [t.spec for t in self._tools.values()]

    def names(self) -> list[str]:
        return sorted(self._tools)

    def execute(self, call: ToolCall) -> ToolResult:
        tool = self.get(call.name)
        try:
            output = tool.handler(call.arguments or {})
        except Exception as exc:  # tool failures are data for the loop
            return ToolResult(call_id=call.id, name=call.name,
                              output=f"tool error: {exc}", ok=False)
        return ToolResult(call_id=call.id, name=call.name,
                          output=str(output), ok=True)
