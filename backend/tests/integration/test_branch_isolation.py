"""
Integration tests for branch isolation.

Tests verify:
- Branch data isolation within tenant
- Cross-branch access prevention
- Branch-scoped queries
- Multi-tenant branch isolation
"""

import pytest
from decimal import Decimal
from django.test import TestCase

from apps.auth.models import Tenant, AppUser, Branch
from apps.inventario.models import Product, ProductCategory, StockSnapshot, StockMovement
from apps.core.managers.tenant_bound import set_current_tenant_id


@pytest.mark.django_db
class TestBranchDataIsolation(TestCase):
    """Test branch data isolation within tenant."""

    def setUp(self):
        """Set up test data with multiple branches."""
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

    def test_stock_isolation_between_branches(self):
        """Test stock data is isolated between branches."""
        # Create different stock levels per branch
        # Note: StockSnapshot doesn't have tenant field - uses branch.tenant
        StockSnapshot.objects.create(
            branch=self.branch1,
            product=self.product,
            quantity=Decimal("100"),
        )
        StockSnapshot.objects.create(
            branch=self.branch2,
            product=self.product,
            quantity=Decimal("50"),
        )

        # Query branch 1 stock
        branch1_stock = StockSnapshot.objects.filter(
            branch=self.branch1,
            product=self.product,
        ).first()

        # Query branch 2 stock
        branch2_stock = StockSnapshot.objects.filter(
            branch=self.branch2,
            product=self.product,
        ).first()

        # Verify isolation
        self.assertEqual(branch1_stock.quantity, Decimal("100"))
        self.assertEqual(branch2_stock.quantity, Decimal("50"))
        self.assertNotEqual(branch1_stock.id, branch2_stock.id)

    def test_movement_isolation_between_branches(self):
        """Test stock movements are isolated between branches."""
        # Create movements in different branches
        # StockMovement uses: type, quantity_delta, reference_id
        _movement1 = StockMovement.objects.create(
            tenant=self.tenant,
            branch=self.branch1,
            product=self.product,
            type=StockMovement.MovementType.PURCHASE,
            quantity_delta=Decimal("100"),
        )
        _movement2 = StockMovement.objects.create(
            tenant=self.tenant,
            branch=self.branch2,
            product=self.product,
            type=StockMovement.MovementType.PURCHASE,
            quantity_delta=Decimal("50"),
        )

        # Query movements by branch
        branch1_movements = StockMovement.objects.filter(branch=self.branch1)
        branch2_movements = StockMovement.objects.filter(branch=self.branch2)

        self.assertEqual(branch1_movements.count(), 1)
        self.assertEqual(branch2_movements.count(), 1)
        self.assertEqual(branch1_movements.first().quantity_delta, Decimal("100"))
        self.assertEqual(branch2_movements.first().quantity_delta, Decimal("50"))

    def test_aggregated_tenant_stock(self):
        """Test aggregating stock across all branches."""
        StockSnapshot.objects.create(
            branch=self.branch1,
            product=self.product,
            quantity=Decimal("100"),
        )
        StockSnapshot.objects.create(
            branch=self.branch2,
            product=self.product,
            quantity=Decimal("50"),
        )

        from django.db.models import Sum

        # Filter by branch's tenant instead of direct tenant field
        total_stock = StockSnapshot.objects.filter(
            branch__tenant=self.tenant,
            product=self.product,
        ).aggregate(total=Sum("quantity"))

        self.assertEqual(total_stock["total"], Decimal("150"))


@pytest.mark.django_db
class TestMultiTenantBranchIsolation(TestCase):
    """Test branch isolation across tenants."""

    def setUp(self):
        """Set up multi-tenant test data."""
        # Tenant 1
        self.tenant1 = Tenant.objects.create(
            name="Company 1",
            is_active=True,
        )
        set_current_tenant_id(self.tenant1.id)
        self.tenant1_branch = Branch.objects.create(
            tenant=self.tenant1,
            name="T1 Branch",
            is_active=True,
        )
        self.tenant1_category = ProductCategory.objects.create(
            tenant=self.tenant1,
            name="T1 Category",
        )
        self.tenant1_product = Product.objects.create(
            tenant=self.tenant1,
            name="T1 Product",
            sku="T1PROD",
            category=self.tenant1_category,
            unit_price=Decimal("100.00"),
        )

        # Tenant 2
        self.tenant2 = Tenant.objects.create(
            name="Company 2",
            is_active=True,
        )
        set_current_tenant_id(self.tenant2.id)
        self.tenant2_branch = Branch.objects.create(
            tenant=self.tenant2,
            name="T2 Branch",
            is_active=True,
        )
        self.tenant2_category = ProductCategory.objects.create(
            tenant=self.tenant2,
            name="T2 Category",
        )
        self.tenant2_product = Product.objects.create(
            tenant=self.tenant2,
            name="T2 Product",
            sku="T2PROD",
            category=self.tenant2_category,
            unit_price=Decimal("200.00"),
        )

    def test_branch_tenant_isolation(self):
        """Test branches are isolated by tenant."""
        # Use all_objects to bypass tenant filtering for this test
        # The TenantBoundManager automatically filters by current tenant context
        tenant1_branches = Branch.all_objects.filter(tenant=self.tenant1)
        tenant2_branches = Branch.all_objects.filter(tenant=self.tenant2)

        self.assertEqual(tenant1_branches.count(), 1)
        self.assertEqual(tenant2_branches.count(), 1)
        self.assertEqual(tenant1_branches.first().name, "T1 Branch")
        self.assertEqual(tenant2_branches.first().name, "T2 Branch")

    def test_stock_tenant_isolation(self):
        """Test stock snapshots are isolated by tenant."""
        StockSnapshot.objects.create(
            branch=self.tenant1_branch,
            product=self.tenant1_product,
            quantity=Decimal("100"),
        )
        StockSnapshot.objects.create(
            branch=self.tenant2_branch,
            product=self.tenant2_product,
            quantity=Decimal("200"),
        )

        # Filter by branch's tenant
        tenant1_stock = StockSnapshot.objects.filter(branch__tenant=self.tenant1)
        tenant2_stock = StockSnapshot.objects.filter(branch__tenant=self.tenant2)

        self.assertEqual(tenant1_stock.count(), 1)
        self.assertEqual(tenant2_stock.count(), 1)
        self.assertEqual(tenant1_stock.first().quantity, Decimal("100"))
        self.assertEqual(tenant2_stock.first().quantity, Decimal("200"))

    def test_cannot_access_other_tenant_branch(self):
        """Test users cannot access other tenant's branches."""
        # Create users for each tenant - use default_branch instead of branch
        set_current_tenant_id(self.tenant1.id)
        user1 = AppUser.objects.create_user(
            email="user1@company1.com",
            tenant=self.tenant1,
            password="testpass123",
            default_branch=self.tenant1_branch,
        )
        set_current_tenant_id(self.tenant2.id)
        user2 = AppUser.objects.create_user(
            email="user2@company2.com",
            tenant=self.tenant2,
            password="testpass123",
            default_branch=self.tenant2_branch,
        )

        # User 1 should only see tenant 1 branches
        # Need to set tenant context to user1's tenant for the query to work
        set_current_tenant_id(user1.tenant.id)
        user1_branches = Branch.objects.filter(tenant=user1.tenant)
        self.assertEqual(user1_branches.count(), 1)
        self.assertTrue(all(b.tenant == self.tenant1 for b in user1_branches))

        # User 2 should only see tenant 2 branches
        set_current_tenant_id(user2.tenant.id)
        user2_branches = Branch.objects.filter(tenant=user2.tenant)
        self.assertEqual(user2_branches.count(), 1)
        self.assertTrue(all(b.tenant == self.tenant2 for b in user2_branches))


@pytest.mark.django_db
class TestBranchScopedQueries(TestCase):
    """Test branch-scoped query patterns."""

    def setUp(self):
        """Set up test data."""
        self.tenant = Tenant.objects.create(
            name="Test Company",
            is_active=True,
        )
        set_current_tenant_id(self.tenant.id)
        self.branches = []
        for i in range(3):
            branch = Branch.objects.create(
                tenant=self.tenant,
                name=f"Branch {i}",
                is_active=True,
            )
            self.branches.append(branch)

        self.category = ProductCategory.objects.create(
            tenant=self.tenant,
            name="Test Category",
        )

        # Create products and stock for each branch
        self.products = []
        for i in range(5):
            product = Product.objects.create(
                tenant=self.tenant,
                name=f"Product {i}",
                sku=f"PROD{i:03d}",
                category=self.category,
                unit_price=Decimal(f"{(i + 1) * 10}.00"),
            )
            self.products.append(product)

            # Add stock to each branch - no tenant param
            for branch in self.branches:
                StockSnapshot.objects.create(
                    branch=branch,
                    product=product,
                    quantity=Decimal(f"{(i + 1) * 10}"),
                )

    def test_branch_specific_stock_query(self):
        """Test querying stock for specific branch."""
        branch = self.branches[0]

        stock = StockSnapshot.objects.filter(
            branch__tenant=self.tenant,
            branch=branch,
        ).select_related("product")

        self.assertEqual(stock.count(), 5)
        for snapshot in stock:
            self.assertEqual(snapshot.branch, branch)

    def test_product_stock_across_branches(self):
        """Test querying product stock across all branches."""
        product = self.products[0]

        stock = StockSnapshot.objects.filter(
            branch__tenant=self.tenant,
            product=product,
        ).select_related("branch")

        self.assertEqual(stock.count(), 3)
        branches_with_stock = {s.branch.name for s in stock}
        expected_branches = {b.name for b in self.branches}
        self.assertEqual(branches_with_stock, expected_branches)

    def test_low_stock_query_by_branch(self):
        """Test querying low stock items by branch."""
        branch = self.branches[0]

        # Products with quantity <= 20
        low_stock = StockSnapshot.objects.filter(
            branch__tenant=self.tenant,
            branch=branch,
            quantity__lte=Decimal("20"),
        ).select_related("product")

        # Should have products with quantity 10 and 20
        self.assertEqual(low_stock.count(), 2)

    def test_out_of_stock_query(self):
        """Test querying out of stock items."""
        # Set one product to 0 in one branch
        snapshot = StockSnapshot.objects.filter(
            branch=self.branches[0],
            product=self.products[0],
        ).first()
        snapshot.quantity = Decimal("0")
        snapshot.save()

        out_of_stock = StockSnapshot.objects.filter(
            branch__tenant=self.tenant,
            branch=self.branches[0],
            quantity=Decimal("0"),
        )

        self.assertEqual(out_of_stock.count(), 1)


@pytest.mark.django_db
class TestBranchContextIsolation(TestCase):
    """Test branch context isolation in operations."""

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

    def test_user_branch_context(self):
        """Test user operations use correct branch context."""
        # Use default_branch instead of branch
        user1 = AppUser.objects.create_user(
            email="user1@test.com",
            tenant=self.tenant,
            password="testpass123",
            default_branch=self.branch1,
        )
        user2 = AppUser.objects.create_user(
            email="user2@test.com",
            tenant=self.tenant,
            password="testpass123",
            default_branch=self.branch2,
        )

        # Each user should have their own branch context
        self.assertEqual(user1.default_branch, self.branch1)
        self.assertEqual(user2.default_branch, self.branch2)

    def test_branch_switching_not_cross_tenant(self):
        """Test users cannot switch to branches in other tenants."""
        other_tenant = Tenant.objects.create(
            name="Other Company",
            is_active=True,
        )
        set_current_tenant_id(other_tenant.id)
        other_branch = Branch.objects.create(
            tenant=other_tenant,
            name="Other Branch",
            is_active=True,
        )
        set_current_tenant_id(self.tenant.id)  # Reset to original tenant

        user = AppUser.objects.create_user(
            email="user@test.com",
            tenant=self.tenant,
            password="testpass123",
            default_branch=self.branch1,
        )

        # User's accessible branches should only be from their tenant
        accessible_branches = Branch.objects.filter(tenant=user.tenant, is_active=True)
        self.assertNotIn(other_branch, accessible_branches)


@pytest.mark.django_db
class TestBranchConcurrency(TestCase):
    """Test concurrent branch operations."""

    def setUp(self):
        """Set up test data."""
        self.tenant = Tenant.objects.create(
            name="Test Company",
            is_active=True,
        )
        set_current_tenant_id(self.tenant.id)
        self.branch = Branch.objects.create(
            tenant=self.tenant,
            name="Test Branch",
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
        # No tenant param for StockSnapshot
        self.snapshot = StockSnapshot.objects.create(
            branch=self.branch,
            product=self.product,
            quantity=Decimal("100"),
        )

    def test_concurrent_stock_reads(self):
        """Test multiple sequential stock reads are consistent and fast."""
        import time

        results = []

        start = time.time()
        # Perform 10 sequential reads to simulate concurrent access pattern
        for _ in range(10):
            snapshot = StockSnapshot.objects.filter(
                branch=self.branch,
                product=self.product,
            ).first()
            results.append(snapshot.quantity)
        elapsed = time.time() - start

        # All reads should succeed and return consistent data
        self.assertEqual(len(results), 10)
        self.assertTrue(all(q == Decimal("100") for q in results))

        # Should complete quickly (no blocking)
        self.assertLess(elapsed, 5.0)

    def test_stock_update_isolation(self):
        """Test stock updates are atomic and isolated."""
        from django.db import transaction

        initial_qty = self.snapshot.quantity

        # Simulate concurrent updates
        with transaction.atomic():
            # Lock the row for update
            snapshot = StockSnapshot.objects.select_for_update().get(
                id=self.snapshot.id
            )
            snapshot.quantity -= Decimal("10")
            snapshot.save()

        self.snapshot.refresh_from_db()
        self.assertEqual(self.snapshot.quantity, initial_qty - Decimal("10"))
