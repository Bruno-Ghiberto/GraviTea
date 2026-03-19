# API Contract: Grain Reference Data

**Feature**: 010-grain-reference | **Date**: 2026-03-18
**Base URL**: `/api/v1/acopio/`
**Auth**: JWT Bearer token required on all endpoints

## Endpoints

### 1. Grain Types

**`GET /api/v1/acopio/grain-types/`** — List all grain types (GLOBAL, no tenant filtering)

Query parameters:
- `?is_active=true|false` — Filter by active status

Response (200):
```json
{
  "count": 7,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "uuid",
      "code": "TRI",
      "codigo": 15,
      "nombre": "Trigo pan",
      "humedad_base_pct": "14.00",
      "hf_secado_pct": "13.50",
      "manipuleo_fijo_pct": "0.10",
      "volatil_fijo_pct": "0.30",
      "grading_system": "GRADO",
      "is_active": true
    }
  ]
}
```

Field mappings: `codigo` = model `arca_codigo`, `nombre` = model `name`.

**`GET /api/v1/acopio/grain-types/{id}/`** — Retrieve single grain type

Response: Same object shape as list item (without pagination envelope).

---

### 2. Tolerance Tables

**`GET /api/v1/acopio/tolerance-tables/`** — List tolerance entries (GLOBAL)

Query parameters:
- `?grain_type={uuid}` — Filter by grain type
- `?valid_from_before={date}` — Filter by validity date

Response (200):
```json
{
  "count": 12,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "uuid",
      "grain_type": "uuid",
      "valid_from": "2020-01-01",
      "valid_to": null,
      "parameter": "humedad",
      "tolerance_pct": "14.00",
      "grado_base": 2,
      "source_resolution": "RES SAGPyA 1075/94"
    }
  ]
}
```

**`GET /api/v1/acopio/tolerance-tables/{id}/`** — Retrieve single entry

---

### 3. Merma Tables

**`GET /api/v1/acopio/merma-tables/`** — List merma bands (GLOBAL)

Query parameters:
- `?grain_type={uuid}` — Filter by grain type

Response (200):
```json
{
  "count": 4,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "uuid",
      "grain_type": "uuid",
      "valid_from": "2020-01-01",
      "valid_to": null,
      "materias_extranas_from_pct": "0.00",
      "materias_extranas_to_pct": "1.00",
      "zarandeo_deduction_pct": "0.00"
    }
  ]
}
```

**`GET /api/v1/acopio/merma-tables/{id}/`** — Retrieve single entry

---

### 4. Campaigns

**`GET /api/v1/acopio/campaigns/`** — List campaigns (TENANT-SCOPED)

Query parameters:
- `?is_active=true|false` — Filter by active status

Response (200): Same envelope format. Each tenant sees only its own campaigns.

```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "uuid",
      "campaign_code": "2025/26",
      "start_date": "2025-12-01",
      "end_date": "2026-11-30",
      "is_active": true,
      "notes": null
    }
  ]
}
```

**`POST /api/v1/acopio/campaigns/`** — Create campaign

Request body:
```json
{
  "campaign_code": "2025/26",
  "start_date": "2025-12-01",
  "end_date": "2026-11-30",
  "is_active": false,
  "notes": "Optional"
}
```

`tenant_id` is auto-set from JWT claims (not in request body).

**`GET/PUT/PATCH/DELETE /api/v1/acopio/campaigns/{id}/`** — Standard CRUD. Tenant-filtered.

## Error Responses

| Status | Meaning |
|--------|---------|
| 401 | Missing or invalid JWT token |
| 403 | Cross-tenant access attempt |
| 404 | Resource not found (or tenant-filtered out) |
| 400 | Validation error (invalid campaign code, date range, etc.) |
| 409 | Constraint violation (duplicate ARCA code, second active campaign) |

## Pagination

All list endpoints use page-number pagination:
- Envelope: `{ "count", "next", "previous", "results" }`
- Default page size: per DRF settings
- Justified deviation from constitution's cursor-based default (see plan.md)
