# API Contract: ARCA WSCDC & WS Padrón Endpoints

**Branch**: `009-new-arca-docs` | **Date**: 2026-03-18
**Target document**: `Docs/Project Blueprint/REST API Design.md`
**Scope**: 2 new endpoints (FR-013, SC-011). No existing endpoints are modified.

---

## Endpoint 1: WSCDC Deposit Certificate Proxy

### POST /api/v1/arca/wscdc/deposit-certificate

**Purpose**: Inform ARCA of grain received at the acopiador establishment via WSCDC.
Proxies the ARCA WSCDC SOAP call, stores the response, and returns the certificate number.

**Trigger**: Called internally by the romaneo reception workflow after romaneo record is saved
and WSCPE `confirmarDescargaCPE` succeeds.

**Authorization**: JWT Bearer token — tenant-scoped.
Required permission: `acopio.wscdc.write`

**Content-Type**: `application/json`

---

#### Request Body

```json
{
  "romaneo_id": "uuid",
  "grain_species": "string",
  "kg_received": "decimal(17,3)",
  "humidity_percent": "decimal",
  "establishment_id": "string"
}
```

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `romaneo_id` | UUID | Yes | Must exist in tenant's Romaneo records | Reception record that triggered this certificate |
| `grain_species` | string | Yes | ARCA grain species catalog code | Grain species (e.g., "TRIGO", "SOJA") |
| `kg_received` | DECIMAL(17,3) | Yes | > 0 | Gross kg received at establishment |
| `humidity_percent` | decimal | Yes | 0.00–100.00 | Humidity percentage at reception |
| `establishment_id` | string | Yes | ARCA-registered establishment | ARCA establishment identifier |

---

#### Response: 201 Created

```json
{
  "certificado_id": "uuid",
  "nro_certificado": "string",
  "estado": "Emitido",
  "romaneo_id": "uuid",
  "created_at": "ISO8601"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `certificado_id` | UUID | Internal `CertificadoDepositoCereal` record ID |
| `nro_certificado` | string | WSCDC deposit certificate number from ARCA |
| `estado` | string | `"Emitido"` (ARCA accepted) or `"Pendiente"` (ARCA call failed, queued for retry) |
| `romaneo_id` | UUID | Echo of request `romaneo_id` |
| `created_at` | datetime | ISO 8601 timestamp |

---

#### Response: 202 Accepted (ARCA Unavailable — Queued)

Returned when ARCA is unreachable. Certificate is queued for retry.

```json
{
  "certificado_id": "uuid",
  "estado": "Pendiente",
  "message": "WSCDC call queued for retry — ARCA service unavailable",
  "romaneo_id": "uuid"
}
```

---

#### Error Responses

| Status | Code | Description |
|--------|------|-------------|
| 400 | `VALIDATION_ERROR` | Missing or invalid field in request body |
| 404 | `ROMANEO_NOT_FOUND` | `romaneo_id` not found in tenant's records |
| 409 | `CERTIFICATE_EXISTS` | A certificate already exists for this `romaneo_id` |
| 422 | `ARCA_REJECTION` | ARCA WSCDC returned an error code — body includes `wscdc_error_code` and `wscdc_message` |
| 503 | `ARCA_UNAVAILABLE` | ARCA is unreachable — certificate is queued for retry (same as 202) |

---

## Endpoint 2: SISA Producer Status Lookup

### GET /api/v1/arca/padron/sisa-status/{cuit}

**Purpose**: Retrieve a producer's SISA registration status and retention tier from ARCA WS Padrón A4.
Used at romaneo reception time to determine applicable IVA and Ganancias retention percentages
before WSLPG liquidation.

**Authorization**: JWT Bearer token — tenant-scoped.
Required permission: `acopio.padron.read`

**Caching**: Results cached in Redis for 24 hours per CUIT per tenant (reduces ARCA API calls).

---

#### Path Parameters

| Parameter | Type | Required | Validation | Description |
|-----------|------|----------|------------|-------------|
| `cuit` | string | Yes | 11 digits, no hyphens | Producer CUIT to look up |

---

#### Response: 200 OK

```json
{
  "cuit": "string",
  "sisa_category": "string",
  "iva_retention_percent": "decimal",
  "ganancias_retention_percent": "decimal",
  "inscripto": true,
  "cache_expires_at": "ISO8601",
  "source": "arca_live | cache"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `cuit` | string | Queried CUIT (echo) |
| `sisa_category` | string | SISA registration category code (from WS Padrón A4 `getPersona` response) |
| `iva_retention_percent` | decimal | IVA retention % applicable at WSLPG liquidation for this producer |
| `ganancias_retention_percent` | decimal | Ganancias retention % applicable at liquidation |
| `inscripto` | boolean | Whether producer has active SISA inscription |
| `cache_expires_at` | datetime | ISO 8601 timestamp when cached result expires |
| `source` | string | `"arca_live"` if fetched from ARCA this request; `"cache"` if served from Redis |

> **Note**: `iva_retention_percent` and `ganancias_retention_percent` are derived from the SISA tier table
> (documented in ARCA Guide §6.5, ADR-027, and SRS). The exact tier → percentage mapping is authoritative
> from RAG Task 3 findings.

---

#### Error Responses

| Status | Code | Description |
|--------|------|-------------|
| 400 | `INVALID_CUIT` | CUIT is not 11 digits or fails CUIT checksum |
| 404 | `CUIT_NOT_FOUND` | CUIT not found in ARCA WS Padrón — producer not registered |
| 503 | `ARCA_UNAVAILABLE` | WS Padrón is unreachable — no cached result available |

---

## Integration Notes

### Error Handling Philosophy

Both endpoints follow the constitution's fiscal compliance principle (§VI): ARCA integration errors must not block core business operations. Specifically:

- WSCDC POST endpoint: `romaneo_id` is saved before this endpoint is called. A WSCDC failure does NOT roll back the romaneo record — the certificate transitions to `Pendiente` for async retry.
- SISA GET endpoint: If ARCA is unavailable AND no cached result exists, the caller may use the most conservative retention tier (highest %) as a fallback. This is a caller decision, not enforced by this endpoint.

### Caching Strategy (SISA endpoint)

```text
Redis key: sisa:{tenant_id}:{cuit}
TTL: 24 hours
Eviction: TTL-based (no manual invalidation)
Rationale: SISA category changes are infrequent; 24h TTL balances freshness vs ARCA API load
```

### Tenant Isolation

Both endpoints are tenant-scoped:
- WSCDC endpoint: writes `CertificadoDepositoCereal` with `tenant_id` from JWT claims
- SISA endpoint: Redis cache key is namespaced by `tenant_id`
- No cross-tenant ARCA credentials: each tenant's WSAA token is used for the ARCA call

### OpenAPI Schema Tags

- WSCDC endpoint: tag `arca-grain`
- SISA endpoint: tag `arca-padron`

Both follow the existing API response envelope and error format established in `Docs/Project Blueprint/REST API Design.md`.
