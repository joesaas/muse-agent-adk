"""A minimal in-process event bus.

The outer loop of a Muse-like agent is event-driven: user messages,
hook firings, scheduled jobs and subagent handoffs are all events that
*wake* the agent loop rather than being polled by it. This bus is the
single delivery mechanism; transports (CLI, chat apps, cron) publish,
the runtime subscribes.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Callable

from muse_agent_adk.core.types import Event

Handler = Callable[[Event], None]


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[Handler]] = defaultdict(list)
        self.history: list[Event] = []

    def subscribe(self, event_type: str, handler: Handler) -> None:
        self._handlers[event_type].append(handler)

    def publish(self, event: Event) -> Event:
        self.history.append(event)
        for handler in self._handlers.get(event.type, []):
            handler(event)
        for handler in self._handlers.get("*", []):
            handler(event)
        return event

    def emit(self, event_type: str, **payload) -> Event:
        return self.publish(Event(type=event_type, payload=payload))
