"""Tests for enterprise_integration module."""

import unittest
from datetime import datetime
from pathlib import Path
import tempfile
import shutil

from src.enterprise_integration import (
    IntegrationType,
    IntegrationConfig,
    IntegrationEvent,
    AuditLog,
    WebhookConnector,
    SlackConnector,
    EnterpriseIntegration,
    create_enterprise_integration,
)


class TestEnterpriseIntegration(unittest.TestCase):
    """Test cases for enterprise integration."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        """Clean up test files."""
        shutil.rmtree(self.test_dir)

    def test_create_integration_config(self):
        """Test creating integration configuration."""
        config = IntegrationConfig(
            id="int1",
            name="Test Integration",
            type=IntegrationType.WEBHOOK,
            endpoint="https://api.example.com/webhook",
        )

        self.assertEqual(config.id, "int1")
        self.assertEqual(config.type, IntegrationType.WEBHOOK)
        self.assertTrue(config.enabled)

    def test_create_integration_event(self):
        """Test creating an integration event."""
        event = IntegrationEvent(
            event_id="evt1",
            integration_id="int1",
            event_type="message",
            payload={"text": "Hello"},
            timestamp=datetime.now(),
        )

        self.assertEqual(event.event_id, "evt1")
        self.assertEqual(event.event_type, "message")

    def test_event_to_dict(self):
        """Test event serialization."""
        event = IntegrationEvent(
            event_id="evt1",
            integration_id="int1",
            event_type="message",
            payload={"key": "value"},
            timestamp=datetime.now(),
        )

        data = event.to_dict()

        self.assertEqual(data["event_id"], "evt1")
        self.assertEqual(data["event_type"], "message")
        self.assertEqual(data["payload"], {"key": "value"})

    def test_create_audit_log(self):
        """Test creating an audit log."""
        log = AuditLog(
            log_id="log1",
            timestamp=datetime.now(),
            integration_id="int1",
            action="send",
            user="testuser",
            resource="message:123",
            details={"size": 100},
            result="success",
        )

        self.assertEqual(log.log_id, "log1")
        self.assertEqual(log.action, "send")
        self.assertEqual(log.result, "success")

    def test_audit_log_to_dict(self):
        """Test audit log serialization."""
        log = AuditLog(
            log_id="log1",
            timestamp=datetime.now(),
            integration_id="int1",
            action="connect",
            user=None,
            resource="integration:int1",
            details={},
            result="success",
        )

        data = log.to_dict()

        self.assertEqual(data["log_id"], "log1")
        self.assertEqual(data["action"], "connect")

    def test_create_webhook_connector(self):
        """Test creating webhook connector."""
        config = IntegrationConfig(
            id="int1",
            name="Webhook",
            type=IntegrationType.WEBHOOK,
            endpoint="https://api.example.com/webhook",
        )

        connector = WebhookConnector(config)

        self.assertEqual(connector.config, config)

    def test_webhook_connect(self):
        """Test webhook connection."""
        config = IntegrationConfig(
            id="int1",
            name="Webhook",
            type=IntegrationType.WEBHOOK,
            endpoint="https://api.example.com/webhook",
        )

        connector = WebhookConnector(config)
        result = connector.connect()

        self.assertTrue(result)

    def test_webhook_test_connection(self):
        """Test webhook connection test."""
        config = IntegrationConfig(
            id="int1",
            name="Webhook",
            type=IntegrationType.WEBHOOK,
            endpoint="https://api.example.com/webhook",
        )

        connector = WebhookConnector(config)
        result = connector.test_connection()

        self.assertTrue(result)

    def test_webhook_receive(self):
        """Test webhook receive (should be empty)."""
        config = IntegrationConfig(
            id="int1",
            name="Webhook",
            type=IntegrationType.WEBHOOK,
            endpoint="https://api.example.com/webhook",
        )

        connector = WebhookConnector(config)
        events = connector.receive()

        self.assertEqual(len(events), 0)

    def test_create_slack_connector(self):
        """Test creating Slack connector."""
        config = IntegrationConfig(
            id="int1",
            name="Slack",
            type=IntegrationType.SLACK,
            endpoint="https://hooks.slack.com/services/xxx",
        )

        connector = SlackConnector(config)

        self.assertEqual(connector.config, config)

    def test_slack_connect(self):
        """Test Slack connection."""
        config = IntegrationConfig(
            id="int1",
            name="Slack",
            type=IntegrationType.SLACK,
            endpoint="https://hooks.slack.com/services/xxx",
        )

        connector = SlackConnector(config)
        result = connector.connect()

        self.assertTrue(result)

    def test_create_enterprise_integration(self):
        """Test creating enterprise integration manager."""
        integration = create_enterprise_integration(self.test_dir)

        self.assertIsInstance(integration, EnterpriseIntegration)
        self.assertEqual(integration.storage_dir, self.test_dir)

    def test_register_integration(self):
        """Test registering an integration."""
        manager = create_enterprise_integration(self.test_dir)

        config = IntegrationConfig(
            id="int1",
            name="Test",
            type=IntegrationType.WEBHOOK,
            endpoint="https://api.example.com/webhook",
        )

        manager.register_integration(config)

        self.assertIn("int1", manager.integrations)

    def test_get_integration(self):
        """Test getting an integration."""
        manager = create_enterprise_integration(self.test_dir)

        config = IntegrationConfig(
            id="int1",
            name="Test",
            type=IntegrationType.WEBHOOK,
            endpoint="https://api.example.com/webhook",
        )

        manager.register_integration(config)
        found = manager.get_integration("int1")

        self.assertIsNotNone(found)
        self.assertEqual(found.name, "Test")

    def test_list_integrations(self):
        """Test listing integrations."""
        manager = create_enterprise_integration(self.test_dir)

        config1 = IntegrationConfig(
            id="int1",
            name="Webhook 1",
            type=IntegrationType.WEBHOOK,
            endpoint="https://api.example.com/webhook1",
        )

        config2 = IntegrationConfig(
            id="int2",
            name="Slack",
            type=IntegrationType.SLACK,
            endpoint="https://hooks.slack.com/services/xxx",
        )

        manager.register_integration(config1)
        manager.register_integration(config2)

        integrations = manager.list_integrations()
        self.assertEqual(len(integrations), 2)

    def test_list_integrations_by_type(self):
        """Test listing integrations filtered by type."""
        manager = create_enterprise_integration(self.test_dir)

        config1 = IntegrationConfig(
            id="int1",
            name="Webhook",
            type=IntegrationType.WEBHOOK,
            endpoint="https://api.example.com/webhook",
        )

        config2 = IntegrationConfig(
            id="int2",
            name="Slack",
            type=IntegrationType.SLACK,
            endpoint="https://hooks.slack.com/services/xxx",
        )

        manager.register_integration(config1)
        manager.register_integration(config2)

        webhooks = manager.list_integrations(type=IntegrationType.WEBHOOK)
        self.assertEqual(len(webhooks), 1)
        self.assertEqual(webhooks[0].type, IntegrationType.WEBHOOK)

    def test_list_integrations_enabled_only(self):
        """Test listing only enabled integrations."""
        manager = create_enterprise_integration(self.test_dir)

        config1 = IntegrationConfig(
            id="int1",
            name="Enabled",
            type=IntegrationType.WEBHOOK,
            endpoint="https://api.example.com/webhook",
            enabled=True,
        )

        config2 = IntegrationConfig(
            id="int2",
            name="Disabled",
            type=IntegrationType.WEBHOOK,
            endpoint="https://api.example.com/webhook",
            enabled=False,
        )

        manager.register_integration(config1)
        manager.register_integration(config2)

        enabled = manager.list_integrations(enabled_only=True)
        self.assertEqual(len(enabled), 1)
        self.assertEqual(enabled[0].name, "Enabled")

    def test_create_connector(self):
        """Test creating connector for integration."""
        manager = create_enterprise_integration(self.test_dir)

        config = IntegrationConfig(
            id="int1",
            name="Webhook",
            type=IntegrationType.WEBHOOK,
            endpoint="https://api.example.com/webhook",
        )

        connector = manager.create_connector(config)

        self.assertIsInstance(connector, WebhookConnector)

    def test_connect_integration(self):
        """Test connecting to an integration."""
        manager = create_enterprise_integration(self.test_dir)

        config = IntegrationConfig(
            id="int1",
            name="Webhook",
            type=IntegrationType.WEBHOOK,
            endpoint="https://api.example.com/webhook",
        )

        manager.register_integration(config)
        result = manager.connect("int1")

        self.assertTrue(result)
        self.assertIn("int1", manager.connectors)

    def test_disconnect_integration(self):
        """Test disconnecting from an integration."""
        manager = create_enterprise_integration(self.test_dir)

        config = IntegrationConfig(
            id="int1",
            name="Webhook",
            type=IntegrationType.WEBHOOK,
            endpoint="https://api.example.com/webhook",
        )

        manager.register_integration(config)
        manager.connect("int1")
        manager.disconnect("int1")

        self.assertNotIn("int1", manager.connectors)

    def test_audit_logging(self):
        """Test audit log generation."""
        manager = create_enterprise_integration(self.test_dir)

        config = IntegrationConfig(
            id="int1",
            name="Webhook",
            type=IntegrationType.WEBHOOK,
            endpoint="https://api.example.com/webhook",
        )

        manager.register_integration(config)
        manager.connect("int1")

        # Check audit log was created
        logs = manager.get_audit_logs()
        self.assertGreater(len(logs), 0)

        connect_logs = manager.get_audit_logs(action="connect")
        self.assertEqual(len(connect_logs), 1)

    def test_get_audit_logs_by_integration(self):
        """Test filtering audit logs by integration."""
        manager = create_enterprise_integration(self.test_dir)

        config1 = IntegrationConfig(
            id="int1",
            name="Webhook 1",
            type=IntegrationType.WEBHOOK,
            endpoint="https://api.example.com/webhook1",
        )

        config2 = IntegrationConfig(
            id="int2",
            name="Webhook 2",
            type=IntegrationType.WEBHOOK,
            endpoint="https://api.example.com/webhook2",
        )

        manager.register_integration(config1)
        manager.register_integration(config2)

        manager.connect("int1")
        manager.connect("int2")

        logs1 = manager.get_audit_logs(integration_id="int1")
        self.assertEqual(len(logs1), 1)
        self.assertEqual(logs1[0].integration_id, "int1")

    def test_integration_persistence(self):
        """Test saving integration to disk."""
        manager = create_enterprise_integration(self.test_dir)

        config = IntegrationConfig(
            id="int1",
            name="Test Webhook",
            type=IntegrationType.WEBHOOK,
            endpoint="https://api.example.com/webhook",
            tags=["production"],
        )

        manager.register_integration(config)

        # Check file exists
        int_file = self.test_dir / "int_int1.json"
        self.assertTrue(int_file.exists())

    def test_audit_log_persistence(self):
        """Test saving audit log to disk."""
        manager = create_enterprise_integration(self.test_dir)

        config = IntegrationConfig(
            id="int1",
            name="Webhook",
            type=IntegrationType.WEBHOOK,
            endpoint="https://api.example.com/webhook",
        )

        manager.register_integration(config)
        manager.connect("int1")

        # Check audit log file exists
        audit_files = list(self.test_dir.glob("audit_*.json"))
        self.assertGreater(len(audit_files), 0)


if __name__ == "__main__":
    unittest.main()
