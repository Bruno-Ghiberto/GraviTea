# Spec 07: Acopio ERP Roadmap — Implementation Context

**Branch**: `007-acopio-roadmap`
**Deliverable**: `Docs/Project Blueprint/Roadmap.md` v1.0
**Type**: Blueprint spec — **single-author document writing, no agent team, no tmux**
**Spec**: `specs/007-acopio-roadmap/spec.md` (10 FRs, 6 SCs, 4 user stories)
**Plan**: `specs/007-acopio-roadmap/plan.md` (12 sections, 8 checkpoint gates)
**Tasks**: `specs/007-acopio-roadmap/tasks.md` (44 tasks, 7 phases)

---

## Execution Protocol

> **BLUEPRINT SPEC (01-08)**: Single author, single Write pass, no agent team.
> Write the ENTIRE document atomically in one Write tool call covering all 12 sections.
> Then verify all 12 acceptance gates. Fix failures with targeted Edit calls.

### Writing Strategy

1. Read setup tasks (T001-T003) — verify all 6 input blueprint docs exist at v1.0
2. Run all 4 RAG queries (T005-T008) in parallel — save key facts before writing
3. Write `Docs/Project Blueprint/Roadmap.md` in a SINGLE Write pass (12 sections)
4. Run all 12 verification gates from `quickstart.md` (T042)
5. Fix gate failures with targeted Edit calls
6. Mark all 44 tasks [x] in `tasks.md` after verification

### Why Atomic Write?

§2 Executive Summary synthesises §3–§12 — it must be written last but placed second
in the document. Writing atomically avoids section-by-section drift and ensures the
summary correctly reflects the final content of all other sections.

### ⚠️ CRITICAL WRITING ORDER (≠ document section order)

Write sections in this order — **NOT** in §-number order:

```
1.  §1  Document Metadata       [~30 lines  — always first]
2.  §3  Strategic Context       [~120 lines — needs RAG results from T005-T006]
3.  §4  Phases Overview         [~60 lines  — summary table for 3-phase model]
4.  §5  Phase 1 MVP             [~180 lines — critical path + DoD — LARGEST block]
5.  §6  Phase 2 Advanced        [~100 lines — trigger conditions + WSLPG notes]
6.  §7  Phase 3 Intelligence    [~80 lines  — AI/ML prerequisites + trigger]
7.  §8  Milestone Diagrams      [~80 lines  — 2 Mermaid diagrams]
8.  §9  Go-to-Market            [~120 lines — contador flywheel + seasonal calendar]
9.  §10 Risk Register           [~60 lines  — ≥8-row table]
10. §11 KPIs                    [~60 lines  — ≥6-row table]
11. §12 Team & Resources        [~60 lines  — 2-dev model]
12. §2  Executive Summary       [~80 lines  — write LAST, synthesise all]
```

---

## RAG Query Protocol

**RULE**: NEVER read full research Markdown files in `Docs/Researches/`. Use RAG for
all supplementary domain facts (market data, competitor details, GTM intelligence).

```bash
# Run ALL four queries BEFORE writing — save key facts to working notes
.venv/bin/python scripts/qdrant/qdrant_search.py -q "acopio software market AGIS competitors VB6 switching costs" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "acopiador pain points TAM market sizing geographic distribution" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "contador rural accountant channel distribution GTM acopiador" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "Expoagro Agroactiva grain trade events AI ML grain storage predictive" -l 5
```

### Upstream Blueprint Docs to Read (specific sections only)

| Source | What to Extract |
|--------|-----------------|
| `Docs/Project Blueprint/Data Model & Domain Model.md` | Module names (`apps/acopio/`, `apps/cuentas/`), entity vocabulary (GrainMovement, AccountMovement) |
| `Docs/Project Blueprint/REST API Design.md` | §13 Phase 1 endpoint count for §5.3 deliverables table |
| `Docs/Project Blueprint/Architecture Decision Records (ADR).md` | ADR-025 (WSAA hub-and-spoke), ADR-027 (SISA-tier retention), ADR-028–030 (offline-first/sync), ADR-033–035 (AI readiness flags) |
| `Docs/Project Blueprint/High-Level Design (HLD).md` | §3 offline-first description (for Phase 1 DoD framing) |

---

## Critical Domain Facts (inline — no RAG needed for these)

### Three-Phase Delivery Model

```
Phase 1 — Core Grain Reception MVP     Specs: 09–12   Exit: go-live checklist
Phase 2 — Advanced Operations          Specs: 13–16   Trigger: ≥5 cust + ≥60d + ≥100 romaneos (ALL 3)
Phase 3 — Intelligence & Scale         Specs: TBD     Trigger: ≥20 cust + ≥10,000 romaneos
```

### Phase 1 Critical Path (T+ working weeks, 2 devs)

```
spec-09 (Grain Reference)   T+0  → T+3    Serial prerequisite: GrainType FK blocks spec-10
spec-10 (Romaneo Core)      T+3  → T+10   ← SERIAL BOTTLENECK (7-week estimate)
spec-11 (Storage/Position)  T+10 → T+15   ← CAN run in PARALLEL with spec-12
spec-12 (Producer Accounts) T+10 → T+15   ← CAN run in PARALLEL with spec-11
Integration + ARCA test     T+15 → T+16
Phase 1 go-live             T+16
```

**RULE**: Use T+ week offsets in §5–§8. Do NOT use absolute calendar dates.
Seasonal GTM dates (April–June) in §9 are calendar-fixed by nature — acceptable exception.

### Phase 1 Module Paths (from spec-03 — immutable)

| Spec | Django app | Rust module |
|------|-----------|-------------|
| spec-09 | `apps/acopio/` (grain_type.py, campaign.py, fixtures) | — |
| spec-10 | `apps/acopio/` (romaneo.py, quality.py) | `rust/gravitea-core/src/merma.rs` |
| spec-11 | `apps/acopio/` (storage_unit.py, grain_lot.py) | — |
| spec-12 | `apps/cuentas/` (account.py, movement.py) | — (encrypted CUIT + blind index) |

**⚠️ Module path rule**: ALWAYS `apps/acopio/` and `apps/cuentas/` — NEVER `apps/grain/`,
`apps/granos/`, or any other variant.

### Phase 1 Go-Live — Definition of Done (all binary pass/fail)

1. All 4 spec PRs (09–12) merged to `main`
2. ≥1 romaneo end-to-end: truck in → weighed → quality analysed → stored → account updated
3. CPE lifecycle tested against ARCA test environment (WSCPE confirmarArribo + cerrar)
4. Offline sync tested: romaneo created offline, synced and resolved when reconnected
5. ≥1 paying customer has completed ≥1 romaneo in production

### Phase 2 Trigger (ALL THREE conditions must be met simultaneously)

1. ≥5 paying customers
2. Phase 1 production-stable ≥60 calendar days, no open P1/P2 bugs
3. ≥100 romaneos processed in production

**Explicit rule to write**: "Starting any spec-13+ work before all three trigger conditions
are met is out of scope — not a timeline decision, a scope guardrail."

### Phase 3 Trigger

≥20 paying customers AND ≥10,000 romaneos processed AND AI pipeline reviewed by team.

### ARCA Phase Distinction (CRITICAL — never conflate these two services)

| Service | Full Name | Purpose | Phase |
|---------|-----------|---------|-------|
| WSCPE | Carta de Porte Electrónica | Grain transport certificate (CPE/CTG) | **Phase 1** |
| WSLPG | Liquidación Primaria de Granos | Settlement + Form 1116 B/C | **Phase 2** |

- ADR-025: WSAA hub-and-spoke — one certificate, multiple ARCA services
- WSLPG effort estimate: 4–6 weeks for spec-14; complex SOAP XML schema

### Market & Competitive Context (for §3 — verify with RAG)

- **Addressable market**: ~1,073 private acopio companies, ~1,622 plants; Pampas concentration
  (Buenos Aires, Córdoba, Santa Fe)
- **SMB budget**: USD 150–500/month; medium USD 500–2,000/month
- **TAM estimate**: ~800 SMBs × ~$300/month avg = **~$2.9M ARR** — always label "(estimated)"
- **AGIS** (AmericaGIS): ~2,000+ clients, VB6/.NET desktop-only — no web/mobile for acopio module
- **Algoritmo S.A.** (Silohub): web integration — most dangerous direct competitor
- **Agrobit**: SAP partner, enterprise-only — not an SMB threat
- **GraviTea moat**: cloud-native + offline-first + ARCA compliance velocity
- **Regulatory tailwind**: RG 5689/2025 + RG 5821/2026; each new reg = moat renewal event
- **Switching window**: post-soybean harvest **April–June** = low-friction switching;
  missing one harvest cycle = 12-month delay in first paying customer

### Contador Rural Flywheel (for §9.1)

- Rural accountant (contador) = dual decision-maker alongside the acopio owner
- Each estudio serves 5–10 acopio/cooperative clients → **10× distribution multiplier**
- Flywheel: free accountant portal → saves contador time → contador recommends to clients
- **Target**: 10 enrolled contadores BEFORE public launch
- Portal requirements: multi-client dashboard, vencimientos calendar, SICORE/IVA exports

### GTM Seasonal Calendar (for §9.2)

| Period | Season | Action |
|--------|--------|--------|
| Jan–Mar | Pre-harvest | Pipeline building via contador outreach |
| Apr–Jun | **Post-soybean harvest** | **PRIMARY conversion window** — low-friction switching |
| Jul–Sep | Off-season | Onboarding, case studies, product refinement |
| Oct–Dec | Pre-summer | Renewals, upsell, second-wave conversions |

### Trade Events Calendar (for §9.5 — at least 3 named with month and location)

| Event | Location | Month | Audience |
|-------|----------|-------|----------|
| Expoagro | San Nicolás, Buenos Aires | March | ~100k+ attendees, broad agro |
| Agroactiva | Armstrong, Santa Fe | June | Córdoba/Santa Fe grain belt |
| CONINAGRO assembly | Annual, varies | TBD | Cooperative network |
| BCCBA events | Bolsa de Cereales de Córdoba | Multiple | Regional pizarra + grain ops |

### Risk Register Pre-Population (for §10 — use as starting rows, ≥8 required)

| # | Risk | Probability | Impact | Mitigation |
|---|------|-------------|--------|------------|
| R1 | ARCA regulation change (new RG mid-sprint) | High | Medium | Compliance-first sprint rule; ARCA monitoring |
| R2 | ARCA SOAP service instability | Medium | High | PendingOperation async queue (ADR-030); retry + backoff |
| R3 | Offline sync edge case (conflict resolution) | Low | High | Conflict strategy matrix (ADR-029); offline integration tests |
| R4 | Data migration friction (AGIS export) | Medium | High | AGIS CSV/Excel import; ≤2h onboarding target; fiscal archive view |
| R5 | 2-dev capacity — spec-10 bottleneck | Medium | High | spec-10 serial known (7 wks); spec-11∥spec-12 parallel to offset |
| R6 | Competitor response — Algoritmo ships web product | Low | Medium | Ship faster; ARCA velocity moat; contador loyalty before competitor |
| R7 | Contador channel slow (< 10 pre-launch) | Medium | Medium | Fallback: Expoagro/Agroactiva direct outreach |
| R8 | Post-harvest window missed | Low | High | Off-season fallback: beta pipeline + refinement sprint |
| R9 | WSAA certificate management complexity (Phase 2) | Low | Medium | ADR-025 hub-and-spoke already designed; cert renewal checklist |

### KPI Table Pre-Population (for §11 — ≥6 numeric rows required)

| KPI | Target | Measurement Method | Phase |
|-----|--------|--------------------|-------|
| Paying customers at Phase 1 go-live | ≥1 | Customer contract signed | Phase 1 |
| Romaneos processed in first 60 days | ≥50 | DB query: `SELECT COUNT(*) FROM acopio_romaneo` | Phase 1 |
| Onboarding time (first login → first romaneo) | ≤2 hours | Timer measured during onboarding | Phase 1 |
| Customers at Phase 2 trigger | ≥5 | Customer count at trigger review | Phase 1→2 |
| Phase 1 build duration | ≤16 working weeks | T+ offset from spec-09 kickoff | Phase 1 |
| Contador enrollments pre-launch | ≥10 | Enrolled portal accounts before public launch | Phase 1 |
| Romaneos at Phase 3 trigger | ≥10,000 | DB query: total romaneo count | Phase 2→3 |

### Append-Only Ledger Rule (Constitution Principle I)

- `GrainMovement`: append-only. PATCH/DELETE = HTTP 405. Never suggest these can be edited.
- `AccountMovement`: append-only. PATCH/DELETE = HTTP 405. Never suggest reversal.
- The Roadmap must NOT imply that grain or account movements can be updated or reversed.

---

## Section Drafting Instructions

Write sections in the CRITICAL WRITING ORDER above, not §-number order.

### §1 — Document Metadata (~30 lines) — WRITE FIRST

Must match the blockquote + metadata table format from prior blueprint docs (ADR.md,
HLD.md, REST API Design.md):

- Blockquote: `> **Version 1.0** · Date: YYYY-MM-DD · Status: Draft · Owner: GraviTea Architecture Team`
- Metadata table: 4 rows — Version, Date, Status, Depends On: spec-01 through spec-06
- One-paragraph scope statement describing the document's purpose
- Changelog table (single row: v1.0)

### §2 — Executive Summary (~80 lines) — WRITE LAST

Synthesises §3–§12. Four paragraphs:
1. What GraviTea Acopio ERP is (cloud-native, offline-first, Argentine acopiadores)
2. Why now (AGIS VB6/.NET gap + ARCA regulatory velocity + switching window + generational shift)
3. Execution plan in 3 sentences (Phase 1 T+16 weeks, Phase 2 at ≥5 customers, Phase 3 at ≥20)
4. GTM (contador flywheel + April–June window)

Plus a key facts blockquote: TAM, go-live week target, competitor name, channel, window months.

### §3 — Strategic Context (~120 lines)

Four subsections — all can be drafted in parallel once RAG queries are complete:
- §3.1 Market Opportunity: ~1,073 companies, ~1,622 plants, TAM ~$2.9M ARR "(estimated)"
- §3.2 Competitive Positioning: AGIS (VB6/.NET, desktop, ~2,000+ clients), Algoritmo, Agrobit, GraviTea gap
- §3.3 Regulatory Tailwind: RG 5689/2025 + RG 5821/2026; compliance velocity = ongoing moat
- §3.4 Window of Opportunity: April–June primary; generational shift; 5–8 year window before AGIS modernises

### §4 — Product Phases Overview (~60 lines)

1-paragraph narrative introducing the 3-phase model, followed by a summary table:
```
| Phase | Name | Specs | Entry | Exit/Trigger |
| Phase 1 | Core Grain Reception MVP | 09–12 | T+0 | go-live checklist |
| Phase 2 | Advanced Operations | 13–16 | Phase 1 go-live | ≥5 cust + ≥60d + ≥100 romaneos |
| Phase 3 | Intelligence & Scale | TBD | Phase 2 stable | ≥20 cust + ≥10,000 romaneos |
```

### §5 — Phase 1 MVP (~180 lines, LARGEST BLOCK)

Five subsections:
- **§5.1 Scope**: 4-row table — spec number, module path, Django models, Rust module, key output
- **§5.2 Critical Path**: spec-09→spec-10 serial (GrainType FK dependency); spec-11∥spec-12 parallel
  after spec-10 merges; **name spec-10 as the serial bottleneck** (7-week estimate)
- **§5.3 Deliverables Table**: Spec | Module path | Django models | Rust | Phase 1 REST endpoints
- **§5.4 Go-Live DoD**: Binary checklist — 5+ items, no subjective wording, every item pass/fail
- **§5.5 Target Timeline**: T+ week offset table (T+0/T+3/T+10/T+15/T+16)

### §6 — Phase 2 Advanced Operations (~100 lines)

- **§6.1 Scope**: 4-spec table (spec-13 Agronomia, spec-14 WSLPG, spec-15 Reports, spec-16 Canje)
- **§6.2 Trigger Conditions**: ALL THREE required — explicit list with "out of scope" enforcement note
- **§6.3 Deliverables Table**: same format as §5.3
- **§6.4 WSLPG Integration Notes**: SOAP v1.22+, pyafipws reference, 4–6 week effort, CPE≠WSLPG
  distinction, ADR-025 WSAA hub-and-spoke reference

### §7 — Phase 3 Intelligence & Scale (~80 lines)

- §7.1 AI/ML Candidates: predictive merma → price signals → anomaly detection → NLQ queries
- §7.2 Multi-Tenant Growth: white-label, cooperative chains, accountant portal expansion
- §7.3 Data Readiness Prerequisites: ADR-033 (event log), ADR-034 (ML scoring table),
  ADR-035 (AI query patterns) — all built in Phase 1 as data-model-level readiness flags
- §7.4 Phase 3 Trigger: ≥20 customers + ≥10,000 romaneos + AI pipeline reviewed

### §8 — Milestone Diagrams (~80 lines)

Two Mermaid diagrams — **both required** (Gate G5 checks ≥2):

**Diagram 1** — Gantt chart (`gantt` block, T+N notation):
- Sections: Foundation (spec-09, spec-10), Parallel Track (spec-11, spec-12), Integration, Go-Live
- Mark spec-10 as the critical path item

**Diagram 2** — Spec dependency graph (`graph TD` block):
```
spec-01/02/03/04/05/06 → spec-09 → spec-10 → spec-11 ──┐
                                              → spec-12 ──┤→ GoLive → spec-13/14 → spec-15/16
```

### §9 — Go-to-Market Strategy (~120 lines)

- **§9.1 Contador Rural Flywheel**: dual decision-maker role, 5–10 clients/estudio = 10× multiplier,
  free portal flywheel logic, target 10 enrolled pre-launch, portal requirements
- **§9.2 Sales Motion Timeline**: seasonal calendar table (Jan-Mar / Apr-Jun / Jul-Sep / Oct-Dec)
- **§9.3 Pricing Tiers**: SMB USD 199–499/month, Medium USD 499–999/month;
  note "directional only — validated post customer discovery"
- **§9.4 Migration Playbook**: AGIS CSV/Excel structured import; ≤2h target; 10-year fiscal archive
  (Argentine regulatory requirement = read-only archive view)
- **§9.5 Trade Events Calendar**: Expoagro, Agroactiva, CONINAGRO, BCCBA — all with months

### §10 — Risk Register (~60 lines)

**Table only — no narrative.** Columns: `# | Risk | Probability | Impact | Mitigation`
Use the pre-populated R1–R9 from Critical Domain Facts. ≥8 rows required (Gate G8).

### §11 — Success Metrics & KPIs (~60 lines)

Table only. Columns: `KPI | Target | Measurement Method | Phase`
Use the pre-populated 7 KPIs from Critical Domain Facts. ≥6 rows required (Gate G10).
All targets must be **numeric** — no "good progress" or subjective wording.

### §12 — Team & Resource Requirements (~60 lines)

- §12.1 Two-developer model: Dev1 = backend/domain (spec-09/10/11); Dev2 = fullstack/integration
  (spec-12 + ARCA tests); note which tracks are parallel (spec-11 ∥ spec-12)
- §12.2 Parallel vs serial tracks: explicitly name spec-10 as the serial bottleneck
- §12.3 External dependencies: ARCA homologación env, WSAA cert, weighbridge test data,
  contador network (10 enrolled)
- §12.4 Tooling: all from HLD — no new infrastructure introduced by Phase 1

---

## Constitution Cross-Check (run before gates)

Verify all four items before running the gate commands:

1. **WSCPE = Phase 1 / WSLPG = Phase 2**: Explicitly stated and distinct. Never conflated.
2. **Module paths**: `apps/acopio/` and `apps/cuentas/` — not `apps/grain/` or any other.
3. **Offline-first**: Described as a Phase 1 requirement in §5.4 DoD — NOT a "future feature".
4. **Append-only ledgers**: GrainMovement + AccountMovement — no PATCH/DELETE anywhere implied.

---

## Review Checklist (run after writing)

```bash
TARGET="Docs/Project Blueprint/Roadmap.md"

echo "=== G1: Version 1.0 metadata (≥2) ==="
grep -c "Version 1.0" "$TARGET"

echo "=== G2: Three phases coverage (≥15) ==="
grep -c "Phase 1\|Phase 2\|Phase 3" "$TARGET"

echo "=== G3: MVP specs 09-12 referenced (≥8) ==="
grep -c "spec-09\|spec-10\|spec-11\|spec-12" "$TARGET"

echo "=== G4: Phase 2 specs 13-16 referenced (≥4) ==="
grep -c "spec-13\|spec-14\|spec-15\|spec-16" "$TARGET"

echo "=== G5: Mermaid diagrams (≥2) ==="
grep -c '```mermaid' "$TARGET"

echo "=== G6: Contador rural GTM (≥4) ==="
grep -ic "contador" "$TARGET"

echo "=== G7: Post-harvest switching window (≥2) ==="
grep -ic "abril\|june\|post-harvest\|switching window\|cosecha\|post-soja" "$TARGET"

echo "=== G8: Risk register rows (≥8) ==="
grep -c "| R[0-9]" "$TARGET"

echo "=== G9: No TBD/TODO (must be 0) ==="
grep -ci "TBD\|TODO" "$TARGET"

echo "=== G10: KPI/romaneo coverage (≥6) ==="
grep -ci "KPI\|paying customer\|romaneo\|onboarding\|contador enroll" "$TARGET"

echo "=== G11: No code blocks — python/sql/bash (must be 0) ==="
grep -c '```python\|```sql\|```bash' "$TARGET"

echo "=== G12: Section headings (≥35) ==="
grep -c "^#" "$TARGET"
```

### Manual Check (after all grep gates pass)

Read §2 Executive Summary and confirm it answers all four advisor questions without
consulting any other document:

1. What is GraviTea Acopio ERP? (cloud-native, offline-first, Argentine acopiadores)
2. Why now? (AGIS VB6/.NET gap + ARCA regulatory velocity + switching window + generational shift)
3. What is the execution plan? (3 phases, Phase 1 in T+16 weeks, 4 implementation specs)
4. How does GTM work? (contador flywheel + April–June primary conversion window)

---

## Done Criteria

The document is DONE when ALL of the following are true:

1. All 12 gates (G1–G12) pass
2. `grep -c "^#" "$TARGET"` ≥ 35 headings
3. Both Mermaid diagrams present (Gantt + dependency graph)
4. All 12 top-level sections present — no TBD or placeholder text
5. §2 Executive Summary written LAST — answers all four advisor questions
6. §5.4 Go-Live DoD checklist has ≥5 binary pass/fail items (no subjective wording)
7. Phase 2 trigger explicitly states ALL THREE conditions (not just one)
8. WSCPE (Phase 1) and WSLPG (Phase 2) are clearly distinct — never conflated
9. Module paths are `apps/acopio/` and `apps/cuentas/` throughout
10. No Python/SQL/bash code blocks anywhere in the document
11. T+ week offsets used in §5–§8 (no absolute calendar dates in these sections)
12. All 44 tasks in `specs/007-acopio-roadmap/tasks.md` marked [x]

---

## Post-Implementation

After all gates pass:

1. Update `specs/007-acopio-roadmap/spec.md` Status field from `Draft` → `Complete`
2. Save Serena memory: `session-YYYY-MM-DD-spec07-roadmap-complete`
3. Save Engram observation with deliverable summary (line count, gate results)
4. Commit:
   ```bash
   git add "Docs/Project Blueprint/Roadmap.md" specs/007-acopio-roadmap/
   git commit -m "docs: add Roadmap.md v1.0 (spec-07)"
   ```
