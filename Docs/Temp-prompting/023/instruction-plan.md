# Speckit Context: Sync Conflict Engine — PLAN Phase (SPEC-023)

> **Phase**: PLAN — Design implementation plan, research decisions, task breakdown
> **Priority**: MEDIUM | **Wave**: 4 (parallel with SPEC-020)
> **Produces**: `plan.md`, `research.md`, `quickstart.md`
> **Does NOT produce**: data-model.md, api-contract.md

---

## Mission

Design the implementation plan for replacing the `most_complete_wins` conflict resolution strategy with a Rust JSON merge function. `serde_json` is already present in the crate since SPEC-019 — no new crate additions needed.

## Team Architecture

| Agent | Subagent Type | Model | Role |
|-------|--------------|-------|------|
| ORCHESTRATOR (LEAD) | system-architect | Opus 4.6 | Coordinates, validates, documentation |
| RUST-EXPERT | general-purpose | Opus 4.6 | Implements sync.rs |
| BACKEND-CODER | backend-architect | Sonnet 4.6 | Modifies conflict_resolver.py |
| QA | quality-engineer | Sonnet 4.6 | Sync scenario tests with real payloads |

### Sequential-Thinking MCP

- **MANDATORY**: RUST-EXPERT (serde_json tree traversal design, type comparison rules)
- **NOT required**: BACKEND-CODER, QA

## Implementation Phases

### Phase 1: Type Comparison Rule Extraction (LEAD)
- **Risk**: HIGH (comparison parity is critical)
- Tasks:
  1. Read `conflict_resolver.py` lines 426-564 — document all comparison rules
  2. Extract None normalization logic (lines 493-499)
  3. Document: str by `len(stripped)`, list by `len()`, dict by key count. All other types (bool, number, mixed) → server wins
  4. Create test payload catalog for QA

### Phase 2: Rust Implementation (RUST-EXPERT)
- **Risk**: MEDIUM
- Tasks:
  1. Verify `serde` + `serde_json` already in Cargo.toml (present since SPEC-019)
  2. Create `rust/gravitea-core/src/sync.rs`
  3. Implement `merge_most_complete` using `serde_json::Value` tree traversal
  4. Implement type-based comparison logic matching Python exactly
  5. Implement None/empty-string normalization
  6. GIL handling: NOT released for single `merge_most_complete`; RELEASED for `merge_most_complete_batch`
  7. Implement `merge_most_complete_batch` — accepts JSON array of `(server, client)` pairs, GIL released via `py.allow_threads()`
  8. Add `SyncError(String)` variant to `errors.rs` → maps to `PyRuntimeError`
  9. Return `(merged_json, merge_log_json)` tuple from both functions — merge_log has 5 categories
  10. Register sync submodule in `lib.rs`
  11. Write Rust-native tests (≥8)

### Phase 3: Python Integration (BACKEND-CODER + QA)
- **Risk**: MEDIUM
- Tasks:
  1. BACKEND-CODER: Create `backend/apps/sync/sync_engine.py` dispatcher (follows `ssrf_engine.py` pattern)
  2. BACKEND-CODER: Add threshold guard `_RUST_FIELD_THRESHOLD = 20` in `sync_engine.py`
  3. BACKEND-CODER: Modify `conflict_resolver.py` to import from `sync_engine` (not direct Rust import)
  4. BACKEND-CODER: Update `gravitea_rust.pyi` with sync signatures (both single + batch)
  5. QA: Write equivalence tests with real sync payloads (FR-001 parity)
  6. QA: Merge log parity test — verify 5 categories match Python field-by-field (SC-007)
  7. QA: Batch test: 100 operations ≥3x speedup benchmark (SC-002)
  8. QA: Verify GIL release with threading test — batch only (SC-003)
  9. QA: SyncError test — invalid JSON raises RuntimeError (SC-008)
  10. QA: Metadata passthrough test — `id`, `created_at`, `updated_at`, `sync_version` always server (FR-005)

### Phase 4: Docker + Regression (LEAD)
- **Risk**: LOW
- Tasks:
  1. Rebuild Docker, verify sync functions available
  2. Full test suite — 0 regressions
  3. Update quickstart.md

## Research Topics (for research.md)

| ID | Topic | Decision Needed | Assigned To |
|----|-------|----------------|-------------|
| R-001 | serde_json::Value comparison semantics vs Python | Document divergences | RUST-EXPERT |
| R-002 | None/null normalization edge cases | Empty string, empty list, empty dict | RUST-EXPERT |
| R-003 | Optimal threshold for Rust vs Python (field count) | Profile at 5, 10, 20, 50 fields | QA |
| R-004 | serde_json compile-time impact | Measure build time increase | RUST-EXPERT |
| R-005 | merge_log return format validation | Verify (merged_json, merge_log_json) tuple matches Python's 5-category structure | RUST-EXPERT |
| R-006 | Metadata field passthrough via parameter | JSON array vs hardcoded; confirm Rust receives configurable list | BACKEND-CODER |

## Crate Dependencies

| Crate | Version | New/Shared | Purpose |
|-------|---------|-----------|---------|
| `serde` | 1.0 (derive) | Already present (SPEC-019) | Serialization framework |
| `serde_json` | 1.0 | Already present (SPEC-019) | JSON parsing and generation |

## Testing Standards

1. **Rust-native**: ≥8 sync tests — basic merge, deep nesting, null handling, type comparison, empty payloads, metadata passthrough, mixed types (SC-006)
2. **Equivalence**: Rust merge produces byte-identical merged payloads AND identical merge decision logs as Python for all test payloads (SC-001)
3. **Merge log parity**: Rust merge_log JSON contains same 5 categories with identical field assignments (SC-007)
4. **Batch benchmark**: `merge_most_complete_batch` with 100 operations ≥3x speedup (SC-002)
5. **GIL release**: Threading concurrency test — batch only, single does NOT release (SC-003)
6. **SyncError**: Invalid JSON input raises RuntimeError mapped from SyncError (SC-008)
7. **Fallback**: System operates correctly when Rust unavailable (SC-005)
8. **Threshold guard**: Sub-20 field payloads route to Python, ≥20 route to Rust (SC-004)
9. **Docker**: Container builds with sync functions importable (SC-009)
10. **Regression**: Full suite 0 new failures (SC-010)

## Reference Documents

| Document | Purpose | Path |
|----------|---------|------|
| Feature spec | Formal specification (15 FRs, 10 SCs) | `specs/023-rust-sync-conflict/spec.md` |
| Specify context | Architecture decisions, comparison rule catalog | `Docs/Temp-prompting/023/instruction-specify.md` |
| Roadmap | OPP-003 details | `Docs/Brainstorming/rust-pyo3-speckit-roadmap.md` §9 |
| Current resolver | Python implementation (lines 426-564) | `backend/apps/sync/conflict_resolver.py` |
| Sync skill | Patterns and conventions | `skills/gravitea-sync/SKILL.md` |
