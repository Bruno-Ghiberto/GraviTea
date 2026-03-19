# Data Model: Storage & Position (Spec-12)

**Generated**: 2026-03-19
**Source**: Data Model v1.0 §5.6, 12-specify.md entity definitions, spec.md requirements

---

## Entity Overview

```
                    ┌─────────────────┐
                    │     Branch      │ (from core — pre-existing)
                    └────────┬────────┘
                             │ 1:N
                ┌────────────▼──────────────────────────┐
                │          StorageUnit                  │
                │ id, name, unit_type, capacity_tonnes  │
                │ current_grain_type (FK→GrainType)     │
                │ is_active, environment_sensor_id      │
                │ tenant, branch, created_by            │
                └────────────┬──────────────────────────┘
                             │ 1:N (related_name=grain_lots)
                ┌────────────▼──────────────────────────┐
                │             GrainLot                  │
                │ id, lot_code (auto-generated)         │
                │ grain_type, campaign, grado           │
                │ total_kg (running balance)            │
                │ is_own_grain (ADR-020 accounting)     │
                │ tenant, branch, storage_unit          │
                │ created_by                            │
                │ [UniqueConstraint on composite key]   │
                └────────────┬──────────────────────────┘
                             │ 1:N (related_name=movements)
                ┌────────────▼──────────────────────────┐
                │          GrainMovement                │  ← IMMUTABLE
                │ id, movement_type, quantity_kg        │
                │ romaneo (FK→Romaneo, nullable)        │
                │ movement_at (auto_now_add)            │
                │ reference_document, notes             │
                │ tenant, grain_lot                     │
                │ created_by, device_id                 │
                └───────────────────────────────────────┘

     Romaneo (pre-existing, MODIFIED)
     ├── storage_unit (FK→StorageUnit, SET_NULL, nullable) ← NEW in spec-12
     └── grain_lot   (FK→GrainLot, SET_NULL, nullable)    ← NEW in spec-12
```

---

## Entity: StorageUnit

**Table**: `acopio_storageunit`
**Inherits**: `TenantBoundModel`
**Manager**: `TenantBoundManager` (fail-closed) + `AllObjectsManager`

### Fields

| Field | Django Type | DB Type | Null | Default | Notes |
|-------|-------------|---------|------|---------|-------|
| `id` | UUIDField PK | uuid | No | uuid4 | Immutable |
| `tenant` | FK(Tenant, PROTECT) | uuid | No | — | TenantBound |
| `branch` | FK(Branch, PROTECT) | uuid | No | — | Plant this unit belongs to |
| `name` | CharField(100) | varchar(100) | No | — | User-visible label, e.g. "Silo 1" |
| `unit_type` | CharField choices | varchar | No | — | SILO_VERTICAL \| CELDA_HORIZONTAL \| SECADERO_BIN |
| `capacity_tonnes` | DecimalField(12,3) | numeric(12,3) | No | — | Nominal capacity; multiply × 1000 for kg |
| `current_grain_type` | FK(GrainType, SET_NULL) | uuid | Yes | NULL | NULL = empty unit |
| `is_active` | BooleanField | boolean | No | True | Soft-delete flag |
| `environment_sensor_id` | CharField(100) | varchar(100) | Yes | NULL | IoT anchor (Phase 4) |
| `created_at` | DateTimeField(auto_now_add) | timestamptz | No | — | ADR-034 |
| `updated_at` | DateTimeField(auto_now) | timestamptz | No | — | ADR-034 |
| `created_by` | FK(AppUser, PROTECT) | uuid | No | — | ADR-034 |

**Derived field** (not stored): `current_occupancy_kg`
Computed via: `Sum("grain_lots__movements__quantity_kg")` in annotated queryset.
Returned in API responses as a read-only decimal.

### Constraints

```python
constraints = [
    UniqueConstraint(
        fields=["tenant", "branch", "name"],
        name="uq_storageunit_tenant_branch_name",
    ),
]
indexes = [
    Index(fields=["tenant_id", "branch_id", "is_active"],
          name="idx_storageunit_tenant_branch_active"),
]
```

### Validation Rules

- `name` unique within `(tenant, branch)` — `UniqueConstraint` + serializer validation
- `capacity_tonnes` must be positive (validate in serializer)
- Cannot delete / deactivate if any active GrainLot has `total_kg > 0`
  (validated in service layer before deactivation)
- `unit_type` must be one of: `SILO_VERTICAL`, `CELDA_HORIZONTAL`, `SECADERO_BIN`

### State Transitions

StorageUnit has no formal state machine. `is_active` is toggled for soft-deactivation.

---

## Entity: GrainLot

**Table**: `acopio_grainlot`
**Inherits**: `TenantBoundModel`
**Manager**: `TenantBoundManager` (fail-closed) + `AllObjectsManager`

### Fields

| Field | Django Type | DB Type | Null | Default | Notes |
|-------|-------------|---------|------|---------|-------|
| `id` | UUIDField PK | uuid | No | uuid4 | Immutable |
| `tenant` | FK(Tenant, PROTECT) | uuid | No | — | TenantBound |
| `lot_code` | CharField(100) | varchar(100) | No | — | Auto-generated: BRANCH-GRAIN-CAMPAIGN-GRADE |
| `branch` | FK(Branch, PROTECT) | uuid | No | — | Plant |
| `grain_type` | FK(GrainType, PROTECT) | uuid | No | — | Grain commodity |
| `campaign` | FK(CampanaConfig, PROTECT) | uuid | No | — | Harvest campaign year |
| `grado` | IntegerField | integer | No | — | 1/2/3 for cereals; 0 for oleaginosas |
| `storage_unit` | FK(StorageUnit, PROTECT) | uuid | No | — | Physical storage location |
| `total_kg` | DecimalField(17,3) | numeric(17,3) | No | 0.000 | Running balance; updated on each movement |
| `is_own_grain` | BooleanField | boolean | No | False | ADR-020; True→1.3.XX; False→8.1.XX |
| `created_at` | DateTimeField(auto_now_add) | timestamptz | No | — | ADR-034 |
| `updated_at` | DateTimeField(auto_now) | timestamptz | No | — | ADR-034 |
| `created_by` | FK(AppUser, PROTECT) | uuid | No | — | ADR-034 |

### Constraints

```python
constraints = [
    UniqueConstraint(
        fields=["tenant", "branch", "grain_type", "campaign", "grado", "storage_unit"],
        name="uq_grainlot_composite_identity",
    ),
    CheckConstraint(
        check=Q(total_kg__gte=0),
        name="chk_grainlot_nonnegative_balance",
    ),
]
indexes = [
    Index(fields=["tenant_id", "storage_unit_id"],
          name="idx_grainlot_tenant_storage"),
    Index(fields=["tenant_id", "campaign_id", "grain_type_id"],
          name="idx_grainlot_tenant_campaign_grain"),
]
```

### Validation Rules

- `lot_code` auto-generated on first save: `{BRANCH_CODE}-{GRAIN_CODE}-{CAMPAIGN_CODE}-{GRADO}`
- Composite key `(tenant, branch, grain_type, campaign, grado, storage_unit)` unique
- `total_kg >= 0` enforced at DB level (CheckConstraint) AND at service layer
  (balance check before each withdrawal)
- `is_own_grain` must be set at creation; cannot change after first movement

### Running Balance Lifecycle

```
lot.total_kg starts at 0.000
+ DEPOSIT quantity_kg     (positive, from romaneo peso_neto_conforme_kg)
- WITHDRAWAL |quantity_kg| (stored negative, reduces balance)
+ TRANSFER_IN quantity_kg
- TRANSFER_OUT |quantity_kg|
+/- ADJUSTMENT quantity_kg  (sign indicates surplus/deficit)
= lot.total_kg at any point must equal Sum(GrainMovement.quantity_kg for this lot)
```

---

## Entity: GrainMovement

**Table**: `acopio_grainmovement`
**Inherits**: `TenantBoundModel`
**Manager**: `TenantBoundManager` (fail-closed) + `AllObjectsManager`
**Immutability**: FULLY IMMUTABLE — no UPDATE, no DELETE

### Fields

| Field | Django Type | DB Type | Null | Default | Notes |
|-------|-------------|---------|------|---------|-------|
| `id` | UUIDField PK | uuid | No | uuid4 | Immutable |
| `tenant` | FK(Tenant, PROTECT) | uuid | No | — | TenantBound |
| `grain_lot` | FK(GrainLot, PROTECT) | uuid | No | — | Target lot; related_name="movements" |
| `movement_type` | CharField choices | varchar | No | — | See movement type table below |
| `quantity_kg` | DecimalField(17,3) | numeric(17,3) | No | — | Positive=inflow; negative=outflow |
| `romaneo` | FK(Romaneo, SET_NULL) | uuid | Yes | NULL | Source romaneo (DEPOSIT only) |
| `movement_at` | DateTimeField(auto_now_add) | timestamptz | No | — | Immutable creation timestamp |
| `reference_document` | CharField(100) | varchar(100) | Yes | NULL | External doc ref for non-romaneo movements |
| `notes` | TextField | text | Yes | NULL | Required for ADJUSTMENT; optional otherwise |
| `created_by` | FK(AppUser, PROTECT) | uuid | No | — | Operator identity (ADR-034) |
| `device_id` | CharField(100) | varchar(100) | Yes | NULL | Device provenance (ADR-034) |

**Note**: `updated_at` is intentionally omitted (immutable model, same precedent
as `MermaCalculation`). `quantity_kg` can be negative — WITHDRAWAL and TRANSFER_OUT
are stored as negative values.

### Movement Types

| Constant | Value | Sign | Triggered By |
|----------|-------|------|-------------|
| `DEPOSIT` | `"DEPOSIT"` | Positive (+) | Romaneo reaches CONFORME; `romaneo` FK required |
| `WITHDRAWAL` | `"WITHDRAWAL"` | Negative (−) | Dispatch (egreso) operation |
| `TRANSFER_IN` | `"TRANSFER_IN"` | Positive (+) | Destination side of inter-silo transfer |
| `TRANSFER_OUT` | `"TRANSFER_OUT"` | Negative (−) | Source side of inter-silo transfer |
| `ADJUSTMENT` | `"ADJUSTMENT"` | +/− | Physical reconciliation; `notes` required |

### Constraints

```python
indexes = [
    Index(fields=["tenant_id", "grain_lot_id", "movement_at"],
          name="idx_grainmovement_tenant_lot_ts"),
    Index(fields=["tenant_id", "movement_type", "movement_at"],
          name="idx_grainmovement_tenant_type_ts"),
]
```

### Immutability Enforcement

- **Model layer**: `save()` raises `ValueError` if `self.pk` already exists in DB.
  `delete()` raises `ValueError` unconditionally.
- **API layer**: ViewSet uses `http_method_names = ["get", "post", "head", "options"]`;
  PATCH/PUT/DELETE return HTTP 405 Method Not Allowed.
- **DB layer**: RLS grants only `SELECT, INSERT` to `gravitea_app`; no `UPDATE` or `DELETE`.
- **Admin layer**: `GrainMovementAdmin.has_change_permission()` and
  `has_delete_permission()` return `False`.

---

## Modified Entity: Romaneo (Spec-11, Extended by Spec-12)

**Table**: `acopio_romaneo` (pre-existing)
**Migration**: 0003_storage_position adds two nullable columns.

### New Fields (added by spec-12)

| Field | Django Type | DB Type | Null | on_delete | Notes |
|-------|-------------|---------|------|-----------|-------|
| `storage_unit` | FK(StorageUnit, SET_NULL) | uuid | Yes | SET_NULL | Set when operator assigns silo at discharge |
| `grain_lot` | FK(GrainLot, SET_NULL) | uuid | Yes | SET_NULL | Set at CONFORME when lot is resolved |

**Immutability gate update**: Romaneo's `save()` override must allow `storage_unit`
and `grain_lot` to be updated when romaneo is in CONFORME status (these are set
by spec-12 services). Add both to the CONFORME mutable fields allowlist.

---

## Relationships Summary

| From | To | Type | FK Name | on_delete |
|------|----|------|---------|-----------|
| StorageUnit | Tenant | M:1 | `tenant` | PROTECT |
| StorageUnit | Branch | M:1 | `branch` | PROTECT |
| StorageUnit | GrainType | M:1 | `current_grain_type` | SET_NULL |
| StorageUnit | AppUser | M:1 | `created_by` | PROTECT |
| GrainLot | Tenant | M:1 | `tenant` | PROTECT |
| GrainLot | Branch | M:1 | `branch` | PROTECT |
| GrainLot | GrainType | M:1 | `grain_type` | PROTECT |
| GrainLot | CampanaConfig | M:1 | `campaign` | PROTECT |
| GrainLot | StorageUnit | M:1 | `storage_unit` | PROTECT |
| GrainLot | AppUser | M:1 | `created_by` | PROTECT |
| GrainMovement | Tenant | M:1 | `tenant` | PROTECT |
| GrainMovement | GrainLot | M:1 | `grain_lot` | PROTECT |
| GrainMovement | Romaneo | M:1 | `romaneo` | SET_NULL |
| GrainMovement | AppUser | M:1 | `created_by` | PROTECT |
| Romaneo ← | StorageUnit | M:1 | `storage_unit` | SET_NULL |
| Romaneo ← | GrainLot | M:1 | `grain_lot` | SET_NULL |

---

## Service Layer Design

### `services/storage.py` — Public Interface

```python
# Core deposit flow (FR-005)
def create_deposit_from_romaneo(
    romaneo: Romaneo,
    storage_unit: StorageUnit,
    is_own_grain: bool,
) -> tuple[GrainMovement, GrainLot]: ...

# Dispatch (FR-006)
def create_withdrawal(
    grain_lot: GrainLot,
    quantity_kg: Decimal,
    operator,
    reference_document: str | None = None,
    notes: str | None = None,
) -> GrainMovement: ...

# Inter-silo transfer (FR-010)
def transfer_grain(
    source_lot: GrainLot,
    destination_lot: GrainLot,
    quantity_kg: Decimal,
    operator,
    notes: str | None = None,
) -> tuple[GrainMovement, GrainLot]: ...

# Cell suggestion (FR-004) — CellSuggestionService
def suggest_cell(
    tenant_id: uuid.UUID,
    branch_id: uuid.UUID,
    grain_type_id: uuid.UUID,
    campaign_id: uuid.UUID,
    grado: int,
    incoming_kg: Decimal,
) -> list[CellSuggestion]: ...

# Stock report (FR-007) — StockReportService
def generate_stock_report(
    tenant_id: uuid.UUID,
    branch_id: uuid.UUID | None = None,
    grain_type_id: uuid.UUID | None = None,
    campaign_id: uuid.UUID | None = None,
) -> dict: ...

# Reconciliation (FR-008) — ReconciliationService
def reconcile(
    tenant_id: uuid.UUID,
    measurements: list[dict],  # [{storage_unit_id, measured_kg}]
    operator_id: uuid.UUID,
    notes: str,
) -> dict: ...

# Campaign close (FR-009) — CampaignCloseService
def close_campaign(
    tenant_id: uuid.UUID,
    campaign_id: uuid.UUID,
    target_campaign_id: uuid.UUID,
    supervisor_id: uuid.UUID,
) -> dict: ...
```

---

## Migration Sequence

```
0001_initial.py          (spec-10: GrainType, ToleranceTable, MermaTable, CampanaConfig)
0002_romaneo_core.py     (spec-11: Romaneo, QualityAnalysis, MermaCalculation)
0003_storage_position.py (spec-12: StorageUnit, GrainLot, GrainMovement + Romaneo FKs)
```

**Migration 0003 operations** (in dependency order):
1. `CreateModel StorageUnit`
2. `CreateModel GrainLot` (FK → StorageUnit)
3. `CreateModel GrainMovement` (FK → GrainLot)
4. `AddField Romaneo.storage_unit` (FK → StorageUnit, null=True)
5. `AddField Romaneo.grain_lot` (FK → GrainLot, null=True)
6. `AddIndex`, `AddConstraint` operations for all new models
