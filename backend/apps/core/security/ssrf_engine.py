"""
SSRF Validation Pipeline dispatcher — Rust-accelerated URL safety checks
with Python fallback.

SPEC-022: Replaces Python url_validator.is_safe_url() with compiled Rust
static checks (scheme, IP encoding, CIDR, hostname patterns, credentials)
plus a Python DNS resolution phase.

Two-phase architecture:
  Phase 1 (Rust): validate_url_safety() — static analysis, O(1) per URL.
  Phase 2 (Python): _resolve_hostname() → check_resolved_ip() — DNS gate.
"""

from __future__ import annotations

import logging
import socket
from typing import Optional

logger = logging.getLogger(__name__)

_USE_RUST: bool

try:
    from gravitea_rust import (  # type: ignore[import-untyped]
        validate_url_safety as _rust_validate_url_safety,
        check_resolved_ip as _rust_check_resolved_ip,
    )
    _USE_RUST = True
except (ImportError, OSError):
    _USE_RUST = False
    logger.warning(
        "gravitea_rust SSRF validation not available — using Python fallback"
    )


def is_safe_url(url: str) -> bool:
    """Check if a URL is safe to request (not an SSRF target).

    Delegates to Rust when available, otherwise falls back to Python.
    Behaves identically to url_validator.is_safe_url().
    """
    if _USE_RUST:
        return _is_safe_url_rust(url)
    return _is_safe_url_python(url)


def _is_safe_url_rust(url: str) -> bool:
    """Rust-accelerated SSRF validation.

    Phase 1 (Rust): Static checks — scheme, credentials, IP encoding
    (decimal/hex/octal/shortened), CIDR ranges, cloud metadata IPs,
    suspicious hostname patterns.

    Phase 2 (Python): DNS resolution + check_resolved_ip() for hostnames
    that pass static checks. GIL NOT released (R-006: OS resolver in Python).

    Returns:
        False if blocked by Rust static checks or DNS phase.
        True if all checks pass.
    """
    is_safe, hostname = _rust_validate_url_safety(url or "")
    if not is_safe:
        return False
    # hostname="" means Rust already verified a direct public IP — no DNS needed.
    if not hostname:
        return True
    resolved_ip = _resolve_hostname(hostname)
    if resolved_ip is None:
        # DNS failure or unresolvable — fail-open for connectivity.
        return True
    return _rust_check_resolved_ip(resolved_ip)


def _is_safe_url_python(url: str) -> bool:
    """Python fallback for SSRF validation.

    Delegates to the original url_validator module-level function.
    Lazy import avoids circular import at module level.
    """
    from apps.core.security.url_validator import is_safe_url as _py  # noqa: PLC0415
    return _py(url)


def _resolve_hostname(hostname: str) -> Optional[str]:
    """Resolve hostname to IP string for post-DNS validation.

    Returns IP address string if resolved, None if DNS fails.
    GIL NOT released — OS resolver must run in Python (R-006).
    """
    try:
        infos = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        if infos:
            return infos[0][4][0]
    except (socket.gaierror, socket.herror, ValueError, OSError):
        pass
    return None
