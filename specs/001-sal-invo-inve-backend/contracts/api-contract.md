# API Contract: Sales-Invoicing-Inventory Integration

**Feature**: 001-sal-invo-inve-backend
**Date**: 2026-02-14
**Base URL**: `/api/v1/`
**Auth**: JWT Bearer token with `tenant_id` and `branch_id` claims

---

## Authentication

All endpoints require `Authorization: Bearer <jwt_token>`. Tenant isolation is automatic via `TenantBoundManager`. All responses are filtered to the authenticated tenant.

---

## Sales Module Endpoints

### Customer Management

#### `GET /api/v1/ventas/customers/`

List customers for the authenticated tenant. Cursor-paginated.

**Query Params**: `?is_active=true`, `?search=<razon_social or cuit>`, `?condicion_iva=1`

**Response 200**:
```json
{
  "next": "cursor_token",
  "previous": null,
  "results": [
    {
      "id": "uuid",
      "cuit": "20123456786",
      "doc_tipo": 80,
      "condicion_iva": 1,
      "condicion_iva_display": "IVA Responsable Inscripto",
      "razon_social": "Empresa SRL",
      "domicilio": "Av. Corrientes 1234, CABA",
      "email": "info@empresa.com",
      "telefono": "011-4555-1234",
      "is_active": true,
      "created_at": "2026-02-14T10:00:00Z"
    }
  ]
}
```

#### `POST /api/v1/ventas/customers/`

Create a new customer. Validates CUIT check digit.

**Request**:
```json
{
  "cuit": "20123456786",
  "doc_tipo": 80,
  "condicion_iva": 1,
  "razon_social": "Empresa SRL",
  "domicilio": "Av. Corrientes 1234, CABA",
  "email": "info@empresa.com",
  "telefono": "011-4555-1234"
}
```

**Response 201**: Full customer object (same as list item).

**Response 400** (validation error):
```json
{
  "cuit": ["CUIT check digit is invalid."],
  "condicion_iva": ["This field is required."]
}
```

**Response 409** (duplicate):
```json
{
  "error": {
    "code": "duplicate_cuit",
    "message": "A customer with CUIT 20123456786 already exists for this tenant."
  }
}
```

#### `GET /api/v1/ventas/customers/{id}/`

Retrieve single customer. **Response 200**: Full customer object. **Response 404**: Not found.

#### `PATCH /api/v1/ventas/customers/{id}/`

Update customer fields. Same validation as POST. **Response 200**: Updated object.

#### `DELETE /api/v1/ventas/customers/{id}/`

Delete customer. Fails if customer has linked sale orders.

**Response 204**: Deleted.
**Response 409**:
```json
{
  "error": {
    "code": "customer_has_orders",
    "message": "Cannot delete customer with existing sale orders. Deactivate instead."
  }
}
```

---

### Sale Order Management

#### `GET /api/v1/ventas/orders/`

List sale orders. Cursor-paginated, newest first.

**Query Params**: `?status=DRAFT`, `?customer={id}`, `?date_from=2026-02-01`, `?date_to=2026-02-28`

**Response 200**:
```json
{
  "next": "cursor_token",
  "results": [
    {
      "id": "uuid",
      "customer": {
        "id": "uuid",
        "cuit": "20123456786",
        "razon_social": "Empresa SRL",
        "condicion_iva": 1
      },
      "branch": {
        "id": "uuid",
        "name": "Sucursal Centro"
      },
      "status": "DRAFT",
      "subtotal": "1240.50",
      "total_iva": "260.51",
      "total_amount": "1501.01",
      "item_count": 3,
      "sale_date": "2026-02-14T10:00:00Z",
      "confirmed_at": null,
      "invoiced_at": null,
      "comprobante_id": null,
      "confirmed_by": null
    }
  ]
}
```

> **Note**: `comprobante_id` is computed from the reverse OneToOneField (`Comprobante.sale_order`). It is null until the order is confirmed.

#### `POST /api/v1/ventas/orders/`

Create a sale order in DRAFT status.

**Request**:
```json
{
  "customer_id": "uuid",
  "branch_id": "uuid"
}
```

**Response 201**: Full order object (items empty, totals zero).

#### `GET /api/v1/ventas/orders/{id}/`

Retrieve order with nested items.

**Response 200**:
```json
{
  "id": "uuid",
  "customer": { "id": "uuid", "razon_social": "Empresa SRL", "cuit": "20123456786", "condicion_iva": 1 },
  "branch": { "id": "uuid", "name": "Sucursal Centro" },
  "status": "DRAFT",
  "subtotal": "1240.50",
  "total_iva": "260.51",
  "total_amount": "1501.01",
  "items": [
    {
      "id": "uuid",
      "product": { "id": "uuid", "sku": "PROD-001", "name": "Widget A" },
      "quantity": "10.0000",
      "unit_price": "124.050",
      "subtotal": "1240.500",
      "tax_rate": "21.00",
      "iva_amount": "260.505"
    }
  ],
  "comprobante": null,
  "sale_date": "2026-02-14T10:00:00Z",
  "confirmed_at": null,
  "invoiced_at": null
}
```

#### `PATCH /api/v1/ventas/orders/{id}/`

Update order header (customer, branch). Only DRAFT orders.

**Response 200**: Updated object.
**Response 409**:
```json
{
  "error": {
    "code": "order_not_draft",
    "message": "Cannot modify a confirmed or invoiced order."
  }
}
```

#### `DELETE /api/v1/ventas/orders/{id}/`

Delete a DRAFT order. Fails if order is confirmed or invoiced.

**Response 204**: Deleted (cascade deletes order items).
**Response 409**:
```json
{
  "error": {
    "code": "order_not_draft",
    "message": "Cannot delete a confirmed or invoiced order."
  }
}
```

#### `POST /api/v1/ventas/orders/{id}/confirm/`

**Atomic operation**: Confirm sale → reserve stock → create invoice draft.

**Request**: Empty body.

**Response 200** (success):
```json
{
  "status": "CONFIRMED",
  "confirmed_at": "2026-02-14T10:05:00Z",
  "comprobante": {
    "id": "uuid",
    "cbte_tipo": 1,
    "cbte_nro": null,
    "status": "DRAFT"
  },
  "stock_reservations": [
    {
      "product_id": "uuid",
      "product_sku": "PROD-001",
      "quantity_reserved": "10.0000",
      "available_after": "40.0000"
    }
  ]
}
```

**Response 409** (insufficient stock):
```json
{
  "error": {
    "code": "insufficient_stock",
    "message": "Insufficient stock for product PROD-001",
    "details": {
      "product_id": "uuid",
      "product_sku": "PROD-001",
      "product_name": "Widget A",
      "available": "5.0000",
      "requested": "10.0000",
      "branch": "Sucursal Centro"
    }
  }
}
```

**Response 409** (no items):
```json
{
  "error": {
    "code": "order_empty",
    "message": "Cannot confirm an order with no items."
  }
}
```

#### `POST /api/v1/ventas/orders/{id}/authorize/`

Submit the linked invoice to ARCA for CAE authorization.

**Request**: Empty body.

**Response 200** (approved):
```json
{
  "status": "INVOICED",
  "invoiced_at": "2026-02-14T10:06:00Z",
  "comprobante": {
    "id": "uuid",
    "cbte_tipo": 1,
    "cbte_nro": 12345,
    "status": "AUTORIZADO",
    "cae": "12345678901234",
    "cae_fch_vto": "2026-02-24",
    "resultado": "A"
  }
}
```

**Response 200** (observed — CAE granted with warnings):
```json
{
  "status": "INVOICED",
  "comprobante": {
    "status": "OBSERVADO",
    "cae": "12345678901234",
    "resultado": "O",
    "observaciones": [
      {"Code": "10016", "Msg": "Verificar fecha de vencimiento"}
    ]
  }
}
```

**Response 422** (rejected by ARCA):
```json
{
  "error": {
    "code": "arca_rejected",
    "message": "Invoice rejected by ARCA",
    "resultado": "R",
    "errors": [
      {"Code": "1501", "Msg": "CUIT del receptor inválido"}
    ],
    "observaciones": [],
    "sale_status": "CONFIRMED",
    "stock_released": true
  }
}
```

**Response 504** (ARCA timeout):
```json
{
  "error": {
    "code": "arca_timeout",
    "message": "Network timeout during ARCA authorization",
    "recovery_attempted": true,
    "recovered": false,
    "sale_status": "CONFIRMED"
  }
}
```

#### `GET /api/v1/ventas/orders/{id}/invoice/`

Get linked comprobante for a sale order.

**Response 200**: Full comprobante object.
**Response 404**: No linked comprobante.

---

### Sale Order Items (nested)

#### `GET /api/v1/ventas/orders/{order_id}/items/`

List items for an order.

#### `POST /api/v1/ventas/orders/{order_id}/items/`

Add item. Only for DRAFT orders.

**Request**:
```json
{
  "product_id": "uuid",
  "quantity": "10.0000",
  "unit_price": "124.050"
}
```

**Response 201**: Full item object with auto-calculated subtotal and iva_amount.

**Response 409** (order not draft):
```json
{
  "error": {
    "code": "order_not_draft",
    "message": "Cannot add items to a confirmed or invoiced order."
  }
}
```

**Response 409** (duplicate product):
```json
{
  "error": {
    "code": "duplicate_product",
    "message": "Product PROD-001 already exists in this order. Update the existing item instead."
  }
}
```

#### `PATCH /api/v1/ventas/orders/{order_id}/items/{id}/`

Update item quantity or price. Only for DRAFT orders.

#### `DELETE /api/v1/ventas/orders/{order_id}/items/{id}/`

Remove item. Only for DRAFT orders. Recalculates order totals.

---

## Invoice Module Enhanced Endpoints

### `POST /api/v1/facturacion/comprobantes/{id}/authorize/`

Submit comprobante to ARCA for CAE. (Existing pattern, may be called via SaleOrder authorize action.)

**Request**: Empty body.

**Response 200** / **Response 422** / **Response 504**: See SaleOrder authorize responses above.

### `GET /api/v1/facturacion/comprobantes/{id}/qr/`

Generate fiscal QR code for authorized comprobante.

**Response 200**:
```json
{
  "qr_data": "https://www.afip.gob.ar/fe/qr/?p=eyJ2ZXIiOjEsImZlY2hhIjoi...",
  "qr_image_base64": "iVBORw0KGgoAAAANSUhEUgAA..."
}
```

**Response 409** (not authorized):
```json
{
  "error": {
    "code": "not_authorized",
    "message": "QR code can only be generated for authorized comprobantes."
  }
}
```

---

## Error Response Format (Standard)

All error responses follow this format:

```json
{
  "error": {
    "code": "error_code_snake_case",
    "message": "Human-readable description",
    "details": {}
  }
}
```

### Error Codes Reference

| Code | HTTP | Description |
|------|------|-------------|
| `insufficient_stock` | 409 | Not enough available stock for reservation |
| `order_not_draft` | 409 | Order is not in DRAFT status |
| `order_empty` | 409 | Order has no items |
| `duplicate_cuit` | 409 | CUIT already exists for tenant |
| `duplicate_product` | 409 | Product already in order |
| `customer_has_orders` | 409 | Cannot delete customer with orders |
| `arca_rejected` | 422 | ARCA rejected the invoice |
| `arca_timeout` | 504 | Network timeout communicating with ARCA |
| `arca_auth_failed` | 502 | WSAA authentication failed |
| `not_authorized` | 409 | Comprobante not in authorized state |
| `invalid_transition` | 409 | Invalid status transition attempted |
| `cross_tenant_reference` | 403 | IDOR violation detected |

---

## Serializer Decimal Precision

| Field Type | Storage | API Display | DRF Serializer |
|-----------|---------|-------------|----------------|
| Money (prices, totals) | DECIMAL(17,3) | 3 decimals | `DecimalField(max_digits=17, decimal_places=3)` |
| Quantity | DECIMAL(16,4) | 4 decimals | `DecimalField(max_digits=16, decimal_places=4)` |
| Tax rate | DECIMAL(5,2) | 2 decimals | `DecimalField(max_digits=5, decimal_places=2)` |

---

## Pagination

All list endpoints use cursor-based pagination per constitution Section XIII:
- Default page size: 100
- Maximum page size: 1000
- Ordering: `-created_at` (newest first)
- Cursor token in `next`/`previous` fields
