# Data Model: Sales-Invoicing-Inventory Integration

**Feature**: 001-sal-invo-inve-backend
**Date**: 2026-02-14
**Spec**: [spec.md](spec.md) | **Research**: [research.md](research.md)

---

## Entity Overview

| Entity | Module | Status | Table Name |
|--------|--------|--------|------------|
| Customer | ventas (NEW) | NEW | `ventas_customer` |
| SaleOrder | ventas (NEW) | NEW | `ventas_saleorder` |
| SaleOrderItem | ventas (NEW) | NEW | `ventas_saleorderitem` |
| Comprobante | facturacion | ENHANCED | `facturacion_comprobante` |
| StockMovement | inventario | ENHANCED | `stock_movement` |
| StockSnapshot | inventario | UNCHANGED | `stock_snapshot` |
| ARCACredential | facturacion | ENHANCED | `facturacion_arcacredential` |

---

## New Models (apps/ventas/)

### Customer

Represents business clients with tax identification and IVA condition for invoice type determination.

**Covers**: FR-001, FR-002, FR-003, FR-004

```python
class Customer(TenantBoundModel):
    """
    Business client with ARCA fiscal identification.

    The condicion_iva determines which invoice type (A/B/C) to emit
    via resolver_tipo_comprobante(). CUIT is validated with Modulo-11.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name="customers"
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
        ]

    def __str__(self) -> str:
        return f"{self.razon_social} (CUIT: {self.cuit})"

    def clean(self) -> None:
        super().clean()
        from .validators import validate_cuit
        validate_cuit(self.cuit)
```

**Multi-Tenant FK Validation**: Automatic via `TenantBoundModel._validate_tenant_references()` — `tenant` FK is the only FK and is skipped.

---

### SaleOrder

Represents a sales transaction lifecycle: DRAFT → CONFIRMED → INVOICED.

**Covers**: FR-005, FR-006, FR-007, FR-008, FR-009, FR-010

```python
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
        Tenant, on_delete=models.CASCADE, related_name="sale_orders"
    )
    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT, related_name="sale_orders",
        help_text="Customer for this sale",
    )
    branch = models.ForeignKey(
        Branch, on_delete=models.PROTECT, related_name="sale_orders",
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

    # Integration links
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
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="confirmed_sales",
        help_text="Set by SaleService.confirm_sale() from request.user",
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

        super().save(*args, **kwargs)
```

**Multi-Tenant FK Validation**: Automatic via `TenantBoundModel._validate_tenant_references()`. Validates:
- `customer.tenant_id == self.tenant_id`
- `branch.tenant_id == self.tenant_id`

---

### SaleOrderItem

Individual line items in a sale order. Locked after parent order confirmation.

**Covers**: FR-006, FR-007, FR-009

```python
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
        Tenant, on_delete=models.CASCADE, related_name="sale_order_items"
    )
    sale_order = models.ForeignKey(
        SaleOrder, on_delete=models.CASCADE, related_name="items",
        help_text="Parent sale order",
    )
    product = models.ForeignKey(
        "inventario.Product", on_delete=models.PROTECT, related_name="sale_items",
        help_text="Product being sold",
    )

    # Quantity and pricing
    quantity = models.DecimalField(
        max_digits=16, decimal_places=4,
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
        max_digits=5, decimal_places=2,
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
        # Block edits if parent sale is not DRAFT
        if self.sale_order_id:
            parent = SaleOrder.all_objects.get(pk=self.sale_order_id)
            if parent.status != SaleOrderStatus.DRAFT:
                if self.pk and SaleOrderItem.all_objects.filter(pk=self.pk).exists():
                    raise ValueError(
                        "Cannot modify items on a confirmed/invoiced sale order."
                    )

        # Auto-calculate
        self.subtotal = self.quantity * self.unit_price
        self.iva_amount = self.subtotal * (self.tax_rate / Decimal("100"))

        super().save(*args, **kwargs)
```

**Multi-Tenant FK Validation**: Automatic. Validates:
- `sale_order.tenant_id == self.tenant_id`
- `product.tenant_id == self.tenant_id`

---

## Enhanced Models

### Comprobante (apps/facturacion/) — New Fields

**Covers**: FR-017, FR-018, FR-020, FR-022

```python
# NEW FIELDS to add via migration:

sale_order = models.OneToOneField(
    "ventas.SaleOrder",
    null=True, blank=True,
    on_delete=models.PROTECT,
    related_name="comprobante_direct",
    help_text="Originating sale order (null for standalone invoices)",
)

customer = models.ForeignKey(
    "ventas.Customer",
    null=True, blank=True,
    on_delete=models.PROTECT,
    related_name="comprobantes",
    help_text="Customer (from sale order or standalone)",
)
```

**Migration notes**:
- Both fields are nullable to preserve backward compatibility with existing comprobantes.
- `sale_order` is OneToOneField enforcing FR-022 (one invoice per sale order).
- Existing 334 tests must continue passing unchanged — these fields default to NULL.
- Validation in SaleService: if `sale_order` is set, `customer` must equal `sale_order.customer`.

---

### StockMovement (apps/inventario/) — New Fields

**Covers**: FR-011, FR-014, FR-015, FR-016

```python
# NEW FIELDS to add via migration:

class StockMovementStatus(models.TextChoices):
    COMMITTED = "COMMITTED", "Comprometido"
    RESERVED = "RESERVED", "Reservado"
    CANCELLED = "CANCELLED", "Cancelado"


status = models.CharField(
    max_length=10,
    choices=StockMovementStatus.choices,
    default=StockMovementStatus.COMMITTED,
    db_index=True,
    help_text="COMMITTED=final, RESERVED=pending sale, CANCELLED=released",
)

sale_order = models.ForeignKey(
    "ventas.SaleOrder",
    null=True, blank=True,
    on_delete=models.PROTECT,
    related_name="stock_movements",
    help_text="Originating sale order",
)

comprobante = models.ForeignKey(
    "facturacion.Comprobante",
    null=True, blank=True,
    on_delete=models.PROTECT,
    related_name="stock_movements",
    help_text="Linked authorized invoice",
)
```

**Modified save() logic**:
```python
def save(self, *args, **kwargs) -> None:
    if self.tenant_id is None and hasattr(self, "tenant") and self.tenant:
        self.tenant_id = self.tenant.id

    if self.pk and StockMovement.all_objects.filter(pk=self.pk).exists():
        existing = StockMovement.all_objects.get(pk=self.pk)

        # Allow ONLY status transitions from RESERVED
        if existing.status != StockMovementStatus.RESERVED:
            raise ValueError(
                "Stock movements are immutable and cannot be modified. "
                "Create a new adjustment movement instead."
            )

        # Only status field can change
        allowed_transitions = {
            StockMovementStatus.COMMITTED,
            StockMovementStatus.CANCELLED,
        }
        if self.status not in allowed_transitions:
            raise ValueError(
                f"Invalid status transition: {existing.status} → {self.status}. "
                f"RESERVED can only transition to COMMITTED or CANCELLED."
            )

        # Prevent changing any other fields
        for field in self._meta.get_fields():
            if hasattr(field, 'attname') and field.attname not in ('status', 'comprobante_id'):
                if field.attname in ('updated_at',):
                    continue
                old_val = getattr(existing, field.attname, None)
                new_val = getattr(self, field.attname, None)
                if old_val != new_val:
                    raise ValueError(
                        f"Cannot modify field '{field.attname}' on stock movement. "
                        f"Only status transitions are allowed."
                    )

    self._validate_tenant_references()
    super().save(*args, **kwargs)
```

**Migration notes**:
- `status` defaults to `COMMITTED` — all existing movements are automatically COMMITTED (backward compatible).
- `sale_order` and `comprobante` are nullable — existing movements have no sale link.
- New index: `(tenant_id, status, product_id)` for efficient available stock queries.

---

### ARCACredential (apps/facturacion/) — New Field

**Covers**: Research Decision 9 (emitter CondicionIVA source)

```python
# NEW FIELD:
emitter_condicion_iva = models.PositiveSmallIntegerField(
    choices=CondicionIVA.choices,
    default=CondicionIVA.RESPONSABLE_INSCRIPTO,
    help_text="Emitter IVA condition for invoice type resolution",
)
```

---

## Entity Relationship Diagram

```
Tenant (existing)
    │
    ├── Customer (NEW) ────────────────────────────────────────┐
    │   ├── cuit (11 chars, unique per tenant, Modulo-11)      │
    │   ├── doc_tipo (DocTipo code)                            │
    │   ├── condicion_iva (CondicionIVA → determines CbteTipo) │
    │   └── razon_social, domicilio, email, telefono           │
    │                                                          │
    ├── SaleOrder (NEW) ←──────────────────────────────────────┘
    │   ├── customer FK → Customer (PROTECT)
    │   ├── branch FK → Branch (PROTECT)
    │   ├── status (DRAFT/CONFIRMED/INVOICED)
    │   ├── subtotal, total_iva, total_amount (MoneyField)
    │   ├── ← comprobante_direct (reverse 1:1 from Comprobante.sale_order)
    │   └── confirmed_at, invoiced_at, confirmed_by
    │       │
    │       └── SaleOrderItem (NEW) [cascade delete with parent]
    │           ├── sale_order FK → SaleOrder (CASCADE)
    │           ├── product FK → Product (PROTECT)
    │           ├── quantity (16,4), unit_price (17,3)
    │           ├── subtotal (17,3) = quantity * unit_price
    │           ├── tax_rate (5,2), iva_amount (17,3)
    │           └── unique(sale_order, product)
    │
    ├── Comprobante (ENHANCED)
    │   ├── sale_order 1:1 → SaleOrder (nullable, PROTECT) ← NEW
    │   ├── customer FK → Customer (nullable, PROTECT) ← NEW
    │   ├── punto_venta FK → PuntoDeVenta (RESTRICT)
    │   ├── cbte_tipo, cbte_nro (unique per tenant+pto_vta+tipo)
    │   ├── status (DRAFT/VALIDANDO/AUTORIZADO/RECHAZADO/OBSERVADO)
    │   ├── cae, cae_fch_vto (from ARCA)
    │   ├── imp_total/neto/iva/trib/op_ex/tot_conc (all 17,3)
    │   └── arca_response, arca_errors (JSON)
    │
    └── StockMovement (ENHANCED)
        ├── status (COMMITTED/RESERVED/CANCELLED) ← NEW
        ├── sale_order FK → SaleOrder (nullable, PROTECT) ← NEW
        ├── comprobante FK → Comprobante (nullable, PROTECT) ← NEW
        ├── product FK → Product (PROTECT)
        ├── branch FK → Branch (PROTECT)
        ├── type (SALE/PURCHASE/ADJ/TRANS_IN/TRANS_OUT)
        ├── quantity_delta (16,4), cost_snapshot (16,4)
        └── immutable once COMMITTED or CANCELLED
```

---

## State Machines

### SaleOrder Status

```
                    ┌──────────────────────┐
                    │                      │
                    ▼                      │
    ┌─────────┐  confirm   ┌───────────┐  │  authorize   ┌──────────┐
    │  DRAFT  │ ─────────► │ CONFIRMED │ ─┼────────────► │ INVOICED │
    └─────────┘            └───────────┘  │              └──────────┘
                                ▲         │                (terminal)
                                │         │
                                └─────────┘
                             rejection/reset
```

### StockMovement Status

```
    ┌──────────┐  authorize   ┌───────────┐
    │ RESERVED │ ───────────► │ COMMITTED │  (immutable)
    └──────────┘              └───────────┘
         │
         │ rejection
         ▼
    ┌───────────┐
    │ CANCELLED │  (immutable)
    └───────────┘
```

### Comprobante Status (existing — unchanged)

```
    ┌───────┐  submit   ┌───────────┐  approved   ┌────────────┐
    │ DRAFT │ ────────► │ VALIDANDO │ ──────────► │ AUTORIZADO │
    └───────┘           └───────────┘             └────────────┘
                             │
                             ├── observed ──► OBSERVADO (immutable)
                             │
                             └── rejected ──► RECHAZADO (mutable, retry)
                                                    │
                                                    └── resubmit ──► VALIDANDO
```

> **Retry flow**: RECHAZADO comprobantes can be corrected and resubmitted. On resubmission, status transitions to VALIDANDO and follows the normal authorization path. The same `cbte_nro` is preserved (not incremented).

---

## Constraints Summary

### Database Constraints

| Table | Constraint | Type | Purpose |
|-------|-----------|------|---------|
| ventas_customer | uq_customer_cuit_per_tenant | UNIQUE(tenant_id, cuit) | One CUIT per tenant |
| ventas_saleorder | — | CHECK(status IN (...)) | Valid status values |
| ventas_saleorderitem | uq_sale_item_product_per_order | UNIQUE(sale_order_id, product_id) | One line per product per order |
| facturacion_comprobante | uq_comprobante_fiscal | UNIQUE(tenant_id, punto_venta, cbte_tipo, cbte_nro) | Fiscal uniqueness (existing) |
| stock_movement | — | CHECK(status IN (...)) | Valid status values |

### RLS Policies (new tables)

```sql
-- Customer
ALTER TABLE ventas_customer ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON ventas_customer
    USING (tenant_id = current_setting('app.current_tenant')::uuid);

-- SaleOrder
ALTER TABLE ventas_saleorder ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON ventas_saleorder
    USING (tenant_id = current_setting('app.current_tenant')::uuid);

-- SaleOrderItem
ALTER TABLE ventas_saleorderitem ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON ventas_saleorderitem
    USING (tenant_id = current_setting('app.current_tenant')::uuid);
```

### Immutability Rules

| Entity | Condition | Immutable Fields | Mutable Fields |
|--------|-----------|-----------------|----------------|
| SaleOrder | status=INVOICED | ALL | NONE |
| SaleOrder | status=CONFIRMED | data fields | status only |
| SaleOrderItem | parent.status != DRAFT | ALL | NONE |
| Comprobante | status=AUTORIZADO/OBSERVADO | ALL | NONE (existing) |
| StockMovement | status=COMMITTED | ALL | NONE |
| StockMovement | status=CANCELLED | ALL | NONE |
| StockMovement | status=RESERVED | data fields | status, comprobante_id only |

---

## Indexes

### New Indexes

```python
# ventas_customer
Index(fields=["tenant_id", "is_active"], name="idx_customer_tenant_active", condition=Q(is_active=True))

# ventas_saleorder
Index(fields=["tenant_id", "status"], name="idx_saleorder_tenant_status")
Index(fields=["tenant_id", "customer_id"], name="idx_saleorder_tenant_customer")
Index(fields=["tenant_id", "-sale_date"], name="idx_saleorder_tenant_date")

# stock_movement (new)
Index(fields=["tenant_id", "status", "product_id"], name="idx_movement_status_product")
```
