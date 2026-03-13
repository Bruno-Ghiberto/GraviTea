"""
PostgreSQL-backed test settings for Gravitea ERP project.

Inherits from base.py (NOT test.py) per R4 decision.
Uses real PostgreSQL on port 5433 (Docker test profile) with real migrations.
Paired with pytest --reuse-db for fast subsequent runs.

Usage:
    pytest                                    # Default (this file via pytest.ini)
    pytest --create-db                        # Force DB recreation after schema changes
    pytest -m unit --ds=gravitea.settings.test  # Fast SQLite path for unit tests
"""

import os
from datetime import timedelta

from .base import *  # noqa: F401, F403

# =============================================================================
# DATABASE — PostgreSQL test container on port 5433
# =============================================================================
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_TEST_DB", "gravitea_test"),
        "USER": os.environ.get("POSTGRES_TEST_USER", "gravitea_test"),
        "PASSWORD": os.environ.get("POSTGRES_TEST_PASSWORD", "gravitea_test"),
        "HOST": os.environ.get("POSTGRES_TEST_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_TEST_PORT", "5433"),
        "OPTIONS": {
            "connect_timeout": 5,
        },
    }
}

# No DisableMigrations — real migrations run with --reuse-db

# =============================================================================
# SPEED OPTIMIZATIONS
# =============================================================================

# Faster password hashing for tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# HS256 JWT for test speed (no RSA key generation needed)
# SECURITY NOTE: HS256 is only acceptable for testing.
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "TOKEN_OBTAIN_SERIALIZER": "apps.auth.jwt.CustomTokenObtainPairSerializer",
    "TOKEN_TYPE_CLAIM": "token_type",
    "JTI_CLAIM": "jti",
}

# LocMemCache for tests — avoids requiring Redis
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "gravitea-test-cache",
    }
}

# =============================================================================
# TEST ENVIRONMENT
# =============================================================================

DEBUG = False

# Test-specific encryption keys (not for production)
# Must be valid base64 that decodes to exactly 32 bytes
ENCRYPTION_KEY = "dGVzdGVuY3J5cHRpb25rZXkzMmJ5dGVzMTIzNDU2Nzg="  # 32 bytes
HMAC_KEY = "dGVzdGhtYWNrZXkzMmJ5dGVzbG9uZzEyMzQ1Njc4OTA="  # 32 bytes

# Simplify logging for tests
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {
        "null": {
            "class": "logging.NullHandler",
        },
    },
    "root": {
        "handlers": ["null"],
    },
}
