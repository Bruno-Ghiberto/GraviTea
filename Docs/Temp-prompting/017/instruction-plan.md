# Speckit Context: Rust Toolchain Bootstrap — PLAN Phase (SPEC-017)

> **Phase**: PLAN (implementation design, task breakdown, research decisions, Docker strategy, developer documentation). Uses the specification from `specs/017-rust-bootstrap/spec.md` as input.

## Mission

Design an implementation plan for bootstrapping the Rust/PyO3/Maturin build toolchain into the GRAVITEA-ERP repository. The plan must produce a `plan.md` with phased execution, task assignments, dependencies, validation criteria, and a clear sequential order. This is a FOUNDATION spec — every subsequent Rust acceleration spec (SPEC-018 through SPEC-025) depends on this being correct.

**Key outputs**:
- `plan.md` — phased implementation plan with complexity tracking
- `research.md` — research decisions on PyO3 API patterns, Maturin configuration, Docker optimization, error mapping conventions, WSL2 build strategy
- `quickstart.md` — developer workflow guide (install toolchain, build, test, iterate)

**NOT produced** (no Django models or API endpoints in this spec):
- ~~`data-model.md`~~ — No database entities
- ~~`contracts/`~~ — No REST endpoints

---

## Team Architecture

### Agent Roster

| Agent | Subagent Type | Model | Isolation | Purpose |
|-------|--------------|-------|-----------|---------|
| **ORCHESTRATOR** | system-architect | Opus 4.6 | — | Task management, plan authoring, cross-concern coordination |
| **RUST-EXPERT** | general-purpose | Opus 4.6 | worktree | Rust architecture decisions, PyO3 patterns, error mapping design. **Executes RAG queries** against Qdrant `wikis` collection for authoritative Rust knowledge |
| **DEVOPS** | devops-architect | Sonnet 4.6 | worktree | Docker multi-stage build design, dependency caching strategy, CI pipeline (optional) |

### RUST-EXPERT RAG Integration

The RUST-EXPERT agent has access to the Rust language reference ("The Rust Programming Language" book) indexed in the Qdrant `wikis` collection. When facing challenging Rust architecture or design decisions, the RUST-EXPERT **MUST** query the RAG system:

**Query command** (execute via Bash tool from repo root):
```bash
python scripts/qdrant/qdrant_search.py --collection wikis -q "<your Rust question>" -l 5
```

**When to query RAG**:
- PyO3 `#[pymodule]` and `#[pyfunction]` attribute patterns
- `Bound<>` API patterns (PyO3 0.23+ migration from deprecated GIL-based API)
- Rust error handling patterns (`thiserror`, `From` trait implementations)
- `cdylib` crate type implications and linking behavior
- Module structure and visibility (`pub mod`, re-exports)
- Trait implementations for FFI boundary types
- Ownership and lifetime patterns relevant to PyO3 bindings

**When NOT to query RAG** (use agent knowledge instead):
- Cargo.toml syntax (well-known, stable)
- Basic Rust syntax (functions, structs, enums)
- File system operations (creating directories, writing files)
- Git operations

**RAG result handling**:
- Parse the search results for relevant code examples and explanations
- Cross-reference RAG results with PyO3 official patterns (agent knowledge)
- If RAG returns no relevant results, proceed with agent knowledge and note the gap
- Summarize key RAG findings in `research.md` under the relevant research topic

### Sequential-Thinking MCP

**MANDATORY** for all agents on complex reasoning tasks. Load the `mcp__sequential-thinking__sequentialthinking` tool via ToolSearch before starting work.

**When to use sequential-thinking**:
- RUST-EXPERT: Always for PyO3 architecture decisions, error mapping design, module structure
- DEVOPS: Always for Docker multi-stage optimization, dependency caching strategy
- ORCHESTRATOR: For phase dependency analysis and cross-concern validation

**When NOT to use sequential-thinking**:
- Simple file creation tasks (write Cargo.toml, create directory)
- Mechanical copy/paste patterns from established references
- Task assignment and status tracking

### Execution Model

    SEQUENTIAL — One task at a time

    For each task:
    1. ORCHESTRATOR assigns task with clear scope
    2. RUST-EXPERT or DEVOPS analyzes → designs → documents decision
    3. ORCHESTRATOR reviews output → validates against spec → advances

**No parallel complex tasks.** RUST-EXPERT and DEVOPS work on separate concerns but never on the same phase simultaneously. This prevents conflicting decisions (e.g., RUST-EXPERT designing module structure while DEVOPS designs Docker paths that depend on that structure).

### Phase Dependencies

```
Phase 1: Rust Project Skeleton (Cargo.toml, pyproject.toml, directory structure)
    |
Phase 2: Rust Source Code (lib.rs + errors.rs + Rust-native tests)
    |
Phase 3: Local Build Validation (maturin develop, Python import test)
    |
Phase 4: Python Integration (fallback pattern, pytest, type stub)
    |
Phase 5: Docker Multi-Stage Build (rust-builder stage, dependency caching)
    |
Phase 6: Developer Documentation (quickstart.md, WSL2 guide)
    |
Phase 7: Final Regression + Validation (existing tests, Docker compose)
```

Each phase completes fully (artifacts produced + validated) before the next begins.

---

## Implementation Phases — Detailed Scope

### Phase 1: Rust Project Skeleton

**Assigned to**: RUST-EXPERT
**Risk level**: LOW — file creation only, no existing code modified.

**Tasks**:
1. Create `rust/gravitea-core/` directory structure
2. Write `Cargo.toml` with PyO3 cdylib configuration
3. Write `pyproject.toml` with Maturin build backend
4. Create placeholder `src/lib.rs` (empty `#[pymodule]`)
5. Generate `Cargo.lock` by running `cargo check` (or `cargo generate-lockfile`)
6. Validate: `cargo check` succeeds

**Research topics for this phase**:
- R-001: PyO3 `features = ["extension-module"]` vs `features = ["auto-initialize"]` — when to use each
- R-002: `pyproject.toml` `[tool.maturin]` configuration options — `features`, `python-source`, `module-name`
- R-003: Rust edition choice (2021 vs 2024) — compatibility with PyO3 0.23+

**Architecture decisions (FINAL — from spec)**:
- Package: `gravitea-core` (Cargo), `gravitea_rust` (Python import name)
- Crate type: `cdylib`
- Dependencies: `pyo3 = { version = "0.23", features = ["extension-module"] }`, `thiserror = "2.0"`
- Rust edition: 2021

### Phase 2: Rust Source Code

**Assigned to**: RUST-EXPERT (with RAG queries for PyO3 patterns)
**Risk level**: MEDIUM — PyO3 API correctness is critical for all subsequent specs.

**Tasks**:
1. Write `src/lib.rs` — `#[pymodule]` entry point with `hello()` function
2. Write `src/errors.rs` — `GraviteaError` enum with `From<GraviteaError> for PyErr`
3. Register error module in `lib.rs`
4. Write Rust-native tests (at least 3: hello function, error variant construction, error-to-PyErr conversion)
5. Validate: `cargo test` passes all tests
6. Validate: `cargo build --release` succeeds

**RAG queries expected**:
- `"PyO3 pymodule function registration Bound API"` — for correct `#[pymodule]` syntax with 0.23+ Bound<> API
- `"thiserror derive Error enum implementation"` — for `GraviteaError` pattern
- `"Rust From trait implementation for custom error types"` — for `PyErr` conversion

**Pattern reference — lib.rs structure** (from instruction-specify.md):
```rust
use pyo3::prelude::*;

mod errors;

#[pyfunction]
fn hello() -> String {
    "Hello from Rust".to_string()
}

#[pymodule]
fn gravitea_rust(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(hello, m)?)?;
    Ok(())
}
```

**Pattern reference — errors.rs structure** (from instruction-specify.md):
```rust
use pyo3::exceptions::{PyValueError, PyRuntimeError, PyIOError};
use pyo3::PyErr;
use thiserror::Error;

#[derive(Error, Debug)]
pub enum GraviteaError {
    #[error("Invalid input: {0}")]
    InvalidInput(String),

    #[error("Crypto error: {0}")]
    CryptoError(String),

    #[error("IO error: {0}")]
    IoError(#[from] std::io::Error),
}

impl From<GraviteaError> for PyErr {
    fn from(err: GraviteaError) -> PyErr {
        match err {
            GraviteaError::InvalidInput(msg) => PyValueError::new_err(msg),
            GraviteaError::CryptoError(msg) => PyRuntimeError::new_err(msg),
            GraviteaError::IoError(err) => PyIOError::new_err(err.to_string()),
        }
    }
}
```

### Phase 3: Local Build Validation

**Assigned to**: RUST-EXPERT
**Risk level**: MEDIUM — first real end-to-end validation of the toolchain.

**Tasks**:
1. Run `maturin develop --release` from `rust/gravitea-core/`
2. Validate: wheel installs into active Python venv
3. Run `python -c "import gravitea_rust; print(gravitea_rust.hello())"` — must output "Hello from Rust"
4. Verify the `.so`/`.pyd` file exists in the venv's site-packages

**Environment note**: This phase runs on WSL2 or Docker. If running on Windows native, `maturin develop` produces a `.pyd` file. If on WSL2/Docker, produces a `.so` file. Both are valid but the Docker build only needs `.so`.

### Phase 4: Python Integration

**Assigned to**: RUST-EXPERT
**Risk level**: LOW — no existing code modified, only new files added.

**Tasks**:
1. Create `backend/gravitea_rust.pyi` — type stub with `hello()` signature
2. Create Python integration test file in `backend/tests/` that validates:
   - Import succeeds and `hello()` returns expected string
   - Fallback pattern works when extension is not installed
3. Demonstrate the fallback pattern in a standalone example module
4. Validate: pytest integration tests pass (with extension installed)
5. Validate: pytest integration tests pass (with extension NOT installed — fallback path)

**Fallback pattern** (project convention established here):
```python
try:
    from gravitea_rust import hello as _rust_hello
    _USE_RUST = True
except ImportError:
    _USE_RUST = False

def hello() -> str:
    if _USE_RUST:
        return _rust_hello()
    return "Hello from Python (fallback)"
```

**Type stub** (`gravitea_rust.pyi`):
```python
def hello() -> str:
    """Return a greeting from Rust. Proves the PyO3 pipeline works."""
    ...
```

### Phase 5: Docker Multi-Stage Build

**Assigned to**: DEVOPS (with sequential-thinking for caching strategy)
**Risk level**: HIGHEST — modifying the Docker build pipeline affects all developers.

**Tasks**:
1. Add `rust-builder` stage to the Dockerfile (or `backend/Dockerfile`)
2. Implement dependency caching trick (copy Cargo.toml + Cargo.lock with dummy lib.rs, build deps, then copy real source)
3. Copy compiled wheel from `rust-builder` to Python runtime stage
4. Install wheel in runtime stage
5. Update `docker-compose.yml` if needed
6. Validate: `docker compose build` succeeds
7. Validate: `docker compose up` starts all services (including existing ones)
8. Validate: `docker compose exec backend python -c "import gravitea_rust; print(gravitea_rust.hello())"` works
9. Validate: existing services unaffected (db, redis, backend endpoints)

**Research topics for this phase**:
- R-004: Base image choice — `rust:1.85-slim` vs `rust:1.85-bookworm` vs `rustup` on debian-slim
- R-005: Maturin installation in Docker — `pip install maturin` vs `cargo install maturin` vs `maturin Docker image`
- R-006: Dependency caching strategy — dummy lib.rs trick vs cargo-chef vs sccache
- R-007: Final image size impact — measure the compiled `.so` size, target <15 MB overhead
- R-008: Python version compatibility in Docker — `python:3.14-slim` availability and PyO3 compatibility

**Docker multi-stage pattern** (from instruction-specify.md):
```dockerfile
# Stage 1: Rust builder (NEW — added by this spec)
FROM rust:1.85-slim AS rust-builder
WORKDIR /rust-build
RUN pip install maturin
COPY rust/gravitea-core/Cargo.toml rust/gravitea-core/Cargo.lock ./
# Dependency caching: build deps with dummy lib.rs first
RUN mkdir src && echo "" > src/lib.rs && cargo build --release && rm -rf src
COPY rust/gravitea-core/src ./src
RUN maturin build --release --out /wheels

# Stage 2: Python runtime (EXISTING — modified to install wheel)
FROM python:3.14-slim AS runtime
COPY --from=rust-builder /wheels/*.whl /tmp/wheels/
RUN pip install /tmp/wheels/*.whl && rm -rf /tmp/wheels
# ... rest of existing Python setup
```

### Phase 6: Developer Documentation

**Assigned to**: ORCHESTRATOR (compiling RUST-EXPERT and DEVOPS findings)
**Risk level**: LOW — documentation only.

**Tasks**:
1. Write `quickstart.md` in `specs/017-rust-bootstrap/`:
   - Prerequisites (Rust toolchain, Maturin, Python venv)
   - Step-by-step build workflow (`maturin develop --release`)
   - Testing workflow (`cargo test`, pytest integration tests)
   - Docker workflow (`docker compose build`)
   - WSL2 considerations (filesystem performance, recommended paths)
   - Troubleshooting common issues
2. Document the Python fallback pattern convention
3. Document the error mapping convention (`GraviteaError` → `PyErr`)
4. Include the iterative development cycle: edit `.rs` → `maturin develop` → test

**WSL2 build path guidance** (from instruction-specify.md):
- Rust compilation on `/mnt/c/` (Windows-mounted) is significantly slower due to 9P filesystem bridge
- Option A: Clone/symlink `rust/` to WSL2-native path (e.g., `~/gravitea-rust/`) — faster builds
- Option B: Accept slower builds on `/mnt/c/` — simpler workflow
- Docker builds are unaffected (run inside Linux container)

### Phase 7: Final Regression + Validation

**Assigned to**: ORCHESTRATOR (coordinating)
**Risk level**: LOW — validation only, no new code.

**Tasks**:
1. Run full existing Python test suite — verify 0 regressions
2. Verify `cargo test` passes (at least 3 tests: hello, error variants, error mapping)
3. Verify pytest integration tests pass (import + hello call, fallback pattern)
4. Verify Docker build completes and `gravitea_rust` imports inside container
5. Verify `docker compose up` starts all services normally
6. Verify final runtime image size increase is ≤ 15 MB
7. Measure build times: first build <60s, incremental <30s
8. Verify Cargo.lock is committed to git

---

## Research Topics (for research.md)

| ID | Topic | Decision Needed | Assigned To |
|----|-------|----------------|-------------|
| R-001 | PyO3 `extension-module` feature flag behavior | When `auto-initialize` is needed vs `extension-module` | RUST-EXPERT |
| R-002 | `[tool.maturin]` configuration options | Which options to set for our use case | RUST-EXPERT |
| R-003 | Rust edition 2021 vs 2024 | Compatibility with PyO3 0.23+ and thiserror 2.0 | RUST-EXPERT |
| R-004 | Docker Rust base image selection | `rust:1.85-slim` vs alternatives for minimal image | DEVOPS |
| R-005 | Maturin installation method in Docker | pip vs cargo vs pre-built binary | DEVOPS |
| R-006 | Docker dependency caching strategy | Dummy lib.rs trick vs cargo-chef vs sccache | DEVOPS |
| R-007 | Final image size budget | Measure compiled .so size, verify <15 MB overhead | DEVOPS |
| R-008 | Python 3.14 Docker image availability | `python:3.14-slim` vs building from source | DEVOPS |
| R-009 | PyO3 `Bound<>` API module registration | Correct `#[pymodule]` pattern for 0.23+ | RUST-EXPERT (RAG) |
| R-010 | `thiserror` 2.0 breaking changes | Verify compatibility with PyO3 error conversion | RUST-EXPERT (RAG) |

---

## Existing Codebase Context

### Current Docker Configuration

The root `docker-compose.yml` is the single source of truth for all profiles (default, dev, test, load). The backend has an existing multi-stage Dockerfile at `backend/Dockerfile`. The rust-builder stage must be added BEFORE the Python runtime stage.

**Files to read before modifying Docker**:
- `docker-compose.yml` — root compose file, current service definitions
- `backend/Dockerfile` — current Python build stages
- `backend/gravitea/settings/base.py` — understand Python version and dependency structure

### Current Rust Presence

**None.** Zero Rust code, zero Cargo files, zero Maturin configuration. Reference documents only:
- `Docs/Brainstorming/rust-pyo3-integration-guide.md` — 2253-line implementation guide
- `Docs/Brainstorming/rust-acceleration-opportunities.md` — 521-line opportunity analysis
- `Docs/Brainstorming/rust-pyo3-speckit-roadmap.md` — 656-line 9-spec roadmap

### RAG Collections Available

| Collection | Content | Embedding Model | Dimensions |
|------------|---------|-----------------|------------|
| `wikis` | The Rust Programming Language book, Django docs, JWT docs | nomic-embed-text | 768 |
| `arca_api_specs` | ARCA API specifications | qwen3-embedding:4b | 2560 |
| `arca_dev_guides` | ARCA developer guides | qwen3-embedding:4b | 2560 |
| `arca_setup_certs` | ARCA certificate setup guides | qwen3-embedding:4b | 2560 |

**RUST-EXPERT uses `wikis` collection only** — contains the Rust language reference relevant to ownership, traits, error handling, and module structure decisions.

---

## Testing Standards

- **Rust-native tests**: At least 3 tests via `cargo test` (hello function, error construction, error-to-PyErr mapping)
- **Python integration tests**: At least 2 tests via pytest (successful import+call, graceful fallback)
- **Docker validation**: `docker compose build` succeeds, `gravitea_rust.hello()` works inside container
- **Zero regressions**: All existing Python tests (2,200+) must continue to pass
- **Test execution**: Use `scripts/run-tests-external.sh` for Python test runs (token optimization)
- **Test location**: Python tests go in `backend/tests/` (follow existing organization)

---

## Constraints

1. **Sequential execution**: One phase at a time, fully validated before proceeding
2. **Zero business logic**: Only `hello() -> str` function in Rust. Error mapping is infrastructure, not business logic
3. **Fallback mandatory**: Backend runs identically without the Rust wheel installed
4. **No existing code modified**: This spec adds new files only. The fallback pattern is demonstrated but not wired into any existing module
5. **Reproducible builds**: Cargo.lock committed, Maturin version pinned, Docker stages deterministic
6. **Minimal dependencies**: Only `pyo3` and `thiserror` — no additional crates in this spec
7. **Docker compatibility**: Existing services (db, redis, backend) must start and operate normally
8. **Image size budget**: Runtime image increases by no more than 15 MB from the compiled extension
9. **No frontend changes**: Purely backend infrastructure
10. **CI is optional**: If GitHub Actions is configured, add workflow. Otherwise defer to follow-up
11. **WSL2 for Rust compilation**: Document the path but don't enforce — Docker builds are the primary compilation target

---

## Success Criteria (from spec)

1. `rust/gravitea-core/` directory exists with valid Cargo.toml, Cargo.lock, pyproject.toml
2. `rust/gravitea-core/src/lib.rs` contains `#[pymodule]` entry point with `hello()` function
3. `rust/gravitea-core/src/errors.rs` contains `GraviteaError` enum with `From<GraviteaError> for PyErr`
4. `cargo build --release` succeeds inside `rust/gravitea-core/`
5. `cargo test` passes with at least 3 Rust-native tests
6. `maturin develop --release` installs the wheel into the active Python venv
7. `python -c "import gravitea_rust; print(gravitea_rust.hello())"` outputs "Hello from Rust"
8. `backend/gravitea_rust.pyi` exists with correct type annotations
9. A Python test file validates the import and function call via pytest
10. Docker multi-stage build completes successfully and the wheel is available in the runtime image
11. `docker compose up` still works — existing services unaffected
12. All existing Python tests continue to pass (0 regressions)
13. Python fallback pattern is documented and demonstrated
14. `quickstart.md` covers the complete developer workflow

---

## Reference Documents

| Document | Purpose | Path |
|----------|---------|------|
| Feature spec | Primary input — user stories, FRs, SCs | `specs/017-rust-bootstrap/spec.md` |
| Instruction context | Architecture decisions, system overview | `Docs/Temp-prompting/017/instruction-specify.md` |
| Rust Roadmap | Full 9-spec plan, dependency graph, team agents | `Docs/Brainstorming/rust-pyo3-speckit-roadmap.md` |
| PyO3 Integration Guide | Deep-dive: Cargo.toml, pyproject.toml, Docker, error mapping, type stubs | `Docs/Brainstorming/rust-pyo3-integration-guide.md` |
| Acceleration Opportunities | 9 OPPs with break-even analysis and priority ranking | `Docs/Brainstorming/rust-acceleration-opportunities.md` |
| Constitution | 14 backend principles (Rust layer must not violate any) | `.specify/memory/constitution.md` |
| Docker Compose | Current service configuration (to be updated with rust-builder) | `docker-compose.yml` |
| Backend Dockerfile | Current Python build (to be extended with rust-builder stage) | `backend/Dockerfile` |
| RAG search script | Qdrant search pipeline for RUST-EXPERT RAG queries | `scripts/qdrant/qdrant_search.py` |
| Plan template | Output format reference | `.specify/templates/plan-template.md` |
| 016 plan instruction | Pattern reference for plan phase structure | `Docs/Temp-prompting/016/instruction-plan.md` |
