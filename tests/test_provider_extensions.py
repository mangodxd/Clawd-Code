"""Tests for provider_extensions module."""

import unittest
from unittest.mock import Mock

from src.provider_extensions import (
    ProviderCapability,
    ProviderInfo,
    ProviderRegistry,
    register_builtin_providers,
    provider,
    create_provider_registry,
)


class TestProviderExtensions(unittest.TestCase):
    """Test cases for provider extensions."""

    def test_create_provider_capability(self):
        """Test creating provider capabilities."""
        capability = ProviderCapability(
            supports_streaming=True,
            supports_tools=True,
        )

        self.assertTrue(capability.supports_streaming)
        self.assertTrue(capability.supports_tools)
        self.assertFalse(capability.supports_vision)

    def test_create_provider_info(self):
        """Test creating provider information."""
        info = ProviderInfo(
            name="test_provider",
            display_name="Test Provider",
            description="Test description",
        )

        self.assertEqual(info.name, "test_provider")
        self.assertEqual(info.display_name, "Test Provider")

    def test_create_provider_registry(self):
        """Test creating provider registry."""
        registry = ProviderRegistry()

        self.assertEqual(len(registry.providers), 0)

    def test_register_provider(self):
        """Test registering a provider."""
        registry = ProviderRegistry()
        info = ProviderInfo(name="test", display_name="Test")

        registry.register_provider(info)

        self.assertIn("test", registry.providers)

    def test_unregister_provider(self):
        """Test unregistering a provider."""
        registry = ProviderRegistry()
        info = ProviderInfo(name="test", display_name="Test")

        registry.register_provider(info)
        result = registry.unregister_provider("test")

        self.assertTrue(result)
        self.assertNotIn("test", registry.providers)

    def test_unregister_provider_missing(self):
        """Test unregistering missing provider."""
        registry = ProviderRegistry()
        result = registry.unregister_provider("nonexistent")

        self.assertFalse(result)

    def test_get_provider(self):
        """Test getting a provider."""
        registry = ProviderRegistry()
        info = ProviderInfo(name="test", display_name="Test")

        registry.register_provider(info)
        result = registry.get_provider("test")

        self.assertEqual(result, info)

    def test_get_provider_missing(self):
        """Test getting missing provider."""
        registry = ProviderRegistry()
        result = registry.get_provider("nonexistent")

        self.assertIsNone(result)

    def test_list_providers(self):
        """Test listing providers."""
        registry = ProviderRegistry()
        info1 = ProviderInfo(name="test1", display_name="Test 1")
        info2 = ProviderInfo(name="test2", display_name="Test 2")

        registry.register_provider(info1)
        registry.register_provider(info2)

        providers = registry.list_providers()

        self.assertEqual(len(providers), 2)

    def test_create_provider_with_factory(self):
        """Test creating provider instance with factory."""
        registry = ProviderRegistry()
        info = ProviderInfo(name="test", display_name="Test")
        mock_factory = Mock(return_value="provider_instance")

        registry.register_provider(info, factory=mock_factory)
        result = registry.create_provider("test", api_key="test_key")

        self.assertEqual(result, "provider_instance")
        mock_factory.assert_called_once_with(api_key="test_key")

    def test_create_provider_without_factory(self):
        """Test creating provider without factory."""
        registry = ProviderRegistry()
        info = ProviderInfo(name="test", display_name="Test")

        registry.register_provider(info)
        result = registry.create_provider("test")

        self.assertIsNone(result)

    def test_register_builtin_providers(self):
        """Test registering built-in providers."""
        registry = ProviderRegistry()
        register_builtin_providers(registry)

        # Should have Anthropic, OpenAI, GLM, Ollama
        self.assertIn("anthropic", registry.providers)
        self.assertIn("openai", registry.providers)
        self.assertIn("zhipuai", registry.providers)
        self.assertIn("ollama", registry.providers)

    def test_create_provider_registry_with_builtins(self):
        """Test creating registry with built-in providers."""
        registry = create_provider_registry()

        self.assertGreater(len(registry.providers), 0)
        self.assertIn("anthropic", registry.providers)

    def test_builtin_provider_capabilities(self):
        """Test built-in provider capabilities."""
        registry = create_provider_registry()
        anthropic = registry.get_provider("anthropic")

        self.assertIsNotNone(anthropic)
        self.assertIsNotNone(anthropic.capabilities)
        self.assertTrue(anthropic.capabilities.supports_streaming)

    def test_builtin_provider_models(self):
        """Test built-in provider model lists."""
        registry = create_provider_registry()
        openai = registry.get_provider("openai")

        self.assertIsNotNone(openai)
        self.assertIn("gpt-4o", openai.available_models)

    def test_provider_decorator(self):
        """Test provider decorator."""
        @provider(
            name="custom",
            display_name="Custom Provider",
            description="Custom provider for testing",
        )
        def custom_factory(api_key=None):
            return f"custom_provider_{api_key}"

        self.assertIsInstance(custom_factory, ProviderInfo)
        self.assertEqual(custom_factory.name, "custom")


if __name__ == "__main__":
    unittest.main()
