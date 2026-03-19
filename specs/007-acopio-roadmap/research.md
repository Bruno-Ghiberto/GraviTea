# Research: Acopio ERP Roadmap (spec-07)

**Branch**: `007-acopio-roadmap`
**Date**: 2026-03-17
**Purpose**: Resolve planning decisions needed to write `Docs/Project Blueprint/Roadmap.md` v1.0

---

## R1 — Timeline Framing: Calendar Dates vs Relative Offsets

**Decision**: Use **relative T+ week offsets** from spec-09 start (T+0). Absolute calendar
dates appear only for seasonal anchors (e.g., "April–June post-harvest window").

**Rationale**: Spec-09 start date is not fixed at document-writing time. T+ offsets
remain accurate regardless of when Phase 1 actually begins. Seasonal GTM anchors (harvest
window) are calendar-fixed by nature and must remain as calendar months.

**Alternatives considered**:
- Absolute dates (e.g., "April 2026"): Rejected — would require updating the document
  whenever spec execution is delayed.
- Sprint numbers: Rejected — team is too small for formal sprint cadence; weeks are simpler.

**Implication for §5.5**: Phase 1 timeline uses T+0 through T+16 notation. Phase 2/3 use
"T+76" style (notional) with explicit note that values are "notional working-weeks".

---

## R2 — Phase 1 Effort Estimate: T+16 Weeks

**Decision**: Phase 1 go-live target = **T+16 working weeks** from spec-09 start with 2 devs.

**Breakdown**:
- spec-09 (Grain Reference Data): T+0 to T+3 (3 weeks; mostly fixtures + models)
- spec-10 (Romaneo Core): T+3 to T+10 (7 weeks; highest complexity — Rust merma + WSCPE)
- spec-11 (Storage & Position): T+10 to T+15 (5 weeks, parallel with spec-12)
- spec-12 (Producer Accounts): T+10 to T+15 (5 weeks, parallel with spec-11)
- Integration + ARCA test env + data migration: T+15 to T+16 (1 week buffer)

**Rationale**: spec-10 (Romaneo Core) contains:
- Django models for Romaneo, QualityAnalysis, MermaCalculation
- Rust FFI for merma engine (`merma.rs`, `grading.rs` via PyO3)
- ARCA WSCPE async integration (CPE lifecycle via PendingOperation queue)
- State machine (PENDIENTE → CONFORME → CERRADO) with 11 REST endpoints
- This is the most complex spec in Phase 1 — 7-week estimate is conservative.

**Alternatives considered**:
- T+12 weeks: Too aggressive — leaves no buffer for ARCA test environment setup and
  data migration validation.
- T+20 weeks: More conservative but misses the April–June switching window if
  spec-09 starts in January.

**Note**: If spec-10 slips past T+10, the total timeline extends proportionally (it is
the serial bottleneck). spec-11 and spec-12 can start as soon as spec-10 merges.

---

## R3 — TAM Calculation Methodology

**Decision**: Use a **bottom-up addressable estimate**: ~800 SMB acopios × ~$300/month
average = ~$2.9M ARR (directional, not audited).

**Inputs from RAG research**:
- ~1,073 private acopio companies, ~1,622 storage plants (source: 4.3 — BCR research data)
- Budget range: USD 150–500/month for SMB, USD 500–2,000 for medium (source: 4.3)
- Target segment: independent SMB acopiadores (not large cooperatives / enterprise)
- Addressable subset: ~75% of 1,073 = ~800 (discounting cooperative members and very
  small operators below the USD 150 threshold)

**Rationale**: The TAM in the Roadmap is directional context for advisor conversations,
not a fundraising deck number. "~$2.9M ARR" gives a concrete scale anchor without
overstating the opportunity. The estimate is clearly labelled as "(estimated)" in §3.1.

**Alternatives considered**:
- Full 1,073 × $500/month = $6.4M ARR: Overstates — some are cooperatives or very small
- 800 × $150/month = $1.4M ARR: Understates — many medium acopios pay $500+

---

## R4 — AI/ML Feature Prioritisation for Phase 3

**Decision**: Phase 3 AI/ML features prioritised by **data availability + implementation
risk** in this order:

1. **Predictive merma modelling** (Phase 3, Q1): Uses existing romaneo data (humidity,
   grain type, ambient conditions) that accumulates from Phase 1. Low ML complexity —
   regression model on tabular data. Highest ROI for acopiadores.

2. **Price optimisation signals** (Phase 3, Q2): MAT (Mercado a Término) data feed +
   historical account movement patterns. Moderate complexity. High business value for
   cuentas module.

3. **Storage condition anomaly detection** (Phase 3, Q3): Requires IoT sensor integration
   (temperature/humidity). Data from external devices. Medium complexity.

4. **Natural language grain position queries** (Phase 3, Q4): "¿Cuánta soja tengo hoy?"
   → SQL aggregation. Low ML complexity but requires LLM integration.

5. **Computer vision grain grading** (Phase 4 / out of Phase 3): Requires camera hardware
   partnership. Deferred beyond Phase 3 horizon.

**Rationale**: Phase 3 trigger requires ≥10,000 romaneos. At that volume, merma prediction
training data is sufficient (≥6 months of time-series). Features 1-4 build on the
AI-ready data model defined in ADR-033/034/035.

**Data prerequisites** (must exist from Phase 1):
- ADR-033: Event log table (every state transition timestamped)
- ADR-034: ML scoring table (prediction outputs stored alongside actuals)
- ADR-035: AI-optimised query patterns (indexed views for aggregation)

---

## R5 — Phase 2 Trigger Conditions (Numeric)

**Decision**: Phase 2 trigger requires ALL THREE of:
1. ≥5 paying customers (billing records)
2. Phase 1 production-stable for ≥60 calendar days with no P1/P2 bugs open
3. ≥100 romaneos processed in production

**Rationale**: 5 customers provides meaningful feedback on Phase 1 UX before committing
Phase 2 scope. 60-day stability window ensures no regressions lurk in the romaneo state
machine or ARCA queue before adding WSLPG complexity on top. 100 romaneos gives enough
data to validate the merma calculations and producer account accuracy.

**Phase 3 trigger**: ≥20 paying customers + ≥10,000 romaneos + AI data pipeline review.

---

## R6 — WSLPG vs CPE/WSCPE Distinction

**Critical clarification for §6**:

| Service | ARCA name | Phase | What it does |
|---------|-----------|-------|-------------|
| WSCPE | Web Service CPE (Carta de Porte Electrónica) | **Phase 1** | Grain transport certificate — initiated when truck arrives (romaneo creation) |
| WSLPG | Web Service Liquidación Primaria de Granos | **Phase 2** | Settlement/payment document — Form 1116 B/C — generated after grain is sold |

These are two completely separate ARCA SOAP services with different authentication flows,
XML schemas, and business events. The Roadmap MUST distinguish them precisely.
Do NOT write "ARCA integration in Phase 2" — CPE is already in Phase 1.

---

## R7 — Contador Rural Distribution Model

**Decision**: Model the contador rural flywheel as a **10× multiplier**:
- Each agro-specialized estudio serves 5–10 acopio/cooperative clients
- Free accountant portal reduces switching friction for the accountant
- Accountant recommends GraviTea to clients because it saves them time
- Target: 10 enrolled contadores before public launch = potential 50–100 prospects

**Source**: Research doc 6.2 (Accountant Channel Strategy) — confirmed by RAG query.

**GTM action items**:
1. Build accountant portal (multi-client view + SICORE/IVA exports) in Phase 1
2. Identify 3–5 target contadores in Villa María / Río Cuarto / Venado Tuerto region
   (Bruno's personal network)
3. Enrol first 3 contadores during integration testing (T+14–T+16) for beta feedback

---

## Summary: Resolved Decisions

| ID | Decision | Applied in |
|----|----------|-----------|
| R1 | T+ week offsets for timeline, not absolute dates | §5.5, §8 Gantt |
| R2 | Phase 1 = T+16 weeks; spec-10 is 7-week bottleneck | §5.2, §5.5, §8 |
| R3 | TAM: ~$2.9M ARR (800 SMBs × $300/month avg, estimated) | §3.1, §2 |
| R4 | Phase 3 AI: merma prediction → price signals → anomaly → NLQ | §7.1 |
| R5 | Phase 2 trigger: ≥5 customers + ≥60 days stable + ≥100 romaneos | §4 table, §6.2 |
| R6 | WSCPE = Phase 1 (CPE); WSLPG = Phase 2 (liquidación) — different services | §5, §6.4 |
| R7 | Contador flywheel: 10× multiplier, 10 estudios = 50–100 prospects | §9.1 |
