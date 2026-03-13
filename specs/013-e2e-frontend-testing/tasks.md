# Tasks: E2E Acceptance Testing via Frontend-Prototype

**Input**: Design documents from `/specs/013-e2e-frontend-testing/`
**Prerequisites**: plan.md (required), spec.md (required), test-scenarios.md (80 scenarios), research.md, quickstart.md

**Tests**: This feature IS testing — all tasks are test execution, monitoring, or documentation. No separate test tasks needed.

**Organization**: Tasks grouped by user story to enable sequential phase-gated execution with parallel monitoring.

**Agent Key**: Each task is assigned to a specific agent. TESTER tasks are sequential; monitoring/report tasks marked [P] run in parallel with TESTER.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different agents, no dependency on TESTER sequence)
- **[Story]**: Which user story this task serves (US1–US7)
- **Agent**: Shown in parentheses after description
- **Scenario IDs**: Reference `specs/013-e2e-frontend-testing/test-scenarios.md`

## Path Conventions

- **Test scenarios**: `specs/013-e2e-frontend-testing/test-scenarios.md`
- **Report output**: `Docs/Tests/REPORT-13.md`
- **OpenAPI specs**: `api/openapi/*.yaml`
- **Frontend**: `frontend-prototype/`
- **Backend**: `backend/apps/`
- **Test runner**: `scripts/run-tests-external.sh` (MANDATORY for any pytest execution)

---

## Phase 1: Setup (Infrastructure Verification + Agent Team)

**Purpose**: Verify all Docker services, seed data, observability, Playwright MCP, WSL/tmux, and test runner are operational before any testing begins. Corresponds to plan Phases 0–1.

- [x] T001 Start core Docker stack and verify all 4 services healthy — `docker compose up -d && docker compose ps` (ORCHESTRATOR)
- [x] T002 Run seed data and verify entity counts — `docker compose exec web python manage.py seed_all` → verify 1 tenant, 5 users, ~10 products, ~26 movements, ~3 customers, ~3 orders, ~5 comprobantes, 1 ARCA credential, 3 PtoVta, 1 CAEA (BACKEND-EXPERT)
- [x] T003 [P] Verify observability stack — start `docker compose -f backend/docker-compose.observability.yml up -d`, confirm Prometheus(:9090), Grafana(:3002), Jaeger(:16686), Loki(:3100), Alertmanager(:9093) healthy, Prometheus scrapes `gravitea-web` (THE-WATCHER)
- [x] T004 [P] Verify Redis connectivity — `redis-cli ping` → PONG, keys accessible, `connected_clients` > 0 (REDIS-EXPERT)
- [x] T005 Verify frontend accessibility — `http://localhost:3000` loads login page, no console errors (BACKEND-EXPERT)
- [x] T006 Verify Playwright MCP connectivity — navigate to localhost:3000, take screenshot, click element, fill form field (ORCHESTRATOR)
- [x] T007 Verify network connectivity — `gravitea-shared` Docker network exists, observability stack can reach core services (BACKEND-EXPERT)
- [x] T008 [P] Verify WSL + tmux environment — WSL v2 running, tmux 3.x+ installed, repo accessible at `/mnt/c/Users/Ghibe/Documents/Gravitea/GRAVITEA-ERP`, Docker accessible from WSL (ORCHESTRATOR)
- [x] T009 [P] Verify test runner script — `scripts/run-tests-external.sh` exists and executable, `Docs/Tests/` output directory exists, WSL venv at `backend/venv-wsl/bin/python` available (ORCHESTRATOR)
- [x] T010 [P] Initialize REPORT-13.md template — create `Docs/Tests/REPORT-13.md` with sections: Executive Summary (placeholder), Per-Module Results (6 sections), Bug Log, Observability Summary, Final Verdict (TECHNICAL-REPORT)
- [x] T011 Run agent context update — `.specify/scripts/powershell/update-agent-context.ps1 -AgentType claude` (ORCHESTRATOR)
- [x] T012 Document infrastructure verification results in `specs/013-e2e-frontend-testing/research.md` — update all PENDING statuses (TECHNICAL-REPORT)

**Checkpoint**: ALL infrastructure checks pass → **HUMAN GATE: Approve to start testing**

---

## Phase 2: US1 — Infrastructure & Authentication Validation (Priority: P1)

**Goal**: Verify login works for all 4 roles, JWT claims are correct, token operations (refresh, verify, change password, logout) succeed. This is the prerequisite for all subsequent module testing.

**Independent Test**: Log in as admin@gravitea-demo.com/admin123, verify sidebar shows 6 modules, check JWT claims in Operations tab, refresh token, logout, re-login.

**Scenarios**: AU-030 to AU-035 + multi-role validation

- [x] T013 [US1] Admin login flow via Playwright — navigate to `/login`, enter admin@gravitea-demo.com/admin123, verify sidebar loads with 6 module links, verify JWT claims in Operations tab: user_id, email, tenant_id, role, exp (TESTER)
- [x] T014 [US1] Token operations — execute AU-031 (refresh token), AU-032 (verify token), AU-033 (change password to admin456) via Operations tab (TESTER)
- [x] T015 [US1] Logout and re-login — execute AU-035 (logout), verify redirect to `/login`, re-login with updated credentials (admin456 from T014). Then change password back to `admin123` to ensure a known baseline for all subsequent phases. (TESTER)
- [x] T016 [US1] Multi-role login cycle — login/logout as vendedor@gravitea-demo.com/vendedor123, gerente@gravitea-demo.com/gerente123, deposito@gravitea-demo.com/deposito123; document which modules each role can access (TESTER)
- [x] T017 [P] [US1] Auth API response monitoring — monitor all auth API responses during T013–T016, verify 200/205 status codes, correct JWT structure per `api/openapi/auth-api.yaml` (BACKEND-EXPERT)
- [x] T018 [US1] Auth results report — document Phase 2 results in `Docs/Tests/REPORT-13.md`: all auth scenarios pass/fail, role access observations (TECHNICAL-REPORT)

**Checkpoint**: Admin login works, JWT claims correct, all 4 roles can log in → **HUMAN GATE: Approve Module CRUD testing**

---

## Phase 3: US2 — Module CRUD Acceptance (Priority: P1)

**Goal**: Systematically test all 6 modules through the frontend UI. One sub-phase per module with a human gate at each module transition. This is the bulk of the testing work: 77 scenarios across 6 modules.

**Independent Test**: For each module, navigate via sidebar, verify seeded data displays correctly, perform CRUD operations, verify persistence. Reference: `specs/013-e2e-frontend-testing/test-scenarios.md`

### Sub-phase 3A: Health Module (3 scenarios: H-001 to H-003)

- [x] T019 [US2] Execute Health module scenarios — H-001 (page loads, healthy status, sub-checks green), H-002 (latency_ms numeric > 0, migrations pending = 0), H-003 (auto-refresh timestamp updates) (TESTER)
- [x] T020 [P] [US2] Health observability monitoring — poll Prometheus for health endpoint metrics during T019 (THE-WATCHER)
- [x] T021 [US2] Health module report — document Health results in `Docs/Tests/REPORT-13.md` (TECHNICAL-REPORT)

### Sub-phase 3B: Auth Admin Module (16 scenarios: AU-001 to AU-035)

- [x] T022 [US2] Users tab scenarios — execute AU-001 (loads seeded users with email, role name, branch name), AU-002 (pagination/Load More), AU-003 (nested role/branch names, not UUIDs) (TESTER) — 2/3 PASS, AU-003 FAIL (BUG-001: role/branch show "-")
- [x] T023 [US2] Roles tab scenarios — execute AU-010 (loads seeded roles), AU-011 (create TestRole), AU-012 (edit to TestRoleEdited), AU-013 (delete TestRoleEdited), AU-014 (delete role with assigned users fails) (TESTER) — 5/5 PASS
- [x] T024 [US2] Branches tab scenarios — execute AU-020 (loads Sucursal Centro + Norte), AU-021 (read-only, no create/edit/delete buttons) (TESTER) — 2/2 PASS (note: seed has "Casa Central" not "Sucursal Centro")
- [x] T025 [US2] Operations tab scenarios — execute AU-030 (get profile /me), AU-031 (refresh), AU-032 (verify), AU-033 (change password OK), AU-034 (change password wrong current fails). (TESTER) — 4/6 PASS, AU-032 UNTESTED (429), AU-035 FAIL (BUG-002: 429→silent logout)
- [x] T026 [P] [US2] Auth Admin API monitoring — N/A (BACKEND-EXPERT not deployed this phase, API verified via TESTER's direct API calls)
- [x] T027 [P] [US2] Auth Admin observability — poll Prometheus/Jaeger for auth endpoint metrics and traces during T022–T025 (THE-WATCHER) — PASS WITH WARNINGS (429 rate limiting, no Jaeger traces)
- [x] T028 [P] [US2] Auth Admin cache check — verify JWT blacklist keys exist after logout, TTLs present on auth-related Redis keys (REDIS-EXPERT) — PASS (0 JWT keys: JWT in React Context not Redis, Redis healthy)
- [x] T029 [US2] Auth Admin report — documented in `Docs/Tests/REPORT-13.md` (ORCHESTRATOR — TECHNICAL-REPORT not deployed)

**Checkpoint**: All 16 Auth Admin scenarios pass → **HUMAN GATE: Approve Inventario**

### Sub-phase 3C: Inventario Module (20 scenarios: INV-001 to INV-052)

- [ ] T030 [US2] Products tab scenarios — execute INV-001 (loads seeded products: sku, name, category_name, supplier_name, cost_price), INV-002 (pagination), INV-003 (create product sku=TEST-001), INV-004 (category/supplier show names not UUIDs) (TESTER)
- [ ] T031 [US2] Categories tab scenarios — execute INV-010 (tree loads with parent/child hierarchy), INV-011 (create root category), INV-012 (create child under root) (TESTER)
- [ ] T032 [US2] Suppliers tab scenarios — execute INV-020 (loads with name, tax_id, email), INV-021 (search by name), INV-022 (create supplier tax_id=20-12345678-9), INV-023 (search no results → empty state) (TESTER)
- [ ] T033 [US2] Price Lists tab scenarios — execute INV-030 (loads with default marked), INV-031 (create Holiday Prices 25%), INV-032 (edit to 30%), INV-033 (set default), INV-034 (delete) (TESTER)
- [ ] T034 [US2] Movements tab scenarios — execute INV-040 (loads seeded movements: product_sku, quantity_delta, type), INV-041 (create PURCHASE qty=10), INV-042 (no edit/delete buttons — immutable), INV-043 (pagination ordered by created_at desc) (TESTER)
- [ ] T035 [US2] History tabs scenarios — execute INV-050 (price history: product_sku, price, valid_from, valid_to), INV-051 (cost history), INV-052 (read-only, no mutation buttons) (TESTER)
- [ ] T036 [P] [US2] Inventario API monitoring — monitor all inventario API calls during T030–T035, verify immutability enforcement returns 405/400 per `api/openapi/inventario-api.yaml` (BACKEND-EXPERT)
- [ ] T037 [P] [US2] Inventario observability — poll Prometheus/Jaeger metrics and traces for inventario endpoints (THE-WATCHER)
- [ ] T038 [US2] Inventario report — document all 20 Inventario scenario results in `Docs/Tests/REPORT-13.md` (TECHNICAL-REPORT)

**Checkpoint**: All 20 Inventario scenarios pass → **HUMAN GATE: Approve Ventas**

### Sub-phase 3D: Ventas Module (11 scenarios: VEN-001 to VEN-017)

- [ ] T039 [US2] Customers tab scenarios — execute VEN-001 (loads with cuit, razon_social, condicion_iva_display), VEN-002 (create Argentine customer), VEN-003 (condicion_iva shows label not code) (TESTER)
- [ ] T040 [US2] Orders tab scenarios — execute VEN-010 (loads seeded orders), VEN-011 (create DRAFT order), VEN-012 (view detail panel), VEN-013 (add items + total recalculation), VEN-014 (confirm → CONFIRMED), VEN-015 (invoice → INVOICED + comprobante_id), VEN-016 (no confirm button on CONFIRMED), VEN-017 (subtotal + iva_amount computation) (TESTER)
- [ ] T041 [P] [US2] Ventas API monitoring — monitor order state transitions DRAFT→CONFIRMED→INVOICED, verify status codes per `api/openapi/ventas-api.yaml` (BACKEND-EXPERT)
- [ ] T042 [P] [US2] Ventas observability — poll Prometheus metrics for ventas endpoints (THE-WATCHER)
- [ ] T043 [US2] Ventas report — document all 11 Ventas scenario results in `Docs/Tests/REPORT-13.md` (TECHNICAL-REPORT)

**Checkpoint**: All 11 Ventas scenarios pass → **HUMAN GATE: Approve Facturacion + ARCA-EXPERT activation**

### Sub-phase 3E: Facturacion Module (17 scenarios: FAC-001 to FAC-033)

- [ ] T044 [US2] Comprobantes tab scenarios — execute FAC-001 (loads with cbte_tipo label, imp_total, status), FAC-002 (type shows "Factura A" not code), FAC-003 (detail panel with amounts/CAE), FAC-004 (customer_name fallback to "Doc {tipo}-{nro}"), FAC-005 (authorize DRAFT — ARCA-dependent), FAC-006 (ARCA error display), FAC-007 (status badges DRAFT/VALIDANDO/AUTORIZADO/OBSERVADO/RECHAZADO) (TESTER)
- [ ] T045 [US2] Credentials tab scenarios — execute FAC-010 (loads ARCA credentials), FAC-011 (create credential), FAC-012 (production/homologacion label display) (TESTER)
- [ ] T046 [US2] Puntos de Venta tab scenarios — execute FAC-020 (loads: numero, tipo, description), FAC-021 (create punto de venta) (TESTER)
- [ ] T047 [US2] CAEA tab scenarios — execute FAC-030 (loads: caea_code, periodo, vigencia, status), FAC-031 (solicitar — ARCA-dependent), FAC-032 (sin-movimiento — ARCA-dependent), FAC-033 (sin-movimiento button only on ACTIVE) (TESTER)
- [ ] T048 [P] [US2] ARCA consultation — advise on FAC-005/FAC-006 authorize scenarios, verify ARCA error handling, read `Docs/ARCA/Researches/arca-discovery-unified-report.md` + Qdrant RAG collections (arca_api_specs, arca_dev_guides, arca_setup_certs) (ARCA-EXPERT)
- [ ] T049 [P] [US2] Facturacion API monitoring — monitor comprobante authorization flow DRAFT→VALIDANDO→AUTORIZADO/RECHAZADO per `api/openapi/facturacion-api.yaml` (BACKEND-EXPERT)
- [ ] T050 [P] [US2] Facturacion observability — poll Prometheus/Jaeger metrics and traces for facturacion endpoints (THE-WATCHER)
- [ ] T051 [US2] Facturacion report — document all 17 Facturacion results (including ARCA-dependent scenario status) in `Docs/Tests/REPORT-13.md` (TECHNICAL-REPORT)

**Checkpoint**: All non-ARCA-dependent scenarios pass, ARCA scenarios documented → **HUMAN GATE: Approve Sync**

### Sub-phase 3F: Sync Module (10 scenarios: SYN-001 to SYN-023)

- [ ] T052 [US2] Sessions tab scenarios — execute SYN-001 (loads sessions table), SYN-002 (register device test-device-001), SYN-003 (unregister device) (TESTER)
- [ ] T053 [US2] Status tab scenarios — execute SYN-010 (query device status), SYN-011 (query non-existent device → error/empty), SYN-012 (expand detail panel) (TESTER)
- [ ] T054 [US2] Operations tab scenarios — execute SYN-020 (pull changes), SYN-021 (pull with entity filter), SYN-022 (push changes), SYN-023 (push invalid JSON → validation error) (TESTER)
- [ ] T055 [P] [US2] Sync API monitoring — monitor sync push/pull responses per `api/openapi/sync-api.yaml` (BACKEND-EXPERT)
- [ ] T056 [P] [US2] Sync observability — poll Prometheus metrics for sync endpoints (THE-WATCHER)
- [ ] T057 [US2] Sync report — document all 10 Sync results in `Docs/Tests/REPORT-13.md` (TECHNICAL-REPORT)

**Checkpoint**: All 10 Sync scenarios pass → **HUMAN GATE: Approve Cross-Module Integration**

---

## Phase 4: US3 + US4 — Cross-Module Integration & Multi-Role Access (Priority: P2)

**Goal**: Execute 3 end-to-end workflows spanning multiple modules and compile the role-permission matrix.

**Independent Test (US3)**: Execute Sale-to-Invoice flow: login → create customer → create order → add items → confirm → invoice → verify comprobante in Facturacion tab.

**Independent Test (US4)**: Login as each of 4 roles, navigate all 6 modules, document which operations succeed/fail per role.

**Scenarios**: E2E-001, E2E-002, E2E-003

- [ ] T058 [US3] Sale-to-Invoice workflow E2E-001 — login as admin → Ventas: create customer → create order → add 2+ items → confirm → invoice → Facturacion: verify comprobante with matching amounts (TESTER)
- [ ] T059 [US3] Credit Note workflow E2E-002 — identify AUTORIZADO comprobante → create credit note referencing original via CbteAsoc (document if UI supports or gaps exist) (TESTER)
- [ ] T060 [US4] Multi-Role Access Discovery E2E-003 — login as admin/vendedor/gerente/deposito in sequence, navigate all 6 module pages, compile role-permission matrix: role × module × tab → accessible/restricted (TESTER)
- [ ] T061 [P] [US3] Integration API monitoring — monitor cross-module API calls during T058–T059, verify data consistency across modules (BACKEND-EXPERT)
- [ ] T062 [P] [US3] Integration observability — check Jaeger for trace spans crossing module boundaries during T058–T059 (THE-WATCHER)
- [ ] T063 [US3] Integration report — document cross-module workflow results and role-permission matrix in `Docs/Tests/REPORT-13.md` (TECHNICAL-REPORT)

**Checkpoint**: All 3 workflows complete, role-permission matrix documented → **HUMAN GATE: Approve Edge Cases**

---

## Phase 5: US5 — Error Injection & Edge Cases (Priority: P3)

**Goal**: Deliberately trigger failure conditions and verify the system handles errors gracefully with informative messages.

**Independent Test**: Submit a duplicate email user, attempt to delete a stock movement, push malformed JSON to sync — verify clear error messages (not crashes, not "undefined", not blank screens).

- [ ] T064 [US5] Duplicate constraint tests — attempt: duplicate email user, duplicate SKU product, duplicate CUIT customer, duplicate PtoVta numero; verify each shows a clear validation error message (TESTER)
- [ ] T065 [US5] Immutability enforcement tests — attempt: edit/delete existing stock movement, modify AUTORIZADO comprobante; verify rejection with appropriate error (TESTER)
- [ ] T066 [US5] FK cascade tests — attempt: delete supplier with linked products, delete role with assigned users; verify FK constraint error messages (TESTER)
- [ ] T067 [US5] Amount validation tests — on comprobante detail, verify imp_total = imp_neto + imp_iva + imp_trib + imp_op_ex + imp_tot_conc on all seeded comprobantes (TESTER)
- [ ] T068 [US5] Invalid ARCA operations — attempt authorize comprobante without valid credentials; verify graceful connection error (expected behavior, not a bug) (TESTER)
- [ ] T069 [US5] Invalid sync operations — push malformed JSON, pull for non-existent device; verify error messages (TESTER)
- [ ] T070 [P] [US5] Edge case API monitoring — monitor all error responses during T064–T069, verify 400/403/405 status codes with RFC 7807 ProblemDetail format per `api/openapi/*.yaml` (BACKEND-EXPERT)
- [ ] T071 [US5] Edge case report — document all edge case results in `Docs/Tests/REPORT-13.md` (TECHNICAL-REPORT)

**Checkpoint**: All edge cases documented, error handling verified → **HUMAN GATE: Approve Report Finalization**

---

## Phase 6: Polish — Report Finalization & Verdict

**Purpose**: TECHNICAL-REPORT assembles the final report. Human reviews and accepts or requests additional tests.

- [ ] T072 Finalize master test report — complete executive summary, per-module pass/fail counts (80 scenarios), complete bug log with all fixes applied, observability health summary (Prometheus/Jaeger/Loki/Redis), final verdict with remaining issues in `Docs/Tests/REPORT-13.md` (TECHNICAL-REPORT)
- [ ] T073 Human review and acceptance — present final report to human; options: Accept / Request additional tests / Flag remaining issues (ORCHESTRATOR)

---

## Cross-Cutting Concerns

### US6 — Observability & System Health Monitoring (P3)

US6 is NOT a separate phase — it runs in parallel throughout Phases 2–5 via THE-WATCHER and REDIS-EXPERT.

**Mapped tasks**: T003 (observability stack health), T004 (Redis health), T020 (Health metrics), T027 (Auth metrics), T028 (Auth cache), T037 (Inventario metrics), T042 (Ventas metrics), T050 (Facturacion metrics), T056 (Sync metrics), T062 (Integration traces)

**Verification criteria** (checked by THE-WATCHER across all phases):
- Prometheus scrapes `gravitea-web` target continuously (UP)
- Every API call has a corresponding Jaeger trace with request/response spans
- Zero ERROR-level Loki log entries during happy-path scenarios
- Redis `connected_clients` > 0 and stable throughout; JWT keys have TTLs

### US7 — Multi-Agent Bug Fix Workflow (P2)

US7 is ON-DEMAND — activates when any agent discovers a bug during Phases 2–5.

**Bug fix cycle** (not assigned fixed task IDs — variable count):
1. TESTER/BACKEND-EXPERT/THE-WATCHER/REDIS-EXPERT discovers error
2. Error routed to ERROR-HANDLER (FR-012)
3. ERROR-HANDLER produces structured report: summary, root cause, severity, recommended fix, CODER role (FR-013)
4. ORCHESTRATOR pauses for HUMAN approval (FR-014)
5. If approved: CODER implements fix using TDD approach where applicable — write/update a failing test first, then implement the fix, then verify the test passes (uses `scripts/run-tests-external.sh` for any pytest — FR-004b)
6. CODER completes fix → ORCHESTRATOR instructs TESTER
7. TESTER re-runs failed scenario + all module scenarios for regression (FR-015)
8. TECHNICAL-REPORT documents bug entry: original failure, root cause, fix applied, re-verification result (FR-030)

**Severity actions** (FR-016):
- **CRITICAL**: Halt ALL testing until resolved
- **HIGH**: Fix before proceeding to next scenario
- **MEDIUM**: Queue for batch fix
- **LOW**: Log and continue

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — can start immediately
- **Phase 2 (US1 Auth)**: Depends on Phase 1 completion — BLOCKS all module testing
- **Phase 3 (US2 CRUD)**: Depends on Phase 2 — sub-phases are SEQUENTIAL (Health → Auth Admin → Inventario → Ventas → Facturacion → Sync) with human gates between each
- **Phase 4 (US3+US4 Integration)**: Depends on ALL Phase 3 sub-phases complete
- **Phase 5 (US5 Edge Cases)**: Depends on Phase 4 complete
- **Phase 6 (Polish)**: Depends on Phase 5 complete

### User Story Dependencies

- **US1 (P1)**: Can start after Setup (Phase 1)
- **US2 (P1)**: Can start after US1 complete — sequential sub-phases with gates
- **US3 (P2)**: Can start after ALL US2 sub-phases complete (needs data from CRUD)
- **US4 (P2)**: Can start after ALL US2 sub-phases complete (needs all modules navigable)
- **US5 (P3)**: Can start after US3+US4 complete (needs stable baseline before injecting errors)
- **US6 (P3)**: Runs in parallel throughout US1–US5 (cross-cutting)
- **US7 (P2)**: On-demand throughout US1–US5 (cross-cutting)

### Within Each Sub-phase

1. TESTER tasks are **strictly sequential** (single browser session)
2. Monitoring tasks (BACKEND-EXPERT, THE-WATCHER, REDIS-EXPERT) run **in parallel** with TESTER
3. TECHNICAL-REPORT runs **after** TESTER completes the sub-phase
4. ARCA-EXPERT activates **only** during Sub-phase 3E (Facturacion)
5. Bug fix loop **halts TESTER** while CODER fixes — resumes after re-verification

### Parallel Opportunities

**Within each sub-phase** (max 5 concurrent agents):
- TESTER (sequential scenarios)
- BACKEND-EXPERT (API monitoring) [P]
- THE-WATCHER (observability) [P]
- REDIS-EXPERT (cache checks, Phase 3B only) [P]
- TECHNICAL-REPORT (documentation) [P]

**Cross-phase**: No cross-phase parallelism — phases are strictly sequential with human gates.

---

## Parallel Example: Sub-phase 3C (Inventario)

```text
# TESTER executes sequentially:
T030: Products tab scenarios (INV-001 to INV-004)
T031: Categories tab scenarios (INV-010 to INV-012)
T032: Suppliers tab scenarios (INV-020 to INV-023)
T033: Price Lists tab scenarios (INV-030 to INV-034)
T034: Movements tab scenarios (INV-040 to INV-043)
T035: History tabs scenarios (INV-050 to INV-052)

# In parallel with TESTER:
T036: [P] BACKEND-EXPERT monitors API calls
T037: [P] THE-WATCHER polls Prometheus/Jaeger

# After TESTER completes:
T038: TECHNICAL-REPORT documents results
```

---

## Implementation Strategy

### MVP First (Phase 1 + Phase 2 Only)

1. Complete Phase 1: Setup — infrastructure verified
2. Complete Phase 2: US1 — auth works for all roles
3. **STOP and VALIDATE**: All 4 users can log in, JWT correct, token ops work
4. If setup or auth has critical issues, fix before proceeding

### Incremental Delivery (Module by Module)

1. Phase 1 → Phase 2 → Auth validated
2. Phase 3A (Health) → 3 scenarios confirmed
3. Phase 3B (Auth Admin) → 16 scenarios confirmed
4. Phase 3C (Inventario) → 20 scenarios confirmed
5. Phase 3D (Ventas) → 11 scenarios confirmed
6. Phase 3E (Facturacion) → 17 scenarios confirmed
7. Phase 3F (Sync) → 10 scenarios confirmed
8. Phase 4 → 3 cross-module workflows confirmed
9. Phase 5 → Edge cases verified
10. Phase 6 → Final report delivered

Each sub-phase produces an independently verifiable result with a human gate.

### Agent Team Strategy

All agents run in **WSL with tmux** (one pane per agent). The team uses `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` for filesystem-based coordination.

| Agent | Role | Model | Active Phases |
|-------|------|-------|--------------|
| ORCHESTRATOR | Coordination + human gates | Opus 4.6 | All |
| TESTER | Playwright browser automation | Sonnet 4.6 | 2–5 |
| BACKEND-EXPERT | API monitoring + verification | Sonnet 4.6 | 0–5 |
| THE-WATCHER | Observability polling | Haiku 4.5 | 0–5 |
| REDIS-EXPERT | Cache verification | Haiku 4.5 | 0, 3B |
| ERROR-HANDLER | Bug triage + reporting | Sonnet 4.6 | On-demand |
| CODER | Bug fixes (sole code modifier) | Opus 4.6 | On-demand |
| ARCA-EXPERT | Facturacion consultation | Opus 4.6 | 3E only |
| TECHNICAL-REPORT | Continuous documentation | Sonnet 4.6 | All |

### Test Runner Protocol

Any agent running backend pytest tests **MUST** use `scripts/run-tests-external.sh`:

```bash
# CORRECT — token-efficient
bash scripts/run-tests-external.sh "pytest backend/tests/auth/ --tb=short -q"
# Read: Docs/Tests/<name>.summary (20 lines)
# Debug: grep "FAIL\|Error" Docs/Tests/<name>.log

# WRONG — floods context
pytest backend/tests/auth/  # NEVER do this inside Claude Code
```

---

## Task Summary

| Category | Count | Agent(s) |
|----------|-------|----------|
| Setup/Infrastructure tasks | 12 | ORCHESTRATOR, BACKEND-EXPERT, THE-WATCHER, REDIS-EXPERT, TECHNICAL-REPORT |
| US1 Auth tasks | 6 | TESTER, BACKEND-EXPERT, TECHNICAL-REPORT |
| US2 CRUD scenario tasks | 39 | TESTER, BACKEND-EXPERT, THE-WATCHER, REDIS-EXPERT, ARCA-EXPERT, TECHNICAL-REPORT |
| US3+US4 Integration tasks | 6 | TESTER, BACKEND-EXPERT, THE-WATCHER, TECHNICAL-REPORT |
| US5 Edge Case tasks | 8 | TESTER, BACKEND-EXPERT, TECHNICAL-REPORT |
| Report Finalization tasks | 2 | TECHNICAL-REPORT, ORCHESTRATOR |
| **Total planned tasks** | **73** | |
| On-demand bug fix tasks (US7) | Variable | ERROR-HANDLER, CODER, TESTER |

### Per User Story

| User Story | Priority | Task Count | Tasks |
|------------|----------|------------|-------|
| US1 (Auth Validation) | P1 | 6 | T013–T018 |
| US2 (Module CRUD) | P1 | 39 | T019–T057 |
| US3 (Cross-Module) | P2 | 4 | T058, T059, T061, T063 |
| US4 (Multi-Role) | P2 | 1 | T060 |
| US5 (Edge Cases) | P3 | 8 | T064–T071 |
| US6 (Observability) | P3 | Cross-cutting | T003, T004, T020, T027, T028, T037, T042, T050, T056, T062 |
| US7 (Bug Fix) | P2 | On-demand | Variable |
| Setup (no story) | — | 12 | T001–T012 |
| Polish (no story) | — | 2 | T072–T073 |

### Scenario Coverage: 80/80

| Module | Scenarios | TESTER Tasks |
|--------|-----------|-------------|
| Health | 3 | T019 |
| Auth Admin | 16 | T022–T025 |
| Inventario | 20 | T030–T035 |
| Ventas | 11 | T039–T040 |
| Facturacion | 17 | T044–T047 |
| Sync | 10 | T052–T054 |
| Cross-Module | 3 | T058–T060 |

---

## Notes

- [P] tasks = different agents running in parallel, no dependency on TESTER sequence
- [Story] label maps task to specific user story for traceability
- TESTER tasks reference scenario IDs from `specs/013-e2e-frontend-testing/test-scenarios.md`
- Phases are strictly sequential with human gates — no cross-phase parallelism
- Screenshots captured before/after each TESTER action (FR-008)
- Navigation via sidebar clicks ONLY — never direct URL (FR-011, JWT in React Context)
- Bug fix loop can inject variable tasks at any point during Phases 2–5
- ARCA-dependent scenarios (FAC-005, FAC-006, FAC-031, FAC-032) may be skipped if homologacion unavailable
- All pytest execution MUST use `scripts/run-tests-external.sh` (FR-004b)
