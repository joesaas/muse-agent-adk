from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from muse_agent_adk.core.types import ToolSpec

ToolHandler = Callable[[dict], str]


@dataclass
class Tool:
    spec: ToolSpec
    handler: ToolHandler

    @property
    def name(self) -> str:
        return self.spec.name
