"""
Production settings for Gravitea ERP project.

Cloud Run deployment with Cloud SQL and Secret Manager.
"""

import os

from .base import *  # noqa: F401, F403

# SECURITY WARNING: set these in production!
DEBUG = False

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "").split(",")


# Database - Cloud SQL connection
# Two connection modes supported:
# 1. DATABASE_URL: Standard TCP connection (VPC Egress / Private IP)
# 2. Unix Socket: Cloud SQL Auth Proxy sidecar (recommended for Cloud Run)
DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL:
    import urllib.parse

    url = urllib.parse.urlparse(DATABASE_URL)
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": url.path[1:],
            "USER": url.username,
            "PASSWORD": url.password,
            "HOST": url.hostname,
            "PORT": url.port or 5432,
            # Cloud Run optimization: Close connections aggressively
            "CONN_MAX_AGE": int(os.environ.get("DB_CONN_MAX_AGE", "0")),
            "CONN_HEALTH_CHECKS": True,
            "OPTIONS": {
                "connect_timeout": 10,
                "options": f"-c statement_timeout={os.environ.get('DB_STATEMENT_TIMEOUT', '30000')}",
            },
        }
    }
else:
    # Cloud Run with Unix socket
    # Connection pooling optimized for Cloud Run's ephemeral containers
    # See: https://cloud.google.com/sql/docs/postgres/connect-run
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("DB_NAME"),
            "USER": os.environ.get("DB_USER"),
            "PASSWORD": os.environ.get("DB_PASSWORD"),
            "HOST": f"/cloudsql/{os.environ.get('CLOUD_SQL_CONNECTION_NAME', '')}",
            "PORT": "5432",
            # Cloud Run optimization: Close connections aggressively
            # Prevents "Thundering Herd" when scaling 0→N instances
            "CONN_MAX_AGE": int(os.environ.get("DB_CONN_MAX_AGE", "0")),
            "CONN_HEALTH_CHECKS": True,  # Validate connections before use
            "OPTIONS": {
                "connect_timeout": 10,
                # Pool size per container (Cloud Run recommendation: 2-5)
                "options": f"-c statement_timeout={os.environ.get('DB_STATEMENT_TIMEOUT', '30000')}",
            },
        }
    }


# Redis - Memorystore
REDIS_URL = os.environ.get("REDIS_URL", "")

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}


# Security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Cloud Run handles SSL termination
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = False  # Cloud Run handles this


# Static files - use Cloud Storage in production
STATIC_URL = os.environ.get("STATIC_URL", "/static/")
STATIC_ROOT = BASE_DIR / "staticfiles"  # noqa: F405


# Logging - structured for Cloud Logging with trace correlation
# Per spec.md FR-007, FR-008 requirements
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "trace_correlation": {
            "()": "apps.core.logging.filters.TraceCorrelationFilter",
        },
    },
    "formatters": {
        "json": {
            "format": '{"time": "%(asctime)s", "level": "%(levelname)s", "trace_id": "%(trace_id)s", "tenant_id": "%(tenant_id)s", "branch_id": "%(branch_id)s", "user_id": "%(user_id)s", "request_method": "%(request_method)s", "request_path": "%(request_path)s", "module": "%(module)s", "message": "%(message)s"}',
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "filters": ["trace_correlation"],
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "security": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "fiscal": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "sync": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}


# Load encryption keys from Secret Manager in production
# These are loaded at app startup via apps.core.secrets


# =============================================================================
# PRODUCTION CELERY CONFIGURATION
# =============================================================================
# Override broker/result backend for production (Memorystore Redis)
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", REDIS_URL.replace("/0", "/1") if REDIS_URL else "redis://localhost:6379/1")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", REDIS_URL.replace("/0", "/2") if REDIS_URL else "redis://localhost:6379/2")

# Production task settings
CELERY_TASK_ALWAYS_EAGER = False  # Never run tasks synchronously in production
CELERY_WORKER_PREFETCH_MULTIPLIER = 4  # Optimize for Cloud Run
CELERY_WORKER_CONCURRENCY = int(os.environ.get("CELERY_WORKER_CONCURRENCY", "4"))

# Task rate limiting for production stability
CELERY_TASK_DEFAULT_RATE_LIMIT = "100/m"  # 100 tasks per minute default

# Production retry policy
CELERY_TASK_ACKS_LATE = True  # Acknowledge after task completes
CELERY_TASK_REJECT_ON_WORKER_LOST = True  # Requeue if worker dies

# Beat scheduler for periodic tasks
CELERY_BEAT_SCHEDULER = "celery.beat:PersistentScheduler"
