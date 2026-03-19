# Research: High-Level Design (HLD) Document

**Feature**: 005-acopio-hld
**Date**: 2026-03-17
**Status**: Complete — no NEEDS CLARIFICATION items remain

---

## Purpose

This file is the writing reference guide for `Docs/Project Blueprint/High-Level Design (HLD).md`.
It consolidates all domain facts, verbatim constraint sentences, and architectural decisions the
author needs in a single place, eliminating the need to re-read specs 01–04 during writing.

---

## 1. Decision Log

### D-001 — Phase 1 / Phase 2 App Annotation

**Decision**: Section 5 of the HLD presents all 8 Django apps uniformly as the intended
architecture. Inline "(Phase 2)" annotations appear only on `apps/facturacion` (Wave 6,
electronic invoicing) and `apps/liquidaciones` (spec-14, WSLPG + SISA gate). Phase 1 apps
receive no annotation.

**Rationale**: Presenting a partial architecture is misleading for new team members. The "(Phase 2)"
label provides full architectural context while clearly communicating delivery timeline. Resolved
via `/speckit.clarify` session 2026-03-17.

**How to apply**: §5 subsection headings or opening sentences for `apps/facturacion` and
`apps/liquidaciones` must contain the literal text "(Phase 2)".

---

### D-002 — Romaneo Flow Step Count

**Decision**: The canonical romaneo reception flow has exactly 10 steps. The PRD's §4.1 lists an
11-step breakdown; silo assignment is treated as a sub-step of romaneo issuance (step 10), not a
separate step.

**Rationale**: spec.md §Assumptions confirms the 10-step representation is canonical.

**How to apply**: The `sequenceDiagram` in §9.1 must contain exactly 10 numbered steps. Do not
collapse gross/tare weight capture into a single step.

---

### D-003 — Mermaid as Diagram Format

**Decision**: All diagrams use Mermaid text notation (`graph TD`, `sequenceDiagram`,
`flowchart TD`, `stateDiagram-v2`). No binary image files.

**Rationale**: NF-0501 mandates text-based notation for diff-friendliness and rendering in
GitHub/MkDocs. Starter skeletons are provided in `Docs/PROMPTS/spec-05-hld/05-plan.md §5`.

---

### D-004 — HLD Cites ADRs; Does Not Reproduce Them

**Decision**: Every architecture section must cite the relevant ADR(s) using format "ADR-NNN
(Title)" but must NOT reproduce the ADR's context/decision/rationale text. Point readers to
spec-04 for rationale.

**Rationale**: NF-0506 and spec.md §Out of Scope. Reproducing ADR rationale creates maintenance
debt and bloats the HLD.

---

### D-005 — CAEA Legal Constraint Verbatim Requirement

**Decision**: Section 6.5 must include the exact sentence (or equivalent in substance):
*"CAEA codes MUST be obtained before the offline period begins. An invoice issued with a deferred
CAE (authorization obtained after issuance) is a legally invalid fiscal document."*

**Rationale**: SC-0502 and the legal constraint is not an implementation preference — it is a
regulatory requirement with no workaround. The sentence must be unambiguous.

---

### D-006 — CPE Lifecycle States (WSCPE Protocol Level)

**Decision**: Section 6.4 documents the WSCPE-level CPE states: `Activa` (issued) →
`Arribo` (`confirmarArriboCPE`) → `Descargada` (`descargadoDestinoCPE`) →
`Confirmada_Definitiva` (`confirmacionDefinitivaCPEAutomotor`). "Vencida" is a derived condition
(timer-based), not a WSCPE state code.

**Rationale**: The romaneo app-level state machine (PENDIENTE → ANALIZADO → etc.) is a UI
workflow concern, not the WSCPE protocol. These are different abstractions. Confusing them leads
to incorrect SOAP call sequencing.

**Alternatives considered**: Documenting app-level states → Rejected (wrong abstraction level for
an architecture document).

---

### D-007 — Rust Benchmark Values and Symbol Format

**Decision**: All speedup values in the §4.4 benchmark table use the × multiplication sign
(Unicode U+00D7), not lowercase ASCII "x". Example: `8.7×`, not `8.7x`.

**Rationale**: Consistency with ADR-031 formatting. SC-0506 requires zero formatting drift.

---

### D-008 — Production Cloud Provider

**Decision**: Production environment targets Google Cloud Platform: Cloud Run for Django API,
Cloud SQL Enterprise Plus for PostgreSQL 18.1. Google Cloud Secret Manager for all private keys.

**Rationale**: spec.md §Assumptions confirms GCP as production provider, consistent with ADR
cross-references to Secret Manager throughout spec-04.

---

## 2. Domain Terminology — First-Use Definitions

The HLD must define each term on first use in each major section. Authors: copy these definitions.

| Term | Definition (for first-use inline note) |
|------|----------------------------------------|
| **romaneo** | The complete reception document generated when a truck is weighed, sampled, and graded at the acopio plant |
| **merma** | Sequential weight deductions (drying, sieving, handling, volatile loss) applied to raw net weight |
| **acopiador** | The enterprise that receives, stores, conditions, and commercialises grain on behalf of producers |
| **CPE** (Carta de Porte Electrónica) | Mandatory electronic waybill authorising grain transit by truck; lifecycle managed by WSCPE |
| **CTG** (Código de Trazabilidad de Granos) | Grain traceability code embedded in each CPE |
| **WSLPG** | ARCA web service for filing Form 1116-B/C (Liquidación Primaria de Granos) grain settlements |
| **WSCPE** | ARCA web service managing CPE lifecycle (arrival confirmation, discharge, definitive confirmation) |
| **WSFEv1** | ARCA web service for per-invoice CAE electronic authorisation (Comprobante Electrónico v1) |
| **WSAA** | ARCA authentication gateway; issues Token+Sign (TA) used by all other ARCA services |
| **CAE** | Código de Autorización Electrónico — per-invoice fiscal code returned by WSFEv1 online |
| **CAEA** | Código de Autorización Electrónico Anticipado — pre-authorised batch code obtained for a quincena period; enables offline invoicing |
| **SISA** | Producer compliance registry (RG 5689/2025); determines withholding tier (Estado 1–3) |
| **COE** | Código de Operación Electrónico — identifier returned by `liquidacionAutorizar` confirming WSLPG filing |
| **campana** | Split-year crop campaign identifier (e.g., "2025/26"); mandatory for all storage and accounting |
| **pizarra** | Reference price per ton published by Bolsa de Comercio; used for fijación events |
| **quincena** | 15-day period used for CAEA batch pre-authorisation cycles |
| **TRA** | Ticket de Requerimiento de Acceso — XML document signed with X.509 cert to initiate WSAA login |

---

## 3. Verbatim Constraints

These sentences must appear verbatim (or with equivalent unambiguous substance) in the HLD.
Each sentence has a verification grep command.

### VC-001 — CAEA Legal Constraint (§6.5)

```
"CAEA codes MUST be obtained before the offline period begins. An invoice issued with a
deferred CAE (authorization obtained after issuance) is a legally invalid fiscal document."
```

Verification: `grep "CAEA codes MUST be obtained before" "Docs/Project Blueprint/High-Level Design (HLD).md"`

---

### VC-002 — Offline as Base Mode (§8.1)

```
"44% of operators report 'regular' (not good) connectivity quality (INTA/ENACOM 2021)"
"Offline is the base operating mode, not a degraded fallback"
```

Verification: `grep "44%" "Docs/Project Blueprint/High-Level Design (HLD).md"`

---

### VC-003 — RLS Session Variable (§10.3)

```
SET LOCAL app.current_tenant_id = '{uuid}'
USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
```

Verification: `grep "SET LOCAL app.current_tenant_id" "Docs/Project Blueprint/High-Level Design (HLD).md"`

---

### VC-004 — Python Fallback on Rust Load Failure (§4.2/§4.4)

Substance (not verbatim): "If the Rust `.so` extension fails to load at Django startup, the
Python fallback activates automatically without operator intervention."

---

### VC-005 — WSLPG Single Grain Constraint (§6.3)

Substance: "`codGrano` is at the XML root — one WSLPG submission per grain type (ADR-019)."

Verification: `grep "codGrano" "Docs/Project Blueprint/High-Level Design (HLD).md"`

---

## 4. Key Numerical Facts

All values derived from ADR document and domain research. Use exactly as shown.

| Fact | Value | HLD Section |
|------|-------|------------|
| WSAA TA token lifetime | 12 hours | §6.2 |
| Redis TA cache TTL | 11 hours (1-hour safety margin) | §6.2 |
| CPE Automotor validity window | 5 days | §6.4, §8.7 |
| AES-256-GCM speedup | 8.7× (branch 018-rust-crypto) | §4.4 |
| HMAC blind index speedup | 8.8× (branch 018-rust-crypto) | §4.4 |
| IVA calculation speedup | 4.4× (branch 019-rust-fiscal-compute) | §4.4 |
| CUIT validation speedup | 3.1× (branch 019-rust-fiscal-compute) | §4.4 |
| Importes validation speedup | 2.7× (branch 019-rust-fiscal-compute) | §4.4 |
| Stock aggregation speedup | 2.1× (branch 019-rust-fiscal-compute) | §4.4 |
| Observability label sanitization speedup | 2.6× (branch 021-rust-observability) | §4.4 |
| JWT access token lifetime | 15 minutes | §10.4 |
| JWT refresh token lifetime | 7 days | §10.4 |
| JWT RSA key size | 4096 bits | §10.4 |
| RS-232 baud rate | 9600 baud, 8N1 | §7.2 |
| Sipel Orion Modbus address: Gross weight | Address 0 (2 registers, 32-bit signed int) | §7.2 |
| Sipel Orion Modbus address: Tare | Address 2 | §7.2 |
| Sipel Orion Modbus address: Net weight | Address 4 | §7.2 |
| Django API port | 8000 | §4.2, §11.1 |
| PostgreSQL port | 5432 | §4.2, §11.1 |
| Redis port | 6379 | §4.2, §11.1 |
| Qdrant port | 6333 | §4.2, §11.1 |
| SMB SaaS budget (USD/month) | 90–360 | §11.4 |
| SISA Estado 1 withholding | IVA 5% / Ganancias 0% | §6.3 |
| SISA Estado 2 withholding | IVA 8% / Ganancias 2% | §6.3 |
| SISA Estado 3 withholding | IVA 10.5% / Ganancias 15% | §6.3 |
| SISA Non-registered withholding | IVA 16% / Ganancias 30% | §6.3 |

---

## 5. ARCA Service URLs

| Service | Environment | URL |
|---------|------------|-----|
| WSLPG | Production | `https://serviciosjava.afip.gob.ar/wslpg/LpgService?wsdl` |
| WSLPG | Homologation | `https://fwshomo.afip.gov.ar/wslpg/LpgService?wsdl` |

Note: Homologation requires pre-seeded ARCA test CUITs. Random CUITs fail validation. Cite in §6.3.

---

## 6. 8 Django Apps — Entity Ownership

Reference for §5 Component Overview:

| App | Phase | Owned Entities |
|-----|-------|---------------|
| `apps/core` | Phase 1 | Tenant, Branch, AppUser, Role, TenantFieldDefinition, TenantModuleConfig |
| `apps/auth` | Phase 1 | AppUser (auth aspects), JWT token management |
| `apps/acopio` | Phase 1 | Romaneo, QualityAnalysis, MermaCalculation, CPE, StorageUnit, GrainLot, GrainMovement, WeighbridgeDevice, CampanaConfig, GrainType, ToleranceTable, MermaTable |
| `apps/cuentas` | Phase 1 | ProducerAccount, AccountMovement, FijacionRecord |
| `apps/sync` | Phase 1 | SyncSession, PendingOperation |
| `apps/core/observability` | Phase 1 | Prometheus metrics, OpenTelemetry tracing (no DB entities) |
| `apps/facturacion` | **Phase 2** | Comprobante, CAEA, ArcaCredential, PuntoDeVenta |
| `apps/liquidaciones` | **Phase 2** | LiquidacionPrimaria |

---

## 7. Romaneo 10-Step Component Mapping

For §9.1 step list (copy verbatim into the step list under the sequence diagram):

| Step | Action | Responsible Component |
|------|--------|-----------------------|
| 1 | Arrival — gross weight reading | Weighbridge Driver (`apps/acopio`) |
| 2 | `peso_bruto` captured | Weighbridge Driver → `apps/acopio` |
| 3 | Calado sampling | `apps/acopio` (lab workflow) |
| 4 | `QualityAnalysis` created (9 parameters) | `apps/acopio` |
| 5 | `merma_calculate(quality_params, tables)` | Rust Engine (via PyO3 FFI) |
| 6 | Grade assignment (`grado_asignado`, `bonificacion_rebaja_pct`) | `apps/acopio` |
| 7 | Unload → tare weight reading | Weighbridge Driver (`apps/acopio`) |
| 8 | `peso_tara` captured | Weighbridge Driver → `apps/acopio` |
| 9 | Net weight = (bruto − tara) × merma_factor | `apps/acopio` |
| 10 | Romaneo issuance (boleta + silo credit + account credit); CPE confirmation queued | `apps/acopio` + `apps/sync` (WSCPE queue) |

---

## 8. Technology Version Reference

For §4.2 Container Architecture:

| Container | Technology | Version | Port | Role |
|-----------|-----------|---------|------|------|
| Django API | Python + Django + DRF | 3.14.3 / 5.2.x | 8000 | WSGI/Gunicorn |
| PostgreSQL | PostgreSQL | 18.1 | 5432 | Primary datastore; RLS enforced |
| Redis | Redis | 7.x | 6379 | Session cache, rate limiter, TA token cache |
| Rust Extension | Rust + PyO3 + Maturin | 1.93.1 + 0.28 + 1.12.4 | N/A | Loaded at startup via Python FFI |
| Qdrant | Qdrant | Latest | 6333 | Optional vector search; dev/RAG only |

---

## 9. ADR Cross-Reference Summary

Key ADRs and their HLD sections (for §13 table construction):

| ADR | Title (abbreviated) | Primary HLD Section |
|-----|--------------------|--------------------|
| ADR-001 | PostgreSQL 18.1 as primary datastore | §4.2 |
| ADR-002 | UUID v4 ID strategy | §8.2 |
| ADR-003 | Modular monolith, no microservices | §4.2, §11.2 |
| ADR-004 | Shared schema cost model | §11.4 |
| ADR-005 | Three-layer tenant isolation | §10.1–10.4 |
| ADR-007 | DECIMAL(17,3) financial precision | §12.2 |
| ADR-010 | Global vs per-tenant table segregation | §10.3 |
| ADR-019 | Single grain type per WSLPG submission | §6.3 |
| ADR-021 | JWT RS256 authentication | §10.4 |
| ADR-022 | AES-256-GCM encryption | §10.5 |
| ADR-023 | Rate limiting | §5.2 |
| ADR-024 | SSRF Rust validation | §5.1 |
| ADR-025 | ARCA web service architecture | §6.1–6.2 |
| ADR-026 | CAEA offline invoicing | §6.5, §8.6, §9.2 |
| ADR-027 | SISA tier retention | §6.3 |
| ADR-028 | Offline-first base architecture | §8.1 |
| ADR-029 | Conflict resolution strategies | §8.4 |
| ADR-030 | Store-and-forward PendingOperation queue | §8.5, §9.3 |
| ADR-031 | Rust/PyO3 acceleration boundary | §4.4 |
| ADR-032 | Weighbridge integration protocols | §7.1–7.4 |
| ADR-033 | AI/ML 4-layer data architecture | §12.1–12.5 |
| ADR-034 | Provenance fields on grain domain models | §12.2–12.3 |
| ADR-035 | Measurement-timestamp pairing | §12.3 |
