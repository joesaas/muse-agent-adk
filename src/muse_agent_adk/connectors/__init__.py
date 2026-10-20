"""connectors: external-service adapters behind status()/call()
(unchanged contract); capabilities surface to the agent as tools via
connectors/tools.py."""
from muse_agent_adk.connectors.base import Connector, ConnectorStatus
from muse_agent_adk.connectors.echo import EchoConnector
from muse_agent_adk.connectors.registry import ConnectorRegistry
from muse_agent_adk.connectors.tools import connector_tools

__all__ = [
    "Connector", "ConnectorStatus", "ConnectorRegistry", "EchoConnector",
    "connector_tools",
]
