# Tasks: Backend Coherence & DevOps Master Plan

**Input**: Design documents from `specs/011-backend-devops-coherence/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api-contract.md, quickstart.md
**Branch**: `011-backend-devops-coherence` | **Date**: 2026-02-15

**Organization**: Tasks grouped by user story (7 stories + 2 cross-cutting analyses, 11 phases, 59 tasks).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story (US1–US7) — maps to spec.md

---

## Phase 1: Setup

**Purpose**: Audit existing state and prepare environment configuration

- [X] T001 Audit existing Docker files (docker-compose.yml, docker-compose.test.yml, docker-compose.observability.yml, Dockerfile) and SQL scripts (database/SQL/*.sql) for baseline understanding
- [X] T002 [P] Create/update backend/.env.example with all required environment variables per research.md env audit (DJANGO_SETTINGS_MODULE, OTEL_TRACING_ENABLED, LOG_FORMAT, JWT keys documented as optional)

---

## Phase 2: Foundational (SQL Script Idempotency)

**Purpose**: Make all SQL initialization scripts safe to run multiple times — MUST complete before US1 bootstrap script can work

**CRITICAL**: US1's bootstrap script (T015) depends on idempotent SQL scripts. US4 verification (T035) also depends on this phase.

- [X] T003 Make database/SQL/000_init_database.sql idempotent (CREATE ROLE IF NOT EXISTS, CREATE EXTENSION IF NOT EXISTS, grant permissions with IF NOT EXISTS guards)
- [X] T004 [P] Make database/SQL/002_rls_policies.sql idempotent (CREATE OR REPLACE FUNCTION for get_current_tenant_id, DROP POLICY IF EXISTS + CREATE POLICY pattern for all policies)
- [X] T005 [P] Make database/SQL/003_stock_functions.sql idempotent (CREATE OR REPLACE FUNCTION for all stock trigger functions)
- [X] T006 [P] Make database/SQL/004_audit_functions.sql idempotent (CREATE OR REPLACE FUNCTION for all audit trigger functions)
- [X] T007 [P] Make database/SQL/005_hardening_constraints.sql idempotent (DO $$ BEGIN ... EXCEPTION WHEN duplicate_object THEN NULL; END $$ blocks for ADD CONSTRAINT)
- [X] T008 Rename database/SQL/001_schema.sql to database/SQL/001_schema_reference.sql and add header comment marking it as deprecated reference per R5 (Django migrations own table schema)

**Checkpoint**: All SQL scripts run multiple times without errors. Foundation ready for US1 and US4.

---

## Phase 3: User Story 1 — Docker One-Command Startup (Priority: P1) 🎯 MVP

**Goal**: `docker compose up -d` starts postgres, redis, and web — all healthy within 120 seconds

**Independent Test**: Fresh clone → single command → health endpoint returns 200 with DB/cache/migrations all up

**Dependencies**: Phase 2 (idempotent SQL scripts for bootstrap)

**FRs**: FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007

### Implementation

- [X] T009 [US1] Merge backend/docker-compose.test.yml into backend/docker-compose.yml using compose profiles: default (postgres, redis, web), test (postgres-test, redis-test, web-test, jaeger-test, prometheus-test), load (locust) per R1
- [X] T010 [US1] Configure named bridge network in backend/docker-compose.yml: `gravitea-shared` with explicit `name: gravitea-shared` to prevent project prefix per R2
- [X] T011 [P] [US1] Update backend/docker-compose.observability.yml network section to reference `gravitea-shared` as external with explicit name per R2
- [X] T012 [US1] Fix environment variables in backend/docker-compose.yml web service: DJANGO_SETTINGS_MODULE=gravitea.settings.development, OTEL_TRACING_ENABLED=true, LOG_FORMAT=json per research.md env audit
- [X] T013 [US1] Update backend/Dockerfile: install postgresql-client in production stage, set ENTRYPOINT to scripts/bootstrap.sh, keep CMD for gunicorn per R6
- [X] T014 [US1] Create scripts/bootstrap.sh: wait-for-db (pg_isready loop) → SQL scripts (000, 002-005 in order) → django migrate --noinput → optional seed (SEED_DATA=true) → exec "$@" per R6
- [X] T015 [US1] Write tests for health check endpoint in backend/tests/core/test_health.py: verify 200 when all services up, 503 when DB/cache down (mocked), response schema matches api-contract.md, no auth required — per Constitution Principle X (TDD)
- [X] T016 [US1] Create health check view in backend/apps/core/health.py: GET /api/v1/health/ returning DB ping (SELECT 1), cache ping (PING), migration status (MigrationExecutor pending count), version, timestamp per api-contract.md — no auth required, 200 if all pass, 503 if any fail
- [X] T017 [US1] Register health check URL at /api/v1/health/ in backend/gravitea/urls.py (security: [] in OpenAPI schema via drf-spectacular @extend_schema)
- [X] T018 [US1] Add Docker healthcheck directives to all services in backend/docker-compose.yml: postgres (pg_isready), redis (redis-cli ping), web (python urllib http://localhost:8080/api/v1/health/ — container-internal port 8080 via gunicorn), test-profile services likewise
- [X] T019 [US1] Delete backend/docker-compose.test.yml after merge verification (all test-profile services confirmed in main compose)
- [X] T020 [US1] Validate: `docker compose up -d` → all 3 services healthy within 120s (SC-001), `curl http://localhost:8000/api/v1/health/` returns 200

**Checkpoint**: One-command startup works. Health endpoint confirmed with tests. DB, cache, migrations all up. Idempotent restart verified.

---

## Phase 4: User Story 2 — PostgreSQL-Backed Test Execution (Priority: P1)

**Goal**: Test suite defaults to PostgreSQL with RLS enforcement; fast unit path preserved on SQLite

**Independent Test**: Full suite against PostgreSQL — RLS blocks cross-tenant access, triggers fire, all ~2123 tests pass

**Dependencies**: Phase 3/US1 (test-profile Docker containers must be running for PostgreSQL test DB)

**FRs**: FR-013, FR-014, FR-015, FR-016, FR-017

### Implementation

- [X] T021 [US2] Create backend/gravitea/settings/test_postgres.py: inherit from base.py (NOT test.py), configure PostgreSQL connection to localhost:5433 (POSTGRES_TEST_* env vars with defaults), MD5PasswordHasher, HS256 JWT per R4
- [X] T022 [US2] Update backend/pytest.ini: change DJANGO_SETTINGS_MODULE default to gravitea.settings.test_postgres, configure --reuse-db as default addopts per R3
- [X] T023 [US2] Add RLS session variable fixture `set_rls_tenant_context` in backend/tests/conftest.py: autouse, depends on tenant_context, executes SET app.current_tenant_id via raw SQL, skips @unit tests, RESET on teardown per R9
- [X] T024 [US2] Add/verify pytest markers in backend/pytest.ini and backend/conftest.py: `unit` (no DB), `integration` (requires DB), `security` (security-focused) per FR-017
- [X] T025 [US2] Run full test suite (~2123 tests) against PostgreSQL with `--create-db`, fix any regressions caused by DB engine switch (SC-009) — fix tests, not skip them
- [X] T026 [US2] Validate RLS enforcement: cross-tenant data access blocked at DB level in isolation tests (SC-002), stock triggers fire on movement creation, audit triggers create log entries
- [X] T027 [US2] Validate fast unit path: `pytest -m unit --ds=gravitea.settings.test` runs without PostgreSQL instance (FR-016)

**Checkpoint**: PostgreSQL is default test DB with RLS enforcement. ~2123 tests pass. Unit fast-path preserved.

---

## Phase 5: User Story 3 — Observability E2E Validation (Priority: P2)

**Goal**: Metrics, traces, and structured JSON logs flow from backend to Prometheus, Jaeger, and log aggregator

**Independent Test**: Start both stacks → make API calls → data appears in all monitoring tools within 30 seconds

**Dependencies**: Phase 3/US1 (Docker stack running, shared network configured)

**FRs**: FR-008, FR-009, FR-010, FR-011, FR-012

### Implementation

- [X] T028 [US3] Verify/fix Prometheus scrape config in backend/observability/prometheus.yml: target gravitea-web:8080/metrics/, scrape interval, job name per FR-008
- [X] T029 [P] [US3] Verify/fix OTEL trace export: OTEL_EXPORTER_OTLP_ENDPOINT=http://gravitea-jaeger:4317 in docker-compose.yml, Jaeger COLLECTOR_OTLP_ENABLED=true in observability compose per R7/FR-012
- [X] T030 [US3] Review/create alert rules in backend/observability/ for: 5xx error rate > 5% over 5 minutes, request latency p99 > 2 seconds, sync operation lag > 30 minutes per FR-011
- [X] T031 [US3] Validate E2E: start both stacks → make API calls → confirm django_http_requests_total in Prometheus, gravitea-backend spans in Jaeger, JSON logs with PII redaction (email, CUIT, token fields sanitized) in stdout, Loki log aggregation receiving structured logs per SC-004/FR-010
- [X] T032 [US3] Validate network: observability compose connects to main compose via gravitea-shared network automatically (no manual docker network create) per FR-007

**Checkpoint**: Full observability pipeline validated. Metrics, traces, logs (including Loki), and alerts all wired correctly.

---

## Phase 6: User Story 4 — Database Schema Alignment (Priority: P2)

**Goal**: SQL scripts and Django migrations produce consistent schemas; all RLS policies verified; zero drift

**Independent Test**: SQL-only vs migration-only database initialization produces matching schemas

**Dependencies**: Phase 2 (idempotent SQL scripts). Can run in PARALLEL with US1/US3.

**FRs**: FR-018, FR-019, FR-020, FR-021, FR-022

### Implementation

- [X] T033 [US4] Generate schema drift report: compare SQL script definitions (tables, columns, types) with Django migration definitions, document in claudedocs/011-schema-drift-report.md per FR-020/SC-005
- [X] T034 [US4] Audit RLS coverage: verify every table with TenantBoundModel has an RLS policy in 002_rls_policies.sql, facturacion_rls.sql, or ventas_rls.sql — document any gaps per FR-021
- [X] T035 [US4] Validate idempotency: run all SQL scripts (000, 002-005) twice in sequence on same database — zero errors on repeat execution per FR-018/SC-003
- [X] T036 [US4] Validate seed commands: run `python manage.py seed_ventas` and any available seed_data commands against fresh schema per FR-022
- [X] T037 [US4] Reconcile drift found in T033: fix SQL scripts or document as intentional per R5 hybrid source of truth (migrations own tables, SQL owns RLS/triggers/functions)

**Checkpoint**: Schema drift report complete. RLS 100% coverage. Idempotency verified. Seed data works.

---

## Phase 7: User Story 5 — Cross-Module Integration Verification (Priority: P3)

**Goal**: Integration tests verify cross-module workflows with real PostgreSQL and RLS enforcement

**Independent Test**: Run integration tests — all pass with real DB, boundary mocks for ARCA SOAP only

**Dependencies**: Phase 3/US1 (Docker), Phase 4/US2 (PostgreSQL tests + RLS fixture)

**FRs**: FR-023, FR-024, FR-025, FR-026

### Implementation

- [X] T038 [US5] Create backend/tests/integration/__init__.py
- [X] T039 [P] [US5] Create backend/tests/integration/test_sale_to_stock.py: confirmed sale order → stock reservation → inventory quantity decreased, tenant isolation verified per FR-023
- [X] T040 [P] [US5] Create backend/tests/integration/test_sale_to_invoice.py: sale order → comprobante creation → ARCA request payload verification — boundary mock external SOAP HTTP only per FR-024
- [X] T041 [P] [US5] Create backend/tests/integration/test_auth_rls_cross_module.py: JWT auth with tenant claims → RLS isolation across ventas, inventario, facturacion, sync per FR-025
- [X] T042 [P] [US5] Create backend/tests/integration/test_sync_conflict.py: offline operation queued → sync executes → applied to correct module with conflict resolution per FR-026
- [X] T043 [US5] Validate: all integration tests pass against PostgreSQL with RLS enforcement — at least 3 workflows verified per SC-006

**Checkpoint**: 3+ cross-module workflows verified. Tenant isolation holds across all module boundaries.

---

## Phase 8: User Story 6 — Cloud SQL Migration Readiness Report (Priority: P3)

**Goal**: Comprehensive analysis covering 9 required topics for Cloud SQL migration

**Independent Test**: Report covers all topics with actionable recommendations referencing actual codebase

**Dependencies**: None (analysis deliverable — CAN START after Phase 2)

**FRs**: FR-027 | **SCs**: SC-007

### Implementation

- [X] T044 [P] [US6] Create claudedocs/011-cloud-sql-readiness.md: connection strategy (Unix socket vs Private IP for Cloud Run per R8), connection pooling (pgbouncer vs Cloud SQL proxy), RLS compatibility (session variables on managed PG), backup strategy, zero-downtime migration plan, performance tuning (instance sizing, IOPS), security (IAM auth, encryption at rest), cost estimation (instance + egress), monitoring integration (Cloud Monitoring → existing Grafana/Prometheus) per FR-027
- [X] T045 [US6] Validate: report references actual codebase paths (production.py:43-65, compose files, RLS scripts) with 9 actionable sections per SC-007

**Checkpoint**: Cloud SQL readiness report complete. 9 topics covered with codebase-specific recommendations.

---

## Phase 9: User Story 7 — ARCA Homologation vs Production Gap Analysis (Priority: P3)

**Goal**: Document all differences between ARCA homologation and production environments

**Independent Test**: Analysis references actual code paths in facturacion module with verifiable claims

**Dependencies**: None (analysis deliverable — CAN START after Phase 2)

**FRs**: FR-028 | **SCs**: SC-008

### Implementation

- [X] T046 [P] [US7] Create claudedocs/011-arca-gap-analysis.md: endpoint switching for WSAA/WSFE/CAEA (URL routing per is_production flag), certificate management (homologation vs production certs, expiry tracking, rotation), response format differences, SOAP fault code differences between environments, testing strategy for production-path code per FR-028
- [X] T047 [US7] Validate: report references actual code in backend/apps/facturacion/arca/ (client classes, constants, cert handling) with verifiable endpoint URLs per SC-008

**Checkpoint**: ARCA gap analysis complete. 3 service types documented. Cert management differences clear.

---

## Phase 10A: Code Quality & Backend Architecture Analysis

**Purpose**: Systematic audit of all 6 backend modules for technical debt, security anti-patterns, performance bottlenecks, and API-Database-Backend cohesion. Produces two read-only analysis reports with actionable, priority-ranked findings.

**Dependencies**: Phase 2 (needs stable codebase understanding). Can run in PARALLEL with all code phases (3-9).

**FRs**: FR-029, FR-030 | **SCs**: SC-011, SC-012

### Refactoring Analysis (REFACTORING-EXPERT)

- [X] T052 [P] Audit AUTH and CORE modules (~12K LOC): security anti-patterns in rate_limiter.py and url_validator.py, middleware chain performance, encryption field usage consistency, observability code dead paths, missing type hints in core managers, TenantBoundManager edge cases
- [X] T053 [P] Audit FACTURACION and INVENTARIO modules (~10K LOC): ARCA client code quality (wsaa_client.py, wsfe_client.py), stock service N+1 query risks, immutable ledger enforcement gaps, serializer field declarations, service layer transaction boundaries, missing select_related/prefetch_related
- [X] T054 [P] Audit VENTAS and SYNC modules (~6K LOC): service layer consistency (sync uses conflict_resolver.py not services/), async task safety in celery tasks, admin.py patterns (only ventas has one), dead code from rapid development, error handling consistency with RFC 7807
- [X] T055 Produce priority-ranked refactoring proposals in claudedocs/011-refactoring-proposals.md: CRITICAL/HIGH/MEDIUM/LOW ratings, file:line references, estimated effort per fix, proposed fix pattern, cross-module pattern recommendations — per SC-011

### Backend Architecture Cohesion (BACKEND-ARCHITECT)

- [X] T056 [P] Analyze API-Database alignment: compare OpenAPI schema (drf-spectacular) with actual view/serializer implementations across all 6 modules, identify exposed fields that shouldn't be (PII leak risk), missing response fields, inconsistent naming between serializer fields and model fields
- [X] T057 [P] Audit transaction boundaries and data integrity: verify @transaction.atomic scoping in all service layers (facturacion, inventario, ventas), check select_for_update patterns in stock/invoice operations, audit FK cascade behavior and orphaned record risks, verify StockMovement and Comprobante immutability enforcement end-to-end
- [X] T058 [P] Audit error handling and fault tolerance: verify all 6 modules use RFC 7807 ProblemDetail format from core/exceptions/, check HTTP status code consistency across modules, assess graceful degradation when PostgreSQL/Redis is down, review Celery task retry patterns in sync/inventario, validate cross-module error propagation (stock failure during sale → correct HTTP response)
- [X] T059 Produce backend cohesion report in claudedocs/011-backend-cohesion-report.md covering: API-DB alignment, transaction safety, error handling patterns, fault tolerance assessment, connection management — per SC-012

**Checkpoint**: Both reports delivered. SECURITY-ENGINEER reviews. Zero unaddressed CRITICAL findings. ORCHESTRATOR decides if any HIGH findings warrant immediate fixes before Phase 10B.

---

## Phase 10B: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, documentation accuracy, and cleanup

- [X] T048 Run quickstart.md validation: follow all steps from specs/011-backend-devops-coherence/quickstart.md end-to-end on clean environment
- [X] T049 Verify full test suite passes with zero regressions against PostgreSQL (~2123 tests, SC-009)
- [X] T050 [P] Verify test suite completes under 9 minutes with --reuse-db on PostgreSQL per SC-010
- [X] T051 Final cleanup: remove temporary files, verify .gitignore covers Docker volumes and test artifacts, commit

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup)
  └── Phase 2 (Foundational — SQL idempotency)
        ├── Phase 3 / US1 (Docker Startup) ──┬── Phase 4 / US2 (PG Tests) ── Phase 7 / US5 (Integration)
        │                                     └── Phase 5 / US3 (Observability)
        ├── Phase 6 / US4 (Schema Alignment) [parallel with US1]
        ├── Phase 8 / US6 (Cloud SQL Report) [parallel — analysis only]
        ├── Phase 9 / US7 (ARCA Gap Report) [parallel — analysis only]
        └── Phase 10A (Code Quality & Architecture) [parallel — analysis only]
                                                                    All ──→ Phase 10B (Polish)
```

### Story Dependencies

| Story | Depends On | Can Parallel With |
|-------|-----------|-------------------|
| US1 (P1) | Phase 2 | US4, US6, US7 |
| US2 (P1) | US1 | US3, US4, US6, US7 |
| US3 (P2) | US1 | US2, US4, US6, US7 |
| US4 (P2) | Phase 2 | US1, US2, US3, US6, US7 |
| US5 (P3) | US1 + US2 | US6, US7 |
| US6 (P3) | Phase 2 | All (analysis only) |
| US7 (P3) | Phase 2 | All (analysis only) |
| 10A (analysis) | Phase 2 | All (analysis only) |

### Within Each Story

- Infrastructure/config before code
- Tests before implementation (where applicable, per Constitution Principle X)
- Code before validation tasks
- Validation tasks are the checkpoint gate

### Parallel Opportunities

**Phase 2** (4 parallel SQL files):
- T004 + T005 + T006 + T007 — each modifies a different SQL file

**Phase 3** (compose files):
- T011 (observability compose) parallel with T010 (main compose)

**Phase 5 + 6** (after US1):
- US3 and US4 can run entirely in parallel

**Phase 7** (integration tests):
- T039 + T040 + T041 + T042 — each creates a different test file

**Phase 8 + 9 + 10A** (analysis reports and audits):
- T044 + T046 + T052-T054 + T056-T058 — independent analyses, can start from Phase 2 onward

---

## Parallel Example: Phase 2

```bash
# All SQL idempotency tasks in parallel (different files):
Task: T004 "Make 002_rls_policies.sql idempotent"
Task: T005 "Make 003_stock_functions.sql idempotent"
Task: T006 "Make 004_audit_functions.sql idempotent"
Task: T007 "Make 005_hardening_constraints.sql idempotent"
```

## Parallel Example: US5 Integration Tests

```bash
# All integration test files in parallel:
Task: T039 "Create test_sale_to_stock.py"
Task: T040 "Create test_sale_to_invoice.py"
Task: T041 "Create test_auth_rls_cross_module.py"
Task: T042 "Create test_sync_conflict.py"
```

## Parallel Example: Analysis Reports

```bash
# US6 and US7 from Phase 2 onward:
Task: T044 "Create Cloud SQL readiness report"
Task: T046 "Create ARCA gap analysis report"
```

## Parallel Example: Code Quality & Architecture Audits (Phase 10A)

```bash
# All module audits in parallel (different modules, read-only):
Task: T052 "Audit AUTH + CORE modules"
Task: T053 "Audit FACTURACION + INVENTARIO modules"
Task: T054 "Audit VENTAS + SYNC modules"

# All cohesion domains in parallel (different analysis focus):
Task: T056 "Analyze API-Database alignment"
Task: T057 "Audit transaction boundaries"
Task: T058 "Audit error handling & fault tolerance"
```

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (SQL idempotency)
3. Complete Phase 3: US1 (Docker one-command startup + health endpoint)
4. **STOP and VALIDATE**: `docker compose up -d` → healthy system → `curl /api/v1/health/` → 200
5. Deploy/demo if ready

### Incremental Delivery

1. Phase 1 + 2 → Foundation ready
2. US1 → Docker startup validated (**MVP**)
3. US2 → PostgreSQL tests with RLS enforcement
4. US3 + US4 (parallel) → Observability + schema alignment
5. US5 → Cross-module integration verified
6. US6 + US7 (parallel, can overlap with US3-US5) → Analysis reports
7. Phase 10A → Code quality & architecture analysis (REFACTORING-EXPERT + BACKEND-ARCHITECT)
8. Phase 10B → Polish, final regression, and address any CRITICAL findings from 10A

### Parallel Team Strategy

With 3 developers after Phase 2:

| Developer | Sequence | Stories |
|-----------|----------|---------|
| Dev A | US1 → US2 → US5 | Docker → Tests → Integration (critical path) |
| Dev B | US4 → US3 | Schema alignment → Observability |
| Dev C | US6 + US7 | Both analysis reports (independent) |
| Dev D | Phase 10A | Code quality audit + backend cohesion (independent, read-only) |

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps to user stories in spec.md (US1–US7)
- FR/SC references in descriptions map to functional requirements and success criteria
- Each user story independently completable and testable at its checkpoint
- Phase 10A analysis tasks (T052-T059) are read-only — agents produce reports, never modify source code
- Commit after each phase completion
- SQL idempotency (Phase 2) is the critical foundation — blocks US1 bootstrap and US4 verification
- Test fixes in T025 should FIX tests for PostgreSQL compatibility, never SKIP them (SC-009)
- Research decisions R1–R9 are referenced in task descriptions for implementation guidance
- Health check endpoint has test-first task (T015) before implementation (T016) per Constitution Principle X
- Phase 10B (Polish) depends on Phase 10A completion — CRITICAL findings from 10A may generate fix tasks before final polish
