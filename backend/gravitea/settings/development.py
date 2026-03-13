"""
Development settings for Gravitea ERP project.

DEBUG mode enabled with local database configuration.
"""

import os
from datetime import timedelta

from .base import *  # noqa: F401, F403

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = os.environ.get(
    "ALLOWED_HOSTS", "localhost,127.0.0.1,0.0.0.0"
).split(",")


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "gravitea_dev"),
        "USER": os.environ.get("POSTGRES_USER", "gravitea"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "gravitea"),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

# Alternative: Use DATABASE_URL if set
DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL:
    import urllib.parse

    url = urllib.parse.urlparse(DATABASE_URL)
    DATABASES["default"] = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": url.path[1:],  # Remove leading slash
        "USER": url.username,
        "PASSWORD": url.password,
        "HOST": url.hostname,
        "PORT": url.port or 5432,
    }


# Cache configuration (Redis)
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique-snowflake",
    }
}


# Development-specific apps (optional — not available in Docker prod image)
try:
    import django_extensions  # noqa: F401

    INSTALLED_APPS += ["django_extensions"]  # noqa: F405
except ImportError:
    pass


# Enable SQL query logging for debugging (set SQL_DEBUG=true in env to activate)
if os.environ.get("SQL_DEBUG", "").lower() == "true":
    LOGGING["loggers"]["django.db.backends"] = {  # noqa: F405
        "level": "DEBUG",
        "handlers": ["console"],
        "propagate": False,
    }


# CORS settings for local frontend development
CORS_ALLOW_ALL_ORIGINS = True


# Email backend for development
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"


# JWT: Use HS256 in development (no RSA key generation needed).
# Production MUST use RS256 with 4096-bit RSA keys.
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,  # noqa: F405
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "TOKEN_OBTAIN_SERIALIZER": "apps.auth.jwt.CustomTokenObtainPairSerializer",
    "TOKEN_TYPE_CLAIM": "token_type",
    "JTI_CLAIM": "jti",
}
