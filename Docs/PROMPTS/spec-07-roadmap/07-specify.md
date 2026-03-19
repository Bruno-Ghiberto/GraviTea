# spec-07: Roadmap — Specify Context Prompt

## Feature Description

Produce `Docs/Project Blueprint/Roadmap.md` v1.0 — the master strategic execution plan for
GraviTea Acopio ERP. This document synthesises all prior blueprint specs (01-06) into a
time-phased delivery plan with milestones, a go-to-market (GTM) strategy, a risk register,
and measurable success KPIs.

The Roadmap is the single artifact that answers: **"What are we building, in what order,
for whom, and how do we know we've succeeded?"** It is addressed to a technical/founding
team audience (Bruno + one other dev) and must be actionable with a team of two.

---

## Current State

No `Docs/Project Blueprint/Roadmap.md` exists. All inputs are complete:

| Input doc | Status |
|-----------|--------|
| `Docs/Project Blueprint/Product Vision & Scope.md` | v1.0 complete |
| `Docs/Project Blueprint/PRD.md` | v1.0 complete |
| `Docs/Project Blueprint/Data Model & Domain Model.md` | v1.0 complete (spec-03) |
| `Docs/Project Blueprint/Architecture Decision Records (ADR).md` | v1.0 complete (spec-04) |
| `Docs/Project Blueprint/High-Level Design (HLD).md` | v1.0 complete (spec-05) |
| `Docs/Project Blueprint/REST API Design.md` | v1.0 complete (spec-06) |

The `specs/007-acopio-roadmap/` directory does not yet exist and will be created by
`/speckit.specify`.

---

## Research Inputs

### RAG Queries (run these FIRST — do NOT read full files)

```bash
# Market sizing and competitive landscape for GTM framing
.venv/bin/python scripts/qdrant/qdrant_search.py \
    -q "acopio software market competitors AGIS switching window" -l 5

# Acopiador pain points for Phase 1 prioritisation
.venv/bin/python scripts/qdrant/qdrant_search.py \
    -q "acopiador pain points technology adoption offline connectivity" -l 5

# Market size TAM for KPI section
.venv/bin/python scripts/qdrant/qdrant_search.py \
    -q "market sizing acopiadores argentina TAM revenue budget" -l 5

# GTM channel: contador rural flywheel
.venv/bin/python scripts/qdrant/qdrant_search.py \
    -q "contador rural accountant channel strategy GTM acopiador" -l 5

# Phase 2 WSLPG complexity
.venv/bin/python scripts/qdrant/qdrant_search.py \
    -q "WSLPG liquidacion primaria granos SOAP integration complexity" -l 4

# Phase 3 AI/ML features
.venv/bin/python scripts/qdrant/qdrant_search.py \
    -q "AI ML grain ERP predictive quality merma intelligent features" -l 4

# Trade events for GTM calendar
.venv/bin/python scripts/qdrant/qdrant_search.py \
    -q "Expoagro Agroactiva trade events grain acopiador calendar" -l 4
```

### Source Documents (for reference only — prefer RAG)

| ID | Path | Relevant sections |
|----|------|-------------------|
| 4.1 | `Docs/Researches/Markdown/4.1 Comprehensive Acopio Software Market Map.md` | Top Pain Points, Market Overview |
| 4.2 | `Docs/Researches/Markdown/4.2 AGIS-AmericaGIS Deep Competitive Analysis.md` | Key Takeaways, Competitive Landscape Comparison |
| 4.3 | `Docs/Researches/Markdown/4.3 Acopiador Pain Points and Technology Adoption.md` | Findings at a Glance, Strategic Implications |
| 6.1 | `Docs/Researches/Markdown/6.1 Market Sizing -- Geographic Distribution of Acopiadores.md` | Size Distribution, Typical Revenue |
| 6.2 | `Docs/Researches/Markdown/6.2 Accountant (Contador Rural) Channel Strategy.md` | Distribution strategy |
| 6.3 | `Docs/Researches/Markdown/6.3 Trade Associations and Industry Events.md` | Acopiador-Specific Events |
| 9.1 | `Docs/Researches/Markdown/9.1 AI-ML Applications for Grain Storage Operations.md` | Strategic Implications, feature categories |

### Critical Domain Facts (inlined — minimum context)

**Market:**
- ~1,073 private acopio companies with ~1,622 storage plants in Argentina (4.3)
- Primary region: Pampas (Buenos Aires, Córdoba, Santa Fe, Entre Ríos, La Pampa)
- Typical software budget: USD 150–500/month for SMB; USD 500–2,000/month for medium acopios
- TAM (addressable SMB): ~800 companies × ~$300/month avg = ~$2.9M ARR potential

**Competition:**
- AGIS (AmericaGIS, Villa María): 2,000+ agro clients, VB6/.NET desktop, no web/mobile for acopio
- Algoritmo S.A. (Rosario): most dangerous direct competitor — Silohub web integration, large grain volumes
- Agrobit (SAP partner): enterprise only ($50k-200k+ implementation), not a direct SMB threat
- AgroSistemas (Mar del Plata): desktop, ISO 9001, full AFIP grain integrations

**Switching:**
- Post-soybean harvest (April–June) = optimal customer switching window — operationally quiet
- Data migration is the #1 switching barrier — structured import from AGIS/Excel = conversion lever
- Owner + external accountant = dual decision-makers; accountant must be won as an ally first
- "Resistance to change" is internal — younger operators (ACA Jóvenes network) are early adopters

**Connectivity & offline:**
- 44% of acopiadores report "regular" connectivity only; 40% of rural locations have none at all
- Offline-first = largest single technical differentiator vs all desktop-only competitors

**Regulatory velocity:**
- RG 5689/2025 + RG 5821/2026 added real-time ARCA compliance requirements
- Vendor that ships compliant updates first after a new RG wins trust → compliance velocity = moat

**Phase 2 complexity:**
- WSLPG (liquidación primaria) = SOAP service, complex XML, 20+ fields — 4-6 weeks minimum effort
- CPE/WSCPE already in Phase 1 (integrated into Romaneo via PendingOperation async queue, ADR-027)

**Phase 3 AI features (from 9.1):**
- Predictive merma modelling (humidity × grain type × ambient conditions)
- Grain quality grading assistance (CV / machine vision for future)
- Price optimisation signals from MAT market data
- Storage condition anomaly detection

---

## Functional Requirements

**FR-071 — Three-phase delivery plan**
The Roadmap MUST define exactly three product phases with discrete scopes:
- Phase 1 (MVP): Core grain reception → storage → producer position loop (specs 09-12)
- Phase 2 (Advanced): WSLPG liquidación + Agronomia adaptation + Reports + Canje (specs 13-16)
- Phase 3 (Intelligence): AI/ML features + multi-tenant growth + marketplace integrations

**FR-072 — Implementation spec traceability**
Each implementation spec (09-16) MUST appear in the Roadmap mapped to its phase, deliverable
path, and responsible module (`apps/acopio/`, `apps/cuentas/`, `apps/facturacion/`, `rust/`).

**FR-073 — Milestone dependency graph (Mermaid)**
A Gantt-style or dependency graph Mermaid diagram MUST show the spec execution order and
the critical path from spec-09 to first customer go-live.

**FR-074 — GTM calendar with switching window**
A GTM section MUST name the contador rural channel as the primary distribution flywheel and
anchor the first sales campaign to the April–June post-soybean harvest switching window.

**FR-075 — Risk register (≥8 risks)**
A risk register with ≥8 risks MUST cover: regulatory change velocity, ARCA SOAP instability,
connectivity/offline edge cases, data migration complexity, team capacity (2 devs), and
competitor response.

**FR-076 — Measurable success KPIs**
A KPIs section MUST define ≥6 measurable metrics. No hedging language ("improve", "increase",
"better"). Each KPI must have a numeric target and a measurement method.
Examples: "5 paying customers by end of Phase 1", "≤2 hours to migrate an AGIS customer".

**FR-077 — Phase 1 go-live criteria (Definition of Done)**
The Phase 1 section MUST define explicit go-live criteria — a checklist of conditions that
must be true before the product is offered to the first paying customer.

**FR-078 — Resource requirements for a 2-person team**
A team section MUST explicitly address 2-dev team constraints, noting which tasks can be
parallelised between spec tracks and which are serial bottlenecks.

**FR-079 — Document changelog and version**
§1 MUST contain version 1.0 metadata with date, status (Draft → Active), and a changelog
table. Blockquote format matching the rest of the blueprint series.

---

## Non-Functional Requirements

**NF-071 — Synthesis, not repetition**
The Roadmap MUST synthesise across prior specs — not copy-paste from them. Each section
must add executive-level framing not already present in the source spec.

**NF-072 — Zero TBD/TODO**
No unresolved placeholders. If a date is genuinely unknown, express it as a relative offset
from a defined milestone (e.g., "T+8 weeks from spec-09 merge").

**NF-073 — Consistent terminology**
Use the canonical terms established in the Data Model (spec-03) and ADRs (spec-04):
romaneo, merma, CPE, liquidación primaria, peso neto, grado asignado, bonificación/rebaja,
posición consolidada, cuenta corriente de productores.

**NF-074 — No Python/SQL code**
This is a blueprint doc. No implementation code, no SQL, no shell commands in the body.
Mermaid diagrams are the only allowed non-prose blocks (except the §12 KPI tables).

---

## Target Document Structure

The Roadmap MUST follow this section structure exactly:

```
§1  Document Metadata
    — Version 1.0, status, date, changelog table
    — Blockquote: "This document is the master strategic plan …"

§2  Executive Summary
    — 2–3 paragraph narrative: what we're building, for whom, the market window
    — Key premise: cloud-native offline-first ERP for Argentine acopiadores, 2-dev team

§3  Strategic Context
    §3.1 Market opportunity (TAM, ~1,073 targets, price point)
    §3.2 Competitive positioning (AGIS VB6 gap → GraviTea web moat)
    §3.3 Regulatory tailwind (ARCA velocity as recurring moat)
    §3.4 Window of opportunity (post-harvest switching window, generational shift)

§4  Product Phases Overview
    — Summary table: Phase | Scope | Target date | Entry criteria | Exit criteria
    — Three phases at a glance

§5  Phase 1 — MVP: Core Grain Reception
    §5.1 Scope (specs 09-12: Grain Reference, Romaneo Core, Storage & Position, Producer Accounts)
    §5.2 Critical path (dependency order: 09 → 10 → 11 ∥ 12)
    §5.3 Deliverables table (spec | module path | key models | REST endpoints)
    §5.4 Go-live criteria (Definition of Done checklist)
    §5.5 Target timeline (relative: T+0 to T+N weeks from spec-09 start)

§6  Phase 2 — Advanced Operations
    §6.1 Scope (specs 13-16: Agronomia, WSLPG, Reports, Canje)
    §6.2 Trigger (conditions that unlock Phase 2: X paying customers, X romaneos processed)
    §6.3 Deliverables table
    §6.4 WSLPG integration notes (SOAP complexity, effort estimate, pyafipws reference)

§7  Phase 3 — Intelligence & Scale
    §7.1 AI/ML feature candidates (predictive merma, price signals, quality grading)
    §7.2 Multi-tenant growth levers (white-label, cooperative chains)
    §7.3 Data readiness prerequisites (AI-ready data model from ADR-033/034/035)
    §7.4 Trigger (conditions that unlock Phase 3)

§8  Milestone & Dependency Graph
    — Mermaid diagram #1: Gantt or timeline (spec-09 through Phase 3 trigger)
    — Mermaid diagram #2: Spec dependency graph (spec-01 → spec-09 → … → Phase 3)
    — Critical path annotation

§9  Go-to-Market Strategy
    §9.1 Primary channel: contador rural flywheel
        — Free accountant portal → accountant recommends to 3–5 clients
        — Target: 10 enrolled contadores rurales before first public launch
    §9.2 Sales motion timeline
        — Pre-harvest (Jan–Mar): Build pipeline via contadores
        — Post-harvest (Apr–Jun): Primary conversion window
        — Off-season (Jul–Dec): Onboarding, data migration, retention
    §9.3 Pricing tiers (placeholder: SMB $199–$499/month, medium $499–$999/month)
    §9.4 Migration playbook (AGIS data import, Excel import, ≤2-hour onboarding target)
    §9.5 Trade events calendar (Expoagro, Agroactiva, CONINAGRO, BCBA events)

§10 Risk Register
    — Table: Risk | Probability | Impact | Mitigation
    — ≥8 risks covering regulatory, ARCA SOAP, offline, migration, team, competitor

§11 Success Metrics & KPIs
    — Table: KPI | Target | Measurement method | Phase
    — ≥6 KPIs, all numeric, no hedging language

§12 Team & Resource Requirements
    §12.1 2-dev team model (who owns what, parallelisation opportunities)
    §12.2 External dependencies (contador rural network, ARCA test environment)
    §12.3 Tooling requirements (no new infra beyond what HLD defines)
```

**Section count**: 12 §-level sections (§1–§12), with subsections as listed.
**Mermaid diagrams**: exactly 2 in §8 (Gantt + dependency graph), optionally 1 more in §4.
**Tables**: ≥1 in §4 (phases overview), §5.3 (deliverables), §6.3, §8 annotation, §10, §11.

---

## Acceptance Criteria

**AC-071 — Version metadata**
`grep -c "Version 1.0"` returns ≥2 (header + changelog row).

**AC-072 — Three phases defined**
`grep -c "Phase 1\|Phase 2\|Phase 3"` returns ≥15 across the document.

**AC-073 — All MVP specs present**
`grep -c "spec-09\|spec-10\|spec-11\|spec-12"` returns ≥8 (each referenced in ≥2 places).

**AC-074 — Phase 2 specs present**
`grep -c "spec-13\|spec-14\|spec-15\|spec-16"` returns ≥4.

**AC-075 — Mermaid diagrams**
`grep -c '```mermaid'` returns ≥2.

**AC-076 — Contador rural GTM**
`grep -i "contador"` returns ≥4 matches.

**AC-077 — Post-harvest switching window**
`grep -i "abril\|june\|post-soja\|cosecha\|switching window\|post-harvest"` returns ≥2 matches.

**AC-078 — Risk register depth**
`grep -c "Probability\|Alto\|Medio\|Bajo\|High\|Medium\|Low"` returns ≥8 (≥8 risk rows).

**AC-079 — No TBD/TODO**
`grep -ci "TBD\|TODO\|placeholder"` returns 0.

**AC-0710 — Measurable KPIs**
`grep -c "KPI\|paying customer\|onboarding\|churn\|ARPU\|NPS"` returns ≥6.

**AC-0711 — No code blocks**
`grep -c '```python\|```sql\|```bash'` returns 0 (only mermaid blocks allowed).

**AC-0712 — Headings count**
`grep -c '^#'` returns ≥35 (§1–§12 with all subsections).

---

## Dependencies

### This spec depends on:
| Spec | Document | What is consumed |
|------|----------|-----------------|
| spec-01 | Product Vision & Scope | Strategic goals, target customer, core value proposition |
| spec-02 | PRD | User stories, feature priorities, phase definitions |
| spec-03 | Data Model & Domain Model | Module structure (`acopio`, `cuentas`), entity names |
| spec-04 | Architecture Decision Records | ADRs 001-035 — constraints on phases and tech choices |
| spec-05 | High-Level Design | Architecture milestones, offline-first design decisions |
| spec-06 | REST API Design | API scope per phase (Phase 1 endpoints vs Phase 2 deferred) |

### This spec blocks:
- spec-08a (ARCA Grain Integration Guide) — roadmap phase framing informs when ARCA features ship
- spec-08b (AI/ML Feature Roadmap) — Phase 3 scope in the Roadmap defines the input for spec-08b
- spec-08c (SRS) — the SRS derives from PRD + Roadmap milestones

### Notes:
- All implementation specs (09+) do NOT depend on this Roadmap — they depend on spec-03.
- The Roadmap is a strategic-planning artifact for the founding team, not a technical prerequisite.
- If PRD (spec-02) is updated materially, re-run `/sc:improve` on this context file first.
