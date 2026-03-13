"""
Google Secret Manager integration for secure secret storage.

Provides access to encryption keys, fiscal credentials, and other
secrets stored in Google Secret Manager per FR-011.
"""

import functools
import logging
from typing import Optional

from django.conf import settings

logger = logging.getLogger("security")

# Flag to track if we're using local secrets (development) or GCP
_using_local_secrets = True


def _get_secret_manager_client():
    """
    Get Google Secret Manager client.

    Returns None in development mode or if GCP client is unavailable.
    """
    global _using_local_secrets

    try:
        from google.cloud import secretmanager

        client = secretmanager.SecretManagerServiceClient()
        _using_local_secrets = False
        return client
    except ImportError:
        logger.debug("google-cloud-secret-manager not installed, using local secrets")
        _using_local_secrets = True
        return None
    except Exception as e:
        logger.warning(f"Failed to initialize Secret Manager client: {e}")
        _using_local_secrets = True
        return None


@functools.lru_cache(maxsize=100)
def get_secret(secret_id: str, version: str = "latest") -> Optional[str]:
    """
    Retrieve secret from Google Secret Manager.

    Falls back to environment variables in development mode.

    Args:
        secret_id: The secret identifier in Secret Manager.
        version: Version to retrieve (default: "latest").

    Returns:
        Secret value as string, or None if not found.

    Example:
        encryption_key = get_secret("gravitea-encryption-key")
    """
    client = _get_secret_manager_client()

    if client is None:
        # Development mode: fall back to environment variables
        import os

        env_key = secret_id.upper().replace("-", "_")
        value = os.environ.get(env_key)
        if value:
            logger.debug(f"Retrieved secret '{secret_id}' from environment")
        return value

    try:
        project_id = getattr(settings, "GCP_PROJECT_ID", "gravitea-erp")
        name = f"projects/{project_id}/secrets/{secret_id}/versions/{version}"

        response = client.access_secret_version(request={"name": name})
        secret_value = response.payload.data.decode("UTF-8")

        logger.debug(f"Retrieved secret '{secret_id}' from Secret Manager")
        return secret_value

    except Exception as e:
        logger.error(f"Failed to retrieve secret '{secret_id}': {e}")
        return None


def get_fiscal_credentials(tenant_secrets_ref: str) -> Optional[dict]:
    """
    Get tenant's AFIP fiscal credentials from Secret Manager.

    Retrieves X.509 certificate, private key, and CUIT for
    AFIP web service authentication.

    Args:
        tenant_secrets_ref: The fiscal_secrets_ref from tenant table
                           (e.g., "tenant-abc123-fiscal")

    Returns:
        Dictionary with fiscal credentials:
        {
            'certificate': X.509 certificate PEM string,
            'private_key': Private key PEM string,
            'cuit': Tenant's CUIT number
        }
        Returns None if credentials cannot be retrieved.

    Security Notes:
        - Credentials are cached for the application lifetime
        - Never log credential values
        - Certificate and key are stored separately in Secret Manager
    """
    if not tenant_secrets_ref:
        logger.warning("No fiscal_secrets_ref provided")
        return None

    try:
        certificate = get_secret(f"{tenant_secrets_ref}-certificate")
        private_key = get_secret(f"{tenant_secrets_ref}-private-key")
        cuit = get_secret(f"{tenant_secrets_ref}-cuit")

        if not all([certificate, private_key, cuit]):
            logger.error(f"Incomplete fiscal credentials for {tenant_secrets_ref}")
            return None

        logger.info(f"Successfully loaded fiscal credentials for {tenant_secrets_ref}")

        return {
            "certificate": certificate,
            "private_key": private_key,
            "cuit": cuit,
        }

    except Exception as e:
        logger.error(f"Failed to load fiscal credentials: {e}")
        return None


def clear_secret_cache():
    """
    Clear the secret cache.

    Call this when secrets need to be refreshed,
    e.g., after key rotation.
    """
    get_secret.cache_clear()
    logger.info("Secret cache cleared")
