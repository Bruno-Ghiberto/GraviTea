"""
Tests for authentication endpoints.

Tests JWT token generation, refresh, and logout functionality.
"""

import pytest
from django.urls import reverse
from rest_framework import status

pytestmark = pytest.mark.django_db


class TestTokenObtain:
    """Tests for token obtain endpoint."""

    def test_obtain_token_success(self, api_client, admin_user):
        """Test successful token generation."""
        url = reverse("auth:token_obtain_pair")
        data = {
            "email": admin_user.email,
            "password": "TestPassword123!",
        }

        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data
        assert "access_expires_at" in response.data

    def test_obtain_token_invalid_password(self, api_client, admin_user):
        """Test token generation with invalid password."""
        url = reverse("auth:token_obtain_pair")
        data = {
            "email": admin_user.email,
            "password": "WrongPassword123!",
        }

        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_obtain_token_invalid_email(self, api_client):
        """Test token generation with non-existent email."""
        url = reverse("auth:token_obtain_pair")
        data = {
            "email": "nonexistent@test.com",
            "password": "TestPassword123!",
        }

        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_obtain_token_inactive_user(self, api_client, admin_user):
        """Test token generation for inactive user."""
        admin_user.is_active = False
        admin_user.save()

        url = reverse("auth:token_obtain_pair")
        data = {
            "email": admin_user.email,
            "password": "TestPassword123!",
        }

        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_obtain_token_inactive_tenant(self, api_client, admin_user, tenant):
        """Test token generation for user with inactive tenant."""
        tenant.is_active = False
        tenant.save()

        url = reverse("auth:token_obtain_pair")
        data = {
            "email": admin_user.email,
            "password": "TestPassword123!",
        }

        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "suspended" in response.data["detail"].lower()


class TestTokenRefresh:
    """Tests for token refresh endpoint."""

    def test_refresh_token_success(self, api_client, admin_user):
        """Test successful token refresh."""
        # First, obtain tokens
        obtain_url = reverse("auth:token_obtain_pair")
        obtain_data = {
            "email": admin_user.email,
            "password": "TestPassword123!",
        }
        obtain_response = api_client.post(obtain_url, obtain_data)
        refresh_token = obtain_response.data["refresh"]

        # Then, refresh
        refresh_url = reverse("auth:token_refresh")
        refresh_data = {"refresh": refresh_token}

        response = api_client.post(refresh_url, refresh_data)

        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data

    def test_refresh_token_invalid(self, api_client):
        """Test refresh with invalid token."""
        url = reverse("auth:token_refresh")
        data = {"refresh": "invalid-token"}

        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestLogout:
    """Tests for logout endpoint."""

    def test_logout_success(self, authenticated_client, admin_user):
        """Test successful logout (token blacklisting)."""
        # First, obtain refresh token
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(admin_user)

        url = reverse("auth:logout")
        data = {"refresh": str(refresh)}

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_205_RESET_CONTENT

    def test_logout_without_token(self, authenticated_client):
        """Test logout without refresh token."""
        url = reverse("auth:logout")

        response = authenticated_client.post(url, {})

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_logout_unauthenticated(self, api_client):
        """Test logout without authentication."""
        url = reverse("auth:logout")
        data = {"refresh": "some-token"}

        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestTokenVerify:
    """Tests for token verification endpoint."""

    def test_verify_token_success(self, api_client, admin_user):
        """Test token verification with valid token."""
        # First, obtain tokens
        obtain_url = reverse("auth:token_obtain_pair")
        obtain_data = {
            "email": admin_user.email,
            "password": "TestPassword123!",
        }
        obtain_response = api_client.post(obtain_url, obtain_data)
        access_token = obtain_response.data["access"]

        # Then, verify
        verify_url = reverse("auth:token_verify")
        verify_data = {"token": access_token}

        response = api_client.post(verify_url, verify_data)

        assert response.status_code == status.HTTP_200_OK

    def test_verify_token_invalid(self, api_client):
        """Test token verification with invalid token."""
        url = reverse("auth:token_verify")
        data = {"token": "invalid-token"}

        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
