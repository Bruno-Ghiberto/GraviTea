# Spec 01: Product Vision & Scope -- Specification Context

## Feature Description

Rewrite the `Docs/Project Blueprint/Product Vision & Scope.md`
document from a generic horizontal ERP vision (v0.4) to a fully
committed **acopio de granos vertical SaaS** vision document. The
current document still references generic retail (hardware stores,
beverage distributors, cashiers) and frames the vertical pivot as
"under evaluation." The new version declares the acopio vertical
as the definitive direction and builds a complete strategic narrative.

The rewritten document is the **NORTH STAR** for all downstream
specs. Every PRD requirement (spec-02), data model decision
(spec-03), and implementation spec (09-12+) must trace its
strategic justification back to this document.

## Current State (what exists)

The existing Product Vision doc (v0.4, 2026-03-01) contains:

- **Status**: "Research Phase — Evaluating Vertical SaaS Pivot" -- CHANGE to committed
- **Vision statement**: Generic retail ("Transform traditional SMB retailers...") -- REPLACE
- **Positioning map**: Cloud vs Offline generic quadrant -- ADAPT for acopio
- **Pain points**: Generic retail (network fragility, stock blindness, price chaos) -- REPLACE with acopiador-specific pains
- **ICP**: Lists 4 candidate verticals still under evaluation -- REPLACE with committed acopio ICP
- **Personas**: Cashier, Owner, Logistics, Accountant (generic) -- REPLACE with Dueño, Balancero, Laboratorista, Admin, Contador Rural
- **MVP scope table**: 16 generic modules -- REPLACE with acopio module map
- **Section 6.4 Feature Branch History**: 001-025 branches -- PRESERVE and update
- **KPIs**: Generic retail metrics -- REPLACE with acopio-specific KPIs
- **Mermaid diagrams**: Present but generic -- REPLACE with acopio-specific diagrams

Also reference `Docs/Project Blueprint/Descripcion General del Producto.md`
which already contains the acopio-specific module map, operational flow,
and dual inventory architecture in Spanish.

## Research Inputs

### RAG Queries (run these FIRST -- do NOT read full research files)

Use the RAG pipeline to gather domain knowledge. Run these queries
BEFORE reading any research files directly:

```bash
.venv/bin/python scripts/qdrant/qdrant_search.py -q "QUERY" -l 5
```

Queries to run:
- "acopio software market competitors Algoritmo AGIS Physis"
- "acopiador pain points regulatory compliance CTG SISA" (`-c acopio_research` required)
- "market sizing geographic distribution acopiadores provinces"
- "AGIS AmericaGIS competitive analysis technology VB6 desktop"
- "acopiador technology adoption cloud versus desktop on-premise"
- "accountant contador rural channel strategy grain operations"
- "AI machine learning grain storage silo prediction optimization"
- "trade associations industry events Expoagro acopiadores"
- "acopio pricing revenue model SaaS grain management"
- "offline connectivity rural areas grain operations argentina"

### Source Documents (for reference -- prefer RAG results above)

Only read specific sections if RAG results are insufficient:

| Doc ID | Relevant Sections |
|--------|------------------|
| 4.1 | Executive Summary, Market Context, all 6+ vendor profiles (Algoritmo, AGIS, Physis, AgroAcopio, Kernel, Versat) |
| 4.2 | Executive Summary, Company Profile, Product Suite, Technology Stack, SWOT, Strategic Vulnerabilities |
| 4.3 | Executive Summary, Sections 2.1-2.6 (pain points), Sections 3.1-3.4 (technology adoption), Section 4 (buying behavior) |
| 6.1 | Total Number of Acopiadores, Geographic Distribution, Size Distribution, Consolidation Trends |
| 6.2 | Channel strategy, contador rural role, free portal model |
| 6.3 | Federacion de Acopiadores, Expoagro, regional associations |
| 9.1 | Introduction, Quality Degradation Prediction, Silo Assignment, Price Forecasting, Fraud Detection, Document Intelligence |

### Critical Domain Facts

**Market size (from 6.1)** [RAG-verified]:
- Total registered: ~1,259 acopiador-consignatario enterprises, ~2,458 storage plants nationwide
- ~1,073 private (non-cooperative) acopiadores operating ~1,622 plants (~68% of total plants)
- ~155 cooperatives with ~476-701 plants (ACA alone: 25Mt in 2024/25 campaign)
- ~950 Federacion member companies representing USD 3B investment, 40% of interior storage, serving 70% of producers
- Private sector combined capacity: ~24 Mt (30-32% of national commercial fixed storage of 75-80 Mt)
- Size: 60% small (<20K tons), 32% medium (20K-80K), 8% large (>80K)
- 88% of plants in Pampas region (BA ~40% of plants, SF largest capacity ~14.8Mt, CBA ~5.5Mt, ER ~2.1Mt, LP ~1.2Mt)
- Average 2.15 plants per company, 31,800 tons avg capacity per plant
- Provincial breakdown: Buenos Aires 96 Federacion members, Cordoba 81, Santa Fe 58, Entre Rios 27
- Cordoba: worst storage deficit vs production (San Francisco area: 4x production vs capacity)
- Bruno is based in Villa Maria, Cordoba -- epicenter of AGIS territory

**Competitive landscape (from 4.1, 4.2)** [RAG-verified]:

Specialized acopio vendors (all desktop-first):
- Algoritmo (Rosario, ~50 employees): ~125 clients, 20Mt through system, desktop ERP, market leader by volume. 2022 Silohub alliance adds web/mobile layer WITHOUT replacing desktop core [4.1]
- AGIS (Villa Maria, 11-50 employees): 3,000+ total claims across ALL product lines (GPS, generic ERP, acopio). Fragmented tech: VB6/SQL Server (acopio) + Grails/PostGIS (GPS) + Odoo 13/PostgreSQL (generic ERP) -- 3 entirely separate systems, no shared codebase. VB6 is EOL since 2008; Odoo 13 out of support since Oct 2022. Personal Gmail as Play Store developer contact [4.2]
- Physis (CABA/Rosario, ~35 years): Most feature-detailed acopio system (futures/options module, agroinsumos, full AFIP connectivity), desktop Windows only, limited online presence [4.1]
- AgroAcopio (Buenos Aires, since 1983): Desktop, automatic scale reading, CTG integration, advanced contract management [4.1]
- Agrosistemas (Mar del Plata, 1990, 11-50 employees): Desktop, ISO 9001:2015 (Bureau Veritas), CTG/LPG/LSG/COT integration, "AI planned for next version" [4.1]
- Gestagro/Kernel (Rosario, 1988): Desktop + mobile app, web portal, coop-focused [4.1]
- Siscoop (Bahia Blanca, 1986): Desktop + partial web, mobile app, coop-focused [4.1]

Cloud/SaaS entrants (none with acopio-depth):
- Finnegans GO Granos (Buenos Aires, 1992): Cloud SaaS on AWS, ~1,500 agro clients total, FinnApp Agro mobile -- closest to a cloud competitor but targets large acopios and lacks the operational depth of desktop incumbents [4.1]
- Versat ERP Agro: Cloud SaaS, USD 200-640/month, 20% annual discount, multi-module -- but NOT acopio-specific depth [4.1]
- Albor Campo: Online platform, 4,000+ users, farm-focused not acopio [4.1]

Key competitive insight: NO incumbent combines cloud-native + offline-first + acopio-operational-depth. Finnegans is cloud but enterprise-tier; desktop vendors have depth but no cloud/mobile.

Market segmentation (estimated from 4.1):
- 10-15% large acopios + coops → full specialized ERP (Algoritmo, Finnegans, SAP)
- 20-30% medium acopios → specialized desktop (AGIS, Physis, AgroAcopio, Agrosistemas)
- 25-35% small acopios → generic ERP + Excel (Tango/Bejerman + spreadsheets)
- 20-30% small acopios → primarily Excel/manual + AFIP web portals directly

7 out of 10 agro software implementations fail within 3 years -- not technology, but poor process alignment and insufficient training (Albor Agtech) [4.3]

**Pain points (from 4.3)** [RAG-verified]:
1. Regulatory compliance burden: CPE/CTG (real-time, needs internet since 2021), C-1116 forms (A/B/C/RT via WSLPG), SISA RG 5689/2025 (24h mandatory registration of grain entries/exits, sanctions = inability to issue Cartas de Porte), RG 5821/2026 (CPE authorization linked to SISA status and plant activation). RUCA eliminated in 2025, data migrated to SISA -- another transition to manage [4.3 s2.1]
2. Complex tax withholdings: IVA retention 8% (RG 2300, 7% theoretically refunded by ARCA within 60 days but delays exceed 12 months; ARS 500K-1.5M trapped per mid-size producer), Ganancias 2-15% (RG 4325), IIBB by province, SICORE magnetic files -- all calculated per liquidacion simultaneously [4.3 s2.2]
3. Physical vs book inventory reconciliation: cubicaje, overselling risk ("sold more grain than physically held"), grain position tracking (comprado vs vendido) across multiple grains and plants. Auditing requires comparison against CTG, 1116 certificates, LPGs, and ARCA Systemic Register [4.3 s2.3]
4. Producer account disputes: quality grading (bonificaciones/rebajas), conditioning cost allocation (drying, screening, fumigation, volatile shrinkage), settlement timing on "a fijar" operations. Grain loses physical identity upon entry -- producer owns "equivalent in quality and quantity" not their specific grain [4.3 s2.4]
5. Manual data entry and fragmented systems: weighbridge-to-system transcription errors (some software reads electronic scales, many don't), peak harvest chaos (hundreds of trucks/day). 7/10 implementations fail from poor process alignment, not technology [4.3 s2.5]
6. Connectivity: 40.2% of rural parajes have no internet (INTA/ENACOM 2021, 311 localities, 21 provinces); 44% report only "regular" connectivity (INTA AgroActiva 2022); urban-rural gap up to 70% (IICA 2023). IMPORTANT nuance: acopio facilities are in small towns, not remote fields -- better than pure field, but brief outages during harvest halt CTG/SISA operations [4.3 s2.6]

**Technology adoption (from 4.3)** [RAG-verified]:
- 92% of ag sector uses apps/platforms (skewed to Pampas); 65% use digital platforms/apps, 17% mobile only [4.3 s3.1]
- 84% of Pampa Humeda producers believe digital tech will change their business in next 5 years (Universidad Austral 2024) [4.3 s3.1]
- Smartphone penetration high (62.1M mobile connections, 135% coverage, 97% 4G), WhatsApp is de facto management tool -- government advisory: "WhatsApp is not sufficient as a management system" [4.3 s3.2]
- Cloud resistance factors: (a) connectivity dependence (on-premise only needs internet for ARCA filings, cloud needs it for everything), (b) data sovereignty concerns (sensitive commercial info), (c) switching cost from decades of accumulated data [4.3 s3.3]
- Typical IT: 1-2 shared PCs, Windows desktop software, electronic scale, sometimes connected to weighbridge [4.3 s3.4]
- Clear generational shift: younger operators more tech-friendly, "ACA Jovenes" movement, but older generation holds decision-making authority [4.3 s3.5]

**Buying behavior (from 4.3 Section 6)** [RAG-verified -- NEW]:
- Software decision-maker: Owner + Accountant (dual influence)
- Typical budget: estimated USD 150-500/month
- Switching barrier #1: data migration (decades of accumulated data)
- Optimal switching window: post-soybean harvest (April-June)
- Migration tools from AGIS/Physis/Excel would dramatically lower adoption barrier

**Strategic implications for new entrants (from 4.3 Section 6)** [RAG-verified -- NEW]:
1. "Hybrid architecture wins" -- offline + cloud sync addresses #1 infrastructure concern
2. "Accountant channel is critical" -- make the external contador an ally
3. "Regulatory compliance is table stakes" -- fastest to ship compliant update wins trust
4. "Weighbridge integration is a quick win" -- automates major daily pain point
5. "Migration tools reduce switching friction" -- structured import from competitors
6. "Target the generational transition" -- market to younger family members and ACA Jovenes networks

**Pricing (from Engram business panel + 4.3 research)** [RAG-enriched]:
- Research-derived typical budget: USD 150-500/month per acopio [4.3 s6]
- Engram panel consensus: $90/seat/month USD-indexed with annual discount to $75/seat
- Sweet spot: $80-120/seat/month USD-indexed (panel range)
- Free accountant portal (distribution channel flywheel -- mirrors Xubio/Colppy model [6.2])
- Cloud reference pricing: Versat ERP Agro USD 200-640/month, 20% annual discount [4.1]
- Incumbents charge $500-800/month per establishment (not per seat)
- Key insight: per-seat model disrupts per-establishment model -- small acopio with 2 users pays ~$180 vs $500+

**AI differentiation (from 9.1)**:
- Grain quality degradation: 3D-CNN + LSTM, 97.38% classification accuracy
- Silo assignment optimization: MILP, 27% reduction in truck queue times
- Price forecasting: VMD-SGMD-LSTM for Matba Rofex, XGBoost for local basis
- Weighbridge fraud detection: anomaly detection on weight patterns
- Document intelligence: OCR for Carta de Porte
- Predictive aeration scheduling: SVM-Poly, 99.98% efficiency classification

**Contador rural channel details (from 6.2)** [RAG-verified -- NEW]:
- Contador is "key advisor" in small/medium agro enterprises, participates in financing, investment, and systemization decisions -- not just tax [6.2]
- Rural estudio typically serves 5-15 acopio/cooperative/contractor clients alongside many pure producers [6.2]
- Free portal value props for contador: real-time client transactions, less spreadsheet/email exchange, automated books, centralized multi-client view, one-click exports [6.2]
- "invitar a tu contador" referral flows + tangible time savings = 10x distribution effect in dense grain regions [6.2]
- Target: FACPCE/Consejo-sponsored courses on agro topics (RT 22, RT 41), CPCE Cordoba agro events, "Herramientas para el contador agropecuario que trabaja con acopios" positioning [6.2]

**Trade associations and events (from 6.3)** [RAG-verified -- NEW]:
- Tier 1 (highest impact): Federacion de Acopiadores de Cereales (~1,000 companies), A Todo Trigo congress (May 2026, Mar del Plata -- sponsorship/exhibition), Sociedad de Acopiadores de Córdoba (Villa Maria corridor direct access) [6.3]
- Tier 2: Grano SAC / Expo Poscosecha (Rosario, November -- storage operations focus), ExpoAgro, AgroActiva [6.3]
- Networking: Federacion working-commission meetings, Sociedad Gremial de Rosario zonal meetings, BCCBA member events [6.3]
- Key regulatory contacts: RG AFIP 3691/2014 (electronic cert), RG 3419/2012 (LPG), RG 4310/2018 (IVA/SISA) [2.3]

**Strategic decisions (from Serena/Engram)**:
- Architecture: Approach B -- new apps/acopio/ + apps/cuentas/ alongside existing infrastructure
- MVP: Romaneo-to-Position loop
- Dual inventory: grain continuous (kg) + insumos discrete (units)
- WSLPG: extend apps/facturacion/ with wslpg/ subpackage
- Merma engine: Rust (merma.rs, grading.rs)
- GTM: contadores rurales network, free accountant portal, target April-June switching window (post-soybean harvest)
- Geographic focus: Villa Maria -> Cordoba -> Pampas

## Requirements

### Functional Requirements

FR-001: Define acopio-specific vision statement replacing generic retail vision
FR-002: Market analysis with quantified data -- TAM (all 1,259 operators + 2,458 plants), SAM (1,073 private acopiadores, 1,622 plants), SOM (Cordoba + Santa Fe initial target)
FR-003: Competitive positioning map showing Gravitea as only solution combining cloud-native + offline-first + acopio-operational-depth (Finnegans is cloud but lacks depth; desktop vendors have depth but no cloud/mobile)
FR-004: Individual profiles of top 6+ competitors (Algoritmo, AGIS, Physis, AgroAcopio, Finnegans GO Granos, Agrosistemas) with technology stack, client count, strengths, and weaknesses. Include market segmentation breakdown (4 tiers from 4.1)
FR-005: 5 acopio-specific user personas with distinct jobs-to-be-done:
  - Dueno/Gerente (owner/manager): remote visibility, grain position, financial control
  - Balancero/Recibidor (weighbridge operator): speed during harvest, offline resilience
  - Laboratorista (lab analyst): quality grading, tolerance tables, merma calculations
  - Administrador/Contable (admin/accountant): regulatory compliance, tax withholdings, C-1116 forms
  - Contador Rural (external accountant): multi-client oversight, fiscal compliance verification
FR-006: Value proposition canvas with acopiador-specific pains (regulatory, inventory reconciliation, producer disputes, connectivity) and gains (automatic compliance, real-time grain position, offline operations)
FR-007: MVP scope definition -- Romaneo-to-Position loop (reception, quality analysis, merma, storage assignment, producer account credit)
FR-008: Module map with 8 functional areas from Descripcion General: Recepcion (Romaneo), Almacenamiento, Calidad, Cuentas Corrientes, Liquidaciones, Facturacion, Agronomia (Insumos), Canje
FR-009: Technical differentiators section leading with offline-first as #1 moat, followed by: Rust acceleration, PostgreSQL RLS multi-tenancy, ARCA direct integration, AI-ready data architecture, field-level encryption
FR-010: AI differentiation roadmap with at least 6 AI capabilities from research 9.1 positioned as Phase 3-4 features
FR-011: Go-to-market strategy: contador rural channel (free portal = distribution flywheel, 5-15 acopio clients per estudio, "invitar a tu contador" referral flow), geographic beachhead (Villa Maria/Cordoba), trade events with specific venues (A Todo Trigo May 2026, Sociedad de Acopiadores de Cordoba, Grano SAC Rosario), target April-June switching window (post-soybean harvest)
FR-012: Pricing strategy: per-seat USD-indexed model ($90/seat/month), competitive vs incumbents ($500-800/month/establishment), free accountant portal
FR-013: Phased roadmap overview: Phase 1 (Romaneo + Position), Phase 2 (Liquidaciones + WSLPG), Phase 3 (Canje + Agronomia), Phase 4 (AI)
FR-014: Success metrics (KPIs) tailored to acopio: stock discrepancy reduction, regulatory compliance rate (CTG/LPG filed successfully), harvest throughput (trucks/hour), sync latency, onboarding time
FR-015: Risk and mitigation section (connectivity, regulatory changes, competitor response, adoption resistance, data migration barrier, 7/10 implementation failure rate)
FR-016: Preserve feature branch history table (001-025) showing existing infrastructure that carries forward
FR-017: Preserve and adapt "Ironclad" design guiding principles for acopio context (add: "Regulatory Automation", "AI-Ready Data Architecture")

### Non-Functional Requirements

NF-001: Document must be self-contained -- readable without other specs
NF-002: All market data must cite research document IDs (e.g., "[Research 6.1]")
NF-003: Use Mermaid diagrams for: competitive positioning map, module map, operational flow, persona hierarchy, phased roadmap
NF-004: Domain-specific Spanish terms used where appropriate (romaneo, merma, acopiador, cuenta corriente, liquidacion, canje) with English explanation on first use
NF-005: Consistent with `Docs/Project Blueprint/Descripcion General del Producto.md` module definitions and operational flow

## Target Document Structure

```
1. Document Metadata
   - Version 1.0, Status: Acopio Vertical -- Active Development
   - Owner, stakeholders, related docs

2. Strategic Purpose
   2.1 Vision Statement (acopio-specific)
   2.2 Design Guiding Principles (Ironclad adapted + Regulatory Automation + AI-Ready)

3. Market Context and Opportunity
   3.1 Market Sizing (TAM/SAM/SOM with real data from research 6.1)
   3.2 Competitive Landscape (Algoritmo, AGIS, Physis, AgroAcopio, Finnegans, Agrosistemas profiles + market segmentation tiers)
   3.3 Competitive Positioning Map (Mermaid: desktop vs cloud, generic vs acopio-depth)
   3.4 Pain Point Analysis (6 acopiador-specific pains from research 4.3)
   3.5 Value Proposition Canvas (Mermaid mindmap: pains/gains/solutions)

4. Product Vision
   4.1 What We Build (module map from Descripcion General)
   4.2 Core Operational Flow (truck arrival -> romaneo -> position)
   4.3 Dual Inventory Architecture (grain continuous + insumos discrete)
   4.4 Technical Differentiators (offline-first lead, Rust, RLS, ARCA, encryption)
   4.5 What We Don't Build (out-of-scope: generic POS, B2C, manufacturing, field ag)

5. Target Segment and Personas
   5.1 Ideal Customer Profile (independent acopiador, 1-5 plants, Pampas)
   5.2 User Personas (5 personas with JTBD)

6. Product Scope
   6.1 MVP v1: Romaneo-to-Position Loop (modules, features, acceptance)
   6.2 Phase 2: Liquidaciones + WSLPG Integration
   6.3 Phase 3: Canje + Agronomia
   6.4 Phase 4: AI Features
   6.5 Implementation Progress (existing infra that carries forward)
   6.6 Feature Branch History (preserve 001-025 table)

7. Go-to-Market Strategy
   7.1 Contador Rural Channel (free portal = distribution flywheel, 5-15 clients/estudio, referral flows)
   7.2 Geographic Beachhead (Villa Maria -> Cordoba -> Pampas)
   7.3 Trade Associations and Events (A Todo Trigo, Sociedad de Acopiadores CBA, Grano SAC)
   7.4 Switching Strategy (April-June window, migration tools from AGIS/Physis/Excel, generational targeting)

8. Pricing Strategy
   8.1 Per-seat USD-indexed model
   8.2 Free accountant portal
   8.3 Competitive analysis vs incumbents

9. AI Differentiation Roadmap
   9.1 Quality degradation prediction
   9.2 Silo assignment optimization
   9.3 Price forecasting (Matba Rofex + local basis)
   9.4 Weighbridge fraud detection
   9.5 Document intelligence (OCR Carta de Porte)
   9.6 Predictive aeration scheduling

10. Success Metrics (KPIs)
    10.1 Operational (harvest throughput, sync latency, uptime)
    10.2 Adoption (onboarding time, active users)
    10.3 Business (stock discrepancy, compliance rate, ARPU)

11. Risk and Mitigation
```

## Acceptance Criteria

AC-01: Vision statement explicitly mentions "acopio de granos" -- no generic retail language remains
AC-02: Competitive map includes at minimum Algoritmo, AGIS, Physis, AgroAcopio, Finnegans GO Granos, Agrosistemas with technology stacks + market segmentation tiers
AC-03: Market sizing uses quantified data from research 6.1 (cite source) with TAM/SAM/SOM breakdown
AC-04: 5 user personas with grain-specific jobs-to-be-done (not generic cashier/logistics)
AC-05: MVP scope is the Romaneo-to-Position loop (consistent with architectural decisions)
AC-06: AI section references at least 6 AI capabilities from research 9.1 with specific model architectures
AC-07: GTM section describes contador rural channel with free portal flywheel mechanism
AC-08: Pricing section includes per-seat USD-indexed model with specific price points
AC-09: Technical differentiators section leads with offline-first as primary moat
AC-10: No references to "hardware store", "beverage distributor", "cashier", or generic retail remain in the final document
AC-11: All 6 pain points from research 4.3 are represented (regulatory, tax, inventory, disputes, data entry, connectivity)
AC-12: Module map is consistent with Descripcion General del Producto.md
AC-13: Feature branch history (001-025) is preserved and updated
AC-14: At least 5 Mermaid diagrams (positioning, modules, flow, personas, roadmap)
AC-15: All market claims cite research document IDs

## Dependencies

- Depends on: **nothing** (spec-01 is the root of the dependency graph)
- Blocks: spec-02 (PRD), spec-07 (Roadmap), and transitively all downstream specs
- References:
  - Existing `Docs/Project Blueprint/Product Vision & Scope.md` (v0.4)
  - `Docs/Project Blueprint/Descripcion General del Producto.md` (acopio module map)
  - Research docs: 4.1, 4.2, 4.3, 6.1, 6.2, 6.3, 9.1
  - Engram: pricing decision ($90/seat), GTM strategy, competitor analysis notes
