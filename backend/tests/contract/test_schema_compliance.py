"""
Contract tests for OpenAPI schema compliance.

Validates that API responses match their documented OpenAPI schemas.
This ensures API contracts are accurate and helps catch breaking changes.

Per spec.md API Contract Validation requirements.
"""

from __future__ import annotations

import uuid

import pytest
from django.urls import reverse
from rest_framework import status


pytestmark = pytest.mark.django_db


# ============================================================
# T044: Product List Schema Compliance
# ============================================================


class TestProductListSchemaCompliance:
    """Tests for product list endpoint schema compliance."""

    def test_product_list_returns_paginated_response(
        self,
        authenticated_client,
        product,
        list_response_contract,
        assert_contract_valid,
    ):
        """Verify product list response matches paginated list contract."""
        url = reverse("product-list")

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        errors = list_response_contract(response.json())
        assert_contract_valid(errors, "Product list pagination")

    def test_product_list_item_has_required_fields(
        self,
        authenticated_client,
        product,
        detail_response_contract,
        assert_contract_valid,
    ):
        """Verify each product item has required fields."""
        url = reverse("product-list")

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Validate each product in results
        required_fields = ["id", "sku", "name", "unit_price", "is_active"]
        field_types = {
            "id": "string",  # UUID
            "sku": "string",
            "name": "string",
            "is_active": "boolean",
        }

        for item in data["results"]:
            errors = detail_response_contract(
                item, required_fields=required_fields, field_types=field_types
            )
            assert_contract_valid(errors, f"Product item {item.get('sku', 'unknown')}")

    def test_product_list_cursor_pagination_structure(
        self,
        authenticated_client,
        product,
        cursor_pagination_contract,
        assert_contract_valid,
    ):
        """Verify product list uses cursor pagination structure."""
        url = reverse("product-list")

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        errors = cursor_pagination_contract(response.json())
        assert_contract_valid(errors, "Product list cursor pagination")

    def test_product_list_empty_results_still_valid(
        self,
        authenticated_client,
        tenant_context,
        list_response_contract,
        assert_contract_valid,
    ):
        """Verify empty product list still returns valid paginated structure."""
        # Don't create any products - just use tenant_context
        url = reverse("product-list")

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        errors = list_response_contract(data)
        assert_contract_valid(errors, "Empty product list")
        assert data["results"] == []


# ============================================================
# T045: Product Detail Schema Compliance
# ============================================================


class TestProductDetailSchemaCompliance:
    """Tests for product detail endpoint schema compliance."""

    def test_product_detail_returns_full_object(
        self,
        authenticated_client,
        product,
        detail_response_contract,
        assert_contract_valid,
    ):
        """Verify product detail response contains all required fields."""
        url = reverse("product-detail", kwargs={"pk": product.pk})

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK

        required_fields = [
            "id",
            "sku",
            "name",
            "unit_price",
            "cost_price",
            "is_active",
            "created_at",
            "updated_at",
        ]
        field_types = {
            "id": "string",  # UUID
            "sku": "string",
            "name": "string",
            "is_active": "boolean",
            "created_at": "string",  # ISO datetime
            "updated_at": "string",  # ISO datetime
        }

        errors = detail_response_contract(
            response.json(), required_fields=required_fields, field_types=field_types
        )
        assert_contract_valid(errors, "Product detail")

    def test_product_detail_uuid_format(
        self,
        authenticated_client,
        product,
    ):
        """Verify product ID is valid UUID format."""
        url = reverse("product-detail", kwargs={"pk": product.pk})

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Validate UUID format
        try:
            uuid.UUID(data["id"])
        except (ValueError, KeyError) as e:
            pytest.fail(f"Product ID is not valid UUID: {e}")

    def test_product_detail_not_found_returns_problem_detail(
        self,
        authenticated_client,
        problem_detail_contract,
        assert_contract_valid,
    ):
        """Verify 404 returns RFC 7807 Problem Details."""
        fake_id = uuid.uuid4()
        url = reverse("product-detail", kwargs={"pk": fake_id})

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        errors = problem_detail_contract(response.json())
        assert_contract_valid(errors, "Product not found error")

    def test_product_detail_datetime_iso_format(
        self,
        authenticated_client,
        product,
    ):
        """Verify datetime fields are in ISO 8601 format."""
        from datetime import datetime

        url = reverse("product-detail", kwargs={"pk": product.pk})

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Validate ISO 8601 datetime format
        for field in ["created_at", "updated_at"]:
            if field in data and data[field]:
                try:
                    # Try parsing ISO format
                    datetime.fromisoformat(data[field].replace("Z", "+00:00"))
                except ValueError as e:
                    pytest.fail(f"Field '{field}' is not valid ISO 8601: {e}")


# ============================================================
# T046: Stock Movement Schema Compliance
# ============================================================


class TestStockMovementSchemaCompliance:
    """Tests for stock movement endpoint schema compliance."""

    def test_stock_movement_list_paginated(
        self,
        authenticated_client,
        stock_movement,
        list_response_contract,
        assert_contract_valid,
    ):
        """Verify stock movement list is paginated."""
        url = reverse("movement-list")

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        errors = list_response_contract(response.json())
        assert_contract_valid(errors, "Stock movement list pagination")

    def test_stock_movement_item_has_required_fields(
        self,
        authenticated_client,
        stock_movement,
        detail_response_contract,
        assert_contract_valid,
    ):
        """Verify stock movement items have required fields."""
        url = reverse("movement-list")

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Validate each movement
        required_fields = ["id", "product", "branch", "type", "quantity_delta"]
        field_types = {
            "id": "string",  # UUID
            "type": "string",
        }

        for item in data["results"]:
            errors = detail_response_contract(
                item, required_fields=required_fields, field_types=field_types
            )
            assert_contract_valid(errors, f"Stock movement {item.get('id', 'unknown')}")

    def test_stock_movement_detail_schema(
        self,
        authenticated_client,
        stock_movement,
        detail_response_contract,
        assert_contract_valid,
    ):
        """Verify stock movement detail matches schema."""
        url = reverse("movement-detail", kwargs={"pk": stock_movement.pk})

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK

        required_fields = [
            "id",
            "product",
            "branch",
            "type",
            "quantity_delta",
            "created_at",
        ]

        errors = detail_response_contract(response.json(), required_fields=required_fields)
        assert_contract_valid(errors, "Stock movement detail")

    def test_stock_movement_type_enum_values(
        self,
        authenticated_client,
        stock_movement,
    ):
        """Verify stock movement type uses valid enum values."""
        url = reverse("movement-detail", kwargs={"pk": stock_movement.pk})

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Valid movement types per model
        valid_types = [
            "PURCHASE",
            "SALE",
            "ADJUSTMENT_IN",
            "ADJUSTMENT_OUT",
            "TRANSFER_IN",
            "TRANSFER_OUT",
            "RETURN",
            "DAMAGE",
        ]
        assert data["type"] in valid_types, f"Invalid movement type: {data['type']}"


# ============================================================
# T047: Sync Session Schema Compliance
# ============================================================


class TestSyncSessionSchemaCompliance:
    """Tests for sync session endpoint schema compliance."""

    def test_sync_session_list_paginated(
        self,
        authenticated_client,
        sync_session,
        list_response_contract,
        assert_contract_valid,
    ):
        """Verify sync session list is paginated."""
        url = reverse("session-list")

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        errors = list_response_contract(response.json())
        assert_contract_valid(errors, "Sync session list pagination")

    def test_sync_session_item_has_required_fields(
        self,
        authenticated_client,
        sync_session,
        detail_response_contract,
        assert_contract_valid,
    ):
        """Verify sync session items have required fields."""
        url = reverse("session-list")

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        required_fields = ["id", "device_id", "branch", "status"]
        field_types = {
            "id": "string",  # UUID
            "device_id": "string",
            "status": "string",
        }

        for item in data["results"]:
            errors = detail_response_contract(
                item, required_fields=required_fields, field_types=field_types
            )
            assert_contract_valid(errors, f"Sync session {item.get('device_id', 'unknown')}")

    def test_sync_session_detail_schema(
        self,
        authenticated_client,
        sync_session,
        detail_response_contract,
        assert_contract_valid,
    ):
        """Verify sync session detail matches schema."""
        url = reverse("session-detail", kwargs={"pk": sync_session.pk})

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK

        required_fields = [
            "id",
            "device_id",
            "branch",
            "status",
            "created_at",
            "updated_at",
        ]

        errors = detail_response_contract(response.json(), required_fields=required_fields)
        assert_contract_valid(errors, "Sync session detail")

    def test_sync_session_status_enum_values(
        self,
        authenticated_client,
        sync_session,
    ):
        """Verify sync session status uses valid enum values."""
        url = reverse("session-detail", kwargs={"pk": sync_session.pk})

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Valid status values per model (uppercase in database)
        valid_statuses = ["PENDING", "PROCESSING", "COMPLETED", "ERROR"]
        assert (
            data["status"] in valid_statuses
        ), f"Invalid sync status: {data['status']}"


# ============================================================
# T048: Authentication Response Schema Compliance
# ============================================================


class TestAuthResponseSchemaCompliance:
    """Tests for authentication endpoint schema compliance."""

    def test_token_obtain_returns_required_fields(
        self,
        api_client,
        admin_user,
        detail_response_contract,
        assert_contract_valid,
    ):
        """Verify token obtain response has required fields."""
        url = reverse("auth:token_obtain_pair")
        data = {
            "email": admin_user.email,
            "password": "TestPassword123!",
        }

        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_200_OK

        required_fields = ["access", "refresh"]
        field_types = {
            "access": "string",
            "refresh": "string",
        }

        errors = detail_response_contract(
            response.json(), required_fields=required_fields, field_types=field_types
        )
        assert_contract_valid(errors, "Token obtain response")

    def test_token_refresh_returns_required_fields(
        self,
        api_client,
        admin_user,
        detail_response_contract,
        assert_contract_valid,
    ):
        """Verify token refresh response has required fields."""
        # First get tokens
        token_url = reverse("auth:token_obtain_pair")
        token_response = api_client.post(
            token_url,
            {"email": admin_user.email, "password": "TestPassword123!"},
        )
        refresh_token = token_response.json()["refresh"]

        # Then refresh
        refresh_url = reverse("auth:token_refresh")
        response = api_client.post(refresh_url, {"refresh": refresh_token})

        assert response.status_code == status.HTTP_200_OK

        required_fields = ["access"]
        field_types = {"access": "string"}

        errors = detail_response_contract(
            response.json(), required_fields=required_fields, field_types=field_types
        )
        assert_contract_valid(errors, "Token refresh response")

    def test_invalid_credentials_returns_problem_detail(
        self,
        api_client,
        problem_detail_contract,
        assert_contract_valid,
    ):
        """Verify invalid credentials return RFC 7807 Problem Details."""
        url = reverse("auth:token_obtain_pair")
        data = {
            "email": "nonexistent@test.com",
            "password": "WrongPassword123!",
        }

        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        errors = problem_detail_contract(response.json())
        assert_contract_valid(errors, "Invalid credentials error")

    def test_user_list_paginated(
        self,
        authenticated_client,
        list_response_contract,
        assert_contract_valid,
    ):
        """Verify user list is paginated."""
        url = reverse("auth:user-list")

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        errors = list_response_contract(response.json())
        assert_contract_valid(errors, "User list pagination")

    def test_user_item_has_required_fields(
        self,
        authenticated_client,
        detail_response_contract,
        assert_contract_valid,
    ):
        """Verify user items have required fields."""
        url = reverse("auth:user-list")

        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        required_fields = ["id", "email", "full_name", "is_active"]
        field_types = {
            "id": "string",  # UUID
            "email": "string",
            "full_name": "string",
            "is_active": "boolean",
        }

        for item in data["results"]:
            errors = detail_response_contract(
                item, required_fields=required_fields, field_types=field_types
            )
            assert_contract_valid(errors, f"User {item.get('email', 'unknown')}")

    def test_token_jwt_structure(
        self,
        api_client,
        admin_user,
    ):
        """Verify JWT tokens have proper structure (header.payload.signature)."""
        url = reverse("auth:token_obtain_pair")
        data = {
            "email": admin_user.email,
            "password": "TestPassword123!",
        }

        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_200_OK
        tokens = response.json()

        for token_name in ["access", "refresh"]:
            token = tokens[token_name]
            parts = token.split(".")
            assert len(parts) == 3, f"{token_name} token should have 3 parts (JWT format)"
            # Each part should be non-empty
            for i, part in enumerate(parts):
                assert len(part) > 0, f"{token_name} token part {i} should not be empty"


# ============================================================
# Cross-Cutting Schema Compliance Tests
# ============================================================


class TestCrossCuttingSchemaCompliance:
    """Tests for schema compliance across multiple endpoints."""

    def test_all_list_endpoints_use_cursor_pagination(
        self,
        authenticated_client,
        product,
        stock_movement,
        sync_session,
        cursor_pagination_contract,
        assert_contract_valid,
    ):
        """Verify all list endpoints use cursor pagination consistently."""
        endpoints = [
            ("product-list", "Products"),
            ("movement-list", "Movements"),
            ("session-list", "Sync Sessions"),
            ("auth:user-list", "Users"),
        ]

        for url_name, description in endpoints:
            url = reverse(url_name)
            response = authenticated_client.get(url)

            assert response.status_code == status.HTTP_200_OK, (
                f"{description} returned {response.status_code}"
            )
            errors = cursor_pagination_contract(response.json())
            assert_contract_valid(errors, f"{description} cursor pagination")

    def test_all_detail_endpoints_return_uuid_id(
        self,
        authenticated_client,
        product,
        stock_movement,
        sync_session,
    ):
        """Verify all detail endpoints return valid UUID IDs."""
        resources = [
            (reverse("product-detail", kwargs={"pk": product.pk}), "Product"),
            (
                reverse("movement-detail", kwargs={"pk": stock_movement.pk}),
                "Movement",
            ),
            (reverse("session-detail", kwargs={"pk": sync_session.pk}), "Sync Session"),
        ]

        for url, description in resources:
            response = authenticated_client.get(url)

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert "id" in data, f"{description} missing 'id' field"
            try:
                uuid.UUID(data["id"])
            except ValueError:
                pytest.fail(f"{description} ID is not valid UUID: {data['id']}")

    def test_all_not_found_errors_are_problem_detail(
        self,
        authenticated_client,
        problem_detail_contract,
        assert_contract_valid,
    ):
        """Verify all 404 errors return RFC 7807 Problem Details."""
        fake_id = uuid.uuid4()
        endpoints = [
            (reverse("product-detail", kwargs={"pk": fake_id}), "Product"),
            (reverse("movement-detail", kwargs={"pk": fake_id}), "Movement"),
            (reverse("session-detail", kwargs={"pk": fake_id}), "Sync Session"),
            (reverse("auth:user-detail", kwargs={"pk": fake_id}), "User"),
        ]

        for url, description in endpoints:
            response = authenticated_client.get(url)

            assert response.status_code == status.HTTP_404_NOT_FOUND, (
                f"{description} returned {response.status_code}, expected 404"
            )
            errors = problem_detail_contract(response.json())
            assert_contract_valid(errors, f"{description} not found error")

    def test_all_unauthorized_errors_are_problem_detail(
        self,
        api_client,
        product,
        problem_detail_contract,
        assert_contract_valid,
    ):
        """Verify all 401 errors return RFC 7807 Problem Details."""
        endpoints = [
            (reverse("product-list"), "Products"),
            (reverse("movement-list"), "Movements"),
            (reverse("session-list"), "Sync Sessions"),
            (reverse("auth:user-list"), "Users"),
        ]

        for url, description in endpoints:
            response = api_client.get(url)

            assert response.status_code == status.HTTP_401_UNAUTHORIZED, (
                f"{description} returned {response.status_code}, expected 401"
            )
            errors = problem_detail_contract(response.json())
            assert_contract_valid(errors, f"{description} unauthorized error")
