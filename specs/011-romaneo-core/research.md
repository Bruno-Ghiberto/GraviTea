# Research: Romaneo Core

**Feature**: 011-romaneo-core | **Date**: 2026-03-19

## Summary

No NEEDS CLARIFICATION items existed in the Technical Context. All technical decisions were resolved during the specification phase (`11-specify.md`) and coherence review. This research documents the key decisions and their rationale.

## Decisions

### R-001: Sequential Merma Formula Implementation

**Decision**: Implement the Circular CAC 10/86 sequential merma formula in Rust via PyO3, with a pure-Python fallback for development/testing.

**Rationale**: The merma calculation is CPU-bound decimal arithmetic that runs on every romaneo confirmation. Rust provides guaranteed precision via `rust_decimal` and performance via native code. PyO3 bridges to Python seamlessly. The Python fallback ensures tests work without the Rust toolchain.

**Alternatives considered**:
- Pure Python only: Sufficient for correctness but slower. Rejected because the Rust infrastructure already exists (spec-017 bootstrap).
- C extension: More complex FFI, less memory-safe. Rejected in favor of Rust/PyO3 already in the codebase.

### R-002: Secado Formula Using hf_secado_pct

**Decision**: The secado (drying) deduction formula uses `GrainType.hf_secado_pct` (regulatory final moisture), NOT `humedad_base_pct` (commercial base moisture).

**Rationale**: These are distinct values with different business meanings. For trigo: Hf=13.5% (secado), base=14.0% (commercial). Using the wrong value yields approximately 168 kg error per 30-tonne truck. Verified against Research 2.5 (Merma Calculations) and RAG results.

**Alternatives considered**:
- Using humedad_base_pct: Incorrect per regulatory formula. Would cause systematic financial errors.

### R-003: Immutability Gate at CONFORME

**Decision**: Romaneo becomes immutable at CONFORME status, following the same `save()` override pattern as `StockMovement` in the inventario module. At CONFORME, only tare capture fields (`tara_kg`, `peso_neto_bruto_kg`, `ts_tara`) and the status transition to CERRADO are permitted. At CERRADO, absolutely nothing can change.

**Rationale**: CONFORME represents the moment the commercial weight is finalized and credited to the producer. Retroactive changes would corrupt the financial record. The CERRADO check must come before CONFORME in the `save()` method so its stricter guard takes precedence.

**Alternatives considered**:
- Database trigger for immutability: Planned as future defense-in-depth layer but not implemented in this spec to avoid migration complexity.
- Soft immutability (warnings only): Rejected -- financial records require hard enforcement.

### R-004: WeighbridgeDevice FK Strategy

**Decision**: Use a nullable `CharField` placeholder for `weighbridge_device` instead of a FK to a stub model. Omit `storage_unit` and `grain_lot` FKs entirely (spec-12 will add them via migration).

**Rationale**: Creating stub models that would need replacement adds unnecessary migration complexity. CharField placeholder is simple, nullable, and can be converted to a FK in a future spec without data loss.

**Alternatives considered**:
- Stub models with docstrings: More complex, requires migration to drop stub and recreate real model.
- String-based FK references: Django doesn't support FK to non-existent models.

### R-005: Romaneo Number Format

**Decision**: Format `ROM-{YYYY}-{NNNNN}` with per-branch sequential numbering. Server assigns final number (offline romaneos get temporary UUID placeholder replaced at sync).

**Rationale**: Per REST API Design Section 10 (`server_assigns_final` conflict resolution strategy). Branch-scoped numbering allows each plant to maintain its own sequence. Year prefix enables annual reset without collisions.

**Alternatives considered**:
- Global numbering (across all branches): Requires distributed sequence coordination. Rejected for simplicity.
- UUID-only (no human-readable number): Rejected because operators need readable identifiers for physical documents.

### R-006: Pagination for Romaneo List

**Decision**: Use `PageNumberPagination` (not cursor) for romaneo list endpoints, with `page_size=25`.

**Rationale**: Constitution XIII mandates cursor pagination, but romaneo lacks the `created_at` field required by the project's `StandardCursorPagination`. Ordering is by `ts_entrada` instead. Spec-10 already established `PageNumberPagination` for acopio models (`ReferenceDataPagination`), so this maintains consistency within the vertical. Documented as a justified deviation.

**Alternatives considered**:
- Adding `created_at` field for cursor pagination: Redundant with `ts_entrada`. Adds unnecessary field.
- Using `ts_entrada` as cursor field: Cursor pagination requires strictly unique ordering; two romaneos could theoretically have identical `ts_entrada` values.

### R-007: QualityAnalysis State Guards

**Decision**: QualityAnalysis creation allowed when romaneo is EN_PROCESO or PESADO. Updates allowed only when romaneo is ANALIZADO. No modifications after CONFORME.

**Rationale**: Per REST API Design v1.0 Section 6. Quality analysis may begin during weighing (EN_PROCESO) or after gross weight (PESADO). Once the romaneo is confirmed, quality data becomes part of the immutable audit record.

**Alternatives considered**:
- Allow QA creation only at PESADO: Too restrictive. Lab analysis may start during arrival processing.
- Allow QA updates at any pre-CONFORME state: Too permissive. Once the romaneo reaches ANALIZADO, the quality data should be stable.
