"""Creates and describes ~/.muse-agent/ (or $MUSE_AGENT_HOME).

Layout:
  IDENTITY.md / SOUL.md / USER.md / AGENTS.md   standing context
  MEMORY.md                                    curated long-term memory
  memory/                                      daily notes
  skills/                                      user skills (*/SKILL.md)
  sessions/                                    recovery snapshots
  goals.json                                   goals & tracked items
  config.toml                                  optional configuration
Templates are minimal starting points; the files belong to the user.
"""
from __future__ import annotations

from pathlib import Path

HOME_FILES: dict[str, str] = {
    "IDENTITY.md": "# IDENTITY.md\n\n- **Name:** Muse Agent\n- **Vibe:** sharp, warm, direct\n",
    "SOUL.md": "# SOUL.md\n\nBe genuinely helpful, not performatively helpful. "
               "Have opinions. Be resourceful before asking.\n",
    "USER.md": "# USER.md\n\n- **Name:**\n- **What to call them:**\n- **Timezone:**\n",
    "AGENTS.md": "# AGENTS.md\n\nOperating conventions for this workspace. "
                 "Add durable lessons here as they are learned.\n",
    "MEMORY.md": "# MEMORY.md\n\n## Facts\n",
}


def ensure_home(home: Path) -> list[Path]:
    """Create missing pieces; never overwrite existing user files."""
    created: list[Path] = []
    home.mkdir(parents=True, exist_ok=True)
    for sub in ("memory", "skills", "sessions"):
        (home / sub).mkdir(exist_ok=True)
    for name, template in HOME_FILES.items():
        path = home / name
        if not path.exists():
            path.write_text(template, encoding="utf-8")
            created.append(path)
    return created
