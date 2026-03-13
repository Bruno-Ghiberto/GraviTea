"""
Security utilities for Gravitea ERP.

Provides structured security logging, audit trails, threat detection,
and rate limiting for API endpoints.
"""

from typing import Optional

from .logging import (SecurityLogger, log_authentication_event,
                      log_bulk_operation_warning, log_idor_attempt,
                      log_tenant_context_change, log_unscoped_access)
from .rate_limiter import (LoginRateLimiter, LoginThrottle, LockoutTier,
                           RateLimitConfig, get_login_limiter)

# Cached reference to avoid repeated imports (M-001 deduplication).
_security_logger_class: Optional[type] = None
_security_logger_loaded: bool = False


def get_security_logger() -> Optional[type]:
    """Return the :class:`SecurityLogger` class, lazily imported.

    This is the **single** copy of the lazy-import helper.  Both
    ``tenant_bound.py`` and ``mixins.py`` should call this instead of
    maintaining their own ``_get_security_logger()`` duplicates.

    Returns ``None`` if the import fails (e.g. during early bootstrap).
    """
    global _security_logger_class, _security_logger_loaded
    if not _security_logger_loaded:
        try:
            _security_logger_class = SecurityLogger
        except Exception:  # pragma: no cover – defensive
            _security_logger_class = None
        _security_logger_loaded = True
    return _security_logger_class


__all__ = [
    # Security logging
    "SecurityLogger",
    "get_security_logger",
    "log_idor_attempt",
    "log_tenant_context_change",
    "log_unscoped_access",
    "log_bulk_operation_warning",
    "log_authentication_event",
    # Rate limiting
    "LoginRateLimiter",
    "LoginThrottle",
    "LockoutTier",
    "RateLimitConfig",
    "get_login_limiter",
]
