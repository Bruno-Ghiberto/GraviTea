# Implementation Plan: Rust Sync Conflict Engine

**Branch**: `023-rust-sync-conflict` | **Date**: 2026-02-27 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/023-rust-sync-conflict/spec.md`

## Summary

Accelerate the `most_complete_wins` conflict resolution strategy by implementing a Rust/PyO3 JSON merge function (`sync.rs`) that produces byte-identical output to the Python original. Two entry points: single merge (no GIL release) and batch merge (GIL released). A Python dispatcher (`sync_engine.py`) routes payloads with ≥20 fields to Rust, smaller payloads to Python, with transparent fallback if Rust is unavailable. `serde` and `serde_json` are already in `Cargo.toml` since SPEC-019 — no new crate additions.

## Technical Context

**Language/Version**: Rust 1.93.1 (PyO3 0.28, Maturin 1.12.4) + Python 3.14.3 (Django 5.2.x)
**Primary Dependencies**: `serde 1.0`, `serde_json 1.0` (both already present), `pyo3 0.28` (already present)
**Storage**: N/A — pure validation/merge functions, no persistence
**Testing**: `cargo test` (Rust-native) + `pytest` via external test runner (Python integration)
**Target Platform**: Linux (WSL2 dev, Docker prod)
**Project Type**: Library extension (PyO3 FFI module within existing `gravitea_rust` crate)
**Performance Goals**: Single merge 2-4x over Python; batch (100 pairs) ≥3x over sequential Python
**Constraints**: FFI overhead ~20-40us per crossing; net positive only for ≥20 field payloads
**Scale/Scope**: 100+ operations per offline sync session, 50-field average customer payloads

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Ironclad Data Model | N/A | Pure computation — no DB writes, no schema changes |
| II. Multi-Tenant Isolation | N/A | Operates on payload dicts, not DB queries |
| III. Modular Django | PASS | `sync_engine.py` lives in `apps/sync/` module; clear boundary |
| IV. Encryption | N/A | No PII handling — payloads may contain encrypted fields but merge is type-agnostic |
| V. Secure Auth | N/A | No auth changes |
| VI. Fiscal Compliance | N/A | No fiscal module changes |
| VII. Offline-First | ALIGNED | Accelerates `most_complete_wins` strategy documented in constitution §VII |
| VIII. Query Optimization | N/A | No QuerySets |
| IX. Secure Data Ops | N/A | No model forms or mass assignment |
| X. TDD | PASS | ≥8 Rust tests, equivalence tests, batch benchmark, regression gate. Note: Foundational phase (Phase 2) implements core Rust code before story-level tests — TDD applies within user story phases (Phase 3+), not to foundational infrastructure. |
| XI. JWT Auth | N/A | No token changes |
| XII. Rate Limiting | N/A | Internal function, not an endpoint |
| XIII. Pagination | N/A | No list endpoints |
| XIV. API Docs | N/A | No public API changes |

**Gate result**: PASS — no violations, no justification needed.

## Project Structure

### Documentation (this feature)

```text
specs/023-rust-sync-conflict/
├── plan.md              # This file
├── research.md          # Phase 0 output — 6 research decisions
├── quickstart.md        # Phase 1 output — build/test commands
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
rust/gravitea-core/src/
├── lib.rs               # MODIFIED — add sync submodule + 2 pymodule_exports
├── errors.rs            # MODIFIED — add SyncError(String) variant
└── sync.rs              # NEW — merge_most_complete + merge_most_complete_batch

backend/apps/sync/
├── conflict_resolver.py # MODIFIED — import merge from sync_engine instead of inline
└── sync_engine.py       # NEW — Rust/Python dispatch (follows ssrf_engine.py pattern)

backend/gravitea_rust.pyi
                         # MODIFIED — add merge_most_complete + merge_most_complete_batch stubs

backend/tests/rust_integration/
└── test_sync_023.py     # NEW — equivalence, batch, GIL, SyncError, metadata, fallback tests
```

**Structure Decision**: Follows established SPEC-018 through 022 pattern — Rust module in `src/`, Python dispatcher `*_engine.py` in the relevant Django app, tests in `tests/rust_integration/`.

## Implementation Phases

### Phase 1: Rule Extraction & Research (LEAD)
- **Risk**: HIGH — comparison parity is the #1 correctness risk
- **Depends on**: Nothing
- **Deliverables**: Comparison Rule Catalog (already in `instruction-specify.md`), test payload catalog, `research.md`
- **Tasks**:
  1. Read `conflict_resolver.py` lines 426-564 — verify Comparison Rule Catalog in instruction-specify.md
  2. Extract None normalization logic (lines 493-499) — `.strip()` semantics
  3. Create test payload catalog: 10+ pairs covering all edge cases from spec
  4. Resolve all 6 research topics → write `research.md`

### Phase 2: Rust Implementation (RUST-EXPERT)
- **Risk**: MEDIUM — serde_json tree traversal is well-understood
- **Depends on**: Phase 1 (comparison rules and research decisions)
- **Deliverables**: `sync.rs`, `errors.rs` update, `lib.rs` update, ≥8 cargo tests
- **Tasks**:
  1. Verify `serde` + `serde_json` already in Cargo.toml
  2. Add `SyncError(String)` variant to `errors.rs` → maps to `PyRuntimeError`
  3. Create `rust/gravitea-core/src/sync.rs`
  4. Implement `merge_most_complete(server_json, client_json, metadata_fields_json) -> PyResult<(String, String)>` — GIL NOT released
  5. Implement type-based comparison: str by `len(stripped)`, list by `len()`, dict by key count, else → server wins
  6. Implement None/empty-string normalization: whitespace-only (`.trim()`) → `Value::Null`
  7. Implement merge_log tracking: 5 categories (`client_won`, `server_won`, `tied_server_won`, `both_null`, `empty_string_normalized`)
  8. Implement metadata field passthrough: configurable list via `metadata_fields_json` parameter
  9. Implement `merge_most_complete_batch(py, pairs_json, metadata_fields_json) -> PyResult<String>` — GIL RELEASED via `py.allow_threads()`
  10. Register `mod sync;` in `lib.rs` + `#[pymodule_export]` for both functions
  11. Write ≥8 Rust-native tests: basic merge, deep nesting, null handling, each type comparison, empty payloads, metadata passthrough, mixed types, invalid JSON

### Phase 3: Python Integration (BACKEND-CODER + QA)
- **Risk**: MEDIUM — dispatcher pattern well-established
- **Depends on**: Phase 2 (Rust functions must compile and pass cargo test)
- **Deliverables**: `sync_engine.py`, modified `conflict_resolver.py`, `.pyi` stubs, test suite
- **BACKEND-CODER Tasks**:
  1. Create `backend/apps/sync/sync_engine.py` — follows `ssrf_engine.py` pattern:
     - `_USE_RUST` flag with ImportError/OSError fallback + warning log
     - `merge_most_complete()` public function: threshold guard → Rust or Python
     - `merge_most_complete_batch()` public function: always Rust if available, else sequential Python
     - `_RUST_FIELD_THRESHOLD = 20` constant
  2. Modify `conflict_resolver.py` to import `merge_most_complete` from `sync_engine` (not direct Rust)
  3. Update `backend/gravitea_rust.pyi` with both function signatures
- **QA Tasks**:
  4. Create `backend/tests/rust_integration/test_sync_023.py`:
     - Equivalence tests: Rust vs Python for 10+ payload pairs (SC-001)
     - Merge log parity: 5 categories match field-by-field (SC-007)
     - Batch benchmark: 100 pairs ≥3x speedup (SC-002)
     - GIL release: threading concurrency test — batch only (SC-003)
     - SyncError: invalid JSON → RuntimeError (SC-008)
     - Metadata passthrough: `id`, `created_at`, `updated_at`, `sync_version` always server (FR-005)
     - Fallback: mock Rust unavailable, verify Python path (SC-005)
     - Threshold guard: <20 fields → Python, ≥20 → Rust (SC-004)

### Phase 4: Docker + Regression (LEAD)
- **Risk**: LOW — established Docker pipeline
- **Depends on**: Phase 3 (all Python tests pass)
- **Deliverables**: Docker validation, regression gate, quickstart.md
- **Tasks**:
  1. `docker compose build web` — verify sync functions importable
  2. Full test suite via external runner — 0 regressions (SC-010)
  3. Update `quickstart.md` with build/test commands

## Research Topics

Resolved in [research.md](research.md).

| ID | Topic | Decision | Rationale |
|----|-------|----------|-----------|
| R-001 | serde_json::Value comparison vs Python | See research.md | String/Array/Object map cleanly; Number/Bool/Null fall to server-wins |
| R-002 | None/null normalization edge cases | See research.md | `.trim()` in Rust mirrors `.strip()` in Python |
| R-003 | Optimal threshold (field count) | 20 fields | FFI overhead ~20-40us; merge savings exceed this above ~20 fields |
| R-004 | serde_json compile-time impact | Negligible | Already compiled since SPEC-019 |
| R-005 | merge_log return format | `(String, String)` tuple | Second element is JSON with 5 categories |
| R-006 | Metadata field passthrough | JSON array parameter | Configurable, not hardcoded in Rust |

## Crate Dependencies

| Crate | Version | Status | Purpose |
|-------|---------|--------|---------|
| `serde` | 1.0 (derive) | Already present (SPEC-019) | Serialization framework |
| `serde_json` | 1.0 | Already present (SPEC-019) | JSON parsing and generation |
| `pyo3` | 0.28 | Already present (SPEC-017) | Python FFI |

No new crate additions required.

## Testing Standards

| # | Category | Criteria | Maps to |
|---|----------|----------|---------|
| 1 | Rust-native | ≥8 tests: basic merge, deep nesting, null, type comparison, empty, metadata, mixed types | SC-006 |
| 2 | Equivalence | Byte-identical merged payloads + identical merge decision logs | SC-001 |
| 3 | Merge log | Same 5 categories with identical field assignments | SC-007 |
| 4 | Batch | `merge_most_complete_batch` 100 ops ≥3x speedup | SC-002 |
| 5 | GIL release | Threading test — batch only, single does NOT release | SC-003 |
| 6 | SyncError | Invalid JSON → RuntimeError | SC-008 |
| 7 | Fallback | System works when Rust unavailable | SC-005 |
| 8 | Threshold | Sub-20 → Python, ≥20 → Rust | SC-004 |
| 9 | Docker | Container builds, functions importable | SC-009 |
| 10 | Regression | Full suite 0 new failures | SC-010 |

## FFI Boundary Analysis

| Scenario | Payload Size | FFI Overhead | Python Time | Rust Time | Net Gain |
|----------|-------------|-------------|-------------|-----------|----------|
| Single (50 fields) | ~10KB | ~20-40us | ~200-500us | ~30-80us | +90-380us (2-4x) |
| Batch 100 (50 fields) | ~500KB | ~20-40us (once) | ~20-50ms | ~3-8ms | +12-42ms (3-6x) |
| Single (<20 fields) | ~2KB | Skipped | ~50-100us | N/A | 0 (Python path) |

## Complexity Tracking

No constitution violations — table not needed.
