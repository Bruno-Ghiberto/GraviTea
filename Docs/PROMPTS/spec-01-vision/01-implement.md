# Spec 01: Product Vision & Scope -- Implementation Context

## Execution Profile

**Type**: Blueprint document -- single-author writing task
**Target file**: `Docs/Project Blueprint/Product Vision & Scope.md` (in-place rewrite v0.4 -> v1.0)
**Task source**: `specs/001-acopio-vision/tasks.md` (50 tasks, 8 phases)
**Validation source**: `specs/001-acopio-vision/contracts/document-structure.md`
**Primary data source**: `specs/001-acopio-vision/research.md` (all facts RAG-verified)
**No code. No tests. No agent teams. No tmux.**

---

## Context Files -- Read Order

Read these files BEFORE writing. They contain everything needed.

| # | File | Why | Time |
|---|------|-----|------|
| 1 | `specs/001-acopio-vision/quickstart.md` | Step-by-step writing guide, checkpoint gates, validation commands | 5 min |
| 2 | `specs/001-acopio-vision/research.md` | ALL verified facts, 7 decisions (D-001 to D-007), section-by-section data | 10 min |
| 3 | `specs/001-acopio-vision/contracts/document-structure.md` | Per-section acceptance tests, traceability matrix | 5 min |
| 4 | `Docs/Project Blueprint/Descripción General del Producto.md` | Module names authority, operational flow, dual inventory | 5 min |
| 5 | `Docs/Project Blueprint/Product Vision & Scope.md` (v0.4) | Content to PRESERVE: Implementation Progress table, Feature Branch History, Ironclad principles | 5 min |
| 6 | `specs/001-acopio-vision/spec.md` | 17 FRs, 9 SCs, 5 User Stories -- the contract to satisfy | 5 min |

**Total pre-read**: ~35 minutes. All domain knowledge is in research.md. Do NOT read raw research PDFs.

---

## Writing Rules

### Tone & Voice
- Professional strategic document -- not a sales pitch, not a technical manual
- Confident and declarative: "GRAVITEA is..." not "GRAVITEA could be..."
- No hedging: eliminate "under evaluation", "considering", "potentially", "may"
- Data-driven: every market claim has a `[Research X.Y]` citation

### Language Protocol
- English is the primary language
- Spanish domain terms are canonical and must be used:
  romaneo, merma, acopiador, cuenta corriente, liquidación, canje,
  Carta de Porte, balancero, laboratorista, contador, calado, pizarra
- First occurrence includes English translation: "romaneo (weighing ticket)"
- After first use, Spanish term alone suffices

### Forbidden Language (DL-001 -- zero tolerance)
The following strings MUST NOT appear ANYWHERE in the final document:
- "hardware store"
- "beverage distributor"
- "cashier"
- "under evaluation"
- "retail store"
- "point of sale" (except in out-of-scope list)

### Citation Protocol
Every quantified claim (number, percentage, statistic) MUST include `[Research X.Y]`:
- Market sizing figures -> `[Research 6.1]`
- Competitor data -> `[Research 4.1]` or `[Research 4.2]`
- Pain point statistics -> `[Research 4.3]`
- AI capabilities -> `[Research 9.1]`
- Contador channel -> `[Research 6.2]`
- Trade events -> `[Research 6.3]`

---

## Section-by-Section Drafting Instructions

Write in this dependency order -- NOT document order:

```
S3 -> S2 -> S4 -> S5 -> S6 -> S7 -> S8 -> S9 -> S10 -> S11 -> S1
```

---

### SECTION 3: Market Context (Write FIRST -- foundation for all)

**Tasks**: T006-T013 | **FRs**: FR-002, FR-003, FR-004 | **Gate**: 1

**3.1 Market Sizing** (T006)
Write TAM/SAM/SOM using EXACT figures from `research.md §3.1`:
- TAM: ~1,259 acopiador-consignatario enterprises, ~2,458 storage plants nationwide `[Research 6.1]`
- SAM: ~1,073 private (non-cooperative), ~1,622 plants (~68% of total) `[Research 6.1]`
- SOM initial: Córdoba (81 Federación members) + Santa Fe (58 members) = 139 targets `[Research 6.1]`
- Size distribution: 60% small (<20K tons), 32% medium (20K-80K), 8% large (>80K)
- Geographic: 88% of plants in Pampas region; BA ~40% of plants; SF largest capacity ~14.8Mt

**3.2 Competitive Landscape** (T007, T008, T009, T010)
1. Create Mermaid quadrant diagram (T007):
   - Axes: X = Desktop-only -> Cloud-native; Y = Generic -> Acopio-depth
   - GRAVITEA alone in upper-right (cloud-native + acopio-depth)
   - Plot: AGIS, Algoritmo, Physis, AgroAcopio, Finnegans GO Granos, Versat, Albor Campo

2. Write 11 competitor profiles (T008) -- use table from `research.md §3.2`:

   | Competitor | Founded | Location | Platform | Clients | Key Weakness |
   |-----------|---------|----------|----------|---------|-------------|
   | Algoritmo | 1985 | Rosario, SF | Desktop + Silohub overlay | ~125 acopio | No native cloud; 2-platform cost |
   | AGIS (AmericaGIS) | ~1985 | Villa María, CBA | VB6/.NET desktop | **2,000+ acopio** | 3 fragmented stacks; VB6 EOL 2008 |
   | Physis | ~1988 | CABA/Rosario | Desktop Windows | Unknown | No web/mobile/cloud |
   | AgroAcopio | 1983 | Buenos Aires | Desktop | Unknown | Oldest tech stack |
   | Agrosistemas | 1990 | Mar del Plata | Desktop | Unknown | Desktop-only despite ISO cert |
   | Gestagro/Kernel | 1988 | Rosario | Desktop + Android | Unknown | Coop-focused only |
   | Siscoop | 1986 | Bahía Blanca | Desktop + partial web | Unknown | Coop-focused only |
   | Informática Tandil | Unknown | Tandil | Desktop | Unknown | Regional, limited reach |
   | SYNAgro | Unknown | Unknown | On-premise + consulting | Unknown | 1-year minimum implementation |
   | Finnegans GO Granos | 1992 | Buenos Aires | Cloud SaaS (AWS) | ~1,500 agro total | Enterprise-tier pricing; lacks operational depth |
   | Versat ERP Agro | Unknown | Unknown | Cloud SaaS | Unknown | Not acopio-specific; USD 200-640/month |

   **CRITICAL**: AGIS = "2,000+ acopio clients" `[Research 4.2]`. NOT "3,000+".
   Per-profile fields required: location, founding year, platform, clients, strengths, weaknesses.

3. Government mandatory systems box (T009):
   > **Mandatory Government Integrations** (must integrate, not competitors):
   > SIO Granos | SISA / Registro Sistémico (RG 5689/2025) | BolsaTech

4. 4-tier market segmentation (T010):
   - 10-15% large acopios + coops -> full specialized ERP (Algoritmo, Finnegans, SAP)
   - 20-30% medium -> specialized desktop (AGIS, Physis, AgroAcopio, Agrosistemas)
   - 25-35% small -> generic ERP + Excel (Tango/Bejerman + spreadsheets)
   - 20-30% small -> primarily Excel/manual + AFIP web portals

**3.3 Pain Points** (T011, T012)
6 pain points with regulatory citations:
1. Regulatory compliance: CPE/CTG real-time since 2021; C-1116 (RG 3419/2012, RG 3690/2014, RG 3691/2014); SISA RG 5689/2025 (24h, sanctions = no Cartas de Porte); RG 5821/2026 (CPE linked to SISA status)
2. Tax withholdings: IVA 8% (RG 4310/2018 + RG 2300; refund delays > 12 months; ARS 500K-1.5M trapped/producer); Ganancias 2-15% (RG 2118/2006); IIBB by province; SICORE magnetic files
3. Inventory reconciliation: cubicaje, grain position (comprado vs vendido), overselling risk
4. Producer account disputes: quality grading, conditioning costs (secado, zarandeo, fumigación), settlement timing ("a fijar")
5. Manual data entry: weighbridge transcription errors; peak harvest = hundreds of trucks/day; 7/10 implementations fail from poor process alignment [Albor Agtech]
6. Connectivity: **NUANCE** -- write "acopio plants are in small towns with better connectivity than remote fields -- brief outages during peak harvest halt CTG/SISA operations." Do NOT frame as "40.2% have no internet" as if plants are offline.

Technology adoption stats (T012):
- 92% of ag sector uses apps/platforms; 65% use digital platforms
- 62.1M smartphone connections, 97% 4G; WhatsApp is de facto management tool
- Buying behavior: Owner + Accountant dual influence; budget USD 150-500/month; April-June switching window

**Gate 1 check** (T013): TAM/SAM/SOM with [Research 6.1] | Mermaid renders | AGIS "2,000+" | Govt box labeled | Connectivity nuance present

---

### SECTION 2: Strategic Purpose & Vision

**Tasks**: T014 | **FRs**: FR-001, FR-017 | **Gate**: 2

**Vision statement** (replace ALL generic content):
> "Empower independent Argentine grain operators (acopiadores de granos) with the first cloud-native, offline-first ERP purpose-built for grain stockpiling operations -- delivering automatic regulatory compliance, real-time grain position visibility, and enterprise-grade security to the small-to-medium acopiador who has been historically underserved by desktop-era software."

**Vertical commitment**: Explicit present-tense declaration. The acopio vertical is the committed direction.

**6 Ironclad Principles** (copy 4 from v0.4, adapt wording, add 2 new):
1. **Pragmatic Offline-First**: offline is the base architecture, not a fallback mode
2. **Transactional Integrity (Ledger)**: no UPDATE on grain movements, only INSERT contra-entries
3. **Encapsulated Complexity**: balancero sees "Green = Approved" not "CTG Issued via WSLPG"
4. **Enterprise Security for SMBs**: RLS, AES-256-GCM, audit -- corporate-grade for grain operators
5. **Regulatory Automation** (NEW): CPE/CTG, C-1116, SISA registrations happen automatically
6. **AI-Ready Data Architecture** (NEW): every weighing, quality grade, storage movement is structured data first

**Gate 2 check**: Vision contains "acopiadores de granos" + "offline-first" + "regulatory compliance" | 6 Ironclad principles | Zero hedging language

---

### SECTION 4: Product Vision & Scope

**Tasks**: T015-T021 | **FRs**: FR-007, FR-008, FR-009, FR-013 | **Gate**: 3

**4.1 Module Map** (T015) -- Mermaid diagram with EXACT Spanish names from Descripción General:
RECEPCIÓN (Romaneo), ALMACENAMIENTO, CALIDAD, CUENTAS CORRIENTES, LIQUIDACIONES, FACTURACIÓN, AGRONOMÍA (Insumos), CANJE

**4.2 Core Operational Flow** (T016) -- Mermaid flowchart:
Llegada CPE/CTG -> Peso Bruto (Balanza) -> Calado y Muestreo -> Análisis Lab (Calidad) ->
Cálculo Merma -> Peso Neto Conforme -> Boleta de Romaneo -> [Asignación Silo] + [Crédito Cuenta Corriente] ->
[Liquidación 1116-C] or [Canje por Insumos]

**4.3 MVP Scope** (T017) -- Phase 1 = Romaneo-to-Position loop:
- Reception: truck arrival, CPE/CTG, gross weight, calado
- Quality analysis: lab grading, tolerance tables (Cámara Arbitral), merma calculations
- Storage assignment: silo allocation by grain type/quality/campaign
- Producer account credit: saldo granos kg, movement history

**4.4 Technical Differentiators** (T018) -- offline-first MUST be #1:
1. Offline-first hybrid architecture (operates without internet; syncs when connectivity restores)
2. Rust acceleration layer (merma engine, grading calculations -- 2-9x speedups via PyO3)
3. PostgreSQL RLS multi-tenancy (plant-level isolation, physically impossible cross-tenant)
4. ARCA direct integration (WSAA/WSFEv1/WSLPG -- CAE online + CAEA offline)
5. AI-ready data architecture (structured capture enables Phase 4 ML without data migration)
6. Field-level encryption (AES-256-GCM for PII -- producer data, certificate data)

**4.5 Dual Inventory** (T019):
- Grain (activo líquido): continuous, measured in kg; stock derived from romaneo net weight
- Insumos (activo contable): discrete, measured in units; N units in/N units out; lot+barcode+expiry

**4.6 Out of Scope** (T020): Generic POS, B2C e-commerce, Manufacturing, Field agriculture, Fleet management, Payroll/HR

**4.7 Phased Roadmap** (T021) -- Mermaid timeline:
- Phase 1: Romaneo + Position (MVP)
- Phase 2: Liquidaciones + WSLPG
- Phase 3: Canje + Agronomía
- Phase 4: AI features

**Gate 3 check**: 8 modules exact names | offline-first = #1 | Phase 4 = AI | All Mermaid diagrams render

---

### SECTION 5: User Personas

**Tasks**: T022 | **FRs**: FR-005 | **Gate**: 4

Mermaid hierarchy diagram + 5 individual persona cards + ICP definition.

| Persona | Role | Primary JTBD | Key Pain | Tech Comfort |
|---------|------|-------------|----------|-------------|
| Dueño/Gerente | Owner/Manager | Remote grain position + financial control from phone | Can't see inventory without being physically present | Medium-high (smartphone) |
| Balancero/Recibidor | Weighbridge operator | Complete truck reception in < 5 min without system waiting | Manual transcription during harvest peak | Medium (Windows desktop) |
| Laboratorista | Lab analyst | Grade samples and calculate merma without spreadsheets | Quality disputes from manual calculation errors | Medium (desktop tools) |
| Administrador/Contable | Admin/accountant | File all regulatory documents automatically | 3+ hours/day on ARCA/SISA compliance | Medium-high (AFIP portals) |
| Contador Rural | External accountant | Real-time multi-client fiscal visibility | Chasing Excel files from 5-15 clients by email | High (cloud tools) |

**ICP**: Independent (non-cooperative) acopiador, 1-5 plants, Pampas region, small-medium capacity, currently using desktop software or generic ERP + Excel, experiencing generational transition.

**Gate 4 check**: 5 personas | No generic roles (no "cashier") | Each has JTBD+pain+tech comfort | ICP defined

---

### SECTION 6: Value Proposition Canvas

**Tasks**: T025 | **FRs**: FR-006 | **Gate**: 5

| Acopiador Pain | GRAVITEA Gain |
|----------------|---------------|
| CPE/CTG/SISA compliance burden | Automatic regulatory filings -- zero manual submission |
| Tax withholding complexity (IVA/Ganancias/IIBB) | Instant retention calculations per liquidación + SICORE output |
| Grain inventory reconciliation discrepancies | Real-time grain position: comprado vs vendido vs físico |
| Producer account disputes over quality | Transparent grading via tolerance tables (Cámara Arbitral) |
| Manual weighbridge transcription during harvest | Direct weighbridge integration + offline romaneo |
| Internet outages halting CTG operations | Hybrid CAEA mode: operations continue, sync when online |

**Gate 5 check**: 6 pairs | "CAEA" in connectivity row | "IVA" or "retenciones" in tax row | Specific product capabilities (not vague)

---

### SECTION 7: Go-to-Market Strategy

**Tasks**: T029-T032 | **FRs**: FR-011 | **Gate**: 6

**7.1 Contador Rural Channel** (T029):
- Free portal: real-time transactions, automated books, multi-client dashboard, one-click exports
- "Invitar a tu contador" referral flow (USE THIS EXACT PHRASE)
- 5-15 acopio clients per agro-specialized estudio (20-50 total agricultural clients)
- FACPCE seminars (RT 22, RT 41) + CPCE Córdoba agro events
- Model mirrors Xubio/Colppy success in Argentine SMB market

**7.2 Geographic Beachhead** (T030):
Villa María -> Córdoba -> Pampas
- D-005 rationale: founder's base, Sociedad de Acopiadores de Córdoba HQ, 81 Federación members
- **MUST ACKNOWLEDGE**: AGIS is also HQ'd in Villa María -- both opportunity and risk

**7.3 Trade Events** (T031):
| Tier | Event | Date | Location |
|------|-------|------|----------|
| 1 | A Todo Trigo | May 2026 | Mar del Plata |
| 1 | Sociedad de Acopiadores de Córdoba | Annual | Villa María corridor |
| 1 | Federación de Acopiadores de Cereales | Ongoing | Buenos Aires |
| 2 | Grano SAC / Expo Poscosecha | November | Rosario |
| 2 | ExpoAgro | Annual | San Nicolás |
| 2 | AgroActiva | Annual | Armstrong, SF |

**7.4 Switching Strategy** (T032):
- April-June window (post-soybean harvest) -- MUST NAME EXACT MONTHS + RATIONALE
- Migration tools from AGIS/Physis/Excel
- ACA Jóvenes networks for generational transition

**Gate 6 check**: "Invitar a tu contador" verbatim | "5-15" present | Villa María first + AGIS risk | A Todo Trigo May 2026 Mar del Plata | April-June with rationale

---

### SECTION 8: Pricing Strategy

**Tasks**: T033 | **FRs**: FR-012 | **Gate**: 6 (continued)

**Pricing model**:
- Monthly: $90/seat/month (USD-indexed)
- Annual: $75/seat/month (17% discount)
- Free: Contador rural portal (unlimited read-only)
- USD-indexing rationale: grain pricing is USD-denominated; protects both parties from ARS devaluation

**Disruption math** (MUST show arithmetic):
> Small acopio (2 users): 2 x $90 = $180/month vs incumbent $500-800/establishment -> 2.8x to 4.4x cheaper

**Competitive comparison table** including Versat reference (USD 200-640/month).

---

### SECTION 9: AI Differentiation Roadmap

**Tasks**: T035 | **FRs**: FR-010 | **Gate**: 7

**Framing**: "Platform built in Phases 1-3 captures structured data enabling Phase 4 ML without data migration -- this is Ironclad Principle 6 in action."

**7 capabilities** (ALL Phase 3-4, cite [Research 9.1]):
| Capability | Model Architecture | Phase | Expected Outcome |
|-----------|-------------------|-------|-----------------|
| Quality degradation prediction | 3D-CNN + LSTM | 4 | 97.38% classification accuracy |
| Silo assignment optimization | MILP | 4 | 27% truck queue reduction |
| Price forecasting (Matba Rofex) | VMD-SGMD-LSTM | 4 | Grain futures prediction |
| Price forecasting (local pizarra) | XGBoost | 4 | Local basis prediction |
| Weighbridge fraud detection | Anomaly detection | 3 | Alert on suspicious weight variance |
| Document intelligence | OCR (Carta de Porte) | 3 | Automatic CPE data extraction |
| Predictive aeration scheduling | SVM-Poly | 4 | 99.98% efficiency classification |

**Gate 7 check**: 6+ capabilities | All Phase 3-4 | 3D-CNN+LSTM, MILP, SVM-Poly named | [Research 9.1] cited

---

### SECTION 10: Success Metrics

**Tasks**: T036 | **FRs**: FR-014

**Operational**: harvest > 10 trucks/hour (vs manual 4-6/hour) | sync < 60s | uptime 99.5%+
**Adoption**: balancero onboarding < 1 day | active users > 80% in 30 days
**Business**: stock discrepancy < 2% (vs 10-15% manual) | CTG compliance > 99.5% | ARPU $360/month/tenant (4 x $90)

---

### SECTION 11: Risks & Mitigation

**Tasks**: T037 | **FRs**: FR-015

| Risk | Severity | Mitigation |
|------|---------|-----------|
| Connectivity gaps during harvest | High | Offline-first is the primary competitive moat |
| Regulatory change velocity (ARCA/SISA) | High | Modular ARCA integration; Rust acceleration |
| Competitor response (Algoritmo + Silohub) | Medium | First-mover in cloud+offline+depth combination |
| Adoption resistance (generational divide) | Medium | ACA Jóvenes + contador channel advocacy |
| Data migration barrier (#1 switching barrier) | High | Import tools from AGIS/Physis/Excel; April-June window |
| 7-in-10 implementation failure rate | High | Process-first onboarding; white-glove for first 10; **[Albor Agtech]** |

---

### SECTION 1: Document Metadata (Write LAST)

**Tasks**: T039-T042 | **FRs**: FR-016, FR-017 | **SC**: SC-009

**Header**: Version 1.0 | Date 2026-03-15 | Status "Vision Document -- Committed"

**Implementation Progress table**: COPY VERBATIM from v0.4 (lines 13-28). Do not edit.

**Feature Branch History table**: Copy all 25 rows (001-025) from v0.4. Update branch descriptions
to reflect acopio vertical context where appropriate. Do NOT delete any rows.

---

## Preserve vs Replace Matrix (from v0.4)

### PRESERVE (adapt wording for acopio context)
| v0.4 Content | Action |
|-------------|--------|
| Implementation Progress table (lines 13-28) | Copy verbatim -- metrics still accurate |
| Feature Branch History table (lines 238-261) | Copy verbatim -- 25 rows (001-025) |
| 4 Ironclad design principles (lines 124-129) | Adapt wording + add 2 new |
| Implementation Summary (lines 190-196) | Copy verbatim |

### REPLACE (rewrite completely)
| v0.4 Content | Why |
|-------------|-----|
| Strategic Purpose + Vision Statement | Generic: "Transform traditional SMB retailers..." |
| Positioning Map (Mermaid) | Generic cloud vs offline quadrant |
| Pain Points (Mermaid + analysis) | Generic retail pains |
| Vision Statement 4.1 | Generic retail quote |
| ICP section | Lists 4 candidates "under evaluation" |
| User Archetypes (Mermaid) | Cashier, Owner, Logistics (generic) |
| Module table | 16 generic modules (POS, Ventas, Electron) |
| Success Metrics | Generic retail KPIs |
| "Strategic Inflection Point" box | References "under evaluation" -- DELETE |

---

## RAG Query Protocol

**Primary rule**: research.md has ALL verified facts. Do NOT re-query unless you find a specific claim
you need to verify or expand.

**If additional depth needed during writing**:
```bash
# Single query
.venv/bin/python scripts/qdrant/qdrant_search.py -q "QUERY" -l 5

# Recommended supplementary queries (only if research.md is insufficient):
.venv/bin/python scripts/qdrant/qdrant_search.py -q "acopio software market competitors Algoritmo AGIS Physis" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "AGIS AmericaGIS competitive analysis technology VB6 desktop" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "acopiador pain points regulatory compliance CTG SISA" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "market sizing geographic distribution acopiadores provinces" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "AI machine learning grain storage silo prediction optimization" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "accountant contador rural channel strategy grain operations" -l 5
```

**NEVER** read full research PDFs. All domain knowledge via RAG or research.md inline data.

---

## Critical Pitfalls to Avoid

1. **AGIS client count**: Use "2,000+ acopio clients" [Research 4.2]. The "3,000+" figure is for ALL product lines. The acopio-specific number is 2,000+.

2. **Connectivity framing**: Do NOT write "acopio plants have no internet." Write: "Brief outages during peak harvest halt real-time CTG/SISA operations." Plants are in towns with adequate connectivity; the issue is intermittent disruption during high-load periods.

3. **AI in MVP**: ALL AI capabilities are Phase 3-4. No ML feature appears in Phase 1 or 2.

4. **Generic value props**: Every gain in S6 must reference a specific GRAVITEA capability (CAEA mode, tolerance tables, Rust merma engine) -- not just "faster" or "easier."

5. **Module names**: Use EXACT Spanish names from Descripción General del Producto.md. Watch accents: "RECEPCIÓN" not "RECEIPCION".

6. **Missing disruption math**: In S8, the `2 x $90 = $180 vs $500-800` comparison MUST include the actual arithmetic. Don't just say "cheaper."

7. **Villa María / AGIS tension**: The beachhead section (S7) MUST acknowledge that AGIS is also HQ'd in Villa María. Name both the opportunity AND the risk.

8. **Phase numbering**: S4 roadmap has 4 phases. They must match throughout: Phase 1 (Romaneo), Phase 2 (Liquidaciones), Phase 3 (Canje), Phase 4 (AI). Do not renumber or skip.

---

## Review Checklist (run after all sections complete)

### Full-Text Searches
```bash
# DL-001: Zero generic retail language
grep -i "hardware store\|beverage distributor\|cashier\|under evaluation\|retail store" \
  "Docs/Project Blueprint/Product Vision & Scope.md"
# Expected: no output

# AGIS client count verification
grep -i "AGIS" "Docs/Project Blueprint/Product Vision & Scope.md" | grep -i "clients\|acopio"
# Verify: shows "2,000" not "3,000"

# Citation coverage
grep "\[Research" "Docs/Project Blueprint/Product Vision & Scope.md" | wc -l
# Expected: 10+ citation references

# Mermaid diagram count
grep -c '```mermaid' "Docs/Project Blueprint/Product Vision & Scope.md"
# Expected: 5 or more

# Line count (DL-004)
wc -l "Docs/Project Blueprint/Product Vision & Scope.md"
# Expected: 500-1000 lines

# Feature branch row count
grep -c "^| 0[0-2][0-9]" "Docs/Project Blueprint/Product Vision & Scope.md"
# Expected: 25
```

### Cross-Section Consistency (T048)
- [ ] Module names S4 vs Descripción General -> match exactly (8 modules)
- [ ] ARPU S10 ($360) = pricing S8 (4 x $90) -> internally consistent
- [ ] AI features S9 ALL in Phase 3-4 per S4 roadmap -> no Phase 1/2 AI
- [ ] Connectivity nuance S3 vs S11 -> same message (plants in towns, brief harvest outages)
- [ ] Contador channel S7 -> matches Contador Rural persona in S5
- [ ] SC-005 3-axes check: no competitor occupies cloud-native + offline-first + acopio-depth simultaneously

### Section Acceptance (from contracts/document-structure.md)
- [ ] S1: Version "1.0", 25 branch rows, 6 Ironclad principles (2 new)
- [ ] S2: Vision has "acopiadores", "offline-first", "regulatory compliance"
- [ ] S3: TAM/SAM/SOM cited [6.1]; 6+ profiles; AGIS "2,000+"; govt box
- [ ] S4: 8 modules (exact names); offline-first = differentiator #1; 4-phase roadmap
- [ ] S5: 5 personas; no generic roles; ICP defined
- [ ] S6: 6 pain-gain pairs; "CAEA" in connectivity row
- [ ] S7: "Invitar a tu contador" present; Villa María first + AGIS risk
- [ ] S8: $90/$75 both present; disruption math with arithmetic
- [ ] S9: 6+ AI capabilities; all Phase 3-4; model architectures named
- [ ] S10: 3 KPI categories; harvest > 10/hour; ARPU $360
- [ ] S11: 6 risks; 7/10 statistic + [Albor Agtech]; offline-first in connectivity mitigation

### Self-Contained Test (DL-005)
A reader unfamiliar with the project can answer WITHOUT consulting any other document:
1. What is the target market? -> Argentine acopiadores de granos
2. What is the MVP scope? -> Romaneo-to-Position loop
3. Which phase does grain quality analysis belong to? -> Phase 1 (MVP)
4. Which persona benefits from balanza integration? -> Balancero/Recibidor

---

## Done Criteria

The document is DONE when ALL of the following are true:

1. All 17 FRs (FR-001 through FR-017) from spec.md are satisfied
2. All 9 SCs (SC-001 through SC-009) from spec.md pass
3. All 7 checkpoint gates from `Docs/PROMPTS/spec-01-vision/01-plan.md` are fully checked
4. Full Document Acceptance Checklist from `contracts/document-structure.md` all boxes marked
5. `Docs/Project Blueprint/Product Vision & Scope.md` updated in-place (v0.4 -> v1.0)
6. Zero references to generic retail, evaluation phase, or candidate verticals
7. All Mermaid diagrams (minimum 5) tested and rendering in GitHub Markdown preview
8. Every quantified market claim has a `[Research X.Y]` citation
9. Module names match `Descripción General del Producto.md` exactly
10. Document is 500-1000 lines and self-contained (DL-005 test passes)

---

## Execution Summary

| Phase | Tasks | What to Write | Time Est. |
|-------|-------|--------------|-----------|
| 1 Setup | T001-T005 | Read sources, backup v0.4, stub header | 30 min |
| 2 Foundation (S3) | T006-T013 | Market sizing, competitors, pain points, tech adoption | 2 hr |
| 3 US1 (S2+S4+S5) | T014-T024 | Vision, modules, flow, personas | 2 hr |
| 4 US2 (S6) | T025-T028 | Value proposition canvas | 30 min |
| 5 US3 (S7+S8) | T029-T034 | GTM strategy + pricing | 1.5 hr |
| 6 US4 (S9+S10+S11) | T035-T038 | AI roadmap, KPIs, risks | 1.5 hr |
| 7 US5 (S1) | T039-T042 | Metadata, branch history, traceability | 30 min |
| 8 Polish | T043-T050 | Full validation, cleanup | 30 min |
| **Total** | **50 tasks** | **11 sections + validation** | **~9 hr** |
