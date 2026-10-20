"""core: the shared data contracts, event bus and error types.

Unchanged in shape from muse-agent — these dataclasses are still the
only shapes that cross module boundaries. ADK-specific objects (Event,
Content) are adapted to these types at the runtime edge, never leaked
into business modules.
"""
from muse_agent_adk.core.errors import (ApprovalDenied, ConfigError,
                                         MuseAgentError, ToolError)
from muse_agent_adk.core.events import EventBus
from muse_agent_adk.core.types import (Event, Message, Role, ToolCall,
                                        ToolResult, ToolSpec)

__all__ = [
    "Event", "EventBus", "Message", "Role", "ToolCall", "ToolResult",
    "ToolSpec", "MuseAgentError", "ToolError", "ApprovalDenied",
    "ConfigError",
]
