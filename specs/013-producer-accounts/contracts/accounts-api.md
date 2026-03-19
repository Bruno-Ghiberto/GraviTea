# API Contracts: Producer Accounts (Spec-13)

**Base URL**: `/api/v1/cuentas/`
**Authentication**: JWT Bearer token required on all endpoints
**Content-Type**: `application/json`
**Generated**: 2026-03-19

---

## ProducerAccount Endpoints

### `GET /accounts/`

List producer accounts for the authenticated tenant.

**Query parameters**:

| Param | Type | Description |
|-------|------|-------------|
| `producer_cuit` | string | CUIT filter (equality via blind index, e.g. `"20-12345678-9"`) |
| `grain_type` | UUID | Filter by grain type ID |
| `campaign` | UUID | Filter by campaign ID |
| `branch` | UUID | Filter by branch ID |
| `is_active` | boolean | Filter by active status (default: true) |
| `cursor` | string | Opaque cursor from previous response (CursorPagination) |

**Pagination**: CursorPagination, ordered by `-created_at`, page_size=25. No `count` field.

**Response 200**:
```json
{
  "next": "http://localhost/api/v1/cuentas/accounts/?cursor=cD0yMDI2...",
  "previous": null,
  "results": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "producer_cuit": "20-12345678-9",
      "branch": "b1b2b3b4-0000-0000-0000-000000000001",
      "branch_name": "Planta Norte",
      "grain_type": "a1a2a3a4-0000-0000-0000-000000000001",
      "grain_type_code": "TRI",
      "grain_type_name": "Trigo",
      "campaign": "c1c2c3c4-0000-0000-0000-000000000001",
      "campaign_label": "2025/26",
      "grain_balance_kg": "10000.000",
      "ars_balance": "0.000",
      "usd_balance": "0.000",
      "is_active": true,
      "created_at": "2026-03-15T10:00:00Z",
      "updated_at": "2026-03-15T10:00:00Z"
    }
  ]
}
```

**Notes**:
- `producer_cuit` is returned decrypted (EncryptedCharField transparent decryption).
- `producer_cuit_encrypted` and `producer_cuit_hash` are never exposed in responses.
- Filtering by `producer_cuit` computes the blind index server-side.

---

### `GET /accounts/{id}/`

Retrieve a single producer account.

**Response 200**: ProducerAccount object (same shape as list item).

**Errors**:
| Code | Condition |
|------|-----------|
| `404` | Account not found or belongs to different tenant |

---

### `GET /accounts/{id}/movements/`

Cursor-paginated movement ledger for an account.

**Query parameters**:

| Param | Type | Description |
|-------|------|-------------|
| `cursor` | string | Opaque cursor from previous response |
| `movement_type` | string | Filter by movement type (e.g. `CEG_DEPOSIT`) |
| `date_from` | ISO8601 | Filter movements on or after this datetime |
| `date_to` | ISO8601 | Filter movements before this datetime |

**Response 200**:
```json
{
  "next": "http://localhost/api/v1/cuentas/accounts/{id}/movements/?cursor=cD0yMDI2...",
  "previous": null,
  "results": [
    {
      "id": "mv01-0000-0000-0000-000000000001",
      "movement_type": "CEG_DEPOSIT",
      "movement_type_display": "Grain Deposit (CEG)",
      "quantity_kg": "10000.000",
      "ars_amount": "0.000",
      "usd_amount": "0.000",
      "romaneo": "rm01-0000-0000-0000-000000000001",
      "romaneo_numero": "0001-00012345",
      "reference_document": "",
      "notes": "",
      "movement_at": "2026-03-15T10:00:00Z",
      "created_by_name": "Juan Operador"
    }
  ]
}
```

**Pagination**: CursorPagination, ordered by `-movement_at`, page_size=50.

---

### `POST /accounts/{id}/movements/`

Create a manual movement entry.

**Allowed types**: `SERVICE_CHARGE`, `RETIRO`, `RETENTION_DEDUCTION`, `ADJUSTMENT`
**Forbidden types** (system-generated): `CEG_DEPOSIT`, `LPG_SALE`, `FIJACION`, `CANJE_GRAIN_DEBIT`, `CANJE_INPUT_CREDIT` → `400 invalid_movement_type`

**Request body**:
```json
{
  "movement_type": "SERVICE_CHARGE",
  "quantity_kg": "0.000",
  "ars_amount": "-5000.000",
  "usd_amount": "0.000",
  "reference_document": "FAC-2026-00123",
  "notes": "Storage fee Q1 2026"
}
```

**Response 201**: AccountMovement object (same shape as ledger item).

**Errors**:
| Code | Condition |
|------|-----------|
| `400` | Invalid movement_type, sign violation (debit must be negative), missing reference_document |
| `403` | ADJUSTMENT without supervisor permission (`settings.admin` required) |
| `404` | Account not found or different tenant |
| `405` | PATCH or DELETE on existing movement (append-only violation) |

**Sign conventions**:
- `SERVICE_CHARGE`: `ars_amount` must be ≤ 0
- `RETIRO`: `ars_amount` or `usd_amount` must be ≤ 0
- `RETENTION_DEDUCTION`: `ars_amount` must be ≤ 0
- `ADJUSTMENT`: can be positive or negative (supervisor discretion)

---

### `PATCH /accounts/{id}/movements/{movement_id}/`

**Response 405**:
```json
{
  "detail": "Method not allowed.",
  "code": "append_only_violation"
}
```

### `DELETE /accounts/{id}/movements/{movement_id}/`

**Response 405**:
```json
{
  "detail": "Method not allowed.",
  "code": "append_only_violation"
}
```

---

## Statement Endpoint

### `GET /accounts/{id}/statement/`

Generate an account statement for a date range.

**Query parameters**:

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `date_from` | ISO8601 date | Yes | Statement period start (inclusive) |
| `date_to` | ISO8601 date | Yes | Statement period end (inclusive) |

**Response 200**:
```json
{
  "account_id": "550e8400-e29b-41d4-a716-446655440000",
  "producer_cuit": "20-12345678-9",
  "grain_type_code": "TRI",
  "campaign_label": "2025/26",
  "branch_name": "Planta Norte",
  "date_from": "2026-02-01",
  "date_to": "2026-02-28",
  "grain_ledger": {
    "opening_balance_kg": "5000.000",
    "movements": [
      {
        "id": "mv01-...",
        "movement_type": "CEG_DEPOSIT",
        "quantity_kg": "3000.000",
        "movement_at": "2026-02-10T08:30:00Z",
        "reference_document": "",
        "notes": ""
      }
    ],
    "closing_balance_kg": "8000.000"
  },
  "monetary_ledger": {
    "opening_ars": "0.000",
    "opening_usd": "0.000",
    "movements": [
      {
        "id": "mv02-...",
        "movement_type": "SERVICE_CHARGE",
        "ars_amount": "-1500.000",
        "usd_amount": "0.000",
        "movement_at": "2026-02-15T11:00:00Z",
        "reference_document": "FAC-2026-00050",
        "notes": "Conditioning fee"
      }
    ],
    "closing_ars": "-1500.000",
    "closing_usd": "0.000"
  }
}
```

**Errors**:
| Code | Condition |
|------|-----------|
| `400` | Missing `date_from` or `date_to`; invalid date format; `date_from > date_to` |
| `404` | Account not found or different tenant |

---

## Posicion Consolidada Endpoint

### `GET /posicion-consolidada/`

Compute cross-branch consolidated position for a producer in a campaign.

**Query parameters**:

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `producer_cuit` | string | Yes | CUIT to look up (blind index search) |
| `campaign_id` | UUID | Yes | Campaign to aggregate |

**Response 200**:
```json
{
  "producer_cuit": "20-12345678-9",
  "campaign_id": "c1c2c3c4-0000-0000-0000-000000000001",
  "campaign_label": "2025/26",
  "summary": [
    {
      "grain_type_id": "a1a2a3a4-...",
      "grain_type_code": "TRI",
      "grain_type_name": "Trigo",
      "total_grain_kg": "15000.000",
      "total_ars": "-1500.000",
      "total_usd": "0.000",
      "branch_breakdown": [
        {
          "branch_id": "b1b2b3b4-...",
          "branch_name": "Planta Norte",
          "grain_balance_kg": "10000.000",
          "ars_balance": "-1500.000",
          "usd_balance": "0.000"
        },
        {
          "branch_id": "b5b6b7b8-...",
          "branch_name": "Planta Sur",
          "grain_balance_kg": "5000.000",
          "ars_balance": "0.000",
          "usd_balance": "0.000"
        }
      ]
    }
  ]
}
```

**Notes**:
- Result is computed on demand via SQL aggregation — no stored entity.
- If no accounts exist for the producer/campaign, `summary` is an empty array.
- `producer_cuit` is computed via blind index — only exact matches returned.

**Errors**:
| Code | Condition |
|------|-----------|
| `400` | Missing `producer_cuit` or `campaign_id` |

---

## Common Error Response Shape

```json
{
  "detail": "Human-readable message",
  "code": "machine_readable_code"
}
```

| Code | HTTP | Description |
|------|------|-------------|
| `not_found` | 404 | Resource not found or cross-tenant access |
| `append_only_violation` | 405 | Attempted PATCH/DELETE on immutable movement |
| `invalid_movement_type` | 400 | Attempt to create system-generated movement type manually |
| `sign_violation` | 400 | Debit movement with positive amount |
| `permission_denied` | 403 | ADJUSTMENT without supervisor permission |
| `authentication_failed` | 401 | Missing or invalid JWT |
