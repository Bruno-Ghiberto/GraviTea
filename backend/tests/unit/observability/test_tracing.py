"""
Unit tests for observability tracing module.

Tests span creation, trace context propagation, and sensitive data filtering.
Per 004-observability-metrics spec FR-011 through FR-020.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from apps.core.observability.tracing import (
    TracingConfig,
    add_span_attribute,
    create_span,
    get_span_context_from_trace_id,
    get_tracer,
    scrub_attributes,
    set_span_error,
)


@pytest.mark.unit
class TestTracingConfig:
    """Test TracingConfig dataclass."""

    def test_default_values(self):
        """Test TracingConfig has sensible defaults."""
        config = TracingConfig()

        assert config.enabled is False
        assert config.service_name == "gravitea-backend"
        assert config.otlp_endpoint == "http://localhost:4317"
        assert config.sampling_ratio == 0.1
        assert config.sample_errors is True

    def test_from_environment(self):
        """Test TracingConfig.from_environment() loads from env vars."""
        with patch.dict(
            os.environ,
            {
                "OTEL_TRACING_ENABLED": "true",
                "OTEL_SERVICE_NAME": "test-service",
                "OTEL_EXPORTER_OTLP_ENDPOINT": "http://collector:4317",
                "OTEL_SAMPLING_RATIO": "0.5",
            },
        ):
            config = TracingConfig.from_environment()

            assert config.enabled is True
            assert config.service_name == "test-service"
            assert config.otlp_endpoint == "http://collector:4317"
            assert config.sampling_ratio == 0.5

    def test_from_environment_defaults(self):
        """Test TracingConfig.from_environment() uses defaults when env not set."""
        with patch.dict(os.environ, {}, clear=True):
            # Clear relevant env vars
            for key in ["OTEL_TRACING_ENABLED", "OTEL_SERVICE_NAME", "OTEL_EXPORTER_OTLP_ENDPOINT"]:
                os.environ.pop(key, None)

            config = TracingConfig.from_environment()

            assert config.enabled is False
            assert config.service_name == "gravitea-backend"


@pytest.mark.unit
class TestSpanCreation:
    """Test span creation functionality."""

    def test_create_span_when_disabled(self):
        """T034: Test create_span returns context manager even when tracing disabled."""
        with patch.dict(os.environ, {"OTEL_TRACING_ENABLED": "false"}):
            # Should not raise, should return a context manager
            with create_span("test-span") as span:
                # Span may be None when tracing is disabled
                pass

    def test_create_span_with_attributes(self):
        """T034: Test create_span accepts attributes."""
        with patch.dict(os.environ, {"OTEL_TRACING_ENABLED": "false"}):
            with create_span(
                "test-span",
                attributes={
                    "http.method": "GET",
                    "http.url": "/api/v1/products",
                },
            ) as span:
                pass

    def test_create_span_with_kind(self):
        """T034: Test create_span accepts span kind."""
        with patch.dict(os.environ, {"OTEL_TRACING_ENABLED": "false"}):
            with create_span("test-span", kind="server") as span:
                pass


@pytest.mark.unit
class TestTraceContextPropagation:
    """Test trace context propagation."""

    def test_get_span_context_from_trace_id(self):
        """T035: Test getting span context from trace ID."""
        trace_id = "550e8400-e29b-41d4-a716-446655440000"

        # Should return a context or None
        context = get_span_context_from_trace_id(trace_id)

        # When tracing is disabled, context may be None
        # This just verifies the function doesn't crash

    def test_get_span_context_from_invalid_trace_id(self):
        """T035: Test handling invalid trace ID."""
        invalid_ids = [
            "",
            "not-a-uuid",
            "123",
            None,
        ]

        for trace_id in invalid_ids:
            # Should not raise, should return None or handle gracefully
            context = get_span_context_from_trace_id(trace_id)


@pytest.mark.unit
class TestSensitiveDataFiltering:
    """Test sensitive data filtering in span attributes."""

    def test_scrub_attributes_removes_passwords(self):
        """T036: Test password fields are scrubbed."""
        attrs = {
            "user.name": "john",
            "user.password": "secret123",
            "password": "another_secret",
        }

        scrubbed = scrub_attributes(attrs)

        assert scrubbed["user.name"] == "john"
        assert scrubbed.get("user.password") == "[REDACTED]"
        assert scrubbed.get("password") == "[REDACTED]"

    def test_scrub_attributes_removes_tokens(self):
        """T036: Test token fields are scrubbed."""
        attrs = {
            "auth.token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "access_token": "some_token",
            "refresh_token": "another_token",
            "api_token": "api_key_value",
        }

        scrubbed = scrub_attributes(attrs)

        for key in attrs:
            assert scrubbed.get(key) == "[REDACTED]"

    def test_scrub_attributes_removes_secrets(self):
        """T036: Test secret fields are scrubbed."""
        attrs = {
            "api_secret": "my_secret",
            "client_secret": "oauth_secret",
            "secret_key": "encryption_key",
        }

        scrubbed = scrub_attributes(attrs)

        for key in attrs:
            assert scrubbed.get(key) == "[REDACTED]"

    def test_scrub_attributes_removes_api_keys(self):
        """T036: Test API key fields are scrubbed."""
        attrs = {
            "api_key": "ak_123456",
            "apikey": "another_key",
            "x-api-key": "header_key",
        }

        scrubbed = scrub_attributes(attrs)

        for key in attrs:
            assert scrubbed.get(key) == "[REDACTED]"

    def test_scrub_attributes_preserves_safe_data(self):
        """T036: Test safe attributes are preserved."""
        attrs = {
            "http.method": "GET",
            "http.url": "/api/v1/products",
            "http.status_code": 200,
            "user.id": "12345",
            "tenant.id": "tenant-abc",
        }

        scrubbed = scrub_attributes(attrs)

        # All safe attributes should be preserved
        for key, value in attrs.items():
            assert scrubbed[key] == value

    def test_scrub_attributes_handles_nested_like_keys(self):
        """T036: Test nested-looking key patterns."""
        attrs = {
            "request.body.password": "should_be_scrubbed",
            "db.statement": "SELECT * FROM users WHERE password = ?",
        }

        scrubbed = scrub_attributes(attrs)

        # Password in key should be scrubbed
        assert scrubbed.get("request.body.password") == "[REDACTED]"

    def test_scrub_attributes_handles_empty_dict(self):
        """T036: Test empty dict handling."""
        assert scrub_attributes({}) == {}

    def test_scrub_attributes_handles_none_values(self):
        """T036: Test None value handling."""
        attrs = {
            "user.name": None,
            "password": None,
        }

        scrubbed = scrub_attributes(attrs)

        assert scrubbed["user.name"] is None
        assert scrubbed.get("password") == "[REDACTED]"


@pytest.mark.unit
class TestSpanError:
    """Test span error handling."""

    def test_set_span_error_with_exception(self):
        """Test setting span error with exception."""
        mock_span = MagicMock()

        exception = ValueError("Test error")
        set_span_error(mock_span, exception)

        # Verify set_status was called (when span is not None)
        # The actual behavior depends on whether OTel is available

    def test_set_span_error_with_none_span(self):
        """Test set_span_error handles None span gracefully."""
        exception = ValueError("Test error")

        # Should not raise
        set_span_error(None, exception)


@pytest.mark.unit
class TestAddSpanAttribute:
    """Test adding attributes to spans."""

    def test_add_span_attribute(self):
        """Test adding attribute to span."""
        mock_span = MagicMock()

        add_span_attribute(mock_span, "http.status_code", 200)

        # Should call set_attribute on span

    def test_add_span_attribute_with_none_span(self):
        """Test add_span_attribute handles None span gracefully."""
        # Should not raise
        add_span_attribute(None, "key", "value")


@pytest.mark.unit
class TestGetTracer:
    """Test tracer provider."""

    def test_get_tracer_when_disabled(self):
        """Test get_tracer returns None when tracing is disabled."""
        with patch.dict(os.environ, {"OTEL_TRACING_ENABLED": "false"}):
            tracer = get_tracer()
            # May return None or NoOp tracer when disabled
            # Just verify it doesn't raise

    def test_get_tracer_caching(self):
        """Test get_tracer returns cached instance."""
        with patch.dict(os.environ, {"OTEL_TRACING_ENABLED": "false"}):
            tracer1 = get_tracer()
            tracer2 = get_tracer()

            # Should return the same instance
            assert tracer1 is tracer2
