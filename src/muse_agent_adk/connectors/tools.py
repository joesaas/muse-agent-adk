"""Connector capabilities, exposed to the agent as tools.

Each registered connector becomes one registry Tool named
``connector_<name>``: the model passes an ``action`` plus an optional
free-form ``text`` argument, and the handler routes to
``connector.call(action, ...)``. This keeps the connector contract
(status/call, credentials by name) intact while giving the agent a
uniform tool surface. Real connectors should declare per-action risk
when they grow write actions; the reference EchoConnector is
read-only, so its tool is risk=read.
"""
from __future__ import annotations

from muse_agent_adk.connectors.registry import ConnectorRegistry
from muse_agent_adk.core.types import ToolSpec
from muse_agent_adk.tools.base import Tool


def connector_tools(registry: ConnectorRegistry) -> list[Tool]:
    tools: list[Tool] = []
    for status in registry.statuses():
        connector = registry.get(status.name)

        def make_handler(conn):
            def handler(args: dict) -> str:
                action = str(args.get("action", "")).strip()
                if not action:
                    return "connector call needs an 'action' argument"
                kwargs = {k: v for k, v in args.items()
                          if k != "action" and v is not None}
                return str(conn.call(action, **kwargs))
            return handler

        tools.append(Tool(
            ToolSpec(
                f"connector_{connector.name}",
                f"Call the {connector.name} connector "
                f"({status.detail}). Pass an action name and any "
                "arguments the action needs (e.g. text).",
                {"type": "object",
                 "properties": {
                     "action": {"type": "string"},
                     "text": {"type": "string"}},
                 "required": ["action"]}, risk="read"),
            make_handler(connector)))
    return tools
