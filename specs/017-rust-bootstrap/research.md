# Research: Rust Toolchain Bootstrap (SPEC-017)

**Date**: 2026-02-25
**Sources**: PyO3 documentation, Maturin documentation, Rust reference (Qdrant RAG), Docker Hub, integration guide

---

## R-001: PyO3 `extension-module` Feature Flag — DEPRECATED

**Decision**: Do NOT use `features = ["extension-module"]`. Use `pyo3 = "0.28"` with no feature flags.

**Rationale**: The `extension-module` feature has been **deprecated** in PyO3. The [PyO3 building and distribution guide](https://pyo3.rs/v0.28.0/building-and-distribution.html) states that the replacement mechanism is the `PYO3_BUILD_EXTENSION_MODULE` environment variable, which Maturin >= 1.9.4 sets **automatically** during wheel builds. This means:
- During `maturin build` / `maturin develop`: the env var is set, libpython linking is disabled (correct for `.so`/`.pyd`).
- During `cargo test`: the env var is NOT set, libpython is linked, and tests work without workarounds.

The `auto-initialize` feature is for **embedding** Python inside a Rust binary (the reverse of our use case) — not needed.

**Corrected Cargo.toml dependency**:
```toml
[dependencies]
pyo3 = "0.28"    # No feature flags; maturin handles extension-module automatically
```

**Alternatives Considered**:
- `features = ["extension-module"]`: REJECTED — deprecated; breaks `cargo test`; maturin handles it automatically.
- `auto-initialize`: REJECTED — for embedding Python in Rust, not our use case.
- `abi3-py312`: DEFERRED — stable ABI wheels are a later optimization; not needed for bootstrap.

---

## R-002: `[tool.maturin]` Configuration Options

**Decision**: Minimal configuration — only `strip = true`:
```toml
[tool.maturin]
strip = true
```

**Rationale**: Maturin infers most settings from `Cargo.toml`. The `module-name` defaults to the `[lib] name` in Cargo.toml (`gravitea_rust`). Maturin auto-detects that this is a pure Rust project (no `python-source` directory). `bindings = "pyo3"` is auto-detected from dependencies. The `features = ["pyo3/extension-module"]` line is **removed** because the feature is deprecated (see R-001).

**Important corrections from the existing integration guide**:
- `features = ["pyo3/extension-module"]`: REMOVED — references deprecated PyO3 feature.
- `python-source = false`: REMOVED — this option expects a string path (e.g. `"python"`), not a boolean. When omitted, Maturin auto-detects pure Rust.
- `module-name = "gravitea_rust"`: REMOVED — redundant; already set via `[lib] name` in Cargo.toml.

**Corrected pyproject.toml**:
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

**Alternatives Considered**:
- `module-name = "gravitea_rust"`: Redundant — already set via `[lib] name` in Cargo.toml.
- `python-source = "python"`: For mixed Python+Rust packages. Not applicable — our Python code lives in `backend/`, not alongside Rust.
- `compatibility = "linux"`: For platform-specific wheel naming. Not needed — Maturin auto-detects platform.

---

## R-003: Rust Edition 2021 vs 2024

**Decision**: Use edition `2021`

**Rationale**: Edition 2021 is the most widely supported and tested with PyO3 0.23+. Edition 2024 was stabilized in Rust 1.85 (released February 2025) but PyO3 0.23 was developed against 2021. While edition 2024 should work (editions are backward compatible), using 2021 avoids any edge cases with new syntax rules. We can upgrade in a future spec after confirming full ecosystem support.

**Alternatives Considered**:
- Edition 2024: Newer syntax features (e.g., `gen` keyword, `unsafe_op_in_unsafe_fn` lint default). Benefits are marginal for our small codebase. Risk of undiscovered PyO3 incompatibilities outweighs benefits.

---

## R-004: Docker Rust Base Image Selection

**Decision**: Use `rust:1.85-slim-bookworm` with Python 3 installed via apt

**Rationale**: The `rust:1.85-slim-bookworm` image is based on Debian Bookworm slim, which provides `apt` for installing `python3-dev` (needed by Maturin for the build). The slim variant is ~300 MB smaller than the full image. Bookworm is the current Debian stable release, matching our Python runtime base (`python:3.14-slim-bookworm`).

**Critical requirement**: Maturin needs Python headers in the builder stage to compile PyO3 bindings. The `python3-dev` package provides these.

**Alternatives Considered**:
- `rust:1.85-slim` (Debian Bookworm default): Same as our choice — Debian Bookworm is the current default for Rust official images.
- `rust:1.85-bookworm` (full): Includes unnecessary tools (gcc, make are already in the Rust image). +300 MB for no benefit.
- `rust:1.85-alpine`: Smaller but uses musl libc which can cause PyO3 compatibility issues. The Python runtime uses glibc — mixing libc implementations is risky.
- Custom `debian:bookworm-slim` + `rustup`: More control but more Dockerfile lines. The official Rust image already handles this optimally.

**Python in builder stage**: The builder needs `python3-dev` installed via:
```dockerfile
RUN apt-get update && apt-get install -y python3-dev python3-pip && rm -rf /var/lib/apt/lists/*
```
Note: The Python version in the builder (Debian's Python 3.11) doesn't need to match the runtime (3.14). Maturin uses the builder's Python only for build tooling, not for the target wheel's Python version. We specify `--interpreter python3.14` or let Maturin auto-detect from `pyproject.toml requires-python`.

**Update**: For Python 3.14 wheel compatibility, Maturin must know the target Python version. Two approaches:
1. Install Python 3.14 in the builder stage from source or deadsnakes PPA
2. Use `maturin build --release` which reads `requires-python` from pyproject.toml

The safest approach for our case: use the `rust:1.85-slim-bookworm` base, install `python3-dev` for build headers, and use `maturin build --release`. The resulting wheel will be tagged for the target Python version.

---

## R-005: Maturin Installation Method in Docker

**Decision**: `pip install maturin==1.12.4` (pre-compiled wheel from PyPI)

**Rationale**: Installing Maturin via pip is the fastest method (~5 seconds) — pre-built manylinux x86_64 wheels (10.3 MB) are available on PyPI. `cargo install maturin` compiles from source, adding 3-5 minutes to the Docker build. Maturin 1.12.4 (released 2026-02-21, latest) supports Python 3.14 and PyO3 0.28.x. Pin to exact version for reproducible builds.

**Alternatives Considered**:
- `cargo install maturin`: Compiles from source (~3-5 min, ~200 MB intermediate artifacts). Wasteful when pre-built binaries exist.
- `cargo binstall maturin`: Pre-built Rust binary (~10s). Requires installing `cargo-binstall` first, and falls back to compilation if no binary exists for the target architecture.
- Download pre-built binary from GitHub releases: Requires curl + chmod. URL includes architecture and version, making it harder to update than a pip pin.
- `ghcr.io/pyo3/maturin` Docker image: Based on manylinux2014 (CentOS 7) for PyPI wheel compatibility. We build for a known runtime, so manylinux compliance is unnecessary overhead.

---

## R-006: Docker Dependency Caching Strategy

**Decision**: Dummy `lib.rs` trick combined with BuildKit cache mounts (`--mount=type=cache`)

**Rationale**: The combination of Docker layer caching (dummy lib.rs) and BuildKit cache mounts provides the best incremental build experience. Layer caching skips the dependency build entirely when `Cargo.toml`/`Cargo.lock` haven't changed (0s). Cache mounts keep the `target/` directory warm even when layers are invalidated, so cargo performs true incremental builds (10-20s for source-only changes).

```dockerfile
# Cache dependencies (only rebuilds when Cargo.toml/Cargo.lock change)
COPY Cargo.toml Cargo.lock ./
RUN mkdir src && echo "use pyo3::prelude::*; #[pymodule] fn gravitea_rust(_m: &Bound<'_, PyModule>) -> PyResult<()> { Ok(()) }" > src/lib.rs
RUN --mount=type=cache,target=/usr/local/cargo/registry,sharing=locked \
    --mount=type=cache,target=/build/target,sharing=locked \
    cargo build --release --lib 2>/dev/null || true

# Build actual source (fast — deps already compiled via cache mount)
RUN rm -rf src
COPY src ./src
RUN --mount=type=cache,target=/usr/local/cargo/registry,sharing=locked \
    --mount=type=cache,target=/build/target,sharing=locked \
    maturin build --release --out /wheels
```

Note: The dummy `lib.rs` must be a valid PyO3 module (not just empty) because PyO3's proc macros generate code that references pyo3 types. An empty file would fail `cargo build`. When using cache mounts, the compiled binary ends up inside the mount — you must copy the output out (maturin's `--out` flag handles this).

**Alternatives Considered**:
- `cargo-chef`: Dedicated tool for Docker layer caching. Requires two extra stages (planner + cook). Overkill for a single crate with 2 dependencies. Better suited for large workspaces. Deferred — revisit if we add more crates.
- `sccache`: Shared compilation cache. Provides fastest builds (7-15s) but requires S3/Redis backend for CI. Adds operational complexity. Deferred — revisit when build times exceed 60s.
- Dummy lib.rs alone (without cache mounts): Works, but without cache mounts, a source change invalidates the second layer and cargo recompiles from a cold target directory. Cache mounts keep it warm.
- BuildKit cache mounts alone (without dummy lib.rs): Every build runs `cargo build`, even if nothing changed. The dummy lib.rs trick adds Docker layer caching on top — fully cached layers are skipped entirely (0s).

---

## R-007: Final Image Size Budget

**Decision**: Target <5 MB for the compiled .so, well within the 15 MB budget.

**Rationale**: A PyO3 cdylib with only pyo3 and thiserror dependencies compiles to approximately 200KB-4MB depending on optimization level. PyO3 itself is the largest contributor. The thiserror crate is zero-cost at runtime (proc macro only).

**Release profile optimizations** (in `Cargo.toml`):
```toml
[profile.release]
opt-level = "z"       # Optimize for size
lto = true            # Link-Time Optimization — eliminates dead code across crates
codegen-units = 1     # Single codegen unit — enables maximum LTO
strip = true          # Strip debug symbols and symbol tables
panic = "abort"       # No unwinding tables (saves ~10-20 KB)
```

**Size budget breakdown**:
| Component | Estimated Size (stripped, LTO) |
|-----------|-------------------------------|
| PyO3 FFI glue (module init, type conversions) | ~200-500 KB |
| thiserror (compile-time only) | ~0 KB |
| Application code (hello + errors) | ~0.01 MB |
| **Total .so (SPEC-017 — hello + errors only)** | **~200 KB - 1 MB** |
| **Total .so (future — with crypto + compute)** | **~2-4 MB** |
| Python wheel metadata | ~0.01 MB |

Well within the 15 MB spec requirement. Even without size optimizations (`opt-level = 3`, no LTO), a PyO3 cdylib with our dependencies would be 8-12 MB.

**Note**: LTO adds 30-60s to build time but reduces binary size by 20-40%. Worth it for the shipping artifact. If `opt-level = "z"` causes measurable performance regression in crypto-heavy code (future specs), switch to `opt-level = 3` and accept the larger binary.

---

## R-008: Python 3.14 Docker Image Availability

**Decision**: Use `python:3.14.3-slim` (or `python:3.14-slim`) — already used by existing Dockerfile.

**Rationale**: The existing `backend/Dockerfile` already uses `python:3.14.3-slim` as its base image. Python 3.14 official Docker images are available on Docker Hub. PyO3 0.23+ supports Python 3.14 (standard CPython build, not free-threaded).

**Key observation**: The existing Dockerfile already uses `python:3.14.3-slim as builder` and `python:3.14.3-slim` as runtime. No change needed for Python version compatibility.

**Free-threaded Python (3.14t)**: Explicitly out of scope. We target standard CPython 3.14.3. PyO3's `extension-module` feature is designed for standard CPython with the GIL.

---

## R-009: PyO3 `Bound<>` API Module Registration

**Decision**: Use the **declarative `#[pymodule] mod`** pattern (preferred in PyO3 0.22+/0.28), with `Bound<>` API.

**Rationale**: PyO3 0.28 supports two module registration patterns. The declarative `mod` pattern is preferred for readability; the imperative `fn` pattern is still supported for `#[pymodule_init]` customization. The old GIL-based `&PyModule` pattern was removed in PyO3 0.24.

**Preferred pattern (declarative, PyO3 0.22+/0.28)**:
```rust
use pyo3::prelude::*;

#[pyfunction]
fn hello() -> String {
    "Hello from Rust".to_string()
}

#[pymodule]
mod gravitea_rust {
    use super::*;

    #[pymodule_export]
    use super::hello;
}
```

**Alternative pattern (imperative, still valid)**:
```rust
use pyo3::prelude::*;

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

**Deprecated pattern (removed in PyO3 0.24)** — DO NOT USE:
```rust
// REMOVED in PyO3 0.24 — compilation error
#[pymodule]
fn gravitea_rust(_py: Python<'_>, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(hello, m)?)?;
    Ok(())
}
```

**Key differences**:
- Declarative `mod` pattern: functions are exported via `#[pymodule_export] use super::func;`
- Imperative `fn` pattern: functions registered via `m.add_function(wrap_pyfunction!(func, m)?)?;`
- Both use `Bound<>` API (not the removed `&PyModule` GIL ref)
- `#[pymodule_init]` available in declarative pattern for custom init logic

---

## R-010: `thiserror` 2.0 Breaking Changes

**Decision**: Use `thiserror = "2.0"` — compatible with our use case.

**Rationale**: thiserror 2.0 (released late 2024) removed the `thiserror-impl` dependency in favor of inline proc macros and updated to syn 2.0. The `#[derive(Error)]` and `#[error()]` attributes work identically for our use case. The `#[from]` attribute for automatic conversion still works.

**Breaking changes in thiserror 2.0**:
1. Minimum Rust version bumped to 1.61 (we use 2021 edition, Rust 1.85 — no issue)
2. `#[source]` attribute behavior slightly changed for manual `source()` implementations (not applicable — we use `#[from]`)
3. Removed `thiserror-impl` as a separate crate (transparent to users)

**Our pattern is fully compatible**:
```rust
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
```

The `impl From<GraviteaError> for PyErr` is a manual implementation that doesn't depend on thiserror internals — it only uses the `GraviteaError` enum variants.

---

## R-EXTRA: PyO3 Testing Patterns

**Decision**: Use dual crate-type `["cdylib", "rlib"]` with `#[cfg(test)]` modules for pure Rust tests; separate pytest files for Python integration.

**Rationale**: The `cdylib` crate type alone does not produce an `rlib` that `cargo test` can link against. Adding `"rlib"` alongside `"cdylib"` fixes this:
```toml
[lib]
name = "gravitea_rust"
crate-type = ["cdylib", "rlib"]  # cdylib for maturin, rlib for cargo test
```

Since we no longer use the deprecated `extension-module` feature (R-001), libpython is linked by default during `cargo test`, and tests work without workarounds. The underlying Rust logic can be extracted into non-PyO3 functions and tested directly.

**Pattern for testable code**:
```rust
// errors.rs — pure Rust function (testable without Python)
pub fn make_invalid_input_error(msg: &str) -> GraviteaError {
    GraviteaError::InvalidInput(msg.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_error_display() {
        let err = GraviteaError::InvalidInput("bad data".to_string());
        assert_eq!(format!("{err}"), "Invalid input: bad data");
    }

    #[test]
    fn test_io_error_from() {
        let io_err = std::io::Error::new(std::io::ErrorKind::NotFound, "file not found");
        let err: GraviteaError = io_err.into();
        assert!(matches!(err, GraviteaError::IoError(_)));
    }
}
```

**What CAN be tested in `cargo test`**:
- Error enum construction and Display formatting
- Error variant matching
- `From` trait conversions (e.g., `std::io::Error` → `GraviteaError`)
- Pure Rust helper functions

**What CANNOT be tested in `cargo test`**:
- `#[pyfunction]` decorated functions (need Python interpreter)
- `PyErr` conversion (requires Python GIL)
- Module registration

**Python integration tests** handle the PyO3 boundary:
```python
# test_rust_import.py
def test_hello_returns_expected_string():
    from gravitea_rust import hello
    assert hello() == "Hello from Rust"
```
