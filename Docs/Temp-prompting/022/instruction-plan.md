# Speckit Context: SSRF Validation Pipeline — PLAN Phase (SPEC-022)

> **Phase**: PLAN — Design implementation plan, research decisions, task breakdown
> **Priority**: HIGH | **Wave**: 3 (parallel with SPEC-019)
> **Produces**: `plan.md`, `research.md`, `quickstart.md`
> **Does NOT produce**: data-model.md, api-contract.md

---

## Mission

Design the implementation plan for replacing CPU-bound URL validation (IP parsing, CIDR checks, hostname regex) with Rust. DNS resolution stays in Python. This is a security-critical path — correctness trumps performance.

## Team Architecture

| Agent | Subagent Type | Model | Role |
|-------|--------------|-------|------|
| ORCHESTRATOR (LEAD) | system-architect | Opus 4.6 | Coordinates, validates, documentation |
| RUST-EXPERT | general-purpose | Opus 4.6 | Implements security.rs |
| SECURITY | security-engineer | Opus 4.6 | Reviews SSRF bypass edge cases |
| QA | quality-engineer | Sonnet 4.6 | Adversarial URL corpus, equivalence tests |

### Sequential-Thinking MCP

- **MANDATORY**: RUST-EXPERT (IP parsing edge cases), SECURITY (SSRF bypass analysis)
- **NOT required**: QA

## Current Python Implementation (Exact Source Map)

These are the exact functions to port. Line numbers from `backend/apps/core/security/url_validator.py` (338 lines total).

### Constants (lines 19–46) — Port to Rust `const`/`static`

```
ALLOWED_SCHEMES = {"http", "https"}                           # line 19
BLOCKED_HOSTNAMES = {"localhost", "metadata.google.internal",  # line 22-26
                     "metadata.gcp.internal"}
METADATA_IPS = {"169.254.169.254", "169.254.170.2"}           # line 29-32
PRIVATE_NETWORKS = [                                           # line 35-46
    "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16",
    "127.0.0.0/8", "169.254.0.0/16", "0.0.0.0/8",
    "::1/128", "fc00::/7", "fe80::/10", "::ffff:0:0/96"
]
```

### `is_safe_url()` (lines 88–159) — Orchestration logic; port STATIC checks to Rust

**Critical flow to replicate:**
1. `url` empty/None/not-str → `return False` (lines 106-111)
2. `urlparse(url)` → extract scheme, hostname, username (lines 114-117)
3. Scheme check: not in `{"http", "https"}` → `return False` (lines 120-122)
4. Credentials check: `parsed.username or parsed.password` → `return False` (lines 125-126)
5. Empty hostname → `return False` (lines 129-131)
6. Blocked hostnames → `return False` (lines 136-137)
7. `_parse_ip(hostname)` → if IP found:
   - `_is_private_ip(ip)` → `return False` (lines 142-143)
   - `str(ip) in METADATA_IPS` → `return False` (lines 144-145)
   - (else: IP is public → `return True`)
8. Else (hostname, not IP):
   - `_is_suspicious_hostname(hostname_lower)` → `return False` (lines 148-149)
   - `_resolve_hostname(hostname)` → **STAYS IN PYTHON** (lines 152-157)
   - If resolved: `_is_private_ip` + metadata check on resolved IP

**Two-function split point**: Steps 1-8a go into `validate_url_safety()`. Step 8b (DNS) stays in Python. Then `check_resolved_ip()` validates the resolved IP.

### `_parse_ip()` (lines 162–246) — 5 IP Format Strategies

Each strategy must be replicated **exactly** in Rust's `parse_ip_flexible()`:

**Strategy 1: Standard** (lines 184-188)
```python
ipaddress.ip_address(hostname)  # Handles IPv4, IPv6, bracketed IPv6
```
→ Rust: `hostname.parse::<IpAddr>()` + strip `[...]` brackets first

**Strategy 2: Decimal integer** (lines 191-196) — e.g., `2130706433` → `127.0.0.1`
```python
if hostname.isdigit():
    decimal_ip = int(hostname)
    if 0 <= decimal_ip <= 0xFFFFFFFF:
        return ipaddress.ip_address(decimal_ip)
```
→ Rust: `hostname.parse::<u32>()` → `Ipv4Addr::from(u32_val)`

**Strategy 3: Hexadecimal** (lines 200-205) — e.g., `0x7f000001` → `127.0.0.1`
```python
if hostname.lower().startswith("0x"):
    hex_ip = int(hostname, 16)
    if 0 <= hex_ip <= 0xFFFFFFFF:
        return ipaddress.ip_address(hex_ip)
```
→ Rust: strip `0x`/`0X` → `u32::from_str_radix(stripped, 16)` → `Ipv4Addr::from(val)`

**Strategy 4: Octal** (lines 208-226) — e.g., `0177.0.0.1` → `127.0.0.1`
```python
parts = hostname.split(".")
for part in parts:
    if part.startswith("0") and len(part) > 1 and part.isdigit():
        octal_parts.append(int(part, 8))  # ← OCTAL parse
    else:
        octal_parts.append(int(part))     # ← DECIMAL parse
while len(octal_parts) < 4:
    octal_parts.append(0)                 # ← PAD to 4 octets
```
→ Rust: split on `.`, detect leading-zero → `u8::from_str_radix(part, 8)`, else decimal. Pad to 4. Validate each 0-255.

**Strategy 5: Shortened** (lines 228-244) — e.g., `127.1` → `127.0.0.1`
```python
if len(parts) == 2:  expanded = f"{parts[0]}.0.0.{parts[1]}"   # a.b → a.0.0.b
if len(parts) == 3:  expanded = f"{parts[0]}.{parts[1]}.0.{parts[2]}"  # a.b.c → a.b.0.c
```
→ Rust: exact same expansion logic, then parse as standard IP.

**CRITICAL**: Strategies must be tried IN ORDER (standard → decimal → hex → octal → shortened). Octal and shortened share the "has dots" condition — octal is tried first because `hostname.replace(".", "").isdigit()` check on line 229 would pass for octal too, but Python's logic separates them.

### `_is_private_ip()` (lines 249–266) — 10 CIDR Range Checks

```python
for network in PRIVATE_NETWORKS:
    try:
        if ip in network:
            return True
    except TypeError:  # IPv4/IPv6 mismatch
        continue
```

→ Rust: Pre-compute start/end for each range. Use `IpAddr` matching with IPv4/IPv6 variants. The `TypeError` catch handles IPv4 address tested against IPv6 range — Rust naturally avoids this by matching on `IpAddr::V4`/`V6`.

**All 10 ranges (from lines 35-46):**

| # | CIDR | First IP | Last IP | Type |
|---|------|----------|---------|------|
| 1 | `10.0.0.0/8` | `10.0.0.0` | `10.255.255.255` | RFC 1918 |
| 2 | `172.16.0.0/12` | `172.16.0.0` | `172.31.255.255` | RFC 1918 |
| 3 | `192.168.0.0/16` | `192.168.0.0` | `192.168.255.255` | RFC 1918 |
| 4 | `127.0.0.0/8` | `127.0.0.0` | `127.255.255.255` | Loopback |
| 5 | `169.254.0.0/16` | `169.254.0.0` | `169.254.255.255` | Link-local |
| 6 | `0.0.0.0/8` | `0.0.0.0` | `0.255.255.255` | "This" network |
| 7 | `::1/128` | `::1` | `::1` | IPv6 loopback |
| 8 | `fc00::/7` | `fc00::` | `fdff:ffff:...:ffff` | IPv6 ULA |
| 9 | `fe80::/10` | `fe80::` | `febf:ffff:...:ffff` | IPv6 link-local |
| 10 | `::ffff:0:0/96` | `::ffff:0.0.0.0` | `::ffff:255.255.255.255` | IPv4-mapped IPv6 |

### `_is_suspicious_hostname()` (lines 269–315) — 9 Regex + 2 Extra Checks

**9 regex patterns (lines 284-294):**

| # | Pattern | Target |
|---|---------|--------|
| 1 | `\.nip\.io$` | nip.io wildcard DNS |
| 2 | `\.xip\.io$` | xip.io wildcard DNS |
| 3 | `\.sslip\.io$` | sslip.io wildcard DNS |
| 4 | `localtest\.me$` | localtest.me alias |
| 5 | `127\.0\.0\.1` | Embedded loopback |
| 6 | `169\.254\.` | Embedded link-local |
| 7 | `192\.168\.` | Embedded RFC 1918 |
| 8 | `10\.\d+\.` | Embedded 10.x |
| 9 | `172\.(1[6-9]\|2\d\|3[01])\.` | Embedded 172.16-31 |

**Additional checks (lines 300-313):**
- Null byte: `"\x00" in hostname or "%00" in hostname` (line 301)
- `"localhost" in hostname` (line 280) — substring match, NOT regex
- IPv6 private prefix: `hostname.startswith("fd"/"fc"/"fe80")` + `remaining.isalnum()` (lines 308-313)

→ Rust: Use `LazyLock<Regex>` for the 9 patterns (same pattern as `observability.rs`). String methods for null byte and "localhost" substring. Manual prefix check for IPv6.

**CRITICAL**: The `"localhost" in hostname` check (line 280) is a substring check, NOT a regex. It catches `sub.localhost.evil.com`. This MUST remain a substring check in Rust.

### `_resolve_hostname()` (lines 318–337) — STAYS IN PYTHON

```python
infos = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
if infos:
    addr = infos[0][4][0]
    return ipaddress.ip_address(addr)
```

This function is NOT ported. It's imported by `ssrf_engine.py` for the DNS phase.

## Target Rust Module: `security.rs`

### Exported PyO3 Functions (2)

```rust
/// Phase 1: All CPU-bound static checks on a URL string.
/// Returns (false, "") if unsafe — caller stops immediately.
/// Returns (true, "") if safe (hostname was IP, validated as public).
/// Returns (true, "hostname.com") if static checks pass but DNS resolution needed.
#[pyfunction]
pub fn validate_url_safety(url: &str) -> PyResult<(bool, String)> { ... }

/// Phase 3: Validate a DNS-resolved IP string against private CIDR + metadata IPs.
/// Returns true if public (safe), false if private/metadata (unsafe).
#[pyfunction]
pub fn check_resolved_ip(ip_str: &str) -> PyResult<bool> { ... }
```

### Internal Rust Functions (4, NOT exported)

```rust
/// 5-strategy IP parsing: standard → decimal → hex → octal → shortened
fn parse_ip_flexible(hostname: &str) -> Option<IpAddr> { ... }

/// Check IP against 10 compiled CIDR ranges
fn is_private_ip(ip: &IpAddr) -> bool { ... }

/// Check IP against 2 cloud metadata addresses
fn is_metadata_ip(ip: &IpAddr) -> bool { ... }

/// 9 LazyLock<Regex> patterns + null byte + localhost substring + IPv6 prefix
fn is_suspicious_hostname(hostname: &str) -> bool { ... }
```

### Static Patterns (LazyLock<Regex>)

Follow the exact pattern from `observability.rs` (lines 21-30):

```rust
use regex::Regex;
use std::sync::LazyLock;

static RE_NIP_IO: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"(?i)\.nip\.io$").unwrap());
static RE_XIP_IO: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"(?i)\.xip\.io$").unwrap());
// ... 7 more patterns
```

All 9 patterns MUST be case-insensitive (`(?i)` prefix) to match Python's `re.search()` default behavior.

## Python Dispatcher: `ssrf_engine.py`

**New file**: `backend/apps/core/security/ssrf_engine.py`

Follows the SPEC-021 `observability_engine.py` pattern exactly (see `backend/apps/core/observability/observability_engine.py`):

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

## Integration Points (Minimal Changes)

### 1. `url_validator.py` — ONE method change

```python
# URLValidator.is_safe() — line 75-85
# BEFORE:
def is_safe(self, url: str) -> bool:
    return is_safe_url(url)

# AFTER:
def is_safe(self, url: str) -> bool:
    from apps.core.security.ssrf_engine import is_safe_url as _dispatch  # noqa: PLC0415
    return _dispatch(url)
```

All existing `from apps.core.security.url_validator import is_safe_url` imports in tests continue working — they call the Python fallback path directly.

### 2. `lib.rs` — Add 3 lines

```rust
mod security;  // NEW — after line 8 (mod observability;)

// In #[pymodule] block — after line 44:
#[pymodule_export]
use super::security::validate_url_safety;
#[pymodule_export]
use super::security::check_resolved_ip;
```

### 3. `Cargo.toml` — Add 1 dependency

```toml
url = "2.5"
# regex = "1.10" already present (from SPEC-021, line 26)
```

### 4. `gravitea_rust.pyi` — Add 2 stubs

```python
def validate_url_safety(url: str) -> tuple[bool, str]:
    """Phase 1: CPU-bound static SSRF checks on a URL string.

    Returns (false, "") if unsafe, (true, "") if safe (public IP),
    (true, "hostname") if hostname needs DNS resolution.
    """
    ...

def check_resolved_ip(ip_str: str) -> bool:
    """Phase 3: Validate DNS-resolved IP against private CIDR ranges.

    Returns true if public (safe), false if private/metadata (unsafe).
    """
    ...
```

### 5. `errors.rs` — Add SecurityError variant

```rust
#[error("Security error: {0}")]
SecurityError(String),  // NEW — after ExportError(String) on line 21

// In From<GraviteaError> for PyErr — after ExportError match:
GraviteaError::SecurityError(msg) => PyRuntimeError::new_err(msg),
```

## Adversarial URL Corpus (Extracted from Tests)

### From `tests/constants.py` (lines 45-73)

| Category | Values | Expected |
|----------|--------|----------|
| `SSRF_INTERNAL_HOSTS` | `localhost`, `127.0.0.1`, `::1`, `0.0.0.0`, `127.0.0.2`, `127.1`, `[::1]` | All `False` |
| `SSRF_METADATA_HOSTS` | `169.254.169.254`, `metadata.google.internal`, `169.254.170.2`, `fd00:ec2::254` | All `False` |
| `SSRF_PRIVATE_NETWORKS` | `10.0.0.1`, `172.16.0.1`, `192.168.1.1` | All `False` |
| `SSRF_DANGEROUS_SCHEMES` | `file:///etc/passwd`, `file:///etc/shadow`, `gopher://localhost:25/`, `dict://localhost:11211/` | All `False` |

### From `test_ssrf.py` Inline URLs

| Test | URLs | Expected |
|------|------|----------|
| SEC-SSRF-001 (ports) | `http://127.0.0.1:{22,80,443,3306,5432,6379,8080,9200}/` | All `False` |
| SEC-SSRF-001 (zero) | `http://0.0.0.0/`, `http://0.0.0.0:8080/`, `http://0/` | All `False` |
| SEC-SSRF-002 (ipv6) | `http://[::1]/`, `http://[::1]:8080/`, `http://[0:0:0:0:0:0:0:1]/`, `http://[::ffff:127.0.0.1]/` | All `False` |
| SEC-SSRF-002 (ipv6 private) | `http://[fc00::1]/`, `http://[fd00::1]/`, `http://[fe80::1]/` | All `False` |
| SEC-SSRF-003 (aws) | `http://169.254.169.254/latest/api/token`, `.../dynamic/instance-identity/document`, `.../user-data` | All `False` |
| SEC-SSRF-003 (gcp) | `http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/...` | All `False` |
| SEC-SSRF-004 (rfc1918) | `10.0.0.1`, `10.255.255.254`, `10.1.2.3`, `172.16.0.1`, `172.31.255.254`, `172.20.1.1`, `192.168.0.1`, `192.168.255.254`, `192.168.1.100` | All `False` |
| SEC-SSRF-005 (schemes) | `ftp://`, `sftp://`, `ldap://`, `ssh://`, `telnet://`, `data:`, `javascript:` | All `False` |
| SEC-SSRF-005 (file) | `file:///etc/passwd`, `.../shadow`, `.../proc/self/environ`, `.../var/log/auth.log`, `file://localhost/etc/passwd`, `FILE:///etc/passwd` | All `False` |
| SEC-SSRF-006 (creds) | `http://user:pass@internal.service/`, `http://admin:admin@127.0.0.1/`, `http://root:toor@192.168.1.1/` | All `False` |
| SEC-SSRF-006 (bypass) | `http://127.0.0.1%00.example.com/`, `http://127.0.0.1%2f.example.com/`, `http://127.0.0.1%252f.example.com/`, `http://127.1/`, `http://2130706433/`, `http://0x7f000001/`, `http://0177.0.0.1/` | All `False` |
| SEC-SSRF-006 (invalid) | `""`, `None`, `"not-a-url"`, `"://missing-scheme.com"`, `"http://"`, `"http:///path"` | All `False` |
| SEC-SSRF-006 (legit) | `https://api.example.com/webhook`, `https://hooks.slack.com/services/xxx`, `https://api.stripe.com/v1/charges`, `http://httpbin.org/post` | All `True` |
| SEC-SSRF-006 (dns rebinding) | `http://localtest.me/`, `http://127.0.0.1.nip.io/`, `http://spoofed.127.0.0.1.nip.io/` | `False` (suspicious) |

### Additional Adversarial URLs (NOT in existing tests — add to corpus)

| Category | URL | Expected | Why |
|----------|-----|----------|-----|
| Decimal private | `http://167772161/` (10.0.0.1) | `False` | Decimal encoding of RFC 1918 |
| Hex private | `http://0xc0a80101/` (192.168.1.1) | `False` | Hex encoding of RFC 1918 |
| Octal private | `http://012.0.0.1/` (10.0.0.1) | `False` | Octal first octet |
| Mixed octal | `http://0177.0.0.01/` (127.0.0.1) | `False` | Mixed octal+decimal |
| Shortened private | `http://10.1/` (10.0.0.1) | `False` | 2-part IP |
| 3-part shortened | `http://192.168.1/` (192.168.0.1) | `False` | 3-part IP |
| IPv4-mapped v6 | `http://[::ffff:10.0.0.1]/` | `False` | v4-mapped RFC 1918 |
| Credential injection | `http://evil.com@safe.com/` | `False` | userinfo parsing |
| Null byte host | `http://safe.com%00.evil.com/` | `False` | Null byte bypass |
| sslip.io | `http://10.0.0.1.sslip.io/` | `False` | sslip.io wildcard |
| xip.io | `http://192.168.1.1.xip.io/` | `False` | xip.io wildcard |
| Public IP (explicit) | `http://93.184.216.34/` (example.com) | `True` | Public IPv4 |
| Long URL | `https://example.com/` + `a`*2048 | `True` | Long URL not unsafe |
| Double-encoded | `http://127.0.0.1%252f/` | `False` | Loopback (hostname parsed as `127.0.0.1%252f`) |

**Total corpus**: ~80+ adversarial URLs covering all 5 IP formats, all 10 CIDR ranges, all 9 hostname patterns, edge cases, and legitimate URLs.

## Implementation Phases (Detailed)

### Phase 1: Adversarial Corpus & Cargo Setup (LEAD + QA)
- **Risk**: HIGH (security correctness depends on test quality)
- **Blocks**: Phase 2, Phase 3
- **Parallelizable with**: Nothing — foundational
- Tasks:
  1. Extract all URLs from `tests/constants.py` SSRF_* constants + `test_ssrf.py` inline URLs
  2. Add the "Additional Adversarial URLs" from the table above
  3. Run each URL through Python `is_safe_url()` to capture expected output → create `ADVERSARIAL_CORPUS` list of `(url, expected_bool)` tuples
  4. Add `url = "2.5"` to `Cargo.toml` (line 27, after `regex = "1.10"`)
  5. Add `SecurityError(String)` variant to `errors.rs`
  6. Add `mod security;` to `lib.rs` (line 9)
  7. Create empty `rust/gravitea-core/src/security.rs` with module doc + imports

### Phase 2: Rust Implementation (RUST-EXPERT)
- **Risk**: HIGH (security-critical code)
- **Blocked by**: Phase 1 (needs corpus + Cargo setup)
- **Blocks**: Phase 3
- Tasks:
  1. Implement `parse_ip_flexible()` — all 5 IP format strategies
  2. Implement `is_private_ip()` — all 10 CIDR ranges as compiled prefix checks
  3. Implement `is_metadata_ip()` — 2 cloud metadata IPs
  4. Implement `is_suspicious_hostname()` — 9 `LazyLock<Regex>` + null byte + localhost substring + IPv6 prefix
  5. Implement `validate_url_safety()` — URL parsing via `url` crate + fallback hostname extraction
  6. Implement `check_resolved_ip()` — parse IP string + private/metadata check
  7. Add `#[pymodule_export]` entries in `lib.rs` pymodule block
  8. Write ≥30 Rust-native `#[test]` tests against the adversarial corpus
  9. Run `cargo test` — all pass

### Phase 3: Security Review (SECURITY)
- **Risk**: HIGH (SSRF bypass = critical vulnerability)
- **Blocked by**: Phase 2 (needs security.rs to review)
- **Blocks**: Phase 4 (cannot integrate unreviewed security code)
- **Parallelizable with**: Nothing — sequential gate
- Tasks:
  1. Review `security.rs` for SSRF bypass vectors
  2. Test `url` crate vs `urlparse` divergences on edge cases:
     - `http://evil.com@safe.com` — credential parsing
     - `http://[::ffff:127.0.0.1]` — IPv4-mapped IPv6
     - `http://0x7f000001` — hex IP (url crate may reject)
     - `http://` (empty hostname) — error handling
  3. Verify all 5 IP format variants: add missing test cases if any
  4. Verify all 10 CIDR ranges: boundary IPs (first and last in each range)
  5. Verify all 9 suspicious hostname patterns: construct positive + negative match
  6. Sign off OR request changes → loop back to Phase 2

### Phase 4: Python Integration & Equivalence Tests (QA)
- **Risk**: MEDIUM
- **Blocked by**: Phase 3 (security sign-off required)
- Tasks:
  1. Create `backend/apps/core/security/ssrf_engine.py` (dispatcher, see code above)
  2. Modify `url_validator.py:URLValidator.is_safe()` to delegate to `ssrf_engine.py`
  3. Update `backend/gravitea_rust.pyi` with 2 new function stubs
  4. Build Rust wheel: `VIRTUAL_ENV=$(pwd)/backend/venv-wsl maturin develop --manifest-path rust/gravitea-core/Cargo.toml --release`
  5. Create `backend/tests/rust_integration/test_security_022.py`:
     - Parametrized parity test over full adversarial corpus (~80 URLs)
     - Individual IP format tests (5 formats × 3 variations)
     - Individual CIDR range tests (10 ranges × boundary IPs)
     - Individual suspicious hostname tests (9 patterns × positive/negative)
     - DNS integration tests (mocked — private, public, failure)
     - Two-phase flow tests (validate_url_safety → check_resolved_ip)
     - Fallback tests (ImportError simulation)
     - Benchmarks (validate_url_safety, check_resolved_ip, combined)
  6. Run existing `test_ssrf.py` — 0 modifications, all pass (SC-010)
  7. Benchmark: ≥3x speedup on CPU portions (SC-002)

### Phase 5: Docker + Regression (LEAD)
- **Risk**: LOW
- **Blocked by**: Phase 4
- Tasks:
  1. Build Docker: `docker compose build web`
  2. Verify Rust functions available in container:
     `docker compose run --rm --entrypoint python web -c "from gravitea_rust import validate_url_safety, check_resolved_ip; print('OK')"`
  3. Run security tests in container:
     `docker compose run --rm --entrypoint python web -m pytest tests/security/test_ssrf.py --tb=short -q --override-ini='addopts='`
  4. Run SPEC-022 integration tests in container:
     `docker compose run --rm --entrypoint python web -m pytest tests/rust_integration/test_security_022.py --tb=short -q --override-ini='addopts='`
  5. Full regression: `docker compose run --rm --entrypoint python web -m pytest tests/ --tb=short -q --override-ini='addopts='`
  6. Update `specs/022-ssrf-validation-pipeline/quickstart.md`

## Research Topics (for research.md)

| ID | Topic | Decision Needed | Assigned To | Priority |
|----|-------|----------------|-------------|----------|
| R-001 | Python `urlparse` vs Rust `url` crate parsing differences | Document divergences; determine if `url` crate rejection of hex/decimal IPs requires fallback hostname extraction via string split | SECURITY | HIGH |
| R-002 | Octal IP handling in Rust | Rust has no stdlib octal IP parser; must implement custom `split(".") → for_each(detect_leading_zero → from_str_radix(8))` | RUST-EXPERT | HIGH |
| R-003 | IPv4-mapped IPv6 (`::ffff:x.x.x.x`) | Verify `IpAddr::V6(v6).to_ipv4_mapped()` correctly extracts inner IPv4 for private range check | SECURITY | HIGH |
| R-004 | URL with userinfo (`evil.com@safe.com`) | `url` crate parses username correctly but may differ on edge cases like `http://@host/` | SECURITY | MEDIUM |
| R-005 | `url` crate hostname extraction for non-standard inputs | When `url::Url::parse()` fails (e.g., `http://0x7f000001/`), need fallback: extract substring between `://` and next `/` or `:` or `?` | RUST-EXPERT | HIGH |
| R-006 | Regex crate pattern compatibility | Confirm all 9 Python patterns compile in Rust `regex` crate (no lookahead needed — already verified in SPEC-021) | RUST-EXPERT | LOW |

## Critical Caveats

### 1. `url` Crate May Reject Valid SSRF Vectors

The Rust `url` crate follows WHATWG URL Standard and may REJECT inputs that Python `urlparse` accepts (RFC 3986). Specifically:
- `http://0x7f000001/` — hex IP may not be recognized as hostname
- `http://2130706433/` — decimal IP may not be recognized
- `http://0177.0.0.1/` — octal IP will not be recognized

**Mitigation**: When `url::Url::parse()` fails, fall back to manual hostname extraction:
```rust
fn extract_hostname_fallback(url: &str) -> Option<&str> {
    let after_scheme = url.strip_prefix("http://")
        .or_else(|| url.strip_prefix("https://"))?;
    // Strip userinfo
    let after_at = after_scheme.rsplit_once('@').map_or(after_scheme, |(_, h)| h);
    // Take until port/path/query
    let end = after_at.find(&[':', '/', '?', '#'][..]).unwrap_or(after_at.len());
    Some(&after_at[..end])
}
```

### 2. Octal IP Parsing Has No Stdlib Support

Neither Python's `ipaddress` nor Rust's `std::net` parse octal IPs. The Python code has a custom parser (lines 208-226). Rust must replicate it exactly: split on `.`, detect leading-zero parts → parse as base-8, else base-10, pad to 4 octets, validate 0-255 each.

### 3. Shortened IP Expansion Is Non-Standard

Python expands `127.1` → `127.0.0.1` (2-part: a.0.0.b) and `192.168.1` → `192.168.0.1` (3-part: a.b.0.c). This is not standard IP parsing behavior. Rust must replicate the exact expansion rules.

### 4. `"localhost" in hostname` Is Substring Match

The Python check at line 280 is `if "localhost" in hostname` — this is a SUBSTRING match, not an exact match. It catches `sub.localhost.evil.com`. Rust should use `hostname.contains("localhost")`.

### 5. IPv6 Prefix Check Has Specific Logic

Lines 308-313: After stripping the 2-char prefix (`fd`, `fc`) or 4-char prefix (`fe80`), it checks `remaining.isalnum()`. This means `fe80abc` is suspicious but `fe80.abc` is not. Rust must replicate: `hostname.starts_with("fe80")` → `hostname[4..].chars().all(|c| c.is_alphanumeric())`.

### 6. GIL NOT Released

Sub-millisecond operations — FFI overhead dominates. Do NOT call `py.allow_threads()` or `Python::with_gil()`. Follow SPEC-021 pattern (no GIL release).

## Existing Rust Patterns to Follow

| Pattern | Reference | Lesson |
|---------|-----------|--------|
| `LazyLock<Regex>` | `observability.rs:21-30` | Pre-compiled patterns, `(?i)` for case-insensitive |
| `#[pymodule_export]` | `lib.rs:19-44` | Must be `pub fn` in the module |
| Error variant | `errors.rs:6-21` | Add `SecurityError(String)` → `PyRuntimeError` |
| `.pyi` stubs | `gravitea_rust.pyi` | Docstring with Args/Returns/Raises |
| Dispatcher | `observability_engine.py` | `_USE_RUST` flag, lazy fallback import |
| Test location | `tests/rust_integration/` | NOT `tests/security/` — avoid conftest RLS conflicts |

## Maturin Build Command

```bash
VIRTUAL_ENV=$(pwd)/backend/venv-wsl maturin develop \
    --manifest-path rust/gravitea-core/Cargo.toml --release
```

## Success Criteria Mapping

| SC | Phase | Validated By |
|----|-------|-------------|
| SC-001 | Phase 4 | Parametrized parity test (~80 URLs) |
| SC-002 | Phase 4 | Benchmark ≥3x on 200 URL corpus |
| SC-003 | Phase 2+4 | 5 format-specific Rust + Python tests |
| SC-004 | Phase 2+4 | 10 range boundary tests |
| SC-005 | Phase 2+4 | 9 pattern positive/negative tests |
| SC-006 | Phase 2+4 | 2 metadata IP tests |
| SC-007 | Phase 4 | ImportError simulation test |
| SC-008 | Phase 5 | Docker container import + test |
| SC-009 | Phase 5 | Full suite 0 regressions |
| SC-010 | Phase 4 | `test_ssrf.py` passes unmodified |

## Reference Documents

| Document | Purpose | Path |
|----------|---------|------|
| Specify context | Architecture decisions, two-function rationale | `Docs/Temp-prompting/022/instruction-specify.md` |
| Formal spec | Technology-agnostic requirements | `specs/022-ssrf-validation-pipeline/spec.md` |
| Current validator | Python implementation (338 lines) | `backend/apps/core/security/url_validator.py` |
| SSRF tests | Existing regression suite (SEC-SSRF-001–006) | `backend/tests/security/test_ssrf.py` |
| Test constants | SSRF_* test data | `backend/tests/constants.py` |
| SPEC-021 dispatcher | Reference dispatcher pattern | `backend/apps/core/observability/observability_engine.py` |
| SPEC-021 Rust regex | LazyLock<Regex> pattern reference | `rust/gravitea-core/src/observability.rs` |
| Rust lib entry | Module registration pattern | `rust/gravitea-core/src/lib.rs` |
| Error types | GraviteaError enum | `rust/gravitea-core/src/errors.rs` |
| Cargo dependencies | Current crate versions | `rust/gravitea-core/Cargo.toml` |
| Type stubs | Python type hints for Rust functions | `backend/gravitea_rust.pyi` |
| Roadmap | OPP-002 details | `Docs/Brainstorming/rust-pyo3-speckit-roadmap.md` §8 |
