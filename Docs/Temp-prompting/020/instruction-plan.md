# Speckit Context: Data Export Pipeline — PLAN Phase (SPEC-020)

> **Phase**: PLAN — Design implementation plan, research decisions, task breakdown
> **Priority**: MEDIUM | **Wave**: 4 (parallel with SPEC-023)
> **Produces**: `plan.md`, `research.md`, `quickstart.md`
> **Does NOT produce**: data-model.md, api-contract.md (engine only, no Django models)

---

## Mission

Design the implementation plan for Rust CSV and Excel (.xlsx) generation. This spec creates the engine; the Django views/tasks connecting to `ExportJob` are part of the `reportes` app spec.

## Team Architecture

| Agent | Subagent Type | Model | Role |
|-------|--------------|-------|------|
| ORCHESTRATOR (LEAD) | system-architect | Opus 4.6 | Coordinates, validates, documentation |
| RUST-EXPERT | general-purpose | Opus 4.6 | Implements export.rs |
| BACKEND-CODER | backend-architect | Sonnet 4.6 | Creates Python wrapper, wires to ExportJob |
| QA | quality-engineer | Sonnet 4.6 | Validates output opens in Excel, benchmarks |

### Sequential-Thinking MCP

- **MANDATORY**: RUST-EXPERT (streaming architecture design)
- **NOT required**: BACKEND-CODER, QA

## Implementation Phases

### Phase 1: Rust Export Engine (RUST-EXPERT)
- **Risk**: MEDIUM (large data handling)
- Tasks:
  1. Add `csv` + `rust_xlsxwriter` to Cargo.toml
  2. Add `ExportError` variant to `GraviteaError` in `errors.rs`
  3. Create `rust/gravitea-core/src/export.rs` with 2 `#[pyfunction]` exports
  4. Implement `generate_csv` with streaming write + UTF-8 BOM
  5. Implement `generate_xlsx` with auto-detect numeric columns + configurable widths
  6. Register export submodule in `lib.rs`
  7. Write Rust-native tests: roundtrip, BOM presence, numeric detection, empty data

### Phase 2: Python Integration (BACKEND-CODER)
- **Risk**: LOW
- Tasks:
  1. Create Python wrapper `backend/apps/reportes/export_engine.py` with fallback
  2. Update `gravitea_rust.pyi` with export function signatures

### Phase 3: Quality Validation (QA)
- **Risk**: MEDIUM (Excel compatibility)
- Tasks:
  1. Write Python integration tests: CSV opens in Excel, XLSX opens in Excel
  2. Test Spanish characters (á, é, ñ, ü) render correctly
  3. Benchmark: 10K rows × 10 cols in < 2 seconds
  4. Test GIL release with concurrent Django requests

### Phase 4: Docker + Regression (LEAD)
- **Risk**: LOW
- Tasks:
  1. Rebuild Docker image — verify export functions available
  2. Run full test suite — 0 regressions
  3. Update quickstart.md

## Research Topics (for research.md)

| ID | Topic | Decision Needed | Assigned To |
|----|-------|----------------|-------------|
| R-001 | rust_xlsxwriter column width API | Confirm HashMap<String, f64> interface | RUST-EXPERT |
| R-002 | UTF-8 BOM detection by Excel versions | Verify BOM works on Excel 2016+ and LibreOffice | QA |
| R-003 | Vec<HashMap> serialization cost for 10K rows | Measure actual FFI overhead | RUST-EXPERT |
| R-004 | Streaming vs buffered CSV output | Which approach minimizes memory for 100K+ rows | RUST-EXPERT |

## Crate Dependencies

| Crate | Version | New/Shared | Purpose |
|-------|---------|-----------|---------|
| `csv` | 1 (latest 1.x) | NEW | CSV generation |
| `rust_xlsxwriter` | 0.92 | NEW | Excel generation |

## Testing Standards

1. **Rust-native**: ≥6 export tests — CSV roundtrip, XLSX roundtrip, BOM, empty, large, numeric
2. **Python integration**: Excel compatibility, Spanish characters, benchmark
3. **Performance**: 10K rows < 2 seconds (both formats)
4. **Docker**: Rebuild and verify
5. **Regression**: Full suite 0 new failures

## Reference Documents

| Document | Purpose | Path |
|----------|---------|------|
| Specify context | Architecture decisions | `Docs/Temp-prompting/020/instruction-specify.md` |
| Roadmap | Full spec details | `Docs/Brainstorming/rust-pyo3-speckit-roadmap.md` §6 |
| Integration Guide | Module 3 code examples | `Docs/Brainstorming/rust-pyo3-integration-guide.md` §7 |
| Reportes app | Skeleton models | `backend/apps/reportes/` |
