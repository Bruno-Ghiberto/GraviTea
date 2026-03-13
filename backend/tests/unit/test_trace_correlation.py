"""Unit tests for trace correlation logging filter.

Tests TraceCorrelationFilter functionality including context injection
and default values when no trace context is available.

Per spec.md FR-007, FR-008 requirements:
- T070: Unit test for TraceCorrelationFilter
"""

from __future__ import annotations

import logging
import uuid
from unittest.mock import MagicMock, patch

import pytest

from apps.core.exceptions.trace import (
    TraceContext,
    clear_trace_context,
    get_trace_context,
    get_trace_id,
    set_trace_context,
)
from apps.core.logging.filters import RequestIdFilter, TraceCorrelationFilter


@pytest.mark.unit
class TestTraceCorrelationFilter:
    """Test suite for TraceCorrelationFilter."""

    def setup_method(self):
        """Clear trace context before each test."""
        clear_trace_context()

    def teardown_method(self):
        """Clear trace context after each test."""
        clear_trace_context()

    def test_filter_always_returns_true(self):
        """Filter allows all log records through."""
        filter_instance = TraceCorrelationFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = filter_instance.filter(record)

        assert result is True

    def test_filter_adds_default_values_without_context(self):
        """Filter adds default dash values when no trace context."""
        filter_instance = TraceCorrelationFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        filter_instance.filter(record)

        assert record.trace_id == "-"
        assert record.tenant_id == "-"
        assert record.branch_id == "-"
        assert record.user_id == "-"
        assert record.request_path == "-"
        assert record.request_method == "-"

    def test_filter_injects_trace_context(self):
        """Filter injects all trace context fields into log record."""
        ctx = TraceContext(
            trace_id="abc-123-def",
            tenant_id="tenant-001",
            branch_id="branch-001",
            user_id="user-001",
            request_path="/api/v1/products/",
            request_method="GET",
        )
        set_trace_context(ctx)

        filter_instance = TraceCorrelationFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        filter_instance.filter(record)

        assert record.trace_id == "abc-123-def"
        assert record.tenant_id == "tenant-001"
        assert record.branch_id == "branch-001"
        assert record.user_id == "user-001"
        assert record.request_path == "/api/v1/products/"
        assert record.request_method == "GET"

    def test_filter_handles_partial_context(self):
        """Filter handles context with some None values."""
        ctx = TraceContext(
            trace_id="xyz-789",
            tenant_id="tenant-002",
            # branch_id is None (default)
            # user_id is None (default)
            request_path="/api/v1/health/",
            request_method="GET",
        )
        set_trace_context(ctx)

        filter_instance = TraceCorrelationFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        filter_instance.filter(record)

        assert record.trace_id == "xyz-789"
        assert record.tenant_id == "tenant-002"
        assert record.branch_id == "-"  # None becomes dash
        assert record.user_id == "-"  # None becomes dash
        assert record.request_path == "/api/v1/health/"
        assert record.request_method == "GET"

    def test_filter_works_with_formatter(self):
        """Filter integrates correctly with logging formatters."""
        ctx = TraceContext(
            trace_id="format-test-123",
            tenant_id="t1",
            request_path="/test/",
            request_method="POST",
        )
        set_trace_context(ctx)

        # Create handler with filter and formatter
        handler = logging.StreamHandler()
        handler.addFilter(TraceCorrelationFilter())
        handler.setFormatter(
            logging.Formatter("[{trace_id}] tenant={tenant_id} {message}", style="{")
        )

        logger = logging.getLogger("test_format")
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        # Capture the formatted output
        with patch.object(handler.stream, "write") as mock_write:
            logger.info("Test formatted message")

        # Verify trace_id and tenant_id appear in output
        call_args = mock_write.call_args[0][0]
        assert "format-test-123" in call_args
        assert "tenant=t1" in call_args

        # Cleanup
        logger.removeHandler(handler)


@pytest.mark.unit
class TestRequestIdFilter:
    """Test suite for RequestIdFilter (lightweight version)."""

    def setup_method(self):
        """Clear trace context before each test."""
        clear_trace_context()

    def teardown_method(self):
        """Clear trace context after each test."""
        clear_trace_context()

    def test_filter_always_returns_true(self):
        """Filter allows all log records through."""
        filter_instance = RequestIdFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = filter_instance.filter(record)

        assert result is True

    def test_filter_adds_trace_id_only(self):
        """Filter only adds trace_id field."""
        ctx = TraceContext(
            trace_id="request-id-only",
            tenant_id="tenant-ignored",
            user_id="user-ignored",
        )
        set_trace_context(ctx)

        filter_instance = RequestIdFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        filter_instance.filter(record)

        assert record.trace_id == "request-id-only"
        # Other fields should not be set by RequestIdFilter
        assert not hasattr(record, "tenant_id")

    def test_filter_adds_default_without_context(self):
        """Filter adds dash when no trace context available."""
        filter_instance = RequestIdFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        filter_instance.filter(record)

        assert record.trace_id == "-"


@pytest.mark.unit
class TestTraceContextFunctions:
    """Test suite for trace context helper functions."""

    def setup_method(self):
        """Clear trace context before each test."""
        clear_trace_context()

    def teardown_method(self):
        """Clear trace context after each test."""
        clear_trace_context()

    def test_get_trace_context_returns_none_when_empty(self):
        """get_trace_context returns None when not set."""
        assert get_trace_context() is None

    def test_set_and_get_trace_context(self):
        """set_trace_context and get_trace_context work together."""
        ctx = TraceContext(trace_id="test-123")
        set_trace_context(ctx)

        retrieved = get_trace_context()

        assert retrieved is not None
        assert retrieved.trace_id == "test-123"

    def test_clear_trace_context(self):
        """clear_trace_context removes the context."""
        ctx = TraceContext(trace_id="to-be-cleared")
        set_trace_context(ctx)
        assert get_trace_context() is not None

        clear_trace_context()

        assert get_trace_context() is None

    def test_get_trace_id_with_context(self):
        """get_trace_id returns trace_id from context."""
        ctx = TraceContext(trace_id="specific-trace-id")
        set_trace_context(ctx)

        result = get_trace_id()

        assert result == "specific-trace-id"

    def test_get_trace_id_without_context_generates_uuid(self):
        """get_trace_id generates new UUID when no context."""
        result = get_trace_id()

        # Should be a valid UUID
        uuid.UUID(result)  # Raises if invalid

    def test_get_trace_id_generates_different_uuids(self):
        """get_trace_id generates unique UUIDs each call without context."""
        results = [get_trace_id() for _ in range(5)]

        assert len(set(results)) == 5  # All unique


@pytest.mark.unit
class TestTraceContextFromRequest:
    """Test suite for TraceContext.from_request method."""

    def test_from_request_generates_trace_id(self):
        """from_request generates new trace_id when not in headers."""
        request = MagicMock()
        request.META = {}
        request.path = "/api/v1/test/"
        request.method = "GET"
        request.user = MagicMock()
        request.user.is_authenticated = False

        ctx = TraceContext.from_request(request)

        assert ctx.trace_id is not None
        uuid.UUID(ctx.trace_id)  # Validates UUID format

    def test_from_request_uses_header_trace_id(self):
        """from_request uses X-Trace-ID from headers when present."""
        request = MagicMock()
        request.META = {"HTTP_X_TRACE_ID": "header-provided-id"}
        request.path = "/api/v1/test/"
        request.method = "POST"
        request.user = MagicMock()
        request.user.is_authenticated = False

        ctx = TraceContext.from_request(request)

        assert ctx.trace_id == "header-provided-id"

    def test_from_request_extracts_authenticated_user_context(self):
        """from_request extracts user info from authenticated user."""
        request = MagicMock()
        request.META = {}
        request.path = "/api/v1/products/"
        request.method = "PATCH"
        request.user = MagicMock()
        request.user.is_authenticated = True
        request.user.id = "user-uuid-123"
        request.user.tenant_id = "tenant-uuid-456"
        request.user.default_branch_id = "branch-uuid-789"

        ctx = TraceContext.from_request(request)

        assert ctx.user_id == "user-uuid-123"
        assert ctx.tenant_id == "tenant-uuid-456"
        assert ctx.branch_id == "branch-uuid-789"
        assert ctx.request_path == "/api/v1/products/"
        assert ctx.request_method == "PATCH"

    def test_from_request_handles_unauthenticated_user(self):
        """from_request handles unauthenticated users gracefully."""
        request = MagicMock()
        request.META = {}
        request.path = "/api/v1/auth/login/"
        request.method = "POST"
        request.user = MagicMock()
        request.user.is_authenticated = False

        ctx = TraceContext.from_request(request)

        assert ctx.user_id is None
        assert ctx.tenant_id is None
        assert ctx.branch_id is None

    def test_to_log_extra_returns_all_fields(self):
        """to_log_extra returns dict suitable for logging."""
        ctx = TraceContext(
            trace_id="log-extra-test",
            tenant_id="t1",
            branch_id="b1",
            user_id="u1",
            request_path="/test/",
            request_method="DELETE",
        )

        extra = ctx.to_log_extra()

        assert extra == {
            "trace_id": "log-extra-test",
            "tenant_id": "t1",
            "branch_id": "b1",
            "user_id": "u1",
            "request_path": "/test/",
            "request_method": "DELETE",
        }
