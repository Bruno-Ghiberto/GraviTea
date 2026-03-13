"""
Authentication app configuration with JWT key validation.

Per gravitea-auth skill: validates RSA key strength at startup to prevent
deployment with weak or missing keys.
"""

from __future__ import annotations

import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class AuthConfig(AppConfig):
    """Authentication app configuration with security validations."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.auth"
    label = "gravitea_auth"  # Avoid conflict with django.contrib.auth
    verbose_name = "Authentication"

    def ready(self) -> None:
        """Validate JWT configuration at application startup."""
        import sys

        # Skip validation for tests and management commands that don't need JWT
        # (e.g. collectstatic, migrate, makemigrations, check)
        if "pytest" in sys.modules or "test" in sys.argv:
            return

        skip_commands = {"collectstatic", "migrate", "makemigrations", "check", "showmigrations"}
        if set(sys.argv[1:2]) & skip_commands:
            return

        self._validate_jwt_keys()

    def _validate_jwt_keys(self) -> None:
        """
        Validate JWT RSA keys are present and meet security requirements.

        Per gravitea-auth skill:
        - RSA keys must be at least 2048 bits (4096 preferred)
        - Keys must be valid PEM format
        - Private key required for signing
        - Public key required for verification

        Raises:
            ImproperlyConfigured: If keys are missing, invalid, or too weak.
        """
        from django.conf import settings
        from django.core.exceptions import ImproperlyConfigured

        # Get JWT configuration
        jwt_config = getattr(settings, "SIMPLE_JWT", {})
        algorithm = jwt_config.get("ALGORITHM", "")

        # Only validate RSA keys if using RS256 algorithm
        if algorithm != "RS256":
            logger.warning(
                "JWT algorithm is not RS256 (%s). Skipping RSA key validation.",
                algorithm,
            )
            return

        private_key = jwt_config.get("SIGNING_KEY", "")
        public_key = jwt_config.get("VERIFYING_KEY", "")

        # Check if keys are present
        if not private_key:
            raise ImproperlyConfigured(
                "JWT_PRIVATE_KEY environment variable is required for RS256 algorithm. "
                "Generate with: openssl genrsa -out jwt_private.pem 4096"
            )

        if not public_key:
            raise ImproperlyConfigured(
                "JWT_PUBLIC_KEY environment variable is required for RS256 algorithm. "
                "Generate with: openssl rsa -in jwt_private.pem -pubout -out jwt_public.pem"
            )

        # Validate private key format and strength
        try:
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.primitives.asymmetric import rsa

            # Load and validate private key
            loaded_private_key = serialization.load_pem_private_key(
                private_key.encode("utf-8"),
                password=None,
            )

            # Verify it's an RSA key
            if not isinstance(loaded_private_key, rsa.RSAPrivateKey):
                raise ImproperlyConfigured(
                    "JWT_PRIVATE_KEY must be an RSA private key for RS256 algorithm."
                )

            # Check key size (minimum 2048 bits, 4096 recommended)
            key_size = loaded_private_key.key_size
            if key_size < 2048:
                raise ImproperlyConfigured(
                    f"JWT_PRIVATE_KEY is only {key_size} bits. "
                    f"RSA keys must be at least 2048 bits (4096 recommended)."
                )

            if key_size < 4096:
                logger.warning(
                    "JWT RSA key is %d bits. 4096 bits is recommended for production.",
                    key_size,
                )

            # Load and validate public key
            loaded_public_key = serialization.load_pem_public_key(
                public_key.encode("utf-8"),
            )

            if not isinstance(loaded_public_key, rsa.RSAPublicKey):
                raise ImproperlyConfigured(
                    "JWT_PUBLIC_KEY must be an RSA public key for RS256 algorithm."
                )

            logger.info(
                "JWT RS256 keys validated successfully (key size: %d bits).",
                key_size,
            )

        except ImportError:
            logger.warning(
                "cryptography library not installed. "
                "JWT key validation skipped. Install with: pip install cryptography"
            )

        except ValueError as e:
            raise ImproperlyConfigured(
                f"Invalid JWT key format: {e}. "
                "Ensure keys are valid PEM-encoded RSA keys."
            ) from e

        except Exception as e:
            raise ImproperlyConfigured(
                f"JWT key validation failed: {e}"
            ) from e
