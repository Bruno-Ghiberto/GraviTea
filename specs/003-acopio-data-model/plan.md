# Implementation Plan: Acopio Data Model & Domain Model

**Branch**: `003-acopio-data-model` | **Date**: 2026-03-16 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/003-acopio-data-model/spec.md`

## Summary

Rewrite `Docs/Project Blueprint/Data Model & Domain Model.md` from v0.3 (generic retail ERP, partially in Spanish) to v1.0 (complete acopio de granos domain model). The output is a ~1200–1800 line Markdown reference document containing: Mermaid ERDs for all 15+ entities, complete field tables (implementation-ready, one row per field), 6-state Romaneo machine, merma sequential formula with all intermediate steps, WSLPG field mapping table, RLS policy templates for all new tables, and an AI-Ready Data Architecture section mapping 4+ AI capabilities to specific model fields. This document is the SINGLE SOURCE OF TRUTH for all Django models; every implementation spec (09+) derives from it.

## Technical Context

**Language/Version**: Python 3.14.3 + Django 5.2.x (target document is Markdown; Django conventions used for field type notation)
**Primary Dependencies**: Django ORM (DecimalField, CharField, ForeignKey, OneToOneField, DateTimeField, JSONField) + PostgreSQL 18.1 (DECIMAL, UUID, ENUM via TextChoices)
**Storage**: PostgreSQL 18.1 — UUID v4 PKs, RLS enabled on all tenant-bound tables
**Testing**: pytest + pytest-django (implementation specs 09+ will write tests from this data model)
**Target Platform**: Cloud SQL Enterprise Plus (GCP) + Django ORM layer
**Project Type**: Blueprint document (single-author Markdown rewrite — not multi-agent code implementation)
**Performance Goals**: N/A for document; downstream: < 5 min/truck full romaneo cycle, < 60s sync for field devices
**Constraints**: DECIMAL(17,3) for all weights/monetary; DECIMAL(5,2) for all percentages; no FLOAT/DOUBLE; TenantBoundModel inheritance required for all grain domain entities
**Scale/Scope**: 15 grain domain entities + 8 preserved infrastructure entities + 7 preserved facturación/sync entities = 30+ entities total

## Constitution Check

*GATE: Passed — no violations.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I — DECIMAL(17,3), no FLOAT | ✅ PASS | FR-019 mandates DECIMAL(17,3) for all weight/monetary fields; DECIMAL(5,2) for percentages |
| I — Append-only ledger | ✅ PASS | AccountMovement, GrainMovement, MermaCalculation all immutable/append-only per spec |
| I — ON DELETE RESTRICT | ✅ PASS | ON DELETE PROTECT (Django equivalent) documented for all FKs in 03-plan.md |
| II — TenantBoundModel | ✅ PASS | FR-018: all grain domain models inherit TenantBoundModel |
| II — RLS | ✅ PASS | FR-023 + SC-004: RLS policy templates required for all new grain domain tables |
| III — Modular Django | ✅ PASS | Grain domain maps to future `acopio` module; no existing module boundaries crossed |
| VI — ARCA/WSAA | ✅ PASS | LiquidacionPrimaria + WSLPG field mapping in §8.2–§8.3; WSAA infrastructure preserved |
| X — TDD | N/A | Blueprint document; tests live in implementation specs 09+ |

## Project Structure

### Documentation (this feature)

```text
specs/003-acopio-data-model/
├── plan.md              ← This file
├── research.md          ← Phase 0 output (domain facts + decisions)
├── data-model.md        ← Phase 1 output (entity inventory)
├── quickstart.md        ← Phase 1 output (navigation guide)
└── tasks.md             ← Phase 2 output (/speckit.tasks command)
```

### Target Document

```text
Docs/Project Blueprint/
└── Data Model & Domain Model.md    ← REWRITE TARGET (v0.3 → v1.0)
```

### Source Code (downstream — derived from this document)

```text
backend/apps/
├── core/models/          ← TenantBoundModel, Tenant, Branch, AppUser, Role (preserved)
├── acopio/models/        ← NEW: GrainType, CampanaConfig, ToleranceTable, MermaTable,
│                              Romaneo, QualityAnalysis, MermaCalculation,
│                              StorageUnit, GrainLot, GrainMovement,
│                              WeighbridgeDevice, WeighbridgeCalibration, CPE
├── cuentas/models/       ← NEW: ProducerAccount, AccountMovement, FijacionRecord
├── inventario/models/    ← ADAPT: Product (+batch/lot/expiration), StockMovement (preserved)
├── facturacion/models/   ← EXTEND: LiquidacionPrimaria, CanjeOperation (NEW alongside existing)
└── sync/models/          ← PRESERVE: SyncSession, PendingOperation
```

## Implementation Approach

### Blueprint Spec Protocol

This is a **single-author document rewrite** (spec-03 through spec-08 convention). No tmux multi-agent orchestration. One AI agent writes the complete target document sequentially, section by section, following the 03-plan.md writing guide.

### Execution Order

1. **§1 Metadata + §2 Ironclad** — adapt from v0.3 (< 30 min)
2. **§3 ERD Global View** — new Mermaid diagrams (requires all entities known first)
3. **§4 Core Infrastructure** — preserve verbatim from v0.3
4. **§5 Grain Domain** — largest section; 8 sub-sections, 15 entities; follow 03-plan.md field tables exactly
5. **§6 Producer Accounts** — 3 entities + 8 transaction types
6. **§7 Agronomia** — adapt Product; preserve StockMovement
7. **§8 Facturación** — preserve Comprobante; add LiquidacionPrimaria + WSLPG mapping + CanjeOperation
8. **§9 Sync** — preserve verbatim
9. **§10 Cross-Module Links** — compile FK table from all sections
10. **§11 RLS Policies** — SQL templates for all new grain domain tables
11. **§12 AI-Ready** — capability → field mapping

### Checkpoint Gates

**Gate 1** (after §4): Infrastructure entities verbatim; ERD renders in Mermaid.
**Gate 2** (after §5): Romaneo ≥30 fields; secado formula uses Hf not humedad_base.
**Gate 3** (after §8): LiquidacionPrimaria 5-state machine; WSLPG mapping table complete.
**Gate 4** (final): SC-010 cross-check passes; RLS covers all new tables; AI section has ≥4 capabilities.

## Done Criteria

1. `Docs/Project Blueprint/Data Model & Domain Model.md` updated to v1.0
2. All 15 grain domain entities have complete field tables (6-column: name, type, precision, null, default, help_text)
3. Romaneo field count ≥30 (verified by counting table rows)
4. All Mermaid ERD diagrams render without syntax errors
5. MermaCalculation documents Hf values per grain type with explicit distinction from Humedad base
6. WSLPG field mapping table covers all mandatory XML elements (puntoEmision, numeroOrden, codGrano, codTipoOperacion, fechaEmision, pesoNetoGranos, precioReferencia, importeBruto, importeNeto)
7. All new grain domain tables have RLS policy template in §11
8. AI-Ready section maps ≥4 AI capabilities to ≥3 specific named model fields each
9. Zero field-name mismatches between ERD and field tables (SC-010 cross-check)
10. No FLOAT or DOUBLE in any field definition
11. Every grain domain entity inherits TenantBoundModel (SC-004)
12. `tasks.md` generated by `/speckit.tasks` after this plan is complete
