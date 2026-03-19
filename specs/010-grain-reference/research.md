# Research: Grain Reference Data

**Feature**: 010-grain-reference | **Date**: 2026-03-18

## Research Summary

All domain knowledge was gathered during the specify phase via RAG queries against the `acopio_research` and `arca_dev_guides` Qdrant collections. No NEEDS CLARIFICATION items remained after `/speckit.clarify`. This document records the key decisions and their rationale.

## Decisions

### D1: Global vs Tenant-Scoped Model Classification

**Decision**: GrainType, ToleranceTable, and MermaTable are GLOBAL (no tenant FK, no RLS). CampanaConfig is tenant-scoped (inherits TenantBoundModel, gets RLS).

**Rationale**: Grain types and their regulatory parameters are government-mandated standards (ARCA, SAGPyA/SENASA). They are identical for all grain elevators in Argentina. Making them tenant-scoped would force every tenant to maintain duplicate copies of identical regulatory data, increasing seed data complexity and creating drift risk. Campaign years, however, are operational configuration per organization (each elevator decides when to open/close campaigns).

**Alternatives considered**:
- All models tenant-scoped: Rejected because regulatory data is universal. Would require N copies of identical data.
- All models global: Rejected because campaigns are genuinely per-organization.
- Tenant-overridable tolerances: Deferred to future spec. Some elevators negotiate custom tolerance thresholds with specific producers, but this is a contract-level feature, not reference data.

**Source**: ADR-010 (Architecture Decision Records v1.0)

### D2: Soja Hf = 12.5% (not 13.0%)

**Decision**: Use 12.5% as Soja's drying-formula moisture (Hf) in the seed fixture.

**Rationale**: The Data Model blueprint lists 13.0% (the base-reference value), but Research 2.5 "Tabla de parametros por grano para la base de datos" (the software-implementation reference table from the Camara Arbitral) explicitly lists 12.5%. The JNG source shows both values ("13,0 (base) / 12,5") for different calculation contexts. The 12.5% value is the correct one for the secado (drying) formula: `%S = (Hi - Hf) / (100 - Hf) * 100`. Using the wrong value yields ~168 kg error per 30-tonne truck.

**Alternatives considered**:
- Use 13.0% from blueprint: Rejected because it produces calculation errors.
- Store both values: Considered but over-engineering for spec-10. The Hf field is specifically for the secado formula.

**Source**: RAG query "merma calculation formula sequential", Research 2.5

### D3: Page-Number Pagination (Constitution Deviation)

**Decision**: Use page-number pagination with `count`/`next`/`previous` envelope, not cursor-based.

**Rationale**: The constitution (Principle XIII) mandates cursor-based pagination, but the REST API Design v1.0 Section 2.6 specifies page-number pagination with a `count` field. Cursor-based pagination cannot provide total count. For reference data endpoints (< 100 rows per table), offset-based performance degradation is not a concern.

**Alternatives considered**:
- Cursor-based (constitution default): Rejected because the API contract requires `count`.
- Hybrid (cursor + count): Over-engineering for small datasets.

**Source**: REST API Design v1.0 Section 2.6, Constitution Principle XIII

### D4: GrainType.code max_length=5 (Blueprint Deviation)

**Decision**: Increase `code` field from `CharField(max_length=3)` to `max_length=5`.

**Rationale**: The Data Model v1.0 specifies max_length=3, but internal codes for barley variants require 5 characters: `CEB_F` (cebada forrajera) and `CEB_C` (cebada cervecera). The blueprint's 3-character limit was based on the initial 5 grain types (TRI, MAI, SOJ, GIR, SOR) and did not account for extended codes.

**Alternatives considered**:
- Keep max_length=3 with shortened codes (CF, CC): Rejected because codes become ambiguous.
- Use ARCA code as primary identifier: Rejected because internal codes serve a different purpose (human-readable display).

**Source**: 10-specify.md reconciliation note, ARCA grain species table

### D5: arca_codigo Field Addition

**Decision**: Add `arca_codigo` (PositiveSmallIntegerField, unique) to GrainType model.

**Rationale**: The Data Model v1.0 defines `code` as the internal shortcode (TRI, MAI, etc.), while the REST API Design v1.0 Section 4.1 includes a `codigo` response field described as "ARCA grain code (e.g., 23 for soja)." These are two distinct identifiers. The `arca_codigo` field stores the official ARCA ncespecie integer used in WSCPE, WSLPG, and WSCDC web service calls.

**Alternatives considered**:
- Overload `code` field with ARCA integer: Rejected because code is a string shortcode.
- Store ARCA code in a separate mapping table: Over-engineering for a 1:1 relationship.

**Source**: REST API Design v1.0 Section 4.1, 10-specify.md reconciliation

### D6: Management Command vs loaddata

**Decision**: Use a custom management command with `update_or_create` instead of Django's `loaddata`.

**Rationale**: `loaddata` is not idempotent — it fails on duplicate PKs and doesn't support upsert behavior. The `seed_grain_reference` command uses natural keys (`code` for GrainType, `(grain_type, parameter, grado_base, valid_from)` for ToleranceTable) with `update_or_create` to achieve safe re-runs. It also supports `--dry-run` preview mode and per-record logging.

**Alternatives considered**:
- Django `loaddata` with fixed UUIDs: Fragile — UUID changes break the fixture.
- SQL INSERT ... ON CONFLICT: Bypasses Django ORM validation.

**Source**: FR-010/FR-011 (idempotency + preview mode requirements)
