"""
Tests for tenant isolation.

Tests that tenant-bound models properly isolate data between tenants.
"""


import pytest

from apps.auth.models import Role
from apps.core.managers.tenant_bound import (clear_current_tenant_id,
                                             get_current_tenant_id,
                                             set_current_tenant_id)
from apps.core.models import Branch

pytestmark = pytest.mark.django_db


class TestTenantContext:
    """Tests for tenant context management."""

    def test_set_and_get_tenant_id(self, tenant):
        """Test setting and getting tenant ID."""
        set_current_tenant_id(tenant.id)

        assert get_current_tenant_id() == tenant.id

        clear_current_tenant_id()

    def test_clear_tenant_id(self, tenant):
        """Test clearing tenant ID."""
        set_current_tenant_id(tenant.id)
        clear_current_tenant_id()

        assert get_current_tenant_id() is None

    def test_no_tenant_context(self):
        """Test that no tenant context is set by default."""
        clear_current_tenant_id()

        assert get_current_tenant_id() is None


class TestTenantBoundManager:
    """Tests for TenantBoundManager."""

    def test_queryset_filters_by_tenant(self, tenant, other_tenant):
        """Test that queryset only returns objects from current tenant."""
        # Create branch in tenant A (set context to avoid validation errors)
        set_current_tenant_id(tenant.id)
        Branch.objects.create(
            tenant=tenant,
            name="Tenant A Branch",
            is_active=True,
        )
        clear_current_tenant_id()

        # Create branch in tenant B (set context to avoid validation errors)
        set_current_tenant_id(other_tenant.id)
        Branch.objects.create(
            tenant=other_tenant,
            name="Tenant B Branch",
            is_active=True,
        )
        clear_current_tenant_id()

        # Set context to tenant A for querying
        set_current_tenant_id(tenant.id)

        branches = Branch.objects.all()

        assert all(b.tenant_id == tenant.id for b in branches)
        assert "Tenant A Branch" in [b.name for b in branches]
        assert "Tenant B Branch" not in [b.name for b in branches]

        clear_current_tenant_id()

    def test_queryset_raises_without_context(self):
        """Test that queryset raises error without tenant context."""
        clear_current_tenant_id()

        with pytest.raises(ValueError) as exc_info:
            list(Branch.objects.all())

        assert "Tenant context not set" in str(exc_info.value)

    def test_all_objects_manager_bypasses_filter(self, tenant, other_tenant):
        """Test that all_objects manager returns all objects."""
        # Create branch in tenant A
        set_current_tenant_id(tenant.id)
        Branch.objects.create(
            tenant=tenant,
            name="Tenant A Branch",
            is_active=True,
        )
        clear_current_tenant_id()

        # Create branch in tenant B
        set_current_tenant_id(other_tenant.id)
        Branch.objects.create(
            tenant=other_tenant,
            name="Tenant B Branch",
            is_active=True,
        )
        clear_current_tenant_id()

        # all_objects should return both regardless of context
        branches = Branch.all_objects.all()

        names = [b.name for b in branches]
        assert "Tenant A Branch" in names
        assert "Tenant B Branch" in names


class TestTenantBoundModel:
    """Tests for TenantBoundModel mixin."""

    def test_idor_prevention_on_save(self, tenant, other_tenant, tenant_context):
        """Test that IDOR is prevented when saving with cross-tenant FK."""
        # Create a role in a different tenant
        other_role = Role.objects.create(
            tenant=other_tenant,
            name="Other Role",
            permissions=["inventory.read"],
        )

        # Try to create a user with the other tenant's role
        from django.contrib.auth import get_user_model

        User = get_user_model()

        with pytest.raises(ValueError) as exc_info:
            User.objects.create_user(
                email="test@test.com",
                tenant=tenant,
                password="TestPassword123!",
                role=other_role,  # Cross-tenant reference
            )

        assert "IDOR violation" in str(exc_info.value)


class TestRoleTenantIsolation:
    """Tests for Role model tenant isolation."""

    def test_role_unique_per_tenant(self, tenant, other_tenant):
        """Test that role names are unique only within a tenant."""
        # Create role in tenant A
        set_current_tenant_id(tenant.id)
        Role.objects.create(
            tenant=tenant,
            name="Admin",
            permissions=["inventory.read"],
        )
        clear_current_tenant_id()

        # Same name in tenant B should work
        set_current_tenant_id(other_tenant.id)
        role_b = Role.objects.create(
            tenant=other_tenant,
            name="Admin",
            permissions=["inventory.read"],
        )
        clear_current_tenant_id()

        assert role_b.name == "Admin"

    def test_role_duplicate_in_same_tenant(self, tenant):
        """Test that duplicate role names in same tenant fail."""
        set_current_tenant_id(tenant.id)
        Role.objects.create(
            tenant=tenant,
            name="Duplicate",
            permissions=["inventory.read"],
        )

        # ValidationError is raised during full_clean() before hitting the database
        from django.core.exceptions import ValidationError

        with pytest.raises(ValidationError):
            Role.objects.create(
                tenant=tenant,
                name="Duplicate",
                permissions=["inventory.write"],
            )
        clear_current_tenant_id()


class TestBranchTenantIsolation:
    """Tests for Branch model tenant isolation."""

    def test_branch_filtered_by_tenant(self, tenant, other_tenant):
        """Test that branches are filtered by current tenant."""
        # Create branch in tenant A
        set_current_tenant_id(tenant.id)
        branch_a = Branch.objects.create(
            tenant=tenant,
            name="Branch A",
            is_active=True,
        )
        clear_current_tenant_id()

        # Create branch in tenant B
        set_current_tenant_id(other_tenant.id)
        Branch.objects.create(
            tenant=other_tenant,
            name="Branch B",
            is_active=True,
        )
        clear_current_tenant_id()

        # Query with tenant A context
        set_current_tenant_id(tenant.id)
        branches = Branch.objects.all()

        assert len(branches) == 1
        assert branches[0].id == branch_a.id

        clear_current_tenant_id()
