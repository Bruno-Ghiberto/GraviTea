# Speckit Context: Rust Toolchain Bootstrap (SPEC-017)

> **Phase**: SPECIFY (project structure, build toolchain, Docker integration, fallback pattern, CI pipeline). Implementation planning follows in a separate `speckit.plan` run.

## Mission Statement

Produce a specification for bootstrapping the Rust/PyO3 acceleration layer into the GRAVITEA-ERP backend. This spec covers INFRASTRUCTURE only: setting up the Rust project structure (`rust/gravitea-core/`), configuring the PyO3 + Maturin build toolchain, creating the shared error mapping, establishing the Python fallback pattern, integrating the Rust build into the existing Docker multi-stage pipeline, and validating the entire chain with a hello-world PyO3 function.

This is a FOUNDATION spec — every subsequent Rust acceleration spec (SPEC-018 through SPEC-025) depends on this being complete and correct. The specification must ensure the build toolchain is reproducible across all development environments (WSL2, Docker, CI), the Python fallback pattern is established as a project convention, and the `gravitea_rust` package imports cleanly in the Django backend.

**IMPORTANT — SCOPE**: This spec delivers ZERO business logic. No crypto functions, no fiscal compute, no export pipelines. The only Rust code that ships is a trivial `hello()` function that proves the full pipeline works: Rust source → Maturin build → Python wheel → Django import → function call → response.

## Why This Matters Now

The backend has 6+ complete modules handling real-world workloads (auth, inventory, sales, invoicing, sync, customization) with identified CPU-bound hot paths:

1. **Encryption hot path**: AES-256-GCM encrypt/decrypt runs on every PII field read/write (~15us per operation in Python, ~2us achievable in Rust).
2. **Fiscal compute hot path**: ARCA invoice validation runs 6+ Decimal arithmetic operations per comprobante emission.
3. **Observability hot path**: 19 sequential regex operations execute on every HTTP request for path normalization.
4. **Export pipeline**: 10K-row CSV/Excel generation blocks the Django thread for 4-8 seconds.
5. **SSRF validation**: 5 IP parse attempts + 10 CIDR checks + 9 hostname regexes per outgoing URL.

These hot paths are documented in the Rust acceleration roadmap with measured FFI boundary costs. But none of them can be addressed until the build toolchain exists. SPEC-017 unblocks 8 subsequent specs.

## Architecture Decisions (FINAL — Do Not Re-Debate)

These decisions were made by the project owner and are not negotiable in the spec:

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Rust project location** | `rust/gravitea-core/` (repo root) | Separate from `backend/` to keep Python and Rust toolchains independent. Maturin builds from here, wheel installs into Python venv. |
| **PyO3 binding style** | `Bound<>` API (PyO3 0.23+) | Latest stable API. Deprecated `GIL` pattern removed in 0.22+. |
| **Build backend** | Maturin 1.7+ via `pyproject.toml` | Industry standard for PyO3 projects. `maturin develop` for local dev, `maturin build --release` for Docker/CI. |
| **Crate type** | `cdylib` (shared library) | Required for PyO3 Python extension modules. Produces `.so` (Linux) / `.pyd` (Windows). |
| **Package name** | `gravitea_rust` (Python), `gravitea-core` (Cargo) | Python name follows Django app naming. Cargo name follows Rust conventions (hyphenated). |
| **Fallback pattern** | `try: import gravitea_rust` at module level | Every Rust-accelerated function has a Python fallback. The wheel is optional — Django runs without it, just slower. |
| **Docker strategy** | Multi-stage: `rust-builder` → `runtime` | Rust compiler not in production image. Only the compiled wheel is copied to runtime stage. |
| **Cargo.lock** | Committed to git | Reproducible builds. Rust best practice for binary/library projects. |
| **Feature number** | 017 | Next sequential after 016-backend-modules-solidification. |
| **Spec directory** | `specs/rust-bootstrap/` | Named by feature, not by number. |
| **Implementation methodology** | Sequential, one task at a time | Setup tasks have strict ordering: Cargo.toml before lib.rs, lib.rs before Docker, Docker before CI. |

## System Overview (Actual State — February 2026)

### Current Backend Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Language | Python | 3.14.3 |
| Framework | Django + DRF | 5.2.x |
| Database | PostgreSQL | 18.1 |
| Cache | Redis | 7.x |
| Auth | djangorestframework-simplejwt | Latest |
| Encryption | `cryptography` (AES-256-GCM) | Latest |
| Testing | pytest + pytest-django | Latest |
| Containerization | Docker + Docker Compose | Latest |

### Current Rust Presence

**None.** The project has zero Rust code, zero Cargo files, zero Maturin configuration. The only Rust-related files are brainstorming documents:

- `Docs/Brainstorming/rust-pyo3-integration-guide.md` — 2253-line implementation guide (3 modules)
- `Docs/Brainstorming/rust-acceleration-opportunities.md` — 521-line opportunity analysis (9 OPPs)
- `Docs/Brainstorming/rust-pyo3-speckit-roadmap.md` — 656-line merged roadmap (9 specs)
- `Docs/Userguides/The Rust Programming Language.pdf` — Rust language reference (ingested into Qdrant `wikis` collection)

### Current Docker Configuration

The root `docker-compose.yml` is the single source of truth for all profiles (default, dev, test, load). It already has a multi-stage Dockerfile for the Python backend at `backend/Dockerfile`. The Rust builder stage needs to be added BEFORE the Python runtime stage.

### Development Environment

- **OS**: Windows 11 Pro (WSL2 available for Rust compilation)
- **Shell**: Git Bash (primary), PowerShell (secondary)
- **Python**: 3.14.3 (both Windows-native and WSL2)
- **Docker**: Docker Desktop with WSL2 backend
- **Ollama**: Local LLM for Qdrant RAG embeddings (qwen3-embedding:4b, nomic-embed-text)

### Key Constraint: WSL2 Build Path

Rust compilation on `/mnt/c/` (Windows-mounted paths in WSL2) is significantly slower than native Linux paths due to the 9P filesystem bridge. The spec must document the recommended approach:
- Clone/symlink the `rust/` directory to a WSL2-native path (e.g., `~/gravitea-rust/`) for compilation
- OR accept the slower build times on `/mnt/c/` for simplicity
- Docker builds are unaffected (they run inside the Linux container)

---

## Target Architecture

### Directory Structure

```
GRAVITEA-ERP/
|-- rust/
|   +-- gravitea-core/
|       |-- Cargo.toml            # Workspace with PyO3 cdylib target
|       |-- Cargo.lock            # Committed for reproducible builds
|       |-- pyproject.toml        # Maturin build configuration
|       +-- src/
|           |-- lib.rs            # PyO3 module entry point (#[pymodule])
|           +-- errors.rs         # GraviteaError → PyErr mapping
|-- backend/
|   |-- gravitea_rust.pyi         # Python type stub for IDE autocomplete
|   +-- ... (existing Python code)
|-- docker-compose.yml            # Updated with rust-builder stage reference
|-- Dockerfile                    # OR backend/Dockerfile — updated with rust-builder stage
```

### Cargo.toml Structure

```toml
[package]
name = "gravitea-core"
version = "0.1.0"
edition = "2021"

[lib]
name = "gravitea_rust"
crate-type = ["cdylib"]       # Required for PyO3

[dependencies]
pyo3 = { version = "0.23", features = ["extension-module"] }
thiserror = "2.0"              # For structured error types
```

Future specs will add their crates here (`aes-gcm`, `rust_decimal`, `serde_json`, `regex`, `csv`, `rust_xlsxwriter`, etc.).

### pyproject.toml Structure

```toml
[build-system]
requires = ["maturin>=1.7,<2.0"]
build-backend = "maturin"

[project]
name = "gravitea-rust"
requires-python = ">=3.12"

[tool.maturin]
features = ["pyo3/extension-module"]
```

### Python Fallback Pattern (Project Convention)

Every Django module that uses Rust acceleration must follow this pattern:

```python
# backend/apps/core/encryption/utils.py (future example)
try:
    from gravitea_rust import encrypt_field as _rust_encrypt
    from gravitea_rust import decrypt_field as _rust_decrypt
    _USE_RUST = True
except ImportError:
    _USE_RUST = False

def encrypt_field(plaintext: str, key: bytes) -> str:
    if _USE_RUST:
        return _rust_encrypt(plaintext, key)
    # Python fallback (existing implementation)
    ...
```

This pattern is established in SPEC-017 with the hello-world function and becomes the template for all subsequent specs.

### Docker Multi-Stage Build

```dockerfile
# Stage 1: Rust builder (NEW — added by this spec)
FROM rust:1.85-slim AS rust-builder
WORKDIR /rust-build
RUN pip install maturin  # Or use maturin Docker image
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

The dependency caching trick (copy Cargo.toml first, build deps with dummy lib.rs, then copy real source) turns 3-5 minute full builds into 15-35 second incremental builds when only Rust source changes.

### Error Mapping (errors.rs)

A shared `GraviteaError` enum that maps Rust errors to Python exceptions:

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

Future specs extend this enum with domain-specific variants (e.g., `FiscalError`, `ExportError`).

### Type Stub (gravitea_rust.pyi)

```python
def hello() -> str:
    """Return a greeting from Rust. Proves the PyO3 pipeline works."""
    ...

# Future specs will add function signatures here:
# def encrypt_field(plaintext: str, key: bytes) -> str: ...
# def validate_importes(...) -> bool: ...
```

---

## Implementation Methodology

The user explicitly requires a systematic approach:

    For each task in the spec:
    1. ANALYZE: Read the relevant context (Cargo docs, PyO3 docs, existing Dockerfile)
    2. CODE: Write or modify files (Cargo.toml, lib.rs, Dockerfile, etc.)
    3. TEST: Write tests for the new code (cargo test, pytest import test)
    4. EXECUTE: Run the test suite
    5. VERIFY: Confirm tests pass
    6. NEXT: Move to the next task only after verification

**Sequential ordering is critical.** Tasks must execute in dependency order:
1. Cargo.toml + pyproject.toml (project skeleton)
2. src/lib.rs + src/errors.rs (code)
3. Local build with `maturin develop` (validation)
4. Python import test (integration)
5. gravitea_rust.pyi (type stub)
6. Docker multi-stage build (containerization)
7. CI pipeline (optional, if GitHub Actions is configured)

**Testing standards**:
- `cargo test` passes with at least one Rust-native test
- `pytest` import test: `import gravitea_rust; assert gravitea_rust.hello() == "Hello from Rust"`
- Docker build produces a working image where `python -c "import gravitea_rust"` succeeds
- Existing Python test suite continues to pass (0 regressions)
- Use `scripts/run-tests-external.sh` for Python test execution (token optimization)

---

## Constraints and Boundaries

### What This Spec Covers

- Creating `rust/gravitea-core/` directory with Cargo.toml, Cargo.lock, pyproject.toml
- Creating `src/lib.rs` with PyO3 module entry point and `hello()` function
- Creating `src/errors.rs` with shared `GraviteaError` → `PyErr` mapping
- Creating `gravitea_rust.pyi` type stub in `backend/`
- Establishing the Python fallback pattern (`try: import gravitea_rust`) as project convention
- Updating Docker configuration with rust-builder multi-stage step
- Validating the full pipeline: Rust source → Maturin build → wheel → Python import → function call
- Documenting the developer workflow (`maturin develop`, WSL2 considerations)
- Optional: `.github/workflows/rust-build.yml` for CI wheel caching

### What This Spec Does NOT Cover

- **Any business logic in Rust** — no crypto, no fiscal compute, no export, no observability (those are SPEC-018 through SPEC-025)
- **Modifying any existing Python code** — the fallback pattern is demonstrated but not wired into any existing module
- **Frontend changes** — purely backend infrastructure
- **Performance benchmarks** — no benchmark framework yet (SPEC-018 introduces `criterion` for Rust, `pytest-benchmark` for Python)
- **Multi-platform wheel distribution** — Docker always produces Linux wheels. Windows-native .pyd is post-MVP
- **Free-threaded Python (3.14t)** — targeting standard CPython 3.14.3, not the free-threaded build
- **Cargo workspace with multiple crates** — single crate for now. Future specs may split into `gravitea-crypto`, `gravitea-compute`, etc. if the single crate grows too large
- **Blueprint document updates** — separate follow-up
- **Constitution amendments** — the Rust layer doesn't change any backend principles; it accelerates existing behavior

### Key Principles

1. **Zero business logic**: The only Rust function in this spec is `hello() -> str`. Everything else is toolchain and build infrastructure.
2. **Fallback mandatory**: The Python backend must work identically without the Rust wheel installed. `gravitea_rust` is an optional accelerator, never a hard dependency.
3. **Reproducible builds**: Cargo.lock committed, Maturin version pinned, Docker stages deterministic.
4. **Minimal dependencies**: Only `pyo3` and `thiserror` in this spec. Future specs add crates incrementally.
5. **Existing tests unaffected**: Adding the Rust toolchain must not break any existing Python test or Docker build.
6. **Developer ergonomics**: `maturin develop --release` is the single command to rebuild Rust and install into venv.

---

## Success Criteria

1. `rust/gravitea-core/` directory exists with valid Cargo.toml, Cargo.lock, pyproject.toml
2. `rust/gravitea-core/src/lib.rs` contains a `#[pymodule]` entry point with `hello()` function
3. `rust/gravitea-core/src/errors.rs` contains `GraviteaError` enum with `From<GraviteaError> for PyErr`
4. `cargo build --release` succeeds inside `rust/gravitea-core/`
5. `cargo test` passes with at least one Rust-native test
6. `maturin develop --release` installs the wheel into the active Python venv
7. `python -c "import gravitea_rust; print(gravitea_rust.hello())"` outputs "Hello from Rust"
8. `backend/gravitea_rust.pyi` exists with correct type annotations
9. A Python test file validates the import and function call via pytest
10. Docker multi-stage build completes successfully and the wheel is available in the runtime image
11. `docker compose up` still works — existing services unaffected
12. All existing Python tests continue to pass (0 regressions)
13. Python fallback pattern is documented and demonstrated (import succeeds with wheel, graceful degradation without it)

---

## Reference Documents

| Document | Purpose | Path |
|----------|---------|------|
| CLAUDE.md | Project overview, skill registry | `CLAUDE.md` |
| Rust Roadmap | Full 9-spec acceleration plan with FFI costs, team agents, dependency graph | `Docs/Brainstorming/rust-pyo3-speckit-roadmap.md` |
| PyO3 Integration Guide | Deep-dive implementation guide (Cargo.toml, pyproject.toml, Docker, error mapping, type stubs) | `Docs/Brainstorming/rust-pyo3-integration-guide.md` |
| Acceleration Opportunities | 9 OPPs with break-even analysis and priority ranking | `Docs/Brainstorming/rust-acceleration-opportunities.md` |
| Speckit Constitution | 14 backend principles (Rust layer must not violate any) | `.specify/memory/constitution.md` |
| Docker Compose | Current service configuration (to be updated with rust-builder) | `docker-compose.yml` |
| Backend Dockerfile | Current Python build (to be extended with rust-builder stage) | `backend/Dockerfile` |
| 016 Spec | Most recent speckit spec (pattern reference for structure) | `specs/016-backend-modules-solidification/spec.md` |

---

## Phase Boundary

This specification covers **WHAT** infrastructure to build, **WHY** it's the foundation for all Rust acceleration, and **WHAT** the acceptance criteria are. It does NOT cover:

- HOW to organize the implementation work (that's `speckit.plan`)
- WHICH tasks to create and in what order (that's `speckit.tasks`)
- WHO executes each task (that's `speckit.implement`)
- WHAT business logic goes into the Rust crate (that's SPEC-018 through SPEC-025)

The specify agent should use this context to produce a rigorous spec.md with testable user stories, detailed functional requirements, and measurable success criteria — all focused on the Rust toolchain bootstrap infrastructure.
