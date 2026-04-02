"""
Enterprise system integration framework.

Provides:
- Integration connectors for common enterprise systems
- Webhook support for external triggers
- API abstraction layer
- Audit logging and compliance
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4


class IntegrationType(str, Enum):
    """Type of enterprise integration."""

    WEBHOOK = "webhook"
    DATABASE = "database"
    API = "api"
    MESSAGE_QUEUE = "message_queue"
    FILE_SYSTEM = "file_system"
    EMAIL = "email"
    SLACK = "slack"
    CUSTOM = "custom"


@dataclass
class IntegrationConfig:
    """Configuration for an integration."""

    id: str
    name: str
    type: IntegrationType
    endpoint: str
    credentials: dict[str, str] = field(default_factory=dict)
    params: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    tags: list[str] = field(default_factory=list)


@dataclass
class IntegrationEvent:
    """Event from an integration."""

    event_id: str
    integration_id: str
    event_type: str
    payload: dict[str, Any]
    timestamp: datetime
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_id": self.event_id,
            "integration_id": self.integration_id,
            "event_type": self.event_type,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class AuditLog:
    """Audit log entry."""

    log_id: str
    timestamp: datetime
    integration_id: str
    action: str
    user: str | None
    resource: str
    details: dict[str, Any]
    result: str  # "success", "failure", "denied"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "log_id": self.log_id,
            "timestamp": self.timestamp.isoformat(),
            "integration_id": self.integration_id,
            "action": self.action,
            "user": self.user,
            "resource": self.resource,
            "details": self.details,
            "result": self.result,
        }


class IntegrationConnector(ABC):
    """Abstract base class for integration connectors."""

    def __init__(self, config: IntegrationConfig):
        """Initialize connector with configuration."""
        self.config = config

    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to the integration."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from the integration."""
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """Test the connection."""
        pass

    @abstractmethod
    def send(self, data: dict[str, Any]) -> bool:
        """Send data to the integration."""
        pass

    @abstractmethod
    def receive(self) -> list[IntegrationEvent]:
        """Receive events from the integration."""
        pass


class WebhookConnector(IntegrationConnector):
    """Webhook integration connector."""

    def connect(self) -> bool:
        """Webhooks don't require persistent connections."""
        return True

    def disconnect(self) -> None:
        """Webhooks don't require disconnection."""
        pass

    def test_connection(self) -> bool:
        """Test webhook endpoint accessibility."""
        # Simplified - in production, would make HTTP request
        return self.config.endpoint.startswith("http")

    def send(self, data: dict[str, Any]) -> bool:
        """Send data via webhook POST."""
        # Simplified - in production, would use httpx/requests
        import urllib.request

        try:
            req = urllib.request.Request(
                self.config.endpoint,
                data=json.dumps(data).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                return response.status == 200
        except Exception:
            return False

    def receive(self) -> list[IntegrationEvent]:
        """Webhooks are push-based, not pull-based."""
        return []


class SlackConnector(IntegrationConnector):
    """Slack integration connector."""

    def connect(self) -> bool:
        """Slack uses webhook URLs, no persistent connection needed."""
        return "slack.com" in self.config.endpoint

    def disconnect(self) -> None:
        """No disconnection needed."""
        pass

    def test_connection(self) -> bool:
        """Test Slack webhook."""
        return self.connect()

    def send(self, data: dict[str, Any]) -> bool:
        """Send message to Slack."""
        import urllib.request

        try:
            payload = {"text": data.get("message", str(data))}
            req = urllib.request.Request(
                self.config.endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                return response.status == 200
        except Exception:
            return False

    def receive(self) -> list[IntegrationEvent]:
        """Slack integration is push-based."""
        return []


class EnterpriseIntegration:
    """Manage enterprise integrations."""

    def __init__(self, storage_dir: Path | None = None):
        """
        Initialize integration manager.

        Args:
            storage_dir: Directory for persistence
        """
        self.storage_dir = storage_dir or Path.home() / ".claude" / "integrations"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.integrations: dict[str, IntegrationConfig] = {}
        self.connectors: dict[str, IntegrationConnector] = {}
        self.audit_logs: list[AuditLog] = []

    def register_integration(self, config: IntegrationConfig) -> None:
        """Register an integration."""
        self.integrations[config.id] = config
        self._save_integration(config)

    def get_integration(self, integration_id: str) -> IntegrationConfig | None:
        """Get an integration by ID."""
        return self.integrations.get(integration_id)

    def list_integrations(
        self,
        type: IntegrationType | None = None,
        enabled_only: bool = False,
    ) -> list[IntegrationConfig]:
        """
        List integrations with optional filters.

        Args:
            type: Filter by type
            enabled_only: Only return enabled integrations

        Returns:
            List of integrations
        """
        results = list(self.integrations.values())

        if type:
            results = [i for i in results if i.type == type]

        if enabled_only:
            results = [i for i in results if i.enabled]

        return results

    def create_connector(self, config: IntegrationConfig) -> IntegrationConnector:
        """Create connector for integration."""
        if config.type == IntegrationType.WEBHOOK:
            return WebhookConnector(config)
        elif config.type == IntegrationType.SLACK:
            return SlackConnector(config)
        else:
            raise ValueError(f"Unsupported integration type: {config.type}")

    def connect(self, integration_id: str) -> bool:
        """Connect to an integration."""
        config = self.integrations.get(integration_id)
        if not config:
            return False

        connector = self.create_connector(config)
        success = connector.connect()

        if success:
            self.connectors[integration_id] = connector
            self._log_audit(
                integration_id,
                "connect",
                resource=f"integration:{integration_id}",
                details={"endpoint": config.endpoint},
                result="success",
            )

        return success

    def disconnect(self, integration_id: str) -> None:
        """Disconnect from an integration."""
        connector = self.connectors.get(integration_id)
        if connector:
            connector.disconnect()
            del self.connectors[integration_id]
            self._log_audit(
                integration_id,
                "disconnect",
                resource=f"integration:{integration_id}",
                details={},
                result="success",
            )

    def send_data(
        self,
        integration_id: str,
        data: dict[str, Any],
    ) -> bool:
        """Send data to an integration."""
        connector = self.connectors.get(integration_id)
        if not connector:
            return False

        success = connector.send(data)

        self._log_audit(
            integration_id,
            "send",
            resource=f"integration:{integration_id}",
            details={"data_keys": list(data.keys())},
            result="success" if success else "failure",
        )

        return success

    def receive_events(self, integration_id: str) -> list[IntegrationEvent]:
        """Receive events from an integration."""
        connector = self.connectors.get(integration_id)
        if not connector:
            return []

        events = connector.receive()

        for event in events:
            self._log_audit(
                integration_id,
                "receive",
                resource=f"event:{event.event_id}",
                details={"event_type": event.event_type},
                result="success",
            )

        return events

    def _log_audit(
        self,
        integration_id: str,
        action: str,
        resource: str,
        details: dict[str, Any],
        result: str,
        user: str | None = None,
    ) -> None:
        """Create audit log entry."""
        log = AuditLog(
            log_id=str(uuid4()),
            timestamp=datetime.now(),
            integration_id=integration_id,
            action=action,
            user=user,
            resource=resource,
            details=details,
            result=result,
        )

        self.audit_logs.append(log)
        self._save_audit_log(log)

    def get_audit_logs(
        self,
        integration_id: str | None = None,
        action: str | None = None,
        limit: int = 100,
    ) -> list[AuditLog]:
        """
        Get audit logs with optional filters.

        Args:
            integration_id: Filter by integration
            action: Filter by action
            limit: Maximum results

        Returns:
            List of audit logs
        """
        results = self.audit_logs

        if integration_id:
            results = [l for l in results if l.integration_id == integration_id]

        if action:
            results = [l for l in results if l.action == action]

        # Sort by timestamp descending
        results.sort(key=lambda l: l.timestamp, reverse=True)

        return results[:limit]

    def _save_integration(self, config: IntegrationConfig) -> None:
        """Save integration to disk."""
        int_file = self.storage_dir / f"int_{config.id}.json"
        data = {
            "id": config.id,
            "name": config.name,
            "type": config.type.value,
            "endpoint": config.endpoint,
            "credentials": config.credentials,
            "params": config.params,
            "enabled": config.enabled,
            "tags": config.tags,
        }
        int_file.write_text(json.dumps(data, indent=2))

    def _save_audit_log(self, log: AuditLog) -> None:
        """Save audit log to disk."""
        log_file = self.storage_dir / f"audit_{log.log_id}.json"
        log_file.write_text(json.dumps(log.to_dict(), indent=2))


def create_enterprise_integration(storage_dir: Path | None = None) -> EnterpriseIntegration:
    """Create an enterprise integration manager."""
    return EnterpriseIntegration(storage_dir)
