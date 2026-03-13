# Quickstart: Tenant Customization Framework

**Branch**: `014-tenant-customization` | **Date**: 2026-02-20

## Prerequisites

- Docker Compose running (`docker compose up -d`)
- Seed data loaded (`docker compose exec web python manage.py seed_all`)
- Frontend accessible at `http://localhost:3000`
- Backend API at `http://localhost:8000`

## Verify Implementation

### 1. Run Migrations

```bash
docker compose exec web python manage.py migrate
```

Expected output: 3 new migrations applied (core 0003, inventario 0006, ventas 0003).

### 2. Apply Ferreteria Template

```bash
docker compose exec web python manage.py apply_template ferreteria --tenant-id <TENANT_UUID>
```

Expected output:
- 3 module configs created (inventario, ventas, facturacion — all enabled)
- 7 field definitions created for Product (peso_kg, largo_cm, ancho_cm, alto_cm, material, marca, codigo_proveedor)

Run again to verify idempotency — should report "already exists" for all records.

### 3. Verify Field Definitions API

```bash
# Get JWT token
TOKEN=$(curl -s http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@gravitea.com","password":"admin123"}' | python -c "import sys,json; print(json.load(sys.stdin)['access'])")

# List all field definitions
curl -s http://localhost:8000/api/v1/field-definitions/ \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool

# Filter by entity type
curl -s "http://localhost:8000/api/v1/field-definitions/?entity_type=product" \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
```

Expected: 7 field definitions returned, ordered by section + position.

### 4. Verify Module Config API

```bash
curl -s http://localhost:8000/api/v1/module-config/ \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
```

Expected: 3 module configs (inventario, ventas, facturacion — all enabled).

### 5. Verify Custom Data Validation

```bash
# Create a product with valid custom data
curl -s http://localhost:8000/api/v1/products/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "sku": "TEST-CUSTOM-001",
    "name": "Test Custom Product",
    "cost_price": "10.00",
    "unit_price": "15.00",
    "tax_rate": "21.00",
    "min_stock": "5",
    "custom_data": {"peso_kg": 2.5, "material": "acero"}
  }' | python -m json.tool

# Try invalid custom data (wrong type for peso_kg)
curl -s http://localhost:8000/api/v1/products/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "sku": "TEST-CUSTOM-002",
    "name": "Test Invalid Product",
    "cost_price": "10.00",
    "unit_price": "15.00",
    "tax_rate": "21.00",
    "min_stock": "5",
    "custom_data": {"peso_kg": "not_a_number"}
  }'

# Try invalid choice for material
curl -s http://localhost:8000/api/v1/products/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "sku": "TEST-CUSTOM-003",
    "name": "Test Invalid Choice",
    "cost_price": "10.00",
    "unit_price": "15.00",
    "tax_rate": "21.00",
    "min_stock": "5",
    "custom_data": {"material": "titanio"}
  }'
```

Expected: First request succeeds. Second returns validation error for `peso_kg`. Third returns validation error for `material` with allowed choices.

### 6. Verify Merge Semantics

```bash
# Update product — only send peso_kg (material should be preserved)
curl -s -X PATCH http://localhost:8000/api/v1/products/<PRODUCT_ID>/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"custom_data": {"peso_kg": 3.0}}'

# Remove a key by sending null
curl -s -X PATCH http://localhost:8000/api/v1/products/<PRODUCT_ID>/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"custom_data": {"material": null}}'
```

Expected: First PATCH merges — `peso_kg` updated to 3.0, `material` preserved. Second PATCH removes `material` from `custom_data`.

### 7. Verify Frontend DynamicFields

1. Open `http://localhost:3000` and login
2. Navigate to Inventario via sidebar
3. Click "New Product"
4. Below standard fields, a "Custom Fields" section should appear with:
   - **Dimensiones**: peso_kg, largo_cm, ancho_cm, alto_cm (number inputs)
   - **Caracteristicas**: material (dropdown with 7 choices), marca (text), codigo_proveedor (text)
5. Fill in custom fields and submit — values should be saved and visible on edit

### 8. Verify Admin Interface

1. Open `http://localhost:8000/admin/`
2. Under "Core", find:
   - **Tenant Field Definitions** — list with field_key, label, entity_type, field_type, section, active
   - **Tenant Module Configs** — list with tenant, module, enabled
   - **Business Templates** — list with slug, name

### 9. Run Tests

```bash
docker compose exec web pytest tests/core/test_customization_models.py -v
docker compose exec web pytest tests/core/test_custom_fields_mixin.py -v
docker compose exec web pytest tests/core/test_field_definitions_api.py -v
docker compose exec web pytest tests/core/test_module_config_api.py -v
docker compose exec web pytest tests/core/test_apply_template.py -v
docker compose exec web pytest tests/integration/test_custom_fields_e2e.py -v
```

All tests should pass with zero failures.
