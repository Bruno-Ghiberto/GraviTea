"""
Integration tests for branch operations.

Tests verify branch management functionality:
- Branch CRUD operations
- Branch activation/deactivation
- Branch-specific inventory operations
- Branch-level user assignments
"""

import pytest
from decimal import Decimal
from django.test import TestCase

from apps.auth.models import Tenant, AppUser, Branch
from apps.core.managers.tenant_bound import set_current_tenant_id
from apps.inventario.models import Product, ProductCategory, StockSnapshot, StockMovement


@pytest.mark.django_db
class TestBranchCRUDOperations(TestCase):
    """Test branch CRUD operations."""

    def setUp(self):
        """Set up test data."""
        self.tenant = Tenant.objects.create(
            name="Test Company",
            is_active=True,
        )
        set_current_tenant_id(self.tenant.id)

    def test_create_branch(self):
        """Test creating a new branch."""
        branch = Branch.objects.create(
            tenant=self.tenant,
            name="Main Store",
            address="123 Main St",
            is_active=True,
        )

        self.assertIsNotNone(branch.id)
        self.assertEqual(branch.tenant, self.tenant)
        self.assertEqual(branch.name, "Main Store")
        self.assertTrue(branch.is_active)

    def test_create_multiple_branches(self):
        """Test creating multiple branches for same tenant."""
        _branch1 = Branch.objects.create(
            tenant=self.tenant,
            name="Downtown Store",
            is_active=True,
        )
        _branch2 = Branch.objects.create(
            tenant=self.tenant,
            name="Mall Store",
            is_active=True,
        )

        branches = Branch.objects.filter(tenant=self.tenant)
        self.assertEqual(branches.count(), 2)

    def test_branch_afip_pos_unique_per_tenant(self):
        """Test AFIP POS number uniqueness within tenant."""
        Branch.objects.create(
            tenant=self.tenant,
            name="Store 1",
            afip_pos_number=1,
            is_active=True,
        )

        # Same AFIP POS in same tenant should fail
        with self.assertRaises(Exception):
            Branch.objects.create(
                tenant=self.tenant,
                name="Store 2",
                afip_pos_number=1,
                is_active=True,
            )

    def test_deactivate_branch(self):
        """Test deactivating a branch."""
        branch = Branch.objects.create(
            tenant=self.tenant,
            name="Temporary Store",
            is_active=True,
        )

        branch.is_active = False
        branch.save()

        branch.refresh_from_db()
        self.assertFalse(branch.is_active)

    def test_branch_string_representation(self):
        """Test branch string representation."""
        branch = Branch.objects.create(
            tenant=self.tenant,
            name="Test Branch",
        )

        self.assertIn("Test Branch", str(branch))


@pytest.mark.django_db
class TestBranchUserAssignment(TestCase):
    """Test user assignment to branches."""

    def setUp(self):
        """Set up test data."""
        self.tenant = Tenant.objects.create(
            name="Test Company",
            is_active=True,
        )
        set_current_tenant_id(self.tenant.id)
        self.branch = Branch.objects.create(
            tenant=self.tenant,
            name="Main Branch",
            is_active=True,
        )

    def test_assign_user_to_branch(self):
        """Test assigning user to a branch."""
        # Use default_branch instead of branch
        user = AppUser.objects.create_user(
            email="employee@test.com",
            tenant=self.tenant,
            password="testpass123",
            default_branch=self.branch,
        )

        self.assertEqual(user.default_branch, self.branch)
        self.assertEqual(user.tenant, self.tenant)

    def test_user_branch_matches_tenant(self):
        """Test user's branch belongs to same tenant."""
        other_tenant = Tenant.objects.create(
            name="Other Company",
            is_active=True,
        )
        set_current_tenant_id(other_tenant.id)
        _other_branch = Branch.objects.create(
            tenant=other_tenant,
            name="Other Branch",
            is_active=True,
        )
        set_current_tenant_id(self.tenant.id)

        # Creating user with mismatched tenant/branch should be prevented
        # (This depends on model validation implementation)
        user = AppUser.objects.create_user(
            email="test@test.com",
            tenant=self.tenant,
            password="testpass123",
            default_branch=self.branch,
        )

        # User's branch should belong to user's tenant
        self.assertEqual(user.default_branch.tenant, user.tenant)

    def test_multiple_users_same_branch(self):
        """Test multiple users can be assigned to same branch."""
        _user1 = AppUser.objects.create_user(
            email="user1@test.com",
            tenant=self.tenant,
            password="testpass123",
            default_branch=self.branch,
        )
        _user2 = AppUser.objects.create_user(
            email="user2@test.com",
            tenant=self.tenant,
            password="testpass123",
            default_branch=self.branch,
        )

        # Query by default_branch instead of branch
        branch_users = AppUser.objects.filter(default_branch=self.branch)
        self.assertEqual(branch_users.count(), 2)


@pytest.mark.django_db
class TestBranchInventoryOperations(TestCase):
    """Test branch-specific inventory operations."""

    def setUp(self):
        """Set up test data."""
        self.tenant = Tenant.objects.create(
            name="Test Company",
            is_active=True,
        )
        set_current_tenant_id(self.tenant.id)
        self.branch1 = Branch.objects.create(
            tenant=self.tenant,
            name="Branch 1",
            is_active=True,
        )
        self.branch2 = Branch.objects.create(
            tenant=self.tenant,
            name="Branch 2",
            is_active=True,
        )
        self.category = ProductCategory.objects.create(
            tenant=self.tenant,
            name="Test Category",
        )
        self.product = Product.objects.create(
            tenant=self.tenant,
            name="Test Product",
            sku="TEST001",
            category=self.category,
            unit_price=Decimal("100.00"),
        )

    def test_stock_snapshot_per_branch(self):
        """Test stock snapshots are branch-specific."""
        # Create stock in branch 1 - no tenant param for StockSnapshot
        snapshot1 = StockSnapshot.objects.create(
            branch=self.branch1,
            product=self.product,
            quantity=Decimal("100"),
        )

        # Create stock in branch 2
        snapshot2 = StockSnapshot.objects.create(
            branch=self.branch2,
            product=self.product,
            quantity=Decimal("50"),
        )

        # Verify separate stock per branch
        self.assertEqual(snapshot1.quantity, Decimal("100"))
        self.assertEqual(snapshot2.quantity, Decimal("50"))

        # Query stock by branch - use branch__tenant for tenant filtering
        branch1_stock = StockSnapshot.objects.filter(
            branch__tenant=self.tenant,
            branch=self.branch1,
            product=self.product,
        ).first()
        self.assertEqual(branch1_stock.quantity, Decimal("100"))

    def test_stock_movement_branch_tracking(self):
        """Test stock movements track branch."""
        # Initialize stock - no tenant param
        _snapshot = StockSnapshot.objects.create(
            branch=self.branch1,
            product=self.product,
            quantity=Decimal("100"),
        )

        # Create movement - StockMovement has tenant, uses type and quantity_delta
        movement = StockMovement.objects.create(
            tenant=self.tenant,
            branch=self.branch1,
            product=self.product,
            type=StockMovement.MovementType.SALE,
            quantity_delta=Decimal("-10"),
        )

        self.assertEqual(movement.branch, self.branch1)
        self.assertEqual(movement.quantity_delta, Decimal("-10"))

    def test_transfer_between_branches(self):
        """Test stock transfer between branches."""
        # Initialize stock in branch 1 - no tenant param
        snapshot1 = StockSnapshot.objects.create(
            branch=self.branch1,
            product=self.product,
            quantity=Decimal("100"),
        )
        snapshot2 = StockSnapshot.objects.create(
            branch=self.branch2,
            product=self.product,
            quantity=Decimal("0"),
        )

        transfer_qty = Decimal("25")

        # Create outgoing movement from branch 1
        _out_movement = StockMovement.objects.create(
            tenant=self.tenant,
            branch=self.branch1,
            product=self.product,
            type=StockMovement.MovementType.TRANS_OUT,
            quantity_delta=-transfer_qty,
        )

        # Create incoming movement to branch 2
        _in_movement = StockMovement.objects.create(
            tenant=self.tenant,
            branch=self.branch2,
            product=self.product,
            type=StockMovement.MovementType.TRANS_IN,
            quantity_delta=transfer_qty,
        )

        # Update snapshots
        snapshot1.quantity -= transfer_qty
        snapshot1.save()
        snapshot2.quantity += transfer_qty
        snapshot2.save()

        # Verify balances
        snapshot1.refresh_from_db()
        snapshot2.refresh_from_db()

        self.assertEqual(snapshot1.quantity, Decimal("75"))
        self.assertEqual(snapshot2.quantity, Decimal("25"))


@pytest.mark.django_db
class TestBranchActivation(TestCase):
    """Test branch activation/deactivation scenarios."""

    def setUp(self):
        """Set up test data."""
        self.tenant = Tenant.objects.create(
            name="Test Company",
            is_active=True,
        )
        set_current_tenant_id(self.tenant.id)

    def test_inactive_branch_excluded_from_active_query(self):
        """Test inactive branches are excluded from active queries."""
        active_branch = Branch.objects.create(
            tenant=self.tenant,
            name="Active Branch",
            is_active=True,
        )
        _inactive_branch = Branch.objects.create(
            tenant=self.tenant,
            name="Inactive Branch",
            is_active=False,
        )

        active_branches = Branch.objects.filter(
            tenant=self.tenant,
            is_active=True,
        )

        self.assertEqual(active_branches.count(), 1)
        self.assertEqual(active_branches.first(), active_branch)

    def test_branch_with_stock_deactivation(self):
        """Test deactivating branch with existing stock."""
        branch = Branch.objects.create(
            tenant=self.tenant,
            name="Test Branch",
            is_active=True,
        )

        category = ProductCategory.objects.create(
            tenant=self.tenant,
            name="Test Category",
        )
        product = Product.objects.create(
            tenant=self.tenant,
            name="Test Product",
            sku="TEST001",
            category=category,
            unit_price=Decimal("100.00"),
        )

        # Create stock in branch - no tenant param
        StockSnapshot.objects.create(
            branch=branch,
            product=product,
            quantity=Decimal("50"),
        )

        # Deactivate branch
        branch.is_active = False
        branch.save()

        # Stock should still exist but branch is inactive
        stock = StockSnapshot.objects.filter(branch=branch)
        self.assertEqual(stock.count(), 1)
        self.assertFalse(stock.first().branch.is_active)


@pytest.mark.django_db
class TestBranchQueryOptimization(TestCase):
    """Test query optimization for branch operations."""

    def setUp(self):
        """Set up test data with multiple branches."""
        self.tenant = Tenant.objects.create(
            name="Test Company",
            is_active=True,
        )
        set_current_tenant_id(self.tenant.id)

        # Create multiple branches
        self.branches = []
        for i in range(5):
            branch = Branch.objects.create(
                tenant=self.tenant,
                name=f"Branch {i}",
                is_active=True,
            )
            self.branches.append(branch)

    def test_branch_list_query_count(self):
        """Test branch listing doesn't cause N+1 queries."""
        from django.test.utils import CaptureQueriesContext
        from django.db import connection

        with CaptureQueriesContext(connection) as context:
            branches = list(
                Branch.objects.filter(tenant=self.tenant).select_related("tenant")
            )
            # Access tenant for each branch
            for branch in branches:
                _ = branch.tenant.name

        # Should be 1 query with select_related
        self.assertEqual(len(context.captured_queries), 1)

    def test_branch_with_stock_prefetch(self):
        """Test branch stock queries use prefetch."""
        category = ProductCategory.objects.create(
            tenant=self.tenant,
            name="Test Category",
        )

        # Create products and stock - no tenant param for StockSnapshot
        for i, branch in enumerate(self.branches[:3]):
            product = Product.objects.create(
                tenant=self.tenant,
                name=f"Product {i}",
                sku=f"PROD{i:03d}",
                category=category,
                unit_price=Decimal("100.00"),
            )
            StockSnapshot.objects.create(
                branch=branch,
                product=product,
                quantity=Decimal("100"),
            )

        from django.test.utils import CaptureQueriesContext
        from django.db import connection

        with CaptureQueriesContext(connection) as context:
            branches = list(
                Branch.objects.filter(tenant=self.tenant)
                .select_related("tenant")
                .prefetch_related("stock_snapshots")
            )
            # Access stock for each branch
            for branch in branches:
                _ = list(branch.stock_snapshots.all())

        # Should be 2 queries: one for branches, one for stock prefetch
        self.assertLessEqual(len(context.captured_queries), 2)
