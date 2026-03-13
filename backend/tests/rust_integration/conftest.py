"""Conftest for rust_integration tests (SPEC-018 crypto + SPEC-019 fiscal compute).

Sets up minimal Django configuration and sys.path for importing apps.core
and apps.facturacion modules without the full Django test infrastructure.
"""

import base64
import hashlib
import sys
from pathlib import Path

import pytest

# Add backend/ to sys.path for "apps.*" imports
_backend_dir = str(Path(__file__).resolve().parents[2])
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from django.conf import settings  # noqa: E402

# Deterministic test keys — same values computed in test_crypto_018.py
_TEST_KEY = hashlib.sha256(b"gravitea-test-encryption-key-018").digest()
_TEST_HMAC_KEY = hashlib.sha256(b"gravitea-test-hmac-key-018").digest()

if not settings.configured:
    settings.configure(
        ENCRYPTION_KEY=base64.b64encode(_TEST_KEY).decode(),
        HMAC_KEY=base64.b64encode(_TEST_HMAC_KEY).decode(),
        SECRET_KEY="test-only-for-crypto-018",
        # Minimal settings so apps.facturacion.validators can be imported
        # (it does not import models at module level, only django.core.exceptions
        # and .constants — both safe with this minimal config).
        INSTALLED_APPS=[],
        USE_TZ=True,
    )


@pytest.fixture(autouse=True)
def set_rls_tenant_context():
    """Override parent conftest fixture — Rust integration tests need no database."""
    yield
