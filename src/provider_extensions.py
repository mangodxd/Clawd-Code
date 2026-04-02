"""
Provider extension system for additional model providers.

Provides functionality to:
- Define custom providers
- Support local models
- Add third-party API providers
- Manage provider registry
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class ProviderCapability:
    """Provider capabilities."""

    supports_streaming: bool = True
    supports_tools: bool = True
    supports_vision: bool = False
    supports_audio: bool = False
    max_tokens: int = 4096


@dataclass(frozen=True)
class ProviderInfo:
    """Provider information."""

    name: str
    display_name: str
    description: str = ""
    api_base_url: str = ""
    capabilities: ProviderCapability | None = None
    default_model: str = ""
    available_models: list[str] | None = None


class ProviderRegistry:
    """Registry for model providers."""

    def __init__(self):
        """Initialize provider registry."""
        self.providers: dict[str, ProviderInfo] = {}
        self._factories: dict[str, Callable] = {}

    def register_provider(
        self,
        info: ProviderInfo,
        factory: Callable | None = None,
    ) -> None:
        """
        Register a provider.

        Args:
            info: Provider information
            factory: Optional factory function to create provider instance
        """
        self.providers[info.name] = info
        if factory:
            self._factories[info.name] = factory

    def unregister_provider(self, name: str) -> bool:
        """Unregister a provider."""
        removed = self.providers.pop(name, None) is not None
        self._factories.pop(name, None)
        return removed

    def get_provider(self, name: str) -> ProviderInfo | None:
        """Get provider information."""
        return self.providers.get(name)

    def get_factory(self, name: str) -> Callable | None:
        """Get provider factory function."""
        return self._factories.get(name)

    def list_providers(self) -> list[ProviderInfo]:
        """List all registered providers."""
        return list(self.providers.values())

    def create_provider(self, name: str, **kwargs) -> Any | None:
        """
        Create a provider instance.

        Args:
            name: Provider name
            **kwargs: Provider configuration

        Returns:
            Provider instance or None
        """
        factory = self._factories.get(name)
        if factory:
            return factory(**kwargs)
        return None


# Built-in providers
def register_builtin_providers(registry: ProviderRegistry) -> None:
    """Register built-in providers."""
    # Anthropic
    registry.register_provider(
        ProviderInfo(
            name="anthropic",
            display_name="Anthropic",
            description="Anthropic Claude models",
            api_base_url="https://api.anthropic.com",
            capabilities=ProviderCapability(
                supports_streaming=True,
                supports_tools=True,
                supports_vision=True,
                max_tokens=200000,
            ),
            default_model="claude-sonnet-4-6",
            available_models=[
                "claude-opus-4-6",
                "claude-sonnet-4-6",
                "claude-haiku-4-5",
            ],
        )
    )

    # OpenAI
    registry.register_provider(
        ProviderInfo(
            name="openai",
            display_name="OpenAI",
            description="OpenAI GPT models",
            api_base_url="https://api.openai.com/v1",
            capabilities=ProviderCapability(
                supports_streaming=True,
                supports_tools=True,
                supports_vision=True,
                max_tokens=128000,
            ),
            default_model="gpt-4o",
            available_models=["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
        )
    )

    # GLM (Zhipu AI)
    registry.register_provider(
        ProviderInfo(
            name="zhipuai",
            display_name="Zhipu AI",
            description="Zhipu AI GLM models",
            api_base_url="https://open.bigmodel.cn/api/paas/v4",
            capabilities=ProviderCapability(
                supports_streaming=True,
                supports_tools=False,
                max_tokens=128000,
            ),
            default_model="glm-4-plus",
            available_models=["glm-4-plus", "glm-4-flash"],
        )
    )

    # Local models (Ollama)
    registry.register_provider(
        ProviderInfo(
            name="ollama",
            display_name="Ollama (Local)",
            description="Local models via Ollama",
            api_base_url="http://localhost:11434",
            capabilities=ProviderCapability(
                supports_streaming=True,
                supports_tools=False,
                max_tokens=8192,
            ),
            default_model="llama3.1",
        )
    )


def provider(
    name: str,
    display_name: str,
    description: str = "",
    api_base_url: str = "",
    capabilities: ProviderCapability | None = None,
    default_model: str = "",
    available_models: list[str] | None = None,
):
    """
    Decorator to define a custom provider.

    Args:
        name: Provider name
        display_name: Display name
        description: Provider description
        api_base_url: API base URL
        capabilities: Provider capabilities
        default_model: Default model
        available_models: Available models

    Returns:
        Decorator function
    """

    def decorator(factory: Callable) -> ProviderInfo:
        info = ProviderInfo(
            name=name,
            display_name=display_name,
            description=description,
            api_base_url=api_base_url,
            capabilities=capabilities,
            default_model=default_model,
            available_models=available_models,
        )
        return info

    return decorator


def create_provider_registry() -> ProviderRegistry:
    """Create a provider registry with built-in providers."""
    registry = ProviderRegistry()
    register_builtin_providers(registry)
    return registry
