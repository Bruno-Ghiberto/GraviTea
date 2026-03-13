"""
Trace ID middleware for request correlation.

Generates a unique trace_id for each request and makes it available
throughout the request lifecycle for logging and error responses.

Also integrates with OpenTelemetry for distributed tracing and
Prometheus for metrics collection.

Per spec.md FR-007, FR-008 requirements.
Per 004-observability-metrics spec for tracing and metrics.
"""

from __future__ import annotations

import logging
import os
import time
from typing import TYPE_CHECKING, Optional

from apps.core.exceptions.trace import (
    TraceContext,
    clear_trace_context,
    set_trace_context,
)

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse

logger = logging.getLogger(__name__)


class TraceMiddleware:
    """Middleware that manages trace context for each request.

    This middleware:
    1. Generates or extracts trace_id at request start
    2. Sets TraceContext in contextvars for cross-cutting access
    3. Creates OpenTelemetry spans for distributed tracing (if enabled)
    4. Records Prometheus metrics for RED monitoring
    5. Adds X-Trace-ID header to all responses
    6. Clears context after request processing

    The trace_id is used for:
    - Log correlation across the request lifecycle
    - RFC 7807 error response trace_id field
    - Distributed tracing with upstream/downstream services

    IMPORTANT: This middleware should be placed early in the MIDDLEWARE list,
    after SecurityMiddleware but before other custom middleware.
    """

    def __init__(self, get_response):
        """Initialize the middleware.

        Args:
            get_response: The next middleware or view in the chain
        """
        self.get_response = get_response
        self._otel_enabled = os.environ.get("OTEL_TRACING_ENABLED", "false").lower() == "true"
        self._metrics_enabled = os.environ.get("METRICS_ENABLED", "true").lower() == "true"
        self._db_wrapper_installed = False
        self._db_wrapper = None

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Process the request and manage trace context.

        Args:
            request: The incoming HTTP request

        Returns:
            The HTTP response with X-Trace-ID header added
        """
        # Ensure database metrics wrapper is installed (once per process)
        if self._metrics_enabled and not self._db_wrapper_installed:
            self._ensure_db_metrics_wrapper()

        # Record request start time for metrics
        start_time = time.perf_counter()

        # Create trace context from request
        trace_ctx = TraceContext.from_request(request)

        # Set trace context in contextvars for cross-cutting access
        set_trace_context(trace_ctx)

        # Attach to request for convenient access in views
        # Note: Dynamic attributes on HttpRequest - common Django pattern
        request.trace_id = trace_ctx.trace_id  # type: ignore[attr-defined]
        request.trace_context = trace_ctx  # type: ignore[attr-defined]

        # Log request start with trace context
        logger.debug(
            "Request started",
            extra=trace_ctx.to_log_extra(),
        )

        # Get tenant_id for metrics (may be None for unauthenticated requests)
        tenant_id = self._get_tenant_id(request)

        # Create OpenTelemetry span if enabled
        span = self._create_otel_span(request, trace_ctx) if self._otel_enabled else None

        try:
            # Process the request
            response = self.get_response(request)

            # Calculate request duration
            duration = time.perf_counter() - start_time

            # Record metrics
            if self._metrics_enabled:
                self._record_metrics(request, response.status_code, duration, tenant_id)

            # Set span attributes and status
            if span:
                self._finish_span(span, response.status_code)

            # Log request completion
            logger.debug(
                "Request completed",
                extra={
                    **trace_ctx.to_log_extra(),
                    "status_code": response.status_code,
                    "duration_ms": round(duration * 1000, 2),
                },
            )

            # Add trace ID to response headers for client correlation
            response["X-Trace-ID"] = trace_ctx.trace_id

            return response

        except Exception as exc:
            # Calculate duration even on error
            duration = time.perf_counter() - start_time

            # Record error metrics (status 500)
            if self._metrics_enabled:
                self._record_metrics(request, 500, duration, tenant_id)

            # Set span error status
            if span:
                self._set_span_error(span, exc)

            # Log exception with trace context
            logger.exception(
                "Request failed with exception",
                extra={
                    **trace_ctx.to_log_extra(),
                    "duration_ms": round(duration * 1000, 2),
                },
            )
            raise

        finally:
            # Always clear trace context after request
            clear_trace_context()

    def _get_tenant_id(self, request: HttpRequest) -> Optional[str]:
        """Extract tenant_id from request if available.

        Args:
            request: The HTTP request

        Returns:
            The tenant_id string or None
        """
        # Try to get from request attributes (set by TenantContextMiddleware)
        tenant_id = getattr(request, "tenant_id", None)
        if tenant_id:
            return str(tenant_id)

        # Try to get from trace context
        trace_ctx = getattr(request, "trace_context", None)
        if trace_ctx and hasattr(trace_ctx, "tenant_id"):
            return str(trace_ctx.tenant_id) if trace_ctx.tenant_id else None

        return None

    def _record_metrics(
        self,
        request: HttpRequest,
        status_code: int,
        duration: float,
        tenant_id: Optional[str],
    ) -> None:
        """Record Prometheus metrics for the request.

        Args:
            request: The HTTP request
            status_code: The response status code
            duration: Request duration in seconds
            tenant_id: The tenant ID or None
        """
        try:
            from apps.core.observability.metrics import record_request

            record_request(
                method=request.method,
                endpoint=request.path,
                status_code=status_code,
                duration=duration,
                tenant_id=tenant_id,
            )
        except ImportError:
            # Observability module not available
            pass
        except Exception as e:
            # Don't let metrics recording break the request
            logger.warning(f"Failed to record metrics: {e}")

    def _create_otel_span(self, request: HttpRequest, trace_ctx: TraceContext):
        """Create an OpenTelemetry span for the request.

        Args:
            request: The HTTP request
            trace_ctx: The trace context

        Returns:
            The span object or None
        """
        try:
            from apps.core.observability.tracing import create_span, add_span_attribute

            # Create span with request information
            span_name = f"{request.method} {request.path}"
            span = create_span(
                name=span_name,
                attributes={
                    "http.method": request.method,
                    "http.url": request.build_absolute_uri(),
                    "http.target": request.path,
                    "http.host": request.get_host(),
                    "http.scheme": request.scheme,
                    "http.user_agent": request.META.get("HTTP_USER_AGENT", ""),
                    "trace.id": trace_ctx.trace_id,
                },
            )
            return span.__enter__() if hasattr(span, "__enter__") else None
        except ImportError:
            return None
        except Exception as e:
            logger.warning(f"Failed to create OTel span: {e}")
            return None

    def _finish_span(self, span, status_code: int) -> None:
        """Set span attributes on completion.

        Args:
            span: The OpenTelemetry span
            status_code: The response status code
        """
        try:
            from apps.core.observability.tracing import add_span_attribute

            add_span_attribute(span, "http.status_code", status_code)

            # Set span status based on status code
            if status_code >= 400:
                from opentelemetry.trace import StatusCode
                span.set_status(StatusCode.ERROR)
        except Exception as e:
            logger.warning(f"Failed to finish OTel span: {e}")

    def _set_span_error(self, span, exception: Exception) -> None:
        """Set span error status on exception.

        Args:
            span: The OpenTelemetry span
            exception: The exception that occurred
        """
        try:
            from apps.core.observability.tracing import set_span_error

            set_span_error(span, exception)
        except Exception as e:
            logger.warning(f"Failed to set span error: {e}")

    def _ensure_db_metrics_wrapper(self) -> None:
        """Ensure database metrics wrapper is installed on all connections.

        This is called once per middleware instance to ensure database query
        metrics are captured in the web process.
        """
        try:
            from django.db import connections

            from apps.core.observability.metrics import record_db_query

            # Create the wrapper function if not already created
            if self._db_wrapper is None:
                def metrics_cursor_wrapper(execute, sql, params, many, context):
                    start = time.perf_counter()
                    try:
                        return execute(sql, params, many, context)
                    finally:
                        duration = time.perf_counter() - start
                        sql_upper = sql.strip().upper()
                        operation = "OTHER"
                        for op in ["SELECT", "INSERT", "UPDATE", "DELETE"]:
                            if sql_upper.startswith(op):
                                operation = op
                                break
                        try:
                            alias = getattr(context, "alias", "default")
                        except Exception:
                            alias = "default"
                        record_db_query(alias, operation, duration)

                self._db_wrapper = metrics_cursor_wrapper

            # Register on all database connections
            for alias in connections.databases:
                conn = connections[alias]
                wrapper_names = [
                    w.__name__ for w in conn.execute_wrappers
                    if hasattr(w, "__name__")
                ]
                if "metrics_cursor_wrapper" not in wrapper_names:
                    conn.execute_wrappers.append(self._db_wrapper)
                    logger.debug(f"DB metrics wrapper installed for {alias}")

            self._db_wrapper_installed = True
            logger.info("Database metrics wrapper installed via middleware")

        except Exception as e:
            logger.warning(f"Failed to install DB metrics wrapper: {e}")
            self._db_wrapper_installed = True  # Don't retry on error
