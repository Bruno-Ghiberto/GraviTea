# Speckit Implement Context: Observability Hot Path (SPEC-021)

> **Phase**: IMPLEMENT — Execute the plan with agent teams
> **Priority**: HIGH | **Wave**: 2
> **Version**: 2.0 (2026-02-27)
> **Depends on**: SPEC-017 (Rust Toolchain Bootstrap) — COMPLETE

---

## IMMEDIATE EXECUTION DIRECTIVE

1. Read `specs/021-rust-observability-hotpath/tasks.md` for authoritative task list (T001–T025)
2. Execute Phase 1 (Setup: T001–T002) yourself — Cargo.toml + lib.rs
3. Spawn RUST-EXPERT — implements observability.rs with 24 `LazyLock<Regex>` patterns (T003–T007)
4. After RUST-EXPERT completes + maturin build:
   - Spawn BACKEND-CODER — Python dispatcher + type stubs + metrics.py integration (T012–T015, T017)
   - Spawn QA — parity tests, benchmark, fallback tests (T008–T011, T016, T018–T021)
   - Optionally spawn WIKI-EXPERT if technical question arises
5. After BACKEND-CODER + QA complete:
   - QA runs Phase 4+5 (T018–T021) — can run in parallel after Phase 3
6. Execute Phase 6 (Polish: T022–T025) yourself
7. Commit and report final results

---

## Authoritative Documents

| Priority | Document | Path |
|----------|----------|------|
| 1 | tasks.md | `specs/021-rust-observability-hotpath/tasks.md` |
| 2 | plan.md | `specs/021-rust-observability-hotpath/plan.md` |
| 3 | research.md | `specs/021-rust-observability-hotpath/research.md` |
| 4 | quickstart.md | `specs/021-rust-observability-hotpath/quickstart.md` |
| 5 | Source of truth | `backend/apps/core/observability/metrics.py` (lines 40–131) |

---

## Agent Team Architecture

| Agent | Model | subagent_type | Role | Agent File |
|-------|-------|--------------|------|------------|
| LEAD (you) | Opus 4.6 | system-architect | Orchestration, setup, polish | — |
| RUST-EXPERT | Opus 4.6 | general-purpose | observability.rs: 24 LazyLock + 2 functions | `agent-RUST-EXPERT.md` |
| BACKEND-CODER | Sonnet 4.6 | backend-architect | Python dispatcher + type stubs + metrics.py | `agent-BACKEND-CODER.md` |
| QA | Sonnet 4.6 | quality-engineer | Parity tests + benchmark + fallback | `agent-QA.md` |
| WIKI-EXPERT | Sonnet 4.6 | general-purpose | On-demand RAG librarian | `agent-WIKI-EXPERT.md` |

### Agent Spawn Prompts

Each agent has a dedicated instruction file in `Docs/Temp-prompting/021/`. Spawn agents by reading their instruction file into the prompt:

**RUST-EXPERT:**
```
name: "RUST-EXPERT"
model: "opus"
subagent_type: "general-purpose"
mode: "bypassPermissions"
prompt: "Read Docs/Temp-prompting/021/agent-RUST-EXPERT.md for your full mission brief."
```

**BACKEND-CODER:**
```
name: "BACKEND-CODER"
model: "sonnet"
subagent_type: "backend-architect"
mode: "bypassPermissions"
prompt: "Read Docs/Temp-prompting/021/agent-BACKEND-CODER.md for your full mission brief."
```

**QA:**
```
name: "QA"
model: "sonnet"
subagent_type: "quality-engineer"
mode: "bypassPermissions"
prompt: "Read Docs/Temp-prompting/021/agent-QA.md for your full mission brief."
```

**WIKI-EXPERT (on-demand only):**
```
name: "WIKI-EXPERT"
model: "sonnet"
subagent_type: "general-purpose"
mode: "bypassPermissions"
prompt: "Read Docs/Temp-prompting/021/agent-WIKI-EXPERT.md for your full mission brief. Challenge: <describe technical question here>"
```

---

## File Ownership Rules (STRICT)

| Agent | May Write |
|-------|-----------|
| LEAD | `rust/gravitea-core/Cargo.toml`, `rust/gravitea-core/src/lib.rs` (setup only), documentation, Docker validation |
| RUST-EXPERT | `rust/gravitea-core/src/observability.rs`, `rust/gravitea-core/src/lib.rs` (observability registration) |
| BACKEND-CODER | `backend/apps/core/observability/observability_engine.py`, `backend/gravitea_rust.pyi`, `backend/apps/core/observability/metrics.py` (import change only) |
| QA | `backend/tests/rust_integration/test_observability_021.py` |
| WIKI-EXPERT | **No file writes** — returns results as text only |

---

## Execution Flow

```
LEAD: Phase 1 Setup (T001–T002)
  ├── T001 [P] Cargo.toml: +regex = "1.10"
  └── T002    lib.rs: +pub mod observability + 2 #[pymodule_export]
         │
         ▼
RUST-EXPERT: Phase 2 Foundational (T003–T007)
  ├── T003  observability.rs: 24 LazyLock<Regex> statics
  ├── T004+T005 (parallel) normalize_path + sanitize_endpoint_label
  ├── T006  #[pyfunction] wrappers (NO GIL release)
  └── T007  Rust-native tests (target: 20+)
         │
         ▼ (maturin build by LEAD)
         │
    ┌────┴────┐
    ▼         ▼
BACKEND-CODER          QA (Tests — can write in parallel, same file)
Phase 3 impl           Phase 3 tests
  ├── T012  observability_engine.py       ├── T008 [P] normalize_path parity
  ├── T013  gravitea_rust.pyi stubs       ├── T009 [P] sanitize_endpoint_label parity
  ├── T014  metrics.py import change      ├── T010 [P] combined scenario tests
  ├── T015  maturin verify import         └── T011 [P] edge case tests
  └── T017  regression check (13 tests)
         │         │
         └────┬────┘
              ▼
         T016: Run all parity tests (0 failures)
              │
    ┌─────────┴─────────┐
    ▼                   ▼
QA: Phase 4 (US3)     QA: Phase 5 (US4)
  ├── T018 benchmark     ├── T020 fallback tests
  └── T019 record        └── T021 run fallback tests
              │                   │
              └─────────┬─────────┘
                        ▼
LEAD: Phase 6 Polish (T022–T025)
  ├── T022  Docker rebuild + import verification
  ├── T023+T024 (parallel) Docker tests + full regression
  └── T025  Update quickstart.md
```

---

## Test Execution Protocol

```bash
# Rust tests (run from repo root)
cd rust/gravitea-core && cargo test observability -- --nocapture

# Python observability tests only
scripts/run-tests-external.sh "021-obs" \
  "backend/venv-wsl/bin/python -m pytest \
    backend/tests/rust_integration/test_observability_021.py \
    -v --tb=short -q"

# Existing observability regression tests
scripts/run-tests-external.sh "021-regression" \
  "backend/venv-wsl/bin/python -m pytest \
    backend/tests/unit/observability/test_metrics.py \
    -v --tb=short -q"

# Full regression suite
scripts/run-tests-external.sh "021-full" \
  "backend/venv-wsl/bin/python -m pytest \
    backend/tests/ --tb=short -q --no-header"
```

---

## Maturin Build (Between Rust and Python Phases)

```bash
# LEAD runs this after RUST-EXPERT completes
VIRTUAL_ENV=$(pwd)/backend/venv-wsl maturin develop \
  --manifest-path rust/gravitea-core/Cargo.toml --release
```

This builds the `.so` that Python imports. BACKEND-CODER and QA cannot start until this succeeds.

---

## Known Gotchas

| Issue | Cause | Fix |
|-------|-------|-----|
| GIL NOT released | Sub-microsecond ops; FFI overhead > GIL contention | Do NOT call `py.allow_threads()` — direct return |
| `LazyLock` not `lazy_static` | `std::sync::LazyLock` stable since Rust 1.80 | No external crate needed (project uses Rust 1.93.1) |
| No capture groups | All 24 patterns use simple `re.sub(pattern, replacement, string)` | Use `Regex::replace_all()` with literal replacement strings |
| RegexSet NOT viable | All ops are substitutions, not match-only | Use individual `LazyLock<Regex>` per pattern (24 statics) |
| Pattern ordering matters | Sequential `replace_all` in a loop must match Python order | Iterate arrays in declaration order (same as Python) |
| `(?i)` for case-insensitive | 22 of 24 patterns use `re.IGNORECASE` | Prefix Rust patterns with `(?i)` — identical for ASCII |
| `\b` word boundaries | 6 fallback patterns use `\b` for word boundaries | Rust `\b` identical to Python `\b` for ASCII (R-004) |
| `pub fn` required | `#[pymodule_export]` needs `pub fn` in PyO3 0.28 | All exported functions must be `pub fn` |
| Dispatcher circular import risk | `observability_engine.py` imports from `metrics.py` | Fallback import path: `from apps.core.observability.metrics import ...` |
| None handling | Rust `&str` cannot accept Python `None` | Dispatcher should guard: `if path is None: return ""` (or callers always provide str) |

---

## WIKI-EXPERT Usage Guide

Spawn WIKI-EXPERT when the team encounters a technical question that documentation can answer. Common scenarios for SPEC-021:

| Scenario | Query Target |
|----------|-------------|
| Rust `regex` crate `replace_all` behavior | `wikis` collection — "regex crate Rust replace_all Cow string" |
| `LazyLock<Regex>` compilation and thread safety | `wikis` collection — "std sync LazyLock Regex thread safe compile once" |
| PyO3 `#[pyfunction]` return types (no Result needed) | `wikis` collection — "PyO3 pyfunction return String without PyResult" |
| `(?i)` case insensitivity in Rust regex | `wikis` collection — "Rust regex case insensitive (?i) flag ASCII Unicode" |
| `\b` word boundary behavior in Rust regex | `wikis` collection — "Rust regex word boundary \\b ASCII behavior" |
| Python `re.sub` vs Rust `replace_all` empty match divergence | `wikis` collection — "Rust regex replace_all empty match Python re.sub difference" |

WIKI-EXPERT is ephemeral — spawned for a single question, delivers results, then terminates.

---

## Pattern Catalog (24 Patterns from metrics.py lines 40–131)

### Group 1: PATH_NORMALIZERS (2 patterns, lines 40–47)

| # | Python Pattern | Flags | Replacement | Rust Static Name |
|---|---------------|-------|-------------|------------------|
| 1 | `/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}(?=/\|$)` | `re.IGNORECASE` | `/{id}` | `RE_UUID` |
| 2 | `/\d+(?=/\|$)` | (none) | `/{id}` | `RE_INT_ID` |

### Group 2: SENSITIVE_ENDPOINT_PATTERNS (16 patterns, lines 75–97)

| # | Python Pattern | Flags | Replacement | Rust Static Name |
|---|---------------|-------|-------------|------------------|
| 3 | `/password[-_]?reset/?` | `re.IGNORECASE` | `/auth-action/` | `RE_PASSWORD_RESET` |
| 4 | `/change[-_]?password/?` | `re.IGNORECASE` | `/auth-action/` | `RE_CHANGE_PASSWORD` |
| 5 | `/reset[-_]?password/?` | `re.IGNORECASE` | `/auth-action/` | `RE_RESET_PASSWORD` |
| 6 | `/forgot[-_]?password/?` | `re.IGNORECASE` | `/auth-action/` | `RE_FORGOT_PASSWORD` |
| 7 | `/token/[^/]+/?` | `re.IGNORECASE` | `/auth/{redacted}/` | `RE_TOKEN_VALUE` |
| 8 | `/token/?` | `re.IGNORECASE` | `/auth/` | `RE_TOKEN` |
| 9 | `/refresh[-_]?token/?` | `re.IGNORECASE` | `/auth-refresh/` | `RE_REFRESH_TOKEN` |
| 10 | `/api[-_]?key/[^/]+/?` | `re.IGNORECASE` | `/key/{redacted}/` | `RE_API_KEY_VALUE` |
| 11 | `/api[-_]?key/?` | `re.IGNORECASE` | `/key/` | `RE_API_KEY` |
| 12 | `/secret/[^/]+/?` | `re.IGNORECASE` | `/{redacted}/` | `RE_SECRET_VALUE` |
| 13 | `/secret/?` | `re.IGNORECASE` | `/{redacted}/` | `RE_SECRET` |
| 14 | `/credential/[^/]+/?` | `re.IGNORECASE` | `/{redacted}/` | `RE_CREDENTIAL_VALUE` |
| 15 | `/credential/?` | `re.IGNORECASE` | `/{redacted}/` | `RE_CREDENTIAL` |
| 16 | `/private[-_]?key/?` | `re.IGNORECASE` | `/{redacted}/` | `RE_PRIVATE_KEY` |
| 17 | `/verify/[^/]+/?` | `re.IGNORECASE` | `/verify/{redacted}/` | `RE_VERIFY_VALUE` |
| 18 | `/activate/[^/]+/?` | `re.IGNORECASE` | `/activate/{redacted}/` | `RE_ACTIVATE_VALUE` |

### Group 3: FALLBACK WORD-BOUNDARY PATTERNS (6 patterns, lines 124–129)

| # | Python Pattern | Flags | Replacement | Rust Static Name |
|---|---------------|-------|-------------|------------------|
| 19 | `\bpassword\b` | `re.IGNORECASE` | `auth` | `RE_FALLBACK_PASSWORD` |
| 20 | `\bsecret\b` | `re.IGNORECASE` | `redacted` | `RE_FALLBACK_SECRET` |
| 21 | `\btoken\b` | `re.IGNORECASE` | `auth` | `RE_FALLBACK_TOKEN` |
| 22 | `\bapi[_-]?key\b` | `re.IGNORECASE` | `key` | `RE_FALLBACK_API_KEY` |
| 23 | `\bprivate[_-]?key\b` | `re.IGNORECASE` | `redacted` | `RE_FALLBACK_PRIVATE_KEY` |
| 24 | `\bcredential\b` | `re.IGNORECASE` | `redacted` | `RE_FALLBACK_CREDENTIAL` |

**Classification**: ALL 24 patterns are simple `re.sub(pattern, replacement, string)` with literal replacement strings. NO capture groups. NO backreferences. `Regex::replace_all()` with string literals is the correct Rust strategy for all 24.
