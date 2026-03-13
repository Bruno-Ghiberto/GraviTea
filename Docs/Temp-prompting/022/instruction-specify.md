# Speckit Context: SSRF Validation Pipeline (SPEC-022)

> **Phase**: SPECIFY — Define what we're accelerating and why
> **Priority**: HIGH | **Wave**: 3 (parallel with SPEC-019)
> **Depends on**: SPEC-017 (Rust Toolchain Bootstrap) MUST be complete

---

## Mission Statement

Replace the CPU-bound portions of `backend/apps/core/security/url_validator.py` `is_safe_url()` with Rust. This covers URL structure validation, IP parsing (5 formats), CIDR range checking (10 ranges), suspicious hostname regex (9 patterns), and metadata IP detection. DNS resolution stays in Python (I/O-bound, not CPU-bound).

## Why This Matters Now

- **Security-critical path**: Every outgoing URL (ARCA SOAP, webhooks) is validated
- **3-8x speedup** on CPU portions — Rust `std::net::IpAddr` parsing is compiled and branch-predicted
- **Memory safety eliminates URL parsing edge cases** — critical for a security function
- **Minimal blast radius**: GitNexus analysis confirms LOW risk — only `test_ssrf.py:ssrf_validator` fixture directly references `URLValidator`; no production execution flows affected

## Architecture Decisions (FINAL — Do Not Re-Debate)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| URL parsing crate | `url 2.5` | Standard Rust URL parser (WHATWG) |
| Regex crate | `regex` (already from SPEC-021) | For hostname patterns; no lookahead needed |
| GIL handling | NOT released | Sub-millisecond operations |
| DNS resolution | Stays in Python | I/O-bound, `socket.getaddrinfo()` |
| IP format coverage | Standard, decimal, hex, octal, shortened | All 5 Python parsing strategies reimplemented |
| Private CIDR ranges | 10 ranges in Rust | Compiled into prefix checks |
| Exported functions | TWO: `validate_url_safety` + `check_resolved_ip` | Two-phase design: static checks + post-DNS check |
| FFI boundary | `(bool, String)` tuple + `bool` | Minimal overhead, clean separation of CPU from I/O |
| Dispatcher pattern | `ssrf_engine.py` (follows SPEC-021 `observability_engine.py`) | Rust dispatch with lazy Python fallback |
| `url_validator.py` changes | MINIMAL — only `URLValidator.is_safe()` delegates to engine | All existing test imports continue working |

## Current State (What Exists Today)

| Item | Details |
|------|---------|
| **File** | `backend/apps/core/security/url_validator.py` (338 lines) |
| **Class** | `URLValidator` — thin wrapper calling `is_safe_url()` |
| **Function** | `is_safe_url()` — main validation entry point (lines 88-159) |
| **Internal: `_parse_ip()`** | 5 IP parse strategies — standard, decimal, hex, octal, shortened (lines 162-246) |
| **Internal: `_is_private_ip()`** | 10 CIDR range checks via `ipaddress.ip_network` (lines 249-266) |
| **Internal: `_is_suspicious_hostname()`** | 9 regex patterns + null byte + IPv6 prefix checks (lines 269-315) |
| **Internal: `_resolve_hostname()`** | DNS resolution via `socket.getaddrinfo` — STAYS IN PYTHON (lines 318-337) |
| **Constants** | `ALLOWED_SCHEMES`, `BLOCKED_HOSTNAMES`, `METADATA_IPS`, `PRIVATE_NETWORKS` |
| **Test file** | `backend/tests/security/test_ssrf.py` — SEC-SSRF-001 through SEC-SSRF-006 |
| **Test constants** | `backend/tests/constants.py` — `SSRF_INTERNAL_HOSTS`, `SSRF_METADATA_HOSTS`, `SSRF_PRIVATE_NETWORKS`, `SSRF_DANGEROUS_SCHEMES` |
| **Call frequency** | Every outgoing URL validation (ARCA SOAP, webhooks) |
| **Current cost** | ~10-30us per validation |

### GitNexus Blast Radius (Verified)

| Symbol | Risk | Dependents | Notes |
|--------|------|-----------|-------|
| `URLValidator` class | LOW | `test_ssrf.py:ssrf_validator` only | No production execution flows |
| `is_safe_url()` | LOW | Direct imports in `test_ssrf.py` test methods | Tests import directly, not via class |
| `_resolve_hostname()` | NONE | No external callers | Will be imported by `ssrf_engine.py` |
| Security cluster | 352 symbols, 68% cohesion | — | Self-contained module |

## Target Architecture

### New Rust Source

```
rust/gravitea-core/src/
├── lib.rs          # Add `mod security;` + 2 #[pymodule_export] re-exports
└── security.rs     # NEW — validate_url_safety + check_resolved_ip
```

### Exported PyO3 Functions

| Function | Signature | Returns | Purpose |
|----------|-----------|---------|---------|
| `validate_url_safety` | `(url: &str) -> PyResult<(bool, String)>` | `(false, "")` = unsafe | All static checks: URL parse, scheme, credentials, IP parse (5 formats), CIDR (10 ranges), metadata IPs, blocked hostnames, suspicious patterns |
| | | `(true, "")` = safe (IP was public) | |
| | | `(true, "hostname.com")` = needs DNS | |
| `check_resolved_ip` | `(ip_str: &str) -> PyResult<bool>` | `true` = safe, `false` = private/metadata | Post-DNS validation: checks resolved IP against same CIDR ranges + metadata IPs |

### Internal Rust Functions (Not Exported)

| Function | Signature | Purpose |
|----------|-----------|---------|
| `parse_ip_flexible` | `(hostname: &str) -> Option<IpAddr>` | 5-strategy IP parsing (standard → decimal → hex → octal → shortened) |
| `is_private_ip` | `(ip: &IpAddr) -> bool` | Checks 10 compiled CIDR ranges |
| `is_metadata_ip` | `(ip: &IpAddr) -> bool` | Checks `169.254.169.254` and `169.254.170.2` |
| `is_suspicious_hostname` | `(hostname: &str) -> bool` | 9 `LazyLock<Regex>` patterns + null byte + IPv6 prefix |

### Why TWO Exported Functions (Not One)

The original instruction proposed `validate_url_safety(url) -> bool`, but this is insufficient:

1. DNS resolution is I/O-bound and MUST stay in Python (`socket.getaddrinfo`)
2. DNS happens AFTER static checks but BEFORE the final decision
3. After DNS resolves, the resolved IP must be checked against the same private ranges
4. A single `bool` return cannot express "static checks passed but DNS check still needed"

The two-function design cleanly separates concerns:
- **Phase 1** (Rust): `validate_url_safety(url)` → all CPU-bound static checks
- **Phase 2** (Python): `_resolve_hostname(hostname)` → I/O-bound DNS
- **Phase 3** (Rust): `check_resolved_ip(resolved_ip)` → CPU-bound range check

### New Python Dispatcher

```
backend/apps/core/security/
├── url_validator.py      # UNCHANGED — Python fallback (existing implementation)
├── ssrf_engine.py        # NEW — Rust-accelerated dispatcher with fallback
└── __init__.py           # Existing (no change)
```

**`ssrf_engine.py`** follows the SPEC-021 `observability_engine.py` pattern:

```python
"""SSRF validation dispatcher — Rust-accelerated with Python fallback.

SPEC-022: Replaces CPU-bound URL validation (5 IP formats, 10 CIDR ranges,
9 hostname patterns) with compiled Rust while DNS stays in Python.
"""
from __future__ import annotations
import logging

logger = logging.getLogger(__name__)
_USE_RUST: bool

try:
    from gravitea_rust import (  # type: ignore[import-untyped]
        validate_url_safety as _rust_validate,
        check_resolved_ip as _rust_check_ip,
    )
    _USE_RUST = True
except (ImportError, OSError):
    _USE_RUST = False
    logger.warning("gravitea_rust security not available — using Python fallback")


def is_safe_url(url):
    """Check if a URL is safe to request (not an SSRF target).

    Delegates static checks to Rust when available, DNS to Python always.
    Falls back to pure Python url_validator.py on ImportError.
    """
    if _USE_RUST:
        safe, hostname = _rust_validate(url if url else "")
        if not safe:
            return False
        if not hostname:
            return True
        # DNS resolution stays in Python
        from apps.core.security.url_validator import _resolve_hostname  # noqa: PLC0415
        resolved_ip = _resolve_hostname(hostname)
        if resolved_ip is None:
            return True  # Can't resolve = allow (matches current behavior)
        return _rust_check_ip(str(resolved_ip))
    # Python fallback
    from apps.core.security.url_validator import is_safe_url as _py  # noqa: PLC0415
    return _py(url)
```

### Integration Points (Minimal Changes)

Only ONE line changes in `url_validator.py`:

```python
# URLValidator.is_safe() — BEFORE:
def is_safe(self, url: str) -> bool:
    return is_safe_url(url)

# URLValidator.is_safe() — AFTER:
def is_safe(self, url: str) -> bool:
    from apps.core.security.ssrf_engine import is_safe_url as _dispatch  # noqa: PLC0415
    return _dispatch(url)
```

All existing `from apps.core.security.url_validator import is_safe_url` imports in tests continue working as the Python fallback path.

### Cargo.toml Addition

```toml
url = "2.5"
# regex already present (SPEC-021): regex = "1.10"
```

### lib.rs Changes

```rust
mod security;  // NEW

// In #[pymodule] block:
#[pymodule_export]
use super::security::validate_url_safety;
#[pymodule_export]
use super::security::check_resolved_ip;
```

### gravitea_rust.pyi Additions

```python
def validate_url_safety(url: str) -> tuple[bool, str]: ...
def check_resolved_ip(ip_str: str) -> bool: ...
```

## FFI Boundary Analysis

| Input | Size | FFI Overhead | Python Work | Rust Work | Net Gain |
|-------|------|-------------|-------------|-----------|----------|
| ~80 char URL (static checks) | ~80 bytes | ~0.3-0.5us | ~10-30us | ~1-3us | **+7-27us** |
| ~15 char resolved IP | ~15 bytes | ~0.3us | ~2-5us | ~0.1-0.3us | **+1.7-4.7us** |

## Critical Caveats

1. **`url` crate vs `urllib.parse.urlparse` quirks**: The Rust `url` crate follows WHATWG URL Standard; Python `urlparse` follows RFC 3986. Test these edge cases: `http://evil.com@safe.com` (credential parsing — `url` crate sees `evil.com` as username, `urlparse` also parses this correctly), `http://[::ffff:127.0.0.1]` (IPv4-mapped IPv6 in brackets), `http://0x7f000001` (hex IP — `url` crate may not parse as hostname).

2. **Octal IP parsing**: Python's `ipaddress` module rejects octal by default; the custom `_parse_ip()` handles it (lines 208-226). Rust must replicate: leading-zero digits → octal, zero-padded to 4 octets, each 0-255.

3. **Shortened IP expansion**: Python expands `127.1` → `127.0.0.1` (2-part: `a.0.0.b`; 3-part: `a.b.0.c`). This is non-standard. Rust must match exactly.

4. **DNS excluded**: Rust validates URL structure and static properties; Python resolves DNS and re-validates the resolved IP through `check_resolved_ip()`.

5. **DNS failure = allow**: Current behavior (line 152-157): when `_resolve_hostname()` returns `None`, the URL is allowed through. This is deliberate — blocking on DNS failure would break legitimate URLs with transient resolution issues.

6. **Adversarial URL corpus**: Must test with the same adversarial URLs as existing Python tests (`tests/constants.py` SSRF_* constants + `test_ssrf.py` inline URLs).

7. **`url` crate may reject some inputs**: The `url` crate requires a valid URL while `urlparse` is lenient. For inputs the `url` crate rejects (e.g., `http://0x7f000001/` may not parse), fall back to extracting the hostname via string manipulation and running IP parsing on it.

8. **Regex crate limitations**: No lookahead/lookbehind support. All 9 current patterns use basic regex only — confirmed compatible.

## Success Criteria

1. `cargo test` passes with >=20 security tests (each IP format, each CIDR range, edge cases, hostile inputs)
2. Adversarial URL corpus produces identical boolean results between Rust and Python (>=60 URLs)
3. All 5 IP format variants handled correctly (standard, decimal, hex, octal, shortened)
4. All 10 private CIDR ranges correctly identified
5. All 9 suspicious hostname patterns correctly matched
6. Cloud metadata IPs (`169.254.169.254`, `169.254.170.2`) correctly blocked
7. Benchmark shows >=3x speedup over Python CPU-bound portions
8. Fallback works without Rust extension (ImportError → Python path)
9. Docker image builds with security functions available
10. Full test suite passes with 0 regressions
11. Existing `test_ssrf.py` (SEC-SSRF-001 through SEC-SSRF-006) passes unmodified

## Test Strategy

### Test Location

```
backend/tests/rust_integration/test_security_022.py
```

### Test Categories

| Category | Count (est.) | Description |
|----------|-------------|-------------|
| IP format parity | 15 | 5 formats x 3 variations (safe, private, edge) |
| CIDR range parity | 12 | 10 ranges + boundary IPs |
| Suspicious hostname parity | 12 | 9 patterns + null byte + IPv6 prefix |
| Scheme/credential checks | 8 | Allowed/blocked schemes, credential-embedded URLs |
| DNS integration | 6 | Mocked DNS → private IP, public IP, DNS failure |
| Two-phase flow | 5 | validate_url_safety → check_resolved_ip integration |
| Fallback | 3 | ImportError simulation, toggle verification |
| Benchmark | 3 | validate_url_safety, check_resolved_ip, combined |
| Adversarial corpus | 1 | Full corpus parity (parametrized over ~60 URLs) |
| **Total** | **~65** | |

### Parity Test Pattern (Following SPEC-021)

```python
@pytest.mark.parametrize("url,expected", ADVERSARIAL_CORPUS)
def test_parity_rust_vs_python(url, expected):
    """Rust and Python must return identical boolean for every adversarial URL."""
    from apps.core.security.url_validator import is_safe_url as py_fn
    from apps.core.security.ssrf_engine import is_safe_url as rust_fn
    assert rust_fn(url) == py_fn(url) == expected
```

## Reference Documents

| Document | Purpose | Path |
|----------|---------|------|
| Current validator | Python implementation (338 lines) | `backend/apps/core/security/url_validator.py` |
| SSRF tests | Existing regression suite | `backend/tests/security/test_ssrf.py` |
| Test constants | SSRF_* test data | `backend/tests/constants.py` |
| SPEC-021 dispatcher | Reference pattern | `backend/apps/core/observability/observability_engine.py` |
| Rust lib entry | Module registration | `rust/gravitea-core/src/lib.rs` |
| Cargo dependencies | Crate versions | `rust/gravitea-core/Cargo.toml` |
| Roadmap | OPP-002 details | `Docs/Brainstorming/rust-pyo3-speckit-roadmap.md` section 8 |
| Acceleration opps | Deep analysis | `Docs/Brainstorming/rust-acceleration-opportunities.md` |
