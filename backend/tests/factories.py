"""
Model factories for Gravitea ERP testing.

Provides factory_boy factories for all models with proper relationships,
tenant isolation, and encrypted field handling.

Usage:
    from tests.factories import TenantFactory, ProductFactory

    tenant = TenantFactory()
    product = ProductFactory(tenant=tenant)
"""

import random
import uuid
from datetime import timedelta
from decimal import Decimal

import factory
from django.utils import timezone
from factory.django import DjangoModelFactory

from apps.auth.models import AppUser, Role
from apps.core.models import Branch, Tenant
from apps.compras.models import Supplier
from apps.inventario.models import (PriceList, Product, ProductCategory,
                                    ProductCostHistory, ProductPriceHistory,
                                    StockMovement, StockSnapshot)
from apps.sync.models import PendingOperation, SyncSession

# ============================================================
# Core Model Factories
# ============================================================


class TenantFactory(DjangoModelFactory):
    """Factory for Tenant model."""

    class Meta:
        model = Tenant
        django_get_or_create = ("name",)

    id = factory.LazyFunction(uuid.uuid4)
    name = factory.Sequence(lambda n: f"Test Company {n}")
    tax_id = factory.Sequence(lambda n: f"27-{12345678 + n}-9")
    fiscal_config_public = factory.LazyFunction(
        lambda: {
            "punto_venta": 1,
            "condicion_iva": "Responsable Inscripto",
        }
    )
    fiscal_secrets_ref = factory.Sequence(
        lambda n: f"projects/gravitea-erp/secrets/tenant-{n}/versions/latest"
    )
    plan_type = "FREE"
    valid_until = None
    is_active = True


class BranchFactory(DjangoModelFactory):
    """Factory for Branch model."""

    class Meta:
        model = Branch

    id = factory.LazyFunction(uuid.uuid4)
    tenant = factory.SubFactory(TenantFactory)
    name = factory.Sequence(lambda n: f"Branch {n}")
    address = factory.Sequence(lambda n: f"{100 + n} Main Street, Buenos Aires")
    phone = factory.Sequence(lambda n: f"+54-11-{4000 + n}-{5000 + n}")
    coordinates = factory.LazyFunction(
        lambda: {
            "lat": -34.6037 + random.uniform(-0.1, 0.1),
            "lng": -58.3816 + random.uniform(-0.1, 0.1),
        }
    )
    afip_pos_number = factory.Sequence(lambda n: n + 1)
    is_active = True


# ============================================================
# Authentication Model Factories
# ============================================================


class RoleFactory(DjangoModelFactory):
    """Factory for Role model."""

    class Meta:
        model = Role

    id = factory.LazyFunction(uuid.uuid4)
    tenant = factory.SubFactory(TenantFactory)
    name = factory.Sequence(lambda n: f"Role {n}")
    permissions = factory.LazyFunction(
        lambda: [
            "inventory.read",
            "inventory.write",
            "sales.read",
            "sales.write",
        ]
    )


class AdminRoleFactory(RoleFactory):
    """Factory for admin role with all permissions."""

    name = "Administrator"
    permissions = factory.LazyFunction(
        lambda: [
            "inventory.read",
            "inventory.write",
            "inventory.create",
            "inventory.delete",
            "inventory.admin",
            "sales.read",
            "sales.write",
            "sales.create",
            "sales.delete",
            "sales.admin",
            "purchases.read",
            "purchases.write",
            "purchases.create",
            "purchases.delete",
            "purchases.admin",
            "customers.read",
            "customers.write",
            "customers.create",
            "customers.delete",
            "customers.admin",
            "reports.read",
            "reports.write",
            "reports.create",
            "reports.delete",
            "reports.admin",
            "settings.read",
            "settings.write",
            "settings.create",
            "settings.delete",
            "settings.admin",
        ]
    )


class SalesRoleFactory(RoleFactory):
    """Factory for sales role with limited permissions."""

    name = "Sales"
    permissions = factory.LazyFunction(
        lambda: [
            "inventory.read",
            "sales.read",
            "sales.write",
            "sales.create",
            "customers.read",
            "customers.write",
            "customers.create",
        ]
    )


class AppUserFactory(DjangoModelFactory):
    """Factory for AppUser model."""

    class Meta:
        model = AppUser

    id = factory.LazyFunction(uuid.uuid4)
    tenant = factory.SubFactory(TenantFactory)
    email = factory.Sequence(lambda n: f"user{n}@testcompany.com")
    full_name = factory.Sequence(lambda n: f"Test User {n}")
    role = factory.SubFactory(RoleFactory, tenant=factory.SelfAttribute("..tenant"))
    default_branch = factory.SubFactory(BranchFactory, tenant=factory.SelfAttribute("..tenant"))
    is_active = True

    @factory.post_generation
    def password(obj, create, extracted, **kwargs):
        """Set password after user creation."""
        if not create:
            return
        password = extracted or "TestPassword123!"
        obj.set_password(password)
        obj.save()


class AdminUserFactory(AppUserFactory):
    """Factory for admin user with admin role."""

    email = factory.Sequence(lambda n: f"admin{n}@testcompany.com")
    full_name = factory.Sequence(lambda n: f"Admin User {n}")
    role = factory.SubFactory(AdminRoleFactory, tenant=factory.SelfAttribute("..tenant"))


# ============================================================
# Inventory Model Factories
# ============================================================


class ProductCategoryFactory(DjangoModelFactory):
    """Factory for ProductCategory model."""

    class Meta:
        model = ProductCategory

    id = factory.LazyFunction(uuid.uuid4)
    tenant = factory.SubFactory(TenantFactory)
    name = factory.Sequence(lambda n: f"Category {n}")
    parent = None


class ChildCategoryFactory(ProductCategoryFactory):
    """Factory for child product category."""

    parent = factory.SubFactory(ProductCategoryFactory, tenant=factory.SelfAttribute("..tenant"))


class SupplierFactory(DjangoModelFactory):
    """Factory for Supplier model with encrypted PII fields."""

    class Meta:
        model = Supplier

    id = factory.LazyFunction(uuid.uuid4)
    tenant = factory.SubFactory(TenantFactory)
    name = factory.Sequence(lambda n: f"Supplier {n}")
    # Encrypted fields - factory_boy will handle encryption via model save()
    tax_id_encrypted = factory.Sequence(lambda n: f"30-{70000000 + n}-5")
    contact_info_encrypted = factory.Sequence(
        lambda n: f"Contact: {n}, Phone: +54-11-{4000 + n}-0000"
    )
    email_encrypted = factory.Sequence(lambda n: f"supplier{n}@example.com")
    address_encrypted = factory.Sequence(lambda n: f"Av. Supplier {n}, CABA, Argentina")
    lead_time_days = factory.Faker("random_int", min=1, max=30)
    current_balance = Decimal("0.000")
    is_active = True


class PriceListFactory(DjangoModelFactory):
    """Factory for PriceList model."""

    class Meta:
        model = PriceList

    id = factory.LazyFunction(uuid.uuid4)
    tenant = factory.SubFactory(TenantFactory)
    name = factory.Sequence(lambda n: f"Price List {n}")
    margin_pct = Decimal("20.00")
    is_default = False


class DefaultPriceListFactory(PriceListFactory):
    """Factory for default price list."""

    name = "Default Price List"
    is_default = True


class ProductFactory(DjangoModelFactory):
    """Factory for Product model."""

    class Meta:
        model = Product

    id = factory.LazyFunction(uuid.uuid4)
    tenant = factory.SubFactory(TenantFactory)
    sku = factory.Sequence(lambda n: f"PROD-{n:06d}")
    barcode = factory.Sequence(lambda n: f"{7890000000000 + n}")
    name = factory.Sequence(lambda n: f"Product {n}")
    description = factory.Faker("text", max_nb_chars=200)
    category = factory.SubFactory(ProductCategoryFactory, tenant=factory.SelfAttribute("..tenant"))
    supplier = factory.SubFactory(SupplierFactory, tenant=factory.SelfAttribute("..tenant"))
    unit_price = Decimal("100.000")
    cost_price = Decimal("50.000")
    tax_rate = Decimal("21.00")
    min_stock = Decimal("10.0000")
    max_stock = Decimal("1000.0000")
    custom_data = factory.LazyFunction(
        lambda: {
            "color": "Blue",
            "size": "Medium",
            "weight": 1.5,
        }
    )
    ml_tags = factory.LazyFunction(lambda: {})
    is_active = True


class ProductWithMLTagsFactory(ProductFactory):
    """Factory for Product with ML predictions."""

    ml_tags = factory.LazyFunction(
        lambda: {
            "category_auto": "Electronics",
            "seasonality": "all_year",
            "price_sensitivity": "medium",
            "demand_pattern": "steady",
            "predictions": {
                "demand": {
                    "next_7_days": 50,
                    "next_30_days": 200,
                    "confidence": 0.85,
                },
                "reorder": {
                    "days_until_stockout": 15,
                    "recommended_quantity": 100,
                    "confidence": 0.78,
                },
            },
            "metadata": {
                "last_updated": timezone.now().isoformat(),
                "model_version": "1.0.0",
                "accuracy_score": 0.82,
            },
        }
    )


class ProductPriceHistoryFactory(DjangoModelFactory):
    """Factory for ProductPriceHistory model."""

    class Meta:
        model = ProductPriceHistory

    id = factory.LazyFunction(uuid.uuid4)
    product = factory.SubFactory(ProductFactory)
    price_list = factory.SubFactory(
        PriceListFactory, tenant=factory.SelfAttribute("..product.tenant")
    )
    price = Decimal("100.000")
    valid_from = factory.LazyFunction(timezone.now)
    valid_to = None
    change_reason = factory.Faker("sentence", nb_words=6)
    changed_by_user = factory.SubFactory(
        AppUserFactory, tenant=factory.SelfAttribute("..product.tenant")
    )


class ProductCostHistoryFactory(DjangoModelFactory):
    """Factory for ProductCostHistory model."""

    class Meta:
        model = ProductCostHistory

    id = factory.LazyFunction(uuid.uuid4)
    product = factory.SubFactory(ProductFactory)
    cost = Decimal("50.000")
    valid_from = factory.LazyFunction(timezone.now)
    valid_to = None
    source_doc = factory.Sequence(lambda n: f"PO-{n:06d}")


class StockMovementFactory(DjangoModelFactory):
    """Factory for StockMovement model (immutable ledger)."""

    class Meta:
        model = StockMovement

    id = factory.LazyFunction(uuid.uuid4)
    tenant = factory.SubFactory(TenantFactory)
    product = factory.SubFactory(ProductFactory, tenant=factory.SelfAttribute("..tenant"))
    branch = factory.SubFactory(BranchFactory, tenant=factory.SelfAttribute("..tenant"))
    type = StockMovement.MovementType.PURCHASE
    quantity_delta = Decimal("100.0000")
    cost_snapshot = Decimal("50.000")
    reference_id = factory.LazyFunction(uuid.uuid4)
    notes = factory.Faker("sentence", nb_words=8)


class PurchaseMovementFactory(StockMovementFactory):
    """Factory for purchase stock movement."""

    type = StockMovement.MovementType.PURCHASE
    quantity_delta = factory.Faker(
        "pydecimal", left_digits=4, right_digits=4, positive=True, min_value=1, max_value=1000
    )


class SaleMovementFactory(StockMovementFactory):
    """Factory for sale stock movement (negative quantity)."""

    type = StockMovement.MovementType.SALE
    quantity_delta = factory.LazyAttribute(
        lambda obj: -abs(
            Decimal(
                factory.Faker(
                    "pydecimal",
                    left_digits=3,
                    right_digits=4,
                    positive=True,
                    min_value=1,
                    max_value=100,
                ).evaluate(None, None, {})
            )
        )
    )


class AdjustmentMovementFactory(StockMovementFactory):
    """Factory for adjustment stock movement."""

    type = StockMovement.MovementType.ADJ
    quantity_delta = factory.Faker(
        "pydecimal", left_digits=3, right_digits=4, positive=False, min_value=-50, max_value=50
    )


class TransferOutMovementFactory(StockMovementFactory):
    """Factory for transfer out stock movement."""

    type = StockMovement.MovementType.TRANS_OUT
    quantity_delta = factory.LazyAttribute(
        lambda obj: -abs(
            Decimal(
                factory.Faker(
                    "pydecimal",
                    left_digits=3,
                    right_digits=4,
                    positive=True,
                    min_value=1,
                    max_value=100,
                ).evaluate(None, None, {})
            )
        )
    )


class TransferInMovementFactory(StockMovementFactory):
    """Factory for transfer in stock movement."""

    type = StockMovement.MovementType.TRANS_IN
    quantity_delta = factory.Faker(
        "pydecimal", left_digits=3, right_digits=4, positive=True, min_value=1, max_value=100
    )


class StockSnapshotFactory(DjangoModelFactory):
    """Factory for StockSnapshot model."""

    class Meta:
        model = StockSnapshot

    id = factory.LazyFunction(uuid.uuid4)
    branch = factory.SubFactory(BranchFactory)
    product = factory.SubFactory(ProductFactory, tenant=factory.SelfAttribute("..branch.tenant"))
    quantity = Decimal("100.0000")
    reserved_quantity = Decimal("0.0000")


# ============================================================
# Sync Model Factories
# ============================================================


class SyncSessionFactory(DjangoModelFactory):
    """Factory for SyncSession model."""

    class Meta:
        model = SyncSession

    id = factory.LazyFunction(uuid.uuid4)
    tenant = factory.SubFactory(TenantFactory)
    branch = factory.SubFactory(BranchFactory, tenant=factory.SelfAttribute("..tenant"))
    device_id = factory.Sequence(lambda n: f"POS-TERMINAL-{n:03d}")
    last_sync_at = None
    sync_vector = factory.LazyFunction(lambda: {})
    status = SyncSession.SyncStatus.PENDING
    error_message = None


class CompletedSyncSessionFactory(SyncSessionFactory):
    """Factory for completed sync session."""

    status = SyncSession.SyncStatus.COMPLETED
    last_sync_at = factory.LazyFunction(timezone.now)
    sync_vector = factory.LazyFunction(
        lambda: {
            "device": 1,
            "server": 1,
        }
    )


class FailedSyncSessionFactory(SyncSessionFactory):
    """Factory for failed sync session."""

    status = SyncSession.SyncStatus.FAILED
    error_message = factory.Faker("sentence", nb_words=10)


class PendingOperationFactory(DjangoModelFactory):
    """Factory for PendingOperation model."""

    class Meta:
        model = PendingOperation

    id = factory.LazyFunction(uuid.uuid4)
    tenant = factory.SubFactory(TenantFactory)
    sync_session = factory.SubFactory(SyncSessionFactory, tenant=factory.SelfAttribute("..tenant"))
    operation_type = PendingOperation.OperationType.CREATE
    entity_type = "Sale"
    entity_id = factory.LazyFunction(uuid.uuid4)
    payload = factory.LazyFunction(
        lambda: {
            "customer_id": str(uuid.uuid4()),
            "total": "150.50",
            "items": [
                {
                    "product_id": str(uuid.uuid4()),
                    "quantity": 2,
                    "price": "75.25",
                }
            ],
        }
    )
    client_timestamp = factory.LazyFunction(lambda: timezone.now() - timedelta(minutes=5))
    status = PendingOperation.OperationStatus.PENDING
    conflict_data = None
    error_message = None
    processed_at = None


class AppliedOperationFactory(PendingOperationFactory):
    """Factory for applied pending operation."""

    status = PendingOperation.OperationStatus.APPLIED
    processed_at = factory.LazyFunction(timezone.now)


class ConflictOperationFactory(PendingOperationFactory):
    """Factory for conflicting pending operation."""

    status = PendingOperation.OperationStatus.CONFLICT
    conflict_data = factory.LazyFunction(
        lambda: {
            "conflict_type": "concurrent_update",
            "server_version": {
                "updated_at": timezone.now().isoformat(),
                "updated_by": str(uuid.uuid4()),
            },
            "client_version": {
                "updated_at": (timezone.now() - timedelta(minutes=10)).isoformat(),
            },
        }
    )


# ============================================================
# Trait Factories for Common Scenarios
# ============================================================


class InactiveTenantFactory(TenantFactory):
    """Factory for inactive tenant."""

    is_active = False


class ProTenantFactory(TenantFactory):
    """Factory for Pro plan tenant."""

    plan_type = "PRO"
    valid_until = factory.LazyFunction(lambda: timezone.now() + timedelta(days=365))


class EnterpriseTenantFactory(TenantFactory):
    """Factory for Enterprise plan tenant."""

    plan_type = "ENTERPRISE"
    valid_until = factory.LazyFunction(lambda: timezone.now() + timedelta(days=730))


class InactiveProductFactory(ProductFactory):
    """Factory for inactive product."""

    is_active = False


class ExpensiveProductFactory(ProductFactory):
    """Factory for high-value product."""

    unit_price = Decimal("1000.000")
    cost_price = Decimal("500.000")


class LowStockProductFactory(ProductFactory):
    """Factory for low-stock product."""

    min_stock = Decimal("100.0000")
    max_stock = Decimal("500.0000")


# ============================================================
# Conflict Scenario Factory
# ============================================================


class ConflictScenarioFactory:
    """
    Generate conflict scenarios for ConflictResolver testing.

    Creates realistic conflict situations matching the 5 resolution strategies:
    1. SERVER_WINS - Configuration data conflicts
    2. LAST_WRITE_WINS - Inventory level conflicts
    3. ADDITIVE - Sales transaction conflicts
    4. MOST_COMPLETE_WINS - Customer data conflicts
    5. SERVER_ASSIGNS_FINAL - Document numbering conflicts
    """

    @staticmethod
    def server_wins_scenario(tenant, entity_type: str = "Product"):
        """
        Create SERVER_WINS conflict scenario.

        Simulates POS terminal attempting to update configuration data
        that was modified on server (e.g., price change).

        Args:
            tenant: Tenant instance
            entity_type: One of Product, PriceList, Branch, Settings

        Returns:
            dict with pending_operation and server_data
        """
        from apps.sync.models import PendingOperation

        # Create sync session
        branch = BranchFactory(tenant=tenant)
        sync_session = SyncSessionFactory(tenant=tenant, branch=branch)

        # Client payload (old price)
        client_payload = {
            "id": str(uuid.uuid4()),
            "sku": "PROD-001",
            "name": "Test Product",
            "unit_price": "100.000",  # Client has old price
            "cost_price": "50.000",
            "updated_at": (timezone.now() - timedelta(hours=2)).isoformat(),
        }

        # Server data (new price updated centrally)
        server_data = {
            "id": client_payload["id"],
            "sku": "PROD-001",
            "name": "Test Product",
            "unit_price": "120.000",  # Server has new price
            "cost_price": "55.000",
            "updated_at": timezone.now().isoformat(),
        }

        # Create pending operation
        pending_op = PendingOperationFactory(
            tenant=tenant,
            sync_session=sync_session,
            operation_type=PendingOperation.OperationType.UPDATE,
            entity_type=entity_type,
            entity_id=uuid.UUID(client_payload["id"]),
            payload=client_payload,
            client_timestamp=timezone.now() - timedelta(hours=2),
            status=PendingOperation.OperationStatus.CONFLICT,
        )

        return {
            "pending_operation": pending_op,
            "server_data": server_data,
            "expected_action": "SERVER_OVERRIDE",
            "scenario": "Configuration data modified centrally while client offline",
        }

    @staticmethod
    def last_write_wins_scenario(tenant, product=None):
        """
        Create LAST_WRITE_WINS conflict scenario.

        Simulates concurrent stock movements with different timestamps.

        Args:
            tenant: Tenant instance
            product: Product instance (created if None)

        Returns:
            dict with pending_operation and server_data
        """
        from apps.sync.models import PendingOperation

        if product is None:
            product = ProductFactory(tenant=tenant)

        branch = BranchFactory(tenant=tenant)
        sync_session = SyncSessionFactory(tenant=tenant, branch=branch)

        # Client timestamp (older)
        client_timestamp = timezone.now() - timedelta(minutes=10)

        # Server timestamp (newer)
        server_timestamp = timezone.now() - timedelta(minutes=5)

        # Client payload
        client_payload = {
            "id": str(uuid.uuid4()),
            "product_id": str(product.id),
            "branch_id": str(branch.id),
            "type": "ADJ",
            "quantity_delta": "-5.0000",
            "timestamp": client_timestamp.isoformat(),
        }

        # Server data (newer adjustment)
        server_data = {
            "id": client_payload["id"],
            "product_id": str(product.id),
            "branch_id": str(branch.id),
            "type": "ADJ",
            "quantity_delta": "-3.0000",
            "timestamp": server_timestamp.isoformat(),
        }

        pending_op = PendingOperationFactory(
            tenant=tenant,
            sync_session=sync_session,
            operation_type=PendingOperation.OperationType.UPDATE,
            entity_type="StockMovement",
            entity_id=uuid.UUID(client_payload["id"]),
            payload=client_payload,
            client_timestamp=client_timestamp,
            server_timestamp=server_timestamp,
            status=PendingOperation.OperationStatus.CONFLICT,
        )

        return {
            "pending_operation": pending_op,
            "server_data": server_data,
            "expected_action": "SERVER_OVERRIDE",  # Server is newer
            "scenario": "Concurrent stock adjustments with server version newer",
        }

    @staticmethod
    def additive_scenario(tenant):
        """
        Create ADDITIVE conflict scenario.

        Simulates offline sale creation that should be preserved.

        Args:
            tenant: Tenant instance

        Returns:
            dict with pending_operation for CREATE and DELETE attempts
        """
        from apps.sync.models import PendingOperation

        branch = BranchFactory(tenant=tenant)
        sync_session = SyncSessionFactory(tenant=tenant, branch=branch)
        product = ProductFactory(tenant=tenant)

        sale_id = uuid.uuid4()

        # CREATE operation (should be applied)
        create_payload = {
            "id": str(sale_id),
            "branch_id": str(branch.id),
            "total": "250.50",
            "items": [
                {
                    "product_id": str(product.id),
                    "quantity": 2,
                    "price": "125.25",
                }
            ],
            "timestamp": timezone.now().isoformat(),
        }

        create_op = PendingOperationFactory(
            tenant=tenant,
            sync_session=sync_session,
            operation_type=PendingOperation.OperationType.CREATE,
            entity_type="Sale",
            entity_id=sale_id,
            payload=create_payload,
            client_timestamp=timezone.now() - timedelta(minutes=5),
            status=PendingOperation.OperationStatus.PENDING,
        )

        # DELETE operation (should be rejected)
        delete_op = PendingOperationFactory(
            tenant=tenant,
            sync_session=sync_session,
            operation_type=PendingOperation.OperationType.DELETE,
            entity_type="Sale",
            entity_id=sale_id,
            payload={"id": str(sale_id)},
            client_timestamp=timezone.now(),
            status=PendingOperation.OperationStatus.PENDING,
        )

        return {
            "create_operation": create_op,
            "delete_operation": delete_op,
            "expected_create_action": "APPLY",
            "expected_delete_action": "REJECT",
            "scenario": "Sales are additive - creates allowed, deletes rejected",
        }

    @staticmethod
    def most_complete_wins_scenario(tenant):
        """
        Create MOST_COMPLETE_WINS conflict scenario.

        Simulates customer data merge with partial information on both sides.

        Args:
            tenant: Tenant instance

        Returns:
            dict with pending_operation and server_data for merging
        """
        from apps.sync.models import PendingOperation

        branch = BranchFactory(tenant=tenant)
        sync_session = SyncSessionFactory(tenant=tenant, branch=branch)

        customer_id = uuid.uuid4()

        # Client has email and phone (captured offline)
        client_payload = {
            "id": str(customer_id),
            "name": "John Doe",
            "email": "john.doe@example.com",
            "phone": "+54-11-1234-5678",
            "address": None,
            "tax_id": None,
            "notes": "Captured offline",
        }

        # Server has address and tax_id (updated centrally)
        server_data = {
            "id": str(customer_id),
            "name": "John Doe",
            "email": None,
            "phone": None,
            "address": "Av. Corrientes 1234, CABA",
            "tax_id": "20-12345678-9",
            "notes": "Updated centrally",
        }

        pending_op = PendingOperationFactory(
            tenant=tenant,
            sync_session=sync_session,
            operation_type=PendingOperation.OperationType.UPDATE,
            entity_type="Customer",
            entity_id=customer_id,
            payload=client_payload,
            client_timestamp=timezone.now() - timedelta(hours=1),
            status=PendingOperation.OperationStatus.CONFLICT,
        )

        expected_merge = {
            "id": str(customer_id),
            "name": "John Doe",
            "email": "john.doe@example.com",  # From client (non-null)
            "phone": "+54-11-1234-5678",  # From client (non-null)
            "address": "Av. Corrientes 1234, CABA",  # From server (non-null)
            "tax_id": "20-12345678-9",  # From server (non-null)
            "notes": "Updated centrally",  # Server wins tie (both non-null, server longer)
        }

        return {
            "pending_operation": pending_op,
            "server_data": server_data,
            "expected_action": "MERGE",
            "expected_merge": expected_merge,
            "scenario": "Customer data merge - prefer non-null values, server wins ties",
        }

    @staticmethod
    def server_assigns_final_scenario(tenant):
        """
        Create SERVER_ASSIGNS_FINAL conflict scenario.

        Simulates fiscal document with temporary placeholder numbers
        that need server-assigned final values.

        Args:
            tenant: Tenant instance

        Returns:
            dict with pending_operation requiring server assignment
        """
        from apps.sync.models import PendingOperation

        branch = BranchFactory(tenant=tenant)
        sync_session = SyncSessionFactory(tenant=tenant, branch=branch)

        doc_id = uuid.uuid4()

        # Client payload with temporary placeholders
        client_payload = {
            "id": str(doc_id),
            "branch_id": str(branch.id),
            "document_type": "FACTURA_B",
            "document_number": "TEMP-00001",  # Temporary placeholder
            "cae": "TEMP-CAE-12345",  # Temporary CAE
            "total": "1250.50",
            "items": [
                {
                    "description": "Product A",
                    "quantity": 2,
                    "price": "625.25",
                }
            ],
            "timestamp": timezone.now().isoformat(),
        }

        pending_op = PendingOperationFactory(
            tenant=tenant,
            sync_session=sync_session,
            operation_type=PendingOperation.OperationType.CREATE,
            entity_type="FiscalDocument",
            entity_id=doc_id,
            payload=client_payload,
            client_timestamp=timezone.now() - timedelta(minutes=2),
            status=PendingOperation.OperationStatus.PENDING,
        )

        expected_merge = {
            "id": str(doc_id),
            "branch_id": str(branch.id),
            "document_type": "FACTURA_B",
            "document_number": None,  # Server will assign
            "cae": None,  # Server will assign
            "total": "1250.50",
            "items": client_payload["items"],
            "timestamp": client_payload["timestamp"],
            "_server_assignment_required": ["document_number", "cae"],
        }

        return {
            "pending_operation": pending_op,
            "server_data": None,
            "expected_action": "MERGE",
            "expected_merge": expected_merge,
            "scenario": "Fiscal document with temporary numbers requiring server assignment",
        }

    @staticmethod
    def create_all_scenarios(tenant):
        """
        Create all 5 conflict scenarios for comprehensive testing.

        Args:
            tenant: Tenant instance

        Returns:
            dict with all scenarios keyed by strategy name
        """
        return {
            "server_wins": ConflictScenarioFactory.server_wins_scenario(tenant),
            "last_write_wins": ConflictScenarioFactory.last_write_wins_scenario(tenant),
            "additive": ConflictScenarioFactory.additive_scenario(tenant),
            "most_complete_wins": ConflictScenarioFactory.most_complete_wins_scenario(tenant),
            "server_assigns_final": ConflictScenarioFactory.server_assigns_final_scenario(tenant),
        }


# ============================================================
# Helper Functions
# ============================================================


def create_tenant_with_setup(
    name="Test Company",
    plan_type="FREE",
    num_branches=1,
    num_users=1,
    num_products=5,
):
    """
    Create a complete tenant setup with branches, users, and products.

    Args:
        name: Tenant name
        plan_type: Subscription plan (FREE, PRO, ENTERPRISE)
        num_branches: Number of branches to create
        num_users: Number of users per branch to create
        num_products: Number of products to create

    Returns:
        dict with tenant, branches, users, products, and category
    """
    tenant = TenantFactory(name=name, plan_type=plan_type)

    branches = [BranchFactory(tenant=tenant) for _ in range(num_branches)]

    category = ProductCategoryFactory(tenant=tenant, name="Default Category")

    users = []
    for branch in branches:
        for _ in range(num_users):
            users.append(AppUserFactory(tenant=tenant, default_branch=branch))

    products = [ProductFactory(tenant=tenant, category=category) for _ in range(num_products)]

    return {
        "tenant": tenant,
        "branches": branches,
        "users": users,
        "products": products,
        "category": category,
    }


def create_stock_scenario(tenant=None, branch=None, product=None, initial_stock=100):
    """
    Create a complete stock scenario with movements and snapshots.

    Args:
        tenant: Tenant instance (created if None)
        branch: Branch instance (created if None)
        product: Product instance (created if None)
        initial_stock: Initial stock quantity

    Returns:
        dict with tenant, branch, product, movements, and snapshot
    """
    if tenant is None:
        tenant = TenantFactory()

    if branch is None:
        branch = BranchFactory(tenant=tenant)

    if product is None:
        product = ProductFactory(tenant=tenant)

    # Create purchase movement for initial stock
    purchase = PurchaseMovementFactory(
        tenant=tenant,
        product=product,
        branch=branch,
        quantity_delta=Decimal(str(initial_stock)),
    )

    # Create snapshot
    snapshot = StockSnapshotFactory(
        branch=branch,
        product=product,
        quantity=Decimal(str(initial_stock)),
    )

    return {
        "tenant": tenant,
        "branch": branch,
        "product": product,
        "movements": [purchase],
        "snapshot": snapshot,
    }
