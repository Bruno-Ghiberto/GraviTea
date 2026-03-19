# Document Interface Contract: Product Vision & Scope v1.0

**Phase 1 output for**: `specs/001-acopio-vision/plan.md`
**Contract type**: Document structure specification
**Target file**: `Docs/Project Blueprint/Product Vision & Scope.md`
**Date**: 2026-03-15

---

## Contract Purpose

This contract specifies the mandatory structure, content requirements, and acceptance tests for each
section of the Product Vision & Scope v1.0 document. It serves as the verifiable interface between
the planning artifacts and the final deliverable.

**Acceptance criteria mapping**: Each contract item below maps to a spec.md SC (Success Criterion)
or FR (Functional Requirement). The document is DONE when all contract items are satisfied.

---

## Document-Level Contracts

### DL-001: No Generic Retail Language

**Maps to**: SC-003, FR-001
**Test**: Full-text search of the final document

```text
MUST NOT CONTAIN (case-insensitive):
- "hardware store"
- "beverage distributor"
- "cashier"
- "under evaluation"
- "retail store"
- "point of sale" (except in out-of-scope list)
- "POS" (except in out-of-scope list)
```

**Pass condition**: Zero matches for any of the above strings.

---

### DL-002: Research Citation Coverage

**Maps to**: SC-002
**Test**: Manual audit of all quantified claims

```text
ALL of the following claim types MUST have [Research X.Y] citation:
- Market size figures (TAM/SAM/SOM)
- Competitor client counts
- Pain point statistics (%, adoption rates)
- Technology adoption figures
- AI model accuracy metrics
```

**Pass condition**: No unverified numerical claim exists in the document.

---

### DL-003: Mermaid Diagram Renderin

**Maps to**: SC-007
**Test**: Copy each Mermaid block into a Mermaid live editor or GitHub preview

```text
REQUIRED DIAGRAMS (minimum 5, up to 6):
1. Competitive positioning quadrant (S3)
2. Module map (S4)
3. Core operational flow (S4)
4. Persona hierarchy (S5)
5. Phased roadmap (S4)
6. Value proposition canvas (S6) — optional but recommended
```

**Pass condition**: All diagrams render without syntax errors and are legible at standard preview width.

---

### DL-004: Document Length

**Maps to**: plan.md target
**Test**: Word count / line count of final document

```text
TARGET: 600-800 lines (GitHub Markdown rendered)
MINIMUM: 500 lines (below this = content gaps)
MAXIMUM: 1000 lines (above this = excessive detail for a vision doc)
```

**Pass condition**: Final document is within 500-1000 lines.

---

### DL-005: Self-Contained Readability

**Maps to**: SC-001
**Test**: Have a reader unfamiliar with the project answer 4 questions without external docs

```text
A reader MUST be able to answer WITHOUT consulting any other document:
Q1: What is the target market? (Answer: Argentine acopiadores de granos)
Q2: What is the MVP scope? (Answer: Romaneo-to-Position loop)
Q3: Which phase does grain quality analysis belong to? (Answer: Phase 1 — MVP)
Q4: Which persona benefits from the balanza integration? (Answer: Balancero/Recibidor)
```

**Pass condition**: All 4 answers are present and unambiguous from the document text alone.

---

## Section-Level Contracts

### S1-CONTRACT: Document Metadata & Preamble

**Maps to**: FR-016, FR-017, SC-009

```yaml
required_fields:
  version: "1.0"
  date: "2026-03-15"

required_sections:
  implementation_progress_table:
    rows_minimum: 5
    must_contain:
      - "Backend Core"
      - "Rust/PyO3"
      - "2,500+"
      - "79 API paths"

  feature_branch_history:
    rows: 25
    row_range: "001-025"
    test: "Count rows — must be exactly 25"

  ironclad_principles:
    count: 6
    new_required:
      - "Regulatory Automation"
      - "AI-Ready Data Architecture"
    existing_required:
      - "Offline-First"
      - "Transactional Integrity"

acceptance_test:
  - Search for "0.4" → must not appear as document version
  - Count Ironclad principles → must be exactly 6
  - Count branch history rows → must be exactly 25
  - Search "Regulatory Automation" → must appear as principle name
```

---

### S2-CONTRACT: Strategic Purpose & Vision

**Maps to**: FR-001, SC-003

```yaml
required_content:
  vision_statement:
    must_contain:
      - "acopiadores de granos"
      - "offline-first"
      - "regulatory compliance"
    must_not_contain:
      - "SMB retailers"
      - "traditional businesses"
      - "horizontal"

  vertical_commitment:
    tone: "declarative, present tense"
    must_not_contain:
      - "under evaluation"
      - "considering"
      - "potential"
      - "may"

acceptance_test:
  - Paste vision statement into readability tool → no passive hedging
  - Search "under evaluation" → zero results
  - Search "acopiadores" → appears in vision statement
```

---

### S3-CONTRACT: Market Context

**Maps to**: FR-002, FR-003, FR-004, SC-002, SC-005

```yaml
market_sizing:
  TAM:
    enterprises: "~1,259"
    plants: "~2,458"
    citation: "[Research 6.1]"
  SAM:
    enterprises: "~1,073"
    plants: "~1,622"
    citation: "[Research 6.1]"
  SOM:
    regions: ["Córdoba", "Santa Fe"]
    cordoba_members: 81
    santafe_members: 58
    citation: "[Research 6.1]"

competitive_landscape:
  diagram_type: "Mermaid quadrant chart"
  axes:
    x: "Deployment model (Desktop-only → Cloud-native)"
    y: "Vertical depth (Generic → Acopio-operational-depth)"
  gravitea_position: "upper-right quadrant (alone)"

competitor_profiles:
  minimum: 6
  target: 11
  required_fields_per_profile:
    - location
    - founding_year_or_history
    - platform_type
    - client_count_or_reach
    - strengths
    - key_weakness
  required_competitors:
    - "Algoritmo"
    - "AGIS"
    - "Physis"
    - "AgroAcopio"
    - "Finnegans GO Granos"
    - "Agrosistemas"
  AGIS_client_count: "2,000+"  # CRITICAL: NOT 3,000+
  citation_required: "[Research 4.1]"

government_systems_box:
  label: "must integrate, not compete"
  required_entries:
    - "SIO Granos"
    - "SISA"
    - "BolsaTech"

market_segmentation:
  tiers: 4
  must_have_percentages: true

pain_points:
  count: 6
  required_regulatory_citations:
    - "RG 3419/2012"
    - "RG 5689/2025"
    - "RG 3419"
  connectivity_nuance: "plants in towns (not remote fields) — brief outages during harvest"

acceptance_test:
  - Verify TAM figure: "1,259" present in S3
  - Verify AGIS entry: "2,000+" not "3,000+"
  - Verify government box is labeled "must integrate" or "mandatory"
  - Count competitor profiles → minimum 6 individual entries
  - Verify [Research 6.1] citation appears with TAM/SAM/SOM
  - Verify connectivity nuance is present (not just "40.2%")
```

---

### S4-CONTRACT: Product Vision & Scope

**Maps to**: FR-007, FR-008, FR-009, FR-013, SC-008

```yaml
module_map:
  diagram_type: "Mermaid"
  module_count: 8
  required_names:  # Spanish names as in Descripcion General
    - "RECEPCIÓN"
    - "ALMACENAMIENTO"
    - "CALIDAD"
    - "CUENTAS CORRIENTES"
    - "LIQUIDACIONES"
    - "FACTURACIÓN"
    - "AGRONOMÍA"
    - "CANJE"

operational_flow:
  diagram_type: "Mermaid flowchart"
  required_steps:
    - "CPE/CTG"
    - "peso bruto" or "gross weight"
    - "calidad" or "quality"
    - "merma"
    - "Boleta de Romaneo"
    - "Silo" or "almacenamiento"
    - "Cuenta Corriente" or "producer account"

mvp_scope:
  phase: 1
  name: "Romaneo-to-Position loop"
  required_components:
    - "reception" or "recepción"
    - "quality analysis" or "calidad"
    - "storage assignment" or "almacenamiento"
    - "producer account" or "cuenta corriente"

technical_differentiators:
  count: 6
  first_must_be: "Offline-first"
  required:
    - "offline-first"
    - "Rust"
    - "PostgreSQL RLS"
    - "ARCA"
    - "AI-ready"
    - "AES-256-GCM"

phased_roadmap:
  diagram_type: "Mermaid"
  phases: 4
  phase_assignments:
    phase_1: ["Romaneo", "Position"]
    phase_2: ["Liquidaciones", "WSLPG"]
    phase_3: ["Canje", "Agronomía"]
    phase_4: ["AI"]

out_of_scope:
  minimum_items: 6
  required_items:
    - "POS" or "punto de venta"
    - "farm management" or "agricultura de campo"

acceptance_test:
  - Module map Mermaid renders in GitHub preview
  - Count module names → exactly 8
  - Verify "offline-first" is first in differentiators list
  - Verify Phase 4 contains "AI" (not Phase 1, 2, or 3)
  - Verify operational flow includes "merma" step
  - Cross-check module names against Descripcion General del Producto.md
```

---

### S5-CONTRACT: User Personas

**Maps to**: FR-005, SC-004

```yaml
persona_count: 5
required_personas:
  - name: "Dueño/Gerente"
    primary_jtbd: "remote grain position"
  - name: "Balancero/Recibidor"
    primary_jtbd: "truck reception speed"
  - name: "Laboratorista"
    primary_jtbd: "quality grading without spreadsheets"
  - name: "Administrador/Contable"
    primary_jtbd: "automatic regulatory filing"
  - name: "Contador Rural"
    primary_jtbd: "multi-client fiscal visibility"

persona_card_fields:
  required:
    - role_name
    - primary_jtbd
    - key_pain
    - tech_comfort_level

hierarchy_diagram:
  type: "Mermaid"
  must_show: "persona → module relationships"

ICP_definition:
  required_attributes:
    - "independent" or "non-cooperative"
    - "1-5 plants" or equivalent size
    - "Pampas" or regional reference
    - generational transition reference

acceptance_test:
  - Count persona sections → exactly 5
  - Verify no generic roles: search "cashier", "clerk", "store" → zero
  - Verify hierarchy Mermaid renders
  - Verify each persona has JTBD + pain + tech comfort
  - ICP definition present and domain-specific
```

---

### S6-CONTRACT: Value Proposition Canvas

**Maps to**: FR-006

```yaml
pain_gain_pairs: 6
required_pairs:
  - pain: "regulatory compliance"
    gain: "automatic" or "automation"
  - pain: "tax withholding" or "retenciones"
    gain: "automatic calculation" or "instant"
  - pain: "inventory reconciliation"
    gain: "real-time grain position"
  - pain: "producer account disputes"
    gain: "transparent quality grading"
  - pain: "manual data entry"
    gain: "weighbridge integration"
  - pain: "connectivity" or "internet"
    gain: "offline-first" or "CAEA"

visual_format: "Mermaid diagram OR structured table"

acceptance_test:
  - Count pain-gain pairs → exactly 6
  - Verify "CAEA" or "offline" appears in connectivity gain row
  - Verify "retenciones" or "IVA" appears in tax withholding row
```

---

### S7-CONTRACT: Go-to-Market Strategy

**Maps to**: FR-011, SC-006

```yaml
contador_channel:
  client_count_per_estudio: "5-15 acopio"
  referral_flow_name: "Invitar a tu contador"
  free_portal_benefits:
    minimum: 3
    required:
      - "real-time" or "tiempo real"
      - "multi-client" or "múltiples clientes"
  facpce_or_cpce_mention: required

geographic_beachhead:
  first_city: "Villa María"
  progression: ["Córdoba", "Pampas"]
  agis_risk_acknowledged: required  # AGIS also based in Villa María

trade_events:
  minimum: 3
  required_events:
    - name: "A Todo Trigo"
      date: "May 2026"
      location: "Mar del Plata"
    - name: "Sociedad de Acopiadores de Córdoba"
    - name: "Grano SAC" or "Expo Poscosecha"
      location: "Rosario"

switching_strategy:
  window: "April-June"
  rationale: "post-soybean harvest" or "post-cosecha soja"

acceptance_test:
  - Verify "Invitar a tu contador" phrase present
  - Verify "Villa María" is named as first beachhead
  - Verify AGIS risk in Villa María is acknowledged
  - Verify A Todo Trigo has month (May 2026) and location (Mar del Plata)
  - Verify April-June window is named
```

---

### S8-CONTRACT: Pricing Strategy

**Maps to**: FR-012, SC-006

```yaml
pricing:
  monthly_per_seat_usd: 90
  annual_per_seat_usd: 75
  free_tier: "Contador rural portal"

disruption_math:
  small_acopio_seats: 2
  small_acopio_monthly: 180  # 2 × $90
  incumbent_monthly_range: "500-800"
  comparison_must_show_math: true

usd_indexing:
  explicitly_mentioned: required
  rationale: "grain pricing in USD" or "ARS devaluation"

reference_competitor:
  versat_price: "200-640"
  unit: "USD/month"

acceptance_test:
  - Verify "$90" and "$75" both present
  - Verify "500-800" or "$500" incumbent range cited
  - Verify "2 users" × "$90" = "$180" math is shown
  - Verify USD-indexing rationale present
```

---

### S9-CONTRACT: AI Differentiation Roadmap

**Maps to**: FR-010

```yaml
ai_capabilities:
  minimum: 6
  required_capabilities:
    - name: "quality degradation prediction"
      model: "3D-CNN" and "LSTM"
    - name: "silo assignment optimization"
      model: "MILP"
    - name: "price forecasting"
      model: "VMD-SGMD-LSTM" or "XGBoost"
    - name: "weighbridge fraud detection"
      model: "anomaly detection"
    - name: "document intelligence" or "OCR"
      model: "OCR"
    - name: "aeration scheduling"
      model: "SVM-Poly"
  citation: "[Research 9.1]"

phase_positioning:
  all_capabilities_phase: "3 or 4"
  must_not_be_in_mvp: true

ai_ready_link:
  references_ironclad_principle: required  # Link back to principle 6

acceptance_test:
  - Count AI capabilities → minimum 6
  - Verify "Phase 3" or "Phase 4" appears near each capability
  - Verify "3D-CNN" and "LSTM" appear together
  - Verify "MILP" appears
  - Verify [Research 9.1] citation present
  - Verify AI-ready data architecture link to S1 principle
```

---

### S10-CONTRACT: Success Metrics

**Maps to**: FR-014

```yaml
kpi_categories:
  - Operational
  - Adoption
  - Business

operational_kpis:
  harvest_throughput:
    target: "> 10 trucks/hour"
    baseline: "4-6 trucks/hour (manual)"
  sync_latency:
    target: "< 60 seconds"
  system_uptime:
    target: "99.5%"

adoption_kpis:
  balancero_onboarding:
    target: "< 1 day"
  active_user_rate:
    target: "> 80%"
    timeframe: "30 days"

business_kpis:
  stock_discrepancy:
    target: "< 2%"
    baseline: "10-15% (manual)"
    timeframe: "3 months"
  regulatory_compliance:
    target: "> 99.5%"
    scope: "CTG/LPG filing"
  arpu:
    target: "$360/month/tenant"
    basis: "4 seats × $90"

acceptance_test:
  - Verify 3 categories present: Operational, Adoption, Business
  - Verify harvest throughput target > 10/hour with manual baseline
  - Verify ARPU target = $360 (must match 4 × $90 from pricing section)
```

---

### S11-CONTRACT: Risks & Mitigation

**Maps to**: FR-015

```yaml
risk_table:
  minimum_rows: 6
  required_columns:
    - Risk
    - Severity  # High/Medium/Low
    - Mitigation

required_risks:
  - risk: "connectivity"
    severity: "High"
    mitigation_must_mention: "offline-first"
  - risk: "regulatory change"
    severity: "High"
    mitigation_must_mention: "ARCA" or "modular"
  - risk: "competitor response"
    severity: "Medium"
  - risk: "adoption resistance" or "generational"
    severity: "Medium"
  - risk: "data migration"
    severity: "High"
    mitigation_must_mention: "April-June"
  - risk: "implementation failure"
    severity: "High"
    must_contain: "7" and "10"  # "7-in-10" or "7/10"
    attribution: "Albor" or "Agtech"

acceptance_test:
  - Count risk rows → minimum 6
  - Verify "7-in-10" or "7/10" failure statistic present
  - Verify "offline-first" appears in connectivity risk mitigation
  - Verify "April-June" in data migration mitigation
```

---

## Full Document Acceptance Checklist

Run this final checklist before marking the document complete:

### Content Gates

```text
[ ] DL-001: Zero generic retail language (full-text search)
[ ] DL-002: All quantified claims have [Research X.Y] citations
[ ] DL-003: All 5+ Mermaid diagrams render without errors
[ ] DL-004: Document is 500-1000 lines
[ ] DL-005: Self-contained (4-question test passes)
```

### Section Gates

```text
[ ] S1: Version "1.0", 25 branch rows, 6 Ironclad principles (2 new)
[ ] S2: Vision statement has "acopiadores", "offline-first", "regulatory compliance"
[ ] S3: TAM/SAM/SOM cited; 6+ competitor profiles; AGIS = "2,000+" not "3,000+"
[ ] S4: 8 modules (exact names); offline-first is differentiator #1; 4-phase roadmap
[ ] S5: 5 personas; no generic roles; ICP defined
[ ] S6: 6 pain-gain pairs; connectivity row mentions "CAEA" or "offline"
[ ] S7: "Invitar a tu contador" present; Villa María first; A Todo Trigo May 2026
[ ] S8: $90/$75 both present; 2 users = $180 vs $500+ disruption math shown
[ ] S9: 6+ AI capabilities; all Phase 3-4; 3D-CNN + LSTM + MILP + SVM-Poly named
[ ] S10: 3 KPI categories; harvest > 10/hour; ARPU $360 = 4 × $90
[ ] S11: 6 risks; 7/10 statistic; offline-first in connectivity mitigation
```

### Cross-Section Consistency

```text
[ ] Module names consistent between S4 and Descripcion General del Producto.md
[ ] ARPU in S10 ($360) = pricing in S8 (4 × $90)
[ ] AI features in S9 are ALL Phase 3 or 4 (per S4 roadmap)
[ ] Connectivity pain in S3 nuanced consistently with S11 risk
[ ] Contador channel in S7 consistent with persona in S5 (Contador Rural)
```

---

## Spec Traceability Matrix

Maps each contract section to its governing spec requirements:

| Contract | FR | SC | US |
|---------|-----|-----|-----|
| DL-001 | FR-001 | SC-003 | US-1 |
| DL-002 | — | SC-002 | US-2 |
| DL-003 | — | SC-007 | US-1 |
| S1 | FR-016, FR-017 | SC-009 | US-5 |
| S2 | FR-001 | SC-003 | US-1 |
| S3 | FR-002, FR-003, FR-004 | SC-002, SC-005 | US-2, US-4 |
| S4 | FR-007, FR-008, FR-009, FR-013 | SC-008 | US-1, US-5 |
| S5 | FR-005 | SC-004 | US-1 |
| S6 | FR-006 | — | US-2 |
| S7 | FR-011 | SC-006 | US-3 |
| S8 | FR-012 | SC-006 | US-3, US-4 |
| S9 | FR-010 | SC-004 | US-5 |
| S10 | FR-014 | — | US-2 |
| S11 | FR-015 | — | US-2 |
