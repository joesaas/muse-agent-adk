"""Bridge: apply the original context logic to ADK sessions.

ADK owns the live conversation as an append-only list of Events on a
Session; the original ContextManager/Compressor logic works on
core.Message lists. This bridge converts between the two and runs the
budget/compression cycle *between runs*:

  1. read the ADK session's events, convert to core Messages;
  2. run the unchanged Compressor against the configured budget
     (system prompt pinned, recent messages kept);
  3. if compression ran, rotate: create a fresh ADK session whose
     state carries the summary (``context_summary``) and whose event
     list is [summary event] + [kept recent events]. The old session
     is left in the service untouched, as an audit trail.

The rotation is what makes compression real in ADK terms: subsequent
Runner invocations on the new session only see the summary plus the
recent tail, not the full history. Recovery snapshots keep the
original JSON format (recovery.py) and are written by the runtime
from the same message mirror, keyed by the logical session id, so
they survive rotations.
"""
from __future__ import annotations

from typing import Any

from google.adk.events.event import Event
from google.genai import types

from muse_agent_adk.context.compression import Compressor
from muse_agent_adk.context.manager import ContextManager
from muse_agent_adk.core.types import Message, Role


class AdkContextBridge:
    def __init__(self, budget_tokens: int = 32_000,
                 keep_recent: int = 12,
                 compressor: Compressor | None = None) -> None:
        self.budget_tokens = budget_tokens
        self.keep_recent = keep_recent
        self.compressor = compressor or Compressor()

    # -- conversions ---------------------------------------------------
    def events_to_messages(self, events: list[Event]) -> list[Message]:
        """ADK events -> core messages (system prompt not included:
        in ADK it is the agent instruction, not an event)."""
        messages: list[Message] = []
        for event in events:
            if not event.content or not event.content.parts:
                continue
            for part in event.content.parts:
                if part.function_call is not None:
                    messages.append(Message(
                        role=Role.ASSISTANT, content="",
                        metadata={"tool_call_ids":
                                  [part.function_call.id or ""],
                                  "tool_name": part.function_call.name}))
                elif part.function_response is not None:
                    fr = part.function_response
                    messages.append(Message(
                        role=Role.TOOL,
                        content=_response_text(fr.response),
                        name=fr.name, tool_call_id=fr.id))
                elif part.text:
                    role = (Role.USER if event.author == "user"
                            else Role.ASSISTANT)
                    messages.append(Message(role=role, content=part.text))
        return messages

    def messages_to_events(self, messages: list[Message],
                           agent_name: str) -> list[Event]:
        """Core messages -> ADK events for seeding a rotated session.

        The pinned system prompt (index 0) is skipped — it lives in
        the agent instruction. Empty assistant placeholders left by
        tool calls are dropped; the tool exchanges themselves survive
        as function_response events.
        """
        events: list[Event] = []
        for i, message in enumerate(messages):
            if i == 0 and message.role is Role.SYSTEM:
                continue
            if message.role is Role.USER:
                events.append(Event(
                    author="user",
                    content=types.Content(
                        role="user",
                        parts=[types.Part(text=message.content)])))
            elif message.role is Role.TOOL:
                events.append(Event(
                    author=agent_name,
                    content=types.Content(
                        role="user",
                        parts=[types.Part.from_function_response(
                            name=message.name or "tool",
                            response={"result": message.content})])))
            elif message.content:
                events.append(Event(
                    author=agent_name,
                    content=types.Content(
                        role="model",
                        parts=[types.Part(text=message.content)])))
        return events

    def mirror(self, events: list[Event],
               system_prompt: str) -> ContextManager:
        """A ContextManager holding the system prompt + the mirrored
        conversation — the shape recovery snapshots are saved in."""
        ctx = ContextManager(budget_tokens=self.budget_tokens,
                             keep_recent=self.keep_recent)
        ctx.set_system(system_prompt)
        ctx.messages.extend(self.events_to_messages(events))
        return ctx

    # -- the between-runs cycle ------------------------------------------
    async def maintain(self, session_service: Any, *, app_name: str,
                       user_id: str, session_id: str, agent_name: str,
                       system_prompt: str) -> str | None:
        """Compress if over budget. Returns the new ADK session id
        when a rotation happened, else None."""
        session = await session_service.get_session(
            app_name=app_name, user_id=user_id, session_id=session_id)
        if session is None:
            return None
        ctx = self.mirror(session.events, system_prompt)
        if not self.compressor.compress_if_needed(ctx):
            return None
        summary_message = next(
            (m for m in ctx.messages if m.metadata.get("compressed")),
            None)
        state = dict(session.state or {})
        if summary_message is not None:
            state["context_summary"] = summary_message.content
            state["context_compressed_removed"] = summary_message.metadata.get(
                "removed_count", 0)
        new_session = await session_service.create_session(
            app_name=app_name, user_id=user_id, state=state)
        for event in self.messages_to_events(ctx.messages, agent_name):
            await session_service.append_event(new_session, event)
        return new_session.id


def _response_text(response: object) -> str:
    if isinstance(response, dict):
        if set(response) == {"result"}:
            return str(response["result"])
        return str(response)
    return str(response)
