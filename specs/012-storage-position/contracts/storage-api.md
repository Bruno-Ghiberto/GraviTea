# API Contracts: Storage & Position (Spec-12)

**Base URL**: `/api/v1/acopio/`
**Authentication**: JWT Bearer token required on all endpoints
**Content-Type**: `application/json`
**Generated**: 2026-03-19

---

## StorageUnit Endpoints

### `GET /storage-units/`

List all active storage units for the authenticated tenant, with derived
`current_occupancy_kg` per unit.

**Query parameters**:
| Param | Type | Description |
|-------|------|-------------|
| `branch` | UUID | Filter by branch ID |
| `is_active` | boolean | Filter by active status (default: true) |
| `page` | integer | Page number (PageNumberPagination) |
| `page_size` | integer | Items per page (default 25, max 100) |

**Response 200**:
```json
{
  "count": 12,
  "next": "...",
  "previous": null,
  "results": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Silo 1",
      "unit_type": "SILO_VERTICAL",
      "unit_type_display": "Silo Vertical",
      "branch": "b1b2b3b4-...",
      "branch_name": "Planta Pergamino",
      "capacity_tonnes": "500.000",
      "current_grain_type": "a1a2a3a4-...",
      "current_grain_type_code": "SOJ",
      "is_active": true,
      "environment_sensor_id": null,
      "current_occupancy_kg": "342500.000",
      "capacity_utilisation_pct": 68.5,
      "created_at": "2026-03-01T10:00:00Z"
    }
  ]
}
```

### `POST /storage-units/`

Create a new storage unit.

**Request body**:
```json
{
  "name": "Silo 3",
  "unit_type": "SILO_VERTICAL",
  "branch": "b1b2b3b4-...",
  "capacity_tonnes": "800.000",
  "environment_sensor_id": null
}
```

**Response 201**: StorageUnit object (same shape as list item).

**Errors**:
| Code | Condition |
|------|-----------|
| `400` | Validation error (e.g., duplicate name within branch, capacity <= 0) |
| `403` | Insufficient permissions |

### `GET /storage-units/{id}/`

Retrieve a single storage unit with current occupancy.

**Response 200**: StorageUnit object.

### `PATCH /storage-units/{id}/`

Update mutable fields on a storage unit.

**Patchable fields**: `name`, `unit_type`, `capacity_tonnes`, `environment_sensor_id`, `is_active`

**Response 200**: Updated StorageUnit object.

**Errors**:
| Code | Condition |
|------|-----------|
| `400` | Duplicate name or validation failure |
| `409` | Attempt to deactivate a unit with non-zero active stock |

### `DELETE /storage-units/{id}/`

Hard delete is rejected. Use `PATCH is_active: false` for soft-deactivation.

**Response 405**: Method Not Allowed.

### `POST /storage-units/suggest/`

Request a ranked list of compatible storage units for incoming grain.

**Request body**:
```json
{
  "grain_type_id": "a1a2a3a4-...",
  "campaign_id": "c1c2c3c4-...",
  "grado": 2,
  "incoming_kg": "28500.000",
  "branch_id": "b1b2b3b4-..."
}
```

**Response 200**:
```json
{
  "suggestions": [
    {
      "storage_unit_id": "550e8400-...",
      "name": "Silo 3",
      "score": 70,
      "reasons": ["grain type match", "grade match", "campaign match"],
      "available_capacity_kg": "157500.000",
      "current_occupancy_kg": "342500.000"
    },
    {
      "storage_unit_id": "660e8400-...",
      "name": "Silo 5",
      "score": 40,
      "reasons": ["empty unit -- compatible"],
      "available_capacity_kg": "500000.000",
      "current_occupancy_kg": "0.000"
    }
  ]
}
```

**Scoring**: grain type match = 40pts; grade match = +20pts; campaign match = +10pts.
Units excluded if: incompatible grain type OR insufficient capacity.

### `GET /storage-units/stock-report/`

Real-time stock report computed from the GrainMovement ledger.

**Query parameters**:
| Param | Type | Description |
|-------|------|-------------|
| `branch` | UUID | Filter report to a specific branch |
| `grain_type` | UUID | Filter by grain type |
| `campaign` | UUID | Filter by campaign year |

**Response 200**:
```json
{
  "generated_at": "2026-03-19T14:30:00Z",
  "total_capacity_tonnes": "5600.000",
  "total_occupied_kg": "2834500.000",
  "utilisation_pct": 50.6,
  "by_storage_unit": [
    {
      "storage_unit_id": "550e8400-...",
      "name": "Silo 1",
      "grain_type_code": "SOJ",
      "campaign_code": "24/25",
      "total_kg": "342500.000",
      "capacity_pct": 68.5
    }
  ],
  "by_grain_type": [
    {"grain_type_code": "SOJ", "total_kg": "1534500.000"},
    {"grain_type_code": "TRI", "total_kg": "1300000.000"}
  ],
  "by_campaign": [
    {"campaign_code": "24/25", "total_kg": "2834500.000"}
  ]
}
```

---

## GrainLot Endpoints

### `GET /grain-lots/`

List grain lots for the authenticated tenant.

**Query parameters**:
| Param | Type | Description |
|-------|------|-------------|
| `storage_unit` | UUID | Filter by storage unit |
| `grain_type` | UUID | Filter by grain type |
| `campaign` | UUID | Filter by campaign |
| `is_own_grain` | boolean | Filter by ownership type |
| `page` | integer | Page number |

**Response 200**:
```json
{
  "count": 8,
  "results": [
    {
      "id": "aa1bb2cc-...",
      "lot_code": "PERG-SOJ-2425-2",
      "grain_type": "a1a2a3a4-...",
      "grain_type_code": "SOJ",
      "campaign": "c1c2c3c4-...",
      "campaign_code": "24/25",
      "grado": 2,
      "storage_unit": "550e8400-...",
      "storage_unit_name": "Silo 1",
      "total_kg": "342500.000",
      "is_own_grain": false,
      "created_at": "2026-03-01T08:00:00Z"
    }
  ]
}
```

### `GET /grain-lots/{id}/`

Retrieve a single grain lot with full details.

**Response 200**: GrainLot object (same shape as list item).

GrainLot is read-only via API. Creation is automatic when a DEPOSIT movement
is recorded (via `create_deposit_from_romaneo` service).

---

## GrainMovement Endpoints (Append-Only)

**Note**: PATCH, PUT, DELETE return HTTP 405. The movement ledger is immutable.

### `GET /grain-lots/{grain_lot_id}/movements/`

List all movements for a specific grain lot (chronological, newest first).

**Response 200**:
```json
{
  "count": 5,
  "results": [
    {
      "id": "mv1mv2mv3-...",
      "movement_type": "DEPOSIT",
      "movement_type_display": "Depósito",
      "quantity_kg": "28500.000",
      "movement_at": "2026-03-10T09:15:00Z",
      "romaneo": "rom1rom2-...",
      "romaneo_number": "ROM-2026-00042",
      "reference_document": null,
      "notes": null,
      "created_by_name": "Juan Pérez"
    }
  ]
}
```

### `POST /grain-lots/{grain_lot_id}/movements/`

Manually create a movement (for dispatch, transfer, or adjustment).
DEPOSIT movements are created automatically by the romaneo confirmation flow.

**Request body**:
```json
{
  "movement_type": "WITHDRAWAL",
  "quantity_kg": "15000.000",
  "reference_document": "CPE-2026-0123",
  "notes": null
}
```

**Response 201**: GrainMovement object.

**Errors**:
| Code | Condition |
|------|-----------|
| `400` | Validation error |
| `409` | Insufficient balance (withdrawal would produce negative total_kg) |

### `GET /grain-lots/{grain_lot_id}/movements/{id}/`

Retrieve a single movement record.

**Response 200**: GrainMovement object.

### `PATCH /grain-lots/{grain_lot_id}/movements/{id}/`

**Response 405**: Method Not Allowed. Movements are immutable.

### `DELETE /grain-lots/{grain_lot_id}/movements/{id}/`

**Response 405**: Method Not Allowed. Movements are immutable.

---

## Transfer Endpoint

### `POST /grain-lots/transfer/`

Atomically transfer grain between two storage units (FR-010). Creates paired
TRANSFER_OUT + TRANSFER_IN movements in a single database transaction.

**Request body**:
```json
{
  "source_lot_id": "aa1bb2cc-...",
  "destination_lot_id": "dd3ee4ff-...",
  "quantity_kg": "20000.000",
  "notes": "Consolidation before campaign close"
}
```

**Response 200**:
```json
{
  "transfer_out": { "id": "mv-out-...", "quantity_kg": "-20000.000", ... },
  "transfer_in": { "id": "mv-in-...", "quantity_kg": "20000.000", ... }
}
```

**Errors**:
| Code | Condition |
|------|-----------|
| `400` | Source and destination are the same lot |
| `409` | Insufficient source balance |

---

## Reconciliation Endpoint

### `POST /storage-units/reconcile/`

Submit physical measurement counts and apply adjustment movements (FR-008).

**Request body**:
```json
{
  "branch_id": "b1b2b3b4-...",
  "notes": "Monthly physical count 2026-03-15",
  "measurements": [
    {"storage_unit_id": "550e8400-...", "measured_kg": "340000.000"},
    {"storage_unit_id": "660e8400-...", "measured_kg": "498000.000"}
  ]
}
```

**Response 200**:
```json
{
  "reconciliation_id": "rec1rec2-...",
  "performed_at": "2026-03-15T17:00:00Z",
  "variances": [
    {
      "storage_unit_id": "550e8400-...",
      "storage_unit_name": "Silo 1",
      "ledger_kg": "342500.000",
      "measured_kg": "340000.000",
      "variance_kg": "-2500.000",
      "adjustment_movement_id": "mv-adj-..."
    }
  ],
  "total_variance_kg": "-2500.000"
}
```

**Errors**:
| Code | Condition |
|------|-----------|
| `400` | Measurements missing for required silos, or notes blank |
| `403` | Insufficient permissions |

---

## Romaneo Endpoint (Modified)

### `PATCH /romaneos/{id}/`

Existing endpoint. Now accepts `storage_unit` as a patchable field (REST API
Design v1.0 §5). Set this field before calling `POST /romaneos/{id}/confirmar-conforme/`.

**Patchable fields (extended)**:
- `storage_unit` (UUID or null) — assign silo at discharge

**Response 200**: Romaneo object with `storage_unit` and `grain_lot` included.

---

## Error Response Format

All errors follow the RFC 7807 Problem Details format used by DRF:

```json
{
  "type": "insufficient_grain_balance",
  "detail": "Insufficient grain stock. Lot 'PERG-SOJ-2425-2' has 10000.000 kg but attempted withdrawal is 15000.000 kg. Shortfall: 5000.000 kg.",
  "current_balance_kg": "10000.000",
  "requested_kg": "15000.000"
}
```

Standard HTTP status codes used:
- `200 OK` — successful retrieval or update
- `201 Created` — successful creation
- `400 Bad Request` — validation error
- `403 Forbidden` — insufficient permissions
- `404 Not Found` — resource not found or tenant-isolated
- `405 Method Not Allowed` — attempt to modify immutable resource
- `409 Conflict` — business rule violation (insufficient balance, duplicate name)
