# Research: Storage & Position (Spec-12)

**Generated**: 2026-03-19
**Source**: 12-specify.md domain facts, RAG results, blueprint cross-reference

---

## Summary

No NEEDS CLARIFICATION markers exist in the spec or plan. All domain decisions
were resolved during the specify + clarify phases using the RAG pipeline and
blueprint documents. This file consolidates those decisions with rationale for
agent consumption.

---

## Decision 1: GrainMovement Separate from StockMovement (ADR-009)

**Decision**: GrainMovement (`apps/acopio`) is a separate, independent immutable
ledger from StockMovement (`apps/inventario`). They share the immutability
pattern but serve different inventory dimensions.

**Rationale**:
- ADR-009 (Dual Inventory) mandates separate ledgers: `StockMovement` for discrete
  units (agronomia inventory: seeds, fertilisers, repuestos) vs `GrainMovement`
  for continuous kg (grain position tracking).
- Grain is measured in kilograms and segregated by type/grade/campaign/silo.
  Discrete inventory uses units and SKUs. The data shapes are fundamentally
  different.
- Reusing StockMovement would require either: (a) shoehorning kg into a units
  ledger, breaking DECIMAL(17,3) grain precision, or (b) adding grain-specific
  fields to a generic inventory model, violating module boundaries.

**Alternatives Considered**:
- Extend StockMovement with grain-specific columns → rejected (module boundary
  violation, conflates two different domain concepts)
- Use a single universal movement model → rejected (over-generalisation, YAGNI)

---

## Decision 2: GrainLot Composite Key Includes storage_unit

**Decision**: The composite natural key for GrainLot is:
`(tenant, branch, grain_type, campaign, grado, storage_unit)`.

Data Model v1.0 states the composite identity as `(branch, grain_type, campaign,
grado)` but lists `storage_unit` as a separate FK on GrainLot. Spec-12 extends
the stated identity to include `storage_unit`.

**Rationale**:
- ARCA RG 3593 minimum composite key is `(plant_id, grain_code, campaign_id)`.
  The Data Model extends this with `grado` for quality grade segregation.
- The same grain type, campaign, and grade CAN physically exist in multiple silos
  simultaneously (e.g., Soybean Grade 2 Campaign 2025/26 in Silo 1 AND Silo 3).
- Without `storage_unit` in the key, a second deposit of the same grain into a
  different silo would reuse the same lot, making per-silo balance tracking
  impossible.
- The Data Model already carries `storage_unit` as a FK on GrainLot — the
  composite key extension is a natural consequence of that FK being non-nullable.

**Alternatives Considered**:
- One lot per `(branch, grain_type, campaign, grado)` spanning multiple silos →
  rejected (cannot track per-silo occupancy, violates stock report requirements)

---

## Decision 3: GrainMovement ADJUSTMENT as 5th Movement Type

**Decision**: GrainMovement has 5 movement types:
`DEPOSIT | WITHDRAWAL | TRANSFER_IN | TRANSFER_OUT | ADJUSTMENT`.

Data Model v1.0 defines 4 types. Spec-12 adds ADJUSTMENT.

**Rationale**:
- SRS-AL06 (Physical Inventory Reconciliation) explicitly requires an "ajuste"
  movement type for recording variances between physical measurements and ledger
  balances.
- ADJUSTMENT movements carry mandatory `notes` field (operator's explanation).
- ADJUSTMENT can be positive (surplus: physical > ledger) or negative (deficit:
  physical < ledger), following the same sign convention as other movement types.

**Alternatives Considered**:
- Model reconciliation as paired WITHDRAWAL + DEPOSIT → rejected (loses the
  semantic meaning of "adjustment" in the audit trail; makes reconciliation
  history harder to query)

---

## Decision 4: current_occupancy_kg as Annotated Queryset (Not Stored)

**Decision**: `current_occupancy_kg` is computed on-demand via a single Django
`annotate(Sum(...))` call on the StorageUnit queryset. It is NOT stored as a
field on StorageUnit.

**Rationale**:
- Storing occupancy as a field creates a second source of truth that can drift
  from the ledger. The requirement SC-006 states: "The grain lot running balance
  equals the arithmetic sum of all its movements at all times."
- The annotated queryset approach ensures occupancy is always derived from the
  authoritative ledger. A single `Sum("grain_lots__movements__quantity_kg")`
  annotation computes correct values for all 200 silos in one SQL query.
- REST API Design v1.0 §7.1 explicitly calls this a "derived value calculated
  from the grain movement ledger on demand."
- Performance target (SC-003: list within 1s for 200 units) is achievable with
  a single annotated query + index on `(tenant_id, grain_lot_id, movement_at)`.

**Alternatives Considered**:
- Store occupancy on StorageUnit and update on every movement → rejected (dual
  source of truth; requires coordinated updates in every movement transaction)
- Use a StockSnapshot-style summary table → rejected (over-engineered for this
  scale; adds a third entity that must be kept consistent)

---

## Decision 5: Romaneo FK Addition in Spec-12 Migration (Not Spec-11)

**Decision**: `Romaneo.storage_unit` (FK, SET_NULL, nullable) and
`Romaneo.grain_lot` (FK, SET_NULL, nullable) are added by spec-12 migration
0003, not by spec-11.

**Rationale**:
- StorageUnit and GrainLot models do not exist until spec-12 creates them.
  Django requires the target model to exist before a FK referencing it can be
  created.
- Spec-11 correctly deferred these FKs. The Data Model v1.0 defines them in
  Group 6 (Storage Assignment) with a clear note that they are set at discharge
  (storage_unit) and at CONFORME resolution (grain_lot).
- Migration 0003 uses `ALTER TABLE acopio_romaneo ADD COLUMN` with `null=True`,
  which is safe for existing rows (all receive NULL).

**Implementation note**: Romaneo's `save()` immutability gate at CONFORME must
allow `grain_lot` and `storage_unit` to be set. If these fields are NOT already
in the CONFORME-mutable allowlist, A1 must add them.

---

## Decision 6: Deposit Service is Triggered from romaneo.views, Not a Signal

**Decision**: The deposit-from-romaneo flow (FR-005) is triggered by an explicit
service call from `RomaneoViewSet.confirmar` action endpoint, not via a Django
`post_save` signal on Romaneo.

**Rationale**:
- Signals execute outside the request/response cycle, making error handling,
  tracing, and transaction management complex.
- The operator explicitly selects a storage unit before or at CONFORME. The
  `storage_unit` FK must be set on the Romaneo before the deposit service runs.
  A signal fired on `status → CONFORME` would need to read `romaneo.storage_unit`
  — if not set, the deposit cannot proceed. An explicit service call in the
  viewset action enforces the correct order: (1) set storage_unit, (2) call
  confirm, (3) service creates lot + movement.
- Explicit service calls are easier to test (no need to mock signal dispatch).

**Integration point**: `RomaneoViewSet.confirmar_conforme` action (spec-11,
`views/romaneo.py`) must be modified by A2 to call
`create_deposit_from_romaneo(romaneo, storage_unit, is_own_grain)` after the
romaneo status is saved. If `storage_unit` is not set, the action returns
HTTP 400.

---

## Decision 7: CampaignCloseService Requires Supervisor Role

**Decision**: `CampaignCloseService.close_campaign()` validates that the calling
user has supervisor-level permission before proceeding. Endpoint returns HTTP 403
for non-supervisor users.

**Rationale**:
- User Story 8 (spec.md) explicitly requires supervisor-level permission for
  campaign close. This is a regulatory compliance requirement (campaign close
  has fiscal implications).
- Campaign close is atomic: either all carry-forward movements are created and
  the campaign marked closed, or the entire operation rolls back (SC-008).
- Implementing this as a service (not inline viewset logic) enables independent
  unit testing of the validation + carry-forward logic.

**Permission check**: Use DRF `permission_classes` with a custom
`IsSupervisorOrAdmin` permission class (check existing auth patterns in
`apps/auth/permissions.py`).

---

## Decision 8: Transfer Locking Order (Deadlock Prevention)

**Decision**: When transferring grain between two lots, acquire `select_for_update()`
locks in ascending PK order (sorted UUID strings) to prevent deadlock when two
concurrent transfers involve the same lots in opposite order.

**Rationale**:
- Classic deadlock scenario: Thread A locks Lot1 then waits for Lot2; Thread B
  locks Lot2 then waits for Lot1.
- Consistent lock ordering (always lock by PK ascending) eliminates this cycle.
- UUIDs are lexicographically ordered; `sorted([str(pk1), str(pk2)])` provides
  a stable, deterministic order.

---

## Decision 9: GrainMovement `notes` Field (Extension Beyond Data Model)

**Decision**: GrainMovement carries a `notes = TextField(null=True, blank=True)`
field not present in the Data Model v1.0 GrainMovement definition.

**Rationale**:
- SRS-AL06 (Reconciliation) mandates "mandatory notes" on adjustment movements.
- The `notes` field is nullable (optional for non-ADJUSTMENT movements) but
  validated as required in the ReconciliationService when `movement_type == ADJUSTMENT`.
- This is a minimal justified extension. The alternative (a separate
  GrainMovementNote model) adds unnecessary complexity for a single text field.

---

## Domain Facts Summary

### Grain Inventory Tracking Axes (RG 3593)
Mandatory minimum per ARCA: `(plant_id, grain_code, campaign_id)`.
GraviTea extended key: `(branch, grain_type, campaign, grado, storage_unit)`.

### Storage Unit Types
1. `SILO_VERTICAL` — vertical concrete silo (main storage)
2. `CELDA_HORIZONTAL` — horizontal storage cell (flat bin)
3. `SECADERO_BIN` — wet holding bin, grain passes through dryer

### Grain Loses Physical Identity in Silo
Once grain enters a silo, the producer becomes owner of an **equivalent in
quality and quantity**, not the original physical grain. This is why tracking
is per-lot (composite identity), not per-producer per-silo.

### Own-Grain vs Third-Party Accounting (ADR-020)
- `is_own_grain = True` → accounting code 1.3.XX (Bienes de cambio — balance-sheet asset)
- `is_own_grain = False` → accounting code 8.1.XX (off-balance-sheet custody per RG 3593)
Misclassification at lot creation propagates through all downstream accounting entries.

### Campaign Year Carry Stock (stock de enlace)
Grain remaining at end of a campaign is carried to the next as "stock de enlace."
The ERP tracks carry lots as separate logical lots with a carry-forward
GrainMovement (TRANSFER_IN to new campaign lot). Physical grain may be co-mingled
but logical segregation is required by ARCA.
