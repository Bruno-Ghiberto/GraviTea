# Inventario Module

The `inventario` module provides inventory management for GRAVITEA ERP, implementing an immutable ledger pattern for stock tracking with full audit trail.

## Directory Structure

```
apps/inventario/
├── migrations/          # Database migrations
├── models/              # Inventory data models
│   ├── __init__.py
│   ├── product.py       # Product, Category models
│   └── stock.py         # StockSnapshot, StockMovement models
├── serializers/         # DRF serializers
│   ├── __init__.py
│   ├── product.py       # Product serializers
│   └── stock.py         # Stock serializers
├── services/            # Business logic services
│   └── stock_service.py # StockService for stock operations
├── views/               # API ViewSets
│   ├── __init__.py
│   ├── product.py       # ProductViewSet
│   └── stock.py         # StockViewSet
├── admin.py             # Django admin configuration
└── apps.py              # Django app configuration
```

## Key Models

### Category

Product categorization:

```python
class Category(TenantBoundModel):
    name = models.CharField(max_length=255)
    parent = models.ForeignKey('self', null=True, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
```

### Product

Core product entity:

```python
class Product(TenantBoundModel):
    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=100)  # Unique within tenant
    barcode = models.CharField(max_length=100, blank=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    base_price = models.DecimalField(max_digits=17, decimal_places=3)
    cost_price = models.DecimalField(max_digits=17, decimal_places=3)
    is_active = models.BooleanField(default=True)

    # ML metadata fields (FR-017, SC-017)
    ml_category_confidence = models.FloatField(null=True)
    ml_last_categorized = models.DateTimeField(null=True)
    ml_features = models.JSONField(default=dict)
```

### StockSnapshot

Current stock levels per branch:

```python
class StockSnapshot(TenantBoundModel):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=17, decimal_places=3)
    reserved_quantity = models.DecimalField(max_digits=17, decimal_places=3, default=0)
    last_movement_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['tenant', 'branch', 'product']
```

### StockMovement

Immutable ledger for stock changes (SC-016):

```python
class StockMovement(TenantBoundModel):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    movement_type = models.CharField(max_length=50)  # purchase, sale, adjustment, transfer
    quantity = models.DecimalField(max_digits=17, decimal_places=3)
    reference = models.CharField(max_length=255)  # PO number, invoice, etc.
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(AppUser, on_delete=models.PROTECT)

    # Immutable - no update/delete allowed
    class Meta:
        ordering = ['-created_at']
```

## API Endpoints

### Products

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/inventory/products/` | GET | List products (cursor paginated) |
| `/api/v1/inventory/products/` | POST | Create product |
| `/api/v1/inventory/products/{id}/` | GET | Get product details |
| `/api/v1/inventory/products/{id}/` | PATCH | Update product |
| `/api/v1/inventory/products/search/` | GET | Search by name/SKU/barcode |
| `/api/v1/inventory/products/low-stock/` | GET | Products below min stock |

### Categories

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/inventory/categories/` | GET | List categories |
| `/api/v1/inventory/categories/` | POST | Create category |
| `/api/v1/inventory/categories/{id}/` | GET | Get category with products |
| `/api/v1/inventory/categories/tree/` | GET | Category tree structure |

### Stock

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/inventory/stock/` | GET | Current stock levels |
| `/api/v1/inventory/stock/movements/` | GET | Movement history |
| `/api/v1/inventory/stock/movements/` | POST | Record movement |
| `/api/v1/inventory/stock/transfer/` | POST | Branch-to-branch transfer |
| `/api/v1/inventory/stock/adjustment/` | POST | Stock correction |

## StockService

Business logic for stock operations:

```python
from apps.inventario.services.stock_service import StockService

service = StockService(tenant=tenant, branch=branch, user=user)

# Record purchase
service.record_movement(
    product=product,
    movement_type="purchase",
    quantity=Decimal("100"),
    reference="PO-2025-001"
)

# Record sale
service.record_movement(
    product=product,
    movement_type="sale",
    quantity=Decimal("-5"),
    reference="INV-2025-1001"
)

# Create correction
service.create_correction(
    product=product,
    new_quantity=Decimal("95"),
    reason="Physical count adjustment"
)

# Transfer between branches
service.transfer_stock(
    product=product,
    target_branch=other_branch,
    quantity=Decimal("20"),
    reference="TRF-2025-001"
)
```

## Immutable Ledger Pattern

All stock changes are recorded as immutable movements (SC-016):

```
Time    | Type       | Quantity | Balance | Reference
--------|------------|----------|---------|------------
T1      | purchase   | +100     | 100     | PO-001
T2      | sale       | -5       | 95      | INV-001
T3      | adjustment | +2       | 97      | ADJ-001
T4      | transfer   | -10      | 87      | TRF-001
```

**Features:**
- No UPDATE or DELETE on movements
- Point-in-time reconstruction capability
- Complete audit trail
- Database triggers prevent modification

## Query Optimization

### N+1 Prevention (SC-020)

All ViewSets use optimized querysets:

```python
class ProductViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        return Product.objects.filter(
            tenant=self.request.user.tenant
        ).select_related(
            'category'
        ).prefetch_related(
            'stocksnapshot_set'
        )
```

### Cursor Pagination (SC-015)

Efficient pagination for large catalogs:

```python
# Handles 50,000+ products efficiently
GET /api/v1/inventory/products/?cursor=cD0yMDI1LTAxLTAxVDAwOjAwOjAwLjAwMDAwMFo=
```

## Barcode Search

Fast barcode lookup for POS (< 50ms target):

```python
# Search by exact barcode
product = Product.objects.filter(
    tenant=tenant,
    barcode=barcode
).select_related('category').first()

# Search by barcode prefix (scanner input)
products = Product.objects.filter(
    tenant=tenant,
    barcode__startswith=partial_barcode
)[:10]
```

## ML Metadata (FR-017, SC-017)

Products include ML readiness fields:

```python
# Store ML categorization results
product.ml_category_confidence = 0.95
product.ml_last_categorized = timezone.now()
product.ml_features = {
    "embedding": [...],
    "predicted_category": "Electronics",
    "similar_products": [123, 456, 789]
}
product.save()
```

## Configuration

### Django Settings

```python
# Pagination
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'apps.core.pagination.CursorPagination',
    'PAGE_SIZE': 50,
}

# Decimal precision
DECIMAL_MAX_DIGITS = 17
DECIMAL_PLACES = 3
```

## Performance Targets

| Operation | Target | Implementation |
|-----------|--------|----------------|
| Product list (50 items) | < 200ms | Cursor pagination, select_related |
| Barcode search | < 50ms | Indexed barcode field |
| Stock query | < 100ms | Branch-scoped, indexed |
| Movement recording | < 100ms | Atomic transaction |

## Testing

```bash
# Run inventory tests
pytest apps/inventario/tests/ -v

# Run performance tests
pytest apps/inventario/tests/test_performance.py -v

# Run N+1 detection
pytest tests/performance/test_n_plus_one.py -v
```

## Related Documentation

- [Data Model](../../../specs/001-backend-core/data-model.md)
- [API Contracts](../../../specs/001-backend-core/contracts/inventory-api.yaml)
- [Performance Baselines](../../PERFORMANCE.md)
