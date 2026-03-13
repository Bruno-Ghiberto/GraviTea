"""
Tests for AES-256-GCM encryption/decryption and HMAC-SHA256 blind indexing.

Covers T038: Test encryption utilities and fields per research.md specifications.

Security Focus:
- AES-256-GCM authenticated encryption
- Tamper detection via GCM tag
- HMAC-SHA256 blind index consistency
- Key validation and error handling
- Unicode and special character support
"""

import base64
import os

import pytest

from apps.core.encryption.utils import (compute_blind_index, decrypt_value,
                                        encrypt_value, get_encryption_key,
                                        get_hmac_key)

# ============================================================
# Test Fixtures
# ============================================================


@pytest.fixture
def test_encryption_key():
    """Generate a valid 32-byte encryption key for testing."""
    return base64.b64encode(os.urandom(32)).decode("utf-8")


@pytest.fixture
def test_hmac_key():
    """Generate a valid 32-byte HMAC key for testing."""
    return base64.b64encode(os.urandom(32)).decode("utf-8")


@pytest.fixture
def encryption_settings(test_encryption_key, test_hmac_key, settings):
    """Configure Django settings with test keys."""
    settings.ENCRYPTION_KEY = test_encryption_key
    settings.HMAC_KEY = test_hmac_key
    # Clear lru_cache to ensure new keys are loaded
    get_encryption_key.cache_clear()
    get_hmac_key.cache_clear()
    return settings


# ============================================================
# AES-256-GCM Encryption Tests
# ============================================================


class TestAES256GCMEncryption:
    """Test suite for AES-256-GCM encryption utilities."""

    def test_encrypt_decrypt_roundtrip(self, encryption_settings):
        """Test basic encryption and decryption roundtrip."""
        plaintext = "This is sensitive PII data"

        encrypted = encrypt_value(plaintext)
        decrypted = decrypt_value(encrypted)

        assert decrypted == plaintext
        assert encrypted != plaintext  # Ensure encryption occurred
        assert len(encrypted) > len(plaintext)  # Base64 + nonce + tag overhead

    def test_encrypt_decrypt_unicode(self, encryption_settings):
        """Test encryption handles Unicode characters correctly."""
        test_cases = [
            "Café résumé",  # Accented characters
            "日本語テスト",  # Japanese
            "中文测试",  # Chinese
            "🎉 emoji test 🔒",  # Emoji
            "Argentiña CUIT: 20-12345678-9",  # Mixed content
        ]

        for plaintext in test_cases:
            encrypted = encrypt_value(plaintext)
            decrypted = decrypt_value(encrypted)
            assert decrypted == plaintext, f"Failed for: {plaintext}"

    def test_encrypt_decrypt_special_characters(self, encryption_settings):
        """Test encryption handles special characters."""
        special_chars = "!@#$%^&*()_+-=[]{}|;':\",./<>?\n\t\r"

        encrypted = encrypt_value(special_chars)
        decrypted = decrypt_value(encrypted)

        assert decrypted == special_chars

    def test_encrypt_decrypt_empty_string(self, encryption_settings):
        """Test encryption returns empty string as-is."""
        assert encrypt_value("") == ""
        assert decrypt_value("") == ""

    def test_encrypt_decrypt_none(self, encryption_settings):
        """Test encryption returns None as-is."""
        assert encrypt_value(None) is None
        assert decrypt_value(None) is None

    def test_encrypt_produces_different_ciphertext(self, encryption_settings):
        """Test that same plaintext produces different ciphertext (random nonce)."""
        plaintext = "Same data encrypted twice"

        encrypted1 = encrypt_value(plaintext)
        encrypted2 = encrypt_value(plaintext)

        # Both should decrypt to same plaintext
        assert decrypt_value(encrypted1) == plaintext
        assert decrypt_value(encrypted2) == plaintext

        # But ciphertext should be different (different nonces)
        assert encrypted1 != encrypted2

    def test_encrypted_format_base64(self, encryption_settings):
        """Test that encrypted output is valid Base64."""
        plaintext = "Test data"

        encrypted = encrypt_value(plaintext)

        # Should be valid base64
        try:
            decoded = base64.b64decode(encrypted)
            assert len(decoded) >= 12  # At least nonce size
        except Exception:
            pytest.fail("Encrypted value is not valid Base64")

    def test_encrypted_contains_nonce(self, encryption_settings):
        """Test that encrypted data contains 12-byte nonce prefix."""
        plaintext = "Test data"

        encrypted = encrypt_value(plaintext)
        decoded = base64.b64decode(encrypted)

        # First 12 bytes should be nonce
        nonce = decoded[:12]
        assert len(nonce) == 12

    @pytest.mark.parametrize("size", [1, 10, 100, 1000, 10000])
    def test_encrypt_various_sizes(self, encryption_settings, size):
        """Test encryption works for various data sizes."""
        plaintext = "x" * size

        encrypted = encrypt_value(plaintext)
        decrypted = decrypt_value(encrypted)

        assert decrypted == plaintext
        assert len(decrypted) == size


# ============================================================
# Tamper Detection Tests (GCM Authentication)
# ============================================================


class TestGCMTamperDetection:
    """Test AES-GCM authentication tag detects tampering."""

    def test_detect_ciphertext_modification(self, encryption_settings):
        """Test that modifying ciphertext causes decryption failure."""
        plaintext = "Sensitive financial data: $999,999.99"

        encrypted = encrypt_value(plaintext)
        decoded = base64.b64decode(encrypted)

        # Modify a byte in the ciphertext (after nonce, before tag)
        modified = bytearray(decoded)
        modified[15] ^= 0xFF  # Flip bits in ciphertext

        tampered = base64.b64encode(bytes(modified)).decode("utf-8")

        with pytest.raises(ValueError, match="Decryption failed"):
            decrypt_value(tampered)

    def test_detect_nonce_modification(self, encryption_settings):
        """Test that modifying nonce causes decryption failure."""
        plaintext = "Test data"

        encrypted = encrypt_value(plaintext)
        decoded = base64.b64decode(encrypted)

        # Modify nonce
        modified = bytearray(decoded)
        modified[0] ^= 0xFF

        tampered = base64.b64encode(bytes(modified)).decode("utf-8")

        with pytest.raises(ValueError, match="Decryption failed"):
            decrypt_value(tampered)

    def test_detect_truncation(self, encryption_settings):
        """Test that truncated ciphertext causes decryption failure."""
        plaintext = "Test data"

        encrypted = encrypt_value(plaintext)
        decoded = base64.b64decode(encrypted)

        # Truncate (remove auth tag)
        truncated = base64.b64encode(decoded[:-16]).decode("utf-8")

        with pytest.raises(ValueError, match="Decryption failed"):
            decrypt_value(truncated)

    def test_invalid_base64_input(self, encryption_settings):
        """Test that invalid Base64 input fails gracefully."""
        with pytest.raises(ValueError, match="Decryption failed"):
            decrypt_value("not-valid-base64!!!")


# ============================================================
# Key Validation Tests
# ============================================================


class TestKeyValidation:
    """Test encryption key validation and error handling."""

    def test_missing_encryption_key(self, settings):
        """Test error when ENCRYPTION_KEY is not set."""
        settings.ENCRYPTION_KEY = ""
        get_encryption_key.cache_clear()

        with pytest.raises(ValueError, match="ENCRYPTION_KEY not set"):
            get_encryption_key()

    def test_missing_hmac_key(self, settings):
        """Test error when HMAC_KEY is not set."""
        settings.HMAC_KEY = ""
        get_hmac_key.cache_clear()

        with pytest.raises(ValueError, match="HMAC_KEY not set"):
            get_hmac_key()

    def test_invalid_encryption_key_length(self, settings):
        """Test error when ENCRYPTION_KEY is wrong length."""
        # 16 bytes instead of 32
        settings.ENCRYPTION_KEY = base64.b64encode(os.urandom(16)).decode("utf-8")
        get_encryption_key.cache_clear()

        with pytest.raises(ValueError, match="exactly 32 bytes"):
            get_encryption_key()

    def test_invalid_hmac_key_length(self, settings):
        """Test error when HMAC_KEY is wrong length."""
        settings.HMAC_KEY = base64.b64encode(os.urandom(16)).decode("utf-8")
        get_hmac_key.cache_clear()

        with pytest.raises(ValueError, match="exactly 32 bytes"):
            get_hmac_key()

    def test_invalid_base64_encryption_key(self, settings):
        """Test error when ENCRYPTION_KEY is invalid Base64."""
        settings.ENCRYPTION_KEY = "not-valid-base64!!!"
        get_encryption_key.cache_clear()

        with pytest.raises(ValueError, match="Invalid ENCRYPTION_KEY"):
            get_encryption_key()

    def test_encryption_fails_without_key(self, settings):
        """Test that encryption fails when key is not configured."""
        settings.ENCRYPTION_KEY = ""
        get_encryption_key.cache_clear()

        with pytest.raises(ValueError):
            encrypt_value("test")

    def test_key_caching(self, encryption_settings):
        """Test that key is cached after first retrieval."""
        key1 = get_encryption_key()
        key2 = get_encryption_key()

        # Should return same cached key
        assert key1 is key2


# ============================================================
# HMAC-SHA256 Blind Index Tests
# ============================================================


class TestBlindIndex:
    """Test HMAC-SHA256 blind indexing for searchable encrypted fields."""

    def test_compute_blind_index_consistency(self, encryption_settings):
        """Test that same input produces same hash."""
        value = "20-12345678-9"

        hash1 = compute_blind_index(value)
        hash2 = compute_blind_index(value)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex output

    def test_blind_index_normalization_lowercase(self, encryption_settings):
        """Test that blind index normalizes to lowercase."""
        assert compute_blind_index("ABC") == compute_blind_index("abc")
        assert compute_blind_index("Test@Email.COM") == compute_blind_index("test@email.com")

    def test_blind_index_normalization_whitespace(self, encryption_settings):
        """Test that blind index strips whitespace."""
        assert compute_blind_index(" test ") == compute_blind_index("test")
        assert compute_blind_index("  20-12345678-9  ") == compute_blind_index("20-12345678-9")

    def test_blind_index_combined_normalization(self, encryption_settings):
        """Test combined lowercase + whitespace normalization."""
        assert compute_blind_index("  ABC  ") == compute_blind_index("abc")

    def test_blind_index_different_inputs(self, encryption_settings):
        """Test that different inputs produce different hashes."""
        hash1 = compute_blind_index("value1")
        hash2 = compute_blind_index("value2")

        assert hash1 != hash2

    def test_blind_index_none(self, encryption_settings):
        """Test that None returns None."""
        assert compute_blind_index(None) is None

    def test_blind_index_hex_format(self, encryption_settings):
        """Test that output is valid hexadecimal."""
        result = compute_blind_index("test")

        # Should be 64 hex characters
        assert len(result) == 64
        # Should be valid hex
        int(result, 16)  # Raises if not valid hex

    def test_blind_index_unicode(self, encryption_settings):
        """Test blind index handles Unicode correctly."""
        # These should produce consistent hashes
        hash1 = compute_blind_index("日本語")
        hash2 = compute_blind_index("日本語")
        assert hash1 == hash2

        # Different Unicode should produce different hashes
        hash3 = compute_blind_index("中文")
        assert hash1 != hash3

    def test_blind_index_deterministic_across_calls(self, encryption_settings):
        """Test that blind index is deterministic (same key = same output)."""
        values = [
            "user@example.com",
            "20-12345678-9",
            "Supplier Name",
        ]

        # Store first computation
        first_hashes = {v: compute_blind_index(v) for v in values}

        # Verify subsequent calls produce same results
        for value in values:
            assert compute_blind_index(value) == first_hashes[value]


# ============================================================
# Integration Tests
# ============================================================


class TestEncryptionIntegration:
    """Integration tests for encryption in realistic scenarios."""

    def test_pii_field_encryption_roundtrip(self, encryption_settings):
        """Test encrypting and decrypting PII data like CUIT."""
        pii_data = [
            ("20-12345678-9", "CUIT"),
            ("user@company.com", "email"),
            ("Av. Corrientes 1234, CABA", "address"),
            ("+54 11 1234-5678", "phone"),
        ]

        for value, field_type in pii_data:
            encrypted = encrypt_value(value)
            decrypted = decrypt_value(encrypted)

            assert decrypted == value, f"Failed for {field_type}: {value}"

    def test_encryption_with_blind_index_workflow(self, encryption_settings):
        """Test typical workflow: encrypt data + compute blind index for search."""
        # Simulate saving a supplier with encrypted tax_id
        tax_id = "20-12345678-9"

        # On save: encrypt and compute blind index
        tax_id_encrypted = encrypt_value(tax_id)
        tax_id_hash = compute_blind_index(tax_id)

        # On search: compute blind index from search term
        search_term = "  20-12345678-9  "  # With whitespace
        search_hash = compute_blind_index(search_term)

        # Search should match (normalized)
        assert search_hash == tax_id_hash

        # On retrieval: decrypt
        retrieved_tax_id = decrypt_value(tax_id_encrypted)
        assert retrieved_tax_id == tax_id

    def test_case_insensitive_search_via_blind_index(self, encryption_settings):
        """Test that blind index enables case-insensitive email search."""
        email = "User@Example.COM"

        # Store normalized hash
        stored_hash = compute_blind_index(email)

        # Search with different casing
        search_variants = [
            "user@example.com",
            "USER@EXAMPLE.COM",
            "User@Example.com",
            " user@example.com ",
        ]

        for search in search_variants:
            assert compute_blind_index(search) == stored_hash

    def test_long_text_encryption(self, encryption_settings):
        """Test encryption of longer text fields like addresses."""
        long_address = """
        Empresa Test S.A.
        Av. Corrientes 1234, Piso 5, Oficina 501
        Ciudad Autónoma de Buenos Aires
        C1043AAZ, Argentina
        Tel: +54 11 1234-5678
        """

        encrypted = encrypt_value(long_address)
        decrypted = decrypt_value(encrypted)

        assert decrypted == long_address


# ============================================================
# Security Edge Cases
# ============================================================


class TestSecurityEdgeCases:
    """Test security-critical edge cases."""

    def test_empty_key_after_strip(self, encryption_settings):
        """Test blind index with value that becomes empty after strip."""
        # Whitespace-only input becomes empty after normalization
        result = compute_blind_index("   ")

        # Should return a consistent hash for empty string
        assert result == compute_blind_index("")

    def test_very_long_input_encryption(self, encryption_settings):
        """Test encryption handles very long inputs."""
        # 1MB of data
        large_data = "x" * (1024 * 1024)

        encrypted = encrypt_value(large_data)
        decrypted = decrypt_value(encrypted)

        assert decrypted == large_data

    def test_null_byte_in_input(self, encryption_settings):
        """Test encryption handles null bytes in input."""
        data_with_null = "before\x00after"

        encrypted = encrypt_value(data_with_null)
        decrypted = decrypt_value(encrypted)

        assert decrypted == data_with_null

    def test_key_rotation_scenario(self, settings, test_hmac_key):
        """Test that changing encryption key invalidates old ciphertext."""
        # Setup first key
        key1 = base64.b64encode(os.urandom(32)).decode("utf-8")
        settings.ENCRYPTION_KEY = key1
        settings.HMAC_KEY = test_hmac_key
        get_encryption_key.cache_clear()

        # Encrypt with first key
        plaintext = "sensitive data"
        encrypted_with_key1 = encrypt_value(plaintext)

        # Verify decryption works with same key
        assert decrypt_value(encrypted_with_key1) == plaintext

        # Change to new key
        key2 = base64.b64encode(os.urandom(32)).decode("utf-8")
        settings.ENCRYPTION_KEY = key2
        get_encryption_key.cache_clear()

        # Old ciphertext should fail with new key
        with pytest.raises(ValueError, match="Decryption failed"):
            decrypt_value(encrypted_with_key1)

    def test_blind_index_key_dependency(self, settings, test_encryption_key):
        """Test that blind index depends on HMAC key."""
        value = "test@example.com"

        # First key
        key1 = base64.b64encode(os.urandom(32)).decode("utf-8")
        settings.HMAC_KEY = key1
        settings.ENCRYPTION_KEY = test_encryption_key
        get_hmac_key.cache_clear()

        hash1 = compute_blind_index(value)

        # Different key
        key2 = base64.b64encode(os.urandom(32)).decode("utf-8")
        settings.HMAC_KEY = key2
        get_hmac_key.cache_clear()

        hash2 = compute_blind_index(value)

        # Different keys should produce different hashes
        assert hash1 != hash2
