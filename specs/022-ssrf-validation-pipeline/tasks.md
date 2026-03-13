# Tasks: Rust SSRF Validation Pipeline

**Input**: Design documents from `/specs/022-ssrf-validation-pipeline/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, quickstart.md

**Tests**: Included — spec mandates TDD (SC-001 through SC-010), constitution Principle X requires test-first. ~65 integration tests + >=30 Rust-native tests.

**Organization**: Tasks grouped by user story. US1 and US2 are co-P1 and share all Rust implementation — combined into one phase for implementation, with story-specific test tasks labeled individually.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1=Static Validation, US2=DNS Post-Check, US3=Performance, US4=Fallback
- Exact file paths included in all task descriptions

---

## Phase 1: Setup (Cargo + Corpus)

**Purpose**: Project scaffolding and adversarial test corpus extraction

- [X] T001 Add `url = "2.5"` dependency to `rust/gravitea-core/Cargo.toml`
- [X] T002 [P] Add `SecurityError(String)` variant to `rust/gravitea-core/src/errors.rs` with `PyRuntimeError` mapping
- [X] T003 [P] Add `mod security;` declaration to `rust/gravitea-core/src/lib.rs`
- [X] T004 Create scaffold `rust/gravitea-core/src/security.rs` with module doc, imports (`url`, `regex`, `LazyLock`, `IpAddr`, `Ipv4Addr`, `Ipv6Addr`), and empty function signatures
- [X] T005 Extract adversarial URL corpus from `backend/tests/constants.py` (SSRF_* constants) and `backend/tests/security/test_ssrf.py` (inline URLs) — run each through Python `is_safe_url()` to capture expected boolean — produce `ADVERSARIAL_CORPUS` list (~80 tuples) as test data constant in `backend/tests/rust_integration/test_security_022.py`
- [X] T006 Add 14 additional adversarial URLs to corpus (decimal private, hex private, octal, mixed octal, shortened private, 3-part shortened, IPv4-mapped v6 private, credential injection, null byte host, sslip.io, xip.io, public IP explicit, long URL, double-encoded) with Python-verified expected outputs
- [X] T007 Verify `cargo check` passes with empty `security.rs` scaffold in `rust/gravitea-core/`

**Checkpoint**: Cargo builds, corpus captured, scaffold in place. Phase 2 can begin.

---

## Phase 2: Foundational — Rust Implementation

**Purpose**: Implement all 6 Rust functions (2 exported, 4 internal) that serve US1+US2. MUST complete before any Python integration.

**CRITICAL**: This is security-critical code. All 5 IP formats, 10 CIDR ranges, and 9 hostname patterns must be exactly correct.

### Internal Functions

- [X] T008 Implement `parse_ip_flexible()` strategy 1 (standard IP parsing via `IpAddr::from_str` + bracket stripping for IPv6) in `rust/gravitea-core/src/security.rs`
- [X] T009 Implement `parse_ip_flexible()` strategy 2 (decimal integer: `hostname.parse::<u32>()` → `Ipv4Addr::from()`) in `rust/gravitea-core/src/security.rs`
- [X] T010 Implement `parse_ip_flexible()` strategy 3 (hexadecimal: strip `0x`/`0X` → `u32::from_str_radix(_, 16)` → `Ipv4Addr::from()`) in `rust/gravitea-core/src/security.rs`
- [X] T011 Implement `parse_ip_flexible()` strategy 4 (octal: split on `.`, detect leading-zero → `u8::from_str_radix(_, 8)`, else decimal, pad to 4, validate 0-255) in `rust/gravitea-core/src/security.rs`
- [X] T012 Implement `parse_ip_flexible()` strategy 5 (shortened: 2-part `a.b`→`a.0.0.b`, 3-part `a.b.c`→`a.b.0.c`, then parse as standard) in `rust/gravitea-core/src/security.rs`
- [X] T013 Implement `is_private_ip()` with 10 CIDR ranges (IPv4: 10/8, 172.16/12, 192.168/16, 127/8, 169.254/16, 0/8; IPv6: ::1/128, fc00::/7, fe80::/10, ::ffff:0:0/96) as compiled prefix checks in `rust/gravitea-core/src/security.rs`
- [X] T014 [P] Implement `is_metadata_ip()` checking `169.254.169.254` and `169.254.170.2` in `rust/gravitea-core/src/security.rs`
- [X] T015 Implement `is_suspicious_hostname()` with 9 `LazyLock<Regex>` patterns (nip.io, xip.io, sslip.io, localtest.me, embedded 127.0.0.1, 169.254, 192.168, 10.x, 172.16-31) + null byte check (`\x00`/`%00`) + `"localhost"` substring check + IPv6 prefix check (`fd`/`fc`/`fe80` + remaining alphanumeric) in `rust/gravitea-core/src/security.rs`
- [X] T016 Implement `extract_hostname_fallback()` for URLs the `url` crate rejects — strip scheme, detect credentials (`@`), extract hostname until `:`/`/`/`?`/`#` in `rust/gravitea-core/src/security.rs`

### Exported PyO3 Functions

- [X] T017 Implement `validate_url_safety(url: &str) -> PyResult<(bool, String)>` — empty/None check, `url::Url::parse()` with fallback to `extract_hostname_fallback()`, scheme check, credential check, blocked hostname set check (FR-006: `localhost`, `metadata.google.internal`, `metadata.gcp.internal` case-insensitive exact match), IP parsing → private/metadata check, suspicious hostname regex check (FR-007) — in `rust/gravitea-core/src/security.rs`
- [X] T018 Implement `check_resolved_ip(ip_str: &str) -> PyResult<bool>` — parse IP string, check `is_private_ip()` + `is_metadata_ip()` — in `rust/gravitea-core/src/security.rs`
- [X] T019 Add 2 `#[pymodule_export]` entries for `validate_url_safety` and `check_resolved_ip` in `rust/gravitea-core/src/lib.rs` pymodule block

### Rust-Native Tests

- [X] T020 Write >=10 Rust `#[test]` tests for `parse_ip_flexible()` covering all 5 formats (standard, decimal, hex, octal, shortened) with private and public IPs in `rust/gravitea-core/src/security.rs`
- [X] T021 [P] Write >=10 Rust `#[test]` tests for `is_private_ip()` covering all 10 CIDR ranges with boundary IPs (first/last in each range) in `rust/gravitea-core/src/security.rs`
- [X] T022 [P] Write >=5 Rust `#[test]` tests for `is_suspicious_hostname()` covering all 9 patterns + null byte + localhost + IPv6 prefix in `rust/gravitea-core/src/security.rs`
- [X] T023 [P] Write >=5 Rust `#[test]` tests for `validate_url_safety()` covering empty input, bad scheme, credentials, safe URL, URL needing DNS in `rust/gravitea-core/src/security.rs`
- [X] T024 Run `cargo test` in `rust/gravitea-core/` — all >=30 tests pass

**Checkpoint**: All Rust functions implemented and unit-tested. Security review can begin.

---

## Phase 3: Security Review (Sequential Gate)

**Purpose**: SSRF bypass analysis — no integration until sign-off

**CRITICAL**: This phase BLOCKS Phase 4. Security code must be reviewed before production integration.

- [X] T025 Review `rust/gravitea-core/src/security.rs` for SSRF bypass vectors — verify no input can bypass static checks
- [X] T026 Test `url` crate vs Python `urlparse` divergences: `http://evil.com@safe.com/`, `http://[::ffff:127.0.0.1]/`, `http://0x7f000001/`, `http://` (empty host) — verify fallback handles all
- [X] T027 Verify all 5 IP format strategies produce identical results to Python `_parse_ip()` on boundary inputs (e.g., `0400.0.0.1` octal overflow, `08.0.0.1` invalid octal digit, `4294967295` max decimal, `0xFFFFFFFF` max hex)
- [X] T028 Verify all 10 CIDR ranges with first and last IP in each range — confirm `is_private_ip()` catches boundaries correctly
- [X] T029 Verify all 9 suspicious hostname patterns with positive match + negative match (non-matching input) — confirm `is_suspicious_hostname()` has no false positives/negatives
- [X] T030 Security sign-off on `security.rs` — or request changes and loop back to Phase 2

**Checkpoint**: Security reviewed and approved. Python integration can begin.

---

## Phase 4: User Story 1+2 — Static + DNS Validation Parity (Priority: co-P1)

**Goal**: Rust-accelerated URL validation produces identical boolean results to Python for all adversarial URLs (US1), and DNS post-check correctly blocks rebinding attacks (US2)

**Independent Test**: Run parametrized parity test over ~80 adversarial URLs through both Rust and Python paths — identical output for every input. Mock DNS to return private IPs and verify blocking.

### Python Integration

- [X] T031 [US1] Create `backend/apps/core/security/ssrf_engine.py` — Rust dispatcher with `_USE_RUST` flag, `is_safe_url()` orchestrating `validate_url_safety` → `_resolve_hostname` → `check_resolved_ip`, Python fallback path
- [X] T032 [US1] Modify `backend/apps/core/security/url_validator.py` — change `URLValidator.is_safe()` to delegate to `ssrf_engine.is_safe_url()` via lazy import
- [X] T033 [P] [US1] Add 2 function stubs to `backend/gravitea_rust.pyi` — `validate_url_safety(url: str) -> tuple[bool, str]` and `check_resolved_ip(ip_str: str) -> bool` with docstrings
- [X] T034 Build Rust wheel: `VIRTUAL_ENV=$(pwd)/backend/venv-wsl maturin develop --manifest-path rust/gravitea-core/Cargo.toml --release`

### US1 Tests — Static Validation Parity

- [X] T035 [US1] Create parametrized parity test in `backend/tests/rust_integration/test_security_022.py` — `@pytest.mark.parametrize("url,expected", ADVERSARIAL_CORPUS)` comparing Rust vs Python on ~80 URLs (SC-001)
- [X] T036 [P] [US1] Create IP format parity tests (5 formats x 3 variations: private, public, edge) in `backend/tests/rust_integration/test_security_022.py` (SC-003)
- [X] T037 [P] [US1] Create CIDR range parity tests (10 ranges x boundary IPs) in `backend/tests/rust_integration/test_security_022.py` (SC-004)
- [X] T038 [P] [US1] Create suspicious hostname parity tests (9 patterns x positive/negative match) in `backend/tests/rust_integration/test_security_022.py` (SC-005)
- [X] T039 [US1] Create scheme/credential/metadata check tests (allowed/blocked schemes, credential-embedded URLs, 2 metadata IPs) in `backend/tests/rust_integration/test_security_022.py` (SC-006)

### US2 Tests — DNS Post-Check

- [X] T040 [US2] Create DNS integration tests with mocked `_resolve_hostname` returning private IP, public IP, and None (failure=allow) in `backend/tests/rust_integration/test_security_022.py`
- [X] T041 [US2] Create two-phase flow tests: `validate_url_safety()` returns hostname → `check_resolved_ip()` validates resolved IP — in `backend/tests/rust_integration/test_security_022.py`

### Existing Test Regression

- [X] T042 [US1] Run existing `backend/tests/security/test_ssrf.py` (SEC-SSRF-001 through SEC-SSRF-006) — must pass unmodified with 0 failures (SC-010)

**Checkpoint**: US1 and US2 fully functional. All static validation produces identical results to Python. DNS post-check blocks rebinding attacks. Existing tests unchanged and passing.

---

## Phase 5: User Story 3 — Accelerated Performance (Priority: P2)

**Goal**: CPU-bound validation completes >=3x faster than Python implementation

**Independent Test**: Benchmark both implementations against adversarial corpus, measure CPU-bound time only (DNS excluded)

- [X] T043 [US3] Create benchmark test for `validate_url_safety()` — 200 adversarial URLs, compare Rust vs Python CPU time in `backend/tests/rust_integration/test_security_022.py`
- [X] T044 [P] [US3] Create benchmark test for `check_resolved_ip()` — 100 IPs, compare Rust vs Python in `backend/tests/rust_integration/test_security_022.py`
- [X] T045 [US3] Create combined flow benchmark — full `is_safe_url()` through dispatcher with mocked DNS, compare Rust path vs Python fallback path in `backend/tests/rust_integration/test_security_022.py`
- [X] T046 [US3] Validate >=3x speedup on CPU-bound portions (SC-002) — document actual speedup in test output. NOTE: SPEC-021 achieved ~2.6x on sanitize_endpoint_label due to PyO3 FFI overhead on sub-microsecond ops. If combined flow <3x, verify CPU-bound-only measurement (excluding FFI round-trip) meets SC-002, and document the FFI overhead delta.

**Checkpoint**: Performance validated. CPU-bound portions >=3x faster than Python.

---

## Phase 6: User Story 4 — Graceful Fallback (Priority: P3)

**Goal**: When Rust extension is unavailable, system falls back to Python with correct output and startup warning

**Independent Test**: Simulate `ImportError` for `gravitea_rust`, verify `is_safe_url()` still works via Python path

- [X] T047 [US4] Create fallback test — simulate `ImportError` for `gravitea_rust`, verify `ssrf_engine.is_safe_url()` uses Python fallback and produces correct results in `backend/tests/rust_integration/test_security_022.py`
- [X] T048 [P] [US4] Create fallback toggle test — verify `_USE_RUST` flag controls dispatch path in `backend/tests/rust_integration/test_security_022.py`
- [X] T049 [US4] Create startup warning test — verify `logger.warning()` is called when Rust extension unavailable in `backend/tests/rust_integration/test_security_022.py`

**Checkpoint**: Fallback mechanism verified. Security protection continues when Rust unavailable.

---

## Phase 7: Polish — Docker & Regression

**Purpose**: Container validation and full regression across all tests

- [X] T050 Build Docker image: `docker compose build web`
- [X] T051 Verify Rust security functions available in container: `docker compose run --rm --entrypoint python web -c "from gravitea_rust import validate_url_safety, check_resolved_ip; print('OK')"` (SC-008)
- [X] T052 Run existing security tests in container: `docker compose run --rm --entrypoint python web -m pytest tests/security/test_ssrf.py --tb=short -q --override-ini='addopts='`
- [X] T053 Run SPEC-022 integration tests in container: `docker compose run --rm --entrypoint python web -m pytest tests/rust_integration/test_security_022.py --tb=short -q --override-ini='addopts='`
- [X] T054 Run full regression in container — 0 failures across all tests (SC-009): `docker compose run --rm --entrypoint python web -m pytest tests/ --tb=short -q --override-ini='addopts='`
- [X] T055 Update `specs/022-ssrf-validation-pipeline/quickstart.md` with final benchmark results and any command adjustments

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories
- **Security Review (Phase 3)**: Depends on Phase 2 — BLOCKS Python integration
- **US1+US2 (Phase 4)**: Depends on Phase 3 security sign-off
- **US3 (Phase 5)**: Depends on Phase 4 (needs working integration to benchmark)
- **US4 (Phase 6)**: Depends on Phase 4 (needs dispatcher to test fallback)
- **Polish (Phase 7)**: Depends on Phases 4, 5, 6

### User Story Dependencies

- **US1+US2 (co-P1)**: Combined because they share all Rust functions. Cannot be implemented independently — same code serves both.
- **US3 (P2)**: Depends on US1+US2 being functional (benchmarks require working code)
- **US4 (P3)**: Depends on US1+US2 being functional (fallback requires dispatcher)
- **US3 and US4 are parallelizable** with each other after Phase 4 completes

### Within Phases

- **Phase 1**: T001-T003 parallel (different files), T004 depends on T003, T005-T006 parallel with T001-T004, T007 depends on T001-T004
- **Phase 2**: T008-T012 sequential (same function, strategies must be ordered), T013-T016 parallel (different functions), T017 depends on T008-T016, T018 depends on T017, T019 depends on T017, T020-T023 parallel with each other after T017
- **Phase 3**: Strictly sequential — security gate
- **Phase 4**: T031-T034 sequential (integration setup), T035-T039 parallel (different test categories in same file), T040-T041 parallel, T042 after T031-T034
- **Phase 5**: T043-T044 parallel, T045 after T043, T046 after T045
- **Phase 6**: T047-T049 parallel (independent test scenarios)
- **Phase 7**: Strictly sequential — container build → validate → regress

### Parallel Opportunities

```text
Phase 1:  T001 ─┬── T004 → T007
          T002 ─┘
          T003 ─┘
          T005 ─── T006 (parallel with T001-T004)

Phase 2:  T008 → T009 → T010 → T011 → T012 (sequential: parse_ip strategies)
          T013 ─┬── T017 → T018 → T024
          T014 ─┤         T019 (parallel with T018)
          T015 ─┤         T020 ─┬── (parallel test groups)
          T016 ─┘         T021 ─┤
                          T022 ─┤
                          T023 ─┘

Phase 4:  T031 → T032 → T034 (sequential setup)
          T033 (parallel with T031-T032, different file)
          T035 ─┬── (parallel test categories)
          T036 ─┤
          T037 ─┤
          T038 ─┤
          T039 ─┘
          T040 ─── T041 (parallel DNS tests)

Phase 5+6: Can run in parallel after Phase 4
```

---

## Parallel Example: Phase 4 (US1+US2)

```bash
# Step 1: Integration setup (sequential — same files)
Task: T031 "Create ssrf_engine.py dispatcher"
Task: T032 "Modify url_validator.py delegation"
Task: T033 "Add .pyi stubs" (parallel with T031-T032)
Task: T034 "Build Rust wheel"

# Step 2: Test categories (parallel — different test classes in same file)
Task: T035 "Parity test ~80 URLs"
Task: T036 "IP format tests"
Task: T037 "CIDR range tests"
Task: T038 "Hostname pattern tests"
Task: T039 "Scheme/credential/metadata tests"

# Step 3: DNS tests (parallel)
Task: T040 "DNS integration tests"
Task: T041 "Two-phase flow tests"

# Step 4: Regression
Task: T042 "Existing test_ssrf.py regression"
```

---

## Implementation Strategy

### MVP First (US1+US2 Only)

1. Complete Phase 1: Setup (T001-T007)
2. Complete Phase 2: Rust Implementation (T008-T024)
3. Complete Phase 3: Security Review (T025-T030)
4. Complete Phase 4: US1+US2 Integration + Tests (T031-T042)
5. **STOP and VALIDATE**: All adversarial URLs produce identical results, DNS post-check works, existing tests pass unmodified

### Incremental Delivery

1. Setup + Foundational + Security Review → Rust core ready
2. US1+US2 Integration → Test parity → **MVP delivered** (security-correct)
3. US3 Benchmarks → Validate >=3x speedup → Performance confirmed
4. US4 Fallback → Validate graceful degradation → Resilience confirmed
5. Docker + Regression → Container validated → Production ready

### Team Strategy

| Agent | Phase Assignments |
|-------|------------------|
| LEAD | Phase 1 (Setup), Phase 3 (Review coordination), Phase 7 (Docker) |
| RUST-EXPERT | Phase 2 (all Rust implementation) |
| SECURITY | Phase 3 (security review + sign-off) |
| QA | Phase 1 (corpus extraction T005-T006), Phase 4-6 (all Python tests) |

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] labels: US1=Static Validation, US2=DNS Post-Check, US3=Performance, US4=Fallback
- US1+US2 combined in Phase 4 because they share all Rust functions — cannot be implemented independently
- Phase 3 (Security Review) is a hard gate — no Python integration until sign-off
- All tests in single file `test_security_022.py` but organized by test class per story
- Existing `test_ssrf.py` MUST NOT be modified (SC-010)
- Test location: `tests/rust_integration/` not `tests/security/` — avoids conftest RLS conflicts
- GIL NOT released — sub-millisecond ops, FFI overhead dominates
