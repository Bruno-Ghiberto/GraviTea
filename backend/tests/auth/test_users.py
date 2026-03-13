"""
Tests for user management endpoints.

Tests CRUD operations on users and profile management.
"""

import pytest
from django.urls import reverse
from rest_framework import status

pytestmark = pytest.mark.django_db


class TestUserList:
    """Tests for user list endpoint."""

    def test_list_users_authenticated(self, authenticated_client, admin_user):
        """Test listing users as authenticated user."""
        url = reverse("auth:user-list")

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert len(response.data["results"]) >= 1

    def test_list_users_unauthenticated(self, api_client):
        """Test listing users without authentication."""
        url = reverse("auth:user-list")

        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_users_tenant_isolation(self, authenticated_client, other_tenant_user):
        """Test that users from other tenants are not visible."""
        url = reverse("auth:user-list")

        response = authenticated_client.get(url)

        emails = [user["email"] for user in response.data["results"]]
        assert other_tenant_user.email not in emails


class TestUserCreate:
    """Tests for user creation endpoint."""

    def test_create_user_success(self, authenticated_client, tenant, sales_role, branch):
        """Test successful user creation."""
        url = reverse("auth:user-list")
        data = {
            "email": "newuser@testcompany.com",
            "full_name": "New User",
            "password": "SecurePassword123!",
            "role_id": str(sales_role.id),
            "default_branch_id": str(branch.id),
        }

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["email"] == "newuser@testcompany.com"

    def test_create_user_duplicate_email(self, authenticated_client, admin_user):
        """Test creating user with duplicate email in same tenant."""
        url = reverse("auth:user-list")
        data = {
            "email": admin_user.email,  # Existing email
            "full_name": "Duplicate User",
            "password": "SecurePassword123!",
        }

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        # RFC 7807: Check for email error in errors array
        assert "errors" in response.data
        error_fields = [e["field"] for e in response.data["errors"]]
        assert "email" in error_fields

    def test_create_user_weak_password(self, authenticated_client):
        """Test creating user with weak password."""
        url = reverse("auth:user-list")
        data = {
            "email": "weakpwd@testcompany.com",
            "full_name": "Weak Password User",
            "password": "123",  # Too weak
        }

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        # RFC 7807: Check for password error in errors array
        assert "errors" in response.data
        error_fields = [e["field"] for e in response.data["errors"]]
        assert "password" in error_fields


class TestUserDetail:
    """Tests for user detail endpoint."""

    def test_get_user_detail(self, authenticated_client, admin_user):
        """Test getting user details."""
        url = reverse("auth:user-detail", kwargs={"pk": admin_user.id})

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == admin_user.email
        assert response.data["full_name"] == admin_user.full_name

    def test_get_other_tenant_user(self, authenticated_client, other_tenant_user):
        """Test that users from other tenants are not accessible."""
        url = reverse("auth:user-detail", kwargs={"pk": other_tenant_user.id})

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestUserUpdate:
    """Tests for user update endpoint."""

    def test_update_user_success(self, authenticated_client, sales_user):
        """Test updating user details."""
        url = reverse("auth:user-detail", kwargs={"pk": sales_user.id})
        data = {
            "full_name": "Updated Name",
        }

        response = authenticated_client.patch(url, data)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["full_name"] == "Updated Name"

    def test_deactivate_user(self, authenticated_client, sales_user):
        """Test deactivating a user."""
        url = reverse("auth:user-detail", kwargs={"pk": sales_user.id})
        data = {"is_active": False}

        response = authenticated_client.patch(url, data)

        assert response.status_code == status.HTTP_200_OK
        sales_user.refresh_from_db()
        assert sales_user.is_active is False


class TestUserMe:
    """Tests for current user endpoints."""

    def test_get_current_user(self, authenticated_client, admin_user):
        """Test getting current user profile."""
        url = reverse("auth:user-me")

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == admin_user.email
        assert "permissions" in response.data

    def test_update_current_user(self, authenticated_client, admin_user):
        """Test updating current user profile."""
        url = reverse("auth:user-me")
        data = {"full_name": "My New Name"}

        response = authenticated_client.patch(url, data)

        assert response.status_code == status.HTTP_200_OK
        admin_user.refresh_from_db()
        assert admin_user.full_name == "My New Name"


class TestChangePassword:
    """Tests for password change endpoint."""

    def test_change_password_success(self, authenticated_client, admin_user):
        """Test successful password change."""
        url = reverse("auth:user-change-password")
        data = {
            "current_password": "TestPassword123!",
            "new_password": "NewSecurePassword456!",
        }

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_200_OK
        admin_user.refresh_from_db()
        assert admin_user.check_password("NewSecurePassword456!")

    def test_change_password_wrong_current(self, authenticated_client):
        """Test password change with wrong current password."""
        url = reverse("auth:user-change-password")
        data = {
            "current_password": "WrongPassword123!",
            "new_password": "NewSecurePassword456!",
        }

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        # RFC 7807: Check for current_password error in errors array
        assert "errors" in response.data
        error_fields = [e["field"] for e in response.data["errors"]]
        assert "current_password" in error_fields

    def test_change_password_weak_new(self, authenticated_client):
        """Test password change with weak new password."""
        url = reverse("auth:user-change-password")
        data = {
            "current_password": "TestPassword123!",
            "new_password": "123",  # Too weak
        }

        response = authenticated_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        # RFC 7807: Check for new_password error in errors array
        assert "errors" in response.data
        error_fields = [e["field"] for e in response.data["errors"]]
        assert "new_password" in error_fields
