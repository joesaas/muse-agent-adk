from __future__ import annotations

from pathlib import Path

from muse_agent_adk.skills.loader import Skill, load_skill_file


class SkillRegistry:
    """Discovers skills in the home skills/ dir and any extra dirs."""

    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {}

    def discover(self, *dirs: Path) -> "SkillRegistry":
        for base in dirs:
            if not base or not base.exists():
                continue
            for skill_md in sorted(base.glob("*/SKILL.md")):
                skill = load_skill_file(skill_md)
                self._skills[skill.name] = skill
        return self

    def all(self) -> list[Skill]:
        return sorted(self._skills.values(), key=lambda s: s.name)

    def get(self, name: str) -> Skill | None:
        return self._skills.get(name)

    def index_lines(self) -> list[str]:
        return [s.index_line() for s in self.all()]

    def match(self, text: str) -> list[Skill]:
        """Keyword matching on triggers — deliberately simple. Ranking
        and embedding-based routing can replace this behind the same
        interface when a project outgrows keywords."""
        low = text.lower()
        return [s for s in self.all()
                if any(t.lower() in low for t in s.triggers)]
