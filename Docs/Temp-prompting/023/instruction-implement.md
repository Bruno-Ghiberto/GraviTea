# SPEC-023: Rust Sync Conflict Engine — Implementation Instructions

| Field | Value |
|-------|-------|
| **Phase** | Implementation (all speckit phases complete) |
| **Priority** | P1 (MVP: US1 single parity), P2 (US2 batch + US3 fallback), P3 (US4 threshold) |
| **Wave** | Phase 1–2 sequential → Phase 3–4 parallel → Phase 5–7 sequential |
| **Version** | 2.0 (2026-02-27) — aligned with spec.md, plan.md, tasks.md, research.md |
| **Dependencies** | `serde 1.0` + `serde_json 1.0` (already present since SPEC-019), `pyo3 0.28` (SPEC-017) |

---

## 1. IMMEDIATE EXECUTION DIRECTIVE

When you read this file, execute these steps IN ORDER:

1. **Read authoritative documents** (Section 2) in priority order
2. **Spawn team** using Claude Code `TeamCreate` with team name `sync-023`
3. **Create tasks** from `specs/023-rust-sync-conflict/tasks.md` (29 tasks, 7 phases)
4. **Spawn agents** per Section 3 — one tmux pane per agent (auto-detected)
5. **Assign Phase 1 tasks** (T001–T003) — LEAD executes T001, parallel T002+T003
6. **Execute Phase 2** (T004–T007) — RUST-EXPERT implements, LEAD verifies compilation
7. **Gate**: `cargo build` must succeed before ANY Phase 3+ work
8. **Execute Phases 3–7** per Execution Flow (Section 5) — parallel where marked [P]
9. **Commit** after each phase checkpoint (plan.md §Implementation Strategy)

---

## 2. Authoritative Documents

Read these in priority order. If any document conflicts, higher priority wins.

| Priority | Document | Path | What It Decides |
|----------|----------|------|-----------------|
| 1 | Feature Spec | `specs/023-rust-sync-conflict/spec.md` | Requirements (15 FRs), success criteria (10 SCs), user stories, edge cases |
| 2 | Implementation Plan | `specs/023-rust-sync-conflict/plan.md` | Architecture, phases, constitution check, FFI analysis |
| 3 | Research Decisions | `specs/023-rust-sync-conflict/research.md` | 6 resolved decisions (R-001–R-006): comparison semantics, normalization, threshold, return format, metadata |
| 4 | Task List | `specs/023-rust-sync-conflict/tasks.md` | 29 tasks (T001–T029), 7 phases, dependencies, parallel markers |
| 5 | Quickstart | `specs/023-rust-sync-conflict/quickstart.md` | Build commands, test commands, Docker validation |
| 6 | Python Source | `backend/apps/sync/conflict_resolver.py` lines 426–564 | `_resolve_most_complete_wins()` — THE reference implementation for parity |

---

## 3. Agent Team Architecture

| Agent | Model | Role | Agent File | Tasks |
|-------|-------|------|------------|-------|
| **LEAD** | Opus | Orchestrator — setup, gates, Docker, regression | *(you — this file)* | T001, T007, T010, T016, T027–T029 |
| **RUST-EXPERT** | Opus | Rust implementation — sync.rs, errors.rs, lib.rs | `agent-RUST-EXPERT.md` | T002–T006, T008–T009, T013–T015 |
| **BACKEND-CODER** | Sonnet | Python integration — sync_engine.py, conflict_resolver.py, .pyi | `agent-BACKEND-CODER.md` | T019, T022, T025–T026 |
| **QA** | Sonnet | Test creation — test_sync_023.py (all categories) | `agent-QA.md` | T011–T012, T017–T018, T020–T021, T023–T024 |
| **WIKI-EXPERT** | Sonnet | On-demand RAG librarian — ephemeral, query Qdrant | `agent-WIKI-EXPERT.md` | On-demand only |

### Agent Spawn Prompts

**RUST-EXPERT** (Opus — persistent throughout Phases 1–4):
```
Read Docs/Temp-prompting/023/agent-RUST-EXPERT.md thoroughly. You are the RUST-EXPERT
agent for SPEC-023 (Rust Sync Conflict Engine). Your mission: implement sync.rs with
merge_most_complete + merge_most_complete_batch, add SyncError to errors.rs, register
in lib.rs, write ≥8 Rust-native tests. Follow the agent file exactly.
```

**BACKEND-CODER** (Sonnet — spawn after Phase 2 gate):
```
Read Docs/Temp-prompting/023/agent-BACKEND-CODER.md thoroughly. You are the BACKEND-CODER
agent for SPEC-023 (Rust Sync Conflict Engine). Your mission: create sync_engine.py
dispatcher, modify conflict_resolver.py imports, update gravitea_rust.pyi stubs.
Follow the agent file exactly.
```

**QA** (Sonnet — spawn after Phase 2 gate, writes tests for US1–US4):
```
Read Docs/Temp-prompting/023/agent-QA.md thoroughly. You are the QA agent for SPEC-023
(Rust Sync Conflict Engine). Your mission: create test_sync_023.py with equivalence,
batch benchmark, GIL, SyncError, fallback, and threshold tests. ALL tests via external
runner. Follow the agent file exactly.
```

**WIKI-EXPERT** (Sonnet — ephemeral, spawn on-demand only):
```
Read Docs/Temp-prompting/023/agent-WIKI-EXPERT.md thoroughly. You are the WIKI-EXPERT
agent for SPEC-023. Answer the following question using Qdrant RAG: {QUESTION}
```

### Claude Code Team Spawn Commands

```python
# Step 1: Create team (auto-detects tmux for multi-pane orchestration)
TeamCreate(team_name="sync-023", description="SPEC-023 Rust Sync Conflict Engine")

# Step 2: Spawn RUST-EXPERT (Opus — one tmux pane)
Task(
    name="RUST-EXPERT",
    team_name="sync-023",
    subagent_type="general-purpose",
    model="opus",
    mode="bypassPermissions",
    prompt="Read Docs/Temp-prompting/023/agent-RUST-EXPERT.md thoroughly..."
)

# Step 3: Spawn BACKEND-CODER (Sonnet — one tmux pane) — after Phase 2 gate
Task(
    name="BACKEND-CODER",
    team_name="sync-023",
    subagent_type="general-purpose",
    model="sonnet",
    mode="bypassPermissions",
    prompt="Read Docs/Temp-prompting/023/agent-BACKEND-CODER.md thoroughly..."
)

# Step 4: Spawn QA (Sonnet — one tmux pane) — after Phase 2 gate
Task(
    name="QA",
    team_name="sync-023",
    subagent_type="general-purpose",
    model="sonnet",
    mode="bypassPermissions",
    prompt="Read Docs/Temp-prompting/023/agent-QA.md thoroughly..."
)

# Step 5: Spawn WIKI-EXPERT (Sonnet — ephemeral, on-demand only)
Task(
    name="WIKI-EXPERT",
    team_name="sync-023",
    subagent_type="general-purpose",
    model="sonnet",
    mode="bypassPermissions",
    prompt="Read Docs/Temp-prompting/023/agent-WIKI-EXPERT.md thoroughly. Answer: {QUESTION}"
)
```

---

## 4. File Ownership Rules

**STRICT**: Only the assigned agent may WRITE to these files. Others may READ.

| File | WRITE Owner | Purpose |
|------|-------------|---------|
| `rust/gravitea-core/src/sync.rs` | RUST-EXPERT | Core merge implementation + Rust tests |
| `rust/gravitea-core/src/errors.rs` | RUST-EXPERT | SyncError(String) variant |
| `rust/gravitea-core/src/lib.rs` | RUST-EXPERT | Module registration + pymodule_export |
| `backend/apps/sync/sync_engine.py` | BACKEND-CODER | Rust/Python dispatcher |
| `backend/apps/sync/conflict_resolver.py` | BACKEND-CODER | Import change only |
| `backend/gravitea_rust.pyi` | BACKEND-CODER | Type stubs |
| `backend/tests/rust_integration/test_sync_023.py` | QA | All Python integration tests |

**Shared READ access** (all agents):
- `specs/023-rust-sync-conflict/*` (all spec files)
- `backend/apps/sync/conflict_resolver.py` lines 426–564 (reference implementation)
- `Docs/Temp-prompting/023/*` (instruction + agent files)

---

## 5. Execution Flow

```
Phase 1: Setup ──────────────────────────────────────────────────
  LEAD: T001 (verify Cargo.toml)
  ┌─ RUST-EXPERT: T002 (SyncError in errors.rs)     ─┐ [P]
  └─ RUST-EXPERT: T003 (mod sync in lib.rs)          ─┘ [P]

Phase 2: Foundational (BLOCKS ALL USER STORIES) ────────────────
  RUST-EXPERT: T004 (normalize_value helper)
            → T005 (compare_completeness helper)
            → T006 (merge_most_complete #[pyfunction])
  LEAD: T007 (pymodule_export + cargo build gate)
  ════════════════ GATE: cargo build SUCCESS ═════════════════════

Phase 3: US1 — Single Parity (MVP) ─────────────────────────────
  ┌─ RUST-EXPERT: T008 (≥8 Rust tests in sync.rs)   ─┐
  │  RUST-EXPERT: T009 (cargo test sync)              │
  │                                                    │ [P after
  │  RUST-EXPERT: T013 (batch function in sync.rs)    │  T006]
  │  RUST-EXPERT: T014 (pymodule_export batch)        │
  └─ RUST-EXPERT: T015 (Rust batch test)             ─┘

  LEAD: T010 (maturin develop — single wheel)
  ═══════════ GATE: maturin develop SUCCESS ═══════════

  QA: T011 (equivalence + merge_log + SyncError tests)
  QA: T012 (pytest US1 via external runner)

Phase 4: US2 — Batch Acceleration ──────────────────────────────
  LEAD: T016 (rebuild wheel — now includes batch)
  QA: T017 (batch benchmark + GIL tests)
  QA: T018 (pytest US2 via external runner)

Phase 5: US3 — Graceful Fallback ──────────────────────────────
  BACKEND-CODER: T019 (create sync_engine.py dispatcher)
  QA: T020 (fallback tests)
  QA: T021 (pytest US3 via external runner)

Phase 6: US4 — Threshold Guard ─────────────────────────────────
  BACKEND-CODER: T022 (threshold routing in sync_engine.py)
  QA: T023 (threshold guard tests)
  QA: T024 (pytest US4 via external runner)

Phase 7: Polish & Cross-Cutting ────────────────────────────────
  ┌─ BACKEND-CODER: T025 (conflict_resolver.py import) ─┐
  ├─ BACKEND-CODER: T026 (gravitea_rust.pyi stubs)      ├ [P]
  └─ LEAD: T027 (Docker validation)                     ─┘
  LEAD: T028 (full regression test)
  LEAD: T029 (quickstart.md validation)
```

---

## 6. Test Execution Protocol

**MANDATORY**: ALL tests (Rust and Python) MUST use the external test runner. NO EXCEPTIONS.

### Rust Tests (cargo test)

```bash
# T009: Rust-native sync tests (≥8 tests)
scripts/run-tests-external.sh -n "cargo-sync-023" \
  "cd rust/gravitea-core && cargo test sync -- --nocapture 2>&1"

# Read results (agents read ONLY .summary — NEVER .log):
# cat Docs/Tests/cargo-sync-023.summary
```

### Maturin Build (between Rust and Python phases)

```bash
# T010 / T016: Build wheel into WSL venv
VIRTUAL_ENV=$(pwd)/backend/venv-wsl maturin develop \
  --manifest-path rust/gravitea-core/Cargo.toml --release
```

### Python Tests (pytest)

```bash
# T012: US1 — equivalence, merge_log, SyncError tests
scripts/run-tests-external.sh -n "sync-023-us1" \
  "cd backend && venv-wsl/bin/python -m pytest tests/rust_integration/test_sync_023.py -k 'parity or equivalence or merge_log or sync_error' --tb=short -q"

# T018: US2 — batch benchmark + GIL tests
scripts/run-tests-external.sh -n "sync-023-us2" \
  "cd backend && venv-wsl/bin/python -m pytest tests/rust_integration/test_sync_023.py -k 'batch or gil' --tb=short -q"

# T021: US3 — fallback tests
scripts/run-tests-external.sh -n "sync-023-us3" \
  "cd backend && venv-wsl/bin/python -m pytest tests/rust_integration/test_sync_023.py -k 'fallback' --tb=short -q"

# T024: US4 — threshold guard tests
scripts/run-tests-external.sh -n "sync-023-us4" \
  "cd backend && venv-wsl/bin/python -m pytest tests/rust_integration/test_sync_023.py -k 'threshold' --tb=short -q"

# T028: Full regression
scripts/run-tests-external.sh -n "regression-023" \
  "cd backend && venv-wsl/bin/python -m pytest tests/ --tb=short -q --no-header"
```

### Docker Tests

```bash
# T027: Docker validation
docker compose build web
docker compose run --rm --entrypoint python web -c \
  "from gravitea_rust import merge_most_complete, merge_most_complete_batch; print('OK')"
```

### Test Output Protocol

| File | Purpose | Agent Action |
|------|---------|-------------|
| `Docs/Tests/{name}.status` | Exit code (0=pass) | Check first |
| `Docs/Tests/{name}.summary` | ~20 lines summary | Read this ONLY |
| `Docs/Tests/{name}.log` | Full output | NEVER read in full — `grep "FAIL\|Error"` only if debugging |

---

## 7. Known Gotchas

| # | Gotcha | Impact | Mitigation |
|---|--------|--------|------------|
| 1 | serde/serde_json already in Cargo.toml | Build fails if duplicate | Verify present (T001), do NOT add again |
| 2 | Boolean comparison: NO `True > False` | Wrong merge results | Bool/Number/Mixed → server wins (else branch). See research.md R-001 |
| 3 | GIL release: single vs batch | Deadlock or perf regression | `merge_most_complete`: GIL NOT released. `merge_most_complete_batch`: GIL RELEASED via `py.allow_threads()` |
| 4 | `.trim()` vs `.strip()` | Whitespace normalization parity | Rust `.trim()` mirrors Python `.strip()`. Only strings normalized — NOT empty lists/dicts (R-002) |
| 5 | HashMap iteration order | Merge log array order differs | Test assertions MUST use sorted list comparison or set equality (R-005) |
| 6 | `empty_string_normalized` format | Wrong merge log entries | Uses `{key}_{side}` format: e.g., `"name_client"`, `"phone_server"` |
| 7 | FR-012: both-empty payloads | New guard clause | Raises SyncError (intentionally diverges from Python). Equivalence tests MUST exclude this case |
| 8 | Metadata passthrough | Wrong field comparison | `["id", "created_at", "updated_at", "sync_version"]` → always server, skip comparison entirely |
| 9 | PyO3 0.28 GIL release | API change from 0.22 | Use `py.allow_threads(|| { ... })` — NOT `py.detach()` for batch function |
| 10 | Stale venv after maturin | Import errors in pytest | After EVERY `maturin develop`, verify: `python -c "from gravitea_rust import merge_most_complete"` |
| 11 | Test DB port | Django uses 5433 | `DJANGO_SETTINGS_MODULE=gravitea.settings.test_postgres` (postgres-test on 5433) |
| 12 | Agent permissions in tmux | Interactive prompts block panes | Spawn agents with `mode: "bypassPermissions"` |

---

## 8. WIKI-EXPERT Usage Guide

Spawn WIKI-EXPERT on-demand when any agent needs external knowledge. Examples:

| Scenario | Query to Ask |
|----------|-------------|
| serde_json::Value traversal patterns | "How to iterate serde_json::Value keys and compare nested values" |
| PyO3 allow_threads pattern | "PyO3 0.28 py.allow_threads closure pattern for batch processing" |
| Python strip() vs Rust trim() | "Unicode whitespace handling differences between Python str.strip() and Rust str.trim()" |
| Conflict resolution strategies | "most_complete_wins merge strategy patterns in offline-first sync systems" |
| HashMap vs BTreeMap ordering | "serde_json serialization order: HashMap vs BTreeMap for deterministic JSON output" |

**Protocol**: LEAD spawns WIKI-EXPERT → passes question → reads answer → forwards to requesting agent → WIKI-EXPERT shuts down.

---

## 9. Comparison Rule Catalog

Reference for RUST-EXPERT (sync.rs) and QA (test_sync_023.py). Extracted from `conflict_resolver.py` lines 483–545.

### Step 1: Key Union
Merge ALL keys from both server and client payloads. Missing key on one side = that side has `null` for that field.

### Step 2: Metadata Field Passthrough (line 488)
If field name is in `metadata_fields` set → always take server value, skip comparison, do NOT log in merge decisions.

### Step 3: Empty String Normalization (lines 493–499)
```python
# Python:
if isinstance(value, str) and not value.strip():
    value = None  # normalized
```
- `""` → `null` (logged as `empty_string_normalized` with `{key}_{side}`)
- `"   "` → `null`
- `"\t\n"` → `null`
- `[]`, `{}`, `0`, `false` → NOT normalized (left as-is)

### Step 4: Null Comparison Table
| Server | Client | Winner | Log Category |
|--------|--------|--------|-------------|
| `null` | `null` | Server (null) | `both_null` |
| non-null | `null` | Server | `server_won` |
| `null` | non-null | Client | `client_won` |

### Step 5: Type-Based Completeness
| Server Type | Client Type | Comparison | Client Wins When | Tie → |
|-------------|-------------|-----------|-----------------|-------|
| `str` | `str` | `len(trimmed)` | `client > server` (strictly) | Server |
| `list` | `list` | `len()` | `client > server` (strictly) | Server |
| `dict` | `dict` | `key count` | `client > server` (strictly) | Server |
| Any | Any (mismatch) | None | Never | Server |
| `bool` | `bool` | None | Never | Server |
| `number` | `number` | None | Never | Server |

### Merge Log Categories
- `client_won`: Client value strictly more complete
- `server_won`: Server value wins (non-null vs null, or type comparison)
- `tied_server_won`: Same completeness measure → server wins by default
- `both_null`: Both values are null after normalization
- `empty_string_normalized`: Field had whitespace-only string converted to null (format: `{key}_{side}`)

---

## 10. FFI Boundary Reference

| Scenario | Payload Size | FFI Overhead | Python Time | Rust Time | Net Gain |
|----------|-------------|-------------|-------------|-----------|----------|
| Single (50 fields) | ~10KB | ~20-40us | ~200-500us | ~30-80us | +90-380us (2-4x) |
| Batch 100 (50 fields) | ~500KB | ~20-40us (once) | ~20-50ms | ~3-8ms | +12-42ms (3-6x) |
| Single (<20 fields) | ~2KB | Skipped | ~50-100us | N/A | 0 (Python path) |

---

## 11. Function Signatures Reference

### Rust (sync.rs)

```rust
/// Single merge — GIL NOT released
#[pyfunction]
pub fn merge_most_complete(
    server_json: &str,
    client_json: &str,
    metadata_fields_json: &str,
) -> PyResult<(String, String)>
// Returns: (merged_json, merge_log_json)

/// Batch merge — GIL RELEASED via py.allow_threads()
#[pyfunction]
pub fn merge_most_complete_batch(
    py: Python,
    pairs_json: &str,
    metadata_fields_json: &str,
) -> PyResult<String>
// Returns: JSON array of {"merged": ..., "merge_log": ...} objects
```

### Python Dispatcher (sync_engine.py)

```python
_USE_RUST: bool  # True if gravitea_rust importable
_RUST_FIELD_THRESHOLD: int = 20
_DEFAULT_METADATA_FIELDS: str = '["id", "created_at", "updated_at", "sync_version"]'

def merge_most_complete(server: dict, client: dict, metadata_fields: list[str] | None = None) -> tuple[dict, dict]:
    """Route to Rust (≥20 fields) or Python (<20 fields). Returns (merged, merge_log)."""

def merge_most_complete_batch(pairs: list[dict], metadata_fields: list[str] | None = None) -> list[dict]:
    """Always Rust if available. Returns list of {"merged": ..., "merge_log": ...}."""
```

### Error Mapping

| Rust Error | Python Exception | Trigger |
|-----------|-----------------|---------|
| `SyncError(String)` | `RuntimeError` | Invalid JSON, both-empty payloads (FR-012) |
