from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass
class MemoryHit:
    source: str        # e.g. "MEMORY.md" or "memory/2026-10-18.md"
    line: int          # 1-based
    text: str
    score: int


class MemoryStore:
    def __init__(self, home: Path) -> None:
        self.home = home
        self.curated = home / "MEMORY.md"
        self.daily_dir = home / "memory"

    # -- writing -----------------------------------------------------
    def append_daily(self, text: str, on: date | None = None) -> Path:
        day = on or date.today()
        self.daily_dir.mkdir(parents=True, exist_ok=True)
        path = self.daily_dir / f"{day.isoformat()}.md"
        prefix = "" if path.exists() else f"# {day.isoformat()}\n\n"
        with path.open("a", encoding="utf-8") as f:
            f.write(prefix + f"- {text}\n")
        return path

    def append_curated(self, text: str) -> Path:
        self.curated.parent.mkdir(parents=True, exist_ok=True)
        prefix = "" if self.curated.exists() else "# MEMORY.md\n\n## Facts\n"
        with self.curated.open("a", encoding="utf-8") as f:
            f.write(prefix + f"- {text}\n")
        return self.curated

    # -- reading -----------------------------------------------------
    def _files(self) -> list[Path]:
        files = [self.curated] if self.curated.exists() else []
        if self.daily_dir.exists():
            files += sorted(self.daily_dir.glob("*.md"))
        return files

    def search(self, query: str, limit: int = 6) -> list[MemoryHit]:
        terms = [t for t in re.split(r"\s+", query.strip().lower()) if t]
        if not terms:
            return []
        hits: list[MemoryHit] = []
        for path in self._files():
            source = ("MEMORY.md" if path == self.curated
                      else f"memory/{path.name}")
            for i, line in enumerate(
                    path.read_text(encoding="utf-8").splitlines(), start=1):
                low = line.lower()
                score = sum(1 for t in terms if t in low)
                if score:
                    hits.append(MemoryHit(source, i, line.strip(), score))
        hits.sort(key=lambda h: (-h.score, h.source, h.line))
        return hits[:limit]

    def index_text(self, max_chars: int = 2000) -> str:
        """What the prompt builder injects: the curated file, trimmed."""
        if not self.curated.exists():
            return ""
        text = self.curated.read_text(encoding="utf-8").strip()
        return text[:max_chars]
