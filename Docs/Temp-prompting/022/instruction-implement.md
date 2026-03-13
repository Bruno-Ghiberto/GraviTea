# Speckit Implement Context: SSRF Validation Pipeline (SPEC-022)

> **Phase**: IMPLEMENT — Execute the plan with agent teams
> **Priority**: HIGH | **Wave**: 3
> **Version**: 2.0 (2026-02-27)
> **Depends on**: SPEC-017 (Rust Toolchain Bootstrap) — COMPLETE, SPEC-021 (Observability) — COMPLETE

---

## IMMEDIATE EXECUTION DIRECTIVE

1. Read `specs/022-ssrf-validation-pipeline/tasks.md` for authoritative task list (T001–T055)
2. Execute Phase 1 Setup (T001–T004, T007) yourself — Cargo.toml + errors.rs + lib.rs + scaffold
3. Spawn QA (corpus extraction: T005–T006) — can run in parallel with your Phase 1 setup
4. Spawn RUST-EXPERT — implements security.rs (Phase 2: T008–T024) — after Phase 1 completes
5. After RUST-EXPERT completes + maturin build:
   - Spawn SECURITY — review + sign-off (Phase 3: T025–T030)
6. After SECURITY sign-off (APPROVED):
   - Spawn QA — Python integration + tests (Phase 4: T031–T042)
   - Optionally spawn WIKI-EXPERT if technical question arises
7. After QA Phase 4 completes:
   - QA runs Phase 5+6 (T043–T049) — can run in parallel
8. Execute Phase 7 (Docker + Regression: T050–T055) yourself
9. Commit and report final results

---

## Authoritative Documents

| Priority | Document | Path |
|----------|----------|------|
| 1 | tasks.md | `specs/022-ssrf-validation-pipeline/tasks.md` |
| 2 | plan.md | `specs/022-ssrf-validation-pipeline/plan.md` |
| 3 | research.md | `specs/022-ssrf-validation-pipeline/research.md` |
| 4 | quickstart.md | `specs/022-ssrf-validation-pipeline/quickstart.md` |
| 5 | spec.md | `specs/022-ssrf-validation-pipeline/spec.md` |
| 6 | Source of truth | `backend/apps/core/security/url_validator.py` (is_safe_url, _parse_ip) |

---

## Agent Team Architecture

| Agent | Model | subagent_type | Role | Agent File |
|-------|-------|--------------|------|------------|
| LEAD (you) | Opus 4.6 | system-architect | Orchestration, setup (Phase 1), Docker (Phase 7) | — |
| RUST-EXPERT | Opus 4.6 | general-purpose | security.rs: 2 exported + 5 internal functions (Phase 2) | `agent-RUST-EXPERT.md` |
| SECURITY | Opus 4.6 | security-engineer | SSRF bypass review + sign-off (Phase 3) | `agent-SECURITY.md` |
| QA | Sonnet 4.6 | quality-engineer | Corpus extraction (Phase 1), Python integration + tests (Phase 4-6) | `agent-QA.md` |
| WIKI-EXPERT | Sonnet 4.6 | general-purpose | On-demand RAG librarian | `agent-WIKI-EXPERT.md` |

### Agent Spawn Prompts

Each agent has a dedicated instruction file in `Docs/Temp-prompting/022/`. Spawn agents by reading their instruction file into the prompt. Use Claude Code Team Agents — auto-detects tmux for multi-pane orchestration (one pane per agent).

**RUST-EXPERT:**
```
name: "RUST-EXPERT"
model: "opus"
subagent_type: "general-purpose"
mode: "bypassPermissions"
prompt: "Read Docs/Temp-prompting/022/agent-RUST-EXPERT.md for your full mission brief."
```

**SECURITY:**
```
name: "SECURITY"
model: "opus"
subagent_type: "security-engineer"
mode: "bypassPermissions"
prompt: "Read Docs/Temp-prompting/022/agent-SECURITY.md for your full mission brief."
```

**QA:**
```
name: "QA"
model: "sonnet"
subagent_type: "quality-engineer"
mode: "bypassPermissions"
prompt: "Read Docs/Temp-prompting/022/agent-QA.md for your full mission brief."
```

**WIKI-EXPERT (on-demand only):**
```
name: "WIKI-EXPERT"
model: "sonnet"
subagent_type: "general-purpose"
mode: "bypassPermissions"
prompt: "Read Docs/Temp-prompting/022/agent-WIKI-EXPERT.md for your full mission brief. Challenge: <describe technical question here>"
```

---

## File Ownership Rules (STRICT)

| Agent | May Write |
|-------|-----------|
| LEAD | `rust/gravitea-core/Cargo.toml`, `rust/gravitea-core/src/lib.rs` (setup only), `rust/gravitea-core/src/errors.rs`, documentation, Docker validation |
| RUST-EXPERT | `rust/gravitea-core/src/security.rs`, `rust/gravitea-core/src/lib.rs` (security registration) |
| SECURITY | **Review only — no file writes** |
| QA | `backend/apps/core/security/ssrf_engine.py`, `backend/apps/core/security/url_validator.py` (minimal delegation change), `backend/gravitea_rust.pyi`, `backend/tests/rust_integration/test_security_022.py` |
| WIKI-EXPERT | **No file writes** — returns results as text only |

---

## Execution Flow

```
LEAD: Phase 1 Setup (T001–T004, T007)
  ├── T001 [P] Cargo.toml: +url = "2.5"
  ├── T002 [P] errors.rs: +SecurityError(String)
  ├── T003 [P] lib.rs: +mod security
  ├── T004    security.rs scaffold
  └── T007    cargo check
       │
       ├── QA: Corpus Extraction (T005–T006, parallel with setup)
       │   ├── T005  Extract adversarial URLs from test_ssrf.py + constants.py
       │   └── T006  Add 14 additional adversarial URLs
       │
       ▼
RUST-EXPERT: Phase 2 Foundational (T008–T024)
  ├── T008–T012  parse_ip_flexible() (5 strategies, sequential)
  ├── T013–T016  is_private_ip + is_metadata_ip + is_suspicious_hostname + extract_hostname_fallback (parallel)
  ├── T017       validate_url_safety() (depends on T008–T016)
  ├── T018       check_resolved_ip()
  ├── T019       lib.rs #[pymodule_export] entries
  ├── T020–T023  Rust-native tests (parallel groups)
  └── T024       cargo test (>=30 tests)
       │
       ▼ (maturin build by LEAD)
       │
SECURITY: Phase 3 Review (T025–T030) — HARD GATE
  ├── T025  Full code review for SSRF bypass vectors
  ├── T026  url crate vs urlparse divergence testing
  ├── T027  IP format boundary verification
  ├── T028  CIDR range boundary verification
  ├── T029  Hostname pattern positive/negative verification
  └── T030  Sign-off: APPROVED or CHANGES_REQUIRED
       │
       ▼ (APPROVED required to proceed)
       │
QA: Phase 4 Integration + Tests (T031–T042)
  ├── T031  ssrf_engine.py dispatcher
  ├── T032  url_validator.py delegation
  ├── T033 [P] gravitea_rust.pyi stubs
  ├── T034  maturin build + verify import
  ├── T035–T039 [P] parity tests (US1)
  ├── T040–T041 [P] DNS tests (US2)
  └── T042  existing test_ssrf.py regression (SC-010)
       │
  ┌────┴────┐
  ▼         ▼
QA: Phase 5 (US3)    QA: Phase 6 (US4)   ← can run in parallel
  ├── T043–T046         ├── T047–T049
  │ benchmark >=3x      │ fallback tests
  └─────────┬───────────┘
            ▼
LEAD: Phase 7 Polish (T050–T055)
  ├── T050  Docker rebuild
  ├── T051  Container import verification (SC-008)
  ├── T052  Container security tests
  ├── T053  Container SPEC-022 tests
  ├── T054  Full regression (SC-009)
  └── T055  Update quickstart.md
```

---

## Test Execution Protocol

**MANDATORY**: ALL Python and Rust tests MUST be executed via `scripts/run-tests-external.sh` using `venv-wsl`. NO EXCEPTIONS. This saves 96% of tokens vs inline test output.

All test logs are saved to `Docs/Tests/`.

```bash
# Rust tests (cargo test — run from repo root)
scripts/run-tests-external.sh -n "022-cargo" \
  "cd rust/gravitea-core && cargo test security -- --nocapture"

# Python SPEC-022 integration tests
scripts/run-tests-external.sh -n "022-security" \
  "cd backend && venv-wsl/bin/python -m pytest \
    tests/rust_integration/test_security_022.py \
    -v --tb=short -q --no-header"

# Parity tests only
scripts/run-tests-external.sh -n "022-parity" \
  "cd backend && venv-wsl/bin/python -m pytest \
    tests/rust_integration/test_security_022.py \
    -k 'Parity or Format or Range or Hostname or Scheme' \
    -v --tb=short -q --no-header"

# Existing SSRF tests (must pass unmodified — SC-010)
scripts/run-tests-external.sh -n "022-ssrf-existing" \
  "cd backend && venv-wsl/bin/python -m pytest \
    tests/security/test_ssrf.py \
    -v --tb=short -q --no-header"

# Benchmark tests only
scripts/run-tests-external.sh -n "022-bench" \
  "cd backend && venv-wsl/bin/python -m pytest \
    tests/rust_integration/test_security_022.py \
    -k 'benchmark' -v --tb=short -q --no-header"

# Fallback tests only
scripts/run-tests-external.sh -n "022-fallback" \
  "cd backend && venv-wsl/bin/python -m pytest \
    tests/rust_integration/test_security_022.py \
    -k 'fallback' -v --tb=short -q --no-header"

# Full regression suite
scripts/run-tests-external.sh -n "022-regression" \
  "cd backend && venv-wsl/bin/python -m pytest \
    tests/ --tb=short -q --no-header"
```

**After running**: Read ONLY the `.summary` file. NEVER read the `.log` in full — use `Grep` for specific errors if needed.

```bash
# Read test results (token-efficient)
cat Docs/Tests/022-security.summary
cat Docs/Tests/022-security.status
# Only on failure — grep specific errors
grep "FAIL\|Error" Docs/Tests/022-security.log
```

---

## Maturin Build (Between Rust and Python Phases)

```bash
# LEAD runs this after RUST-EXPERT completes Phase 2
VIRTUAL_ENV=$(pwd)/backend/venv-wsl maturin develop \
  --manifest-path rust/gravitea-core/Cargo.toml --release
```

This builds the `.so` that Python imports. QA cannot start Phase 4 until this succeeds.

---

## Known Gotchas

| Issue | Cause | Fix |
|-------|-------|-----|
| `url` crate rejects hex/decimal/octal IPs | WHATWG standard is strict | `extract_hostname_fallback()` handles these (R-001, R-005) |
| Octal IP parsing | Neither Rust std nor `url` crate parse octal | Custom `parse_ip_flexible()` strategy 4 (R-002) |
| `::ffff:0:0/96` catches ALL IPv4-mapped | Python uses this CIDR — matches public IPs too | Replicate for parity; more precise approach deferred (R-003) |
| `http://@host/` has empty username | Python `if parsed.username:` is falsy for `""` | Rust: only block if username non-empty OR password present (R-004) |
| `pub fn` required for PyO3 | `#[pymodule_export]` needs `pub fn` visibility | All exported functions must be `pub fn` |
| GIL NOT released | Sub-millisecond ops; FFI overhead dominates | Do NOT call `py.allow_threads()` — direct return |
| FFI overhead limits speedup | SPEC-021 got ~2.6x (not 5x) due to per-call FFI cost | Measure CPU-bound only (exclude FFI round-trip) for SC-002 |
| `SecurityError` vs `PyRuntimeError` | Callers may expect specific Python exception types | Wrapper in ssrf_engine.py catches `RuntimeError` → raise as appropriate |
| test_postgres setting required | Django tests need `DJANGO_SETTINGS_MODULE=gravitea.settings.test_postgres` | The external test runner handles this; verify in conftest |
| Docker service name | Container is "web" not "backend" | `docker compose build web`, `docker compose run --rm --entrypoint python web` |

---

## WIKI-EXPERT Usage Guide

Spawn WIKI-EXPERT when the team encounters a technical question that documentation can answer. Common scenarios for SPEC-022:

| Scenario | Query Target |
|----------|-------------|
| Rust `url` crate WHATWG parsing behavior | `wikis` — "Rust url crate WHATWG parse hostname non-standard" |
| `IpAddr::from_str` format acceptance | `wikis` — "Rust std net IpAddr from_str accepted formats IPv4 IPv6" |
| `LazyLock<Regex>` compilation (same as SPEC-021) | `wikis` — "std sync LazyLock Regex thread safe compile once" |
| PyO3 `PyResult` tuple return types | `wikis` — "PyO3 PyResult tuple return type Python binding" |
| Python `urlparse` vs WHATWG URL Standard | `wikis` — "Python urllib urlparse vs WHATWG URL standard differences" |
| DNS rebinding attack patterns | `wikis` — "SSRF DNS rebinding attack prevention validation" |

WIKI-EXPERT is ephemeral — spawned for a single question, delivers results, then terminates.

---

## IP Format Reference (5 Strategies)

| # | Format | Example (loopback) | Parse Method |
|---|--------|-------------------|--------------|
| 1 | Standard | `127.0.0.1`, `::1` | `IpAddr::from_str()` + bracket stripping for `[::1]` |
| 2 | Decimal | `2130706433` | `hostname.parse::<u32>()` → `Ipv4Addr::from()` |
| 3 | Hexadecimal | `0x7f000001` | Strip `0x`/`0X` → `u32::from_str_radix(_, 16)` → `Ipv4Addr` |
| 4 | Octal | `0177.0.0.1` | Split on `.`, leading-zero → `u8::from_str_radix(_, 8)`, pad to 4 |
| 5 | Shortened | `127.1` | 2-part `a.b`→`a.0.0.b`, 3-part `a.b.c`→`a.b.0.c`, then standard parse |

## CIDR Range Reference (10 Ranges)

| # | Range | Type |
|---|-------|------|
| 1 | `10.0.0.0/8` | RFC 1918 private |
| 2 | `172.16.0.0/12` | RFC 1918 private |
| 3 | `192.168.0.0/16` | RFC 1918 private |
| 4 | `127.0.0.0/8` | Loopback |
| 5 | `169.254.0.0/16` | Link-local |
| 6 | `0.0.0.0/8` | "This" network |
| 7 | `::1/128` | IPv6 loopback |
| 8 | `fc00::/7` | IPv6 unique local |
| 9 | `fe80::/10` | IPv6 link-local |
| 10 | `::ffff:0:0/96` | IPv4-mapped IPv6 |

## Suspicious Hostname Patterns (9 Regex + 3 Checks)

| # | Pattern | Target |
|---|---------|--------|
| 1 | `(?i)\.nip\.io$` | Wildcard DNS (nip.io) |
| 2 | `(?i)\.xip\.io$` | Wildcard DNS (xip.io) |
| 3 | `(?i)\.sslip\.io$` | Wildcard DNS (sslip.io) |
| 4 | `(?i)localtest\.me$` | Localhost alias |
| 5 | `127\.0\.0\.1` | Embedded loopback IP |
| 6 | `169\.254\.` | Embedded link-local IP |
| 7 | `192\.168\.` | Embedded private IP |
| 8 | `10\.\d+\.` | Embedded 10.x.x IP |
| 9 | `172\.(1[6-9]\|2\d\|3[01])\.` | Embedded 172.16-31.x IP |
| + | `\x00` / `%00` in hostname | Null byte injection |
| + | `"localhost"` substring | Hostname contains localhost |
| + | `fd`/`fc`/`fe80` prefix + alphanumeric | IPv6 private prefix in hostname |
