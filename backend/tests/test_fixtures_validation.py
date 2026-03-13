"""
Validation tests for Phase 2 fixtures.

Verifies that all fixtures are working correctly before proceeding
with user story implementation.
"""

import pytest
from decimal import Decimal

from apps.sync.models import PendingOperation
from tests.factories import ConflictScenarioFactory


class TestConftestFixtures:
    """Test basic conftest.py fixtures."""

    def test_tenant_fixture(self, tenant):
        """Verify tenant fixture creates tenant correctly."""
        assert tenant.id is not None
        assert tenant.name == "Test Company"
        assert tenant.is_active is True
        assert tenant.plan_type == "FREE"

    def test_tenant_context_fixture(self, tenant_context):
        """Verify tenant_context sets current tenant."""
        from apps.core.managers.tenant_bound import get_current_tenant_id

        assert tenant_context.id is not None
        assert get_current_tenant_id() == tenant_context.id

    def test_branch_fixture(self, branch, tenant_context):
        """Verify branch fixture creates branch correctly."""
        assert branch.id is not None
        assert branch.tenant == tenant_context
        assert branch.name == "Main Store"
        assert branch.is_active is True

    def test_authenticated_client_fixture(self, authenticated_client, admin_user):
        """Verify authenticated client has JWT token."""
        # Check that authorization header is set
        auth_header = authenticated_client._credentials.get("HTTP_AUTHORIZATION")
        assert auth_header is not None
        assert auth_header.startswith("Bearer ")


class TestPerformanceFixtures:
    """Test performance test fixtures."""

    @pytest.mark.slow
    def test_large_product_dataset(self, large_product_dataset):
        """Verify large_product_dataset creates 10k products."""
        count = large_product_dataset.count()
        assert count == 10000

        # Verify products have correct attributes
        first_product = large_product_dataset.first()
        assert first_product.sku.startswith("PERF-")
        assert first_product.unit_price == Decimal("100.000")
        assert first_product.cost_price == Decimal("50.000")

    def test_multi_branch_setup(self, multi_branch_setup, tenant_context):
        """Verify multi_branch_setup creates 5 branches."""
        assert len(multi_branch_setup) == 5

        # Verify all branches belong to tenant
        for i, branch in enumerate(multi_branch_setup, start=1):
            assert branch.tenant == tenant_context
            assert branch.name == f"Branch {i}"
            assert branch.afip_pos_number == i

    def test_concurrent_operations_setup(self, concurrent_operations_setup):
        """Verify concurrent_operations_setup creates initial stock."""
        setup = concurrent_operations_setup

        assert setup["tenant"] is not None
        assert setup["product"] is not None
        assert setup["branch"] is not None
        assert setup["initial_movement"] is not None
        assert setup["snapshot"] is not None
        assert setup["initial_quantity"] == Decimal("1000.0000")

        # Verify snapshot has correct quantity
        assert setup["snapshot"].quantity == Decimal("1000.0000")


class TestConflictScenarioFactory:
    """Test ConflictScenarioFactory for all 5 strategies."""

    def test_server_wins_scenario(self, tenant_context):
        """Test SERVER_WINS scenario creation."""
        scenario = ConflictScenarioFactory.server_wins_scenario(tenant_context)

        assert scenario["pending_operation"] is not None
        assert scenario["server_data"] is not None
        assert scenario["expected_action"] == "SERVER_OVERRIDE"
        assert scenario["pending_operation"].entity_type == "Product"

        # Verify client and server data differ
        client_price = scenario["pending_operation"].payload["unit_price"]
        server_price = scenario["server_data"]["unit_price"]
        assert client_price != server_price

    def test_last_write_wins_scenario(self, tenant_context):
        """Test LAST_WRITE_WINS scenario creation."""
        scenario = ConflictScenarioFactory.last_write_wins_scenario(tenant_context)

        assert scenario["pending_operation"] is not None
        assert scenario["server_data"] is not None
        assert scenario["expected_action"] == "SERVER_OVERRIDE"
        assert scenario["pending_operation"].entity_type == "StockMovement"

        # Verify timestamps differ
        client_ts = scenario["pending_operation"].client_timestamp
        server_ts = scenario["pending_operation"].server_timestamp
        assert client_ts < server_ts  # Client is older

    def test_additive_scenario(self, tenant_context):
        """Test ADDITIVE scenario creation."""
        scenario = ConflictScenarioFactory.additive_scenario(tenant_context)

        assert scenario["create_operation"] is not None
        assert scenario["delete_operation"] is not None
        assert scenario["expected_create_action"] == "APPLY"
        assert scenario["expected_delete_action"] == "REJECT"

        # Verify operation types
        assert scenario["create_operation"].operation_type == PendingOperation.OperationType.CREATE
        assert scenario["delete_operation"].operation_type == PendingOperation.OperationType.DELETE

    def test_most_complete_wins_scenario(self, tenant_context):
        """Test MOST_COMPLETE_WINS scenario creation."""
        scenario = ConflictScenarioFactory.most_complete_wins_scenario(tenant_context)

        assert scenario["pending_operation"] is not None
        assert scenario["server_data"] is not None
        assert scenario["expected_action"] == "MERGE"
        assert scenario["expected_merge"] is not None

        # Verify merge combines non-null values
        merge = scenario["expected_merge"]
        assert merge["email"] is not None  # From client
        assert merge["phone"] is not None  # From client
        assert merge["address"] is not None  # From server
        assert merge["tax_id"] is not None  # From server

    def test_server_assigns_final_scenario(self, tenant_context):
        """Test SERVER_ASSIGNS_FINAL scenario creation."""
        scenario = ConflictScenarioFactory.server_assigns_final_scenario(tenant_context)

        assert scenario["pending_operation"] is not None
        assert scenario["expected_action"] == "MERGE"
        assert scenario["expected_merge"] is not None

        # Verify temporary placeholders
        client_payload = scenario["pending_operation"].payload
        assert client_payload["document_number"].startswith("TEMP-")
        assert client_payload["cae"].startswith("TEMP-")

        # Verify expected merge marks fields for server assignment
        merge = scenario["expected_merge"]
        assert merge["document_number"] is None
        assert merge["cae"] is None
        assert "_server_assignment_required" in merge

    def test_create_all_scenarios(self, tenant_context):
        """Test create_all_scenarios creates all 5 strategies."""
        all_scenarios = ConflictScenarioFactory.create_all_scenarios(tenant_context)

        assert len(all_scenarios) == 5
        assert "server_wins" in all_scenarios
        assert "last_write_wins" in all_scenarios
        assert "additive" in all_scenarios
        assert "most_complete_wins" in all_scenarios
        assert "server_assigns_final" in all_scenarios

        # Verify each scenario has required keys
        for name, scenario in all_scenarios.items():
            assert "pending_operation" in scenario or "create_operation" in scenario
            assert "expected_action" in scenario or "expected_create_action" in scenario
            assert "scenario" in scenario


class TestFactoryPatterns:
    """Test factory_boy patterns are working correctly."""

    def test_product_factory_with_tenant(self, tenant_context):
        """Verify ProductFactory respects tenant isolation."""
        from tests.factories import ProductFactory

        product = ProductFactory(tenant=tenant_context)

        assert product.id is not None
        assert product.tenant == tenant_context
        assert product.sku is not None
        assert product.name is not None

    def test_sync_session_factory(self, tenant_context):
        """Verify SyncSessionFactory creates sessions correctly."""
        from tests.factories import SyncSessionFactory, BranchFactory

        branch = BranchFactory(tenant=tenant_context)
        sync_session = SyncSessionFactory(tenant=tenant_context, branch=branch)

        assert sync_session.id is not None
        assert sync_session.tenant == tenant_context
        assert sync_session.branch == branch
        assert sync_session.device_id.startswith("POS-TERMINAL-")

    def test_pending_operation_factory(self, tenant_context):
        """Verify PendingOperationFactory creates operations correctly."""
        from tests.factories import (
            PendingOperationFactory,
            SyncSessionFactory,
            BranchFactory,
        )

        branch = BranchFactory(tenant=tenant_context)
        sync_session = SyncSessionFactory(tenant=tenant_context, branch=branch)

        pending_op = PendingOperationFactory(
            tenant=tenant_context, sync_session=sync_session, entity_type="Sale"
        )

        assert pending_op.id is not None
        assert pending_op.tenant == tenant_context
        assert pending_op.sync_session == sync_session
        assert pending_op.entity_type == "Sale"
        assert pending_op.payload is not None
