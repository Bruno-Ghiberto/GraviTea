# Speckit Context: Sync Conflict Engine (SPEC-023)

> **Phase**: SPECIFY — Define what we're accelerating and why
> **Priority**: MEDIUM | **Wave**: 4 (parallel with SPEC-020)
> **Depends on**: SPEC-017 (Rust Toolchain Bootstrap) MUST be complete

---

## Mission Statement

Replace the `_resolve_most_complete_wins()` strategy in `backend/apps/sync/conflict_resolver.py` with a Rust JSON merge function using `serde_json`. This is the only conflict resolution strategy worth accelerating — `server_wins`, `client_wins`, and `manual` are trivial assignments.

## Why This Matters Now

- **Batch amplification**: Individual call is 2-4x faster; batch of 100+ operations sees **3-8x** due to reduced GC pressure
- **Per-operation during batch sync push**: 100+ operations per offline sync session
- **GIL released** during merge computation — other sync operations proceed in parallel
- **Introduces `serde_json`** — foundational for SPEC-024 and SPEC-025

## Architecture Decisions (FINAL — Do Not Re-Debate)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Serialization crate | `serde 1.0` + `serde_json 1.0` | Standard Rust JSON handling |
| GIL handling | Single call: NOT released. Batch call (`merge_most_complete_batch`): RELEASED | Sub-ms single calls — GIL release overhead not worth it. Batch calls benefit. |
| Input/Output | JSON strings via serde | Clean boundary, ~20-40μs FFI cost |
| Strategy scope | `most_complete_wins` ONLY | Other strategies are trivial Python assignments |
| None handling | Empty strings → `null` | Must replicate Python normalization at lines 493-499 |
| Comparison rules | str by `len(stripped)`, list by `len()`, dict by key count. All other types (bool, number, mixed) → server wins | Must exactly match Python lines 514-545 |
| Return format | `(merged_json, merge_log_json)` tuple | Rust tracks decisions during traversal; 5 categories: `client_won`, `server_won`, `tied_server_won`, `both_null`, `empty_string_normalized` |
| Metadata fields | Configurable via JSON parameter | Python hardcodes `["id", "created_at", "updated_at", "sync_version"]` at line 488 — passed to Rust |

## Current State (What Exists Today)

| Item | Details |
|------|---------|
| **File** | `backend/apps/sync/conflict_resolver.py` lines 426-564 |
| **Function** | `_resolve_most_complete_wins()` |
| **Call frequency** | Per operation during batch sync push (100+ ops/session) |
| **Current cost** | ~200-500μs per operation for 50-field payloads |

## Target Architecture

### New Rust Source

```
rust/gravitea-core/src/
├── lib.rs          # Add sync submodule + re-exports
├── errors.rs       # Add SyncError variant → maps to PyRuntimeError
└── sync.rs         # NEW — merge_most_complete + merge_most_complete_batch
```

### Python Dispatcher

```
backend/apps/sync/
├── conflict_resolver.py   # MODIFIED — imports from sync_engine
└── sync_engine.py         # NEW — Rust/Python dispatch (follows ssrf_engine.py pattern)
```

### Functions to Implement

| Function | Signature | GIL Released |
|----------|-----------|-------------|
| `merge_most_complete` | `(server_json: &str, client_json: &str, metadata_fields_json: &str) -> PyResult<(String, String)>` | No |
| `merge_most_complete_batch` | `(py: Python, pairs_json: &str, metadata_fields_json: &str) -> PyResult<String>` | Yes |

### Cargo.toml Dependencies

No additions needed — `serde 1.0` and `serde_json 1.0` already present since SPEC-019.

## FFI Boundary Analysis

| Input | Size | FFI Overhead | Python Work | Rust Work | Net Gain |
|-------|------|-------------|-------------|-----------|----------|
| Single: ~5KB JSON × 2 | ~10KB | ~20-40μs | ~200-500μs | ~30-80μs | **+90-380μs (2-4x)** |
| Batch 100: ~5KB × 200 | ~500KB | ~20-40μs (once) | ~20-50ms | ~3-8ms | **+12-42ms (3-6x)** |

## Comparison Rule Catalog (Python lines 483-545 — EXACT logic)

### Step 1: Key Union
```python
all_keys = set(client_payload.keys()) | set(server_payload.keys())
```

### Step 2: Metadata Field Passthrough (line 488)
Keys in `["id", "created_at", "updated_at", "sync_version"]` → always use `server_value`, skip comparison.

### Step 3: Empty String Normalization (lines 493-499)
```python
if isinstance(value, str) and not value.strip():
    value = None  # whitespace-only → None
    merge_log["empty_string_normalized"].append(f"{key}_{side}")
```
Note: Uses `.strip()` — so `"  "` and `"\t"` also become None.

### Step 4: Null Comparison Table

| Client | Server | Result | Log Category |
|--------|--------|--------|-------------|
| None | None | None | `both_null` |
| non-None | None | client_value | `client_won` |
| None | non-None | server_value | `server_won` |

### Step 5: Type-Based Completeness (both non-None)

| Client Type | Server Type | Comparison | Client Wins When | Else |
|-------------|-------------|------------|-------------------|------|
| str | str | `len(client.strip())` vs `len(server.strip())` | `client_len > server_len` | server (`tied_server_won`) |
| list | list | `len(client)` vs `len(server)` | `len(client) > len(server)` | server (`tied_server_won`) |
| dict | dict | key count | `len(client) > len(server)` | server (`tied_server_won`) |
| **any other** | **any other** | **no comparison** | **never** | **server wins** (`tied_server_won`) |

The `else` branch (line 542-545) catches: bool/bool, number/number, bool/number, str/list, mixed types — ALL → server wins.

## Critical Caveats

1. **Serialization overhead**: Two 5KB JSON strings → parse → merge → serialize. ~20-40μs FFI cost. Net positive only for payloads with 20+ fields.
2. **Type-based comparison rules**: str by `len(stripped)`, list by `len()`, dict by key count. All other types (bool, number, mixed) → **server wins**. No `True > False` comparison exists in Python. Must EXACTLY match Python lines 514-545.
3. **None handling**: Empty strings and whitespace-only strings become None in Python (uses `.strip()`). JSON has `null`. Must replicate normalization at lines 493-499.
4. **Only `most_complete_wins`**: Other strategies (`server_wins`, `client_wins`, `manual`) stay in Python — trivial assignments not worth FFI overhead.
5. **Metadata field passthrough**: Keys `["id", "created_at", "updated_at", "sync_version"]` always take server value — skipped from comparison entirely (line 488).
6. **serde_json Number (f64) vs Python int/float**: Both are non-str/non-list/non-dict → fall to `else` branch → server wins. No numeric comparison logic exists.
7. **Merge log structure**: Rust must return the same 5 categories (`client_won`, `server_won`, `tied_server_won`, `both_null`, `empty_string_normalized`) as the second element of the return tuple.

## Success Criteria

1. `cargo test` passes with ≥8 sync tests (basic merge, deep nesting, None handling, type comparison)
2. Equivalence tests: Rust merge produces identical output to Python for all test payloads
3. Batch test: `merge_most_complete_batch` with 100 operations shows ≥3x speedup over Python
4. GIL released during batch merge only (`merge_most_complete_batch`); single call does NOT release
5. Payloads < 20 fields fall back to Python (threshold guard `_RUST_FIELD_THRESHOLD = 20` in `sync_engine.py`)
6. Fallback works without Rust extension
7. Docker builds with sync functions available
8. Full test suite passes with 0 regressions
9. Merge log parity: Rust `merge_log` JSON contains same 5 categories as Python, with identical field assignments
10. SyncError variant tested: invalid JSON input raises `RuntimeError` (mapped from `SyncError`)

## Reference Documents

| Document | Purpose | Path |
|----------|---------|------|
| Roadmap | OPP-003 details | `Docs/Brainstorming/rust-pyo3-speckit-roadmap.md` §9 |
| Acceleration opps | Deep analysis | `Docs/Brainstorming/rust-acceleration-opportunities.md` |
| Current resolver | Python implementation | `backend/apps/sync/conflict_resolver.py` |
| Sync skill | Patterns and conventions | `skills/gravitea-sync/SKILL.md` |
