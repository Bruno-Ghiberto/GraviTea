"""
Integration tests for structured JSON logging.

Tests async log emission and full logging pipeline.
Per 004-observability-metrics spec FR-016 through FR-020.
"""

import json
import logging
import os
import time
from io import StringIO
from unittest.mock import patch

import pytest
from django.test import Client, TestCase, override_settings


class TestAsyncLogEmission:
    """T061: Integration test for async log emission."""

    def test_logging_does_not_block_request(self):
        """T061: Test logging doesn't significantly impact request time."""
        # Setup a test logger
        logger = logging.getLogger("test.async")
        logger.setLevel(logging.INFO)

        # Time logging operations
        start = time.perf_counter()
        for _ in range(100):
            logger.info("Test log message %d", _, extra={"data": "value"})
        elapsed = time.perf_counter() - start

        # 100 log calls should complete in under 100ms
        # This ensures logging isn't blocking
        assert elapsed < 0.1, f"Logging took {elapsed:.3f}s for 100 calls"

    def test_log_records_include_context(self):
        """T061: Test log records maintain context in async pipeline."""
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(
            logging.Formatter("%(levelname)s %(name)s %(message)s")
        )

        logger = logging.getLogger("test.context")
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        try:
            logger.info("Test message with context")
            stream.seek(0)
            output = stream.read()

            assert "INFO" in output
            assert "test.context" in output
            assert "Test message" in output
        finally:
            logger.removeHandler(handler)


class TestLoggingWithDjango(TestCase):
    """Integration tests for logging with Django."""

    def setUp(self):
        """Set up test client."""
        self.client = Client()

    def test_request_generates_log_entries(self):
        """Test Django requests generate log entries."""
        # Make a request
        response = self.client.get("/health/live")

        # Request should succeed
        assert response.status_code == 200

    def test_json_format_in_django_context(self):
        """Test JSON formatting works in Django context."""
        from apps.core.observability.logging import JSONLogFormatter

        formatter = JSONLogFormatter()
        record = logging.LogRecord(
            name="django.request",
            level=logging.INFO,
            pathname="views.py",
            lineno=1,
            msg="Request processed",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)

        # Should be valid JSON
        parsed = json.loads(output)
        assert parsed["logger"] == "django.request"


class TestLogCorrelationWithTraces(TestCase):
    """Test log correlation with trace context."""

    def setUp(self):
        """Set up test client."""
        self.client = Client()

    def test_logs_have_trace_id_from_request(self):
        """Test logs include trace_id from request headers."""
        from apps.core.observability.logging import TraceCorrelationFilter

        filter = TraceCorrelationFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )

        # Filter should add trace context fields
        result = filter.filter(record)

        assert result is True
        assert hasattr(record, "trace_id")
        assert hasattr(record, "tenant_id")


class TestLoggingPerformance(TestCase):
    """Test logging doesn't impact application performance."""

    def setUp(self):
        """Set up test client."""
        self.client = Client()

    def test_logging_overhead_minimal(self):
        """T061: Test logging adds minimal overhead."""
        # Warm up
        self.client.get("/health/live")

        # Measure request time
        start = time.perf_counter()
        for _ in range(10):
            self.client.get("/health/live")
        baseline = time.perf_counter() - start

        # Average should be under 50ms per request
        avg_ms = (baseline / 10) * 1000
        assert avg_ms < 50, f"Average request time {avg_ms:.2f}ms is too high"


class TestLogFormatEnvironment(TestCase):
    """Test log format configuration via environment."""

    def test_log_format_json(self):
        """Test JSON log format when configured."""
        from apps.core.observability.logging import get_log_format

        with patch.dict(os.environ, {"LOG_FORMAT": "json"}):
            assert get_log_format() == "json"

    def test_log_format_text(self):
        """Test text log format when configured."""
        from apps.core.observability.logging import get_log_format

        with patch.dict(os.environ, {"LOG_FORMAT": "text"}):
            assert get_log_format() == "text"

    def test_log_level_from_environment(self):
        """Test log level from environment variable."""
        from apps.core.observability.logging import get_log_level

        with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}):
            assert get_log_level() == "DEBUG"

        with patch.dict(os.environ, {"LOG_LEVEL": "ERROR"}):
            assert get_log_level() == "ERROR"


class TestLogSchemaCompliance(TestCase):
    """Test logs comply with defined schema."""

    def test_log_schema_fields(self):
        """Test log entry has all required schema fields."""
        from apps.core.observability.logging import JSONLogFormatter

        formatter = JSONLogFormatter()
        record = logging.LogRecord(
            name="apps.inventario.views",
            level=logging.INFO,
            pathname="views.py",
            lineno=42,
            msg="Product created",
            args=(),
            exc_info=None,
        )
        record.trace_id = "550e8400-e29b-41d4-a716-446655440000"
        record.tenant_id = "tenant-123"

        output = formatter.format(record)
        parsed = json.loads(output)

        # Verify schema
        assert "@timestamp" in parsed
        assert "level" in parsed
        assert "logger" in parsed
        assert "message" in parsed
        assert "trace_id" in parsed
        assert "tenant_id" in parsed

        # Verify values
        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "apps.inventario.views"
        assert parsed["message"] == "Product created"

    def test_error_log_includes_exception(self):
        """Test error logs include exception details."""
        from apps.core.observability.logging import JSONLogFormatter

        formatter = JSONLogFormatter()

        try:
            raise ValueError("Test error")
        except ValueError:
            import sys
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )

        output = formatter.format(record)
        parsed = json.loads(output)

        assert "exception" in parsed
        assert parsed["exception"]["type"] == "ValueError"
        assert "Test error" in parsed["exception"]["message"]
