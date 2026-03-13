# Speckit Implement Context: Rust Toolchain Bootstrap

> **Phase**: IMPLEMENT (Rust crate, PyO3 module, Docker multi-stage build, tests, type stubs, documentation).
> **Version**: 1.0 (2026-02-25) — Machine-readable orchestration prompt for Rust bootstrap implementation.
> **Feature**: `017-rust-bootstrap`

---

## IMMEDIATE EXECUTION DIRECTIVE

**Upon reading this document, LEAD must act — not plan.**

**Execute this sequence NOW, without pausing for human approval between phases:**

1. **Create the team** (`TeamCreate` with name `017-rust-bootstrap`)
2. **Execute Phase 1 yourself** (T001-T004) — create directory structure, write Cargo.toml, pyproject.toml, test init file
3. **Verify Phase 1 GATE** — directory `rust/gravitea-core/src/` exists, all 3 config files are valid
4. **Spawn RUST-EXPERT** (foreground) — gets ALL Phases 2-5 + 7 (T005-T020, T029-T030) upfront. Starts working immediately.
5. **When RUST-EXPERT completes** → verify Phase 3 checkpoint (extension imports, hello() works, 3+ Rust tests, 2+ Python tests)
6. **Spawn DEVOPS** (foreground) — gets Phase 6 (T021-T028). Starts working immediately.
7. **When DEVOPS completes** → verify Phase 6 checkpoint (Docker build succeeds, import works in container)
8. **Execute Phase 8 yourself** (T031-T040) — documentation verification, full regression, measurements
9. **Report final results** to human → wait for commit approval

**Key principle**: Maximize agent autonomy. Each agent gets its full workload upfront and works through phases sequentially on its own. LEAD monitors and intervenes only on CRITICAL errors.

**No worktree isolation** — all agents share the main filesystem. This works because RUST-EXPERT and DEVOPS write to completely non-overlapping files (Rust source vs Dockerfile).

**Sequential spawning** — DEVOPS depends on RUST-EXPERT's output (compiled Rust code must exist before Docker-izing it). DEVOPS starts ONLY after RUST-EXPERT finishes.

---

## Authoritative Documents

Read these documents for reference (do NOT block execution to study them — execute Phase 1 immediately, spawn agents, read as needed):

| Priority | Document | Path | Purpose |
|----------|----------|------|---------|
| 1 | Tasks (AUTHORITATIVE) | `specs/017-rust-bootstrap/tasks.md` | 40 tasks, 8 phases, execution order — THIS IS THE TASK AUTHORITY |
| 2 | Plan | `specs/017-rust-bootstrap/plan.md` | Architecture, constitution check, phase gates |
| 3 | Spec | `specs/017-rust-bootstrap/spec.md` | 5 user stories, 14 FRs, 10 SCs |
| 4 | Research | `specs/017-rust-bootstrap/research.md` | 11 decisions (R-001 through R-EXTRA) — PyO3 patterns, Docker strategy |
| 5 | Quickstart | `specs/017-rust-bootstrap/quickstart.md` | Developer workflow guide |

**`tasks.md` supersedes `plan.md`** for task IDs, counts, and execution order. When in doubt, follow `tasks.md`.

**Deviation from tasks.md**: `tasks.md` assigns T001-T004 to RUST-EXPERT. This orchestration file reassigns them to LEAD because Phase 1 is trivial file creation (config files with exact contents from spec) — no need to spawn an Opus agent for 4 file writes. RUST-EXPERT starts at T005 with actual Rust code. This deviation is intentional and noted here for traceability.

**No data model or API contracts** — this spec has zero database entities and zero API endpoints.

---

## Agent Team Architecture (2 Agents + LEAD)

### Agent Roster

| Agent | Model | subagent_type | Role Summary |
|-------|-------|---------------|-------------|
| **LEAD** | Opus 4.6 | orchestrator (main) | Shot caller. Executes Phase 1 setup and Phase 8 polish. Manages phase gates. |
| **RUST-EXPERT** | Opus 4.6 | general-purpose | Writes ALL Rust code: lib.rs, errors.rs, Rust tests, maturin build validation, Python integration tests, fallback tests, type stubs. 18 tasks. |
| **DEVOPS** | Sonnet 4.6 | devops-architect | Docker multi-stage build: rust-builder stage, dependency caching, compose update, container validation. 8 tasks. |

### Why This Split

- **RUST-EXPERT gets Opus** because PyO3 API correctness is critical for all 8 subsequent specs — wrong patterns here propagate everywhere
- **DEVOPS gets Sonnet** because Docker work follows well-established patterns (multi-stage build, BuildKit cache mounts) and the research doc provides exact Dockerfile snippets
- **LEAD handles setup and validation** — Phase 1 is trivial file creation from spec, Phase 8 is verification only

### Spawning Schedule

| Phase | Active Agents | Notes |
|-------|---------------|-------|
| 1 (Setup) | LEAD only | Create dirs + config files — trivial |
| 2 (Foundational) | RUST-EXPERT | Core Rust source code — BLOCKS everything |
| 3 (US1 Build & Import) | RUST-EXPERT | First end-to-end toolchain validation |
| 4 (US2 Fallback) | RUST-EXPERT | Python fallback pattern test |
| 5 (US5 Error Mapping) | RUST-EXPERT | Error convention validation |
| 6 (US3 Docker) | DEVOPS | Docker multi-stage build — depends on US1 |
| 7 (US4 Type Stubs) | RUST-EXPERT | IDE autocomplete stub |
| 8 (Polish) | LEAD only | Regression, measurements, doc checks |

**Max concurrent agents**: 2 (LEAD + one spawned agent at a time). Sequential spawning due to hard dependency.

---

## Agent Spawn Prompts (LEAD: copy these EXACTLY)

Each agent has a dedicated instruction file in `Docs/Temp-prompting/017/`. The spawn prompt is a boot loader — the agent's first action reads its instruction file for the complete mission brief.

**CRITICAL**: Do NOT improvise spawn prompts. Do NOT embed long instructions in the prompt. The instruction files are the single source of truth per agent.

#### RUST-EXPERT

```
name: "RUST-EXPERT"
model: "opus"
subagent_type: "general-purpose"
mode: "bypassPermissions"
```

Spawn prompt:

```
You are RUST-EXPERT on team 017-rust-bootstrap.

STEP 1: Read your mission brief at Docs/Temp-prompting/017/agent-RUST-EXPERT.md
STEP 2: Read the tasks at specs/017-rust-bootstrap/tasks.md
STEP 3: Read the research decisions at specs/017-rust-bootstrap/research.md
STEP 4: Execute ALL your assigned tasks: T005-T020 and T029-T030 (Phases 2-5 + 7)

Phase execution order (MUST be sequential between phases):
  Phase 2 (T005-T008): Foundational — lib.rs, errors.rs, Cargo.lock, cargo build --release
  Phase 3 (T009-T016): US1 Build & Import — maturin develop, import verification, Rust tests, Python tests
  Phase 4 (T017-T018): US2 Fallback — test_rust_fallback.py, pytest verification
  Phase 5 (T019-T020): US5 Error Mapping — verify all 3 variants, cargo test error tests
  Phase 7 (T029-T030): US4 Type Stubs — gravitea_rust.pyi, syntax verification

GATE after Phase 2: cargo build --release MUST succeed. If it fails, fix before Phase 3.
GATE after Phase 3: Extension imports, hello() works, 3+ Rust tests pass, 2+ Python tests pass.

When all phases complete, report: tasks completed, test counts (Rust + Python), any issues, any deviations from spec.
```

#### DEVOPS

```
name: "DEVOPS"
model: "sonnet"
subagent_type: "devops-architect"
mode: "bypassPermissions"
```

Spawn prompt:

```
You are DEVOPS on team 017-rust-bootstrap.

STEP 1: Read your mission brief at Docs/Temp-prompting/017/agent-DEVOPS.md
STEP 2: Read the tasks at specs/017-rust-bootstrap/tasks.md (Phase 6 only: T021-T028)
STEP 3: Read the research decisions at specs/017-rust-bootstrap/research.md (R-004, R-005, R-006, R-007, R-008)
STEP 4: Execute ALL tasks T021-T028 (Phase 6)

Build order (sequential within Phase 6):
  T021: Add rust-builder stage to backend/Dockerfile
  T022: Implement dependency caching (dummy lib.rs + BuildKit cache mounts)
  T023: Build real source — maturin build --release --out /wheels
  T024: Copy wheel to Python runtime stage
  T025: Update docker-compose.yml build context
  T026: Verify docker compose build web succeeds
  T027: Verify docker compose up -d — all services healthy
  T028: Verify docker compose exec web python -c "from gravitea_rust import hello; print(hello())"

CRITICAL: Read research.md R-004 through R-008 before writing ANY Dockerfile lines.
The dummy lib.rs MUST be a valid PyO3 module (not empty) — see R-006.

When complete, report: build success/failure, image size delta, any issues.
```

### Spawn Protocol Notes

- **No [READY] handshake** — tasks included in spawn prompt, agents start working immediately
- **Sequential spawning** — DEVOPS starts ONLY after RUST-EXPERT completes (hard dependency)
- **No worktree isolation** — agents share filesystem (non-overlapping writes)
- **bypassPermissions mode** — agents read/write freely without approval prompts
- If an agent acts outside its documented boundaries, send: `"BOUNDARY VIOLATION: Re-read your instruction file — you are not authorized to {action}"`

---

## Communication Protocol

### Message Flow

```
LEAD (human-facing)
    |
    +---> RUST-EXPERT (Phases 2-5, 7: all Rust code + tests)
    |        +- progress / GATE results / blockers ---> LEAD
    |
    +---> DEVOPS (Phase 6: Docker integration)
             +- progress / GATE results / blockers ---> LEAD
```

### Communication Rules

1. **LEAD is the ONLY agent that communicates with the human**
2. **No agent-to-agent direct messaging** — all communication flows through LEAD
3. **RUST-EXPERT and DEVOPS never communicate directly** — they work on separate files in separate phases
4. Agents report phase completion, GATE results, blockers, and issues to LEAD only

---

## File Ownership Rules (STRICT)

| Agent | May Write |
|-------|-----------|
| **LEAD** | Phase 1: `rust/gravitea-core/Cargo.toml`, `rust/gravitea-core/pyproject.toml`, `rust/gravitea-core/src/` (directory only), `backend/tests/rust_integration/__init__.py`. Phase 8: verification commands only — no code writes. |
| **RUST-EXPERT** | `rust/gravitea-core/src/lib.rs`, `rust/gravitea-core/src/errors.rs`, `rust/gravitea-core/Cargo.lock` (generated), `backend/tests/rust_integration/test_rust_import.py`, `backend/tests/rust_integration/test_rust_fallback.py`, `backend/gravitea_rust.pyi`. |
| **DEVOPS** | `backend/Dockerfile` (add rust-builder stage), `docker-compose.yml` (build context change). |

### No Overlap

- **RUST-EXPERT** writes Rust source code and Python test/stub files
- **DEVOPS** writes Docker configuration files only
- **LEAD** writes initial config files (Phase 1) and runs verification commands (Phase 8)
- Zero file overlap between RUST-EXPERT and DEVOPS — they are completely independent
- LEAD's Phase 1 files (Cargo.toml, pyproject.toml) are READ by RUST-EXPERT but never modified by RUST-EXPERT

**Violation of file ownership is a CRITICAL error.** LEAD must enforce this.

---

## Phase Execution Guide

### Phase 1: Setup (Tasks T001-T004) — LEAD

**Purpose**: Create the Rust project skeleton and test directory.

**LEAD actions**:
1. T001: Create directory structure `rust/gravitea-core/src/`
2. T002: Write `rust/gravitea-core/Cargo.toml` with these EXACT contents:
   ```toml
   [package]
   name = "gravitea-core"
   version = "0.1.0"
   edition = "2021"

   [lib]
   name = "gravitea_rust"
   crate-type = ["cdylib", "rlib"]

   [dependencies]
   pyo3 = "0.28"
   thiserror = "2.0"

   [profile.release]
   opt-level = "z"
   lto = true
   codegen-units = 1
   strip = true
   panic = "abort"
   ```
3. T003: Write `rust/gravitea-core/pyproject.toml` with these EXACT contents:
   ```toml
   [build-system]
   requires = ["maturin>=1.12,<2.0"]
   build-backend = "maturin"

   [project]
   name = "gravitea-rust"
   version = "0.1.0"
   description = "Rust acceleration layer for GRAVITEA-ERP"
   requires-python = ">=3.12"

   [tool.maturin]
   strip = true
   ```
4. T004: Create `backend/tests/rust_integration/__init__.py` (empty file)

**GATE**: Directories exist, all files valid. Verify with:
- `ls rust/gravitea-core/src/` (directory exists)
- `ls rust/gravitea-core/Cargo.toml` (file exists)
- `ls rust/gravitea-core/pyproject.toml` (file exists)
- `ls backend/tests/rust_integration/__init__.py` (file exists)

**Then immediately spawn RUST-EXPERT.** Do NOT wait for human approval.

---

### Phases 2-5 + 7: All Rust Work (Tasks T005-T020, T029-T030) — RUST-EXPERT

**LEAD actions**: Spawn RUST-EXPERT with exact prompt above. Wait for completion.

**Phase 2 (T005-T008)**: Foundational Rust Source — **BLOCKING**
- Write lib.rs with `#[pymodule]` and `hello()` function
- Write errors.rs with `GraviteaError` enum + `impl From<GraviteaError> for PyErr`
- Generate Cargo.lock via `cargo generate-lockfile`
- Verify `cargo build --release` succeeds
- GATE: Crate compiles — ALL subsequent work depends on this

**Phase 3 (T009-T016)**: US1 Build & Import
- `maturin develop --release` — wheel installs into venv
- `python -c "from gravitea_rust import hello; print(hello())"` → "Hello from Rust"
- Verify `.pyd`/`.so` in site-packages
- Write Rust-native tests (hello + error display + error from) in `#[cfg(test)]` modules
- Verify `cargo test` passes (3+ tests green)
- Write Python integration tests (import, hello call, consistency)
- Verify pytest passes
- GATE: Extension builds, imports, 3+ Rust tests, 2+ Python tests

**Phase 4 (T017-T018)**: US2 Fallback Pattern
- Write fallback pattern test (monkeypatch ImportError, verify `_USE_RUST` flag toggling)
- Verify pytest passes for fallback tests

**Phase 5 (T019-T020)**: US5 Error Mapping Validation
- Verify errors.rs has all 3 required variants with correct PyErr mappings
- Verify `cargo test` passes error-specific tests

**Phase 7 (T029-T030)**: US4 Type Stubs
- Write `backend/gravitea_rust.pyi` with `def hello() -> str: ...` and `class GraviteaError`
- Verify type stub has valid Python syntax (`ast.parse` + optionally `mypy`)

---

### Phase 6: Docker Multi-Stage Build (Tasks T021-T028) — DEVOPS

**LEAD actions**: Spawn DEVOPS with exact prompt above AFTER RUST-EXPERT completes. Wait for completion.

- Add `rust-builder` stage to `backend/Dockerfile` (FROM `rust:1.85-slim-bookworm`)
- Implement dependency caching (dummy lib.rs + BuildKit cache mounts)
- Build real source with `maturin build --release --out /wheels`
- Copy wheel from rust-builder to Python runtime stage
- Update `docker-compose.yml` build context to include `rust/` directory
- Verify `docker compose build web` succeeds
- Verify `docker compose up -d` — all services healthy
- Verify import works inside container
- GATE: Docker build includes Rust extension, all services healthy

---

### Phase 8: Polish & Final Validation (Tasks T031-T040) — LEAD

**Depends on**: RUST-EXPERT AND DEVOPS both complete.

**LEAD actions**:
1. T031: Verify `specs/017-rust-bootstrap/quickstart.md` covers: prerequisites, build, test, Docker, WSL2, troubleshooting
2. T032: Verify fallback pattern convention documented in quickstart.md
3. T033: Verify error mapping convention documented in research.md (R-010)
4. T034: Run full existing Python test suite — `pytest --tb=short -q --no-header` in `backend/` — 0 new failures
5. T035: Verify `cargo test` in `rust/gravitea-core/` — all 3+ tests green
6. T036: Verify pytest passes for all `backend/tests/rust_integration/` tests
7. T037: Verify Docker build + import — `docker compose build web && docker compose exec web python -c "from gravitea_rust import hello"`
8. T038: Measure runtime Docker image size increase — verify delta ≤ 15 MB
9. T039: Measure build times — first build <60s, incremental <30s
10. T040: Verify `rust/gravitea-core/Cargo.lock` is committed to git

**Human Gate**: Present final validation report to human. Wait for commit approval.

---

## Test Execution Protocol

This feature has THREE types of tests, each with different execution patterns.

### 1. Rust-Native Tests (cargo test)

```bash
# Run from rust/gravitea-core/
cd rust/gravitea-core && cargo test
```

Output is small (~10 lines). Run directly — no external runner needed.

### 2. Python Integration Tests (pytest)

```bash
# Module-scoped (fast, during development)
cd backend && pytest tests/rust_integration/ --tb=short -q --no-header
```

Output is small (~5-10 lines). Run directly.

### 3. Full Regression (pytest — 2,200+ tests)

**Use the external test runner to save tokens:**

```bash
bash scripts/run-tests-external.sh "017-regression" "cd backend && python -m pytest tests/ --tb=short -q --no-header"
```

Then read ONLY the `.summary` file: `Docs/Tests/017-regression.summary`

If failures exist: `Grep "FAIL\|Error" Docs/Tests/017-regression.log`

**NEVER read the full `.log` file** — grep for specific failures only.

### GATE Test Requirements

| Phase | Test Type | Command | Expectation |
|-------|-----------|---------|-------------|
| Phase 2 GATE | Rust compile | `cargo build --release` | Exit code 0 |
| Phase 3 GATE | Rust tests | `cargo test` | 3+ tests green |
| Phase 3 GATE | Python tests | `pytest tests/rust_integration/test_rust_import.py` | 2+ tests green |
| Phase 4 GATE | Python tests | `pytest tests/rust_integration/test_rust_fallback.py` | Tests pass |
| Phase 5 GATE | Rust tests | `cargo test` | Error tests pass |
| Phase 6 GATE | Docker | `docker compose build web` | Exit code 0 |
| Phase 6 GATE | Docker import | `docker compose exec web python -c "from gravitea_rust import hello"` | Output: "Hello from Rust" |
| Phase 7 GATE | Syntax check | `python -c "import ast; ast.parse(open('backend/gravitea_rust.pyi').read())"` | No errors |
| Phase 8 GATE | Full regression | `pytest tests/ --tb=short -q` | 0 new failures |

---

## Error & Blocker Protocol

When ANY agent encounters a problem:

```
1. Agent detects issue (compilation fails, test breaks, Docker error)
        |
        v
2. Agent reports to LEAD with:
   - Problem summary (1-2 sentences)
   - File(s) involved
   - Severity: CRITICAL / HIGH / MEDIUM / LOW
        |
        v
3. LEAD evaluates:
   - CRITICAL: Pause ALL work. Present to human.
   - HIGH: Agent must fix before proceeding to next phase.
   - MEDIUM: Note for Phase 8. Continue current phase.
   - LOW: Note for Phase 8. Continue.
```

### Severity Classification

| Severity | Criteria | Action |
|----------|----------|--------|
| **CRITICAL** | `cargo build` fails due to PyO3 incompatibility, maturin cannot produce wheel | Halt ALL work. Fix immediately. |
| **HIGH** | GATE test fails (cargo test, pytest, Docker build), wrong PyO3 API used | Fix before next phase. |
| **MEDIUM** | Type stub missing a docstring, non-critical test assertion too strict | Note for Phase 8 fix. |
| **LOW** | Build time slightly over target, minor doc wording | Note for Phase 8. |

---

## Human-in-the-Loop Protocol

| Event | LEAD Action | Blocks? |
|-------|------------|---------|
| Phase 1 complete | Print status | **NO** — spawn RUST-EXPERT immediately |
| RUST-EXPERT complete | Print GATE results, test counts | **NO** — spawn DEVOPS immediately |
| DEVOPS complete | Print GATE results, image size | **NO** — start Phase 8 |
| Phase 8 complete | Print final validation report | **YES** — wait for human commit approval |
| CRITICAL error | Print full error context | **YES** — wait for human decision |

---

## Skills to Invoke

Each agent should invoke these skills when working on relevant files:

| Agent | Skills |
|-------|--------|
| LEAD | `gravitea-testing` (Phase 8 regression), `gravitea-docker` (Phase 8 Docker verification) |
| RUST-EXPERT | `gravitea-testing` (Python integration test writing) |
| DEVOPS | `gravitea-docker` (Dockerfile patterns, compose config) |

**No Django skills needed** — this feature creates zero Django models, views, serializers, or migrations.

---

## Existing Pattern References

Agents should study these existing implementations for pattern consistency:

| Pattern | Reference File | Used For |
|---------|---------------|----------|
| Python test structure | `backend/tests/conftest.py` | Test discovery and fixture patterns |
| Existing Dockerfile | `backend/Dockerfile` | Understanding current build stages before modification |
| Docker compose | `docker-compose.yml` | Understanding current service definitions |
| PyO3 module pattern | `specs/017-rust-bootstrap/research.md` R-009 | Declarative `#[pymodule] mod` pattern |
| Error mapping pattern | `specs/017-rust-bootstrap/research.md` R-010 | thiserror + From<GraviteaError> for PyErr |
| Docker caching pattern | `specs/017-rust-bootstrap/research.md` R-006 | Dummy lib.rs + BuildKit cache mounts |
| Fallback convention | `specs/017-rust-bootstrap/quickstart.md` | try/except ImportError pattern |

---

## Execution Sequence for LEAD (DO THIS NOW)

1. **Create team** → `TeamCreate(team_name: "017-rust-bootstrap")`
2. **Create tracking tasks** → One TaskCreate per major phase
3. **Execute Phase 1** (T001-T004) yourself — create dirs, write Cargo.toml + pyproject.toml + test init
4. **Verify Phase 1 GATE** — all files exist
5. **Spawn RUST-EXPERT** (foreground) using exact spawn prompt above. Wait for completion.
6. **Print RUST-EXPERT results** to human (non-blocking)
7. **Spawn DEVOPS** (foreground) using exact spawn prompt above. Wait for completion.
8. **Print DEVOPS results** to human (non-blocking)
9. **Execute Phase 8** (T031-T040) — doc checks, full regression, measurements
10. **Print final validation report** → **WAIT for human approval** before committing

**DO NOT** re-read all authoritative documents before spawning. The agents have their own instruction files. Just execute Phase 1, spawn, and go.

---

## Critical PyO3 Decisions (from research.md — READ BEFORE CODING)

These decisions are NON-NEGOTIABLE. Violating any of them will break the toolchain:

| Decision | Rule | Why |
|----------|------|-----|
| R-001 | `pyo3 = "0.28"` with **NO feature flags** | `extension-module` is DEPRECATED. Maturin handles it via env var. |
| R-002 | `[tool.maturin]` only has `strip = true` | module-name, python-source, features are all auto-detected or deprecated. |
| R-003 | Edition `2021` | Most tested with PyO3 0.28. Edition 2024 deferred. |
| R-009 | Declarative `#[pymodule] mod gravitea_rust` | Preferred in PyO3 0.22+. Uses `#[pymodule_export]` for functions. |
| R-EXTRA | Dual crate-type `["cdylib", "rlib"]` | cdylib for maturin wheel, rlib for `cargo test`. Both required. |

---

## Known Gotchas

| Issue | Cause | Fix |
|-------|-------|-----|
| `cargo test` fails to link | Missing `"rlib"` in crate-type | Ensure `crate-type = ["cdylib", "rlib"]` in Cargo.toml |
| `maturin develop` fails with Python version error | Wrong Python in PATH | Activate the project venv before running maturin |
| `ImportError: dynamic module does not define init function` | Wrong module name in lib.rs | `#[pymodule] mod gravitea_rust` must match `[lib] name` in Cargo.toml |
| Dummy lib.rs fails to compile in Docker | Empty file or missing PyO3 imports | Dummy MUST be valid PyO3 module — see R-006 for exact code |
| `cargo build` fails with `pyo3 not found` | Cargo.lock not generated | Run `cargo generate-lockfile` first (T007) |
| Docker build context missing `rust/` | Compose `context` still points to `./backend` | T025 must change context to `.` (repo root) |
| `.pyd` not found in site-packages | Windows extension file naming | On Windows look for `.pyd`, on Linux look for `.so` |
| Type stub fails mypy | Missing `__all__` or wrong syntax | Use `ast.parse` as primary check (T030), mypy is optional |
| Full regression shows 2,200+ test output | Reading raw output wastes tokens | Use external test runner for full suite, grep failures only |

---

## Summary

| Metric | Value |
|--------|-------|
| Total tasks | 40 |
| LEAD tasks | 14 (Phase 1: T001-T004, Phase 8: T031-T040) |
| RUST-EXPERT tasks | 18 (Phases 2-5 + 7: T005-T020, T029-T030) |
| DEVOPS tasks | 8 (Phase 6: T021-T028) |
| New Rust source files | 2 (lib.rs, errors.rs) |
| New Python test files | 2 (test_rust_import.py, test_rust_fallback.py) |
| New config files | 3 (Cargo.toml, pyproject.toml, Cargo.lock) |
| Modified files | 2 (Dockerfile, docker-compose.yml) |
| Type stub files | 1 (gravitea_rust.pyi) |
| Target: Rust tests | >= 3 |
| Target: Python tests | >= 5 (import + fallback) |
| Target: image size delta | <= 15 MB |
| Target: first build time | < 60s |
| Blocking human gates | 1 (final commit) + CRITICAL errors |
| Django models / migrations | 0 |
| API endpoints | 0 |
| Business logic | 0 |
