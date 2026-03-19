# Research: Acopio de Granos Product Vision & Scope

**Phase 0 output for**: `specs/001-acopio-vision/plan.md`
**All facts below are RAG-verified** (queries run 2026-03-15 against `acopio_research` collection)
**Sources**: Research documents 4.1, 4.2, 4.3, 6.1, 6.2, 6.3, 9.1

---

## Decision Log

### D-001: Vertical Commitment
- **Decision**: Acopio de granos is the committed vertical — not "under evaluation"
- **Rationale**: Team resources (2 devs) cannot sustain horizontal ERP against SAP/Odoo; acopio offers highest ARPU, regulatory moat (ARCA/SISA/WSLPG), and no cloud-native competitor in the operational-depth segment
- **Alternatives considered**: Beverage distributors (30% new code gap, no regulatory moat), hardware stores (high market fragmentation), meat processors (dual SENASA+ARCA compliance doubles regulatory complexity)

### D-002: Primary Competitive Moat
- **Decision**: Offline-first architecture leads all differentiation messaging
- **Rationale**: Cloud resistance is the #1 adoption barrier (connectivity dependence cited by 44% of operators reporting "regular" connectivity, INTA AgroActiva 2022). Every incumbent is either desktop-only or pure cloud — no one occupies offline-first + cloud-native + acopio-depth simultaneously
- **Alternatives considered**: Regulatory automation as lead (valid, but offline-first is more visible to buyers and harder for incumbents to copy)

### D-003: Pricing Model
- **Decision**: Per-seat USD-indexed model at $90/seat/month (annual: $75/seat)
- **Rationale**: Incumbents charge per-establishment ($500-800/month regardless of user count). Per-seat disrupts this — small acopio with 2 users pays ~$180 vs incumbent $500+. USD-indexed protects against ARS devaluation (buyer budget is mental USD anyway given grain pricing in USD)
- **Alternatives considered**: Per-establishment pricing (matches incumbent expectations but sacrifices disruptive positioning); flat monthly (unpredictable ARPU scaling)

### D-004: MVP Scope
- **Decision**: Romaneo-to-Position loop (reception → quality → merma → storage → producer account)
- **Rationale**: This is the daily operational core — every truck that arrives must go through this loop. It generates the most data for downstream AI features and immediately demonstrates value to the balancero and laboratorista personas
- **Alternatives considered**: Liquidaciones first (high value but complex regulatory surface), full module set (too broad for MVP validation)

### D-005: Geographic Beachhead
- **Decision**: Villa María, Córdoba first
- **Rationale**: Founder's base (direct relationship access), Sociedad de Acopiadores de Córdoba HQ in Villa María corridor, Córdoba has worst storage deficit vs production (San Francisco area: 4x production vs capacity), 81 Federación members in Córdoba
- **Risk acknowledged**: Villa María is also AGIS's home base (founded there ~1985, 2,000+ clients). This is both a risk and validation signal — if AGIS clients are dissatisfied, they're the easiest to convert with a modern alternative
- **Alternatives considered**: Rosario (larger market but Algoritmo stronghold); Buenos Aires (larger but less acopio concentration)

### D-006: Distribution Channel
- **Decision**: Contador rural free portal as primary channel
- **Rationale**: Contador is "key advisor" participating in systemization decisions (not just tax). Each agro-specialized estudio has 5-15 acopio/cooperative/contractor clients. Free portal that saves contadores time on spreadsheet/email exchange creates strong referral incentive. Mirrors Xubio/Colppy model proven effective in Argentine SMB market
- **Alternatives considered**: Direct sales (viable but expensive at this stage); trade association sponsorship (high-cost, long sales cycle)

### D-007: Architecture Pattern
- **Decision**: Approach B — new `apps/acopio/` + `apps/cuentas/` alongside existing infrastructure
- **Rationale**: Preserves all 9 Rust modules, 2,500+ tests, and proven auth/sync/ARCA foundation. Grain operations are fundamentally different from generic retail — separate apps avoid polluting existing models. Dual inventory (grain continuous kg + insumos discrete units) requires new data layer
- **Alternatives considered**: Approach A (extend existing apps) — rejected because grain data model (romaneo, merma, cubicaje) has no common base with retail inventory

---

## Section-by-Section Research Facts

### Section 1: Document Metadata
**Source**: v0.4 document (copy/adapt)
**Verified facts**:
- Current version: 0.4, date 2026-03-01 → New: 1.0, date 2026-03-15
- Implementation Progress table (lines 13-28 of v0.4) **copy verbatim** — metrics still accurate:
  - Backend Core ✅ Complete (Auth, Inventory, Ventas, ARCA, Sync)
  - Rust/PyO3 ✅ Complete (9 modules)
  - 2,500+ tests | 79 API paths | 9 OpenAPI contracts | 9 Rust modules
  - Python 3.14.3, Django 5.2.x, DRF, PostgreSQL 18.1, Rust 1.93.1 (PyO3 0.28)

### Section 2: Strategic Purpose

**Vision statement draft** (replace "Transform traditional SMB retailers..."):
> "Empower independent Argentine grain operators (acopiadores de granos) with the first cloud-native, offline-first ERP purpose-built for grain stockpiling operations — delivering automatic regulatory compliance, real-time grain position visibility, and enterprise-grade security to the small-to-medium acopiador who has been historically underserved by desktop-era software."

**Ironclad principles** (from v0.4, lines 124-129 — adapt wording, preserve intent):
1. Pragmatic Offline-First: offline is the base architecture, not a fallback mode
2. Transactional Integrity (Ledger): no UPDATE on grain movements, only INSERT contra-entries
3. Encapsulated Complexity: balancero sees "Green = Approved" not "CTG Issued via WSLPG"
4. Enterprise Security for SMBs: RLS, AES-256-GCM, audit — corporate-grade for grain operators

**NEW principles to add**:
5. Regulatory Automation: CPE/CTG, C-1116, SISA registrations happen automatically — operators don't manage compliance, they manage grain
6. AI-Ready Data Architecture: every weighing, every quality grade, every storage movement is structured data first — enabling ML features in Phase 4 without data migration

### Section 3: Market Context

**3.1 Market Sizing** [Research 6.1]
- TAM: ~1,259 acopiador-consignatario enterprises, ~2,458 storage plants nationwide
- SAM: ~1,073 private (non-cooperative), ~1,622 plants (~68% of total plants); 24 Mt combined capacity (30-32% of national 75-80 Mt)
- SOM initial: Córdoba (81 Federación members) + Santa Fe (58 members) = 139 targets
- Size distribution: 60% small (<20K tons), 32% medium (20K-80K), 8% large (>80K)
- Provincial breakdown: BA ~40% of plants, SF largest capacity ~14.8Mt, CBA ~5.5Mt, ER ~2.1Mt, LP ~1.2Mt
- Federación members: 96 BA, 81 CBA, 58 SF, 27 ER
- Average: 2.15 plants/company, 31,800 tons avg capacity/plant

**3.2 Competitive Landscape** [Research 4.1, 4.2]

Specialized desktop vendors:
| Competitor | Founded | Location | Platform | Clients | Key Weakness |
|-----------|---------|----------|----------|---------|-------------|
| Algoritmo | 1985 | Rosario, SF | Desktop + Silohub overlay | ~125 acopio | No native cloud; 2-platform cost |
| AGIS (AmericaGIS) | ~1985 | Villa María, CBA | VB6/.NET desktop | 2,000+ acopio | 3 fragmented stacks; VB6 EOL 2008 |
| Physis | ~1988 | CABA/Rosario | Desktop Windows | Unknown | No web/mobile/cloud |
| AgroAcopio | 1983 | Buenos Aires | Desktop | Unknown | Oldest tech stack |
| Agrosistemas | 1990 | Mar del Plata | Desktop | Unknown | Desktop-only despite ISO cert |
| Gestagro/Kernel | 1988 | Rosario | Desktop + Android | Unknown | Coop-focused only |
| Siscoop | 1986 | Bahía Blanca | Desktop + partial web | Unknown | Coop-focused only |
| Informática Tandil | Unknown | Tandil | Desktop | Unknown | Regional, limited reach |
| SYNAgro | Unknown | Unknown | On-premise + consulting | Unknown | 1-year minimum implementation |

Cloud/SaaS with no acopio-depth:
| Competitor | Founded | Location | Platform | Clients | Key Weakness |
|-----------|---------|----------|----------|---------|-------------|
| Finnegans GO Granos | 1992 | Buenos Aires | Cloud SaaS (AWS) | ~1,500 agro total | Enterprise-tier pricing; lacks operational depth |
| Versat ERP Agro | Unknown | Unknown | Cloud SaaS | Unknown | Not acopio-specific; USD 200-640/month |
| Albor Campo | Unknown | Mar del Plata | Cloud SaaS | 4,000+ users | Farm-focused, not acopio |

Government mandatory systems (must integrate, not compete):
- SIO Granos (grain buy/sell registration)
- SISA / Registro Sistémico (RG 5689/2025 — 24h grain movement registration)
- BolsaTech (soy technology commercialization)

Market segmentation [Research 4.1]:
- 10-15% large acopios + coops → full specialized ERP (Algoritmo, Finnegans, SAP)
- 20-30% medium → specialized desktop (AGIS, Physis, AgroAcopio, Agrosistemas)
- 25-35% small → generic ERP + Excel (Tango/Bejerman + spreadsheets)
- 20-30% small → primarily Excel/manual + AFIP web portals

**GRAVITEA unique position**: cloud-native + offline-first + acopio-operational-depth = combination no incumbent offers

**3.4 Pain Points** [Research 4.3]
1. **Regulatory compliance**: CPE/CTG real-time since 2021; C-1116 (A/B/C/RT) via WSLPG (RG 3419/2012, RG 3690/2014, RG 3691/2014); SISA RG 5689/2025 (24h, sanctions = no Cartas de Porte); RG 5821/2026 (CPE linked to SISA status); RUCA eliminated 2025 → migrated to SISA
2. **Tax withholdings**: IVA 8% (RG 4310/2018 + RG 2300; refund delays > 12 months; ARS 500K-1.5M trapped/producer); Ganancias 2-15% (RG 2118/2006); IIBB by province; SICORE magnetic files — all calculated per liquidación simultaneously
3. **Inventory reconciliation**: cubicaje, grain position (comprado vs vendido), overselling risk; auditing vs CTG + 1116 certs + LPGs + ARCA Systemic Register
4. **Producer account disputes**: quality grading (bonificaciones/rebajas), conditioning costs (secado, zarandeo, fumigación), settlement timing ("a fijar" operations); grain loses physical identity at entry
5. **Manual data entry**: weighbridge transcription errors; peak harvest = hundreds of trucks/day; 7/10 implementations fail from poor process alignment not technology [Albor Agtech]
6. **Connectivity**: 40.2% rural parajes have no internet (INTA/ENACOM 2021); 44% report only "regular" connectivity; nuance: acopio plants are in small towns (better than remote fields), but brief outages halt CTG/SISA operations during harvest

**Technology adoption** [Research 4.3]:
- 92% of ag sector uses apps/platforms; 65% use digital platforms
- Smartphone penetration: 62.1M connections, 97% 4G — WhatsApp is de facto management tool
- Cloud resistance: connectivity dependence (on-premise needs internet only for ARCA filings; cloud needs it for everything)
- Generational shift: younger operators more tech-friendly (ACA Jóvenes), older hold decision authority
- Typical IT setup: 1-2 shared PCs, Windows desktop, electronic scale, sometimes connected to weighbridge

**Buying behavior** [Research 4.3 Section 6]:
- Decision-maker: Owner + Accountant (dual influence)
- Budget: USD 150-500/month
- Switching barrier #1: data migration (decades of accumulated data)
- Optimal switching window: April-June (post-soybean harvest)

### Section 4: Product Vision

**Module map** (from Descripción General del Producto.md — use these exact names):
- RECEPCIÓN (Romaneo): truck entry, CPE/CTG, gross weight, calado, quality analysis, merma calc, net weight conforme, boleta de romaneo
- ALMACENAMIENTO: silos/cells with capacity and state; assignment by type/quality/campaign; grain position (what/where/whose); campaign management; inter-silo movements
- CALIDAD: tolerance tables (Cámara Arbitral de Rosario); bonificaciones/rebajas; merma tables for drying; plant-configurable parameters
- CUENTAS CORRIENTES: producer account (saldo granos kg + pesos + dollars); movement history; extractos
- LIQUIDACIONES: Liquidación Primaria (1116-C), Secundaria (1116-B); retentions (IVA, Ganancias, IIBB); ARCA integration (WSLPG); SISA status; price per ton/quintal
- FACTURACIÓN: electronic invoices A/B/C; plant services (secada, zarandeo, almacenaje, paritaria); credit/debit notes; CAE/CAEA (offline mode)
- AGRONOMÍA (Insumos): input catalog (seeds, fertilizers, agroquímicos, repuestos); stock by lot/expiry; purchases from distributors; sales to producers; price lists
- CANJE: grain-for-input exchange; automatic compensation (grain credit at pizarra price vs input debit); fiscal documentation

**Core operational flow** (from Descripción General ASCII → convert to Mermaid):
Arrival (CPE/CTG) → Gross weight (balanza) → Calado y muestreo → Quality analysis (lab) → Merma calc → Net weight conforme → Boleta de Romaneo → [Silo assignment] + [Producer account credit] → [Liquidación (1116-C)] or [Canje por insumos]

**Dual inventory** (from Descripción General):
- Grain (activo líquido): continuous, measured in kg; stock derived from romaneo net weight adjusted by quality/campaign/merma; segregated by grain type, quality grade, and campaign year
- Insumos (activo contable): discrete, measured in units; N units in/N units out; lot control + barcode + expiry date

**Technical differentiators** (in order — offline-first LEADS):
1. Offline-first hybrid architecture (operates without internet; syncs when connectivity restores)
2. Rust acceleration layer (merma engine, grading calculations — 2-9x speedups via PyO3)
3. PostgreSQL RLS multi-tenancy (plant-level isolation, physically impossible cross-tenant access)
4. ARCA direct integration (WSAA/WSFEv1/WSLPG — CAE online + CAEA offline)
5. AI-ready data architecture (structured capture enables Phase 4 ML without data migration)
6. Field-level encryption (AES-256-GCM for PII — producer data, certificate data)

**Out of scope (what we don't build)**:
- Generic POS / retail cash register
- B2C e-commerce
- Manufacturing / industrial processes
- Field agriculture (farm management, precision agriculture, soil testing)
- Last-mile logistics / truck fleet management
- Payroll / HR

### Section 5: Personas

5 personas with JTBD (grain-specific):

| Persona | Role | Primary JTBD | Key Pain | Tech Comfort |
|---------|------|-------------|----------|-------------|
| Dueño/Gerente | Owner/Manager | Remote grain position + financial control from phone | Can't see grain inventory without being physically present | Medium-high (smartphone) |
| Balancero/Recibidor | Weighbridge operator | Complete a truck reception in < 5 minutes without system waiting | Manual transcription errors during harvest peak | Medium (Windows desktop) |
| Laboratorista | Lab analyst | Grade samples and calculate merma without spreadsheets | Quality disputes with producers due to manual calculation errors | Medium (desktop tools) |
| Administrador/Contable | Admin/accountant | File all regulatory documents automatically | 3+ hours/day on ARCA/SISA compliance; ARS 500K trapped in IVA refunds | Medium-high (AFIP portals) |
| Contador Rural | External accountant | Real-time multi-client fiscal visibility | Chasing Excel files from 5-15 acopio clients by email | High (cloud tools) |

**ICP**: Independent (non-cooperative) acopiador, 1-5 plants, Pampas region, small-medium capacity, currently using desktop software or generic ERP + Excel, experiencing generational transition.

### Sections 7-8: GTM + Pricing

**Contador rural channel** [Research 6.2]:
- 5-15 acopio/cooperative/contractor clients per agro-specialized estudio
- 20-50 total agricultural clients per estudio (mostly farms, subset are acopios)
- Contador is "key advisor" for financing, investment, and systemization decisions
- Free portal value props: real-time transactions, automated books, multi-client dashboard, one-click exports
- "Invitar a tu contador" referral flow → contadores recommend the ERP that saves them time
- Target: FACPCE seminars (RT 22, RT 41), CPCE Córdoba agro events

**Trade events** [Research 6.3]:
- Tier 1: Federación de Acopiadores de Cereales; A Todo Trigo (May 2026, Mar del Plata); Sociedad de Acopiadores de Córdoba (Villa María corridor)
- Tier 2: Grano SAC/Expo Poscosecha (Rosario, November); ExpoAgro; AgroActiva
- Networking: Federación working-commission meetings; BCCBA member events

**Switching strategy**:
- April-June window (post-soybean harvest — lowest operational intensity)
- Migration tools from AGIS/Physis/Excel (structured data import) — reduces #1 switching barrier
- ACA Jóvenes networks (generational transition targeting)

**Pricing** [Engram business panel + Research 4.3]:
- $90/seat/month USD-indexed (annual: $75/seat)
- Disruption vs incumbents: small acopio 2 users = ~$180/month vs incumbent $500-800/establishment
- Free accountant portal (mirrors Xubio/Colppy model)
- Versat reference: USD 200-640/month (no acopio-depth)
- Incumbent pricing: not publicly disclosed; custom quotes; est. $500-800/establishment/month

### Section 9: AI Differentiation

6 capabilities from Research 9.1 (all Phase 3-4, not MVP):

| Capability | Model Architecture | Expected Outcome |
|-----------|-------------------|-----------------|
| Quality degradation prediction | 3D-CNN + LSTM | 97.38% classification accuracy |
| Silo assignment optimization | MILP (Mixed Integer Linear Programming) | 27% reduction in truck queue times |
| Price forecasting (Matba Rofex) | VMD-SGMD-LSTM | Grain futures price prediction |
| Price forecasting (local basis) | XGBoost | Local pizarra basis prediction |
| Weighbridge fraud detection | Anomaly detection on weight patterns | Alert on suspicious weight variance |
| Document intelligence | OCR (Carta de Porte) | Automatic CPE data extraction |
| Predictive aeration scheduling | SVM-Poly | 99.98% efficiency classification |

### Section 10: KPIs

Operational:
- Harvest throughput: trucks processed per hour per balancero (target: > 10/hour vs manual 4-6/hour)
- Sync latency: critical data propagation to all plants < 60 seconds
- System uptime: 99.5%+ (offline mode ensures local availability even during cloud outages)

Adoption:
- Balancero onboarding time: < 1 day from zero to processing first romaneo
- Active user rate: > 80% of provisioned users active within 30 days of onboarding

Business:
- Stock discrepancy rate: < 2% after 3 months (vs 10-15% industry standard with manual tracking)
- Regulatory compliance rate: CTG/LPG successfully filed > 99.5% of attempts
- ARPU growth: target $360/month/tenant (4 seats at $90) in Year 1

### Section 11: Risk and Mitigation

| Risk | Severity | Mitigation |
|------|---------|-----------|
| Connectivity gaps during harvest | High | Offline-first architecture — primary competitive moat; all daily ops work without internet |
| Regulatory change velocity (ARCA/SISA) | High | Modular ARCA integration; Rust acceleration enables fast compliance updates |
| Competitor response (Algoritmo + Silohub) | Medium | First-mover in cloud+offline+depth combo; faster iteration than desktop incumbents |
| Adoption resistance (generational divide) | Medium | Target younger operators (ACA Jóvenes); contador channel provides trusted third-party advocacy |
| Data migration barrier (#1 switching barrier) | High | Structured import tools from AGIS/Physis/Excel; April-June window for low-risk migration |
| 7/10 implementation failure rate | High | Process-first onboarding (not technology-first); contador as built-in training advocate; white-glove onboarding for first 10 clients |

---

## All NEEDS CLARIFICATION Resolved

No items required clarification (spec.md had 0 [NEEDS CLARIFICATION] markers). All research
findings above come directly from RAG-verified corpus data and established architectural decisions.
