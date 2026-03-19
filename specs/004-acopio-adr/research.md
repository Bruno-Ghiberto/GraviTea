# Research: Architecture Decision Records — Content Inventory

**Branch**: `004-acopio-adr` | **Date**: 2026-03-17
**Phase**: 0 — Pre-writing content extraction from source documents
**Status**: Complete — all source content extracted; ready for ADR authoring

---

## Overview

This document is the content inventory for `Docs/Project Blueprint/Architecture Decision Records (ADR).md`. It extracts the key decision rationale from all five source documents so the ADR author can write each entry without context-switching between sources.

**Source documents** (fully read; excerpts below):

| Source | Location | ADRs Fed |
|--------|----------|----------|
| Constitution | `.specify/memory/constitution.md` | §4 (I–III), §7 (IV–V, XI), §8 (VI), §9 (VII), §10 (VIII–IX), §11 (X) |
| Vision v1.0 | `Docs/Project Blueprint/Product Vision & Scope.md` | §4 ADR-001/003, §9 ADR-028, §11 ADR-033 |
| PRD v1.0 | `Docs/Project Blueprint/PRD.md` | §5 ADR-011/013, §6 ADR-019, §8 ADR-025–027, §9 ADR-028/030, §10 ADR-032 |
| Data Model v1.0 | `Docs/Project Blueprint/Data Model & Domain Model.md` | §4–§5 (P1–P5), §6 ADR-017/018, §11 ADR-033–035 |
| spec-03 research | `specs/003-acopio-data-model/research.md` | §5 ADR-010/012/013, §6 ADR-014–016 |

---

## §4 Infrastructure Decisions — Source Extracts

### ADR-001: PostgreSQL 18.1 as Primary Database

**Source**: Constitution Principle I, Data Model §1 Metadata, Data Model P1

> Constitution I: "The database is the last line of defense. PostgreSQL 18.1 (Cloud SQL Enterprise Plus) serves as the foundation. Mechanical integrity is enforced at the database level with `ON DELETE RESTRICT` on all foreign keys and strict check constraints. Financial precision uses `DECIMAL(17,3)` exclusively."

> Data Model §1: "Database: PostgreSQL 18.1 | ID Strategy: UUID v4 auto-generated | Tenancy: Shared Database, Shared Schema, Hardened RLS"

**Rejected alternatives to document**: MySQL (no native RLS), SQLite (no concurrent multi-tenant writes), MSSQL (licensing cost, no RLS)

---

### ADR-002: UUID v4 as Primary Key Strategy

**Source**: Data Model §1 Metadata

> "ID Strategy: UUID v4 auto-generated"
> "No sequential enumeration (security), distributed generation (offline-first), no collision risk across branches"

**Rejected alternative**: Auto-increment integer — sequential enumeration attack surface (IDOR); sync conflicts between offline branches with overlapping sequences

---

### ADR-003: Modular Monolith via Django Apps (Not Microservices)

**Source**: Constitution Principle III

> "The backend follows a monolithic modular pattern using Django Apps [...] Views/ViewSets remain lightweight (orchestration only). Business invariants reside in Domain Services. Each module maintains clear boundaries and explicit dependencies."
> "Rationale: Modular architecture enables team scalability, independent testing, and future service extraction while avoiding premature microservices complexity."

**Acopio vertical modules**: `acopio` (grain reception, quality, merma, CPE), `cuentas` (producer current accounts, grain ledger)

---

### ADR-004: Shared Database / Shared Schema Multi-Tenancy

**Source**: Data Model §1 Metadata, Constitution II

> Data Model: "Tenancy: Shared Database, Shared Schema, Hardened RLS"
> Constitution II: "PostgreSQL Row Level Security (RLS) is mandatory on all transactional tables, making cross-tenant data access physically impossible."

**Rejected alternatives**: Schema-per-tenant (migration complexity, connection pooling overhead); Database-per-tenant (operational cost per tenant — incompatible with SMB SaaS pricing)

---

### ADR-005: Three-Layer Tenant Isolation (ORM + RLS + IDOR)

**Source**: Constitution II, Data Model §4.9 Physical & Security Architecture

> Constitution II: "The backend establishes three-layer tenant isolation:
> 1. Serializer Layer: Validates tenant_id/branch_id in request data
> 2. Model Layer: TenantBoundModel._validate_tenant_references() enforces FK tenant consistency
> 3. Database Layer: PostgreSQL RLS policies provide final enforcement"

> Data Model §4.9: "Layer 1 — ORM: TenantBoundManager auto-filters all queries by tenant_id. Layer 2 — Database: Session variable app.current_tenant_id (SET LOCAL, transaction-scoped). Layer 3 — Validation: JWT claims iss, aud, exp validated on every request."

**Rejected alternative**: ORM-only isolation — single-point bypass via raw SQL queries or ORM bugs

---

## §5 Data Architecture Decisions — Source Extracts

### ADR-006: Ironclad Principles Lineage (Three Sets)

**Source**: Constitution I–XI, Vision §2.3, Data Model §2.1

Three independent principle sets exist:
1. **Constitution I–XIV**: Foundational technical principles for all backend code
2. **Vision §2.3 Ironclad Design Principles (6)**: Strategic framing — offline-first, transactional integrity, encapsulated complexity, SMB security, regulatory automation, AI-ready data
3. **Data Model P1–P5**: Database-specific extensions — P1 engine integrity, P2 multi-tenant RLS, P3 financial immutability, P4 ML First, P5 AI-Ready Architecture

**Relationship**: Constitution is the foundational layer. Vision adds strategic framing (offline-first as principle 1, regulatory automation as principle 5). Data Model extends with P4 (ML First — "we discard nothing") and P5 (AI-Ready — provenance on all models) that have no equivalent in Constitution or Vision.

---

### ADR-007: DECIMAL(17,3) for Weights/Money, DECIMAL(5,2) for Percentages

**Source**: Constitution I, Data Model P1

> Constitution I: "Financial precision uses `DECIMAL(17,3)` exclusively for storage — `FLOAT`/`DOUBLE` are prohibited."
> Data Model P1: "`DECIMAL(17,3)` for all weights and monetary fields. `DECIMAL(5,2)` for all percentages. **`FLOAT`/`DOUBLE` are prohibited — zero exceptions.**"

**Key evidence**: Critical domain fact from spec-03 research — using wrong humidity value (Hf vs Humedad Base) yields ~168 kg error per 30-tonne truck. FLOAT/DOUBLE rounding errors in financial calculations are unacceptable for grain settlements.

---

### ADR-008: Append-Only Ledger for Financial Immutability

**Source**: Data Model P3, Constitution I, Vision §2.3 Principle 2

> Data Model P3: "Golden Rule: 'The past is not edited; it is corrected.' `StockMovement`, `Comprobante` (AUTORIZADO/OBSERVADO), `GrainMovement`, `AccountMovement`, and `MermaCalculation` are **APPEND-ONLY**. Errors are corrected via counter-entries, never via `UPDATE`."
> Vision §2.3.2: "No UPDATE on grain movements — only INSERT contra-entries. This guarantees forensic traceability for every kilogram from romaneo entry to liquidación completion."

**Rejected alternative**: Soft-delete with audit log — allows mutation (UPDATE on status fields), which breaks forensic traceability and enables retroactive data manipulation

---

### ADR-009: Dual Inventory Architecture (Grain vs Discrete SKU)

**Source**: Vision §4.5 Dual Inventory, PRD §4.3 ALMACENAMIENTO, Data Model §5.6 GrainLot

> Vision §4.5: "Grain (Activo Líquido): Continuous, in kilograms. Derived from romaneo peso neto conforme, adjusted by quality, campaña, and merma. Segregated by grain type, quality grade, campaña, silo, producer."
> "Insumos — Agronomía (Activo Contable): Discrete, in units. Counted: N units in, N units out."

**Data model divergence**: Grain uses `GrainLot + GrainMovement` (kg-based ledger). Agronomía uses `Product + StockMovement` (unit-based ledger).

**Rejected alternative**: Single unified inventory model — grain is measured in continuous kg (not discrete units), requires campaign segregation, and has different lifecycle (no expiration but quality degradation tracking)

---

### ADR-010: Global vs Per-Tenant Entity Classification

**Source**: spec-03 research D-004, D-006; Data Model §4.1, §5.1, §5.2

> spec-03 D-004: "ToleranceTable and MermaTable are GLOBAL reference tables — no tenant FK. Tolerance tables are issued by the Cámara Arbitral de Cereales de la Bolsa de Comercio de Rosario via SAGPyA/SENASA resolutions. They are legally binding and apply uniformly to all market participants."
> spec-03 D-006: "GrainType has no tenant FK. Grain type definitions (codes, names, humidity values, merma constants) are global reference data derived from ARCA species codes and SAGPyA/SENASA regulations."

**GLOBAL entities** (no tenant FK, no RLS): `GrainType`, `ToleranceTable`, `MermaTable`, `BusinessTemplate`
**PER-TENANT entities** (all others): `CampanaConfig`, `Romaneo`, `StorageUnit`, `GrainLot`, `ProducerAccount`, `AccountMovement`, `LiquidacionPrimaria`, and all operational entities

**Rejected alternative**: Per-tenant tolerance table overrides — tolerance tables are regulatory (not configurable); divergence from official tables exposes tenants to legal/commercial dispute risk

---

### ADR-011: Campaign-Year Segregation Pattern

**Source**: Data Model §5.1 CampanaConfig, PRD §4.3 ALMACENAMIENTO, spec-03 domain facts

> Data Model §5.1: "Format 'YYYY/YY' — 7 characters (e.g., '2024/25'). Starts April 1st. Ends March 31st. Constraint: UniqueConstraint(fields=['tenant', 'is_active'], condition=Q(is_active=True)) — only one active campaign per tenant."
> spec-03: "WSLPG XML uses 4-digit format: '2425' (not '2024/25'). CampanaConfig.campaign_code stores human-readable 'YYYY/YY' format."
> PRD §4.3: "Campaign year logical segregation using composite key (plant_id, grain_code, campaign_id) per RG 3593."

**Rejected alternative**: Calendar-year segregation — Argentine harvest campaigns span two calendar years (April–March); a 2024/25 campaign cannot be split across calendar year boundaries

---

### ADR-012: ON DELETE Behavior — RESTRICT Default with CASCADE/SET_NULL Exceptions

**Source**: spec-03 research D-007, Constitution I, Data Model P1

> spec-03 D-007: "Three entities use `ON DELETE CASCADE` (not RESTRICT/PROTECT): CPE, QualityAnalysis, MermaCalculation → Romaneo. These are 1:1 satellite records with no meaning without their parent Romaneo."
> "SET_NULL — Romaneo.weighbridge_device, Romaneo.storage_unit, Romaneo.grain_lot are nullable assignment fields. Deleting a device or storage unit must not cascade to delete historical romaneos."

**Full exception list**:
- CASCADE: `CPE → Romaneo`, `QualityAnalysis → Romaneo`, `MermaCalculation → Romaneo` (1:1 satellites)
- SET_NULL: `Romaneo.weighbridge_device_id`, `Romaneo.storage_unit_id`, `Romaneo.grain_lot_id`
- Default RESTRICT (PROTECT) everywhere else

---

### ADR-013: Posición Consolidada as Derived View (Not Stored)

**Source**: spec-03 research D-005, PRD §4.4 CUENTAS CORRIENTES

> spec-03 D-005: "No PosicionConsolidada model. Cross-plant consolidated view computed on-demand by aggregating per-plant ProducerAccount balances for the same producer CUIT across all plants of the same tenant."
> PRD §4.4: "The system MUST NOT use posicion consolidada as a source of truth — it is always recalculated from per-plant ledgers."

**Rejected alternative**: Materialized view or stored aggregate — consistency risk (aggregate can diverge from source ledger); deferred to implementation phase as optimization if query profiling shows need

---

## §6 Grain Domain Decisions — Source Extracts

### ADR-014: MermaTable Scope — Zarandeo Only

**Source**: spec-03 research D-001

> D-001: "MermaTable holds per-grain zarandeo thresholds only. Manipuleo and volatil are fixed regulatory constants that have never changed since publication. They belong on GrainType as static constants."
> "MermaTable is versioned (valid_from/valid_to) because the Cámara Arbitral de Cereales periodically updates zarandeo schedules."

**Fixed values on GrainType (not MermaTable)**:
- Manipuleo: trigo 0.10%, maiz 0.25%, soja 0.25%, girasol 0.20%, sorgo 0.25%
- Volátil: cereales (trigo/maiz/sorgo) 0.30%, oleaginosas (soja/girasol) 0.50%

---

### ADR-015: QualityParameter Inline on QualityAnalysis

**Source**: spec-03 research D-002

> D-002: "No QualityParameter model. Quality measurement fields are defined inline in QualityAnalysis with grain-type conditionality captured in help_text."
> "The 9 quality measurement parameters are a fixed, well-known set per Argentine grain trade regulations. A lookup table adds no value — it would be queried on every QualityAnalysis read without enabling any flexibility."

**9 fixed parameters**: humedad, materias_extranas, granos_dañados, granos_quebrados, peso_hectolitrico (cereals only), proteina (trigo only), granos_verdes (soja only), granos_ardidos, cuerpos_extranos

---

### ADR-016: WeighbridgeDevice as Separate Entity

**Source**: spec-03 research D-003

> D-003: "WeighbridgeDevice is a separate entity (name, serial_number, branch FK, is_active, interface_type, connection_address). A weighbridge is a distinct physical asset that accumulates multiple calibration records over its lifetime."
> "Pointing directly to Branch would prevent multi-scale branches and lose serial/certificate traceability required for regulatory audits."

**Rejected alternatives**: FK to Branch (no device traceability), FK to StorageUnit (weighbridge is not a storage unit)

---

### ADR-017: Grade Fields on Romaneo (Not QualityAnalysis)

**Source**: Data Model §5.3 Romaneo field table (spec-03 implementation override)

> Data Model: `Romaneo.grado_asignado` (int) and `Romaneo.bonificacion_rebaja_pct` DECIMAL(5,2) are fields on Romaneo, not QualityAnalysis.
> Design rationale: Grade is the commercial outcome of quality analysis — it belongs on the reception document (Romaneo), not in the lab measurement record. For oleaginosas, `grado_asignado=0`.

---

### ADR-018: Per-Step Merma kg Not Stored (Derived from Intermediates)

**Source**: Data Model §5.5 MermaCalculation, spec-03 implementation design

> Data Model P4/P5: MermaCalculation stores: all 4 input percentages, all 4 `peso_post_*` intermediate weights, `total_merma_kg`, `total_factor_pct`, and `peso_final_kg`.
> Design rationale: Individual step deductions (zarandeo_kg, secado_kg, manipuleo_kg, volatil_kg) are derivable as the difference between consecutive `peso_post_*` fields. Storing them would be redundant and introduce consistency risk (stored value could diverge from derivation).

---

### ADR-019: Single Form 1116-C per Grain Type (WSLPG Constraint)

**Source**: spec-03 domain facts, PRD §4.5 LIQUIDACIONES

> spec-03: "CRITICAL constraint: One Form 1116-C = ONE grain type only. Separate XML submission per grain type required."
> "codGrano (Integer, 2 digits) — grain type at ROOT level (single-grain-type constraint)"
> PRD §4.5: "Form 1116-C and 1116-B are filed electronically via the WSLPG web service. References: RG 3419/2012, RG 3690/2014, RG 3691/2014."

**System implication**: Software must split multi-grain liquidaciones into separate payloads before WSLPG filing

---

### ADR-020: Own Grain vs Third-Party Grain Accounting Separation

**Source**: Data Model §5.6 GrainLot (`is_own_grain` field), Data Model §7 (chart of accounts context)

> Data Model: `GrainLot.is_own_grain` BooleanField
> Accounting treatment: Own grain = 1.3.XX Bienes de cambio (balance-sheet asset); Third-party grain = 8.1.XX Cuentas de orden (off-balance-sheet)
> Rationale: Own grain held for resale is a balance-sheet asset. Grain held on behalf of producers is custodial — never an asset of the acopiador.

---

## §7 Security Decisions — Source Extracts

### ADR-021: JWT RS256 with Custom Tenant/Branch Claims

**Source**: Constitution V, XI, Data Model §4.7 AppUser

> Constitution XI: "Custom JWT claims include: tenant_id, branch_id, email, full_name. Token lifetimes: Access 15 minutes; Refresh 7 days."
> Data Model §4.7: "Algorithm: RS256 (4096-bit RSA). HS256/HS512 prohibited."

**Rejected alternative**: HS256 (symmetric HMAC) — key compromise affects all tenants simultaneously; asymmetric RS256 limits blast radius to the private key holder

---

### ADR-022: AES-256-GCM Field-Level Encryption with HMAC Blind Index

**Source**: Constitution IV

> Constitution IV: "Sensitive data (PII/fiscal) requires application-level encryption using AES-256-GCM via the cryptography library with custom wrapper implementation in apps/core/encryption/. Master keys are stored in Google Secret Manager, never in code/Docker/Git. Searchable encrypted fields use blind indexing with HMAC-SHA256 deterministic hashes on normalized data."

**Rust acceleration**: Feature branch 018 delivers 8.7x speedup for AES-256-GCM, 8.8x for HMAC blind index

**Rejected alternative**: Database-level TDE (Transparent Data Encryption) — does not protect against application-layer breaches; key stored in database infra, same breach radius as data

---

### ADR-023: Argon2 Password Hashing (Not bcrypt)

**Source**: Constitution V

> Constitution V: "Password hashing uses ArgonPasswordHasher (via argon2-cffi) to resist GPU/ASIC attacks."
> Constitution V: "Rationale: Authentication is the gateway to all system access. Modern threats require state-of-the-art password hashing."

**Rejected alternative**: bcrypt — GPU-parallelizable; lower resistance than Argon2's memory-hard design against modern hardware accelerators

---

### ADR-024: SSRF Validation Pipeline (Rust)

**Source**: Feature branch 022-ssrf-validation-pipeline

> Feature 022: "SSRF validation: validate_url_safety + check_resolved_ip — 831 lines, 308 tests"
> PRD implementation status: "Rust SSRF Security ✅ Complete | 83-entry adversarial corpus, 10 CIDR ranges"
> Design rationale: URL safety validation requires adversarial input processing; Rust regex engine avoids ReDoS on malformed URLs; resolved IP check prevents bypass via DNS rebinding

---

## §8 Fiscal Integration Decisions — Source Extracts

### ADR-025: ARCA Web Service Architecture (WSAA → WSLPG + WSCPE + WSFEv1)

**Source**: Constitution VI, PRD §4.5, §4.6

> Constitution VI: "The facturacion module implements robust integration with ARCA Web Services (WSAA/WSFEv1) for electronic invoicing (CAE/CAEA). Communication uses SOAP over HTTPS. The system handles the complete WSAA flow: TRA generation, X.509 certificate signing to create CMS, Base64 encoding, and LoginCMS invocation for Token/Sign receipt."
> PRD §3.1: ARCA Web Services: WSAA (auth) → WSFEv1 (standard invoicing/CAE), WSLPG (grain liquidaciones), WSCPE (CPE lifecycle)

---

### ADR-026: CAEA for Offline Fiscal Operations During Harvest

**Source**: PRD §3.2 (feature 024), Data Model §8 ARCA entities

> PRD: "Rust ARCA Batch ✅ Complete | 024-rust-arca-batch | CAEA batch builder via serde_json — enables offline fiscal operations during harvest"
> Constitution VI: "The system handles the complete WSAA flow... CAE (online) for connected operations; CAEA (offline) for harvest-season fiscal continuity"

> **Legal constraint**: ARCA requires authorization BEFORE invoice issuance for legal validity. CAE-only with store-and-forward would mean the invoice is issued offline WITHOUT authorization — a legally invalid document. CAEA provides pre-authorized batch codes for a quincena (15-day period), enabling legally valid invoice issuance offline.

**Rejected alternative**: CAE-only + store-and-forward — deferred authorization equals legally invalid document at time of issuance; harvest-season fiscal continuity requires anticipatory batch codes

---

### ADR-027: SISA-Tier Retention Calculation at LPG Filing Time

**Source**: PRD §4.5 LIQUIDACIONES

> PRD §4.5: "SISA Pre-Liquidación Blocking Gate: The system MUST query SISA before every settlement. If the SISA query fails or returns an invalid/suspended status, the system MUST block the liquidación from proceeding to WSLPG filing. This gate cannot be bypassed."
> SISA Estado determines IVA retention rate: Estado 1 → 5%, Estado 2 → 8%, Estado 3 → 10.5%, Non-registered → 16%
> Ganancias: Estado 1 → 0%, Estado 2 → 2%, Estado 3 → 15%, Non-registered → 30%

**Regulatory reference**: RG 5689/2025 (SISA replacing RUCA), RG 5821/2026 (CPE issuance linked to SISA compliance)

---

## §9 Offline & Sync Decisions — Source Extracts

### ADR-028: Offline-First as Base Architecture (Not Fallback)

**Source**: Vision §2.3 Principle 1, Vision §4.4 Technical Differentiators, PRD §4.1

> Vision §2.3.1: "Offline is the base architecture, not a fallback mode. The system assumes the network is unreliable. Synchronization is a secondary, non-blocking process — every truck reception completes locally regardless of connectivity."
> PRD §4.1 offline behavior: "The romaneo completes entirely offline. CPE confirmation calls are queued in a store-and-forward buffer and transmitted when connectivity restores. Conflict resolution for romaneo data is additive."
> PRD §4.3: "All storage operations — silo assignment, inter-silo transfers, position queries — work fully offline."

**Market evidence**: PRD §3.3: "44% of operators report only 'regular' connectivity quality (INTA/ENACOM 2021). Cloud-dependent systems require internet for all operations, not just ARCA filings."

**Rejected alternative**: Online-first with offline fallback — "fallback" implies degraded experience; rural Argentine acopios have intermittent connectivity during harvest peak

---

### ADR-029: Conflict Resolution Taxonomy (5 Strategies by Data Type)

**Source**: Constitution VII

> Constitution VII (full verbatim):
> - **Configuration data**: `server_wins` — server values always take precedence
> - **Inventory levels**: `last_write_wins` — most recent update prevails, with audit trail
> - **Sales transactions**: `additive` — combine transactions from all sources
> - **Customer data**: `most_complete_wins` — merge with preference for complete records
> - **Document numbering**: `server_assigns_final` — temporary offline numbers replaced by server sequence

**Rust implementation**: Feature 023 (`023-rust-sync-conflict`) delivers `most_complete_wins` merge via serde_json with GIL-released batch processing

---

### ADR-030: Store-and-Forward Queue for ARCA Web Service Calls

**Source**: PRD §4.1 RECEPCION offline behavior

> PRD §4.1: "CPE confirmation calls (confirmarArriboCPE, descargadoDestinoCPE, confirmacionDefinitivaCPEAutomotor) are queued in a store-and-forward buffer and transmitted when connectivity restores."
> spec-03 domain facts: "CPE validity: 5-day window from issuance. Store-and-forward required for offline operations."

**Data model support**: `PendingOperation` entity in sync module queues ARCA web service calls

---

## §10 Performance Decisions — Source Extracts

### ADR-031: Rust/PyO3 Acceleration Boundary

**Source**: Vision §4.4, PRD §3.2 (feature branches 017–025), CLAUDE.md Active Technologies

**Measured benchmarks** (from feature branches):
| Module | Feature | Speedup |
|--------|---------|---------|
| AES-256-GCM encryption | 018-rust-crypto | 8.7x |
| HMAC blind index | 018-rust-crypto | 8.8x |
| IVA calculation | 019-rust-fiscal-compute | 4.4x |
| CUIT validation | 019-rust-fiscal-compute | 3.1x |
| Importes validation | 019-rust-fiscal-compute | 2.7x |
| Stock aggregation | 019-rust-fiscal-compute | 2.1x |
| Observability label sanitization | 021-rust-observability | 2.6x |

**Move to Rust when**:
- Latency-sensitive hot path (>1000 calls/sec)
- GIL contention in batch processing
- CPU-bound computation (crypto, regex, merma calculation)
- Adversarial input validation (SSRF, URL parsing)

**Stay in Python when**:
- ORM/database operations (Django handles this well)
- Business orchestration logic (readability > speed)
- API endpoint handlers (Django REST Framework)
- One-time operations (not worth compile overhead)

**Rejected alternatives**: Pure Python everywhere — measured 2.1x–8.7x slowdowns on hot paths; Pure Rust server — loses Django ecosystem (ORM, DRF, migrations, admin)

---

### ADR-032: Weighbridge Integration Architecture

**Source**: PRD §4.1 RECEPCION, Research 3.1

> PRD §4.1: "Peso bruto and tara capture directly from weighbridge (RS-232 / TCP-IP)"
> PRD US-R03: "Given the weighbridge is connected via RS-232 and the truck is on the scale, When the scale signals a stable reading, Then the system automatically captures the weight value without manual transcription."

**Protocol stack**:
- Primary: Modbus RTU (Sipel Orion scales) or command/response ASCII (Systel scales)
- Fallback: Continuous ASCII stream (GaMa A12 and similar)
- Network bridge: KYASERV RS232-Ethernet adapter for LAN access from application server

---

## §11 AI/ML Readiness Decisions — Source Extracts

### ADR-033: AI-Ready Data Architecture (4-Layer Strategy)

**Source**: Data Model §12.1, Data Model P4, P5, Vision §2.3 Principle 6

> Data Model §12.1 Four-Layer Data Strategy:
> - Layer 1 — Operational Data: All grain domain fields captured in real-time with full timestamps
> - Layer 2 — Behavioural Data: operator_id, laboratorista_id, device_id, 6 named per-process timestamps
> - Layer 3 — Quality History: QualityAnalysis rows accumulate over time per (grain_type, campaign, storage_unit)
> - Layer 4 — Physical State (IoT-Ready): StorageUnit.environment_sensor_id as IoT anchor

> Vision §2.3.6: "Every weighing event, quality grade, and storage movement is captured as structured data from day one — enabling ML features in Phase 4 without data migration."

**Rejected alternative**: Post-hoc data structuring after collecting unstructured records — requires data archaeology; ML training delayed by months; "captured as structured data from day one" is the commitment

---

### ADR-034: Provenance Fields on All Grain Domain Models

**Source**: Data Model P5, §12.3 Feature Store Readiness

> Data Model P5: "Provenance fields present on all grain domain models: created_at, updated_at, created_by, device_id."
> Data Model §12.3: "All grain domain models include created_at (auto_now_add), updated_at (auto_now), created_by (FK → AppUser), device_id (CharField on Romaneo)."
> "Enables behavioral analytics and fraud detection baselines — operator performance baselines, device drift detection."

---

### ADR-035: Measurement-Timestamp Pairing for Behavioral Analytics

**Source**: Data Model P5, §12.2 AI Capability → Model Field Mapping, spec-03 NF-002

> Data Model P5: "Measurement fields paired with timestamps (e.g., QualityAnalysis.analysis_timestamp, Romaneo.ts_pesada_bruta). Derived fields stored alongside inputs (MermaCalculation stores all 4 peso_post_* intermediates)."
> Data Model §5.3 Romaneo: 6 named timestamps: ts_entrada, ts_pesada_bruta, ts_calado, ts_analisis, ts_descarga, ts_tara
> §12.2 Use case: "Weighbridge Fraud Detection — Romaneo.patente_chasis + Romaneo.peso_bruto_kg + Romaneo.operator_id + Romaneo.ts_pesada_bruta → anomaly detection on weight/operator patterns"

---

## Constitution Principle → ADR Traceability Map

All 11 principles (I–XI) traced to at least one ADR:

| Principle | Subject | ADR(s) |
|-----------|---------|--------|
| I — Ironclad Data Model | PostgreSQL, DECIMAL, RESTRICT, append-only | ADR-001, ADR-007, ADR-008 |
| II — Multi-Tenant RLS | Shared schema, RLS, IDOR | ADR-004, ADR-005 |
| III — Modular Django Architecture | Django Apps, modular monolith | ADR-003 |
| IV — Application-Level Encryption | AES-256-GCM, blind index, GCP Secret Manager | ADR-022 |
| V — Secure Authentication | Argon2, JWT RS256, custom claims | ADR-021, ADR-023 |
| VI — Fiscal Compliance (ARCA) | WSAA, WSFEv1, WSLPG, CAEA | ADR-025, ADR-026 |
| VII — Offline-First | Offline base, conflict resolution, store-and-forward | ADR-028, ADR-029, ADR-030 |
| VIII — Query Optimization | select_related, N+1 prevention | ADR-031 (Rust boundary for DB hotpaths) |
| IX — Secure Data Operations | Mass assignment prevention, explicit fields | ADR-005 (IDOR validation) |
| X — Test-Driven Development | 80% coverage, TDD | ADR-003 (modular independence enables isolated tests) |
| XI — JWT Authentication | RS256, 15min/7day lifetimes, custom claims | ADR-021 |

---

## spec-03 Domain Decisions → ADR Map

All 7 decisions captured:

| spec-03 Decision | ADR | Category |
|-----------------|-----|----------|
| D-001: MermaTable Scope — Zarandeo Only | ADR-014 | §6 Grain Domain |
| D-002: QualityParameter Inline | ADR-015 | §6 Grain Domain |
| D-003: WeighbridgeDevice as Separate Entity | ADR-016 | §6 Grain Domain |
| D-004: ToleranceTable is Global | ADR-010 | §5 Data Architecture |
| D-005: Posición Consolidada is Derived | ADR-013 | §5 Data Architecture |
| D-006: GrainType is Global | ADR-010 | §5 Data Architecture |
| D-007: ON DELETE CASCADE for 1:1 Satellites | ADR-012 | §5 Data Architecture |
