# Feature Specification: Rust Observability Hot Path Acceleration

**Feature Branch**: `021-rust-observability-hotpath`
**Created**: 2026-02-27
**Status**: Draft
**Input**: Accelerate the per-request path normalization and endpoint sanitization functions with compiled Rust regex, replacing 24 sequential Python regex operations
**Depends on**: SPEC-017 (Rust Toolchain Bootstrap) — COMPLETE

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Path Normalization Produces Identical Results (Priority: P1)

The system normalizes URL paths in HTTP request metrics by replacing dynamic segments (UUIDs, integer IDs) with a placeholder token, preventing metric label cardinality explosion. After acceleration, the normalized output is byte-for-byte identical to the current behavior for every URL pattern the system encounters.

**Why this priority**: Path normalization runs on every single HTTP request. If the accelerated version produces different output, Prometheus dashboards break — operators see duplicate metric series, alerts fire incorrectly, and historical data becomes incomparable. Correctness is the absolute prerequisite before any performance work matters.

**Independent Test**: Can be fully tested by passing a corpus of 50+ URL paths through both the current and accelerated implementations and asserting identical output for every path. Delivers immediate confidence that the migration is safe.

**Acceptance Scenarios**:

1. **Given** a URL path containing a UUID segment (e.g., `/api/v1/products/550e8400-e29b-41d4-a716-446655440000/details`), **When** path normalization is applied, **Then** the UUID is replaced with `{id}` (output: `/api/v1/products/{id}/details`).
2. **Given** a URL path containing one or more integer ID segments (e.g., `/api/v1/tenants/123/branches/456/products/789`), **When** path normalization is applied, **Then** all integer segments are replaced with `{id}` (output: `/api/v1/tenants/{id}/branches/{id}/products/{id}`).
3. **Given** a URL path with query parameters (e.g., `/api/v1/products/123?sort=name&page=2`), **When** path normalization is applied, **Then** query parameters are stripped and the ID is replaced (output: `/api/v1/products/{id}`).
4. **Given** a URL path without any dynamic segments (e.g., `/health/live`, `/metrics`), **When** path normalization is applied, **Then** the path is returned unchanged.
5. **Given** an empty string or root path (`/`), **When** path normalization is applied, **Then** the input is returned as-is without error.

---

### User Story 2 - Endpoint Sanitization Redacts Sensitive Data (Priority: P1)

The system sanitizes endpoint labels in Prometheus metrics by redacting sensitive keywords (passwords, tokens, secrets, credentials, API keys) from URL paths. After acceleration, the sanitized output is identical to the current behavior across all 22 redaction patterns, ensuring no sensitive data leaks into the metrics system.

**Why this priority**: Sensitive data exposure in Prometheus labels is a security incident. If the accelerated sanitization misses even one pattern, passwords or tokens could appear in metric dashboards, alerting systems, and log aggregators. This is a security-critical function that must maintain exact parity.

**Independent Test**: Can be fully tested by passing URL paths containing each category of sensitive keyword through both implementations and asserting identical output. Delivers immediate confidence that no security regression occurs.

**Acceptance Scenarios**:

1. **Given** a URL path containing a password-related segment (e.g., `/api/v1/auth/password-reset/`), **When** endpoint sanitization is applied, **Then** the segment is replaced with a neutral term (output: `/api/v1/auth/auth-action/`).
2. **Given** a URL path containing a token with value (e.g., `/api/v1/token/abc123xyz/`), **When** endpoint sanitization is applied, **Then** the token value is redacted (output: `/api/v1/auth/{redacted}/`).
3. **Given** a URL path containing an API key segment (e.g., `/api/v1/api-key/my-key-value/`), **When** endpoint sanitization is applied, **Then** the value is redacted (output: `/api/v1/key/{redacted}/`).
4. **Given** a URL path containing a secret or credential keyword (e.g., `/api/v1/secret/my-secret/`), **When** endpoint sanitization is applied, **Then** the keyword and value are fully redacted (output: `/api/v1/{redacted}/`).
5. **Given** a URL path containing a sensitive keyword embedded in a larger word (e.g., `/api/v1/passwordless/`), **When** endpoint sanitization is applied, **Then** the word boundary rule prevents false redaction (output: path unchanged for non-matching boundaries).
6. **Given** a URL path containing mixed-case sensitive keywords (e.g., `/api/v1/Token/Reset-PASSWORD/`), **When** endpoint sanitization is applied, **Then** case-insensitive matching correctly redacts the keywords.

---

### User Story 3 - Accelerated Processing Under Load (Priority: P2)

When the system processes a high volume of HTTP requests, the accelerated path normalization and endpoint sanitization complete significantly faster than the current implementation, reducing per-request CPU overhead and improving overall system throughput.

**Why this priority**: Performance is the reason for this acceleration. However, it is secondary to correctness (Stories 1 and 2) because a fast but incorrect implementation has negative value. Once correctness is proven, the performance improvement delivers measurable operational savings.

**Independent Test**: Can be tested by benchmarking both implementations against a corpus of realistic URL paths and measuring execution time. Delivers measurable evidence of the performance improvement.

**Acceptance Scenarios**:

1. **Given** a corpus of 1,000 realistic URL paths, **When** path normalization and endpoint sanitization are applied to each, **Then** the accelerated implementation completes at least 5 times faster than the current implementation.
2. **Given** a sustained load of HTTP requests, **When** the accelerated functions are processing metrics, **Then** concurrent requests are not blocked or delayed by the processing.

---

### User Story 4 - Graceful Fallback When Acceleration Unavailable (Priority: P3)

When the accelerated processing engine is unavailable (e.g., native extension missing after a deployment issue), the system falls back to the current implementation so metrics collection continues to work, even at the original speed.

**Why this priority**: Operational resilience. A deployment issue with the native extension should degrade performance, not disable metrics collection entirely. Metrics are critical for observability — losing them means flying blind.

**Independent Test**: Can be tested by simulating the absence of the native extension and verifying that normalization and sanitization functions still produce correct output.

**Acceptance Scenarios**:

1. **Given** the accelerated engine is not available, **When** a request is processed, **Then** the system uses the fallback implementation and metrics are recorded correctly.
2. **Given** the accelerated engine becomes available again (e.g., after redeployment), **When** the next request is processed, **Then** the system automatically uses the accelerated engine without manual intervention.

---

### Edge Cases

- What happens when the URL path exceeds 1,000 characters? The system should process it correctly without error or performance regression.
- What happens when a URL path contains multiple sensitive keywords in the same segment (e.g., `/api/v1/reset-password/token/abc/`)? All keywords should be redacted in the correct order.
- What happens when a URL path contains Unicode characters (e.g., `/api/v1/productos/busqueda`)? Non-ASCII characters should pass through unchanged; only ASCII-pattern matching should apply.
- What happens when the path is `None` or not a string? The system should handle it gracefully — either return a safe default or raise a clear error.
- What happens when the path contains double slashes (e.g., `/api//v1/products//123`)? The system should normalize consistently with the current behavior (double slashes are preserved, not collapsed).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST normalize URL paths by replacing UUID segments with a placeholder token, producing output identical to the current path normalization behavior.
- **FR-002**: System MUST normalize URL paths by replacing integer ID segments with a placeholder token, producing output identical to the current path normalization behavior.
- **FR-003**: System MUST strip query parameters from URL paths before applying normalization patterns.
- **FR-004**: System MUST sanitize endpoint labels by redacting password-related keywords from URL paths using 4 distinct patterns (password-reset, change-password, reset-password, forgot-password).
- **FR-005**: System MUST sanitize endpoint labels by redacting token-related segments from URL paths using 3 distinct patterns (token with value, bare token, refresh-token).
- **FR-006**: System MUST sanitize endpoint labels by redacting API key segments from URL paths using 2 distinct patterns (api-key with value, bare api-key).
- **FR-007**: System MUST sanitize endpoint labels by redacting secret, credential, and private-key segments from URL paths using 5 distinct patterns.
- **FR-008**: System MUST sanitize endpoint labels by redacting verification and activation token values from URL paths using 2 distinct patterns.
- **FR-009**: System MUST apply 6 fallback word-boundary substitutions after primary sanitization to catch any remaining sensitive keywords that were not matched by the primary patterns.
- **FR-010**: System MUST apply all sanitization patterns with case-insensitive matching.
- **FR-011**: System MUST apply sanitization patterns in a defined order: primary compiled patterns first (in order), then fallback word-boundary patterns (in order).
- **FR-012**: System MUST provide a fallback implementation that activates automatically when the accelerated engine is unavailable, producing identical output.
- **FR-013**: System MUST NOT block concurrent request processing during path normalization or endpoint sanitization.
- **FR-014**: System MUST produce byte-for-byte identical output to the current implementation for every URL path pattern, verified by automated equivalence tests.
- **FR-015**: System MUST be available within the containerized deployment without additional runtime dependencies beyond what the build process provides.

### Key Entities

- **URL Path**: A string representing the path component of an HTTP request URL, typically 20-100 characters, used as input to both normalization and sanitization functions.
- **Normalized Path**: The output of path normalization, where dynamic segments (UUIDs, integers) are replaced with `{id}` to prevent metric cardinality explosion.
- **Sanitized Endpoint Label**: The output of endpoint sanitization, where sensitive keywords (passwords, tokens, secrets) are redacted to prevent security-sensitive data from appearing in metrics labels.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The accelerated implementation produces identical output to the current implementation for a test corpus of at least 50 diverse URL paths, including all 24 pattern categories.
- **SC-002**: The accelerated implementation processes 1,000 URL paths at least 5 times faster than the current implementation, measured by automated benchmark.
- **SC-003**: The system correctly sanitizes all 22 categories of sensitive endpoint patterns (16 primary + 6 fallback), verified by individual pattern tests.
- **SC-004**: The fallback mechanism activates automatically when the accelerated engine is unavailable and produces correct output without manual intervention.
- **SC-005**: The containerized deployment includes the accelerated functions and passes all observability-related automated tests.
- **SC-006**: The complete automated test suite passes with zero regressions after the accelerated engine is integrated.
- **SC-007**: End-to-end request processing through the middleware chain records metrics with correctly normalized and sanitized endpoint labels.

## Assumptions

- URL paths are standard ASCII HTTP paths. While Unicode characters may appear (e.g., in percent-encoded form or UTF-8 path segments), the regex patterns only match ASCII keywords and placeholders. Non-ASCII content passes through unchanged.
- The current Python implementation is the source of truth for correctness. Any ambiguity in expected output is resolved by running the input through the existing Python functions.
- Pattern application order within each group (primary patterns, fallback patterns) must match the current Python list ordering to ensure identical output when multiple patterns could match the same input.
- The system processes a maximum of approximately 1,000 requests per second under normal load. The performance improvement is measured in aggregate CPU savings, not in user-visible latency (individual request processing is already sub-millisecond).
- The accelerated engine and the fallback implementation are functionally interchangeable — callers cannot and should not distinguish between them.
