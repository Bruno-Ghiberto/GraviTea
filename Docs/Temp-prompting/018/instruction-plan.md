# Speckit Context: Crypto Acceleration — PLAN Phase (SPEC-018)

> **Phase**: PLAN — Design implementation plan, research decisions, task breakdown
> **Priority**: HIGH | **Wave**: 2 (parallel with SPEC-021)
> **Produces**: `plan.md`, `research.md`, `quickstart.md`
> **Does NOT produce**: data-model.md, api-contract.md (no Django models or API endpoints)

---

## Mission

Design the implementation plan for replacing Python `cryptography` internals with Rust AES-256-GCM and HMAC-SHA256 blind indexing. The plan must ensure byte-for-byte compatibility with existing encrypted database data. Nonce generation is internal to `encrypt_value` — no fourth Rust export.

## Team Architecture

| Agent | Subagent Type | Model | Role |
|-------|--------------|-------|------|
| ORCHESTRATOR (LEAD) | system-architect | Opus 4.6 | Coordinates, validates, documentation |
| RUST-PROGRAMMER | general-purpose | Opus 4.6 | Implements crypto.rs, Rust tests |
| SECURITY | security-engineer | Opus 4.6 | Reviews crypto correctness, key handling |
| QA | quality-engineer | Sonnet 4.6 | Cross-implementation tests, property-based tests, benchmarks |

### Sequential-Thinking MCP

- **MANDATORY**: RUST-PROGRAMMER (ownership analysis for key material handling), SECURITY (crypto review)
- **NOT required**: QA (mechanical test writing)

### Execution Model

Sequential phases — crypto correctness demands validation at each step before proceeding.

## Implementation Phases

### Phase 1: Rust Crypto Implementation (RUST-PROGRAMMER)
- **Risk**: HIGH (crypto correctness is critical)
- Tasks:
  1. Read current `backend/apps/core/encryption/utils.py` — understand exact wire format
  2. Add crypto crates to `Cargo.toml` (aes-gcm, hmac, sha2, rand, hex)
  3. Create `rust/gravitea-core/src/crypto.rs` with 3 `#[pyfunction]` exports (`encrypt_value`, `decrypt_value`, `compute_blind_index` — nonce generation is internal to `encrypt_value`, NOT a separate export)
  4. Register crypto submodule in `lib.rs`
  5. Write Rust-native tests: roundtrip, determinism, wrong-key rejection, key-length validation, nonce uniqueness
  6. Run `cargo test` — all crypto tests pass

### Phase 2: Security Review (SECURITY)
- **Risk**: HIGH (crypto bypass would corrupt PII)
- Tasks:
  1. Review `crypto.rs` for: constant-time operations, key material handling, nonce reuse prevention
  2. Verify wire format matches `base64(nonce[12] || ciphertext || tag[16])` exactly
  3. Review blind index normalisation: confirm Rust applies NFC → lowercase → strip whitespace (in that order); verify `unicode-normalization` crate produces identical NFC output to Python's `unicodedata.normalize("NFC", ...)`
  4. Verify `GraviteaError::InvalidInput` raised for invalid key length (maps to `PyValueError`)
  5. Sign off or request changes

### Phase 3: Python Integration (QA)
- **Risk**: MEDIUM (FFI boundary)
- Tasks:
  1. Modify `backend/apps/core/encryption/utils.py` — add Rust fallback wrapper
  2. Update `gravitea_rust.pyi` with crypto function signatures
  3. Write cross-implementation tests: Rust-encrypted → Python-decrypted, Python-encrypted → Rust-decrypted
  4. Write NFC normalisation parity test: for the same PII string stored in different Unicode forms (NFC and NFD), `compute_blind_index` must produce identical hex output from both Rust and Python paths
  5. Write property-based tests (hypothesis): random string roundtrips including Argentine PII (ñ, á, é, ü, CUITs) — minimum 500 examples
  6. Write benchmark tests: measure actual speedup vs Python (target ≥5× — under 5 µs per operation)

### Phase 4: Docker Validation (LEAD)
- **Risk**: LOW
- Tasks:
  1. Rebuild Docker image — verify crypto functions available in container
  2. Run crypto integration tests inside container

### Phase 5: Polish & Regression (LEAD)
- **Risk**: LOW
- Tasks:
  1. Run full test suite (2,200+ tests) — 0 regressions
  2. Verify fallback: temporarily remove Rust extension → Python encryption works, all tests pass
  3. Verify FR-010: when running in fallback mode, application startup emits exactly one `WARNING`-level log entry identifying that the software fallback is active; no warning emitted when Rust loads successfully
  4. Update quickstart.md with crypto-specific notes
  5. Measure: cargo test passes, Docker builds, benchmarks documented

## Research Topics (for research.md)

| ID | Topic | Decision Needed | Assigned To |
|----|-------|----------------|-------------|
| R-001 | NFC Unicode normalisation in Rust `compute_blind_index` | Use `unicode-normalization = "0.1"` crate; verify `nfc()` iterator produces byte-identical NFC to Python's `unicodedata.normalize("NFC", value)` for Argentine PII corpus (ñ, á, é, ü, CUITs) | SECURITY |
| R-002 | `aes-gcm` crate audit status and version pinning | Confirm crate is RustCrypto-audited | RUST-PROGRAMMER |
| R-003 | Property-based test coverage: which input distributions matter | Random bytes vs structured strings vs CUITs | QA |
| R-004 | Blind index hex encoding: lower vs upper case | Match Python's `hexdigest()` output exactly | RUST-PROGRAMMER |

## Crate Dependencies

| Crate | Version | New/Shared | Purpose |
|-------|---------|-----------|---------|
| `aes-gcm` | 0.10 | NEW | AES-256-GCM encrypt/decrypt |
| `hmac` | 0.12 | NEW | HMAC-SHA256 blind index |
| `sha2` | 0.10 | NEW | SHA256 digest |
| `rand` | 0.8 | NEW | CSPRNG for nonce generation |
| `hex` | 0.4 | NEW | Hex encoding for blind index |
| `unicode-normalization` | 0.1 | NEW | NFC normalisation for blind index (resolves R-001) |

## Testing Standards

1. **Rust-native** (`cargo test`): ≥8 crypto tests — roundtrip, determinism, wrong-key, key-length, nonce uniqueness, empty input, large input, concurrent
2. **Python integration** (`pytest`): Cross-encrypt/decrypt equivalence, blind index matching
3. **Property-based**: `proptest` (Rust) + `hypothesis` (Python) — random string roundtrips
4. **Benchmark**: `criterion` (Rust) + `pytest-benchmark` (Python) — measure ≥5× speedup (absolute target: under 5 µs per operation for a 50-char plaintext)
5. **Docker**: Rebuild and verify crypto available in container
6. **Regression**: Full suite (2,200+ tests) with 0 new failures

## Constraints

1. SPEC-017 must be complete — `gravitea_rust` module exists
2. Byte-for-byte wire format compatibility — existing DB data must decrypt
3. `cryptography` library RETAINED — WSAA certificate ops stay in Python
4. Python fallback mandatory — `_USE_RUST` pattern
5. No Django model changes, no migrations
6. Sequential-thinking for RUST-PROGRAMMER and SECURITY (crypto correctness)
7. ANALYZE → CODE → TEST → VERIFY cycle per phase
8. External test runner for all pytest: `scripts/run-tests-external.sh`

## Success Criteria

1. `cargo test` ≥8 crypto tests pass
2. Cross-implementation equivalence verified (Rust↔Python)
3. Property-based tests pass (1000+ random inputs)
4. Benchmark ≥5× speedup (under 5 µs per operation absolute)
5. Existing encrypted DB data decrypts with Rust
6. Fallback works without Rust extension
7. Docker builds with crypto available
8. Full test suite 0 regressions
9. Type stub updated

## Reference Documents

| Document | Purpose | Path |
|----------|---------|------|
| Specify context | Architecture decisions | `Docs/Temp-prompting/018/instruction-specify.md` |
| Roadmap | Full spec details | `Docs/Brainstorming/rust-pyo3-speckit-roadmap.md` §4 |
| Integration Guide | Code examples | `Docs/Brainstorming/rust-pyo3-integration-guide.md` §5 |
| Current encryption | Python implementation | `backend/apps/core/encryption/utils.py` |
| Encryption skill | Patterns | `skills/gravitea-encryption/SKILL.md` |
| 017 spec | Bootstrap foundation | `specs/017-rust-bootstrap/` |
