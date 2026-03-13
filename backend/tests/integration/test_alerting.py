"""
Integration tests for alerting system.

Tests verify SC-021, SC-022, SC-023 requirements:
- SC-021: Fiscal service failure alerts within 1 minute
- SC-022: Sync failure logging with debug context
- SC-023: Security event real-time alerts
"""

import json
import threading
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from apps.core.observability.alerts import (
    Alert,
    AlertLevel,
    AlertManager,
    AlertType,
    InMemoryAlertStore,
    LoggingAlertHandler,
    fiscal_alert,
    get_alert_manager,
    security_alert,
    sync_alert,
    system_alert,
)
from apps.core.observability.uptime import (
    ComponentStatus,
    DatabaseHealthCheck,
    HealthStatus,
    UptimeMonitor,
)


class TestAlertDataStructure(TestCase):
    """Test Alert data structure."""

    def test_alert_creation_with_defaults(self):
        """Test alert created with default values."""
        alert = Alert()
        self.assertIsNotNone(alert.id)
        self.assertEqual(alert.alert_type, AlertType.SYSTEM)
        self.assertEqual(alert.level, AlertLevel.INFO)
        self.assertFalse(alert.acknowledged)
        self.assertIsNotNone(alert.timestamp)

    def test_alert_creation_with_values(self):
        """Test alert created with specified values."""
        alert = Alert(
            alert_type=AlertType.FISCAL,
            level=AlertLevel.CRITICAL,
            message="Test fiscal alert",
            source="fiscal.afip",
            tenant_id=1,
            branch_id=2,
            context={"cae_request_id": "123"},
        )
        self.assertEqual(alert.alert_type, AlertType.FISCAL)
        self.assertEqual(alert.level, AlertLevel.CRITICAL)
        self.assertEqual(alert.message, "Test fiscal alert")
        self.assertEqual(alert.tenant_id, 1)
        self.assertEqual(alert.context["cae_request_id"], "123")

    def test_alert_to_dict(self):
        """Test alert serialization to dictionary."""
        alert = Alert(
            alert_type=AlertType.SECURITY,
            level=AlertLevel.WARNING,
            message="Security event",
            source="security.auth",
        )
        data = alert.to_dict()
        self.assertEqual(data["alert_type"], "security")
        self.assertEqual(data["level"], "warning")
        self.assertEqual(data["message"], "Security event")
        self.assertIn("timestamp", data)

    def test_alert_to_json(self):
        """Test alert serialization to JSON."""
        alert = Alert(message="Test alert")
        json_str = alert.to_json()
        data = json.loads(json_str)
        self.assertEqual(data["message"], "Test alert")


class TestLoggingAlertHandler(TestCase):
    """Test LoggingAlertHandler."""

    def test_handler_logs_to_correct_logger(self):
        """Test alerts are logged to appropriate loggers."""
        handler = LoggingAlertHandler()

        with patch.object(handler.loggers[AlertType.FISCAL], "log") as mock_log:
            alert = Alert(alert_type=AlertType.FISCAL, level=AlertLevel.ERROR)
            handler.handle(alert)
            mock_log.assert_called_once()

        with patch.object(handler.loggers[AlertType.SYNC], "log") as mock_log:
            alert = Alert(alert_type=AlertType.SYNC, level=AlertLevel.WARNING)
            handler.handle(alert)
            mock_log.assert_called_once()

        with patch.object(handler.loggers[AlertType.SECURITY], "log") as mock_log:
            alert = Alert(alert_type=AlertType.SECURITY, level=AlertLevel.CRITICAL)
            handler.handle(alert)
            mock_log.assert_called_once()

    def test_handler_uses_correct_log_level(self):
        """Test alerts use appropriate logging levels."""
        from unittest.mock import ANY
        handler = LoggingAlertHandler()

        # Test ERROR level
        with patch.object(handler.loggers[AlertType.SYSTEM], "log") as mock_log:
            alert = Alert(alert_type=AlertType.SYSTEM, level=AlertLevel.ERROR)
            handler.handle(alert)
            mock_log.assert_called_with(40, ANY)  # 40 = ERROR


class TestInMemoryAlertStore(TestCase):
    """Test InMemoryAlertStore."""

    def setUp(self):
        self.store = InMemoryAlertStore(max_alerts=100, retention_hours=1)

    def test_store_alert(self):
        """Test storing alerts."""
        alert = Alert(message="Test alert")
        result = self.store.handle(alert)
        self.assertTrue(result)
        self.assertEqual(self.store.count(), 1)

    def test_get_alerts(self):
        """Test retrieving alerts."""
        for i in range(5):
            self.store.handle(Alert(message=f"Alert {i}"))

        alerts = self.store.get_alerts()
        self.assertEqual(len(alerts), 5)

    def test_filter_by_type(self):
        """Test filtering alerts by type."""
        self.store.handle(Alert(alert_type=AlertType.FISCAL))
        self.store.handle(Alert(alert_type=AlertType.SYNC))
        self.store.handle(Alert(alert_type=AlertType.FISCAL))

        fiscal_alerts = self.store.get_alerts(alert_type=AlertType.FISCAL)
        self.assertEqual(len(fiscal_alerts), 2)

    def test_filter_by_level(self):
        """Test filtering alerts by level."""
        self.store.handle(Alert(level=AlertLevel.ERROR))
        self.store.handle(Alert(level=AlertLevel.WARNING))
        self.store.handle(Alert(level=AlertLevel.ERROR))

        error_alerts = self.store.get_alerts(level=AlertLevel.ERROR)
        self.assertEqual(len(error_alerts), 2)

    def test_filter_by_tenant(self):
        """Test filtering alerts by tenant."""
        self.store.handle(Alert(tenant_id=1))
        self.store.handle(Alert(tenant_id=2))
        self.store.handle(Alert(tenant_id=1))

        tenant_alerts = self.store.get_alerts(tenant_id=1)
        self.assertEqual(len(tenant_alerts), 2)

    def test_max_alerts_limit(self):
        """Test max alerts limit enforced."""
        store = InMemoryAlertStore(max_alerts=10)
        for i in range(20):
            store.handle(Alert(message=f"Alert {i}"))

        self.assertEqual(store.count(), 10)

    def test_acknowledge_alert(self):
        """Test acknowledging alerts."""
        alert = Alert()
        self.store.handle(alert)

        result = self.store.acknowledge_alert(alert.id, acknowledged_by=1)
        self.assertTrue(result)

        stored = self.store.get_alert_by_id(alert.id)
        self.assertTrue(stored.acknowledged)
        self.assertEqual(stored.acknowledged_by, 1)

    def test_clear_store(self):
        """Test clearing all alerts."""
        for i in range(5):
            self.store.handle(Alert())

        self.store.clear()
        self.assertEqual(self.store.count(), 0)


class TestAlertManager(TestCase):
    """Test AlertManager."""

    def setUp(self):
        self.manager = AlertManager(
            rate_limit_window=60,
            rate_limit_count=10,
            dedup_window=30,
        )

    def test_send_alert(self):
        """Test sending alerts through manager."""
        alert = self.manager.send_alert(
            alert_type=AlertType.SYSTEM,
            level=AlertLevel.INFO,
            message="Test alert",
            source="test",
        )
        self.assertIsNotNone(alert)
        self.assertEqual(alert.message, "Test alert")

    def test_rate_limiting(self):
        """Test rate limiting prevents alert storms."""
        manager = AlertManager(rate_limit_window=60, rate_limit_count=5)

        # First 5 should succeed
        for i in range(5):
            alert = manager.send_alert(
                alert_type=AlertType.SYSTEM,
                level=AlertLevel.INFO,
                message=f"Alert {i}",
                source="test",
                skip_dedup=True,
            )
            self.assertIsNotNone(alert)

        # 6th should be rate limited
        alert = manager.send_alert(
            alert_type=AlertType.SYSTEM,
            level=AlertLevel.INFO,
            message="Rate limited alert",
            source="test",
            skip_dedup=True,
        )
        self.assertIsNone(alert)

    def test_deduplication(self):
        """Test duplicate alerts are suppressed."""
        # First alert should succeed
        alert1 = self.manager.send_alert(
            alert_type=AlertType.FISCAL,
            level=AlertLevel.ERROR,
            message="Duplicate test",
            source="test",
            tenant_id=1,
        )
        self.assertIsNotNone(alert1)

        # Duplicate should be suppressed
        alert2 = self.manager.send_alert(
            alert_type=AlertType.FISCAL,
            level=AlertLevel.ERROR,
            message="Duplicate test",
            source="test",
            tenant_id=1,
        )
        self.assertIsNone(alert2)

    def test_skip_dedup_flag(self):
        """Test skip_dedup allows duplicate alerts."""
        alert1 = self.manager.send_alert(
            alert_type=AlertType.SECURITY,
            level=AlertLevel.WARNING,
            message="Security event",
            source="test",
            skip_dedup=True,
        )
        self.assertIsNotNone(alert1)

        alert2 = self.manager.send_alert(
            alert_type=AlertType.SECURITY,
            level=AlertLevel.WARNING,
            message="Security event",
            source="test",
            skip_dedup=True,
        )
        self.assertIsNotNone(alert2)

    def test_get_store(self):
        """Test getting in-memory store."""
        store = self.manager.get_store()
        self.assertIsNotNone(store)
        self.assertIsInstance(store, InMemoryAlertStore)


class TestFiscalAlertSC021(TestCase):
    """
    Test fiscal alerts per SC-021.

    SC-021: 100% of fiscal service failures generate alerts within 1 minute.
    """

    def setUp(self):
        # Reset global manager for clean tests
        import apps.core.observability.alerts as alerts_module

        alerts_module._alert_manager = None

    def test_fiscal_alert_generation(self):
        """Test fiscal alerts are generated correctly."""
        start_time = timezone.now()

        alert = fiscal_alert(
            service="afip",
            operation="invoice_emission",
            error="Connection timeout",
            tenant_id=1,
            context={"cae_request_id": "123", "retry_count": 3},
        )

        self.assertIsNotNone(alert)
        self.assertEqual(alert.alert_type, AlertType.FISCAL)
        self.assertEqual(alert.level, AlertLevel.ERROR)
        self.assertIn("afip", alert.message)
        self.assertIn("invoice_emission", alert.message)

        # Verify alert generated within 1 minute (SC-021)
        elapsed = alert.timestamp - start_time
        self.assertLess(elapsed, timedelta(minutes=1))

    def test_fiscal_alert_context_preservation(self):
        """Test fiscal alert context is preserved for debugging."""
        alert = fiscal_alert(
            service="arca",
            operation="cae_request",
            error="Invalid certificate",
            tenant_id=2,
            branch_id=5,
            context={
                "certificate_expiry": "2025-01-01",
                "environment": "production",
            },
        )

        self.assertIn("service", alert.context)
        self.assertIn("operation", alert.context)
        self.assertIn("certificate_expiry", alert.context)
        self.assertEqual(alert.context["environment"], "production")

    def test_fiscal_alert_custom_level(self):
        """Test fiscal alerts can use custom severity."""
        alert = fiscal_alert(
            service="afip",
            operation="status_check",
            error="Service degraded",
            level=AlertLevel.WARNING,
        )

        self.assertEqual(alert.level, AlertLevel.WARNING)


class TestSyncAlertSC022(TestCase):
    """
    Test sync alerts per SC-022.

    SC-022: 100% of sync failures logged with sufficient context for debugging.
    """

    def setUp(self):
        import apps.core.observability.alerts as alerts_module

        alerts_module._alert_manager = None

    def test_sync_alert_generation(self):
        """Test sync alerts are generated correctly."""
        alert = sync_alert(
            operation="push",
            branch_id=10,
            error="Conflict resolution failed",
            tenant_id=1,
            context={
                "conflict_type": "price_update",
                "records_affected": 5,
                "sync_batch_id": "batch-123",
            },
        )

        self.assertIsNotNone(alert)
        self.assertEqual(alert.alert_type, AlertType.SYNC)
        self.assertEqual(alert.level, AlertLevel.WARNING)
        self.assertIn("push", alert.message)
        self.assertIn("10", alert.message)

    def test_sync_alert_debug_context(self):
        """Test sync alert includes sufficient debug context (SC-022)."""
        context = {
            "conflict_type": "inventory_adjustment",
            "records_affected": 3,
            "sync_batch_id": "batch-456",
            "offline_duration_hours": 12,
            "local_version": 5,
            "server_version": 7,
        }

        alert = sync_alert(
            operation="conflict_resolution",
            branch_id=20,
            error="Version conflict detected",
            context=context,
        )

        # Verify all debug context is preserved
        for key in context:
            self.assertIn(key, alert.context)

        # Verify operation info is also in context
        self.assertIn("operation", alert.context)
        self.assertIn("error_detail", alert.context)

    def test_sync_alert_branch_tracking(self):
        """Test sync alerts track branch information."""
        alert = sync_alert(
            operation="pull",
            branch_id=15,
            error="Network timeout",
            tenant_id=3,
        )

        self.assertEqual(alert.branch_id, 15)
        self.assertEqual(alert.tenant_id, 3)


class TestSecurityAlertSC023(TestCase):
    """
    Test security alerts per SC-023.

    SC-023: Security events (failed auth, IDOR attempts) generate real-time alerts.
    """

    def setUp(self):
        import apps.core.observability.alerts as alerts_module

        alerts_module._alert_manager = None

    def test_failed_auth_alert(self):
        """Test failed authentication alerts."""
        alert = security_alert(
            event_type="failed_auth",
            ip_address="192.168.1.100",
            user_identifier="john@example.com",
            context={"attempts": 5, "lockout_triggered": True},
        )

        self.assertIsNotNone(alert)
        self.assertEqual(alert.alert_type, AlertType.SECURITY)
        self.assertIn("failed_auth", alert.message)
        self.assertIn("192.168.1.100", alert.message)
        self.assertEqual(alert.context["attempts"], 5)

    def test_idor_attempt_alert_escalation(self):
        """Test IDOR attempts escalate to CRITICAL level."""
        alert = security_alert(
            event_type="idor_attempt",
            ip_address="10.0.0.50",
            user_identifier="attacker@example.com",
            tenant_id=1,
            user_id=99,
            context={
                "attempted_tenant_id": 2,
                "resource_type": "product",
                "resource_id": 12345,
            },
        )

        self.assertEqual(alert.level, AlertLevel.CRITICAL)
        self.assertIn("idor_attempt", alert.context["event_type"])

    def test_permission_violation_escalation(self):
        """Test permission violations escalate to CRITICAL."""
        alert = security_alert(
            event_type="permission_violation",
            user_id=100,
            context={"attempted_action": "delete_all_products"},
        )

        self.assertEqual(alert.level, AlertLevel.CRITICAL)

    def test_security_alerts_not_deduplicated(self):
        """Test security alerts are never deduplicated (skip_dedup=True)."""
        # Send same security event twice
        alert1 = security_alert(
            event_type="failed_auth",
            ip_address="10.0.0.1",
            user_identifier="test@example.com",
        )
        alert2 = security_alert(
            event_type="failed_auth",
            ip_address="10.0.0.1",
            user_identifier="test@example.com",
        )

        # Both should succeed (not deduplicated)
        self.assertIsNotNone(alert1)
        self.assertIsNotNone(alert2)
        self.assertNotEqual(alert1.id, alert2.id)

    def test_rate_limit_exceeded_alert(self):
        """Test rate limit exceeded alerts."""
        alert = security_alert(
            event_type="rate_limit_exceeded",
            ip_address="192.168.1.200",
            context={
                "requests_per_minute": 1000,
                "limit": 100,
                "endpoint": "/api/products/",
            },
        )

        self.assertEqual(alert.level, AlertLevel.WARNING)
        self.assertIn("rate_limit_exceeded", alert.context["event_type"])


class TestSystemAlert(TestCase):
    """Test general system alerts."""

    def setUp(self):
        import apps.core.observability.alerts as alerts_module

        alerts_module._alert_manager = None

    def test_system_alert_generation(self):
        """Test system alerts work correctly."""
        alert = system_alert(
            component="database",
            message="Connection pool exhausted",
            context={"active_connections": 100, "max_connections": 100},
        )

        self.assertIsNotNone(alert)
        self.assertEqual(alert.alert_type, AlertType.SYSTEM)
        self.assertIn("database", alert.source)


class TestUptimeMonitorSC014(TestCase):
    """
    Test uptime monitoring per SC-014.

    SC-014: 99.9% uptime for critical sales processing functions.
    """

    def setUp(self):
        import apps.core.observability.uptime as uptime_module

        uptime_module._uptime_monitor = None
        self.monitor = UptimeMonitor()

    def test_uptime_target(self):
        """Test uptime target is 99.9%."""
        self.assertEqual(self.monitor.TARGET_UPTIME, 99.9)

    def test_database_health_check(self):
        """Test database health check."""
        check = DatabaseHealthCheck()
        result = check.check()

        self.assertEqual(result.component, "database")
        self.assertIn(
            result.status,
            [ComponentStatus.HEALTHY, ComponentStatus.DEGRADED, ComponentStatus.UNHEALTHY],
        )
        self.assertIsNotNone(result.latency_ms)

    def test_run_all_checks(self):
        """Test running all health checks."""
        status = self.monitor.run_checks()

        self.assertIsInstance(status, HealthStatus)
        self.assertIn("database", status.components)
        self.assertIsNotNone(status.uptime_percentage)

    def test_health_status_to_dict(self):
        """Test health status serialization."""
        status = self.monitor.get_health()
        data = status.to_dict()

        self.assertIn("status", data)
        self.assertIn("is_healthy", data)
        self.assertIn("uptime_percentage", data)
        self.assertIn("components", data)

    def test_record_manual_check(self):
        """Test recording manual health checks."""
        self.monitor.record_check(
            component="custom_service",
            healthy=True,
            latency_ms=25.5,
        )

        metrics = self.monitor.get_metrics()
        self.assertGreater(metrics["total_checks"], 0)

    def test_metrics_collection(self):
        """Test metrics are collected properly."""
        # Run some checks
        self.monitor.run_checks()
        self.monitor.run_checks()

        metrics = self.monitor.get_metrics()

        self.assertIn("target_uptime", metrics)
        self.assertIn("actual_uptime", metrics)
        self.assertIn("total_checks", metrics)
        self.assertIn("success_rate", metrics)

    def test_sla_check(self):
        """Test SLA compliance check."""
        # Initially should meet SLA (100% if no failures)
        self.monitor.run_checks()
        is_meeting = self.monitor.is_meeting_sla()

        # Result depends on database availability
        self.assertIsInstance(is_meeting, bool)

    def test_cached_health_status(self):
        """Test getting cached health without running checks."""
        # First run checks to populate cache
        self.monitor.run_checks()

        # Get cached status
        cached = self.monitor.get_cached_health()
        self.assertIsInstance(cached, HealthStatus)


class TestAlertingIntegration(TestCase):
    """Integration tests for alerting across the system."""

    def setUp(self):
        import apps.core.observability.alerts as alerts_module

        alerts_module._alert_manager = None

    def test_multiple_alert_types_same_session(self):
        """Test multiple alert types in same session."""
        # Send different alert types
        fiscal = fiscal_alert(
            service="afip", operation="test", error="Test error", tenant_id=1
        )
        sync = sync_alert(
            operation="push", branch_id=1, error="Test error", tenant_id=1
        )
        security = security_alert(event_type="failed_auth", ip_address="127.0.0.1")

        # All should succeed
        self.assertIsNotNone(fiscal)
        self.assertIsNotNone(sync)
        self.assertIsNotNone(security)

        # Check store has all three
        manager = get_alert_manager()
        store = manager.get_store()

        fiscal_count = store.count(alert_type=AlertType.FISCAL)
        sync_count = store.count(alert_type=AlertType.SYNC)
        security_count = store.count(alert_type=AlertType.SECURITY)

        self.assertEqual(fiscal_count, 1)
        self.assertEqual(sync_count, 1)
        self.assertGreaterEqual(security_count, 1)

    def test_concurrent_alert_sending(self):
        """Test alerts can be sent concurrently."""
        results = []

        def send_alerts(thread_id):
            for i in range(5):
                alert = system_alert(
                    component=f"thread_{thread_id}",
                    message=f"Alert {i}",
                    context={"thread_id": thread_id},
                )
                if alert:
                    results.append(alert)

        threads = [
            threading.Thread(target=send_alerts, args=(i,)) for i in range(3)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have multiple alerts (some may be deduplicated)
        self.assertGreater(len(results), 0)

    def test_alert_with_full_context_chain(self):
        """Test alert with complete context chain for debugging."""
        alert = fiscal_alert(
            service="afip",
            operation="invoice_emission",
            error="Certificate expired",
            tenant_id=100,
            branch_id=200,
            context={
                "request_id": "req-12345",
                "invoice_type": "A",
                "invoice_number": 1001,
                "customer_cuit": "20-12345678-9",
                "total_amount": 15000.00,
                "attempt_number": 3,
                "last_error_code": "CERT_EXPIRED",
                "certificate_serial": "ABC123",
                "environment": "production",
            },
        )

        # Verify full context preserved
        self.assertEqual(alert.tenant_id, 100)
        self.assertEqual(alert.branch_id, 200)
        self.assertEqual(alert.context["request_id"], "req-12345")
        self.assertEqual(alert.context["total_amount"], 15000.00)
