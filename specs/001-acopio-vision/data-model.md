# Document Content Model: Acopio de Granos Product Vision & Scope

**Phase 1 output for**: `specs/001-acopio-vision/plan.md`
**Deliverable**: `Docs/Project Blueprint/Product Vision & Scope.md` v1.0
**Date**: 2026-03-15

---

## Overview

This document defines the content model for the vision document. Each section is treated as an
entity with required fields, data sources, relationships to other sections, and completion criteria.

The document has 11 sections with a strict dependency chain (upstream sections must be written first):

```text
S1 (Metadata) ─────────────────────────────────────────────────────→ (stamp all sections)
S3 (Market) ────→ S2 (Purpose) ────→ S4 (Product) ────→ S5 (Personas)
                       ↓                    ↓
                  S6 (Value Prop)      S7 (GTM)
                                           ↓
                                      S8 (Pricing)
                                           ↓
                                      S9 (AI Roadmap)
                                           ↓
                              S10 (KPIs) + S11 (Risks)
```

---

## Entity: Section 1 — Document Metadata & Preamble

**Purpose**: Version stamp, implementation status table, and feature branch history.

### Fields

| Field | Required | Source | Notes |
|-------|----------|--------|-------|
| Version | Yes | New: `1.0` | Replace `0.4` |
| Date | Yes | New: `2026-03-15` | Today's date |
| Status | Yes | "Vision Document — Committed" | Remove "Under Evaluation" language |
| Implementation Progress table | Yes | v0.4 lines 13-28 (copy verbatim) | All metrics still accurate |
| Feature Branch History table | Yes | Git history + v0.4 | Preserve 001-025; update descriptions for acopio context |
| "Ironclad" design principles | Yes | v0.4 + 2 new principles | Expand from 4 to 6 principles |

### Content Requirements

**Implementation Progress table** — copy verbatim from v0.4:
- Backend Core ✅ Complete (Auth, Inventory, Ventas, ARCA, Sync)
- Rust/PyO3 ✅ Complete (9 modules)
- 2,500+ tests | 79 API paths | 9 OpenAPI contracts | 9 Rust modules
- Python 3.14.3, Django 5.2.x, DRF, PostgreSQL 18.1, Rust 1.93.1 (PyO3 0.28)

**Feature Branch History** — all 25 branches (001-025) with descriptions updated for acopio context.

**Ironclad principles** — 6 total:
1. Pragmatic Offline-First (existing, preserve intent)
2. Transactional Integrity / Ledger (existing, preserve intent)
3. Encapsulated Complexity (existing, preserve intent)
4. Enterprise Security for SMBs (existing, preserve intent)
5. Regulatory Automation (**NEW** — CPE/CTG, C-1116, SISA happen automatically)
6. AI-Ready Data Architecture (**NEW** — structured capture enables Phase 4 ML)

### Relationships
- Referenced by: ALL other sections (they use the version stamp)
- Must be consistent with: `Docs/Project Blueprint/Descripcion General del Producto.md` (module names)

### Completion Criteria
- `[x]` Version reads "1.0" and date reads "2026-03-15"
- `[x]` Zero occurrences of: "hardware store", "beverage distributor", "cashier", "under evaluation"
- `[x]` Exactly 6 Ironclad principles, last 2 are "Regulatory Automation" and "AI-Ready Data Architecture"
- `[x]` Feature Branch History table has exactly 25 rows (001-025)

---

## Entity: Section 2 — Strategic Purpose & Vision

**Purpose**: Acopio-specific vision statement and commitment declaration.

### Fields

| Field | Required | Source | Notes |
|-------|----------|--------|-------|
| Vision statement | Yes | research.md §S2 draft | Replace generic retail statement |
| Vertical commitment declaration | Yes | D-001 decision log | Declarative, no "under evaluation" |
| Primary competitive moat | Yes | D-002 decision log | Offline-first leads |

### Content Requirements

**Vision statement** (replaces "Transform traditional SMB retailers..."):
> "Empower independent Argentine grain operators (acopiadores de granos) with the first cloud-native,
> offline-first ERP purpose-built for grain stockpiling operations — delivering automatic regulatory
> compliance, real-time grain position visibility, and enterprise-grade security to the small-to-medium
> acopiador who has been historically underserved by desktop-era software."

**Vertical commitment**: explicit declaration that the acopio pivot is final — no hedging language.

### Relationships
- Depends on: S3 (market context validates the opportunity claim)
- Feeds into: S4 (product vision follows from strategic vision)
- Feeds into: S6 (value proposition operationalizes the strategic purpose)

### Completion Criteria
- `[x]` Vision statement contains: "acopiadores de granos", "offline-first", "regulatory compliance", "real-time"
- `[x]` No generic retail language in this section
- `[x]` Commitment declaration is unambiguous (present tense, not conditional)

---

## Entity: Section 3 — Market Context

**Purpose**: Market sizing, competitive landscape, pain points, and technology adoption.

### Fields

| Field | Required | Source | Notes |
|-------|----------|--------|-------|
| TAM | Yes | research.md §3.1 | [Research 6.1] citation required |
| SAM | Yes | research.md §3.1 | [Research 6.1] citation required |
| SOM | Yes | research.md §3.1 | Cordoba + Santa Fe with member counts |
| Competitive landscape diagram | Yes | research.md §3.2 | Mermaid quadrant chart |
| 11 competitor profiles | Yes | research.md §3.2 | FR-004 requires min 6, document 11 |
| Government mandatory systems box | Yes | research.md §3.2 | Must-integrate, not compete |
| Market segmentation (4 tiers) | Yes | research.md §3.2 | Percentages per tier |
| 6 pain points | Yes | research.md §3.4 | With regulatory citations |
| Technology adoption stats | Yes | research.md §3.4 | [Research 4.3] citations |
| GRAVITEA unique position statement | Yes | research.md §3.2 | "combination no incumbent offers" |

### Content Requirements

**Market sizing** (cite [Research 6.1]):
- TAM: ~1,259 acopiador-consignatario enterprises, ~2,458 storage plants nationwide
- SAM: ~1,073 private (non-cooperative), ~1,622 plants (~68% of total)
- SOM: Córdoba (81 Federación members) + Santa Fe (58 members) = 139 initial targets

**Competitive positioning diagram**: Mermaid quadrant with axes:
- X: Deployment model (Desktop-only → Cloud-native)
- Y: Vertical depth (Generic/Horizontal → Acopio-operational-depth)
- GRAVITEA occupies upper-right quadrant alone

**Competitor profiles** (11 entries — see research.md §3.2 tables):
- 8 specialized desktop vendors (Algoritmo, AGIS/AmericaGIS, Physis, AgroAcopio, Agrosistemas, Gestagro/Kernel, Siscoop, Informática Tandil, SYNAgro)
- 3 cloud/SaaS generalist (Finnegans GO Granos, Versat ERP Agro, Albor Campo)

**Government mandatory systems** (callout box — must integrate, not compete):
- SIO Granos, SISA/Registro Sistémico, BolsaTech

**6 pain points** (with regulatory citations):
1. Regulatory compliance: CPE/CTG, C-1116 (RG 3419/2012), SISA (RG 5689/2025), CPE+SISA link (RG 5821/2026)
2. Tax withholdings: IVA 8%, Ganancias 2-15%, IIBB, SICORE magnetic files
3. Inventory reconciliation: cubicaje, grain position, overselling risk
4. Producer account disputes: quality grading, conditioning costs, "a fijar" operations
5. Manual data entry: weighbridge transcription, peak harvest hundreds of trucks/day
6. Connectivity: 40.2% rural parajes, 44% "regular" connectivity (nuanced — plants in towns not fields)

### Relationships
- Depends on: S1 (version stamp)
- Feeds into: S2 (validates the market opportunity)
- Feeds into: S4 (competitor gaps → product features)
- Feeds into: S5 (pain points → persona jobs-to-be-done)
- Feeds into: S7 (market map → GTM targeting)

### Completion Criteria
- `[x]` TAM/SAM/SOM all cite [Research 6.1]
- `[x]` Mermaid competitive positioning diagram renders without errors
- `[x]` Minimum 6 individual competitor profiles with: location, platform, clients, strengths, weaknesses
- `[x]` Government systems box present and labeled "must integrate, not compete"
- `[x]` 4-tier market segmentation with percentages
- `[x]` All 6 pain points present with regulatory citations where applicable
- `[x]` GRAVITEA unique position statement: "cloud-native + offline-first + acopio-operational-depth"

---

## Entity: Section 4 — Product Vision & Scope

**Purpose**: Module map, operational flow, technical differentiators, MVP scope, and out-of-scope declaration.

### Fields

| Field | Required | Source | Notes |
|-------|----------|--------|-------|
| Module map (Mermaid diagram) | Yes | research.md §S4, Descripcion General | 8 modules, exact Spanish names |
| Core operational flow (Mermaid) | Yes | research.md §S4 | Romaneo-to-Position loop |
| MVP scope definition | Yes | D-004, research.md §S4 | FR-007 |
| Technical differentiators | Yes | research.md §S4 | 6 items, offline-first LEADS |
| Dual inventory explanation | Yes | research.md §S4 | Grain continuous kg + insumos discrete |
| Out-of-scope list | Yes | research.md §S4 | 6 items |
| Phased roadmap (Mermaid) | Yes | D-004, spec.md FR-013 | 4 phases |

### Content Requirements

**8 modules** (exact names from Descripcion General del Producto.md):
1. RECEPCIÓN (Romaneo)
2. ALMACENAMIENTO
3. CALIDAD
4. CUENTAS CORRIENTES
5. LIQUIDACIONES
6. FACTURACIÓN
7. AGRONOMÍA (Insumos)
8. CANJE

**Core operational flow** (Mermaid flowchart):
Arrival (CPE/CTG) → Gross weight (balanza) → Calado y muestreo → Quality analysis → Merma calc →
Net weight conforme → Boleta de Romaneo → Silo assignment + Producer account credit →
Liquidación (1116-C) or Canje por insumos

**MVP scope** (Phase 1 = Romaneo-to-Position loop):
- Reception: truck arrival, CPE/CTG, gross weight, calado
- Quality analysis: lab grading, tolerance tables, merma calculations
- Storage assignment: silo allocation by grain type/quality/campaign
- Producer account credit: saldo granos kg, movement history

**Technical differentiators** (order matters — offline-first is primary moat):
1. Offline-first hybrid architecture
2. Rust acceleration layer (PyO3, 2-9x speedups)
3. PostgreSQL RLS multi-tenancy (plant-level isolation)
4. ARCA direct integration (WSAA/WSFEv1/WSLPG)
5. AI-ready data architecture
6. Field-level encryption (AES-256-GCM)

**Out of scope**: Generic POS, B2C e-commerce, Manufacturing/industrial, Field agriculture, Fleet management, Payroll/HR

**4-phase roadmap** (Mermaid timeline or Gantt):
- Phase 1: Romaneo + Position (MVP)
- Phase 2: Liquidaciones + WSLPG
- Phase 3: Canje + Agronomía
- Phase 4: AI features

### Relationships
- Depends on: S3 (competitor gaps inform what we build)
- Feeds into: S5 (modules map to persona jobs-to-be-done)
- Feeds into: S9 (AI roadmap is Phase 4 of the phased plan)
- Must be consistent with: `Docs/Project Blueprint/Descripcion General del Producto.md` (module names/scope)

### Completion Criteria
- `[x]` Module map Mermaid diagram renders with exactly 8 modules using Spanish names
- `[x]` Operational flow Mermaid diagram shows the Romaneo-to-Position loop end-to-end
- `[x]` MVP scope explicitly calls out 4 sub-components: reception, quality, storage, producer account
- `[x]` Technical differentiators list: offline-first is item #1
- `[x]` Phased roadmap Mermaid renders with 4 phases in correct order
- `[x]` Out-of-scope list has minimum 6 items including "farm management" and "POS"
- `[x]` Module names consistent with Descripcion General (spot-check: RECEPCIÓN, LIQUIDACIONES, CANJE)

---

## Entity: Section 5 — User Personas

**Purpose**: 5 acopio-specific personas with jobs-to-be-done, pain points, and tech profiles.

### Fields

| Field | Required | Source | Notes |
|-------|----------|--------|-------|
| Persona hierarchy diagram (Mermaid) | Yes | research.md §S5 | FR-005 |
| 5 persona profiles | Yes | research.md §S5 | One card per persona |
| ICP definition | Yes | research.md §S5 | Independent acopiador profile |

### Content Requirements

**5 personas** (from research.md §S5 table):
1. **Dueño/Gerente**: remote grain position + financial control; smartphone, medium-high comfort
2. **Balancero/Recibidor**: complete truck reception < 5 min; Windows desktop, medium comfort
3. **Laboratorista**: grade samples without spreadsheets; desktop tools, medium comfort
4. **Administrador/Contable**: file all regulatory docs automatically; AFIP portals, medium-high
5. **Contador Rural**: real-time multi-client fiscal visibility; cloud tools, high comfort

**ICP**: Independent (non-cooperative) acopiador, 1-5 plants, Pampas region, small-medium capacity,
currently using desktop software or generic ERP + Excel, experiencing generational transition.

**Persona hierarchy diagram**: Mermaid showing which personas interact with which modules:
- Dueño/Gerente → dashboard/reports (all modules read-only)
- Balancero → RECEPCIÓN primary
- Laboratorista → CALIDAD primary
- Administrador → LIQUIDACIONES + FACTURACIÓN + CUENTAS CORRIENTES
- Contador Rural → external portal (read-only fiscal view)

### Relationships
- Depends on: S3 (pain points drive persona pains), S4 (modules drive persona scope)
- Feeds into: S6 (personas' pains → value proposition)
- Feeds into: S7 (personas → GTM targeting)

### Completion Criteria
- `[x]` Exactly 5 persona profiles
- `[x]` Each profile contains: role, primary JTBD, key pain, tech comfort level
- `[x]` Persona hierarchy Mermaid diagram renders
- `[x]` ICP definition covers: business type, size (plants), region, current tech, transition context
- `[x]` No generic roles (no "cashier", "store manager", "retail clerk")

---

## Entity: Section 6 — Value Proposition Canvas

**Purpose**: Explicit pain-to-gain mapping showing how GRAVITEA solves acopiador-specific problems.

### Fields

| Field | Required | Source | Notes |
|-------|----------|--------|-------|
| 6 pain points | Yes | research.md §3.4 | Same 6 from market context |
| 6 corresponding gains | Yes | research.md §S4 | Product features as gains |
| Value prop canvas (Mermaid or table) | Yes | FR-006 | Visual mapping |

### Content Requirements

**Pain → Gain mapping**:
| Acopiador Pain | GRAVITEA Gain |
|----------------|---------------|
| Regulatory burden (CPE/CTG/SISA manual) | Automatic regulatory compliance |
| Tax withholding complexity (IVA/Gan/IIBB) | Instant retention calculations per liquidación |
| Inventory reconciliation discrepancies | Real-time grain position (comprado vs vendido vs físico) |
| Producer account disputes | Transparent quality grading with tolerance tables |
| Manual data entry during harvest peak | Weighbridge integration + offline operations |
| Connectivity gaps halting CTG operations | Hybrid offline-first: CAEA mode when cloud unavailable |

### Relationships
- Depends on: S3 (pain points), S4 (product features as gains), S5 (personas experience these pains)
- Feeds into: S7 (GTM messaging uses this value prop)

### Completion Criteria
- `[x]` All 6 pain-to-gain pairs present
- `[x]` Visual representation (Mermaid diagram or structured table) renders correctly
- `[x]` Pains use domain-specific language (CPE/CTG, not "compliance")
- `[x]` Gains reference actual product capabilities (CAEA mode, tolerance tables)

---

## Entity: Section 7 — Go-to-Market Strategy

**Purpose**: Channel strategy, geographic beachhead, trade events, and switching strategy.

### Fields

| Field | Required | Source | Notes |
|-------|----------|--------|-------|
| Contador rural channel mechanics | Yes | research.md §S7-8, D-006 | FR-011 |
| Geographic beachhead | Yes | D-005 | Villa María → Córdoba → Pampas |
| Trade events (specific dates/venues) | Yes | research.md §S7-8 | FR-011 |
| Switching window | Yes | research.md §S7-8 | April-June |
| Referral flow description | Yes | research.md §S7-8 | "Invitar a tu contador" |

### Content Requirements

**Contador rural channel**:
- 5-15 acopio clients per agro-specialized estudio (20-50 total agricultural clients)
- Free portal: real-time transactions, automated books, multi-client dashboard, one-click exports
- "Invitar a tu contador" referral flow
- FACPCE seminars targeting (RT 22, RT 41) + CPCE Córdoba agro events

**Geographic beachhead** (Villa María → Córdoba → Pampas):
- D-005 rationale: founder's base, Sociedad de Acopiadores HQ, 81 Federación CBA members
- Risk acknowledged: AGIS HQ also in Villa María (both vulnerability signal and competitive risk)

**Trade events**:
- Tier 1: A Todo Trigo (May 2026, Mar del Plata), Sociedad de Acopiadores de Córdoba
- Tier 2: Grano SAC/Expo Poscosecha (Rosario, November), ExpoAgro, AgroActiva
- Federación de Acopiadores de Cereales (ongoing membership)

**Switching strategy**:
- April-June window (post-soybean harvest, lowest operational intensity)
- Migration tools from AGIS/Physis/Excel
- ACA Jóvenes networks (generational transition targeting)

### Relationships
- Depends on: S3 (market map → targeting), S5 (personas → channel actors: contador is a persona)
- Feeds into: S8 (GTM connects to pricing model)

### Completion Criteria
- `[x]` Contador channel section includes: client count per estudio, free portal mechanics, referral flow name
- `[x]` Geographic beachhead is explicitly Villa María first (with AGIS risk acknowledged)
- `[x]` Minimum 3 trade events with specific venues; A Todo Trigo has month (May 2026)
- `[x]` April-June switching window explicitly named with rationale

---

## Entity: Section 8 — Pricing Strategy

**Purpose**: Per-seat pricing model, competitive comparison, and free accountant portal.

### Fields

| Field | Required | Source | Notes |
|-------|----------|--------|-------|
| Per-seat price | Yes | D-003, research.md §S7-8 | $90/seat/month, $75 annual |
| Incumbent comparison | Yes | research.md §S7-8 | $500-800/establishment |
| Small acopio disruption example | Yes | D-003 | 2 users = $180 vs $500+ |
| Free accountant portal | Yes | D-006 | Distribution mechanism |
| USD-indexing rationale | Yes | D-003 | ARS devaluation protection |

### Content Requirements

**Pricing structure**:
- Monthly: $90/seat/month (USD-indexed)
- Annual: $75/seat/month (17% discount for annual commitment)
- Free: Contador rural portal (unlimited read-only fiscal view)

**Disruption comparison**:
- Small acopio (2 users): $180/month vs. incumbent $500-800/establishment → 2.8x-4.4x cheaper
- Versat reference: USD 200-640/month (no acopio-depth)

**USD-indexing rationale**: grain pricing in Argentina is USD-denominated; operators mentally budget in USD regardless of ARS price; USD-indexed SaaS protects against devaluation for both operator and GRAVITEA

### Relationships
- Depends on: S7 (pricing is part of GTM strategy)
- Feeds into: S10 (ARPU KPI of $360/month/tenant)

### Completion Criteria
- `[x]` $90/seat/month and $75/seat/year both present
- `[x]` Incumbent price range $500-800/establishment cited
- `[x]` Small acopio disruption math present (2 users, ~$180 vs $500+)
- `[x]` Free accountant portal described as distribution mechanism (not just a feature)

---

## Entity: Section 9 — AI Differentiation Roadmap

**Purpose**: Phase 3-4 AI capabilities from research 9.1 — future differentiators, not MVP.

### Fields

| Field | Required | Source | Notes |
|-------|----------|--------|-------|
| 6-7 AI capabilities | Yes | research.md §S9 | [Research 9.1] citations |
| Model architectures per capability | Yes | research.md §S9 | 3D-CNN, MILP, VMD-SGMD-LSTM, etc. |
| Phase assignment (3 or 4) | Yes | spec.md FR-010 | All are post-MVP |
| AI-ready data architecture link | Yes | S1 Ironclad principle 6 | Forward reference |

### Content Requirements

**7 AI capabilities** (from research.md §S9):
1. Quality degradation prediction — 3D-CNN + LSTM — 97.38% accuracy
2. Silo assignment optimization — MILP — 27% truck queue reduction
3. Price forecasting (Matba Rofex) — VMD-SGMD-LSTM
4. Price forecasting (local basis) — XGBoost
5. Weighbridge fraud detection — Anomaly detection
6. Document intelligence — OCR (Carta de Porte)
7. Predictive aeration scheduling — SVM-Poly — 99.98% efficiency

**Framing**: All capabilities are Phase 3-4 ("the platform we're building today enables these capabilities
without data migration"). The AI-ready data architecture (Ironclad principle 6) is the bridge.

### Relationships
- Depends on: S4 (phased roadmap positions AI in Phase 4)
- Depends on: S1 (Ironclad principle 6 = AI-ready data architecture)
- Feeds into: S10 (AI features generate future KPIs)

### Completion Criteria
- `[x]` Minimum 6 AI capabilities present
- `[x]` Each capability has model architecture named
- `[x]` All capabilities explicitly positioned as Phase 3-4 (not MVP)
- `[x]` [Research 9.1] citation present
- `[x]` Forward reference to AI-ready data architecture principle

---

## Entity: Section 10 — Success Metrics

**Purpose**: KPIs organized by category (Operational, Adoption, Business) with targets.

### Fields

| Field | Required | Source | Notes |
|-------|----------|--------|-------|
| Operational KPIs | Yes | research.md §S10 | Harvest throughput, sync latency, uptime |
| Adoption KPIs | Yes | research.md §S10 | Onboarding time, active user rate |
| Business KPIs | Yes | research.md §S10 | Stock discrepancy, compliance rate, ARPU |

### Content Requirements

**Operational KPIs**:
- Harvest throughput: > 10 trucks/hour per balancero (vs manual 4-6/hour)
- Sync latency: < 60 seconds for critical data to all plants
- System uptime: 99.5%+ (offline mode local availability even during cloud outages)

**Adoption KPIs**:
- Balancero onboarding: < 1 day from zero to first romaneo
- Active user rate: > 80% provisioned users active within 30 days

**Business KPIs**:
- Stock discrepancy: < 2% after 3 months (vs 10-15% industry standard with manual tracking)
- Regulatory compliance: CTG/LPG filed successfully > 99.5% of attempts
- ARPU: $360/month/tenant Year 1 (4 seats × $90)

### Relationships
- Depends on: S4 (product capabilities set the baseline), S8 (pricing drives ARPU)
- No downstream dependencies (terminal section)

### Completion Criteria
- `[x]` 3 categories present: Operational, Adoption, Business
- `[x]` Each KPI has a specific numeric target
- `[x]` Harvest throughput comparison (> 10/hour vs manual 4-6/hour) present
- `[x]` ARPU target consistent with pricing section ($360 = 4 × $90)

---

## Entity: Section 11 — Risks & Mitigation

**Purpose**: 6 identified risks with severity ratings and mitigation strategies.

### Fields

| Field | Required | Source | Notes |
|-------|----------|--------|-------|
| 6 risk rows | Yes | research.md §S11 | With severity and mitigation |
| 7-in-10 failure statistic | Yes | research.md §3.4 pain point 5 | [Albor Agtech] attribution |

### Content Requirements

**6 risks** (from research.md §S11):
1. Connectivity gaps during harvest — High — offline-first primary moat
2. Regulatory change velocity (ARCA/SISA) — High — modular ARCA integration
3. Competitor response (Algoritmo + Silohub) — Medium — first-mover advantage
4. Adoption resistance (generational divide) — Medium — ACA Jóvenes + contador channel
5. Data migration barrier — High — structured import tools + April-June window
6. 7/10 implementation failure rate — High — process-first onboarding + white-glove

### Relationships
- Depends on: S3 (market risks), S4 (technical risks), S7 (GTM risks)
- No downstream dependencies (terminal section)

### Completion Criteria
- `[x]` Exactly 6 risks (FR-015 minimum)
- `[x]` Each risk has severity (High/Medium/Low) and mitigation
- `[x]` 7-in-10 failure statistic present with [Albor Agtech] attribution
- `[x]` Connectivity risk explicitly names offline-first as the mitigation
- `[x]` Data migration risk names April-June window

---

## Section Dependency Summary

```text
WRITE ORDER (dependency-driven):
1. S3 (Market Context)      — foundation, no dependencies
2. S2 (Strategic Purpose)   — depends on S3 for market validation
3. S4 (Product Vision)      — depends on S3 gap analysis
4. S5 (Personas)            — depends on S3 pains + S4 modules
5. S6 (Value Prop Canvas)   — depends on S3 pains + S4 features + S5 personas
6. S7 (GTM Strategy)        — depends on S3 map + S5 personas
7. S8 (Pricing)             — depends on S7 GTM
8. S9 (AI Roadmap)          — depends on S4 phased plan + S1 Ironclad principle 6
9. S10 (KPIs)               — depends on S4 capabilities + S8 pricing
10. S11 (Risks)             — depends on S3 market + S4 technical + S7 GTM
11. S1 (Metadata)           — written last to stamp correct version + copy tables
```

---

## Cross-Section Consistency Constraints

| Constraint | Sections | Rule |
|-----------|---------|------|
| Module names | S4, S5 | Must match Descripcion General exactly (8 modules) |
| Persona roles | S5, S6, S7 | Same 5 roles used consistently, no new personas added |
| Phase assignment | S4, S9 | AI = Phase 4; WSLPG = Phase 2; AI cannot appear in Phase 1 |
| AGIS client count | S3 | Must use "2,000+ acopio clients" not "3,000+" |
| Pricing figures | S8, S10 | $90/seat/month → ARPU $360 (4 seats) are internally consistent |
| Research citations | ALL | Every market claim cites [Research X.Y]; no unverified statistics |
| Language | ALL | Spanish domain terms on first use with English translation |
