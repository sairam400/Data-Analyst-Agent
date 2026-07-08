"""get_provider() reads config.SETTINGS.llm_provider and returns the matching
Provider — swapping the underlying LLM is then a .env change, not a code change."""
from .anthropic_provider import AnthropicProvider
from .base import Provider
from .mock_provider import MockProvider
from .openai_provider import OpenAIProvider
from ...config import SETTINGS

_PROVIDERS = {
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
    "azure_openai": OpenAIProvider,
}


def get_provider(mock_plans=None, provider_name=None):
    provider_name = provider_name or SETTINGS.llm_provider

    if provider_name == "mock":
        if mock_plans is None:
            raise ValueError("the mock provider requires mock_plans")
        return MockProvider(mock_plans)

    if provider_name not in _PROVIDERS:
        raise ValueError(f"unknown LLM_PROVIDER '{provider_name}'")
    return _PROVIDERS[provider_name]()
