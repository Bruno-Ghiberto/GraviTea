---
name: gravitea-inventory
description: >
  Inventory management patterns for GRAVITEA-ERP including products, stock movements, and the immutable ledger pattern.
  Trigger: When editing apps/inventario/, working with products, stock movements, or inventory calculations.
license: MIT
metadata:
  author: gravitea-team
  version: "1.0"
---

# Gravitea Inventory Skill

Patterns for product catalog management, immutable stock movement ledger, and real-time stock calculations in a multi-tenant context.

## When to Use

- Creating or modifying inventory models (Product, StockMovement, StockSnapshot)
- Implementing stock movement operations (SALE, PURCHASE, ADJ, TRANS_IN, TRANS_OUT)
- Working with price/cost history tracking
- Building inventory reports or stock queries
- Implementing stock reservation logic

---

## Critical Patterns

### Pattern 1: Immutable Ledger for Stock Movements

**Stock movements are append-only entries that cannot be modified or deleted. Corrections require new reversal movements.**

```python
# apps/inventario/models.py
class StockMovement(TenantBoundModel):
    """
    Immutable stock movement ledger entry.

    Movements are append-only and cannot be modified or deleted.
    To correct errors, create adjustment or reversal movements.
    """

    class MovementType(models.TextChoices):
        SALE = "SALE", "Sale"                 # Stock out via sale
        PURCHASE = "PURCHASE", "Purchase"     # Stock in via purchase
        ADJ = "ADJ", "Adjustment"             # Manual stock adjustment
        TRANS_IN = "TRANS_IN", "Transfer In"  # Stock in from another branch
        TRANS_OUT = "TRANS_OUT", "Transfer Out"  # Stock out to another branch

    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT)
    type = PostgresEnumField(enum_type=STOCK_MOVEMENT_TYPE_ENUM, ...)
    quantity_delta = models.DecimalField(max_digits=16, decimal_places=4)
    cost_snapshot = models.DecimalField(max_digits=16, decimal_places=4, null=True)
    reference_id = models.UUIDField(null=True, blank=True)  # Links to Sale, Purchase, etc.
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        """Enforce immutability for existing records."""
        if self.pk and StockMovement.all_objects.filter(pk=self.pk).exists():
            raise ValueError(
                "Stock movements are immutable and cannot be modified. "
                "Create a new adjustment movement instead."
            )
        self._validate_tenant_references()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Prevent deletion of stock movements."""
        raise ValueError(
            "Stock movements cannot be deleted. Create a reversal movement instead."
        )
```

**Usage - Creating a reversal instead of delete**:

```python
# To reverse a sale (instead of deleting)
def reverse_movement(original_movement):
    return StockMovement.objects.create(
        tenant=original_movement.tenant,
        product=original_movement.product,
        branch=original_movement.branch,
        type=StockMovement.MovementType.ADJ,
        quantity_delta=-original_movement.quantity_delta,  # Negate the delta
        cost_snapshot=original_movement.cost_snapshot,
        reference_id=original_movement.id,  # Link to original
        notes=f"Reversal of movement {original_movement.id}"
    )
```

---

### Pattern 2: Quantity Sign Convention

**Outbound movements are negative, inbound movements are positive. Enforce this in serializer validation.**

```python
# apps/inventario/serializers.py
class StockMovementCreateSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        """Ensure quantity sign matches movement type."""
        movement_type = attrs.get("type")
        quantity_delta = attrs.get("quantity_delta")

        # Outbound types should have negative delta
        outbound_types = [
            StockMovement.MovementType.SALE,
            StockMovement.MovementType.TRANS_OUT,
        ]

        if movement_type in outbound_types and quantity_delta > 0:
            attrs["quantity_delta"] = -abs(quantity_delta)
        elif movement_type not in outbound_types and quantity_delta < 0:
            attrs["quantity_delta"] = abs(quantity_delta)

        return attrs
```

---

### Pattern 3: StockSnapshot for Real-Time Stock

**StockSnapshot is a materialized view of current stock levels, updated on each movement. It does NOT have tenant_id directly - uses branch.tenant_id.**

```python
# apps/inventario/models.py
class StockSnapshot(models.Model):
    """
    Current stock level per product per branch.

    This is a materialized view of stock movements for efficient
    stock queries. Updated via triggers on StockMovement.

    Note: Does NOT have tenant_id directly - uses branch_id → branch.tenant_id
    for tenant isolation via RLS nested policy.
    """

    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=16, decimal_places=4, default=Decimal("0.0000"))
    reserved_quantity = models.DecimalField(max_digits=16, decimal_places=4, default=Decimal("0.0000"))
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["branch_id", "product_id"],
                name="uq_stock_snapshot"
            ),
        ]

    @property
    def available_quantity(self) -> Decimal:
        """Stock available for sale (quantity - reserved)."""
        return self.quantity - self.reserved_quantity

    @property
    def tenant_id(self) -> uuid.UUID:
        """Get tenant_id from branch for compatibility."""
        return self.branch.tenant_id
```

**Updating snapshot after movement**:

```python
def _update_branch_stock(self, movement):
    """Update or create StockSnapshot record."""
    branch_stock, created = StockSnapshot.objects.get_or_create(
        product=movement.product,
        branch=movement.branch,
        defaults={"quantity": Decimal("0.0000")},
    )

    branch_stock.quantity += movement.quantity_delta
    branch_stock.save()  # last_updated is auto_now
```

---

### Pattern 4: Product Model with Encrypted Barcode

**Products use TenantBoundModel with encrypted barcode and blind index for search.**

```python
# apps/inventario/models.py
class Product(TenantBoundModel):
    sku = models.CharField(max_length=50, db_index=True)
    barcode = EncryptedCharField(max_length=255, null=True, blank=True)
    barcode_blind_idx = BlindIndexField(null=True, blank=True, db_index=True)
    name = models.CharField(max_length=255)
    unit_price = MoneyField(help_text="Default selling price")  # DECIMAL(17,3)
    cost_price = MoneyField(help_text="Last known cost price")  # DECIMAL(17,3)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("21.00"))
    min_stock = models.DecimalField(max_digits=16, decimal_places=4, null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "sku"],
                name="unique_sku_per_tenant"
            ),
        ]

    def save(self, *args, **kwargs):
        """Generate blind index for barcode if set."""
        if self.barcode and not self.barcode_blind_idx:
            self.barcode_blind_idx = compute_blind_index(self.barcode)
        super().save(*args, **kwargs)
```

---

### Pattern 5: ViewSet with Immutability Enforcement

**StockMovementViewSet restricts HTTP methods to enforce immutability at the API level.**

```python
# apps/inventario/views.py
class StockMovementViewSet(viewsets.ModelViewSet):
    """
    Stock movement management viewset.

    Stock movements are immutable. Update and delete operations
    are not allowed. Create adjustment movements instead.
    """

    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]  # No PUT, PATCH, DELETE

    def get_queryset(self):
        return StockMovement.objects.select_related("product", "branch").all()

    def get_serializer_class(self):
        if self.action == "create":
            return StockMovementCreateSerializer
        return StockMovementSerializer

    def update(self, request, *args, **kwargs):
        """Prevent update of stock movements."""
        return Response(
            {"detail": "Stock movements are immutable and cannot be updated."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def destroy(self, request, *args, **kwargs):
        """Prevent deletion of stock movements."""
        return Response(
            {"detail": "Stock movements cannot be deleted. Create a reversal movement instead."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )
```

---

## Decision Tree

```
Working with stock?
|-- Need current stock level? -> Query StockSnapshot
|-- Recording stock change? -> Create StockMovement
|   |-- Sale -> type=SALE, quantity_delta negative
|   |-- Purchase -> type=PURCHASE, quantity_delta positive
|   |-- Adjustment -> type=ADJ, sign depends on correction
|   |-- Transfer -> TRANS_OUT at source, TRANS_IN at destination
+-- Need historical data? -> Query StockMovement ledger

Correcting a movement?
|-- NEVER modify existing movement
|-- Create reversal movement with:
|   |-- quantity_delta = -original.quantity_delta
|   |-- reference_id = original.id
+-- Notes explaining the reversal

Stock query optimization?
|-- Current levels -> StockSnapshot (fast)
|-- Historical analysis -> StockMovement with date filters
|-- Low stock alerts -> StockSnapshot.quantity < Product.min_stock
+-- Movement audit -> StockMovement with reference_id filter
```

---

## Anti-Patterns (What NOT to Do)

### Anti-Pattern 1: Modifying Stock Movements

```python
# FORBIDDEN - Stock movements are immutable
movement = StockMovement.objects.get(id=movement_id)
movement.quantity_delta = 50  # Will raise ValueError
movement.save()

# CORRECT - Create a reversal/adjustment movement
def correct_movement(original, correct_quantity):
    # First reverse the original
    reversal = StockMovement.objects.create(
        tenant=original.tenant,
        product=original.product,
        branch=original.branch,
        type=StockMovement.MovementType.ADJ,
        quantity_delta=-original.quantity_delta,
        reference_id=original.id,
        notes=f"Reversal: {original.id}"
    )
    # Then create correct movement
    corrected = StockMovement.objects.create(
        tenant=original.tenant,
        product=original.product,
        branch=original.branch,
        type=original.type,
        quantity_delta=correct_quantity,
        reference_id=reversal.id,
        notes=f"Correction for: {original.id}"
    )
    return corrected
```

### Anti-Pattern 2: Direct StockSnapshot Updates

```python
# FORBIDDEN - Never update StockSnapshot directly
snapshot = StockSnapshot.objects.get(product=product, branch=branch)
snapshot.quantity = 100  # Breaks audit trail!
snapshot.save()

# CORRECT - Always create StockMovement to adjust stock
StockMovement.objects.create(
    tenant=product.tenant,
    product=product,
    branch=branch,
    type=StockMovement.MovementType.ADJ,
    quantity_delta=100 - snapshot.quantity,  # Delta to reach target
    notes="Physical inventory count adjustment"
)
# Serializer/trigger will update StockSnapshot
```

### Anti-Pattern 3: Querying Stock Without Tenant Context

```python
# FORBIDDEN - May leak cross-tenant data
all_stock = StockSnapshot.objects.all()

# CORRECT - Use branch filtering (which provides tenant context)
branch = Branch.objects.get(id=branch_id)  # Already tenant-filtered
stock = StockSnapshot.objects.filter(branch=branch)

# Or filter explicitly
stock = StockSnapshot.objects.filter(branch__tenant=tenant)
```

---

## Testing Inventory

```python
# tests/inventario/test_stock_movement.py
import pytest
from decimal import Decimal

@pytest.mark.integration
@pytest.mark.django_db
class TestStockMovementImmutability:
    def test_cannot_update_existing_movement(self, stock_movement_factory):
        """Stock movements cannot be modified after creation."""
        movement = stock_movement_factory()
        movement.quantity_delta = Decimal("999")

        with pytest.raises(ValueError, match="immutable"):
            movement.save()

    def test_cannot_delete_movement(self, stock_movement_factory):
        """Stock movements cannot be deleted."""
        movement = stock_movement_factory()

        with pytest.raises(ValueError, match="cannot be deleted"):
            movement.delete()

    def test_reversal_corrects_stock(
        self, tenant, branch, product_factory, stock_movement_factory
    ):
        """Reversal movement correctly adjusts stock."""
        product = product_factory(tenant=tenant)

        # Create initial movement
        original = stock_movement_factory(
            tenant=tenant,
            product=product,
            branch=branch,
            type=StockMovement.MovementType.PURCHASE,
            quantity_delta=Decimal("100")
        )

        # Create reversal
        reversal = stock_movement_factory(
            tenant=tenant,
            product=product,
            branch=branch,
            type=StockMovement.MovementType.ADJ,
            quantity_delta=Decimal("-100"),
            reference_id=original.id
        )

        # Verify stock is back to zero
        snapshot = StockSnapshot.objects.get(product=product, branch=branch)
        assert snapshot.quantity == Decimal("0")


@pytest.mark.integration
@pytest.mark.django_db
class TestQuantitySignConvention:
    def test_sale_movement_has_negative_delta(self, authenticated_client, product):
        """Sale movements should have negative quantity_delta."""
        response = authenticated_client.post("/api/v1/inventory/movements/", {
            "product": str(product.id),
            "branch": str(product.tenant.branches.first().id),
            "type": "SALE",
            "quantity_delta": 10,  # Positive input
        })

        assert response.status_code == 201
        assert response.json()["quantity_delta"] == "-10.0000"  # Auto-negated
```

---

## Commands

```bash
# Run inventory tests
cd backend && pytest tests/inventario/ -v

# Test stock movement immutability
cd backend && pytest tests/inventario/test_stock_movement.py -v -k "immutable"

# Run integration tests
cd backend && pytest -m "integration" tests/inventario/ -v

# Check product model
cd backend && python manage.py shell -c "from apps.inventario.models import Product; print(Product._meta.get_fields())"
```

---

## Developer Checklist

Before submitting inventory-related code, verify:

- [ ] Stock movements are created, never modified
- [ ] Reversals/adjustments used for corrections
- [ ] Quantity sign convention enforced (outbound negative, inbound positive)
- [ ] StockSnapshot updated via movement, never directly
- [ ] Products use TenantBoundModel inheritance
- [ ] Barcode uses encrypted field with blind index
- [ ] Monetary values use MoneyField (DECIMAL 17,3)
- [ ] ViewSet restricts methods for immutable resources
- [ ] Tenant isolation verified in queries
- [ ] Tests cover immutability constraints

---

## Resources

- **Models**: See `backend/apps/inventario/models.py`
- **Serializers**: See `backend/apps/inventario/serializers.py`
- **Views**: See `backend/apps/inventario/views.py`
- **Tests**: See `backend/tests/inventario/`
- **Database Schema**: See `database/SQL/001_schema.sql`
- **RLS Policies**: See `database/SQL/002_rls_policies.sql`
- **Data Model**: See `Docs/Project Blueprint/Data Model & Domain Model.md`

---

*Last updated: 2026-01-20*
*Models: Product, ProductCategory, Supplier, PriceList, StockMovement, StockSnapshot*
