"""
Base Django settings for Gravitea ERP project.

Common settings shared across all environments.
"""

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured("The SECRET_KEY environment variable must be set")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get("DEBUG", "False").lower() == "true"

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party apps
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "django_filters",
    "drf_spectacular",
    "corsheaders",
    # Local apps
    "apps.core",
    "apps.core.observability",  # Observability: metrics, tracing, logging
    "apps.auth",
    "apps.inventario",
    "apps.sync",
    "apps.facturacion",
    "apps.ventas",
    "apps.compras",
    "apps.reportes",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "apps.core.middleware.trace_middleware.TraceMiddleware",  # Trace ID for request correlation
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Custom middleware
    "apps.core.middleware.tenant_context.TenantContextMiddleware",
]

# CORS Configuration
# In production, set CORS_ALLOWED_ORIGINS via environment variable
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
    if origin.strip()
]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
    "x-trace-id",
]

ROOT_URLCONF = "gravitea.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "gravitea.wsgi.application"


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators
#
# Security hardening (P2): Enforce strong password complexity:
# - Minimum 12 characters
# - At least 1 uppercase letter (A-Z)
# - At least 1 lowercase letter (a-z)
# - At least 1 digit (0-9)
# - At least 1 special character

AUTH_PASSWORD_VALIDATORS = [
    # Prevent passwords too similar to user attributes
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    # Enforce minimum length of 12 characters (P2 security requirement)
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 12,
        },
    },
    # Prevent commonly used passwords
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    # Prevent entirely numeric passwords
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
    # Custom complexity validator: uppercase, lowercase, digit, special char
    {
        "NAME": "apps.core.validators.PasswordComplexityValidator",
        "OPTIONS": {
            "min_length": 12,
            "require_uppercase": True,
            "require_lowercase": True,
            "require_digit": True,
            "require_special": True,
        },
    },
]

# Password Hashers - Argon2 as primary per research.md
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",  # Fallback for migration
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = "es-ar"

TIME_ZONE = "America/Argentina/Buenos_Aires"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"


# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Custom User Model (using custom label to avoid conflict with django.contrib.auth)
AUTH_USER_MODEL = "gravitea_auth.AppUser"

# Silence auth.E003: USERNAME_FIELD must be unique.
# Our AppUser.email uses a per-tenant UniqueConstraint instead of unique=True
# because the same email can exist across different tenants (multi-tenancy).
SILENCED_SYSTEM_CHECKS = ["auth.E003"]


# Django REST Framework Configuration
REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.core.authentication.TenantAwareJWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.StandardCursorPagination",
    "PAGE_SIZE": 100,
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
    ],
    "EXCEPTION_HANDLER": "apps.core.exceptions.handlers.problem_detail_exception_handler",
    "COERCE_DECIMAL_TO_STRING": True,  # Preserve DECIMAL precision in JSON
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/hour",
        "user": "1000/hour",
    },
}


# =============================================================================
# JWT CONFIGURATION (RS256 Asymmetric)
# =============================================================================
# Per gravitea-auth skill: RS256 with 4096-bit keys, algorithm whitelist enforced.
# CRITICAL: HS256/HS384/HS512 are FORBIDDEN for API authentication.
#
# Key Generation:
#   openssl genrsa -out jwt_private.pem 4096
#   openssl rsa -in jwt_private.pem -pubout -out jwt_public.pem
#
# Environment Variables:
#   JWT_PRIVATE_KEY: Full PEM-encoded private key (with newlines as \n)
#   JWT_PUBLIC_KEY: Full PEM-encoded public key (with newlines as \n)

# Load RSA keys from environment (replace literal \n with newlines)
_JWT_PRIVATE_KEY_RAW = os.environ.get("JWT_PRIVATE_KEY", "")
_JWT_PUBLIC_KEY_RAW = os.environ.get("JWT_PUBLIC_KEY", "")

JWT_PRIVATE_KEY = _JWT_PRIVATE_KEY_RAW.replace("\\n", "\n") if _JWT_PRIVATE_KEY_RAW else ""
JWT_PUBLIC_KEY = _JWT_PUBLIC_KEY_RAW.replace("\\n", "\n") if _JWT_PUBLIC_KEY_RAW else ""

# JWT Issuer and Audience for claim validation
JWT_ISSUER = os.environ.get("JWT_ISSUER", "https://auth.gravitea.io")
JWT_AUDIENCE = os.environ.get("JWT_AUDIENCE", "gravitea-api")

# SimpleJWT Configuration per gravitea-auth skill patterns
SIMPLE_JWT = {
    # Token lifetimes
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=int(os.environ.get("JWT_ACCESS_TOKEN_LIFETIME_MINUTES", 15))
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=int(os.environ.get("JWT_REFRESH_TOKEN_LIFETIME_DAYS", 7))
    ),
    # Token rotation and blacklisting
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    # CRITICAL: RS256 algorithm with explicit key configuration
    # Algorithm whitelist: RS256, ES256, PS256 only (HS* forbidden)
    "ALGORITHM": "RS256",
    "SIGNING_KEY": JWT_PRIVATE_KEY,
    "VERIFYING_KEY": JWT_PUBLIC_KEY,
    # Header configuration
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    # User identification
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    # Custom serializer for tenant-aware claims
    "TOKEN_OBTAIN_SERIALIZER": "apps.auth.jwt.CustomTokenObtainPairSerializer",
    # Token type claim
    "TOKEN_TYPE_CLAIM": "token_type",
    # JTI claim for blacklisting
    "JTI_CLAIM": "jti",
}


# Open API / Swagger Documentation
SPECTACULAR_SETTINGS = {
    # API Info
    "TITLE": "Gravitea ERP API",
    "DESCRIPTION": "Multi-tenant ERP API for inventory, sales, and supplier management.",
    "VERSION": "1.0.0",
    "CONTACT": {
        "name": "Gravitea Development Team",
        "email": "dev@gravitea.com",
    },
    "LICENSE": {
        "name": "Proprietary",
    },
    "EXTERNAL_DOCS": {
        "description": "Full API Documentation",
        "url": "https://docs.gravitea.com",
    },
    # Schema Configuration
    "SCHEMA_PATH_PREFIX": "/api/v1",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,  # Enable modular request body splitting
    # OpenAPI 3.1 Support
    "OAS_VERSION": "3.1.0",
    # Server URLs (base URL only - paths already include /api/v1)
    "SERVERS": [
        {
            "url": "http://localhost:8000",
            "description": "Local Development Server",
        },
        {
            "url": "https://staging.gravitea.com",
            "description": "Staging Environment",
        },
        {
            "url": "https://api.gravitea.com",
            "description": "Production Environment",
        },
    ],
    # Security Configuration - JWT Bearer Authentication
    "SECURITY": [
        {
            "bearerAuth": [],
        }
    ],
    "APPEND_COMPONENTS": {
        "securitySchemes": {
            "bearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "JWT token obtained from /auth/token/ endpoint. Include tenant_id in token payload.",
            }
        }
    },
    # API Organization Tags
    "TAGS": [
        {
            "name": "Authentication",
            "description": "User authentication and token management",
        },
        {
            "name": "Inventory",
            "description": "Product and inventory management operations",
        },
        {
            "name": "Sync",
            "description": "Data synchronization with external systems",
        },
        {
            "name": "Health Checks",
            "description": "System health and readiness endpoints",
        },
        {
            "name": "ventas-customers",
            "description": "Customer management with fiscal identification",
        },
        {
            "name": "ventas-orders",
            "description": "Sale order lifecycle management (DRAFT → CONFIRMED → INVOICED)",
        },
        {
            "name": "ventas-order-items",
            "description": "Sale order line items with price snapshots",
        },
    ],
    # Postprocessing Hooks - RFC 7807 error response enrichment
    "POSTPROCESSING_HOOKS": [
        "apps.core.openapi.postprocess_schema",
    ],
    # Example Generation
    "EXAMPLES": True,
    "SCHEMA_COERCE_PATH_PK": True,
    # TypeScript Generation Support
    "CAMELIZE_NAMES": False,  # Keep snake_case for consistency
    "ENUM_NAME_OVERRIDES": {},
    # Response Format
    "SCHEMA_COERCE_METHOD_NAMES": {
        "retrieve": "get",
        "list": "list",
        "create": "create",
        "update": "update",
        "partial_update": "partial_update",
        "destroy": "delete",
    },
}


# Encryption settings for PII fields per research.md
ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY", "")
HMAC_KEY = os.environ.get("HMAC_KEY", "")


# Google Cloud settings (for Secret Manager in production)
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "gravitea-erp")


# Logging configuration with trace correlation
# Per spec.md FR-007, FR-008 requirements
# Per 004-observability-metrics for JSON logging format

# Determine log format from environment (json or text)
_LOG_FORMAT = os.environ.get("LOG_FORMAT", "text").lower()

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "trace_correlation": {
            "()": "apps.core.logging.filters.TraceCorrelationFilter",
        },
        "request_id": {
            "()": "apps.core.logging.filters.RequestIdFilter",
        },
        "sensitive_data": {
            "()": "apps.core.observability.logging.SensitiveDataFilter",
        },
    },
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} [{trace_id}] tenant={tenant_id} user={user_id} {module} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {asctime} [{trace_id}] {message}",
            "style": "{",
        },
        "detailed": {
            "format": "{levelname} {asctime} [{trace_id}] tenant={tenant_id} branch={branch_id} user={user_id} {request_method} {request_path} {module} {message}",
            "style": "{",
        },
        # JSON formatter for ELK/Loki ingestion (per 004-observability-metrics)
        "json": {
            "()": "apps.core.observability.logging.JSONLogFormatter",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json" if _LOG_FORMAT == "json" else "simple",
            "filters": ["trace_correlation", "sensitive_data"] if _LOG_FORMAT == "json" else ["trace_correlation"],
        },
        "detailed_console": {
            "class": "logging.StreamHandler",
            "formatter": "json" if _LOG_FORMAT == "json" else "detailed",
            "filters": ["trace_correlation", "sensitive_data"] if _LOG_FORMAT == "json" else ["trace_correlation"],
        },
        # JSON-only handler for structured logging
        "json_console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "filters": ["trace_correlation", "sensitive_data"],
        },
    },
    "root": {
        "handlers": ["console"],
        "level": os.environ.get("LOG_LEVEL", "INFO"),
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": os.environ.get("LOG_LEVEL", "INFO"),
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
        # Security logging per SC-022 - uses detailed format for audit
        "security": {
            "handlers": ["detailed_console"],
            "level": "WARNING",
            "propagate": False,
        },
        # Fiscal operations logging per SC-020 - uses detailed format for compliance
        "fiscal": {
            "handlers": ["detailed_console"],
            "level": "INFO",
            "propagate": False,
        },
        # Sync operations logging per SC-021
        "sync": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        # Observability module logging
        "observability": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}


# =============================================================================
# CELERY CONFIGURATION
# =============================================================================
# Redis broker URL for task queue
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/1")

# Redis result backend for task results
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")

# Celery task serialization
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"

# Task execution settings
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes max per task

# Task result expiration (24 hours)
CELERY_RESULT_EXPIRES = 60 * 60 * 24

# Timezone configuration
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True


# =============================================================================
# REDIS CACHE CONFIGURATION
# =============================================================================
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
        "KEY_PREFIX": "gravitea",
        "TIMEOUT": 300,  # 5 minutes default
        "OPTIONS": {
            "socket_connect_timeout": 5,
            "socket_timeout": 5,
        },
    }
}

# Cache key patterns for tenant isolation
CACHE_KEY_PATTERNS = {
    "tenant_config": "{prefix}:tenant:{tenant_id}:config",
    "product_cache": "{prefix}:tenant:{tenant_id}:product:{product_id}",
    "price_cache": "{prefix}:tenant:{tenant_id}:prices:{price_list_id}",
    "branch_config": "{prefix}:tenant:{tenant_id}:branch:{branch_id}",
}
