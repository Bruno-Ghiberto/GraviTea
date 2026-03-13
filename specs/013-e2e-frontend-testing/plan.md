# Implementation Plan: E2E Acceptance Testing via Frontend-Prototype

**Branch**: `013-e2e-frontend-testing` | **Date**: 2026-02-18 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/013-e2e-frontend-testing/spec.md`

## Summary

E2E acceptance testing of all 6 ERP modules (Health, Auth Admin, Inventario, Ventas, Facturacion, Sync) through the frontend-prototype UI, using a 9-agent team with Playwright browser automation, observability monitoring (Prometheus/Jaeger/Loki), and a human-in-the-loop bug-fix feedback loop. Covers 80 test scenarios across 5 test phases (Infrastructure → Authentication → Module CRUD → Cross-Module Integration → Edge Cases). Any bugs found are triaged by ERROR-HANDLER, approved by human, fixed by CODER, and re-verified by TESTER with module-level regression. TECHNICAL-REPORT continuously documents results in `Docs/Tests/REPORT-13.md`.

## Technical Context

**Language/Version**: Python 3.14.3 (backend), TypeScript 5 / Next.js 15 (frontend) — existing code, not new
**Primary Dependencies**: Playwright MCP (browser automation), Prometheus/Jaeger/Loki APIs (monitoring), redis-cli (cache), Docker Compose (infrastructure)
**Storage**: PostgreSQL 18.1 (existing), Redis 7 (existing) — no new storage
**Testing**: Playwright MCP for browser E2E; pytest for any backend fixes; no new test framework
**Target Platform**: Docker Compose on local Windows machine
**Execution Environment**: WSL (Windows Subsystem for Linux) with tmux for multi-pane agent team orchestration
**Project Type**: E2E testing orchestration (NOT code implementation)
**Performance Goals**: All API responses < 2s, all 80 test scenarios complete, zero CRITICAL/HIGH bugs remaining
**Constraints**: No real ARCA certificates (DRAFT only), JWT in React Context (sidebar navigation only), single tenant
**Scale/Scope**: 6 modules, 80 test scenarios (from test-scenarios.md), 9 agents, 5 test phases (A-E mapped to Phases 0-6)

## Constitution Check

*GATE: Passed. Re-check applies to CODER bug fixes only.*

Most principles are **N/A** since we are testing existing code, not building new code. The constitution applies only when CODER writes bug fixes.

| # | Principle | Status | Reasoning |
|---|-----------|--------|-----------|
| I | Ironclad Data Model | N/A → PASS on fixes | No new models; CODER fixes must comply |
| II | Multi-Tenant Isolation | N/A | Testing within single tenant |
| III | Modular Architecture | N/A | No new modules |
| IV | Encryption | PASS (verify) | Test that encrypted fields display correctly |
| V | Secure Auth | PASS (verify) | Testing JWT flow end-to-end |
| VI | Fiscal Compliance | PASS (verify) | Testing ARCA DRAFT operations |
| VII | Offline-First | N/A | Sync module tested but no offline simulation |
| VIII | Query Optimization | N/A → PASS on fixes | No new queries; CODER fixes must comply |
| IX | Secure Data Operations | N/A | No new forms/serializers |
| X | Test-Driven Development | PASS | This entire feature IS testing |
| XI | JWT Authentication | PASS (verify) | Testing token lifecycle |
| XII | Rate Limiting | N/A | Not testing rate limits |
| XIII | Cursor Pagination | PASS (verify) | Testing list endpoints use cursor pagination |
| XIV | API Documentation | N/A | No new endpoints |

**Key rule**: Any bug fix by CODER that creates new code MUST comply with the constitution. This is enforced by ORCHESTRATOR before approving fixes.

## Project Structure

### Documentation (this feature)

```text
specs/013-e2e-frontend-testing/
├── plan.md                    # This file
├── spec.md                    # Feature specification (32 FRs)
├── test-scenarios.md          # 80 test scenarios (canonical source)
├── research.md                # Phase 0: infrastructure verification results
├── quickstart.md              # How to start the test run
├── checklists/
│   └── requirements.md        # Spec quality checklist
└── tasks.md                   # speckit.tasks output (NOT created here)
```

**No `data-model.md`** — we test existing models.
**No `contracts/`** — we test existing APIs.

### Output Files (repository root)

```text
Docs/Tests/REPORT-13.md        # NEW — TECHNICAL-REPORT writes this continuously
frontend-prototype/             # EXISTING — may be ENHANCED by CODER bug fixes
backend/apps/*/                 # EXISTING — may be ENHANCED by CODER bug fixes
```

## Test Scenario Summary

Source: `specs/013-e2e-frontend-testing/test-scenarios.md`

| Module | Prefix | Scenarios | CRITICAL | HIGH | MEDIUM | LOW |
|--------|--------|-----------|----------|------|--------|-----|
| Health | H | 3 | 1 | 0 | 1 | 1 |
| Auth Admin | AU | 16 | 3 | 7 | 4 | 2 |
| Inventario | INV | 20 | 5 | 9 | 4 | 2 |
| Ventas | VEN | 11 | 3 | 5 | 2 | 1 |
| Facturacion | FAC | 17 | 3 | 5 | 5 | 2 |
| Sync | SYN | 10 | 1 | 4 | 3 | 0 |
| Cross-Module | E2E | 3 | 1 | 2 | 0 | 0 |
| **Total** | | **80** | **17** | **32** | **19** | **8** |

Note: 4 scenarios (FAC-005, FAC-006, FAC-031, FAC-032) are ARCA-dependent and may be skipped if homologacion is unavailable.

## Phases

### Phase 0: Infrastructure Verification (Research Equivalent)

**Goal**: Verify that all Docker services, seed data, frontend, observability, and Playwright MCP are operational before testing begins.

**Agents active**: ORCHESTRATOR, BACKEND-EXPERT, THE-WATCHER, REDIS-EXPERT, TECHNICAL-REPORT

| # | Task | Agent | Description |
|---|------|-------|-------------|
| 0.1 | Core Docker stack health | BACKEND-EXPERT | Verify postgres, redis, web, frontend containers are healthy. Check ports 8000, 3000, 5432, 6379. |
| 0.2 | Seed data verification | BACKEND-EXPERT | Run `seed_all`, verify counts: 1 tenant, 5 users, ~10 products, ~26 movements, ~3 customers, ~3 orders, ~5 comprobantes, 1 ARCA credential, 3 PtoVta, 1 CAEA. |
| 0.3 | Observability stack health | THE-WATCHER | Verify Prometheus (:9090), Grafana (:3002), Jaeger (:16686), Loki (:3100), Alertmanager (:9093). Confirm Prometheus scrapes `gravitea-web` target. |
| 0.4 | Redis connectivity | REDIS-EXPERT | `redis-cli ping` → PONG. Verify keys accessible. Check connection count. |
| 0.5 | Frontend accessibility | BACKEND-EXPERT | `http://localhost:3000` loads. Login page renders. No console errors. |
| 0.6 | Playwright MCP connectivity | ORCHESTRATOR | Navigate to frontend, take screenshot, click an element. Confirm browser automation works. |
| 0.7 | Network verification | BACKEND-EXPERT | Confirm `gravitea-shared` network exists. Observability can reach core services. |
| 0.0r | Infrastructure report | TECHNICAL-REPORT | Initialize REPORT-13.md with template. Document all Phase 0 results. |

**Deliverable**: `research.md` documenting all verification results and any issues resolved.
**Gate**: ALL checks pass → HUMAN approves to start testing.

### Phase 1: Agent Team Setup & Quickstart

**Goal**: Configure 9-agent team, initialize report template, write quickstart guide.

**Agents active**: ORCHESTRATOR, TECHNICAL-REPORT

| # | Task | Agent | Description |
|---|------|-------|-------------|
| 1.1 | Write quickstart.md | ORCHESTRATOR | Prerequisites, startup commands, agent launch instructions, report location. |
| 1.2 | Initialize REPORT-13.md | TECHNICAL-REPORT | Create report with sections: Executive Summary (placeholder), Per-Module Results (6 sections), Bug Log, Observability Summary, Final Verdict. |
| 1.3 | Agent context update | ORCHESTRATOR | Run `.specify/scripts/powershell/update-agent-context.ps1 -AgentType claude`. |

**Deliverable**: `quickstart.md`, initialized `Docs/Tests/REPORT-13.md`.

### Phase 2: Authentication Testing (Test Phase B)

**Goal**: Verify login, JWT lifecycle, multi-role access, and logout.

**Agents active**: ORCHESTRATOR, TESTER, BACKEND-EXPERT, TECHNICAL-REPORT

| # | Task | Agent | Description |
|---|------|-------|-------------|
| 2.1 | Admin login | TESTER | Navigate to /login, enter admin credentials, verify sidebar loads with 6 modules. Verify JWT claims in Operations tab (AU-030). |
| 2.2 | Token operations | TESTER | Execute AU-031 (refresh), AU-032 (verify), AU-033 (change password). |
| 2.3 | Logout and re-login | TESTER | Execute AU-035 (logout). Verify redirect to /login. Re-login with new password (or original if AU-033 skipped). |
| 2.4 | Multi-role login cycle | TESTER | Login/logout as vendedor, gerente, deposito. Document which modules each role can access. |
| 2.2b | Auth API monitoring | BACKEND-EXPERT | Monitor API responses during auth tests. Verify 200/205 status codes, correct JWT structure. |
| 2.0r | Auth report update | TECHNICAL-REPORT | Document Phase 2 results: all auth scenarios, role access observations. |

**Gate**: Admin login works, JWT claims correct, all 4 roles can log in → HUMAN approves Phase 3.

### Phase 3: Module CRUD Testing (Test Phase C)

**Goal**: Execute all module-specific scenarios from test-scenarios.md. One sub-phase per module with human gate at each transition.

#### Phase 3.1: Health Module (3 scenarios: H-001 to H-003)

| # | Task | Agent | Description |
|---|------|-------|-------------|
| 3.1.1 | Health scenarios | TESTER | Execute H-001 (page loads, healthy status), H-002 (sub-checks with latency), H-003 (auto-refresh). |
| 3.1.1m | Health observability | THE-WATCHER | Poll Prometheus for health endpoint metrics. |
| 3.1.1r | Health report | TECHNICAL-REPORT | Document Health results in REPORT-13.md. |

#### Phase 3.2: Auth Admin Module (16 scenarios: AU-001 to AU-035)

| # | Task | Agent | Description |
|---|------|-------|-------------|
| 3.2.1 | Users tab scenarios | TESTER | Execute AU-001 (loads seeded users), AU-002 (pagination), AU-003 (nested role/branch). |
| 3.2.2 | Roles tab scenarios | TESTER | Execute AU-010 to AU-014 (list, create, edit, delete, delete-with-users-fails). |
| 3.2.3 | Branches tab scenarios | TESTER | Execute AU-020 (loads branches), AU-021 (read-only check). |
| 3.2.4 | Operations tab scenarios | TESTER | Execute AU-030 to AU-034 (profile, refresh, verify, password change OK, password change fail). AU-035 covered in Phase 2. |
| 3.2.1b | Auth API monitoring | BACKEND-EXPERT | Monitor all auth API calls for correct status codes, response structure. |
| 3.2.1m | Auth observability | THE-WATCHER | Poll Prometheus/Jaeger for auth endpoint metrics and traces. |
| 3.2.1c | Auth cache check | REDIS-EXPERT | Verify JWT blacklist keys exist after logout, TTLs present on auth keys. |
| 3.2.0r | Auth Admin report | TECHNICAL-REPORT | Document Auth Admin results in REPORT-13.md. |

**Gate**: All 16 Auth Admin scenarios pass → HUMAN approves Inventario.

#### Phase 3.3: Inventario Module (20 scenarios: INV-001 to INV-052)

| # | Task | Agent | Description |
|---|------|-------|-------------|
| 3.3.1 | Products tab | TESTER | Execute INV-001 to INV-004 (list, pagination, create, nested names). |
| 3.3.2 | Categories tab | TESTER | Execute INV-010 to INV-012 (tree load, create root, create child). |
| 3.3.3 | Suppliers tab | TESTER | Execute INV-020 to INV-023 (list, search, create, empty search). |
| 3.3.4 | Price Lists tab | TESTER | Execute INV-030 to INV-034 (list, create, edit, set default, delete). |
| 3.3.5 | Movements tab | TESTER | Execute INV-040 to INV-043 (list, create, immutable check, pagination). |
| 3.3.6 | History tabs | TESTER | Execute INV-050 to INV-052 (price history, cost history, read-only check). |
| 3.3.1b | Inventario API monitoring | BACKEND-EXPERT | Monitor all inventario API calls. Verify immutability enforcement returns 405/400. |
| 3.3.1m | Inventario observability | THE-WATCHER | Poll metrics/traces for inventario endpoints. |
| 3.3.0r | Inventario report | TECHNICAL-REPORT | Document Inventario results in REPORT-13.md. |

**Gate**: All 20 Inventario scenarios pass → HUMAN approves Ventas.

#### Phase 3.4: Ventas Module (11 scenarios: VEN-001 to VEN-017)

| # | Task | Agent | Description |
|---|------|-------|-------------|
| 3.4.1 | Customers tab | TESTER | Execute VEN-001 to VEN-003 (list, create Argentine customer, condicion_iva label). |
| 3.4.2 | Orders tab | TESTER | Execute VEN-010 to VEN-017 (list, create order, view detail, add items, confirm, invoice, state guards, total computation). |
| 3.4.1b | Ventas API monitoring | BACKEND-EXPERT | Monitor order state transitions. Verify DRAFT→CONFIRMED→INVOICED status codes. |
| 3.4.1m | Ventas observability | THE-WATCHER | Poll metrics for ventas endpoints. |
| 3.4.0r | Ventas report | TECHNICAL-REPORT | Document Ventas results in REPORT-13.md. |

**Gate**: All 11 Ventas scenarios pass → HUMAN approves Facturacion. **ARCA-EXPERT activation prompt**.

#### Phase 3.5: Facturacion Module (17 scenarios: FAC-001 to FAC-033)

| # | Task | Agent | Description |
|---|------|-------|-------------|
| 3.5.1 | Comprobantes tab | TESTER | Execute FAC-001 to FAC-007 (list, type labels, detail panel, customer fallback, authorize, ARCA errors, status badges). |
| 3.5.2 | Credentials tab | TESTER | Execute FAC-010 to FAC-012 (list, create, production/homologacion display). |
| 3.5.3 | Puntos de Venta tab | TESTER | Execute FAC-020 to FAC-021 (list, create). |
| 3.5.4 | CAEA tab | TESTER | Execute FAC-030 to FAC-033 (list, solicitar, sin-movimiento, button visibility). |
| 3.5.1a | ARCA consultation | ARCA-EXPERT | Advise on FAC-005, FAC-006 (authorize scenarios). Verify ARCA error handling is correct. Read ARCA discovery report + Qdrant RAG. |
| 3.5.1b | Facturacion API monitoring | BACKEND-EXPERT | Monitor comprobante authorization flow. Verify DRAFT→VALIDANDO→AUTORIZADO/RECHAZADO transitions. |
| 3.5.1m | Facturacion observability | THE-WATCHER | Poll metrics/traces for facturacion endpoints. |
| 3.5.0r | Facturacion report | TECHNICAL-REPORT | Document Facturacion results including ARCA-dependent scenario status. |

**Gate**: All non-ARCA-dependent scenarios pass, ARCA scenarios documented → HUMAN approves Sync.

#### Phase 3.6: Sync Module (10 scenarios: SYN-001 to SYN-023)

| # | Task | Agent | Description |
|---|------|-------|-------------|
| 3.6.1 | Sessions tab | TESTER | Execute SYN-001 to SYN-003 (list, register device, unregister). |
| 3.6.2 | Status tab | TESTER | Execute SYN-010 to SYN-012 (query device, non-existent device, detail expansion). |
| 3.6.3 | Operations tab | TESTER | Execute SYN-020 to SYN-023 (pull, pull with filter, push, push invalid JSON). |
| 3.6.1b | Sync API monitoring | BACKEND-EXPERT | Monitor sync push/pull API responses. |
| 3.6.1m | Sync observability | THE-WATCHER | Poll metrics for sync endpoints. |
| 3.6.0r | Sync report | TECHNICAL-REPORT | Document Sync results in REPORT-13.md. |

**Gate**: All 10 Sync scenarios pass → HUMAN approves Cross-Module Integration.

### Phase 4: Cross-Module Integration (Test Phase D)

**Goal**: Execute the 3 end-to-end workflows that span multiple modules.

**Agents active**: ORCHESTRATOR, TESTER, BACKEND-EXPERT, THE-WATCHER, TECHNICAL-REPORT

| # | Task | Agent | Description |
|---|------|-------|-------------|
| 4.1 | E2E-001: Sale-to-Invoice | TESTER | Execute full workflow: login → create customer → create order → add items → confirm → invoice → verify comprobante in Facturacion. |
| 4.2 | E2E-002: Credit Note | TESTER | Identify AUTORIZADO comprobante → attempt credit note creation (document if UI supports or doesn't). |
| 4.3 | E2E-003: Multi-Role Access | TESTER | Login as each of 4 roles, navigate all 6 modules, compile role-permission matrix. |
| 4.1b | Integration API monitoring | BACKEND-EXPERT | Monitor cross-module API calls. Verify data consistency across modules. |
| 4.1m | Integration observability | THE-WATCHER | Check for trace spans crossing module boundaries. |
| 4.0r | Integration report | TECHNICAL-REPORT | Document cross-module results and role-permission matrix in REPORT-13.md. |

**Gate**: All 3 workflows complete, role matrix documented → HUMAN approves Edge Cases.

### Phase 5: Error Injection & Edge Cases (Test Phase E)

**Goal**: Test negative scenarios, validation boundaries, and immutability enforcement.

**Agents active**: ORCHESTRATOR, TESTER, BACKEND-EXPERT, ERROR-HANDLER, TECHNICAL-REPORT

| # | Task | Agent | Description |
|---|------|-------|-------------|
| 5.1 | Duplicate constraints | TESTER | Attempt: duplicate email user, duplicate SKU product, duplicate CUIT customer, duplicate PtoVta numero. Verify error messages. |
| 5.2 | Immutability enforcement | TESTER | Attempt: edit/delete a stock movement, modify an AUTORIZADO comprobante. Verify rejection. |
| 5.3 | FK cascade tests | TESTER | Attempt: delete supplier with linked products, delete role with assigned users. Verify error messages. |
| 5.4 | Amount validation | TESTER | On comprobante detail, verify imp_total = imp_neto + imp_iva + imp_trib + imp_op_ex + imp_tot_conc. |
| 5.5 | Invalid ARCA operations | TESTER | Attempt: authorize comprobante without valid credentials. Verify graceful error. |
| 5.6 | Invalid sync operations | TESTER | Push malformed JSON, pull for non-existent device. Verify error messages. |
| 5.1b | Edge case API monitoring | BACKEND-EXPERT | Monitor all error responses. Verify 400/403/405 status codes with RFC 7807 ProblemDetail format. |
| 5.0r | Edge case report | TECHNICAL-REPORT | Document all edge case results in REPORT-13.md. |

**Gate**: All edge cases documented, error handling verified → HUMAN approves Report Finalization.

### Phase 6: Report Finalization & Verdict

**Goal**: TECHNICAL-REPORT assembles the final report. Human reviews and accepts.

**Agents active**: ORCHESTRATOR, TECHNICAL-REPORT

| # | Task | Agent | Description |
|---|------|-------|-------------|
| 6.1 | Finalize report | TECHNICAL-REPORT | Complete executive summary, per-module pass/fail counts, bug log with all fixes, observability health summary, final verdict. |
| 6.2 | Human review | ORCHESTRATOR | Present final report to human. Options: Accept / Request additional tests. |

**Gate**: Human accepts final report → Feature complete.

## FR Coverage Matrix

| FR | Description | Phase | Task(s) |
|----|------------|-------|---------|
| FR-001 | 9 specialized agents | 1 | 1.1 (team setup) |
| FR-002 | ORCHESTRATOR sole human contact | All | All gate tasks |
| FR-003 | TESTER sole browser operator | 2-5 | All TESTER tasks |
| FR-004 | CODER sole code modifier | On-demand | Bug fix loop |
| FR-004b | Pytest via run-tests-external.sh only | All | All agents running pytest |
| FR-005 | ERROR-HANDLER receives all errors | On-demand | Bug fix loop |
| FR-006 | ARCA-EXPERT for Facturacion only | 3.5 | 3.5.1a |
| FR-006b | TECHNICAL-REPORT continuous docs | All | All `*.0r` tasks |
| FR-007 | Sequential test execution | 2-5 | TESTER tasks sequential |
| FR-008 | Screenshots before/after actions | 2-5 | All TESTER tasks |
| FR-009 | Phase order A→B→C→D→E | 0-5 | Phase numbering enforces order |
| FR-010 | Scenarios from test-scenarios.md | 2-5 | All TESTER tasks reference scenario IDs |
| FR-011 | Sidebar navigation only | 2-5 | All TESTER tasks |
| FR-012 | Errors route to ERROR-HANDLER | On-demand | Bug fix loop step 1 |
| FR-013 | Structured error reports | On-demand | Bug fix loop step 3 |
| FR-014 | Human approves before CODER | On-demand | Bug fix loop step 4 |
| FR-015 | Module-level regression after fix | On-demand | Bug fix loop step 7 |
| FR-016 | Severity → action mapping | On-demand | Bug fix loop |
| FR-017 | THE-WATCHER polls after scenarios | 3-5 | All `*.1m` tasks |
| FR-018 | THE-WATCHER reports anomalies | 3-5 | All `*.1m` tasks |
| FR-019 | REDIS-EXPERT verifies cache | 0, 3.2 | 0.4, 3.2.1c |
| FR-020 | BACKEND-EXPERT monitors containers | 0-5 | All `*.1b` tasks |
| FR-021 | Health module tested | 3.1 | 3.1.1 |
| FR-022 | Auth Admin module tested | 3.2 | 3.2.1-3.2.4 |
| FR-023 | Inventario module tested | 3.3 | 3.3.1-3.3.6 |
| FR-024 | Ventas module tested | 3.4 | 3.4.1-3.4.2 |
| FR-025 | Facturacion module tested | 3.5 | 3.5.1-3.5.4 |
| FR-026 | Sync module tested | 3.6 | 3.6.1-3.6.3 |
| FR-027 | Mandatory human pause points | All gates | Phase gates + bug fix loop |
| FR-028 | No pause for routine ops | 2-5 | TESTER intra-module, monitors |
| FR-029 | Master test report produced | 6 | 6.1 |
| FR-030 | Bug documentation with full context | On-demand | Bug fix loop + TECHNICAL-REPORT |
| FR-031 | Report updated after each event | All | All `*.0r` tasks |
| FR-032 | Report structure (exec summary, modules, bugs, observability, verdict) | 1, 6 | 1.2, 6.1 |

**Coverage**: 33/33 FRs mapped (100%).

## Parallelization Strategy

### Agent Concurrency by Phase

| Phase | TESTER | BACKEND-EXPERT | THE-WATCHER | REDIS-EXPERT | ERROR-HANDLER | CODER | ARCA-EXPERT | TECHNICAL-REPORT |
|-------|--------|---------------|-------------|-------------|--------------|-------|------------|-----------------|
| 0 | - | Active | Active | Active | - | - | - | Active |
| 1 | - | - | - | - | - | - | - | Active |
| 2 | **Sequential** | Parallel | - | - | On-demand | On-demand | - | Parallel |
| 3.1-3.6 | **Sequential** | Parallel | Parallel | Parallel (3.2) | On-demand | On-demand | Active (3.5) | Parallel |
| 4 | **Sequential** | Parallel | Parallel | - | On-demand | On-demand | - | Parallel |
| 5 | **Sequential** | Parallel | - | - | Active | On-demand | - | Parallel |
| 6 | - | - | - | - | - | - | - | **Primary** |

### Key Constraints

- **TESTER is always sequential** — single browser session, one scenario at a time
- **THE-WATCHER, REDIS-EXPERT, BACKEND-EXPERT** run in parallel with TESTER
- **TECHNICAL-REPORT** runs continuously in parallel across all phases
- **ERROR-HANDLER** activates on demand when errors are detected
- **CODER** activates on demand — **halts TESTER while fixing** to prevent testing against broken code
- **ARCA-EXPERT** activates only during Phase 3.5 (Facturacion)
- **Max concurrent agents**: 5 (TESTER + BACKEND-EXPERT + THE-WATCHER + REDIS-EXPERT + TECHNICAL-REPORT)

### Execution Environment

- **WSL + tmux**: The multi-agent team launches in WSL (Windows Subsystem for Linux) using tmux for multi-pane session management. Each agent runs in its own tmux pane.
- **Test Runner Requirement**: Any agent that needs to run backend pytest tests (typically CODER after a fix, or BACKEND-EXPERT for verification) **MUST** use `scripts/run-tests-external.sh` instead of running pytest directly. This avoids consuming tokens with verbose test output inside Claude Code instances.
  - Usage: `bash scripts/run-tests-external.sh "<pytest-command>"`
  - Outputs: `Docs/Tests/{name}.status` (1-line pass/fail), `{name}.summary` (~20-line digest), `{name}.log` (full output — grep only, never read in full)
  - After execution, the agent reads ONLY the `.summary` file. If failures need debugging, use `grep "FAIL\|Error"` on the `.log` file.
  - **NEVER** run `pytest` directly in a Claude Code instance — always delegate to `run-tests-external.sh`.

## Integration Checkpoints (Phase Gates)

| After Phase | Checkpoint | Human Action |
|-------------|-----------|--------------|
| 0 | All infrastructure healthy, seed data verified | Approve to start testing |
| 2 | Auth flow works for all 4 roles | Approve CRUD testing |
| 3.1 | Health module scenarios pass | Approve Auth Admin |
| 3.2 | Auth Admin scenarios pass | Approve Inventario |
| 3.3 | Inventario scenarios pass | Approve Ventas |
| 3.4 | Ventas scenarios pass | Approve Facturacion + ARCA-EXPERT |
| 3.5 | Facturacion scenarios documented | Approve Sync |
| 3.6 | Sync scenarios pass | Approve Cross-Module |
| 4 | Integration workflows complete | Approve Edge Cases |
| 5 | Edge cases documented | Approve Report Finalization |
| 6 | Final report delivered | Accept or request more tests |

## Task Summary

| Category | Count |
|----------|-------|
| TESTER scenario tasks | 25 |
| BACKEND-EXPERT monitoring tasks | 10 |
| THE-WATCHER observability tasks | 7 |
| REDIS-EXPERT cache tasks | 2 |
| ARCA-EXPERT consultation tasks | 1 |
| TECHNICAL-REPORT documentation tasks | 10 |
| ORCHESTRATOR setup/gate tasks | 5 |
| **Total planned tasks** | **~60** |
| **On-demand tasks (bug fix loop)** | Variable (depends on bugs found) |

## Complexity Tracking

No constitution violations requiring justification. The constitution is N/A for most of this feature (testing, not building). CODER bug fixes are constrained by the constitution on a case-by-case basis through the human-approval loop.
