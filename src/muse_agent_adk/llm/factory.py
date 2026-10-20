"""Model factory: config -> the model object an ADK LlmAgent runs.

In muse-agent this seam was a hand-rolled ``LLMProvider`` protocol; in
ADK the ``BaseLlm`` class *is* that contract, so the factory returns
ADK models directly:

  mock              -> MockLlm (offline, deterministic; the default)
  gemini            -> ADK's native Gemini model wrapper
  openai-compatible -> ADK's LiteLlm wrapper pointed at any endpoint
                       speaking the OpenAI chat API (needs the optional
                       ``litellm`` extra and a key read by env-var name)

No key is ever stored in config: the key is fetched by name through
security.CredentialStore at build time and handed to the wrapper.
"""
from __future__ import annotations

from google.adk.models.base_llm import BaseLlm

from muse_agent_adk.core.errors import ConfigError
from muse_agent_adk.llm.mock import MockLlm
from muse_agent_adk.security.credentials import CredentialStore


def build_model(config, credentials: CredentialStore | None = None) -> BaseLlm:
    if config.provider == "mock":
        return MockLlm(model=config.model)
    if config.provider == "gemini":
        from google.adk.models.google_llm import Gemini
        store = credentials or CredentialStore()
        key = store.get("GOOGLE_API_KEY") or store.get("GEMINI_API_KEY")
        if key:
            return Gemini(model=config.model, api_key=key)
        return Gemini(model=config.model)
    if config.provider == "openai-compatible":
        try:
            from google.adk.models.lite_llm import LiteLlm
        except ImportError as exc:  # pragma: no cover - optional extra
            raise ConfigError(
                "provider 'openai-compatible' needs the litellm extra: "
                "pip install 'muse-agent-adk[litellm]'") from exc
        store = credentials or CredentialStore()
        kwargs: dict = {}
        key = store.get(config.api_key_env)
        if key:
            kwargs["api_key"] = key
        return LiteLlm(model=f"openai/{config.model}",
                       api_base=config.base_url, **kwargs)
    raise ConfigError(
        f"unknown provider: {config.provider!r} "
        "(expected 'mock', 'gemini' or 'openai-compatible')")
