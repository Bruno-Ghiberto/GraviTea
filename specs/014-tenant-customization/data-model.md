# Data Model: Tenant Customization Framework

**Branch**: `014-tenant-customization` | **Date**: 2026-02-20
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Entity Definitions

### TenantFieldDefinition

**Location**: `backend/apps/core/models/customization.py`
**Inherits**: `TenantBoundModel` (tenant isolation via RLS)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | `UUIDField` | PK, auto-generated | Inherited from TenantBoundModel |
| `tenant` | `ForeignKey(Tenant)` | NOT NULL, ON DELETE CASCADE | Inherited from TenantBoundModel |
| `field_key` | `CharField(max_length=50)` | NOT NULL, regex `^[a-z][a-z0-9_]{0,49}$` | Unique identifier for the field within tenant+entity_type |
| `label` | `CharField(max_length=100)` | NOT NULL | Human-readable display name |
| `entity_type` | `CharField(max_length=20)` | NOT NULL, choices: `product`, `customer`, `supplier`, `sale_order` | Which entity this field applies to |
| `field_type` | `CharField(max_length=10)` | NOT NULL, choices: `text`, `integer`, `decimal`, `boolean`, `date`, `select` | Data type for validation and rendering |
| `section` | `CharField(max_length=100)` | NOT NULL, default `"custom_fields"` | UI grouping label |
| `position` | `PositiveIntegerField` | NOT NULL, default `0` | Sort order within section |
| `required` | `BooleanField` | NOT NULL, default `False` | Whether the field is mandatory on create/update |
| `default_value` | `JSONField` | NULL, blank=True | Default value (type matches field_type). Applied on create only when key absent. |
| `choices` | `JSONField` | NULL, blank=True | List of allowed values for `select` type. Example: `["acero","aluminio","plastico"]` |
| `active` | `BooleanField` | NOT NULL, default `True` | Inactive fields are excluded from validation and API response |
| `created_at` | `DateTimeField` | auto_now_add | Inherited from TenantBoundModel |
| `updated_at` | `DateTimeField` | auto_now | Inherited from TenantBoundModel |

**Constraints**:
- `UniqueConstraint(fields=["tenant", "entity_type", "field_key"], name="unique_field_per_tenant_entity")`

**Validators**:
- `field_key`: `RegexValidator(r'^[a-z][a-z0-9_]{0,49}$', 'field_key must be snake_case, start with letter, max 50 chars')`
- `choices`: If `field_type == "select"`, `choices` must be a non-empty list of strings
- `default_value`: If provided, must match `field_type` (e.g., integer default must be int)

**Ordering**: `["section", "position", "field_key"]`

**Manager**: `TenantBoundManager` (inherited — ensures all queries are tenant-scoped)

---

### TenantModuleConfig

**Location**: `backend/apps/core/models/customization.py`
**Inherits**: `TenantBoundModel`

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | `UUIDField` | PK, auto-generated | Inherited from TenantBoundModel |
| `tenant` | `ForeignKey(Tenant)` | NOT NULL, ON DELETE CASCADE | Inherited from TenantBoundModel |
| `module` | `CharField(max_length=20)` | NOT NULL, choices: `inventario`, `ventas`, `facturacion`, `sync` | Module identifier |
| `enabled` | `BooleanField` | NOT NULL, default `True` | Whether the module is active for this tenant |
| `settings` | `JSONField` | NOT NULL, default=dict, blank=True | Module-specific settings (future extensibility) |
| `created_at` | `DateTimeField` | auto_now_add | Inherited |
| `updated_at` | `DateTimeField` | auto_now | Inherited |

**Constraints**:
- `UniqueConstraint(fields=["tenant", "module"], name="unique_module_per_tenant")`

**Manager**: `TenantBoundManager`

---

### BusinessTemplate

**Location**: `backend/apps/core/models/customization.py`
**Inherits**: `models.Model` (NOT TenantBoundModel — system-wide resource)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | `UUIDField` | PK, `uuid.uuid4` | System-wide unique identifier |
| `slug` | `SlugField(max_length=50)` | UNIQUE, NOT NULL | URL-safe identifier (e.g., `ferreteria`) |
| `name` | `CharField(max_length=100)` | NOT NULL | Human-readable template name |
| `description` | `TextField` | blank=True | Template purpose description |
| `modules` | `JSONField` | NOT NULL, default=list | List of module names to enable. Example: `["inventario", "ventas", "facturacion"]` |
| `field_definitions` | `JSONField` | NOT NULL, default=list | List of field definition dicts to create. Each dict mirrors TenantFieldDefinition fields. |
| `created_at` | `DateTimeField` | auto_now_add | |
| `updated_at` | `DateTimeField` | auto_now | |

**No tenant FK**: BusinessTemplate is visible to all tenants. It defines what TO create, not who owns it.

**Manager**: Default Django `Manager` (NOT TenantBoundManager)

---

## Modified Entities

### Product (inventario)

**Change**: Rename `attributes` → `custom_data`

| Field | Before | After |
|-------|--------|-------|
| `attributes` | `JSONField(default=dict, blank=True)` | Renamed to `custom_data` |
| `ml_tags` | `JSONField(default=dict, blank=True)` | **No change** — remains independent |

**Migration**: `RenameField(model_name="product", old_name="attributes", new_name="custom_data")`

**Index**: `GinIndex(fields=["custom_data"], opclasses=["jsonb_path_ops"], name="idx_product_custom_data")`

---

### Customer (ventas)

**Change**: Add `custom_data` field

| Field | Type | Constraints |
|-------|------|-------------|
| `custom_data` | `JSONField` | NOT NULL, default=dict, blank=True |

**Index**: `GinIndex(fields=["custom_data"], opclasses=["jsonb_path_ops"], name="idx_customer_custom_data")`

---

### Supplier (inventario)

**Change**: Add `custom_data` field

| Field | Type | Constraints |
|-------|------|-------------|
| `custom_data` | `JSONField` | NOT NULL, default=dict, blank=True |

**Index**: `GinIndex(fields=["custom_data"], opclasses=["jsonb_path_ops"], name="idx_supplier_custom_data")`

---

### SaleOrder (ventas)

**Change**: Add `custom_data` field

| Field | Type | Constraints |
|-------|------|-------------|
| `custom_data` | `JSONField` | NOT NULL, default=dict, blank=True |

**Index**: `GinIndex(fields=["custom_data"], opclasses=["jsonb_path_ops"], name="idx_saleorder_custom_data")`

---

## Entity Relationship Diagram

```text
Tenant (core)
  │
  ├─── 1:N ──► TenantFieldDefinition (core)
  │              unique(tenant, entity_type, field_key)
  │
  ├─── 1:N ──► TenantModuleConfig (core)
  │              unique(tenant, module)
  │
  ├─── 1:N ──► Product (inventario)
  │              .custom_data validated against TenantFieldDefinition(entity_type='product')
  │
  ├─── 1:N ──► Customer (ventas)
  │              .custom_data validated against TenantFieldDefinition(entity_type='customer')
  │
  ├─── 1:N ──► Supplier (inventario)
  │              .custom_data validated against TenantFieldDefinition(entity_type='supplier')
  │
  └─── 1:N ──► SaleOrder (ventas)
                 .custom_data validated against TenantFieldDefinition(entity_type='sale_order')

BusinessTemplate (core) ─── system-wide, no tenant FK
  │
  └─── apply_template command ──► creates TenantFieldDefinition + TenantModuleConfig rows
```

## Migration Strategy

### Order of Operations

1. **Core migration `0003_customization_models`**:
   - Create `TenantFieldDefinition` table with all fields, constraints, validators
   - Create `TenantModuleConfig` table with unique constraint
   - Create `BusinessTemplate` table
   - RLS policies auto-apply to TenantFieldDefinition and TenantModuleConfig (they inherit TenantBoundModel)
   - BusinessTemplate gets NO RLS (not tenant-bound)

2. **Inventario migration `0006_product_custom_data`**:
   - `RenameField(model_name="product", old_name="attributes", new_name="custom_data")`
   - `AddField(model_name="supplier", name="custom_data", field=JSONField(default=dict, blank=True))`
   - Add GIN indexes on both Product.custom_data and Supplier.custom_data

3. **Ventas migration `0003_custom_data_fields`**:
   - `AddField(model_name="customer", name="custom_data", field=JSONField(default=dict, blank=True))`
   - `AddField(model_name="saleorder", name="custom_data", field=JSONField(default=dict, blank=True))`
   - Add GIN indexes on both

### Rollback Plan

Each migration is reversible:
- Core: Drop 3 tables
- Inventario: Rename `custom_data` back to `attributes`, drop Supplier.custom_data, drop indexes
- Ventas: Drop `custom_data` fields and indexes

## Ferreteria Template Data

The `apply_template` management command includes a built-in "ferreteria" template:

```json
{
  "slug": "ferreteria",
  "name": "Ferretería (Hardware Store)",
  "description": "Template for industrial hardware stores with weight, dimensions, and material tracking",
  "modules": ["inventario", "ventas", "facturacion"],
  "field_definitions": [
    {"field_key": "peso_kg", "label": "Peso (kg)", "entity_type": "product", "field_type": "decimal", "section": "dimensiones", "position": 0, "required": false},
    {"field_key": "largo_cm", "label": "Largo (cm)", "entity_type": "product", "field_type": "decimal", "section": "dimensiones", "position": 1, "required": false},
    {"field_key": "ancho_cm", "label": "Ancho (cm)", "entity_type": "product", "field_type": "decimal", "section": "dimensiones", "position": 2, "required": false},
    {"field_key": "alto_cm", "label": "Alto (cm)", "entity_type": "product", "field_type": "decimal", "section": "dimensiones", "position": 3, "required": false},
    {"field_key": "material", "label": "Material", "entity_type": "product", "field_type": "select", "section": "caracteristicas", "position": 0, "required": false, "choices": ["acero", "aluminio", "plastico", "madera", "vidrio", "cobre", "bronce"]},
    {"field_key": "marca", "label": "Marca", "entity_type": "product", "field_type": "text", "section": "caracteristicas", "position": 1, "required": false},
    {"field_key": "codigo_proveedor", "label": "Código Proveedor", "entity_type": "product", "field_type": "text", "section": "caracteristicas", "position": 2, "required": false}
  ]
}
```
