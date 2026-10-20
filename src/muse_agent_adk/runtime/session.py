"""Session assembly — the one place all subsystems are wired together.

Order mirrors the original muse-agent (and a real Muse-style turn,
see design ch19):
  1. ensure the home layout exists
  2. load identity/profile + curated memory
  3. discover skills, register tools (builtins, skill/memory tools,
     connector tools) & connectors
  4. build the system prompt from those indexes
  5. build the ADK model and create the ADK session, seeding its
     state with the memory index (the memory <-> state bridge)
Nothing else in the codebase constructs an Agent; new front-ends
(CLI, chat, API) all start here.

The Session keeps the original assembly result (bus, tool registry,
skill registry, memory, connectors, goals, system prompt) and adds
the ADK runtime handles: the model object, the SessionService and
the ADK session id (which rotates when context compression runs —
the logical ``id`` stays stable across rotations).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from google.adk.sessions import InMemorySessionService

from muse_agent_adk.config import Config
from muse_agent_adk.connectors import (ConnectorRegistry, EchoConnector,
                                          connector_tools)
from muse_agent_adk.context import ContextManager
from muse_agent_adk.core.events import EventBus
from muse_agent_adk.goals import GoalTracker
from muse_agent_adk.home import ensure_home
from muse_agent_adk.identity import load_profile
from muse_agent_adk.llm import build_model
from muse_agent_adk.memory import MemoryStore
from muse_agent_adk.prompts import PromptBuilder, PromptContext
from muse_agent_adk.skills import SkillRegistry
from muse_agent_adk.tools import ToolRegistry, builtin_tools
from muse_agent_adk.tools import memory_tools, skill_tools
from muse_agent_adk.approval import Approver

APP_NAME = "muse-agent-adk"
DEFAULT_USER_ID = "user"


@dataclass
class Session:
    config: Config
    bus: EventBus
    context: ContextManager
    tools: ToolRegistry
    skills: SkillRegistry
    memory: MemoryStore
    connectors: ConnectorRegistry
    goals: GoalTracker
    system_prompt: str
    model: Any                       # google.adk BaseLlm
    session_service: InMemorySessionService
    adk_session_id: str
    app_name: str = APP_NAME
    user_id: str = DEFAULT_USER_ID
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    extra_skill_dirs: list[Path] = field(default_factory=list)


def initial_state(profile_text: str, memory: MemoryStore) -> dict[str, Any]:
    """What the ADK session state starts with: the memory bridge.

    The curated memory index is mirrored into state so agent logic
    and callbacks can read it without file I/O; the runtime refreshes
    it via state_delta on every run (see runtime/agent.py), and the
    remember tool writes through to the files, which stay canonical.
    """
    return {
        "memory_index": memory.index_text(),
        "profile_loaded": bool(profile_text.strip()),
    }


def build_session(config: Config | None = None,
                  approver: Approver | None = None,
                  extra_skill_dirs: list[Path] | None = None) -> Session:
    cfg = config or Config.load()
    ensure_home(cfg.home)
    bus = EventBus()
    profile = load_profile(cfg.home)
    memory = MemoryStore(cfg.home)
    skills = SkillRegistry().discover(
        cfg.home / "skills", *(extra_skill_dirs or []))
    connectors = ConnectorRegistry()
    connectors.register(EchoConnector())
    tools = ToolRegistry()
    for tool in builtin_tools():
        tools.register(tool)
    for tool in skill_tools(skills):
        tools.register(tool)
    for tool in memory_tools(memory):
        tools.register(tool)
    for tool in connector_tools(connectors):
        tools.register(tool)
    prompt_ctx = PromptContext(
        profile_text=profile.render(),
        memory_text=memory.index_text(),
        skill_lines=skills.index_lines(),
        tool_lines=[f"{s.name} — {s.description} (risk: {s.risk})"
                    for s in tools.specs()],
    )
    system_prompt = PromptBuilder().build(prompt_ctx)
    context = ContextManager(budget_tokens=cfg.context_budget_tokens,
                             keep_recent=cfg.keep_recent_messages)
    context.set_system(system_prompt)
    model = build_model(cfg)
    session_service = InMemorySessionService()
    adk_session = session_service.create_session_sync(
        app_name=APP_NAME, user_id=DEFAULT_USER_ID,
        state=initial_state(profile.render(), memory))
    session = Session(
        config=cfg, bus=bus, context=context, tools=tools, skills=skills,
        memory=memory, connectors=connectors,
        goals=GoalTracker(cfg.home / "goals.json"),
        system_prompt=system_prompt, model=model,
        session_service=session_service, adk_session_id=adk_session.id,
        extra_skill_dirs=list(extra_skill_dirs or []))
    # The approver is a front-end concern (terminal prompt, approval
    # card, test double). It is stored on the session for the runtime
    # to pick up — and unlike muse-agent there is NO silent fallback:
    # leaving it None means the approval gate denies write/exec.
    session._approver = approver  # type: ignore[attr-defined]
    return session
