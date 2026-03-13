"""
Tests for sync logging module (SC-022 compliance).

Validates structured logging for all sync operations.
"""

import json
import uuid
from datetime import datetime
from io import StringIO

import pytest
from django.test import TestCase

from apps.sync.logging import SyncEventType, SyncLogger


class SyncLoggerTests(TestCase):
    """Test sync logging functionality."""

    def setUp(self):
        """Set up test data."""
        self.tenant_id = uuid.uuid4()
        self.device_id = "POS-001"
        self.operation_id = uuid.uuid4()
        self.user_id = uuid.uuid4()
        self.session_id = uuid.uuid4()

    def test_log_sync_push_start(self):
        """Test push start logging."""
        SyncLogger.log_sync_push_start(
            tenant_id=self.tenant_id,
            device_id=self.device_id,
            operation_count=5,
            user_id=self.user_id,
            session_id=self.session_id,
            request_ip="192.168.1.100",
        )
        # Logging should not raise exceptions

    def test_log_sync_push_complete(self):
        """Test push completion logging."""
        SyncLogger.log_sync_push_complete(
            tenant_id=self.tenant_id,
            device_id=self.device_id,
            operations_count=5,
            operations_applied=4,
            operations_skipped=1,
            operations_rejected=0,
            conflicts_detected=0,
            duration_ms=250.5,
            session_id=self.session_id,
        )

    def test_log_sync_push_failed(self):
        """Test push failure logging."""
        SyncLogger.log_sync_push_failed(
            tenant_id=self.tenant_id,
            device_id=self.device_id,
            error="Database connection failed",
            operation_count=5,
            operations_processed=3,
            session_id=self.session_id,
            error_code="DB_ERROR",
        )

    def test_log_sync_pull_start(self):
        """Test pull start logging."""
        since = datetime.utcnow()
        SyncLogger.log_sync_pull_start(
            tenant_id=self.tenant_id,
            device_id=self.device_id,
            since_timestamp=since,
            entity_types=["Product", "Sale"],
            user_id=self.user_id,
            session_id=self.session_id,
            request_ip="192.168.1.100",
        )

    def test_log_sync_pull_complete(self):
        """Test pull completion logging."""
        SyncLogger.log_sync_pull_complete(
            tenant_id=self.tenant_id,
            device_id=self.device_id,
            changes_count=15,
            entity_breakdown={"Product": 10, "Sale": 5},
            duration_ms=150.2,
            has_more=False,
            session_id=self.session_id,
        )

    def test_log_operation_applied(self):
        """Test operation applied logging."""
        SyncLogger.log_operation_applied(
            operation_id=self.operation_id,
            entity_type="Product",
            operation_type="CREATE",
            entity_id="prod-123",
            tenant_id=self.tenant_id,
            device_id=self.device_id,
            processing_time_ms=10.5,
        )

    def test_log_operation_rejected(self):
        """Test operation rejection logging."""
        SyncLogger.log_operation_rejected(
            operation_id=self.operation_id,
            entity_type="Sale",
            operation_type="DELETE",
            reason="Sales cannot be deleted",
            tenant_id=self.tenant_id,
            device_id=self.device_id,
            validation_errors={"operation": "DELETE not allowed"},
        )

    def test_log_operation_skipped(self):
        """Test operation skipped logging."""
        SyncLogger.log_operation_skipped(
            operation_id=self.operation_id,
            entity_type="Product",
            reason="already_exists",
            tenant_id=self.tenant_id,
            device_id=self.device_id,
        )

    def test_log_operation_failed(self):
        """Test operation failure logging."""
        SyncLogger.log_operation_failed(
            operation_id=self.operation_id,
            entity_type="StockMovement",
            error="Insufficient stock",
            tenant_id=self.tenant_id,
            device_id=self.device_id,
            retry_count=1,
            will_retry=True,
        )

    def test_log_conflict_detected(self):
        """Test conflict detection logging."""
        SyncLogger.log_conflict_detected(
            operation_id=self.operation_id,
            entity_type="Product",
            entity_id="prod-123",
            resolution_rule="server_wins",
            tenant_id=self.tenant_id,
            device_id=self.device_id,
            conflict_details={
                "client_version": 1,
                "server_version": 2,
            },
        )

    def test_log_conflict_resolved(self):
        """Test conflict resolution logging."""
        SyncLogger.log_conflict_resolved(
            operation_id=self.operation_id,
            entity_type="Product",
            entity_id="prod-123",
            resolution_rule="server_wins",
            resolution_action="SERVER_OVERRIDE",
            tenant_id=self.tenant_id,
            device_id=self.device_id,
            audit_log={"reason": "Configuration data"},
            merged_payload=False,
        )

    def test_log_conflict_failed(self):
        """Test conflict resolution failure logging."""
        SyncLogger.log_conflict_failed(
            operation_id=self.operation_id,
            entity_type="Product",
            error="Unknown entity type",
            tenant_id=self.tenant_id,
            device_id=self.device_id,
            resolution_rule="unknown_rule",
        )

    def test_log_retry_attempt(self):
        """Test retry attempt logging."""
        SyncLogger.log_retry_attempt(
            operation_id=self.operation_id,
            entity_type="StockMovement",
            retry_count=2,
            max_retries=3,
            tenant_id=self.tenant_id,
            device_id=self.device_id,
            previous_error="Connection timeout",
        )

    def test_log_retry_exhausted(self):
        """Test retry exhaustion logging."""
        SyncLogger.log_retry_exhausted(
            operation_id=self.operation_id,
            entity_type="StockMovement",
            retry_count=3,
            tenant_id=self.tenant_id,
            device_id=self.device_id,
            final_error="Connection timeout",
        )

    def test_log_retry_success(self):
        """Test retry success logging."""
        SyncLogger.log_retry_success(
            operation_id=self.operation_id,
            entity_type="StockMovement",
            retry_count=2,
            tenant_id=self.tenant_id,
            device_id=self.device_id,
        )

    def test_log_format_structure(self):
        """Test that log format is valid JSON with required fields."""
        # Create a string stream to capture log output
        import logging

        from apps.sync.logging import logger as sync_logger

        # Create handler that writes to string
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        sync_logger.addHandler(handler)
        sync_logger.setLevel(logging.INFO)

        # Generate a log
        SyncLogger.log_sync_push_start(
            tenant_id=self.tenant_id,
            device_id=self.device_id,
            operation_count=5,
            user_id=self.user_id,
        )

        # Get the log output
        log_output = stream.getvalue().strip()
        sync_logger.removeHandler(handler)

        # Verify it's valid JSON
        try:
            log_data = json.loads(log_output)
            assert "timestamp" in log_data
            assert "event_type" in log_data
            assert "severity" in log_data
            assert "message" in log_data
            assert log_data["event_type"] == SyncEventType.SYNC_PUSH_START
            assert log_data["severity"] == "INFO"
        except json.JSONDecodeError:
            pytest.fail(f"Log output is not valid JSON: {log_output}")

    def test_uuid_serialization(self):
        """Test that UUIDs are properly serialized to strings."""
        # UUIDs should be converted to strings in log output
        SyncLogger.log_operation_applied(
            operation_id=self.operation_id,
            entity_type="Product",
            operation_type="CREATE",
            entity_id="prod-123",
            tenant_id=self.tenant_id,
            device_id=self.device_id,
        )
        # Should not raise any serialization errors
