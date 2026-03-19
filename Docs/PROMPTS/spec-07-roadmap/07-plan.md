# Spec 07: Acopio ERP Roadmap — Plan Context

## Overview

**Target deliverable**: `Docs/Project Blueprint/Roadmap.md` v1.0
**Creates**: New document (no existing file to replace)
**Type**: Blueprint document (strategic planning, not code)
**Spec reference**: `specs/007-acopio-roadmap/spec.md`
**Context reference**: `Docs/PROMPTS/spec-07-roadmap/07-specify.md`

This plan guides the creation of the Roadmap blueprint. The output is a ~800–1,100 line
Markdown file with 12 top-level sections (§1–§12), at least 35 headings, at least 2
Mermaid diagrams, 5+ tables, and zero TBD/TODO placeholders.

The Roadmap is the **master strategic execution plan** for GraviTea Acopio ERP. It
synthesises all prior blueprint specs (01-06) into a time-phased delivery plan that the
founding team can execute with 2 developers. It is not a technical reference — it is a
decision framework.

---

## Content Guidelines

### Tone & Voice

- **Strategic planning document** — assertive and action-oriented
- "Phase 1 ships the following four specs in this order…" not "Phase 1 could include…"
- No hedging: no "TBD", "to be determined", "under consideration"
- Relative timeline offsets from T+0 (spec-09 start date) — no absolute calendar dates
  except for seasonal references (e.g., "April–June post-harvest window")
- Risk register: matter-of-fact, not alarmist; every risk has a named mitigation

### Audience

- **Primary**: Founding team (2 developers) using this doc to sequence work and make
  scope decisions
- **Secondary**: Advisor or early investor evaluating the company's execution plan
- **Tertiary**: A first-hire who needs to onboard without reading all 6 prior specs

### Language

- English throughout, with Spanish domain terms inline where unavoidable:
  romaneo, merma, campaña, CPE, liquidación primaria, posición consolidada,
  cuenta corriente, canje, acopiador, contador rural
- First occurrence of each term per section: include English gloss in parentheses
- Spec numbers use numeric format: spec-09, spec-10 (not "Spec 9" or "SPEC-09")
- Phase numbers use words: Phase 1, Phase 2, Phase 3 (not "phase one" or "Phase I")

### Level of Detail

- **Phase sections (§5–§7)**: Named spec number + module path + 2-3 sentence scope
  description. No implementation code. No field lists.
- **Mermaid diagrams**: Clean and minimal — 8–15 nodes maximum per diagram. No styling.
- **Risk register (§10)**: Table format only. No narrative. 1-line mitigation per risk.
- **KPI section (§11)**: Table format. Numeric targets. No hedging.
- **GTM (§9)**: Narrative + bullet lists. Seasonal anchors. No pricing commitments.

### Conventions to Preserve from Prior Blueprint Docs

- §1 metadata block: blockquote format with `> **Version**` fields + changelog table
- Section headings use `§N` prefix notation: `## §1 Document Metadata`
- Mermaid diagrams wrapped in ` ```mermaid ` fenced blocks — no inline styles
- Tables have spaced pipes and header separator with ≥3 dashes
- Changelog table columns: `| Version | Date | Author | Description |`
- Status progression: `Draft → Active` (not "In Progress", "Review", etc.)

---

## Writing Execution Order

Write sections in this order (NOT top-to-bottom). §2 is written LAST because it
synthesises from all other sections.

```
Step 1: §1 Document Metadata        [boilerplate — ~30 lines]
Step 2: §3 Strategic Context        [market facts from RAG — ~120 lines]
Step 3: §4 Phases Overview          [3-row table + prose — ~60 lines]
Step 4: §5 Phase 1 — MVP            [deepest section — ~180 lines]
Step 5: §6 Phase 2 — Advanced       [~100 lines]
Step 6: §7 Phase 3 — Intelligence   [~80 lines]
Step 7: §8 Milestone & Dependency   [Mermaid ×2 — ~80 lines]
Step 8: §9 Go-to-Market             [~120 lines]
Step 9: §10 Risk Register           [table — ~60 lines]
Step 10: §11 Success Metrics & KPIs [table — ~60 lines]
Step 11: §12 Team & Resources       [~60 lines]
Step 12: §2 Executive Summary       [LAST — synthesises all — ~80 lines]
```

**Why this order**: Phase 1 content (§5) is the most complex and must be written before
the overview table (§4 uses it) or the Mermaid timeline (§8 depends on it). The executive
summary (§2) must reflect all 12 sections, so it is written last.

---

## Section-by-Section Writing Plan

### §1 — Document Metadata

**Source**: Boilerplate + version convention from prior blueprint docs.
**Output length**: ~30 lines
**Content**:
- Blockquote header block:
  ```
  > **Document**: GraviTea Acopio ERP — Roadmap
  > **Version**: 1.0
  > **Status**: Draft
  > **Date**: [today's date]
  > **Authors**: GraviTea founding team
  > **Depends on**: spec-01 through spec-06 (all v1.0)
  ```
- Changelog table: single row (v1.0 — Initial version)
- One-paragraph scope statement: "This Roadmap synthesises…"

**Gate 1 check** (after §1 + §3 + §4):
- `grep -c "Version 1.0"` ≥ 2

---

### §3 — Strategic Context

**Write BEFORE §2 and §4.**
**Source data**:
- RAG query: `"acopio software market competitors AGIS switching window"` → 4.2
- RAG query: `"acopiador pain points technology adoption barriers"` → 4.1, 4.3
- RAG query: `"market sizing geographic distribution acopiadores TAM"` → 6.1
- RAG query: `"regulatory ARCA grain real-time compliance requirements"` → 4.3, 1.x

**Output length**: ~120 lines
**Subsections (§3.1–§3.4)**:

§3.1 Market Opportunity
- ~1,073 private acopio companies, ~1,622 storage plants
- Pampas region concentration (Buenos Aires, Córdoba, Santa Fe)
- Budget range: USD 150–500/month (SMB) to USD 500–2,000/month (medium)
- Rough TAM: ~800 addressable SMB acopios × ~$300/month avg → ~$2.9M ARR addressable

§3.2 Competitive Positioning
- AGIS (AmericaGIS, Villa María): 2,000+ clients, VB6/.NET, desktop-only; no web/mobile
- Algoritmo S.A. (Rosario): most dangerous; Silohub web integration; large grain volumes
- Agrobit (SAP partner): enterprise only ($50k–200k+ impl cost); not an SMB threat
- GraviTea gap: cloud-native + offline-first + weighbridge integration + ARCA velocity
- Data migration as conversion lever: structured AGIS SQL Server → GraviTea import

§3.3 Regulatory Tailwind
- RG 5689/2025 + RG 5821/2026 add real-time ARCA reporting requirements
- Compliance velocity = ongoing moat: first vendor to ship a compliant update wins trust
- CPE/WSCPE integration already in Phase 1 (romaneo async queue, ADR-027)
- WSLPG (liquidación primaria) in Phase 2 — SOAP complexity is a barrier for incumbents

§3.4 Window of Opportunity
- Post-soybean harvest (April–June): operational quiet season for acopiadores
- This is the only low-friction switching window — one harvest cycle = 12-month delay
- Generational shift: younger operators (ACA Jóvenes, family succession) are early adopters
- Cloud-native entrants have a 5–8 year window before AGIS modernises

**Writing rule**: Use data from RAG results; do NOT invent statistics. If a number is
estimated rather than from research, mark it as "(estimated)".

---

### §4 — Product Phases Overview

**Write AFTER §5 (so Phase 1 scope is confirmed).**
**Source data**: spec.md FR-001, FR-008; README.md spec catalog (waves 5-6).
**Output length**: ~60 lines
**Content**:
- 1-paragraph narrative introducing the 3-phase model
- Summary table:

  | Phase | Name | Specs | Entry Criteria | Exit Criteria / Trigger to next |
  |-------|------|-------|---------------|----------------------------------|
  | 1 | Core Grain Reception MVP | 09–12 | Specs 01-08 complete | ≥1 paying customer, ≥50 romaneos processed |
  | 2 | Advanced Operations | 13–16 | ≥5 paying customers; Phase 1 stable ≥60 days | ≥10 customers; WSLPG live |
  | 3 | Intelligence & Scale | TBD | ≥20 customers; AI data pipeline ready | — |

- Note: trigger conditions are explicitly from spec FR-008

---

### §5 — Phase 1: Core Grain Reception (MVP)

**The most critical section — write this before §6 and §7.**
**Source data**:
- spec.md FR-001, FR-002, FR-003, FR-009
- README.md spec catalog (Wave 5: specs 09-12)
- Serena memory: `spec-03/acopio-data-model-complete` (module paths + entities)
- Serena memory: `session-2026-03-17-spec06-api-design-complete` (Phase 1 endpoints)
- REST API Design §13 endpoint summary (Phase 1 endpoints)

**Output length**: ~180 lines
**Subsections (§5.1–§5.5)**:

§5.1 Scope
- 4 implementation specs in one table:

  | Spec | Name | Module | Key Deliverables |
  |------|------|--------|-----------------|
  | 09 | Grain Reference Data | `apps/acopio/` | GrainType, CampanaConfig, ToleranceTable, MermaTable + fixtures |
  | 10 | Romaneo Core | `apps/acopio/` + `rust/gravitea-core/src/merma.rs` | Romaneo, QualityAnalysis, MermaCalculation, CPE (WSCPE async) |
  | 11 | Storage & Position | `apps/acopio/` | StorageUnit, GrainLot, GrainMovement (append-only ledger) |
  | 12 | Producer Accounts | `apps/cuentas/` | ProducerAccount, AccountMovement, FijacionRecord, posición consolidada |

§5.2 Critical Path
- spec-09 MUST be complete before spec-10 (romaneo depends on GrainType FK)
- spec-10 MUST be complete before spec-11 (storage references romaneo)
- spec-11 and spec-12 CAN run in parallel once spec-10 is done
- Mermaid diagram showing this (referenced from §8 — write the note, diagram goes in §8)

§5.3 Deliverables Table
- Columns: Spec | Module path | Django models | Rust modules | REST endpoints (Phase 1 only)
- Data from REST API Design §13 (Phase 1 rows only): 48 total endpoints, Phase 1 subset

§5.4 Go-Live Definition of Done
- Binary checklist — every item pass/fail:
  ```
  [ ] All 4 spec PRs merged to main
  [ ] ≥1 romaneo created end-to-end (truck in → grains stored → producer account updated)
  [ ] CPE lifecycle tested against ARCA test environment
  [ ] Offline sync works: romaneo created offline, synced when connected
  [ ] ≥1 paying customer has completed ≥1 romaneo in production
  [ ] Weighbridge auto-fill tested (manual fallback confirmed)
  [ ] Data migration: ≥1 test customer migrated from AGIS/Excel
  ```

§5.5 Target Timeline
- Use T+ week offsets from spec-09 start (T+0):
  - T+0: spec-09 begins (grain reference data)
  - T+3: spec-09 merged; spec-10 begins
  - T+7: spec-10 merged; spec-11 and spec-12 begin (parallel)
  - T+12: spec-11 + spec-12 merged
  - T+14: integration testing, data migration test, ARCA test env validation
  - T+16: Phase 1 go-live (first paying customer)
- Note: "Weeks are 5-day working weeks with 2 devs. Spec-10 (Romaneo Core) is the
  highest-complexity spec — treat as the critical path bottleneck."

**Gate 2 check** (after §5):
- Does the DoD checklist have ≥5 binary items? → YES
- Is the critical path (09 → 10 → 11 ∥ 12) explicit? → YES

---

### §6 — Phase 2: Advanced Operations

**Write AFTER §5.**
**Source data**:
- README.md spec catalog (Wave 6: specs 13-16)
- RAG: `"WSLPG liquidacion primaria SOAP complexity effort estimate"` → 5.1
- Serena memory: `session-2026-03-17-spec06-api-design-complete` (Phase 2 endpoints in §12)

**Output length**: ~100 lines
**Subsections (§6.1–§6.4)**:

§6.1 Scope
- 4 implementation specs: 13 (Agronomia Adaptation), 14 (WSLPG), 15 (Reports), 16 (Canje)

§6.2 Phase 2 Trigger
- Must meet ALL of: ≥5 paying customers, Phase 1 stable for ≥60 days with no critical bugs,
  ≥100 romaneos processed in production
- State explicitly: "Starting any spec-13+ work before this trigger is out of scope"

§6.3 Deliverables Table
- Same format as §5.3

§6.4 WSLPG Integration Notes
- SOAP service (AFIP/ARCA WSLPGv1.22+); manual developer doc PDF available
- pyafipws reference implementation exists (open source, Python)
- Effort estimate: 4–6 weeks for spec-14 alone (SOAP complexity + XML validation + test env)
- CPE distinction: WSCPE (grain transport certificate) = Phase 1; WSLPG (liquidación
  primaria, Form 1116 B/C) = Phase 2 — these are DIFFERENT ARCA services
- Reference: ADR-025 (WSAA hub-and-spoke), ADR-026 (WSLPG design choice)

---

### §7 — Phase 3: Intelligence & Scale

**Source data**:
- RAG: `"AI ML grain storage operations intelligent features roadmap"` → 9.1
- ADR-033 (AI event log), ADR-034 (ML scoring table), ADR-035 (AI query patterns)

**Output length**: ~80 lines
**Subsections (§7.1–§7.4)**:

§7.1 AI/ML Feature Candidates
- Predictive merma modelling (humidity × grain type × ambient → loss forecast)
- Price optimisation signals from MAT (Mercado a Término) data feed
- Grain quality grading assistance (computer vision for visual quality — Phase 3 horizon)
- Storage condition anomaly detection (temperature × humidity sensors)
- Natural language query: "What is my soy position today?" → SQL aggregation

§7.2 Multi-Tenant Growth Levers
- White-label for cooperative chains (ACA, FECOAGRO)
- Accountant portal → multi-client dashboard for contadores rurales
- API-first design enables mobile app (separate roadmap phase)

§7.3 Data Readiness Prerequisites
- AI-ready data model built in from Phase 1 (ADR-033/034/035):
  - Every romaneo is timestamped + grain-type-coded (ML training data)
  - QualityAnalysis stores raw sensor readings (humidity, protein, gluten, etc.)
  - GrainMovement is append-only with movement_type codes (classification target)
- "Phase 1 data collection is Phase 3 training data" — this is intentional

§7.4 Phase 3 Trigger
- ≥20 paying customers, ≥12 months of production romaneo data, ≥10,000 romaneos processed
- AI data pipeline reviewed for completeness (ADR-033 event log actively populated)

---

### §8 — Milestone & Dependency Graph

**Write AFTER §5, §6, §7 (so node names are confirmed).**
**Source data**: §5.2 (Phase 1 critical path), §6.2 (Phase 2 trigger), spec dependency chain.
**Output length**: ~80 lines (Mermaid diagrams are dense)

**Diagram 1 — Gantt / Timeline** (```mermaid gantt``` syntax):
```
gantt
    title GraviTea Acopio ERP — Delivery Timeline (T+ weeks from spec-09)
    dateFormat  X
    axisFormat  T+%s

    section Phase 1 — MVP
    spec-09 Grain Reference   :done, s09, 0, 3
    spec-10 Romaneo Core      :active, s10, 3, 7
    spec-11 Storage & Position:s11, after s10, 5
    spec-12 Producer Accounts :s12, after s10, 5
    Phase 1 Go-Live           :milestone, m1, 16, 0

    section Phase 2 — Advanced
    Phase 2 Trigger Gate      :milestone, t2, 76, 0
    spec-13 Agronomia         :s13, after t2, 4
    spec-14 WSLPG             :s14, after t2, 6
    spec-15 Reports           :s15, after s13, 4
    spec-16 Canje             :s16, after s14, 3

    section Phase 3 — Intelligence
    Phase 3 Trigger Gate      :milestone, t3, 128, 0
    AI/ML Foundation          :s_ai, after t3, 12
```

*Note: T+ values are notional working-weeks, not calendar weeks. Adjust when spec-09
actually begins. "T+76" for Phase 2 trigger = ~18 weeks after go-live + buffer.*

**Diagram 2 — Spec Dependency Graph** (```mermaid graph TD``` syntax):
```
graph TD
    s01[spec-01 Vision] --> s02[spec-02 PRD]
    s02 --> s03[spec-03 Data Model]
    s02 --> s07[spec-07 Roadmap ← you are here]
    s03 --> s04[spec-04 ADRs]
    s03 --> s05[spec-05 HLD]
    s04 --> s05
    s05 --> s06[spec-06 REST API]
    s03 --> s09[spec-09 Grain Ref]
    s09 --> s10[spec-10 Romaneo Core]
    s10 --> s11[spec-11 Storage]
    s10 --> s12[spec-12 Accounts]
    s11 --> GoLive([Phase 1 Go-Live])
    s12 --> GoLive
    GoLive --> s13[spec-13 Agronomia]
    GoLive --> s14[spec-14 WSLPG]
    s13 --> s15[spec-15 Reports]
    s14 --> s16[spec-16 Canje]
```

**Gate 3 check** (after §8):
- `grep -c '```mermaid'` ≥ 2 → YES

---

### §9 — Go-to-Market Strategy

**Source data**:
- RAG: `"contador rural accountant channel strategy GTM acopiador"` → 6.2
- RAG: `"Expoagro Agroactiva trade events grain calendar"` → 6.3
- RAG: `"acopio software market competitors AGIS switching window"` → 4.2

**Output length**: ~120 lines
**Subsections (§9.1–§9.5)**:

§9.1 Primary Channel: Contador Rural Flywheel
- Rural accountant (contador rural) is the dual decision-maker alongside the owner
- An agro-focused estudio serves 5–10 acopio/cooperative clients (data from research 6.2)
- Distribution flywheel: free accountant portal → accountant saves time → recommends to
  3–5 clients → each client refers others via word-of-mouth in grain-dense communities
- Target: 10 enrolled contadores rurales BEFORE public launch
- Accountant portal must provide: multi-client dashboard, vencimientos calendar, one-click
  SICORE/IVA exports

§9.2 Sales Motion Timeline (seasonal calendar)
- Jan–Mar (pre-harvest): Build pipeline via contadores; target 10 enrolled estudios
- Apr–Jun (post-soybean harvest): PRIMARY conversion window; operational quiet season;
  data migration offers from AGIS/Excel; first paid conversions
- Jul–Sep (off-season): Onboarding, refinement, reference customer case studies
- Oct–Dec (pre-summer planting): Renewals, upsell, second wave conversions

§9.3 Pricing Tiers (placeholder ranges)
- SMB: USD 199–499/month (1 branch, ≤5 users)
- Medium: USD 499–999/month (2–5 branches, ≤20 users)
- Note: "Exact pricing validated post customer discovery; ranges are directional only"

§9.4 Migration Playbook
- AGIS uses SQL Server — direct DB access or CSV export required
- Offer structured import from: AGIS CSV export, Excel (.xlsx), manual entry wizard
- Target: ≤2 hours from data upload to first romaneo in GraviTea
- Fiscal record continuity: retain historical data in read-only "archive" view (10-year
  Argentine regulatory requirement)

§9.5 Trade Events Calendar
- **Expoagro** (San Nicolás, Buenos Aires) — March; largest field days event; 100k+ attendees
- **Agroactiva** (Armstrong, Santa Fe) — June; Córdoba/Santa Fe belt target
- **CONINAGRO** assembly — annual cooperative gathering; contador rural network access
- **Bolsa de Cereales de Córdoba (BCCBA)** events — regional pizarra price events

**Gate 4 check** (after §9):
- `grep -i "contador"` ≥ 4 matches → YES
- `grep -i "post-harvest\|cosecha\|abril\|April"` ≥ 2 → YES

---

### §10 — Risk Register

**Source data**: spec.md FR-005 (mandatory risk categories); RAG 4.1, 4.3 (market risks);
spec complexity knowledge (WSLPG, offline, 2-dev).

**Output length**: ~60 lines (table only — no narrative)

**Format**:
```markdown
| # | Risk | Probability | Impact | Mitigation |
|---|------|-------------|--------|------------|
| R1 | ARCA regulation change mid-Phase 1 | High | High | Compliance-first sprint protocol; dedicate 1 dev-week per major RG |
| R2 | ARCA SOAP service instability (WSAA downtime) | Medium | High | PendingOperation queue (ADR-027); async retry with exponential backoff |
| R3 | Offline sync conflict edge case corrupts romaneo | Low | Critical | Append-only ledger (ADR-009); last-writer-wins with audit trail; E2E sync tests |
| R4 | Data migration friction blocks first customer | High | High | Structured AGIS CSV import tool; ≤2 hour onboarding target; migration support included in Year 1 |
| R5 | 2-dev team capacity — spec-10 (Romaneo) takes longer than T+4 | Medium | High | spec-11 ∥ spec-12 parallelism; spec-10 is serial bottleneck; no scope additions during spec-10 |
| R6 | Competitor response — Algoritmo ships web product | Low | High | Ship Phase 1 MVP before 2027 harvest; offline-first moat is 12-month build effort minimum for incumbents |
| R7 | Contador rural channel slower than expected | Medium | Medium | Expoagro/Agroactiva direct booth as secondary channel; ACA Jóvenes network as early adopter pipeline |
| R8 | Post-harvest switching window missed (Phase 1 late) | Low | High | If Phase 1 not ready by April 2026, target April–June 2027 window; use 2026 for beta with 1 free pilot customer |
```

**Gate 5 check** (after §10):
- `grep -c "| R"` ≥ 8 → YES

---

### §11 — Success Metrics & KPIs

**Source data**: spec.md SC-001–SC-006, FR-006; Phase 1 DoD from §5.4.
**Output length**: ~60 lines (table + brief framing paragraph)

**Format**:
```markdown
| KPI | Target | Measurement Method | Phase |
|-----|--------|--------------------|-------|
| Paying customers | ≥1 by end of Phase 1 | CRM / billing record | Phase 1 |
| Romaneos processed | ≥50 in first 60 days post-launch | Database count | Phase 1 |
| Onboarding time | ≤2 hours (AGIS/Excel → first romaneo) | Timed onboarding session | Phase 1 |
| Paying customers | ≥5 before Phase 2 trigger | CRM / billing record | Phase 1 → 2 trigger |
| Phase 1 spec time | ≤16 working weeks from T+0 | Git merge timestamps | Phase 1 |
| Contador enrollments | ≥10 estudios before public launch | Accountant portal signups | Pre-launch |
| Phase 2 trigger | ≥5 customers + ≥60 stable days + ≥100 romaneos | CRM + DB | Phase 2 gate |
| Phase 3 trigger | ≥20 customers + ≥10,000 romaneos | CRM + DB | Phase 3 gate |
```

**Writing rule**: Every KPI must be deterministically pass/fail. A team member must be
able to check it in ≤1 working day without judgment calls.

**Gate 6 check** (after §11):
- KPI rows ≥ 6 → YES (table has 8 rows)
- All numeric targets → YES

---

### §12 — Team & Resource Requirements

**Source data**: spec.md Assumptions (2-dev team); §5.2 (parallel tracks); HLD team model.
**Output length**: ~60 lines
**Subsections (§12.1–§12.3)**:

§12.1 Two-Developer Team Model
- Dev 1 (backend/domain lead): owns spec-09, spec-10, spec-11
- Dev 2 (fullstack/integration): owns spec-12, offline sync layer, ARCA integration tests
- Parallel tracks: spec-11 ∥ spec-12 (both start after spec-10 merge)
- Serial bottleneck: spec-10 (Romaneo Core) — no other spec work starts until it merges
- Code review: all PRs reviewed by the other dev before merge (2-dev rule)

§12.2 External Dependencies
- ARCA test environment (homologación): obtain CUIT + test certificates before spec-10
- WSAA digital certificate: 1 per tenant (test + production); certificate lifecycle = 2 years
- Weighbridge test data: simulate via fixture if no physical device available for testing
- Contador rural network: Bruno's personal network from Villa María region (Phase 0 GTM)

§12.3 Tooling & Infrastructure
- All tooling defined in HLD (spec-05); no new infrastructure for Phase 1
- Development: Docker Compose stack (db + redis + backend) as per `docker-compose.dev.yml`
- CI/CD: GitHub Actions (existing); branch protection + GGA pre-commit review
- Observability: Prometheus + Grafana (already deployed per HLD spec-05)

---

### §2 — Executive Summary (LAST)

**Write this AFTER all other sections are complete.**
**Source data**: Synthesised from §3–§12.
**Output length**: ~80 lines
**Content** (3–4 paragraphs + key facts callout):

Para 1: What GraviTea Acopio ERP is (cloud-native, offline-first grain ERP for Argentine
SMB acopiadores; 2-dev founding team; addresses ~1,073 underserved companies).

Para 2: Why now (AGIS VB6/.NET gap, ARCA regulatory velocity, post-harvest switching
window, generational shift to cloud-native tooling).

Para 3: The execution plan in 3 sentences (Phase 1 in 16 weeks shipping 4 specs for the
romaneo-to-position loop; Phase 2 triggered by ≥5 customers adding WSLPG + advanced ops;
Phase 3 adding AI/ML after ≥20 customers and 10k romaneos).

Para 4: GTM (contador rural flywheel, April–June 2026/2027 post-harvest window, 10× multiplier).

Key facts block:
```
> **TAM**: ~800 addressable SMB acopios × ~$300/month avg = ~$2.9M ARR
> **Phase 1 go-live**: T+16 weeks from spec-09 start
> **Main competitor**: AGIS (AmericaGIS) — VB6/.NET, 2,000+ clients, no web product for acopio
> **Primary GTM channel**: Contador rural flywheel (5–10 acopio clients per estudio)
> **Switching window**: April–June (post-soybean harvest)
```

**Gate 7 check** (after §2):
- Does the executive summary mention all three phases? → YES
- Does it name the competitor, the GTM channel, and the switching window? → YES

---

## Constitution Compliance Check

Run after completing all sections, before the final gate:

| Principle | Coverage in Roadmap |
|-----------|---------------------|
| P-I (Append-only ledgers) | §5.3 — GrainMovement + AccountMovement are append-only |
| P-II (Tenant isolation) | §5.3 — All Phase 1 models inherit TenantBoundModel |
| P-III (No speculative data) | §6.4 — WSLPG deferred to Phase 2 |
| P-IV (Offline-first) | §5.4 DoD item + §3.2 differentiator |
| P-V (ARCA compliance velocity) | §3.3 + §10 R1 |
| P-VI (2-dev constraint) | §12.1 explicit |
| P-VII (Decimal precision) | N/A — planning doc |
| P-VIII (Canonical vocabulary) | §1 content guidelines section |
| P-IX (Secure data operations) | §5.3 encrypted CUIT (blind index) in spec-12 |
| P-X (TDD) | §5.4 DoD requires tests to pass |
| P-XI (No TBD) | Final gate: grep check |

---

## Checkpoint Gates Summary

| Gate | After | Verification | Pass Criteria |
|------|-------|-------------|---------------|
| G1 | §1 + §3 + §4 | `grep -c "Version 1.0"` | ≥ 2 |
| G2 | §5 | DoD checklist count | ≥ 5 binary items |
| G3 | §8 | `grep -c '```mermaid'` | ≥ 2 |
| G4 | §9 | `grep -i "contador"` | ≥ 4 matches |
| G5 | §10 | `grep -c "| R"` | ≥ 8 |
| G6 | §11 | KPI row count | ≥ 6 numeric KPIs |
| G7 | §2 | Manual review | All 3 phases + competitor + GTM channel named |
| G8 | Final | All 12 AC from 07-specify.md | 12/12 PASS |

---

## Research Inputs by Section

Run only the queries you need as you write each section. Use `--json` for programmatic parsing.

```bash
# §3.1–§3.2 (Market + Competitive):
.venv/bin/python scripts/qdrant/qdrant_search.py \
    -q "acopio software market AGIS competitors switching costs" -l 5

# §3.3 (Regulatory):
.venv/bin/python scripts/qdrant/qdrant_search.py \
    -q "ARCA grain regulatory RG compliance real-time requirements" -l 4

# §6.4 (WSLPG complexity):
.venv/bin/python scripts/qdrant/qdrant_search.py \
    -q "WSLPG liquidacion primaria SOAP XML effort complexity" -l 4

# §7.1 (AI/ML features):
.venv/bin/python scripts/qdrant/qdrant_search.py \
    -q "AI ML grain storage predictive merma quality intelligent features" -l 4

# §9.1 (Contador rural GTM):
.venv/bin/python scripts/qdrant/qdrant_search.py \
    -q "contador rural accountant channel distribution multiplier acopiador" -l 4

# §9.5 (Trade events):
.venv/bin/python scripts/qdrant/qdrant_search.py \
    -q "Expoagro Agroactiva CONINAGRO grain events calendar" -l 4
```

---

## Done Criteria

The Roadmap.md is complete when ALL of the following pass:

**Content gates** (grep-verifiable):
```bash
# G1: Version metadata
grep -c "Version 1.0" Docs/Project\ Blueprint/Roadmap.md        # ≥ 2

# G2: All three phases
grep -c "Phase 1\|Phase 2\|Phase 3" Docs/Project\ Blueprint/Roadmap.md  # ≥ 15

# G3: All MVP specs referenced
grep -c "spec-09\|spec-10\|spec-11\|spec-12" Docs/Project\ Blueprint/Roadmap.md  # ≥ 8

# G4: Phase 2 specs referenced
grep -c "spec-13\|spec-14\|spec-15\|spec-16" Docs/Project\ Blueprint/Roadmap.md  # ≥ 4

# G5: Mermaid diagrams
grep -c '```mermaid' Docs/Project\ Blueprint/Roadmap.md         # ≥ 2

# G6: Contador rural GTM
grep -i "contador" Docs/Project\ Blueprint/Roadmap.md           # ≥ 4

# G7: Post-harvest switching window
grep -i "abril\|june\|post-harvest\|switching window\|cosecha" \
    Docs/Project\ Blueprint/Roadmap.md                          # ≥ 2

# G8: Risk register depth
grep -c "| R[0-9]" Docs/Project\ Blueprint/Roadmap.md           # ≥ 8

# G9: No TBD/TODO
grep -ci "TBD\|TODO" Docs/Project\ Blueprint/Roadmap.md         # 0

# G10: KPI table
grep -c "KPI\|paying customer\|romaneo\|onboarding\|contador" \
    Docs/Project\ Blueprint/Roadmap.md                          # ≥ 6

# G11: No code blocks (Python/SQL/bash)
grep -c '```python\|```sql\|```bash' Docs/Project\ Blueprint/Roadmap.md  # 0

# G12: Headings count
grep -c "^#" Docs/Project\ Blueprint/Roadmap.md                 # ≥ 35
```

**Manual review gate** (G7):
- The executive summary names: AGIS, the contador rural flywheel, the post-harvest window,
  and all 3 phases — readable in ≤5 minutes by a non-technical advisor.

Once all 12 gates pass, update the spec.md status from Draft to Complete and save a
Serena memory: `session-[date]-spec07-roadmap-complete`.
