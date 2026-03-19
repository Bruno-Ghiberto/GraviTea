# Implementation Plan: Producer Accounts

**Branch**: `013-producer-accounts` | **Date**: 2026-03-19 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/013-producer-accounts/spec.md`

## Summary

Implement the producer current account (cuenta corriente) module as a new Django app
`apps/cuentas` (label: `gravitea_cuentas`). Core deliverables: dual-ledger
`ProducerAccount` and immutable `AccountMovement` models, CEG_DEPOSIT trigger from
romaneo confirmation, manual movement API, posicion consolidada aggregation, account
statements, encrypted CUIT blind index search, and RLS-enforced tenant isolation.
4-agent wave execution: A1 (models) → A2 (services + romaneo hook) → A3 (API) → A4 (tests).

## Technical Context

**Language/Version**: Python 3.14.3
**Primary Dependencies**: Django 5.2.x, Django REST Framework, djangorestframework-simplejwt, cryptography (AES-256-GCM), argon2-cffi
**Storage**: PostgreSQL 18.1 — DECIMAL(17,3) for all monetary/weight fields; RLS on both cuentas tables
**Testing**: pytest + pytest-django; external runner via `scripts/run-tests-external.sh`
**Target Platform**: Linux server (GKE / Cloud SQL)
**Project Type**: Django web-service module (new app within monolith)
**Performance Goals**: Balance queries <100ms p95 for tenants with ≤5,000 accounts; consolidated position <200ms for ≤10 branches
**Constraints**: All account operations atomic (single transaction); no direct plaintext CUIT storage; backward-compatible romaneo confirmar (no existing test breakage)
**Scale/Scope**: One ProducerAccount per (tenant, producer, branch, grain type, campaign); append-only AccountMovement ledger; 40+ automated tests

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Ironclad Data Model** | ✅ PASS | DECIMAL(17,3) for all balances; ON DELETE RESTRICT FKs; append-only ledger (ValueError on save/delete if not adding) |
| **II. Multi-Tenant Isolation** | ✅ PASS | TenantBoundModel inheritance; RLS via cuentas_rls.sql; blind-index lookup uses tenant-scoped queries |
| **III. Modular Django Architecture** | ✅ PASS | New app `apps.cuentas` (gravitea_cuentas) per constitution §III Acopio Vertical listing |
| **IV. Application-Level Encryption** | ✅ PASS | EncryptedCharField + BlindIndexField from apps/core/encryption/fields.py; no plaintext CUIT stored |
| **VIII. Query Optimization** | ✅ PASS | select_for_update() on get_or_create; select_related in ViewSets; posicion consolidada uses SQL aggregation not Python loops |
| **IX. Secure Data Operations** | ✅ PASS | Explicit `fields` on all serializers; manual movement types whitelisted; ADJUSTMENT gated on permission |
| **X. Test-Driven Development** | ✅ PASS | 40+ tests targeting all 13 FRs; A4 agent writes tests in Wave 4 |
| **XIII. Cursor-Based Pagination** | ✅ PASS | Both ProducerAccountViewSet (`-created_at`, page_size=25) and AccountMovementViewSet (`-movement_at`, page_size=50) use CursorPagination |

**Violations**: None. Constitution fully satisfied.

## Project Structure

### Documentation (this feature)

```text
specs/013-producer-accounts/
├── plan.md              # This file (/speckit.plan output)
├── research.md          # Phase 0 output — all decisions resolved
├── data-model.md        # Phase 1 output — entity definitions
├── quickstart.md        # Phase 1 output — developer quick-start
├── contracts/           # Phase 1 output
│   └── accounts-api.md  # REST API contracts
└── tasks.md             # Phase 2 output (/speckit.tasks — NOT created here)
```

### Source Code

```text
backend/
├── apps/
│   ├── cuentas/                          # NEW — gravitea_cuentas
│   │   ├── __init__.py
│   │   ├── apps.py                       # CuentasConfig
│   │   ├── admin.py
│   │   ├── models/
│   │   │   ├── __init__.py               # Re-exports
│   │   │   ├── producer_account.py       # ProducerAccount
│   │   │   └── account_movement.py       # AccountMovement (IMMUTABLE)
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── accounts.py               # AccountService, CEGDepositService, ManualMovementService
│   │   │   └── statements.py             # StatementService, PosicionConsolidadaService
│   │   ├── serializers/
│   │   │   ├── __init__.py
│   │   │   └── accounts.py               # All serializers
│   │   ├── views/
│   │   │   ├── __init__.py
│   │   │   └── accounts.py               # ViewSets + views
│   │   ├── urls.py
│   │   ├── migrations/
│   │   │   └── 0001_producer_accounts.py
│   │   └── management/commands/
│   │       └── check_account_balance.py
│   └── acopio/
│       └── views/
│           └── romaneo.py                # MODIFIED — transaction.atomic + CEG_DEPOSIT hook
├── database/sql/
│   └── cuentas_rls.sql                   # NEW — RLS policies
├── gravitea/settings/
│   └── base.py                           # MODIFIED — add "apps.cuentas" to INSTALLED_APPS
├── gravitea/
│   └── urls.py                           # MODIFIED — add cuentas/ include
└── tests/cuentas/                        # NEW
    ├── __init__.py
    ├── conftest.py
    ├── test_account_models.py
    ├── test_account_api.py
    ├── test_account_services.py
    └── test_ceg_deposit_integration.py
```

**Structure Decision**: Web-service (backend-only) module following `apps/acopio/` precedent.
New app at `backend/apps/cuentas/`. Tests at `backend/tests/cuentas/`.

## Agent Team Protocol

### tmux Layout (4 panes)

```
┌──────────────────────┬──────────────────────┐
│ A1: Models (py-exp)  │ A2: Services (be-ar) │
│                      │                      │
├──────────────────────┼──────────────────────┤
│ A3: API (be-ar)      │ A4: Tests (qa-eng)   │
│                      │                      │
└──────────────────────┴──────────────────────┘
```

### Wave Execution

```
Wave 1: A1 — Models + Migration + RLS + App Boilerplate
    │ GATE G1: models importable; no missing migrations
    ▼
Wave 2: A2 — Services + Romaneo Integration Hook
    │ GATE G2: services importable; romaneo integration compiles
    ▼
Wave 3: A3 — API Layer + Blind Index Search
    │ GATE G3: URL routes registered; endpoints respond 200/401
    ▼
Wave 4: A4 — Full Test Suite
    │ GATE G4: all tests pass via run-tests-external.sh
    ▼
DONE + regression check on tests/acopio/
```

| Agent | Type | Scope |
|-------|------|-------|
| A1 | python-expert | ProducerAccount, AccountMovement, migration, RLS, app boilerplate |
| A2 | backend-architect | AccountService, CEGDepositService, ManualMovementService, StatementService, PosicionConsolidadaService, romaneo confirmar hook |
| A3 | backend-architect | Serializers, ViewSets, URLs, cursor pagination, CUIT blind index search |
| A4 | quality-engineer | 43+ tests: models, immutability, API, services, CEG_DEPOSIT integration, tenant isolation, blind index |

## Complexity Tracking

No violations. No unusual complexity beyond established patterns.

## Checkpoint Gates

### G1: After Wave 1

```bash
cd backend
DJANGO_SETTINGS_MODULE=gravitea.settings.test \
  .venv/bin/python -c "from apps.cuentas.models import ProducerAccount, AccountMovement; print('OK')"
.venv/bin/python manage.py makemigrations --check --dry-run
```

### G2: After Wave 2

```bash
cd backend
DJANGO_SETTINGS_MODULE=gravitea.settings.test \
  .venv/bin/python -c "from apps.cuentas.services.accounts import create_ceg_deposit; print('OK')"
DJANGO_SETTINGS_MODULE=gravitea.settings.test \
  .venv/bin/python -c "from apps.cuentas.services.statements import generate_statement; print('OK')"
```

### G3: After Wave 3

```bash
cd backend
DJANGO_SETTINGS_MODULE=gravitea.settings.test \
  .venv/bin/python -c "from apps.cuentas.urls import urlpatterns; print(f'{len(urlpatterns)} routes')"
```

### G4: After Wave 4

```bash
bash scripts/run-tests-external.sh -n spec13-final tests/cuentas/
cat Docs/Tests/spec13-final.status    # → PASSED
cat Docs/Tests/spec13-final.summary
# Then regression check:
bash scripts/run-tests-external.sh -n spec13-regression tests/acopio/
cat Docs/Tests/spec13-regression.status
```

## Done Criteria

All 14 criteria from spec.md must be met:

1. ProducerAccount + AccountMovement models importable, all fields per Data Model v1.0 §6
2. `0001_producer_accounts.py` applies cleanly on a fresh DB
3. `cuentas_rls.sql` defines tenant isolation policies for both tables
4. `gravitea_cuentas` in INSTALLED_APPS; URLs mounted at `/api/v1/cuentas/`
5. Romaneo CONFORME → ProducerAccount + AccountMovement atomically in one transaction
6. AccountMovement.save() and .delete() raise ValueError; API returns 405 on PATCH/DELETE
7. SERVICE_CHARGE, RETIRO, RETENTION_DEDUCTION, ADJUSTMENT via API; ADJUSTMENT requires supervisor
8. Posicion Consolidada endpoint returns aggregated balances; never stored
9. Account Statement returns opening balance + movements + closing balance
10. producer_cuit encrypted; equality search via HMAC-SHA256 blind index
11. Cross-tenant queries return empty; tenant can never access another's accounts
12. Management command detects stored vs ledger drift
13. 40+ tests pass via `scripts/run-tests-external.sh`
14. No regressions in `tests/acopio/` (especially romaneo confirmar tests)
