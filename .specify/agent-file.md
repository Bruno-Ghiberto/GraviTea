# GRAVITEA-ERP Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-02-25

## Active Technologies

| Language/Tool | Version | Context |
|---------------|---------|---------|
| Python | 3.14.3 | Primary backend language |
| Django | 5.2.x | Web framework |
| Rust | 1.93.1 | Crypto acceleration layer (PyO3 FFI) |
| PyO3 | 0.28 | Python↔Rust FFI bridge |
| Maturin | 1.12.4 | Rust extension build tool |
| PostgreSQL | 18.1 | Primary database |
| Redis | 7.x | Cache, rate limiting |
| pytest + hypothesis | latest | Testing (Python) |
| cargo test | built-in | Testing (Rust) |

### Rust Crates (018-rust-crypto)

| Crate | Version | Purpose |
|-------|---------|---------|
| `aes-gcm` | 0.10 | AES-256-GCM encryption |
| `hmac` | 0.12 | HMAC-SHA256 blind index |
| `sha2` | 0.10 | SHA256 digest |
| `rand` | 0.8 | OsRng nonce generation |
| `hex` | 0.4 | Lowercase hex encoding |
| `unicode-normalization` | 0.1 | NFC normalisation for blind index |

## Project Structure

```text
rust/gravitea-core/
├── Cargo.toml
└── src/
    ├── lib.rs          # declarative #[pymodule] with #[pymodule_export]
    ├── errors.rs       # GraviteaError enum (InvalidInput, CryptoError)
    └── crypto.rs       # 3 #[pyfunction] exports (SPEC-018)

backend/
├── gravitea_rust.pyi   # type stubs for Rust extension
├── apps/core/encryption/
│   └── utils.py        # _USE_RUST dispatch; encrypt_value, decrypt_value, compute_blind_index
└── tests/
    └── rust_integration/
        ├── test_rust_import.py    (SPEC-017)
        └── test_crypto_018.py     (SPEC-018)
```

## Commands

```bash
# Build Rust extension into WSL venv
maturin develop -m rust/gravitea-core/Cargo.toml \
  --interpreter backend/venv-wsl/bin/python

# Run Rust tests
cd rust/gravitea-core && cargo test

# Run crypto integration tests (no Django required)
backend/venv-wsl/bin/python -m pytest \
  backend/tests/rust_integration/test_crypto_018.py \
  -p no:django --confcutdir=backend/tests/rust_integration \
  -o "addopts=" --tb=short -q

# Run full test suite (via external runner)
scripts/run-tests-external.sh \
  "backend/venv-wsl/bin/python -m pytest backend/tests/ --tb=short -q --no-header"
```

## Code Style

### Rust (PyO3 functions)
- Use `GraviteaError` variants (not raw `PyErr`) for error mapping
- `InvalidInput` → `PyValueError`, `CryptoError` → `PyRuntimeError`
- None/empty guards in Python wrapper, not in Rust functions
- Key validation: `key.len() != 32` → `Err(GraviteaError::InvalidInput(...))`
- Blind index normalisation order: **NFC → `.to_lowercase()` → `.trim()`** (this order is mandatory)

### Python (`utils.py` fallback dispatch)
```python
try:
    from gravitea_rust import encrypt_value as _rust_encrypt_value
    _USE_RUST = True
except ImportError:
    _USE_RUST = False
    import logging
    logging.getLogger(__name__).warning("gravitea_rust not available — using software fallback")
```

## Recent Changes

| Feature | Branch | Key Additions |
|---------|--------|---------------|
| SPEC-017: Rust Bootstrap | `017-rust-bootstrap` | PyO3 0.28 + Maturin toolchain; `gravitea_rust` module with `hello()`; `GraviteaError` enum; WSL2 venv at `backend/venv-wsl/` |
| SPEC-018: Crypto Acceleration | `018-rust-crypto` | AES-256-GCM + HMAC-SHA256 in Rust; 3 PyO3 exports; `_USE_RUST` Python fallback; NFC blind index; FR-010 startup warning |

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
