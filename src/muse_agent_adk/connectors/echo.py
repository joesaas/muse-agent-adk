"""Reference connector: proves the contract with no external service.
Real connectors (mail, calendar, GitHub, ...) follow exactly this
shape: a status check, a small action set, credentials by name."""
from __future__ import annotations

from typing import Any

from muse_agent_adk.connectors.base import ConnectorStatus


class EchoConnector:
    name = "echo"

    def status(self) -> ConnectorStatus:
        return ConnectorStatus(name=self.name, connected=True,
                               detail="reference connector, always available")

    def call(self, action: str, **kwargs: Any) -> Any:
        if action == "echo":
            return kwargs.get("text", "")
        raise ValueError(f"echo connector: unknown action {action!r}")
