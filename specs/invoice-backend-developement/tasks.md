# Tasks: Electronic Invoicing Backend (Facturacion)

**Input**: Design documents from `/specs/invoice-backend-developement/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/facturacion-api.yaml, quickstart.md
**Tests**: Included — Constitution Section X mandates 80% min coverage, 95% critical paths

**Organization**: Tasks grouped by user story. Each story is independently testable after foundational phase.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US7)
- All paths relative to repository root (`backend/apps/facturacion/` for source, `backend/tests/facturacion/` for tests)

---

## Phase 1: Setup

**Purpose**: Project initialization — install dependency, scaffold Django app

- [ ] T001 Install `zeep>=4.0,<5.0` dependency in `backend/requirements.txt` and pip install
- [ ] T002 Create Django app scaffolding: `backend/apps/facturacion/__init__.py` and `backend/apps/facturacion/apps.py` with `AppConfig(name='apps.facturacion', label='gravitea_facturacion')`
- [ ] T003 [P] Create ARCA subpackage: `backend/apps/facturacion/arca/__init__.py`
- [ ] T004 Register `'apps.facturacion'` in `INSTALLED_APPS` in `backend/gravitea/settings/base.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: All models, constants, exceptions, migration, RLS, URL routing, test infrastructure. MUST complete before ANY user story.

**Warning**: No user story work can begin until this phase is complete.

### Constants & Exceptions

- [ ] T005 [P] Create enums (CbteTipo, DocTipo, CondicionIVA, Concepto, AlicIvaId) in `backend/apps/facturacion/constants.py` — include all type codes from spec (A=1,2,3 / B=6,7,8 / C=11,12,13 / M=51,52,53) and NOTA_DEBITO/NOTA_CREDITO variants
- [ ] T006 [P] Create ARCA exception hierarchy (ARCAAuthError, ARCARequestError, ARCAComprobanteRejected with code, message, observations fields) in `backend/apps/facturacion/arca/exceptions.py`

### Models

- [ ] T007 Create all models in `backend/apps/facturacion/models.py`: ARCACredential (EncryptedTextField for private_key_pem, UniqueConstraint on tenant_id+is_production), PuntoDeVenta (UniqueConstraint on tenant_id+numero, CheckConstraint 1-99999), Comprobante (immutable save()/delete() overrides for AUTORIZADO/OBSERVADO, UniqueConstraint on tenant_id+punto_venta+cbte_tipo+cbte_nro, DecimalField(17,3) for all amounts, JSONB for arca_response/arca_errors, ON DELETE RESTRICT for all FKs), AlicIva, Tributo, CbteAsoc, CAEA — all inheriting TenantBoundModel where applicable per data-model.md

### Migration & RLS

- [ ] T008 Generate initial migration via `python manage.py makemigrations facturacion` producing `backend/apps/facturacion/migrations/0001_initial.py`
- [ ] T009 [P] Write RLS policies for facturacion_arcacredential, facturacion_puntodeventa, facturacion_comprobante, facturacion_caea in `backend/database/sql/facturacion_rls.sql` (ENABLE ROW LEVEL SECURITY, FORCE, tenant_id = current_setting policy)
- [ ] T010 Add `RunSQL` operations for RLS policies (with reverse SQL) in `backend/apps/facturacion/migrations/0001_initial.py`
- [ ] T011 Run `python manage.py migrate` and verify all tables + RLS policies apply cleanly

### Test Infrastructure & URL Routing

- [ ] T012 [P] Create test directory structure: `backend/tests/facturacion/__init__.py`, `backend/tests/facturacion/conftest.py` (facturacion-specific fixtures: credential_factory, punto_venta_factory, comprobante_factory), `backend/tests/facturacion/unit/__init__.py`, `backend/tests/facturacion/integration/__init__.py`
- [ ] T013 [P] Create URL configuration with DRF DefaultRouter in `backend/apps/facturacion/urls.py` (empty for now — endpoints added per user story)
- [ ] T014 Wire `path("api/v1/facturacion/", include("apps.facturacion.urls"))` into main urlconf in `backend/gravitea/urls.py`

### PuntoDeVenta API (shared infrastructure)

- [ ] T015 [P] Create PuntoDeVentaSerializer (explicit fields: id, numero, tipo, description, is_active, fecha_alta) in `backend/apps/facturacion/serializers.py`
- [ ] T016 [P] Create PuntoDeVentaViewSet (list, create, retrieve, partial_update) with select_related in `backend/apps/facturacion/views.py`
- [ ] T017 Register PuntoDeVenta routes in `backend/apps/facturacion/urls.py`

**Checkpoint**: Foundation ready — all models migrated, RLS active, test fixtures available, PuntoDeVenta API functional. User story implementation can now begin.

---

## Phase 3: User Story 3 — Multi-Tenant Credential Management (Priority: P1) MVP

**Goal**: Tenant admin can upload ARCA certificates; private keys stored encrypted via AES-256-GCM; one credential per (tenant, environment) pair enforced.

**Independent Test**: POST a certificate+key via API, verify private key is encrypted in DB, confirm cross-tenant access blocked by RLS.

### Tests for US3

- [ ] T018 [P] [US3] Write unit tests for ARCACredential model in `backend/tests/facturacion/unit/test_models.py`: unique constraint on (tenant_id, is_production), EncryptedTextField storage, CUIT 11-digit validation, certificate_expires_at system check

### Implementation for US3

- [ ] T019 [US3] Create ARCACredentialWriteSerializer (accepts cuit_holder, cuit_represented, certificate_pem, private_key_pem, is_production; validates PEM format, CUIT 11-digit format with check digit verification, and environment uniqueness) in `backend/apps/facturacion/serializers.py`
- [ ] T020 [US3] Create ARCACredentialReadSerializer (redacts private_key_pem, exposes cuit_holder, is_production, is_active, certificate_expires_at, created_at) in `backend/apps/facturacion/serializers.py`
- [ ] T021 [US3] Create ARCACredentialViewSet (list, create, retrieve, partial_update for cert rotation, destroy=soft-deactivate) with `get_serializer_class()` switching read/write in `backend/apps/facturacion/views.py`
- [ ] T022 [US3] Register credential routes (`credentials/`) in `backend/apps/facturacion/urls.py`
- [ ] T023 [US3] Implement Django system check for certificate expiration warning (`arca.W001` when expires_at < 30 days) in `backend/apps/facturacion/apps.py`

**Checkpoint**: Credential CRUD functional. Tenant can upload/manage ARCA certificates. Private keys encrypted at rest.

---

## Phase 4: User Story 1 — WSAA Authentication & Token Management (Priority: P1)

**Goal**: System authenticates with ARCA WSAA using TRA/CMS/LoginCms flow; Token+Sign cached in Redis with 11h TTL; cached calls return in <50ms.

**Independent Test**: Upload test certificate, trigger WSAA LoginCms against `wsaahomo.afip.gov.ar`, verify Token+Sign returned and cached in Redis.

**Depends on**: US3 (needs ARCACredential to retrieve certificate/key)

### Tests for US1

- [ ] T024 [P] [US1] Write unit tests for TRA XML generation (uniqueId=timestamp, generationTime=now-5m, expirationTime=now+10m, service=wsfe) in `backend/tests/facturacion/unit/test_wsaa.py`
- [ ] T025 [P] [US1] Write unit tests for CMS/PKCS#7 signing (mock private key + certificate) and token caching (cache hit/miss/expiry/Redis unavailable fallback to direct WSAA call) in `backend/tests/facturacion/unit/test_wsaa.py`

### Implementation for US1

- [ ] T026 [US1] Implement WSAAClient class in `backend/apps/facturacion/arca/wsaa.py`: `generate_tra(service)` using lxml, `sign_tra(tra_xml, private_key_pem, cert_pem)` using cryptography PKCS7SignatureBuilder, `login(signed_tra, wsdl_url)` using zeep
- [ ] T027 [US1] Implement Token+Sign Redis caching in `backend/apps/facturacion/arca/wsaa.py`: cache key `arca_auth:{tenant_cuit}:{service_id}`, TTL=11h, `get_or_refresh()` method that proactively refreshes when TTL<1h, `invalidate()` for forced re-auth
- [ ] T028 [US1] Create ARCAClient facade in `backend/apps/facturacion/arca/__init__.py` that orchestrates: load credential → check cache → WSAA auth if needed → return (token, sign, cuit, is_production)

**Checkpoint**: WSAA authentication complete. System can obtain and cache Token+Sign from ARCA. Ready for WSFEv1 calls.

---

## Phase 5: User Story 4 — CbteTipo Resolution & Amount Validation (Priority: P2)

**Goal**: Automatic CbteTipo resolution from CondicionIVA matrix; amount validation with dual-tolerance; service date conditional rules; IVA/Tributo structure validation.

**Independent Test**: Unit tests covering all CondicionIVA combinations and amount validation edge cases — no ARCA API calls needed.

**Depends on**: None (pure logic, can run in parallel with US1 after foundation)

### Tests for US4

- [ ] T029 [P] [US4] Write unit tests for CbteTipo resolution (RI→RI=A, RI→CF=B, RI→Mono=B, RI→Exento=B, Mono→any=C, Exento→any=C, invalid emitter raises ValueError) in `backend/tests/facturacion/unit/test_constants.py`
- [ ] T030 [P] [US4] Write unit tests for validators in `backend/tests/facturacion/unit/test_validators.py`: validate_importes (valid, mismatch, dual-tolerance edge cases), validate_iva_breakdown (mandatory for A/B, prohibited for C, sum mismatch), validate_service_dates (omit for Concepto=1, required for 2/3, date logic), validate_tributos (omit Tributos element when ImpTrib=0)

### Implementation for US4

- [ ] T031 [US4] Implement `resolver_tipo_comprobante(emitter_condition, receiver_condition, operation_type)` returning CbteTipo for factura/NC/ND in `backend/apps/facturacion/constants.py`
- [ ] T032 [US4] Implement all validators in `backend/apps/facturacion/validators.py`: `validate_importes()` with dual-tolerance (0.01% relative OR 0.01 absolute), `validate_iva_breakdown()` (sum checks + type-conditional mandatory/prohibited), `validate_service_dates()` (Concepto-conditional OMIT/REQUIRE), `validate_tributos()` (omit when ImpTrib=0)

**Checkpoint**: All validation logic complete. CbteTipo resolution covers full CondicionIVA matrix. Ready for CAE issuance.

---

## Phase 6: User Story 2 — CAE Invoice Issuance via WSFEv1 (Priority: P1)

**Goal**: Tenant can issue an invoice and receive a CAE from ARCA. Full flow: auth → last number → validate → submit → persist immutable record.

**Independent Test**: Issue a Factura B (CbteTipo=6) against ARCA homologation, verify CAE returned, comprobante stored as AUTORIZADO and immutable.

**Depends on**: US1 (WSAA auth), US4 (validators)

### Tests for US2

- [ ] T033 [P] [US2] Write unit tests for Comprobante immutability in `backend/tests/facturacion/unit/test_models.py`: save() raises ValueError for AUTORIZADO/OBSERVADO records, delete() always raises ValueError, DRAFT/RECHAZADO can be updated
- [ ] T034 [P] [US2] Write integration tests for comprobante API in `backend/tests/facturacion/integration/test_api.py`: emitir endpoint validation errors (bad amounts, wrong dates), list with cursor pagination, retrieve by ID, status filtering

### Implementation for US2

- [ ] T035 [US2] Implement WSFEv1Client in `backend/apps/facturacion/arca/wsfe.py`: `get_ultimo_comprobante(pto_vta, cbte_tipo)` via FECompUltimoAutorizado, `solicitar_cae(comprobante_data)` via FECAESolicitar (handle A/O/R results), `consultar_comprobante(pto_vta, cbte_tipo, cbte_nro)` via FECompConsultar
- [ ] T036 [US2] Implement InvoiceService in `backend/apps/facturacion/services.py`: `issue_comprobante()` with `@transaction.atomic` + `select_for_update()` on PuntoDeVenta, full flow (auth → ultimo → validate → save DRAFT → submit → update with CAE → AUTORIZADO), handle RECHAZADO (store errors, allow retry)
- [ ] T037 [US2] Implement network failure recovery in `backend/apps/facturacion/services.py`: `_recover_from_timeout()` using FECompUltimoAutorizado to check if CAE was granted, then FECompConsultar to retrieve it
- [ ] T038 [US2] Create ComprobanteEmitirSerializer (nested writable AlicIva, Tributo, CbteAsoc; validates amounts via validators.py; explicit fields; accept amounts with up to 3 decimal places per constitution DECIMAL(17,3)) in `backend/apps/facturacion/serializers.py`
- [ ] T039 [US2] Create ComprobanteReadSerializer (all fields + computed qr_url for authorized comprobantes; nested read-only AlicIva, Tributo, CbteAsoc; format amount fields to 2 decimal places for display per FR-022) in `backend/apps/facturacion/serializers.py`
- [ ] T040 [US2] Create ComprobanteViewSet in `backend/apps/facturacion/views.py`: list (cursor pagination, select_related punto_venta, prefetch_related aliciva_set/tributo_set/cbteasoc_set, filterset for status/cbte_tipo/cbte_fch range), retrieve, `@action emitir` calling InvoiceService
- [ ] T041 [US2] Register comprobante routes (list, detail, emitir) in `backend/apps/facturacion/urls.py`

**Checkpoint**: Core invoicing functional. Tenant can issue invoices, receive CAE, view authorized comprobantes. Immutability enforced.

---

## Phase 7: User Story 5 — Fiscal QR Code Generation (Priority: P2)

**Goal**: Generate ARCA-compliant fiscal QR code (RG 4291) for authorized comprobantes.

**Independent Test**: Generate QR for a mock authorized comprobante, verify JSON payload fields and base64url encoding match spec.

**Depends on**: US2 (needs authorized comprobante with CAE)

### Tests for US5

- [ ] T042 [P] [US5] Write unit tests for fiscal QR in `backend/tests/facturacion/unit/test_qr.py`: JSON payload structure (ver=1, all required fields), base64url encoding (no padding), URL prefix `https://www.afip.gob.ar/fe/qr/?p=`, error for non-authorized comprobante

### Implementation for US5

- [ ] T043 [US5] Implement `generate_fiscal_qr_data(comprobante)` in `backend/apps/facturacion/qr.py`: JSON payload with ver, fecha, cuit, ptoVta, tipoCmp, nroCmp, importe, moneda, ctz, tipoDocRec, nroDocRec, tipoCodAut='E', codAut=CAE; base64url encode; return full URL
- [ ] T044 [US5] Add `@action(detail=True) qr` endpoint to ComprobanteViewSet in `backend/apps/facturacion/views.py` returning `{"qr_url": "..."}` for authorized comprobantes, 400 for others

**Checkpoint**: Authorized comprobantes now have fiscal QR code URLs. Complete for print/display integration.

---

## Phase 8: User Story 6 — Credit and Debit Notes (Priority: P2)

**Goal**: Issue Nota de Credito/Debito referencing an original Factura via CbtesAsoc. Type compatibility enforced (A→A, B→B, C→C).

**Independent Test**: Issue a Factura, then issue a NC referencing it, verify CbtesAsoc included in ARCA request and CAE granted.

**Depends on**: US2 (extends invoice service)

### Tests for US6

- [ ] T045 [P] [US6] Write unit tests for CbteAsoc validation in `backend/tests/facturacion/unit/test_validators.py`: type compatibility (A→A pass, A→B fail with error 202), referenced comprobante existence soft-check

### Implementation for US6

- [ ] T046 [US6] Implement `validate_cbtes_asoc(cbte_tipo, cbtes_asoc_list)` in `backend/apps/facturacion/validators.py`: type compatibility matrix (A→A, B→B, C→C), referenced comprobante local existence check (soft warning)
- [ ] T047 [US6] Extend InvoiceService in `backend/apps/facturacion/services.py` to include CbtesAsoc in FECAESolicitar request when issuing NC/ND
- [ ] T048 [US6] Update ComprobanteEmitirSerializer in `backend/apps/facturacion/serializers.py` to validate cbtes_asoc is required for NC/ND CbteTipo codes (2,3,7,8,12,13,52,53) and forbidden for Factura codes

**Checkpoint**: Full correction workflow. NC/ND can reference original facturas with type-safe validation.

---

## Phase 9: User Story 7 — CAEA Offline Authorization (Priority: P3)

**Goal**: Pre-request CAEA for biweekly quincena; issue offline invoices with CAEA; batch report via FECAEARegInformativo within 5-day deadline.

**Independent Test**: Request CAEA from homologation, create offline invoices, batch report them.

**Depends on**: US1 (WSAA auth), US2 (comprobante infrastructure)

### Tests for US7

- [ ] T049a [P] [US7] Write unit tests for CAEA model and CAEAService in `backend/tests/facturacion/unit/test_caea.py`: CAEA status transitions (ACTIVE→REPORTED, ACTIVE→REPORTED_NO_MOVEMENT, ACTIVE→EXPIRED), UniqueConstraint on (tenant_id, punto_venta, periodo, orden), solicitar/informar/sin_movimiento mock tests, deadline warning flag logic
- [ ] T049b [P] [US7] Write unit tests for CAEA-mode invoice issuance in `backend/tests/facturacion/unit/test_models.py`: comprobante with caea FK stored as DRAFT, batch report transitions

### Implementation for US7

- [ ] T049 [US7] Implement CAEAService in `backend/apps/facturacion/arca/caea.py`: `solicitar_caea(pto_vta, periodo, orden)` via FECAEASolicitar, `informar_comprobantes(caea, comprobantes)` via FECAEARegInformativo, `informar_sin_movimiento(caea)` via FECAEASinMovimientoInformar
- [ ] T050 [US7] Create CAEASerializer (read: id, punto_venta_numero, caea_code, periodo, orden, dates, status) and CAEASolicitarSerializer (write: punto_venta_numero, periodo, orden) in `backend/apps/facturacion/serializers.py`
- [ ] T051 [US7] Create CAEAViewSet in `backend/apps/facturacion/views.py`: list, `@action solicitar`, `@action(detail=True) informar`, `@action(detail=True) sin_movimiento`
- [ ] T052 [US7] Register CAEA routes in `backend/apps/facturacion/urls.py`
- [ ] T053 [US7] Extend InvoiceService in `backend/apps/facturacion/services.py` to support CAEA-mode: when active CAEA exists for (punto_venta, current period), store comprobante with caea FK and status=DRAFT (pending batch report)

**Checkpoint**: Offline invoicing complete. CAEA pre-authorization, offline issuance, and batch reporting functional.

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Observability, documentation, integration tests, final validation

- [ ] T053a Implement VALIDANDO recovery check in `backend/apps/facturacion/services.py`: on-demand method `recover_stale_comprobantes()` that queries Comprobante.objects.filter(status='VALIDANDO') and runs the recovery algorithm (FECompUltimoAutorizado + FECompConsultar) for each, transitioning to AUTORIZADO/OBSERVADO/RECHAZADO. Add unit test with mocked ARCA responses in `backend/tests/facturacion/unit/test_models.py`
- [ ] T054 [P] Create Prometheus metrics in `backend/apps/facturacion/metrics.py`: `arca_wsaa_auth_total` Counter (labels: result), `arca_cae_result_total` Counter (labels: cbte_tipo, resultado), `arca_soap_duration_seconds` Histogram (labels: method) — all registered on existing REGISTRY from `apps.core.observability.metrics`. Note: omit `tenant_id` from labels to avoid cardinality explosion; tenant context is available in log correlation instead
- [ ] T055 Integrate metrics instrumentation into WSAAClient, WSFEv1Client, and InvoiceService: increment counters on auth success/failure, CAE approved/rejected/observed; observe SOAP call duration
- [ ] T056 [P] Add drf-spectacular `@extend_schema` annotations to all ViewSets and actions in `backend/apps/facturacion/schema.py` (or inline on views) per contracts/facturacion-api.yaml
- [ ] T057 [P] Write WSAA homologation integration test (marked `@pytest.mark.integration`) in `backend/tests/facturacion/integration/test_wsaa_homo.py`: full TRA → CMS → LoginCms flow against wsaahomo.afip.gov.ar
- [ ] T058 [P] Write WSFEv1 homologation integration test (marked `@pytest.mark.integration`) in `backend/tests/facturacion/integration/test_wsfe_homo.py`: full FECompUltimoAutorizado + FECAESolicitar flow
- [ ] T059 Run quickstart.md validation: install dep → migrate → create credential → create PtoVta → issue invoice → verify CAE end-to-end

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup) ──────► Phase 2 (Foundational) ──────┬──► Phase 3 (US3) ──► Phase 4 (US1) ──┐
                                                       │                                       │
                                                       ├──► Phase 5 (US4) ─────────────────────┤
                                                       │                                       │
                                                       │                        ┌──────────────┤
                                                       │                        ▼              │
                                                       │                  Phase 6 (US2) ───────┤
                                                       │                        │              │
                                                       │               ┌────────┼──────┐       │
                                                       │               ▼        ▼      ▼       │
                                                       │          Phase 7  Phase 8  Phase 9    │
                                                       │           (US5)    (US6)    (US7)     │
                                                       │               │        │      │       │
                                                       │               └────────┼──────┘       │
                                                       │                        ▼              │
                                                       └──────────────► Phase 10 (Polish) ◄────┘
```

### User Story Dependencies

| Story | Depends On | Can Parallel With |
|-------|-----------|-------------------|
| US3 (Credentials) | Foundation only | US4 |
| US1 (WSAA Auth) | US3 | US4 |
| US4 (Validation) | Foundation only | US3, US1 |
| US2 (CAE Issuance) | US1 + US4 | — |
| US5 (QR) | US2 | US6, US7 |
| US6 (NC/ND) | US2 | US5, US7 |
| US7 (CAEA) | US1, US2 infra | US5, US6 |

### Within Each User Story

1. Tests FIRST → ensure they FAIL before implementation
2. Models/constants before services
3. Services before serializers/views
4. Serializers before views
5. Wire URL routes last

### Parallel Opportunities

**After Foundation (Phase 2) completes**:
- **Track A**: US3 → US1 → US2 (critical path)
- **Track B**: US4 (can run in parallel with Track A until US2)

**After US2 completes**:
- US5, US6, US7 can all start in parallel

---

## Parallel Example: Foundation Phase

```bash
# These tasks can all run in parallel (different files):
T005: constants.py
T006: arca/exceptions.py
T009: database/sql/facturacion_rls.sql
T012: tests/facturacion/ structure
T013: urls.py
T015: serializers.py (PuntoDeVenta)
T016: views.py (PuntoDeVenta)
```

## Parallel Example: User Story 2 Tests + US4 Implementation

```bash
# These can run in parallel (different stories, different files):
Track A: T033 (test_models.py immutability) + T034 (test_api.py integration)
Track B: T031 (constants.py resolver) + T032 (validators.py)
```

---

## Implementation Strategy

### MVP First (US3 + US1 + US2)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (BLOCKS all stories)
3. Complete Phase 3: US3 — Credential Management
4. Complete Phase 4: US1 — WSAA Authentication
5. Complete Phase 5: US4 — Validation (can overlap with US1)
6. Complete Phase 6: US2 — CAE Invoice Issuance
7. **STOP and VALIDATE**: Issue a test invoice against ARCA homologation

At this point you have a working invoicing MVP: credential upload, WSAA auth, amount validation, CAE issuance with immutable ledger.

### Incremental Delivery

1. **MVP**: Setup + Foundation + US3 + US1 + US4 + US2 → Core invoicing works
2. **+QR**: US5 → Fiscal QR codes on authorized invoices
3. **+Corrections**: US6 → Credit/debit notes for invoice corrections
4. **+Offline**: US7 → CAEA pre-authorization for offline scenarios
5. **+Polish**: Metrics, schema docs, homologation integration tests

### Parallel Team Strategy (3 developers)

Phase 1-2: All together (foundational)

After foundation:
- **Dev A**: US3 → US1 → US2 (critical path)
- **Dev B**: US4 → US5 → US6 (validation + QR + NC/ND)
- **Dev C**: US7 → Polish (CAEA + metrics)

Note: Dev B must complete US4 before Dev A starts US2. Dev C's US7 depends on Dev A's US1.

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks in same phase
- [Story] label maps task to specific user story for traceability
- Each user story is independently testable after its checkpoint
- Constitution Section X: 80% min coverage, 95% for WSAA/CAE/validation/immutability
- All serializers use explicit `fields` list (never `__all__`) per Constitution Section IX
- All FKs use `ON DELETE RESTRICT` per Constitution Section I
- All amounts use `DecimalField(max_digits=17, decimal_places=3)` per Constitution Section I
- ARCA homologation integration tests marked `@pytest.mark.integration` (require network + credentials)
