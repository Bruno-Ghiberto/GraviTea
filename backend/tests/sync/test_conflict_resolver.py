"""
Comprehensive tests for ConflictResolver - 5 Resolution Strategies.

This module tests the ConflictResolver class which implements the following strategies:
1. SERVER_WINS - Configuration data (Products, PriceLists, Branches, Settings)
2. LAST_WRITE_WINS - Inventory levels (StockMovement, StockSnapshot)
3. ADDITIVE - Sales transactions (Sale, SaleItem, Payment) - no deletions
4. MOST_COMPLETE_WINS - Customer data (Customer, Address, Contact)
5. SERVER_ASSIGNS_FINAL - Document numbering (FiscalDocument, Invoice, CAE)

Target: 80% coverage for apps/sync/conflict_resolver.py
"""

import uuid
from datetime import timedelta

import pytest
from django.utils import timezone

from apps.sync.conflict_resolver import (
    ConflictResolution,
    ConflictResolver,
    ResolutionAction,
    ResolutionRule,
)
from apps.sync.models import PendingOperation
from tests.factories import (
    BranchFactory,
    ConflictScenarioFactory,
    PendingOperationFactory,
    SyncSessionFactory,
)


@pytest.mark.django_db
class TestConflictResolverInit:
    """Test ConflictResolver initialization."""

    def test_resolver_initializes_with_strategy_map(self):
        """T010: Verify ConflictResolver initializes with all 5 strategy mappings."""
        resolver = ConflictResolver()

        assert hasattr(resolver, "_strategy_map")
        assert len(resolver._strategy_map) == 5

        # Verify all strategies are mapped
        expected_rules = [
            ResolutionRule.SERVER_WINS,
            ResolutionRule.LAST_WRITE_WINS,
            ResolutionRule.ADDITIVE,
            ResolutionRule.MOST_COMPLETE_WINS,
            ResolutionRule.SERVER_ASSIGNS_FINAL,
        ]
        for rule in expected_rules:
            assert rule in resolver._strategy_map
            assert callable(resolver._strategy_map[rule])

    def test_entity_resolution_map_completeness(self):
        """Verify all expected entity types are mapped."""
        resolver = ConflictResolver()

        # Configuration entities -> SERVER_WINS
        config_entities = ["Product", "PriceList", "PriceListItem", "Branch", "Settings", "TaxRate", "PaymentMethod"]
        for entity in config_entities:
            assert resolver.ENTITY_RESOLUTION_MAP.get(entity) == ResolutionRule.SERVER_WINS

        # Inventory entities -> LAST_WRITE_WINS
        inventory_entities = ["StockMovement", "StockSnapshot", "InventoryAdjustment"]
        for entity in inventory_entities:
            assert resolver.ENTITY_RESOLUTION_MAP.get(entity) == ResolutionRule.LAST_WRITE_WINS

        # Sales entities -> ADDITIVE
        sales_entities = ["Sale", "SaleItem", "Payment"]
        for entity in sales_entities:
            assert resolver.ENTITY_RESOLUTION_MAP.get(entity) == ResolutionRule.ADDITIVE

        # Customer entities -> MOST_COMPLETE_WINS
        customer_entities = ["Customer", "Address", "Contact"]
        for entity in customer_entities:
            assert resolver.ENTITY_RESOLUTION_MAP.get(entity) == ResolutionRule.MOST_COMPLETE_WINS

        # Document entities -> SERVER_ASSIGNS_FINAL
        document_entities = ["FiscalDocument", "CAEAssignment", "Invoice"]
        for entity in document_entities:
            assert resolver.ENTITY_RESOLUTION_MAP.get(entity) == ResolutionRule.SERVER_ASSIGNS_FINAL


@pytest.mark.django_db
class TestServerWinsStrategy:
    """Tests for SERVER_WINS resolution strategy (T011-T015)."""

    @pytest.fixture
    def resolver(self):
        return ConflictResolver()

    def test_server_wins_product_conflict(self, resolver, tenant_context):
        """T011: Test SERVER_WINS resolves Product entity conflicts correctly."""
        scenario = ConflictScenarioFactory.server_wins_scenario(tenant_context, entity_type="Product")
        pending_op = scenario["pending_operation"]
        server_data = scenario["server_data"]

        resolution = resolver.resolve(pending_op, server_data)

        assert resolution.action == ResolutionAction.SERVER_OVERRIDE
        assert resolution.merged_payload == server_data
        assert resolution.resolution_rule == ResolutionRule.SERVER_WINS
        assert "Configuration data: server always wins" in resolution.audit_log.get("reason", "")
        assert resolution.metadata.get("sync_required") is True

    def test_server_wins_pricelist_conflict(self, resolver, tenant_context):
        """T012: Test SERVER_WINS resolves PriceList entity conflicts correctly."""
        branch = BranchFactory(tenant=tenant_context)
        sync_session = SyncSessionFactory(tenant=tenant_context, branch=branch)

        pending_op = PendingOperationFactory(
            tenant=tenant_context,
            sync_session=sync_session,
            entity_type="PriceList",
            operation_type=PendingOperation.OperationType.UPDATE,
            payload={
                "id": str(uuid.uuid4()),
                "name": "Retail Prices",
                "discount_percentage": "10.00",
            },
            client_timestamp=timezone.now() - timedelta(hours=1),
        )

        server_data = {
            "id": pending_op.payload["id"],
            "name": "Retail Prices",
            "discount_percentage": "15.00",  # Server has different discount
        }

        resolution = resolver.resolve(pending_op, server_data)

        assert resolution.action == ResolutionAction.SERVER_OVERRIDE
        assert resolution.merged_payload["discount_percentage"] == "15.00"
        assert resolution.resolution_rule == ResolutionRule.SERVER_WINS

    def test_server_wins_branch_conflict(self, resolver, tenant_context):
        """T013: Test SERVER_WINS resolves Branch entity conflicts correctly."""
        branch = BranchFactory(tenant=tenant_context)
        sync_session = SyncSessionFactory(tenant=tenant_context, branch=branch)

        pending_op = PendingOperationFactory(
            tenant=tenant_context,
            sync_session=sync_session,
            entity_type="Branch",
            operation_type=PendingOperation.OperationType.UPDATE,
            payload={
                "id": str(branch.id),
                "name": "Main Store",
                "address": "Old Address",
            },
            client_timestamp=timezone.now() - timedelta(minutes=30),
        )

        server_data = {
            "id": str(branch.id),
            "name": "Main Store",
            "address": "New Central Address",  # Server has updated address
        }

        resolution = resolver.resolve(pending_op, server_data)

        assert resolution.action == ResolutionAction.SERVER_OVERRIDE
        assert resolution.merged_payload["address"] == "New Central Address"

    def test_server_wins_settings_conflict(self, resolver, tenant_context):
        """T014: Test SERVER_WINS resolves SystemSetting entity conflicts correctly."""
        branch = BranchFactory(tenant=tenant_context)
        sync_session = SyncSessionFactory(tenant=tenant_context, branch=branch)

        pending_op = PendingOperationFactory(
            tenant=tenant_context,
            sync_session=sync_session,
            entity_type="Settings",
            operation_type=PendingOperation.OperationType.UPDATE,
            payload={
                "key": "tax_rate",
                "value": "21.00",
            },
        )

        server_data = {
            "key": "tax_rate",
            "value": "22.00",  # Server has different tax rate
        }

        resolution = resolver.resolve(pending_op, server_data)

        assert resolution.action == ResolutionAction.SERVER_OVERRIDE
        assert resolution.merged_payload["value"] == "22.00"

    def test_server_wins_null_server_value(self, resolver, tenant_context):
        """T015: Test SERVER_WINS edge case: null server value vs non-null client value."""
        branch = BranchFactory(tenant=tenant_context)
        sync_session = SyncSessionFactory(tenant=tenant_context, branch=branch)

        pending_op = PendingOperationFactory(
            tenant=tenant_context,
            sync_session=sync_session,
            entity_type="Product",
            operation_type=PendingOperation.OperationType.UPDATE,
            payload={
                "id": str(uuid.uuid4()),
                "name": "Test Product",
                "unit_price": "100.00",
            },
        )

        # Server data is None (product might have been deleted)
        resolution = resolver.resolve(pending_op, None)

        assert resolution.action == ResolutionAction.SERVER_OVERRIDE
        assert resolution.merged_payload is None  # Server wins, even if None
        assert resolution.audit_log.get("server_payload") is None


@pytest.mark.django_db
class TestLastWriteWinsStrategy:
    """Tests for LAST_WRITE_WINS resolution strategy (T016-T019)."""

    @pytest.fixture
    def resolver(self):
        return ConflictResolver()

    def test_last_write_wins_stock_movement_client_newer(self, resolver, tenant_context):
        """T016: Test LAST_WRITE_WINS resolves StockMovement conflicts - client newer."""
        scenario = ConflictScenarioFactory.last_write_wins_scenario(tenant_context)
        pending_op = scenario["pending_operation"]
        server_data = scenario["server_data"]

        # Ensure client is newer
        pending_op.client_timestamp = timezone.now()
        pending_op.server_timestamp = timezone.now() - timedelta(minutes=10)
        pending_op.save()

        resolution = resolver.resolve(pending_op, server_data)

        assert resolution.action == ResolutionAction.APPLY
        assert resolution.merged_payload == pending_op.payload
        assert resolution.resolution_rule == ResolutionRule.LAST_WRITE_WINS
        assert resolution.audit_log.get("winner") == "client"

    def test_last_write_wins_stock_level_server_newer(self, resolver, tenant_context):
        """T17: Test LAST_WRITE_WINS resolves StockLevel conflicts - server newer."""
        branch = BranchFactory(tenant=tenant_context)
        sync_session = SyncSessionFactory(tenant=tenant_context, branch=branch)

        # Client timestamp is older
        client_ts = timezone.now() - timedelta(hours=1)
        server_ts = timezone.now()

        pending_op = PendingOperationFactory(
            tenant=tenant_context,
            sync_session=sync_session,
            entity_type="StockSnapshot",
            operation_type=PendingOperation.OperationType.UPDATE,
            payload={
                "product_id": str(uuid.uuid4()),
                "quantity": "100.0000",
            },
            client_timestamp=client_ts,
            server_timestamp=server_ts,
        )

        server_data = {
            "product_id": pending_op.payload["product_id"],
            "quantity": "150.0000",  # Server has newer quantity
        }

        resolution = resolver.resolve(pending_op, server_data)

        assert resolution.action == ResolutionAction.SERVER_OVERRIDE
        assert resolution.merged_payload == server_data
        assert resolution.audit_log.get("winner") == "server"

    def test_last_write_wins_identical_timestamps(self, resolver, tenant_context):
        """T018: Test LAST_WRITE_WINS edge case: identical timestamps."""
        branch = BranchFactory(tenant=tenant_context)
        sync_session = SyncSessionFactory(tenant=tenant_context, branch=branch)

        # Same timestamp for both
        same_ts = timezone.now()

        pending_op = PendingOperationFactory(
            tenant=tenant_context,
            sync_session=sync_session,
            entity_type="StockMovement",
            operation_type=PendingOperation.OperationType.CREATE,
            payload={
                "product_id": str(uuid.uuid4()),
                "quantity_delta": "10.0000",
            },
            client_timestamp=same_ts,
            server_timestamp=same_ts,
        )

        server_data = {
            "product_id": pending_op.payload["product_id"],
            "quantity_delta": "15.0000",
        }

        resolution = resolver.resolve(pending_op, server_data)

        # Server wins ties
        assert resolution.action == ResolutionAction.SERVER_OVERRIDE
        assert resolution.audit_log.get("winner") == "server"

    def test_last_write_wins_very_old_timestamp(self, resolver, tenant_context):
        """T019: Test LAST_WRITE_WINS edge case: very old client timestamp."""
        branch = BranchFactory(tenant=tenant_context)
        sync_session = SyncSessionFactory(tenant=tenant_context, branch=branch)

        # Client has very old timestamp (device was offline for a long time)
        very_old_time = timezone.now() - timedelta(days=365)

        pending_op = PendingOperationFactory(
            tenant=tenant_context,
            sync_session=sync_session,
            entity_type="StockMovement",
            operation_type=PendingOperation.OperationType.CREATE,
            payload={
                "product_id": str(uuid.uuid4()),
                "quantity_delta": "10.0000",
            },
            client_timestamp=very_old_time,
            server_timestamp=timezone.now(),  # Server processes now
        )

        server_data = {"product_id": pending_op.payload["product_id"]}

        resolution = resolver.resolve(pending_op, server_data)

        # Server should win since it's much newer
        assert resolution.action == ResolutionAction.SERVER_OVERRIDE
        assert resolution.resolution_rule == ResolutionRule.LAST_WRITE_WINS
        assert resolution.audit_log.get("winner") == "server"


@pytest.mark.django_db
class TestAdditiveStrategy:
    """Tests for ADDITIVE resolution strategy (T020-T022)."""

    @pytest.fixture
    def resolver(self):
        return ConflictResolver()

    def test_additive_preserves_sale_records(self, resolver, tenant_context):
        """T020: Test ADDITIVE preserves Sale records."""
        scenario = ConflictScenarioFactory.additive_scenario(tenant_context)
        # additive_scenario returns create_operation and delete_operation keys
        pending_op = scenario["create_operation"]
        server_data = None  # No server data for CREATE

        resolution = resolver.resolve(pending_op, server_data)

        assert resolution.action == ResolutionAction.APPLY
        assert resolution.merged_payload == pending_op.payload
        assert resolution.resolution_rule == ResolutionRule.ADDITIVE
        assert resolution.metadata.get("additive") is True

    def test_additive_preserves_sale_item_records(self, resolver, tenant_context):
        """T021: Test ADDITIVE preserves SaleItem records."""
        branch = BranchFactory(tenant=tenant_context)
        sync_session = SyncSessionFactory(tenant=tenant_context, branch=branch)

        pending_op = PendingOperationFactory(
            tenant=tenant_context,
            sync_session=sync_session,
            entity_type="SaleItem",
            operation_type=PendingOperation.OperationType.CREATE,
            payload={
                "sale_id": str(uuid.uuid4()),
                "product_id": str(uuid.uuid4()),
                "quantity": "2.0000",
                "unit_price": "50.00",
            },
        )

        resolution = resolver.resolve(pending_op, None)

        assert resolution.action == ResolutionAction.APPLY
        assert resolution.resolution_rule == ResolutionRule.ADDITIVE

    def test_additive_rejects_deletions(self, resolver, tenant_context):
        """T022: Test ADDITIVE returns appropriate error on deletion attempt."""
        branch = BranchFactory(tenant=tenant_context)
        sync_session = SyncSessionFactory(tenant=tenant_context, branch=branch)

        pending_op = PendingOperationFactory(
            tenant=tenant_context,
            sync_session=sync_session,
            entity_type="Sale",
            operation_type=PendingOperation.OperationType.DELETE,  # DELETE operation
            payload={
                "id": str(uuid.uuid4()),
            },
        )

        resolution = resolver.resolve(pending_op, None)

        assert resolution.action == ResolutionAction.REJECT
        assert resolution.metadata.get("deletion_rejected") is True
        assert "cannot be deleted" in resolution.metadata.get("message", "")
        assert "deletions not allowed" in resolution.audit_log.get("reason", "")

    def test_additive_allows_updates(self, resolver, tenant_context):
        """Test ADDITIVE allows UPDATE operations (e.g., void/cancel)."""
        branch = BranchFactory(tenant=tenant_context)
        sync_session = SyncSessionFactory(tenant=tenant_context, branch=branch)

        pending_op = PendingOperationFactory(
            tenant=tenant_context,
            sync_session=sync_session,
            entity_type="Sale",
            operation_type=PendingOperation.OperationType.UPDATE,
            payload={
                "id": str(uuid.uuid4()),
                "status": "voided",  # Mark as voided instead of delete
            },
        )

        resolution = resolver.resolve(pending_op, None)

        assert resolution.action == ResolutionAction.APPLY
        assert resolution.metadata.get("additive") is True


@pytest.mark.django_db
class TestMostCompleteWinsStrategy:
    """Tests for MOST_COMPLETE_WINS resolution strategy (T023-T025)."""

    @pytest.fixture
    def resolver(self):
        return ConflictResolver()

    def test_most_complete_merges_customer_fields(self, resolver, tenant_context):
        """T023: Test MOST_COMPLETE_WINS merges Customer fields correctly."""
        scenario = ConflictScenarioFactory.most_complete_wins_scenario(tenant_context)
        pending_op = scenario["pending_operation"]
        server_data = scenario["server_data"]

        resolution = resolver.resolve(pending_op, server_data)

        assert resolution.action == ResolutionAction.MERGE
        assert resolution.resolution_rule == ResolutionRule.MOST_COMPLETE_WINS
        assert resolution.merged_payload is not None

        # Verify merge decisions are logged
        assert "merge_decisions" in resolution.audit_log

    def test_most_complete_prefers_non_null_values(self, resolver, tenant_context):
        """T024: Test MOST_COMPLETE_WINS prefers non-null values."""
        branch = BranchFactory(tenant=tenant_context)
        sync_session = SyncSessionFactory(tenant=tenant_context, branch=branch)

        pending_op = PendingOperationFactory(
            tenant=tenant_context,
            sync_session=sync_session,
            entity_type="Customer",
            operation_type=PendingOperation.OperationType.UPDATE,
            payload={
                "id": str(uuid.uuid4()),
                "name": "John Doe",
                "email": "john@example.com",
                "phone": None,  # Client has null phone
            },
        )

        server_data = {
            "id": pending_op.payload["id"],
            "name": None,  # Server has null name
            "email": None,  # Server has null email
            "phone": "+1234567890",  # Server has phone
        }

        resolution = resolver.resolve(pending_op, server_data)

        assert resolution.action == ResolutionAction.MERGE
        merged = resolution.merged_payload

        # Client wins: name, email (non-null)
        assert merged["name"] == "John Doe"
        assert merged["email"] == "john@example.com"
        # Server wins: phone (non-null)
        assert merged["phone"] == "+1234567890"

    def test_most_complete_server_wins_ties(self, resolver, tenant_context):
        """T025: Test MOST_COMPLETE_WINS uses server tiebreaker when completeness equal."""
        branch = BranchFactory(tenant=tenant_context)
        sync_session = SyncSessionFactory(tenant=tenant_context, branch=branch)

        pending_op = PendingOperationFactory(
            tenant=tenant_context,
            sync_session=sync_session,
            entity_type="Customer",
            operation_type=PendingOperation.OperationType.UPDATE,
            payload={
                "id": str(uuid.uuid4()),
                "name": "John",  # Same length
                "tax_id": "12345678",  # Same as server (non-string comparison)
            },
        )

        server_data = {
            "id": pending_op.payload["id"],
            "name": "Jane",  # Same length as "John" -> server wins tie
            "tax_id": "87654321",  # Different value, server wins non-string tie
        }

        resolution = resolver.resolve(pending_op, server_data)

        assert resolution.action == ResolutionAction.MERGE
        merged = resolution.merged_payload

        # Server wins ties
        assert merged["name"] == "Jane"  # Server wins string tie
        assert merged["tax_id"] == "87654321"  # Server wins non-string tie

    def test_most_complete_longer_string_wins(self, resolver, tenant_context):
        """Test MOST_COMPLETE_WINS prefers longer string values."""
        branch = BranchFactory(tenant=tenant_context)
        sync_session = SyncSessionFactory(tenant=tenant_context, branch=branch)

        pending_op = PendingOperationFactory(
            tenant=tenant_context,
            sync_session=sync_session,
            entity_type="Address",
            operation_type=PendingOperation.OperationType.UPDATE,
            payload={
                "id": str(uuid.uuid4()),
                "street": "123 Main Street, Suite 100, Building A",  # Longer
            },
        )

        server_data = {
            "id": pending_op.payload["id"],
            "street": "123 Main St",  # Shorter
        }

        resolution = resolver.resolve(pending_op, server_data)

        merged = resolution.merged_payload
        # Client wins with longer address
        assert merged["street"] == "123 Main Street, Suite 100, Building A"


@pytest.mark.django_db
class TestServerAssignsFinalStrategy:
    """Tests for SERVER_ASSIGNS_FINAL resolution strategy (T026-T028)."""

    @pytest.fixture
    def resolver(self):
        return ConflictResolver()

    def test_server_assigns_final_document_numbers(self, resolver, tenant_context):
        """T026: Test SERVER_ASSIGNS_FINAL assigns final FiscalDocument numbers."""
        scenario = ConflictScenarioFactory.server_assigns_final_scenario(tenant_context)
        pending_op = scenario["pending_operation"]
        server_data = scenario.get("server_data")

        resolution = resolver.resolve(pending_op, server_data)

        assert resolution.action == ResolutionAction.MERGE
        assert resolution.resolution_rule == ResolutionRule.SERVER_ASSIGNS_FINAL
        assert resolution.metadata.get("server_assignment_required") is True

    def test_server_assigns_final_temporary_placeholder(self, resolver, tenant_context):
        """T027: Test SERVER_ASSIGNS_FINAL handles temporary placeholder numbering."""
        branch = BranchFactory(tenant=tenant_context)
        sync_session = SyncSessionFactory(tenant=tenant_context, branch=branch)

        pending_op = PendingOperationFactory(
            tenant=tenant_context,
            sync_session=sync_session,
            entity_type="FiscalDocument",
            operation_type=PendingOperation.OperationType.CREATE,
            payload={
                "id": str(uuid.uuid4()),
                "document_number": "TEMP-12345",  # Temporary placeholder
                "total": "500.00",
            },
        )

        resolution = resolver.resolve(pending_op, None)

        assert resolution.action == ResolutionAction.MERGE
        merged = resolution.merged_payload

        # Document number should be set to None for server assignment
        assert merged["document_number"] is None
        assert "document_number" in resolution.metadata.get("fields_to_assign", [])
        assert resolution.metadata.get("placeholder_detected") is True

    def test_server_assigns_final_cae_reference(self, resolver, tenant_context):
        """T028: Test SERVER_ASSIGNS_FINAL assigns CAE reference correctly."""
        branch = BranchFactory(tenant=tenant_context)
        sync_session = SyncSessionFactory(tenant=tenant_context, branch=branch)

        pending_op = PendingOperationFactory(
            tenant=tenant_context,
            sync_session=sync_session,
            entity_type="Invoice",
            operation_type=PendingOperation.OperationType.CREATE,
            payload={
                "id": str(uuid.uuid4()),
                "document_number": "TEMP-INV-001",
                "cae": "TEMP-CAE-001",  # Temporary CAE
                "total": "1500.00",
            },
        )

        resolution = resolver.resolve(pending_op, None)

        assert resolution.action == ResolutionAction.MERGE
        merged = resolution.merged_payload

        # Both document_number and CAE should be marked for server assignment
        assert merged["document_number"] is None
        assert merged["cae"] is None
        fields_to_assign = resolution.metadata.get("fields_to_assign", [])
        assert "document_number" in fields_to_assign
        assert "cae" in fields_to_assign

    def test_server_assigns_final_non_temp_preserved(self, resolver, tenant_context):
        """Test SERVER_ASSIGNS_FINAL preserves non-temporary values."""
        branch = BranchFactory(tenant=tenant_context)
        sync_session = SyncSessionFactory(tenant=tenant_context, branch=branch)

        pending_op = PendingOperationFactory(
            tenant=tenant_context,
            sync_session=sync_session,
            entity_type="FiscalDocument",
            operation_type=PendingOperation.OperationType.CREATE,
            payload={
                "id": str(uuid.uuid4()),
                "document_number": "INV-2024-0001",  # Not a TEMP- prefix
                "total": "500.00",
            },
        )

        resolution = resolver.resolve(pending_op, None)

        merged = resolution.merged_payload
        # Non-temp document number is preserved
        assert merged["document_number"] == "INV-2024-0001"
        fields_to_assign = resolution.metadata.get("fields_to_assign", [])
        assert "document_number" not in fields_to_assign


@pytest.mark.django_db
class TestErrorHandling:
    """Tests for error handling in ConflictResolver (T029-T030)."""

    @pytest.fixture
    def resolver(self):
        return ConflictResolver()

    def test_unknown_entity_type_raises_error(self, resolver, tenant_context):
        """T029: Test unknown entity type handling."""
        branch = BranchFactory(tenant=tenant_context)
        sync_session = SyncSessionFactory(tenant=tenant_context, branch=branch)

        pending_op = PendingOperationFactory(
            tenant=tenant_context,
            sync_session=sync_session,
            entity_type="UnknownEntity",  # Not in ENTITY_RESOLUTION_MAP
            operation_type=PendingOperation.OperationType.CREATE,
            payload={"id": str(uuid.uuid4())},
        )

        with pytest.raises(ValueError) as exc_info:
            resolver.resolve(pending_op, None)

        assert "Unknown entity type: UnknownEntity" in str(exc_info.value)

    def test_invalid_data_structure_handling(self, resolver, tenant_context):
        """T030: Test invalid data structure handling - empty/minimal payload."""
        branch = BranchFactory(tenant=tenant_context)
        sync_session = SyncSessionFactory(tenant=tenant_context, branch=branch)

        # Create operation with minimal/empty payload (edge case)
        pending_op = PendingOperationFactory(
            tenant=tenant_context,
            sync_session=sync_session,
            entity_type="Product",
            operation_type=PendingOperation.OperationType.UPDATE,
            payload={},  # Empty payload - edge case
        )

        # Should still resolve (SERVER_WINS handles empty payload gracefully)
        resolution = resolver.resolve(pending_op, {"valid": "server_data"})

        assert resolution is not None
        assert resolution.action == ResolutionAction.SERVER_OVERRIDE

    def test_resolve_returns_conflict_resolution_dataclass(self, resolver, tenant_context):
        """Verify resolve returns proper ConflictResolution dataclass."""
        branch = BranchFactory(tenant=tenant_context)
        sync_session = SyncSessionFactory(tenant=tenant_context, branch=branch)

        pending_op = PendingOperationFactory(
            tenant=tenant_context,
            sync_session=sync_session,
            entity_type="Product",
            operation_type=PendingOperation.OperationType.UPDATE,
            payload={"id": str(uuid.uuid4()), "name": "Test"},
        )

        resolution = resolver.resolve(pending_op, {"name": "Server Test"})

        assert isinstance(resolution, ConflictResolution)
        assert hasattr(resolution, "action")
        assert hasattr(resolution, "merged_payload")
        assert hasattr(resolution, "audit_log")
        assert hasattr(resolution, "resolution_rule")
        assert hasattr(resolution, "metadata")


@pytest.mark.django_db
class TestAuditLogging:
    """Tests for audit logging in ConflictResolver."""

    @pytest.fixture
    def resolver(self):
        return ConflictResolver()

    def test_resolution_includes_operation_details(self, resolver, tenant_context):
        """Verify resolution includes complete operation details in audit log."""
        branch = BranchFactory(tenant=tenant_context)
        sync_session = SyncSessionFactory(tenant=tenant_context, branch=branch)

        pending_op = PendingOperationFactory(
            tenant=tenant_context,
            sync_session=sync_session,
            entity_type="Product",
            operation_type=PendingOperation.OperationType.UPDATE,
            payload={"id": str(uuid.uuid4()), "name": "Test Product"},
        )

        resolution = resolver.resolve(pending_op, {"name": "Server Product"})

        audit_log = resolution.audit_log
        assert "operation_id" in audit_log
        assert "entity_type" in audit_log
        assert "entity_id" in audit_log
        assert "operation_type" in audit_log
        assert "resolution_rule" in audit_log

    def test_resolution_to_dict_serializable(self, resolver, tenant_context):
        """Verify ConflictResolution can be serialized to dict."""
        branch = BranchFactory(tenant=tenant_context)
        sync_session = SyncSessionFactory(tenant=tenant_context, branch=branch)

        pending_op = PendingOperationFactory(
            tenant=tenant_context,
            sync_session=sync_session,
            entity_type="Product",
            operation_type=PendingOperation.OperationType.UPDATE,
            payload={"id": str(uuid.uuid4())},
        )

        resolution = resolver.resolve(pending_op, None)

        result_dict = resolution.to_dict()

        assert isinstance(result_dict, dict)
        assert "action" in result_dict
        assert "merged_payload" in result_dict
        assert "audit_log" in result_dict
        assert "resolution_rule" in result_dict
        assert "resolved_at" in result_dict


@pytest.mark.django_db
class TestConflictScenarioFactoryIntegration:
    """Integration tests using ConflictScenarioFactory."""

    @pytest.fixture
    def resolver(self):
        return ConflictResolver()

    def test_all_scenarios_resolve_successfully(self, resolver, tenant_context):
        """Verify all ConflictScenarioFactory scenarios resolve without error."""
        scenarios = ConflictScenarioFactory.create_all_scenarios(tenant_context)

        for scenario_name, scenario in scenarios.items():
            # Handle different scenario structures
            if scenario_name == "additive":
                # Additive has create_operation and delete_operation
                pending_op = scenario["create_operation"]
                server_data = None
            else:
                pending_op = scenario["pending_operation"]
                server_data = scenario.get("server_data")

            resolution = resolver.resolve(pending_op, server_data)

            assert resolution is not None, f"Failed to resolve {scenario_name}"
            assert resolution.action in [
                ResolutionAction.APPLY,
                ResolutionAction.REJECT,
                ResolutionAction.MERGE,
                ResolutionAction.SERVER_OVERRIDE,
            ], f"Invalid action for {scenario_name}"
