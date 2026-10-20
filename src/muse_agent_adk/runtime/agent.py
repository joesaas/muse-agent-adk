"""The agent runtime on ADK (see design ch05/ch19).

muse-agent hand-rolled its loop (ask model -> gate -> run tool ->
re-inject). Here that inner loop is ADK's: ``build_root_agent()``
assembles an ``LlmAgent`` tree (root + worker subagent) and a
``Runner`` drives it against a SessionService. What this module adds
around ADK is the original runtime's outer behaviour:

  - before each run: the context bridge checks the token budget
    against the ADK session's events and compresses (rotating the
    ADK session) when over budget; the memory index is refreshed
    into session state via state_delta;
  - during the run: ADK events are adapted onto the core event bus
    (turn.started / tool.called / tool.finished / turn.finished),
    keeping the run observable in the original vocabulary;
  - after each run: a recovery snapshot in the original JSON format
    is saved under the logical session id;
  - interruption is cooperative: interrupt() sets the run's abort
    signal, checked between events.

The public surface stays synchronous (``run_turn(text) -> str``) like
the original: the Agent owns one event loop and runs every ADK call
on it, so session-service state never crosses loops.
"""
from __future__ import annotations

import asyncio
import threading

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.genai import types

from muse_agent_adk.approval import ApprovalGate, ApprovalPolicy
from muse_agent_adk.context import AdkContextBridge, save_snapshot
from muse_agent_adk.runtime.session import Session
from muse_agent_adk.tools import to_function_tools

ROOT_AGENT_NAME = "muse_agent"
WORKER_AGENT_NAME = "worker"

SUBAGENT_NOTE = (
    "\n\n## Subagent mode\n"
    "You are a subagent spawned by the main agent. The conversation "
    "you see is a snapshot of the parent context plus your task "
    "brief. Do only the briefed task, then return a concise, complete "
    "result for the main agent. Do not spawn further subagents.")


def _gate_for(session: Session) -> ApprovalGate:
    policy = ApprovalPolicy(
        approver=getattr(session, "_approver", None),
        auto_approve_write=session.config.auto_approve_write)
    return ApprovalGate(policy, session.tools, session.bus)


def build_worker_agent(session: Session) -> LlmAgent:
    """The leaf worker: same model and tools as the root, brief-style
    instruction, no subagents of its own (depth control)."""
    return LlmAgent(
        name=WORKER_AGENT_NAME,
        description=(
            "General-purpose subagent: executes one self-contained "
            "task from a brief and returns a concise result."),
        model=session.model,
        instruction=session.system_prompt + SUBAGENT_NOTE,
        tools=to_function_tools(session.tools),
        before_tool_callback=_gate_for(session).before_tool)


def build_root_agent(session: Session) -> LlmAgent:
    """Assemble the LlmAgent tree for a session.

    Delegation exists in two ADK forms, both real:
      - the worker sits in ``sub_agents``: a model can transfer to it
        (transfer_to_agent) and it works with the full conversation —
        the framework's equivalent of the original full-snapshot copy;
      - subagents.manager additionally wraps the worker in an
        AgentTool-style isolated run with an explicit brief for
        programmatic spawning (CLI/tests).
    """
    worker = build_worker_agent(session)
    return LlmAgent(
        name=ROOT_AGENT_NAME,
        description="Muse Agent (ADK edition): a personal super agent.",
        model=session.model,
        instruction=session.system_prompt,
        tools=to_function_tools(session.tools),
        sub_agents=[worker],
        before_tool_callback=_gate_for(session).before_tool)


class Agent:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.root_agent = build_root_agent(session)
        self.runner = Runner(
            agent=self.root_agent, app_name=session.app_name,
            session_service=session.session_service)
        self.bridge = AdkContextBridge(
            budget_tokens=session.config.context_budget_tokens,
            keep_recent=session.config.keep_recent_messages)
        self._loop = asyncio.new_event_loop()
        self._abort: asyncio.Event | None = None
        self._interrupt = threading.Event()
        # Let collaborators (subagents.manager) run on the same loop.
        session._loop = self._loop  # type: ignore[attr-defined]

    # -- public, synchronous surface (original parity) -------------------
    def interrupt(self) -> None:
        """User interrupt wins over any in-flight step."""
        self._interrupt.set()
        if self._abort is not None and not self._abort.is_set():
            self._loop.call_soon_threadsafe(self._abort.set)

    def run_turn(self, user_text: str) -> str:
        return self._loop.run_until_complete(self._run_turn(user_text))

    def close(self) -> None:
        self._loop.close()

    # -- internals ---------------------------------------------------------
    async def _run_turn(self, user_text: str) -> str:
        session = self.session
        bus = session.bus
        self._interrupt.clear()
        self._abort = asyncio.Event()
        bus.emit("turn.started", session_id=session.id, text=user_text)

        rotated = await self.bridge.maintain(
            session.session_service, app_name=session.app_name,
            user_id=session.user_id, session_id=session.adk_session_id,
            agent_name=ROOT_AGENT_NAME,
            system_prompt=session.system_prompt)
        if rotated:
            session.adk_session_id = rotated
            bus.emit("context.compressed", session_id=session.id)

        final = ""
        message = types.Content(
            role="user", parts=[types.Part(text=user_text)])
        async for event in self.runner.run_async(
                user_id=session.user_id, session_id=session.adk_session_id,
                new_message=message,
                state_delta={"memory_index":
                             session.memory.index_text()},
                abort_signal=self._abort):
            self._adapt(event)
            if event.is_final_response():
                final = _event_text(event) or final
            if self._interrupt.is_set():
                final = "(已打断)"
                bus.emit("turn.interrupted", session_id=session.id)
                break
        await self._save_snapshot()
        bus.emit("turn.finished", session_id=session.id)
        return final

    def _adapt(self, event) -> None:
        """Translate one ADK event into core bus events."""
        if not event.content or not event.content.parts:
            return
        for part in event.content.parts:
            if part.function_call is not None:
                self.session.bus.emit(
                    "tool.called", name=part.function_call.name,
                    author=event.author)
            elif part.function_response is not None:
                self.session.bus.emit(
                    "tool.finished", name=part.function_response.name,
                    ok="error" not in (part.function_response.response
                                       or {}))

    async def _save_snapshot(self) -> None:
        session = self.session
        adk_session = await session.session_service.get_session(
            app_name=session.app_name, user_id=session.user_id,
            session_id=session.adk_session_id)
        if adk_session is None:
            return
        ctx = self.bridge.mirror(adk_session.events,
                                 session.system_prompt)
        save_snapshot(session.config.home, session.id, ctx)


def _event_text(event) -> str:
    if not event.content or not event.content.parts:
        return ""
    return "".join(p.text or "" for p in event.content.parts if p.text)
