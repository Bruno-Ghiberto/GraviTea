# Speckit Implement Context: Custom Field Type Validator Acceleration (SPEC-025)

> **Phase**: IMPLEMENT — Execute the plan with agent teams
> **Priority**: MEDIUM | **Wave**: 6
> **Version**: 2.0 (2026-02-28) — Solidified from instruction-plan.md
> **Branch**: `025-rust-custom-field-validator`

---

## IMMEDIATE EXECUTION DIRECTIVE

1. Read `specs/025-rust-custom-field-validator/tasks.md` for authoritative task list (T001–T020)
2. Execute **Phase 1 (Setup)** yourself: T001 (errors.rs) + T002 (lib.rs registration)
3. Spawn **RUST-EXPERT** for Phase 2 (Foundational): T003–T006
4. After RUST-EXPERT delivers, run `maturin develop` to install wheel into venv-wsl
5. Spawn **QA** for Phases 3–6: T007–T015 (all Python integration + parity + threshold + fallback tests)
6. Execute **Phase 7 (Polish)** yourself: T016–T020 (Docker, regression, quickstart)
7. Spawn **WIKI-EXPERT** on-demand if any agent needs RAG documentation lookup
8. Report final results

---

## Authoritative Documents

| Priority | Document | Path |
|----------|----------|------|
| 1 | **Tasks** (T001–T020) | `specs/025-rust-custom-field-validator/tasks.md` |
| 2 | **Plan** (phases, architecture) | `specs/025-rust-custom-field-validator/plan.md` |
| 3 | **Spec** (FRs, SCs, edge cases) | `specs/025-rust-custom-field-validator/spec.md` |
| 4 | **Research** (6 resolved decisions) | `specs/025-rust-custom-field-validator/research.md` |
| 5 | **Validation logic + dispatcher code** | `Docs/Temp-prompting/025/instruction-specify.md` §Validation Logic / §Dispatcher Pattern |
| 6 | **Quickstart** (build/test commands) | `specs/025-rust-custom-field-validator/quickstart.md` |

---

## Agent Team Architecture

| Agent | Model | subagent_type | mode | Role |
|-------|-------|--------------|------|------|
| **LEAD** (you) | Opus 4.6 | system-architect | — | Orchestration, setup, Docker, regression |
| **RUST-EXPERT** | Opus 4.6 | general-purpose | bypassPermissions | validation.rs implementation + cargo tests |
| **QA** | Sonnet 4.6 | python-expert | bypassPermissions | validation_engine.py, customization.py integration, all pytest |
| **WIKI-EXPERT** | Sonnet 4.6 | general-purpose | bypassPermissions | Ephemeral RAG librarian (on-demand only) |

### Why 3+1 Agents

- **BACKEND-CODER was eliminated**: QA handles both the dispatcher creation and the customization.py modification — they are tightly coupled and belong to the same agent.
- **WIKI-EXPERT is ephemeral**: Spawned only when RUST-EXPERT or QA needs Qdrant documentation lookup. Terminates after each answer.

---

## Tmux Multi-Pane Orchestration

### Auto-Detection Protocol

Before spawning agents, detect tmux availability:

```bash
# Check if running inside tmux
if [ -n "$TMUX" ]; then
    echo "TMUX detected — using multi-pane orchestration"
else
    echo "No TMUX — using sequential agent execution"
fi
```

### Team Spawn Pattern (Claude Agent Teams)

```python
# Step 1: Create team
TeamCreate(team_name="custom-fields-025", description="SPEC-025 Custom Field Type Validator Acceleration")

# Step 2: Spawn RUST-EXPERT in dedicated pane
Task(
    name="RUST-EXPERT",
    team_name="custom-fields-025",
    subagent_type="general-purpose",
    model="opus",
    mode="bypassPermissions",
    prompt="<contents of agent-RUST-EXPERT.md>"
)

# Step 3: After RUST-EXPERT completes, spawn QA
Task(
    name="QA",
    team_name="custom-fields-025",
    subagent_type="python-expert",
    model="sonnet",
    mode="bypassPermissions",
    prompt="<contents of agent-QA.md>"
)

# Step 4: On-demand WIKI-EXPERT (ephemeral)
Task(
    name="WIKI-EXPERT",
    team_name="custom-fields-025",
    subagent_type="general-purpose",
    model="sonnet",
    mode="bypassPermissions",
    prompt="<question-specific prompt from agent-WIKI-EXPERT.md>"
)
```

### Pane Layout

```
┌─────────────────────────────────────────┐
│ LEAD (Pane 0) — orchestration           │
├───────────────────┬─────────────────────┤
│ RUST-EXPERT       │ QA                  │
│ (Pane 1)          │ (Pane 2)            │
│ Phase 2: T003-T06 │ Phase 3-6: T07-T15  │
└───────────────────┴─────────────────────┘
```

- WIKI-EXPERT does NOT get a persistent pane — spawned as ephemeral Task when needed
- Each agent runs in its own tmux pane for visibility
- LEAD monitors all panes and coordinates handoffs

---

## File Ownership Rules (STRICT)

| Agent | May Write | May NOT Write |
|-------|-----------|---------------|
| **LEAD** | `errors.rs`, `lib.rs`, Docker validation, `quickstart.md` | `validation.rs`, `validation_engine.py`, test files |
| **RUST-EXPERT** | `validation.rs` (NEW) | `errors.rs`, `lib.rs`, Python files |
| **QA** | `validation_engine.py` (NEW), `customization.py` (MODIFY), `gravitea_rust.pyi` (MODIFY), `test_custom_fields_025.py` (NEW) | Rust files |
| **WIKI-EXPERT** | **No file writes** — returns text to LEAD only | Everything |

---

## Phase Execution Plan

### Phase 1: Setup (LEAD — T001, T002)

**T001**: Add `ValidationFieldError(String)` variant to `rust/gravitea-core/src/errors.rs`
- Follow existing pattern (CryptoError, ComputeError, ExportError, SecurityError, SyncError, ARCABuildError)
- Map to `PyValueError::new_err(msg)` — NOT `PyRuntimeError` (validation errors are value errors)

**T002**: Register module in `rust/gravitea-core/src/lib.rs`
- Add `mod validation;`
- Add `#[pymodule_export] use super::validation::validate_custom_fields;`

**Gate**: `cargo build` succeeds (validation.rs can be empty placeholder for now)

### Phase 2: Foundational — Rust Core (RUST-EXPERT — T003–T006)

Spawn RUST-EXPERT with `Docs/Temp-prompting/025/agent-RUST-EXPERT.md`.

RUST-EXPERT reads `instruction-specify.md` §Validation Logic and implements:
- **T003**: `FieldDefinition` serde input struct + `validate_custom_fields` PyO3 function signature
- **T004**: 6 field type validators (text, integer, decimal, boolean, date, select) with exact error messages
- **T005**: Select error format with single-quote Python list repr parity
- **T006**: ≥10 cargo tests

**Gate**: `cargo test validation` passes with ≥10 tests

**LEAD action after gate**: Run `maturin develop` to install wheel:
```bash
VIRTUAL_ENV=$(pwd)/backend/venv-wsl maturin develop \
  --manifest-path rust/gravitea-core/Cargo.toml --release
```

### Phase 3–6: Python Integration + Tests (QA — T007–T015)

Spawn QA with `Docs/Temp-prompting/025/agent-QA.md`.

QA creates the dispatcher, modifies customization.py, and writes all integration tests:
- **T007** [US1]: Create `validation_engine.py` dispatcher with `_USE_RUST`, threshold guard (>5), `_DecimalEncoder`
- **T008** [US1]: Modify `customization.py` — replace lines 80-91 with `validate_fields()` call
- **T009** [P] [US1]: Update `gravitea_rust.pyi` with function stub
- **T010** [US1]: Write parity tests for all 6 field types (valid + invalid, Rust == Python)
- **T011** [US1]: Write benchmark test (25 fields, all 6 types, < 2ms)
- **T012** [US2]: Write edge case parity tests (null, undefined keys, bool/int, Decimal, empty, unknown type)
- **T013** [US2]: Write select error format parity test (single-quote byte-identical)
- **T014** [US3]: Write threshold guard tests (3→Python, 5→Python, 6→Rust)
- **T015** [US4]: Write fallback tests (`_USE_RUST=False` → correct output + warning logged)

**Gate**: All pytest pass via external runner

### Phase 7: Polish (LEAD — T016–T020)

- **T016**: Docker build: `docker compose build web`
- **T017**: Docker import check: `from gravitea_rust import validate_custom_fields`
- **T018**: Run SPEC-025 tests in Docker
- **T019**: Full regression — 69 existing custom field tests pass with 0 new failures
- **T020**: Update `quickstart.md` with final results

---

## Test Execution Protocol (MANDATORY — Zero Exceptions)

### Rule: ALL Tests Via External Runner

Every agent MUST use `scripts/run-tests-external.sh` for ALL test execution. No exceptions.

```bash
# Rust tests (cargo)
scripts/run-tests-external.sh -n "cargo-validation-025" \
  "cd rust/gravitea-core && cargo test validation -- --nocapture 2>&1"

# Python integration tests
scripts/run-tests-external.sh -n "fields-025-us1" \
  tests/rust_integration/test_custom_fields_025.py

# Python tests with marker filter
scripts/run-tests-external.sh -n "fields-025-parity" \
  tests/rust_integration/test_custom_fields_025.py -k "parity"

# Full regression (69 existing custom field tests)
scripts/run-tests-external.sh -n "fields-025-regression" \
  "tests/core/test_customization.py tests/core/test_custom_fields_integration.py tests/core/test_custom_fields_edge_cases.py tests/core/test_custom_fields_serializer.py"
```

### Output Files

All test logs are saved to `Docs/Tests/`:

| File | Content | Agent Action |
|------|---------|-------------|
| `Docs/Tests/{name}.summary` | Token-efficient summary (~20 lines) | **READ THIS** |
| `Docs/Tests/{name}.log` | Full verbose output | **NEVER read in full** — grep only |
| `Docs/Tests/{name}.status` | Single word: PASS or FAIL | Quick check |

### Reading Results

```bash
# Always read .summary ONLY
cat Docs/Tests/cargo-validation-025.summary

# If failures, grep the log for specific errors
grep "FAIL\|Error\|panicked" Docs/Tests/cargo-validation-025.log
```

**NEVER run `cargo test`, `pytest`, or `python -m pytest` directly in agent context.**

---

## Key Decisions (Corrected — FINAL)

| Decision | Correct Value | Wrong (from Draft 1.0) |
|----------|---------------|----------------------|
| Schema caching | **NONE in Rust** — Python 60s TTL sufficient | ~~once_cell + DashMap~~ |
| Date validation | **Format-only regex** `^\d{4}-\d{2}-\d{2}$` | ~~Validate actual date validity / leap years~~ |
| Cargo dependencies | **ZERO new** (serde, serde_json, regex, pyo3, thiserror all present) | ~~+once_cell = "1.19"~~ |
| Backend-coder agent | **Eliminated** — QA handles dispatcher + customization.py | ~~BACKEND-CODER agent~~ |
| Test file name | **`test_custom_fields_025.py`** | ~~test_validation_equivalence.py~~ |
| Team composition | **LEAD + RUST-EXPERT + QA + WIKI-EXPERT(ephemeral)** | ~~LEAD + RUST-EXPERT + BACKEND-CODER + QA~~ |
| Error variant mapping | **`PyValueError`** (validation = bad input) | ~~PyRuntimeError~~ |
| Select error format | **Explicit single-quote `format!("'{}'", s)`** | ~~Rust Debug trait `{:?}`~~ |
| Spec path | **`specs/025-rust-custom-field-validator/`** | ~~specs/025-rust-custom-fields/~~ |

---

## Critical Caveats (8 Implementation Guards)

1. **DATE_RE is format-only**: `^\d{4}-\d{2}-\d{2}$` — accepts `2026-02-29` (invalid calendar date). Do NOT add leap year validation — breaks parity with Python.
2. **Select error uses single quotes**: Python `f"Invalid choice. Allowed: {allowed}"` produces `['acero', 'aluminio']`. Rust must use `format!("'{}'", s)` construction, NOT `Debug` trait (`{:?}` produces double quotes).
3. **Bool rejected for integer AND decimal**: In `serde_json`, `Value::Bool` is distinct from `Value::Number`. Rust naturally enforces this — integer checks `n.is_i64()`, decimal checks `value.is_number()`. Both reject `Value::Bool`.
4. **Integer accepted for decimal**: JSON `5` → `Value::Number(i64)` → `as_f64()` returns `Some(5.0)`. Decimal validator checks `value.is_number()` which covers both `i64` and `f64`.
5. **Null values skipped**: The dispatcher filters `None` pre-FFI. Rust should still guard against `Value::Null` defensively.
6. **Undefined keys silently ignored**: Keys in `custom_data` not in `definitions` are NOT errors. Both paths skip them.
7. **`_validate_field_value()` preserved**: The static method stays on the class (FR-013). Only the loop in `validate()` changes.
8. **Threshold is `>5` not `>=5`**: 5 definitions → Python path. 6 definitions → Rust path. Match `len(definitions) > _RUST_FIELD_THRESHOLD`.

---

## Known Gotchas (from SPEC 018–024 Lessons)

| Issue | Cause | Fix |
|-------|-------|-----|
| `NameError: gravitea_rust` after Rust changes | Stale venv wheel | Re-run `maturin develop` into venv-wsl |
| PyO3 0.28 GIL release | `allow_threads()` deprecated | Use `py.detach()` instead (but GIL NOT released for this spec — sub-ms ops) |
| `pub fn` visibility | `#[pymodule_export]` needs pub | Always declare `pub fn` in validation.rs |
| External test runner args | Expects test target, not full command | Pass `tests/rust_integration/test_custom_fields_025.py` not `python -m pytest ...` |
| Agent permission prompts | Interactive prompts block tmux panes | Use `mode: "bypassPermissions"` |
| Docker rebuild | Docker builds fresh wheel | Local changes need `maturin develop` separately |
| Decimal in custom_data | `json.dumps(Decimal("9.99"))` raises TypeError | `_DecimalEncoder` converts to float before FFI |

---

## Agent Instruction Files

| Agent | File |
|-------|------|
| RUST-EXPERT | `Docs/Temp-prompting/025/agent-RUST-EXPERT.md` |
| QA | `Docs/Temp-prompting/025/agent-QA.md` |
| WIKI-EXPERT | `Docs/Temp-prompting/025/agent-WIKI-EXPERT.md` |

---

## Reference Documents

| Document | Purpose | Path |
|----------|---------|------|
| Specify context (solidified) | Validation logic, dispatcher code, caveats | `Docs/Temp-prompting/025/instruction-specify.md` |
| Spec | 15 FRs, 6 SCs, 4 user stories | `specs/025-rust-custom-field-validator/spec.md` |
| Research | 6 resolved decisions (R-001–R-006) | `specs/025-rust-custom-field-validator/research.md` |
| Tasks | Authoritative T001–T020 | `specs/025-rust-custom-field-validator/tasks.md` |
| Python target | `customization.py` validation loop (lines 80-91) | `backend/apps/core/serializers/customization.py` |
| Dispatcher template | `sync_engine.py` / `caea_engine.py` pattern | `backend/apps/sync/sync_engine.py` |
| Error variants | Current `errors.rs` (8 variants) | `rust/gravitea-core/src/errors.rs` |
| Module registry | Current `lib.rs` | `rust/gravitea-core/src/lib.rs` |
| Type stubs | `.pyi` pattern | `backend/gravitea_rust.pyi` |
