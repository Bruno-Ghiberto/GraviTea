"""
Ventas (Sales) models for Gravitea ERP.

Defines Customer, SaleOrder, and SaleOrderItem with lifecycle
management, price snapshots, and multi-tenant isolation.
"""

import logging
import uuid
from decimal import Decimal

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.db import models

from apps.core.fields import MoneyField
from apps.core.managers.tenant_bound import AllObjectsManager, TenantBoundManager
from apps.core.models.branch import Branch
from apps.core.models.mixins import TenantBoundModel
from apps.core.models.tenant import Tenant
from apps.facturacion.constants import CondicionIVA, DocTipo

from .validators import validate_cuit

logger = logging.getLogger(__name__)


# ============================================================
# Customer
# ============================================================


class Customer(TenantBoundModel):
    """
    Business client with ARCA fiscal identification.

    The condicion_iva determines which invoice type (A/B/C) to emit
    via resolver_tipo_comprobante(). CUIT is validated with Modulo-11.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="customers",
    )

    # Fiscal identification
    cuit = models.CharField(
        max_length=11,
        help_text="Tax ID (11 digits, Modulo-11 validated)",
    )
    doc_tipo = models.PositiveSmallIntegerField(
        choices=DocTipo.choices,
        default=DocTipo.CUIT,
        help_text="Document type code (80=CUIT, 96=DNI, 99=CF)",
    )
    condicion_iva = models.PositiveSmallIntegerField(
        choices=CondicionIVA.choices,
        help_text="IVA condition — determines invoice type (A/B/C)",
    )

    # Basic identification
    razon_social = models.CharField(
        max_length=255,
        help_text="Legal business name or full name",
    )
    domicilio = models.TextField(
        blank=True,
        default="",
        help_text="Fiscal address",
    )

    # Contact (optional)
    email = models.EmailField(blank=True, default="")
    telefono = models.CharField(max_length=50, blank=True, default="")

    custom_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Tenant-defined custom fields. Validated against TenantFieldDefinition.",
    )

    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantBoundManager()
    all_objects = AllObjectsManager()

    class Meta:
        db_table = "ventas_customer"
        ordering = ["razon_social"]
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "cuit"],
                name="uq_customer_cuit_per_tenant",
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant_id", "is_active"],
                name="idx_customer_tenant_active",
                condition=models.Q(is_active=True),
            ),
            GinIndex(
                fields=["custom_data"],
                name="idx_customer_custom_data",
                opclasses=["jsonb_path_ops"],
            ),
        ]

    def __str__(self) -> str:
        return f"{self.razon_social} (CUIT: {self.cuit})"

    def clean(self) -> None:
        super().clean()
        validate_cuit(self.cuit)


# ============================================================
# SaleOrder
# ============================================================


class SaleOrderStatus(models.TextChoices):
    DRAFT = "DRAFT", "Borrador"
    CONFIRMED = "CONFIRMED", "Confirmado"
    INVOICED = "INVOICED", "Facturado"


# Allowed status transitions
SALE_ORDER_TRANSITIONS = {
    SaleOrderStatus.DRAFT: {SaleOrderStatus.CONFIRMED},
    SaleOrderStatus.CONFIRMED: {SaleOrderStatus.INVOICED, SaleOrderStatus.DRAFT},
    SaleOrderStatus.INVOICED: set(),  # Terminal state
}
# NOTE: CONFIRMED→DRAFT is allowed for manual cancellation of a confirmed order
# (e.g., customer changes their mind before authorization). It is NOT used during
# ARCA rejection recovery — rejected orders stay CONFIRMED for re-authorization.


class SaleOrder(TenantBoundModel):
    """
    Sales order with lifecycle management and invoice integration.

    Immutability: INVOICED orders cannot be modified. CONFIRMED orders
    can only transition status (not edit data). DRAFT orders are fully editable.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="sale_orders",
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="sale_orders",
        help_text="Customer for this sale",
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.PROTECT,
        related_name="sale_orders",
        help_text="Branch where sale originates (determines stock source)",
    )

    # Status lifecycle
    status = models.CharField(
        max_length=10,
        choices=SaleOrderStatus.choices,
        default=SaleOrderStatus.DRAFT,
        db_index=True,
    )

    # Totals (calculated from items)
    subtotal = MoneyField(help_text="Sum of item subtotals (before tax)")
    total_iva = MoneyField(help_text="Total IVA amount")
    total_amount = MoneyField(help_text="Final total (subtotal + IVA)")

    # NOTE: No comprobante FK here. The link is via Comprobante.sale_order
    # (OneToOneField on Comprobante side). Access from SaleOrder:
    #   order.comprobante_direct  (reverse accessor, may raise RelatedObjectDoesNotExist)
    #   hasattr(order, 'comprobante_direct')  (safe check)

    # Audit
    sale_date = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    invoiced_at = models.DateTimeField(null=True, blank=True)
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="confirmed_sales",
        help_text="Set by SaleService.confirm_sale() from request.user",
    )

    custom_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Tenant-defined custom fields. Validated against TenantFieldDefinition.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantBoundManager()
    all_objects = AllObjectsManager()

    class Meta:
        db_table = "ventas_saleorder"
        ordering = ["-created_at"]
        verbose_name = "Pedido de Venta"
        verbose_name_plural = "Pedidos de Venta"
        indexes = [
            models.Index(
                fields=["tenant_id", "status"],
                name="idx_saleorder_tenant_status",
            ),
            models.Index(
                fields=["tenant_id", "customer_id"],
                name="idx_saleorder_tenant_customer",
            ),
            models.Index(
                fields=["tenant_id", "-sale_date"],
                name="idx_saleorder_tenant_date",
            ),
            GinIndex(
                fields=["custom_data"],
                name="idx_saleorder_custom_data",
                opclasses=["jsonb_path_ops"],
            ),
        ]

    def __str__(self) -> str:
        return f"Sale #{str(self.id)[:8]} [{self.status}] - {self.customer.razon_social}"

    def save(self, *args, **kwargs) -> None:
        """
        Enforce status transition rules and immutability.

        - INVOICED orders cannot be modified at all.
        - CONFIRMED orders can only change status (not data fields).
        - DRAFT orders are fully editable.
        """
        if self.pk:
            try:
                existing = SaleOrder.all_objects.get(pk=self.pk)
            except SaleOrder.DoesNotExist:
                existing = None

            if existing:
                # INVOICED is terminal — no modifications
                if existing.status == SaleOrderStatus.INVOICED:
                    raise ValueError(
                        "Cannot modify invoiced sale order. "
                        "Invoiced orders are immutable."
                    )

                # Validate status transition
                if self.status != existing.status:
                    allowed = SALE_ORDER_TRANSITIONS.get(existing.status, set())
                    if self.status not in allowed:
                        raise ValueError(
                            f"Invalid status transition: "
                            f"{existing.status} → {self.status}. "
                            f"Allowed: {allowed}"
                        )
                    logger.info(
                        "SaleOrder status transition: order=%s from=%s to=%s user=%s",
                        self.pk,
                        existing.status,
                        self.status,
                        getattr(self, "_changed_by", "system"),
                    )

                # F-001: CONFIRMED orders — only status-related fields may change
                if existing.status == SaleOrderStatus.CONFIRMED:
                    _MUTABLE_ON_CONFIRMED = {
                        "status", "confirmed_at", "invoiced_at",
                        "confirmed_by_id", "updated_at",
                    }
                    for field in self._meta.get_fields():
                        if not hasattr(field, "attname"):
                            continue
                        attr = field.attname
                        if attr in _MUTABLE_ON_CONFIRMED:
                            continue
                        old_val = getattr(existing, attr, None)
                        new_val = getattr(self, attr, None)
                        if old_val != new_val:
                            raise ValueError(
                                f"Cannot modify field '{attr}' on a CONFIRMED "
                                f"sale order. Only status transitions are allowed."
                            )

        super().save(*args, **kwargs)

    def recalculate_totals(self) -> None:
        """
        Recalculate subtotal, total_iva, and total_amount from items.

        Called after item add/update/delete to keep order totals in sync.
        """
        from django.db.models import Sum

        aggregates = self.items.aggregate(
            total_subtotal=Sum("subtotal"),
            total_iva_amount=Sum("iva_amount"),
        )
        self.subtotal = aggregates["total_subtotal"] or Decimal("0.000")
        self.total_iva = aggregates["total_iva_amount"] or Decimal("0.000")
        self.total_amount = self.subtotal + self.total_iva
        self.save(update_fields=["subtotal", "total_iva", "total_amount", "updated_at"])


# ============================================================
# SaleOrderItem
# ============================================================


class SaleOrderItem(TenantBoundModel):
    """
    Sale order line item with price snapshot.

    unit_price is captured at item creation time (price snapshot).
    subtotal is auto-calculated: quantity * unit_price.
    iva_amount is auto-calculated: subtotal * (tax_rate / 100).
    Items are locked when parent SaleOrder leaves DRAFT status.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="sale_order_items",
    )
    sale_order = models.ForeignKey(
        SaleOrder,
        on_delete=models.CASCADE,
        related_name="items",
        help_text="Parent sale order",
    )
    product = models.ForeignKey(
        "inventario.Product",
        on_delete=models.PROTECT,
        related_name="sale_items",
        help_text="Product being sold",
    )

    # Quantity and pricing
    quantity = models.DecimalField(
        max_digits=16,
        decimal_places=4,
        help_text="Quantity sold (matches StockMovement precision)",
    )
    unit_price = MoneyField(
        help_text="Price per unit at time of sale (snapshot)",
    )
    subtotal = MoneyField(
        help_text="quantity * unit_price (auto-calculated)",
    )

    # Tax
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("21.00"),
        help_text="IVA rate percentage (inherited from Product.tax_rate)",
    )
    iva_amount = MoneyField(
        help_text="IVA amount: subtotal * (tax_rate / 100)",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    objects = TenantBoundManager()
    all_objects = AllObjectsManager()

    class Meta:
        db_table = "ventas_saleorderitem"
        ordering = ["created_at"]
        verbose_name = "Línea de Pedido"
        verbose_name_plural = "Líneas de Pedido"
        constraints = [
            models.UniqueConstraint(
                fields=["sale_order_id", "product_id"],
                name="uq_sale_item_product_per_order",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.product.sku} x {self.quantity} @ {self.unit_price}"

    def save(self, *args, **kwargs) -> None:
        """
        Auto-calculate subtotal/iva_amount and enforce parent status check.
        """
        # F-002: Block both creates and edits if parent sale is not DRAFT
        if self.sale_order_id:
            parent = SaleOrder.all_objects.get(pk=self.sale_order_id)
            if parent.status != SaleOrderStatus.DRAFT:
                raise ValueError(
                    "Cannot add or modify items on a non-DRAFT sale order."
                )

        # Auto-calculate
        self.subtotal = self.quantity * self.unit_price
        self.iva_amount = self.subtotal * (self.tax_rate / Decimal("100"))

        super().save(*args, **kwargs)
