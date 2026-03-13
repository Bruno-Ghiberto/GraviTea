# Implementation Plan: Backend Coherence & DevOps Master Plan

**Branch**: `011-backend-devops-coherence` | **Date**: 2026-02-15 | **Spec**: `specs/011-backend-devops-coherence/spec.md`
**Input**: Feature specification from `specs/011-backend-devops-coherence/spec.md`

## Summary

Achieve full backend coherence across all 6 modules (AUTH, CORE, FACTURACION, INVENTARIO, VENTAS, SYNC) by consolidating Docker deployment, switching test database to PostgreSQL with RLS enforcement, validating the observability pipeline end-to-end, resolving schema drift between SQL scripts and Django migrations, verifying cross-module integration workflows, and producing Cloud SQL readiness and ARCA gap analysis reports. Research phase resolved 9 technical unknowns — see `research.md`.

## Technical Context

**Language/Version**: Python 3.14.3
**Primary Dependencies**: Django 5.2.x, DRF, pytest-django, psycopg, opentelemetry-sdk, prometheus-client, gunicorn
**Storage**: PostgreSQL 18.1 (Docker), Redis 7.x (Docker)
**Testing**: pytest + pytest-django (PostgreSQL default, SQLite fast-path preserved)
**Target Platform**: Linux (Docker containers, Cloud Run for production)
**Project Type**: Web application (backend only — Django monolith)
**Performance Goals**: Full test suite under 9 minutes on PostgreSQL with `--reuse-db`; Docker startup under 120 seconds
**Constraints**: All existing ~2123 tests must pass (zero regressions); idempotent SQL scripts; RLS enforcement in tests
**Scale/Scope**: 6 backend modules, ~20 migration files, 6 SQL scripts, 3 compose files, 1 Dockerfile, 2 settings modules

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Relevant? | Compliance | Notes |
|-----------|-----------|------------|-------|
| I. Ironclad Data Model | Yes | PASS | Schema drift resolution (R5) preserves Django migrations as table source of truth; SQL scripts own RLS/triggers/functions. No schema changes introduced. |
| II. Multi-Tenant RLS | Yes | PASS | R9 adds DB-level session variable to test fixtures, enabling real RLS enforcement in tests. Strengthens existing 3-layer defense. |
| III. Modular Django Architecture | Yes | PASS | No module boundaries changed. Cross-module integration tests verify existing boundaries. |
| IV. Application-Level Encryption | Peripheral | PASS | No encryption changes. Test settings preserve existing encryption key handling. |
| V. Secure Authentication | Peripheral | PASS | JWT config preserved in new `test_postgres.py` settings. HS256 for test speed (same as existing `test.py`). |
| VI. Fiscal Compliance (ARCA) | Yes | PASS | ARCA gap analysis (US7) documents homologation vs production differences. No ARCA code changes. |
| VII. Offline-First | Peripheral | PASS | Sync integration tests verify conflict resolution against real module operations. |
| VIII. Query Optimization | N/A | N/A | No query changes. |
| IX. Secure Data Operations | N/A | N/A | No data operation changes. |
| X. Test-Driven Development | Yes | PASS | PostgreSQL switch enables real RLS/trigger testing — strengthens TDD posture. |
| XI. JWT Authentication | Peripheral | PASS | Auth integration tests verify JWT+RLS across all modules. |
| XII. Rate Limiting | N/A | N/A | No rate limiting changes. |
| XIII. Cursor Pagination | N/A | N/A | No pagination changes. |
| XIV. API Documentation | Peripheral | PASS | Health endpoint added to OpenAPI schema via DRF. |

**Gate Result**: PASS — no violations. Feature strengthens compliance with Principles II (RLS) and X (TDD).

**Post-Phase-1 Re-check**: Same result. Design artifacts (data-model, contracts, quickstart) introduce no new violations.

## Project Structure

### Documentation (this feature)

```text
specs/011-backend-devops-coherence/
├── plan.md              # This file
├── research.md          # Phase 0 output (9 research items resolved)
├── data-model.md        # Phase 1 output (infrastructure entities)
├── quickstart.md        # Phase 1 output (developer onboarding)
├── contracts/
│   └── api-contract.md  # Phase 1 output (health/metrics endpoints)
└── tasks.md             # Phase 2 output (NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
backend/
├── docker-compose.yml              # MODIFY: merge profiles (dev/test/load), fix network
├── docker-compose.observability.yml # MODIFY: fix external network reference
├── docker-compose.test.yml          # DELETE: merged into docker-compose.yml
├── Dockerfile                       # MODIFY: add ENTRYPOINT, install postgresql-client
├── gravitea/settings/
│   ├── base.py                      # NO CHANGE
│   ├── development.py               # NO CHANGE
│   ├── production.py                # NO CHANGE
│   ├── test.py                      # NO CHANGE (preserved for fast unit path)
│   └── test_postgres.py             # CREATE: PostgreSQL test settings
├── pytest.ini                       # MODIFY: default to test_postgres settings
├── tests/
│   ├── conftest.py                  # MODIFY: add RLS session variable fixture
│   └── integration/                 # CREATE: cross-module integration tests
│       ├── __init__.py
│       ├── test_sale_to_stock.py
│       ├── test_sale_to_invoice.py
│       ├── test_auth_rls_cross_module.py
│       └── test_sync_conflict.py
├── observability/
│   └── prometheus.yml               # REVIEW: verify scrape targets
├── .env.example                     # MODIFY: add missing env vars
scripts/
└── bootstrap.sh                     # CREATE: Docker entrypoint script
database/SQL/
├── 000_init_database.sql            # MODIFY: make idempotent (IF NOT EXISTS)
├── 001_schema.sql                   # RENAME → 001_schema_reference.sql (deprecated)
├── 002_rls_policies.sql             # MODIFY: make idempotent
├── 003_stock_functions.sql          # MODIFY: make idempotent
├── 004_audit_functions.sql          # MODIFY: make idempotent
└── 005_hardening_constraints.sql    # MODIFY: make idempotent
claudedocs/
├── 011-cloud-sql-readiness.md       # CREATE: US6 analysis report
├── 011-arca-gap-analysis.md         # CREATE: US7 analysis report
├── 011-schema-drift-report.md       # CREATE: US4 schema drift report
├── 011-refactoring-proposals.md     # CREATE: Phase 10A refactoring audit (REFACTORING-EXPERT)
└── 011-backend-cohesion-report.md   # CREATE: Phase 10A cohesion analysis (BACKEND-ARCHITECT)
```

**Structure Decision**: Existing Django monolith structure retained. No new apps created. Cross-module integration tests go in `backend/tests/integration/`. Analysis reports go in `claudedocs/`. Bootstrap script goes in `scripts/`.

## Complexity Tracking

> No constitution violations to justify. Feature strengthens existing compliance.

| Aspect | Complexity | Notes |
|--------|-----------|-------|
| Docker consolidation | LOW | Profile merge is configuration, not new code |
| PostgreSQL test switch | MEDIUM | Requires new settings, fixture changes, potential test fixes |
| Observability validation | LOW | Wiring verification, env var fixes |
| Schema drift resolution | MEDIUM | Audit and idempotency fixes across 6 SQL scripts |
| Cross-module integration | MEDIUM | 3 new integration test files exercising existing code |
| Analysis reports | LOW | Documentation deliverables, no code changes |
| Code quality audit | MEDIUM | ~28K LOC across 6 modules, requires deep reading |
| Backend cohesion analysis | MEDIUM | Cross-module tracing of API-DB-Backend paths |
