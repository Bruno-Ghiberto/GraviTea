# Implementation Plan: Rust SSRF Validation Pipeline

**Branch**: `022-ssrf-validation-pipeline` | **Date**: 2026-02-27 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/022-ssrf-validation-pipeline/spec.md`

## Summary

Replace CPU-bound SSRF URL validation in `url_validator.py:is_safe_url()` with compiled Rust via PyO3. The Rust module (`security.rs`) handles URL parsing, 5 IP encoding formats, 10 CIDR range checks, 9 suspicious hostname regex patterns, and cloud metadata IP detection. DNS resolution stays in Python (`socket.getaddrinfo`). A two-function FFI boundary (`validate_url_safety` + `check_resolved_ip`) cleanly separates CPU-bound static checks from I/O-bound DNS. A Python dispatcher (`ssrf_engine.py`) orchestrates the Rust/Python split with automatic fallback to the existing Python implementation.

## Technical Context

**Language/Version**: Rust 1.93.1 (PyO3 0.28, Maturin 1.12.4) + Python 3.14.3 (Django 5.2.x)
**Primary Dependencies**: `url 2.5` (WHATWG URL parsing), `regex 1.10` (already present from SPEC-021), `pyo3 0.28` (FFI)
**Storage**: N/A — pure validation functions, no persistence
**Testing**: `cargo test` (Rust-native) + `pytest` (Python integration, parity, benchmarks)
**Target Platform**: Linux (WSL2 dev, Docker prod — glibc 2.36+)
**Project Type**: Library — 2 PyO3 exported functions consumed by Python dispatcher
**Performance Goals**: >=3x speedup on CPU-bound portions vs Python (DNS excluded from measurement)
**Constraints**: Sub-millisecond per validation, GIL NOT released (FFI overhead dominates), byte-for-byte identical boolean output vs Python
**Scale/Scope**: ~80 adversarial URL corpus, ~65 integration tests, 2 exported functions, 5 internal functions, 1 Python dispatcher, 1 integration point change

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Status | Notes |
|---|-----------|--------|-------|
| I | Ironclad Data Model | N/A | No data model changes |
| II | Multi-Tenant Isolation | N/A | URL validation is tenant-agnostic |
| III | Modular Django Architecture | PASS | `ssrf_engine.py` in `apps/core/security/` — existing module, follows SPEC-021 dispatcher pattern |
| IV | Application-Level Encryption | N/A | No encryption changes |
| V | Secure Authentication | N/A | SSRF validation is not auth (but is security) |
| VI | Fiscal Compliance (ARCA) | PASS | ARCA SOAP endpoint URLs validated through this pipeline — correctness parity ensures no disruption |
| VII | Offline-First | N/A | URL validation is server-side only |
| VIII | Query Optimization | N/A | No database queries |
| IX | Secure Data Operations | N/A | No model forms or data mutations |
| X | Test-Driven Development | PASS | ~65 tests planned: adversarial corpus parity, IP format, CIDR boundary, hostname pattern, DNS mock, fallback, benchmarks. TDD: corpus captured before Rust implementation. |
| XI | JWT Authentication | N/A | Not auth-related |
| XII | Rate Limiting | N/A | Not rate-limiting-related |
| XIII | Cursor-Based Pagination | N/A | Not an API endpoint |
| XIV | API Documentation | N/A | Internal function, no REST endpoint |

**Result**: NO VIOLATIONS. All relevant principles (III, VI, X) are satisfied.

## Project Structure

### Documentation (this feature)

```text
specs/022-ssrf-validation-pipeline/
├── plan.md              # This file
├── research.md          # Phase 0 output — 6 research topics resolved
├── quickstart.md        # Phase 1 output — build/test/integrate commands
├── checklists/
│   └── requirements.md  # Spec quality checklist (already complete, 16/16 pass)
└── tasks.md             # Phase 2 output (/speckit.tasks — NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
rust/gravitea-core/
├── Cargo.toml                 # +url = "2.5" (regex already present)
├── src/
│   ├── lib.rs                 # +mod security; +2 #[pymodule_export]
│   ├── errors.rs              # +SecurityError(String) variant
│   └── security.rs            # NEW — validate_url_safety + check_resolved_ip
│                              #   Internal: parse_ip_flexible, is_private_ip,
│                              #   is_metadata_ip, is_suspicious_hostname,
│                              #   extract_hostname_fallback

backend/
├── apps/core/security/
│   ├── url_validator.py       # MINIMAL CHANGE — URLValidator.is_safe() delegates to ssrf_engine
│   └── ssrf_engine.py         # NEW — Rust dispatcher with Python fallback
├── gravitea_rust.pyi          # +2 function stubs
└── tests/
    ├── security/test_ssrf.py  # UNCHANGED — must pass unmodified (SC-010)
    └── rust_integration/
        └── test_security_022.py  # NEW — ~65 tests (parity, format, range, pattern, DNS, fallback, bench)
```

**Structure Decision**: Hybrid Rust library + Python dispatcher. Rust source in `rust/gravitea-core/src/security.rs` (following SPEC-018/019/020/021 module pattern). Python dispatcher in `backend/apps/core/security/ssrf_engine.py` (following SPEC-021 `observability_engine.py` pattern). Test in `backend/tests/rust_integration/` to avoid conftest RLS conflicts.

## Implementation Phases

### Phase 1: Adversarial Corpus & Cargo Setup

**Risk**: HIGH (security correctness depends on test quality)
**Blocks**: Phase 2, Phase 3
**Agents**: LEAD + QA

1. Extract all URLs from `tests/constants.py` SSRF_* constants + `test_ssrf.py` inline URLs
2. Add ~14 additional adversarial URLs (decimal private, hex private, octal, mixed octal, shortened private, 3-part shortened, IPv4-mapped v6, credential injection, null byte host, sslip.io, xip.io, public IP explicit, long URL, double-encoded)
3. Run each URL through Python `is_safe_url()` to capture expected output → `ADVERSARIAL_CORPUS` list
4. Add `url = "2.5"` to `Cargo.toml`
5. Add `SecurityError(String)` variant to `errors.rs`
6. Add `mod security;` to `lib.rs`
7. Create empty `security.rs` with module doc + imports

### Phase 2: Rust Implementation

**Risk**: HIGH (security-critical code)
**Blocked by**: Phase 1
**Blocks**: Phase 3
**Agents**: RUST-EXPERT

1. Implement `parse_ip_flexible()` — 5 IP format strategies (standard → decimal → hex → octal → shortened)
2. Implement `is_private_ip()` — 10 CIDR ranges as compiled prefix checks
3. Implement `is_metadata_ip()` — 2 cloud metadata IPs
4. Implement `is_suspicious_hostname()` — 9 `LazyLock<Regex>` + null byte + localhost substring + IPv6 prefix
5. Implement `validate_url_safety()` — URL parsing via `url` crate + fallback hostname extraction
6. Implement `check_resolved_ip()` — parse IP string + private/metadata check
7. Add `#[pymodule_export]` entries in `lib.rs` pymodule block
8. Write >=30 Rust-native `#[test]` tests
9. `cargo test` — all pass

### Phase 3: Security Review

**Risk**: HIGH (SSRF bypass = critical vulnerability)
**Blocked by**: Phase 2
**Blocks**: Phase 4
**Agents**: SECURITY

1. Review `security.rs` for SSRF bypass vectors
2. Test `url` crate vs `urlparse` divergences on edge cases
3. Verify all 5 IP format variants with boundary tests
4. Verify all 10 CIDR ranges with first/last IPs in each range
5. Verify all 9 suspicious hostname patterns with positive/negative matches
6. Sign off OR request changes → loop back to Phase 2

### Phase 4: Python Integration & Equivalence Tests

**Risk**: MEDIUM
**Blocked by**: Phase 3
**Agents**: QA

1. Create `ssrf_engine.py` (dispatcher)
2. Modify `url_validator.py:URLValidator.is_safe()` to delegate
3. Update `gravitea_rust.pyi` with 2 stubs
4. Build Rust wheel with maturin
5. Create `test_security_022.py` (~65 tests: parity, format, range, pattern, DNS, fallback, bench)
6. Run existing `test_ssrf.py` — 0 modifications, all pass (SC-010)
7. Benchmark: >=3x on CPU portions (SC-002)

### Phase 5: Docker & Regression

**Risk**: LOW
**Blocked by**: Phase 4
**Agents**: LEAD

1. Build Docker: `docker compose build web`
2. Verify Rust functions available in container
3. Run security tests in container
4. Run SPEC-022 integration tests in container
5. Full regression: 0 regressions
6. Update quickstart.md

## Phase Dependency Graph

```text
Phase 1 (Corpus + Setup)
    │
    ├──→ Phase 2 (Rust Impl)
    │        │
    │        └──→ Phase 3 (Security Review)
    │                 │
    │                 └──→ Phase 4 (Python Integration + Tests)
    │                          │
    │                          └──→ Phase 5 (Docker + Regression)
```

All phases are sequential — no parallelization between phases (security gate at Phase 3).

## Success Criteria Mapping

| SC | Phase | Validated By |
|----|-------|-------------|
| SC-001 | Phase 4 | Parametrized parity test (~80 URLs) |
| SC-002 | Phase 4 | Benchmark >=3x on 200 URL corpus |
| SC-003 | Phase 2+4 | 5 format-specific Rust + Python tests |
| SC-004 | Phase 2+4 | 10 range boundary tests |
| SC-005 | Phase 2+4 | 9 pattern positive/negative tests |
| SC-006 | Phase 2+4 | 2 metadata IP tests |
| SC-007 | Phase 4 | ImportError simulation test |
| SC-008 | Phase 5 | Docker container import + test |
| SC-009 | Phase 5 | Full suite 0 regressions |
| SC-010 | Phase 4 | `test_ssrf.py` passes unmodified |

## Complexity Tracking

No constitution violations — this section is empty by design.
