"""
Tests for Google Secret Manager integration module.

Tests cover:
1. Environment variable fallback behavior
2. GCP Secret Manager client initialization
3. Secret retrieval and caching
4. Fiscal credentials retrieval
5. Error handling and edge cases
6. Cache management
"""

import logging
import os
from unittest.mock import MagicMock, Mock, patch

import pytest

from apps.core.secrets import (
    _get_secret_manager_client,
    clear_secret_cache,
    get_fiscal_credentials,
    get_secret,
)

pytestmark = pytest.mark.django_db


# ============================================================
# Secret Manager Client Tests
# ============================================================


class TestSecretManagerClient:
    """Test Google Secret Manager client initialization."""

    def test_client_initialization_without_gcp_library(self):
        """
        Test client initialization when google-cloud-secretmanager is not installed.

        Expected: Returns None and sets _using_local_secrets flag.
        """
        with patch.dict("sys.modules", {"google.cloud.secretmanager": None}):
            with patch("apps.core.secrets.logger") as mock_logger:
                client = _get_secret_manager_client()

                assert client is None
                mock_logger.debug.assert_called_once()
                assert "not installed" in str(mock_logger.debug.call_args)

    def test_client_initialization_with_gcp_library_success(self):
        """
        Test successful GCP client initialization.

        Expected: Returns client instance and clears _using_local_secrets flag.
        """
        mock_client = MagicMock()
        mock_secretmanager_module = MagicMock()
        mock_secretmanager_module.SecretManagerServiceClient.return_value = mock_client

        mock_gcp = MagicMock()
        mock_gcp.secretmanager = mock_secretmanager_module

        with patch.dict("sys.modules", {"google.cloud": mock_gcp, "google.cloud.secretmanager": mock_secretmanager_module}):
            # Force reimport of the function to pick up mocked module
            import importlib
            import apps.core.secrets as secrets_module
            importlib.reload(secrets_module)

            client = secrets_module._get_secret_manager_client()
            assert client == mock_client

    def test_client_initialization_with_gcp_library_failure(self):
        """
        Test GCP client initialization failure handling.

        Expected: Returns None, logs warning, sets _using_local_secrets flag.
        Note: Warning is logged via the actual logger, not the mock during reload.
        """
        mock_secretmanager_module = MagicMock()
        mock_secretmanager_module.SecretManagerServiceClient.side_effect = Exception(
            "GCP authentication failed"
        )

        mock_gcp = MagicMock()
        mock_gcp.secretmanager = mock_secretmanager_module

        with patch.dict("sys.modules", {"google.cloud": mock_gcp, "google.cloud.secretmanager": mock_secretmanager_module}):
            # Force reimport to pick up mocked module
            import importlib
            import apps.core.secrets as secrets_module
            importlib.reload(secrets_module)

            client = secrets_module._get_secret_manager_client()

            assert client is None
            # The function returns None on exception - warning was logged during reload


# ============================================================
# Secret Retrieval Tests - Environment Variable Fallback
# ============================================================


class TestGetSecretEnvironment:
    """Test get_secret() with environment variable fallback."""

    def setup_method(self):
        """Clear cache before each test."""
        get_secret.cache_clear()

    def test_get_secret_from_environment_variable(self):
        """
        Test retrieving secret from environment variable.

        Expected: Returns environment variable value.
        """
        test_secret_value = "test-encryption-key-value"

        with patch.dict(os.environ, {"GRAVITEA_ENCRYPTION_KEY": test_secret_value}):
            with patch("apps.core.secrets._get_secret_manager_client", return_value=None):
                with patch("apps.core.secrets.logger") as mock_logger:
                    result = get_secret("gravitea-encryption-key")

                    assert result == test_secret_value
                    mock_logger.debug.assert_called_once()
                    assert "Retrieved secret" in str(mock_logger.debug.call_args)
                    assert "environment" in str(mock_logger.debug.call_args)

    def test_get_secret_environment_key_transformation(self):
        """
        Test secret_id to environment variable name transformation.

        Expected: Hyphens converted to underscores, uppercased.
        """
        test_value = "fiscal-secret-value"

        with patch.dict(os.environ, {"TENANT_ABC123_FISCAL": test_value}):
            with patch("apps.core.secrets._get_secret_manager_client", return_value=None):
                result = get_secret("tenant-abc123-fiscal")

                assert result == test_value

    def test_get_secret_not_found_in_environment(self):
        """
        Test behavior when secret not found in environment.

        Expected: Returns None.
        """
        with patch.dict(os.environ, {}, clear=True):
            with patch("apps.core.secrets._get_secret_manager_client", return_value=None):
                result = get_secret("non-existent-secret")

                assert result is None

    def test_get_secret_empty_environment_value(self):
        """
        Test behavior when environment variable is empty string.

        Expected: Returns empty string (falsy but present).
        """
        with patch.dict(os.environ, {"EMPTY_SECRET": ""}):
            with patch("apps.core.secrets._get_secret_manager_client", return_value=None):
                result = get_secret("empty-secret")

                # Empty string is falsy but still returned by os.environ.get()
                assert result == ""


# ============================================================
# Secret Retrieval Tests - GCP Secret Manager
# ============================================================


class TestGetSecretGCP:
    """Test get_secret() with GCP Secret Manager."""

    def setup_method(self):
        """Clear cache before each test."""
        get_secret.cache_clear()

    def test_get_secret_from_gcp_success(self, settings):
        """
        Test successful secret retrieval from GCP Secret Manager.

        Expected: Returns decrypted secret value.
        """
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.payload.data = b"gcp-secret-value"
        mock_client.access_secret_version.return_value = mock_response

        settings.GCP_PROJECT_ID = "test-project"

        with patch("apps.core.secrets._get_secret_manager_client", return_value=mock_client):
            with patch("apps.core.secrets.logger") as mock_logger:
                result = get_secret("test-secret", version="latest")

                assert result == "gcp-secret-value"
                mock_client.access_secret_version.assert_called_once()

                # Verify request format
                call_args = mock_client.access_secret_version.call_args
                request = call_args[1]["request"]
                assert "projects/test-project/secrets/test-secret/versions/latest" == request["name"]

                mock_logger.debug.assert_called_once()
                assert "Secret Manager" in str(mock_logger.debug.call_args)

    def test_get_secret_from_gcp_with_custom_version(self, settings):
        """
        Test secret retrieval with specific version.

        Expected: Requests correct version from GCP.
        """
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.payload.data = b"versioned-secret"
        mock_client.access_secret_version.return_value = mock_response

        settings.GCP_PROJECT_ID = "test-project"

        with patch("apps.core.secrets._get_secret_manager_client", return_value=mock_client):
            result = get_secret("test-secret", version="5")

            assert result == "versioned-secret"
            call_args = mock_client.access_secret_version.call_args
            request = call_args[1]["request"]
            assert "versions/5" in request["name"]

    def test_get_secret_from_gcp_failure(self, settings):
        """
        Test GCP secret retrieval failure handling.

        Expected: Returns None, logs error.
        """
        mock_client = MagicMock()
        mock_client.access_secret_version.side_effect = Exception(
            "Secret not found in GCP"
        )

        settings.GCP_PROJECT_ID = "test-project"

        with patch("apps.core.secrets._get_secret_manager_client", return_value=mock_client):
            with patch("apps.core.secrets.logger") as mock_logger:
                result = get_secret("missing-secret")

                assert result is None
                mock_logger.error.assert_called_once()
                assert "Failed to retrieve secret" in str(mock_logger.error.call_args)

    def test_get_secret_default_project_id(self):
        """
        Test secret retrieval uses default project ID when not configured.

        Expected: Uses 'gravitea-erp' as default project.
        """
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.payload.data = b"default-project-secret"
        mock_client.access_secret_version.return_value = mock_response

        with patch("apps.core.secrets._get_secret_manager_client", return_value=mock_client):
            with patch("apps.core.secrets.settings") as mock_settings:
                # No GCP_PROJECT_ID attribute
                delattr(mock_settings, "GCP_PROJECT_ID") if hasattr(
                    mock_settings, "GCP_PROJECT_ID"
                ) else None

                result = get_secret("test-secret")

                assert result == "default-project-secret"
                call_args = mock_client.access_secret_version.call_args
                request = call_args[1]["request"]
                assert "projects/gravitea-erp/" in request["name"]

    def test_get_secret_utf8_decoding(self):
        """
        Test secret value is properly decoded from UTF-8 bytes.

        Expected: Returns string with special characters correctly decoded.
        """
        mock_client = MagicMock()
        mock_response = MagicMock()
        # UTF-8 encoded string with special characters
        mock_response.payload.data = "Contraseña-Ñoño-2024!".encode("utf-8")
        mock_client.access_secret_version.return_value = mock_response

        with patch("apps.core.secrets._get_secret_manager_client", return_value=mock_client):
            result = get_secret("test-secret")

            assert result == "Contraseña-Ñoño-2024!"
            assert isinstance(result, str)


# ============================================================
# Secret Caching Tests
# ============================================================


class TestSecretCaching:
    """Test LRU cache behavior for get_secret()."""

    def setup_method(self):
        """Clear cache before each test."""
        get_secret.cache_clear()

    def test_secret_cached_after_first_retrieval(self):
        """
        Test secret is cached after first successful retrieval.

        Expected: Second call doesn't hit backend.
        """
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.payload.data = b"cached-secret"
        mock_client.access_secret_version.return_value = mock_response

        with patch("apps.core.secrets._get_secret_manager_client", return_value=mock_client):
            # First call
            result1 = get_secret("cached-secret")
            assert result1 == "cached-secret"
            assert mock_client.access_secret_version.call_count == 1

            # Second call - should use cache
            result2 = get_secret("cached-secret")
            assert result2 == "cached-secret"
            # Still only 1 call to backend
            assert mock_client.access_secret_version.call_count == 1

    def test_different_secrets_cached_separately(self):
        """
        Test different secrets are cached independently.

        Expected: Each unique secret_id cached separately.
        """
        test_secrets = {
            "SECRET_ONE": "value-one",
            "SECRET_TWO": "value-two",
        }

        with patch.dict(os.environ, test_secrets):
            with patch("apps.core.secrets._get_secret_manager_client", return_value=None):
                result1 = get_secret("secret-one")
                result2 = get_secret("secret-two")

                assert result1 == "value-one"
                assert result2 == "value-two"

    def test_secret_version_cached_separately(self):
        """
        Test different versions of same secret cached separately.

        Expected: version parameter affects cache key.
        """
        mock_client = MagicMock()

        def mock_access(request):
            mock_response = MagicMock()
            if "versions/1" in request["name"]:
                mock_response.payload.data = b"version-1-value"
            else:
                mock_response.payload.data = b"latest-value"
            return mock_response

        mock_client.access_secret_version.side_effect = mock_access

        with patch("apps.core.secrets._get_secret_manager_client", return_value=mock_client):
            result_latest = get_secret("test-secret", version="latest")
            result_v1 = get_secret("test-secret", version="1")

            assert result_latest == "latest-value"
            assert result_v1 == "version-1-value"
            # Should make 2 calls (not cached together)
            assert mock_client.access_secret_version.call_count == 2

    def test_cache_cleared_successfully(self):
        """
        Test clear_secret_cache() clears the LRU cache.

        Expected: Calling clear_secret_cache logs and calls cache_clear.
        """
        with patch("apps.core.secrets.get_secret.cache_clear") as mock_cache_clear:
            with patch("apps.core.secrets.logger") as mock_logger:
                clear_secret_cache()

                # Verify cache_clear was called
                mock_cache_clear.assert_called_once()

                # Verify info log was written
                mock_logger.info.assert_called_once_with("Secret cache cleared")


# ============================================================
# Fiscal Credentials Tests
# ============================================================


class TestGetFiscalCredentials:
    """Test get_fiscal_credentials() for AFIP integration."""

    def setup_method(self):
        """Clear cache before each test."""
        get_secret.cache_clear()

    def test_get_fiscal_credentials_success(self):
        """
        Test successful retrieval of complete fiscal credentials.

        Expected: Returns dict with certificate, private_key, and cuit.
        """
        test_secrets = {
            "TENANT_ABC_FISCAL_CERTIFICATE": "-----BEGIN CERTIFICATE-----\ntest-cert\n-----END CERTIFICATE-----",
            "TENANT_ABC_FISCAL_PRIVATE_KEY": "-----BEGIN PRIVATE KEY-----\ntest-key\n-----END PRIVATE KEY-----",
            "TENANT_ABC_FISCAL_CUIT": "20-12345678-9",
        }

        with patch.dict(os.environ, test_secrets):
            with patch("apps.core.secrets._get_secret_manager_client", return_value=None):
                with patch("apps.core.secrets.logger") as mock_logger:
                    result = get_fiscal_credentials("tenant-abc-fiscal")

                    assert result is not None
                    assert "certificate" in result
                    assert "private_key" in result
                    assert "cuit" in result
                    assert result["certificate"].startswith("-----BEGIN CERTIFICATE-----")
                    assert result["private_key"].startswith("-----BEGIN PRIVATE KEY-----")
                    assert result["cuit"] == "20-12345678-9"

                    mock_logger.info.assert_called_once()
                    assert "Successfully loaded fiscal credentials" in str(
                        mock_logger.info.call_args
                    )

    def test_get_fiscal_credentials_missing_certificate(self):
        """
        Test fiscal credentials retrieval with missing certificate.

        Expected: Returns None, logs error about incomplete credentials.
        """
        test_secrets = {
            "TENANT_XYZ_FISCAL_PRIVATE_KEY": "test-key",
            "TENANT_XYZ_FISCAL_CUIT": "20-12345678-9",
            # Certificate missing
        }

        with patch.dict(os.environ, test_secrets, clear=True):
            with patch("apps.core.secrets._get_secret_manager_client", return_value=None):
                with patch("apps.core.secrets.logger") as mock_logger:
                    result = get_fiscal_credentials("tenant-xyz-fiscal")

                    assert result is None
                    mock_logger.error.assert_called_once()
                    assert "Incomplete fiscal credentials" in str(
                        mock_logger.error.call_args
                    )

    def test_get_fiscal_credentials_missing_private_key(self):
        """
        Test fiscal credentials retrieval with missing private key.

        Expected: Returns None, logs error.
        """
        test_secrets = {
            "TENANT_DEF_FISCAL_CERTIFICATE": "test-cert",
            "TENANT_DEF_FISCAL_CUIT": "20-12345678-9",
            # Private key missing
        }

        with patch.dict(os.environ, test_secrets, clear=True):
            with patch("apps.core.secrets._get_secret_manager_client", return_value=None):
                with patch("apps.core.secrets.logger") as mock_logger:
                    result = get_fiscal_credentials("tenant-def-fiscal")

                    assert result is None
                    mock_logger.error.assert_called_once()

    def test_get_fiscal_credentials_missing_cuit(self):
        """
        Test fiscal credentials retrieval with missing CUIT.

        Expected: Returns None, logs error.
        """
        test_secrets = {
            "TENANT_GHI_FISCAL_CERTIFICATE": "test-cert",
            "TENANT_GHI_FISCAL_PRIVATE_KEY": "test-key",
            # CUIT missing
        }

        with patch.dict(os.environ, test_secrets, clear=True):
            with patch("apps.core.secrets._get_secret_manager_client", return_value=None):
                with patch("apps.core.secrets.logger") as mock_logger:
                    result = get_fiscal_credentials("tenant-ghi-fiscal")

                    assert result is None
                    mock_logger.error.assert_called_once()

    def test_get_fiscal_credentials_empty_secrets_ref(self):
        """
        Test fiscal credentials with empty secrets_ref.

        Expected: Returns None, logs warning.
        """
        with patch("apps.core.secrets.logger") as mock_logger:
            result = get_fiscal_credentials("")

            assert result is None
            mock_logger.warning.assert_called_once()
            assert "No fiscal_secrets_ref provided" in str(mock_logger.warning.call_args)

    def test_get_fiscal_credentials_none_secrets_ref(self):
        """
        Test fiscal credentials with None secrets_ref.

        Expected: Returns None, logs warning.
        """
        with patch("apps.core.secrets.logger") as mock_logger:
            result = get_fiscal_credentials(None)

            assert result is None
            mock_logger.warning.assert_called_once()

    def test_get_fiscal_credentials_retrieval_exception(self):
        """
        Test fiscal credentials retrieval with unexpected exception.

        Expected: Returns None, logs error.
        """
        with patch("apps.core.secrets.get_secret", side_effect=Exception("Unexpected error")):
            with patch("apps.core.secrets.logger") as mock_logger:
                result = get_fiscal_credentials("tenant-abc-fiscal")

                assert result is None
                mock_logger.error.assert_called_once()
                assert "Failed to load fiscal credentials" in str(
                    mock_logger.error.call_args
                )

    def test_get_fiscal_credentials_calls_get_secret_correctly(self):
        """
        Test fiscal credentials makes correct get_secret() calls.

        Expected: Calls get_secret 3 times with correct secret IDs.
        """
        with patch("apps.core.secrets.get_secret") as mock_get_secret:
            mock_get_secret.return_value = "test-value"

            get_fiscal_credentials("tenant-xyz-fiscal")

            assert mock_get_secret.call_count == 3

            # Verify call arguments
            calls = [call[0][0] for call in mock_get_secret.call_args_list]
            assert "tenant-xyz-fiscal-certificate" in calls
            assert "tenant-xyz-fiscal-private-key" in calls
            assert "tenant-xyz-fiscal-cuit" in calls


# ============================================================
# Logging Tests
# ============================================================


class TestSecretLogging:
    """Test logging behavior for security audit trails."""

    def setup_method(self):
        """Clear cache before each test."""
        get_secret.cache_clear()

    def test_secret_retrieval_logs_debug(self):
        """
        Test secret retrieval logs at debug level (not info).

        Expected: Uses logger.debug() to avoid log spam.
        """
        with patch.dict(os.environ, {"TEST_SECRET": "value"}):
            with patch("apps.core.secrets._get_secret_manager_client", return_value=None):
                with patch("apps.core.secrets.logger") as mock_logger:
                    get_secret("test-secret")

                    mock_logger.debug.assert_called_once()
                    mock_logger.info.assert_not_called()

    def test_fiscal_credentials_success_logs_info(self):
        """
        Test fiscal credentials success logs at info level.

        Expected: Important AFIP credential loads are logged.
        """
        test_secrets = {
            "TENANT_FISCAL_CERTIFICATE": "cert",
            "TENANT_FISCAL_PRIVATE_KEY": "key",
            "TENANT_FISCAL_CUIT": "cuit",
        }

        with patch.dict(os.environ, test_secrets):
            with patch("apps.core.secrets._get_secret_manager_client", return_value=None):
                with patch("apps.core.secrets.logger") as mock_logger:
                    get_fiscal_credentials("tenant-fiscal")

                    mock_logger.info.assert_called_once()

    def test_cache_clear_logs_info(self):
        """
        Test cache clearing logs at info level.

        Expected: Cache operations are logged for audit.
        """
        with patch("apps.core.secrets.logger") as mock_logger:
            clear_secret_cache()

            mock_logger.info.assert_called_once_with("Secret cache cleared")

    def test_errors_logged_not_raised(self):
        """
        Test errors are logged but not raised (graceful degradation).

        Expected: Returns None instead of raising exception.
        """
        mock_client = MagicMock()
        mock_client.access_secret_version.side_effect = Exception("GCP error")

        with patch("apps.core.secrets._get_secret_manager_client", return_value=mock_client):
            with patch("apps.core.secrets.logger") as mock_logger:
                # Should not raise exception
                result = get_secret("failing-secret")

                assert result is None
                mock_logger.error.assert_called_once()


# ============================================================
# Edge Cases and Security Tests
# ============================================================


class TestSecretSecurityAndEdgeCases:
    """Test security considerations and edge cases."""

    def setup_method(self):
        """Clear cache before each test."""
        get_secret.cache_clear()

    def test_secret_values_not_logged(self):
        """
        Test secret values are never logged (security requirement).

        Expected: Log messages contain secret IDs but not values.
        """
        test_value = "super-secret-password-12345"

        with patch.dict(os.environ, {"TEST_SECRET": test_value}):
            with patch("apps.core.secrets._get_secret_manager_client", return_value=None):
                with patch("apps.core.secrets.logger") as mock_logger:
                    get_secret("test-secret")

                    # Get all log calls
                    all_calls = (
                        mock_logger.debug.call_args_list
                        + mock_logger.info.call_args_list
                        + mock_logger.warning.call_args_list
                        + mock_logger.error.call_args_list
                    )

                    # Verify secret value is not in any log message
                    for call in all_calls:
                        log_message = str(call)
                        assert test_value not in log_message

    def test_empty_string_secret_handled(self):
        """
        Test empty string secrets are returned as-is.

        Expected: Empty string is returned (application layer decides if valid).
        """
        with patch.dict(os.environ, {"EMPTY": ""}):
            with patch("apps.core.secrets._get_secret_manager_client", return_value=None):
                result = get_secret("empty")

                # Empty string is returned as-is, let application decide if valid
                assert result == ""

    def test_whitespace_only_secret_preserved(self):
        """
        Test whitespace-only secrets are preserved (might be intentional).

        Expected: Returns the whitespace value.
        """
        whitespace_value = "   "

        with patch.dict(os.environ, {"WHITESPACE": whitespace_value}):
            with patch("apps.core.secrets._get_secret_manager_client", return_value=None):
                result = get_secret("whitespace")

                # Whitespace is truthy, so it should be returned
                assert result == whitespace_value

    def test_special_characters_in_secret_id(self):
        """
        Test secret IDs with special characters are handled correctly.

        Expected: Hyphens converted to underscores for env lookup.
        """
        with patch.dict(os.environ, {"TENANT_ABC_123_FISCAL_KEY": "value"}):
            with patch("apps.core.secrets._get_secret_manager_client", return_value=None):
                result = get_secret("tenant-abc-123-fiscal-key")

                assert result == "value"

    def test_case_sensitivity_in_environment_lookup(self):
        """
        Test environment variable lookup is case-sensitive.

        Expected: Lowercase secret_id uppercased for env lookup.
        """
        with patch.dict(os.environ, {"MYAPP_SECRET": "correct-value"}):
            with patch("apps.core.secrets._get_secret_manager_client", return_value=None):
                result = get_secret("myapp-secret")

                assert result == "correct-value"

    def test_unicode_in_secret_value(self):
        """
        Test Unicode characters in secret values are preserved.

        Expected: UTF-8 encoding/decoding handles Unicode correctly.
        """
        unicode_value = "Contraseña-Ñoño-José-Óscar-Ángel"

        with patch.dict(os.environ, {"UNICODE_SECRET": unicode_value}):
            with patch("apps.core.secrets._get_secret_manager_client", return_value=None):
                result = get_secret("unicode-secret")

                assert result == unicode_value
                assert isinstance(result, str)

    def test_binary_data_in_secret(self):
        """
        Test binary data in GCP secrets is decoded to string.

        Expected: Payload bytes decoded as UTF-8.
        """
        mock_client = MagicMock()
        mock_response = MagicMock()
        # Binary data that decodes to valid UTF-8
        mock_response.payload.data = b"\x48\x65\x6c\x6c\x6f"  # "Hello"
        mock_client.access_secret_version.return_value = mock_response

        with patch("apps.core.secrets._get_secret_manager_client", return_value=mock_client):
            result = get_secret("binary-secret")

            assert result == "Hello"
            assert isinstance(result, str)

    def test_concurrent_access_cache_safety(self):
        """
        Test LRU cache is thread-safe for concurrent access.

        Expected: functools.lru_cache is thread-safe by default.
        Note: This is a basic smoke test. Full concurrency testing
        requires threading/multiprocessing.
        """
        with patch.dict(os.environ, {"CONCURRENT_SECRET": "value"}):
            with patch("apps.core.secrets._get_secret_manager_client", return_value=None):
                # Multiple sequential calls should use cache safely
                results = [get_secret("concurrent-secret") for _ in range(100)]

                assert all(r == "value" for r in results)
                assert len(set(id(r) for r in results)) == 1  # Same cached object
