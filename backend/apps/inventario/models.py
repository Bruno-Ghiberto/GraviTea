"""
Inventory models for Gravitea ERP.

Provides Product and StockMovement models with tenant isolation
and immutable ledger pattern for stock tracking.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.db import models

from apps.core.encryption.fields import (BlindIndexField, EncryptedCharField,
                                         EncryptedTextField)
from apps.core.encryption.utils import compute_blind_index
from apps.core.fields import (STOCK_MOVEMENT_TYPE_ENUM, MoneyField,
                              PostgresEnumField)
from apps.core.managers.tenant_bound import (AllObjectsManager,
                                             TenantBoundManager)
from apps.core.models.branch import Branch
from apps.core.models.mixins import TenantBoundModel
from apps.core.models.tenant import Tenant


class ProductCategory(TenantBoundModel):
    """
    Hierarchical product categorization.

    Self-referential parent relationship allows nested category trees.

    Attributes:
        id: UUID primary key
        tenant_id: Parent tenant (via TenantBoundModel)
        name: Category name
        parent: Parent category (null for root categories)
        created_at: Record creation timestamp
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="product_categories",
    )
    name = models.CharField(max_length=100, help_text="Category name")
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        help_text="Parent category (null for root categories)",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = TenantBoundManager()
    all_objects = AllObjectsManager()

    class Meta:
        db_table = "product_category"
        ordering = ["name"]
        verbose_name = "Product Category"
        verbose_name_plural = "Product Categories"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "name"], name="unique_category_per_tenant"
            ),
        ]

    def __str__(self) -> str:
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name

    def save(self, *args: object, **kwargs: object) -> None:
        """Set tenant_id from tenant."""
        if self.tenant_id is None and hasattr(self, "tenant") and self.tenant:
            self.tenant_id = self.tenant.id
        super().save(*args, **kwargs)


# Supplier has been migrated to apps.compras.models (T005-T007).
# Re-export for backward compatibility during transition.
from apps.compras.models import Supplier  # noqa: F401


class PriceList(TenantBoundModel):
    """
    Price list definitions.

    Multiple price lists enable different pricing strategies
    (retail, wholesale, VIP, etc.).

    Attributes:
        id: UUID primary key
        tenant_id: Parent tenant (via TenantBoundModel)
        name: Price list name
        margin_pct: Default margin percentage
        is_default: Default price list flag
        created_at: Record creation timestamp
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="price_lists",
    )
    name = models.CharField(max_length=100, help_text="Price list name")
    margin_pct = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True, help_text="Default margin percentage"
    )
    is_default = models.BooleanField(
        default=False, db_index=True, help_text="Default price list flag"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = TenantBoundManager()
    all_objects = AllObjectsManager()

    class Meta:
        db_table = "price_list"
        ordering = ["name"]
        verbose_name = "Price List"
        verbose_name_plural = "Price Lists"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "name"], name="unique_pricelist_per_tenant"
            ),
            # H-004: Prevent two default price lists per tenant at the DB level.
            # The application-level unset in save() is racy under concurrency;
            # this partial unique index is the authoritative guard.
            models.UniqueConstraint(
                fields=["tenant_id"],
                condition=models.Q(is_default=True),
                name="unique_default_pricelist_per_tenant",
            ),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args: object, **kwargs: object) -> None:
        """Set tenant_id and enforce single default price list."""
        if self.tenant_id is None and hasattr(self, "tenant") and self.tenant:
            self.tenant_id = self.tenant.id

        # If this is being set as default, unset other defaults
        if self.is_default:
            PriceList.objects.filter(tenant_id=self.tenant_id, is_default=True).update(
                is_default=False
            )

        super().save(*args, **kwargs)


class Product(TenantBoundModel):
    """
    Product catalog entry within a tenant.

    Attributes:
        id: UUID primary key
        tenant_id: Parent tenant (via TenantBoundModel)
        sku: Stock Keeping Unit (unique per tenant)
        barcode: Optional barcode (encrypted for PII protection)
        barcode_blind_idx: Blind index for barcode searches
        name: Product display name
        description: Optional product description
        category: Product category (FK to ProductCategory)
        supplier: Default supplier (FK to Supplier)
        unit_price: Default selling price
        cost_price: Last known cost
        tax_rate: VAT rate (default 21% for Argentina)
        min_stock: Minimum stock level for reorder alerts
        max_stock: Maximum stock level
        custom_data: Tenant-defined custom fields (JSON)
        ml_tags: ML-generated categorization tags (JSON)
        is_active: Active/available for sale flag
        created_at: Record creation timestamp
        updated_at: Last modification timestamp
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="products",
    )
    sku = models.CharField(
        max_length=50, db_index=True, help_text="Stock Keeping Unit (unique per tenant)"
    )
    barcode = EncryptedCharField(
        max_length=255, null=True, blank=True, help_text="Product barcode (encrypted)"
    )
    barcode_blind_idx = BlindIndexField(
        null=True, blank=True, db_index=True, help_text="Blind index for barcode searches"
    )
    name = models.CharField(max_length=255, help_text="Product display name")
    description = models.TextField(null=True, blank=True, help_text="Product description")
    category = models.ForeignKey(
        ProductCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
        help_text="Product category",
    )
    supplier = models.ForeignKey(
        "gravitea_compras.Supplier",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
        help_text="Default supplier",
    )
    unit_price = MoneyField(help_text="Default selling price")
    cost_price = MoneyField(help_text="Last known cost price")
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("21.00"),
        help_text="VAT rate percentage (default 21% for Argentina)",
    )
    min_stock = models.DecimalField(
        max_digits=16,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Minimum stock level for reorder alerts",
    )
    max_stock = models.DecimalField(
        max_digits=16, decimal_places=4, null=True, blank=True, help_text="Maximum stock level"
    )
    custom_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Tenant-defined custom fields. Validated against TenantFieldDefinition.",
    )
    ml_tags = models.JSONField(
        default=dict,
        blank=True,
        help_text="""
        ML-generated categorization and predictive analytics metadata.

        Expected schema for ML predictions:
        {
            "category_auto": "string - auto-detected product category",
            "seasonality": "string - seasonal pattern (e.g., 'summer', 'winter',
                           'spring', 'fall', 'all_year')",
            "price_sensitivity": "string - price sensitivity level
                                 ('high', 'medium', 'low')",
            "demand_pattern": "string - demand pattern classification
                              ('steady', 'volatile', 'trending_up', 'trending_down',
                              'seasonal', 'sporadic')",
            "reorder_prediction": "float - predicted days until reorder needed",
            "predictions": {
                "demand": {
                    "next_7_days": "int - predicted demand for next week",
                    "next_30_days": "int - predicted demand for next month",
                    "confidence": "float - confidence score (0.0-1.0)"
                },
                "reorder": {
                    "days_until_stockout": "int - predicted days until stockout",
                    "recommended_quantity": "int - AI-recommended reorder quantity",
                    "confidence": "float - confidence score (0.0-1.0)"
                }
            },
            "seasonality_data": {
                "pattern": "string - detected seasonal pattern",
                "peak_months": ["list of int - peak demand months (1-12)"],
                "multipliers": {
                    "month_name": "float - seasonal demand multiplier"
                }
            },
            "metadata": {
                "last_updated": "string - ISO 8601 timestamp of last ML update",
                "model_version": "string - ML model version used",
                "accuracy_score": "float - model accuracy score (0.0-1.0)"
            }
        }

        Note: This field is populated by ML services and should not be manually
        edited in most cases. The schema may evolve as new ML models are deployed.
        Empty dict {} is valid and indicates no ML analysis has been performed yet.
        """,
    )
    is_active = models.BooleanField(
        default=True, db_index=True, help_text="Active/available for sale"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantBoundManager()
    all_objects = AllObjectsManager()

    class Meta:
        db_table = "product"
        ordering = ["name"]
        verbose_name = "Product"
        verbose_name_plural = "Products"
        constraints = [
            models.UniqueConstraint(fields=["tenant_id", "sku"], name="unique_sku_per_tenant"),
        ]
        indexes = [
            models.Index(
                fields=["tenant_id", "category", "is_active"], name="idx_product_category"
            ),
            # Partial index for active products - optimizes product list queries
            models.Index(
                fields=["tenant_id", "is_active"],
                name="idx_product_tenant_active",
                condition=models.Q(is_active=True),
            ),
            GinIndex(
                fields=["custom_data"],
                name="idx_product_custom_data",
                opclasses=["jsonb_path_ops"],
            ),
        ]

    def __str__(self) -> str:
        return f"{self.sku} - {self.name}"

    def save(self, *args: object, **kwargs: object) -> None:
        """Set tenant_id and generate blind index for barcode."""
        if self.tenant_id is None and hasattr(self, "tenant") and self.tenant:
            self.tenant_id = self.tenant.id

        # Generate blind index for barcode if set
        if self.barcode and not self.barcode_blind_idx:
            self.barcode_blind_idx = compute_blind_index(self.barcode)

        super().save(*args, **kwargs)


class ProductPriceHistory(models.Model):
    """
    Price history tracking (SCD Type 2).

    Maintains complete audit trail of price changes across price lists.
    Each price change creates a new record with valid_from/valid_to range.

    Attributes:
        id: UUID primary key
        product: Product (FK to Product)
        price_list: Price list (FK to PriceList)
        price: Price value
        valid_from: Start of validity period
        valid_to: End of validity period (null for current price)
        change_reason: Reason for price change
        changed_by_user: User who made the change
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="price_history", help_text="Product"
    )
    price_list = models.ForeignKey(
        PriceList, on_delete=models.CASCADE, related_name="price_history", help_text="Price list"
    )
    price = MoneyField(help_text="Price value")
    valid_from = models.DateTimeField(db_index=True, help_text="Start of validity period")
    valid_to = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="End of validity period (null for current price)",
    )
    change_reason = models.CharField(
        max_length=255, null=True, blank=True, help_text="Reason for price change"
    )
    changed_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="price_changes",
        help_text="User who made the change",
    )

    class Meta:
        db_table = "product_price_history"
        ordering = ["-valid_from"]
        verbose_name = "Product Price History"
        verbose_name_plural = "Product Price History"
        indexes = [
            models.Index(
                fields=["product_id", "price_list_id", "valid_from"],
                name="idx_price_history_validity",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.product.sku} - {self.price_list.name}: {self.price} ({self.valid_from})"


class ProductCostHistory(models.Model):
    """
    Cost history tracking.

    Maintains audit trail of cost changes for COGS calculations
    and inventory valuation.

    Attributes:
        id: UUID primary key
        product: Product (FK to Product)
        cost: Cost value
        valid_from: Start of validity period
        valid_to: End of validity period (null for current cost)
        source_doc: Source document reference (PO, invoice, etc.)
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="cost_history", help_text="Product"
    )
    cost = MoneyField(help_text="Cost value")
    valid_from = models.DateTimeField(db_index=True, help_text="Start of validity period")
    valid_to = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="End of validity period (null for current cost)",
    )
    source_doc = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Source document reference (PO, invoice, etc.)",
    )

    class Meta:
        db_table = "product_cost_history"
        ordering = ["-valid_from"]
        verbose_name = "Product Cost History"
        verbose_name_plural = "Product Cost History"
        indexes = [
            models.Index(fields=["product_id", "valid_from"], name="idx_cost_history_validity"),
        ]

    def __str__(self) -> str:
        return f"{self.product.sku}: {self.cost} ({self.valid_from})"


class StockMovement(TenantBoundModel):
    """
    Immutable stock movement ledger entry.

    Each movement records a change in stock level. Movements are
    append-only and cannot be modified or deleted (immutable ledger pattern).

    Movement Types (matching PostgreSQL ENUM stock_movement_type_enum):
        SALE: Stock sold to customer
        PURCHASE: Stock received from supplier
        ADJ: Manual stock adjustment
        TRANS_IN: Stock transferred from another branch
        TRANS_OUT: Stock transferred to another branch

    Attributes:
        id: UUID primary key
        tenant_id: Parent tenant (via TenantBoundModel)
        product: Product being moved
        branch: Branch where movement occurred
        type: Type of movement (uses PostgreSQL ENUM)
        quantity_delta: Quantity moved (positive for in, negative for out)
        cost_snapshot: Cost per unit at time of movement
        reference_id: External reference (invoice, PO, etc.)
        notes: Optional movement notes
        created_at: Movement timestamp (immutable)
    """

    # Match PostgreSQL ENUM: stock_movement_type_enum
    class MovementType(models.TextChoices):
        SALE = "SALE", "Sale"
        PURCHASE = "PURCHASE", "Purchase"
        ADJ = "ADJ", "Adjustment"
        TRANS_IN = "TRANS_IN", "Transfer In"
        TRANS_OUT = "TRANS_OUT", "Transfer Out"

    class StockMovementStatus(models.TextChoices):
        COMMITTED = "COMMITTED", "Comprometido"
        RESERVED = "RESERVED", "Reservado"
        CANCELLED = "CANCELLED", "Cancelado"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="stock_movements",
    )
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, related_name="movements", help_text="Product being moved"
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        related_name="stock_movements",
        help_text="Branch where movement occurred",
    )
    # Column name matches TABLAS.sql: 'type' with PostgreSQL ENUM
    type = PostgresEnumField(
        enum_type=STOCK_MOVEMENT_TYPE_ENUM,
        max_length=20,
        choices=MovementType.choices,
        db_column="type",
        db_index=True,
        help_text="Type of stock movement (PostgreSQL ENUM)",
    )
    # Column name matches TABLAS.sql: 'quantity_delta' instead of 'quantity'
    quantity_delta = models.DecimalField(
        max_digits=16,
        decimal_places=4,
        db_column="quantity_delta",
        help_text="Quantity moved (positive=in, negative=out)",
    )
    # Column name matches TABLAS.sql: 'cost_snapshot' instead of 'unit_cost'
    cost_snapshot = models.DecimalField(
        max_digits=16,
        decimal_places=4,
        null=True,
        blank=True,
        db_column="cost_snapshot",
        help_text="Cost per unit at time of movement",
    )
    reference_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="External reference (SaleID, PurchaseID, etc.)",
    )
    # Movement status lifecycle (T012-T013)
    status = models.CharField(
        max_length=10,
        choices=StockMovementStatus.choices,
        default=StockMovementStatus.COMMITTED,
        db_index=True,
        help_text="COMMITTED=final, RESERVED=pending sale, CANCELLED=released",
    )

    # Cross-module FKs (T014-T015)
    sale_order = models.ForeignKey(
        "gravitea_ventas.SaleOrder",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="stock_movements",
        help_text="Originating sale order",
    )
    comprobante = models.ForeignKey(
        "gravitea_facturacion.Comprobante",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="stock_movements",
        help_text="Linked authorized invoice",
    )

    notes = models.TextField(null=True, blank=True, help_text="Movement notes")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    # Note: TABLAS.sql doesn't have created_by column - omitting it

    objects = TenantBoundManager()
    all_objects = AllObjectsManager()

    class Meta:
        db_table = "stock_movement"
        ordering = ["-created_at"]
        verbose_name = "Stock Movement"
        verbose_name_plural = "Stock Movements"
        indexes = [
            models.Index(
                fields=["tenant_id", "product_id", "created_at"], name="idx_movement_product_date"
            ),
            models.Index(
                fields=["tenant_id", "branch_id", "created_at"], name="idx_movement_branch_date"
            ),
            # Optimized index for tenant-scoped time queries
            models.Index(
                fields=["tenant_id", "-created_at"], name="idx_movement_tenant_created"
            ),
            # Composite index for available stock queries (T017)
            models.Index(
                fields=["tenant_id", "status", "product_id"],
                name="idx_mvmt_tenant_status_prod",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.type}: {self.product.sku} x {self.quantity_delta}"

    def save(self, *args: object, **kwargs: object) -> None:
        """
        Enforce immutability with limited mutability for RESERVED movements.

        - COMMITTED and CANCELLED movements are fully immutable.
        - RESERVED movements can transition to COMMITTED or CANCELLED only.
        - Only `status` and `comprobante_id` fields may change during transition.
        """
        if self.tenant_id is None and hasattr(self, "tenant") and self.tenant:
            self.tenant_id = self.tenant.id

        if self.pk and StockMovement.all_objects.filter(pk=self.pk).exists():
            existing = StockMovement.all_objects.get(pk=self.pk)

            # Allow ONLY status transitions from RESERVED
            if existing.status != self.StockMovementStatus.RESERVED:
                raise ValueError(
                    "Stock movements are immutable and cannot be modified. "
                    "Create a new adjustment movement instead."
                )

            # Only COMMITTED and CANCELLED are valid targets from RESERVED
            allowed_transitions = {
                self.StockMovementStatus.COMMITTED,
                self.StockMovementStatus.CANCELLED,
            }
            if self.status not in allowed_transitions:
                raise ValueError(
                    f"Invalid status transition: {existing.status} → {self.status}. "
                    f"RESERVED can only transition to COMMITTED or CANCELLED."
                )

            # Prevent changing any fields except status and comprobante_id
            for field in self._meta.get_fields():
                if hasattr(field, "attname") and field.attname not in (
                    "status",
                    "comprobante_id",
                ):
                    old_val = getattr(existing, field.attname, None)
                    new_val = getattr(self, field.attname, None)
                    if old_val != new_val:
                        raise ValueError(
                            f"Cannot modify field '{field.attname}' on stock movement. "
                            f"Only status and comprobante transitions are allowed."
                        )

        # Validate FK tenant references
        self._validate_tenant_references()

        super().save(*args, **kwargs)

    def delete(self, *args: object, **kwargs: object) -> None:
        """Prevent deletion of stock movements (immutable ledger)."""
        raise ValueError(
            "Stock movements cannot be deleted. " "Create a reversal movement instead."
        )


class StockSnapshot(models.Model):
    """
    Current stock level per product per branch.

    Maps to TABLAS.sql: stock_snapshot table.
    This is a materialized view of stock movements for efficient
    stock queries. Updated via triggers on StockMovement.

    Note: This table does NOT have tenant_id directly - it uses
    branch_id → branch.tenant_id for tenant isolation.

    Attributes:
        id: UUID primary key
        product: Product
        branch: Branch (provides tenant context)
        quantity: Current stock quantity
        reserved_quantity: Reserved stock (pending orders)
        last_updated: Last update timestamp
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    branch = models.ForeignKey(
        Branch, on_delete=models.CASCADE, related_name="stock_snapshots", help_text="Branch"
    )
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="stock_snapshots", help_text="Product"
    )
    quantity = models.DecimalField(
        max_digits=16,
        decimal_places=4,
        default=Decimal("0.0000"),
        help_text="Current stock quantity",
    )
    reserved_quantity = models.DecimalField(
        max_digits=16,
        decimal_places=4,
        default=Decimal("0.0000"),
        help_text="Reserved stock (pending orders)",
    )
    last_updated = models.DateTimeField(auto_now=True, help_text="Timestamp of last update")

    class Meta:
        db_table = "stock_snapshot"
        verbose_name = "Stock Snapshot"
        verbose_name_plural = "Stock Snapshots"
        constraints = [
            models.UniqueConstraint(fields=["branch_id", "product_id"], name="uq_stock_snapshot"),
        ]
        indexes = [
            # Explicit index for branch+product lookups (complements unique constraint)
            models.Index(fields=["branch_id", "product_id"], name="idx_stock_branch_product"),
        ]

    def __str__(self) -> str:
        return f"{self.product.sku} @ {self.branch.name}: {self.quantity}"

    @property
    def available_quantity(self) -> Decimal:
        """Stock available for sale (quantity - reserved)."""
        return self.quantity - self.reserved_quantity

    @property
    def tenant_id(self) -> uuid.UUID:
        """Get tenant_id from branch for compatibility."""
        return self.branch.tenant_id


# Alias for backward compatibility
BranchStock = StockSnapshot
