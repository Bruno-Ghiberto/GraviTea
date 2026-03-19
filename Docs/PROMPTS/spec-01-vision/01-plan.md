# Spec 01: Product Vision & Scope -- Plan Context

## Overview

**Target deliverable**: `Docs/Project Blueprint/Product Vision & Scope.md` v1.0
**Replaces**: Same file, v0.4 (2026-03-01)
**Type**: Blueprint document (strategic, not code)
**Spec reference**: `specs/001-acopio-vision/spec.md`

This plan guides the rewrite of the Product Vision & Scope from a generic
horizontal ERP (v0.4) to a committed acopio de granos vertical SaaS document.
The output is a ~500-800 line Markdown file with 11 major sections, at least
5 Mermaid diagrams, and all market data cited to research sources.

---

## Content Guidelines

### Tone & Voice
- **Professional strategic document** -- not a sales pitch, not a technical manual
- Confident and declarative: "GRAVITEA is..." not "GRAVITEA could be..."
- No hedging language: eliminate "under evaluation", "considering", "potentially"
- Data-driven: every market claim has a `[Research X.Y]` citation
- Accessible to business stakeholders while credible to technical readers

### Audience
- **Primary**: Development team (needs to trace features back to strategy)
- **Secondary**: Product owner / founder (needs data for scope decisions)
- **Tertiary**: Investors / advisors (needs market opportunity assessment)
- **External stakeholders**: Potential partners, accountants (GTM channel)

### Language
- English is the primary language of the document
- Spanish domain terms used where they are the canonical industry terms:
  romaneo, merma, acopiador, cuenta corriente, liquidacion, canje,
  Carta de Porte, balancero, laboratorista, contador
- First occurrence of each Spanish term includes English translation in parentheses
- Example: "romaneo (weighing ticket)" on first use, then just "romaneo" after

### Level of Detail
- Market data: specific numbers with sources (no "many", "large", "significant")
- Competitor profiles: structured (location, tech stack, clients, strengths, weaknesses)
- Personas: narrative + JTBD format (not just bullet points)
- Module descriptions: 2-3 sentences per module with clear scope
- Mermaid diagrams: functional and renderable (test in a Markdown viewer)

---

## Existing Content: Preserve vs. Replace

### PRESERVE (adapt for acopio context)

| v0.4 Section | Lines | Action | Notes |
|-------------|-------|--------|-------|
| 1. Document Metadata table | 1-12 | **Adapt** | Update version to 1.0, status to "Acopio Vertical -- Active Development", date to current |
| Implementation Progress table | 13-28 | **Preserve as-is** | Current metrics accurate, shows carried-forward infrastructure |
| 4.2 Design Guiding Principles | 124-129 | **Adapt** | Keep all 4 Ironclad principles, ADD two new ones: "Regulatory Automation" and "AI-Ready Data Architecture" |
| 6.4 Feature Branch History | 238-261 | **Preserve as-is** | Full table of branches 001-025. Do NOT edit individual entries |
| Implementation Summary | 190-196 | **Preserve as-is** | Tech stack metrics still accurate |

### REPLACE (rewrite completely)

| v0.4 Section | Why Replace |
|-------------|-------------|
| 2. Strategic Purpose + Vision Statement | Generic retail "Transform traditional SMB retailers..." |
| 3.1 Positioning Map (Mermaid) | Generic cloud vs offline quadrant, not acopio-specific |
| 3.2 Pain Points mindmap (Mermaid) | Generic retail pains (internet outages, phantom stock, price chaos) |
| 3.3 Pain Point Analysis | Generic retail deep-dive |
| 4.1 Vision Statement | Generic retail quote |
| 5.1 ICP | Lists 4 candidate verticals "under evaluation" |
| 5.2 User Archetypes (Mermaid) | Cashier, Owner, Logistics, Accountant (generic) |
| 6.1 In-Scope Modules table | 16 generic modules (POS, Ventas, Electron, etc.) |
| 6.2 Functional Ecosystem (Mermaid) | Generic retail module relationships |
| 6.3 Out-of-Scope | Generic retail exclusions |
| 7. Success Metrics | Generic retail KPIs (cashier training, sales uptime) |
| "Strategic Inflection Point" box | References "under evaluation" / 4 candidates |

### NEW SECTIONS (do not exist in v0.4)

| New Section | Source |
|-------------|--------|
| 3.1 Market Sizing (TAM/SAM/SOM) | Research 6.1 + RAG |
| 3.2 Competitive Landscape (6+ profiles) | Research 4.1, 4.2 + RAG |
| 3.4 Pain Point Analysis (6 acopio pains) | Research 4.3 + RAG |
| 4.3 Dual Inventory Architecture | Descripcion General |
| 4.5 What We Don't Build | New (define negative scope) |
| 6.1-6.4 Phased scope (4 phases) | Architectural decisions |
| 7. Go-to-Market Strategy (4 subsections) | Research 6.2, 6.3 + RAG |
| 8. Pricing Strategy | Engram business panel + Research 4.3 |
| 9. AI Differentiation Roadmap (6 capabilities) | Research 9.1 |
| 10. Success Metrics (acopio KPIs) | Domain-specific |
| 11. Risk and Mitigation | Research 4.3 + domain |

---

## Section-by-Section Writing Plan

### Section 1: Document Metadata
**Effort**: Small (copy-adapt from v0.4)
**Source**: Existing v0.4 metadata table
**Action**:
- Copy metadata table structure from v0.4
- Update: Version 1.0, Status "Acopio Vertical -- Active Development", date 2026-03-15
- Keep Implementation Progress table exactly as-is (lines 13-28 of v0.4)
- Remove the "Strategic Inflection Point" box (lines 30-32) -- no longer evaluating

**RAG queries**: None needed

---

### Section 2: Strategic Purpose
**Effort**: Medium
**Source**: Existing principles (v0.4 lines 124-129) + domain decisions
**Action**:
- 2.1: Write new acopio-specific vision statement. Replace "Transform traditional SMB retailers..." with a grain-operations-focused statement. Must mention "acopio de granos" explicitly.
- 2.2: Preserve all 4 existing "Ironclad" principles:
  1. Pragmatic Offline-First
  2. Transactional Integrity (Ledger)
  3. Encapsulated Complexity
  4. Enterprise Security for SMBs
- ADD two new principles:
  5. Regulatory Automation (automatic compliance with ARCA/SISA/CTG/WSLPG)
  6. AI-Ready Data Architecture (structured data capture enabling future ML features)
- Adapt wording of existing principles for acopio context (e.g., "cashier" -> "balancero", "CAE" context becomes grain-specific WSLPG context)

**RAG queries**: None needed (internal strategic content)

---

### Section 3: Market Context and Opportunity
**Effort**: Large (most research-intensive section)
**Source**: Research 4.1, 4.2, 4.3, 6.1 + all RAG results
**Action**:

**3.1 Market Sizing (TAM/SAM/SOM)**
- TAM: ~1,259 acopiador-consignatario enterprises, ~2,458 storage plants [Research 6.1]
- SAM: ~1,073 private (non-cooperative) acopiadores, ~1,622 plants [Research 6.1]
- SOM: Cordoba (81 Federacion members) + Santa Fe (58 members) initial target [Research 6.1]
- Include size distribution: 60% small, 32% medium, 8% large
- Geographic concentration: 88% Pampas region
- Cordoba storage deficit note (San Francisco area: 4x production vs capacity)
- RAG query: `"market sizing geographic distribution acopiadores provinces"`

**3.2 Competitive Landscape**
- Individual competitor profiles in structured format (at minimum 6, corpus has 9):

| Competitor | Founded | Location | Tech | Clients | Distinction |
|-----------|---------|----------|------|---------|-------------|
| Algoritmo | 1985 | Rosario | Desktop + Silohub overlay | ~125 acopio | "Most widespread ERP", 20M+ tons |
| AGIS (AmericaGIS) | ~1985 | Villa María | VB6/.NET desktop | 2,000+ acopio [Research 4.2] | Fragmented: 3 separate stacks |
| Physis | ~1988 | CABA/Rosario | Desktop Windows | Unknown | Most feature-complete (futures, agroinsumos) |
| AgroAcopio (AEA&A) | 1983 | Buenos Aires | Desktop | Unknown | Longest-running, automatic scale reading |
| Agrosistemas | 1990 | Mar del Plata | Desktop | Unknown | ISO 9001:2015, CTG/LPG/LSG/COT, "AI planned" |
| Gestagro/Kernel | 1988 | Rosario | Desktop + Android app | Unknown | Coop-focused, web portal |
| Siscoop | 1986 | Bahía Blanca | Desktop + partial web | Unknown | Coop-focused, mobile app |
| Informática Tandil | Unknown | Tandil | Desktop | Unknown | Regional desktop vendor |
| SYNAgro | Unknown | Unknown | On-premise + consulting | Unknown | 1-year minimum implementation [Research 4.3] |
| Finnegans GO Granos | 1992 | Buenos Aires | Cloud SaaS (AWS) | ~1,500 agro total | Only cloud competitor; enterprise-tier pricing |
| Versat ERP Agro | Unknown | Unknown | Cloud SaaS | Unknown | USD 200-640/month; not acopio-specific depth |

- **IMPORTANT**: Distinguish commercial software (competitors) from government mandatory systems
  (must integrate). Add a clear "Government & Mandatory Systems" box:
  - SIO Granos (Secretaría de Agricultura/CNV) — mandatory grain transaction registration
  - Registro Sistémico / SISA (ARCA, RG 5689/2025) — mandatory 24h grain movement registration
  - BolsaTech (BCCBA) — soy technology commercialization and royalty management
  These are **integration targets**, not competitors.

- 4-tier market segmentation breakdown (from Research 4.1)
- 7/10 implementation failure rate statistic (SYNAgro's 1-year minimum is an example of this pain)
- RAG queries:
  - `"acopio software market competitors Algoritmo AGIS Physis"`
  - `"AGIS AmericaGIS competitive analysis technology VB6 desktop"`

**3.3 Competitive Positioning Map (Mermaid)**
- NEW Mermaid diagram replacing v0.4's generic quadrant
- Axes: X = deployment model (Desktop-only ← → Cloud-native), Y = vertical depth (Generic ← → Acopio-specific)
- Plot all 6+ competitors + GRAVITEA in the quadrant
- GRAVITEA occupies unique position: Cloud-native + Acopio-depth (upper-right if Cloud is right, Acopio-depth is up)
- Key insight: Finnegans is cloud but generic/enterprise; AGIS/Physis have depth but desktop

**3.4 Pain Point Analysis**
- 6 acopiador-specific pain points from Research 4.3:
  1. Regulatory compliance burden (CPE/CTG, C-1116, SISA)
  2. Complex tax withholdings (IVA, Ganancias, IIBB, SICORE)
  3. Physical vs book inventory reconciliation (cubicaje, grain position)
  4. Producer account disputes (quality grading, merma, "a fijar")
  5. Manual data entry / fragmented systems (weighbridge transcription)
  6. Connectivity limitations (nuanced: small town, not remote field)
- RAG query: `"acopiador pain points regulatory compliance CTG SISA"`

**3.5 Value Proposition Canvas (Mermaid)**
- NEW Mermaid mindmap replacing v0.4's generic version
- Root: GRAVITEA VALUE
- Left: 6 Customer Pains (from 3.4 above)
- Right: Corresponding Gains (automatic compliance, real-time position, offline ops, etc.)
- Bottom: Our Solution (Hybrid Architecture, Regulatory Engine, AI-Ready)

---

### Section 4: Product Vision
**Effort**: Medium
**Source**: Descripcion General + architectural decisions

**4.1 What We Build (Module Map)**
- Mermaid diagram of 8 functional areas from Descripcion General:
  Recepcion (Romaneo), Almacenamiento, Calidad, Cuentas Corrientes,
  Liquidaciones, Facturacion, Agronomia (Insumos), Canje
- Plus cross-cutting: Reportes, Administracion, AI layer
- Consistent with Descripcion General module names and scope

**4.2 Core Operational Flow**
- Adapt the operational flow from Descripcion General (truck arrival -> romaneo -> position)
- Convert the ASCII diagram to Mermaid for consistency
- Key steps: Arrival (CPE/CTG) -> Gross weight -> Lab sampling -> Quality grade -> Merma calc -> Net weight -> Boleta de Romaneo -> Silo assignment + Producer account credit

**4.3 Dual Inventory Architecture**
- From Descripcion General "Inventario Dual" section
- Grain continuous inventory (kg, derived from romaneo net weight, adjusted by quality/campaign/merma)
- Insumos discrete inventory (units, lot control, expiry dates)
- Explain why both coexist in same platform (canje operation links them)

**4.4 Technical Differentiators**
- Lead with #1 moat: Offline-first architecture
- Then: Rust acceleration (merma.rs, grading.rs), PostgreSQL RLS multi-tenancy,
  ARCA direct integration (WSAA/WSFEv1/WSLPG), AI-ready data architecture,
  field-level encryption (AES-256-GCM for PII)
- Reference Implementation Progress table for evidence

**4.5 What We Don't Build**
- Generic POS / retail cash register
- B2C e-commerce
- Manufacturing / industrial processes
- Field agriculture (farm management, precision ag)
- Last-mile logistics / fleet management
- Payroll / HR

---

### Section 5: Target Segment and Personas
**Effort**: Medium
**Source**: Research 4.3 + architectural decisions + RAG

**5.1 Ideal Customer Profile**
- Independent acopiador (non-cooperative), 1-5 plants
- Pampas region (Cordoba, Santa Fe, Buenos Aires, Entre Rios)
- Small to medium capacity (< 80K tons total)
- Currently using: desktop software (AGIS, Physis) or generic ERP + Excel
- Pain level: high regulatory burden, manual processes, no mobile/remote access
- Sweet spot: generational transition (younger operator taking over)

**5.2 User Personas (5 personas with JTBD)**
- Mermaid diagram showing hierarchy + needs (replace v0.4's generic Cashier/Owner/Logistics/Accountant)
- Each persona: Name, Role, Primary JTBD, Key Pain, Success metric
  1. Dueno/Gerente: remote visibility, grain position, financial control
  2. Balancero/Recibidor: speed during harvest, offline resilience
  3. Laboratorista: quality grading, tolerance tables, merma calculations
  4. Administrador/Contable: regulatory compliance, tax withholdings, C-1116 forms
  5. Contador Rural: multi-client oversight, fiscal compliance verification
- RAG query (optional): `"acopiador technology adoption cloud versus desktop on-premise"` for technology comfort level by persona

---

### Section 6: Product Scope
**Effort**: Large
**Source**: Architectural decisions + v0.4 feature branch history

**6.1 MVP v1: Romaneo-to-Position Loop**
- Modules: Recepcion, Calidad, Almacenamiento, Cuentas Corrientes (basic)
- Features: truck entry, weighbridge integration, lab analysis, merma calculation,
  silo assignment, producer account credit, boleta de romaneo
- Acceptance: a complete grain reception cycle from truck arrival to producer account entry

**6.2 Phase 2: Liquidaciones + WSLPG**
- Liquidacion Primaria (C-1116-C), Secundaria (C-1116-B)
- WSLPG electronic filing via ARCA
- Tax withholding calculations (IVA, Ganancias, IIBB, SICORE)
- Producer account settlement

**6.3 Phase 3: Canje + Agronomia**
- Grain-for-input exchange (canje)
- Insumos catalog and discrete inventory
- Compras (purchases from distributors)
- Ventas de insumos (sales to producers)

**6.4 Phase 4: AI Features**
- Quality degradation prediction, silo optimization, price forecasting,
  fraud detection, document intelligence, aeration scheduling
- (Details in Section 9)

**6.5 Implementation Progress**
- Preserve the Implementation Progress table from v0.4 (lines 13-28)
- Preserve the Implementation Summary paragraph (lines 190-196)
- Frame as: "existing infrastructure that carries forward"

**6.6 Feature Branch History**
- **COPY VERBATIM** from v0.4 lines 238-261 (branches 001-025 + API Audit)
- Do NOT modify individual entries
- Update section title if needed

**Mermaid diagram**: Phased roadmap (Phase 1 → Phase 2 → Phase 3 → Phase 4 with key deliverables)

---

### Section 7: Go-to-Market Strategy
**Effort**: Medium
**Source**: Research 6.2, 6.3 + RAG + Engram business panel

**7.1 Contador Rural Channel**
- Free portal for accountants (distribution flywheel — mirrors Xubio/Colppy model)
- Mechanics: **5-15 acopio/cooperative/contractor clients per estudio** (20-50 agricultural clients total, subset are acopios) [Research 6.2]
- Contador is "key advisor" in small/medium agro enterprises: participates in financing, investment, and systemization decisions — not just tax [Research 6.2]
- Free portal value props: real-time client transactions, less spreadsheet/email exchange, automated books, centralized multi-client view, one-click exports [Research 6.2]
- "Invitar a tu contador" referral flow + tangible time savings = 10x distribution effect in dense grain regions [Research 6.2]
- FACPCE/CPCE course targeting: seminars on RT 22 (agropecuaria accounting), RT 41; position as "Herramientas para el contador agropecuario que trabaja con acopios de granos" [Research 6.2]
- CPCE Córdoba specifically for Villa María/Córdoba beachhead
- RAG query: `"accountant contador rural channel strategy grain operations"`

**7.2 Geographic Beachhead**
- Villa Maria (founder's base, direct Sociedad de Acopiadores access)
- -> Cordoba province (81 Federacion members, worst storage deficit)
- -> Pampas region (88% of plants)
- RAG query: `"market sizing geographic distribution acopiadores provinces"`

**7.3 Trade Associations and Events**
- Tier 1: Federacion de Acopiadores, A Todo Trigo (May 2026), Sociedad de Acopiadores CBA
- Tier 2: Grano SAC (November, Rosario), ExpoAgro, AgroActiva
- RAG query: `"trade associations industry events Expoagro acopiadores"`

**7.4 Switching Strategy**
- Optimal window: April-June (post-soybean harvest, lowest operational intensity)
- Migration tools from AGIS/Physis/Excel (structured data import)
- Target generational transition (ACA Jovenes networks)
- RAG query: `"acopiador technology adoption cloud versus desktop on-premise"`

---

### Section 8: Pricing Strategy
**Effort**: Small-Medium
**Source**: Engram business panel + Research 4.3 Section 6

**8.1 Per-seat USD-indexed model**
- $90/seat/month, annual discount to $75/seat
- Per-seat disruption: small acopio (2 users) pays ~$180 vs incumbents $500-800/establishment

**8.2 Free Accountant Portal**
- Zero cost for contador rural users
- Value: centralized multi-client view, automated exports, real-time transactions
- Distribution flywheel (mirrors Xubio/Colppy model)

**8.3 Competitive Analysis**
- Table comparing GRAVITEA pricing vs Algoritmo, AGIS, Finnegans, Versat
- RAG query: `"acopio pricing revenue model SaaS grain management"`

---

### Section 9: AI Differentiation Roadmap
**Effort**: Medium
**Source**: Research 9.1

Six capabilities with model architectures and expected outcomes:
1. Quality degradation prediction (3D-CNN + LSTM, 97.38% accuracy)
2. Silo assignment optimization (MILP, 27% truck queue reduction)
3. Price forecasting (VMD-SGMD-LSTM for Matba Rofex, XGBoost for local basis)
4. Weighbridge fraud detection (anomaly detection on weight patterns)
5. Document intelligence (OCR for Carta de Porte)
6. Predictive aeration scheduling (SVM-Poly, 99.98% efficiency)

- RAG query: `"AI machine learning grain storage silo prediction optimization"`

---

### Section 10: Success Metrics (KPIs)
**Effort**: Small
**Source**: Domain knowledge + spec requirements

Organized by category:
- **Operational**: harvest throughput (trucks/hour), sync latency (< 60s), system uptime (99.5%+)
- **Adoption**: onboarding time (< 1 day for balancero), active users per tenant
- **Business**: stock discrepancy reduction (target < 2%), regulatory compliance rate (CTG/LPG filing success %), ARPU

---

### Section 11: Risk and Mitigation
**Effort**: Small-Medium
**Source**: Research 4.3 + domain knowledge

| Risk | Mitigation |
|------|-----------|
| Connectivity gaps during harvest | Offline-first architecture (primary moat) |
| Regulatory change velocity (ARCA/SISA) | Modular ARCA integration, Rust acceleration for update speed |
| Competitor response (Algoritmo + Silohub) | First-mover in cloud+offline+depth combination; faster iteration |
| Adoption resistance (generational) | Target younger operators, ACA Jovenes, generous onboarding |
| Data migration barrier | Structured import tools from AGIS/Physis/Excel formats |
| 7/10 implementation failure rate | Process-first onboarding, not technology-first; accountant channel provides built-in training advocate |

- RAG query: `"offline connectivity rural areas grain operations argentina"`

---

## Research-to-Section Mapping

| Research Doc | Sections Fed |
|-------------|-------------|
| 4.1 (Market Map) | 3.2 Competitive Landscape, 3.3 Positioning Map, 8.3 Competitive Pricing |
| 4.2 (AGIS Deep Dive) | 3.2 AGIS profile, 3.3 Positioning Map |
| 4.3 (Pain Points + Adoption) | 3.4 Pain Points, 3.5 Value Canvas, 5.1 ICP, 7.4 Switching, 8.1 Pricing, 11. Risk |
| 6.1 (Market Sizing) | 3.1 TAM/SAM/SOM, 7.2 Geographic Beachhead |
| 6.2 (Contador Channel) | 7.1 Contador Rural Channel, 8.2 Free Portal |
| 6.3 (Trade Associations) | 7.3 Trade Events |
| 9.1 (AI/ML) | 9. AI Roadmap |
| Descripcion General | 4.1 Module Map, 4.2 Operational Flow, 4.3 Dual Inventory |
| Engram Business Panel | 2.1 Vision, 8.1 Pricing, 7. GTM Strategy |
| v0.4 Document | 1. Metadata, 2.2 Principles, 6.5 Progress, 6.6 Branch History |

### RAG Query Schedule

The RAG-Verified Inline Data section above has pre-verified facts from the key queries.
If additional depth is needed, run targeted queries or the full batch:

```bash
# Single query (single-author workflow)
.venv/bin/python scripts/qdrant/qdrant_search.py -q "QUERY" -l 5

# Full batch (saves to Docs/RAG_results/spec01/)
.venv/bin/python scripts/qdrant/qdrant_batch_search.py \
  -q "acopio software market competitors Algoritmo AGIS Physis" \
  -q "acopiador pain points regulatory compliance CTG SISA" \
  -q "market sizing geographic distribution acopiadores provinces" \
  -q "AGIS AmericaGIS competitive analysis technology VB6 desktop" \
  -q "acopiador technology adoption cloud versus desktop on-premise" \
  -q "accountant contador rural channel strategy grain operations" \
  -q "AI machine learning grain storage silo prediction optimization" \
  -q "trade associations industry events Expoagro acopiadores" \
  -q "acopio pricing revenue model SaaS grain management" \
  -q "offline connectivity rural areas grain operations argentina" \
  -o Docs/RAG_results/spec01 -l 5

# Read results
ls Docs/RAG_results/spec01/
cat Docs/RAG_results/spec01/01_acopio_software_market_competitors.txt
```

---

## Mermaid Diagrams Required (minimum 5)

| # | Diagram | Type | Section | Notes |
|---|---------|------|---------|-------|
| 1 | Competitive Positioning Map | Quadrant (graph) | 3.3 | X: Desktop↔Cloud, Y: Generic↔Acopio-depth. Plot 7+ products |
| 2 | Value Proposition Canvas | Mindmap | 3.5 | Pains (6) → Gains (6) → Solution pillars |
| 3 | Module Map | Block diagram | 4.1 | 8 functional areas + AI + Reportes + Admin |
| 4 | Core Operational Flow | Flowchart | 4.2 | Truck arrival → romaneo → position (adapt from Descripcion General) |
| 5 | User Persona Hierarchy | Graph | 5.2 | 5 personas with JTBD connections |
| 6 | Phased Roadmap | Timeline/flowchart | 6 | Phase 1→2→3→4 with key deliverables per phase |

---

## Checkpoint Gates

### Gate 1: After Sections 1-2 (Metadata + Strategic Purpose)
- [ ] v0.4 metadata adapted (version 1.0, status updated)
- [ ] Implementation Progress preserved verbatim
- [ ] "Strategic Inflection Point" box REMOVED
- [ ] Vision statement mentions "acopio de granos" explicitly
- [ ] All 4 original Ironclad principles preserved
- [ ] Two new principles added (Regulatory Automation, AI-Ready)
- [ ] Zero generic retail language ("hardware store", "beverage", "cashier")

### Gate 2: After Section 3 (Market Context)
- [ ] TAM/SAM/SOM with specific numbers and [Research 6.1] citations
- [ ] 6+ competitor profiles (spec minimum); 9+ profiles recommended per corpus data
- [ ] AGIS client count cited as "2,000+ acopio clients" [Research 4.2] (not 3,000+)
- [ ] Government mandatory systems box (SIO Granos, SISA, BolsaTech) clearly labeled "must integrate"
- [ ] Competitive positioning Mermaid diagram renders correctly
- [ ] All 6 pain points from Research 4.3 represented with specific regulation citations (RG 5689/2025, RG 5821/2026, RG 2300, etc.)
- [ ] Value proposition canvas Mermaid diagram renders correctly
- [ ] 4-tier market segmentation included
- [ ] 7/10 implementation failure rate cited [Research 4.3]; SYNAgro 1-year minimum as concrete example

### Gate 3: After Sections 4-5 (Product Vision + Personas)
- [ ] Module map consistent with Descripcion General (8 areas)
- [ ] Module map Mermaid diagram renders correctly
- [ ] Operational flow Mermaid diagram renders correctly
- [ ] Dual inventory architecture explained (grain continuous + insumos discrete)
- [ ] Offline-first leads technical differentiators
- [ ] Out-of-scope section clearly bounds what we DON'T build
- [ ] 5 acopio personas with JTBD (not generic cashier/logistics)
- [ ] Persona hierarchy Mermaid diagram renders correctly

### Gate 4: After Section 6 (Product Scope)
- [ ] MVP is Romaneo-to-Position loop (not generic retail)
- [ ] 4 phases clearly defined with scope boundaries
- [ ] Phased roadmap Mermaid diagram renders correctly
- [ ] Feature branch history table copied verbatim (001-025)
- [ ] Implementation Progress table preserved
- [ ] Implementation Summary paragraph preserved

### Gate 5: After Sections 7-8 (GTM + Pricing)
- [ ] Contador rural channel described with flywheel mechanics
- [ ] Geographic beachhead: Villa Maria -> Cordoba -> Pampas
- [ ] Trade events with specific names and dates
- [ ] Switching window: April-June (post-soybean harvest)
- [ ] Per-seat USD-indexed pricing with specific numbers
- [ ] Free accountant portal as distribution mechanism
- [ ] Competitive pricing comparison

### Gate 6: After Sections 9-11 (AI + KPIs + Risk)
- [ ] 6+ AI capabilities from Research 9.1 with model architectures
- [ ] AI positioned as Phase 3-4 (not MVP)
- [ ] KPIs organized: Operational, Adoption, Business
- [ ] KPIs are acopio-specific (not generic retail)
- [ ] Risk table covers all 6 required risks
- [ ] 7/10 failure rate addressed with mitigation

### Final Validation Gate
- [ ] Full-text search: zero hits for "hardware store", "beverage distributor", "cashier", "under evaluation"
- [ ] All Mermaid diagrams (minimum 5) render correctly
- [ ] All market claims have [Research X.Y] citations
- [ ] Document is self-contained (readable without other specs)
- [ ] Module map consistent with Descripcion General
- [ ] Feature branch history complete (001-025)
- [ ] Word count in 500-800 line range (not too terse, not bloated)

---

## Done Criteria

The document is DONE when ALL of the following are true:

1. **AC-01 through AC-15** from `specs/001-acopio-vision/spec.md` all pass
2. **All 7 checkpoint gates** above are fully checked
3. **File replaced**: `Docs/Project Blueprint/Product Vision & Scope.md` updated in-place (v0.4 -> v1.0)
4. **No stale content**: zero references to generic retail, evaluation phase, or candidate verticals
5. **Diagram verification**: all Mermaid diagrams tested in a Markdown renderer
6. **Cross-reference check**: module names match `Descripcion General del Producto.md`
7. **Citation check**: every quantified market claim has a `[Research X.Y]` tag
8. **Self-contained**: a reader unfamiliar with the project understands the full vision from this document alone

---

## RAG-Verified Inline Data (use these directly, do not re-query)

The following facts were confirmed by RAG queries and are ready to inline during writing. Use
these to avoid redundant queries on facts already verified.

### Competitor Table (Research 4.1 + 4.2) [RAG-verified 2026-03-15]
| Competitor | Founded | Location | Platform | Key Differentiator |
|-----------|---------|----------|----------|--------------------|
| Algoritmo | 1985 | Rosario, SF | Desktop + Silohub web overlay | ~125 acopios, 20M+ tons, "most widespread" |
| AGIS | ~1985 | Villa María, CBA | VB6/.NET desktop | 2,000+ acopio clients; 3 fragmented stacks |
| Physis | ~1988 | CABA/Rosario | Desktop Windows | Futures/options module, most feature-complete |
| AgroAcopio | 1983 | Buenos Aires | Desktop | Oldest (42 years), auto scale reading |
| Agrosistemas | 1990 | Mar del Plata | Desktop | ISO 9001:2015, CTG+LPG+LSG+COT, "AI planned" |
| Gestagro/Kernel | 1988 | Rosario | Desktop + Android | Coop-focused |
| Siscoop | 1986 | Bahía Blanca | Desktop + partial web | Coop-focused |
| Informática Tandil | Unknown | Tandil | Desktop | Regional vendor |
| SYNAgro | Unknown | Unknown | On-premise + consulting | 1-year minimum implementation |
| Finnegans GO Granos | 1992 | Buenos Aires | Cloud SaaS (AWS) | ~1,500 agro total; enterprise-tier |
| Versat ERP Agro | Unknown | Unknown | Cloud SaaS | USD 200-640/mo; not acopio-depth |

### Regulatory Systems (Research 4.1) [RAG-verified — label as "must integrate", not competitors]
- **SIO Granos** (Secretaría de Agricultura/CNV): mandatory grain buy/sell registration
- **Registro Sistémico / SISA** (ARCA, RG 5689/2025): 24h grain movement/stock registration
- **BolsaTech** (BCCBA): soy technology commercialization and royalty management

### Key Regulatory Citations for Pain Points (Research 4.3) [RAG-verified]
- CPE/CTG: mandatory since 2021, real-time internet required
- C-1116 forms (A/B/C/RT): filed via WSLPG (RG 3419/2012, RG 3690/2014, RG 3691/2014)
- SISA RG 5689/2025: 24h registration; RG 5821/2026: CPE linked to SISA status
- IVA retention: RG 4310/2018 + older RG 2300 (8% retention, theoretically refunded in 60 days)
- Ganancias retention: RG 2118/2006; IIBB by province

### Contador Rural Channel (Research 6.2) [RAG-verified]
- 5-15 acopio/cooperative/contractor clients per agro-specialized estudio
- 20-50 agricultural clients total per estudio (mostly farms, subset are acopios)
- Contador is "key advisor" for financing, investment, and systemization — not just tax
- Value props: real-time transactions, automated books, multi-client dashboard, one-click exports
- GTM: FACPCE seminars (RT 22, RT 41), CPCE Córdoba agro events

### Trade Events (Research 6.3) [RAG-verified]
- **Tier 1**: Federación de Acopiadores de Cereales (~1,000 companies), A Todo Trigo (May 2026, Mar del Plata), Sociedad de Acopiadores de Córdoba (Villa María corridor)
- **Tier 2**: Grano SAC/Expo Poscosecha (Rosario, November), ExpoAgro, AgroActiva
- **Networking**: Federación working-commission meetings, BCCBA member events

---

## Execution Notes

### Pre-Writing Setup
Before writing any section:
1. Read `specs/001-acopio-vision/spec.md` (the authoritative spec) -- understand all 17 FRs and 9 SCs
2. Read `Docs/Project Blueprint/Descripcion General del Producto.md` -- module map authority
3. Read `Docs/Project Blueprint/Product Vision & Scope.md` (v0.4) -- understand what to preserve
4. Use the RAG-Verified Inline Data table above for competitor/regulatory facts (no re-querying needed)
5. Run batch RAG only if additional detail is needed beyond what's in that table

### Writing Order Recommendation
Write sections in dependency order, not document order:
1. **Section 1** (Metadata) -- quick, sets framing, preserve Implementation Progress table verbatim
2. **Section 3** (Market) -- most research-intensive; use RAG-Verified Inline Data table above
3. **Section 4** (Product Vision) -- depends on module map from Descripcion General
4. **Section 5** (Personas) -- depends on pain points from Section 3
5. **Section 2** (Strategic Purpose) -- vision statement crafted AFTER market + product are clear
6. **Section 6** (Scope) -- depends on personas + modules; copy branch history verbatim from v0.4
7. **Sections 7-8** (GTM + Pricing) -- depends on ICP from Section 5; use RAG channel data
8. **Section 9** (AI) -- independent, use Research 9.1 capability list
9. **Sections 10-11** (KPIs + Risk) -- synthesize from all above

### Key Cross-References to Maintain
- Module names in Section 4.1 MUST match Descripcion General
- Personas in Section 5.2 MUST map to pain points in Section 3.4
- MVP scope in Section 6.1 MUST match architectural decision (Romaneo-to-Position)
- Phase assignments MUST be consistent between Section 6 and Section 13 (Roadmap)
- Technical differentiators in Section 4.4 MUST match Implementation Progress in Section 1

### File Operations
- **Target file**: `Docs/Project Blueprint/Product Vision & Scope.md`
- **Operation**: REPLACE entire file content (v0.4 -> v1.0)
- **Backup**: Git tracks v0.4 in history, no manual backup needed
- **No new files created** -- this is an in-place rewrite
