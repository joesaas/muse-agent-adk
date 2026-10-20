"""Compression: trade old detail for a faithful summary.

Contract (see design ch04):
  - The system prompt and the most recent messages are never touched.
  - What is removed is replaced by ONE summary message, marked in
    metadata, so recovery and debugging can see that compression ran.
  - Summarization is an interface. The default is extractive and
    offline (first line of each removed message); an LLM summarizer
    can be dropped in behind the same protocol without touching the
    runtime.
"""
from __future__ import annotations

from typing import Protocol

from muse_agent_adk.context.manager import ContextManager
from muse_agent_adk.core.types import Message, Role

SUMMARY_PREFIX = "[上下文已压缩] 以下为较早对话的摘要："


class Summarizer(Protocol):
    def summarize(self, messages: list[Message]) -> str:
        ...


class ExtractiveSummarizer:
    """Offline default: keep the first line of each message, labelled
    by role. Lossy but deterministic, free, and honest about it."""

    def summarize(self, messages: list[Message]) -> str:
        lines = []
        for m in messages:
            first = m.content.strip().splitlines()[0] if m.content.strip() else ""
            if len(first) > 120:
                first = first[:120] + "…"
            label = m.name or m.role.value
            lines.append(f"- {label}: {first}")
        return "\n".join(lines)


class Compressor:
    def __init__(self, summarizer: Summarizer | None = None) -> None:
        self.summarizer = summarizer or ExtractiveSummarizer()

    def compress_if_needed(self, ctx: ContextManager) -> bool:
        """Returns True when compression ran."""
        if not ctx.over_budget():
            return False
        rng = ctx.compressible_range()
        if rng is None:
            return False
        start, end = rng
        removed = ctx.messages[start:end]
        if not removed:
            return False
        summary = Message(
            role=Role.SYSTEM,
            content=SUMMARY_PREFIX + "\n" + self.summarizer.summarize(removed),
            metadata={"compressed": True, "removed_count": len(removed)})
        ctx.messages[start:end] = [summary]
        return True
