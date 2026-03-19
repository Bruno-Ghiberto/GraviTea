# Feature Specification: Acopio ERP Roadmap

**Feature Branch**: `007-acopio-roadmap`
**Created**: 2026-03-17
**Status**: Complete
**Input**: User description: "Read @Docs/PROMPTS/spec-07-roadmap/07-specify.md"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Phase 1 Execution Plan (Priority: P1)

A founding team member opens the Roadmap to understand exactly what to build in Phase 1
(the MVP), in what order, and what "done" means before the product is offered to the
first paying customer. They need a clear critical path (spec-09 → spec-10 → spec-11
in parallel with spec-12) and a concrete Definition of Done checklist.

**Why this priority**: Without a clear Phase 1 scope and go-live criteria, the team risks
scope creep, indefinite iteration, and missing the post-harvest April–June customer
switching window. This is the highest-value decision the Roadmap enables.

**Independent Test**: A team member who has not read any prior spec can read Phase 1 alone
and name all four MVP implementation specs, their build order, and five go-live criteria
without consulting any other document.

**Acceptance Scenarios**:

1. **Given** a team member reads §5 (Phase 1), **When** they finish, **Then** they can
   list all four MVP specs (09–12), their deliverable modules, and the dependency order
   without referring to any other document.

2. **Given** a team member reaches the go-live criteria checklist, **When** they review
   it, **Then** every criterion is binary (pass/fail) with no subjective interpretation.

3. **Given** the product is approaching Phase 1 completion, **When** the team consults the
   Definition of Done, **Then** they can determine unambiguously whether all criteria are
   met before accepting the first paying customer.

---

### User Story 2 — Go-to-Market Calendar (Priority: P2)

A founder planning the first sales campaign uses the GTM section to anchor outreach to
the post-harvest switching window and to design the contador rural distribution flywheel.
They need a seasonal calendar, a channel strategy, and a migration playbook to reduce the
#1 switching barrier (data migration from AGIS/desktop systems).

**Why this priority**: The post-soybean harvest window (April–June) is the only
low-friction moment to convert customers from legacy desktop systems. Missing one harvest
cycle means a 12-month delay in acquiring the first paying customer.

**Independent Test**: A non-technical co-founder reads §9 alone and can produce a
3-step quarterly action plan (Q1: enrol contadores; Q2: convert first customers;
Q3: onboard and iterate) without consulting any other document.

**Acceptance Scenarios**:

1. **Given** a founder reads §9 (GTM), **When** they identify the primary channel,
   **Then** the contador rural flywheel is named with the rationale that 5–10 acopio
   clients per estudio gives a 10× distribution multiplier.

2. **Given** a prospect's #1 objection is "my data is in AGIS", **When** the founder
   consults the GTM section, **Then** the migration playbook provides a concrete response
   (structured AGIS/Excel import, ≤2-hour onboarding target).

3. **Given** the team is planning a trade event appearance, **When** they consult §9.5,
   **Then** the document names at least 3 industry events with months and target audience.

---

### User Story 3 — Strategic Context for Stakeholder Conversations (Priority: P2)

A founder uses §3 (Strategic Context) to brief an advisor, early investor, or key
potential customer on the market opportunity, the competitive gap, and the timing
rationale — in under 10 minutes without a separate pitch deck.

**Why this priority**: The competitive gap (AGIS VB6/.NET, no web/mobile) and regulatory
tailwind (RG 5689/2025, RG 5821/2026) justify the company's timing and moat. An advisor
or investor who reads §3 must immediately understand why now and why this team.

**Independent Test**: An advisor unfamiliar with the project reads §3 alone and can
answer: (a) how large is the addressable market, (b) why is the incumbent vulnerable,
(c) what is the regulatory moat, (d) when is the right time to sell.

**Acceptance Scenarios**:

1. **Given** an advisor reads §3, **When** they finish, **Then** they can state the TAM,
   the main competitor name (AGIS), its platform weakness (VB6/.NET, desktop-only),
   and the optimal switching window.

2. **Given** a new ARCA regulation is announced, **When** the team consults §3.3,
   **Then** the section frames regulatory velocity as an ongoing competitive moat —
   not a one-time compliance cost.

---

### User Story 4 — Phase Boundary Enforcement (Priority: P3)

A technical lead uses §6 and §7 to scope Phase 2 (WSLPG, Agronomia, Reports, Canje)
and Phase 3 (AI/ML), and consults the trigger conditions to avoid premature scope expansion
into Phase 2 features while Phase 1 is incomplete.

**Why this priority**: Without explicit phase boundaries and trigger conditions, the team
risks building advanced features before the MVP is validated. The trigger conditions act
as measurable guardrails.

**Independent Test**: A team member who is considering starting WSLPG integration early
can consult §6 and identify the specific, measurable Phase 2 trigger that must be met first.

**Acceptance Scenarios**:

1. **Given** a team member reads §6, **When** they ask "can we start WSLPG now?",
   **Then** the Phase 2 trigger conditions provide a binary (yes/no) answer.

2. **Given** §7 is read in isolation, **When** a reader asks what Phase 3 requires,
   **Then** the AI/ML prerequisites (data model readiness flags) are explicitly named.

---

### Edge Cases

- **Missed switching window**: If the post-harvest window passes before Phase 1 go-live,
  the Roadmap must describe the off-season fallback (beta pipeline, refinement sprint).
- **Parallel track delay**: If spec-11 (Storage) or spec-12 (Accounts) is delayed, the
  team needs to know which path is on the critical path to go-live.
- **Regulatory surprise during Phase 1**: A new ARCA regulation mid-sprint requires a
  defined response protocol in the risk register (compliance-first sprint rule).
- **Contador channel underperforms**: If 10 contadores are not enrolled before the
  switching window, the GTM section must name a secondary channel
  (direct Expoagro/Agroactiva outreach).

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The Roadmap document MUST define exactly three delivery phases with
  distinct, named scopes: Phase 1 (Core Grain Reception MVP), Phase 2 (Advanced
  Operations), Phase 3 (Intelligence & Scale).

- **FR-002**: The Roadmap MUST map every implementation spec (09–16) to a specific
  phase, listing the spec number, deliverable module, and key outputs.

- **FR-003**: The Phase 1 section MUST include a Definition of Done checklist with
  binary (pass/fail) criteria that can be evaluated without subjective interpretation.

- **FR-004**: The Roadmap MUST include a go-to-market strategy naming the contador rural
  channel as the primary distribution flywheel and anchoring the first sales campaign to
  the post-soybean harvest April–June switching window.

- **FR-005**: The Roadmap MUST include a risk register with at least 8 risks, each with
  probability category (high/medium/low), impact category, and an actionable mitigation.
  Mandatory risks: regulatory change velocity, ARCA service instability, offline/sync
  edge cases, data migration friction, 2-person team capacity, and competitor response.

- **FR-006**: The Roadmap MUST define at least 6 success KPIs with numeric targets and
  measurement methods. Every KPI must be verifiable without subjective interpretation.

- **FR-007**: The Roadmap MUST contain at least 2 Mermaid diagrams: (1) a Gantt or
  timeline chart showing the critical path from spec-09 to Phase 1 go-live, and (2) a
  spec dependency graph showing the spec 09–16 execution order.

- **FR-008**: The Phase 2 section MUST state explicit trigger conditions — measurable
  criteria (e.g., "at least 5 paying customers") that must be met before Phase 2 begins.
  The Phase 3 section MUST do the same.

- **FR-009**: The team section MUST explicitly address the 2-dev constraint, identifying
  which spec tracks can run in parallel (spec-11 ∥ spec-12) and which are serial
  bottlenecks (spec-09 → spec-10).

- **FR-010**: §1 MUST contain version 1.0 metadata with date, status (Draft), and a
  changelog table using the same blockquote-plus-table format as all prior blueprint docs.

### Key Entities

- **Phase**: A time-bounded delivery unit with a name, scope, entry criteria, exit
  criteria, and assigned implementation specs. Three phases: Phase 1 (MVP), Phase 2
  (Advanced), Phase 3 (Intelligence).

- **Implementation Spec**: A numbered work unit (spec-09 through spec-16) producing a
  concrete technical deliverable. Each spec belongs to exactly one phase.

- **Milestone**: A named checkpoint within a phase (e.g., "spec-09 models merged",
  "Phase 1 go-live"). Milestones appear on the Gantt diagram and define the critical path.

- **Trigger Condition**: A measurable, binary criterion that gates the start of a phase
  (e.g., "≥5 paying customers before Phase 2"). Prevents premature scope expansion.

- **KPI**: A success metric with a numeric target, a measurement method, and the phase
  in which it is evaluated.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A team member unfamiliar with prior specs can read Phase 1 (§5) alone and
  name all four MVP implementation specs, their build order, and the go-live criteria in
  under 5 minutes.

- **SC-002**: A founder can brief an advisor or investor using only §2 (Executive Summary)
  and §3 (Strategic Context) in under 10 minutes with no supplementary materials.

- **SC-003**: The risk register contains at least 8 risks; each risk has a named
  mitigation that can be acted on immediately without additional research.

- **SC-004**: All 6+ KPIs are numeric with measurement methods; a team member can
  determine pass/fail for each KPI within one working day by querying the relevant source
  (customer count, romaneos processed, onboarding elapsed time).

- **SC-005**: The GTM section contains a seasonal calendar; a founder can identify the
  specific months to begin outreach and the specific months to close first customers
  directly from the document.

- **SC-006**: The Roadmap passes all 12 acceptance-criteria gates defined in
  `07-specify.md`: version metadata, phase coverage, Mermaid diagram count, spec
  references, contador mentions, risk register depth, KPI count, and zero TBD/TODO.

---

## Assumptions

- The founding team remains 2 developers for Phase 1 and Phase 2.
- Phase 1 spec execution begins in Q1 2026, targeting Phase 1 go-live before or during
  the April–June 2026 post-harvest window (with April–June 2027 as the fallback harvest).
- All 6 blueprint specs (01-06) are stable; no material changes are expected to the
  Data Model, ADRs, HLD, or REST API Design before the Roadmap is authored.
- Primary sales territory for Phase 1 is the Pampas region (Buenos Aires, Córdoba,
  Santa Fe) where grain acopio density is highest.
- WSLPG/SOAP effort for liquidación primaria is estimated at 4–6 weeks; this estimate
  underpins the Phase 2 timeline framing.
- The Roadmap is a living document versioned via changelog; phase scope changes require
  a version bump.

---

## Out of Scope

- Implementation code, technical architecture, and database schemas — these live in
  the HLD (spec-05) and Data Model (spec-03).
- Exact pricing tiers are placeholders pending customer discovery validation.
- spec-08a (ARCA Grain Integration Guide), spec-08b (AI/ML Feature Roadmap), and
  spec-08c (SRS) are downstream outputs; they are not authored within this spec.
- Legacy GRAVITEA-ERP modules for non-grain verticals are excluded.

---

## Dependencies

| Dependency | Type | Reason |
|------------|------|--------|
| `Docs/Project Blueprint/Product Vision & Scope.md` | Input | Strategic goals and target customer definition |
| `Docs/Project Blueprint/PRD.md` | Input | User stories, feature priorities, initial phase framing |
| `Docs/Project Blueprint/Data Model & Domain Model.md` | Input | Module names (acopio, cuentas), canonical entity vocabulary |
| `Docs/Project Blueprint/Architecture Decision Records (ADR).md` | Input | ADR-033–035 for AI readiness; ADR-027 for SISA-tier retention at WSLPG filing (Phase 2) |
| `Docs/Project Blueprint/High-Level Design (HLD).md` | Input | Architecture decisions, offline-first milestones |
| `Docs/Project Blueprint/REST API Design.md` | Input | Phase 1 vs Phase 2 endpoint scope boundary |
| `specs/007-acopio-roadmap/plan.md` | Next output | Generated by `/speckit.plan` after this spec |
| `Docs/Project Blueprint/Roadmap.md` | Final deliverable | The blueprint document produced by `/speckit.implement` |
