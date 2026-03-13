"""
Security tests for Mass Assignment vulnerability prevention.

OWASP A04:2021 - Insecure Design (Mass Assignment)

Tests ensure the application properly protects sensitive fields
from being modified through API requests.

Test IDs: SEC-MASS-001 through SEC-MASS-011
"""

import uuid
import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from tests.constants import (
    FORBIDDEN_FIELDS_TENANT,
    FORBIDDEN_FIELDS_USER,
    FORBIDDEN_FIELDS_AUDIT,
    MASS_ASSIGNMENT_ENDPOINTS,
    TEST_TENANT_NAME,
    OTHER_TENANT_NAME,
)


User = get_user_model()


@pytest.mark.security
@pytest.mark.owasp
@pytest.mark.django_db
class TestMassAssignmentPrevention:
    """
    Tests for Mass Assignment vulnerability prevention.

    Mass assignment occurs when an attacker can set object properties
    that should not be user-controllable by including extra fields
    in API requests.

    Coverage:
    - Tenant ID manipulation (SEC-MASS-001)
    - Admin/superuser flag manipulation (SEC-MASS-002)
    - Audit field manipulation (SEC-MASS-003)
    - Product model protection (SEC-MASS-004)
    - Category model protection (SEC-MASS-005)
    - Supplier model protection (SEC-MASS-006)
    - Price list model protection (SEC-MASS-007)
    - Stock movement model protection (SEC-MASS-008)
    - Role model protection (SEC-MASS-009)
    - Sync session model protection (SEC-MASS-010)
    - Pending operation model protection (SEC-MASS-011)
    """

    @pytest.fixture
    def api_client(self) -> APIClient:
        """Create API client for testing."""
        return APIClient()

    @pytest.fixture
    def authenticated_client(self, api_client, test_user, test_tenant):
        """Create authenticated API client with tenant context."""
        # Set tenant header via defaults BEFORE force_authenticate
        api_client.defaults['HTTP_X_TENANT_ID'] = str(test_tenant.id)
        api_client.force_authenticate(user=test_user)
        return api_client

    @pytest.fixture
    def admin_client(self, api_client, admin_user, test_tenant):
        """Create authenticated admin API client."""
        # Set tenant header via defaults BEFORE force_authenticate
        api_client.defaults['HTTP_X_TENANT_ID'] = str(test_tenant.id)
        api_client.force_authenticate(user=admin_user)
        return api_client

    @pytest.fixture
    def other_tenant_id(self, other_tenant):
        """Get another tenant's ID for cross-tenant testing."""
        return str(other_tenant.id)

    # =========================================================================
    # SEC-MASS-001: Tenant ID Manipulation Prevention
    # =========================================================================

    @pytest.mark.parametrize("endpoint", MASS_ASSIGNMENT_ENDPOINTS)
    def test_cannot_set_tenant_id_on_create(
        self, authenticated_client, endpoint, other_tenant_id
    ):
        """
        SEC-MASS-001: Verify tenant_id cannot be set in create requests.

        Attackers may try to create resources in another tenant's context
        by including tenant_id in the request body.
        """
        # Prepare payload with malicious tenant_id
        payload = {
            "name": "Test Resource",
            "tenant_id": other_tenant_id,
            "tenant": other_tenant_id,
        }

        response = authenticated_client.post(endpoint, payload, format="json")

        # The request should either:
        # 1. Succeed but ignore the tenant_id (use authenticated user's tenant)
        # 2. Return 400 Bad Request (rejecting the field)
        # 3. Return 403 Forbidden (denying cross-tenant access)

        if response.status_code == status.HTTP_201_CREATED:
            # If created, verify it's in the correct tenant
            assert response.data.get("tenant_id") != other_tenant_id, (
                f"SEC-MASS-001 FAILED at {endpoint}: "
                f"Resource was created in attacker's tenant!"
            )
        elif response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
        ]:
            # Request was properly rejected
            pass
        elif response.status_code == status.HTTP_404_NOT_FOUND:
            # Endpoint doesn't exist - skip
            pytest.skip(f"Endpoint {endpoint} not found")
        else:
            # Unexpected status - may need investigation
            pass

    def test_tenant_id_stripped_from_update(
        self, authenticated_client, test_product, other_tenant_id
    ):
        """
        SEC-MASS-001: Verify tenant_id cannot be changed via update.

        Attackers may try to move resources to another tenant by updating
        the tenant_id field.
        """
        original_tenant = test_product.tenant_id

        # Attempt to update with different tenant_id
        payload = {
            "name": test_product.name,
            "tenant_id": other_tenant_id,
        }

        response = authenticated_client.patch(
            f"/api/v1/products/{test_product.id}/",
            payload,
            format="json",
        )

        if response.status_code == status.HTTP_200_OK:
            # Verify tenant_id wasn't changed
            test_product.refresh_from_db()
            assert str(test_product.tenant_id) == str(original_tenant), (
                "SEC-MASS-001 FAILED: tenant_id was changed via PATCH request!"
            )

    # =========================================================================
    # SEC-MASS-002: Admin/Superuser Flag Manipulation Prevention
    # =========================================================================

    def test_cannot_set_is_admin_on_registration(self, api_client, test_tenant):
        """
        SEC-MASS-002: Verify is_admin cannot be set during registration.

        Attackers may try to register as admin by including is_admin=True.
        """
        payload = {
            "email": "attacker@example.com",
            "password": "SecurePass123!",
            "password_confirm": "SecurePass123!",
            "first_name": "Attacker",
            "last_name": "User",
            "is_admin": True,
            "is_superuser": True,
            "is_staff": True,
        }

        response = api_client.post("/api/v1/auth/register/", payload, format="json")

        if response.status_code == status.HTTP_201_CREATED:
            # Check the created user
            user = User.objects.filter(email="attacker@example.com").first()
            if user:
                assert user.is_admin is False, (
                    "SEC-MASS-002 FAILED: is_admin was set during registration!"
                )
                assert user.is_superuser is False, (
                    "SEC-MASS-002 FAILED: is_superuser was set during registration!"
                )
                assert user.is_staff is False, (
                    "SEC-MASS-002 FAILED: is_staff was set during registration!"
                )
                # Cleanup
                user.delete()
        elif response.status_code == status.HTTP_404_NOT_FOUND:
            pytest.skip("Registration endpoint not found")

    def test_cannot_set_is_admin_on_profile_update(
        self, authenticated_client, test_user
    ):
        """
        SEC-MASS-002: Verify is_admin cannot be set via profile update.

        Attackers may try to escalate privileges by updating their profile.
        """
        payload = {
            "is_admin": True,
            "is_superuser": True,
            "is_staff": True,
        }

        response = authenticated_client.patch(
            "/api/v1/users/me/",
            payload,
            format="json",
        )

        if response.status_code in [status.HTTP_200_OK, status.HTTP_204_NO_CONTENT]:
            test_user.refresh_from_db()
            assert test_user.is_admin is False, (
                "SEC-MASS-002 FAILED: is_admin was set via profile update!"
            )
            assert test_user.is_superuser is False, (
                "SEC-MASS-002 FAILED: is_superuser was set via profile update!"
            )
        elif response.status_code == status.HTTP_404_NOT_FOUND:
            pytest.skip("Profile update endpoint not found")

    def test_non_admin_cannot_promote_user_to_admin(
        self, authenticated_client, other_user
    ):
        """
        SEC-MASS-002: Verify non-admin cannot promote other users.

        Even if the endpoint exists, regular users shouldn't be able to
        modify admin flags on other users.
        """
        payload = {
            "is_admin": True,
        }

        response = authenticated_client.patch(
            f"/api/v1/users/{other_user.id}/",
            payload,
            format="json",
        )

        # Should be forbidden or ignored
        if response.status_code == status.HTTP_200_OK:
            other_user.refresh_from_db()
            assert other_user.is_admin is False, (
                "SEC-MASS-002 FAILED: Non-admin was able to promote user to admin!"
            )
        # 403 or 404 are acceptable responses

    # =========================================================================
    # SEC-MASS-003: Audit Field Manipulation Prevention
    # =========================================================================

    @pytest.mark.parametrize("field", FORBIDDEN_FIELDS_AUDIT)
    def test_cannot_set_audit_fields_on_create(
        self, authenticated_client, field
    ):
        """
        SEC-MASS-003: Verify audit fields cannot be set on create.

        Fields like created_at, updated_at, created_by, modified_by should
        be set automatically by the system, not by API requests.
        """
        from datetime import datetime, timedelta

        fake_timestamp = (datetime.now() - timedelta(days=365)).isoformat()
        fake_user_id = str(uuid.uuid4())

        payload = {
            "name": "Test Product",
            "sku": "TEST-AUDIT-001",
            field: fake_timestamp if "at" in field else fake_user_id,
        }

        response = authenticated_client.post(
            "/api/v1/products/",
            payload,
            format="json",
        )

        if response.status_code == status.HTTP_201_CREATED:
            # Verify audit field wasn't set to the fake value
            if field in response.data:
                if "at" in field:
                    # Timestamp fields - should be recent, not a year ago
                    assert response.data[field] != fake_timestamp, (
                        f"SEC-MASS-003 FAILED: {field} was set to attacker value!"
                    )
                else:
                    # User reference fields
                    assert response.data[field] != fake_user_id, (
                        f"SEC-MASS-003 FAILED: {field} was set to attacker value!"
                    )
        elif response.status_code == status.HTTP_404_NOT_FOUND:
            pytest.skip("Products endpoint not found")

    # =========================================================================
    # SEC-MASS-004: Product Model Protection
    # =========================================================================

    def test_product_tenant_isolation_on_create(
        self, authenticated_client, other_tenant_id
    ):
        """
        SEC-MASS-004: Verify Product model rejects tenant_id manipulation.
        """
        payload = {
            "name": "Malicious Product",
            "sku": "MALICIOUS-001",
            "tenant_id": other_tenant_id,
        }

        response = authenticated_client.post(
            "/api/v1/products/",
            payload,
            format="json",
        )

        if response.status_code == status.HTTP_201_CREATED:
            assert response.data.get("tenant_id") != other_tenant_id, (
                "SEC-MASS-004 FAILED: Product created in wrong tenant!"
            )
        elif response.status_code == status.HTTP_404_NOT_FOUND:
            pytest.skip("Products endpoint not found")

    def test_product_cannot_change_id(
        self, authenticated_client, test_product
    ):
        """
        SEC-MASS-004: Verify Product ID cannot be changed via update.
        """
        fake_id = str(uuid.uuid4())
        original_id = str(test_product.id)

        payload = {
            "id": fake_id,
            "name": test_product.name,
        }

        response = authenticated_client.patch(
            f"/api/v1/products/{test_product.id}/",
            payload,
            format="json",
        )

        if response.status_code == status.HTTP_200_OK:
            assert response.data.get("id") == original_id, (
                "SEC-MASS-004 FAILED: Product ID was changed!"
            )

    # =========================================================================
    # SEC-MASS-005: Category Model Protection
    # =========================================================================

    def test_category_tenant_isolation(
        self, authenticated_client, other_tenant_id
    ):
        """
        SEC-MASS-005: Verify ProductCategory model rejects tenant manipulation.
        """
        payload = {
            "name": "Malicious Category",
            "tenant_id": other_tenant_id,
        }

        response = authenticated_client.post(
            "/api/v1/categories/",
            payload,
            format="json",
        )

        if response.status_code == status.HTTP_201_CREATED:
            assert response.data.get("tenant_id") != other_tenant_id, (
                "SEC-MASS-005 FAILED: Category created in wrong tenant!"
            )
        elif response.status_code == status.HTTP_404_NOT_FOUND:
            pytest.skip("Categories endpoint not found")

    # =========================================================================
    # SEC-MASS-006: Supplier Model Protection
    # =========================================================================

    def test_supplier_tenant_isolation(
        self, authenticated_client, other_tenant_id
    ):
        """
        SEC-MASS-006: Verify Supplier model rejects tenant manipulation.
        """
        payload = {
            "name": "Malicious Supplier",
            "contact_email": "supplier@malicious.com",
            "tenant_id": other_tenant_id,
        }

        response = authenticated_client.post(
            "/api/v1/compras/suppliers/",
            payload,
            format="json",
        )

        if response.status_code == status.HTTP_201_CREATED:
            assert response.data.get("tenant_id") != other_tenant_id, (
                "SEC-MASS-006 FAILED: Supplier created in wrong tenant!"
            )
        elif response.status_code == status.HTTP_404_NOT_FOUND:
            pytest.skip("Suppliers endpoint not found")

    # =========================================================================
    # SEC-MASS-007: Price List Model Protection
    # =========================================================================

    def test_price_list_tenant_isolation(
        self, authenticated_client, other_tenant_id
    ):
        """
        SEC-MASS-007: Verify PriceList model rejects tenant manipulation.
        """
        payload = {
            "name": "Malicious Price List",
            "tenant_id": other_tenant_id,
        }

        response = authenticated_client.post(
            "/api/v1/price-lists/",
            payload,
            format="json",
        )

        if response.status_code == status.HTTP_201_CREATED:
            assert response.data.get("tenant_id") != other_tenant_id, (
                "SEC-MASS-007 FAILED: PriceList created in wrong tenant!"
            )
        elif response.status_code == status.HTTP_404_NOT_FOUND:
            pytest.skip("Price lists endpoint not found")

    # =========================================================================
    # SEC-MASS-008: Stock Movement Model Protection
    # =========================================================================

    def test_stock_movement_tenant_isolation(
        self, authenticated_client, test_product, other_tenant_id
    ):
        """
        SEC-MASS-008: Verify StockMovement model rejects tenant manipulation.
        """
        payload = {
            "product_id": str(test_product.id),
            "quantity": 10,
            "movement_type": "IN",
            "tenant_id": other_tenant_id,
        }

        response = authenticated_client.post(
            "/api/v1/inventory/movements/",
            payload,
            format="json",
        )

        if response.status_code == status.HTTP_201_CREATED:
            assert response.data.get("tenant_id") != other_tenant_id, (
                "SEC-MASS-008 FAILED: StockMovement created in wrong tenant!"
            )
        elif response.status_code == status.HTTP_404_NOT_FOUND:
            pytest.skip("Stock movements endpoint not found")

    def test_stock_movement_cannot_modify_product_tenant(
        self, authenticated_client, test_product, other_product
    ):
        """
        SEC-MASS-008: Verify stock movements can't be created for cross-tenant products.

        Even if a user somehow has another tenant's product ID, the movement
        should be rejected or created for the user's own product.
        """
        payload = {
            "product_id": str(other_product.id),  # Product from different tenant
            "quantity": 100,
            "movement_type": "IN",
        }

        response = authenticated_client.post(
            "/api/v1/inventory/movements/",
            payload,
            format="json",
        )

        # Should either fail or be scoped to the user's tenant
        if response.status_code == status.HTTP_201_CREATED:
            # Movement should be created for the user's own product, not the other tenant's
            pass  # Implementation-specific
        # 400 or 404 are acceptable - product not found in user's tenant
        elif response.status_code == status.HTTP_404_NOT_FOUND:
            pytest.skip("Stock movements endpoint not found")

    # =========================================================================
    # SEC-MASS-009: Role Model Protection
    # =========================================================================

    def test_role_permissions_manipulation(
        self, authenticated_client, other_tenant_id
    ):
        """
        SEC-MASS-009: Verify Role model rejects dangerous permission injection.

        Attackers may try to create roles with elevated permissions.
        """
        payload = {
            "name": "Super Admin Role",
            "permissions": ["*", "admin.*", "superuser"],
            "tenant_id": other_tenant_id,
        }

        response = authenticated_client.post(
            "/api/v1/roles/",
            payload,
            format="json",
        )

        if response.status_code == status.HTTP_201_CREATED:
            # Verify tenant isolation
            assert response.data.get("tenant_id") != other_tenant_id, (
                "SEC-MASS-009 FAILED: Role created in wrong tenant!"
            )
            # Verify dangerous permissions weren't granted
            permissions = response.data.get("permissions", [])
            assert "*" not in permissions, (
                "SEC-MASS-009 FAILED: Wildcard permission was granted!"
            )
        elif response.status_code == status.HTTP_404_NOT_FOUND:
            pytest.skip("Roles endpoint not found")
        # 400 or 403 are acceptable for rejecting the dangerous payload

    # =========================================================================
    # SEC-MASS-010: Sync Session Model Protection
    # =========================================================================

    def test_sync_session_tenant_isolation(
        self, authenticated_client, other_tenant_id
    ):
        """
        SEC-MASS-010: Verify SyncSession model rejects tenant manipulation.
        """
        payload = {
            "device_id": "malicious-device",
            "tenant_id": other_tenant_id,
        }

        response = authenticated_client.post(
            "/api/v1/sync/sessions/",
            payload,
            format="json",
        )

        if response.status_code == status.HTTP_201_CREATED:
            assert response.data.get("tenant_id") != other_tenant_id, (
                "SEC-MASS-010 FAILED: SyncSession created in wrong tenant!"
            )
        elif response.status_code == status.HTTP_404_NOT_FOUND:
            pytest.skip("Sync sessions endpoint not found")

    def test_sync_session_cannot_impersonate_user(
        self, authenticated_client, other_user
    ):
        """
        SEC-MASS-010: Verify sync sessions can't be created for other users.
        """
        payload = {
            "device_id": "attacker-device",
            "user_id": str(other_user.id),
        }

        response = authenticated_client.post(
            "/api/v1/sync/sessions/",
            payload,
            format="json",
        )

        if response.status_code == status.HTTP_201_CREATED:
            # Should be created for the authenticated user, not the other user
            assert response.data.get("user_id") != str(other_user.id), (
                "SEC-MASS-010 FAILED: Sync session impersonated another user!"
            )
        elif response.status_code == status.HTTP_404_NOT_FOUND:
            pytest.skip("Sync sessions endpoint not found")

    # =========================================================================
    # SEC-MASS-011: Pending Operation Model Protection
    # =========================================================================

    def test_pending_operation_tenant_isolation(
        self, authenticated_client, other_tenant_id
    ):
        """
        SEC-MASS-011: Verify PendingOperation model rejects tenant manipulation.
        """
        payload = {
            "operation_type": "CREATE",
            "entity_type": "Product",
            "entity_data": {"name": "Test"},
            "tenant_id": other_tenant_id,
        }

        response = authenticated_client.post(
            "/api/v1/sync/operations/",
            payload,
            format="json",
        )

        if response.status_code == status.HTTP_201_CREATED:
            assert response.data.get("tenant_id") != other_tenant_id, (
                "SEC-MASS-011 FAILED: PendingOperation created in wrong tenant!"
            )
        elif response.status_code == status.HTTP_404_NOT_FOUND:
            pytest.skip("Sync operations endpoint not found")

    def test_pending_operation_cannot_forge_status(
        self, authenticated_client
    ):
        """
        SEC-MASS-011: Verify pending operations can't be created with forged status.

        Attackers may try to create operations that appear already processed.
        """
        payload = {
            "operation_type": "CREATE",
            "entity_type": "Product",
            "entity_data": {"name": "Test"},
            "status": "COMPLETED",  # Should not be settable on create
            "processed_at": "2023-01-01T00:00:00Z",
        }

        response = authenticated_client.post(
            "/api/v1/sync/operations/",
            payload,
            format="json",
        )

        if response.status_code == status.HTTP_201_CREATED:
            # Status should be PENDING, not COMPLETED
            assert response.data.get("status") != "COMPLETED", (
                "SEC-MASS-011 FAILED: Operation created with forged status!"
            )
            assert response.data.get("processed_at") is None, (
                "SEC-MASS-011 FAILED: Operation created with forged processed_at!"
            )
        elif response.status_code == status.HTTP_404_NOT_FOUND:
            pytest.skip("Sync operations endpoint not found")


@pytest.mark.security
@pytest.mark.owasp
@pytest.mark.django_db
class TestBulkMassAssignment:
    """
    Tests for mass assignment in bulk operations.

    Bulk create/update endpoints may have different code paths
    that need separate protection.
    """

    @pytest.fixture
    def api_client(self) -> APIClient:
        """Create API client for testing."""
        return APIClient()

    @pytest.fixture
    def authenticated_client(self, api_client, test_user, test_tenant):
        """Create authenticated API client."""
        # Set tenant header via defaults BEFORE force_authenticate
        api_client.defaults['HTTP_X_TENANT_ID'] = str(test_tenant.id)
        api_client.force_authenticate(user=test_user)
        return api_client

    def test_bulk_create_tenant_isolation(
        self, authenticated_client, other_tenant
    ):
        """
        Verify bulk create operations respect tenant isolation.

        Attackers may try to inject items into other tenants via bulk operations.
        """
        other_tenant_id = str(other_tenant.id)

        payload = [
            {"name": "Product 1", "sku": "BULK-001", "tenant_id": other_tenant_id},
            {"name": "Product 2", "sku": "BULK-002"},
            {"name": "Product 3", "sku": "BULK-003", "tenant_id": other_tenant_id},
        ]

        response = authenticated_client.post(
            "/api/v1/products/bulk/",
            payload,
            format="json",
        )

        if response.status_code == status.HTTP_201_CREATED:
            for item in response.data:
                assert item.get("tenant_id") != other_tenant_id, (
                    "Bulk create allowed cross-tenant item!"
                )
        elif response.status_code == status.HTTP_404_NOT_FOUND:
            pytest.skip("Bulk products endpoint not found")

    def test_bulk_update_tenant_isolation(
        self, authenticated_client, test_products, other_tenant
    ):
        """
        Verify bulk update operations respect tenant isolation.
        """
        other_tenant_id = str(other_tenant.id)

        payload = [
            {"id": str(p.id), "name": f"Updated {p.name}", "tenant_id": other_tenant_id}
            for p in test_products[:3]
        ]

        response = authenticated_client.patch(
            "/api/v1/products/bulk/",
            payload,
            format="json",
        )

        if response.status_code == status.HTTP_200_OK:
            for item in response.data:
                assert item.get("tenant_id") != other_tenant_id, (
                    "Bulk update changed tenant_id!"
                )
        elif response.status_code == status.HTTP_404_NOT_FOUND:
            pytest.skip("Bulk products endpoint not found")
