"""Built-in tools. Deliberately small and sandbox-aware:
file tools are confined to a root directory (default: the cwd) —
a tool must never silently reach outside its declared scope.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from muse_agent_adk.core.types import ToolSpec
from muse_agent_adk.tools.base import Tool


def _confine(root: Path, raw: str) -> Path:
    path = (root / raw).resolve() if not Path(raw).is_absolute() \
        else Path(raw).resolve()
    if root.resolve() not in path.parents and path != root.resolve():
        raise ValueError(f"path escapes sandbox root: {raw}")
    return path


def builtin_tools(sandbox_root: Path | None = None) -> list[Tool]:
    root = sandbox_root or Path.cwd()

    def echo(args: dict) -> str:
        return str(args.get("text", ""))

    def now(args: dict) -> str:
        return datetime.now().astimezone().isoformat(timespec="seconds")

    def list_dir(args: dict) -> str:
        path = _confine(root, str(args.get("path", ".")))
        if not path.is_dir():
            raise ValueError(f"not a directory: {path}")
        entries = sorted(p.name + ("/" if p.is_dir() else "")
                         for p in path.iterdir())
        return "\n".join(entries) if entries else "(empty)"

    def read_file(args: dict) -> str:
        path = _confine(root, str(args.get("path", "")))
        text = path.read_text(encoding="utf-8")
        limit = int(args.get("max_chars", 4000))
        return text[:limit]

    return [
        Tool(ToolSpec("echo", "Return the given text unchanged.",
                      {"type": "object",
                       "properties": {"text": {"type": "string"}},
                       "required": ["text"]}, risk="read"), echo),
        Tool(ToolSpec("now", "Return the current local date and time.",
                      {"type": "object", "properties": {}}, risk="read"), now),
        Tool(ToolSpec("list_dir", "List a directory inside the sandbox root.",
                      {"type": "object",
                       "properties": {"path": {"type": "string"}}},
                      risk="read"), list_dir),
        Tool(ToolSpec("read_file", "Read a text file inside the sandbox root.",
                      {"type": "object",
                       "properties": {"path": {"type": "string"},
                                      "max_chars": {"type": "integer"}},
                       "required": ["path"]}, risk="read"), read_file),
    ]
