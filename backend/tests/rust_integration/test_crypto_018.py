"""
SPEC-018: Crypto Acceleration Layer — Integration Tests.

Tests for AES-256-GCM encryption and HMAC-SHA256 blind indexing
via the Rust extension (gravitea_rust).

Covers: T015–T024, T029–T032, T039.
"""

import base64
import builtins
import hashlib
import hmac as hmac_mod
import importlib
import logging
import os
import re
import sys
import unicodedata

import pytest

# Direct Rust function imports
from gravitea_rust import (
    encrypt_value as _rust_encrypt_value,
    decrypt_value as _rust_decrypt_value,
    compute_blind_index as _rust_compute_blind_index,
)

# Python reference implementation (no Django needed)
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Django-dependent imports (conftest.py configures Django settings)
import apps.core.encryption.utils as utils_module

# ---------------------------------------------------------------------------
# Deterministic test keys (match conftest.py Django settings)
# ---------------------------------------------------------------------------
TEST_KEY = hashlib.sha256(b"gravitea-test-encryption-key-018").digest()
TEST_HMAC_KEY = hashlib.sha256(b"gravitea-test-hmac-key-018").digest()


# ---------------------------------------------------------------------------
# Helper functions: standalone Python reference implementations
# ---------------------------------------------------------------------------

def python_encrypt(value: str, key: bytes) -> str:
    """Reference Python AES-256-GCM encrypt (standalone, no Django)."""
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, value.encode("utf-8"), None)
    return base64.b64encode(nonce + ciphertext).decode("utf-8")


def python_decrypt(encrypted: str, key: bytes) -> str:
    """Reference Python AES-256-GCM decrypt (standalone, no Django)."""
    aesgcm = AESGCM(key)
    data = base64.b64decode(encrypted)
    nonce = data[:12]
    ciphertext = data[12:]
    return aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")


def python_blind_index(value: str, hmac_key: bytes) -> str:
    """Reference Python blind index: NFC -> lower -> trim -> HMAC-SHA256 -> hex.

    Matches the Rust algorithm exactly (including NFC normalization).
    """
    normalized = unicodedata.normalize("NFC", value).lower().strip()
    h = hmac_mod.new(hmac_key, normalized.encode("utf-8"), hashlib.sha256)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Argentine PII test corpus (20 values for T016/T017)
# ---------------------------------------------------------------------------
ARGENTINE_PII_CORPUS = [
    # CUITs (10)
    "20345678901",
    "27123456789",
    "30712345671",
    "23345678909",
    "24123456782",
    "33456789012",
    "34567890123",
    "20999888777",
    "27111222333",
    "30555666777",
    # Spanish names with accents (10) — NFC form
    "María García",
    "José Núñez",
    "Andrés Peña",
    "Lucía Martínez",
    "Héctor Muñoz",
    "Raúl López",
    "Sofía Álvarez",
    "Darío Gutiérrez",
    "Ñoño Peñaloza",
    "Agüero Ramírez",
]


# =============================================================================
# Phase 3 Python: T015 — Benchmark Tests
# =============================================================================

@pytest.mark.slow
def test_encrypt_benchmark(benchmark):
    """T015: Benchmark Rust encrypt_value (1000 iterations, 50-char plaintext)."""
    plaintext = "A" * 50
    benchmark.pedantic(
        lambda: _rust_encrypt_value(plaintext, TEST_KEY),
        iterations=1000,
        rounds=3,
    )


@pytest.mark.slow
def test_decrypt_benchmark(benchmark):
    """T015: Benchmark Rust decrypt_value (1000 iterations, 50-char plaintext)."""
    plaintext = "A" * 50
    encrypted = _rust_encrypt_value(plaintext, TEST_KEY)
    benchmark.pedantic(
        lambda: _rust_decrypt_value(encrypted, TEST_KEY),
        iterations=1000,
        rounds=3,
    )


@pytest.mark.slow
def test_encrypt_benchmark_python(benchmark):
    """T015/T037: Benchmark Python encrypt_value for speedup comparison."""
    plaintext = "A" * 50
    benchmark.pedantic(
        lambda: python_encrypt(plaintext, TEST_KEY),
        iterations=1000,
        rounds=3,
    )


@pytest.mark.slow
def test_decrypt_benchmark_python(benchmark):
    """T015/T037: Benchmark Python decrypt_value for speedup comparison."""
    plaintext = "A" * 50
    encrypted = python_encrypt(plaintext, TEST_KEY)
    benchmark.pedantic(
        lambda: python_decrypt(encrypted, TEST_KEY),
        iterations=1000,
        rounds=3,
    )


# =============================================================================
# Phase 4: T016–T019 — Cross-Compatibility Tests
# =============================================================================

def test_python_encrypted_rust_decrypted():
    """T016: 20-string corpus — Python encrypts, Rust decrypts, all 20 match."""
    for value in ARGENTINE_PII_CORPUS:
        encrypted = python_encrypt(value, TEST_KEY)
        decrypted = _rust_decrypt_value(encrypted, TEST_KEY)
        assert decrypted == value, f"Failed for: {value!r}"


def test_rust_encrypted_python_decrypted():
    """T017: 20-string corpus — Rust encrypts, Python decrypts, all 20 match."""
    for value in ARGENTINE_PII_CORPUS:
        encrypted = _rust_encrypt_value(value, TEST_KEY)
        decrypted = python_decrypt(encrypted, TEST_KEY)
        assert decrypted == value, f"Failed for: {value!r}"


def test_wire_format_test_vector():
    """T018: Known-good AESGCM blob — Rust decrypts to 'gravitea'; standard base64."""
    key = bytes(32)
    nonce = bytes(12)
    aead = AESGCM(key)
    ct = aead.encrypt(nonce, b"gravitea", None)
    blob_b64 = base64.b64encode(nonce + ct).decode("utf-8")

    # Rust must decrypt the Python-produced blob correctly
    result = _rust_decrypt_value(blob_b64, key)
    assert result == "gravitea"

    # Standard alphabet: only [A-Za-z0-9+/=] — NO hyphen or underscore
    assert re.fullmatch(r"[A-Za-z0-9+/=]+", blob_b64), (
        f"URL-safe alphabet detected in blob: {blob_b64}"
    )


def test_1000_sequential_roundtrips():
    """T019: 1000 Rust encrypt->decrypt cycles of '20123456789' all match."""
    value = "20123456789"
    for i in range(1000):
        encrypted = _rust_encrypt_value(value, TEST_KEY)
        decrypted = _rust_decrypt_value(encrypted, TEST_KEY)
        assert decrypted == value, f"Failed at iteration {i}"


# =============================================================================
# Phase 5: T023 — Fallback All Operations
# =============================================================================

def test_fallback_all_operations(monkeypatch):
    """T023: _USE_RUST=False — all 3 functions return correct results."""
    monkeypatch.setattr(utils_module, "_USE_RUST", False)

    # encrypt -> decrypt roundtrip via Python fallback
    plaintext = "María García"
    encrypted = utils_module.encrypt_value(plaintext)
    decrypted = utils_module.decrypt_value(encrypted)
    assert decrypted == plaintext

    # Rust can decrypt what the Python fallback produced (wire compat)
    key = utils_module.get_encryption_key()
    rust_decrypted = _rust_decrypt_value(encrypted, key)
    assert rust_decrypted == plaintext

    # Blind index consistency (use NFC-safe values — Python fallback lacks NFC)
    hmac_key = utils_module.get_hmac_key()
    py_idx = utils_module.compute_blind_index("smith")
    rust_idx = _rust_compute_blind_index("smith", hmac_key)
    assert py_idx == rust_idx


# =============================================================================
# Phase 5: T024 — FR-010 Startup Warning Tests
# =============================================================================

def test_fr010_startup_warning(caplog):
    """T024a: Exactly 1 WARNING with 'software fallback' when gravitea_rust absent."""
    original_import = builtins.__import__

    def importerror_import(name, *args, **kwargs):
        if name == "gravitea_rust":
            raise ImportError("Simulated: no Rust extension")
        return original_import(name, *args, **kwargs)

    saved = sys.modules.pop("gravitea_rust", None)
    saved_sub = sys.modules.pop("gravitea_rust.gravitea_rust", None)
    try:
        builtins.__import__ = importerror_import
        with caplog.at_level(
            logging.WARNING, logger="apps.core.encryption.utils"
        ):
            importlib.reload(utils_module)
        records = [
            r for r in caplog.records if "software fallback" in r.message
        ]
        assert len(records) == 1, (
            f"Expected 1 warning, got {len(records)}: "
            f"{[r.message for r in caplog.records]}"
        )
    finally:
        builtins.__import__ = original_import
        if saved is not None:
            sys.modules["gravitea_rust"] = saved
        if saved_sub is not None:
            sys.modules["gravitea_rust.gravitea_rust"] = saved_sub
        importlib.reload(utils_module)


def test_fr010_no_warning_when_rust_loads(caplog):
    """T024b: Zero WARNINGs when gravitea_rust is importable."""
    with caplog.at_level(
        logging.WARNING, logger="apps.core.encryption.utils"
    ):
        importlib.reload(utils_module)
    fallback_records = [
        r for r in caplog.records if "software fallback" in r.message
    ]
    assert len(fallback_records) == 0, (
        f"Unexpected warnings: {[r.message for r in fallback_records]}"
    )


def test_fr010_oserror_triggers_fallback(caplog):
    """T024c: OSError during import triggers fallback warning (EC-6 corrupted binary)."""
    original_import = builtins.__import__

    def oserror_import(name, *args, **kwargs):
        if name == "gravitea_rust":
            raise OSError("Simulated corrupted binary")
        return original_import(name, *args, **kwargs)

    saved = sys.modules.pop("gravitea_rust", None)
    try:
        builtins.__import__ = oserror_import
        with caplog.at_level(
            logging.WARNING, logger="apps.core.encryption.utils"
        ):
            importlib.reload(utils_module)
        records = [
            r for r in caplog.records if "software fallback" in r.message
        ]
        assert len(records) == 1, (
            f"Expected 1 OSError warning, got {len(records)}"
        )
    finally:
        builtins.__import__ = original_import
        if saved is not None:
            sys.modules["gravitea_rust"] = saved
        importlib.reload(utils_module)


# =============================================================================
# Phase 5: T039 — Null/Empty Passthrough (FR-005)
# =============================================================================

@pytest.mark.parametrize("use_rust", [True, False], ids=["rust", "python"])
def test_null_empty_passthrough(monkeypatch, use_rust):
    """T039: None/empty guards in Python wrapper for all 3 functions (FR-005)."""
    monkeypatch.setattr(utils_module, "_USE_RUST", use_rust)

    # encrypt_value
    assert utils_module.encrypt_value(None) is None
    assert utils_module.encrypt_value("") == ""

    # decrypt_value
    assert utils_module.decrypt_value(None) is None
    assert utils_module.decrypt_value("") == ""

    # compute_blind_index
    assert utils_module.compute_blind_index(None) is None
    assert utils_module.compute_blind_index("") == ""


# =============================================================================
# Phase 6: T029 — Blind Index Parity (50 values)
# =============================================================================

def test_blind_index_parity_50_values():
    """T029: 50-value corpus — Rust and Python produce identical blind index hex."""
    corpus_cuit = [
        "20345678901", "27123456789", "30712345671",
        "23345678909", "24123456782", "33456789012",
        "34567890123", "20999888777", "27111222333",
        "30555666777",
    ]
    corpus_accented = [
        "María García", "José Núñez", "Andrés Peña",
        "Lucía Martínez", "Héctor Muñoz", "Raúl López",
        "Sofía Álvarez", "Darío Gutiérrez", "Ñoño Peñaloza",
        "Agüero Ramírez",
    ]
    corpus_mixed_case = [
        "MARÍA GARCÍA", "josé núñez", "AnDrÉs PeÑa",
        "LUCÍA MARTÍNEZ", "hÉcToR mUñOz", "RAÚL LÓPEZ",
        "sofía álvarez", "DARÍO GUTIÉRREZ", "ÑOÑO PEÑALOZA",
        "agüero ramírez",
    ]
    corpus_padded = [
        "  María García  ", " José Núñez ", "  Andrés Peña",
        "Lucía Martínez  ", " Héctor Muñoz ", "  Raúl López  ",
        " Sofía Álvarez", "Darío Gutiérrez  ", " Ñoño Peñaloza ",
        "  Agüero Ramírez  ",
    ]
    corpus_nfd = [
        unicodedata.normalize("NFD", name) for name in corpus_accented
    ]

    full_corpus = (
        corpus_cuit + corpus_accented + corpus_mixed_case
        + corpus_padded + corpus_nfd
    )
    assert len(full_corpus) == 50

    for value in full_corpus:
        rust_idx = _rust_compute_blind_index(value, TEST_HMAC_KEY)
        py_idx = python_blind_index(value, TEST_HMAC_KEY)
        assert rust_idx == py_idx, (
            f"Parity mismatch for {value!r}: "
            f"rust={rust_idx[:16]}... py={py_idx[:16]}..."
        )


# =============================================================================
# Phase 6: T030 — NFC Equivalence
# =============================================================================

NFC_TEST_STRINGS = [
    "ñ", "á", "é", "ü", "Ñoño", "García", "Martínez",
    "Núñez", "López", "Agüero",
]


def test_blind_index_nfc_equivalence():
    """T030: NFC and NFD forms produce identical blind index via Rust and Python."""
    for nfc_str in NFC_TEST_STRINGS:
        nfd_str = unicodedata.normalize("NFD", nfc_str)
        rust_nfc = _rust_compute_blind_index(nfc_str, TEST_HMAC_KEY)
        rust_nfd = _rust_compute_blind_index(nfd_str, TEST_HMAC_KEY)
        py_ref = python_blind_index(nfc_str, TEST_HMAC_KEY)

        assert rust_nfc == rust_nfd, (
            f"Rust NFC/NFD mismatch for {nfc_str!r}: "
            f"nfc={rust_nfc[:16]}... nfd={rust_nfd[:16]}..."
        )
        assert rust_nfc == py_ref, (
            f"Rust/Python mismatch for {nfc_str!r}: "
            f"rust={rust_nfc[:16]}... py={py_ref[:16]}..."
        )


# =============================================================================
# Phase 6: T031 — Hypothesis Property-Based Tests
# =============================================================================

from hypothesis import given, settings as hyp_settings
from hypothesis import strategies as st

CUIT_STRATEGY = st.from_regex(
    r"(20|23|24|27|30|33|34)[0-9]{8}[0-9]", fullmatch=True
)
SPANISH_NAME_STRATEGY = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyzáéíóúüñÁÉÍÓÚÜÑ ",
    min_size=2,
    max_size=40,
)
PADDED_NAME_STRATEGY = SPANISH_NAME_STRATEGY.map(lambda s: f"  {s}  ")
NFD_NAME_STRATEGY = SPANISH_NAME_STRATEGY.map(
    lambda s: unicodedata.normalize("NFD", s)
)
MIXED_CASE_STRATEGY = SPANISH_NAME_STRATEGY.map(str.upper)
EDGE_CHAR_STRATEGY = st.sampled_from(["a", "ñ", "á"])


@given(
    value=st.one_of(
        CUIT_STRATEGY,
        SPANISH_NAME_STRATEGY,
        PADDED_NAME_STRATEGY,
        NFD_NAME_STRATEGY,
        MIXED_CASE_STRATEGY,
        EDGE_CHAR_STRATEGY,
    )
)
@hyp_settings(max_examples=500)
def test_hypothesis_blind_index_parity(value):
    """T031: Hypothesis — Rust and Python blind index parity for Argentine PII."""
    rust_result = _rust_compute_blind_index(value, TEST_HMAC_KEY)
    py_result = python_blind_index(value, TEST_HMAC_KEY)
    assert rust_result == py_result, (
        f"Parity failed for {value!r}: "
        f"rust={rust_result[:16]}... py={py_result[:16]}..."
    )
