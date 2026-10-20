"""The ADK seam for tools: registry entries -> ADK FunctionTool.

The registry (Tool + ToolSpec + handler) stays the single source of
truth — names, descriptions, parameter schemas and risk levels all
come from the ToolSpec, so approval, the prompt's tool index and the
ADK tool table can never drift apart. Each registry entry becomes one
FunctionTool whose signature is synthesised from the spec's JSON
schema (required parameters first), and whose body routes the call
back through ``ToolRegistry.execute`` — so tool errors are returned
as data (``tool error: ...``), never raised into the agent loop.

This module also defines the tools that bind other subsystems into
the registry: load_skill (skills/), memory_search + remember
(memory/). They are ordinary registry entries with honest risk
levels — remember is a write, so the approval gate applies to it.
"""
from __future__ import annotations

import inspect
from typing import Any

from google.adk.tools.function_tool import FunctionTool

from muse_agent_adk.core.types import ToolCall, ToolSpec
from muse_agent_adk.memory.store import MemoryStore
from muse_agent_adk.skills.registry import SkillRegistry
from muse_agent_adk.tools.base import Tool
from muse_agent_adk.tools.registry import ToolRegistry

_ANNOTATIONS = {"string": str, "integer": int, "number": float,
                "boolean": bool}


def _build_wrapper(tool: Tool, registry: ToolRegistry):
    props: dict[str, Any] = (tool.spec.parameters or {}).get(
        "properties", {})
    required = list((tool.spec.parameters or {}).get("required", []))
    ordered = ([n for n in required if n in props]
               + [n for n in props if n not in required])
    params = []
    for name in ordered:
        schema = props.get(name, {})
        annotation = _ANNOTATIONS.get(schema.get("type"), str)
        if name in required:
            params.append(inspect.Parameter(
                name, inspect.Parameter.POSITIONAL_OR_KEYWORD,
                annotation=annotation))
        else:
            params.append(inspect.Parameter(
                name, inspect.Parameter.POSITIONAL_OR_KEYWORD,
                annotation=annotation, default=None))

    def wrapper(**kwargs: Any) -> str:
        args = {k: v for k, v in kwargs.items() if v is not None}
        result = registry.execute(ToolCall(name=tool.name, arguments=args))
        return result.output

    wrapper.__name__ = tool.name
    wrapper.__qualname__ = tool.name
    wrapper.__doc__ = tool.spec.description
    wrapper.__signature__ = inspect.Signature(params)
    wrapper.__annotations__ = {
        name: _ANNOTATIONS.get((props.get(name) or {}).get("type"), str)
        for name in ordered}
    return wrapper


def to_function_tools(registry: ToolRegistry) -> list[FunctionTool]:
    """One FunctionTool per registry entry, in registry order."""
    tools = []
    for spec in registry.specs():
        tool = registry.get(spec.name)
        tools.append(FunctionTool(_build_wrapper(tool, registry)))
    return tools


def skill_tools(skills: SkillRegistry) -> list[Tool]:
    """Progressive disclosure: the prompt carries only the skill
    index; the body is loaded on demand through this tool."""

    def load_skill(args: dict) -> str:
        name = str(args.get("name", "")).strip()
        skill = skills.get(name)
        if skill is None:
            available = ", ".join(s.name for s in skills.all()) or "(none)"
            return f"unknown skill: {name!r}. Available: {available}"
        return f"# Skill: {skill.name}\n\n{skill.body}"

    return [Tool(
        ToolSpec("load_skill",
                 "Load the full body of a skill by name. The system "
                 "prompt lists available skills; call this before "
                 "following one.",
                 {"type": "object",
                  "properties": {"name": {"type": "string"}},
                  "required": ["name"]}, risk="read"),
        load_skill)]


def memory_tools(memory: MemoryStore) -> list[Tool]:
    """The memory bridge as tools: reads search the files, writes go
    to today's daily note (and are approval-gated as writes)."""

    def memory_search(args: dict) -> str:
        hits = memory.search(str(args.get("query", "")))
        if not hits:
            return "(no memory hits)"
        return "\n".join(f"{h.source}:{h.line}  {h.text}" for h in hits)

    def remember(args: dict) -> str:
        text = str(args.get("text", "")).strip()
        if not text:
            return "nothing to remember (empty text)"
        path = memory.append_daily(text)
        return f"remembered in memory/{path.name}: {text}"

    return [
        Tool(ToolSpec("memory_search",
                      "Search the user's file memory (MEMORY.md and "
                      "daily notes) by keywords.",
                      {"type": "object",
                       "properties": {"query": {"type": "string"}},
                       "required": ["query"]}, risk="read"),
             memory_search),
        Tool(ToolSpec("remember",
                      "Append a durable note to today's memory file. "
                      "This writes to disk, so it needs approval.",
                      {"type": "object",
                       "properties": {"text": {"type": "string"}},
                       "required": ["text"]}, risk="write"),
             remember),
    ]
