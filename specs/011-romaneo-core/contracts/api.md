# API Contracts: Romaneo Core

**Feature**: 011-romaneo-core | **Date**: 2026-03-19
**Base Path**: `/api/v1/acopio/`

## Romaneo Endpoints

### POST /romaneos/
Create a new romaneo in PENDIENTE status.

**Request**: RomaneoSerializer fields (grain_type, campaign, branch, vehicle, CPE, producer)
**Response**: 201 Created -- full romaneo representation with auto-generated romaneo_number
**Auth**: JWT required, tenant from token

### GET /romaneos/
List romaneos (paginated, tenant-filtered).

**Query params**: `?ordering=-ts_entrada,romaneo_number`, `?page=N`, `?page_size=N`
**Response**: 200 OK -- `{ "count": N, "next": "...", "previous": "...", "results": [...] }`
**Pagination**: PageNumberPagination, default 25, max 100

### GET /romaneos/{id}/
Retrieve single romaneo with nested quality_analysis and merma_calculation when present.

**Response**: 200 OK -- RomaneoDetailSerializer (nested QA + MC)

### PATCH /romaneos/{id}/
Update editable fields. Guard: only PENDIENTE or EN_PROCESO.

**Response**: 200 OK / 409 Conflict (romaneo_immutable)

## State Transition Endpoints

All POST, nested under member. Return error type `invalid_state_transition` with `current_status` and `attempted_transition` on 409.

### POST /romaneos/{id}/confirmar-arribo/
PENDIENTE -> EN_PROCESO. No request body.

**Response**: 202 Accepted (async WSCPE enqueued)

### POST /romaneos/{id}/peso-bruto/
EN_PROCESO -> PESADO.

**Request**: `{ "peso_bruto_kg": "28450.000" }`
**Response**: 200 OK

### POST /romaneos/{id}/analizar/
PESADO -> ANALIZADO. Creates QualityAnalysis record.

**Request**: Inline 9 quality parameters
**Response**: 200 OK

### POST /romaneos/{id}/confirmar/
ANALIZADO -> CONFORME. Triggers merma calculation. Creates MermaCalculation. Sets peso_neto_conforme_kg. **IMMUTABILITY GATE**.

**Request**: `{ "grado_asignado": 1 }`
**Response**: 200 OK

### POST /romaneos/{id}/tara/
Capture tare weight while CONFORME. Computes peso_neto_bruto_kg.

**Request**: `{ "tara_kg": "12340.000" }`
**Response**: 200 OK

### POST /romaneos/{id}/cerrar/
CONFORME -> CERRADO. Requires tara_kg present.

**Response**: 202 Accepted (async WSCPE x2 enqueued)

## Preview Endpoint

### GET /romaneos/{id}/merma-preview/
Non-persisting merma projection. Available when romaneo is PESADO or ANALIZADO.

**Response**: 200 OK -- projected merma deductions (same format as MermaCalculation fields)
**Error**: 409 if no quality analysis exists

## Quality Analysis Nested Endpoints

### POST /romaneos/{romaneo_id}/quality-analysis/
Create QA record. Guard: romaneo in EN_PROCESO or PESADO.

**Request**: 9+ quality parameter fields
**Response**: 201 Created

### GET /romaneos/{romaneo_id}/quality-analysis/
Retrieve QA. Returns 404 if not yet created.

**Response**: 200 OK

### PATCH /romaneos/{romaneo_id}/quality-analysis/
Update QA parameters. Guard: romaneo in ANALIZADO only.

**Response**: 200 OK / 409 Conflict (if CONFORME/CERRADO)

## Error Responses

| Status | Type | When |
|--------|------|------|
| 409 | `invalid_state_transition` | Out-of-sequence state transition attempted |
| 409 | `romaneo_immutable` | PATCH on CONFORME/CERRADO romaneo |
| 404 | Not found | Cross-tenant access or nonexistent resource |
| 400 | Validation error | Invalid field values |

## Rust FFI Interface

### calculate_merma(input_json: str) -> str

**Input JSON**:
```json
{
  "peso_neto_bruto_kg": "30000.000",
  "humedad_pct": "15.2",
  "hf_secado_pct": "13.5",
  "materias_extranas_pct": "1.8",
  "zarandeo_deduction_pct": "1.00",
  "manipuleo_fijo_pct": "0.25",
  "volatil_fijo_pct": "0.30"
}
```

**Output JSON**:
```json
{
  "zarandeo_pct": "1.00",
  "secado_pct": "1.97",
  "manipuleo_pct": "0.25",
  "volatil_pct": "0.30",
  "peso_post_zarandeo_kg": "29700.000",
  "peso_post_secado_kg": "29116.301",
  "peso_post_manipuleo_kg": "29043.510",
  "peso_final_kg": "28956.379",
  "total_merma_kg": "1043.621",
  "total_factor_pct": "0.9652"
}
```

**Errors**: `GraviteaError::InvalidInput` for invalid JSON, negative weights, out-of-range percentages.
