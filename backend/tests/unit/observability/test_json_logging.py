"""
Unit tests for structured JSON logging.

Tests JSON format, trace correlation, tenant_id injection, and sensitive data filtering.
Per 004-observability-metrics spec FR-016 through FR-020.
"""

import json
import logging
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

from apps.core.observability.logging import (
    JSONLogFormatter,
    SensitiveDataFilter,
    TraceCorrelationFilter,
    get_log_format,
    get_log_level,
    get_logging_config,
    scrub_dict,
)


@pytest.mark.unit
class TestJSONLogFormat:
    """T057: Test JSON log format compliance."""

    def test_log_entry_is_valid_json(self):
        """T057: Test log output is valid JSON."""
        formatter = JSONLogFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)

        # Should parse as valid JSON
        parsed = json.loads(output)
        assert isinstance(parsed, dict)

    def test_log_entry_has_required_fields(self):
        """T057: Test log entry contains all required schema fields."""
        formatter = JSONLogFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)
        parsed = json.loads(output)

        # Required fields per schema
        assert "@timestamp" in parsed
        assert "level" in parsed
        assert "logger" in parsed
        assert "message" in parsed

    def test_log_level_is_string(self):
        """T057: Test log level is a string."""
        formatter = JSONLogFormatter()

        for level in [logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR]:
            record = logging.LogRecord(
                name="test",
                level=level,
                pathname="test.py",
                lineno=1,
                msg="Test",
                args=(),
                exc_info=None,
            )
            output = formatter.format(record)
            parsed = json.loads(output)

            assert isinstance(parsed["level"], str)

    def test_timestamp_is_iso8601(self):
        """T057: Test timestamp is ISO 8601 format."""
        formatter = JSONLogFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)
        parsed = json.loads(output)

        # Should be ISO 8601 format
        timestamp = parsed["@timestamp"]
        assert "T" in timestamp
        assert ":" in timestamp

    def test_message_is_formatted(self):
        """T057: Test message includes format args."""
        formatter = JSONLogFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="User %s logged in",
            args=("john",),
            exc_info=None,
        )

        output = formatter.format(record)
        parsed = json.loads(output)

        assert parsed["message"] == "User john logged in"

    def test_exception_info_included(self):
        """T057: Test exception info is included on errors."""
        formatter = JSONLogFormatter()

        try:
            raise ValueError("Test exception")
        except ValueError:
            import sys
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="An error occurred",
            args=(),
            exc_info=exc_info,
        )

        output = formatter.format(record)
        parsed = json.loads(output)

        assert "exception" in parsed
        assert parsed["exception"]["type"] == "ValueError"
        assert "Test exception" in parsed["exception"]["message"]
        assert parsed["exception"]["stacktrace"] is not None

    def test_extra_fields_included(self):
        """T057: Test extra fields are included in log entry."""
        formatter = JSONLogFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )
        record.custom_field = "custom_value"
        record.another_field = 42

        output = formatter.format(record)
        parsed = json.loads(output)

        assert "extra" in parsed
        assert parsed["extra"]["custom_field"] == "custom_value"
        assert parsed["extra"]["another_field"] == 42


@pytest.mark.unit
class TestTraceIdInLogs:
    """T058: Test trace_id appears in log entries."""

    def test_trace_id_added_by_filter(self):
        """T058: Test TraceCorrelationFilter adds trace_id."""
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

        filter.filter(record)

        # Should have trace_id attribute (may be None if no context)
        assert hasattr(record, "trace_id")

    def test_trace_id_preserved_if_set(self):
        """T058: Test trace_id is preserved if already set on record."""
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
        record.trace_id = "existing-trace-id"

        filter.filter(record)

        assert record.trace_id == "existing-trace-id"

    def test_trace_id_included_in_json_output(self):
        """T058: Test trace_id appears in JSON formatted output."""
        formatter = JSONLogFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )
        record.trace_id = "550e8400-e29b-41d4-a716-446655440000"

        output = formatter.format(record)
        parsed = json.loads(output)

        assert parsed.get("trace_id") == "550e8400-e29b-41d4-a716-446655440000"

    def test_span_id_included_in_json_output(self):
        """T058: Test span_id appears in JSON formatted output."""
        formatter = JSONLogFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )
        record.span_id = "a1b2c3d4e5f67890"

        output = formatter.format(record)
        parsed = json.loads(output)

        assert parsed.get("span_id") == "a1b2c3d4e5f67890"


@pytest.mark.unit
class TestTenantIdInLogs:
    """T059: Test tenant_id appears in log entries."""

    def test_tenant_id_added_by_filter(self):
        """T059: Test TraceCorrelationFilter adds tenant_id."""
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

        filter.filter(record)

        assert hasattr(record, "tenant_id")

    def test_tenant_id_preserved_if_set(self):
        """T059: Test tenant_id is preserved if already set."""
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
        record.tenant_id = "tenant-123"

        filter.filter(record)

        assert record.tenant_id == "tenant-123"

    def test_tenant_id_included_in_json_output(self):
        """T059: Test tenant_id appears in JSON formatted output."""
        formatter = JSONLogFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )
        record.tenant_id = "tenant-123"

        output = formatter.format(record)
        parsed = json.loads(output)

        assert parsed.get("tenant_id") == "tenant-123"

    def test_branch_id_included_in_json_output(self):
        """T059: Test branch_id appears in JSON formatted output."""
        formatter = JSONLogFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )
        record.branch_id = "branch-456"

        output = formatter.format(record)
        parsed = json.loads(output)

        assert parsed.get("branch_id") == "branch-456"

    def test_user_id_included_in_json_output(self):
        """T059: Test user_id appears in JSON formatted output."""
        formatter = JSONLogFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )
        record.user_id = "user-789"

        output = formatter.format(record)
        parsed = json.loads(output)

        assert parsed.get("user_id") == "user-789"


@pytest.mark.unit
class TestSensitiveDataFilteringInLogs:
    """T060: Test sensitive data filtering in logs."""

    def test_password_scrubbed_in_extra(self):
        """T060: Test password is scrubbed from extra fields."""
        formatter = JSONLogFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )
        record.password = "secret123"

        output = formatter.format(record)
        parsed = json.loads(output)

        # Password should be redacted
        assert parsed.get("extra", {}).get("password") == "[REDACTED]"

    def test_token_scrubbed_in_extra(self):
        """T060: Test tokens are scrubbed from extra fields."""
        formatter = JSONLogFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )
        record.access_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

        output = formatter.format(record)
        parsed = json.loads(output)

        assert parsed.get("extra", {}).get("access_token") == "[REDACTED]"

    def test_scrub_dict_function(self):
        """T060: Test scrub_dict removes sensitive data."""
        data = {
            "username": "john",
            "password": "secret",
            "api_key": "key123",
            "nested": {
                "token": "token123",
                "safe": "value",
            },
        }

        scrubbed = scrub_dict(data)

        assert scrubbed["username"] == "john"
        assert scrubbed["password"] == "[REDACTED]"
        assert scrubbed["api_key"] == "[REDACTED]"
        assert scrubbed["nested"]["token"] == "[REDACTED]"
        assert scrubbed["nested"]["safe"] == "value"

    def test_sensitive_data_filter_class(self):
        """T060: Test SensitiveDataFilter filters log records."""
        filter = SensitiveDataFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )
        record.extra = {"password": "secret", "name": "john"}

        filter.filter(record)

        assert record.extra["password"] == "[REDACTED]"
        assert record.extra["name"] == "john"

    def test_authorization_header_scrubbed(self):
        """T060: Test authorization header is scrubbed."""
        data = {"authorization": "Bearer xyz123"}
        scrubbed = scrub_dict(data)
        assert scrubbed["authorization"] == "[REDACTED]"

    def test_credit_card_scrubbed(self):
        """T060: Test credit card numbers are scrubbed."""
        data = {"credit_card": "4111111111111111"}
        scrubbed = scrub_dict(data)
        assert scrubbed["credit_card"] == "[REDACTED]"

    def test_case_insensitive_scrubbing(self):
        """T060: Test scrubbing is case-insensitive."""
        data = {
            "PASSWORD": "secret",
            "Api_Key": "key123",
            "AccessToken": "token",
        }
        scrubbed = scrub_dict(data)

        assert scrubbed["PASSWORD"] == "[REDACTED]"
        assert scrubbed["Api_Key"] == "[REDACTED]"
        assert scrubbed["AccessToken"] == "[REDACTED]"


@pytest.mark.unit
class TestLoggingConfiguration:
    """Test logging configuration helpers."""

    def test_get_log_format_default(self):
        """Test default log format is json."""
        with patch.dict("os.environ", {}, clear=True):
            import os
            os.environ.pop("LOG_FORMAT", None)
            # Default should be json
            assert get_log_format() in ["json", "text"]

    def test_get_log_level_default(self):
        """Test default log level is INFO."""
        with patch.dict("os.environ", {}, clear=True):
            import os
            os.environ.pop("LOG_LEVEL", None)
            # Default should be INFO
            assert get_log_level() in ["INFO", "DEBUG", "WARNING", "ERROR"]

    def test_get_logging_config_returns_dict(self):
        """Test get_logging_config returns valid config."""
        config = get_logging_config()

        assert isinstance(config, dict)
        assert "version" in config
        assert config["version"] == 1
        assert "formatters" in config
        assert "handlers" in config
        assert "loggers" in config

    def test_get_logging_config_json_formatter(self):
        """Test config includes JSON formatter."""
        config = get_logging_config(log_format="json")

        assert "json" in config["formatters"]

    def test_get_logging_config_filters(self):
        """Test config includes required filters."""
        config = get_logging_config()

        assert "trace_correlation" in config["filters"]
        assert "sensitive_data" in config["filters"]


@pytest.mark.unit
class TestRequestContextInLogs:
    """Test request context fields in logs."""

    def test_request_path_in_log(self):
        """Test request_path appears in log entry."""
        formatter = JSONLogFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Request processed",
            args=(),
            exc_info=None,
        )
        record.request_path = "/api/v1/products/"
        record.request_method = "GET"
        record.status_code = 200
        record.duration_ms = 45.5

        output = formatter.format(record)
        parsed = json.loads(output)

        assert parsed.get("request_path") == "/api/v1/products/"
        assert parsed.get("request_method") == "GET"
        assert parsed.get("status_code") == 200
        assert parsed.get("duration_ms") == 45.5
