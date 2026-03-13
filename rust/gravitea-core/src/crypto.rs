use aes_gcm::{
    aead::{Aead, KeyInit, OsRng},
    Aes256Gcm, AeadCore,
};
use base64::{engine::general_purpose, Engine as _};
use hmac::{Hmac, Mac};
use pyo3::prelude::*;
use sha2::Sha256;
use unicode_normalization::UnicodeNormalization;

use crate::GraviteaError;

type HmacSha256 = Hmac<Sha256>;

// =============================================================================
// Internal functions (testable without Python interpreter)
// =============================================================================

/// Internal: encrypt a plaintext string using AES-256-GCM.
/// Returns base64(nonce[12] || ciphertext || tag[16]).
fn encrypt_value_internal(plaintext: &str, key: &[u8]) -> Result<String, GraviteaError> {
    // T011: key-length validation
    if key.len() != 32 {
        return Err(GraviteaError::InvalidInput(
            "key must be exactly 32 bytes".to_string(),
        ));
    }

    // T009: AES-256-GCM encryption
    let cipher = Aes256Gcm::new_from_slice(key)
        .map_err(|e| GraviteaError::CryptoError(e.to_string()))?;
    let nonce = Aes256Gcm::generate_nonce(&mut OsRng);
    let ciphertext_with_tag = cipher
        .encrypt(&nonce, plaintext.as_bytes())
        .map_err(|e| GraviteaError::CryptoError(e.to_string()))?;

    // Wire format: base64_STANDARD(nonce[12] || ciphertext || tag[16])
    let blob = [nonce.as_slice(), ciphertext_with_tag.as_slice()].concat();
    Ok(general_purpose::STANDARD.encode(&blob))
}

/// Internal: decrypt an AES-256-GCM encrypted value.
/// Expects base64(nonce[12] || ciphertext || tag[16]).
fn decrypt_value_internal(encrypted: &str, key: &[u8]) -> Result<String, GraviteaError> {
    // T011: key-length validation
    if key.len() != 32 {
        return Err(GraviteaError::InvalidInput(
            "key must be exactly 32 bytes".to_string(),
        ));
    }

    // T010: AES-256-GCM decryption
    let raw = general_purpose::STANDARD
        .decode(encrypted)
        .map_err(|e| GraviteaError::CryptoError(format!("base64 decode failed: {e}")))?;

    if raw.len() < 12 + 16 {
        return Err(GraviteaError::CryptoError(
            "encrypted data too short".to_string(),
        ));
    }

    let nonce_bytes = &raw[..12];
    let ciphertext_with_tag = &raw[12..];

    let nonce = aes_gcm::Nonce::from_slice(nonce_bytes);
    let cipher = Aes256Gcm::new_from_slice(key)
        .map_err(|e| GraviteaError::CryptoError(e.to_string()))?;

    let plaintext_bytes = cipher
        .decrypt(nonce, ciphertext_with_tag)
        .map_err(|e| GraviteaError::CryptoError(format!("decryption failed: {e}")))?;

    String::from_utf8(plaintext_bytes)
        .map_err(|e| GraviteaError::CryptoError(format!("invalid UTF-8: {e}")))
}

/// Internal: normalise value for blind index computation.
/// Order: NFC -> to_lowercase() -> trim() (mandatory per FR-003).
fn normalise_for_blind_index(value: &str) -> String {
    value
        .nfc()
        .collect::<String>()
        .to_lowercase()
        .trim()
        .to_string()
}

/// Internal: compute blind index from a value and HMAC key.
/// Used by both the pyfunction and proptests.
fn compute_blind_index_internal(value: &str, hmac_key: &[u8]) -> Result<String, GraviteaError> {
    if hmac_key.len() != 32 {
        return Err(GraviteaError::InvalidInput(
            "key must be exactly 32 bytes".to_string(),
        ));
    }

    let normalised = normalise_for_blind_index(value);

    let mut mac = <HmacSha256 as Mac>::new_from_slice(hmac_key)
        .map_err(|_| GraviteaError::InvalidInput("invalid HMAC key length".to_string()))?;
    mac.update(normalised.as_bytes());

    Ok(hex::encode(mac.finalize().into_bytes()))
}

// =============================================================================
// PyO3 exports (thin wrappers)
// =============================================================================

/// Encrypt a plaintext string using AES-256-GCM.
///
/// Returns base64(nonce[12] || ciphertext || tag[16]).
#[pyfunction]
pub fn encrypt_value(plaintext: &str, key: &[u8]) -> PyResult<String> {
    encrypt_value_internal(plaintext, key).map_err(|e| e.into())
}

/// Decrypt an AES-256-GCM encrypted value.
///
/// Expects base64(nonce[12] || ciphertext || tag[16]).
#[pyfunction]
pub fn decrypt_value(encrypted: &str, key: &[u8]) -> PyResult<String> {
    decrypt_value_internal(encrypted, key).map_err(|e| e.into())
}

/// Compute HMAC-SHA256 blind index with NFC normalisation.
///
/// Order: NFC -> to_lowercase() -> trim() -> HMAC-SHA256 -> hex.
#[pyfunction]
pub fn compute_blind_index(value: &str, hmac_key: &[u8]) -> PyResult<String> {
    compute_blind_index_internal(value, hmac_key).map_err(|e| e.into())
}

// =============================================================================
// Tests
// =============================================================================

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashSet;

    // =========================================================================
    // T007: Roundtrip, nonce uniqueness, wrong-key rejection, tag mismatch
    // =========================================================================

    #[test]
    fn test_encrypt_decrypt_roundtrip() {
        let key = [0u8; 32];
        let encrypted = encrypt_value_internal("hello", &key).unwrap();
        let decrypted = decrypt_value_internal(&encrypted, &key).unwrap();
        assert_eq!(decrypted, "hello");
    }

    #[test]
    fn test_nonce_uniqueness() {
        let key = [0u8; 32];
        let mut blobs = HashSet::new();
        for _ in 0..1000 {
            let encrypted = encrypt_value_internal("same plaintext", &key).unwrap();
            blobs.insert(encrypted);
        }
        assert_eq!(blobs.len(), 1000, "All 1000 encryptions must produce distinct blobs");
    }

    #[test]
    fn test_wrong_key_rejection() {
        let key1 = [0u8; 32];
        let key2 = [1u8; 32];
        let encrypted = encrypt_value_internal("hello", &key1).unwrap();
        let result = decrypt_value_internal(&encrypted, &key2);
        assert!(result.is_err());
        // Verify it is CryptoError, not InvalidInput
        match result.unwrap_err() {
            GraviteaError::CryptoError(msg) => {
                assert!(msg.contains("decryption failed"), "Expected 'decryption failed', got: {msg}");
            }
            other => panic!("Expected CryptoError, got: {other}"),
        }
    }

    #[test]
    fn test_tag_mismatch_returns_crypto_error() {
        let key = [0u8; 32];
        let encrypted = encrypt_value_internal("hello", &key).unwrap();

        // Decode, flip last byte (part of tag), re-encode
        let mut raw = general_purpose::STANDARD.decode(&encrypted).unwrap();
        let last = raw.len() - 1;
        raw[last] ^= 0xFF;
        let tampered = general_purpose::STANDARD.encode(&raw);

        let result = decrypt_value_internal(&tampered, &key);
        assert!(result.is_err());
        match result.unwrap_err() {
            GraviteaError::CryptoError(msg) => {
                assert!(msg.contains("decryption failed"), "Expected 'decryption failed', got: {msg}");
            }
            other => panic!("Expected CryptoError, got: {other}"),
        }
    }

    // =========================================================================
    // T008: Key length validation tests
    // =========================================================================

    #[test]
    fn test_encrypt_short_key() {
        let key = [0u8; 16];
        let result = encrypt_value_internal("hello", &key);
        assert!(result.is_err());
        match result.unwrap_err() {
            GraviteaError::InvalidInput(msg) => {
                assert!(msg.contains("key must be exactly 32 bytes"), "Got: {msg}");
            }
            other => panic!("Expected InvalidInput for short key, got: {other}"),
        }
    }

    #[test]
    fn test_encrypt_off_by_one_key() {
        // 31-byte key
        let key31 = [0u8; 31];
        let result31 = encrypt_value_internal("hello", &key31);
        assert!(result31.is_err());
        match result31.unwrap_err() {
            GraviteaError::InvalidInput(msg) => {
                assert!(msg.contains("key must be exactly 32 bytes"), "31-byte: got: {msg}");
            }
            other => panic!("31-byte key: expected InvalidInput, got: {other}"),
        }

        // 33-byte key
        let key33 = [0u8; 33];
        let result33 = encrypt_value_internal("hello", &key33);
        assert!(result33.is_err());
        match result33.unwrap_err() {
            GraviteaError::InvalidInput(msg) => {
                assert!(msg.contains("key must be exactly 32 bytes"), "33-byte: got: {msg}");
            }
            other => panic!("33-byte key: expected InvalidInput, got: {other}"),
        }
    }

    #[test]
    fn test_decrypt_short_key() {
        let key = [0u8; 16];
        // Use a dummy encrypted value (doesn't matter, key check comes first)
        let result = decrypt_value_internal("dGVzdA==", &key);
        assert!(result.is_err());
        match result.unwrap_err() {
            GraviteaError::InvalidInput(msg) => {
                assert!(msg.contains("key must be exactly 32 bytes"), "Got: {msg}");
            }
            other => panic!("Expected InvalidInput for short decrypt key, got: {other}"),
        }
    }

    // =========================================================================
    // T025: Blind index tests
    // =========================================================================

    #[test]
    fn test_blind_index_case_insensitive() {
        let key = [0u8; 32];
        let upper = compute_blind_index_internal("SMITH", &key).unwrap();
        let lower = compute_blind_index_internal("smith", &key).unwrap();
        assert_eq!(upper, lower);
    }

    #[test]
    fn test_blind_index_whitespace_strip() {
        let key = [0u8; 32];
        let padded = compute_blind_index_internal("  smith  ", &key).unwrap();
        let clean = compute_blind_index_internal("smith", &key).unwrap();
        assert_eq!(padded, clean);
    }

    #[test]
    fn test_blind_index_nfc_normalisation() {
        let key = [0u8; 32];
        // NFD: n + combining tilde
        let nfd = compute_blind_index_internal("n\u{0303}", &key).unwrap();
        // NFC: precomposed enye
        let nfc = compute_blind_index_internal("\u{00F1}", &key).unwrap();
        assert_eq!(nfd, nfc, "NFD and NFC forms must produce identical blind index");
    }

    #[test]
    fn test_blind_index_cuit_passthrough() {
        let key = [0u8; 32];
        let result = compute_blind_index_internal("20123456789", &key).unwrap();
        assert_eq!(result.len(), 64, "HMAC-SHA256 hex output must be 64 chars");
        // Must be lowercase hex
        assert!(
            result.chars().all(|c| c.is_ascii_hexdigit() && !c.is_ascii_uppercase()),
            "Output must be lowercase hex, got: {result}"
        );
    }

    #[test]
    fn test_blind_index_wrong_key_length() {
        let key = [0u8; 16];
        let result = compute_blind_index_internal("smith", &key);
        assert!(result.is_err());
        match result.unwrap_err() {
            GraviteaError::InvalidInput(msg) => {
                assert!(msg.contains("key must be exactly 32 bytes"), "Got: {msg}");
            }
            other => panic!("Expected InvalidInput for wrong HMAC key length, got: {other}"),
        }
    }
}

// =============================================================================
// T040: Proptest property-based tests
// =============================================================================

#[cfg(test)]
mod proptests {
    use super::*;
    use proptest::prelude::*;

    proptest! {
        #[test]
        fn test_blind_index_idempotent(s in "[a-zA-Z0-9]{1,64}") {
            let key = [0u8; 32];
            let r1 = compute_blind_index_internal(&s, &key).unwrap();
            let r2 = compute_blind_index_internal(&s, &key).unwrap();
            prop_assert_eq!(r1, r2);
        }

        #[test]
        fn test_blind_index_case_normalisation_idempotent(s in "[a-zA-Z0-9]{1,64}") {
            let key = [0u8; 32];
            let lower_result = compute_blind_index_internal(&s, &key).unwrap();
            let upper_input = s.to_uppercase();
            let upper_result = compute_blind_index_internal(&upper_input, &key).unwrap();
            prop_assert_eq!(lower_result, upper_result);
        }
    }
}
