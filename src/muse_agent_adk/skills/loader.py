from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Skill:
    name: str
    description: str
    body: str
    path: Path
    triggers: list[str] = field(default_factory=list)

    def index_line(self) -> str:
        return f"{self.name} — {self.description}"


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Minimal frontmatter: --- key: value --- at the very top.

    Supports name / description / triggers (comma-separated) only.
    A full YAML parser is an adapter concern, not core behaviour.
    """
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    meta: dict[str, str] = {}
    for line in text[3:end].splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip()
    return meta, text[end + 4:].lstrip("\n")


def load_skill_file(path: Path) -> Skill:
    text = path.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(text)
    triggers = [t.strip() for t in meta.get("triggers", "").split(",")
                if t.strip()]
    return Skill(name=meta.get("name") or path.parent.name,
                 description=meta.get("description", ""),
                 body=body, path=path, triggers=triggers)
