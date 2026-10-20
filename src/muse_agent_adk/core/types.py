"""Shared data contracts.

These dataclasses are the *only* shapes that cross module boundaries.
Providers, tools, context and runtime all speak in these types, so any
module can be reimplemented behind the same contract.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class Message:
    role: Role
    content: str
    name: str | None = None            # tool name, when role == TOOL
    tool_call_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"role": self.role.value, "content": self.content,
                "name": self.name, "tool_call_id": self.tool_call_id,
                "metadata": self.metadata}

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Message":
        return Message(role=Role(d["role"]), content=d["content"],
                       name=d.get("name"), tool_call_id=d.get("tool_call_id"),
                       metadata=d.get("metadata") or {})


@dataclass
class ToolCall:
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])


@dataclass
class ToolResult:
    call_id: str
    name: str
    output: str
    ok: bool = True


@dataclass
class ToolSpec:
    """What the LLM is told about a tool, and what policy needs to know."""
    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)  # JSON-schema-ish
    risk: str = "read"   # read | write | exec — consumed by approval.policy


@dataclass(frozen=True)
class Event:
    """One entry on the event bus: messages, hooks, cron ticks, subagent
    returns and user interrupts all arrive as Events (see docs ch11/ch19)."""
    type: str
    payload: dict[str, Any] = field(default_factory=dict)
    ts: float = field(default_factory=time.time)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
