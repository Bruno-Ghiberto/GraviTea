# Quick Start: Sales-Invoicing-Inventory Integration

**Feature**: 001-sal-invo-inve-backend
**Branch**: `001-sal-invo-inve-backend`
**Prerequisites**: Existing backend running with `inventario` and `facturacion` modules

---

## 1. Branch Setup

```bash
git checkout 001-sal-invo-inve-backend
cd backend
```

## 2. Create the Ventas App

```bash
python manage.py startapp ventas apps/ventas
```

Update `apps/ventas/apps.py`:
```python
from django.apps import AppConfig

class VentasConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ventas"
    label = "gravitea_ventas"
    verbose_name = "Ventas"
```

Add to `gravitea/settings/base.py` INSTALLED_APPS:
```python
INSTALLED_APPS = [
    # ... existing apps
    "apps.ventas",
]
```

## 3. Implementation Order

### Phase 1: Models (start here)

1. **validators.py** — CUIT Modulo-11 validation
2. **models.py** — Customer → SaleOrder → SaleOrderItem
3. **migrations** — `python manage.py makemigrations ventas`
4. **serializers.py** — CustomerSerializer, SaleOrderSerializer, SaleOrderItemSerializer
5. **views.py** — CustomerViewSet, SaleOrderViewSet, SaleOrderItemViewSet
6. **urls.py** — Router registration under `/api/v1/ventas/`

### Phase 2-3: Module Enhancements (parallel)

7. **facturacion migration** — Add sale_order (OneToOne) + customer FK to Comprobante
8. **inventario migration** — Add status + sale_order + comprobante to StockMovement
9. **Update StockMovement.save()** — Limited mutability for status transitions

### Phase 4: Integration Service

10. **services/sale_service.py** — SaleService with confirm_sale() and authorize_sale()
11. **ViewSet actions** — `confirm/` and `authorize/` actions on SaleOrderViewSet

### Phase 5-6: ARCA + Error Handling

12. **Amount mapping** — SaleOrder totals → Comprobante fields
13. **AlicIva creation** — Group items by tax_rate
14. **Error responses** — Standardized error format

### Phase 7-8: Testing + Deployment

15. **Test fixtures** — Customers, products, ARCA mocks
16. **Test suite** — Unit, integration, security, performance
17. **Docker + migrations** — Deployment preparation

## 4. Key Patterns to Follow

### Model Inheritance
```python
from apps.core.models.mixins import TenantBoundModel
from apps.core.fields import MoneyField

class Customer(TenantBoundModel):
    # TenantBoundModel provides: tenant FK, _validate_tenant_references()
    cuit = models.CharField(max_length=11)
    # Use MoneyField for all monetary values
    # MoneyField = DecimalField(max_digits=17, decimal_places=3)
```

### Status Transitions
```python
SALE_ORDER_TRANSITIONS = {
    "DRAFT": {"CONFIRMED"},
    "CONFIRMED": {"INVOICED", "DRAFT"},  # DRAFT for manual cancel (NOT used in rejection recovery — rejected orders stay CONFIRMED)
    "INVOICED": set(),  # Terminal
}
```

### Atomic Cross-Module Transaction
```python
from django.db import transaction

class SaleService:
    @transaction.atomic
    def confirm_sale(self, sale_order_id):
        order = SaleOrder.objects.select_for_update().get(id=sale_order_id)
        # 1. Validate stock (select_for_update on BranchStock)
        # 2. Reserve stock (StockMovement with status=RESERVED)
        # 3. Create Comprobante DRAFT (sets Comprobante.sale_order FK)
        # 4. Set order.status = CONFIRMED, confirmed_by = request.user
        # Access linked comprobante via: order.comprobante_direct
```

### Invoice Type Resolution
```python
from apps.facturacion.constants import resolver_tipo_comprobante

cbte_tipo = resolver_tipo_comprobante(
    emitter_condition=credential.emitter_condicion_iva,
    receiver_condition=customer.condicion_iva,
)
```

### CUIT Validation (Modulo-11)
```python
def validate_cuit(cuit: str) -> None:
    if not cuit.isdigit() or len(cuit) != 11:
        raise ValidationError("CUIT must be exactly 11 digits")
    weights = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    total = sum(int(d) * w for d, w in zip(cuit[:10], weights))
    check = 11 - (total % 11)
    if check == 11:
        check = 0
    elif check == 10:
        check = 9  # Special case per ARCA spec
    if check != int(cuit[10]):
        raise ValidationError("CUIT check digit is invalid")
```

## 5. API Endpoints Summary

| Method | Path | Purpose |
|--------|------|---------|
| GET/POST | `/api/v1/ventas/customers/` | List/Create customers |
| GET/PATCH/DELETE | `/api/v1/ventas/customers/{id}/` | Retrieve/Update/Delete customer |
| GET/POST | `/api/v1/ventas/orders/` | List/Create sale orders |
| GET/PATCH/DELETE | `/api/v1/ventas/orders/{id}/` | Retrieve/Update/Delete order (DRAFT only) |
| POST | `/api/v1/ventas/orders/{id}/confirm/` | Confirm order (reserve stock + create invoice) |
| POST | `/api/v1/ventas/orders/{id}/authorize/` | Submit to ARCA for CAE |
| GET | `/api/v1/ventas/orders/{id}/invoice/` | Get linked comprobante |
| GET/POST | `/api/v1/ventas/orders/{id}/items/` | List/Add order items |
| PATCH/DELETE | `/api/v1/ventas/orders/{id}/items/{item_id}/` | Update/Remove item |

## 6. Testing Pattern

All tests run externally per token efficiency protocol:

```bash
# Run in external terminal (NOT inside Claude Code)
cd backend
pytest tests/ventas/ -v --tb=short -q
```

Read results:
```bash
# Summary only
cat .claude-test-results.txt
```

### Key Test Categories
```python
@pytest.mark.unit          # Fast, no DB
@pytest.mark.integration   # Requires DB
@pytest.mark.security      # Tenant isolation
@pytest.mark.performance   # Concurrent load
```

## 7. Reference Files

| File | Purpose |
|------|---------|
| `specs/001-sal-invo-inve-backend/spec.md` | 43 functional requirements |
| `specs/001-sal-invo-inve-backend/data-model.md` | Entity schemas, constraints, ERD |
| `specs/001-sal-invo-inve-backend/contracts/api-contract.md` | REST API specification |
| `specs/001-sal-invo-inve-backend/research.md` | 10 design decisions with rationale |
| `specs/001-sal-invo-inve-backend/plan.md` | 8-phase, 100-task implementation plan |
| `backend/apps/facturacion/constants.py` | CbteTipo, DocTipo, CondicionIVA enums |
| `backend/apps/facturacion/services.py` | InvoiceService (reuse for ARCA flow) |
| `backend/apps/inventario/services/stock_service.py` | StockService (reuse reserve/release) |
| `backend/apps/core/models/mixins.py` | TenantBoundModel base class |
| `backend/apps/core/fields.py` | MoneyField, PostgresEnumField |

## 8. Critical Reminders

- **MoneyField** for ALL monetary values (17,3 storage, 3 decimals)
- **DECIMAL(16,4)** for quantities (matches existing inventario patterns)
- **TenantBoundModel** for ALL new models (auto tenant validation)
- **select_for_update()** when checking/reserving stock (prevent TOCTOU)
- **Nullable FKs** on Comprobante enhancements (backward compatibility)
- **OneToOneField on Comprobante side** — `Comprobante.sale_order` points to SaleOrder; access from SaleOrder via `order.comprobante_direct` (no comprobante FK on SaleOrder)
- **StockMovement.status defaults to COMMITTED** (existing rows are COMMITTED)
- **StockMovement immutability exception** — `comprobante_id` can be set during RESERVED→COMMITTED transition (whitelisted in save())
- **resolver_tipo_comprobante()** already exists — reuse, don't rewrite
- **InvoiceService** handles ARCA communication — SaleService delegates to it
- **334 existing tests** must keep passing after all changes
