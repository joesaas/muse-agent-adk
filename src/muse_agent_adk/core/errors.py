class MuseAgentError(Exception):
    """Base error for muse-agent."""


class ToolError(MuseAgentError):
    """A tool failed or was called incorrectly."""


class ApprovalDenied(MuseAgentError):
    """The approval gate refused a tool call."""


class ConfigError(MuseAgentError):
    """Configuration is missing or invalid."""
