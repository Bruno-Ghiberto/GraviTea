# Speckit Context: Crypto Acceleration (SPEC-018)

> **Phase**: SPECIFY — Define what we're accelerating and why
> **Priority**: HIGH | **Wave**: 2 (parallel with SPEC-021)
> **Depends on**: SPEC-017 (Rust Toolchain Bootstrap) — COMPLETE (commit `2db3189`)

---

## Mission Statement

Replace the CPU-bound internals of `backend/apps/core/encryption/utils.py` with Rust
AES-256-GCM encryption and HMAC-SHA256 blind indexing. The Python public API is preserved
unchanged — Rust replaces only the cryptographic operations, maintaining byte-for-byte
wire-format compatibility with all existing encrypted database data.

## Why This Matters

- **Every PII field** (Customer name, address, CUIT, phone) is encrypted/decrypted on every
  read/write through `EncryptedField` descriptors
- **~7x speedup** per encrypt/decrypt operation — for a Customer with 3 encrypted fields
  that is ~39 µs saved per DB write
- **Memory safety for key material**: Rust drops key bytes deterministically; no GC delay
- **Smallest FFI boundary** of all Rust specs — proves the pattern for Waves 3-5

---

## Current State — What Exists Today

### File: `backend/apps/core/encryption/utils.py`

Three public functions (read the file before writing the spec — do not guess signatures):

```python
def encrypt_value(value: str) -> str:
    """AES-256-GCM encryption. Handles None → None, '' → '' internally.
    Format: base64(nonce[12] || ciphertext || tag[16])
    Key fetched internally via get_encryption_key() (lru_cached)."""

def decrypt_value(encrypted: str) -> str:
    """AES-256-GCM decryption. Handles None → None, '' → '' internally.
    Raises ValueError on tampered/invalid data."""

def compute_blind_index(value: str) -> Optional[str]:
    """HMAC-SHA256 of value.lower().strip(). Returns 64-char hex string.
    Returns None when value is None.
    Key fetched internally via get_hmac_key() (lru_cached)."""
```

**There is no `generate_nonce` Python function** — nonce generation (`os.urandom(12)`) is
internal to `encrypt_value`. Do NOT spec a `generate_nonce` export.

### Existing Rust Crate: `rust/gravitea-core/`

- `src/lib.rs` — declarative `#[pymodule] mod gravitea_rust { ... }` with `#[pymodule_export]`
- `src/errors.rs` — `GraviteaError` enum: `InvalidInput` → `PyValueError`,
  `CryptoError` → `PyRuntimeError`
- `Cargo.toml` — `pyo3 = "0.28"`, `thiserror = "2.0"`. **No crypto crates yet.**
- `backend/gravitea_rust.pyi` — currently has only `hello()` and `GraviteaError`

---

## Architecture Decisions (FINAL — Do Not Re-Debate)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| AES-GCM crate | `aes-gcm = "0.10"` | RustCrypto audited; `Aes256Gcm` type alias |
| HMAC crate | `hmac = "0.12"` + `sha2 = "0.10"` | RustCrypto ecosystem, HMAC-SHA256 |
| Nonce generation | `rand = "0.8"` with `OsRng` | CSPRNG, internal to `rust_encrypt_value` |
| Hex encoding | `hex = "0.4"` | Blind index hex output |
| GIL handling | NOT released | Sub-millisecond operations; GIL overhead exceeds savings |
| Wire format | `base64(nonce[12] \|\| ciphertext \|\| tag[16])` | AES-GCM standard; byte-for-byte compatible with Python |
| Key passing | Rust takes explicit `key: &[u8]` | Rust cannot call Django `settings`; Python wrapper fetches via `get_encryption_key()` / `get_hmac_key()` and passes through |
| None/empty guard | Python wrapper, NOT Rust | Keeps Rust functions simple pure-compute; wrapper returns `None`/`""` before calling Rust |
| Module structure | Top-level exports (not submodule) | `from gravitea_rust import encrypt_value` — consistent with `from gravitea_rust import hello` |
| Fallback pattern | `try: from gravitea_rust import ...; _USE_RUST = True` | Matches SPEC-017 bootstrap convention |
| `cryptography` library | Retained | WSAA certificate operations (PKCS#7/X.509) in `apps/facturacion/` stay in Python |

---

## Target Architecture

### New Rust Source Files

```
rust/gravitea-core/src/
├── lib.rs       # MODIFIED — add #[pymodule_export] for 3 new functions
├── errors.rs    # UNCHANGED — GraviteaError already has CryptoError variant
└── crypto.rs    # NEW — all 3 functions
```

### Rust Function Signatures (`crypto.rs`)

```rust
// AES-256-GCM encrypt. key must be exactly 32 bytes.
// Returns base64(nonce[12] || ciphertext || tag[16]).
// Raises PyValueError for wrong key length; PyRuntimeError for crypto failures.
pub fn encrypt_value(plaintext: &str, key: &[u8]) -> PyResult<String>

// AES-256-GCM decrypt. key must be exactly 32 bytes.
// Raises PyValueError for wrong key length; PyRuntimeError for decryption failures.
pub fn decrypt_value(encrypted: &str, key: &[u8]) -> PyResult<String>

// HMAC-SHA256 of value.lower().strip(). hmac_key must be exactly 32 bytes.
// Returns 64-char hex string.
// Raises PyValueError for wrong key length.
pub fn compute_blind_index(value: &str, hmac_key: &[u8]) -> PyResult<String>
```

Nonce generation (`rand::rngs::OsRng`) is internal to `encrypt_value` — no fourth export.

### lib.rs Additions

Following the existing declarative `#[pymodule]` pattern in `lib.rs`:

```rust
mod crypto;

#[pymodule]
mod gravitea_rust {
    #[pymodule_export]
    use super::hello;
    #[pymodule_export]
    use super::crypto::encrypt_value;
    #[pymodule_export]
    use super::crypto::decrypt_value;
    #[pymodule_export]
    use super::crypto::compute_blind_index;
}
```

### Python Wrapper Changes (`encryption/utils.py`)

The public API signatures do NOT change. Only the internal dispatch changes:

```python
try:
    from gravitea_rust import (
        encrypt_value as _rust_encrypt_value,
        decrypt_value as _rust_decrypt_value,
        compute_blind_index as _rust_compute_blind_index,
    )
    _USE_RUST = True
except ImportError:
    _USE_RUST = False


def encrypt_value(value: str) -> str:
    if value is None:
        return None
    if value == "":
        return ""
    key = get_encryption_key()   # lru_cached, already existed
    if _USE_RUST:
        return _rust_encrypt_value(value, key)
    # ... existing Python implementation unchanged as fallback


def decrypt_value(encrypted: str) -> str:
    if encrypted is None:
        return None
    if encrypted == "":
        return ""
    key = get_encryption_key()
    if _USE_RUST:
        return _rust_decrypt_value(encrypted, key)
    # ... existing Python implementation unchanged as fallback


def compute_blind_index(value: str) -> Optional[str]:
    if value is None:
        return None
    key = get_hmac_key()         # lru_cached, already existed
    if _USE_RUST:
        return _rust_compute_blind_index(value, key)
    # ... existing Python implementation unchanged as fallback
```

### Cargo.toml Additions

```toml
# Add to [dependencies] in rust/gravitea-core/Cargo.toml
aes-gcm = "0.10"
hmac = "0.12"
sha2 = "0.10"
rand = "0.8"
hex = "0.4"
```

### Type Stub Update (`backend/gravitea_rust.pyi`)

Add three function signatures to the existing stub:

```python
def encrypt_value(plaintext: str, key: bytes) -> str: ...
def decrypt_value(encrypted: str, key: bytes) -> str: ...
def compute_blind_index(value: str, hmac_key: bytes) -> str: ...
```

---

## FFI Boundary Analysis

| Input | Size | FFI Overhead | Python Work | Rust Work | Net Gain |
|-------|------|-------------|-------------|-----------|----------|
| ~50 char plaintext + 32B key | ~82 bytes | ~0.1 µs | ~15 µs | ~2 µs | **+12.9 µs** |
| ~80 char blind index value + 32B key | ~112 bytes | ~0.1 µs | ~10 µs | ~1 µs | **+8.9 µs** |

All three functions have trivial FFI boundaries. No serialization beyond `&str` + `&[u8]`.

---

## Critical Caveats

1. **Cross-implementation equivalence tests are non-negotiable**: Before shipping, MUST verify:
   - Rust-encrypted → Python-decrypted ✓
   - Python-encrypted → Rust-decrypted ✓
   A format mismatch silently corrupts all existing PII data in the database.

2. **Blind index Unicode normalization**: `value.lower().strip()` in Python uses Python's Unicode
   lowercasing, which can differ from Rust's `.to_lowercase()` for edge cases (Turkish `İ`,
   German `ß`). GRAVITEA data is Argentine (CUITs, addresses) — primarily ASCII + Spanish accents.
   Test with actual sample data including `ñ`, `á`, `é`, `ü` to confirm parity.

3. **Key length validation**: Rust MUST reject keys with `!= 32 bytes` via `PyValueError`,
   exactly matching Python's `ValueError("ENCRYPTION_KEY must decode to exactly 32 bytes")`.

4. **aes-gcm tag position**: Python's `cryptography.AESGCM.encrypt()` appends the 16-byte GCM
   authentication tag to the ciphertext. The `aes-gcm` Rust crate does the same. Verify the
   exact output layout with a test vector before claiming compatibility.

5. **Test key management**: Rust integration tests cannot use Django `settings`. Tests must
   supply a `[u8; 32]` key directly. Use `[0u8; 32]` or a fixed test key constant.
   Run with: `-p no:django --confcutdir=backend/tests/rust_integration -o "addopts="`

---

## Testing Strategy

### Location

```
backend/tests/rust_integration/
├── __init__.py            # already exists (SPEC-017)
├── test_rust_import.py    # already exists (SPEC-017)
└── test_crypto_018.py     # NEW — all crypto tests
```

### Test Categories (in `test_crypto_018.py`)

1. **Rust-native tests** (`cargo test` in `crypto.rs`):
   - Roundtrip: encrypt → decrypt recovers original
   - Determinism: same key, different nonces → different ciphertexts (encrypt called twice)
   - Wrong-key rejection: decryption fails with different 32-byte key
   - Key-length validation: `PyValueError` for 16, 31, 33-byte keys
   - Empty-string input: verify Rust receives a valid `&str` (wrapper guards this — test the wrapper)
   - Nonce uniqueness: 1000 encryptions of same plaintext → 1000 unique ciphertexts

2. **Cross-implementation equivalence** (`pytest` in `test_crypto_018.py`):
   - Python-encrypted → Rust-decrypted: 20 test strings including ASCII, Spanish, CUITs
   - Rust-encrypted → Python-decrypted: same corpus
   - Blind index parity: `compute_blind_index(value)` produces identical hex for same value
   - Blind index case-insensitivity: "SMITH" and "smith" produce the same index

3. **Property-based** (Python `hypothesis` in `test_crypto_018.py`):
   - Random UTF-8 strings roundtrip through Rust encrypt → Rust decrypt
   - Minimum 500 examples

4. **Benchmark** (optional, `pytest-benchmark`):
   - Measure speedup of Rust vs Python for encrypt, decrypt, blind_index
   - Include in test file, skip by default with `@pytest.mark.slow`

### Run Command

```bash
# Rust tests
cd rust/gravitea-core && cargo test

# Python integration tests
backend/venv-wsl/bin/python -m pytest backend/tests/rust_integration/test_crypto_018.py \
    -p no:django --confcutdir=backend/tests/rust_integration -o "addopts=" --tb=short -q

# Full regression (after integration tests pass)
backend/venv-wsl/bin/python -m pytest backend/tests/ --tb=short -q --no-header 2>&1 | tail -20
```

---

## Scope

### In Scope

- `rust/gravitea-core/src/crypto.rs` — 3 `#[pyfunction]` exports
- `rust/gravitea-core/src/lib.rs` — add 3 `#[pymodule_export]` lines
- `rust/gravitea-core/Cargo.toml` — add 5 crate dependencies
- `backend/apps/core/encryption/utils.py` — add `_USE_RUST` fallback dispatch
- `backend/gravitea_rust.pyi` — add 3 function stubs
- `backend/tests/rust_integration/test_crypto_018.py` — all test categories above

### Out of Scope

- ~~Changes to `EncryptedField` or `BlindIndexField` descriptors~~
- ~~Business logic changes to any Django model~~
- ~~WSAA/facturacion certificate operations (stays in Python `cryptography`)~~
- ~~Database migrations (wire format unchanged)~~
- ~~Multi-platform wheel builds~~
- ~~Changing Python's `get_encryption_key()` or `get_hmac_key()` functions~~

---

## Success Criteria

1. `cargo test` passes with ≥ 8 crypto-specific Rust tests
2. Cross-implementation equivalence: Rust↔Python encrypt/decrypt roundtrips pass for 20+ strings
3. Blind index: Rust and Python produce identical hex for same input (including Spanish chars)
4. Property-based: 500+ random strings roundtrip without error
5. Key-length validation: 16/31/33-byte keys raise `ValueError` from both Rust and Python paths
6. Fallback: commenting out the `try` block → Python implementation takes over, all tests pass
7. Existing encrypted DB data: a snapshot of real encrypted values decrypts correctly via Rust
8. `gravitea_rust.pyi` updated with 3 new signatures
9. Docker image builds and `import gravitea_rust; gravitea_rust.encrypt_value` works in container
10. Full Python test suite (2,200+ tests) passes with 0 new failures

---

## Reference Documents

| Document | Purpose | Path |
|----------|---------|------|
| Roadmap | Spec details, FFI table, caveats | `Docs/Brainstorming/rust-pyo3-speckit-roadmap.md` §4 |
| Integration Guide | PyO3 patterns, code examples | `Docs/Brainstorming/rust-pyo3-integration-guide.md` §5 |
| Current encryption | Python implementation to study | `backend/apps/core/encryption/utils.py` |
| Encryption skill | Field descriptor patterns | `skills/gravitea-encryption/SKILL.md` |
| SPEC-017 spec | Bootstrap patterns to follow | `specs/017-rust-bootstrap/spec.md` |
| SPEC-017 lib.rs | Declarative pymodule example | `rust/gravitea-core/src/lib.rs` |
| SPEC-017 errors.rs | GraviteaError to reuse | `rust/gravitea-core/src/errors.rs` |
| SPEC-017 integration tests | Test structure to follow | `backend/tests/rust_integration/test_rust_import.py` |
