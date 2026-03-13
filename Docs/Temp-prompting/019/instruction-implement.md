# Speckit Implement Context: Fiscal Compute Engine (SPEC-019)

> **Phase**: IMPLEMENT — Execute the plan with agent teams
> **Feature**: `019-rust-fiscal-compute` | **Version**: 2.0 (2026-02-26)

---

## IMMEDIATE EXECUTION DIRECTIVE

**Upon reading this document, LEAD must act — not plan.**

Execute this sequence NOW, without pausing for human approval between phases:

1. **Execute Phase 1 yourself** (T001–T003): verify SPEC-017+018 foundation, add Cargo.toml deps, scaffold test file
2. **Spawn RUST-EXPERT** with full Rust workload (T004–T035): decimal_utils.rs + compute.rs with 5 functions in TDD order
3. **After RUST-EXPERT signals ALL COMPLETE** (cargo test ≥33) → **spawn ARCA-EXPERT** for T038 review
4. **After ARCA-EXPERT reports APPROVED** → **spawn QA** with full Python workload (T011–T013, T017–T019, T023–T026, T030–T032, T036–T037)
5. **When QA reports ALL COMPLETE** → execute Phase 8 yourself (T039–T045)
6. **Report final results**

**Key principle**: Each agent gets its full workload upfront. LEAD monitors and intervenes only on CRITICAL errors.

**No worktree isolation** — all agents share the main filesystem. File ownership rules prevent conflicts.

---

## Authoritative Documents

| Priority | Document | Path | Purpose |
|----------|----------|------|---------|
| 1 | **tasks.md** | `specs/019-rust-fiscal-compute/tasks.md` | 45 tasks, 8 phases, TDD execution order — AUTHORITATIVE |
| 2 | plan.md | `specs/019-rust-fiscal-compute/plan.md` | Phase structure, constraints, architecture |
| 3 | spec.md | `specs/019-rust-fiscal-compute/spec.md` | 5 user stories, 12 FRs, 8 SCs |
| 4 | research.md | `specs/019-rust-fiscal-compute/research.md` | R-001 (Decimal), R-002 (IVA rates), R-003 (CUIT), R-004 (stock), R-005 (boundary) |
| 5 | quickstart.md | `specs/019-rust-fiscal-compute/quickstart.md` | 8-step build/test guide |

> `tasks.md` supersedes `plan.md` for task IDs, counts, and execution order.

---

## Agent Team Architecture

### Agent Roster

| Agent | Model | subagent_type | Role |
|-------|-------|--------------|------|
| **LEAD** (you) | Opus 4.6 | system-architect | Setup (Phase 1), orchestration, Polish (Phase 8) |
| **RUST-EXPERT** | Opus 4.6 | general-purpose | decimal_utils.rs + compute.rs TDD (Phases 2–7 Rust) |
| **ARCA-EXPERT** | Opus 4.6 | general-purpose | T038 fiscal compliance review — no file writes |
| **QA** | Sonnet 4.6 | quality-engineer | All Python: dispatch, tests, fallback, benchmarks (Phases 3–7 Python) |
| **WIKI-EXPERT** | Sonnet 4.6 | general-purpose | On-demand: RAG queries to Qdrant collections (any phase) |

### Spawning Schedule

| Phase | Active Agents | Tasks | Gate |
|-------|--------------|-------|------|
| 1 (Setup) | LEAD only | T001–T003 | Foundation verified, deps added |
| 2 (Foundational) | RUST-EXPERT | T004–T007 | `cargo check` exits 0 |
| 3 Rust (US1) | RUST-EXPERT | T008–T010 | `cargo test` ≥9 |
| 4 Rust (US2) | RUST-EXPERT | T014–T016 | `cargo test` ≥15 |
| 5 Rust (US3) | RUST-EXPERT | T020–T022 | `cargo test` ≥22 |
| 6 Rust (US4) | RUST-EXPERT | T027–T029 | `cargo test` ≥27 |
| 7 Rust (US5) | RUST-EXPERT | T033–T035 | `cargo test` ≥33 |
| 8a (ARCA Review) | ARCA-EXPERT | T038 | APPROVED report |
| 3–7 Python | QA | T011–T013, T017–T019, T023–T026, T030–T032, T036–T037 | All Python tests pass |
| 8b (Polish) | LEAD | T039–T045 | 0 regressions, Docker builds |
| **On-demand** | **WIKI-EXPERT** | — | Any phase: activated by LEAD when blocked |

### Agent Spawn Instructions

Each agent has a dedicated instruction file. Pass ONLY the instruction file path in the spawn prompt:

**RUST-EXPERT spawn prompt**:
```
name: "RUST-EXPERT"
model: "opus"
subagent_type: "general-purpose"
mode: "bypassPermissions"
```
> Read `Docs/Temp-prompting/019/agent-RUST-EXPERT.md` and execute your mission exactly as described.

**ARCA-EXPERT spawn prompt**:
```
name: "ARCA-EXPERT"
model: "opus"
subagent_type: "general-purpose"
mode: "bypassPermissions"
```
> Read `Docs/Temp-prompting/019/agent-ARCA-EXPERT.md` and execute your review exactly as described.

**QA spawn prompt**:
```
name: "QA"
model: "sonnet"
subagent_type: "quality-engineer"
mode: "bypassPermissions"
```
> Read `Docs/Temp-prompting/019/agent-QA.md` and execute your mission exactly as described.

**WIKI-EXPERT spawn prompt** (on-demand — include the specific question):
```
name: "WIKI-EXPERT"
model: "sonnet"
subagent_type: "general-purpose"
mode: "bypassPermissions"
```
> Read `Docs/Temp-prompting/agents/agent-WIKI-EXPERT.md` and execute your mission exactly as described.
> Your query: [DESCRIBE THE TECHNICAL CHALLENGE HERE]

---

## File Ownership Rules (STRICT)

| Agent | May WRITE |
|-------|-----------|
| **LEAD** | `rust/gravitea-core/Cargo.toml` (T002 deps only), Phase 1 scaffold, Phase 8 docs/Docker |
| **RUST-EXPERT** | `rust/gravitea-core/src/decimal_utils.rs`, `rust/gravitea-core/src/compute.rs`, `rust/gravitea-core/src/lib.rs`, `rust/gravitea-core/src/errors.rs` (add ComputeError only) |
| **ARCA-EXPERT** | No file writes — reports text to LEAD only |
| **QA** | `backend/apps/facturacion/validators.py`, `backend/apps/ventas/validators.py`, `backend/apps/ventas/services/sale_service.py`, `backend/apps/facturacion/serializers.py`, `backend/apps/inventario/services/stock_service.py`, `backend/tests/rust_integration/test_compute_019.py`, `backend/gravitea_rust.pyi` |
| **WIKI-EXPERT** | No file writes — RAG query results returned to LEAD only |

**Violation of file ownership is a CRITICAL error.**

---

## Phase Execution Guide

### Phase 1: Setup (LEAD executes — T001–T003)

**T001**: Verify SPEC-017 + SPEC-018 foundation:
```bash
backend/venv-wsl/bin/python -c "import gravitea_rust; print(gravitea_rust.hello()); gravitea_rust.encrypt_value('test', b'0'*32); print('Foundation OK')"
```
If this fails → stop and fix prerequisites.

**T002**: Add 4 crate dependencies to `[dependencies]` in `rust/gravitea-core/Cargo.toml`:
```toml
rust_decimal = "1.36"
rust_decimal_macros = "1.36"
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
```

**T003**: Create `backend/tests/rust_integration/test_compute_019.py` scaffold — importable with module-level imports (`pytest`, `json`, `decimal.Decimal`), `_USE_RUST` toggle helper, empty `pass` body.

**GATE**: T001 succeeds, T002 deps added, T003 file importable → spawn RUST-EXPERT.

### Phases 2–7 Rust (RUST-EXPERT executes)

See `agent-RUST-EXPERT.md`. Key progression:

```
Phase 2: T004 (decimal_utils.rs) → T005 (compute stubs) → T006 (lib.rs) → T007 (cargo check)
Phase 3: T008 (US1 tests) → T009 (validate_importes) → T010 (cargo test ≥9)
Phase 4: T014 (US2 tests) → T015 (calculate_iva_breakdown) → T016 (cargo test ≥15)
Phase 5: T020 (US3 tests) → T021 (validate_cuit) → T022 (cargo test ≥22)
Phase 6: T027 (US4 tests) → T028 (aggregate_stock_levels) → T029 (cargo test ≥27)
Phase 7: T033 (US5 tests) → T034 (validate_iva_breakdown) → T035 (cargo test ≥33)
```

**IMPORTANT**: RUST-EXPERT must add `ComputeError` variant to `errors.rs` (line ~12):
```rust
#[error("Compute error: {msg}")]
ComputeError { msg: String },
```
And add the `PyRuntimeError` mapping in the `From<GraviteaError> for PyErr` impl (line ~19):
```rust
GraviteaError::ComputeError { msg } => PyRuntimeError::new_err(msg),
```

**GATE**: RUST-EXPERT reports "ALL COMPLETE — cargo test ≥33" → spawn ARCA-EXPERT.

### Phase 8a: ARCA Review (ARCA-EXPERT executes — T038)

See `agent-ARCA-EXPERT.md`. Reviews compute.rs against ARCA specifications.

**GATE**: ARCA-EXPERT report says APPROVED (or LEAD resolves CHANGES_REQUIRED with RUST-EXPERT).

### Phases 3–7 Python (QA executes — after ARCA APPROVED)

See `agent-QA.md`. Key progression:

```
US1: T011 (validators.py dispatch) → T012+T013 (tests, parallel)
US2: T017 (sale_service.py dispatch) → T018+T019 (tests, parallel)
US3: T023+T024 (2 files dispatch) → T025+T026 (tests, parallel)
US4: T030 (stock_service.py dispatch) → T031+T032 (tests, parallel)
US5: T036 (validators.py dispatch, same file as T011) → T037 (tests)
```

**File conflict**: T011 and T036 both modify `facturacion/validators.py`. QA must execute T011 first (create import block), then T036 (add to existing block).

### Phase 8b: Polish (LEAD executes — T039–T045)

After QA reports ALL COMPLETE:

**T039**: Update `backend/gravitea_rust.pyi` with 5 new function stubs.

**T040**: Full `cargo test` from `rust/gravitea-core/` — all crypto + compute tests pass.

**T041**: Docker rebuild:
```bash
docker compose build web
docker compose run --rm web python -c "
import gravitea_rust, json
gravitea_rust.validate_importes('121.00','100.00','21.00','0.00','0.00','0.00')
gravitea_rust.validate_cuit('27000000006')
items = json.dumps([{'price':'100.00','quantity':'1','iva_rate':'21.00'}])
r = gravitea_rust.calculate_iva_breakdown(items)
print(f'Docker compute OK: {r}')
"
```

**T042**: Run compute tests inside Docker container.

**T043**: Full regression via:
```bash
scripts/run-tests-external.sh \
  "backend/venv-wsl/bin/python -m pytest backend/tests/ --tb=short -q --no-header"
```
Read `.summary` only. Target: 0 new failures (SC-007).

**T044**: Run benchmark tests; document speedup ratios in `research.md`.

**T045**: Update `quickstart.md` with actual outputs and figures.

**GATE**: 0 regressions, Docker builds, benchmarks documented.

### On-Demand: WIKI-EXPERT (any phase)

LEAD may spawn WIKI-EXPERT at any point when a technical challenge requires documentation lookup:

| Challenge | Query topic | Collection |
|-----------|-------------|------------|
| ARCA IVA rates / AlicIva structure | `"AlicIva IVA rates IvaId"` | `arca_api_specs` |
| CUIT Modulo-11 specification | `"CUIT validation Modulo 11"` | `arca_api_specs` |
| Comprobante type rules | `"comprobante tipo IVA mandatory"` | `arca_api_specs` |
| rust_decimal precision or API | `"rust_decimal precision Decimal"` | `wikis` |
| PyO3 binding patterns | `"PyO3 allow_threads GIL release"` | `wikis` |

Spawn with the question in the prompt. WIKI-EXPERT returns top results and terminates.

---

## Test Execution Protocol

```bash
# Rust tests (RUST-EXPERT runs this)
cd rust/gravitea-core && cargo test -- --nocapture 2>&1 | tail -40

# Python compute tests only (QA + LEAD)
backend/venv-wsl/bin/python -m pytest \
  backend/tests/rust_integration/test_compute_019.py \
  -p no:django --confcutdir=backend/tests/rust_integration \
  -o "addopts=" --tb=short -q

# Full regression (LEAD Phase 8)
scripts/run-tests-external.sh \
  "backend/venv-wsl/bin/python -m pytest backend/tests/ --tb=short -q --no-header"

# Benchmark tests (slow marker)
backend/venv-wsl/bin/python -m pytest \
  backend/tests/rust_integration/test_compute_019.py \
  -m slow -p no:django --confcutdir=backend/tests/rust_integration \
  -o "addopts=" --tb=short -q
```

Read ONLY `.summary` files from external runner. If failures: `grep "FAIL\|Error" .claude-test-full.log | head -40`.

---

## Error Protocol

| Severity | Criteria | Action |
|----------|----------|--------|
| CRITICAL | IVA rate mapping wrong; CUIT algorithm wrong; Decimal precision loss; data corruption risk | HALT all work, fix immediately, ARCA-EXPERT re-review |
| HIGH | `cargo test` failure; tolerance mismatch; comprobante type rule error; ARCA CHANGES_REQUIRED | Agent fixes before next phase |
| MEDIUM | Benchmark below ≥3× target; Python fallback minor mismatch | Note for polish, continue |
| LOW | Documentation gap; minor style issue | Fix in Phase 8 |

---

## Known Gotchas

| Issue | Cause | Fix |
|-------|-------|-----|
| `ComputeError` doesn't exist | errors.rs only has InvalidInput/CryptoError/IoError | RUST-EXPERT adds variant + mapping in Phase 2 |
| Decimal roundtrip loss | Python `Decimal('10.500')` → str → Rust → str → `Decimal('10.5')` | Use `normalize()` on both sides |
| IVA rate string mismatch | `"21.00" != "21"` as strings | Compare as `Decimal` values, not strings |
| 0% IVA forgotten | AlicIva ID=3 for 0% rate often missed | Explicit match arm with `dec!(0)` required |
| CUIT checksum edge case | Modulo-11 result=10→digit=9, result=11→digit=0 | Match Python logic exactly (both special cases) |
| validators.py shared file | T011 (US1) and T036 (US5) both modify same file | QA executes T011 first, T036 adds to existing block |
| `RuntimeError` vs `ValidationError` | Rust raises RuntimeError, but DRF expects ValidationError | Python wrapper catches RuntimeError → re-raises as ValidationError |
| serde_json parse failure | Wrong JSON format from Python side | Test vectors must match expected struct format exactly |
| GIL release only for aggregate | Other 4 functions are sub-millisecond | Only `aggregate_stock_levels` gets `py: Python<'_>` parameter |
| `cryptography` still needed | WSAA certs use PKCS#7/X.509 | Do NOT remove from requirements.txt |

---

## Final Report Template

When ALL phases complete, report:

```
SPEC-019 IMPLEMENTATION COMPLETE
- T001-T003  (Phase 1 Setup):             [PASS] — Foundation verified, deps added
- T004-T007  (Phase 2 Foundational):      [PASS] — cargo check 0
- T008-T010  (Phase 3 US1 Rust):          [PASS] — cargo test [N]
- T014-T016  (Phase 4 US2 Rust):          [PASS] — cargo test [N]
- T020-T022  (Phase 5 US3 Rust):          [PASS] — cargo test [N]
- T027-T029  (Phase 6 US4 Rust):          [PASS] — cargo test [N]
- T033-T035  (Phase 7 US5 Rust):          [PASS] — cargo test [N] (target ≥33)
- T038        (ARCA review):              [APPROVED]
- T011-T013  (Phase 3 US1 Python):        [PASS]
- T017-T019  (Phase 4 US2 Python):        [PASS]
- T023-T026  (Phase 5 US3 Python):        [PASS]
- T030-T032  (Phase 6 US4 Python):        [PASS]
- T036-T037  (Phase 7 US5 Python):        [PASS]
- T039        (type stubs):               [PASS]
- T040        (full cargo test):           [PASS] — [N] total Rust tests
- T041-T042  (Docker build + tests):      [PASS]
- T043        (full regression):           [PASS] — 0 new failures
- T044        (benchmarks):               [PASS] — validate_importes [X]×, calculate_iva [X]×, aggregate_stock [X]×
- SC-001 (equivalence 100+ vectors):      [PASS/FAIL]
- SC-002 (≥3× validate/calculate):        [PASS/FAIL] — actual: [X]×
- SC-003 (≥3× aggregate, GIL released):   [PASS/FAIL] — actual: [X]×
- SC-004 (CUIT consolidated):             [PASS/FAIL]
- SC-005 (Decimal precision preserved):   [PASS/FAIL]
- SC-006 (fallback all 5 functions):      [PASS/FAIL]
- SC-007 (0 regressions):                 [PASS/FAIL]
- SC-008 (Docker builds):                 [PASS/FAIL]
```
