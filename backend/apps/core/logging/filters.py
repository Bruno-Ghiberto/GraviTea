"""
Logging filters for trace correlation.

Provides TraceCorrelationFilter to automatically inject trace context
into all log records for structured logging and request correlation.

Per spec.md FR-007, FR-008 requirements.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from apps.core.exceptions.trace import get_trace_context

if TYPE_CHECKING:
    pass


class TraceCorrelationFilter(logging.Filter):
    """Logging filter that adds trace context fields to log records.

    This filter automatically injects trace_id, tenant_id, branch_id,
    user_id, request_path, and request_method from the current request
    context into every log record, enabling request correlation across
    all log entries.

    Example log output with this filter:
        INFO 2025-01-15 [abc-123] tenant=t1 user=u1 Processing request

    Usage:
        Add to LOGGING config filters:
            "filters": {
                "trace_correlation": {
                    "()": "apps.core.logging.filters.TraceCorrelationFilter",
                },
            }

        Apply to handlers:
            "handlers": {
                "console": {
                    "filters": ["trace_correlation"],
                    ...
                }
            }
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Add trace context fields to the log record.

        Args:
            record: The log record to augment with trace context

        Returns:
            True (always allows the record through)
        """
        ctx = get_trace_context()

        if ctx:
            record.trace_id = ctx.trace_id
            record.tenant_id = ctx.tenant_id or "-"
            record.branch_id = ctx.branch_id or "-"
            record.user_id = ctx.user_id or "-"
            record.request_path = ctx.request_path or "-"
            record.request_method = ctx.request_method or "-"
        else:
            # Set defaults when no trace context is available
            # (e.g., during startup, management commands, celery tasks)
            record.trace_id = "-"
            record.tenant_id = "-"
            record.branch_id = "-"
            record.user_id = "-"
            record.request_path = "-"
            record.request_method = "-"

        return True


class RequestIdFilter(logging.Filter):
    """Simple filter that adds only trace_id to log records.

    A lighter-weight alternative to TraceCorrelationFilter when only
    the trace_id is needed for correlation.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Add trace_id to the log record.

        Args:
            record: The log record to augment

        Returns:
            True (always allows the record through)
        """
        ctx = get_trace_context()
        record.trace_id = ctx.trace_id if ctx else "-"
        return True
