# Feature Specification: Rust SSRF Validation Pipeline

**Feature Branch**: `022-ssrf-validation-pipeline`
**Created**: 2026-02-27
**Status**: Draft
**Input**: Replace CPU-bound portions of `url_validator.py:is_safe_url()` with compiled Rust. IP parsing (5 formats), CIDR range checking (10 ranges), suspicious hostname regex (9 patterns), URL structure validation, and metadata IP detection move to Rust. DNS resolution stays in Python (I/O-bound).
**Depends on**: SPEC-017 (Rust Toolchain Bootstrap) — COMPLETE

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Static URL Validation Produces Identical Results (Priority: P1)

The system validates every outbound URL (ARCA SOAP calls, webhook dispatches) against SSRF attack vectors before making HTTP requests. The accelerated validation engine performs all CPU-bound checks — URL structure parsing, IP address detection across 5 encoding formats, private CIDR range matching across 10 ranges, cloud metadata IP blocking, and suspicious hostname pattern matching across 9 regex patterns — and produces byte-for-byte identical boolean results to the current implementation for every URL.

**Why this priority**: This is a security-critical function. If the accelerated version differs from the current implementation on even one adversarial input, it could either (a) allow SSRF attacks through (security breach) or (b) false-positive block legitimate ARCA invoicing calls (business disruption). Correctness parity is the absolute prerequisite before any performance work matters.

**Independent Test**: Can be fully tested by passing a corpus of 60+ adversarial URLs — including localhost variations, decimal/hex/octal-encoded IPs, private ranges, cloud metadata endpoints, credential-embedded URLs, wildcard DNS services, null bytes, and legitimate external hosts — through both implementations and asserting identical boolean output for every input.

**Acceptance Scenarios**:

1. **Given** a URL with standard loopback IP (`http://127.0.0.1:8080/admin`), **When** static URL validation is applied, **Then** the function returns `false` (unsafe).
2. **Given** a URL with decimal-encoded loopback IP (`http://2130706433/`), **When** static URL validation is applied, **Then** the function decodes `2130706433` to `127.0.0.1` and returns `false` (unsafe).
3. **Given** a URL with hexadecimal-encoded loopback IP (`http://0x7f000001/`), **When** static URL validation is applied, **Then** the function returns `false` (unsafe).
4. **Given** a URL with octal-encoded loopback IP (`http://0177.0.0.1/`), **When** static URL validation is applied, **Then** the function converts octal `0177` to decimal `127` and returns `false` (unsafe).
5. **Given** a URL with shortened IP (`http://127.1/`), **When** static URL validation is applied, **Then** the function expands `127.1` to `127.0.0.1` and returns `false` (unsafe).
6. **Given** a URL with embedded credentials (`http://evil.com@safe.com/`), **When** static URL validation is applied, **Then** the function detects credentials and returns `false` (unsafe).
7. **Given** a URL targeting AWS cloud metadata (`http://169.254.169.254/latest/meta-data/`), **When** static URL validation is applied, **Then** the function returns `false` (unsafe).
8. **Given** a URL with dangerous scheme (`file:///etc/passwd`), **When** static URL validation is applied, **Then** the function rejects the non-HTTP scheme and returns `false` (unsafe).
9. **Given** a legitimate external URL (`https://api.example.com/webhook`), **When** static URL validation is applied, **Then** the function passes all static checks and indicates DNS resolution is needed for the hostname `api.example.com`.
10. **Given** a URL with IPv6 loopback (`http://[::1]/`), **When** static URL validation is applied, **Then** the function returns `false` (unsafe).
11. **Given** a URL with IPv4-mapped IPv6 (`http://[::ffff:127.0.0.1]/`), **When** static URL validation is applied, **Then** the function returns `false` (unsafe — mapped to private range).

---

### User Story 2 - DNS-Resolved IP Validation Prevents Rebinding Attacks (Priority: P1)

After the accelerated engine performs static URL validation and identifies a hostname needing DNS resolution, Python resolves the hostname via the operating system DNS resolver, and then the accelerated engine validates that resolved IP address against the same private CIDR ranges and cloud metadata addresses. This two-phase architecture prevents DNS rebinding attacks where a hostname initially resolves to a public IP during validation but changes to an internal IP during the actual request.

**Why this priority**: DNS rebinding is the most common SSRF bypass technique. Without post-resolution IP validation, an attacker can register a domain (e.g., via nip.io or a custom DNS server) that resolves to internal IPs after initial validation. This story ensures the critical second-pass validation catches DNS-based SSRF bypasses. It is co-P1 with Story 1 because both are security gates.

**Independent Test**: Can be tested by mocking DNS resolution to return private IPs for public-looking hostnames and verifying the post-DNS IP check correctly blocks them. Also test DNS failure behavior (unresolvable hostnames are allowed through, matching current behavior).

**Acceptance Scenarios**:

1. **Given** a hostname that DNS-resolves to `127.0.0.1`, **When** the resolved IP is validated, **Then** the system returns `false` (private loopback).
2. **Given** a hostname that DNS-resolves to `10.0.0.5`, **When** the resolved IP is validated, **Then** the system returns `false` (RFC 1918 private).
3. **Given** a hostname that DNS-resolves to `172.20.1.1`, **When** the resolved IP is validated, **Then** the system returns `false` (RFC 1918 private).
4. **Given** a hostname that DNS-resolves to `192.168.1.100`, **When** the resolved IP is validated, **Then** the system returns `false` (RFC 1918 private).
5. **Given** a hostname that DNS-resolves to `169.254.169.254`, **When** the resolved IP is validated, **Then** the system returns `false` (cloud metadata).
6. **Given** a hostname that DNS-resolves to `169.254.170.2`, **When** the resolved IP is validated, **Then** the system returns `false` (AWS ECS task metadata).
7. **Given** a hostname that DNS-resolves to `93.184.216.34` (example.com), **When** the resolved IP is validated, **Then** the system returns `true` (public).
8. **Given** a hostname that DNS-resolves to `::ffff:127.0.0.1` (IPv4-mapped IPv6), **When** the resolved IP is validated, **Then** the system returns `false` (private mapped range).
9. **Given** a hostname that cannot be DNS-resolved (lookup fails), **When** the system processes the result, **Then** the URL is allowed through (matching current behavior — DNS failure does not block).

---

### User Story 3 - Accelerated Validation Performance (Priority: P2)

The accelerated validation engine completes the CPU-bound portions of URL validation — URL parsing, 5 IP format parse attempts, 10 CIDR range checks, and 9 suspicious hostname regex matches — significantly faster than the current implementation. This reduces per-validation CPU overhead for every outgoing ARCA SOAP call and webhook dispatch.

**Why this priority**: Performance is the motivation for the acceleration, but it is secondary to correctness (Stories 1 and 2). The security function must be correct first, then fast. Once parity is proven, the speedup delivers operational savings on every outbound request.

**Independent Test**: Can be tested by benchmarking both implementations against the adversarial URL corpus and measuring execution time per validation. Only the CPU-bound portions are benchmarked; DNS resolution latency is excluded.

**Acceptance Scenarios**:

1. **Given** a corpus of 200 adversarial URLs, **When** static URL validation is applied to each via the accelerated engine, **Then** the CPU-bound portions complete at least 3 times faster than the current implementation.
2. **Given** a batch of 100 legitimate external URLs, **When** static URL validation is applied via the accelerated engine, **Then** the CPU-bound portions complete at least 3 times faster than the current implementation.

---

### User Story 4 - Graceful Fallback When Acceleration Unavailable (Priority: P3)

When the accelerated validation engine is unavailable (missing native extension after a deployment issue), the system falls back to the current Python implementation so SSRF protection continues to function, even at the original speed.

**Why this priority**: Operational resilience. A deployment issue with the native extension must degrade performance, not disable security protection. SSRF validation is a security gate — disabling it exposes the system to attacks.

**Independent Test**: Can be tested by simulating the absence of the native extension and verifying that `is_safe_url()` still works correctly through the Python fallback path.

**Acceptance Scenarios**:

1. **Given** the accelerated engine is not available (native extension import fails), **When** `is_safe_url()` is called, **Then** the system uses the Python fallback and produces correct results for all adversarial URLs.
2. **Given** the accelerated engine becomes available again (after redeployment), **When** the next validation is called, **Then** the system uses the accelerated engine without manual intervention.
3. **Given** the system starts with the accelerated engine unavailable, **When** a warning is logged at startup, **Then** the log clearly identifies that the fallback is active and why.

---

### Edge Cases

- What happens when the URL is `None`, empty string, or whitespace-only? The system returns `false` (unsafe), matching current behavior.
- What happens when a URL contains a null byte (`\x00`) or percent-encoded null byte (`%00`) in the hostname? The system detects it as a suspicious bypass attempt and returns `false`.
- What happens when a URL uses the credential-injection pattern `http://evil.com@safe.com`? The system detects embedded credentials and returns `false`.
- What happens when a URL has IPv6 in non-bracketed form (e.g., `http://::1/`)? The URL parser may handle this differently than bracketed form — the system should handle gracefully and block if the address is private.
- What happens when a hostname contains mixed octal and decimal parts (e.g., `http://0177.0.0.01/`)? The system applies octal parsing to leading-zero parts and decimal parsing to others, then validates the resulting IP.
- What happens when an IP falls in the `0.0.0.0/8` ("This" network) range? The system blocks it (current behavior).
- What happens when a hostname starts with `fe80` (resembling an IPv6 link-local prefix fragment)? The suspicious hostname check flags it as potentially dangerous.
- What happens when a hostname matches a wildcard DNS service (e.g., `127.0.0.1.nip.io`, `spoofed.xip.io`, `localtest.me`)? The suspicious hostname regex catches these patterns.
- What happens when the URL exceeds 2,048 characters? The system processes it without error — long URLs are not inherently unsafe.
- What happens when the URL contains double-encoded characters (e.g., `%252f`)? The system validates the URL as-is without double-decoding (matching current behavior).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST validate URL structure by checking that the scheme is `http` or `https`, rejecting all other schemes (file, ftp, gopher, dict, ssh, telnet, ldap, data, javascript).
- **FR-002**: System MUST detect and reject URLs containing embedded credentials (username or password in the URL).
- **FR-003**: System MUST parse hostnames as IP addresses using 5 strategies in order: (a) standard IP address parsing, (b) decimal integer encoding (e.g., `2130706433`), (c) hexadecimal encoding (e.g., `0x7f000001`), (d) octal encoding (e.g., `0177.0.0.1`), (e) shortened notation (e.g., `127.1` → `127.0.0.1`).
- **FR-004**: System MUST check parsed IP addresses against 10 private/reserved CIDR ranges: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `127.0.0.0/8`, `169.254.0.0/16`, `0.0.0.0/8`, `::1/128`, `fc00::/7`, `fe80::/10`, `::ffff:0:0/96`.
- **FR-005**: System MUST check parsed IP addresses against cloud metadata addresses: `169.254.169.254` (AWS/Azure metadata), `169.254.170.2` (AWS ECS task metadata).
- **FR-006**: System MUST check hostnames against a blocked hostname set: `localhost`, `metadata.google.internal`, `metadata.gcp.internal` (case-insensitive matching).
- **FR-007**: System MUST detect suspicious hostnames using 9 patterns targeting: wildcard DNS services (nip.io, xip.io, sslip.io), known localhost aliases (localtest.me), and embedded private IP patterns (127.0.0.1, 169.254.x, 192.168.x, 10.x, 172.16-31.x in hostname strings).
- **FR-008**: System MUST detect null bytes (`\x00`) and percent-encoded null bytes (`%00`) in hostnames as bypass attempts.
- **FR-009**: System MUST detect hostnames starting with IPv6 private address prefixes (`fd`, `fc`, `fe80`) followed by only alphanumeric characters as suspicious.
- **FR-010**: System MUST implement a two-phase validation design: Phase 1 performs all CPU-bound static checks and returns either a definitive unsafe result OR a hostname requiring DNS resolution. Phase 2 validates a DNS-resolved IP string against the same private CIDR ranges and metadata addresses.
- **FR-011**: System MUST NOT perform DNS resolution in the accelerated engine. DNS resolution MUST remain in the existing Python DNS resolver using the operating system's name resolution.
- **FR-012**: System MUST allow URLs through when DNS resolution fails (hostname unresolvable), matching the current behavior. DNS failure does not indicate an unsafe URL.
- **FR-013**: System MUST provide a fallback implementation that activates automatically when the accelerated engine is unavailable, producing identical output via the existing Python URL validator.
- **FR-014**: System MUST produce identical boolean results to the current `url_validator.py:is_safe_url()` implementation for every input in the adversarial test corpus, verified by automated parity tests.
- **FR-015**: System MUST be available within the containerized deployment without additional runtime dependencies beyond what the existing build process provides.

### Key Entities

- **URL Under Validation**: A string representing a user-supplied or system-generated URL to be validated before making an outbound HTTP request. Typical sources: ARCA SOAP endpoint URLs, webhook callback URLs, external API integration endpoints. Length typically 30-200 characters.
- **Parsed IP Address**: An IP address (IPv4 or IPv6) extracted from the URL hostname, potentially decoded from one of 5 encoding formats (standard, decimal, hexadecimal, octal, shortened). Validated against private CIDR ranges and metadata addresses.
- **Private CIDR Range**: One of 10 reserved network ranges (RFC 1918, loopback, link-local, "This" network, IPv6 unique local, IPv6 link-local, IPv4-mapped IPv6) that indicate internal/private addresses. URLs pointing to these are rejected.
- **Cloud Metadata Address**: One of 2 specific IPs (169.254.169.254, 169.254.170.2) used by cloud providers (AWS, Azure, GCP) to expose instance metadata. URLs pointing to these are rejected to prevent credential leakage.
- **Suspicious Hostname**: A hostname matching one of 9 regex patterns associated with SSRF bypass services (wildcard DNS resolvers, embedded private IPs), containing null bytes, or resembling IPv6 private address prefixes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The accelerated implementation produces identical boolean output to the current implementation for a test corpus of at least 60 adversarial URLs, covering all 5 IP encoding formats, all 10 private CIDR ranges, all 9 suspicious hostname patterns, credential-embedded URLs, dangerous schemes, cloud metadata endpoints, null bytes, empty/malformed inputs, and legitimate external URLs.
- **SC-002**: The accelerated implementation completes CPU-bound URL validation at least 3 times faster than the current implementation, measured by automated benchmark on a corpus of 200 adversarial URLs (DNS resolution excluded from measurement).
- **SC-003**: All 5 IP address encoding formats are correctly parsed and validated, verified by individual format-specific tests with private and public IPs for each format.
- **SC-004**: All 10 private CIDR ranges are correctly identified, verified by tests with boundary IPs (first and last address in each range).
- **SC-005**: All 9 suspicious hostname patterns are correctly matched, verified by individual pattern tests.
- **SC-006**: Both cloud metadata IPs (169.254.169.254, 169.254.170.2) are correctly blocked, verified by tests.
- **SC-007**: The fallback mechanism activates automatically when the accelerated engine is unavailable and produces correct output without manual intervention, verified by test.
- **SC-008**: The containerized deployment includes the accelerated validation functions and passes all SSRF-related automated tests.
- **SC-009**: The complete automated test suite passes with zero regressions after the accelerated engine is integrated.
- **SC-010**: The existing security tests (SEC-SSRF-001 through SEC-SSRF-006) pass without modification when the accelerated engine is active.

## Assumptions

- The current Python `is_safe_url()` implementation is the source of truth for correctness. Any ambiguity in expected output is resolved by running the input through the existing Python function.
- DNS resolution behavior (allow on failure) is a deliberate design choice, not a bug. The spec preserves this behavior.
- The 5 IP encoding formats (standard, decimal, hex, octal, shortened) cover all known SSRF bypass techniques targeting IP address representation. No additional formats are expected.
- The 10 private CIDR ranges cover all RFC-reserved private/internal address space relevant to SSRF prevention. The explicit metadata IP check provides defense-in-depth beyond what CIDR matching alone would catch.
- The 9 suspicious hostname patterns cover the known wildcard DNS services and embedded private IP patterns used in SSRF bypass attacks as of the time of writing.
- Pattern application order must match the current Python implementation to ensure identical behavior when multiple patterns could match the same input.
- The accelerated engine and the fallback implementation are functionally interchangeable — callers cannot and should not distinguish between them.
- URL parsing edge cases between different URL standards (WHATWG vs RFC 3986) are resolved in favor of matching the current Python `urlparse` behavior.
