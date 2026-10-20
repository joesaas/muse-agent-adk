"""Standing files, Muse-style (see design ch10/ch16).

The home directory holds plain Markdown the user can read and edit:
  IDENTITY.md — who the agent is (name, character, vibe)
  SOUL.md     — persona and tone
  USER.md     — who the user is
  AGENTS.md   — operating conventions for this workspace
They are injected into the system prompt at session start, in this
order, each under its own heading. Missing files are skipped, never
fatal: identity is configuration, not code.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

FILES = ("IDENTITY.md", "SOUL.md", "USER.md", "AGENTS.md")


@dataclass
class Profile:
    sections: dict[str, str] = field(default_factory=dict)

    def render(self) -> str:
        parts = []
        for name in FILES:
            text = self.sections.get(name, "").strip()
            if text:
                parts.append(f"## {name}\n{text}")
        return "\n\n".join(parts)


def load_profile(home: Path) -> Profile:
    profile = Profile()
    for name in FILES:
        path = home / name
        if path.exists():
            profile.sections[name] = path.read_text(encoding="utf-8")
    return profile
