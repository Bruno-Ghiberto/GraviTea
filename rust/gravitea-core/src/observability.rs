//! Observability hot-path functions: path normalization and endpoint sanitization.
//!
//! These functions run on every HTTP request in the Prometheus metrics middleware.
//! They use 24 pre-compiled `LazyLock<Regex>` patterns to replace dynamic path
//! segments (UUIDs, integer IDs) and sensitive keywords (passwords, tokens, secrets)
//! with neutral placeholders, preventing metric cardinality explosion and data leakage.
//!
//! Port of `backend/apps/core/observability/metrics.py` lines 40–131.

use pyo3::prelude::*;
use regex::Regex;
use std::sync::LazyLock;

// =============================================================================
// Group 1: PATH_NORMALIZERS (2 patterns)
// =============================================================================

/// UUID pattern: `/550e8400-e29b-41d4-a716-446655440000` → `/{id}`
/// Uses `(/|$)` capture group instead of lookahead (unsupported by `regex` crate).
/// Replacement uses `$1` to preserve the trailing delimiter.
static RE_UUID: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i)/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}(/|$)")
        .unwrap()
});

/// Integer ID pattern: `/123` → `/{id}` (case-sensitive — no `(?i)`)
/// Uses `(/|$)` capture group instead of lookahead (unsupported by `regex` crate).
/// Replacement uses `$1` to preserve the trailing delimiter.
static RE_INT_ID: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"/\d+(/|$)").unwrap());

// =============================================================================
// Group 2: SENSITIVE_ENDPOINT_PATTERNS (16 patterns, all case-insensitive)
// =============================================================================

static RE_PASSWORD_RESET: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?i)/password[-_]?reset/?").unwrap());

static RE_CHANGE_PASSWORD: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?i)/change[-_]?password/?").unwrap());

static RE_RESET_PASSWORD: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?i)/reset[-_]?password/?").unwrap());

static RE_FORGOT_PASSWORD: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?i)/forgot[-_]?password/?").unwrap());

static RE_TOKEN_VALUE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?i)/token/[^/]+/?").unwrap());

static RE_TOKEN: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?i)/token/?").unwrap());

static RE_REFRESH_TOKEN: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?i)/refresh[-_]?token/?").unwrap());

static RE_API_KEY_VALUE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?i)/api[-_]?key/[^/]+/?").unwrap());

static RE_API_KEY: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?i)/api[-_]?key/?").unwrap());

static RE_SECRET_VALUE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?i)/secret/[^/]+/?").unwrap());

static RE_SECRET: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?i)/secret/?").unwrap());

static RE_CREDENTIAL_VALUE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?i)/credential/[^/]+/?").unwrap());

static RE_CREDENTIAL: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?i)/credential/?").unwrap());

static RE_PRIVATE_KEY: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?i)/private[-_]?key/?").unwrap());

static RE_VERIFY_VALUE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?i)/verify/[^/]+/?").unwrap());

static RE_ACTIVATE_VALUE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?i)/activate/[^/]+/?").unwrap());

// =============================================================================
// Group 3: FALLBACK WORD-BOUNDARY PATTERNS (6 patterns, all case-insensitive)
// =============================================================================

static RE_FALLBACK_PASSWORD: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?i)\bpassword\b").unwrap());

static RE_FALLBACK_SECRET: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?i)\bsecret\b").unwrap());

static RE_FALLBACK_TOKEN: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?i)\btoken\b").unwrap());

static RE_FALLBACK_API_KEY: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?i)\bapi[_-]?key\b").unwrap());

static RE_FALLBACK_PRIVATE_KEY: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?i)\bprivate[_-]?key\b").unwrap());

static RE_FALLBACK_CREDENTIAL: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?i)\bcredential\b").unwrap());

// =============================================================================
// Pattern arrays for ordered iteration
// =============================================================================

/// Path normalizer patterns applied in order: UUID first, then integer ID.
/// Replacements use `$1` to preserve the captured trailing delimiter (`/` or end).
static PATH_NORMALIZERS: &[(&LazyLock<Regex>, &str)] = &[
    (&RE_UUID, "/{id}$1"),
    (&RE_INT_ID, "/{id}$1"),
];

/// Sensitive endpoint patterns applied in order (16 entries).
static SENSITIVE_PATTERNS: &[(&LazyLock<Regex>, &str)] = &[
    (&RE_PASSWORD_RESET, "/auth-action/"),
    (&RE_CHANGE_PASSWORD, "/auth-action/"),
    (&RE_RESET_PASSWORD, "/auth-action/"),
    (&RE_FORGOT_PASSWORD, "/auth-action/"),
    (&RE_TOKEN_VALUE, "/auth/{redacted}/"),
    (&RE_TOKEN, "/auth/"),
    (&RE_REFRESH_TOKEN, "/auth-refresh/"),
    (&RE_API_KEY_VALUE, "/key/{redacted}/"),
    (&RE_API_KEY, "/key/"),
    (&RE_SECRET_VALUE, "/{redacted}/"),
    (&RE_SECRET, "/{redacted}/"),
    (&RE_CREDENTIAL_VALUE, "/{redacted}/"),
    (&RE_CREDENTIAL, "/{redacted}/"),
    (&RE_PRIVATE_KEY, "/{redacted}/"),
    (&RE_VERIFY_VALUE, "/verify/{redacted}/"),
    (&RE_ACTIVATE_VALUE, "/activate/{redacted}/"),
];

/// Fallback word-boundary patterns applied after sensitive patterns (6 entries).
static FALLBACK_PATTERNS: &[(&LazyLock<Regex>, &str)] = &[
    (&RE_FALLBACK_PASSWORD, "auth"),
    (&RE_FALLBACK_SECRET, "redacted"),
    (&RE_FALLBACK_TOKEN, "auth"),
    (&RE_FALLBACK_API_KEY, "key"),
    (&RE_FALLBACK_PRIVATE_KEY, "redacted"),
    (&RE_FALLBACK_CREDENTIAL, "redacted"),
];

// =============================================================================
// Internal functions (pure Rust, no PyO3 dependency)
// =============================================================================

/// Strip query params and normalize UUIDs/integer IDs in URL paths.
fn normalize_path_internal(path: &str) -> String {
    // Strip query parameters
    let path_without_query = match path.find('?') {
        Some(idx) => &path[..idx],
        None => path,
    };

    let mut normalized = path_without_query.to_string();
    for (pattern, replacement) in PATH_NORMALIZERS {
        normalized = pattern.replace_all(&normalized, *replacement).into_owned();
    }
    normalized
}

/// Sanitize endpoint labels by replacing sensitive keywords with neutral terms.
fn sanitize_endpoint_label_internal(endpoint: &str) -> String {
    let mut sanitized = endpoint.to_string();

    // Apply 16 compiled sensitive patterns in order
    for (pattern, replacement) in SENSITIVE_PATTERNS {
        sanitized = pattern.replace_all(&sanitized, *replacement).into_owned();
    }

    // Apply 6 fallback word-boundary patterns in order
    for (pattern, replacement) in FALLBACK_PATTERNS {
        sanitized = pattern.replace_all(&sanitized, *replacement).into_owned();
    }

    sanitized
}

// =============================================================================
// PyO3 function wrappers (NO GIL release — sub-microsecond ops)
// =============================================================================

/// Normalize a URL path for Prometheus metric labels.
///
/// Strips query parameters, replaces UUIDs and integer IDs with `{id}`.
#[pyfunction]
pub fn normalize_path(path: &str) -> String {
    normalize_path_internal(path)
}

/// Sanitize an endpoint label for Prometheus metric labels.
///
/// Replaces sensitive keywords (passwords, tokens, secrets, credentials)
/// with neutral placeholders to prevent data leakage in metrics.
#[pyfunction]
pub fn sanitize_endpoint_label(endpoint: &str) -> String {
    sanitize_endpoint_label_internal(endpoint)
}

// =============================================================================
// Tests
// =============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    // -------------------------------------------------------------------------
    // normalize_path tests
    // -------------------------------------------------------------------------

    #[test]
    fn test_uuid_replacement() {
        assert_eq!(
            normalize_path_internal("/api/v1/products/550e8400-e29b-41d4-a716-446655440000/"),
            "/api/v1/products/{id}/"
        );
    }

    #[test]
    fn test_uuid_case_insensitive() {
        assert_eq!(
            normalize_path_internal("/api/v1/items/550E8400-E29B-41D4-A716-446655440000"),
            "/api/v1/items/{id}"
        );
    }

    #[test]
    fn test_integer_id_replacement() {
        assert_eq!(
            normalize_path_internal("/api/v1/branches/123/products/"),
            "/api/v1/branches/{id}/products/"
        );
    }

    #[test]
    fn test_multiple_ids() {
        assert_eq!(
            normalize_path_internal("/api/v1/tenants/123/branches/456/products/789"),
            "/api/v1/tenants/{id}/branches/{id}/products/{id}"
        );
    }

    #[test]
    fn test_query_param_stripping() {
        assert_eq!(
            normalize_path_internal("/api/v1/products?page=1&size=10"),
            "/api/v1/products"
        );
    }

    #[test]
    fn test_query_param_with_id() {
        assert_eq!(
            normalize_path_internal("/api/v1/products/42?page=1"),
            "/api/v1/products/{id}"
        );
    }

    // -------------------------------------------------------------------------
    // sanitize_endpoint_label: Group 2 (sensitive patterns)
    // -------------------------------------------------------------------------

    #[test]
    fn test_password_reset() {
        assert_eq!(
            sanitize_endpoint_label_internal("/api/v1/password-reset/"),
            "/api/v1/auth-action/"
        );
    }

    #[test]
    fn test_change_password() {
        assert_eq!(
            sanitize_endpoint_label_internal("/api/v1/change_password/"),
            "/api/v1/auth-action/"
        );
    }

    #[test]
    fn test_reset_password() {
        assert_eq!(
            sanitize_endpoint_label_internal("/api/v1/reset-password/"),
            "/api/v1/auth-action/"
        );
    }

    #[test]
    fn test_forgot_password() {
        assert_eq!(
            sanitize_endpoint_label_internal("/api/v1/forgot_password/"),
            "/api/v1/auth-action/"
        );
    }

    #[test]
    fn test_token_with_value() {
        assert_eq!(
            sanitize_endpoint_label_internal("/api/v1/token/abc123xyz/"),
            "/api/v1/auth/{redacted}/"
        );
    }

    #[test]
    fn test_token_bare() {
        assert_eq!(
            sanitize_endpoint_label_internal("/api/v1/token/"),
            "/api/v1/auth/"
        );
    }

    #[test]
    fn test_refresh_token() {
        assert_eq!(
            sanitize_endpoint_label_internal("/api/v1/refresh-token/"),
            "/api/v1/auth-refresh/"
        );
    }

    #[test]
    fn test_api_key_with_value() {
        assert_eq!(
            sanitize_endpoint_label_internal("/api/v1/api-key/mykey123/"),
            "/api/v1/key/{redacted}/"
        );
    }

    #[test]
    fn test_api_key_bare() {
        assert_eq!(
            sanitize_endpoint_label_internal("/api/v1/api_key/"),
            "/api/v1/key/"
        );
    }

    #[test]
    fn test_secret_with_value() {
        assert_eq!(
            sanitize_endpoint_label_internal("/api/v1/secret/mysecret/"),
            "/api/v1/{redacted}/"
        );
    }

    #[test]
    fn test_secret_bare() {
        assert_eq!(
            sanitize_endpoint_label_internal("/api/v1/secret/"),
            "/api/v1/{redacted}/"
        );
    }

    #[test]
    fn test_credential_with_value() {
        assert_eq!(
            sanitize_endpoint_label_internal("/api/v1/credential/abc/"),
            "/api/v1/{redacted}/"
        );
    }

    #[test]
    fn test_credential_bare() {
        assert_eq!(
            sanitize_endpoint_label_internal("/api/v1/credential/"),
            "/api/v1/{redacted}/"
        );
    }

    #[test]
    fn test_private_key() {
        assert_eq!(
            sanitize_endpoint_label_internal("/api/v1/private-key/"),
            "/api/v1/{redacted}/"
        );
    }

    #[test]
    fn test_verify_with_value() {
        assert_eq!(
            sanitize_endpoint_label_internal("/api/v1/verify/abc123/"),
            "/api/v1/verify/{redacted}/"
        );
    }

    #[test]
    fn test_activate_with_value() {
        assert_eq!(
            sanitize_endpoint_label_internal("/api/v1/activate/abc123/"),
            "/api/v1/activate/{redacted}/"
        );
    }

    // -------------------------------------------------------------------------
    // sanitize_endpoint_label: Group 3 (fallback word-boundary patterns)
    // -------------------------------------------------------------------------

    #[test]
    fn test_fallback_password() {
        assert_eq!(
            sanitize_endpoint_label_internal("/some-password-endpoint"),
            "/some-auth-endpoint"
        );
    }

    #[test]
    fn test_fallback_secret() {
        assert_eq!(
            sanitize_endpoint_label_internal("/my-secret-path"),
            "/my-redacted-path"
        );
    }

    #[test]
    fn test_fallback_token() {
        assert_eq!(
            sanitize_endpoint_label_internal("/custom-token-check"),
            "/custom-auth-check"
        );
    }

    #[test]
    fn test_fallback_api_key() {
        assert_eq!(
            sanitize_endpoint_label_internal("/check-api-key-status"),
            "/check-key-status"
        );
    }

    #[test]
    fn test_fallback_private_key() {
        assert_eq!(
            sanitize_endpoint_label_internal("/validate-private-key"),
            "/validate-redacted"
        );
    }

    #[test]
    fn test_fallback_credential() {
        assert_eq!(
            sanitize_endpoint_label_internal("/user-credential-info"),
            "/user-redacted-info"
        );
    }

    // -------------------------------------------------------------------------
    // Combined scenario tests
    // -------------------------------------------------------------------------

    #[test]
    fn test_uuid_plus_sensitive() {
        // Token path with a UUID value — token pattern fires first
        assert_eq!(
            sanitize_endpoint_label_internal(
                "/api/v1/token/550e8400-e29b-41d4-a716-446655440000/"
            ),
            "/api/v1/auth/{redacted}/"
        );
    }

    #[test]
    fn test_case_insensitive_sensitive() {
        assert_eq!(
            sanitize_endpoint_label_internal("/api/v1/Password-Reset/"),
            "/api/v1/auth-action/"
        );
    }

    // -------------------------------------------------------------------------
    // Edge case tests
    // -------------------------------------------------------------------------

    #[test]
    fn test_empty_string() {
        assert_eq!(normalize_path_internal(""), "");
        assert_eq!(sanitize_endpoint_label_internal(""), "");
    }

    #[test]
    fn test_root_path() {
        assert_eq!(normalize_path_internal("/"), "/");
        assert_eq!(sanitize_endpoint_label_internal("/"), "/");
    }

    #[test]
    fn test_long_path() {
        let long_segment = "a".repeat(1000);
        let path = format!("/api/v1/{}/details", long_segment);
        let result = normalize_path_internal(&path);
        assert_eq!(result, path); // no IDs to replace, passes through
    }

    #[test]
    fn test_unicode_passthrough() {
        assert_eq!(
            normalize_path_internal("/api/v1/productos/café/"),
            "/api/v1/productos/café/"
        );
    }

    #[test]
    fn test_double_slashes() {
        let result = normalize_path_internal("//api//v1//");
        assert_eq!(result, "//api//v1//"); // slashes preserved
    }

    #[test]
    fn test_no_false_positive_integer_mid_word() {
        // Integer pattern requires leading `/`, so `abc123` should NOT match
        assert_eq!(
            normalize_path_internal("/api/v1/abc123def"),
            "/api/v1/abc123def"
        );
    }

    #[test]
    fn test_password_underscore_variant() {
        assert_eq!(
            sanitize_endpoint_label_internal("/api/v1/password_reset/"),
            "/api/v1/auth-action/"
        );
    }

    #[test]
    fn test_no_trailing_slash() {
        assert_eq!(
            sanitize_endpoint_label_internal("/api/v1/token"),
            "/api/v1/auth/"
        );
    }
}
