"""Session snapshots: recovery after a crash or a VM replacement.

After every agent step the runtime saves the full context (a *snapshot
copy*, never a shared reference) to home/sessions/<id>.json. A new
process can load it and continue exactly where the old one stopped —
the same snapshot discipline subagents use at spawn time.
"""
from __future__ import annotations

import json
from pathlib import Path

from muse_agent_adk.context.manager import ContextManager
from muse_agent_adk.core.types import Message


def snapshot_path(home: Path, session_id: str) -> Path:
    return home / "sessions" / f"{session_id}.json"


def save_snapshot(home: Path, session_id: str, ctx: ContextManager) -> Path:
    path = snapshot_path(home, session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"session_id": session_id,
            "messages": [m.to_dict() for m in ctx.messages]}
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1),
                    encoding="utf-8")
    return path


def load_snapshot(home: Path, session_id: str,
                  budget_tokens: int = 32_000,
                  keep_recent: int = 12) -> ContextManager | None:
    path = snapshot_path(home, session_id)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    ctx = ContextManager(budget_tokens=budget_tokens, keep_recent=keep_recent)
    ctx.messages = [Message.from_dict(d) for d in data["messages"]]
    return ctx
