# Phase 0 Research: Technology Decisions

**Feature**: Electronic Invoicing Backend (Facturacion)
**Date**: 2026-02-10
**Status**: Complete — All decisions resolved

---

## R1: SOAP Client Library

**Decision**: `zeep` (v4.x)

**Rationale**:
- De-facto Python SOAP client; handles WSDL parsing, type generation, and SOAP envelope construction
- WSFEv1 uses SOAP 1.1 over HTTPS — zeep handles this natively
- Supports both sync and async transports (we use sync per spec constraints)
- Alternatives considered:
  - `suds-community`: Abandoned, Python 2 era
  - `requests` + manual XML: Too much boilerplate for WSDL-based services
  - `pysimplesoap`: Lightweight but no WSDL auto-parsing

**Configuration**:
```python
from zeep import Client
from zeep.transports import Transport
from requests import Session

session = Session()
session.timeout = 30  # ARCA can be slow
transport = Transport(session=session)
client = Client(wsdl_url, transport=transport)
```

**Risk**: zeep WSDL caching may cause issues if ARCA updates their WSDL without URL change. Mitigation: disable WSDL caching in production or use versioned WSDL snapshots.

---

## R2: XML Generation for TRA

**Decision**: `lxml` (already in project dependencies via other packages)

**Rationale**:
- TRA (LoginTicketRequest) is a simple XML document (~10 elements)
- lxml's `etree.Element` / `etree.SubElement` API is clean for programmatic XML construction
- Used by zeep internally, so no additional dependency
- Alternatives considered:
  - `xml.etree.ElementTree` (stdlib): Works but lxml is faster and more feature-complete
  - Template strings: Fragile, XSS risk, no validation

**Usage**: TRA XML generation only (wsaa.py). All WSFEv1 XML is handled by zeep.

---

## R3: CMS/PKCS#7 Signing

**Decision**: `cryptography` library (already in project — used by EncryptedTextField)

**Rationale**:
- `cryptography.hazmat.primitives.serialization.pkcs7.PKCS7SignatureBuilder` provides CMS signing
- Already a project dependency for AES-256-GCM encryption
- Supports loading PEM-encoded private keys and X.509 certificates
- Alternatives considered:
  - `pyOpenSSL`: Deprecated API, `cryptography` is the recommended replacement
  - `M2Crypto`: Complex build requirements, less maintained
  - External `openssl` CLI: Not suitable for runtime signing

**PKCS#7 Options**: Use `pkcs7.PKCS7Options.Binary` for DER-encoded output compatible with ARCA's LoginCms.

---

## R4: Redis Token Caching

**Decision**: Django cache framework with Redis backend (already configured)

**Rationale**:
- Token+Sign caching uses `django.core.cache` API
- Redis backend already configured in project settings
- Cache key pattern: `arca_auth:{tenant_cuit}:{service_id}`
- TTL: 11 hours (1-hour safety margin from 12-hour WSAA token validity)
- Fallback: If Redis is unavailable, degrade to per-request WSAA auth (no failure)

**No new dependencies required.**

---

## R5: Financial Amount Precision

**Decision**: `DecimalField(max_digits=17, decimal_places=3)` storage, `Decimal("0.01")` quantization for ARCA submission

**Rationale**:
- Constitution Section I mandates DECIMAL(17,3) storage
- ARCA expects 2-decimal-place amounts in SOAP requests
- Storage at 3 decimal places allows intermediate calculations without precision loss
- Display and ARCA submission use `.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)`
- Python `Decimal` type used throughout (never `float`)

---

## R6: Prometheus Metrics

**Decision**: Use existing `apps/core/observability/metrics.py` patterns with `REGISTRY`

**Rationale**:
- Project already uses `prometheus-client` with a custom `CollectorRegistry`
- ARCA-specific metrics follow the same pattern: Counter, Histogram, explicit labels
- New metrics defined in `apps/facturacion/metrics.py`:
  - `arca_wsaa_auth_total` (Counter): labels=[tenant_id, result]
  - `arca_cae_result_total` (Counter): labels=[tenant_id, cbte_tipo, resultado]
  - `arca_soap_duration_seconds` (Histogram): labels=[method, tenant_id]

**No new dependencies required.**

---

## R7: Database Schema

**Decision**: Standard Django migrations with `RunSQL` for RLS policies

**Rationale**:
- All facturacion models inherit `TenantBoundModel` (automatic tenant_id field + IDOR validation)
- PostgreSQL RLS policies applied via `RunSQL` in `0001_initial.py` migration
- RLS SQL also stored in `database/sql/facturacion_rls.sql` for documentation
- Immutability enforced at application layer (`save()`/`delete()` overrides) — no database triggers needed
- `select_for_update()` for CbteNro concurrency (PostgreSQL row-level locking on PuntoDeVenta)

---

## R8: OpenAPI Documentation

**Decision**: `drf-spectacular` (already in project)

**Rationale**:
- All existing viewsets use `@extend_schema` annotations
- Facturacion endpoints follow the same pattern
- Generates OpenAPI 3.0 spec for Swagger/ReDoc
- Custom schema extensions in `schema.py` for ARCA-specific types

**No new dependencies required.**

---

## Dependencies Summary

| Package | Version | New? | Purpose |
|---------|---------|------|---------|
| zeep | >=4.0 | YES | SOAP client for WSAA/WSFEv1 |
| lxml | >=4.9 | NO (transitive) | TRA XML generation |
| cryptography | >=41.0 | NO (existing) | CMS/PKCS#7 signing, AES-256-GCM |
| django-redis | >=5.0 | NO (existing) | Token+Sign caching |
| prometheus-client | >=0.17 | NO (existing) | ARCA metrics |
| drf-spectacular | >=0.27 | NO (existing) | OpenAPI docs |

**Only `zeep` is a new dependency.** All other packages are already in the project.

---

## Open Questions

None — all technology decisions resolved. Proceed to Phase 1.
