"""
Test settings for Gravitea ERP project.

Optimized for fast test execution with in-memory SQLite.
"""

from .base import *  # noqa: F401, F403

# Use in-memory SQLite for fast tests
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Faster password hashing for tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]


# Disable migrations for faster test setup
class DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None


MIGRATION_MODULES = DisableMigrations()

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

# Test-specific encryption keys (not for production)
# Must be valid base64 that decodes to exactly 32 bytes
ENCRYPTION_KEY = "dGVzdGVuY3J5cHRpb25rZXkzMmJ5dGVzMTIzNDU2Nzg="  # 32 bytes
HMAC_KEY = "dGVzdGhtYWNrZXkzMmJ5dGVzbG9uZzEyMzQ1Njc4OTA="  # 32 bytes

# =============================================================================
# TEST JWT CONFIGURATION
# =============================================================================
# Use HS256 for tests to avoid RSA key generation overhead.
# These settings override the RS256 production configuration.
#
# SECURITY NOTE: HS256 is only acceptable for testing.
# Production MUST use RS256 with 4096-bit keys.

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    # Use HS256 for tests (faster, no key generation needed)
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

# Use LocMemCache for tests - required for rate limiting tests to function
# DummyCache was causing rate limiting tests to fail (stores nothing)
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "gravitea-test-cache",
    }
}

# Speed up tests by disabling debug toolbar and other dev tools
DEBUG = False
