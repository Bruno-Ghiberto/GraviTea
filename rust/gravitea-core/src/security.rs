//! SSRF Validation Pipeline (SPEC-022)
//!
//! Rust-accelerated URL validation for SSRF prevention.
//! Replaces CPU-bound portions of `url_validator.py:is_safe_url()`.
//!
//! Exported functions:
//! - `validate_url_safety(url) -> (bool, hostname)` — static URL checks
//! - `check_resolved_ip(ip_str) -> bool` — post-DNS IP validation
//!
//! Internal functions:
//! - `parse_ip_flexible()` — 5-strategy IP parser (standard, decimal, hex, octal, shortened)
//! - `is_private_ip()` — 10 CIDR range check
//! - `is_suspicious_hostname()` — 9 regex + 3 string checks
//! - `extract_hostname_fallback()` — manual hostname extraction for urls the `url` crate rejects

use std::net::{IpAddr, Ipv4Addr, Ipv6Addr};
use std::sync::LazyLock;

use pyo3::prelude::*;
use regex::Regex;
use url::Url;

// ─── Constants ──────────────────────────────────────────────────────────────

/// Blocked hostnames (case-insensitive exact match)
const BLOCKED_HOSTNAMES: &[&str] = &[
    "localhost",
    "metadata.google.internal",
    "metadata.gcp.internal",
];

// ─── Compiled Regex Patterns ────────────────────────────────────────────────

static RE_NIP_IO: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"(?i)\.nip\.io$").unwrap());
static RE_XIP_IO: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"(?i)\.xip\.io$").unwrap());
static RE_SSLIP_IO: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"(?i)\.sslip\.io$").unwrap());
static RE_LOCALTEST_ME: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?i)localtest\.me$").unwrap());
static RE_LOOPBACK_IP: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"127\.0\.0\.1").unwrap());
static RE_LINK_LOCAL: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"169\.254\.").unwrap());
static RE_PRIVATE_192: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"192\.168\.").unwrap());
static RE_PRIVATE_10: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"10\.\d+\.").unwrap());
static RE_PRIVATE_172: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"172\.(1[6-9]|2\d|3[01])\.").unwrap());

// ─── Helper: Scheme Detection ───────────────────────────────────────────────

/// Case-insensitive HTTP(S) scheme check. Returns byte length of scheme prefix.
fn http_scheme_len(url: &str) -> Option<usize> {
    let bytes = url.as_bytes();
    if bytes.len() >= 8 && bytes[..8].eq_ignore_ascii_case(b"https://") {
        Some(8)
    } else if bytes.len() >= 7 && bytes[..7].eq_ignore_ascii_case(b"http://") {
        Some(7)
    } else {
        None
    }
}

// ─── IP Parsing (5 Strategies) ─────────────────────────────────────────────

/// Parse a hostname as an IP address using 5 strategies:
/// 1. Standard (IpAddr::from_str + bracket stripping)
/// 2. Decimal integer (2130706433)
/// 3. Hexadecimal (0x7f000001)
/// 4. Octal/decimal dotted with trailing-zero padding (0177.0.0.1, 127.1)
/// 5. Shortened expansion (127.1 → 127.0.0.1) — rarely reached, octal catches most
fn parse_ip_flexible(hostname: &str) -> Option<IpAddr> {
    // Strategy 1: Standard IP parsing (handles IPv4, IPv6, bracketed IPv6)
    let stripped = hostname
        .strip_prefix('[')
        .and_then(|s| s.strip_suffix(']'))
        .unwrap_or(hostname);
    if let Ok(ip) = stripped.parse::<IpAddr>() {
        return Some(ip);
    }

    // Strategy 2: Decimal integer (e.g., 2130706433 → 127.0.0.1)
    if !hostname.is_empty() && hostname.chars().all(|c| c.is_ascii_digit()) {
        if let Ok(num) = hostname.parse::<u32>() {
            return Some(IpAddr::V4(Ipv4Addr::from(num)));
        }
    }

    // Strategy 3: Hexadecimal (e.g., 0x7f000001 → 127.0.0.1)
    if let Some(hex_str) = hostname
        .strip_prefix("0x")
        .or_else(|| hostname.strip_prefix("0X"))
    {
        if let Ok(num) = u32::from_str_radix(hex_str, 16) {
            return Some(IpAddr::V4(Ipv4Addr::from(num)));
        }
    }

    // Strategy 4: Octal/decimal dotted with trailing-zero padding
    // Replicates Python _parse_ip() lines 208-226 exactly:
    //   split on ".", each part: leading-zero+len>1+all-digits → octal, else decimal
    //   pad to 4 parts with trailing zeros, all must be 0-255
    if hostname.contains('.') {
        let parts: Vec<&str> = hostname.split('.').collect();
        if parts.len() >= 2 && parts.len() <= 4 {
            let mut octets: Vec<u32> = Vec::with_capacity(4);
            let mut valid = true;
            for part in &parts {
                if part.starts_with('0')
                    && part.len() > 1
                    && part.chars().all(|c| c.is_ascii_digit())
                {
                    // Octal
                    match u32::from_str_radix(part, 8) {
                        Ok(v) => octets.push(v),
                        Err(_) => {
                            valid = false;
                            break;
                        }
                    }
                } else {
                    // Decimal
                    match part.parse::<u32>() {
                        Ok(v) => octets.push(v),
                        Err(_) => {
                            valid = false;
                            break;
                        }
                    }
                }
            }
            if valid {
                while octets.len() < 4 {
                    octets.push(0);
                }
                if octets.iter().all(|&v| v <= 255) {
                    return Some(IpAddr::V4(Ipv4Addr::new(
                        octets[0] as u8,
                        octets[1] as u8,
                        octets[2] as u8,
                        octets[3] as u8,
                    )));
                }
            }
        }
    }

    // Strategy 5: Shortened expansion (127.1 → 127.0.0.1, 192.168.1 → 192.168.0.1)
    // Rarely reached — Strategy 4 catches most digit-only dotted hostnames.
    // Replicates Python _parse_ip() lines 228-244.
    if hostname.contains('.')
        && hostname
            .replace('.', "")
            .chars()
            .all(|c| c.is_ascii_digit())
    {
        let parts: Vec<&str> = hostname.split('.').collect();
        if parts.len() > 1 && parts.len() < 4 {
            let expanded = match parts.len() {
                2 => format!("{}.0.0.{}", parts[0], parts[1]),
                3 => format!("{}.{}.0.{}", parts[0], parts[1], parts[2]),
                _ => return None,
            };
            if let Ok(ip) = expanded.parse::<Ipv4Addr>() {
                return Some(IpAddr::V4(ip));
            }
        }
    }

    None
}

// ─── Private IP Check (10 CIDR Ranges) ─────────────────────────────────────

/// Check if IP is in a private/internal CIDR range.
/// 10 ranges: IPv4 (10/8, 172.16/12, 192.168/16, 127/8, 169.254/16, 0/8)
///            IPv6 (::1/128, fc00::/7, fe80::/10, ::ffff:0:0/96)
fn is_private_ip(ip: &IpAddr) -> bool {
    match ip {
        IpAddr::V4(v4) => {
            let o = v4.octets();
            // 10.0.0.0/8
            o[0] == 10
            // 172.16.0.0/12
            || (o[0] == 172 && (16..=31).contains(&o[1]))
            // 192.168.0.0/16
            || (o[0] == 192 && o[1] == 168)
            // 127.0.0.0/8
            || o[0] == 127
            // 169.254.0.0/16
            || (o[0] == 169 && o[1] == 254)
            // 0.0.0.0/8
            || o[0] == 0
        }
        IpAddr::V6(v6) => {
            let seg = v6.segments();
            // ::1/128
            v6.is_loopback()
            // fc00::/7
            || (seg[0] & 0xfe00) == 0xfc00
            // fe80::/10
            || (seg[0] & 0xffc0) == 0xfe80
            // ::ffff:0:0/96 — catches ALL IPv4-mapped for Python parity (R-003)
            || (seg[0] == 0 && seg[1] == 0 && seg[2] == 0
                && seg[3] == 0 && seg[4] == 0 && seg[5] == 0xffff)
        }
    }
}

/// Check if IP is a cloud metadata endpoint.
fn is_metadata_ip(ip: &IpAddr) -> bool {
    match ip {
        IpAddr::V4(v4) => {
            // 169.254.169.254 — AWS/Azure metadata
            *v4 == Ipv4Addr::new(169, 254, 169, 254)
            // 169.254.170.2 — AWS ECS task metadata
            || *v4 == Ipv4Addr::new(169, 254, 170, 2)
        }
        IpAddr::V6(_) => false,
    }
}

// ─── Suspicious Hostname Check ──────────────────────────────────────────────

/// Check if a hostname matches suspicious SSRF bypass patterns.
/// Input should be lowercase. Checks:
/// 1. "localhost" substring
/// 2. 9 compiled regex patterns (wildcard DNS, embedded IPs)
/// 3. Null bytes (\x00 or %00)
/// 4. IPv6 private address prefixes (fd, fc, fe80)
fn is_suspicious_hostname(hostname: &str) -> bool {
    // Check for localhost substring
    if hostname.contains("localhost") {
        return true;
    }

    // 9 regex patterns
    if RE_NIP_IO.is_match(hostname)
        || RE_XIP_IO.is_match(hostname)
        || RE_SSLIP_IO.is_match(hostname)
        || RE_LOCALTEST_ME.is_match(hostname)
        || RE_LOOPBACK_IP.is_match(hostname)
        || RE_LINK_LOCAL.is_match(hostname)
        || RE_PRIVATE_192.is_match(hostname)
        || RE_PRIVATE_10.is_match(hostname)
        || RE_PRIVATE_172.is_match(hostname)
    {
        return true;
    }

    // Null byte check
    if hostname.contains('\0') || hostname.contains("%00") {
        return true;
    }

    // IPv6 private prefix check (fd, fc, fe80)
    // Replicates Python bug: always uses hostname[2:] even for "fe80" prefix
    if hostname.starts_with("fd")
        || hostname.starts_with("fc")
        || hostname.starts_with("fe80")
    {
        let remaining = &hostname[2..]; // Python parity: always [2:]
        if remaining.is_empty() || remaining.chars().all(|c| c.is_alphanumeric()) {
            return true;
        }
    }

    false
}

// ─── Fallback Hostname Extraction ───────────────────────────────────────────

/// Extract hostname from URLs that the `url` crate rejects.
/// Handles scheme stripping, credential detection, and hostname extraction.
/// Returns None if scheme is not http/https or hostname is empty.
fn extract_hostname_fallback(url: &str) -> Option<String> {
    let scheme_len = http_scheme_len(url)?;
    let after_scheme = &url[scheme_len..];

    // Skip past credentials (take content after rightmost @)
    let authority = after_scheme
        .rsplit_once('@')
        .map_or(after_scheme, |(_, h)| h);

    // Extract hostname until : / ? #
    let end = authority
        .find(&[':', '/', '?', '#'][..])
        .unwrap_or(authority.len());
    let hostname = &authority[..end];

    if hostname.is_empty() {
        None
    } else {
        Some(hostname.to_string())
    }
}

// ─── Exported PyO3 Functions ────────────────────────────────────────────────

/// Validate URL safety for SSRF prevention (static checks only, no DNS).
///
/// Returns `(is_safe, hostname)`:
/// - `(true, "example.com")` — safe, caller should resolve DNS and call `check_resolved_ip`
/// - `(false, "")` — unsafe, blocked by static checks
#[pyfunction]
pub fn validate_url_safety(url: &str) -> PyResult<(bool, String)> {
    let trimmed = url.trim();
    if trimmed.is_empty() {
        return Ok((false, String::new()));
    }

    let (has_credentials, hostname) = match Url::parse(trimmed) {
        Ok(parsed) => {
            // Standard path via url crate
            let scheme = parsed.scheme();
            if scheme != "http" && scheme != "https" {
                return Ok((false, String::new()));
            }
            let has_creds =
                !parsed.username().is_empty() || parsed.password().is_some();
            let host = match parsed.host_str() {
                Some(h) if !h.is_empty() => h.to_string(),
                _ => return Ok((false, String::new())),
            };
            (has_creds, host)
        }
        Err(_) => {
            // Fallback path for non-standard URLs (hex, decimal, octal, shortened IPs)
            // Check scheme
            if http_scheme_len(trimmed).is_none() {
                return Ok((false, String::new()));
            }

            // Check credentials in fallback path
            let scheme_len = http_scheme_len(trimmed).unwrap();
            let after_scheme = &trimmed[scheme_len..];
            if let Some(at_pos) = after_scheme.find('@') {
                let before_at = &after_scheme[..at_pos];
                if !before_at.is_empty() {
                    // Non-empty username → credential injection (R-004)
                    return Ok((false, String::new()));
                }
            }

            // Extract hostname
            match extract_hostname_fallback(trimmed) {
                Some(host) if !host.is_empty() => (false, host),
                _ => return Ok((false, String::new())),
            }
        }
    };

    // Credential check
    if has_credentials {
        return Ok((false, String::new()));
    }

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

    // Suspicious hostname check (FR-007)
    if is_suspicious_hostname(&hostname_lower) {
        return Ok((false, String::new()));
    }

    // Hostname needs DNS resolution — return true with hostname
    Ok((true, hostname))
}

/// Check if a resolved IP address is safe (not private/metadata).
///
/// Called by Python after DNS resolution to validate the actual IP.
/// Returns `true` if safe (public), `false` if private/metadata/unparseable.
#[pyfunction]
pub fn check_resolved_ip(ip_str: &str) -> PyResult<bool> {
    match ip_str.parse::<IpAddr>() {
        Ok(ip) => Ok(!is_private_ip(&ip) && !is_metadata_ip(&ip)),
        Err(_) => Ok(false), // Defensive: unparseable → block
    }
}

// ─── Tests ──────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    // ── parse_ip_flexible tests (T020) ──────────────────────────────────

    #[test]
    fn test_parse_ip_standard_ipv4() {
        assert_eq!(
            parse_ip_flexible("127.0.0.1"),
            Some(IpAddr::V4(Ipv4Addr::new(127, 0, 0, 1)))
        );
    }

    #[test]
    fn test_parse_ip_standard_ipv6() {
        assert_eq!(
            parse_ip_flexible("::1"),
            Some(IpAddr::V6(Ipv6Addr::LOCALHOST))
        );
    }

    #[test]
    fn test_parse_ip_bracketed_ipv6() {
        assert_eq!(
            parse_ip_flexible("[::1]"),
            Some(IpAddr::V6(Ipv6Addr::LOCALHOST))
        );
    }

    #[test]
    fn test_parse_ip_decimal_private() {
        // 2130706433 = 127.0.0.1
        assert_eq!(
            parse_ip_flexible("2130706433"),
            Some(IpAddr::V4(Ipv4Addr::new(127, 0, 0, 1)))
        );
    }

    #[test]
    fn test_parse_ip_decimal_public() {
        // 134744072 = 8.8.8.8
        assert_eq!(
            parse_ip_flexible("134744072"),
            Some(IpAddr::V4(Ipv4Addr::new(8, 8, 8, 8)))
        );
    }

    #[test]
    fn test_parse_ip_hex_lower() {
        assert_eq!(
            parse_ip_flexible("0x7f000001"),
            Some(IpAddr::V4(Ipv4Addr::new(127, 0, 0, 1)))
        );
    }

    #[test]
    fn test_parse_ip_hex_upper() {
        assert_eq!(
            parse_ip_flexible("0X7F000001"),
            Some(IpAddr::V4(Ipv4Addr::new(127, 0, 0, 1)))
        );
    }

    #[test]
    fn test_parse_ip_octal_private() {
        // 0177 = 127 (octal)
        assert_eq!(
            parse_ip_flexible("0177.0.0.1"),
            Some(IpAddr::V4(Ipv4Addr::new(127, 0, 0, 1)))
        );
    }

    #[test]
    fn test_parse_ip_octal_overflow() {
        // 0400 = 256 (octal) > 255 → None
        assert_eq!(parse_ip_flexible("0400.0.0.1"), None);
    }

    #[test]
    fn test_parse_ip_octal_mixed() {
        // 0300=192, 0250=168 (octal), 0=0, 01=1(octal)
        assert_eq!(
            parse_ip_flexible("0300.0250.0.01"),
            Some(IpAddr::V4(Ipv4Addr::new(192, 168, 0, 1)))
        );
    }

    #[test]
    fn test_parse_ip_two_part_dotted() {
        // "127.1" → Strategy 4 catches: [127,1,0,0] = 127.1.0.0 (Python parity)
        assert_eq!(
            parse_ip_flexible("127.1"),
            Some(IpAddr::V4(Ipv4Addr::new(127, 1, 0, 0)))
        );
    }

    #[test]
    fn test_parse_ip_three_part_dotted() {
        // "192.168.1" → Strategy 4: [192,168,1,0] = 192.168.1.0 (Python parity)
        assert_eq!(
            parse_ip_flexible("192.168.1"),
            Some(IpAddr::V4(Ipv4Addr::new(192, 168, 1, 0)))
        );
    }

    #[test]
    fn test_parse_ip_not_an_ip() {
        assert_eq!(parse_ip_flexible("example.com"), None);
    }

    #[test]
    fn test_parse_ip_invalid_octal_digit() {
        // "08" has leading zero but 8 is invalid octal → ValueError → None
        assert_eq!(parse_ip_flexible("08.0.0.1"), None);
    }

    // ── is_private_ip tests (T021) ──────────────────────────────────────

    #[test]
    fn test_private_10_network() {
        let ip: IpAddr = "10.0.0.1".parse().unwrap();
        assert!(is_private_ip(&ip));
        let ip: IpAddr = "10.255.255.255".parse().unwrap();
        assert!(is_private_ip(&ip));
    }

    #[test]
    fn test_private_172_network() {
        let ip: IpAddr = "172.16.0.1".parse().unwrap();
        assert!(is_private_ip(&ip));
        let ip: IpAddr = "172.31.255.255".parse().unwrap();
        assert!(is_private_ip(&ip));
        // Just outside range
        let ip: IpAddr = "172.15.255.255".parse().unwrap();
        assert!(!is_private_ip(&ip));
        let ip: IpAddr = "172.32.0.0".parse().unwrap();
        assert!(!is_private_ip(&ip));
    }

    #[test]
    fn test_private_192_168_network() {
        let ip: IpAddr = "192.168.0.1".parse().unwrap();
        assert!(is_private_ip(&ip));
        let ip: IpAddr = "192.168.255.255".parse().unwrap();
        assert!(is_private_ip(&ip));
    }

    #[test]
    fn test_private_loopback() {
        let ip: IpAddr = "127.0.0.1".parse().unwrap();
        assert!(is_private_ip(&ip));
        let ip: IpAddr = "127.255.255.255".parse().unwrap();
        assert!(is_private_ip(&ip));
    }

    #[test]
    fn test_private_link_local() {
        let ip: IpAddr = "169.254.0.1".parse().unwrap();
        assert!(is_private_ip(&ip));
        let ip: IpAddr = "169.254.255.255".parse().unwrap();
        assert!(is_private_ip(&ip));
    }

    #[test]
    fn test_private_this_network() {
        let ip: IpAddr = "0.0.0.0".parse().unwrap();
        assert!(is_private_ip(&ip));
        let ip: IpAddr = "0.255.255.255".parse().unwrap();
        assert!(is_private_ip(&ip));
    }

    #[test]
    fn test_private_ipv6_loopback() {
        let ip: IpAddr = "::1".parse().unwrap();
        assert!(is_private_ip(&ip));
    }

    #[test]
    fn test_private_ipv6_ula() {
        let ip: IpAddr = "fc00::1".parse().unwrap();
        assert!(is_private_ip(&ip));
        let ip: IpAddr = "fd00::1".parse().unwrap();
        assert!(is_private_ip(&ip));
    }

    #[test]
    fn test_private_ipv6_link_local() {
        let ip: IpAddr = "fe80::1".parse().unwrap();
        assert!(is_private_ip(&ip));
    }

    #[test]
    fn test_private_ipv4_mapped_v6() {
        // ::ffff:192.168.1.1 — caught by ::ffff:0:0/96 range (R-003)
        let ip: IpAddr = "::ffff:192.168.1.1".parse().unwrap();
        assert!(is_private_ip(&ip));
        // Even mapped public IPs are caught (Python parity)
        let ip: IpAddr = "::ffff:8.8.8.8".parse().unwrap();
        assert!(is_private_ip(&ip));
    }

    #[test]
    fn test_public_ipv4() {
        let ip: IpAddr = "8.8.8.8".parse().unwrap();
        assert!(!is_private_ip(&ip));
        let ip: IpAddr = "93.184.216.34".parse().unwrap();
        assert!(!is_private_ip(&ip));
    }

    #[test]
    fn test_public_ipv6() {
        let ip: IpAddr = "2001:4860:4860::8888".parse().unwrap();
        assert!(!is_private_ip(&ip));
    }

    // ── is_metadata_ip tests ────────────────────────────────────────────

    #[test]
    fn test_metadata_aws_azure() {
        let ip: IpAddr = "169.254.169.254".parse().unwrap();
        assert!(is_metadata_ip(&ip));
    }

    #[test]
    fn test_metadata_ecs() {
        let ip: IpAddr = "169.254.170.2".parse().unwrap();
        assert!(is_metadata_ip(&ip));
    }

    #[test]
    fn test_metadata_not_metadata() {
        let ip: IpAddr = "169.254.1.1".parse().unwrap();
        assert!(!is_metadata_ip(&ip));
    }

    // ── is_suspicious_hostname tests (T022) ─────────────────────────────

    #[test]
    fn test_suspicious_nip_io() {
        assert!(is_suspicious_hostname("evil.nip.io"));
        assert!(!is_suspicious_hostname("nipxio.com"));
    }

    #[test]
    fn test_suspicious_xip_io() {
        assert!(is_suspicious_hostname("test.xip.io"));
    }

    #[test]
    fn test_suspicious_sslip_io() {
        assert!(is_suspicious_hostname("10.0.0.1.sslip.io"));
    }

    #[test]
    fn test_suspicious_localtest_me() {
        assert!(is_suspicious_hostname("localtest.me"));
        assert!(is_suspicious_hostname("sub.localtest.me"));
    }

    #[test]
    fn test_suspicious_embedded_loopback() {
        assert!(is_suspicious_hostname("evil-127.0.0.1.example.com"));
    }

    #[test]
    fn test_suspicious_embedded_link_local() {
        assert!(is_suspicious_hostname("evil-169.254.1.1.example.com"));
    }

    #[test]
    fn test_suspicious_localhost_substring() {
        assert!(is_suspicious_hostname("sub.localhost.example.com"));
        assert!(is_suspicious_hostname("notlocalhost"));
    }

    #[test]
    fn test_suspicious_null_byte() {
        assert!(is_suspicious_hostname("evil\0.example.com"));
        assert!(is_suspicious_hostname("evil%00.example.com"));
    }

    #[test]
    fn test_suspicious_ipv6_prefix_fd() {
        assert!(is_suspicious_hostname("fd00"));
        assert!(is_suspicious_hostname("fc"));
        assert!(is_suspicious_hostname("fe80"));
        assert!(is_suspicious_hostname("fd00abc"));
    }

    #[test]
    fn test_suspicious_safe_hostname() {
        assert!(!is_suspicious_hostname("example.com"));
        assert!(!is_suspicious_hostname("api.example.com"));
        assert!(!is_suspicious_hostname("cdn.cloudflare.com"));
    }

    // ── extract_hostname_fallback tests ─────────────────────────────────

    #[test]
    fn test_fallback_hex_ip() {
        assert_eq!(
            extract_hostname_fallback("http://0x7f000001/"),
            Some("0x7f000001".to_string())
        );
    }

    #[test]
    fn test_fallback_decimal_ip() {
        assert_eq!(
            extract_hostname_fallback("http://2130706433/path"),
            Some("2130706433".to_string())
        );
    }

    #[test]
    fn test_fallback_with_port() {
        assert_eq!(
            extract_hostname_fallback("http://0x7f000001:8080/"),
            Some("0x7f000001".to_string())
        );
    }

    #[test]
    fn test_fallback_bad_scheme() {
        assert_eq!(extract_hostname_fallback("ftp://example.com/"), None);
    }

    // ── validate_url_safety tests (T023) ────────────────────────────────

    #[test]
    fn test_validate_empty_string() {
        assert_eq!(
            validate_url_safety("").unwrap(),
            (false, String::new())
        );
    }

    #[test]
    fn test_validate_whitespace_only() {
        assert_eq!(
            validate_url_safety("   ").unwrap(),
            (false, String::new())
        );
    }

    #[test]
    fn test_validate_bad_scheme() {
        assert_eq!(
            validate_url_safety("ftp://example.com").unwrap(),
            (false, String::new())
        );
    }

    #[test]
    fn test_validate_credentials() {
        assert_eq!(
            validate_url_safety("http://user:pass@example.com/").unwrap(),
            (false, String::new())
        );
    }

    #[test]
    fn test_validate_blocked_localhost() {
        assert_eq!(
            validate_url_safety("http://localhost/").unwrap(),
            (false, String::new())
        );
    }

    #[test]
    fn test_validate_private_ip() {
        assert_eq!(
            validate_url_safety("http://192.168.1.1/").unwrap(),
            (false, String::new())
        );
    }

    #[test]
    fn test_validate_metadata_ip() {
        assert_eq!(
            validate_url_safety("http://169.254.169.254/latest/meta-data/").unwrap(),
            (false, String::new())
        );
    }

    #[test]
    fn test_validate_safe_url() {
        let (safe, host) = validate_url_safety("http://example.com/path").unwrap();
        assert!(safe);
        assert_eq!(host, "example.com");
    }

    #[test]
    fn test_validate_safe_https() {
        let (safe, host) = validate_url_safety("https://api.example.com/v1").unwrap();
        assert!(safe);
        assert_eq!(host, "api.example.com");
    }

    #[test]
    fn test_validate_hex_private() {
        // http://0x7f000001/ → 127.0.0.1 → private
        // Whether url crate handles it or fallback catches it, result is (false, "")
        assert_eq!(
            validate_url_safety("http://0x7f000001/").unwrap(),
            (false, String::new())
        );
    }

    #[test]
    fn test_validate_suspicious_hostname() {
        assert_eq!(
            validate_url_safety("http://evil.nip.io/").unwrap(),
            (false, String::new())
        );
    }

    // ── check_resolved_ip tests ─────────────────────────────────────────

    #[test]
    fn test_resolved_public_ip() {
        assert_eq!(check_resolved_ip("8.8.8.8").unwrap(), true);
    }

    #[test]
    fn test_resolved_private_ip() {
        assert_eq!(check_resolved_ip("192.168.1.1").unwrap(), false);
    }

    #[test]
    fn test_resolved_metadata_ip() {
        assert_eq!(check_resolved_ip("169.254.169.254").unwrap(), false);
    }

    #[test]
    fn test_resolved_invalid_input() {
        assert_eq!(check_resolved_ip("not-an-ip").unwrap(), false);
    }
}
