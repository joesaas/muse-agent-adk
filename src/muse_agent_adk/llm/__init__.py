"""llm: model adapters behind ADK's BaseLlm contract.

The runtime never sees a vendor SDK: LlmAgent takes the object
build_model() returns, and swapping providers is a config change.
"""
from muse_agent_adk.llm.factory import build_model
from muse_agent_adk.llm.mock import MockLlm

__all__ = ["build_model", "MockLlm"]
