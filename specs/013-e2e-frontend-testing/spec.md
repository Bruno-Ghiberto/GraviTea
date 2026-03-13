# Feature Specification: E2E Acceptance Testing via Frontend-Prototype

**Feature Branch**: `013-e2e-frontend-testing`
**Created**: 2026-02-18
**Status**: Draft
**Input**: End-to-end acceptance testing of all 6 ERP modules through the frontend-prototype UI with multi-agent orchestration, observability monitoring, and human-in-the-loop bug-fix workflow.

## User Scenarios & Testing

### User Story 1 — Infrastructure & Authentication Validation (Priority: P1)

As the **human operator**, I want to verify that the full Docker stack (core + observability) starts correctly with seeded data, and that I can log in through the frontend-prototype and see valid JWT claims, so that I have a trustworthy baseline before testing any module.

**Why this priority**: Nothing else can be tested if infrastructure is broken or authentication doesn't work. This is the prerequisite for all subsequent testing.

**Independent Test**: Start both Docker compose stacks, seed data, open `http://localhost:3000`, log in with `admin@gravitea-demo.com` / `admin123`, navigate to Tokens tab and verify decoded JWT claims (user_id, email, tenant_id, role, exp).

**Acceptance Scenarios**:

1. **Given** the core Docker stack is not running, **When** the operator runs `docker compose up -d`, **Then** all 4 services (postgres, redis, web, frontend) reach healthy status within 120 seconds.
2. **Given** healthy core services, **When** the operator runs `docker compose exec web python manage.py seed_all`, **Then** seed data is created: 1 tenant, 4 users, ~10 products, ~26 movements, ~3 customers, ~3 orders, 5 comprobantes, 1 ARCA credential, 3 PtoVta, 1 CAEA.
3. **Given** the observability stack is not running, **When** the operator runs `docker compose -f backend/docker-compose.observability.yml up -d`, **Then** all 6 observability services (Prometheus, Grafana, Jaeger, Loki, Promtail, Alertmanager) start and Prometheus scrapes the `gravitea-web` target.
4. **Given** frontend is accessible at `http://localhost:3000`, **When** the user enters valid admin credentials, **Then** the sidebar loads with all 6 module links and the Tokens tab shows decoded JWT with `tenant_id`, `role`, and `email` claims.
5. **Given** a logged-in admin session, **When** the user clicks "Refresh Token", **Then** a new access token is issued with updated `exp` timestamp.
6. **Given** a logged-in session, **When** the user refreshes the browser page, **Then** the JWT is lost (React Context cleared) and the user is redirected to `/login`.

---

### User Story 2 — Module CRUD Acceptance (Priority: P1)

As the **human operator**, I want to systematically navigate each of the 6 ERP modules through the frontend-prototype and verify that all CRUD operations (create, read, update, delete) work correctly against the backend API, so that I can confirm every backend endpoint is functional and data displays correctly.

**Why this priority**: This is the core purpose of the testing — exercising every backend endpoint through the UI. Without this, the ERP cannot be considered functional.

**Independent Test**: For each module, navigate to its page via the sidebar, verify seeded data appears correctly in tables, perform create/update/delete operations, and verify the changes persist. Reference: `specs/013-e2e-frontend-testing/test-scenarios.md` module sections (H, AU, INV, VEN, FAC, SYN).

**Acceptance Scenarios**:

1. **Given** a logged-in admin and seeded data, **When** navigating to Health module, **Then** health status shows PostgreSQL connected, Redis connected, and response time below 500ms.
2. **Given** seeded users exist, **When** navigating to Auth Admin → Users tab, **Then** table shows 4 users with correct email, role name, and branch name (no "-" or "undefined").
3. **Given** seeded products exist, **When** navigating to Inventario → Products tab, **Then** table shows ~10 products with correct SKU, name, category, prices. Creating a new product with unique SKU succeeds; duplicate SKU shows error.
4. **Given** seeded movements exist, **When** navigating to Inventario → Stock Movements tab, **Then** 26 PURCHASE movements display with correct `quantity_delta`. Creating a new movement succeeds; attempting to update or delete an existing movement **fails** (immutable ledger).
5. **Given** seeded customers and orders exist, **When** navigating to Ventas module, **Then** ~3 customers and ~3 sale orders display. Creating a new DRAFT order succeeds. Adding items updates totals. Confirming an order changes status to CONFIRMED and locks editing.
6. **Given** seeded comprobantes exist, **When** navigating to Facturacion → Comprobantes tab, **Then** 5 DRAFT comprobantes display with correct amounts. Customer column shows fallback text for null customers. Amount equation (imp_total = imp_neto + imp_iva + imp_trib + imp_op_ex + imp_tot_conc) balances on all comprobantes.
7. **Given** no sync devices exist in seed data, **When** navigating to Sync module, **Then** Sessions and Pending Ops tabs load without errors (empty state is expected).

---

### User Story 3 — Cross-Module Integration Workflows (Priority: P2)

As the **human operator**, I want to execute end-to-end business workflows that span multiple modules (inventory → sales → invoicing), so that I can verify the modules work together as an integrated system.

**Why this priority**: Individual module CRUD is necessary but not sufficient. Real business value comes from the integration between modules.

**Independent Test**: Execute the Sale-to-Invoice flow from the test scenario matrix: verify product stock → create purchase movement → create customer → create order → add items → confirm order → create invoice. Reference: `specs/013-e2e-frontend-testing/test-scenarios.md` section "Cross-Module Workflows (E2E)" — scenario E2E-001.

**Acceptance Scenarios**:

1. **Given** a product with known stock, **When** a PURCHASE movement is created for qty=20, **Then** the stock_snapshot reflects the increase, visible in the product's stock display.
2. **Given** a customer and a product with stock, **When** a sale order is created with items and confirmed, **Then** the order status becomes CONFIRMED and items are locked from editing.
3. **Given** a confirmed sale order, **When** a corresponding DRAFT Factura A comprobante is created with matching amounts, **Then** the comprobante displays correct imp_neto, imp_iva, and imp_total. AlicIva entries sum to imp_iva.
4. **Given** an existing Factura B, **When** a Nota de Credito B is created referencing it via CbteAsoc, **Then** the NC displays the association and amounts match the original.

---

### User Story 4 — Multi-Role Access Verification (Priority: P2)

As the **human operator**, I want to log in with different user roles (admin, gerente, vendedor, deposito) and verify that each role sees the appropriate modules and can only perform authorized actions, so that role-based access control is confirmed.

**Why this priority**: Security and access control are fundamental ERP requirements. Each role must have correct boundaries.

**Independent Test**: Log in with each of the 4 seeded users and verify which modules are accessible, which CRUD operations succeed, and which are denied.

**Acceptance Scenarios**:

1. **Given** admin credentials, **When** logged in, **Then** all 6 modules are accessible and all CRUD operations succeed.
2. **Given** vendedor credentials, **When** logged in, **Then** TESTER exercises all 6 modules and documents which operations succeed and which are denied. The discovered permissions are recorded in the test report as the baseline role-access matrix.
3. **Given** deposito credentials, **When** logged in, **Then** TESTER exercises all 6 modules and documents which operations succeed and which are denied. Deposito is expected to have more restrictions than vendedor.
4. **Given** gerente credentials, **When** logged in, **Then** TESTER exercises all 6 modules and documents the permission level. Gerente is expected to have broader access than vendedor but may differ from admin.

---

### User Story 5 — Error Injection & Edge Case Validation (Priority: P3)

As the **human operator**, I want to deliberately trigger failure conditions (duplicate keys, constraint violations, immutability breaches, invalid data) through the frontend, so that I can verify the system handles errors gracefully with informative messages rather than crashes.

**Why this priority**: A system that works only on the happy path is incomplete. Error handling defines the production-readiness of the backend.

**Independent Test**: Execute each edge case from the test scenario matrix and verify the frontend shows an appropriate error message (not a crash, not "undefined", not a blank screen).

**Acceptance Scenarios**:

1. **Given** a user with email `admin@gravitea-demo.com` exists, **When** creating another user with the same email, **Then** the frontend displays a clear "duplicate email" error.
2. **Given** a PURCHASE stock movement exists, **When** attempting to update or delete it, **Then** the operation is rejected (immutable ledger enforcement).
3. **Given** a supplier with linked products, **When** attempting to delete the supplier, **Then** the operation is rejected with a foreign key constraint message.
4. **Given** a comprobante where imp_total does not equal the sum of components, **When** submitting, **Then** ARCA amount validation rejects the comprobante with a clear error.
5. **Given** no real ARCA certificates, **When** attempting to authorize a comprobante, **Then** the system returns a connection error (expected behavior) without crashing.

---

### User Story 6 — Observability & System Health Monitoring (Priority: P3)

As the **human operator**, I want real-time monitoring of the backend's health (metrics, traces, logs, cache) during the entire test run, so that I can detect performance degradation, missing instrumentation, or silent failures that the UI tests alone wouldn't catch.

**Why this priority**: The UI may appear to work while the backend silently drops traces, leaks connections, or fails to populate cache. Monitoring catches what UI testing misses.

**Independent Test**: While TESTER executes scenarios, THE-WATCHER polls Prometheus/Jaeger/Loki and REDIS-EXPERT checks cache. Any 5xx, missing trace, error log, or cache anomaly is flagged.

**Acceptance Scenarios**:

1. **Given** both Docker stacks are running, **When** Prometheus is queried, **Then** the `gravitea-web:8080` scrape target shows as UP.
2. **Given** TESTER performs API calls through the frontend, **When** Jaeger is queried, **Then** each API call has a corresponding trace with request/response spans.
3. **Given** normal test operations, **When** Loki is queried for ERROR-level logs, **Then** zero error logs appear during happy-path scenarios.
4. **Given** a user logs in, **When** Redis key count is checked, **Then** at least one JWT-related key exists with a TTL.
5. **Given** repeated API requests, **When** Redis hit/miss ratio is checked, **Then** the cache hit ratio is greater than zero.

---

### User Story 7 — Multi-Agent Bug Fix Workflow (Priority: P2)

As the **human operator**, I want a structured workflow where discovered bugs are analyzed by ERROR-HANDLER, presented to me with root-cause analysis and fix recommendations, and then fixed by CODER after my approval, so that problems are resolved systematically without me having to diagnose every issue myself.

**Why this priority**: Without a structured bug-fix workflow, testing becomes chaotic. The human operator needs filtered, actionable reports — not raw error dumps.

**Independent Test**: When TESTER finds a bug (e.g., field mismatch), the report flows: TESTER → ERROR-HANDLER → ORCHESTRATOR → human approval → CODER fixes → TESTER re-verifies.

**Acceptance Scenarios**:

1. **Given** TESTER encounters a UI crash, **When** the error is sent to ERROR-HANDLER, **Then** ERROR-HANDLER produces a digested report with: problem summary, root cause, recommended fix, severity, and suggested CODER role.
2. **Given** ERROR-HANDLER sends a report to ORCHESTRATOR, **When** the report arrives, **Then** ORCHESTRATOR pauses and presents the report to the human with "Approve / Reject / Modify / Skip" options.
3. **Given** the human approves a fix, **When** ORCHESTRATOR assigns CODER, **Then** CODER receives the role assignment (backend-architect/python-expert/frontend-architect/system-architect) and specific fix instructions.
4. **Given** CODER implements a fix, **When** ORCHESTRATOR instructs TESTER to re-run the failed scenario, **Then** TESTER re-executes and reports pass/fail.

---

### Edge Cases

- What happens when a Docker container crashes mid-test? (BACKEND-EXPERT or THE-WATCHER detects and reports to ERROR-HANDLER)
- What happens when the JWT token expires during a long test run? (TESTER re-authenticates automatically or ORCHESTRATOR instructs re-login)
- What happens when seed data has duplicates from a previous `seed_all --clear` run? (Run `seed_all --clear` once more to reset cleanly)
- What happens when the observability stack can't connect to the core stack? (THE-WATCHER reports connectivity failure; verify `gravitea-shared` network exists)
- What happens when CODER's fix introduces a new bug? (TESTER catches it in re-verification → new bug enters the same fix loop)
- What happens when multiple agents report the same underlying issue? (ERROR-HANDLER deduplicates before sending to ORCHESTRATOR)

## Requirements

### Functional Requirements

#### Agent Team & Orchestration

- **FR-001**: The system MUST support 9 specialized agents working as a coordinated team: ORCHESTRATOR, TESTER, BACKEND-EXPERT, THE-WATCHER, REDIS-EXPERT, ERROR-HANDLER, CODER, ARCA-EXPERT, TECHNICAL-REPORT.
- **FR-002**: ORCHESTRATOR MUST be the only agent that communicates with the human operator for approvals and decisions.
- **FR-003**: TESTER MUST be the only agent that interacts with the frontend browser.
- **FR-004**: CODER MUST be the only agent that modifies source code files. No other agent may write to backend or frontend source code.
- **FR-004b**: Any agent that needs to run backend pytest tests MUST use `scripts/run-tests-external.sh` instead of invoking pytest directly. This preserves token efficiency in Claude Code instances by delegating test execution to an external process. Agents read only the summary output file, not the full log.
- **FR-005**: ERROR-HANDLER MUST receive all error reports from TESTER, BACKEND-EXPERT, THE-WATCHER, and REDIS-EXPERT. It MUST NOT fix anything — only analyze and report.
- **FR-006**: ARCA-EXPERT MUST only be activated during Facturacion module testing and MUST use the ARCA discovery report and semantic search collections as primary knowledge sources.
- **FR-006b**: TECHNICAL-REPORT MUST continuously document the testing process by writing a professional report to `Docs/Tests/REPORT-13.md`. It MUST NOT execute tests, fix code, or interact with the browser — only observe and document.

#### Test Execution

- **FR-007**: TESTER MUST execute test scenarios sequentially, one at a time, through the browser.
- **FR-008**: TESTER MUST capture a screenshot before and after each user action during a scenario.
- **FR-009**: Test execution MUST follow the phase order: A (Infrastructure) → B (Authentication) → C (Module CRUD) → D (Cross-Module) → E (Edge Cases).
- **FR-010**: The canonical test scenarios MUST be sourced from `specs/013-e2e-frontend-testing/test-scenarios.md` (80 scenarios across 7 categories). The spec MUST NOT duplicate those scenarios but reference them.
- **FR-011**: TESTER MUST navigate the frontend via sidebar link clicks (NOT direct URL navigation) to preserve the authentication session.

#### Bug Fix Workflow

- **FR-012**: When any agent detects an error, it MUST route the report to ERROR-HANDLER (not directly to ORCHESTRATOR).
- **FR-013**: ERROR-HANDLER MUST produce a structured report containing: problem summary, root cause analysis, recommended fix with file paths, severity classification (CRITICAL/HIGH/MEDIUM/LOW), and suggested CODER role.
- **FR-014**: ORCHESTRATOR MUST pause for human approval before assigning any fix to CODER.
- **FR-015**: After CODER implements a fix, TESTER MUST re-run the previously failed scenario AND all other scenarios in the same module to verify the fix and detect regressions.
- **FR-016**: CRITICAL severity issues MUST halt all testing until resolved. HIGH severity MUST be fixed before proceeding to the next scenario. MEDIUM and LOW may be queued.

#### Monitoring

- **FR-017**: THE-WATCHER MUST poll the metrics, tracing, logging, and alerting services after each test scenario completes.
- **FR-018**: THE-WATCHER MUST report any server errors, response times exceeding 2 seconds, missing traces, error-level log entries, or firing alerts.
- **FR-019**: REDIS-EXPERT MUST verify cache connection health, key population, TTL presence on authentication-related keys, and stable connection counts.
- **FR-020**: BACKEND-EXPERT MUST monitor container logs for application errors, missing endpoint responses, database connection failures, and migration issues.

#### Module Coverage

- **FR-021**: Health module MUST be tested for liveness, readiness, and authenticated health check with dependency status.
- **FR-022**: Auth Admin module MUST be tested for: Users CRUD (create, list, update, delete), Branches listing, Roles CRUD, Token operations (verify, refresh).
- **FR-023**: Inventario module MUST be tested for: Products CRUD, Categories tree navigation, Suppliers CRUD (with encrypted field verification), Stock Movements (immutable ledger enforcement), Price Lists CRUD, Price/Cost History display.
- **FR-024**: Ventas module MUST be tested for: Customers CRUD (with document validation), Sale Orders lifecycle (DRAFT → CONFIRMED → CANCELLED), Order Items add/remove, totals recalculation.
- **FR-025**: Facturacion module MUST be tested for: Credentials display, Puntos de Venta CRUD, Comprobantes CRUD (DRAFT only — amount validation, immutability enforcement on non-DRAFT), CAEA display, IVA detail, associated document references for credit notes.
- **FR-026**: Sync module MUST be tested for: Sessions listing, Push/Pull interface display, Device Status interface.

#### Human-in-the-Loop

- **FR-027**: ORCHESTRATOR MUST pause for human input at these events: bug fix approval, phase transitions, CRITICAL severity issues, ARCA module entry, CODER role ambiguity, test completion.
- **FR-028**: ORCHESTRATOR MUST NOT pause for routine operations: TESTER proceeding within a module, monitoring agents polling, ERROR-HANDLER processing reports.

#### Evidence & Reporting

- **FR-029**: The testing process MUST produce a final master test report with per-module pass/fail verdicts and cumulative evidence. TECHNICAL-REPORT is responsible for writing and maintaining this report at `Docs/Tests/REPORT-13.md`.
- **FR-030**: Every bug found and fixed MUST be documented with: original failure description, root cause, fix applied, re-verification result. TECHNICAL-REPORT MUST append each bug entry as it is resolved.
- **FR-031**: TECHNICAL-REPORT MUST update the report after each significant event: phase transitions, bug discoveries, fix completions, re-verifications, and phase gate decisions.
- **FR-032**: The report MUST include: executive summary, per-module test results with pass/fail counts, a bugs-found-and-resolved log, observability health summary, and a final verdict with remaining issues (if any).

### Key Entities

- **Test Scenario**: A single testable interaction with the frontend (e.g., "Create a product with SKU TEST-001"). Has a module, phase, pass/fail status, and optional screenshot evidence.
- **Bug Report**: A structured document produced by ERROR-HANDLER. Contains summary, root cause, severity, recommended fix, and CODER role assignment.
- **Phase Gate**: A transition point between test phases (A→B→C→D→E) requiring human approval with a summary of results.
- **Agent Team**: The 9-agent configuration with defined roles, communication paths, and model assignments.
- **Test Report**: The living document at `Docs/Tests/REPORT-13.md` maintained by TECHNICAL-REPORT throughout the test run. Contains executive summary, per-module results, bug log, and final verdict.

## Success Criteria

### Measurable Outcomes

- **SC-001**: All 6 ERP modules (Health, Auth Admin, Inventario, Ventas, Facturacion, Sync) pass their CRUD test scenarios with zero CRITICAL or HIGH severity issues remaining.
- **SC-002**: All 3 cross-module integration workflows (sale-to-invoice, credit note, multi-role access) complete successfully.
- **SC-003**: The observability stack reports zero server errors and zero missing traces during the complete test run.
- **SC-004**: The cache system is operational: keys are populated after authentication, TTLs are present, and connections remain stable throughout testing.
- **SC-005**: Every bug discovered during testing has a documented fix with re-verification evidence (before/after screenshots + pass confirmation).
- **SC-006**: A comprehensive test report is delivered with per-module verdicts, evidence screenshots, and a summary of all bugs found and resolved.
- **SC-007**: Error injection tests (duplicate constraints, immutability violations, FK cascades, invalid ARCA operations) produce clear user-facing error messages — no crashes, no "undefined", no blank screens.
- **SC-008**: If bugs are discovered during testing, the multi-agent workflow processes at least one complete bug-fix cycle end-to-end: detection → analysis → human approval → fix → re-verification. If no bugs are found, the workflow readiness is verified via a dry-run with a synthetic low-severity issue.

## Clarifications

### Session 2026-02-18

- Q: SC-002 references "tenant isolation" as a cross-module workflow but no user story covers it. Include or remove? → A: Remove. Cross-tenant isolation is out of scope for frontend E2E testing; validated via backend pytest with RLS policies instead. SC-002 updated from 4 to 3 workflows.
- Q: After CODER fixes a bug, should TESTER re-run only the failed scenario, all scenarios in the same module, or full regression? → A: Module-level regression. Re-run the failed scenario plus all other scenarios in the same module. FR-015 and Risks table updated.
- Q: Should role-based access permissions be predefined in a matrix or discovered during testing? → A: Discover-and-document. TESTER exercises each role across all modules and records what works/fails. The discovered permissions become the baseline role-access matrix in the test report. US4 acceptance scenarios updated.

## Assumptions

- The Docker stack (core + observability) is available and can be started on the operator's machine.
- The test scenario matrix (`specs/013-e2e-frontend-testing/test-scenarios.md`) is the canonical, complete reference for all test scenarios and remains up to date. It was derived from the OpenAPI specs (`api/openapi/*.yaml`) and frontend tab components.
- ARCA invoicing tests are limited to DRAFT operations (no real ARCA certificates for CAE authorization). Authorization failure is an expected behavior, not a bug.
- Seeded data from `seed_all` is sufficient for most test scenarios. Additional seed data may be created if gaps are found.
- The browser automation tool can drive browser automation against the frontend at localhost.
- All agents communicate via the filesystem-based coordination mechanism.
- The multi-agent team launches in WSL (Windows Subsystem for Linux) using tmux for multi-pane session management.
- The shared Docker network is created by the core compose and consumed by the observability compose.

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Observability stack fails to connect to core stack | Medium | High | Verify shared network creation before starting observability |
| Authentication expires during long test run | High | Low | Re-authenticate at start of each module phase |
| Browser automation cannot reach the frontend | Medium | Critical | Verify network connectivity before first test scenario |
| A code fix breaks a previously passing scenario | Medium | Medium | Re-run all scenarios in the affected module after each fix (module-level regression) |
| Agent team token cost exceeds budget | Medium | Medium | Use cost-efficient models for monitoring agents, limit expensive models to decision-making and coding |
| Seed data has duplicates from prior runs | Low | Medium | Run seed reset as first step; all seed methods use idempotent patterns |
| ARCA module tests blocked without real certificates | Certain | Low | Explicitly scope to DRAFT operations only; authorization failure is expected and documented |
