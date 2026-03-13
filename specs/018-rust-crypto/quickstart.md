# Quickstart: Crypto Acceleration Layer (SPEC-018)

**Branch**: `018-rust-crypto` | **Date**: 2026-02-25

---

## Prerequisites

| Tool | Version | Check |
|------|---------|-------|
| Rust (rustup) | 1.93.1+ | `rustc --version` |
| Maturin | 1.12.4+ | `maturin --version` |
| Python venv (WSL2) | 3.13.12 | `backend/venv-wsl/bin/python --version` |
| Docker | Any | `docker --version` |

> SPEC-017 must be complete. Verify: `backend/venv-wsl/bin/python -c "import gravitea_rust; print(gravitea_rust.hello())"` should print `"Hello from Rust!"`.

---

## 1. Add Crate Dependencies

```bash
# From repo root (WSL2)
cd rust/gravitea-core

# Edit Cargo.toml — add to [dependencies]:
# aes-gcm = "0.10"
# hmac = "0.12"
# sha2 = "0.10"
# rand = "0.8"
# hex = "0.4"
# unicode-normalization = "0.1"
```

---

## 2. Build the Rust Extension

```bash
# From repo root (WSL2)
cd rust/gravitea-core

# Run Rust tests first
cargo test

# Build and install into WSL venv
cd /mnt/c/Users/Ghibe/Documents/Gravitea/GRAVITEA-ERP
maturin develop -m rust/gravitea-core/Cargo.toml \
  --interpreter backend/venv-wsl/bin/python
```

**Expected output**:
```
🔗 Found pyo3 bindings with abi3 support for Python ≥ 3.8
📦 Built wheel for abi3 Python ≥ 3.8: [wheel path]
✅ Installed gravitea_rust-0.x.x
```

---

## 3. Verify the Build

```bash
backend/venv-wsl/bin/python -c "
import gravitea_rust, os
key = os.urandom(32)
enc = gravitea_rust.encrypt_value('hello', key)
dec = gravitea_rust.decrypt_value(enc, key)
assert dec == 'hello', f'mismatch: {dec!r}'
print('encrypt/decrypt OK')

idx = gravitea_rust.compute_blind_index('García', key)
assert len(idx) == 64, f'wrong length: {len(idx)}'
print(f'blind_index OK: {idx[:16]}...')
"
```

---

## 4. Run the Integration Tests

```bash
# Crypto-specific tests only (no Django required)
backend/venv-wsl/bin/python -m pytest \
  backend/tests/rust_integration/test_crypto_018.py \
  -p no:django \
  --confcutdir=backend/tests/rust_integration \
  -o "addopts=" \
  --tb=short -q

# Or via external runner (recommended for agents)
scripts/run-tests-external.sh \
  "backend/venv-wsl/bin/python -m pytest backend/tests/rust_integration/test_crypto_018.py \
   -p no:django --confcutdir=backend/tests/rust_integration -o 'addopts=' --tb=short -q"
```

---

## 5. Run Cargo Tests

```bash
cd rust/gravitea-core
cargo test -- --nocapture 2>&1 | tail -30
```

**Expected**: 17 tests pass (7 encrypt/decrypt + 5 blind index + 3 error validation + 2 proptests).

Actual output (2026-02-26):
```
running 17 tests
test crypto::tests::test_encrypt_decrypt_roundtrip ... ok
test crypto::tests::test_nonce_uniqueness ... ok
test crypto::tests::test_wrong_key_rejection ... ok
test crypto::tests::test_tag_mismatch_returns_crypto_error ... ok
test crypto::tests::test_encrypt_short_key ... ok
test crypto::tests::test_encrypt_off_by_one_key ... ok
test crypto::tests::test_decrypt_short_key ... ok
test crypto::tests::test_blind_index_case_insensitive ... ok
test crypto::tests::test_blind_index_whitespace_strip ... ok
test crypto::tests::test_blind_index_nfc_normalisation ... ok
test crypto::tests::test_blind_index_cuit_passthrough ... ok
test crypto::tests::test_blind_index_wrong_key_length ... ok
test crypto::proptests::test_blind_index_case_normalisation_idempotent ... ok
test crypto::proptests::test_blind_index_idempotent ... ok
test errors::tests::test_error_display ... ok
test errors::tests::test_io_error_from ... ok
test tests::test_hello ... ok
test result: ok. 17 passed; 0 failed; finished in 0.03s
```

---

## 6. Test the Fallback Path

```bash
# Temporarily disable the Rust path:
# In backend/apps/core/encryption/utils.py, change:
#   _USE_RUST = True  →  _USE_RUST = False
# (or uninstall: pip uninstall gravitea_rust)

backend/venv-wsl/bin/python -m pytest backend/tests/ \
  --tb=short -q --no-header 2>&1 | tail -20

# Verify FR-010: startup warning appears when fallback active
backend/venv-wsl/bin/python -c "
import logging, sys
logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
import backend.apps.core.encryption.utils  # should print WARNING
"
```

---

## 7. Docker Build Verification

```bash
# Rebuild image (includes Maturin build step)
docker compose build web

# Test crypto availability inside container
docker compose run --rm web python -c "
import gravitea_rust
print(gravitea_rust.encrypt_value('test', b'0' * 32))
"
```

---

## 8. Full Regression

```bash
scripts/run-tests-external.sh \
  "backend/venv-wsl/bin/python -m pytest backend/tests/ --tb=short -q --no-header"
# Then: cat Docs/Tests/<name>.summary
```

Target: 0 new failures vs SPEC-017 baseline.

---

## File Reference

| File | Change |
|------|--------|
| `rust/gravitea-core/Cargo.toml` | +7 crate deps (6 runtime + proptest dev-dep) |
| `rust/gravitea-core/src/lib.rs` | +1 `mod crypto;` + 3 `#[pymodule_export]` |
| `rust/gravitea-core/src/crypto.rs` | NEW: 3 pyfunction exports |
| `backend/apps/core/encryption/utils.py` | +`_USE_RUST` dispatch block |
| `backend/gravitea_rust.pyi` | +3 function stubs |
| `backend/tests/rust_integration/test_crypto_018.py` | NEW: all crypto tests |

---

## Troubleshooting

**`ImportError: No module named 'gravitea_rust'`**
→ Run `maturin develop` (step 2 above). Fallback activates automatically in production if import fails.

**`ValueError: key must be exactly 32 bytes`**
→ Check `get_encryption_key()` / `get_hmac_key()` return values. Keys must be exactly 32 bytes.

**`DecryptionError` / `PyRuntimeError` on existing data**
→ Wire format mismatch. Run the fixed test vector test from research.md R-002 to confirm format parity. Check that `base64url` vs standard base64 is not the issue.

**Blind index mismatch between Rust and Python**
→ Check normalisation order: NFC FIRST, then `.lower()`, then `.strip()`. Confirm `unicode-normalization` version in Cargo.lock matches expected NFC output for test vectors in research.md R-001.
