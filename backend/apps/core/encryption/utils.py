"""
Encryption utilities for PII protection.

Implements AES-256-GCM encryption and HMAC-SHA256 blind indexing
per research.md specifications for Ley 25.326 compliance.
"""

import base64
import functools
import hashlib
import hmac
import logging
import os
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings

logger = logging.getLogger("security")

# ---------------------------------------------------------------------------
# Rust acceleration dispatch (T014, T022, T028)
# ---------------------------------------------------------------------------
try:
    from gravitea_rust import (
        encrypt_value as _rust_encrypt_value,
        decrypt_value as _rust_decrypt_value,
        compute_blind_index as _rust_compute_blind_index,
    )

    _USE_RUST = True
except (ImportError, OSError):
    _USE_RUST = False
    logging.getLogger(__name__).warning(
        "gravitea_rust not available — using software fallback"
        " for PII encryption and blind indexing"
    )


@functools.lru_cache(maxsize=1)
def get_encryption_key() -> bytes:
    """
    Get the AES-256 encryption key for PII fields.

    Returns 32-byte key decoded from base64 ENCRYPTION_KEY setting.

    Raises:
        ValueError: If ENCRYPTION_KEY is not set or invalid.
    """
    key_b64 = getattr(settings, "ENCRYPTION_KEY", "")
    if not key_b64:
        raise ValueError(
            "ENCRYPTION_KEY not set. Generate with: "
            'python -c "import secrets; import base64; '
            'print(base64.b64encode(secrets.token_bytes(32)).decode())"'
        )
    try:
        key = base64.b64decode(key_b64)
        if len(key) != 32:
            raise ValueError("ENCRYPTION_KEY must decode to exactly 32 bytes")
        return key
    except Exception as e:
        raise ValueError(f"Invalid ENCRYPTION_KEY: {e}")


@functools.lru_cache(maxsize=1)
def get_hmac_key() -> bytes:
    """
    Get the HMAC key for blind indexing.

    Returns 32-byte key decoded from base64 HMAC_KEY setting.

    Raises:
        ValueError: If HMAC_KEY is not set or invalid.
    """
    key_b64 = getattr(settings, "HMAC_KEY", "")
    if not key_b64:
        raise ValueError(
            "HMAC_KEY not set. Generate with: "
            'python -c "import secrets; import base64; '
            'print(base64.b64encode(secrets.token_bytes(32)).decode())"'
        )
    try:
        key = base64.b64decode(key_b64)
        if len(key) != 32:
            raise ValueError("HMAC_KEY must decode to exactly 32 bytes")
        return key
    except Exception as e:
        raise ValueError(f"Invalid HMAC_KEY: {e}")


def encrypt_value(value: str) -> str:
    """
    Encrypt a string value using AES-256-GCM.

    Args:
        value: Plain text to encrypt.

    Returns:
        Base64-encoded string containing nonce + ciphertext + tag.

    Format: base64(nonce[12] || ciphertext || tag[16])
    """
    if value is None:
        return None
    if value == "":
        return ""

    if _USE_RUST:
        return _rust_encrypt_value(value, get_encryption_key())

    key = get_encryption_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)  # 96-bit nonce for GCM

    ciphertext = aesgcm.encrypt(nonce, value.encode("utf-8"), None)

    # Combine nonce + ciphertext (tag is appended by AESGCM)
    encrypted = nonce + ciphertext

    return base64.b64encode(encrypted).decode("utf-8")


def decrypt_value(encrypted: str) -> str:
    """
    Decrypt a value encrypted with AES-256-GCM.

    Args:
        encrypted: Base64-encoded encrypted value.

    Returns:
        Decrypted plain text.

    Raises:
        ValueError: If decryption fails (invalid key, tampered data).
    """
    if encrypted is None:
        return None
    if encrypted == "":
        return ""

    if _USE_RUST:
        try:
            return _rust_decrypt_value(encrypted, get_encryption_key())
        except RuntimeError as e:
            logger.warning(f"Decryption failed: {e}")
            raise ValueError(f"Decryption failed: {e}") from e

    key = get_encryption_key()
    aesgcm = AESGCM(key)

    try:
        data = base64.b64decode(encrypted)
        nonce = data[:12]
        ciphertext = data[12:]

        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode("utf-8")
    except Exception as e:
        logger.warning(f"Decryption failed: {e}")
        raise ValueError(f"Decryption failed: {e}")


def compute_blind_index(value: str) -> Optional[str]:
    """
    Compute HMAC-SHA256 blind index for searchable encrypted fields.

    Normalizes input (lowercase, strip whitespace) before hashing
    to ensure consistent lookups.

    Args:
        value: Plain text value to hash.

    Returns:
        64-character hex string (SHA256 output) or None if value is None.
    """
    if value is None:
        return None
    if not value or value.strip() == "":
        return ""

    if _USE_RUST:
        return _rust_compute_blind_index(value, get_hmac_key())

    key = get_hmac_key()

    # Normalize: lowercase, strip whitespace
    normalized = value.lower().strip()

    # Compute HMAC-SHA256
    h = hmac.new(key, normalized.encode("utf-8"), hashlib.sha256)

    return h.hexdigest()
