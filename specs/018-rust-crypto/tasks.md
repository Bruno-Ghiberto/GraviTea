# Tasks: Crypto Acceleration Layer

**Input**: Design documents from `/specs/018-rust-crypto/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, quickstart.md ✅

**Tests**: Included — spec explicitly requires cross-implementation equivalence tests,
property-based tests (FR-009, SC-007), and fallback verification (FR-006, FR-010).

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description with file path`

- **[P]**: Can run in parallel (different files / independent logic within same file)
- **[Story]**: Which user story this task serves (US1–US4)
- Exact file paths required in every task

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify SPEC-017 foundation, add crate deps, scaffold test file

- [x] T001 Verify SPEC-017 foundation: run `backend/venv-wsl/bin/python -c "import gravitea_rust; print(gravitea_rust.hello())"` and confirm output is `"Hello from Rust!"` — if this fails, stop and fix SPEC-017 before proceeding; then install test dependencies: `backend/venv-wsl/bin/pip install hypothesis pytest-benchmark`
- [x] T002 Add 6 crate dependencies to `[dependencies]` section of `rust/gravitea-core/Cargo.toml`: `aes-gcm = "0.10"`, `hmac = "0.12"`, `sha2 = "0.10"`, `rand = "0.8"`, `hex = "0.4"`, `unicode-normalization = "0.1"`
- [x] T003 [P] Create `backend/tests/rust_integration/test_crypto_018.py` with: module-level imports (`pytest`, `os`, `hmac`, `hashlib`, `unicodedata`), two constants (`TEST_KEY = os.urandom(32)` and `TEST_HMAC_KEY = os.urandom(32)`), and an empty `pass` body — file must be importable

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Wire crypto submodule into PyO3 module; verify crates compile

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Add `mod crypto;` declaration at the top of `rust/gravitea-core/src/lib.rs` and add three `#[pymodule_export]` lines inside the existing `mod gravitea_rust` block: `use super::crypto::encrypt_value;`, `use super::crypto::decrypt_value;`, `use super::crypto::compute_blind_index;` — follow the existing `use super::hello;` pattern exactly
- [x] T005 Create `rust/gravitea-core/src/crypto.rs` with: all necessary `use` imports (`aes_gcm`, `hmac`, `sha2`, `rand`, `hex`, `unicode_normalization`, `pyo3`), and three `#[pyfunction]` stubs that each return `Err(GraviteaError::CryptoError("not implemented".to_string()).into())` — module must compile
- [x] T006 Run `cargo check` from `rust/gravitea-core/` and confirm it exits 0 with all 6 new crates resolved; fix any dependency version conflicts before proceeding

**Checkpoint**: `cargo check` passes — user story implementation can now begin

---

## Phase 3: User Story 1 — Faster PII Read/Write (Priority: P1) 🎯 MVP

**Goal**: Rust AES-256-GCM encrypt_value and decrypt_value replace Python internals;
existing Python dispatch falls through to Rust; key validation enforced; Rust tests passing.

**Independent Test**: `backend/venv-wsl/bin/python -c "from gravitea_rust import encrypt_value, decrypt_value; import os; k=os.urandom(32); assert decrypt_value(encrypt_value('hello', k), k) == 'hello'; print('US1 OK')"` — must print `US1 OK` without importing Django.

- [x] T007 [US1] Write `#[cfg(test)]` module in `rust/gravitea-core/src/crypto.rs` with tests: `test_encrypt_decrypt_roundtrip` (encrypt then decrypt returns original plaintext), `test_nonce_uniqueness` (1000 encrypt calls of same plaintext produce 1000 distinct ciphertexts), `test_wrong_key_rejection` (decrypt with a different valid 32-byte key returns `Err` of `CryptoError` variant — NOT `InvalidInput`; assert on the error variant), `test_tag_mismatch_returns_crypto_error` (decrypt with correct key but last byte of blob flipped returns `CryptoError`, never partial plaintext)
- [x] T008 [US1] Write key-length tests in the `#[cfg(test)]` block of `rust/gravitea-core/src/crypto.rs`: `test_encrypt_short_key` (16-byte key → `InvalidInput` error, not `CryptoError`), `test_encrypt_off_by_one_key` (31-byte and 33-byte keys → `InvalidInput`), `test_decrypt_short_key` (16-byte key → `InvalidInput`); assert the correct `GraviteaError` variant for each case
- [x] T009 [US1] Implement `encrypt_value(plaintext: &str, key: &[u8]) -> PyResult<String>` in `rust/gravitea-core/src/crypto.rs`: validate `key.len() != 32` → `GraviteaError::InvalidInput`; generate 12-byte nonce via `rand::rngs::OsRng`; encrypt with `Aes256Gcm`; prepend nonce to ciphertext+tag; return `general_purpose::STANDARD.encode(nonce_bytes + ciphertext_with_tag)` as base64 string
- [x] T010 [US1] Implement `decrypt_value(encrypted: &str, key: &[u8]) -> PyResult<String>` in `rust/gravitea-core/src/crypto.rs`: validate key length; base64-decode input; split at byte 12 (nonce) and remainder (ciphertext+tag); decrypt with `Aes256Gcm::decrypt` — tag mismatch → `GraviteaError::CryptoError`; return UTF-8 plaintext string
- [x] T011 [US1] Add key-length validation to both functions in `rust/gravitea-core/src/crypto.rs`: `key.len() != 32` check at the top of each function body returning `Err(GraviteaError::InvalidInput("key must be exactly 32 bytes".to_string()).into())`
- [x] T012 [US1] Run `cargo test` from `rust/gravitea-core/` and confirm ≥7 crypto tests pass (T007: 4 tests, T008: 3 tests) — if any fail, fix before proceeding to Python integration
- [x] T013 [US1] Security review gate — verify `rust/gravitea-core/src/crypto.rs`: (a) key `&[u8]` is not cloned or retained beyond function scope; (b) `OsRng` called fresh inside each `encrypt_value` invocation, never reused across calls; (c) decryption failure (`CryptoError`) never returns partial plaintext; confirm and document findings inline as code comments
- [x] T014 [US1] Add `_USE_RUST` dispatch for `encrypt_value` and `decrypt_value` to `backend/apps/core/encryption/utils.py`: add `try: from gravitea_rust import encrypt_value as _rust_encrypt_value, decrypt_value as _rust_decrypt_value; _USE_RUST = True` / `except ImportError: _USE_RUST = False` block at module top; in each function body, add None/empty guard then `if _USE_RUST: return _rust_encrypt_value(value, get_encryption_key())` before existing Python implementation
- [x] T015 [P] [US1] Write benchmark tests `test_encrypt_benchmark` and `test_decrypt_benchmark` in `backend/tests/rust_integration/test_crypto_018.py` using `pytest-benchmark`; mark with `@pytest.mark.slow`; each benchmark runs 1000 iterations of a 50-char plaintext and records Rust vs Python timing

**Checkpoint**: `cargo test` ≥7 passing; Rust encrypt/decrypt importable and working from Python; Python fallback intact

---

## Phase 4: User Story 2 — Existing Encrypted Data Remains Accessible (Priority: P1)

**Goal**: Byte-for-byte wire format compatibility verified by cross-implementation tests;
existing DB data provably decryptable via Rust path.

**Independent Test**: Run `backend/venv-wsl/bin/python -m pytest backend/tests/rust_integration/test_crypto_018.py -k "compat or roundtrip or vector" -p no:django --confcutdir=backend/tests/rust_integration -o "addopts=" --tb=short -q` — all cross-compat tests pass without Django.

- [x] T016 [P] [US2] Write test `test_python_encrypted_rust_decrypted` in `backend/tests/rust_integration/test_crypto_018.py`: define a corpus of 20 Argentine PII strings (mix of CUIT numbers, Spanish names with accents, addresses); for each, encrypt with the Python path (`_USE_RUST=False` monkeypatch), then decrypt with `_rust_decrypt_value`; assert all 20 decrypted values match originals
- [x] T017 [P] [US2] Write test `test_rust_encrypted_python_decrypted` in `backend/tests/rust_integration/test_crypto_018.py`: for the same 20-string corpus, encrypt with `_rust_encrypt_value`, decrypt with the Python path (`_USE_RUST=False`); assert all 20 match
- [x] T018 [US2] Write fixed test vector test `test_wire_format_test_vector` in `backend/tests/rust_integration/test_crypto_018.py`: using Python's `cryptography.AESGCM`, encrypt `b"gravitea"` with `key=bytes(32)` and `nonce=bytes(12)` to produce a known blob; assert that `_rust_decrypt_value(blob_b64, bytes(32))` returns `"gravitea"` — this is the canonical wire format compatibility proof; also assert that the base64 blob contains only standard-alphabet characters `[A-Za-z0-9+/=]` and does NOT contain `-` or `_` (which would indicate URL-safe base64, incompatible with existing data)
- [x] T019 [US2] Write test `test_1000_sequential_roundtrips` in `backend/tests/rust_integration/test_crypto_018.py`: run 1000 encrypt→decrypt cycles on the string `"20123456789"` using the Rust path; assert every decrypted value equals `"20123456789"` (SC-001 acceptance scenario 3)
- [x] T020 [US2] Run `backend/venv-wsl/bin/python -m pytest backend/tests/rust_integration/test_crypto_018.py -p no:django --confcutdir=backend/tests/rust_integration -o "addopts=" --tb=short -q` and confirm T016–T019 all pass; document SC-002 and SC-007 as verified in `specs/018-rust-crypto/research.md`

**Checkpoint**: Cross-implementation equivalence proven; US1 + US2 both independently functional

---

## Phase 5: User Story 3 — Transparent Operation Without the Acceleration Layer (Priority: P2)

**Goal**: `_USE_RUST=False` path is fully functional; exactly one WARNING logged at startup
when fallback is active; all existing tests pass with Rust extension uninstalled.

**Independent Test**: `pip uninstall gravitea_rust -y; backend/venv-wsl/bin/python -m pytest backend/tests/ --tb=short -q --no-header 2>&1 | tail -5` — must show 0 new failures.

- [x] T021 [US3] Verify the `_USE_RUST=False` path in `backend/apps/core/encryption/utils.py` is complete: when `_USE_RUST=False`, `encrypt_value`, `decrypt_value`, and `compute_blind_index` all call only the original Python implementation; no new code branches introduced; existing Python body remains unchanged as the fallback
- [x] T022 [US3] Implement FR-010 in `backend/apps/core/encryption/utils.py`: broaden the exception clause from `except ImportError` to `except (ImportError, OSError)` — `OSError` covers edge case EC-6 (corrupted binary present on disk that fails to load); in this combined except block, set `_USE_RUST = False` and add `import logging; logging.getLogger(__name__).warning("gravitea_rust not available — using software fallback for PII encryption and blind indexing")`; no log call in the `try` path
- [x] T023 [US3] Write test `test_fallback_all_operations` in `backend/tests/rust_integration/test_crypto_018.py`: using `monkeypatch.setattr("backend.apps.core.encryption.utils._USE_RUST", False)`, verify `encrypt_value`, `decrypt_value`, and `compute_blind_index` all return correct results identical to those produced with `_USE_RUST=True`
- [x] T024 [US3] Write test `test_fr010_startup_warning` in `backend/tests/rust_integration/test_crypto_018.py`: to trigger the warning the module must be re-imported with `gravitea_rust` absent — use `sys.modules.pop("gravitea_rust", None)` to hide the Rust extension, then `importlib.reload(backend.apps.core.encryption.utils)` inside a `caplog` context; assert exactly one `WARNING`-level record with substring `"software fallback"` was emitted during the reload; restore `sys.modules["gravitea_rust"]` in a `finally` block; write a second test `test_fr010_no_warning_when_rust_loads` that confirms zero WARNING records when `gravitea_rust` is importable (no reload needed, check caplog on a fresh import); also write `test_fr010_oserror_triggers_fallback` that patches `builtins.__import__` to raise `OSError` for `"gravitea_rust"` and reloads the module, confirming the warning fires for a corrupted binary scenario (EC-6)

- [x] T039 [US3] Write test `test_null_empty_passthrough` in `backend/tests/rust_integration/test_crypto_018.py` covering FR-005: call `encrypt_value(None, key)` via the Python wrapper in `utils.py` and assert `None` is returned; call `encrypt_value("", key)` and assert `""` is returned; repeat for `decrypt_value(None, key)` → `None`, `decrypt_value("", key)` → `""`, and `compute_blind_index(None, key)` → `None`, `compute_blind_index("", key)` → `""`; run with both `_USE_RUST=True` and `_USE_RUST=False` (monkeypatched) to confirm the guard lives in the Python wrapper, not in Rust

**Checkpoint**: Fallback path complete; FR-005, FR-006, FR-007, FR-010 all implemented and tested

---

## Phase 6: User Story 4 — Blind Index Searches Return Consistent Results (Priority: P2)

**Goal**: Rust `compute_blind_index` implements NFC→lowercase→trim→HMAC-SHA256→hex;
output is byte-identical to Python for any Argentine PII input including NFD-encoded variants.

**Independent Test**: `backend/venv-wsl/bin/python -m pytest backend/tests/rust_integration/test_crypto_018.py -k "blind_index or hypothesis" -p no:django --confcutdir=backend/tests/rust_integration -o "addopts=" --tb=short -q` — all blind index tests pass.

- [x] T025 [US4] Write `#[cfg(test)]` tests for `compute_blind_index` in `rust/gravitea-core/src/crypto.rs`: `test_blind_index_case_insensitive` (`"SMITH"` and `"smith"` produce identical output), `test_blind_index_whitespace_strip` (`"  smith  "` and `"smith"` produce identical output), `test_blind_index_nfc_normalisation` (NFD `"n\u{0303}"` and NFC `"ñ"` produce identical output — this validates the NFC step), `test_blind_index_cuit_passthrough` (`"20123456789"` is unchanged by NFC/lower/trim and produces a valid 64-char hex), `test_blind_index_wrong_key_length` (16-byte key → `InvalidInput` error, not `CryptoError`)
- [x] T026 [US4] Implement `compute_blind_index(value: &str, hmac_key: &[u8]) -> PyResult<String>` in `rust/gravitea-core/src/crypto.rs`: (1) validate `hmac_key.len() != 32` → `GraviteaError::InvalidInput`; (2) apply NFC normalisation via `value.nfc().collect::<String>()`; (3) `.to_lowercase()`; (4) `.trim().to_string()`; (5) compute `Hmac::<Sha256>::new_from_slice(hmac_key)` → `mac.update(normalised.as_bytes())`; (6) return `hex::encode(mac.finalize().into_bytes())` as 64-char lowercase string
- [x] T040 [US4] Add `proptest = "1"` to `[dev-dependencies]` in `rust/gravitea-core/Cargo.toml`; write Rust property-based test `test_blind_index_idempotent` using `proptest::prelude::*`: for any ASCII alphanumeric string up to 64 chars, assert that calling `compute_blind_index` twice with the same key returns the same output (determinism property); write `test_blind_index_normalisation_idempotent`: for any such string, assert result equals result of pre-applying `.to_uppercase()` (case normalisation is applied inside the function)
- [x] T027 [US4] Run `cargo test` and confirm ≥13 total crypto tests pass (≥7 from US1 + 5 from US4 + 2 Rust proptests from T040); fix any failures before proceeding
- [x] T028 [US4] Add `_USE_RUST` dispatch for `compute_blind_index` to `backend/apps/core/encryption/utils.py`: add `compute_blind_index as _rust_compute_blind_index` to the existing `try` import block; in `compute_blind_index()`, add `if _USE_RUST: return _rust_compute_blind_index(value, get_hmac_key())` after the None guard
- [x] T029 [P] [US4] Write test `test_blind_index_parity_50_values` in `backend/tests/rust_integration/test_crypto_018.py`: define a 50-value corpus (10 CUITs, 10 Spanish names with accents, 10 mixed-case, 10 leading/trailing whitespace variants, 10 NFD-encoded names); for each, assert `_rust_compute_blind_index(v, TEST_HMAC_KEY) == python_compute_blind_index(v)` (SC-003)
- [x] T030 [P] [US4] Write test `test_blind_index_nfc_equivalence` in `backend/tests/rust_integration/test_crypto_018.py`: for 10 strings containing ñ/á/é/ü in NFC form, compute NFD equivalent via `unicodedata.normalize("NFD", s)`, then assert `_rust_compute_blind_index(nfc_form, k) == _rust_compute_blind_index(nfd_form, k)` and both equal the Python result
- [x] T031 [US4] Write property-based test `test_hypothesis_blind_index_parity` in `backend/tests/rust_integration/test_crypto_018.py` using `hypothesis`: mark `@settings(max_examples=500)`; strategy combines Spanish names, padded names, NFD variants, and CUIT strings (R-003 distributions); for each generated value, assert Rust and Python produce the same blind index hex
- [x] T032 [US4] Run full `test_crypto_018.py` test suite (T016–T031 tests) and confirm all pass

**Checkpoint**: All 4 user stories fully implemented and independently verifiable; T039 (null/empty) and T040 (Rust proptest) complete the coverage of FR-005 and property-based correctness

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Type stubs, Docker build, regression, benchmarks, documentation

- [x] T033 [P] Update `backend/gravitea_rust.pyi` with 3 new function signatures: `def encrypt_value(plaintext: str, key: bytes) -> str: ...`, `def decrypt_value(encrypted: str, key: bytes) -> str: ...`, `def compute_blind_index(value: str, hmac_key: bytes) -> str: ...`
- [x] T034 [P] Rebuild Docker image: run `docker compose build web`; then run `docker compose run --rm web python -c "import gravitea_rust; k=b'0'*32; print(gravitea_rust.decrypt_value(gravitea_rust.encrypt_value('test', k), k))"` — must print `test` (SC-005)
- [x] T035 Run crypto integration tests inside Docker container: `docker compose exec web python -m pytest backend/tests/rust_integration/test_crypto_018.py -p no:django --confcutdir=backend/tests/rust_integration -o "addopts=" --tb=short -q`; confirm all tests pass in container environment
- [x] T036 Run full test suite regression via `scripts/run-tests-external.sh "backend/venv-wsl/bin/python -m pytest backend/tests/ --tb=short -q --no-header"`; read `.summary` file and confirm 0 new failures vs SPEC-017 baseline (SC-004, SC-006)
- [x] T037 [P] Run benchmark tests: `backend/venv-wsl/bin/python -m pytest backend/tests/rust_integration/test_crypto_018.py -m slow -p no:django --confcutdir=backend/tests/rust_integration -o "addopts=" --tb=short -q`; document measured Rust/Python speedup ratio in `specs/018-rust-crypto/research.md` under a new "Benchmark Results" section (target: ≥5× speedup, SC-001)
- [x] T038 [P] Update `specs/018-rust-crypto/quickstart.md` with actual build output examples (maturin develop output, cargo test summary), confirmed benchmark figures, and any platform-specific notes discovered during Docker validation

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (T001–T003)      → No dependencies
Phase 2 (T004–T006)      → Requires T001 (SPEC-017 verified), T002 (deps added)
Phase 3 (T007–T015)      → Requires Phase 2 complete (cargo check passes)
                            TDD order within phase: T007+T008 (tests) → T009+T010+T011 (impl) → T012+
Phase 4 (T016–T020)      → Requires T012 (cargo test passes) + T014 (Python dispatch added)
Phase 5 (T021–T024,T039) → Requires T014 (utils.py dispatch) — independent of Phase 4
                            T039 (null/empty) requires T021 (fallback path verified)
Phase 6 (T025–T032,T040) → Requires T006 (cargo check) — independent of Phases 4 & 5
                            TDD order within phase: T025 (tests) → T026 (impl) → T040 (proptest) → T027+
Phase 7 (T033–T038)      → Requires all Phase 3–6 tasks complete
```

### User Story Dependencies

- **US1 (P1)**: Starts after Phase 2 (Foundational) — no dependency on US2/US3/US4
- **US2 (P1)**: Starts after T012 (cargo test) + T014 (Python dispatch) — no dependency on US3/US4
- **US3 (P2)**: Starts after T014 (utils.py dispatch written) — no dependency on US2/US4; T039 (null/empty) adds to this story
- **US4 (P2)**: Starts after T006 (cargo check) — no dependency on US1/US2/US3 (separate function)

### Within Each User Story (TDD order — §X constitution)

```
Rust tests written → Rust implementation → cargo test pass → Python dispatch → Python tests
```

### Parallel Opportunities

- T003 (test file scaffold) with T004–T005 (Rust module wiring)
- T007 + T008 (roundtrip/nonce/wrong-key tests and key-length tests) — distinct test functions (write in parallel)
- T009 + T010 (encrypt_value and decrypt_value implementations) — different function bodies (implement in parallel after tests)
- T016 + T017 (python-encrypted-rust-decrypted and rust-encrypted-python-decrypted) — independent
- T025 + T007/T008 combo approach: T025 (blind index tests) can be written in parallel with T007+T008 since all are test authoring
- T029 + T030 (blind index parity and NFC equivalence tests) — independent test functions
- T033 (type stub) with T034 (Docker build) with T037 (benchmark) with T038 (quickstart) — fully independent

---

## Parallel Execution Examples

### Phase 3 (US1): Tests then Implementation (TDD)

```
Sequential: T007 (roundtrip+nonce+wrong-key tests) → T008 (key-length tests)
→ Parallel A: T009 — encrypt_value implementation
→ Parallel B: T010 — decrypt_value implementation
→ Sequential: T011 (key-length validation in both) → T012 cargo test → T013 security review → T014 Python dispatch
```

### Phase 4 (US2): Cross-Compat Tests in Parallel

```
Parallel A: T016 — test_python_encrypted_rust_decrypted
Parallel B: T017 — test_rust_encrypted_python_decrypted
→ Sequential: T018 (fixed test vector), T019 (1000 roundtrips)
```

### Phase 6 (US4): Tests then Implementation (TDD)

```
Sequential: T025 (Rust unit tests) → T026 (compute_blind_index implementation) → T040 (Rust proptest)
→ Sequential: T027 cargo test → T028 Python dispatch
→ Parallel A: T029 — test_blind_index_parity_50_values
→ Parallel B: T030 — test_blind_index_nfc_equivalence
→ Sequential: T031 (hypothesis, requires both distributions designed) → T032
```

### Phase 7 (Polish): All in Parallel

```
Parallel A: T033 — type stub update
Parallel B: T034 — Docker rebuild
Parallel C: T037 — benchmark tests
Parallel D: T038 — quickstart update
→ Sequential: T035 (Docker test, needs T034) → T036 (full regression)
```

---

## Implementation Strategy

### MVP First (US1 + US2 Only — both P1)

1. Complete Phase 1: Setup (T001–T003)
2. Complete Phase 2: Foundational (T004–T006)
3. Complete Phase 3: US1 — Performance (T007–T015)
4. **VALIDATE**: `python -c "from gravitea_rust import encrypt_value, decrypt_value; ..."` — Rust path live
5. Complete Phase 4: US2 — Compatibility (T016–T020)
6. **VALIDATE**: Cross-compat tests pass — existing DB data safe
7. **STOP** — production-deployable at this point (US3/US4 are P2)

### Incremental Delivery

1. Setup + Foundational → compile verified
2. US1 → Rust encrypt/decrypt live → **Demo: benchmark showing ≥5× speedup**
3. US2 → Cross-compat proven → **Deploy: existing data remains accessible**
4. US3 → Fallback verified → **CI/CD: developers without Rust unblocked**
5. US4 → Blind index consistent → **Complete: search parity guaranteed**
6. Polish → Docker + regression → **Release**

### Parallel Team Strategy

With multiple developers (matching instruction-plan.md team):

```
RUST-PROGRAMMER:  Phase 2 → Phase 3 (T007–T013) → Phase 6 (T025–T027, T040)
QA:           Phase 3 (T015, benchmarks) → Phase 4 (T016–T020) → Phase 6 (T029–T032)
SECURITY:     Phase 3 gate (T013 review) → Phase 5 (T021–T024, T039)
LEAD:         Phase 7 (T033–T038) + orchestration
```

---

## Notes

- **[P]** tasks operate on different logical units (separate functions, independent test cases) — parallelizable within their phase
- **[Story]** label maps each task to the user story it serves for traceability
- **TDD enforced (§X)**: Test tasks (T007, T008, T025) precede implementation tasks (T009, T010, T011, T026) within each phase
- `cargo test` is the gate between Rust implementation and Python integration (T012, T027)
- The security review at T013 is a required gate before Python dispatch (T014)
- `hypothesis` and `pytest-benchmark` are installed in T001 (setup step); targets: T031 (hypothesis), T015/T037 (pytest-benchmark)
- `proptest` for Rust property tests added in T040 (dev-dependency in Cargo.toml)
- All pytest runs use external runner for agents: `scripts/run-tests-external.sh`
- FR-005 null/empty coverage lives in the Python wrapper (utils.py), not in Rust — verified by T039
- FR-010 (startup warning) test uses `importlib.reload` + `sys.modules` removal to retrigger the `except` clause — NOT monkeypatching `_USE_RUST` post-import
- Commit after each user story checkpoint (T015, T020, T039, T032, T038)
