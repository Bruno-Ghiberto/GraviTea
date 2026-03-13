# Speckit Implement Context: ARCA CAEA Batch Builder (SPEC-024)

> **Phase**: IMPLEMENT — Execute the plan with agent teams
> **Priority**: MEDIUM | **Wave**: 5
> **Version**: 2.0 (2026-02-28) — Solidified from instruction-plan.md

---

## IMMEDIATE EXECUTION DIRECTIVE

1. Read `specs/024-rust-arca-batch/tasks.md` for authoritative task list (T001–T023)
2. Execute **Phase 1 (Setup)** yourself: T001 (errors.rs) + T002 (lib.rs registration)
3. Spawn **RUST-EXPERT** for Phase 2 (Foundational): T003–T006
4. After RUST-EXPERT delivers, run `maturin develop` to install wheel into venv-wsl
5. Spawn **QA** for Phases 3–6: T007–T017 (all Python integration + parity tests)
6. Execute **Phase 7 (Polish)** yourself: T018–T023 (Docker, regression, quickstart)
7. Spawn **WIKI-EXPERT** on-demand if any agent needs RAG documentation lookup
8. Report final results

---

## Authoritative Documents

| Priority | Document | Path |
|----------|----------|------|
| 1 | **Tasks** (T001–T023) | `specs/024-rust-arca-batch/tasks.md` |
| 2 | **Plan** (phases, architecture) | `specs/024-rust-arca-batch/plan.md` |
| 3 | **Spec** (FRs, SCs, edge cases) | `specs/024-rust-arca-batch/spec.md` |
| 4 | **Research** (6 resolved decisions) | `specs/024-rust-arca-batch/research.md` |
| 5 | **Serde struct designs** | `Docs/Temp-prompting/024/instruction-specify.md` §Serde Struct Design |
| 6 | **Plan context** (dispatcher, caveats) | `Docs/Temp-prompting/024/instruction-plan.md` |

**Note**: Task IDs in `tasks.md` (T001–T023) supersede plan.md IDs (T001–T020) for execution.

---

## Agent Team Architecture

| Agent | Model | subagent_type | mode | Role |
|-------|-------|--------------|------|------|
| **LEAD** (you) | Opus 4.6 | system-architect | — | Orchestration, setup, Docker, regression |
| **RUST-EXPERT** | Opus 4.6 | general-purpose | bypassPermissions | arca.rs implementation + cargo tests |
| **QA** | Sonnet 4.6 | python-expert | bypassPermissions | caea_engine.py, caea.py integration, all pytest |
| **WIKI-EXPERT** | Sonnet 4.6 | general-purpose | bypassPermissions | Ephemeral RAG librarian (on-demand only) |

### Why 3+1 Agents

- **ARCA-EXPERT was eliminated**: The SOAP structure is fully documented in `instruction-specify.md` from source code analysis. No RAG query is needed — the Python source IS the specification.
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
TeamCreate(team_name="arca-024", description="SPEC-024 ARCA CAEA Batch Builder")

# Step 2: Spawn RUST-EXPERT in dedicated pane
Task(
    name="RUST-EXPERT",
    team_name="arca-024",
    subagent_type="general-purpose",
    model="opus",
    mode="bypassPermissions",
    prompt="<contents of agent-RUST-EXPERT.md>"
)

# Step 3: After RUST-EXPERT completes, spawn QA
Task(
    name="QA",
    team_name="arca-024",
    subagent_type="python-expert",
    model="sonnet",
    mode="bypassPermissions",
    prompt="<contents of agent-QA.md>"
)

# Step 4: On-demand WIKI-EXPERT (ephemeral)
Task(
    name="WIKI-EXPERT",
    team_name="arca-024",
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
│ Phase 2: T003-T06 │ Phase 3-6: T07-T17  │
└───────────────────┴─────────────────────┘
```

- WIKI-EXPERT does NOT get a persistent pane — spawned as ephemeral Task when needed
- Each agent runs in its own tmux pane for visibility
- LEAD monitors all panes and coordinates handoffs

---

## File Ownership Rules (STRICT)

| Agent | May Write | May NOT Write |
|-------|-----------|---------------|
| **LEAD** | `errors.rs`, `lib.rs`, Docker validation, `quickstart.md` | `arca.rs`, `caea_engine.py`, test files |
| **RUST-EXPERT** | `arca.rs` (NEW) | `errors.rs`, `lib.rs`, Python files |
| **QA** | `caea_engine.py` (NEW), `caea.py` (MODIFY), `gravitea_rust.pyi` (MODIFY), `test_arca_024.py` (NEW) | Rust files |
| **WIKI-EXPERT** | **No file writes** — returns text to LEAD only | Everything |

---

## Phase Execution Plan

### Phase 1: Setup (LEAD — T001, T002)

**T001**: Add `ARCABuildError(String)` variant to `rust/gravitea-core/src/errors.rs`
- Follow existing pattern (CryptoError, ComputeError, ExportError, SecurityError, SyncError)
- Map to `PyRuntimeError::new_err(msg)`

**T002**: Register module in `rust/gravitea-core/src/lib.rs`
- Add `mod arca;`
- Add `#[pymodule_export] use super::arca::build_caea_batch_request;`

**Gate**: `cargo build` succeeds (arca.rs can be empty placeholder for now)

### Phase 2: Foundational — Rust Core (RUST-EXPERT — T003–T006)

Spawn RUST-EXPERT with `Docs/Temp-prompting/024/agent-RUST-EXPERT.md`.

RUST-EXPERT reads `instruction-specify.md` §Serde Struct Design and implements:
- **T003**: Input serde structs (ComprobanteInput, AlicIvaInput, TributoInput, CbteAsocInput)
- **T004**: Output serde structs (FECAEADetRequest + wrappers) with exact key renames
- **T005**: `build_caea_batch_request` function with all conversion logic
- **T006**: ≥10 cargo tests

**Gate**: `cargo test` passes with ≥10 tests

**LEAD action after gate**: Run `maturin develop` to install wheel:
```bash
VIRTUAL_ENV=$(pwd)/backend/venv-wsl maturin develop \
  --manifest-path rust/gravitea-core/Cargo.toml --release
```

### Phase 3–6: Python Integration + Tests (QA — T007–T017)

Spawn QA with `Docs/Temp-prompting/024/agent-QA.md`.

QA creates the dispatcher, extracts the Python fallback, modifies caea.py, and writes all integration tests:
- **T007** [US1]: Create `caea_engine.py` dispatcher
- **T008** [US1]: Extract Python inner loop into `_build_python()` fallback
- **T009** [US1]: Replace inner loop in `caea.py` with dispatcher call
- **T010** [US1]: Add function stub to `gravitea_rust.pyi`
- **T011** [US1]: Write integration test (50 comprobantes)
- **T012–T015** [US4]: Parity tests (Rust vs Python for all edge cases)
- **T016** [US2]: Threshold guard tests
- **T017** [US3]: Fallback tests

**Gate**: All pytest pass via external runner

### Phase 7: Polish (LEAD — T018–T023)

- **T018**: Benchmark test (50 comprobantes < 5ms)
- **T019**: Docker build: `docker compose build web`
- **T020**: Docker import check
- **T021**: Run SPEC-024 tests in Docker
- **T022**: Full regression suite
- **T023**: Update `quickstart.md`

---

## Test Execution Protocol (MANDATORY — Zero Exceptions)

### Rule: ALL Tests Via External Runner

Every agent MUST use `scripts/run-tests-external.sh` for ALL test execution. No exceptions.

```bash
# Rust tests (cargo)
scripts/run-tests-external.sh -n "cargo-arca-024" \
  "cd rust/gravitea-core && cargo test arca -- --nocapture 2>&1"

# Python integration tests
scripts/run-tests-external.sh -n "arca-024-us1" \
  tests/rust_integration/test_arca_024.py

# Python tests with marker filter
scripts/run-tests-external.sh -n "arca-024-parity" \
  tests/rust_integration/test_arca_024.py -k "parity"

# Full regression
scripts/run-tests-external.sh -n "arca-024-regression" \
  tests/ --no-cov
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
cat Docs/Tests/cargo-arca-024.summary

# If failures, grep the log for specific errors
grep "FAIL\|Error\|panicked" Docs/Tests/cargo-arca-024.log
```

**NEVER run `cargo test`, `pytest`, or `python -m pytest` directly in agent context.**

---

## Key Decisions (Corrected — FINAL)

| Decision | Correct Value | Wrong (from Draft 1.0) |
|----------|---------------|----------------------|
| Date handling | **String passthrough** — no parsing | ~~chrono::NaiveDate~~ |
| Amount conversion | **`str::parse::<f64>()`** | ~~rust_decimal .to_f64()~~ |
| Cargo dependencies | **ZERO new** (serde, serde_json, pyo3, thiserror all present) | ~~+chrono = "0.4"~~ |
| ARCA structure agent | **Eliminated** — structure in instruction-specify.md | ~~ARCA-EXPERT agent~~ |
| Test file name | **`test_arca_024.py`** | ~~test_arca_batch_equivalence.py~~ |
| Team composition | **LEAD + RUST-EXPERT + QA + WIKI-EXPERT(ephemeral)** | ~~LEAD + ARCA-EXPERT + RUST-EXPERT + QA~~ |

---

## Critical Caveats (8 Implementation Guards)

1. **`ImpIVA` not `ImpIva`**: Use `#[serde(rename = "ImpIVA")]` — PascalCase auto-rename produces wrong key
2. **`CAEA` not `Caea`**: Use `#[serde(rename = "CAEA")]` — same issue
3. **Tributos guard is `imp_trib > 0.0`**, not just "tributos present" — both conditions required
4. **Empty `alic_iva: []`** treated as absent — check `!vec.is_empty()` before wrapping
5. **`mon_cotiz` default is `"1"` → f64 `1.0`** — serde `#[serde(default)]` with custom default fn
6. **CbteAsoc CUIT fallback**: When `cuit` is `None`, substitute `default_cuit` — happens during conversion, not serde
7. **Output order**: `Vec` preserves insertion order; struct fields serialize in declaration order. Both deterministic.
8. **`float("0") > 0` is `False` in Python** — Rust must use `imp_trib > 0.0` (not `>= 0.0`) to match

---

## Known Gotchas (from SPEC 018–023 Lessons)

| Issue | Cause | Fix |
|-------|-------|-----|
| `NameError: gravitea_rust` after Rust changes | Stale venv wheel | Re-run `maturin develop` into venv-wsl |
| PyO3 0.28 GIL release | `allow_threads()` deprecated | Use `py.detach()` instead |
| `pub fn` visibility | `#[pymodule_export]` needs pub | Always declare `pub fn` in arca.rs |
| External test runner args | Expects test target, not full command | Pass `tests/rust_integration/test_arca_024.py` not `python -m pytest ...` |
| Agent permission prompts | Interactive prompts block tmux panes | Use `mode: "bypassPermissions"` |
| Docker rebuild | Docker builds fresh wheel | Local changes need `maturin develop` separately |

---

## Agent Instruction Files

| Agent | File |
|-------|------|
| RUST-EXPERT | `Docs/Temp-prompting/024/agent-RUST-EXPERT.md` |
| QA | `Docs/Temp-prompting/024/agent-QA.md` |
| WIKI-EXPERT | `Docs/Temp-prompting/024/agent-WIKI-EXPERT.md` |

---

## Reference Documents

| Document | Purpose | Path |
|----------|---------|------|
| Specify context (solidified) | Serde struct designs, exact Python code, caveats | `Docs/Temp-prompting/024/instruction-specify.md` |
| Plan context (solidified) | Dispatcher code, architecture, research | `Docs/Temp-prompting/024/instruction-plan.md` |
| Spec | 17 FRs, 6 SCs, 4 user stories | `specs/024-rust-arca-batch/spec.md` |
| Research | 6 resolved decisions (R-001–R-006) | `specs/024-rust-arca-batch/research.md` |
| Tasks | Authoritative T001–T023 | `specs/024-rust-arca-batch/tasks.md` |
| Python target | `caea.py` inner loop (lines 232-302) | `backend/apps/facturacion/arca/caea.py` |
| Dispatcher template | `sync_engine.py` pattern | `backend/apps/sync/sync_engine.py` |
| Error variants | Current `errors.rs` (7 variants) | `rust/gravitea-core/src/errors.rs` |
| Module registry | Current `lib.rs` | `rust/gravitea-core/src/lib.rs` |
| Type stubs | `.pyi` pattern | `backend/gravitea_rust.pyi` |
