# Quickstart: Rust Sync Conflict Engine (SPEC-023)

## Prerequisites

- Rust 1.93.1+ with `cargo` (installed via rustup in WSL2)
- Maturin 1.12.4+ (`pip install maturin`)
- Python 3.14.3 venv at `backend/venv-wsl/`
- Docker (for container validation)

## Build

```bash
# Build Rust extension into WSL venv
cd /mnt/c/Users/Ghibe/Documents/Gravitea/GRAVITEA-ERP
VIRTUAL_ENV=$(pwd)/backend/venv-wsl maturin develop \
  --manifest-path rust/gravitea-core/Cargo.toml --release
```

## Test — Rust Native

```bash
cd rust/gravitea-core && cargo test sync -- --nocapture
```

Expected: ≥8 sync tests passing.

## Test — Python Integration

```bash
# Via external test runner (mandatory for agents)
scripts/run-tests-external.sh "sync-023" \
  "cd backend && venv-wsl/bin/python -m pytest tests/rust_integration/test_sync_023.py --tb=short -q"
```

## Test — Full Regression

```bash
scripts/run-tests-external.sh "regression-023" \
  "cd backend && venv-wsl/bin/python -m pytest tests/ --tb=short -q --no-header"
```

## Test — Docker

```bash
# Build container
docker compose build web

# Verify import
docker compose run --rm --entrypoint python web -c \
  "from gravitea_rust import merge_most_complete, merge_most_complete_batch; print('OK')"

# Run SPEC-023 tests in container
docker compose run --rm --entrypoint bash web -c \
  "pip install -r requirements/development.txt && \
   python -m pytest tests/rust_integration/test_sync_023.py --tb=short -q \
   --override-ini='addopts='"
```

## Verify Fallback

```python
# In Python shell — simulate Rust unavailable
import unittest.mock as mock
with mock.patch.dict('sys.modules', {'gravitea_rust': None}):
    from importlib import reload
    from apps.sync import sync_engine
    reload(sync_engine)
    assert sync_engine._USE_RUST is False
```

## Key Files

| File | Purpose |
|------|---------|
| `rust/gravitea-core/src/sync.rs` | Rust merge implementation |
| `rust/gravitea-core/src/errors.rs` | SyncError variant |
| `rust/gravitea-core/src/lib.rs` | Module registration |
| `backend/apps/sync/sync_engine.py` | Python dispatcher |
| `backend/apps/sync/conflict_resolver.py` | Modified caller |
| `backend/gravitea_rust.pyi` | Type stubs |
| `backend/tests/rust_integration/test_sync_023.py` | Test suite |
