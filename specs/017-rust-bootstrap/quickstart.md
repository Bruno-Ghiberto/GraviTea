# Developer Quickstart: Rust Toolchain Bootstrap (SPEC-017)

**Date**: 2026-02-25 | **Branch**: `017-rust-bootstrap` | **Spec**: [spec.md](spec.md)

---

## Prerequisites

### Required (for Rust development)

| Tool | Version | Install |
|------|---------|---------|
| Rust (stable) | 1.85+ | `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \| sh` |
| Maturin | 1.12+ | `pip install maturin>=1.12,<2.0` |
| Python | 3.14.x | Already in project (virtual env) |

### Optional (for Docker builds)

| Tool | Version | Install |
|------|---------|---------|
| Docker Desktop | Latest | [docker.com](https://www.docker.com/products/docker-desktop/) |
| WSL2 | Default | Included with Docker Desktop on Windows |

### Not required (for Python-only developers)

If you only work on Python code, you do **not** need Rust installed. The fallback pattern ensures the backend runs without the Rust extension.

---

## Project Layout

```text
GRAVITEA-ERP/
├── rust/gravitea-core/          # Rust crate
│   ├── Cargo.toml               # Package manifest (PyO3 + thiserror)
│   ├── Cargo.lock               # Committed for reproducible builds
│   ├── pyproject.toml            # Maturin build backend config
│   └── src/
│       ├── lib.rs               # #[pymodule] entry point + hello()
│       └── errors.rs            # GraviteaError → PyErr mapping
├── backend/
│   ├── gravitea_rust.pyi        # Type stub for IDE autocomplete
│   └── tests/rust_integration/  # Python integration tests
│       ├── test_rust_import.py  # Import + hello() tests
│       └── test_rust_fallback.py # Fallback pattern tests
└── backend/Dockerfile           # Modified: rust-builder stage added
```

---

## Build & Test Workflow

### 1. Build the Rust extension (local development)

From the Rust crate directory:

```bash
cd rust/gravitea-core
maturin develop --release
```

This compiles the Rust code and installs the resulting `.pyd` (Windows) or `.so` (Linux) into your active Python virtual environment. First build takes ~45-60s; incremental builds take ~15-30s.

### 2. Verify the import

```bash
python -c "from gravitea_rust import hello; print(hello())"
# Expected: Hello from Rust
```

### 3. Run Rust-native tests

```bash
cd rust/gravitea-core
cargo test
```

Tests cover:
- `hello()` return value
- `GraviteaError` display formatting
- `GraviteaError::IoError` From conversion

### 4. Run Python integration tests

```bash
cd backend
pytest tests/rust_integration/ -v
```

Tests cover:
- `test_rust_import.py` — importing and calling `hello()`
- `test_rust_fallback.py` — graceful fallback when extension is absent

### 5. Run full backend test suite (regression check)

```bash
cd backend
pytest --tb=short -q --no-header
```

All 2,200+ existing tests must pass with zero regressions.

---

## Docker Workflow

### Build the image

```bash
docker compose build web
```

The Dockerfile now has a `rust-builder` stage that:
1. Starts from `rust:1.85-slim-bookworm`
2. Installs `python3-dev` for PyO3 build headers
3. Caches Rust dependencies (rebuilds only when `Cargo.toml`/`Cargo.lock` change)
4. Compiles the Rust source into a wheel via `maturin build --release`
5. Passes the wheel to the Python runtime stage for installation

### Verify inside container

```bash
docker compose up -d web
docker compose exec web python -c "from gravitea_rust import hello; print(hello())"
# Expected: Hello from Rust
```

### Build time expectations

| Scenario | Expected Time |
|----------|--------------|
| First build (deps + source) | 45-60s |
| Source-only change (deps cached) | 15-35s |
| No Rust changes (full cache hit) | <5s |

---

## WSL2 Notes (Windows Developers)

- **Recommended**: Install Rust inside WSL2 (not native Windows) since Docker builds target Linux
- **Maturin develop**: Works from Git Bash/WSL2 terminal with the Python venv activated
- **File watching**: If using `cargo watch`, run it inside WSL2 for better filesystem event support
- **Path format**: Use Linux-style paths inside WSL2 (`/mnt/c/...`), Windows paths in Git Bash

---

## Fallback Pattern Convention

All future Rust-accelerated modules follow this pattern:

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

**Rules**:
- The `try/except ImportError` block is at module level (runs once at import time)
- The `_USE_RUST` flag is module-private
- Public functions check the flag and dispatch accordingly
- The fallback produces **identical results** to the Rust implementation

---

## Error Mapping Convention

Rust errors map to Python exceptions via `GraviteaError`:

| Rust Variant | Python Exception | When |
|-------------|-----------------|------|
| `GraviteaError::InvalidInput(msg)` | `ValueError` | Bad function arguments |
| `GraviteaError::CryptoError(msg)` | `RuntimeError` | Crypto operation failures |
| `GraviteaError::IoError(err)` | `IOError` | File/network I/O errors |

New variants are added by future specs (SPEC-018+) following this same pattern.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `maturin: command not found` | Maturin not installed | `pip install maturin>=1.12,<2.0` |
| `error: can't find crate for pyo3` | Missing Rust deps | `cargo build --release` first |
| `ImportError: No module named 'gravitea_rust'` | Extension not built | Run `maturin develop --release` |
| `OSError: ... wrong ELF class` | Architecture mismatch | Rebuild for correct platform |
| `cargo test` fails with Python errors | Expected — PyO3 boundary tests need Python | Run those via `pytest`, not `cargo test` |
| Docker build slow on deps | Cache invalidated | Only modify `Cargo.toml` when deps change |
