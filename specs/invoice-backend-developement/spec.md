# Feature Specification: Electronic Invoicing Backend (Facturacion)

**Feature Branch**: `invoice-backend-developement`
**Created**: 2026-02-10
**Status**: Draft
**Input**: User description: "Build the electronic invoicing backend module (facturacion) for GRAVITEA-ERP that integrates with Argentina's ARCA (ex-AFIP) system."
**Feature Number**: 008
**References**:
- `Docs/ARCA/Researches/arca-discovery-unified-report.md` — Unified technical report (8 domains, 20 PDFs, 2,304 Qdrant chunks)
- `skills/gravitea-invoice/SKILL.md` — Implementation patterns (1,139 lines)
- `.specify/memory/constitution.md` — Project constitution (14 principles)

---

## Clarifications

### Session 2026-02-10

- Q: What is explicitly out of scope for the facturacion MVP? → A: Exclude PDF/print rendering, export invoices (Type E: 19,20,21), FCE MiPyME (201-208), WSMTXCA integration, Celery beat scheduling (CAEA deadlines are manual-trigger only for now).
- Q: Can a tenant have multiple ARCACredentials (e.g., one for testing, one for production)? → A: One credential per (tenant, environment) pair. Unique constraint on (tenant_id, is_production). Maximum 2 credentials per tenant.
- Q: Which concurrency mechanism for CbteNro assignment? → A: select_for_update() on PuntoDeVenta row within @transaction.atomic. PostgreSQL row-level lock serializes concurrent requests.
- Q: How should the system behave when ARCA endpoints are unreachable? → A: Reject synchronously with a clear error. Comprobante stays in DRAFT. User manually retries when ready. No background queue.
- Q: Should the facturacion module emit ARCA-specific Prometheus metrics? → A: Yes — counters for WSAA auth (success/failure), CAE results (approved/rejected/observed), and histogram for SOAP call latency. Use existing apps/core/observability/ patterns.

---

## Out of Scope

The following are **explicitly excluded** from the facturacion MVP and deferred to future phases:

- **PDF/print rendering**: Invoice PDF generation and print layout are NOT part of this module. The API returns data only; presentation is handled by the frontend/client.
- **Export invoices (Type E: CbteTipo 19, 20, 21)**: Foreign trade invoices require additional research (confidence 0.75) and are deferred to Phase 4.
- **FCE MiPyME (CbteTipo 201-208)**: Electronic credit invoices require Opcionales Id=27 research and are deferred to Phase 4.
- **WSMTXCA integration**: The multi-tax-credit web service is not required for standard invoicing; WSFEv1 is sufficient for Phase 1-3.
- **Celery beat scheduling**: CAEA deadline monitoring (User Story 7) uses manual-trigger batch reporting only. Automated Celery beat scheduling is deferred.
- **ComprobanteItem (line items)**: Internal line-item tracking is deferred to Phase 4. ARCA WSFEv1 does not require individual line items — amounts are submitted as totals only. The entity definition in Key Entities is retained for forward reference.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — WSAA Authentication & Token Management (Priority: P1)

A tenant administrator uploads their ARCA certificate (PEM) and encrypted private key to GRAVITEA-ERP. When any invoicing operation is triggered, the system automatically authenticates with ARCA's WSAA service using the TRA/LoginCms flow. Tokens are cached in Redis with an 11-hour TTL (1-hour safety margin from the 12-hour validity). Subsequent invoicing calls within the same tenant reuse the cached token without re-authenticating.

**Why this priority**: Without WSAA authentication, no ARCA web service call can be made. This is the foundational layer that all other stories depend on.

**Independent Test**: Can be fully tested by uploading a test certificate, triggering a WSAA LoginCms call against `wsaahomo.afip.gov.ar`, and verifying a valid Token+Sign pair is returned and cached in Redis. Delivers value as the authentication foundation.

**Acceptance Scenarios**:

1. **Given** a tenant has uploaded a valid ARCA certificate and private key, **When** an invoice issuance is requested, **Then** the system generates a TRA XML with `uniqueId=int(time.time())`, signs it with CMS/PKCS#7, calls LoginCms, and receives a Token+Sign pair.
2. **Given** a valid Token+Sign exists in Redis cache with TTL > 1 hour, **When** a subsequent invoicing call is made for the same tenant, **Then** the cached Token+Sign is returned without calling WSAA.
3. **Given** a cached Token+Sign has TTL < 1 hour remaining, **When** an invoicing call is made, **Then** the system proactively refreshes by generating a new TRA and calling LoginCms.
4. **Given** a tenant has NOT uploaded ARCA credentials, **When** an invoice issuance is attempted, **Then** the system returns a clear error indicating missing ARCA credentials.
5. **Given** two tenants each have their own certificates, **When** both request invoicing simultaneously, **Then** each tenant receives independent Token+Sign pairs cached under `arca_auth:{tenant_cuit}:{service_id}`.

---

### User Story 2 — CAE Invoice Issuance via WSFEv1 (Priority: P1)

A tenant user creates an invoice in GRAVITEA-ERP with product/service line items. The system determines the correct CbteTipo based on the seller's and buyer's IVA conditions (CondicionIVA matrix), queries FECompUltimoAutorizado to get the next consecutive number, validates all amounts locally, submits to FECAESolicitar for CAE authorization, and stores the authorized comprobante as an immutable ledger entry.

**Why this priority**: CAE invoice issuance is the core value proposition — without it, the module cannot issue legally valid electronic invoices.

**Independent Test**: Can be fully tested by issuing a Factura B (CbteTipo=6) against the ARCA homologation environment. Delivers value as the primary invoicing workflow.

**Acceptance Scenarios**:

1. **Given** a Responsable Inscripto seller invoicing a Consumidor Final buyer for products, **When** the invoice is submitted, **Then** CbteTipo=6 (Factura B) is selected, CbteNro is `last_authorized + 1`, and FECAESolicitar returns Resultado=A with a 14-digit CAE.
2. **Given** ARCA returns Resultado=A (Approved), **When** the response is processed, **Then** the Comprobante record is saved with status=AUTORIZADO, the CAE and CAEFchVto are stored, and the record becomes immutable (no UPDATE/DELETE allowed).
3. **Given** ARCA returns Resultado=R (Rejected) with error codes, **When** the response is processed, **Then** the Comprobante is saved with status=RECHAZADO, errors are logged, and the user is informed to fix and retry with the **same CbteNro**.
4. **Given** ARCA returns Resultado=O (Observed), **When** the response is processed, **Then** the CAE is stored (it was granted), the Comprobante is saved as OBSERVADO (immutable), and observaciones are logged as warnings.
5. **Given** the FECAESolicitar call times out (network failure), **When** the timeout is detected, **Then** the system executes the recovery algorithm: queries FECompUltimoAutorizado to check if the CAE was granted, and either retrieves it via FECompConsultar or retries with the same CbteNro.
6. **Given** amount fields ImpTotal, ImpNeto, ImpIVA, ImpTrib, ImpOpEx, ImpTotConc, **When** local validation runs before submission, **Then** the master equation `ImpTotal = ImpNeto + ImpOpEx + ImpIVA + ImpTrib + ImpTotConc` passes with ARCA's dual-tolerance (≤0.01% relative error OR ≤0.01 absolute error).

---

### User Story 3 — Multi-Tenant Credential Management (Priority: P1)

A tenant administrator securely uploads and manages ARCA certificates and private keys through the API. Private keys are encrypted at rest using AES-256-GCM via the existing EncryptedTextField. Each tenant stores credentials for their represented CUIT (company), with support for the delegation model (software house certificate representing a company).

**Why this priority**: Credential management is a prerequisite for WSAA authentication and must enforce multi-tenant isolation per the constitution's defense-in-depth strategy.

**Independent Test**: Can be fully tested by creating an ARCACredential via the API, verifying the private key is encrypted in the database, and confirming cross-tenant credential access is blocked by RLS.

**Acceptance Scenarios**:

1. **Given** a tenant admin, **When** they POST a certificate PEM and private key, **Then** an ARCACredential is created with the private key stored as AES-256-GCM encrypted text and the CUIT stored as 11 digits without hyphens.
2. **Given** a tenant has an ARCACredential, **When** a different tenant tries to access it, **Then** PostgreSQL RLS policies block the query and return no results.
3. **Given** a credential with `is_production=True`, **When** the system makes WSAA calls, **Then** it uses the production endpoints (`wsaa.afip.gov.ar`, `servicios1.afip.gov.ar`). When `is_production=False`, it uses homologation endpoints.
4. **Given** a certificate approaching expiration (within 30 days), **When** Django system checks run, **Then** a Warning is raised with `id='arca.W001'` indicating the tenant and expiration date.

---

### User Story 4 — CbteTipo Resolution & Amount Validation (Priority: P2)

The system automatically resolves the correct comprobante type (CbteTipo) based on the emisor and receptor CondicionIVA conditions and the operation type (factura, nota de debito, nota de credito). Amount validation enforces type-specific rules: Type A/B require IVA breakdown (AlicIva), Type C must omit IVA, service dates are conditional on Concepto, and Tributos must be omitted when ImpTrib=0.

**Why this priority**: Correct CbteTipo resolution and amount validation prevent ARCA rejections. This is critical for production reliability but can be validated independently of the ARCA connection.

**Independent Test**: Can be fully tested with unit tests covering all CondicionIVA combinations and amount validation edge cases, without any ARCA API calls.

**Acceptance Scenarios**:

1. **Given** emisor=Responsable Inscripto (1) and receptor=Responsable Inscripto (1), **When** resolving for a factura, **Then** CbteTipo=1 (Factura A) is returned; for nota de credito, CbteTipo=3 is returned.
2. **Given** emisor=Responsable Inscripto (1) and receptor=Consumidor Final (5), **When** resolving for a factura, **Then** CbteTipo=6 (Factura B) is returned.
3. **Given** emisor=Monotributo (6), **When** resolving for any operation, **Then** Type C is returned (11, 12, or 13).
4. **Given** a Type A invoice, **When** the AlicIva array is empty or missing, **Then** validation raises an error (IVA breakdown mandatory for CbteTipo 1,2,3,6,7,8,51,52,53).
5. **Given** a Type C invoice, **When** the AlicIva array is provided, **Then** validation raises an error (IVA must be completely omitted for CbteTipo 11,12,13).
6. **Given** Concepto=1 (Productos) with FchServDesde present, **When** validation runs, **Then** an error is raised (service dates must be OMITTED for products).
7. **Given** Concepto=2 (Servicios) without FchServDesde/Hasta/VtoPago, **When** validation runs, **Then** an error is raised (service dates MANDATORY for services, error 10049).
8. **Given** ImpTrib=0, **When** building the SOAP XML, **Then** the `<Tributos>` element is completely absent from the request (not empty, not null — omitted).

---

### User Story 5 — Fiscal QR Code Generation (Priority: P2)

After a comprobante is authorized (has CAE), the system generates an ARCA-compliant fiscal QR code per RG 4291. The QR encodes a JSON payload with the invoice's fiscal data, base64url-encoded, appended to the ARCA verification URL.

**Why this priority**: Fiscal QR codes are legally required on printed invoices. This is a display/output feature that depends on having authorized comprobantes.

**Independent Test**: Can be tested by generating a QR code for a mock authorized comprobante and verifying the encoded JSON payload matches the RG 4291 specification.

**Acceptance Scenarios**:

1. **Given** an authorized Comprobante with CAE, **When** the fiscal QR is requested, **Then** a JSON payload is generated containing: ver (1), fecha, cuit, ptoVta, tipoCmp, nroCmp, importe, moneda, ctz, tipoDocRec, nroDocRec, tipoCodAut (E for CAE), codAut (14-digit CAE).
2. **Given** the JSON payload, **When** the QR URL is constructed, **Then** the payload is base64url-encoded (no padding) and appended to `https://www.afip.gob.ar/fe/qr/?p=`.
3. **Given** a Comprobante with status=DRAFT or RECHAZADO (no CAE), **When** the fiscal QR is requested, **Then** an error is returned indicating the comprobante must be authorized first.

---

### User Story 6 — Credit and Debit Notes (Priority: P2)

A tenant user can issue Nota de Credito (NC) and Nota de Debito (ND) referencing an original Factura via CbtesAsoc. The system validates that the associated comprobante exists, the types are compatible (A→A, B→B, C→C), and submits to ARCA for CAE authorization.

**Why this priority**: NC/ND are essential for correcting invoices (the ONLY way to correct an authorized comprobante, since they are immutable). Required for complete invoicing workflows.

**Independent Test**: Can be tested by issuing a Factura, then issuing a NC referencing it, and verifying the CbtesAsoc is correctly included in the ARCA request.

**Acceptance Scenarios**:

1. **Given** an authorized Factura A (CbteTipo=1), **When** a Nota de Credito A is created referencing it, **Then** CbteTipo=3 is used with CbtesAsoc containing the original factura's (Tipo, PtoVta, Nro).
2. **Given** a Nota de Credito that references a non-existent comprobante, **When** submitted to ARCA, **Then** error 200 is returned and the NC is rejected.
3. **Given** a Nota de Credito where the type doesn't match the factura (e.g., NC-B referencing Factura-A), **When** submitted, **Then** error 202 is returned (incompatible types).
4. **Given** a Nota de Credito whose amount exceeds the original Factura, **When** submitted, **Then** ARCA may return Resultado=O with observacion 194 (warning, but CAE is still granted).

---

### User Story 7 — CAEA Offline Authorization (Priority: P3)

A tenant pre-requests a CAEA code for a biweekly quincena period. During that period, invoices can be issued offline using the CAEA code instead of real-time CAE. After the quincena ends, all CAEA-issued invoices are batch-reported to ARCA via FECAEARegInformativo within the 5-day deadline.

**Why this priority**: CAEA supports offline-first scenarios aligned with the constitution's Section VII. This is a significant feature but builds on top of the online CAE infrastructure.

**Independent Test**: Can be tested by requesting a CAEA from homologation, issuing mock offline invoices with it, then batch-reporting them.

**Acceptance Scenarios**:

1. **Given** a tenant requests a CAEA for Periodo=202603, Orden=1 (first quincena of March), **When** FECAEASolicitar succeeds, **Then** a CAEA record is stored with FchVigDesde, FchVigHasta, FchTopeInf, and status=ACTIVE.
2. **Given** an active CAEA for the current period, **When** an offline invoice is created, **Then** it is stored with the CAEA code and status=DRAFT (pending batch report).
3. **Given** the quincena has ended and CAEA invoices exist, **When** batch reporting runs (manual or scheduled), **Then** FECAEARegInformativo is called with all pending invoices and accepted ones are marked AUTORIZADO.
4. **Given** a quincena has ended with no invoices issued, **When** the reporting deadline approaches, **Then** FECAEASinMovimientoInformar is called to report no movement.
5. **Given** a CAEA reporting deadline is 2 days away, **When** the tenant admin checks the CAEA status via the API, **Then** the response includes the number of pending invoices, days remaining until the reporting deadline, and a warning flag indicating urgency.

---

### Edge Cases

- What happens when two concurrent requests try to issue invoices for the same (PtoVta, CbteTipo) — race condition on CbteNro? → Use `select_for_update()` on the PuntoDeVenta row within `@transaction.atomic` to serialize concurrent requests via PostgreSQL row-level locking.
- How does the system handle WSAA returning an error for an already-expired certificate? → Return clear error with renewal instructions.
- What if the Redis cache is unavailable (connection refused)? → Fall back to WSAA authentication on every call (degraded performance, not failure).
- What happens when ARCA homologation endpoints are down for maintenance? → Reject synchronously with a clear error (ARCA unreachable, HTTP status/error code). Comprobante stays in DRAFT status. User manually retries when ready. No background queue infrastructure required.
- What if a tenant uploads a production certificate but the system is configured for testing? → Validate the certificate CN against the environment endpoint before saving.
- What happens when `FECompUltimoAutorizado` returns 0 (no previous invoices)? → First invoice for the (PtoVta, CbteTipo) is number 1.
- What if ARCA accepts the CAE but the database commit fails? → The CAE is "burned" — use FECompConsultar to retrieve it on next attempt.
- What happens when a Comprobante is in VALIDANDO state and the server restarts? → On startup, check for VALIDANDO comprobantes and run recovery algorithm (FECompUltimoAutorizado + FECompConsultar).

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST authenticate with ARCA WSAA using TRA XML generation with timestamp-based `uniqueId` (`int(time.time())`), CMS/PKCS#7 signing, and LoginCms SOAP call.
- **FR-002**: System MUST cache Token+Sign pairs in Redis with key `arca_auth:{tenant_cuit}:{service_id}` and TTL=11 hours (1-hour safety margin from 12-hour validity).
- **FR-003**: System MUST proactively refresh tokens when remaining TTL < 1 hour.
- **FR-004**: System MUST issue electronic invoices via WSFEv1 FECAESolicitar, supporting batch submission with correct FeCabReq and FeDetReq structures.
- **FR-005**: System MUST query FECompUltimoAutorizado before each invoice to determine the next consecutive CbteNro, enforcing strict monotonic numbering with no gaps.
- **FR-006**: System MUST resolve CbteTipo based on the emisor/receptor CondicionIVA matrix: RI→RI = A(1,2,3), RI→CF/Mono/Exento = B(6,7,8), Mono/Exento→Any = C(11,12,13).
- **FR-007**: System MUST validate amount fields using the master equation `ImpTotal = ImpNeto + ImpOpEx + ImpIVA + ImpTrib + ImpTotConc` with ARCA's dual-tolerance (≤0.01% relative error OR ≤0.01 absolute error).
- **FR-008**: System MUST validate IVA breakdown (AlicIva) sums match ImpIVA and ImpNeto, enforcing IVA is mandatory for types A/B/M and prohibited for type C.
- **FR-009**: System MUST enforce conditional service date fields: OMIT FchServDesde/Hasta/VtoPago when Concepto=1, REQUIRE them when Concepto=2 or 3.
- **FR-010**: System MUST omit `<Tributos>` XML element entirely when ImpTrib=0.
- **FR-011**: System MUST handle all three ARCA response results: A (store CAE, immutable), O (store CAE, log warnings, immutable), R (store errors, allow retry with same CbteNro).
- **FR-012**: System MUST implement network failure recovery using FECompUltimoAutorizado to determine if CAE was granted, followed by FECompConsultar to retrieve it.
- **FR-013**: System MUST enforce comprobante immutability: authorized (AUTORIZADO/OBSERVADO) records cannot be modified or deleted. Corrections require Nota de Credito.
- **FR-014**: System MUST store all comprobantes in an append-only ledger following TenantBoundModel with PostgreSQL RLS enforcement.
- **FR-015**: System MUST generate fiscal QR codes per RG 4291: JSON payload with fiscal data, base64url-encoded, appended to `https://www.afip.gob.ar/fe/qr/?p=`.
- **FR-016**: System MUST encrypt private keys at rest using AES-256-GCM via existing EncryptedTextField.
- **FR-017**: System MUST support both homologacion (testing) and produccion (live) ARCA environments with independent endpoint configuration per credential.
- **FR-018**: System MUST validate CbtesAsoc for Nota de Credito/Debito: associated comprobante must exist, types must be compatible (A→A, B→B, C→C).
- **FR-019**: System MUST support CAEA pre-authorization (FECAEASolicitar) for biweekly quincena periods.
- **FR-020**: System MUST support batch reporting of CAEA-issued invoices (FECAEARegInformativo) and no-movement reporting (FECAEASinMovimientoInformar) within the 5-day deadline.
- **FR-021**: System MUST support the delegation model (CUIT Representado) where a software house certificate represents a company CUIT in WSFEv1 calls.
- **FR-022**: System MUST store financial amounts using `DECIMAL(17,3)` in the database per constitution Section I, with display precision of 2 decimal places.
- **FR-023**: System MUST expose REST API endpoints for invoice issuance, comprobante retrieval, and credential management with cursor-based pagination per constitution Section XIII.
- **FR-024**: System MUST emit Prometheus metrics for ARCA interactions using existing `apps/core/observability/` patterns: counters for WSAA auth (success/failure by tenant), CAE results (approved/rejected/observed by cbte_tipo), and a histogram for SOAP call latency (wsaa_login, fecae_solicitar, fecomp_ultimo_autorizado).

### Key Entities

- **ARCACredential**: Stores per-tenant ARCA certificate (PEM), encrypted private key (AES-256-GCM), holder CUIT (11 digits), represented CUIT (delegation), environment flag (`is_production` boolean), last TRA uniqueId for replay protection. One per (tenant, environment) pair with unique constraint on `(tenant_id, is_production)`. Maximum 2 credentials per tenant (one testing, one production).
- **PuntoDeVenta**: Represents a registered point of sale. Attributes: number (1-99999, range enforced by CheckConstraint), type (electronic/manual), authorization date, active flag. Many-to-one with Tenant.
- **Comprobante**: The immutable invoice ledger entry. Attributes: cbte_tipo (CbteTipo enum), cbte_nro (consecutive), concepto (1/2/3), amounts (imp_total, imp_neto, imp_iva, imp_trib, imp_op_ex, imp_tot_conc), buyer info (doc_tipo, doc_nro), dates (cbte_fch, fch_serv_desde/hasta, fch_vto_pago), currency (mon_id, mon_cotiz), CAE (14-digit string), cae_fch_vto, status (DRAFT/VALIDANDO/AUTORIZADO/OBSERVADO/RECHAZADO), arca_response (JSONB for raw response), arca_errors (JSONB for error details). Many-to-one with Tenant and PuntoDeVenta.
- **ComprobanteItem**: Optional line items for internal tracking (not sent to ARCA directly). Attributes: description, quantity, unit_price, iva_rate, subtotal. Many-to-one with Comprobante.
- **AlicIva**: IVA rate breakdown entry for a comprobante. Attributes: id (3=0%, 4=10.5%, 5=21%, 6=27%, 8=5%, 9=2.5%), base_imp, importe. Many-to-one with Comprobante.
- **Tributo**: Other tax entry for a comprobante. Attributes: id (tax type code), desc, base_imp, alic, importe. Many-to-one with Comprobante.
- **CbteAsoc**: Associated comprobante reference for NC/ND. Attributes: tipo, pto_vta, nro, cuit (optional). Many-to-one with Comprobante.
- **CAEA**: Pre-authorized offline code. Attributes: caea_code (14 digits), periodo (YYYYMM), orden (1 or 2), fch_vig_desde, fch_vig_hasta, fch_tope_inf, status (ACTIVE/REPORTED/REPORTED_NO_MOVEMENT/EXPIRED). Many-to-one with Tenant.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: System can complete the full WSAA authentication flow (TRA → CMS → LoginCms → Token+Sign) against ARCA homologation in under 5 seconds, with cached calls returning in under 50ms.
- **SC-002**: System can issue a CAE-authorized Factura B against ARCA homologation with correct CbteNro, passing all amount validations, in under 10 seconds end-to-end.
- **SC-003**: 100% of authorized comprobantes (AUTORIZADO/OBSERVADO) are immutable — any attempt to UPDATE or DELETE raises an error at the application layer AND is blocked by database constraints.
- **SC-004**: Network failure recovery successfully determines CAE status in 100% of timeout scenarios (no "lost" invoices or duplicate numbers).
- **SC-005**: Amount validation catches 100% of equation mismatches before submission to ARCA, reducing ARCA error 10048 rejections to zero.
- **SC-006**: Private keys stored in the database are unreadable without the AES-256-GCM encryption key — database dumps reveal only ciphertext.
- **SC-007**: Cross-tenant credential access is blocked at both application layer (TenantBoundManager) and database layer (PostgreSQL RLS) — zero cross-tenant data leaks.
- **SC-008**: All API endpoints for invoice issuance and comprobante retrieval use cursor-based pagination with ≤100ms response time for lists of up to 1000 records.
- **SC-009**: Test coverage for the facturacion module reaches 80% minimum, with 95% coverage for critical paths (WSAA auth, CAE issuance, amount validation, immutability enforcement).
- **SC-010**: CbteTipo resolution correctly handles all documented CondicionIVA combinations (RI→RI, RI→CF, RI→Mono, RI→Exento, Mono→Any, Exento→Any) verified by unit tests.
