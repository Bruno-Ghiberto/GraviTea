"""
Structured JSON logging for GRAVITEA ERP.

Provides ELK/Loki-compatible log format with trace correlation.
Integrates with existing TraceContext from 003-api-contracts-hardening.

Configuration via environment variables:
- LOG_FORMAT: "json" or "text" (default: json)
- LOG_LEVEL: DEBUG, INFO, WARNING, ERROR, CRITICAL (default: INFO)

Log Schema:
{
    "@timestamp": "2025-12-05T10:30:00.123Z",
    "level": "INFO",
    "logger": "apps.inventario.views",
    "message": "Product created successfully",
    "trace_id": "550e8400-e29b-41d4-a716-446655440000",
    "span_id": "a1b2c3d4e5f67890",
    "tenant_id": "tenant-123",
    "branch_id": "branch-456",
    "user_id": "user-789",
    "extra": {}
}

Usage:
    from apps.core.observability.logging import (
        get_json_formatter,
        TraceCorrelationFilter,
    )

    # Configure in settings.py LOGGING
    LOGGING = {
        "formatters": {
            "json": {
                "()": "apps.core.observability.logging.get_json_formatter",
            },
        },
        "filters": {
            "trace_correlation": {
                "()": "apps.core.observability.logging.TraceCorrelationFilter",
            },
        },
    }
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    pass

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------


def get_log_format() -> str:
    """Get log format from environment (json or text)."""
    return os.getenv("LOG_FORMAT", "json").lower()


def get_log_level() -> str:
    """Get log level from environment."""
    return os.getenv("LOG_LEVEL", "INFO").upper()


# -----------------------------------------------------------------------------
# Sensitive Data Filtering
# -----------------------------------------------------------------------------

SENSITIVE_KEYS = frozenset({
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "access_token",
    "refresh_token",
    "authorization",
    "credit_card",
    "card_number",
    "cvv",
    "ssn",
    "social_security",
    "private_key",
})


def scrub_dict(data: dict, sensitive_keys: frozenset = SENSITIVE_KEYS) -> dict:
    """
    Recursively scrub sensitive data from a dictionary.

    Args:
        data: Dictionary to scrub
        sensitive_keys: Set of sensitive key names

    Returns:
        Dictionary with sensitive values replaced by [REDACTED]
    """
    scrubbed = {}
    for key, value in data.items():
        key_lower = key.lower()
        if any(s in key_lower for s in sensitive_keys):
            scrubbed[key] = "[REDACTED]"
        elif isinstance(value, dict):
            scrubbed[key] = scrub_dict(value, sensitive_keys)
        elif isinstance(value, list):
            scrubbed[key] = [
                scrub_dict(item, sensitive_keys) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            scrubbed[key] = value
    return scrubbed


class SensitiveDataFilter(logging.Filter):
    """
    Logging filter that scrubs sensitive data from log records.

    Automatically redacts passwords, tokens, API keys, and other
    sensitive information from log messages and extra fields.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter and scrub sensitive data from log record."""
        # Scrub extra fields
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            record.extra = scrub_dict(record.extra)

        # Scrub args if it's a dict
        if isinstance(record.args, dict):
            record.args = scrub_dict(record.args)

        return True


# -----------------------------------------------------------------------------
# Trace Correlation Filter
# -----------------------------------------------------------------------------


class TraceCorrelationFilter(logging.Filter):
    """
    Logging filter that adds trace context to log records.

    Injects trace_id, span_id, tenant_id, branch_id, user_id from
    the current request context (via TraceContext from 003).
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Add trace context fields to log record."""
        # Default values
        record.trace_id = getattr(record, "trace_id", None)
        record.span_id = getattr(record, "span_id", None)
        record.tenant_id = getattr(record, "tenant_id", None)
        record.branch_id = getattr(record, "branch_id", None)
        record.user_id = getattr(record, "user_id", None)

        try:
            # Try to get TraceContext from contextvars
            from apps.core.exceptions.trace import get_trace_context

            trace_ctx = get_trace_context()
            if trace_ctx:
                record.trace_id = record.trace_id or trace_ctx.trace_id
                record.tenant_id = record.tenant_id or getattr(trace_ctx, "tenant_id", None)
                record.user_id = record.user_id or getattr(trace_ctx, "user_id", None)
        except ImportError:
            # TraceContext not available
            pass

        return True


# -----------------------------------------------------------------------------
# JSON Formatter
# -----------------------------------------------------------------------------


class JSONLogFormatter(logging.Formatter):
    """
    JSON log formatter for ELK/Loki compatibility.

    Produces structured JSON logs with consistent schema:
    - @timestamp: ISO 8601 timestamp with timezone
    - level: Log level name
    - logger: Logger name (module path)
    - message: Log message
    - trace_id: Request trace ID for correlation
    - span_id: OpenTelemetry span ID (if available)
    - tenant_id: Tenant identifier
    - branch_id: Branch identifier
    - user_id: User identifier
    - extra: Additional context fields
    """

    def __init__(
        self,
        *args,
        include_stack_info: bool = True,
        **kwargs,
    ):
        """
        Initialize JSON formatter.

        Args:
            include_stack_info: Include stack trace on errors
        """
        super().__init__(*args, **kwargs)
        self.include_stack_info = include_stack_info

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON string."""
        import json

        # Build log entry
        log_entry: dict[str, Any] = {
            "@timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add trace correlation fields
        for field in ("trace_id", "span_id", "tenant_id", "branch_id", "user_id"):
            value = getattr(record, field, None)
            if value is not None:
                log_entry[field] = str(value)

        # Add request context if available
        if hasattr(record, "request_path"):
            log_entry["request_path"] = record.request_path
        if hasattr(record, "request_method"):
            log_entry["request_method"] = record.request_method
        if hasattr(record, "status_code"):
            log_entry["status_code"] = record.status_code
        if hasattr(record, "duration_ms"):
            log_entry["duration_ms"] = record.duration_ms

        # Add extra fields
        extra_fields = {}
        standard_fields = {
            "name",
            "msg",
            "args",
            "created",
            "filename",
            "funcName",
            "levelname",
            "levelno",
            "lineno",
            "module",
            "msecs",
            "pathname",
            "process",
            "processName",
            "relativeCreated",
            "stack_info",
            "exc_info",
            "exc_text",
            "thread",
            "threadName",
            "message",
            "trace_id",
            "span_id",
            "tenant_id",
            "branch_id",
            "user_id",
            "request_path",
            "request_method",
            "status_code",
            "duration_ms",
        }
        for key, value in record.__dict__.items():
            if key not in standard_fields and not key.startswith("_"):
                extra_fields[key] = value

        if extra_fields:
            log_entry["extra"] = scrub_dict(extra_fields)

        # Add exception info if present
        if record.exc_info and self.include_stack_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "stacktrace": self.formatException(record.exc_info),
            }

        return json.dumps(log_entry, default=str)


def get_json_formatter() -> JSONLogFormatter:
    """Factory function for creating JSON formatter in Django settings."""
    return JSONLogFormatter()


# -----------------------------------------------------------------------------
# Log Queue Handler (async logging support)
# -----------------------------------------------------------------------------

_log_queue = None
_queue_listener = None


def setup_async_logging(max_queue_size: int = 10000) -> None:
    """
    Set up asynchronous logging with a bounded queue.

    Prevents logging from blocking request processing.

    Args:
        max_queue_size: Maximum queue size before dropping logs
    """
    global _log_queue, _queue_listener

    from logging.handlers import QueueHandler, QueueListener
    from queue import Queue

    _log_queue = Queue(maxsize=max_queue_size)

    # Create queue handler
    queue_handler = QueueHandler(_log_queue)

    # Get root logger and add queue handler
    root_logger = logging.getLogger()
    root_logger.addHandler(queue_handler)


def stop_async_logging() -> None:
    """Stop the async logging queue listener."""
    global _queue_listener
    if _queue_listener is not None:
        _queue_listener.stop()
        _queue_listener = None


# -----------------------------------------------------------------------------
# Logging Configuration Helper
# -----------------------------------------------------------------------------


def get_logging_config(
    log_level: Optional[str] = None,
    log_format: Optional[str] = None,
) -> dict:
    """
    Generate Django LOGGING configuration dict.

    Args:
        log_level: Override log level (default: from environment)
        log_format: Override log format (default: from environment)

    Returns:
        Django LOGGING configuration dictionary
    """
    level = log_level or get_log_level()
    fmt = log_format or get_log_format()

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": "apps.core.observability.logging.JSONLogFormatter",
            },
            "verbose": {
                "format": "{asctime} {levelname} {name} [{trace_id}] {message}",
                "style": "{",
            },
        },
        "filters": {
            "trace_correlation": {
                "()": "apps.core.observability.logging.TraceCorrelationFilter",
            },
            "sensitive_data": {
                "()": "apps.core.observability.logging.SensitiveDataFilter",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "json" if fmt == "json" else "verbose",
                "filters": ["trace_correlation", "sensitive_data"],
            },
        },
        "loggers": {
            "": {
                "handlers": ["console"],
                "level": level,
            },
            "django": {
                "handlers": ["console"],
                "level": level,
                "propagate": False,
            },
            "django.request": {
                "handlers": ["console"],
                "level": level,
                "propagate": False,
            },
            "apps": {
                "handlers": ["console"],
                "level": level,
                "propagate": False,
            },
            "fiscal": {
                "handlers": ["console"],
                "level": level,
                "propagate": False,
            },
            "sync": {
                "handlers": ["console"],
                "level": level,
                "propagate": False,
            },
            "security": {
                "handlers": ["console"],
                "level": level,
                "propagate": False,
            },
        },
    }

    return config
