# Speckit Implement Context: Crypto Acceleration (SPEC-018)

> **Phase**: IMPLEMENT — Execute the plan with agent teams
> **Feature**: `018-rust-crypto` | **Version**: 2.0 (2026-02-25)

---

## IMMEDIATE EXECUTION DIRECTIVE

**Upon reading this document, LEAD must act — not plan.**

Execute this sequence NOW, without pausing for human approval between phases:

1. **Execute Phases 1–2 yourself** (T001–T006): verify SPEC-017, add Cargo.toml deps, wire crypto submodule, `cargo check`
2. **Spawn RUST-PROGRAMMER** with full Rust workload (T007–T012 + T025–T027 + T040) — agent works sequentially through all Rust phases
3. **After RUST-PROGRAMMER signals Phase 3 complete** (T012 `cargo test ≥7` passes) → **spawn SECURITY** for T013 review
4. **After SECURITY reports APPROVED** → **spawn QA** with full Python workload (T014–T015, T016–T024, T039, T028–T032, T033, T037)
5. **RUST-PROGRAMMER continues independently** with Phase 6 Rust (T025–T027, T040) in parallel with SECURITY + QA
6. **When both RUST-PROGRAMMER and QA complete** → execute Phase 7 yourself (T034–T038)
7. **Report final results**

**Key principle**: Each agent gets its full workload upfront. LEAD monitors and intervenes only on CRITICAL errors.

**No worktree isolation** — all agents share the main filesystem. File ownership rules prevent conflicts.

---

## Authoritative Documents

| Priority | Document | Path | Purpose |
|----------|----------|------|---------|
| 1 | **tasks.md** | `specs/018-rust-crypto/tasks.md` | 40 tasks, 7 phases, TDD execution order — AUTHORITATIVE |
| 2 | plan.md | `specs/018-rust-crypto/plan.md` | Phase structure, constraints, architecture |
| 3 | spec.md | `specs/018-rust-crypto/spec.md` | 4 user stories, 10 FRs, 7 SCs |
| 4 | research.md | `specs/018-rust-crypto/research.md` | R-001 (NFC), R-002 (wire format), R-003 (hypothesis), R-004 (hex) |
| 5 | quickstart.md | `specs/018-rust-crypto/quickstart.md` | 8-step build/test guide |

> `tasks.md` supersedes `plan.md` for task IDs, counts, and execution order.

---

## Agent Team Architecture

### Agent Roster

| Agent | Model | subagent_type | Role |
|-------|-------|--------------|------|
| **LEAD** (you) | Opus 4.6 | system-architect | Setup (Phases 1–2), orchestration, Docker + regression (Phase 7) |
| **RUST-PROGRAMMER** | Opus 4.6 | general-purpose | All Rust: crypto.rs TDD (Phase 3) + blind index TDD (Phase 6) |
| **SECURITY** | Opus 4.6 | security-engineer | T013 gate review — no file writes |
| **QA** | Sonnet 4.6 | quality-engineer | All Python: dispatch, tests, property-based, fallback, benchmarks |
| **WIKI-EXPERT** | Sonnet 4.6 | general-purpose | On-demand: RAG queries to `wikis` collection (JWT, Rust, Django docs) |

### Spawning Schedule

| Phase | Active Agents | Tasks | Gate |
|-------|--------------|-------|------|
| 1–2 (Setup + Foundational) | LEAD only | T001–T006 | `cargo check` exits 0 |
| 3 Rust (US1) | RUST-PROGRAMMER | T007–T012 | `cargo test ≥7` |
| 3 Review | SECURITY | T013 | APPROVED report |
| 3–5 Python + 6 Rust | RUST-PROGRAMMER + QA | RUST: T025–T027, T040 / QA: T014–T024, T039 | |
| 6 Python (US4) | QA | T028–T032 | requires RUST-PROGRAMMER T027 complete |
| 7 (Polish) | LEAD + QA | T033, T034–T038 | 0 regressions, Docker builds |
| **On-demand** | **WIKI-EXPERT** | — | Any phase: activated by LEAD when a technical challenge arises |

### Agent Spawn Instructions

Each agent has a dedicated instruction file. Pass ONLY the instruction file path in the spawn prompt:

**RUST-PROGRAMMER spawn prompt**:
```
Read Docs/Temp-prompting/018/agent-RUST-PROGRAMMER.md and execute your mission exactly as described.
```

**SECURITY spawn prompt**:
```
Read Docs/Temp-prompting/018/agent-SECURITY.md and execute your review exactly as described.
```

**QA spawn prompt**:
```
Read Docs/Temp-prompting/018/agent-QA.md and execute your mission exactly as described.
```

**WIKI-EXPERT spawn prompt** (on-demand — include the specific question):
```
Read Docs/Temp-prompting/018/agent-WIKI-EXPERT.md and execute your mission exactly as described.
Your query: [DESCRIBE THE TECHNICAL CHALLENGE HERE]
```

---

## File Ownership Rules (STRICT)

| Agent | May WRITE |
|-------|-----------|
| **LEAD** | `rust/gravitea-core/Cargo.toml` (T002 deps only), `rust/gravitea-core/src/lib.rs` (T004), `specs/018-rust-crypto/quickstart.md` (T038), Docker validation |
| **RUST-PROGRAMMER** | `rust/gravitea-core/src/crypto.rs`, `rust/gravitea-core/Cargo.toml` (T040 dev-deps) |
| **SECURITY** | No file writes — reports text to LEAD only |
| **QA** | `backend/apps/core/encryption/utils.py`, `backend/gravitea_rust.pyi`, `backend/tests/rust_integration/test_crypto_018.py` |
| **WIKI-EXPERT** | No file writes — RAG query results returned to LEAD only |

**Violation of file ownership is a CRITICAL error.**

---

## Phase Execution Guide

### Phases 1–2: Setup + Foundational (LEAD executes)

**T001**: Verify `backend/venv-wsl/bin/python -c "import gravitea_rust; print(gravitea_rust.hello())"` prints `"Hello from Rust!"` — stop if it fails; install test deps: `backend/venv-wsl/bin/pip install hypothesis pytest-benchmark`

**T002**: Add 6 crates to `[dependencies]` in `rust/gravitea-core/Cargo.toml`:
```toml
aes-gcm = "0.10"
hmac = "0.12"
sha2 = "0.10"
rand = "0.8"
hex = "0.4"
unicode-normalization = "0.1"
```

**T003**: Create `backend/tests/rust_integration/test_crypto_018.py` scaffold (importable, imports + constants only).

**T004**: Add to `rust/gravitea-core/src/lib.rs`:
- `mod crypto;` declaration
- `use super::crypto::encrypt_value;` / `::decrypt_value;` / `::compute_blind_index;` inside the `mod gravitea_rust` block

**T005**: Create `rust/gravitea-core/src/crypto.rs` stub — 3 `#[pyfunction]` stubs returning `Err(GraviteaError::CryptoError("not implemented".to_string()).into())`.

**T006**: Run `cargo check` from `rust/gravitea-core/` — exits 0 with all 6 crates resolved.

**GATE**: `cargo check` passes → spawn RUST-PROGRAMMER.

### Phase 3 Rust (RUST-PROGRAMMER)

See `agent-RUST-PROGRAMMER.md`. Key: TDD order — write tests (T007–T008) BEFORE implementation (T009–T011).

**GATE**: `cargo test` from `rust/gravitea-core/` reports ≥7 crypto tests passing.

### Phase 3 Review (SECURITY)

See `agent-SECURITY.md`. Reviews `rust/gravitea-core/src/crypto.rs` after T012 passes.

**GATE**: SECURITY report says APPROVED (or LEAD resolves CHANGES_REQUIRED).

### Phase 3–5 Python + Phase 6 Rust (QA + RUST-PROGRAMMER parallel)

After SECURITY APPROVED:
- **Spawn QA** with full workload (T014–T024 + T039 + T028–T032 + T033 + T037)
- **RUST-PROGRAMMER** continues with T025–T027 + T040 (blind index TDD)
- QA blocks on T028 until RUST-PROGRAMMER signals T027 complete

### Phase 7: Polish (LEAD)

After both RUST-PROGRAMMER and QA report complete:

**T034**: `docker compose build web` → `docker compose run --rm web python -c "import gravitea_rust; k=b'0'*32; print(gravitea_rust.decrypt_value(gravitea_rust.encrypt_value('test', k), k))"` — must print `test`

**T035**: Run integration tests inside Docker container.

**T036**: Full regression via `scripts/run-tests-external.sh "backend/venv-wsl/bin/python -m pytest backend/tests/ --tb=short -q --no-header"` — read `.summary` only. Target: 0 new failures.

**T038**: Update `specs/018-rust-crypto/quickstart.md` with actual build outputs and benchmark results.

**GATE**: 0 regressions, Docker builds, benchmark ≥5× documented.

### On-Demand: WIKI-EXPERT (any phase)

LEAD may spawn WIKI-EXPERT at any point when a technical challenge requires documentation lookup. Activation triggers:

| Challenge | Query topic |
|-----------|-------------|
| JWT claim validation patterns, RS256 algorithm enforcement | `jwt claims validation`, `jwt algorithm RS256` |
| AES-GCM crate API, `aes-gcm 0.10` usage patterns | `aes gcm rust crate usage` |
| PyO3 binding patterns, Python↔Rust type conversions | `pyo3 python rust interop` |
| Django DRF serializer or ORM patterns affecting utils.py | `django drf serializer`, `django orm` |
| HMAC-SHA256 or base64 Rust patterns | `hmac sha256 rust`, `base64 encoding rust` |

Spawn with the question in the prompt. WIKI-EXPERT returns top results and terminates — no state persists.

---

## Test Execution Protocol

```bash
# Rust tests (RUST-PROGRAMMER runs this)
cd rust/gravitea-core && cargo test -- --nocapture 2>&1 | tail -30

# Python crypto tests only (QA + LEAD)
backend/venv-wsl/bin/python -m pytest \
  backend/tests/rust_integration/test_crypto_018.py \
  -p no:django --confcutdir=backend/tests/rust_integration \
  -o "addopts=" --tb=short -q

# Full regression (LEAD Phase 7)
scripts/run-tests-external.sh "018-regression" \
  "backend/venv-wsl/bin/python -m pytest backend/tests/ --tb=short -q --no-header"
```

Read ONLY `.summary` files. If failures: `grep "FAIL\|Error" .claude-test-full.log | head -40`.

---

## Error Protocol

| Severity | Criteria | Action |
|----------|----------|--------|
| CRITICAL | Wire format mismatch; cross-compat test failure; data corruption risk | HALT all work, fix immediately |
| HIGH | `cargo test` failure; key handling issue; SECURITY CHANGES_REQUIRED | Agent fixes before next phase |
| MEDIUM | Benchmark below ≥5× target | Note for polish, continue |
| LOW | Documentation gap | Fix in Phase 7 |

---

## Known Gotchas

| Issue | Cause | Fix |
|-------|-------|-----|
| Wrong base64 alphabet | `STANDARD_NO_PAD` vs `STANDARD` | Use `general_purpose::STANDARD` exactly |
| Wrong blind index output | Missing NFC step | Order is NFC → lower → strip (not lower → strip) |
| FR-010 test fails | `_USE_RUST` monkeypatch doesn't retrigger warning | Use `importlib.reload` + `sys.modules.pop` |
| `cryptography` still needed | WSAA certs use PKCS#7/X.509 | Do NOT remove from requirements.txt |
| CRLF in `.rs` files | Windows Git line endings | Ensure `.rs` files use LF only |

---

## Final Report Template

When ALL phases complete, report:

```
SPEC-018 IMPLEMENTATION COMPLETE
- T001-T006  (Phases 1-2 Setup):      [PASS] — cargo check 0
- T007-T012  (Phase 3 Rust):          [PASS] — cargo test [N] passing
- T013        (SECURITY gate):         [APPROVED]
- T014-T024  (Phases 3-5 Python):     [PASS] — [N] tests
- T025-T027  (Phase 6 Rust):          [PASS] — cargo test [N] passing
- T040        (Rust proptest):         [PASS]
- T028-T032  (Phase 6 Python):        [PASS] — [N] tests
- T039        (null/empty FR-005):     [PASS]
- T034-T036  (Phase 7 Docker+Regr):   [PASS] — 0 new failures
- T037        (benchmarks):            [PASS] — Rust [X]× faster
- SC-001 (≥5× < 5µs):                [PASS/FAIL] — actual: [X]×, [Y]µs
- SC-002 (backward compat):           [PASS]
- SC-003 (blind index parity):        [PASS]
- SC-004 (fallback):                  [PASS]
- SC-007 (1000 cross-path):           [PASS]
```
