# Feature Specification: Backend Coherence & DevOps Master Plan

**Feature Branch**: `011-backend-devops-coherence`
**Created**: 2026-02-15
**Status**: Draft
**Input**: Achieve full backend coherence across all 6 modules (AUTH, CORE, FACTURACION, INVENTARIO, VENTAS, SYNC) with working Docker deployment, validated observability, PostgreSQL-aligned testing, database alignment, and Cloud SQL migration readiness.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Docker One-Command Startup (Priority: P1)

A developer clones the repository, runs a single command, and gets the full backend system running locally with a database, cache, and web service — all healthy and accessible.

**Why this priority**: Nothing else works (testing, observability, integration) until the backend can actually start in a containerized environment. This is the foundation for all other goals.

**Independent Test**: Run the startup command on a clean machine with only Docker installed. Verify all three services reach healthy status and the API responds to requests.

**Acceptance Scenarios**:

1. **Given** a fresh clone of the repository with Docker installed, **When** the developer runs the documented startup command, **Then** the database, cache, and web service all start and report healthy within 120 seconds.
2. **Given** a running system, **When** the developer runs the documented teardown command and then re-runs startup, **Then** the system returns to a fully healthy state (idempotent restart).
3. **Given** a running system, **When** the developer hits the health endpoint, **Then** the response confirms database connectivity, migration status, and cache availability.
4. **Given** the startup command, **When** the database container initializes for the first time, **Then** all SQL initialization scripts, Django migrations, and optional seed data are applied in the correct order without errors.

---

### User Story 2 — PostgreSQL-Backed Test Execution (Priority: P1)

A developer runs the test suite against a real PostgreSQL database so that RLS policies, database triggers, stock functions, and PostgreSQL-specific features are exercised during testing.

**Why this priority**: The current test database silently skips RLS, triggers, and functions — meaning critical security and data-integrity features are untested. This is a known gap that could mask production bugs.

**Independent Test**: Run the full test suite with the PostgreSQL configuration. Verify RLS policies block cross-tenant data access, stock triggers update snapshots, and audit triggers fire correctly.

**Acceptance Scenarios**:

1. **Given** the test database uses PostgreSQL, **When** a test creates data for Tenant A, **Then** queries scoped to Tenant B return zero results (RLS enforcement verified at the database level).
2. **Given** the test database uses PostgreSQL, **When** a stock movement is created, **Then** the stock snapshot trigger fires and the product's current stock reflects the change.
3. **Given** the test database uses PostgreSQL, **When** audit-triggering operations occur on audited tables, **Then** audit log entries are created automatically by database triggers.
4. **Given** the developer wants fast feedback, **When** running the full suite against PostgreSQL, **Then** test execution completes within 9 minutes by reusing the database schema across runs.
5. **Given** a test that does not require database features, **When** the developer runs unit tests only, **Then** those tests execute without requiring a running database instance.

---

### User Story 3 — Observability End-to-End Validation (Priority: P2)

A developer or operator starts the observability stack alongside the backend and can verify that metrics, traces, and logs flow correctly from the application to the monitoring tools.

**Why this priority**: Observability code exists but has never been validated end-to-end in the Docker environment. Without this validation, monitoring in production is unreliable. Depends on Docker startup (US1) working first.

**Independent Test**: Start both compose stacks, make API calls, then query the monitoring dashboard for metrics, the tracing tool for traces, and the log aggregator for structured logs — all should contain data from the API calls.

**Acceptance Scenarios**:

1. **Given** both the main and observability stacks are running, **When** API requests are made to the backend, **Then** the metrics dashboard shows request latency histograms and error counters populated with the recent requests.
2. **Given** both stacks are running, **When** API requests are made, **Then** the tracing tool shows distributed traces with spans that include the trace ID from the request.
3. **Given** both stacks are running, **When** API requests are made, **Then** the log aggregator contains structured JSON logs from the backend with PII redaction applied.
4. **Given** the observability stack, **When** an alert condition is simulated (e.g., high error rate via targeted 5xx responses or Prometheus test recording rules), **Then** the alerting rules fire and the alert manager receives the alert.
5. **Given** the main compose and observability compose, **When** they are started independently, **Then** they connect via the shared Docker network without manual network setup.

---

### User Story 4 — Database Schema Alignment (Priority: P2)

A developer can verify that the SQL initialization scripts and Django migrations produce consistent schemas, and that all database-level features (RLS, triggers, functions, constraints) are complete and correct across both definitions.

**Why this priority**: Two parallel schema definitions create drift risk. If they diverge, the containerized database may behave differently from the expected production schema. Can be done in parallel with observability.

**Independent Test**: Initialize a database from SQL scripts only, initialize another from Django migrations only, compare schemas. The diff should be empty or contain only documented intentional differences.

**Acceptance Scenarios**:

1. **Given** the SQL initialization scripts and Django migrations, **When** both are applied to separate empty databases, **Then** the resulting table structures, column types, and constraints match.
2. **Given** all RLS policy definitions, **When** compared across all definition sources, **Then** every tenant-scoped table has an RLS policy and the policies are consistent.
3. **Given** the SQL scripts, **When** run against a fresh database multiple times, **Then** each script completes without errors (idempotent execution).
4. **Given** the seed data scripts and management commands, **When** run against a fresh schema, **Then** they complete without errors and produce valid test data.

---

### User Story 5 — Cross-Module Integration Verification (Priority: P3)

A developer can run integration tests that verify the 6 backend modules work together correctly, including cross-module workflows like sale-to-stock-reservation and sale-to-invoice.

**Why this priority**: Individual module tests exist, but cross-module interactions have not been tested as integrated workflows. Depends on PostgreSQL testing (US2) and Docker (US1) working first.

**Independent Test**: Run cross-module integration tests that exercise the full workflow paths. Each test verifies data flows correctly between the involved modules.

**Acceptance Scenarios**:

1. **Given** a confirmed sale order with items, **When** the sale triggers stock reservation, **Then** the inventory module reflects the reserved quantity and available stock decreases accordingly.
2. **Given** a sale order ready for invoicing with ARCA SOAP calls mocked at the HTTP boundary, **When** the invoice creation workflow runs, **Then** a comprobante is created in the facturacion module linked to the sale order and the mocked ARCA request contains the correct payload.
3. **Given** a user authenticated with tenant claims, **When** the user makes requests to any module, **Then** RLS enforces that only the user's tenant data is accessible.
4. **Given** an offline operation queued in the sync module, **When** sync executes, **Then** the operation is applied to the correct module with conflict resolution if needed.

---

### User Story 6 — Cloud SQL Migration Readiness Report (Priority: P3)

A technical lead receives a comprehensive report analyzing the readiness of the current database setup for migration to Cloud SQL, covering connection strategy, RLS compatibility, backup planning, zero-downtime migration, performance tuning, security, cost estimation, and monitoring integration.

**Why this priority**: This is an analysis deliverable, not a code change. It informs future deployment decisions but does not block current development.

**Independent Test**: The report is reviewed by a technical lead and covers all required topics with actionable recommendations referencing the actual codebase configuration.

**Acceptance Scenarios**:

1. **Given** the current production settings and database configuration, **When** the report is produced, **Then** it includes a connection strategy recommendation (Unix socket vs Private IP) with pros/cons for the target deployment platform.
2. **Given** the current RLS policy implementation, **When** analyzed for managed PostgreSQL compatibility, **Then** the report confirms whether session variables and role management work, with workarounds if needed.
3. **Given** the current database schema and expected workload, **When** the report is produced, **Then** it includes instance sizing recommendations with cost estimates.
4. **Given** the existing observability stack, **When** the report is produced, **Then** it includes recommendations for integrating managed database metrics with the current monitoring tools.

---

### User Story 7 — ARCA Homologation vs Production Gap Analysis (Priority: P3)

A developer working on the invoicing module receives an analysis documenting all differences between ARCA homologation and production environments, covering endpoint switching, certificate management, response format variations, error handling differences, and a testing strategy for production-path code.

**Why this priority**: Critical for eventual production deployment of fiscal invoicing, but does not block current development. Analysis deliverable that can be done in parallel.

**Independent Test**: The analysis references actual code paths in the facturacion module and provides verifiable claims about endpoint routing, certificate handling, and error code coverage.

**Acceptance Scenarios**:

1. **Given** the production flag in ARCA configuration, **When** the analysis reviews endpoint switching, **Then** it confirms that all ARCA service endpoints switch correctly between homologation and production URLs.
2. **Given** the certificate management code, **When** the analysis reviews cert handling, **Then** it documents the differences between homologation and production certificates, including expiry tracking and rotation strategy.
3. **Given** the ARCA error handling code, **When** the analysis reviews SOAP fault codes, **Then** it documents any known differences in fault codes between environments, with recommendations for comprehensive error handling.

---

### Edge Cases

- What happens when Docker is not running or has insufficient resources (memory, disk)?
- How does the system handle a corrupt or partially-initialized database volume?
- What happens when RLS policies reference a tenant_id that doesn't exist in the tenants table?
- How does the test suite behave when the PostgreSQL test database is unavailable (graceful fallback or clear error)?
- What happens when the observability stack starts before the backend (no service to scrape)?
- What happens when SQL scripts are run out of order or with missing prerequisites?
- How does the system handle managed database connection drops during high-concurrency scenarios?
- What if ARCA homologation endpoints are temporarily unavailable during testing?

## Requirements *(mandatory)*

### Functional Requirements

#### Docker Deployment Coherence

- **FR-001**: System MUST start all backend services (database, cache, web) from a single documented command.
- **FR-002**: System MUST support compose profiles to separate development, test, and load-test configurations within a single compose file.
- **FR-003**: System MUST automatically initialize the database (SQL scripts, migrations, optional seed data) on first startup without manual intervention.
- **FR-004**: System MUST expose health check endpoints that verify database connectivity, migration status, and cache availability.
- **FR-005**: System MUST document all required environment variables and flag any mismatch between compose files and application settings.
- **FR-006**: System MUST support idempotent startup — running the startup command multiple times produces the same healthy state.
- **FR-007**: The main compose and observability compose MUST communicate via a shared network that is created automatically.

#### Observability Validation

- **FR-008**: System MUST expose a metrics endpoint that the monitoring tool can scrape, populated with request latency, error counts, and business metrics after API activity.
- **FR-009**: System MUST send distributed traces to the tracing backend, including trace ID correlation through request middleware.
- **FR-010**: System MUST output structured JSON logs to stdout that the log shipper can forward to the log aggregator, with PII redaction applied.
- **FR-011**: System MUST include alert rules that fire for defined conditions: 5xx error rate > 5% over 5 minutes, request latency p99 > 2 seconds, sync operation lag > 30 minutes.
- **FR-012**: System MUST configure tracing environment variables in the compose file to point to the correct observability containers.

#### PostgreSQL Test Configuration

- **FR-013**: System MUST switch the default test database to PostgreSQL. The existing in-memory configuration is preserved only for a fast unit-test subset that has no database dependencies.
- **FR-014**: Test suite MUST exercise RLS policies, database triggers, and database functions when running against PostgreSQL.
- **FR-015**: Test suite MUST support schema reuse across runs for fast feedback (no full database teardown per run).
- **FR-016**: Unit tests that do not require database features MUST remain runnable without a running PostgreSQL instance.
- **FR-017**: Test suite MUST provide clear markers to distinguish fast unit tests from database-dependent integration tests.

#### Database Alignment

- **FR-018**: All SQL initialization scripts MUST be idempotent (safe to run multiple times without errors).
- **FR-019**: A master bootstrap script MUST exist that runs all SQL scripts in order, applies migrations, and optionally seeds data.
- **FR-020**: System MUST produce a schema drift report comparing SQL script definitions with Django migration definitions.
- **FR-021**: Every tenant-scoped table MUST have an RLS policy, verified across all RLS definition sources.
- **FR-022**: Database seed data scripts and management commands MUST work with the current schema without errors.

#### Cross-Module Integration

- **FR-023**: Integration tests MUST verify the Ventas to Inventario stock reservation workflow.
- **FR-024**: Integration tests MUST verify the Ventas to Facturacion invoice creation workflow using boundary mocks — the full internal workflow (sale order → comprobante creation → ARCA request assembly) is tested end-to-end, with only the external SOAP HTTP calls to ARCA mocked.
- **FR-025**: Integration tests MUST verify that JWT authentication with tenant claims enforces RLS isolation across all modules.
- **FR-026**: Integration tests MUST verify the Sync module's conflict resolution against real module operations.

#### Analysis Deliverables

- **FR-027**: System MUST produce a Cloud SQL migration readiness report covering connection strategy, RLS compatibility, backup, zero-downtime migration, performance tuning, security, cost estimation, and monitoring integration.
- **FR-028**: System MUST produce an ARCA homologation vs production gap analysis covering endpoint switching, certificate management, response format differences, error handling, and testing strategy.

#### Code Quality & Architecture Analysis

- **FR-029**: System MUST produce a refactoring proposals report auditing all 6 backend modules for security anti-patterns, performance bottlenecks, and technical debt, with priority ratings (CRITICAL/HIGH/MEDIUM/LOW), file:line references, and proposed fix patterns.
- **FR-030**: System MUST produce a backend cohesion report analyzing API-Database-Backend alignment, transaction boundaries, error handling patterns, fault tolerance, and data integrity across all 6 modules.

### Key Entities

- **Docker Service**: A containerized process (web, database, cache) defined in the compose file, with health check status, environment variables, and network membership.
- **Test Configuration**: A settings module that determines the database backend, test markers, and schema reuse behavior.
- **SQL Initialization Script**: An idempotent SQL file that creates or updates database objects (tables, RLS policies, triggers, functions, constraints) in a specific execution order.
- **Observability Pipeline**: The flow of application telemetry (metrics, traces, logs) from the backend through collection agents to storage and visualization tools.
- **Schema Drift Report**: A comparison document listing differences between SQL script definitions and Django migration definitions for tables, columns, constraints, and policies.
- **Cross-Module Workflow**: A business process that spans multiple backend modules (e.g., sale to stock reservation to invoice), tested as an integrated sequence.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A fresh clone of the repository reaches a fully healthy backend (database, cache, web all responding) within 120 seconds of running the startup command.
- **SC-002**: The test suite runs against PostgreSQL with RLS policies actively enforced — cross-tenant data access attempts are blocked in 100% of isolation tests.
- **SC-003**: All database initialization scripts execute successfully when run multiple times in sequence on the same database (idempotent execution, zero errors on repeat runs).
- **SC-004**: After making API calls to the running backend, metrics appear in the monitoring dashboard, traces appear in the tracing tool, and structured logs appear in the log aggregator — all within 30 seconds of the API call.
- **SC-005**: The schema drift report identifies zero unresolved discrepancies between SQL scripts and Django migrations (all differences either reconciled or documented as intentional).
- **SC-006**: Cross-module integration tests verify at least 3 primary workflows (sale to stock, sale to invoice, auth to RLS across modules) with all tests passing.
- **SC-007**: Cloud SQL readiness report covers all 9 required topics (connection, pooling, RLS, backup, migration, performance, security, cost, monitoring) with actionable recommendations referencing actual codebase configuration.
- **SC-008**: ARCA gap analysis verifies endpoint switching for all 3 service types (WSAA, WSFE, CAEA) and documents certificate management differences between environments.
- **SC-009**: All existing tests (~2123) pass against PostgreSQL after infrastructure changes — zero regressions introduced (tests that break due to PostgreSQL-specific behavior are fixed, not skipped).
- **SC-010**: The full test suite completes in under 9 minutes when running against PostgreSQL with schema reuse enabled.
- **SC-011**: Refactoring proposals report contains zero unaddressed CRITICAL findings — all CRITICAL items have either a fix applied or a documented deferral rationale. All HIGH findings are prioritized with estimated effort.
- **SC-012**: Backend cohesion report covers all 5 analysis domains (API-DB alignment, transaction safety, error handling, fault tolerance, connection management) with specific file:line references from the actual codebase.

## Clarifications

### Session 2026-02-15

- Q: Should existing ~2123 tests default to PostgreSQL or stay on SQLite? → A: PostgreSQL becomes the default test database. SQLite preserved only for fast unit tests without DB dependencies.
- Q: How should cross-module tests handle the ARCA external SOAP dependency? → A: Boundary mock — test the full internal workflow (sale → comprobante → request assembly), mock only the SOAP HTTP calls to ARCA. No live homologation required for integration tests.
- Q: What is the acceptable execution time for the full test suite on PostgreSQL? → A: 9 minutes maximum.

## Assumptions

- **A-001**: Docker Desktop (or equivalent container runtime) is available on the developer's machine with at least 4GB RAM allocated.
- **A-002**: The current 6 backend modules are feature-complete for their current scope — this spec does not add new business features.
- **A-003**: The existing observability code is functionally correct — this spec validates wiring and integration, not reimplementation.
- **A-004**: Cloud SQL readiness is an analysis deliverable only — actual cloud provisioning and migration are out of scope.
- **A-005**: ARCA homologation endpoints are accessible from the development environment for testing.
- **A-006**: PostgreSQL is the default test database. The in-memory test path is preserved only for a fast unit-test subset (tests with no database dependencies). Existing tests that fail under PostgreSQL will be fixed as part of this feature.
- **A-007**: The schema drift audit compares logical equivalence (same tables, columns, types, constraints) — cosmetic differences (naming conventions, whitespace) are acceptable.
- **A-008**: The shared Docker network between compose files will use Docker's built-in external network mechanism.

## Dependencies

- **D-001**: Docker Desktop (or Docker Engine + Compose plugin) installed and running.
- **D-002**: Existing backend modules (AUTH, CORE, FACTURACION, INVENTARIO, VENTAS, SYNC) in their current working state.
- **D-003**: PostgreSQL 18 container image available from a container registry.
- **D-004**: ARCA homologation endpoints accessible for gap analysis validation.
- **D-005**: Current test suite (~2123 tests) as regression baseline.

## Risks

- **R-001** (MEDIUM): Switching test database to PostgreSQL may surface previously-hidden bugs masked by the more permissive in-memory database. Mitigation: Treat discovered bugs as findings in the drift report, not blockers.
- **R-002** (LOW): Compose profile consolidation may break existing developer workflows. Mitigation: Document new commands clearly and provide a migration guide.
- **R-003** (MEDIUM): Schema drift between SQL scripts and Django migrations may be larger than expected, requiring significant reconciliation. Mitigation: Prioritize one source of truth (migrations for app schema, SQL scripts for RLS/triggers/functions).
- **R-004** (LOW): Observability tools may require specific versions or configurations not currently documented. Mitigation: Pin versions in compose files and document requirements.
- **R-005** (LOW): Managed PostgreSQL RLS compatibility is uncertain — session variables or role management may have restrictions. Mitigation: Research and document early in the analysis phase.
