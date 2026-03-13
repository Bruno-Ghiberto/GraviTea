# Speckit Context: Fiscal Compute Engine — PLAN Phase (SPEC-019)

> **Phase**: PLAN — Design implementation plan, research decisions, task breakdown
> **Priority**: HIGH | **Wave**: 3 (parallel with SPEC-022)
> **Produces**: `plan.md`, `research.md`, `quickstart.md`
> **Does NOT produce**: data-model.md, api-contract.md (no new Django models)

---

## Mission

Design the implementation plan for Rust fiscal calculations (ARCA validation, IVA breakdown, stock aggregation, CUIT Modulo-11). The defining challenge is the `str`↔`Decimal` boundary crossing pattern that all subsequent money-handling Rust specs will reuse.

## Team Architecture

| Agent | Subagent Type | Model | Role |
|-------|--------------|-------|------|
| ORCHESTRATOR (LEAD) | system-architect | Opus 4.6 | Coordinates, validates, documentation |
| RUST-EXPERT | general-purpose | Opus 4.6 | Implements compute.rs + decimal_utils.rs |
| ARCA-EXPERT | general-purpose | Opus 4.6 | Validates fiscal math, IVA rates, CUIT algorithm |
| QA | quality-engineer | Sonnet 4.6 | Equivalence tests with ARCA test vectors |
| WIKI-EXPERT | general-purpose | Sonnet 4.6 | On-demand RAG librarian — queries Qdrant collections to unblock technical challenges |

### RAG Integration

- **WIKI-EXPERT** is the team's RAG librarian — spawned on-demand by LEAD when any agent is blocked
- Queries all Qdrant collections: `wikis`, `arca_api_specs`, `arca_dev_guides`, `arca_setup_certs`
- Command format: `backend/venv-wsl/bin/python scripts/qdrant/qdrant_search.py -q "YOUR QUERY" -c <collection> -l 5`
- See `Docs/Temp-prompting/agents/agent-WIKI-EXPERT.md` for full mission brief
- **ARCA-EXPERT** may also query Qdrant directly for fiscal validation: `-c arca_api_specs`

### Sequential-Thinking MCP

- **MANDATORY**: RUST-EXPERT (Decimal boundary ownership), ARCA-EXPERT (fiscal rule validation)
- **NOT required**: QA (mechanical test writing), WIKI-EXPERT (query-and-report)

## Implementation Phases

### Phase 1: Decimal Infrastructure (RUST-EXPERT)
- **Risk**: HIGH (Decimal precision is foundational)
- Tasks:
  1. Add `rust_decimal` + `rust_decimal_macros` to Cargo.toml
  2. Create `rust/gravitea-core/src/decimal_utils.rs` — shared str↔Decimal helpers
  3. Write conversion tests: Python Decimal edge cases (very small, very large, negative, zero)
  4. Document precision limits (28 sig digits vs GRAVITEA's DECIMAL(17,3))

### Phase 2: Fiscal Functions (RUST-EXPERT)
- **Risk**: HIGH (ARCA rejection on mismatch)
- Tasks:
  1. Create `rust/gravitea-core/src/compute.rs` with 5 `#[pyfunction]` exports
  2. Implement `validate_importes` with dual-tolerance validation (FR-001)
  3. Implement `calculate_iva_breakdown` with AlicIva ID mapping (FR-002, FR-003)
  4. Implement `validate_iva_breakdown` — sum checks + comprobante type rules (FR-008)
  5. Implement `aggregate_stock_levels` with GIL release (FR-006, FR-007)
  6. Implement `validate_cuit` (Modulo-11 algorithm) (FR-004, FR-005)
  7. Register compute submodule in `lib.rs`

### Phase 3: ARCA Validation (ARCA-EXPERT)
- **Risk**: HIGH (fiscal compliance)
- Tasks:
  1. Review all IVA rates (0, 2.5, 5, 10.5, 21, 27) against ARCA documentation
  2. Verify AlicIva ID mapping: 21%→5, 10.5%→4, 5%→8, 27%→6, 2.5%→9, 0%→3
  3. Verify CUIT Modulo-11 algorithm matches ARCA specification
  4. Verify tolerance values match ARCA acceptance rules
  5. Sign off or request changes

### Phase 4: Python Integration (QA)
- **Risk**: MEDIUM
- Tasks:
  1. Modify affected Python files to call Rust with fallback
  2. Update `gravitea_rust.pyi` with compute function signatures
  3. Write equivalence tests against known ARCA test vectors
  4. Write stock aggregation test with real-shaped data
  5. Write CUIT validation tests (valid + invalid CUITs)

### Phase 5: Docker + Regression (LEAD)
- **Risk**: LOW
- Tasks:
  1. Rebuild Docker image — verify compute functions available
  2. Run full test suite — 0 regressions
  3. Verify fallback: Python implementations still work
  4. Update quickstart.md

## Research Topics (for research.md)

| ID | Topic | Decision Needed | Assigned To |
|----|-------|----------------|-------------|
| R-001 | rust_decimal precision limits vs Python Decimal | Document maximum values GRAVITEA could encounter | RUST-EXPERT |
| R-002 | AlicIva ID mapping — complete ARCA rate table | Verify all rate→ID mappings from ARCA docs | ARCA-EXPERT |
| R-003 | CUIT Modulo-11 reference implementation | Find authoritative ARCA specification | ARCA-EXPERT |
| R-004 | Stock aggregation input format (QuerySet → str) | Design optimal serialization for batch data | RUST-EXPERT |
| R-005 | GIL release benchmarks for aggregate_stock_levels | Measure actual thread concurrency benefit | QA |

## Crate Dependencies

| Crate | Version | New/Shared | Purpose |
|-------|---------|-----------|---------|
| `rust_decimal` | 1.36 | NEW | Decimal arithmetic |
| `rust_decimal_macros` | 1.36 | NEW | Decimal literal macros |

## Testing Standards

1. **Rust-native**: ≥10 compute tests — each function + Decimal edge cases + IVA rates
2. **Python integration**: Known ARCA test vectors, stock aggregation, CUIT validation
3. **Benchmark**: Measure per-function speedup vs Python
4. **Docker**: Rebuild and verify
5. **Regression**: Full suite 0 new failures

## Constraints

1. SPEC-017 must be complete
2. str↔Decimal pattern for all money values (no float!)
3. ARCA tolerance: ABSOLUTE=0.01, RELATIVE=0.0001
4. GIL release ONLY for aggregate_stock_levels
5. CUIT validation consolidated from 2 files → 1 Rust function
6. No Django model changes, no migrations
7. Python fallback mandatory
8. External test runner for pytest

## Reference Documents

| Document | Purpose | Path |
|----------|---------|------|
| Specify context | Architecture decisions | `Docs/Temp-prompting/019/instruction-specify.md` |
| Roadmap | Full spec details | `Docs/Brainstorming/rust-pyo3-speckit-roadmap.md` §5 |
| Integration Guide | Module 2 code examples | `Docs/Brainstorming/rust-pyo3-integration-guide.md` §6 |
| ARCA validators | validate_importes + validate_iva_breakdown | `backend/apps/facturacion/validators.py` (lines 89+ for IVA breakdown) |
| Sale service | IVA calculation reference | `backend/apps/ventas/services/sale_service.py` |
| Invoice skill | ARCA patterns | `skills/gravitea-invoice/SKILL.md` |
| WIKI-EXPERT brief | Shared RAG agent mission | `Docs/Temp-prompting/agents/agent-WIKI-EXPERT.md` |
