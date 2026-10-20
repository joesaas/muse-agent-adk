from __future__ import annotations

from muse_agent_adk.connectors.base import Connector, ConnectorStatus


class ConnectorRegistry:
    def __init__(self) -> None:
        self._items: dict[str, Connector] = {}

    def register(self, connector: Connector) -> None:
        self._items[connector.name] = connector

    def get(self, name: str) -> Connector:
        if name not in self._items:
            raise KeyError(f"unknown connector: {name}")
        return self._items[name]

    def statuses(self) -> list[ConnectorStatus]:
        return [c.status() for c in self._items.values()]
