# Speckit Implement Context: Data Export Pipeline (SPEC-020)

> **Phase**: IMPLEMENT — Execute the plan with agent teams
> **Priority**: MEDIUM | **Wave**: 4 (parallel with SPEC-023)
> **Version**: 2.0 (2026-02-26)

---

## IMMEDIATE EXECUTION DIRECTIVE

1. Read `specs/020-rust-data-export/tasks.md` for authoritative task list (T001–T025)
2. Execute Phase 1 (Setup: T001–T003) yourself
3. Spawn RUST-EXPERT — implements Rust engine (T004–T007 CSV, T011–T014 XLSX)
4. After RUST-EXPERT completes + maturin build:
   - Spawn BACKEND-CODER — Python wrapper + type stubs (T008–T010, T015–T017)
   - Optionally spawn WIKI-EXPERT if technical question arises
5. After BACKEND-CODER completes:
   - Spawn QA — benchmarks + fallback tests (T018–T022)
6. Execute Phase 6 (Polish: T023–T025) yourself
7. Commit and report final results

---

## Authoritative Documents

| Priority | Document | Path |
|----------|----------|------|
| 1 | tasks.md | `specs/020-rust-data-export/tasks.md` |
| 2 | plan.md | `specs/020-rust-data-export/plan.md` |
| 3 | research.md | `specs/020-rust-data-export/research.md` |
| 4 | quickstart.md | `specs/020-rust-data-export/quickstart.md` |

---

## Agent Team Architecture

| Agent | Model | subagent_type | Role | Agent File |
|-------|-------|--------------|------|------------|
| LEAD (you) | Opus 4.6 | system-architect | Orchestration, setup, polish | — |
| RUST-EXPERT | Opus 4.6 | general-purpose | export.rs: CSV + XLSX engine | `agent-RUST-EXPERT.md` |
| BACKEND-CODER | Sonnet 4.6 | backend-architect | Python wrapper + type stubs | `agent-BACKEND-CODER.md` |
| QA | Sonnet 4.6 | quality-engineer | Benchmarks + fallback tests | `agent-QA.md` |
| WIKI-EXPERT | Sonnet 4.6 | general-purpose | On-demand RAG librarian | `agent-WIKI-EXPERT.md` |

### Agent Spawn Prompts

Each agent has a dedicated instruction file in `Docs/Temp-prompting/020/`. Spawn agents by reading their instruction file into the prompt:

**RUST-EXPERT:**
```
name: "RUST-EXPERT"
model: "opus"
subagent_type: "general-purpose"
mode: "bypassPermissions"
prompt: "Read Docs/Temp-prompting/020/agent-RUST-EXPERT.md for your full mission brief."
```

**BACKEND-CODER:**
```
name: "BACKEND-CODER"
model: "sonnet"
subagent_type: "backend-architect"
mode: "bypassPermissions"
prompt: "Read Docs/Temp-prompting/020/agent-BACKEND-CODER.md for your full mission brief."
```

**QA:**
```
name: "QA"
model: "sonnet"
subagent_type: "quality-engineer"
mode: "bypassPermissions"
prompt: "Read Docs/Temp-prompting/020/agent-QA.md for your full mission brief."
```

**WIKI-EXPERT (on-demand only):**
```
name: "WIKI-EXPERT"
model: "sonnet"
subagent_type: "general-purpose"
mode: "bypassPermissions"
prompt: "Read Docs/Temp-prompting/020/agent-WIKI-EXPERT.md for your full mission brief. Challenge: <describe technical question here>"
```

---

## File Ownership Rules (STRICT)

| Agent | May Write |
|-------|-----------|
| LEAD | `rust/gravitea-core/Cargo.toml`, `rust/gravitea-core/src/errors.rs`, `rust/gravitea-core/src/lib.rs` (setup only), documentation, Docker validation |
| RUST-EXPERT | `rust/gravitea-core/src/export.rs`, `rust/gravitea-core/src/lib.rs` (export registration), `rust/gravitea-core/Cargo.toml` (if setup incomplete) |
| BACKEND-CODER | `backend/apps/reportes/export_engine.py`, `backend/gravitea_rust.pyi`, `backend/tests/reportes/test_export_020.py` (CSV + XLSX integration tests) |
| QA | `backend/tests/reportes/test_export_020.py` (benchmark + fallback tests — append to file) |
| WIKI-EXPERT | **No file writes** — returns results as text only |

---

## Execution Flow

```
LEAD: Phase 1 Setup (T001–T003)
  ├── T001 [P] Cargo.toml: +csv, +rust_xlsxwriter
  ├── T002 [P] errors.rs: +ExportError variant
  └── T003    export.rs skeleton + mod declaration in lib.rs
         │
         ▼
RUST-EXPERT: Rust Engine (T004–T007, T011–T014)
  ├── T004–T007  CSV internal + pyfunction + lib.rs + Rust tests
  └── T011–T014  XLSX internal + pyfunction + lib.rs + Rust tests
         │
         ▼ (maturin build by LEAD)
         │
BACKEND-CODER: Python Integration (T008–T010, T015–T017)
  ├── T008  export_engine.py: generate_csv() wrapper + fallback
  ├── T009  gravitea_rust.pyi: generate_csv stub
  ├── T010  pytest: CSV integration tests
  ├── T015  export_engine.py: generate_xlsx() wrapper + fallback
  ├── T016  gravitea_rust.pyi: generate_xlsx stub
  └── T017  pytest: XLSX integration tests
         │
         ▼
QA: Validation (T018–T022)
  ├── T018 [P] Benchmark: 10K CSV < 2s
  ├── T019 [P] Benchmark: 10K XLSX < 2s
  ├── T020    GIL release test
  ├── T021 [P] Fallback: CSV without Rust
  └── T022 [P] Fallback: XLSX without Rust
         │
         ▼
LEAD: Phase 6 Polish (T023–T025)
  ├── T023  Docker rebuild + import verification
  ├── T024  Full regression suite
  └── T025  Update quickstart.md
```

---

## Test Execution Protocol

```bash
# Rust tests (run from repo root)
cd rust/gravitea-core && cargo test -- --nocapture

# Python export tests only (no Django)
scripts/run-tests-external.sh "020-export" \
  "backend/venv-wsl/bin/python -m pytest \
    backend/tests/reportes/test_export_020.py \
    -p no:django --tb=short -q"

# Full regression suite
scripts/run-tests-external.sh "020-regression" \
  "backend/venv-wsl/bin/python -m pytest \
    backend/tests/ --tb=short -q --no-header"
```

---

## Maturin Build (Between Rust and Python Phases)

```bash
# LEAD runs this after RUST-EXPERT completes
VIRTUAL_ENV=$(pwd)/backend/venv-wsl maturin develop \
  --manifest-path rust/gravitea-core/Cargo.toml --release
```

This builds the `.so` that Python imports. BACKEND-CODER cannot start until this succeeds.

---

## Known Gotchas

| Issue | Cause | Fix |
|-------|-------|-----|
| `Vec<HashMap>` serialization cost | 100K entries crossing FFI for 10K rows | Accept ~50-100ms overhead; still well under 2s target |
| Excel BOM detection | Some Excel versions ignore BOM | BOM confirmed working on Excel 2016+/365/LibreOffice (R-002) |
| Column ordering | Dict keys unordered in Python | Always use `headers` list for column order — spec FR-002 |
| rust_xlsxwriter temp files | XLSX uses temp files during generation | Ensure Docker has `/tmp` writable |
| PyO3 `Option<HashMap>` | `column_widths` is optional in XLSX | Use `Option<HashMap<String, f64>>`, default to empty HashMap |
| `openpyxl` fallback | Python fallback needs openpyxl installed | Already in requirements — verify in venv |
| Numeric overflow | Very large numbers exceed f64 precision | `parse::<f64>()` fails gracefully → written as text (edge case EC-002) |

---

## WIKI-EXPERT Usage Guide

Spawn WIKI-EXPERT when the team encounters a technical question that documentation can answer. Common scenarios for SPEC-020:

| Scenario | Query Target |
|----------|-------------|
| `rust_xlsxwriter` API details | `wikis` collection — "rust_xlsxwriter autofit column width API" |
| `csv` crate RFC 4180 behavior | `wikis` collection — "csv crate RFC 4180 escaping quoting" |
| PyO3 `Option<HashMap>` extraction | `wikis` collection — "PyO3 Option HashMap Python None extraction" |
| `openpyxl` fallback patterns | `wikis` collection — "openpyxl write workbook number format column width" |
| Django `ExportJob` model (future) | `wikis` collection — "Django model async task export file" |

WIKI-EXPERT is ephemeral — spawned for a single question, delivers results, then terminates.
