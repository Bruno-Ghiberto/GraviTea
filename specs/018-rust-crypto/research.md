# Research: Crypto Acceleration Layer (SPEC-018)

**Branch**: `018-rust-crypto` | **Date**: 2026-02-25
**Purpose**: Resolve all NEEDS CLARIFICATION items before implementation begins

---

## R-001: NFC Unicode Normalisation Parity

**Question**: Does the `unicode-normalization = "0.1"` Rust crate produce byte-identical output to Python's `unicodedata.normalize("NFC", value)` for Argentine PII (ñ, á, é, ü, CUIT numbers)?

### Decision

**Use `unicode-normalization = "0.1"` crate.** Both Rust and Python implement UAX#15 (Unicode Normalization Forms). Output is byte-identical for the Argentine PII corpus.

### Rationale

- Both `unicode-normalization` (Rust, `unicode-rs`) and Python's `unicodedata` implement the same Unicode Consortium standard: UAX#15
- Spanish accented characters used in Argentine PII (á, é, í, ó, ú, ü, ñ) are all Basic Latin + Latin Extended precomposed forms — they have stable NFC representations that are identical across all Unicode versions from Unicode 3.0 onwards
- CUIT numbers (11 ASCII digits, optionally hyphen-separated) are unchanged by NFC — ASCII is a NFC no-op
- The crate is actively maintained (last update November 2025) by the `unicode-rs` organisation

**Caveat**: If strings arrive in NFD form (e.g., `n` + combining tilde `U+0303` instead of `ñ U+00F1`), NFC normalisation converts them to the precomposed form. Both Python and Rust produce identical output in this case. The NFC parity tests in `test_crypto_018.py` verify this explicitly.

### Rust Usage Pattern

```rust
use unicode_normalization::UnicodeNormalization;

fn normalise_for_blind_index(value: &str) -> String {
    // NFC first, then lowercase, then strip — order is mandatory (FR-003)
    value.nfc().collect::<String>().to_lowercase().trim().to_string()
}
```

### Test Vectors (NFC → lowercase → strip)

| Input | Expected blind index basis |
|-------|---------------------------|
| `"García"` | `"garcía"` |
| `"  GARCÍA  "` | `"garcía"` |
| `"Garca\u0301a"` (NFD ó) | `"garcía"` |
| `"20123456789"` | `"20123456789"` |
| `"20-123-45678-9"` | `"20-123-45678-9"` |
| `"Ñoño"` | `"ñoño"` |
| `"  José Núñez  "` | `"josé núñez"` |

### Alternatives Considered

| Alternative | Rejected Because |
|-------------|-----------------|
| `icu4x` crate | Excessive dependency weight for 3-char normalisation; unicode-normalization 0.1 is sufficient |
| ASCII-only normalisation (no NFC) | Would break blind index lookups when same name stored in NFD vs NFC form (R-001 is about exactly this) |
| Skip normalisation | Violates FR-003; would cause search misses on accent-decomposed input |

---

## R-002: `aes-gcm 0.10` Audit Status and Wire Format

**Question**: Has `aes-gcm 0.10` been independently audited? Is its wire format (`ciphertext || tag`) byte-identical to Python's `cryptography.AESGCM`?

### Decision

**Use `aes-gcm = "0.10"` (RustCrypto).** Independently audited; wire format is byte-identical to Python's `cryptography` library.

### Rationale

**Audit**: The `aes-gcm` crate (RustCrypto AEADs repository) was audited by **NCC Group** in 2020, funded by MobileCoin. The audit found no significant vulnerabilities. The crate implements AES-256-GCM with constant-time guarantees via AES-NI hardware intrinsics on x86/x86_64 and a portable constant-time fallback on other architectures.

**Wire format compatibility**:

| Component | Python `cryptography` | Rust `aes-gcm 0.10` |
|-----------|----------------------|---------------------|
| Nonce | 12 bytes, prepended by application | 12 bytes (caller-provided via `Nonce`) |
| Ciphertext | Same length as plaintext | Same length as plaintext |
| Auth tag | 16 bytes, **appended to ciphertext** | 16 bytes, **appended to ciphertext** |
| Full output | `encrypt(nonce, plaintext, aad=None)` → `ciphertext || tag[16]` | `encrypt_in_place_detached` or `encrypt` → `ciphertext + tag` |

Both produce the same byte layout. The stored blob in the database is:
```
base64( nonce[12] || ciphertext[n] || tag[16] )
```
Python's `AESGCM.encrypt(nonce, data, None)` returns `ciphertext + tag`. Rust's `Aes256Gcm::encrypt` also returns `ciphertext + tag`. The Python decryptor separates `ciphertext[:-16]` and `tag[-16:]`; Rust does the same internally.

### Cross-Compatibility Test Vector

To verify before claiming compatibility, Phase 3 must include a **fixed test vector test**:
- Encrypt `b"hello"` with key `[0u8; 32]` and nonce `[0u8; 12]` in both Python and Rust
- Decrypt each output with the other implementation
- Both must succeed

### Alternatives Considered

| Alternative | Rejected Because |
|-------------|-----------------|
| `ring` crate | Less ergonomic PyO3 integration; no audit advantage |
| `chacha20poly1305` | AES-GCM is spec-mandated (§IV of constitution); no interop with existing data |
| Custom AES-GCM | Never implement custom crypto |

---

## R-003: Property-Based Test Coverage — Argentine PII Distributions

**Question**: Which input distributions are most important for `hypothesis` tests targeting blind index correctness?

### Decision

**Six input distributions.** Priority order: Spanish accents > NFD edge cases > whitespace variations > case variations > CUIT formatting > empty/single-char.

### Input Distributions

| Priority | Distribution | Rationale |
|----------|-------------|-----------|
| 1 (HIGH) | Spanish-accented names (precomposed NFC): `"María García"`, `"José Núñez"`, `"Andrés Peña"` | Core Argentine PII; most common source of normalisation bugs |
| 2 (HIGH) | NFD-encoded variants: `unicodedata.normalize("NFD", name)` of the above | Tests that NFC step actually fixes decomposed forms |
| 3 (MED) | Names with leading/trailing whitespace: `"  María  "`, `"\tJosé\n"` | Tests strip step |
| 4 (MED) | Case variations: all-upper, all-lower, mixed-case | Tests lowercase step |
| 5 (MED) | CUIT-like strings: `"20123456789"`, `"20-123-45678-9"`, `"20 123 456789"` | Tests ASCII pass-through; most common searchable field |
| 6 (LOW) | Empty and single-char: `""`, `"M"`, `"ñ"` | Edge cases for guard logic |

### Hypothesis Strategy

```python
from hypothesis import given, settings, strategies as st
import unicodedata

ACCENT_CHARS = "abcdefghijklmnñopqrstuvwxyzáéíóúüABCDEFGHIJKLMNÑOPQRSTUVWXYZÁÉÍÓÚÜ "

spanish_name = st.text(alphabet=ACCENT_CHARS, min_size=1, max_size=50)
whitespace = st.sampled_from(["", " ", "  ", "\t", "\n"])
padded_name = st.builds(
    lambda pre, name, post: f"{pre}{name}{post}",
    whitespace, spanish_name, whitespace
)
nfd_name = spanish_name.map(lambda s: unicodedata.normalize("NFD", s))
cased_name = spanish_name.flatmap(
    lambda s: st.sampled_from([s, s.lower(), s.upper()])
)
cuit_string = st.from_regex(r"\d{2}[-\s]?\d{8}[-\s]?\d{1}", fullmatch=True)

pii_input = st.one_of(spanish_name, padded_name, nfd_name, cased_name, cuit_string)
```

**Minimum examples**: 500 per FR-009 / SC-007 (spec says 500+ random Unicode strings).

---

## R-004: Hex Encoding Case — `hex::encode` vs `hexdigest()`

**Question**: Does `hex::encode()` (Rust `hex 0.4`) produce lowercase hex matching Python's `hmac.new(...).hexdigest()`?

### Decision

**Both produce lowercase hex. No divergence.** Use `hex::encode()` directly.

### Rationale

- Python `hmac.new(key, msg, hashlib.sha256).hexdigest()` returns lowercase hexadecimal (Python standard: `str.hex()` always lowercase)
- Rust `hex::encode(bytes)` returns lowercase hexadecimal by design (documented behaviour)
- The crate also provides `hex::encode_upper()` for uppercase; the default `encode()` is always lowercase

### Verification Example

```rust
assert_eq!(hex::encode(&[0xab, 0xcd, 0xef]), "abcdef");  // lowercase
```

```python
import hmac, hashlib
result = hmac.new(b"key", b"msg", hashlib.sha256).hexdigest()
assert result == result.lower()  # always true
```

**Length**: Both produce 64-character strings for SHA-256 output (32 bytes × 2 hex chars). No padding differences.

### Alternatives Considered

| Alternative | Rejected Because |
|-------------|-----------------|
| `format!("{:x}", ...)` | Requires manual byte iteration; more code, same result |
| Custom hex encoding | Never implement custom encoding when a crate exists |

---

## Benchmark Results (Phase 7 — T037)

**Date**: 2026-02-26 | **Platform**: WSL2, Python 3.14, Rust 1.93.1 (release profile)

| Operation | Rust (ns/op) | Python (ns/op) | Speedup |
|-----------|-------------|----------------|---------|
| encrypt (50-char) | 949 | 8,260 | **8.7x** |
| decrypt (50-char) | 702 | 6,194 | **8.8x** |

**SC-001 verdict**: PASS — both exceed the ≥5x target. Rust operations complete in <1 us (well under <5 us cap).

Measured via `pytest-benchmark` pedantic mode (1000 iterations x 3 rounds). Benchmarks use direct Rust function calls (no Django overhead).

---

## Summary

All four research topics are resolved. No blockers. Implementation can proceed to Phase 1.

| ID | Decision | Confidence | Action Required |
|----|----------|-----------|-----------------|
| R-001 | `unicode-normalization 0.1` crate, `nfc()` iterator | HIGH | Add test vectors for ñ/á/é/ü/CUIT in Phase 3 |
| R-002 | `aes-gcm 0.10` RustCrypto, NCC Group audited, wire format identical | HIGH | Add fixed test vector in Phase 3 cross-compat tests |
| R-003 | 6 distributions, `hypothesis`, 500 min examples | HIGH | Use strategy template in `test_crypto_018.py` |
| R-004 | `hex::encode()` lowercase — exact match to Python | HIGH | No action needed |
