"""
Compras (Purchases) models for Gravitea ERP.

Provides Supplier (migrated from inventario), PurchaseOrder with state machine,
PurchaseOrderItem, GoodsReceipt, and GoodsReceiptLine models with tenant isolation
and immutable ledger patterns.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.db import models

from apps.core.encryption.fields import EncryptedCharField, EncryptedTextField
from apps.core.encryption.utils import compute_blind_index
from apps.core.fields import MoneyField
from apps.core.managers.tenant_bound import AllObjectsManager, TenantBoundManager
from apps.core.models.mixins import TenantBoundModel
from apps.core.models.tenant import Tenant


# ============================================================
# Supplier (migrated from inventario — T005)
# ============================================================


class Supplier(TenantBoundModel):
    """
    Vendor/supplier with encrypted PII fields.

    Migrated from apps.inventario via SeparateDatabaseAndState.
    The database table remains 'supplier' (no rename).

    Attributes:
        id: UUID primary key
        tenant_id: Parent tenant (via TenantBoundModel)
        name: Supplier name
        tax_id_encrypted: Encrypted tax identification number
        tax_id_hash: Blind index for tax_id searches
        contact_info_encrypted: Encrypted contact information
        email_encrypted: Encrypted email address
        email_hash: Blind index for email searches
        address_encrypted: Encrypted physical address
        lead_time_days: Expected delivery lead time in days
        current_balance: Current account balance (payables)
        is_active: Active/available flag
        custom_data: Tenant-defined custom fields (JSON)
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
        related_name="suppliers",
    )
    name = models.CharField(max_length=255, help_text="Supplier name")
    tax_id_encrypted = EncryptedCharField(
        max_length=50, null=True, blank=True, help_text="Encrypted tax identification number"
    )
    tax_id_hash = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        db_index=True,
        help_text="Blind index for tax_id searches",
    )
    contact_info_encrypted = EncryptedTextField(
        null=True, blank=True, help_text="Encrypted contact information"
    )
    email_encrypted = EncryptedCharField(
        max_length=255, null=True, blank=True, help_text="Encrypted email address"
    )
    email_hash = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        db_index=True,
        help_text="Blind index for email searches",
    )
    address_encrypted = EncryptedTextField(
        null=True, blank=True, help_text="Encrypted physical address"
    )
    lead_time_days = models.IntegerField(
        null=True, blank=True, help_text="Expected delivery lead time in days"
    )
    current_balance = MoneyField(
        default=Decimal("0.000"), help_text="Current account balance (payables)"
    )
    is_active = models.BooleanField(default=True, db_index=True, help_text="Active/available flag")
    custom_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Tenant-defined custom fields. Validated against TenantFieldDefinition.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = TenantBoundManager()
    all_objects = AllObjectsManager()

    class Meta:
        db_table = "supplier"
        ordering = ["name"]
        verbose_name = "Supplier"
        verbose_name_plural = "Suppliers"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "name"], name="unique_supplier_per_tenant"
            ),
        ]
        indexes = [
            GinIndex(
                fields=["custom_data"],
                name="idx_supplier_custom_data",
                opclasses=["jsonb_path_ops"],
            ),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args: object, **kwargs: object) -> None:
        """Set tenant_id and compute blind indexes for encrypted fields."""
        if self.tenant_id is None and hasattr(self, "tenant") and self.tenant:
            self.tenant_id = self.tenant.id

        # Generate blind index for tax_id if set
        if self.tax_id_encrypted and not self.tax_id_hash:
            self.tax_id_hash = compute_blind_index(self.tax_id_encrypted)

        # Generate blind index for email if set
        if self.email_encrypted and not self.email_hash:
            self.email_hash = compute_blind_index(self.email_encrypted)

        super().save(*args, **kwargs)


# ============================================================
# PurchaseOrder (T015)
# ============================================================


class PurchaseOrderStatus(models.TextChoices):
    DRAFT = "DRAFT", "Borrador"
    CONFIRMED = "CONFIRMED", "Confirmado"
    PARTIAL_RECEIVED = "PARTIAL_RECEIVED", "Parcialmente Recibida"
    RECEIVED = "RECEIVED", "Recibida"
    CANCELLED = "CANCELLED", "Cancelada"


PURCHASE_ORDER_TRANSITIONS: dict[str, set[str]] = {
    PurchaseOrderStatus.DRAFT: {PurchaseOrderStatus.CONFIRMED, PurchaseOrderStatus.CANCELLED},
    PurchaseOrderStatus.CONFIRMED: {
        PurchaseOrderStatus.PARTIAL_RECEIVED,
        PurchaseOrderStatus.CANCELLED,
    },
    PurchaseOrderStatus.PARTIAL_RECEIVED: {
        PurchaseOrderStatus.RECEIVED,
        PurchaseOrderStatus.CANCELLED,
    },
    PurchaseOrderStatus.RECEIVED: set(),
    PurchaseOrderStatus.CANCELLED: set(),
}

# Fields mutable per state (for ViewSet enforcement)
MUTABLE_FIELDS_BY_STATUS: dict[str, set[str]] = {
    PurchaseOrderStatus.DRAFT: {
        "supplier",
        "order_number",
        "order_date",
        "expected_delivery_date",
        "notes",
        "custom_data",
        "items",
    },
    PurchaseOrderStatus.CONFIRMED: {"notes", "expected_delivery_date"},
    PurchaseOrderStatus.PARTIAL_RECEIVED: {"notes"},
    PurchaseOrderStatus.RECEIVED: set(),
    PurchaseOrderStatus.CANCELLED: set(),
}


class PurchaseOrder(TenantBoundModel):
    """
    Purchase order with state-machine lifecycle.

    States: DRAFT → CONFIRMED → PARTIAL_RECEIVED → RECEIVED
    Cancellation: DRAFT|CONFIRMED|PARTIAL_RECEIVED → CANCELLED
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="purchase_orders",
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.RESTRICT,
        related_name="purchase_orders",
        help_text="Cannot delete supplier with open POs",
    )
    order_number = models.CharField(
        max_length=32,
        help_text="Unique order number per tenant",
    )
    status = models.CharField(
        max_length=20,
        choices=PurchaseOrderStatus.choices,
        default=PurchaseOrderStatus.DRAFT,
        db_index=True,
    )
    order_date = models.DateField(help_text="Date PO was created")
    expected_delivery_date = models.DateField(
        null=True,
        blank=True,
        help_text="Optional estimated arrival",
    )
    notes = models.TextField(null=True, blank=True)
    custom_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Tenant-defined custom fields. Validated against TenantFieldDefinition.",
    )
    total_amount = MoneyField(
        default=Decimal("0.000"),
        help_text="Sum of line_total values",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantBoundManager()
    all_objects = AllObjectsManager()

    class Meta:
        db_table = "compras_purchaseorder"
        ordering = ["-created_at"]
        verbose_name = "Purchase Order"
        verbose_name_plural = "Purchase Orders"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "order_number"],
                name="unique_po_number_per_tenant",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant_id", "status"], name="idx_po_tenant_status"),
            models.Index(
                fields=["tenant_id", "supplier_id"],
                name="idx_po_tenant_supplier",
            ),
            GinIndex(
                fields=["custom_data"],
                name="idx_po_custom_data",
                opclasses=["jsonb_path_ops"],
            ),
        ]

    def __str__(self) -> str:
        return f"PO-{self.order_number} ({self.status})"

    def can_transition_to(self, new_status: str) -> bool:
        """Check if transition from current status to new_status is valid."""
        return new_status in PURCHASE_ORDER_TRANSITIONS.get(self.status, set())

    def recalculate_total(self) -> None:
        """Recompute total_amount from line items."""
        from django.db.models import Sum

        total = self.items.aggregate(total=Sum("line_total"))["total"] or Decimal("0.000")
        self.total_amount = total
        self.save(update_fields=["total_amount", "updated_at"])


# ============================================================
# PurchaseOrderItem (T016)
# ============================================================


class PurchaseOrderItem(models.Model):
    """
    Line item on a purchase order.

    line_total is auto-computed as quantity * unit_price on save.
    received_quantity is accumulated from GoodsReceiptLine entries.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(
        "inventario.Product",
        on_delete=models.RESTRICT,
        related_name="purchase_order_items",
        help_text="Cannot delete product on open PO",
    )
    quantity = MoneyField(help_text="Ordered quantity (> 0)")
    unit_price = MoneyField(help_text="Price per unit (>= 0)")
    line_total = MoneyField(
        default=Decimal("0.000"),
        help_text="Computed: quantity * unit_price",
    )
    received_quantity = MoneyField(
        default=Decimal("0.000"),
        help_text="Accumulated from GoodsReceiptLines",
    )

    class Meta:
        db_table = "compras_purchaseorderitem"
        ordering = ["id"]
        verbose_name = "Purchase Order Item"
        verbose_name_plural = "Purchase Order Items"
        constraints = [
            models.CheckConstraint(
                check=models.Q(quantity__gt=0),
                name="poi_quantity_positive",
            ),
            models.CheckConstraint(
                check=models.Q(unit_price__gte=0),
                name="poi_unit_price_non_negative",
            ),
        ]

    def __str__(self) -> str:
        return f"POItem {self.id} — {self.product_id} x {self.quantity}"

    def save(self, *args: object, **kwargs: object) -> None:
        """Auto-compute line_total before save."""
        self.line_total = self.quantity * self.unit_price
        super().save(*args, **kwargs)


# ============================================================
# GoodsReceipt (T025) — Immutable
# ============================================================


class GoodsReceipt(TenantBoundModel):
    """
    Record of goods received against a purchase order.

    IMMUTABLE: No update or delete operations. Corrections handled
    by adjustment StockMovements.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="goods_receipts",
    )
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.RESTRICT,
        related_name="goods_receipts",
    )
    receipt_number = models.CharField(
        max_length=32,
        help_text="Unique receipt number per tenant",
    )
    receipt_date = models.DateField(auto_now_add=True, help_text="Date goods arrived")
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="goods_receipts",
        help_text="User who received the goods",
    )
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = TenantBoundManager()
    all_objects = AllObjectsManager()

    class Meta:
        db_table = "compras_goodsreceipt"
        ordering = ["-created_at"]
        verbose_name = "Goods Receipt"
        verbose_name_plural = "Goods Receipts"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "receipt_number"],
                name="unique_gr_number_per_tenant",
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant_id", "purchase_order_id"],
                name="idx_gr_tenant_po",
            ),
        ]

    def __str__(self) -> str:
        return f"GR-{self.receipt_number}"


# ============================================================
# GoodsReceiptLine (T026)
# ============================================================


class GoodsReceiptLine(models.Model):
    """
    Line item on a goods receipt — references a PO item.

    IMMUTABLE: Created by GoodsReceiptService only.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    goods_receipt = models.ForeignKey(
        GoodsReceipt,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    purchase_order_item = models.ForeignKey(
        PurchaseOrderItem,
        on_delete=models.RESTRICT,
        related_name="receipt_lines",
    )
    product = models.ForeignKey(
        "inventario.Product",
        on_delete=models.RESTRICT,
        related_name="goods_receipt_lines",
        help_text="Denormalized from PO item for easy access",
    )
    quantity_received = MoneyField(help_text="Quantity received (> 0)")

    class Meta:
        db_table = "compras_goodsreceiptline"
        ordering = ["id"]
        verbose_name = "Goods Receipt Line"
        verbose_name_plural = "Goods Receipt Lines"
        constraints = [
            models.CheckConstraint(
                check=models.Q(quantity_received__gt=0),
                name="grl_quantity_positive",
            ),
        ]

    def __str__(self) -> str:
        return f"GRLine {self.id} — {self.product_id} x {self.quantity_received}"
