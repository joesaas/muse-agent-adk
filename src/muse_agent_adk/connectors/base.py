from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class ConnectorStatus:
    name: str
    connected: bool
    detail: str = ""


class Connector(Protocol):
    name: str

    def status(self) -> ConnectorStatus:
        ...

    def call(self, action: str, **kwargs: Any) -> Any:
        ...
