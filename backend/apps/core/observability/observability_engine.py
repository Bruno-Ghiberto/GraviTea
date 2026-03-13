"""
Observability hot-path dispatcher — Rust-accelerated path normalization
and endpoint label sanitization with Python fallback.

SPEC-021: Replaces 24 sequential Python regex ops with compiled Rust patterns.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_USE_RUST: bool

try:
    from gravitea_rust import (  # type: ignore[import-untyped]
        normalize_path as _rust_normalize_path,
        sanitize_endpoint_label as _rust_sanitize_endpoint_label,
    )
    _USE_RUST = True
except (ImportError, OSError):
    _USE_RUST = False
    logger.warning("gravitea_rust observability not available — using Python fallback")


def normalize_path(path: str) -> str:
    """Normalize URL path to prevent metric cardinality explosion.

    Delegates to Rust when available, otherwise falls back to Python.
    Fallback import is lazy to avoid circular import with metrics.py.
    """
    if _USE_RUST:
        return _rust_normalize_path(path)
    from apps.core.observability.metrics import normalize_path as _py  # noqa: PLC0415
    return _py(path)


def sanitize_endpoint_label(endpoint: str) -> str:
    """Sanitize endpoint path for Prometheus metric labels.

    Delegates to Rust when available, otherwise falls back to Python.
    Fallback import is lazy to avoid circular import with metrics.py.
    """
    if _USE_RUST:
        return _rust_sanitize_endpoint_label(endpoint)
    from apps.core.observability.metrics import sanitize_endpoint_label as _py  # noqa: PLC0415
    return _py(endpoint)
