"""
Tenant Isolation Property Tests.

Tests for FR-021:
- FR-021: Tenant ID MUST be consistently applied across all data access operations

Uses Hypothesis for property-based testing to verify tenant isolation
properties hold across all valid input combinations.
"""

from decimal import Decimal
from typing import Dict, List, Set, Optional
from dataclasses import dataclass, field
from uuid import UUID
import uuid

import pytest
from hypothesis import given, assume, settings, example
from hypothesis import strategies as st

from tests.fixtures.property_strategies import (
    tenant_id,
    branch_id,
    tenant_resource_data,
    product_data,
    user_data,
)


@dataclass
class TenantResource:
    """Represents a resource owned by a tenant."""

    resource_id: UUID
    tenant_id: UUID
    branch_id: Optional[UUID]
    resource_type: str
    data: Dict = field(default_factory=dict)

    def belongs_to_tenant(self, check_tenant_id: UUID) -> bool:
        """Check if resource belongs to the given tenant."""
        return self.tenant_id == check_tenant_id

    def belongs_to_branch(self, check_branch_id: UUID) -> bool:
        """Check if resource belongs to the given branch."""
        return self.branch_id == check_branch_id


@dataclass
class TenantDataStore:
    """Simulates a multi-tenant data store."""

    resources: Dict[UUID, TenantResource] = field(default_factory=dict)

    def create(
        self,
        resource_id: UUID,
        tenant_id: UUID,
        branch_id: Optional[UUID],
        resource_type: str,
        data: Dict
    ) -> TenantResource:
        """Create a new tenant-scoped resource."""
        resource = TenantResource(
            resource_id=resource_id,
            tenant_id=tenant_id,
            branch_id=branch_id,
            resource_type=resource_type,
            data=data,
        )
        self.resources[resource_id] = resource
        return resource

    def get(
        self,
        resource_id: UUID,
        requesting_tenant_id: UUID
    ) -> Optional[TenantResource]:
        """
        Get a resource by ID, but only if it belongs to the requesting tenant.

        Enforces tenant isolation at the data access layer.
        """
        resource = self.resources.get(resource_id)
        if resource and resource.belongs_to_tenant(requesting_tenant_id):
            return resource
        return None

    def list_for_tenant(self, tenant_id: UUID) -> List[TenantResource]:
        """List all resources belonging to a tenant."""
        return [r for r in self.resources.values() if r.belongs_to_tenant(tenant_id)]

    def list_for_branch(
        self,
        tenant_id: UUID,
        branch_id: UUID
    ) -> List[TenantResource]:
        """List all resources belonging to a specific branch within a tenant."""
        return [
            r for r in self.resources.values()
            if r.belongs_to_tenant(tenant_id) and r.belongs_to_branch(branch_id)
        ]

    def update(
        self,
        resource_id: UUID,
        requesting_tenant_id: UUID,
        new_data: Dict
    ) -> bool:
        """
        Update a resource, enforcing tenant isolation.

        Returns True if update succeeded, False if resource not found or unauthorized.
        """
        resource = self.get(resource_id, requesting_tenant_id)
        if resource:
            resource.data.update(new_data)
            return True
        return False

    def delete(
        self,
        resource_id: UUID,
        requesting_tenant_id: UUID
    ) -> bool:
        """
        Delete a resource, enforcing tenant isolation.

        Returns True if delete succeeded, False if resource not found or unauthorized.
        """
        resource = self.get(resource_id, requesting_tenant_id)
        if resource:
            del self.resources[resource_id]
            return True
        return False


def create_tenant_jwt_claims(
    tenant_id: UUID,
    branch_id: Optional[UUID] = None,
    user_id: Optional[UUID] = None
) -> Dict:
    """Create JWT claims structure for a tenant user."""
    claims = {
        "sub": str(user_id or uuid.uuid4()),
        "tenant_id": str(tenant_id),
        "iat": 1700000000,
        "exp": 1700003600,
    }
    if branch_id:
        claims["branch_id"] = str(branch_id)
    return claims


def validate_tenant_access(
    resource_tenant_id: UUID,
    requesting_tenant_id: UUID
) -> bool:
    """Validate that a tenant can access a resource."""
    return resource_tenant_id == requesting_tenant_id


@pytest.mark.property
class TestTenantIsolationInvariants:
    """
    FR-021: Tenant ID MUST be consistently applied across all data access operations.

    Property-based tests for tenant isolation invariants.
    """

    @given(
        owner_tenant=tenant_id,
        other_tenant=tenant_id
    )
    @settings(max_examples=100)
    def test_different_tenants_cannot_access_each_others_resources(
        self,
        owner_tenant: UUID,
        other_tenant: UUID
    ):
        """
        Property: Resources owned by tenant A are never accessible to tenant B.
        """
        assume(owner_tenant != other_tenant)

        store = TenantDataStore()
        resource_id = uuid.uuid4()

        # Tenant A creates a resource
        store.create(
            resource_id=resource_id,
            tenant_id=owner_tenant,
            branch_id=None,
            resource_type="product",
            data={"name": "Test Product"}
        )

        # Tenant B tries to access it
        result = store.get(resource_id, other_tenant)

        assert result is None, (
            f"Tenant {other_tenant} accessed resource owned by {owner_tenant}"
        )

    @given(
        owner_tenant=tenant_id,
        other_tenant=tenant_id
    )
    @settings(max_examples=100)
    def test_tenant_can_always_access_own_resources(
        self,
        owner_tenant: UUID,
        other_tenant: UUID
    ):
        """
        Property: A tenant can always access their own resources.
        """
        store = TenantDataStore()
        resource_id = uuid.uuid4()

        # Tenant creates a resource
        store.create(
            resource_id=resource_id,
            tenant_id=owner_tenant,
            branch_id=None,
            resource_type="product",
            data={"name": "Test Product"}
        )

        # Same tenant can access it
        result = store.get(resource_id, owner_tenant)

        assert result is not None, (
            f"Tenant {owner_tenant} cannot access their own resource"
        )
        assert result.tenant_id == owner_tenant

    @given(
        owner_tenant=tenant_id,
        other_tenant=tenant_id,
        new_data=st.fixed_dictionaries({
            "name": st.text(min_size=1, max_size=50),
        })
    )
    @settings(max_examples=100)
    def test_tenant_cannot_update_other_tenant_resources(
        self,
        owner_tenant: UUID,
        other_tenant: UUID,
        new_data: Dict
    ):
        """
        Property: Tenant cannot update resources belonging to another tenant.
        """
        assume(owner_tenant != other_tenant)

        store = TenantDataStore()
        resource_id = uuid.uuid4()

        # Tenant A creates resource
        store.create(
            resource_id=resource_id,
            tenant_id=owner_tenant,
            branch_id=None,
            resource_type="product",
            data={"name": "Original"}
        )

        # Tenant B tries to update
        success = store.update(resource_id, other_tenant, new_data)

        assert not success, (
            f"Tenant {other_tenant} was able to update resource owned by {owner_tenant}"
        )

        # Verify data unchanged
        original = store.get(resource_id, owner_tenant)
        assert original.data["name"] == "Original"

    @given(
        owner_tenant=tenant_id,
        other_tenant=tenant_id
    )
    @settings(max_examples=100)
    def test_tenant_cannot_delete_other_tenant_resources(
        self,
        owner_tenant: UUID,
        other_tenant: UUID
    ):
        """
        Property: Tenant cannot delete resources belonging to another tenant.
        """
        assume(owner_tenant != other_tenant)

        store = TenantDataStore()
        resource_id = uuid.uuid4()

        # Tenant A creates resource
        store.create(
            resource_id=resource_id,
            tenant_id=owner_tenant,
            branch_id=None,
            resource_type="product",
            data={"name": "Test"}
        )

        # Tenant B tries to delete
        success = store.delete(resource_id, other_tenant)

        assert not success, (
            f"Tenant {other_tenant} was able to delete resource owned by {owner_tenant}"
        )

        # Verify resource still exists
        original = store.get(resource_id, owner_tenant)
        assert original is not None


@pytest.mark.property
class TestTenantListingIsolation:
    """
    Test that listing operations are properly tenant-scoped.
    """

    @given(
        tenant_a=tenant_id,
        tenant_b=tenant_id,
        num_resources=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=50)
    def test_list_returns_only_own_resources(
        self,
        tenant_a: UUID,
        tenant_b: UUID,
        num_resources: int
    ):
        """
        Property: Listing returns only resources belonging to requesting tenant.
        """
        assume(tenant_a != tenant_b)

        store = TenantDataStore()

        # Create resources for both tenants
        for i in range(num_resources):
            store.create(
                resource_id=uuid.uuid4(),
                tenant_id=tenant_a,
                branch_id=None,
                resource_type="product",
                data={"index": i}
            )
            store.create(
                resource_id=uuid.uuid4(),
                tenant_id=tenant_b,
                branch_id=None,
                resource_type="product",
                data={"index": i}
            )

        # List for tenant A
        tenant_a_resources = store.list_for_tenant(tenant_a)

        # Should only see own resources
        assert len(tenant_a_resources) == num_resources
        for resource in tenant_a_resources:
            assert resource.tenant_id == tenant_a, (
                f"Tenant A listing contains resource from tenant {resource.tenant_id}"
            )

    @given(
        tenant=tenant_id,
        branch_a=branch_id,
        branch_b=branch_id,
        num_resources=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=50)
    def test_branch_listing_within_tenant(
        self,
        tenant: UUID,
        branch_a: UUID,
        branch_b: UUID,
        num_resources: int
    ):
        """
        Property: Branch listing returns only resources from that branch.
        """
        assume(branch_a != branch_b)

        store = TenantDataStore()

        # Create resources for both branches
        for i in range(num_resources):
            store.create(
                resource_id=uuid.uuid4(),
                tenant_id=tenant,
                branch_id=branch_a,
                resource_type="product",
                data={"branch": "A", "index": i}
            )
            store.create(
                resource_id=uuid.uuid4(),
                tenant_id=tenant,
                branch_id=branch_b,
                resource_type="product",
                data={"branch": "B", "index": i}
            )

        # List for branch A
        branch_a_resources = store.list_for_branch(tenant, branch_a)

        # Should only see branch A resources
        assert len(branch_a_resources) == num_resources
        for resource in branch_a_resources:
            assert resource.branch_id == branch_a, (
                f"Branch A listing contains resource from branch {resource.branch_id}"
            )


@pytest.mark.property
class TestTenantIDConsistency:
    """
    Test that tenant ID is consistently applied.
    """

    @given(tenant_resource_data())
    @settings(max_examples=100)
    def test_resource_always_has_tenant_id(self, resource_data: Dict):
        """
        Property: Every resource always has a tenant_id assigned.
        """
        assert "tenant_id" in resource_data
        assert resource_data["tenant_id"] is not None
        assert isinstance(resource_data["tenant_id"], UUID)

    @given(
        tenant=tenant_id,
        resource_ids=st.lists(st.uuids(), min_size=1, max_size=10)
    )
    @settings(max_examples=50)
    def test_all_created_resources_have_same_tenant(
        self,
        tenant: UUID,
        resource_ids: List[UUID]
    ):
        """
        Property: All resources created in a tenant context have the same tenant_id.
        """
        store = TenantDataStore()

        # Create multiple resources
        for rid in resource_ids:
            store.create(
                resource_id=rid,
                tenant_id=tenant,
                branch_id=None,
                resource_type="product",
                data={}
            )

        # Verify all have same tenant
        all_resources = store.list_for_tenant(tenant)
        tenant_ids = {r.tenant_id for r in all_resources}

        assert len(tenant_ids) == 1, (
            f"Found multiple tenant IDs: {tenant_ids}"
        )
        assert tenant in tenant_ids

    @given(
        tenant=tenant_id,
        other_tenant=tenant_id
    )
    @settings(max_examples=100)
    def test_tenant_id_immutable_on_resource(
        self,
        tenant: UUID,
        other_tenant: UUID
    ):
        """
        Property: Resource tenant_id cannot be changed after creation.
        """
        assume(tenant != other_tenant)

        store = TenantDataStore()
        resource_id = uuid.uuid4()

        # Create resource
        resource = store.create(
            resource_id=resource_id,
            tenant_id=tenant,
            branch_id=None,
            resource_type="product",
            data={"name": "Test"}
        )

        # Attempt to update tenant_id via data (shouldn't work)
        store.update(resource_id, tenant, {"tenant_id": str(other_tenant)})

        # Fetch and verify tenant_id unchanged
        fetched = store.get(resource_id, tenant)
        assert fetched.tenant_id == tenant, (
            f"Tenant ID was mutated from {tenant} to {fetched.tenant_id}"
        )


@pytest.mark.property
class TestJWTClaimsConsistency:
    """
    Test JWT claims consistency for tenant context.
    """

    @given(
        tenant=tenant_id,
        branch=st.one_of(st.none(), branch_id),
        user=st.uuids()
    )
    @settings(max_examples=100)
    def test_jwt_claims_contain_tenant_id(
        self,
        tenant: UUID,
        branch: Optional[UUID],
        user: UUID
    ):
        """
        Property: JWT claims always contain tenant_id.
        """
        claims = create_tenant_jwt_claims(tenant, branch, user)

        assert "tenant_id" in claims
        assert claims["tenant_id"] == str(tenant)

    @given(
        tenant=tenant_id,
        branch=branch_id
    )
    @settings(max_examples=100)
    def test_jwt_claims_branch_consistent_with_tenant(
        self,
        tenant: UUID,
        branch: UUID
    ):
        """
        Property: When branch_id is in JWT, tenant_id is also present.
        """
        claims = create_tenant_jwt_claims(tenant, branch)

        if "branch_id" in claims:
            assert "tenant_id" in claims, (
                "branch_id present without tenant_id"
            )

    @given(
        tenant1=tenant_id,
        tenant2=tenant_id
    )
    @settings(max_examples=100)
    def test_access_validation_symmetric_for_same_tenant(
        self,
        tenant1: UUID,
        tenant2: UUID
    ):
        """
        Property: Access validation is symmetric for matching tenants.
        """
        result1 = validate_tenant_access(tenant1, tenant2)
        result2 = validate_tenant_access(tenant2, tenant1)

        # If tenants are same, both should be True
        # If different, both should be False
        if tenant1 == tenant2:
            assert result1 and result2
        else:
            assert not result1 and not result2


@pytest.mark.property
class TestCrossTenantDataLeak:
    """
    Test for potential cross-tenant data leaks.
    """

    @given(
        tenants=st.lists(tenant_id, min_size=2, max_size=5, unique=True),
        resource_count=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=50)
    def test_no_cross_tenant_data_in_listings(
        self,
        tenants: List[UUID],
        resource_count: int
    ):
        """
        Property: Listing for one tenant never contains other tenant's data.
        """
        store = TenantDataStore()

        # Create resources for each tenant
        all_resources = {}
        for tenant in tenants:
            all_resources[tenant] = []
            for i in range(resource_count):
                rid = uuid.uuid4()
                store.create(
                    resource_id=rid,
                    tenant_id=tenant,
                    branch_id=None,
                    resource_type="product",
                    data={"tenant": str(tenant), "index": i}
                )
                all_resources[tenant].append(rid)

        # Verify each tenant's listing
        for tenant in tenants:
            listing = store.list_for_tenant(tenant)
            listed_ids = {r.resource_id for r in listing}

            # Should contain all own resources
            expected_ids = set(all_resources[tenant])
            assert listed_ids == expected_ids, (
                f"Tenant {tenant} listing mismatch"
            )

            # Should not contain any other tenant's resources
            for other_tenant, other_ids in all_resources.items():
                if other_tenant != tenant:
                    overlap = listed_ids & set(other_ids)
                    assert not overlap, (
                        f"Tenant {tenant} listing contains {overlap} from {other_tenant}"
                    )

    @given(
        owner_tenant=tenant_id,
        attacker_tenant=tenant_id,
        guessed_ids=st.lists(st.uuids(), min_size=1, max_size=10)
    )
    @settings(max_examples=50)
    def test_no_access_by_id_guessing(
        self,
        owner_tenant: UUID,
        attacker_tenant: UUID,
        guessed_ids: List[UUID]
    ):
        """
        Property: Attacker cannot access resources by guessing IDs.
        """
        assume(owner_tenant != attacker_tenant)

        store = TenantDataStore()

        # Create resources for owner
        actual_ids = []
        for i in range(5):
            rid = uuid.uuid4()
            store.create(
                resource_id=rid,
                tenant_id=owner_tenant,
                branch_id=None,
                resource_type="product",
                data={"secret": "data"}
            )
            actual_ids.append(rid)

        # Attacker tries to access by guessing IDs (including actual IDs)
        all_attempts = guessed_ids + actual_ids

        for rid in all_attempts:
            result = store.get(rid, attacker_tenant)
            if result is not None:
                # If attacker got something, it must be their own resource
                assert result.tenant_id == attacker_tenant, (
                    f"Attacker {attacker_tenant} accessed resource of {result.tenant_id}"
                )


@pytest.mark.property
class TestMultiTenantOperations:
    """
    Test operations across multiple tenants.
    """

    @given(
        tenants=st.lists(tenant_id, min_size=2, max_size=5, unique=True)
    )
    @settings(max_examples=50)
    def test_total_resource_count_equals_sum_of_tenant_counts(
        self,
        tenants: List[UUID]
    ):
        """
        Property: Total resources equals sum of per-tenant resources.
        """
        store = TenantDataStore()

        # Create varying resources per tenant
        for i, tenant in enumerate(tenants):
            for j in range(i + 1):  # Varying count per tenant
                store.create(
                    resource_id=uuid.uuid4(),
                    tenant_id=tenant,
                    branch_id=None,
                    resource_type="product",
                    data={}
                )

        # Count per tenant
        tenant_counts = {}
        for tenant in tenants:
            tenant_counts[tenant] = len(store.list_for_tenant(tenant))

        # Verify total
        total_from_listings = sum(tenant_counts.values())
        total_in_store = len(store.resources)

        assert total_from_listings == total_in_store, (
            f"Count mismatch: listings={total_from_listings}, store={total_in_store}"
        )
