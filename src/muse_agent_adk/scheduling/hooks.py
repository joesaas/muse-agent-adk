from __future__ import annotations

from typing import Callable

from muse_agent_adk.core.events import EventBus

CheckFn = Callable[[], bool]


class HookRegistry:
    """Condition watchers: register check() functions; when one flips
    to True, a `hook.fired` event wakes the agent. Hooks are cheap
    polling by design — inteligencia stays in the agent run they wake.
    """

    def __init__(self, bus: EventBus) -> None:
        self.bus = bus
        self._hooks: dict[str, CheckFn] = {}
        self._fired: set[str] = set()

    def register(self, name: str, check: CheckFn) -> None:
        self._hooks[name] = check

    def poll(self) -> list[str]:
        fired = []
        for name, check in self._hooks.items():
            if name in self._fired:
                continue
            try:
                hit = check()
            except Exception:
                hit = False
            if hit:
                self._fired.add(name)
                fired.append(name)
                self.bus.emit("hook.fired", hook=name)
        return fired

    def reset(self, name: str) -> None:
        self._fired.discard(name)
