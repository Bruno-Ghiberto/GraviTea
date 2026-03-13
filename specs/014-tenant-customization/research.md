# Phase 0 Research: Tenant Customization Framework

**Branch**: `014-tenant-customization` | **Date**: 2026-02-20
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Research Questions & Findings

### 1. Product.attributes Field

**Decision**: Rename `Product.attributes` to `custom_data` via `RenameField` migration.

**Finding**:
- Field: `JSONField(default=dict, blank=True)` at `models.py:347`
- `ml_tags` is a separate, independent `JSONField` at line 375 — ML-generated only, never manual
- No business logic references `.attributes` by name — only serializers and tests
- Seeds (`seed_inventario.py`) do NOT populate `attributes` — products use default empty dict
- Both `ProductSerializer` (read) and `ProductCreateSerializer` (write) include `attributes` in field lists

**Rationale**: Clean rename with zero data loss. No code besides serializers/tests references the field name directly. Seeds are unaffected since they don't set the field.

**Alternatives**: (a) Add a second JSONField `custom_data` alongside `attributes` — rejected, creates confusion and data duplication. (b) Keep name `attributes` — rejected, `custom_data` better communicates purpose and aligns with other entities.

**Impact**: Serializers must update field name. Tests referencing `attributes` must update. Migration is a simple `RenameField`.

---

### 2. Existing Serializer Patterns

**Decision**: Create `CustomFieldsMixin` as a new pattern. Existing serializers do NOT use mixins.

**Finding**:
- **ProductSerializer** (read): `ModelSerializer` with computed fields (`price_with_tax`, `category_name`). Explicit field lists.
- **ProductCreateSerializer** (write): Separate class with `validate_*` methods, `create()` injects tenant from `request.user.tenant`.
- **CustomerSerializer**: Single class for read/write. `validate_cuit()`, `condicion_iva_display` via `SerializerMethodField`.
- **SaleOrderSerializer**: Read with `comprobante_id` computed field. `SaleOrderDetailSerializer` for nested items.
- **SupplierSerializer**: Standard `ModelSerializer` pattern.
- **No mixin usage** anywhere — each serializer implements validation independently.

**Rationale**: `CustomFieldsMixin` will be the project's FIRST serializer mixin. It must be designed to inject into existing serializers without breaking their validation flow. The mixin hooks into `validate()` and `create()`/`update()` methods.

**Alternatives**: (a) Inline validation in each serializer — rejected, violates DRY across 4 entities. (b) Separate validation serializer — rejected, adds complexity without reuse benefit.

**Impact**: Mixin must call `super().validate()` and `super().create()`/`super().update()` to preserve existing serializer behavior.

---

### 3. Migration Numbering

**Decision**: Use next available numbers per app.

**Finding**:

| App | Latest Migration | Next |
|-----|-----------------|------|
| `core` | `0002_add_rls_policies` | `0003` |
| `inventario` | `0005_pricelist_unique_default_per_tenant` | `0006` |
| `ventas` | `0002_add_rls_policies` | `0003` |

**Rationale**: Django auto-numbers migrations. Manual naming follows `000N_descriptive_name.py` convention used by existing migrations.

**Migration order**: `core` first (new models TenantFieldDefinition, TenantModuleConfig, BusinessTemplate), then `inventario` (rename Product.attributes + add Supplier.custom_data), then `ventas` (add Customer.custom_data + SaleOrder.custom_data).

---

### 4. Admin Patterns

**Decision**: Create `backend/apps/core/admin.py` with standard `ModelAdmin` registrations.

**Finding**:
- **No `admin.py` exists** in `apps/core/` — the module has no admin registrations
- `django.contrib.admin` IS in `INSTALLED_APPS` (base settings)
- `/admin/` URL is configured in root `urls.py`
- No other app has admin registrations either — this is an API-first project

**Rationale**: FR-014 requires admin views for TenantFieldDefinition, TenantModuleConfig, and BusinessTemplate. Standard `ModelAdmin` with `list_display`, `list_filter`, `search_fields` follows Django conventions.

**Impact**: First admin.py in the project. Sets the pattern for future admin registrations.

---

### 5. Cache Configuration

**Decision**: Use `django.core.cache` with existing infrastructure. 60s TTL, keyed by `field_defs:{tenant_id}:{entity_type}`.

**Finding**:
- **Development**: `LocMemCache` (in-memory, non-persistent) configured in `settings/development.py`
- **Production**: `REDIS_URL` environment variable exists; Redis service available in Docker Compose
- **Existing usage**: `apps.core.security.rate_limiter.py` uses `cache.get()`, `cache.set()`, `cache.incr()`, `cache.delete()` — proven pattern
- **Test fixtures**: `tests/fixtures/cache.py` provides `mock_cache` and `mock_cache_stateful` fixtures

**Rationale**: Existing cache infrastructure is sufficient. No new cache backend needed. LocMemCache works for development; Redis for production. Signal-based invalidation via `post_save`/`post_delete` on TenantFieldDefinition ensures consistency.

**Impact**: Cache invalidation requires connecting Django signals — first use of signals for cache in this project.

---

### 6. Frontend Form Patterns

**Decision**: Create `DynamicFields` component following existing `FieldConfig[]` pattern. Place in `frontend-prototype/src/components/inventario/`.

**Finding**:
- **Form state**: Manual `useState` hooks — no form library (not React Hook Form, not Formik)
- **Component library**: shadcn/ui (`Button`, `Input`, etc.) + custom `CrudForm` and `DataTable` components
- **Field rendering**: Declarative `FieldConfig[]` array defines fields with `name`, `label`, `type`, `required`, `placeholder`
- **Error handling**: `ApiError` extraction with field-level error display
- **No form library overhead**: Simple state + event handlers

**Rationale**: `DynamicFields` fetches field definitions from API, converts them to `FieldConfig[]` format, and renders via similar input patterns. Integrates into `products-tab.tsx` as a section below standard fields.

**Impact**: Must align with `CrudForm` field rendering pattern. Dynamic fields rendered as separate section, not mixed into standard fields.

---

### 7. URL Routing

**Decision**: Create `backend/apps/core/urls.py` for customization API endpoints. Include in root `urls.py` under `/api/v1/`.

**Finding**:
- **Root config**: Hierarchical under `/api/v1/` — each app included separately
- **Core has NO API urls.py** — only `health/urls.py` and `observability/urls.py` (both outside `/api/v1/`)
- **Router pattern**: `DefaultRouter()` used by inventario (registers ViewSets)
- **Include pattern**: `path("", include("apps.inventario.urls"))` — inventario has no prefix

**Rationale**: New endpoints (`/api/v1/field-definitions/`, `/api/v1/module-config/`) belong in core since the models are in core. Creating `core/urls.py` with its own `DefaultRouter` follows the inventario pattern.

**URL registration in root**:
```python
path("", include("apps.core.urls")),  # Field definitions, module config
```

**Impact**: First API endpoints in `apps/core/`. Sets pattern for future core API endpoints.

---

### 8. Seed Data Impact

**Decision**: Rename is safe. Seeds do NOT use `Product.attributes`.

**Finding**:
- `seed_inventario.py` creates 25 products with `get_or_create()` — idempotent
- `attributes` NOT in the `defaults` dict — products get empty dict default
- `ml_tags` also NOT populated in seeds
- Seed data uses: `sku`, `name`, `category`, `supplier`, `cost_price`, `unit_price`, `tax_rate`, `min_stock`, `is_active`

**Rationale**: Zero seed data impact. After rename, new seeds for `apply_template` command can populate `custom_data` for ferreteria template demonstration.

**Impact**: No changes to existing seed commands needed. New `apply_template` command handles template-based seeding separately.

---

## Summary of Decisions

| # | Decision | Confidence |
|---|----------|-----------|
| 1 | Rename `attributes` → `custom_data` via `RenameField` | High |
| 2 | Create `CustomFieldsMixin` (first mixin in project) | High |
| 3 | Migration order: core (0003) → inventario (0006) → ventas (0003) | High |
| 4 | Create `apps/core/admin.py` (first admin in project) | High |
| 5 | Use existing cache infrastructure with 60s TTL + signal invalidation | High |
| 6 | `DynamicFields` in inventario, follows `FieldConfig[]` pattern | High |
| 7 | Create `apps/core/urls.py` with `DefaultRouter` for new endpoints | High |
| 8 | Seed rename is safe, no existing data uses `attributes` | High |

**Blockers**: None identified.
**Risks**: First mixin, first admin, first core API endpoints — all are "firsts" that set patterns. Quality matters.
