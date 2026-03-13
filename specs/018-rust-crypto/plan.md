# Implementation Plan: Crypto Acceleration Layer

**Branch**: `018-rust-crypto` | **Date**: 2026-02-25 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/018-rust-crypto/spec.md`

## Summary

Replace the CPU-bound internals of `backend/apps/core/encryption/utils.py` with a Rust
acceleration layer (`rust/gravitea-core/src/crypto.rs`) exporting three PyO3 functions:
`encrypt_value`, `decrypt_value`, and `compute_blind_index`. The Python public API is
preserved unchanged. A `try/except ImportError` fallback ensures transparent operation when
the Rust extension is absent. All existing encrypted database data must remain readable with
zero migration; blind index searches must return identical results before and after deployment.

## Technical Context

**Language/Version**: Python 3.14.3 (host) + Rust 1.93.1 (acceleration layer)
**Primary Dependencies**: PyO3 0.28, Maturin 1.12.4; `aes-gcm 0.10`, `hmac 0.12`, `sha2 0.10`, `rand 0.8`, `hex 0.4`, `unicode-normalization 0.1`
**Storage**: N/A — no new Django models or database migrations
**Testing**: `cargo test` (Rust-native) + `pytest` with `hypothesis` (Python integration)
**Target Platform**: Linux (Docker container, WSL2 development)
**Project Type**: Single project — Rust FFI extension into existing Django backend
**Performance Goals**: Under 5 µs per encrypt/decrypt/blind-index operation (50-char plaintext in container); ≥5× improvement over ~15 µs Python baseline
**Constraints**: Byte-for-byte wire format compatibility with all existing encrypted DB data; zero call-site changes; `cryptography` library retained for WSAA/PKCS#7 operations
**Scale/Scope**: Affects every PII field read/write across all tenant operations; 3 Python functions redirected; 2 new source files (`crypto.rs`, `test_crypto_018.py`), 4 modified (`Cargo.toml`, `lib.rs`, `utils.py`, `gravitea_rust.pyi`)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **§I — Ironclad Data Model** | ✅ PASS | No schema changes; wire format unchanged; DB values remain valid |
| **§II — Multi-Tenant Isolation** | ✅ PASS | No model or RLS changes; encryption is pre-persistence and tenant-agnostic |
| **§III — Modular Django Architecture** | ✅ PASS | Changes confined to `apps/core/encryption/utils.py` — the encryption module; no new Django apps |
| **§IV — Application-Level Encryption** | ✅ PASS — Direct implementation | This feature strengthens §IV: replaces Python internals with audited Rust crypto (NCC Group–audited aes-gcm); maintains AES-256-GCM + HMAC-SHA256 mandated by constitution |
| **§V — Secure Authentication** | ✅ PASS | No auth changes |
| **§IX — Secure Data Operations** | ✅ PASS | Keys passed explicitly; never stored or logged |
| **§X — Test-Driven Development** | ✅ PASS | 8 Rust-native tests + pytest integration + property-based (500+ cases) |
| **§XIV — API Documentation** | ✅ PASS | No new endpoints; `gravitea_rust.pyi` stub updated |

**Gate result**: PASS — No constitution violations. Proceed to Phase 0.

**Post-design re-check**: After Phase 1 design, verify that `utils.py` changes preserve the existing public API (no signature changes) and that `crypto.rs` does not introduce any new dependencies that conflict with §IV requirements.

## Project Structure

### Documentation (this feature)

```text
specs/018-rust-crypto/
├── spec.md              ✅ (speckit.specify output)
├── checklists/
│   └── requirements.md  ✅ (speckit.specify output)
├── plan.md              ← This file
├── research.md          ← Phase 0 output
├── quickstart.md        ← Phase 1 output
└── tasks.md             (speckit.tasks command — NOT created by speckit.plan)
```

### Source Code (concrete paths modified by this feature)

```text
rust/gravitea-core/
├── Cargo.toml                    MODIFY — add 6 crate deps
└── src/
    ├── lib.rs                    MODIFY — add 3 #[pymodule_export] lines + mod crypto
    ├── errors.rs                 UNCHANGED
    └── crypto.rs                 NEW — 3 #[pyfunction] exports

backend/
├── gravitea_rust.pyi             MODIFY — add 3 function stubs
├── apps/core/encryption/
│   └── utils.py                  MODIFY — add _USE_RUST fallback dispatch
└── tests/
    └── rust_integration/
        ├── __init__.py            UNCHANGED (created by SPEC-017)
        ├── test_rust_import.py    UNCHANGED (created by SPEC-017)
        └── test_crypto_018.py     NEW — all crypto integration tests
```

**Structure Decision**: Single project (Option 1 variant). No new top-level directories. All Rust source in the existing `rust/gravitea-core/` crate established by SPEC-017. All Python test additions in the existing `backend/tests/rust_integration/` directory.

---

## Implementation Phases

### Phase 1: Rust Crypto Implementation (RUST-PROGRAMMER)

**Risk**: HIGH (crypto correctness is critical)
**Depends on**: SPEC-017 complete, `gravitea_rust` module loadable

Tasks:
1. Read `backend/apps/core/encryption/utils.py` — confirm exact wire format: `base64(nonce[12] || ciphertext || tag[16])` and blind index: NFC → lowercase → strip → HMAC-SHA256 → hexdigest
2. Add 6 crate deps to `rust/gravitea-core/Cargo.toml`: `aes-gcm = "0.10"`, `hmac = "0.12"`, `sha2 = "0.10"`, `rand = "0.8"`, `hex = "0.4"`, `unicode-normalization = "0.1"`
3. Create `rust/gravitea-core/src/crypto.rs` with **3** `#[pyfunction]` exports:
   - `encrypt_value(plaintext: &str, key: &[u8]) -> PyResult<String>` — nonce generation is internal via `OsRng`, NOT a fourth export
   - `decrypt_value(encrypted: &str, key: &[u8]) -> PyResult<String>`
   - `compute_blind_index(value: &str, hmac_key: &[u8]) -> PyResult<String>` — normalise NFC → `.to_lowercase()` → `.trim()` before HMAC
4. Add `mod crypto;` and three `#[pymodule_export]` lines to `rust/gravitea-core/src/lib.rs` following the existing declarative pattern
5. Write Rust-native tests in `crypto.rs` (`#[cfg(test)]`): roundtrip, nonce uniqueness (1000 encryptions), wrong-key rejection, key-length validation (16/31/33-byte keys → error), empty-string input guard, determinism of blind index
6. Run `cargo test` — all crypto tests pass

### Phase 2: Security Review (SECURITY)

**Risk**: HIGH (crypto bypass would silently corrupt PII)
**Depends on**: Phase 1 complete

Tasks:
1. Review `crypto.rs` for: constant-time operations, key material handling (zeroization on drop vs. scope), nonce reuse prevention (single-use OsRng per encrypt call)
2. Verify wire format: `base64(nonce[12] || ciphertext || tag[16])` — confirm `aes-gcm 0.10` appends 16-byte tag matching Python's `AESGCM.encrypt()` layout
3. Review blind index normalisation: confirm order is **NFC → lowercase → trim** (per FR-003); verify `unicode-normalization nfc()` produces identical output to Python's `unicodedata.normalize("NFC", ...)` for Argentine corpus test vectors (ñ, á, é, ü, CUIT)
4. Verify `GraviteaError::InvalidInput` is raised for keys with length ≠ 32 bytes (maps to `PyValueError`)
5. Sign off or request changes before Phase 3 proceeds

### Phase 3: Python Integration (QA)

**Risk**: MEDIUM (FFI boundary; cross-implementation correctness)
**Depends on**: Phase 2 sign-off

Tasks:
1. Modify `backend/apps/core/encryption/utils.py` — add `_USE_RUST` fallback dispatch (try/except ImportError pattern); None/empty guards in Python wrapper (not Rust)
2. Update `backend/gravitea_rust.pyi` with 3 function stubs: `encrypt_value(plaintext: str, key: bytes) -> str`, `decrypt_value(encrypted: str, key: bytes) -> str`, `compute_blind_index(value: str, hmac_key: bytes) -> str`
3. Write cross-implementation equivalence tests in `test_crypto_018.py`:
   - Python-encrypted → Rust-decrypted (20+ strings including ASCII, Spanish names, CUITs)
   - Rust-encrypted → Python-decrypted (same corpus)
   - Blind index parity: Python and Rust produce identical hex for same input
4. Write NFC normalisation parity test: same PII string in NFC and NFD forms must produce the same blind index from both Rust and Python paths
5. Write property-based tests (hypothesis): random string roundtrips including Argentine PII (ñ, á, é, ü, CUITs) — minimum 500 examples per FR-009
6. Write benchmark tests (`pytest-benchmark`): measure Rust vs Python speedup — target ≥5× (under 5 µs per operation); mark `@pytest.mark.slow`

### Phase 4: Docker Validation (LEAD)

**Risk**: LOW
**Depends on**: Phase 3 tests passing

Tasks:
1. Rebuild Docker image (`docker compose build`) — verify `gravitea_rust` module importable inside container
2. Run crypto integration tests inside container: `docker compose exec web python -m pytest backend/tests/rust_integration/test_crypto_018.py -p no:django --confcutdir=backend/tests/rust_integration -o "addopts=" --tb=short -q`

### Phase 5: Polish & Regression (LEAD)

**Risk**: LOW
**Depends on**: Phase 4 pass

Tasks:
1. Run full test suite — target 0 new failures: `scripts/run-tests-external.sh "backend/venv-wsl/bin/python -m pytest backend/tests/ --tb=short -q --no-header"`
2. Verify fallback: temporarily comment out the `try` import block in `utils.py` → confirm Python encryption works and all tests pass without Rust extension
3. Verify FR-010: in fallback mode, application startup emits exactly one `WARNING`-level log entry (`"gravitea_rust not available, using software fallback"` or similar); no warning when Rust loads successfully
4. Update `specs/018-rust-crypto/quickstart.md` with any build-time findings
5. Confirm: `cargo test` passes, Docker image builds, benchmark results documented in research.md

---

## Research Topics (resolved in research.md)

| ID | Topic | Status |
|----|-------|--------|
| R-001 | NFC normalisation parity: `unicode-normalization` vs Python `unicodedata` | ✅ Resolved — compatible, verify with test vectors |
| R-002 | `aes-gcm 0.10` audit status and wire format | ✅ Resolved — NCC Group audited, byte-identical to Python AESGCM |
| R-003 | Property-based test distributions for Argentine PII | ✅ Resolved — 6 input distributions defined |
| R-004 | Hex encoding case: `hex::encode` vs `hexdigest()` | ✅ Resolved — both lowercase, exact match |

## Crate Dependencies

| Crate | Version | Purpose |
|-------|---------|---------|
| `aes-gcm` | 0.10 | AES-256-GCM authenticated encryption |
| `hmac` | 0.12 | HMAC-SHA256 for blind index computation |
| `sha2` | 0.10 | SHA256 digest (used by hmac) |
| `rand` | 0.8 | CSPRNG (`OsRng`) for nonce generation |
| `hex` | 0.4 | Lowercase hex encoding for blind index output |
| `unicode-normalization` | 0.1 | NFC normalisation for blind index (R-001) |

## Testing Standards

| Category | Framework | Target |
|----------|-----------|--------|
| Rust-native | `cargo test` | ≥8 tests: roundtrip, nonce uniqueness (1000), wrong-key, key-length (3 bad lengths), empty-input guard, blind-index determinism |
| Cross-implementation | `pytest` | Rust↔Python encrypt/decrypt equivalence (20+ strings); blind index parity |
| NFC parity | `pytest` | Same PII in NFC and NFD forms → identical blind index |
| Property-based | `hypothesis` | ≥500 examples; Argentine PII distributions (R-003) |
| Benchmark | `pytest-benchmark` | ≥5× speedup (under 5 µs absolute); `@pytest.mark.slow` |
| Docker | container exec | `import gravitea_rust; gravitea_rust.encrypt_value(...)` works |
| Regression | `pytest` | Full suite 2200+ tests, 0 new failures |

## Constraints

1. SPEC-017 complete — `gravitea_rust` module exists and is importable
2. Byte-for-byte wire format compatibility — existing DB data decrypts without migration
3. `cryptography` library **retained** — WSAA/PKCS#7 operations in `apps/facturacion/` stay in Python
4. Python fallback mandatory — `_USE_RUST` dispatch pattern, no config required
5. No Django model changes, no migrations (FR-002: wire format unchanged)
6. None/empty guards in Python wrapper only (not Rust) — keeps Rust functions as pure-compute
7. Sequential-thinking MCP mandatory for RUST-PROGRAMMER and SECURITY agents
8. External test runner for all pytest: `scripts/run-tests-external.sh`
9. Split Python dispatch is intentional — `_USE_RUST` dispatch for `encrypt_value`/`decrypt_value` is added in Phase 3 (US1) while `compute_blind_index` dispatch is added in Phase 6 (US4); this allows US4 to be implemented independently without merging a partial function into `utils.py`. The two partial dispatches are safe because `_USE_RUST` is a single module-level flag applied to all three functions simultaneously.

## Success Criteria

| # | Criterion | Target |
|---|-----------|--------|
| 1 | `cargo test` crypto tests | ≥8 pass |
| 2 | Cross-implementation equivalence | Rust↔Python roundtrips pass for 20+ strings |
| 3 | Blind index parity | Rust and Python produce identical hex for same input including Spanish chars |
| 4 | NFC normalisation parity | NFC and NFD inputs produce same blind index |
| 5 | Property-based tests | ≥500 random inputs roundtrip without error |
| 6 | Performance benchmark | ≥5× speedup, under 5 µs per operation (absolute) |
| 7 | Existing DB data | Snapshot of real encrypted values decrypts via Rust path |
| 8 | Fallback mode | All tests pass with Rust extension removed; FR-010 warning emitted |
| 9 | Docker | Image builds; `encrypt_value` callable inside container |
| 10 | Type stub | `gravitea_rust.pyi` updated with 3 new signatures |
| 11 | Regression | Full suite 0 new failures |
