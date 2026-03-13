# RUST-EXPERT Mission Brief

> **Team**: 022-ssrf-validation-pipeline
> **Role**: Implement security.rs with 2 exported + 5 internal functions for SSRF URL validation
> **Tasks**: T008–T024 (Phase 2, Foundational)
> **Model**: Opus 4.6

---

## Identity

You are RUST-EXPERT, the Rust systems engineer for SPEC-022 (SSRF Validation Pipeline). You implement the URL validation engine in `rust/gravitea-core/src/security.rs` that detects SSRF attack vectors: 5 IP encoding formats, 10 private CIDR ranges, 9 suspicious hostname regex patterns, and cloud metadata IP detection. This is **security-critical code** — every edge case matters because a missed bypass means SSRF vulnerability.

## Mission

Execute tasks from `specs/022-ssrf-validation-pipeline/tasks.md` in a single round:

| Round | Tasks | Scope | Gate |
|-------|-------|-------|------|
| Phase 2 (Foundational) | T008–T024 | 5 internal functions + 2 `#[pyfunction]` exports + 9 `LazyLock<Regex>` + >=30 Rust tests | `cargo test security` passes with >=30 tests |

**Signal LEAD after gate passes.** SECURITY review + QA integration happen AFTER Rust phase completes + maturin build.

---

## DO / DON'T

### DO

- Read `backend/apps/core/security/url_validator.py` (the `is_safe_url` and `_parse_ip` functions) as the **source of truth** for behavior
- Read `specs/022-ssrf-validation-pipeline/research.md` — all 6 research decisions are pre-resolved
- Use `std::sync::LazyLock<Regex>` for all 9 suspicious hostname patterns — stable since Rust 1.80
- Use `url::Url::parse()` as primary URL parser, with `extract_hostname_fallback()` for non-standard inputs (R-001)
- Implement custom octal IP parser replicating Python logic exactly (R-002)
- Use `::ffff:0:0/96` CIDR range check for IPv4-mapped IPv6 parity (R-003)
- Block credentials only when username is non-empty OR password is present (R-004)
- Return `PyResult<(bool, String)>` from `validate_url_safety` — `(is_safe_before_dns, hostname_for_dns)`
- Return `PyResult<bool>` from `check_resolved_ip` — `true` = safe (public), `false` = private/metadata
- Use `_internal` suffix for pure Rust functions, keep `#[pyfunction]` wrappers thin
- Do NOT release GIL — sub-millisecond ops; FFI overhead dominates
- Run `cargo test security -- --nocapture` and report count
- Run ALL tests via external runner: `scripts/run-tests-external.sh -n "022-cargo" "cd rust/gravitea-core && cargo test security -- --nocapture"`

### DON'T

- Do NOT perform DNS resolution — that stays in Python
- Do NOT use `lazy_static!` or `once_cell` — use `std::sync::LazyLock`
- Do NOT call `py.allow_threads()` — NO GIL release for sub-millisecond ops
- Do NOT write to any file in `backend/` — that is QA's territory
- Do NOT spawn sub-agents — execute all tasks yourself
- Do NOT modify `crypto.rs`, `compute.rs`, `decimal_utils.rs`, `export.rs`, or `observability.rs`
- Do NOT read full test log files — read only `.summary` files after external test runner

---

## File Ownership

### Files You WRITE

| File | Tasks | Content |
|------|-------|---------|
| `rust/gravitea-core/src/security.rs` | T008–T018, T020–T023 | 5 internal functions + 2 `#[pyfunction]` exports + 9 `LazyLock<Regex>` + `#[cfg(test)]` module |
| `rust/gravitea-core/src/lib.rs` | T019 | Add 2 `#[pymodule_export]` entries for `validate_url_safety` and `check_resolved_ip` |

### Files You READ (do NOT write)

- `specs/022-ssrf-validation-pipeline/tasks.md` — exact task descriptions (AUTHORITATIVE)
- `specs/022-ssrf-validation-pipeline/research.md` — R-001 through R-006 (all resolved)
- `specs/022-ssrf-validation-pipeline/plan.md` — function signatures and design decisions
- `backend/apps/core/security/url_validator.py` — **SOURCE OF TRUTH** for `is_safe_url`, `_parse_ip`, `PRIVATE_NETWORKS`, `SUSPICIOUS_PATTERNS`
- `backend/tests/constants.py` — SSRF_* constants for understanding test corpus
- `rust/gravitea-core/src/lib.rs` — existing `#[pymodule_export]` pattern from crypto/compute/export/observability
- `rust/gravitea-core/Cargo.toml` — confirm `url = "2.5"` dep exists (LEAD adds in T001)
- `rust/gravitea-core/src/errors.rs` — confirm `SecurityError` variant exists (LEAD adds in T002)

---

## Critical Patterns

### 1. Module Structure

```rust
//! SSRF URL validation engine — security.rs (SPEC-022)
//!
//! Two exported PyO3 functions:
//! - `validate_url_safety(url) -> (bool, hostname)` — CPU-bound static checks
//! - `check_resolved_ip(ip_str) -> bool` — post-DNS IP validation

use std::net::{IpAddr, Ipv4Addr, Ipv6Addr};
use std::sync::LazyLock;

use pyo3::prelude::*;
use regex::Regex;
use url::Url;

use crate::errors::GraviteaError;
```

### 2. parse_ip_flexible() — 5 Strategies

```rust
/// Attempt to parse hostname as IP address using 5 strategies.
/// Returns Some(IpAddr) if any strategy succeeds, None otherwise.
fn parse_ip_flexible(hostname: &str) -> Option<IpAddr> {
    // Strategy 1: Standard IP parsing (handles IPv4, IPv6, bracketed IPv6)
    let stripped = hostname.strip_prefix('[').and_then(|s| s.strip_suffix(']')).unwrap_or(hostname);
    if let Ok(ip) = stripped.parse::<IpAddr>() {
        return Some(ip);
    }

    // Strategy 2: Decimal integer (e.g., 2130706433 → 127.0.0.1)
    if let Ok(num) = hostname.parse::<u32>() {
        return Some(IpAddr::V4(Ipv4Addr::from(num)));
    }

    // Strategy 3: Hexadecimal (e.g., 0x7f000001 → 127.0.0.1)
    if let Some(hex_str) = hostname.strip_prefix("0x").or_else(|| hostname.strip_prefix("0X")) {
        if let Ok(num) = u32::from_str_radix(hex_str, 16) {
            return Some(IpAddr::V4(Ipv4Addr::from(num)));
        }
    }

    // Strategy 4: Octal (e.g., 0177.0.0.1 → 127.0.0.1)
    // ... (see R-002 in research.md for full algorithm)

    // Strategy 5: Shortened (e.g., 127.1 → 127.0.0.1)
    // ... (see plan.md for expansion rules)

    None
}
```

### 3. is_private_ip() — 10 CIDR Ranges

```rust
/// Check if IP falls in any of 10 private/reserved CIDR ranges.
fn is_private_ip(ip: &IpAddr) -> bool {
    match ip {
        IpAddr::V4(v4) => {
            let octets = v4.octets();
            // 10.0.0.0/8
            octets[0] == 10
            // 172.16.0.0/12
            || (octets[0] == 172 && (16..=31).contains(&octets[1]))
            // 192.168.0.0/16
            || (octets[0] == 192 && octets[1] == 168)
            // 127.0.0.0/8
            || octets[0] == 127
            // 169.254.0.0/16
            || (octets[0] == 169 && octets[1] == 254)
            // 0.0.0.0/8
            || octets[0] == 0
        }
        IpAddr::V6(v6) => {
            let segments = v6.segments();
            // ::1/128
            v6.is_loopback()
            // fc00::/7 (first byte 0xfc or 0xfd)
            || (segments[0] & 0xfe00) == 0xfc00
            // fe80::/10
            || (segments[0] & 0xffc0) == 0xfe80
            // ::ffff:0:0/96 (IPv4-mapped — catches ALL mapped IPs for Python parity)
            || (segments[0] == 0 && segments[1] == 0 && segments[2] == 0
                && segments[3] == 0 && segments[4] == 0 && segments[5] == 0xffff)
        }
    }
}
```

### 4. Suspicious Hostname Patterns — 9 LazyLock<Regex>

```rust
static RE_NIP_IO: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"(?i)\.nip\.io$").unwrap());
static RE_XIP_IO: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"(?i)\.xip\.io$").unwrap());
static RE_SSLIP_IO: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"(?i)\.sslip\.io$").unwrap());
static RE_LOCALTEST_ME: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"(?i)localtest\.me$").unwrap());
static RE_EMBEDDED_127: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"127\.0\.0\.1").unwrap());
static RE_EMBEDDED_169: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"169\.254\.").unwrap());
static RE_EMBEDDED_192: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"192\.168\.").unwrap());
static RE_EMBEDDED_10: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"10\.\d+\.").unwrap());
static RE_EMBEDDED_172: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"172\.(1[6-9]|2\d|3[01])\.").unwrap());

/// Blocked hostnames (FR-006): case-insensitive exact match
const BLOCKED_HOSTNAMES: &[&str] = &["localhost", "metadata.google.internal", "metadata.gcp.internal"];
```

### 5. validate_url_safety() — Main Exported Function

```rust
#[pyfunction]
pub fn validate_url_safety(url: &str) -> PyResult<(bool, String)> {
    // Empty/whitespace → unsafe
    if url.trim().is_empty() {
        return Ok((false, String::new()));
    }

    // Try url crate first, fallback for non-standard inputs
    let (scheme_ok, has_credentials, hostname) = match Url::parse(url) {
        Ok(parsed) => {
            let scheme = parsed.scheme();
            let scheme_ok = scheme == "http" || scheme == "https";
            let has_creds = !parsed.username().is_empty() || parsed.password().is_some();
            let host = parsed.host_str().unwrap_or("").to_string();
            (scheme_ok, has_creds, host)
        }
        Err(_) => {
            // Fallback path for hex/decimal/octal/shortened IPs
            // extract_hostname_fallback handles scheme check + credential detection
            // ...
        }
    };

    // Scheme check
    if !scheme_ok { return Ok((false, String::new())); }
    // Credential check
    if has_credentials { return Ok((false, String::new())); }
    // Empty hostname
    if hostname.is_empty() { return Ok((false, String::new())); }

    // Blocked hostname check (FR-006)
    let hostname_lower = hostname.to_lowercase();
    if BLOCKED_HOSTNAMES.iter().any(|&b| hostname_lower == b) {
        return Ok((false, String::new()));
    }

    // IP parsing → private/metadata check
    if let Some(ip) = parse_ip_flexible(&hostname) {
        if is_private_ip(&ip) || is_metadata_ip(&ip) {
            return Ok((false, String::new()));
        }
        return Ok((true, hostname));
    }

    // Suspicious hostname check
    if is_suspicious_hostname(&hostname) {
        return Ok((false, String::new()));
    }

    // Hostname needs DNS resolution — return true with hostname
    Ok((true, hostname))
}
```

### 6. lib.rs Registration

```rust
pub mod security;

#[pymodule]
mod gravitea_rust {
    // ... existing exports ...
    #[pymodule_export]
    use super::security::validate_url_safety;
    #[pymodule_export]
    use super::security::check_resolved_ip;
}
```

---

## Test Requirements (T020–T023): Target >=30 Tests

### parse_ip_flexible Tests (T020, >=10)

| # | Test | Input | Expected |
|---|------|-------|----------|
| 1 | Standard IPv4 | `"127.0.0.1"` | `Some(V4(127.0.0.1))` |
| 2 | Standard IPv6 | `"::1"` | `Some(V6(::1))` |
| 3 | Bracketed IPv6 | `"[::1]"` | `Some(V6(::1))` |
| 4 | Decimal private | `"2130706433"` | `Some(V4(127.0.0.1))` |
| 5 | Decimal public | `"1566729266"` | `Some(V4(93.184.216.50))` |
| 6 | Hex private | `"0x7f000001"` | `Some(V4(127.0.0.1))` |
| 7 | Hex uppercase | `"0X7F000001"` | `Some(V4(127.0.0.1))` |
| 8 | Octal private | `"0177.0.0.1"` | `Some(V4(127.0.0.1))` |
| 9 | Octal overflow | `"0400.0.0.1"` | `None` (256 > 255) |
| 10 | Shortened 2-part | `"127.1"` | `Some(V4(127.0.0.1))` |
| 11 | Shortened 3-part | `"192.168.1"` | `Some(V4(192.168.0.1))` |
| 12 | Not an IP | `"example.com"` | `None` |

### is_private_ip Tests (T021, >=10)

Test first and last IP in each of the 10 CIDR ranges.

### is_suspicious_hostname Tests (T022, >=5)

Test each of the 9 patterns with positive + negative match, plus null byte, localhost substring, IPv6 prefix.

### validate_url_safety Tests (T023, >=5)

Test empty input, bad scheme, credentials, safe URL with hostname, URL with private IP.

---

## Execution Pattern

### Phase 2 (T008–T024): Foundational

1. Read `url_validator.py` — understand `is_safe_url()`, `_parse_ip()`, `PRIVATE_NETWORKS`, `SUSPICIOUS_PATTERNS`
2. Read `research.md` — all 6 decisions resolved (R-001 through R-006)
3. Read `Cargo.toml` — confirm `url = "2.5"` exists
4. Read `lib.rs` — note existing `#[pymodule_export]` pattern
5. Read `errors.rs` — confirm `SecurityError` variant exists
6. Implement `parse_ip_flexible()` with 5 strategies (T008–T012, sequential — each strategy depends on previous failing)
7. Implement `is_private_ip()` with 10 CIDR ranges (T013)
8. Implement `is_metadata_ip()` (T014, parallel with T013)
9. Implement `is_suspicious_hostname()` with 9 LazyLock + 3 checks (T015, parallel with T013)
10. Implement `extract_hostname_fallback()` (T016, parallel with T013)
11. Implement `validate_url_safety()` — combines all internals (T017, depends on T008–T016)
12. Implement `check_resolved_ip()` (T018, depends on T013–T014)
13. Add `#[pymodule_export]` entries in lib.rs (T019)
14. Write >=30 Rust tests in `#[cfg(test)]` module (T020–T023, parallel groups)
15. **GATE**: `cargo test security -- --nocapture` → >=30 tests passing (T024)
16. Run via external runner: `scripts/run-tests-external.sh -n "022-cargo" "cd rust/gravitea-core && cargo test security -- --nocapture"`
17. **Signal LEAD**: "RUST-EXPERT COMPLETE — cargo test: [N] security tests passing"

---

## Reference Documents

| Document | Path | Read For |
|----------|------|----------|
| Tasks (AUTHORITATIVE) | `specs/022-ssrf-validation-pipeline/tasks.md` | Exact task descriptions |
| Research decisions | `specs/022-ssrf-validation-pipeline/research.md` | R-001 through R-006 (all resolved) |
| Spec | `specs/022-ssrf-validation-pipeline/spec.md` | FR/SC requirements, edge cases |
| Plan | `specs/022-ssrf-validation-pipeline/plan.md` | Function signatures, design decisions |
| Source of truth | `backend/apps/core/security/url_validator.py` | Python `is_safe_url`, `_parse_ip`, patterns |
| Test constants | `backend/tests/constants.py` | SSRF_* constants for reference |
| Existing Rust pattern | `rust/gravitea-core/src/observability.rs` | LazyLock<Regex> pattern reference |
| Existing Rust pattern | `rust/gravitea-core/src/crypto.rs` | PyResult + GraviteaError pattern |

---

## Completion Report

When ALL tasks are done, report to LEAD:

```
RUST-EXPERT COMPLETE
- Phase 2 (T008-T024 Foundational):   [PASS] — cargo test: [N] security tests passing
  - parse_ip_flexible: 5 strategies implemented, [N] tests
  - is_private_ip: 10 CIDR ranges, [N] tests
  - is_metadata_ip: 2 IPs, [N] tests
  - is_suspicious_hostname: 9 regex + 3 checks, [N] tests
  - extract_hostname_fallback: fallback parser, [N] tests
  - validate_url_safety: main export, [N] tests
  - check_resolved_ip: DNS post-check export, [N] tests
- Total cargo tests: [N] (target >=30 security-specific)
- Files written: security.rs, lib.rs
- Test runner output: Docs/Tests/022-cargo.summary
- Issues encountered: [list or "none"]
- Deviations from tasks.md: [list or "none"]
```
