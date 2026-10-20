"""Subagent spawning on ADK.

Original semantics, kept: a subagent is a complete agent instance
born for one self-contained task; at spawn it receives a **full
snapshot copy** of the parent context plus a task brief; it works
independently and hands back only its final result; the parent
context is never mutated by the child; depth is capped (default 2).

ADK offers two delegation shapes; this project wires both:

  1. Agent tree (runtime/agent.build_root_agent): the worker sits in
     the root's ``sub_agents`` — a model may *transfer* to it, and
     ADK hands it the full conversation (framework-managed snapshot).
  2. This manager (programmatic spawn, used by the CLI and tests):
     the worker runs under its own Runner on its **own ADK session**,
     seeded with a brief that embeds the rendered parent snapshot.
     True isolation: child events land on the child session only.
     ``as_agent_tool()`` exposes the same worker wrapped as an
     AgentTool, for front-ends that prefer tool-style delegation.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from google.adk.runners import Runner
from google.adk.tools.agent_tool import AgentTool
from google.genai import types

from muse_agent_adk.context import AdkContextBridge
from muse_agent_adk.runtime.agent import build_worker_agent
from muse_agent_adk.runtime.session import Session

_SNAPSHOT_CHAR_CAP = 24_000


@dataclass
class SubagentResult:
    task: str
    output: str
    session_id: str
    ok: bool = True


def render_snapshot(messages) -> str:
    """Render core messages as the read-only snapshot text a child
    brief carries (the textual equivalent of the original deep copy)."""
    lines = []
    for m in messages:
        label = m.name or m.role.value
        if m.content:
            lines.append(f"[{label}] {m.content}")
    text = "\n".join(lines) if lines else "(无历史)"
    if len(text) > _SNAPSHOT_CHAR_CAP:
        text = "(快照过长，仅保留最近部分)\n" + text[-_SNAPSHOT_CHAR_CAP:]
    return text


@dataclass
class SubagentManager:
    parent: Session
    depth: int = 0
    max_depth: int = 2
    results: list[SubagentResult] = field(default_factory=list)

    def as_agent_tool(self) -> AgentTool:
        """The worker as an AgentTool — the optional tool-style
        delegation surface (same worker, same gate)."""
        return AgentTool(build_worker_agent(self.parent))

    def spawn(self, task: str) -> SubagentResult:
        if self.depth >= self.max_depth:
            return SubagentResult(task=task, ok=False,
                                  output="(超过最大子代理深度，未执行)",
                                  session_id="")
        loop = getattr(self.parent, "_loop", None)
        coro = self._spawn(task)
        result = (loop.run_until_complete(coro) if loop is not None
                  else asyncio.run(coro))
        self.results.append(result)
        return result

    async def _spawn(self, task: str) -> SubagentResult:
        parent = self.parent
        service = parent.session_service
        parent_adk = await service.get_session(
            app_name=parent.app_name, user_id=parent.user_id,
            session_id=parent.adk_session_id)
        bridge = AdkContextBridge(
            budget_tokens=parent.config.context_budget_tokens,
            keep_recent=parent.config.keep_recent_messages)
        snapshot = render_snapshot(
            bridge.events_to_messages(parent_adk.events)
            if parent_adk else [])
        brief = (
            "你是一个子代理。以下是父会话的上下文快照（只读参考）：\n"
            f"{snapshot}\n\n你的任务是：{task}\n"
            "只做这件事，做完给出简洁、完整的结果交回主代理。")
        child = await service.create_session(
            app_name=parent.app_name, user_id="subagent",
            state={"parent_session": parent.id, "brief_task": task})
        parent.bus.emit("subagent.spawned", task=task,
                        child_session=child.id)
        runner = Runner(agent=build_worker_agent(parent),
                        app_name=parent.app_name,
                        session_service=service)
        final = ""
        message = types.Content(role="user",
                                parts=[types.Part(text=brief)])
        async for event in runner.run_async(
                user_id="subagent", session_id=child.id,
                new_message=message):
            if event.is_final_response() and event.content:
                text = "".join(p.text or "" for p in event.content.parts
                               if p.text)
                if text:
                    final = text
        parent.bus.emit("subagent.finished", task=task,
                        child_session=child.id)
        return SubagentResult(task=task, output=final,
                              session_id=child.id)
