"""
Unified alerting configuration for GRAVITEA ERP.

Implements SC-021, SC-022, SC-023 requirements:
- SC-021: 100% of fiscal service failures generate alerts within 1 minute
- SC-022: 100% of sync failures logged with sufficient context for debugging
- SC-023: Security events (failed auth, IDOR attempts) generate real-time alerts

Usage:
    from apps.core.observability import fiscal_alert, sync_alert, security_alert

    # Fiscal failure alert (SC-021)
    fiscal_alert(
        service="afip",
        operation="invoice_emission",
        error="Connection timeout",
        tenant_id=tenant.id,
        context={"cae_request_id": "123", "retry_count": 3}
    )

    # Sync failure alert (SC-022)
    sync_alert(
        operation="push",
        branch_id=branch.id,
        error="Conflict resolution failed",
        context={"conflict_type": "price_update", "records_affected": 5}
    )

    # Security event alert (SC-023)
    security_alert(
        event_type="failed_auth",
        ip_address="192.168.1.100",
        user_identifier="john@example.com",
        context={"attempts": 5, "lockout_triggered": True}
    )
"""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
from uuid import uuid4

from django.conf import settings
from django.utils import timezone


class AlertLevel(str, Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertType(str, Enum):
    """Alert categories per SC-021, SC-022, SC-023."""

    FISCAL = "fiscal"  # SC-021: Fiscal service failures
    SYNC = "sync"  # SC-022: Sync failures
    SECURITY = "security"  # SC-023: Security events
    SYSTEM = "system"  # General system alerts


@dataclass
class Alert:
    """Alert data structure for consistent handling."""

    id: str = field(default_factory=lambda: str(uuid4()))
    alert_type: AlertType = AlertType.SYSTEM
    level: AlertLevel = AlertLevel.INFO
    message: str = ""
    source: str = ""
    tenant_id: Optional[str] = None
    branch_id: Optional[str] = None
    user_id: Optional[str] = None
    context: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=timezone.now)
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert alert to dictionary for logging/serialization."""
        return {
            "id": self.id,
            "alert_type": self.alert_type.value,
            "level": self.level.value,
            "message": self.message,
            "source": self.source,
            "tenant_id": self.tenant_id,
            "branch_id": self.branch_id,
            "user_id": self.user_id,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
            "acknowledged": self.acknowledged,
            "acknowledged_at": (
                self.acknowledged_at.isoformat() if self.acknowledged_at else None
            ),
            "acknowledged_by": self.acknowledged_by,
        }

    def to_json(self) -> str:
        """Convert alert to JSON string."""
        return json.dumps(self.to_dict(), default=str)


class AlertHandler:
    """Base class for alert handlers."""

    def handle(self, alert: Alert) -> bool:
        """
        Handle an alert. Return True if handled successfully.

        Subclasses should override this method.
        """
        raise NotImplementedError


class LoggingAlertHandler(AlertHandler):
    """Handler that logs alerts to Python logging system."""

    def __init__(self):
        self.loggers = {
            AlertType.FISCAL: logging.getLogger("fiscal"),
            AlertType.SYNC: logging.getLogger("sync"),
            AlertType.SECURITY: logging.getLogger("security"),
            AlertType.SYSTEM: logging.getLogger("apps"),
        }
        self.level_map = {
            AlertLevel.INFO: logging.INFO,
            AlertLevel.WARNING: logging.WARNING,
            AlertLevel.ERROR: logging.ERROR,
            AlertLevel.CRITICAL: logging.CRITICAL,
        }

    def handle(self, alert: Alert) -> bool:
        """Log alert to appropriate logger with structured JSON."""
        logger = self.loggers.get(alert.alert_type, self.loggers[AlertType.SYSTEM])
        level = self.level_map.get(alert.level, logging.INFO)

        # Structured log entry for debugging (SC-022 requirement)
        log_entry = {
            "alert_id": alert.id,
            "type": alert.alert_type.value,
            "level": alert.level.value,
            "message": alert.message,
            "source": alert.source,
            "tenant_id": alert.tenant_id,
            "branch_id": alert.branch_id,
            "user_id": alert.user_id,
            "context": alert.context,
            "timestamp": alert.timestamp.isoformat(),
        }

        logger.log(level, json.dumps(log_entry, default=str))
        return True


class WebhookAlertHandler(AlertHandler):
    """Handler that sends alerts to webhook endpoints."""

    def __init__(self, webhook_url: str, timeout: int = 30):
        self.webhook_url = webhook_url
        self.timeout = timeout

    def handle(self, alert: Alert) -> bool:
        """Send alert to webhook endpoint."""
        if not self.webhook_url:
            return False

        try:
            import requests

            response = requests.post(
                self.webhook_url,
                json=alert.to_dict(),
                timeout=self.timeout,
                headers={"Content-Type": "application/json"},
            )
            return response.status_code < 400
        except Exception as e:
            logging.getLogger("apps").error(
                f"Webhook alert delivery failed: {e}",
                extra={"alert_id": alert.id, "webhook_url": self.webhook_url},
            )
            return False


class InMemoryAlertStore(AlertHandler):
    """
    In-memory alert store for testing and development.

    Production deployments should use persistent storage.
    """

    def __init__(self, max_alerts: int = 1000, retention_hours: int = 24):
        self.max_alerts = max_alerts
        self.retention_hours = retention_hours
        self._alerts: list[Alert] = []
        self._lock = threading.Lock()

    def handle(self, alert: Alert) -> bool:
        """Store alert in memory."""
        with self._lock:
            self._cleanup_old_alerts()
            self._alerts.append(alert)
            if len(self._alerts) > self.max_alerts:
                self._alerts = self._alerts[-self.max_alerts :]
        return True

    def _cleanup_old_alerts(self) -> None:
        """Remove alerts older than retention period."""
        cutoff = timezone.now() - timedelta(hours=self.retention_hours)
        self._alerts = [a for a in self._alerts if a.timestamp > cutoff]

    def get_alerts(
        self,
        alert_type: Optional[AlertType] = None,
        level: Optional[AlertLevel] = None,
        tenant_id: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[Alert]:
        """Query stored alerts with filters."""
        with self._lock:
            filtered = self._alerts.copy()

            if alert_type:
                filtered = [a for a in filtered if a.alert_type == alert_type]
            if level:
                filtered = [a for a in filtered if a.level == level]
            if tenant_id:
                filtered = [a for a in filtered if a.tenant_id == tenant_id]
            if since:
                filtered = [a for a in filtered if a.timestamp >= since]

            return sorted(filtered, key=lambda a: a.timestamp, reverse=True)[:limit]

    def get_alert_by_id(self, alert_id: str) -> Optional[Alert]:
        """Get specific alert by ID."""
        with self._lock:
            for alert in self._alerts:
                if alert.id == alert_id:
                    return alert
        return None

    def acknowledge_alert(
        self, alert_id: str, acknowledged_by: Optional[str] = None
    ) -> bool:
        """Mark alert as acknowledged."""
        with self._lock:
            for alert in self._alerts:
                if alert.id == alert_id:
                    alert.acknowledged = True
                    alert.acknowledged_at = timezone.now()
                    alert.acknowledged_by = acknowledged_by
                    return True
        return False

    def clear(self) -> None:
        """Clear all alerts (for testing)."""
        with self._lock:
            self._alerts.clear()

    def count(
        self,
        alert_type: Optional[AlertType] = None,
        level: Optional[AlertLevel] = None,
    ) -> int:
        """Count alerts matching criteria."""
        return len(self.get_alerts(alert_type=alert_type, level=level, limit=10000))


class AlertManager:
    """
    Central alert management system.

    Coordinates alert handling across multiple handlers with:
    - Rate limiting to prevent alert storms
    - Deduplication of similar alerts
    - Handler chain execution
    - Alert lifecycle management
    """

    def __init__(
        self,
        rate_limit_window: int = 60,  # seconds
        rate_limit_count: int = 100,  # max alerts per window
        dedup_window: int = 300,  # seconds for deduplication
    ):
        self.handlers: list[AlertHandler] = []
        self.rate_limit_window = rate_limit_window
        self.rate_limit_count = rate_limit_count
        self.dedup_window = dedup_window
        self._alert_counts: dict[str, list[float]] = {}
        self._recent_alerts: dict[str, float] = {}
        self._lock = threading.Lock()

        # Default handlers
        self.handlers.append(LoggingAlertHandler())
        self.handlers.append(InMemoryAlertStore())

        # Optional webhook handler from settings
        webhook_url = getattr(settings, "ALERT_WEBHOOK_URL", None)
        if webhook_url:
            self.handlers.append(WebhookAlertHandler(webhook_url))

    def add_handler(self, handler: AlertHandler) -> None:
        """Add an alert handler to the chain."""
        self.handlers.append(handler)

    def remove_handler(self, handler: AlertHandler) -> None:
        """Remove an alert handler from the chain."""
        if handler in self.handlers:
            self.handlers.remove(handler)

    def _get_alert_key(self, alert: Alert) -> str:
        """Generate deduplication key for alert."""
        return f"{alert.alert_type.value}:{alert.source}:{alert.message}:{alert.tenant_id}"

    def _is_rate_limited(self, alert_type: AlertType) -> bool:
        """Check if alerts of this type are rate limited."""
        now = time.time()
        key = alert_type.value

        with self._lock:
            if key not in self._alert_counts:
                self._alert_counts[key] = []

            # Clean old entries
            self._alert_counts[key] = [
                t for t in self._alert_counts[key] if now - t < self.rate_limit_window
            ]

            return len(self._alert_counts[key]) >= self.rate_limit_count

    def _record_alert(self, alert: Alert) -> None:
        """Record alert for rate limiting."""
        now = time.time()
        key = alert.alert_type.value

        with self._lock:
            if key not in self._alert_counts:
                self._alert_counts[key] = []
            self._alert_counts[key].append(now)

    def _is_duplicate(self, alert: Alert) -> bool:
        """Check if this is a duplicate alert within dedup window."""
        now = time.time()
        key = self._get_alert_key(alert)

        with self._lock:
            if key in self._recent_alerts:
                if now - self._recent_alerts[key] < self.dedup_window:
                    return True

            self._recent_alerts[key] = now
            return False

    def send_alert(
        self,
        alert_type: AlertType,
        level: AlertLevel,
        message: str,
        source: str,
        tenant_id: Optional[str] = None,
        branch_id: Optional[str] = None,
        user_id: Optional[str] = None,
        context: Optional[dict] = None,
        skip_dedup: bool = False,
    ) -> Optional[Alert]:
        """
        Send an alert through all handlers.

        Args:
            alert_type: Category of alert (fiscal, sync, security, system)
            level: Severity level
            message: Human-readable alert message
            source: System/component generating the alert
            tenant_id: Associated tenant ID if applicable
            branch_id: Associated branch ID if applicable
            user_id: Associated user ID if applicable
            context: Additional context dictionary for debugging
            skip_dedup: Skip deduplication check

        Returns:
            Alert object if sent, None if rate limited or deduplicated
        """
        alert = Alert(
            alert_type=alert_type,
            level=level,
            message=message,
            source=source,
            tenant_id=tenant_id,
            branch_id=branch_id,
            user_id=user_id,
            context=context or {},
        )

        # Rate limiting check
        if self._is_rate_limited(alert_type):
            logging.getLogger("apps").warning(
                f"Alert rate limited: {alert_type.value}",
                extra={"alert_type": alert_type.value},
            )
            return None

        # Deduplication check
        if not skip_dedup and self._is_duplicate(alert):
            return None

        # Record for rate limiting
        self._record_alert(alert)

        # Send to all handlers
        for handler in self.handlers:
            try:
                handler.handle(alert)
            except Exception as e:
                logging.getLogger("apps").error(
                    f"Alert handler failed: {handler.__class__.__name__}: {e}",
                    extra={"alert_id": alert.id},
                )

        return alert

    def get_store(self) -> Optional[InMemoryAlertStore]:
        """Get the in-memory alert store if configured."""
        for handler in self.handlers:
            if isinstance(handler, InMemoryAlertStore):
                return handler
        return None


# Global alert manager instance
_alert_manager: Optional[AlertManager] = None
_manager_lock = threading.Lock()


def get_alert_manager() -> AlertManager:
    """Get or create the global alert manager instance."""
    global _alert_manager
    with _manager_lock:
        if _alert_manager is None:
            _alert_manager = AlertManager()
    return _alert_manager


# Convenience functions for specific alert types


def fiscal_alert(
    service: str,
    operation: str,
    error: str,
    tenant_id: Optional[str] = None,
    branch_id: Optional[str] = None,
    context: Optional[dict] = None,
    level: AlertLevel = AlertLevel.ERROR,
) -> Optional[Alert]:
    """
    Send a fiscal service failure alert (SC-021).

    Must generate alert within 1 minute of occurrence.

    Args:
        service: Fiscal service name (e.g., "afip", "arca")
        operation: Operation that failed (e.g., "invoice_emission", "cae_request")
        error: Error message/description
        tenant_id: Tenant ID
        branch_id: Branch ID if applicable
        context: Additional context (cae_request_id, retry_count, etc.)
        level: Alert severity (default: ERROR)

    Returns:
        Alert object if sent
    """
    manager = get_alert_manager()
    full_context = {
        "service": service,
        "operation": operation,
        "error_detail": error,
        **(context or {}),
    }

    return manager.send_alert(
        alert_type=AlertType.FISCAL,
        level=level,
        message=f"Fiscal service failure: {service}/{operation} - {error}",
        source=f"fiscal.{service}",
        tenant_id=tenant_id,
        branch_id=branch_id,
        context=full_context,
    )


def sync_alert(
    operation: str,
    branch_id: str,
    error: str,
    tenant_id: Optional[str] = None,
    context: Optional[dict] = None,
    level: AlertLevel = AlertLevel.WARNING,
) -> Optional[Alert]:
    """
    Send a sync failure alert with debug context (SC-022).

    Context should include sufficient information for debugging:
    - conflict_type, records_affected, sync_batch_id, etc.

    Args:
        operation: Sync operation (e.g., "push", "pull", "conflict_resolution")
        branch_id: Branch ID involved in sync
        error: Error message/description
        tenant_id: Tenant ID
        context: Debug context (conflict details, affected records, etc.)
        level: Alert severity (default: WARNING)

    Returns:
        Alert object if sent
    """
    manager = get_alert_manager()
    full_context = {
        "operation": operation,
        "error_detail": error,
        **(context or {}),
    }

    return manager.send_alert(
        alert_type=AlertType.SYNC,
        level=level,
        message=f"Sync failure: {operation} for branch {branch_id} - {error}",
        source=f"sync.{operation}",
        tenant_id=tenant_id,
        branch_id=branch_id,
        context=full_context,
    )


def security_alert(
    event_type: str,
    ip_address: Optional[str] = None,
    user_identifier: Optional[str] = None,
    tenant_id: Optional[str] = None,
    user_id: Optional[str] = None,
    context: Optional[dict] = None,
    level: AlertLevel = AlertLevel.WARNING,
) -> Optional[Alert]:
    """
    Send a security event alert in real-time (SC-023).

    Event types include:
    - failed_auth: Failed authentication attempt
    - idor_attempt: IDOR (Insecure Direct Object Reference) attempt
    - rate_limit_exceeded: Too many requests
    - suspicious_activity: General suspicious behavior
    - permission_violation: Unauthorized access attempt

    Args:
        event_type: Type of security event
        ip_address: Source IP address
        user_identifier: Username/email attempted
        tenant_id: Tenant ID if applicable
        user_id: User ID if known
        context: Additional context (attempts count, lockout status, etc.)
        level: Alert severity (default: WARNING)

    Returns:
        Alert object if sent
    """
    manager = get_alert_manager()
    full_context = {
        "event_type": event_type,
        "ip_address": ip_address,
        "user_identifier": user_identifier,
        **(context or {}),
    }

    # Escalate to CRITICAL for certain events
    if event_type in ("idor_attempt", "permission_violation"):
        level = AlertLevel.CRITICAL

    message_parts = [f"Security event: {event_type}"]
    if ip_address:
        message_parts.append(f"from {ip_address}")
    if user_identifier:
        message_parts.append(f"for {user_identifier}")

    return manager.send_alert(
        alert_type=AlertType.SECURITY,
        level=level,
        message=" ".join(message_parts),
        source=f"security.{event_type}",
        tenant_id=tenant_id,
        user_id=user_id,
        context=full_context,
        skip_dedup=True,  # Security alerts should never be deduplicated
    )


def system_alert(
    component: str,
    message: str,
    tenant_id: Optional[str] = None,
    context: Optional[dict] = None,
    level: AlertLevel = AlertLevel.INFO,
) -> Optional[Alert]:
    """
    Send a general system alert.

    Args:
        component: System component name
        message: Alert message
        tenant_id: Tenant ID if applicable
        context: Additional context
        level: Alert severity (default: INFO)

    Returns:
        Alert object if sent
    """
    manager = get_alert_manager()
    return manager.send_alert(
        alert_type=AlertType.SYSTEM,
        level=level,
        message=message,
        source=f"system.{component}",
        tenant_id=tenant_id,
        context=context or {},
    )
