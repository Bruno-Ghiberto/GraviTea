# Research: Rust Sync Conflict Engine (SPEC-023)

**Date**: 2026-02-27
**Status**: Complete — all 6 topics resolved

## R-001: serde_json::Value Comparison Semantics vs Python

**Decision**: Map `serde_json::Value` variants to Python type-dispatch logic as follows.

| serde_json::Value | Python type | Comparison | Notes |
|-------------------|-------------|------------|-------|
| `Value::String` | `str` | `a.trim().len()` vs `b.trim().len()` | `.trim()` in Rust mirrors `.strip()` in Python |
| `Value::Array` | `list` | `a.len()` vs `b.len()` | Direct length comparison |
| `Value::Object` | `dict` | `a.len()` vs `b.len()` | Key count comparison |
| `Value::Number` | `int`/`float` | Server wins | Falls to else branch — no numeric comparison exists in Python |
| `Value::Bool` | `bool` | Server wins | Falls to else branch — no `True > False` comparison exists in Python |
| `Value::Null` | `None` | Handled by null comparison table | Before type-dispatch |
| Mixed types | Mixed | Server wins | `Value::String` vs `Value::Number` etc. — else branch |

**Rationale**: Python uses `isinstance()` checks that require BOTH values to be the same type (str/str, list/list, dict/dict). Any mismatch falls to the catch-all `else` branch. serde_json's `Value` enum provides clean variant matching that maps directly.

**Alternatives considered**:
- Custom `PartialOrd` impl on `Value` — rejected, Python has no ordering on these types
- Numeric precision comparison — rejected, Python doesn't compare numbers for completeness

## R-002: None/Null Normalization Edge Cases

**Decision**: Normalize whitespace-only strings to `Value::Null` using Rust's `.trim()` before comparison. Leave empty lists `[]` and empty dicts `{}` as-is (they are NOT normalized to null in Python).

**Key edge cases**:

| Input | Python behavior | Rust must do |
|-------|----------------|-------------|
| `""` (empty string) | `"".strip()` → `""` → falsy → `None` | `"".trim().is_empty()` → `Value::Null` |
| `"   "` (spaces) | `"   ".strip()` → `""` → falsy → `None` | `"   ".trim().is_empty()` → `Value::Null` |
| `"\t\n"` (whitespace) | `"\t\n".strip()` → `""` → falsy → `None` | `"\t\n".trim().is_empty()` → `Value::Null` |
| `[]` (empty list) | NOT normalized, stays `[]` | Leave as `Value::Array([])` |
| `{}` (empty dict) | NOT normalized, stays `{}` | Leave as `Value::Object({})` |
| `0` (zero) | NOT normalized, stays `0` | Leave as `Value::Number(0)` |
| `false` | NOT normalized, stays `false` | Leave as `Value::Bool(false)` |

**Rationale**: Python line 493 checks `isinstance(value, str) and not value.strip()` — only strings are normalized. All other falsy values (0, False, [], {}) pass through as-is.

**Alternatives considered**:
- Normalize empty lists/dicts to null — rejected, Python doesn't do this
- Normalize all falsy values — rejected, would break parity

## R-003: Optimal Threshold for Rust vs Python (Field Count)

**Decision**: 20 fields. Configurable via `_RUST_FIELD_THRESHOLD = 20` in `sync_engine.py`.

**Analysis** (from SPEC-022 FFI measurements and SPEC-019 profiling):

| Field count | FFI overhead | Python merge time | Rust merge time | Net gain |
|-------------|-------------|-------------------|-----------------|----------|
| 5 fields | ~20-40us | ~30-60us | ~10-20us | -10 to +20us (break-even) |
| 10 fields | ~20-40us | ~60-120us | ~15-30us | +5 to +70us (marginal) |
| 20 fields | ~20-40us | ~120-250us | ~25-50us | +50 to +160us (positive) |
| 50 fields | ~20-40us | ~300-600us | ~40-80us | +180 to +480us (strong) |

**Rationale**: At 20 fields, even worst-case FFI overhead (40us) is recouped. Below 20, the overhead can exceed savings. The threshold lives in the Python dispatcher so it can be tuned without Rust recompilation.

**Alternatives considered**:
- 10 fields — rejected, marginal gains don't justify FFI complexity
- 50 fields — rejected, too conservative, misses many real payloads
- Dynamic threshold — rejected, adds complexity with minimal benefit

## R-004: serde_json Compile-Time Impact

**Decision**: Negligible — `serde` and `serde_json` are already compiled and cached since SPEC-019.

**Evidence**: `Cargo.toml` lines 22-23 show `serde = { version = "1.0", features = ["derive"] }` and `serde_json = "1.0"` present since SPEC-019 (commit `710994e`). Incremental builds only recompile `sync.rs` itself.

**Measured impact** (from SPEC-019 build logs):
- First build with serde: ~45s additional
- Incremental builds after: 0s additional (already cached)
- Adding `sync.rs`: ~2-4s incremental (new file compilation only)

## R-005: Merge Log Return Format

**Decision**: Return `(String, String)` tuple from Rust — first element is merged JSON, second is merge_log JSON.

**Merge log JSON structure**:
```json
{
  "client_won": ["field_a", "field_b"],
  "server_won": ["field_c"],
  "tied_server_won": ["field_d", "field_e"],
  "both_null": ["field_f"],
  "empty_string_normalized": ["field_a_client", "field_g_server"]
}
```

**Notes**:
- `empty_string_normalized` entries use `{key}_{side}` format matching Python (e.g., `"name_client"`)
- Arrays are ordered by key iteration order (HashMap in Rust — not guaranteed same order as Python's dict). Test assertions must compare sorted arrays or use set equality.
- Batch function returns a JSON array of `{"merged": ..., "merge_log": ...}` objects

**Rationale**: Tuple return avoids introducing a custom Python class at the FFI boundary. JSON strings are the established pattern (SPEC-018 through 022). The merge_log enables the caller (`conflict_resolver.py`) to reconstruct the `audit_log["merge_decisions"]` dict.

**Alternatives considered**:
- Return single JSON with both merged + log — rejected, forces caller to parse a wrapper
- Return PyDict directly — rejected, PyO3 dict construction is slower than JSON string passing for this size

## R-006: Metadata Field Passthrough via Parameter

**Decision**: Pass metadata fields as a JSON array string parameter (`metadata_fields_json`). Rust deserializes once into `HashSet<String>` for O(1) lookup.

**Function signatures**:
```rust
fn merge_most_complete(server_json: &str, client_json: &str, metadata_fields_json: &str) -> PyResult<(String, String)>
fn merge_most_complete_batch(py: Python, pairs_json: &str, metadata_fields_json: &str) -> PyResult<String>
```

**Python dispatcher** passes the default set:
```python
_DEFAULT_METADATA_FIELDS = '["id", "created_at", "updated_at", "sync_version"]'
```

**Rationale**: Making metadata fields a parameter keeps Rust generic. The Python dispatcher hardcodes the default (matching `conflict_resolver.py` line 488) but allows future callers to pass different sets. JSON array string avoids PyO3 list conversion overhead.

**Alternatives considered**:
- Hardcode in Rust — rejected, reduces flexibility for future entity types
- Pass as Python list — rejected, PyO3 list→Vec conversion slower than JSON parse for 4 elements
- Compile-time constant — rejected, can't be changed without Rust recompilation
