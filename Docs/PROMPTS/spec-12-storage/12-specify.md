---
spec: "012"
name: "Storage & Position"
type: Implementation
branch: 012-storage-position
created: 2026-03-19
depends_on: [spec-10, spec-11]
blocks: [spec-13]
deliverable: "backend/apps/acopio/ storage models, grain lot ledger, storage API endpoints"
qdrant_collections: [acopio_research]
agents: [A1, A2, A3]
---

# Spec-12: Storage & Position -- Specification Context

## Feature Description

Implement the physical storage infrastructure and grain position ledger for the
acopio operation. This spec creates the following deliverables within the existing
`backend/apps/acopio/` application (established by spec-10, extended by spec-11):

1. **StorageUnit model** -- physical silo/celda/bin representing each storage
   location at a plant (branch). Fields: name, unit_type
   (SILO_VERTICAL | CELDA_HORIZONTAL | SECADERO_BIN), capacity in tonnes,
   current grain type, active status, IoT sensor anchor.
2. **GrainLot model** -- grain position record tracking kg balance per
   (branch x grain_type x campaign x grado x storage_unit). Composite identity
   enforced by RG 3593. Carries `is_own_grain` for accounting segregation
   (ADR-020).
3. **GrainMovement model** -- immutable append-only ledger recording every grain
   inflow/outflow per lot. Movement types: DEPOSIT, WITHDRAWAL, TRANSFER_IN,
   TRANSFER_OUT. Same immutability pattern as `StockMovement` in inventario and
   `MermaCalculation` in acopio.
4. **Storage services** -- cell suggestion algorithm (SRS-AL03), stock report
   computation, physical inventory reconciliation, campaign-year close workflow.
5. **DRF serializers and viewsets** implementing REST API Design v1.0 Section 7
   -- StorageUnit CRUD, GrainLot listing, GrainMovement append-only ledger.
6. **Test suite** covering models, immutability enforcement, running balance
   updates, derived field computation, cell suggestion, tenant isolation, and
   API endpoints.

This builds directly on:
- **Spec-10** reference data: GrainType, CampanaConfig, ToleranceTable, MermaTable
- **Spec-11** romaneo lifecycle: Romaneo (with `storage_unit_id` and `grain_lot_id`
  FK slots defined in the Data Model but not yet populated), QualityAnalysis,
  MermaCalculation

---

## Current State

### What Exists (from spec-10 + spec-11)

- `backend/apps/acopio/` -- Django app registered in `INSTALLED_APPS` with URL
  routing at `/api/v1/acopio/`.
- `backend/apps/acopio/models/grain_type.py` -- `GrainType` (GLOBAL). Provides
  `grading_system` field consumed by GrainLot for grade validation.
- `backend/apps/acopio/models/campana_config.py` -- `CampanaConfig`
  (TenantBound). Per-tenant campaign year config.
- `backend/apps/acopio/models/romaneo.py` -- `Romaneo` (TenantBound). 6-state
  state machine. **NOTE**: The Data Model v1.0 (Group 6 -- Storage Assignment)
  defines `storage_unit` (FK StorageUnit, SET_NULL, nullable) and `grain_lot`
  (FK GrainLot, SET_NULL, nullable) on Romaneo. The REST API Design §5 lists
  `storage_unit` as a PATCHABLE field. The FK cross-reference table lists both.
  **These fields do NOT exist in the current spec-11 implementation.**
  Spec-12 MUST add these two nullable FKs to Romaneo via migration to align
  with the authoritative blueprint. `storage_unit` is set at discharge (silo
  assignment); `grain_lot` is set at CONFORME (when the deposit movement is
  created). These FKs provide direct navigability from Romaneo -> StorageUnit
  and Romaneo -> GrainLot without requiring a join through GrainMovement.
- `backend/apps/acopio/models/quality_analysis.py` -- `QualityAnalysis`.
  One-to-one satellite of Romaneo.
- `backend/apps/acopio/models/merma_calculation.py` -- `MermaCalculation`.
  Immutable one-to-one satellite with final peso_neto_conforme_kg.
- `backend/apps/acopio/serializers/` -- reference_data.py (4 serializers),
  romaneo.py (Romaneo + nested serializers).
- `backend/apps/acopio/views/` -- reference_data.py (4 viewsets),
  romaneo.py (RomaneoViewSet with state transition actions).
- `backend/apps/acopio/urls.py` -- DRF router with registered viewsets.
- `backend/apps/core/models/mixins.py` -- `TenantBoundModel` (abstract base).
- `backend/apps/core/managers/tenant_bound.py` -- `TenantBoundManager` with
  fail-closed tenant filtering; `AllObjectsManager`.
- `backend/apps/inventario/models.py` -- `StockMovement` (lines 470-675)
  demonstrates the immutable ledger pattern. `StockSnapshot` (lines 678-750)
  demonstrates the running balance snapshot pattern. **IMPORTANT**: Grain does
  NOT use StockMovement. ADR-009 mandates separate ledgers: StockMovement for
  discrete (agronomia) inventory; GrainMovement for continuous (grain) inventory.
- `backend/apps/core/models/branch.py` -- `Branch` model. StorageUnit has a FK
  to Branch (a storage unit belongs to a plant).

### What Needs Creating

- `backend/apps/acopio/models/storage_unit.py` -- StorageUnit model.
- `backend/apps/acopio/models/grain_lot.py` -- GrainLot model.
- `backend/apps/acopio/models/grain_movement.py` -- GrainMovement model.
- `backend/apps/acopio/services/storage.py` -- Cell suggestion, stock report,
  reconciliation, campaign close services.
- `backend/apps/acopio/serializers/storage.py` -- StorageUnit, GrainLot,
  GrainMovement serializers.
- `backend/apps/acopio/views/storage.py` -- StorageUnitViewSet,
  GrainLotViewSet, GrainMovementViewSet.
- Updated `backend/apps/acopio/urls.py` -- register storage routes.
- Updated `backend/apps/acopio/models/__init__.py` -- re-export new models.
- Updated `backend/apps/acopio/models/romaneo.py` -- add `storage_unit` and
  `grain_lot` nullable FKs (Data Model v1.0 Group 6).
- Updated `backend/apps/acopio/serializers/romaneo.py` -- add `storage_unit`
  to patchable fields (REST API Design §5).
- Database migration `0003_storage_position.py` (next after 0002_romaneo_core).
- Test files for all new code.

---

## Research Inputs

### RAG Queries (run these FIRST -- do NOT read full research files)

```bash
.venv/bin/python scripts/qdrant/qdrant_batch_search.py \
    -q "grain storage silo position stock movement tracking" \
    -q "storage operations acopio planta silo celda position" \
    -q "romaneo descarga storage destination silo assignment" \
    -q "grain stock balance position inventory by silo" \
    -q "storage legal framework warrants deposito certificado" \
    -q "AI ML grain storage temperature monitoring prediction" \
    -q "quality degradation storage spoilage grain monitoring" \
    -q "campaign year segregation grain storage by type grade" \
    -o Docs/RAG_results/spec-12 -l 5
```

### Source Documents (for reference only -- prefer RAG)

| Doc | Path | Relevant Sections |
|-----|------|-------------------|
| Research 2.1 | `Docs/Researches/Markdown/2.1 Day-to-Day Operations of an Acopiador.md` | ESCENARIO 2 (Almacenamiento y Monitoreo), Paso 1 (Inventario por silo), Paso 8 (Asignación de silo) |
| Research 2.6 | `Docs/Researches/Markdown/2.6 Campaign Year Management.md` | Campaign overlap handling, logical segregation composite key, carry stock |
| Research 1.6 | `Docs/Researches/Markdown/1.6 Ley de Granos, Warrants, and Storage Legal Framework.md` | Legal custody obligations, warrant system |
| Research 9.1 | `Docs/Researches/Markdown/9.1 AI-ML Applications for Grain Storage Operations.md` | Silo assignment optimisation, quality degradation prediction, temperature monitoring |
| Research 2.3 | `Docs/Researches/Markdown/2.3 Producer Current Accounts (Cuentas Corrientes de Productores).md` | Transaction type effects on grain balance (reception +kg, retiro -kg, almacenaje) |

### Blueprint References

| Doc | Path | Relevant Sections |
|-----|------|-------------------|
| Data Model v1.0 | `Docs/Project Blueprint/Data Model & Domain Model.md` | Section 5.6 (Storage & Grain Inventory -- StorageUnit, GrainLot, GrainMovement field definitions), ER diagram, FK cross-reference table |
| REST API Design v1.0 | `Docs/Project Blueprint/REST API Design.md` | Section 7 (Storage API -- 7.1-7.5: storage-units, grain-lots, grain-lots/{id}/movements), Endpoint summary table |
| HLD v1.0 | `Docs/Project Blueprint/High-Level Design (HLD).md` | Section 5.3 (apps/acopio owned entities), Section 9.1 (Romaneo Reception Flow step 10: silo credit), Section 12 (AI-Ready Data Architecture layers 3-4) |
| ADR v1.0 | `Docs/Project Blueprint/Architecture Decision Records (ADR).md` | ADR-006 (Ironclad Lineage -- append-only), ADR-009 (Dual Inventory -- grain vs discrete), ADR-010 (Global vs Tenant), ADR-011 (Campaign Segregation), ADR-020 (Own vs Third-Party Grain Accounting), ADR-033 (AI-Ready 4-Layer), ADR-034 (Provenance Fields) |
| SRS v1.0 | `Docs/Project Blueprint/Software Requirements Specification (SRS).md` | SRS-AL01 (Cell Master Data), SRS-AL02 (Stock Movement Ledger), SRS-AL03 (Automatic Cell Assignment), SRS-AL04 (Dispatch Processing), SRS-AL05 (Stock Report), SRS-AL06 (Reconciliation), SRS-AL07 (Campaign Close), SRS-CA06 (Quality History per Cell) |

### Critical Domain Facts

#### Grain Inventory Is NOT Discrete Inventory (ADR-009)

Grain inventory is measured in **kilograms** (continuous), derived from romaneo
reception events. It is segregated by grain_type / quality grade / campaign /
storage_unit. It does **NOT** use `StockMovement` or `StockSnapshot` from
`apps/inventario`. The grain position system uses its own ledger:
`GrainLot` + `GrainMovement`.

- `StockMovement` (inventario) = discrete (units) -- seeds, fertilisers, repuestos
- `GrainMovement` (acopio) = continuous (kg) -- grain position tracking

#### Silo / Celda Entity (Research 2.1)

Per RAG Result Q02-R3 (Source 2.1, ESCENARIO 2):
- El stock fisico en planta se gestiona por **silo/celda**, con informacion de:
  grano, calidad promedio, campana, capacidad utilizada, fecha de ultima
  carga/descarga.
- **Silo / Celda** entity: Identificacion, grano actual, capacidad, stock,
  temperatura, estado.

Three storage unit types per Data Model v1.0:
1. `SILO_VERTICAL` -- vertical concrete silo
2. `CELDA_HORIZONTAL` -- horizontal storage cell
3. `SECADERO_BIN` -- wet holding bin (routing before dryer)

#### Silo Assignment Criteria (Research 2.1, Paso 8)

The jefe de planta decides target silo based on:
1. Grain type compatibility (same type or empty)
2. Quality/grade of the lot (avoid mixing grades that degrade the average)
3. Humidity (if needs drying, route to silo pulmon or directly to secadora)
4. Campaign (old harvest vs new harvest)
5. Owner segregation (some cases -- by producer or destination)
6. Available capacity (remaining >= incoming adjusted net weight)

If grain requires conditioning (secado/limpieza), it passes through the secadora
and/or zaranda first, then to the definitive storage silo.

#### Grain Loses Physical Identity in Silo (Research 2.1, ESCENARIO 2)

Once grain enters the silo, it physically mixes. The producer is no longer
owner of the specific physical grain -- they become owner of an **equivalent
in quality and quantity**. This is why grain tracking is per-lot (composite
identity), not per-producer per-silo.

#### Campaign Year Segregation (Research 2.6)

Per ARCA RG 3593, the ERP must track stock along three mandatory axes:
**plant -> grain -> campaign**. Even when physical co-mingling occurs in the
same cell, logical segregation by campaign is required.

- The same silo may contain wheat from campaign 2024/25 AND 2025/26 after
  the new harvest begins in December.
- The ERP tracks these as **separate logical lots** linked to different campaigns.
- ARCA displays the last 3 campaigns for stock declaration.
- **Carry stock** (stock de enlace): grain carried over from previous campaign.

ARCA RG 3593 minimum composite key: `(plant_id, grain_code, campaign_id)`.
Data Model v1.0 composite identity: `(branch, grain_type, campaign, grado)`.
Extended for physical storage location: `(branch, grain_type, campaign, grado,
storage_unit)` -- because the same grain/campaign/grade CAN exist in multiple
silos simultaneously. The storage_unit dimension is added to the Data Model's
stated composite identity to enable per-silo position tracking.

#### Own-Grain vs Third-Party Accounting (ADR-020)

`GrainLot.is_own_grain`:
- `True` -> balance-sheet asset (accounting code 1.3.XX -- Bienes de cambio)
- `False` -> off-balance-sheet custody (accounting code 8.1.XX per RG 3593)

Every grain movement must correctly classify the grain. Misclassification at
lot creation propagates through all downstream accounting entries.

#### Conciliation: Contable vs Fisico

Per Research 2.1, the acopiador must reconcile:
- **Stock contable** = sum of producer current accounts + own grain
- **Stock fisico** = cubicaje/aforo (physical measurement per silo)

Variances require adjustment ledger entries (SRS-AL06).

#### AI-Ready Data Architecture (ADR-033, Layers 3-4)

StorageUnit carries `environment_sensor_id` (nullable) -- IoT sensor anchor
for future Phase 4 temperature/humidity monitoring. This FK is present in the
schema with NULL values today. Populating it in a future phase requires **no
schema change**.

QualityAnalysis records per `(grain_type, campaign, storage_unit)` enable:
- Grain quality degradation prediction per silo (Phase 4: 3D-CNN + LSTM)
- Campaign-over-campaign quality trend analysis per storage unit
- Blending optimisation -- complementary quality profiles

---

## Functional Requirements

### FR-001: StorageUnit CRUD

The system shall allow tenant administrators to manage physical storage units
(silos, celdas, bins) per branch. Each storage unit has: name (unique per
tenant+branch), unit_type (SILO_VERTICAL | CELDA_HORIZONTAL | SECADERO_BIN),
capacity_tonnes, current_grain_type (nullable FK to GrainType), is_active,
environment_sensor_id (nullable IoT anchor).

Derived field `current_occupancy_kg` is computed on-demand from GrainMovement
aggregation -- NOT stored on the model (REST API Design v1.0 Section 7.1).

**Maps to**: SRS-AL01, REST API Design §7.1-§7.2

### FR-002: GrainLot Position Tracking

The system shall maintain grain lot position records per
(branch x grain_type x campaign x grado x storage_unit). Each lot tracks a
running `total_kg` balance updated on every GrainMovement. Lots carry
`is_own_grain` (ADR-020) for accounting classification. Lot codes are
auto-generated: `BRANCH-GRAIN-CAMPAIGN-GRADE`.

A lot is identified by the composite natural key. A new DEPOSIT into the same
(branch, grain_type, campaign, grado, storage_unit) reuses the existing lot
and increments its `total_kg`.

**Maps to**: Data Model v1.0 Section 5.6 GrainLot, REST API Design §7.3-§7.4

### FR-003: GrainMovement Immutable Ledger

The system shall record all grain movements as immutable append-only ledger
entries. Each entry contains: grain_lot FK, movement_type (DEPOSIT | WITHDRAWAL
| TRANSFER_IN | TRANSFER_OUT | ADJUSTMENT), romaneo FK (for DEPOSIT type; null otherwise),
quantity_kg (positive = inflow; negative = outflow), movement_at (auto_now_add),
reference_document (string for non-romaneo movements), and operator provenance
fields (created_by, device_id per ADR-034).

**Immutability rules** (same pattern as StockMovement):
- No UPDATE operations -- save() raises ValueError on existing records.
- No DELETE operations -- delete() raises ValueError.
- Running stock balance per lot is recomputed from the ledger.
- A negative resulting balance triggers a blocking error before commit.

**Maps to**: SRS-AL02, ADR-006, REST API Design §7.5

### FR-004: Automatic Cell Suggestion

The system shall suggest a target storage unit for incoming grain from a
CONFORME romaneo based on:
1. Grain type compatibility (current_grain_type matches or is NULL/empty)
2. Available capacity (capacity_tonnes * 1000 - current_occupancy_kg >= incoming_kg)
3. Quality/grade segregation (prefer lots with matching grado)
4. Campaign match (prefer lots in the same campaign)

The suggestion is displayed before the operator confirms; the operator may
override. Override reason is captured.

**Maps to**: SRS-AL03

### FR-005: Deposit from Romaneo (Reception Inflow)

When a romaneo reaches CONFORME status, the system shall create:
1. A `GrainLot` record (or find existing matching lot) for
   (branch, grain_type, campaign, grado, storage_unit).
2. A `GrainMovement` of type DEPOSIT with `quantity_kg = romaneo.peso_neto_conforme_kg`
   and `romaneo` FK pointing to the source romaneo.
3. Update `GrainLot.total_kg += quantity_kg`.
4. Update `StorageUnit.current_grain_type` if previously NULL.
5. Set `Romaneo.grain_lot = grain_lot` (Data Model Group 6).

The `Romaneo.storage_unit` FK is set earlier -- when the operator assigns the
silo (before or at discharge). The `Romaneo.grain_lot` FK is set at CONFORME
when the GrainLot is resolved.

**Maps to**: HLD v1.0 Section 9.1 step 10 ("silo credit"), SRS-AL02

### FR-006: Dispatch (Egreso) Processing

The system shall allow recording grain dispatches from a storage unit, capturing:
dispatch reference, destination, truck plate, weights, departure timestamp, CPE/CTG
reference. A dispatch creates a GrainMovement of type WITHDRAWAL with negative
quantity_kg. Dispatch reduces lot balance immediately upon confirmation.

**Maps to**: SRS-AL04

### FR-007: Stock Report

The system shall produce a stock report (API endpoint returning JSON; PDF/XLSX
export deferred to future) showing: current stock per storage unit, per grain type,
per campaign, and total warehouse capacity utilisation percentage. Report reflects
real-time stock (all confirmed movements). Filterable by grain type, campaign, and
storage unit group.

**Maps to**: SRS-AL05

### FR-008: Physical Inventory Reconciliation

The system shall support periodic physical inventory counts. Operator enters
measured weights per storage unit; system computes variance against ledger balance.
Applying reconciliation creates ADJUSTMENT movements with mandatory operator
CUIT and notes field. **NOTE**: The Data Model v1.0 defines 4 movement types
(DEPOSIT | WITHDRAWAL | TRANSFER_IN | TRANSFER_OUT) but SRS-AL06 requires
"adjustment ledger entries (movement type: ajuste)". Spec-12 adds a 5th type
`ADJUSTMENT` to GrainMovement choices to match SRS-AL06. ADJUSTMENT movements
carry positive quantity_kg for surplus and negative for deficit. This is a
justified extension of the Data Model to satisfy SRS-AL06.

**Maps to**: SRS-AL06

### FR-009: Campaign Year Close

The system shall provide a campaign close workflow that:
1. Validates all romaneos in the campaign are in a final state (CONFORME or CERRADO)
2. Carries remaining stock to next campaign as "stock de enlace" (carry lots)
3. Generates a carry-forward GrainMovement for non-zero lots

Campaign close requires supervisor-level user. The close operation is atomic.

**Maps to**: SRS-AL07

### FR-010: Transfer Between Storage Units

The system shall support internal grain transfer between storage units of the same
branch. A transfer creates two GrainMovement entries: TRANSFER_OUT (negative) on
the source lot and TRANSFER_IN (positive) on the destination lot. These must be
created atomically in a single database transaction.

**Maps to**: Data Model v1.0 GrainMovement movement_types

---

## Non-Functional Requirements

### NF-001: Stock Balance Consistency

`GrainLot.total_kg` must equal the sum of all `GrainMovement.quantity_kg` for
that lot at all times. A background consistency check (management command) must
be provided to detect and report drift.

### NF-002: Query Performance

StorageUnit list with current_occupancy_kg must respond within 200ms for a
tenant with up to 200 storage units. The derived occupancy field is computed
via a single annotated queryset, not N+1 queries.

### NF-003: Immutability Enforcement

GrainMovement must reject UPDATE and DELETE at both the Django model level
(save/delete overrides) and the database level (PostgreSQL RLS policy or
trigger -- deferred to DB migration). API must return HTTP 405 for PATCH/DELETE
on GrainMovement endpoints.

### NF-004: Tenant Isolation

All three new models (StorageUnit, GrainLot, GrainMovement) inherit
TenantBoundModel and use TenantBoundManager with fail-closed filtering.
Cross-tenant data leakage is a critical security defect.

### NF-005: Provenance Fields (ADR-034)

All grain domain models carry: `created_at` (auto_now_add), `updated_at`
(auto_now on mutable models; omit on immutable GrainMovement), `created_by`
(FK to AppUser), `device_id` (CharField nullable).

---

## Key Technical Details

### Entity Definitions (from Data Model v1.0 Section 5.6)

#### StorageUnit -- Inherits TenantBoundModel

| Field | Django Type | Precision | Null | Default | Description |
|-------|-------------|-----------|------|---------|-------------|
| `id` | UUIDField PK | -- | No | uuid4 | -- |
| `tenant` | ForeignKey(Tenant) PROTECT | -- | No | -- | Owning tenant |
| `name` | CharField | max_length=100 | No | -- | Silo or bin name |
| `unit_type` | CharField choices | -- | No | -- | SILO_VERTICAL \| CELDA_HORIZONTAL \| SECADERO_BIN |
| `branch` | ForeignKey(Branch) PROTECT | -- | No | -- | Plant this unit belongs to |
| `capacity_tonnes` | DecimalField | (12,3) | No | -- | Nominal capacity in tonnes |
| `is_active` | BooleanField | -- | No | True | -- |
| `current_grain_type` | ForeignKey(GrainType) SET_NULL | -- | Yes | -- | Current grain in storage (NULL if empty) |
| `environment_sensor_id` | CharField | max_length=100 | Yes | -- | IoT sensor ID anchor (Phase 4) |
| `created_at` | DateTimeField | -- | No | auto_now_add | ADR-034 provenance |
| `updated_at` | DateTimeField | -- | No | auto_now | ADR-034 provenance |
| `created_by` | ForeignKey(AppUser) PROTECT | -- | No | -- | ADR-034 provenance |

**Derived field** (not stored): `current_occupancy_kg` -- sum of all
GrainMovement.quantity_kg for GrainLots in this storage unit.

**Constraints**:
- UniqueConstraint: `(tenant, branch, name)` -- silo names unique per plant
- Index: `(tenant_id, branch_id, is_active)` -- filtered list queries

#### GrainLot -- Inherits TenantBoundModel

| Field | Django Type | Precision | Null | Default | Description |
|-------|-------------|-----------|------|---------|-------------|
| `id` | UUIDField PK | -- | No | uuid4 | -- |
| `tenant` | ForeignKey(Tenant) PROTECT | -- | No | -- | -- |
| `lot_code` | CharField | max_length=100 | No | -- | Auto-generated: BRANCH-GRAIN-CAMPAIGN-GRADE |
| `branch` | ForeignKey(Branch) PROTECT | -- | No | -- | -- |
| `grain_type` | ForeignKey(GrainType) PROTECT | -- | No | -- | -- |
| `campaign` | ForeignKey(CampanaConfig) PROTECT | -- | No | -- | -- |
| `grado` | IntegerField | -- | No | -- | 1/2/3 for cereals; 0 for oleaginosas |
| `storage_unit` | ForeignKey(StorageUnit) PROTECT | -- | No | -- | Physical storage location |
| `total_kg` | DecimalField | (17,3) | No | 0.000 | Running grain balance |
| `is_own_grain` | BooleanField | -- | No | False | True=1.3.XX; False=8.1.XX per ADR-020 |
| `created_at` | DateTimeField | -- | No | auto_now_add | ADR-034 provenance |
| `updated_at` | DateTimeField | -- | No | auto_now | ADR-034 provenance (total_kg updates) |
| `created_by` | ForeignKey(AppUser) PROTECT | -- | No | -- | ADR-034 provenance |

**Constraints**:
- UniqueConstraint: `(tenant, branch, grain_type, campaign, grado, storage_unit)` -- RG 3593 composite identity (extended from Data Model's `(branch, grain_type, campaign, grado)` to include storage_unit for per-silo tracking)
- CheckConstraint: `total_kg >= 0` -- no negative balances
- Index: `(tenant_id, storage_unit_id)` -- lookup by silo
- Index: `(tenant_id, campaign_id, grain_type_id)` -- campaign stock queries

#### GrainMovement -- Inherits TenantBoundModel (IMMUTABLE)

| Field | Django Type | Precision | Null | Default | Description |
|-------|-------------|-----------|------|---------|-------------|
| `id` | UUIDField PK | -- | No | uuid4 | -- |
| `tenant` | ForeignKey(Tenant) PROTECT | -- | No | -- | -- |
| `grain_lot` | ForeignKey(GrainLot) PROTECT | -- | No | -- | Target lot |
| `movement_type` | CharField choices | -- | No | -- | DEPOSIT \| WITHDRAWAL \| TRANSFER_IN \| TRANSFER_OUT \| ADJUSTMENT |
| `romaneo` | ForeignKey(Romaneo) SET_NULL | -- | Yes | -- | Source romaneo (DEPOSIT only) |
| `quantity_kg` | DecimalField | (17,3) | No | -- | Positive=inflow; negative=outflow |
| `movement_at` | DateTimeField | -- | No | auto_now_add | Immutable timestamp |
| `reference_document` | CharField | max_length=100 | Yes | -- | External doc ref for non-romaneo |
| `created_by` | ForeignKey(AppUser) PROTECT | -- | No | -- | Operator (ADR-034) |
| `device_id` | CharField | max_length=100 | Yes | -- | Device provenance (ADR-034) |
| `notes` | TextField | -- | Yes | -- | Operator notes (required for ADJUSTMENT; extension beyond Data Model, justified by SRS-AL06) |

**Provenance note**: `created_by` and `device_id` are mandated by ADR-034.
`notes` is not in the Data Model GrainMovement definition but is required by
SRS-AL06 (reconciliation adjustment movements need mandatory notes). GrainMovement
omits `updated_at` because the model is immutable (no updates possible).

**Immutability enforcement**:
- `save()`: raise ValueError if `self.pk` exists in DB
- `delete()`: raise ValueError always
- API: return HTTP 405 for PATCH/DELETE/PUT

**Constraints**:
- Index: `(tenant_id, grain_lot_id, movement_at)` -- ledger queries
- Index: `(tenant_id, movement_type, movement_at)` -- filtered movement queries

### Service Layer

#### CellSuggestionService

```python
def suggest_cell(
    tenant_id: uuid.UUID,
    branch_id: uuid.UUID,
    grain_type_id: uuid.UUID,
    campaign_id: uuid.UUID,
    grado: int,
    incoming_kg: Decimal,
) -> list[dict]:
    """
    Return ranked list of suggested storage units.

    Ranking criteria (descending priority):
    1. Grain type match (current_grain_type == grain_type or NULL)
    2. Grade match (existing lot with same grado)
    3. Campaign match (existing lot in same campaign)
    4. Available capacity >= incoming_kg
    5. Lowest current_occupancy_kg (prefer emptier silos)

    Returns list of {storage_unit_id, name, score, reason} dicts.
    """
```

#### StockReportService

```python
def generate_stock_report(
    tenant_id: uuid.UUID,
    branch_id: uuid.UUID | None = None,
    grain_type_id: uuid.UUID | None = None,
    campaign_id: uuid.UUID | None = None,
) -> dict:
    """
    Compute real-time stock report from GrainMovement ledger.

    Returns:
    - stock_by_storage_unit: [{unit_id, name, grain_type, total_kg, capacity_pct}]
    - stock_by_grain_type: [{grain_type, total_kg}]
    - stock_by_campaign: [{campaign, total_kg}]
    - total_capacity_tonnes, total_occupied_kg, utilisation_pct
    """
```

#### ReconciliationService

```python
def reconcile(
    tenant_id: uuid.UUID,
    measurements: list[dict],  # [{storage_unit_id, measured_kg}]
    operator_id: uuid.UUID,
    notes: str,
) -> dict:
    """
    Compare measured weights against ledger balances.

    For each storage unit:
    1. Compute ledger balance from GrainMovement sum
    2. Compare against measured_kg
    3. If variance exists, create adjustment GrainMovement
    4. Return reconciliation report with variances

    Adjustment movements use movement_type appropriate for the direction.
    """
```

### Integration Points

#### Romaneo -> Storage (FR-005)

When romaneo transitions to CONFORME, the storage system creates a DEPOSIT
movement. This can be triggered by:
- A signal/hook on Romaneo.save() when status becomes CONFORME
- An explicit service call from the romaneo viewset after successful state transition

The spec-11 RomaneoViewSet `@action confirm` endpoint is the natural integration
point. Spec-12 adds the storage deposit logic after confirmation succeeds.

#### Producer Accounts -> Storage (spec-13 dependency)

Spec-13 (Producer Accounts) will read GrainLot and GrainMovement data to credit
producer accounts. The DEPOSIT movement triggers an AccountMovement of type
CEG_DEPOSIT. This is NOT implemented in spec-12 -- spec-13 handles it.

---

## Acceptance Criteria

### AC-01: StorageUnit CRUD

- [ ] Tenant admin can create, list, update, and soft-deactivate storage units
- [ ] `current_occupancy_kg` is returned in API responses as a computed field
- [ ] Storage unit names are unique within tenant+branch
- [ ] A storage unit with non-zero stock in any active campaign cannot be deleted

### AC-02: GrainLot Creation and Reuse

- [ ] A DEPOSIT into an existing (branch, grain_type, campaign, grado, storage_unit)
      reuses the existing lot and increments total_kg
- [ ] A DEPOSIT into a new combination creates a new GrainLot automatically
- [ ] `lot_code` is auto-generated on first save
- [ ] `is_own_grain` is correctly set based on the romaneo context

### AC-03: GrainMovement Immutability

- [ ] GrainMovement.save() raises ValueError for existing records
- [ ] GrainMovement.delete() raises ValueError always
- [ ] API returns HTTP 405 for PATCH/DELETE/PUT on movements endpoint
- [ ] Running balance per lot equals sum of all movements for that lot

### AC-04: Negative Balance Prevention

- [ ] A WITHDRAWAL that would make total_kg < 0 is rejected with a clear error
- [ ] The check is performed before the movement is committed (within transaction)

### AC-05: Cell Suggestion

- [ ] Suggestion API returns ranked list of compatible storage units
- [ ] Operator can override suggestion; override reason is logged

### AC-06: Stock Report

- [ ] Report shows stock per storage unit, per grain type, per campaign
- [ ] Report shows total capacity utilisation percentage
- [ ] Report can be filtered by grain type, campaign, and branch

### AC-07: Reconciliation

- [ ] Operator enters measured weights; system computes variance
- [ ] Applying reconciliation creates adjustment movements
- [ ] Adjustment movements carry mandatory operator_id and notes

### AC-08: Campaign Close

- [ ] Close validates all romaneos are in final state
- [ ] Remaining stock is carried forward as stock de enlace
- [ ] Close operation is atomic (all-or-nothing)
- [ ] Requires supervisor-level permission

### AC-09: Tenant Isolation

- [ ] All models use TenantBoundManager
- [ ] Cross-tenant queries return empty results (fail-closed)
- [ ] Tests verify isolation for StorageUnit, GrainLot, GrainMovement

### AC-10: Transfer Between Units

- [ ] Internal transfer creates paired TRANSFER_OUT + TRANSFER_IN movements
- [ ] Transfer is atomic (single transaction)
- [ ] Source lot balance decreases; destination lot balance increases

---

## Coherence Notes

### Blueprint Deviations (Justified)

1. **GrainMovement ADJUSTMENT type**: Data Model v1.0 defines 4 movement types.
   Spec-12 adds a 5th (`ADJUSTMENT`) to satisfy SRS-AL06 reconciliation
   requirement. SRS says "movement type: ajuste".
2. **GrainLot composite identity includes storage_unit**: Data Model states
   `(branch, grain_type, campaign, grado)`. Spec-12 extends to include
   `storage_unit` because the same grain/campaign/grade can physically exist in
   multiple silos. The Data Model lists storage_unit as a separate FK on GrainLot
   but omits it from the composite identity text.
3. **GrainMovement `notes` field**: Not in Data Model GrainMovement definition.
   Added to satisfy SRS-AL06 mandatory notes on reconciliation adjustments.
4. **GrainMovement omits `updated_at`**: ADR-034 mandates `updated_at` on all
   grain domain models. GrainMovement is immutable, so `updated_at` is
   meaningless and omitted. Same pattern as MermaCalculation.

### SRS Traceability Discrepancy

The SRS v1.0 traceability matrix (Section 8) maps SRS-AL01 through SRS-AL08 to
"spec-011". However, the README spec catalog and dependency graph assign Storage
& Position to **spec-12**. Spec-12 is the authoritative assignment. The SRS
mapping is a labeling artifact from an earlier spec numbering scheme.

### Romaneo FK Addition (Blueprint Alignment)

Spec-12 adds `storage_unit` (FK, SET_NULL) and `grain_lot` (FK, SET_NULL) to the
existing Romaneo model per Data Model v1.0 Group 6 and REST API Design §5
(patchable fields). This is a schema change to an existing model. The migration
must handle existing Romaneo rows with NULL values for both new fields.

---

## Dependencies

### Depends On

| Spec | What It Provides |
|------|------------------|
| spec-10 | GrainType (grain codes), CampanaConfig (campaign years), ToleranceTable, MermaTable -- reference data consumed by storage |
| spec-11 | Romaneo (source of DEPOSIT movements via peso_neto_conforme_kg), QualityAnalysis (grado for lot assignment), MermaCalculation (net weight) |

### Blocks

| Spec | What It Needs |
|------|---------------|
| spec-13 | ProducerAccount reads GrainLot/GrainMovement to credit producer accounts on romaneo reception |

---

## Agent Structure (3 agents)

| Agent | File | Type | Scope |
|-------|------|------|-------|
| A1 | `agents/A1-models.md` | python-expert | StorageUnit, GrainLot, GrainMovement models + storage services |
| A2 | `agents/A2-api.md` | backend-architect | Serializers, ViewSets, URL registration, API integration |
| A3 | `agents/A3-tests.md` | quality-engineer | Model tests, API tests, immutability, tenant isolation, reconciliation |

### Wave Structure

```
Wave 1: A1 (Models + Services)
    |
    v
Wave 2: A2 (API) -- depends on A1 models being in place
    |
    v
Wave 3: A3 (Tests) -- depends on A1 + A2 for full coverage
```

### Gate Checkpoints

| Gate | After | Command | Criterion |
|------|-------|---------|-----------|
| G1 | Wave 1 | `DJANGO_SETTINGS_MODULE=gravitea.settings.test python -c "from apps.acopio.models import StorageUnit, GrainLot, GrainMovement; print('OK')"` | Models importable |
| G2 | Wave 1 | `python manage.py makemigrations --check --dry-run` | No missing migrations |
| G3 | Wave 2 | `DJANGO_SETTINGS_MODULE=gravitea.settings.test python -c "from apps.acopio.urls import urlpatterns; print(len(urlpatterns))"` | URL count increased |
| G4 | Wave 3 | `pytest tests/acopio/test_storage*.py -v --tb=short` | All storage tests pass |
