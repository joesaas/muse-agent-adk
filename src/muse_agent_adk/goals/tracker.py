from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class Goal:
    title: str
    description: str = ""
    id: str = field(default_factory=lambda: "goal_" + uuid.uuid4().hex[:8])
    status: str = "active"      # active | completed


@dataclass
class TrackedItem:
    title: str
    detail: str = ""
    id: str = field(default_factory=lambda: "item_" + uuid.uuid4().hex[:8])
    status: str = "open"        # open | completed


class GoalTracker:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.goals: list[Goal] = []
        self.items: list[TrackedItem] = []
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.goals = [Goal(**g) for g in data.get("goals", [])]
        self.items = [TrackedItem(**i) for i in data.get("items", [])]

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {"goals": [asdict(g) for g in self.goals],
                "items": [asdict(i) for i in self.items]}
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=1),
                             encoding="utf-8")

    def add_goal(self, title: str, description: str = "") -> Goal:
        goal = Goal(title=title, description=description)
        self.goals.append(goal)
        self._save()
        return goal

    def add_item(self, title: str, detail: str = "") -> TrackedItem:
        item = TrackedItem(title=title, detail=detail)
        self.items.append(item)
        self._save()
        return item

    def complete_item(self, item_id: str) -> bool:
        for item in self.items:
            if item.id == item_id:
                item.status = "completed"
                self._save()
                return True
        return False

    def open_items(self) -> list[TrackedItem]:
        return [i for i in self.items if i.status == "open"]
