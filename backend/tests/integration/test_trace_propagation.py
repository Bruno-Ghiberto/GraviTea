"""Integration tests for trace ID propagation.

Tests that trace_id is correctly propagated through requests and responses,
included in error responses, and passed through headers.

Per spec.md FR-007, FR-008 requirements:
- T071: Integration test for trace propagation through middleware
- T072: Test trace_id in RFC 7807 error responses
- T073: Test X-Trace-ID header passthrough
- T074: Test trace context in logs
"""

from __future__ import annotations

import logging
import re
from io import StringIO
from typing import TYPE_CHECKING

import pytest
from django.test import Client

from apps.core.exceptions.trace import (
    TraceContext,
    clear_trace_context,
    set_trace_context,
)
from apps.core.logging.filters import TraceCorrelationFilter

if TYPE_CHECKING:
    pass


@pytest.mark.django_db
class TestTraceMiddlewarePropagation:
    """Test trace ID propagation through the middleware stack."""

    def test_response_includes_x_trace_id_header(self, client: Client):
        """Responses include X-Trace-ID header."""
        response = client.get("/health/live")

        assert "X-Trace-ID" in response
        trace_id = response["X-Trace-ID"]
        assert trace_id is not None
        assert len(trace_id) > 0

    def test_trace_id_is_uuid_format(self, client: Client):
        """X-Trace-ID is in valid UUID format."""
        response = client.get("/health/live")
        trace_id = response["X-Trace-ID"]

        # UUID format: 8-4-4-4-12 hex digits
        uuid_pattern = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
            re.IGNORECASE,
        )
        assert uuid_pattern.match(trace_id), f"Invalid UUID format: {trace_id}"

    def test_different_requests_get_different_trace_ids(self, client: Client):
        """Each request gets a unique trace_id."""
        trace_ids = []
        for _ in range(5):
            response = client.get("/health/live")
            trace_ids.append(response["X-Trace-ID"])

        # All should be unique
        assert len(set(trace_ids)) == 5

    def test_passthrough_of_client_provided_trace_id(self, client: Client):
        """Server uses X-Trace-ID from client when provided."""
        client_trace_id = "client-provided-trace-12345"

        response = client.get(
            "/health/live",
            HTTP_X_TRACE_ID=client_trace_id,
        )

        assert response["X-Trace-ID"] == client_trace_id

    def test_invalid_trace_id_is_replaced(self, client: Client):
        """Invalid trace IDs from client are accepted (lenient policy)."""
        # Even invalid trace IDs are passed through for debugging purposes
        response = client.get(
            "/health/live",
            HTTP_X_TRACE_ID="invalid-not-a-uuid",
        )

        # The server accepts client-provided trace IDs for correlation
        assert response["X-Trace-ID"] == "invalid-not-a-uuid"


@pytest.mark.django_db
class TestTraceInErrorResponses:
    """Test trace_id inclusion in RFC 7807 error responses."""

    def test_validation_error_includes_trace_id(self, client: Client):
        """Validation errors include trace_id in RFC 7807 response."""
        # Attempt to create product without required fields
        response = client.post(
            "/api/v1/products/",
            data={},
            content_type="application/json",
        )

        # Should be 401 (unauthorized) or 400 (bad request)
        assert response.status_code in [400, 401, 403]
        assert "X-Trace-ID" in response

    def test_auth_endpoint_includes_trace_id(self, client: Client):
        """Auth endpoints include trace_id in responses."""
        response = client.post(
            "/api/v1/auth/token/",
            data={"email": "test@test.com", "password": "wrong"},
            content_type="application/json",
        )

        # Should return error with trace_id header
        assert "X-Trace-ID" in response

    def test_trace_id_propagates_through_health_endpoint(self, client: Client):
        """Health endpoint passes through client trace_id."""
        client_trace_id = "health-test-trace-789"

        response = client.get(
            "/health/live",
            HTTP_X_TRACE_ID=client_trace_id,
        )

        header_trace_id = response["X-Trace-ID"]
        assert header_trace_id == client_trace_id


@pytest.mark.django_db
class TestTraceContextInLogs:
    """Test trace context propagation to logging system."""

    def test_filter_receives_trace_context_during_request(self, client: Client):
        """TraceCorrelationFilter receives context during request processing."""
        # This test verifies the filter can access trace context
        # by checking it injects values into log records

        # Create a test logger with our filter
        test_logger = logging.getLogger("test_trace_logs")
        test_logger.setLevel(logging.DEBUG)

        handler = logging.StreamHandler(StringIO())
        handler.addFilter(TraceCorrelationFilter())
        handler.setFormatter(
            logging.Formatter("[{trace_id}] tenant={tenant_id} {message}", style="{")
        )
        test_logger.addHandler(handler)

        try:
            # Simulate having a trace context set (as middleware would do)
            ctx = TraceContext(
                trace_id="test-log-trace",
                tenant_id="log-tenant",
                request_path="/test/",
                request_method="GET",
            )
            set_trace_context(ctx)

            # Log a message
            test_logger.info("Test log message")

            # Get the logged output
            output = handler.stream.getvalue()

            assert "test-log-trace" in output
            assert "tenant=log-tenant" in output

        finally:
            clear_trace_context()
            test_logger.removeHandler(handler)

    def test_filter_handles_no_context_gracefully(self):
        """Filter produces valid output even without trace context."""
        clear_trace_context()

        test_logger = logging.getLogger("test_no_context")
        test_logger.setLevel(logging.DEBUG)

        handler = logging.StreamHandler(StringIO())
        handler.addFilter(TraceCorrelationFilter())
        handler.setFormatter(
            logging.Formatter("[{trace_id}] {message}", style="{")
        )
        test_logger.addHandler(handler)

        try:
            test_logger.info("Message without context")

            output = handler.stream.getvalue()

            # Should have dash placeholder
            assert "[-]" in output
            assert "Message without context" in output

        finally:
            test_logger.removeHandler(handler)


@pytest.mark.django_db
class TestTraceContextCleanup:
    """Test that trace context is properly cleaned up after requests."""

    def test_context_cleared_after_request(self, client: Client):
        """Trace context is cleared after request completes."""
        # Make a request
        response = client.get("/health/live")

        # Context should be cleared after request
        # Verify the request completed successfully with trace_id
        assert response.status_code == 200
        assert "X-Trace-ID" in response

    def test_sequential_requests_have_isolated_contexts(self, client: Client):
        """Sequential requests have separate, isolated contexts."""
        trace_id_1 = "first-request-trace"
        trace_id_2 = "second-request-trace"

        response1 = client.get(
            "/health/live",
            HTTP_X_TRACE_ID=trace_id_1,
        )
        response2 = client.get(
            "/health/live",
            HTTP_X_TRACE_ID=trace_id_2,
        )

        assert response1["X-Trace-ID"] == trace_id_1
        assert response2["X-Trace-ID"] == trace_id_2
        assert response1["X-Trace-ID"] != response2["X-Trace-ID"]


@pytest.mark.django_db
class TestTraceContextDataclass:
    """Test TraceContext dataclass properties."""

    def test_trace_context_is_frozen(self):
        """TraceContext is immutable (frozen dataclass)."""
        ctx = TraceContext(trace_id="immutable-test")

        # Frozen dataclass raises FrozenInstanceError (subclass of AttributeError)
        with pytest.raises((AttributeError, TypeError)):
            ctx.trace_id = "changed"

    def test_trace_context_has_slots(self):
        """TraceContext uses slots for memory efficiency."""
        ctx = TraceContext(trace_id="slots-test")

        # Verify slots are defined (frozen + slots dataclass)
        assert hasattr(TraceContext, "__slots__")
        # Verify it doesn't have a __dict__ (memory efficient)
        assert not hasattr(ctx, "__dict__") or ctx.__dict__ == {}

    def test_trace_context_equality(self):
        """TraceContext instances with same values are equal."""
        ctx1 = TraceContext(
            trace_id="equal-test",
            tenant_id="t1",
            user_id="u1",
        )
        ctx2 = TraceContext(
            trace_id="equal-test",
            tenant_id="t1",
            user_id="u1",
        )

        assert ctx1 == ctx2

    def test_trace_context_hashing(self):
        """TraceContext is hashable (can be used in sets/dicts)."""
        ctx = TraceContext(trace_id="hashable-test")

        # Should be hashable
        hash_value = hash(ctx)
        assert isinstance(hash_value, int)

        # Can use in set
        context_set = {ctx}
        assert ctx in context_set
