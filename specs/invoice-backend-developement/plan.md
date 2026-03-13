# Implementation Plan: Electronic Invoicing Backend (Facturacion)

**Branch**: `invoice-backend-developement` | **Date**: 2026-02-10 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/invoice-backend-developement/spec.md`

## Summary

Build `apps/facturacion/` Django app integrating with Argentina's ARCA electronic invoicing system. The module implements WSAA certificate-based authentication with Redis-cached tokens, WSFEv1 SOAP API for CAE invoice authorization, an immutable Comprobante ledger with TenantBoundModel isolation, fiscal QR code generation per RG 4291, and CAEA offline pre-authorization. All ARCA interactions are synchronous (no background queue). Concurrency on CbteNro is managed via `select_for_update()`.

## Technical Context

**Language/Version**: Python 3.14.3
**Primary Dependencies**: Django 5.2.x, Django REST Framework, zeep (SOAP client), cryptography (AES-256-GCM via existing EncryptedTextField), lxml (XML generation for TRA), prometheus-client
**Storage**: PostgreSQL 18.1 with RLS, Redis 7.x (token caching)
**Testing**: pytest + pytest-django (existing test infrastructure)
**Target Platform**: Linux server (Docker/Kubernetes on GCP)
**Project Type**: Web application — backend module within existing monolith
**Performance Goals**: WSAA auth <5s (uncached), <50ms (cached); CAE issuance <10s end-to-end; API lists <100ms for 1000 records
**Constraints**: Synchronous ARCA calls only (no background queue); DECIMAL(17,3) for financial amounts; append-only ledger for authorized comprobantes; no PDF rendering
**Scale/Scope**: Multi-tenant, cursor-based pagination, expected low-medium volume (SMB retail)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Requirement | Plan Compliance | Status |
|---|-----------|-------------|-----------------|--------|
| I | Ironclad Data Model | DECIMAL(17,3), append-only ledger, ON DELETE RESTRICT | Comprobante uses DecimalField(max_digits=17, decimal_places=3), immutability enforced in save()/delete(), all FKs RESTRICT | PASS |
| II | Multi-Tenant Isolation | RLS on all transactional tables, three-layer isolation | All models inherit TenantBoundModel, RLS policies in migration, serializer + model + DB validation | PASS |
| III | Modular Django Architecture | Django Apps with clear boundaries | New `apps/facturacion/` app with `app_label: gravitea_facturacion`, lightweight views, domain services | PASS |
| IV | Application-Level Encryption | AES-256-GCM for PII/fiscal | Private keys stored via existing EncryptedTextField, master keys in Secret Manager | PASS |
| V | Secure Authentication | JWT tokens, IDOR prevention | Existing auth middleware applies; facturacion endpoints require authenticated tenant context | PASS |
| VI | Fiscal Compliance | ARCA/WSAA integration, SOAP/HTTPS, TRA/CMS/LoginCms, JSONB response storage | Full WSFEv1 implementation with WSAA auth, arca_response JSONB field | PASS |
| VII | Offline-First | CAEA support, deferred fiscalization | User Story 7 implements CAEA pre-authorization and manual batch reporting | PASS |
| VIII | Query Optimization | select_related/prefetch_related | All ViewSets use select_related for FK joins, prefetch_related for reverse relations | PASS |
| IX | Secure Data Operations | Explicit fields (no __all__), bulk operations | All serializers use explicit `fields` list, no `__all__` | PASS |
| X | Test-Driven Development | 80% min, 95% critical paths | Test plan targets 80% overall, 95% for WSAA/CAE/validation/immutability | PASS |
| XI | JWT Authentication | Custom claims with tenant_id, branch_id | Existing JWT infrastructure; facturacion endpoints use IsAuthenticated + tenant context | PASS |
| XII | Rate Limiting | Progressive lockout on auth endpoints | Invoice issuance inherits existing rate limiting middleware; ARCA calls are naturally throttled by SOAP latency | PASS |
| XIII | Cursor-Based Pagination | Default 100, max 1000, ordered by created_at | ComprobanteViewSet uses existing CursorPagination class | PASS |
| XIV | API Documentation | drf-spectacular OpenAPI | All endpoints annotated with @extend_schema for Swagger/ReDoc generation | PASS |

**Gate Result**: ALL PASS — No violations. Proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/invoice-backend-developement/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0: Technology decisions
├── data-model.md        # Phase 1: Entity definitions
├── quickstart.md        # Phase 1: Developer setup guide
├── contracts/           # Phase 1: API contracts
│   └── facturacion-api.yaml  # OpenAPI 3.0 schema
└── tasks.md             # Phase 2: Implementation tasks (/speckit.tasks)
```

### Source Code (repository root)

```text
backend/
├── apps/
│   └── facturacion/                 # NEW Django app
│       ├── __init__.py
│       ├── apps.py                  # AppConfig (gravitea_facturacion)
│       ├── constants.py             # CbteTipo, DocTipo, CondicionIVA, AlicIvaId enums
│       ├── models.py                # ARCACredential, PuntoDeVenta, Comprobante, AlicIva, Tributo, CbteAsoc, CAEA
│       ├── serializers.py           # DRF serializers (explicit fields, no __all__)
│       ├── views.py                 # ViewSets (lightweight orchestration)
│       ├── urls.py                  # URL routing under /api/v1/facturacion/
│       ├── schema.py                # drf-spectacular schema extensions
│       ├── validators.py            # validate_importes, validate_iva_breakdown, validate_service_dates, validate_tributos
│       ├── qr.py                    # Fiscal QR code generation (RG 4291)
│       ├── metrics.py               # Prometheus counters/histograms for ARCA
│       ├── services.py              # InvoiceService (CAE issuance orchestration)
│       ├── arca/                    # ARCA integration subpackage
│       │   ├── __init__.py          # ARCAClient facade
│       │   ├── wsaa.py              # WSAAClient: TRA generation, CMS signing, LoginCms
│       │   ├── wsfe.py              # WSFEv1Client: FECAESolicitar, FECompUltimoAutorizado, FECompConsultar
│       │   ├── caea.py              # CAEAService: FECAEASolicitar, FECAEARegInformativo
│       │   └── exceptions.py        # ARCAAuthError, ARCARequestError, ARCAComprobanteRejected
│       └── migrations/
│           └── 0001_initial.py      # Models + RLS policies
├── tests/
│   └── facturacion/                 # NEW test directory
│       ├── __init__.py
│       ├── conftest.py              # Facturacion-specific fixtures
│       ├── unit/
│       │   ├── test_constants.py    # CbteTipo resolution, CondicionIVA matrix
│       │   ├── test_validators.py   # Amount validation, service dates, tributos
│       │   ├── test_qr.py           # Fiscal QR payload generation
│       │   ├── test_wsaa.py         # TRA generation, CMS mock
│       │   └── test_models.py       # Immutability enforcement, model constraints
│       └── integration/
│           ├── test_wsaa_homo.py    # WSAA homologation integration (marked @pytest.mark.integration)
│           ├── test_wsfe_homo.py    # WSFEv1 homologation integration
│           └── test_api.py          # DRF endpoint integration tests
└── database/sql/
    └── facturacion_rls.sql          # RLS policies for facturacion tables
```

**Structure Decision**: Follows existing monolith pattern (`apps/{module}/` with `arca/` subpackage for ARCA-specific SOAP clients). Test structure mirrors `tests/auth/` and `tests/inventario/` conventions with unit/integration split.

## Complexity Tracking

No constitution violations to justify. All patterns align with existing codebase conventions.

## Implementation Phases

### Phase 1: Foundation (Models + WSAA Auth + Credentials API)

**Goal**: Tenant can upload ARCA credentials; system can authenticate with WSAA.

| Component | Files | Dependencies |
|-----------|-------|--------------|
| Django app scaffolding | `apps/facturacion/apps.py`, `__init__.py` | None |
| Constants/Enums | `constants.py` | None |
| Models | `models.py` | TenantBoundModel, EncryptedTextField |
| Migrations + RLS | `migrations/0001_initial.py`, `database/sql/facturacion_rls.sql` | PostgreSQL |
| WSAA Client | `arca/wsaa.py` | zeep, cryptography, lxml |
| ARCA Exceptions | `arca/exceptions.py` | None |
| Credentials Serializer + View | `serializers.py`, `views.py`, `urls.py` | DRF |
| Unit Tests | `tests/facturacion/unit/test_wsaa.py`, `test_models.py` | pytest |

### Phase 2: CAE Invoice Issuance (Core Workflow)

**Goal**: Tenant can issue an invoice and receive a CAE from ARCA.

| Component | Files | Dependencies |
|-----------|-------|--------------|
| WSFEv1 Client | `arca/wsfe.py` | zeep, WSAA (Phase 1) |
| Validators | `validators.py` | constants.py |
| Invoice Service | `services.py` | wsfe.py, wsaa.py, models, validators |
| Invoice API endpoints | `views.py`, `serializers.py`, `urls.py` | DRF, services.py |
| Metrics | `metrics.py` | prometheus-client, existing REGISTRY |
| Unit Tests | `test_validators.py`, `test_constants.py` | pytest |
| Integration Tests | `test_wsfe_homo.py`, `test_api.py` | ARCA homologation |

### Phase 3: QR + Credit/Debit Notes + CAEA

**Goal**: Complete invoicing feature set including corrections and offline mode.

| Component | Files | Dependencies |
|-----------|-------|--------------|
| Fiscal QR | `qr.py` | base64, json |
| Credit/Debit Note support | Update `services.py`, `validators.py` | Phase 2 |
| CAEA Service | `arca/caea.py` | wsfe.py, WSAA (Phase 1) |
| Schema annotations | `schema.py` | drf-spectacular |
| Unit Tests | `test_qr.py` | pytest |
| Integration Tests | Update `test_api.py` | Phase 2 tests |
