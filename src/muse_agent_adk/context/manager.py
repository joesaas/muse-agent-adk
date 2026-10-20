"""The conversation window.

Owns the ordered message list for one session. The system prompt is
pinned at index 0 and never compressed. Everything else is managed
against a token budget; when the budget is exceeded the Compressor
(see compression.py) rewrites the middle of the window.
"""
from __future__ import annotations

from muse_agent_adk.core.types import Message, Role


def estimate_tokens(text: str) -> int:
    """Cheap, provider-agnostic estimate (~4 chars/token, CJK ~1.5).

    Good enough for budget decisions; exact counts are a provider
    concern and belong in the adapter layer if ever needed.
    """
    cjk = sum(1 for ch in text if '\u4e00' <= ch <= '\u9fff')
    rest = len(text) - cjk
    return int(cjk / 1.5 + rest / 4) + 1


class ContextManager:
    def __init__(self, budget_tokens: int = 32_000,
                 keep_recent: int = 12) -> None:
        self.budget_tokens = budget_tokens
        self.keep_recent = keep_recent
        self.messages: list[Message] = []

    def set_system(self, text: str) -> None:
        msg = Message(role=Role.SYSTEM, content=text)
        if self.messages and self.messages[0].role is Role.SYSTEM:
            self.messages[0] = msg
        else:
            self.messages.insert(0, msg)

    def add(self, message: Message) -> None:
        self.messages.append(message)

    def add_user(self, text: str) -> None:
        self.add(Message(role=Role.USER, content=text))

    def total_tokens(self) -> int:
        return sum(estimate_tokens(m.content) for m in self.messages)

    def over_budget(self) -> bool:
        return self.total_tokens() > self.budget_tokens

    def compressible_range(self) -> tuple[int, int] | None:
        """(start, end) slice that compression may rewrite: everything
        after the system prompt, except the most recent messages."""
        start = 1 if self.messages and self.messages[0].role is Role.SYSTEM else 0
        end = len(self.messages) - self.keep_recent
        if end <= start:
            return None
        return (start, end)
