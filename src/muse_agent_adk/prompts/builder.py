"""Assembles sections into the final system prompt, deterministically."""
from __future__ import annotations

from dataclasses import dataclass, field

from muse_agent_adk.prompts.sections import Section, default_sections


@dataclass
class PromptContext:
    profile_text: str = ""
    memory_text: str = ""
    skill_lines: list[str] = field(default_factory=list)
    tool_lines: list[str] = field(default_factory=list)


class PromptBuilder:
    def __init__(self, sections: list[Section] | None = None,
                 disabled: set[str] | None = None) -> None:
        self.sections = sorted(sections or default_sections(),
                               key=lambda s: s.order)
        self.disabled = disabled or set()

    def build(self, ctx: PromptContext) -> str:
        parts = []
        for section in self.sections:
            if section.id in self.disabled:
                continue
            text = section.render(ctx).strip()
            if text:
                parts.append(text)
        return "\n\n".join(parts)

    def section_ids(self) -> list[str]:
        return [s.id for s in self.sections]
