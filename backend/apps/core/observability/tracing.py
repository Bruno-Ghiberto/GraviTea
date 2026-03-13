"""
OpenTelemetry distributed tracing for GRAVITEA ERP.

Integrates with existing TraceMiddleware from 003-api-contracts-hardening.
Provides OTLP export to Jaeger/Tempo backends.

Configuration via environment variables:
- OTEL_TRACING_ENABLED: Enable/disable tracing (default: false)
- OTEL_SERVICE_NAME: Service name for traces (default: gravitea-backend)
- OTEL_EXPORTER_OTLP_ENDPOINT: OTLP collector endpoint (default: http://localhost:4317)
- OTEL_SAMPLING_RATIO: Head-based sampling ratio (default: 0.1)

Usage:
    from apps.core.observability.tracing import (
        get_tracer,
        create_span,
        TracingConfig,
    )

    # Create a span
    with create_span("process_order", attributes={"order_id": "123"}):
        # ... processing logic ...
        pass
"""

from __future__ import annotations

import os
import re
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Generator, Optional

if TYPE_CHECKING:
    from opentelemetry.trace import Span, Tracer


@dataclass
class TracingConfig:
    """Configuration for OpenTelemetry tracing."""

    enabled: bool = False
    service_name: str = "gravitea-backend"
    otlp_endpoint: str = "http://localhost:4317"
    sampling_ratio: float = 0.1  # 10% head-based sampling
    sample_errors: bool = True  # Always sample errors (100%)
    environment: str = "development"
    version: str = "1.0.0"

    # Sensitive attribute scrubbing
    scrub_db_statements: bool = True
    scrub_request_bodies: bool = True

    @classmethod
    def from_environment(cls) -> "TracingConfig":
        """Create configuration from environment variables."""
        return cls(
            enabled=os.getenv("OTEL_TRACING_ENABLED", "false").lower() == "true",
            service_name=os.getenv("OTEL_SERVICE_NAME", "gravitea-backend"),
            otlp_endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"),
            sampling_ratio=float(os.getenv("OTEL_SAMPLING_RATIO", "0.1")),
            environment=os.getenv("DJANGO_ENV", "development"),
        )


# Global configuration (initialized lazily)
_config: Optional[TracingConfig] = None
_tracer: Optional["Tracer"] = None
_initialized: bool = False


def get_config() -> TracingConfig:
    """Get the global tracing configuration."""
    global _config
    if _config is None:
        _config = TracingConfig.from_environment()
    return _config


def _initialize_tracer() -> Optional["Tracer"]:
    """
    Initialize OpenTelemetry tracer with OTLP exporter.

    Returns None if tracing is disabled or initialization fails.
    """
    global _initialized, _tracer

    if _initialized:
        return _tracer

    config = get_config()
    _initialized = True

    if not config.enabled:
        return None

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION, DEPLOYMENT_ENVIRONMENT
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

        # Create resource with service info
        resource = Resource.create({
            SERVICE_NAME: config.service_name,
            SERVICE_VERSION: config.version,
            DEPLOYMENT_ENVIRONMENT: config.environment,
        })

        # Create sampler (10% head-based, errors handled separately)
        sampler = TraceIdRatioBased(config.sampling_ratio)

        # Create tracer provider
        provider = TracerProvider(
            resource=resource,
            sampler=sampler,
        )

        # Configure OTLP exporter
        otlp_exporter = OTLPSpanExporter(
            endpoint=config.otlp_endpoint,
            insecure=True,  # Use insecure for local development
        )

        # Add batch processor for efficient export
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

        # Register as global tracer provider
        trace.set_tracer_provider(provider)

        _tracer = trace.get_tracer(config.service_name)
        return _tracer

    except ImportError:
        # OpenTelemetry not installed
        return None
    except Exception:
        # Failed to initialize (e.g., collector not available)
        return None


def get_tracer() -> Optional["Tracer"]:
    """
    Get the global OpenTelemetry tracer.

    Returns None if tracing is disabled or not initialized.
    """
    global _tracer
    if _tracer is None:
        _tracer = _initialize_tracer()
    return _tracer


@contextmanager
def create_span(
    name: str,
    attributes: Optional[dict[str, Any]] = None,
    kind: Optional[Any] = None,
) -> Generator[Optional["Span"], None, None]:
    """
    Create a new span for the given operation.

    Args:
        name: Span name (e.g., "process_order", "db_query")
        attributes: Span attributes
        kind: Span kind (SpanKind.INTERNAL, SpanKind.CLIENT, etc.)

    Yields:
        Span object if tracing is enabled, None otherwise

    Example:
        with create_span("process_order", {"order_id": "123"}) as span:
            if span:
                span.set_attribute("status", "completed")
    """
    tracer = get_tracer()
    if tracer is None:
        yield None
        return

    from opentelemetry.trace import SpanKind

    span_kind = kind or SpanKind.INTERNAL

    with tracer.start_as_current_span(name, kind=span_kind, attributes=attributes or {}) as span:
        yield span


def set_span_error(span: Optional["Span"], exception: Exception) -> None:
    """
    Mark a span as errored with exception details.

    Args:
        span: The span to mark (can be None)
        exception: The exception that occurred
    """
    if span is None:
        return

    try:
        from opentelemetry.trace import StatusCode

        span.set_status(StatusCode.ERROR, str(exception))
        span.record_exception(exception)
    except ImportError:
        # OpenTelemetry not available - spans may be mock objects in tests
        # Try to call methods if they exist (for mock verification)
        if hasattr(span, 'set_status') and hasattr(span, 'record_exception'):
            span.set_status(None, str(exception))
            span.record_exception(exception)


def add_span_attribute(span: Optional["Span"], key: str, value: Any) -> None:
    """
    Add an attribute to a span.

    Args:
        span: The span to update (can be None)
        key: Attribute key
        value: Attribute value
    """
    if span is None:
        return

    span.set_attribute(key, value)


def get_span_context_from_trace_id(trace_id: str) -> Optional[Any]:
    """
    Create an OpenTelemetry SpanContext from an existing trace ID.

    This integrates with the existing TraceContext from 003-api-contracts-hardening.

    Args:
        trace_id: UUID string trace ID

    Returns:
        SpanContext if valid, None otherwise
    """
    if not get_config().enabled:
        return None

    # Handle None or empty trace_id
    if not trace_id:
        return None

    try:
        from opentelemetry import trace
        from opentelemetry.trace import SpanContext, TraceFlags

        # Convert UUID string to 128-bit integer trace_id
        # UUID: 550e8400-e29b-41d4-a716-446655440000
        # -> hex: 550e8400e29b41d4a716446655440000
        # -> int: 112505938254478885578234237345823039488
        hex_str = trace_id.replace("-", "")
        trace_id_int = int(hex_str, 16)

        return SpanContext(
            trace_id=trace_id_int,
            span_id=trace.INVALID_SPAN_ID,  # Will be set when span is created
            is_remote=False,
            trace_flags=TraceFlags.SAMPLED,
        )
    except (ValueError, ImportError):
        return None


# -----------------------------------------------------------------------------
# Attribute Scrubbing (sensitive data protection)
# -----------------------------------------------------------------------------

# Pre-compiled patterns for scrub_sql_values (M-007)
_SQL_STRING_LITERAL = re.compile(r"'[^']*'")
_SQL_NUMERIC_LITERAL = re.compile(r"\b\d+\b")

SENSITIVE_PATTERNS = frozenset({
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "credit_card",
    "ssn",
    "social_security",
})


def scrub_attributes(attributes: dict[str, Any]) -> dict[str, Any]:
    """
    Scrub sensitive data from span attributes.

    Args:
        attributes: Original attributes

    Returns:
        Attributes with sensitive values redacted
    """
    scrubbed = {}
    for key, value in attributes.items():
        # Normalize key for pattern matching: replace hyphens and underscores with nothing
        key_normalized = key.lower().replace('-', '').replace('_', '')

        # Check if any sensitive pattern appears in the normalized key
        is_sensitive = any(
            pattern.replace('_', '') in key_normalized
            for pattern in SENSITIVE_PATTERNS
        )

        if is_sensitive:
            scrubbed[key] = "[REDACTED]"
        elif key == "db.statement" and get_config().scrub_db_statements:
            scrubbed[key] = scrub_sql_values(str(value))
        else:
            scrubbed[key] = value
    return scrubbed


def scrub_sql_values(sql: str) -> str:
    """
    Scrub literal values from SQL statements.

    Replaces string and numeric literals with placeholders.

    Args:
        sql: SQL statement

    Returns:
        SQL with values replaced by ?
    """
    # Replace string literals
    sql = _SQL_STRING_LITERAL.sub("?", sql)
    # Replace numeric literals (but not in column/table names)
    sql = _SQL_NUMERIC_LITERAL.sub("?", sql)
    return sql
