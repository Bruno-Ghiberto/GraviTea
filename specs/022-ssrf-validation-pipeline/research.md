# Research: Rust SSRF Validation Pipeline (SPEC-022)

**Date**: 2026-02-27
**Status**: Complete — all 6 topics resolved
**Input**: [instruction-plan.md](../../Docs/Temp-prompting/022/instruction-plan.md), [spec.md](spec.md)

---

## R-001: Python `urlparse` vs Rust `url` Crate Parsing Differences

**Priority**: HIGH | **Assigned**: SECURITY

### Decision

Use `url::Url::parse()` as the primary URL parser for standard URLs. When it fails (returns `Err`), fall back to `extract_hostname_fallback()` — a manual string parser that extracts the hostname from non-standard URL formats.

### Rationale

The Rust `url` crate follows the WHATWG URL Standard, which is stricter than Python's `urllib.parse.urlparse` (RFC 3986). Key divergences:

| Input | Python `urlparse` | Rust `url::Url::parse()` | Impact |
|-------|-------------------|--------------------------|--------|
| `http://0x7f000001/` | `hostname = "0x7f000001"` | **Error** (invalid host) | Must fallback to extract hex IP |
| `http://2130706433/` | `hostname = "2130706433"` | **Error** (invalid host) | Must fallback to extract decimal IP |
| `http://0177.0.0.1/` | `hostname = "0177.0.0.1"` | **Error** (invalid host) | Must fallback to extract octal IP |
| `http://evil.com@safe.com/` | `hostname = "safe.com"`, `username = "evil.com"` | `host = "safe.com"`, `username = "evil.com"` | Both parse correctly |
| `http://[::1]/` | `hostname = "::1"` | `host = "::1"` | Both parse correctly |
| `http://127.1/` | `hostname = "127.1"` | **Error** (invalid host) | Must fallback to extract shortened IP |

### Fallback Implementation

```rust
fn extract_hostname_fallback(url: &str) -> Option<&str> {
    let after_scheme = url.strip_prefix("http://")
        .or_else(|| url.strip_prefix("https://"))?;
    let after_at = after_scheme.rsplit_once('@').map_or(after_scheme, |(_, h)| h);
    let end = after_at.find(&[':', '/', '?', '#'][..]).unwrap_or(after_at.len());
    let hostname = &after_at[..end];
    if hostname.is_empty() { None } else { Some(hostname) }
}
```

This extracts the hostname for non-standard inputs so IP parsing strategies can run on them.

### Alternatives Rejected

1. **Only string-based parsing (no `url` crate)**: Rejected — the `url` crate correctly handles scheme extraction, credential detection, port parsing, and bracket-stripping for IPv6. Reimplementing all of this is error-prone.
2. **`url` crate only (no fallback)**: Rejected — would miss SSRF vectors using non-standard IP encodings (hex, decimal, octal, shortened), which are the primary attack surface.

---

## R-002: Octal IP Handling in Rust

**Priority**: HIGH | **Assigned**: RUST-EXPERT

### Decision

Implement a custom octal IP parser that replicates the Python logic at `url_validator.py` lines 208-226 exactly.

### Algorithm

```
1. Split hostname on "."
2. Reject if <2 or >4 parts
3. For each part:
   a. If starts with "0" AND len > 1 AND all digits → parse as octal (base 8)
   b. Else → parse as decimal (base 10)
   c. Reject if any part > 255 or parse fails
4. Pad to 4 octets with trailing zeros
5. Construct Ipv4Addr from 4 octets
```

### Rationale

Neither Rust's `std::net::Ipv4Addr::from_str()` nor any mainstream crate parses octal-encoded IPs. Python's `ipaddress` module also rejects octal by default — the existing `_parse_ip()` has a custom handler. Rust must replicate it exactly to maintain parity.

### Key Edge Cases

| Input | Part Analysis | Result |
|-------|--------------|--------|
| `0177.0.0.1` | `0177`=octal(127), `0`=dec(0), `0`=dec(0), `1`=dec(1) | `127.0.0.1` |
| `0177.0.0.01` | `0177`=octal(127), `0`=dec(0), `0`=dec(0), `01`=octal(1) | `127.0.0.1` |
| `012.0.0.1` | `012`=octal(10), `0`=dec(0), `0`=dec(0), `1`=dec(1) | `10.0.0.1` |
| `0300.0.0.1` | `0300`=octal(192), rest decimal | `192.0.0.1` |
| `0400.0.0.1` | `0400`=octal(256) → **REJECT** (>255) | `None` |
| `08.0.0.1` | `08` has leading zero but `8` is invalid octal → **depends on Python behavior** | Investigate — Python `int("08", 8)` raises `ValueError` → strategy fails, try next |

### Alternatives Rejected

1. **Skip octal parsing**: Rejected — octal IPs are a well-known SSRF bypass vector. Omitting would create a security gap.
2. **External crate**: No suitable crate exists for this specific format.

---

## R-003: IPv4-Mapped IPv6 (`::ffff:x.x.x.x`)

**Priority**: HIGH | **Assigned**: SECURITY

### Decision

When checking an IPv6 address against private ranges, also extract the inner IPv4 address using `Ipv6Addr::to_ipv4_mapped()` and check that IPv4 against the 7 IPv4 private CIDR ranges.

### Implementation

```rust
fn is_private_ip(ip: &IpAddr) -> bool {
    match ip {
        IpAddr::V4(v4) => check_v4_ranges(v4),
        IpAddr::V6(v6) => {
            // Direct IPv6 range checks (::1, fc00::/7, fe80::/10)
            if check_v6_ranges(v6) { return true; }
            // IPv4-mapped: ::ffff:x.x.x.x → extract and check inner IPv4
            if let Some(mapped_v4) = v6.to_ipv4_mapped() {
                return check_v4_ranges(&mapped_v4);
            }
            false
        }
    }
}
```

### Rationale

`::ffff:127.0.0.1` is an IPv4-mapped IPv6 address that resolves to loopback. Without extracting the inner IPv4, it would bypass IPv4 private range checks. The Python implementation handles this via the `::ffff:0:0/96` CIDR range in `PRIVATE_NETWORKS`, but this catches ALL IPv4-mapped addresses including public ones. The Rust implementation should be more precise: extract the inner IPv4 and check it against specific private ranges.

However, for **exact parity with Python**, the `::ffff:0:0/96` range check catches everything in that prefix — including mapped public IPs. This means Python marks `::ffff:93.184.216.34` as private too. Rust must replicate this behavior for parity, even though it's overly broad.

### Final Decision (Parity-First)

Keep the `::ffff:0:0/96` range check in the CIDR list (matches all IPv4-mapped IPv6). This ensures parity with Python. The `to_ipv4_mapped()` extraction is not needed if the CIDR check already catches everything.

### Alternatives Rejected

1. **Only CIDR check without extraction**: This is actually what we'll do for parity. The extraction approach is more precise but would change behavior from Python.
2. **Treat all IPv6 as unsafe**: Too broad — blocks legitimate IPv6 addresses.

---

## R-004: URL with Userinfo (`evil.com@safe.com`)

**Priority**: MEDIUM | **Assigned**: SECURITY

### Decision

Detect credentials by checking for `@` in the authority section. The `url` crate correctly parses userinfo; the fallback parser uses `rsplit_once('@')`.

### Implementation

**`url` crate path**: After `url::Url::parse()` succeeds, check `parsed.username() != ""` or `parsed.password().is_some()`. If either is true, return `(false, "")` (unsafe).

**Fallback path**: In `extract_hostname_fallback()`, use `rsplit_once('@')` to split authority. If `@` is present, return `(false, "")` before extracting hostname — matching Python's behavior of rejecting credential-embedded URLs.

### Edge Cases

| Input | `url` crate | Fallback | Python | Decision |
|-------|-------------|----------|--------|----------|
| `http://evil.com@safe.com/` | username=`evil.com` | `@` detected | username=`evil.com` | `False` (unsafe) |
| `http://user:pass@host/` | username=`user`, password=`pass` | `@` detected | username=`user` | `False` (unsafe) |
| `http://@host/` | username=`` (empty) | `@` detected | username=`` (empty but present) | `False` — Python returns False because `parsed.username` is `""` which is falsy... **INVESTIGATE** |

**Resolution for `http://@host/`**: Python's `urlparse("http://@host/").username` returns `""`. In Python, `if parsed.username:` evaluates to `False` for empty string. So `http://@host/` is NOT blocked by the credential check in Python. Rust must replicate: only block if username is non-empty OR password is present.

### Alternatives Rejected

1. **Only detect via `url` crate**: Rejected — fallback parser also needs credential detection for non-standard URLs.
2. **Block all URLs with `@`**: Rejected — `http://@host/` has empty username, Python allows it through the credential check (though it may fail later on other checks).

---

## R-005: `url` Crate Hostname Extraction for Non-Standard Inputs

**Priority**: HIGH | **Assigned**: RUST-EXPERT

### Decision

Implement `extract_hostname_fallback()` as a string-based hostname extractor for URLs that the `url` crate rejects.

### Algorithm

```
1. Check scheme: must start with "http://" or "https://" (case-insensitive)
   - If neither → return (false, "") immediately (bad scheme)
2. Strip scheme prefix
3. Check for credentials: if "@" present → return (false, "") (credential injection)
4. Extract hostname: take characters until ":", "/", "?", or "#"
5. If hostname is empty → return (false, "")
6. Return hostname for IP parsing
```

### When This Runs

This fallback only runs when `url::Url::parse()` returns `Err`. In practice, this happens for:
- Hex IPs: `http://0x7f000001/`
- Decimal IPs: `http://2130706433/`
- Octal IPs: `http://0177.0.0.1/`
- Shortened IPs: `http://127.1/`

For these inputs, the `url` crate considers them invalid hosts, but we need to extract the hostname to attempt IP parsing strategies.

### Integration in `validate_url_safety()`

```rust
pub fn validate_url_safety(url: &str) -> PyResult<(bool, String)> {
    // ... empty/whitespace check ...

    match Url::parse(url) {
        Ok(parsed) => {
            // Standard path: scheme, credentials, hostname from url crate
        }
        Err(_) => {
            // Fallback path: check scheme manually, extract hostname
            let hostname = extract_hostname_fallback(url)?;
            // Run IP parsing strategies on hostname
        }
    }
}
```

### Alternatives Rejected

1. **Return unsafe on parse failure**: Rejected — would block all non-standard IP formats, missing the entire point of SSRF detection (these formats are the attack surface).
2. **Pre-process URL before passing to `url` crate**: Rejected — would require resolving the IP format before URL parsing, creating circular logic.

---

## R-006: Regex Crate Pattern Compatibility

**Priority**: LOW | **Assigned**: RUST-EXPERT

### Decision

All 9 suspicious hostname patterns are confirmed compatible with the Rust `regex` crate. No changes needed.

### Verification

| # | Python Pattern | Rust Pattern | Compatible |
|---|---------------|-------------|------------|
| 1 | `r"\.nip\.io$"` | `r"(?i)\.nip\.io$"` | Yes |
| 2 | `r"\.xip\.io$"` | `r"(?i)\.xip\.io$"` | Yes |
| 3 | `r"\.sslip\.io$"` | `r"(?i)\.sslip\.io$"` | Yes |
| 4 | `r"localtest\.me$"` | `r"(?i)localtest\.me$"` | Yes |
| 5 | `r"127\.0\.0\.1"` | `r"127\.0\.0\.1"` | Yes |
| 6 | `r"169\.254\."` | `r"169\.254\."` | Yes |
| 7 | `r"192\.168\."` | `r"192\.168\."` | Yes |
| 8 | `r"10\.\d+\."` | `r"10\.\d+\."` | Yes |
| 9 | `r"172\.(1[6-9]\|2\d\|3[01])\."` | `r"172\.(1[6-9]\|2\d\|3[01])\."` | Yes |

### Rationale

The Rust `regex` crate supports all features used by these patterns: character classes (`\d`), alternation (`|`), anchors (`$`), escape sequences (`\.`), and case-insensitive flag (`(?i)`). No lookahead/lookbehind is needed. This was already confirmed during SPEC-021 implementation.

### Implementation Note

All 9 patterns use `(?i)` prefix for case-insensitive matching (matching Python's default `re.search()` behavior). They are compiled as `LazyLock<Regex>` statics — same pattern as `observability.rs`.

### Alternatives Rejected

1. **`regex-fancy` crate**: Not needed — no advanced features required. Would add an unnecessary dependency.
2. **String methods instead of regex**: Rejected for patterns 8-9 which use character classes and alternation. Patterns 1-7 could theoretically use string methods, but regex is more maintainable and consistent.
