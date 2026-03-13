# GraviTea ERP – Database Schema (PostgreSQL 18.1)

## 0. Convenciones globales

- **Motor:** PostgreSQL 18.1
- **PK por defecto:** `UUID` generado con `gen_random_uuid()` (extensión `pgcrypto`)
- **Multi-tenant:** casi todas las entidades de negocio tienen `tenant_id` (FK a `tenant.id`).
- **Timestamps:** `created_at TIMESTAMPTZ DEFAULT NOW()`
- **Moneda / montos:** `DECIMAL(17,3)` para todos los valores financieros (montos, cantidades, costos unitarios, precios).
- **Encriptación (aplicación Django):**
  - `encrypted_app`: el valor se guarda cifrado en la BD (AES-256-GCM u otro) y se descifra sólo desde el backend.
  - `hash`: valor hash (SHA-256 hex) para búsquedas exactas sin descifrar toda la tabla.
  - `plain`: sin cifrado app-level (igual protegido con cifrado en reposo + TLS + permisos).

## 1. ENUM Types

```sql
payment_method_enum         = ('CASH','CREDIT_CARD','DEBIT_CARD','TRANSFER','QR','ACCOUNT')
stock_movement_type_enum    = ('SALE','PURCHASE','ADJ','TRANS_IN','TRANS_OUT')
sale_type_enum              = ('FACTURA_A','FACTURA_B','TICKET','NC')
sale_status_enum            = ('DRAFT','PENDING_AFIP','FISCALIZED','CANCELLED')
budget_status_enum          = ('OPEN','CONVERTED','EXPIRED')
customer_ledger_type_enum   = ('DEBIT','CREDIT')
supplier_ledger_type_enum   = ('DEBIT','CREDIT')
purchase_order_status_enum  = ('DRAFT','SENT','PARTIAL_RECEIVED','COMPLETED')
````

## 2. Tablas

---

### 2.1. `tenant`

Raíz de multi-tenant: representa a cada empresa cliente.

| columna                | tipo        | null | default             | notas / constraints                         | encrypt |
| ---------------------- | ----------- | ---- | ------------------- | ------------------------------------------- | ------- |
| `id`                   | UUID        | no   | `gen_random_uuid()` | PK                                          | plain   |
| `name`                 | TEXT        | no   |                     | nombre del tenant                           | plain   |
| `tax_id`               | TEXT        | sí   |                     | CUIT/RUT empresa                            | plain   |
| `fiscal_config_public` | JSONB       | sí   |                     | config fiscal NO sensible (puntos de venta) | plain   |
| `fiscal_secrets_ref`   | TEXT        | sí   |                     | referencia a secretos en Secret Manager     | plain   |
| `plan_type`            | TEXT        | no   |                     | FREE / PRO / ENTERPRISE                     | plain   |
| `valid_until`          | TIMESTAMPTZ | sí   |                     | fecha de expiración del plan                | plain   |
| `is_active`            | BOOLEAN     | no   | `TRUE`              |                                             | plain   |
| `created_at`           | TIMESTAMPTZ | no   | `NOW()`             |                                             | plain   |

---

### 2.2. `branch`

Sucursales físicas del tenant.

| columna           | tipo        | null | default             | notas / constraints                   | encrypt |
| ----------------- | ----------- | ---- | ------------------- | ------------------------------------- | ------- |
| `id`              | UUID        | no   | `gen_random_uuid()` | PK                                    | plain   |
| `tenant_id`       | UUID        | no   |                     | FK → `tenant(id)` `ON DELETE CASCADE` | plain   |
| `name`            | TEXT        | no   |                     |                                       | plain   |
| `address`         | TEXT        | sí   |                     |                                       | plain   |
| `phone`           | TEXT        | sí   |                     |                                       | plain   |
| `coordinates`     | JSONB       | sí   |                     | lat/long u otros datos logísticos     | plain   |
| `afip_pos_number` | INTEGER     | sí   |                     | punto de venta fiscal                 | plain   |
| `is_active`       | BOOLEAN     | no   | `TRUE`              |                                       | plain   |
| `created_at`      | TIMESTAMPTZ | no   | `NOW()`             |                                       | plain   |

---

### 2.3. `role`

Roles y permisos por tenant.

| columna       | tipo        | null | default             | notas / constraints                   | encrypt |
| ------------- | ----------- | ---- | ------------------- | ------------------------------------- | ------- |
| `id`          | UUID        | no   | `gen_random_uuid()` | PK                                    | plain   |
| `tenant_id`   | UUID        | no   |                     | FK → `tenant(id)` `ON DELETE CASCADE` | plain   |
| `name`        | TEXT        | no   |                     | nombre del rol                        | plain   |
| `permissions` | JSONB       | no   |                     | lista de acciones                     | plain   |
| `created_at`  | TIMESTAMPTZ | no   | `NOW()`             |                                       | plain   |

---

### 2.4. `app_user`

Usuarios de la aplicación asociados a un tenant.

| columna         | tipo        | null | default             | notas / constraints                                    | encrypt |
| --------------- | ----------- | ---- | ------------------- | ------------------------------------------------------ | ------- |
| `id`            | UUID        | no   | `gen_random_uuid()` | PK                                                     | plain   |
| `tenant_id`     | UUID        | no   |                     | FK → `tenant(id)` `ON DELETE CASCADE`                  | plain   |
| `email`         | TEXT        | no   |                     | `UNIQUE(tenant_id, email)`                             | plain   |
| `password_hash` | TEXT        | no   |                     | hash Django (PBKDF2/Argon2), **no cifrado**, sólo hash | hash    |
| `full_name`     | TEXT        | sí   |                     | nombre completo                                        | plain   |
| `role_id`       | UUID        | sí   |                     | FK → `role(id)`                                        | plain   |
| `last_login`    | TIMESTAMPTZ | sí   |                     |                                                        | plain   |
| `is_active`     | BOOLEAN     | no   | `TRUE`              |                                                        | plain   |
| `created_at`    | TIMESTAMPTZ | no   | `NOW()`             |                                                        | plain   |

---

### 2.5. `product_category`

Categorías de producto (por tenant).

| columna      | tipo        | null | default             | notas / constraints                   | encrypt |
| ------------ | ----------- | ---- | ------------------- | ------------------------------------- | ------- |
| `id`         | UUID        | no   | `gen_random_uuid()` | PK                                    | plain   |
| `tenant_id`  | UUID        | no   |                     | FK → `tenant(id)` `ON DELETE CASCADE` | plain   |
| `name`       | TEXT        | no   |                     | `UNIQUE(tenant_id, name)`             | plain   |
| `created_at` | TIMESTAMPTZ | no   | `NOW()`             |                                       | plain   |

---

### 2.6. `price_list`

Listas de precios por tenant.

| columna      | tipo         | null | default             | notas / constraints                   | encrypt |
| ------------ | ------------ | ---- | ------------------- | ------------------------------------- | ------- |
| `id`         | UUID         | no   | `gen_random_uuid()` | PK                                    | plain   |
| `tenant_id`  | UUID         | no   |                     | FK → `tenant(id)` `ON DELETE CASCADE` | plain   |
| `name`       | TEXT         | no   |                     | `UNIQUE(tenant_id, name)`             | plain   |
| `margin_pct` | NUMERIC(6,2) | sí   |                     | margen base sugerido                  | plain   |
| `is_default` | BOOLEAN      | no   | `FALSE`             |                                       | plain   |
| `created_at` | TIMESTAMPTZ  | no   | `NOW()`             |                                       | plain   |

---

### 2.7. `supplier`

Proveedores (empresa o persona física).

| columna                  | tipo          | null | default             | notas / constraints                       | encrypt       |
| ------------------------ | ------------- | ---- | ------------------- | ----------------------------------------- | ------------- |
| `id`                     | UUID          | no   | `gen_random_uuid()` | PK                                        | plain         |
| `tenant_id`              | UUID          | no   |                     | FK → `tenant(id)` `ON DELETE CASCADE`     | plain         |
| `name`                   | TEXT          | no   |                     | nombre del proveedor                      | plain         |
| `tax_id_encrypted`       | TEXT          | sí   |                     | CUIT/DNI cifrado                          | encrypted_app |
| `tax_id_hash`            | CHAR(64)      | sí   |                     | SHA-256 hex para búsqueda exacta          | hash          |
| `contact_info_encrypted` | TEXT          | sí   |                     | datos de contacto (tel, persona) cifrados | encrypted_app |
| `email_encrypted`        | TEXT          | sí   |                     | email cifrado                             | encrypted_app |
| `email_hash`             | CHAR(64)      | sí   |                     | índice para búsqueda por email            | hash          |
| `address_encrypted`      | TEXT          | sí   |                     | dirección cifrada                         | encrypted_app |
| `lead_time_days`         | INTEGER       | sí   |                     | tiempo medio de entrega                   | plain         |
| `current_balance`        | DECIMAL(17,3) | no   | `0`                 | saldo cta cte proveedor                   | plain         |
| `created_at`             | TIMESTAMPTZ   | no   | `NOW()`             |                                           | plain         |

Índices extra:

* `idx_supplier_tenant_taxid_hash(tenant_id, tax_id_hash)`
* `idx_supplier_tenant_email_hash(tenant_id, email_hash)`

---

### 2.8. `product`

Productos del catálogo.

| columna         | tipo          | null | default             | notas / constraints                       | encrypt |
| --------------- | ------------- | ---- | ------------------- | ----------------------------------------- | ------- |
| `id`            | UUID          | no   | `gen_random_uuid()` | PK                                        | plain   |
| `tenant_id`     | UUID          | no   |                     | FK → `tenant(id)` `ON DELETE CASCADE`     | plain   |
| `sku`           | TEXT          | no   |                     | `UNIQUE(tenant_id, sku)`                  | plain   |
| `barcode`       | TEXT          | sí   |                     | `UNIQUE(tenant_id, barcode)` (si no null) | plain   |
| `name`          | TEXT          | no   |                     |                                           | plain   |
| `description`   | TEXT          | sí   |                     |                                           | plain   |
| `category_id`   | UUID          | sí   |                     | FK → `product_category(id)`               | plain   |
| `supplier_id`   | UUID          | sí   |                     | FK → `supplier(id)`                       | plain   |
| `current_cost`  | DECIMAL(17,3) | sí   |                     | costo promedio ponderado                  | plain   |
| `current_price` | DECIMAL(17,3) | sí   |                     | precio actual                             | plain   |
| `tax_rate`      | NUMERIC(5,2)  | sí   |                     | IVA (por ej. 21.00)                       | plain   |
| `min_stock`     | DECIMAL(17,3) | sí   |                     | punto de pedido                           | plain   |
| `max_stock`     | DECIMAL(17,3) | sí   |                     | stock máximo                              | plain   |
| `attributes`    | JSONB         | sí   |                     | atributos varios (color, potencia, etc.)  | plain   |
| `ml_tags`       | JSONB         | sí   |                     | tags de ML / categorización               | plain   |
| `is_active`     | BOOLEAN       | no   | `TRUE`              |                                           | plain   |
| `created_at`    | TIMESTAMPTZ   | no   | `NOW()`             |                                           | plain   |

---

### 2.9. `product_price_history`

Historial de precios por producto y lista de precios.

| columna              | tipo          | null | default             | notas / constraints                       | encrypt |
| -------------------- | ------------- | ---- | ------------------- | ----------------------------------------- | ------- |
| `id`                 | UUID          | no   | `gen_random_uuid()` | PK                                        | plain   |
| `product_id`         | UUID          | no   |                     | FK → `product(id)` `ON DELETE CASCADE`    | plain   |
| `price_list_id`      | UUID          | no   |                     | FK → `price_list(id)` `ON DELETE CASCADE` | plain   |
| `price`              | DECIMAL(17,3) | no   |                     |                                           | plain   |
| `valid_from`         | TIMESTAMPTZ   | no   |                     | inicio vigencia                           | plain   |
| `valid_to`           | TIMESTAMPTZ   | sí   |                     | fin vigencia                              | plain   |
| `change_reason`      | TEXT          | sí   |                     | motivo del cambio                         | plain   |
| `changed_by_user_id` | UUID          | sí   |                     | FK → `app_user(id)`                       | plain   |

---

### 2.10. `product_cost_history`

| columna      | tipo          | null | default             | notas / constraints                    | encrypt |
| ------------ | ------------- | ---- | ------------------- | -------------------------------------- | ------- |
| `id`         | UUID          | no   | `gen_random_uuid()` | PK                                     | plain   |
| `product_id` | UUID          | no   |                     | FK → `product(id)` `ON DELETE CASCADE` | plain   |
| `cost`       | DECIMAL(17,3) | no   |                     | costo                                  | plain   |
| `valid_from` | TIMESTAMPTZ   | no   |                     |                                        | plain   |
| `valid_to`   | TIMESTAMPTZ   | sí   |                     |                                        | plain   |
| `source_doc` | TEXT          | sí   |                     | referencia factura / ajuste            | plain   |

---

### 2.11. `stock_snapshot`

Snapshot de stock por sucursal y producto.

| columna             | tipo          | null | default             | notas / constraints                    | encrypt |
| ------------------- | ------------- | ---- | ------------------- | -------------------------------------- | ------- |
| `id`                | UUID          | no   | `gen_random_uuid()` | PK                                     | plain   |
| `branch_id`         | UUID          | no   |                     | FK → `branch(id)` `ON DELETE CASCADE`  | plain   |
| `product_id`        | UUID          | no   |                     | FK → `product(id)` `ON DELETE CASCADE` | plain   |
| `quantity`          | DECIMAL(17,3) | no   | `0`                 | cantidad disponible                    | plain   |
| `reserved_quantity` | DECIMAL(17,3) | no   | `0`                 | reservada                              | plain   |
| `last_updated`      | TIMESTAMPTZ   | no   | `NOW()`             |                                        | plain   |

Constraint: `UNIQUE(branch_id, product_id)`.

---

### 2.12. `stock_movement`

Movimientos de stock.

| columna          | tipo                     | null | default             | notas / constraints                          | encrypt |
| ---------------- | ------------------------ | ---- | ------------------- | -------------------------------------------- | ------- |
| `id`             | UUID                     | no   | `gen_random_uuid()` | PK                                           | plain   |
| `tenant_id`      | UUID                     | no   |                     | FK → `tenant(id)` `ON DELETE CASCADE`        | plain   |
| `branch_id`      | UUID                     | no   |                     | FK → `branch(id)` `ON DELETE CASCADE`        | plain   |
| `product_id`     | UUID                     | no   |                     | FK → `product(id)` `ON DELETE CASCADE`       | plain   |
| `quantity_delta` | DECIMAL(17,3)            | no   |                     | +venta / -compra / etc.                      | plain   |
| `cost_snapshot`  | DECIMAL(17,3)            | sí   |                     | costo al momento                             | plain   |
| `type`           | stock_movement_type_enum | no   |                     | SALE / PURCHASE / ADJ / TRANS_IN / TRANS_OUT | plain   |
| `reference_id`   | UUID                     | sí   |                     | referencia a SALE / PURCHASE_ORDER / etc.    | plain   |
| `notes`          | TEXT                     | sí   |                     |                                              | plain   |
| `created_at`     | TIMESTAMPTZ              | no   | `NOW()`             |                                              | plain   |

---

### 2.13. `customer`

Clientes finales (persona física o jurídica).

| columna             | tipo          | null | default             | notas / constraints                   | encrypt       |
| ------------------- | ------------- | ---- | ------------------- | ------------------------------------- | ------------- |
| `id`                | UUID          | no   | `gen_random_uuid()` | PK                                    | plain         |
| `tenant_id`         | UUID          | no   |                     | FK → `tenant(id)` `ON DELETE CASCADE` | plain         |
| `name`              | TEXT          | no   |                     | nombre mostrado en listados           | plain         |
| `tax_id_encrypted`  | TEXT          | sí   |                     | DNI/CUIT cifrado                      | encrypted_app |
| `tax_id_hash`       | CHAR(64)      | sí   |                     | SHA-256 para búsquedas exactas        | hash          |
| `email_encrypted`   | TEXT          | sí   |                     | email cifrado                         | encrypted_app |
| `email_hash`        | CHAR(64)      | sí   |                     | SHA-256 para búsquedas exactas        | hash          |
| `phone_encrypted`   | TEXT          | sí   |                     | teléfono cifrado                      | encrypted_app |
| `address_encrypted` | TEXT          | sí   |                     | dirección cifrada                     | encrypted_app |
| `price_list_id`     | UUID          | sí   |                     | FK → `price_list(id)`                 | plain         |
| `credit_limit`      | DECIMAL(17,3) | no   | `0`                 | límite de crédito                     | plain         |
| `current_balance`   | DECIMAL(17,3) | no   | `0`                 | saldo de cuenta corriente             | plain         |
| `created_at`        | TIMESTAMPTZ   | no   | `NOW()`             |                                       | plain         |

Índices:

* `idx_customer_tenant_taxid_hash(tenant_id, tax_id_hash)`
* `idx_customer_tenant_email_hash(tenant_id, email_hash)`

---

### 2.14. `customer_account_ledger`

Movimiento de cuenta corriente de clientes.

| columna            | tipo                      | null | default             | notas / constraints                     | encrypt |
| ------------------ | ------------------------- | ---- | ------------------- | --------------------------------------- | ------- |
| `id`               | UUID                      | no   | `gen_random_uuid()` | PK                                      | plain   |
| `customer_id`      | UUID                      | no   |                     | FK → `customer(id)` `ON DELETE CASCADE` | plain   |
| `type`             | customer_ledger_type_enum | no   |                     | DEBIT (Venta) / CREDIT (Pago)           | plain   |
| `amount`           | DECIMAL(17,3)             | no   |                     |                                         | plain   |
| `reference_id`     | UUID                      | sí   |                     | SALE/PAYMENT asociado                   | plain   |
| `balance_snapshot` | DECIMAL(17,3)             | no   |                     | saldo luego del movimiento              | plain   |
| `description`      | TEXT                      | sí   |                     |                                         | plain   |
| `created_at`       | TIMESTAMPTZ               | no   | `NOW()`             |                                         | plain   |

---

### 2.15. `supplier_account_ledger`

Análogo al ledger de clientes, para proveedores.

| columna            | tipo                      | null | default             | notas / constraints                     | encrypt |
| ------------------ | ------------------------- | ---- | ------------------- | --------------------------------------- | ------- |
| `id`               | UUID                      | no   | `gen_random_uuid()` | PK                                      | plain   |
| `supplier_id`      | UUID                      | no   |                     | FK → `supplier(id)` `ON DELETE CASCADE` | plain   |
| `type`             | supplier_ledger_type_enum | no   |                     | DEBIT (Pago) / CREDIT (Factura)         | plain   |
| `amount`           | DECIMAL(17,3)             | no   |                     |                                         | plain   |
| `reference_id`     | UUID                      | sí   |                     | PURCHASE/PAYMENT asociado               | plain   |
| `balance_snapshot` | DECIMAL(17,3)             | no   |                     | saldo luego del movimiento              | plain   |
| `description`      | TEXT                      | sí   |                     |                                         | plain   |
| `created_at`       | TIMESTAMPTZ               | no   | `NOW()`             |                                         | plain   |

---

### 2.16. `purchase_order`

Ordenes de compra.

| columna             | tipo                       | null | default             | notas / constraints                         | encrypt |
| ------------------- | -------------------------- | ---- | ------------------- | ------------------------------------------- | ------- |
| `id`                | UUID                       | no   | `gen_random_uuid()` | PK                                          | plain   |
| `tenant_id`         | UUID                       | no   |                     | FK → `tenant(id)` `ON DELETE CASCADE`       | plain   |
| `supplier_id`       | UUID                       | no   |                     | FK → `supplier(id)` `ON DELETE CASCADE`     | plain   |
| `status`            | purchase_order_status_enum | no   |                     | DRAFT / SENT / PARTIAL_RECEIVED / COMPLETED | plain   |
| `total_estimated`   | DECIMAL(17,3)              | sí   |                     |                                             | plain   |
| `expected_delivery` | TIMESTAMPTZ                | sí   |                     |                                             | plain   |
| `created_at`        | TIMESTAMPTZ                | no   | `NOW()`             |                                             | plain   |

---

### 2.17. `purchase_item`

Líneas de una orden de compra.

| columna             | tipo          | null | default             | notas / constraints                           | encrypt |
| ------------------- | ------------- | ---- | ------------------- | --------------------------------------------- | ------- |
| `id`                | UUID          | no   | `gen_random_uuid()` | PK                                            | plain   |
| `purchase_order_id` | UUID          | no   |                     | FK → `purchase_order(id)` `ON DELETE CASCADE` | plain   |
| `product_id`        | UUID          | no   |                     | FK → `product(id)` `ON DELETE RESTRICT`       | plain   |
| `quantity_ordered`  | DECIMAL(17,3) | no   |                     |                                               | plain   |
| `quantity_received` | DECIMAL(17,3) | no   | `0`                 |                                               | plain   |
| `unit_cost`         | DECIMAL(17,3) | no   |                     |                                               | plain   |
| `subtotal`          | DECIMAL(17,3) | no   |                     | cantidad * unit_cost                          | plain   |

---

### 2.18. `sale`

Cabecera de venta / comprobante fiscal.

| columna         | tipo             | null | default             | notas / constraints                                 | encrypt |
| --------------- | ---------------- | ---- | ------------------- | --------------------------------------------------- | ------- |
| `id`            | UUID             | no   | `gen_random_uuid()` | PK                                                  | plain   |
| `tenant_id`     | UUID             | no   |                     | FK → `tenant(id)` `ON DELETE CASCADE`               | plain   |
| `branch_id`     | UUID             | no   |                     | FK → `branch(id)` `ON DELETE CASCADE`               | plain   |
| `customer_id`   | UUID             | sí   |                     | FK → `customer(id)`                                 | plain   |
| `user_id`       | UUID             | sí   |                     | FK → `app_user(id)` (vendedor)                      | plain   |
| `doc_number`    | TEXT             | sí   |                     | número fiscal / punto+comprobante                   | plain   |
| `type`          | sale_type_enum   | no   |                     | FACTURA_A/B, TICKET, NC                             | plain   |
| `status`        | sale_status_enum | no   |                     | DRAFT, PENDING_AFIP, etc.                           | plain   |
| `total_net`     | DECIMAL(17,3)    | no   | `0`                 |                                                     | plain   |
| `total_tax`     | DECIMAL(17,3)    | no   | `0`                 |                                                     | plain   |
| `total_gross`   | DECIMAL(17,3)    | no   | `0`                 |                                                     | plain   |
| `afip_response` | JSONB            | sí   |                     | datos de CAE / vencimiento (solo cifrado en reposo) | plain   |
| `ml_context`    | JSONB            | sí   |                     | info para modelos ML (clima, hora, etc.)            | plain   |
| `created_at`    | TIMESTAMPTZ      | no   | `NOW()`             |                                                     | plain   |

Índice: `idx_sale_tenant_branch_date(tenant_id, branch_id, created_at)`.

---

### 2.19. `sale_item`

Líneas de la venta.

| columna        | tipo          | null | default             | notas / constraints                     | encrypt |
| -------------- | ------------- | ---- | ------------------- | --------------------------------------- | ------- |
| `id`           | UUID          | no   | `gen_random_uuid()` | PK                                      | plain   |
| `sale_id`      | UUID          | no   |                     | FK → `sale(id)` `ON DELETE CASCADE`     | plain   |
| `product_id`   | UUID          | no   |                     | FK → `product(id)` `ON DELETE RESTRICT` | plain   |
| `description`  | TEXT          | no   |                     | snapshot del nombre del producto        | plain   |
| `quantity`     | DECIMAL(17,3) | no   |                     |                                         | plain   |
| `unit_price`   | DECIMAL(17,3) | no   |                     |                                         | plain   |
| `discount_pct` | NUMERIC(6,2)  | no   | `0`                 |                                         | plain   |
| `tax_rate`     | NUMERIC(5,2)  | sí   |                     |                                         | plain   |
| `subtotal`     | DECIMAL(17,3) | no   |                     | (quantity * unit_price) - descuento     | plain   |

---

### 2.20. `payment`

Pagos asociados a una venta.

| columna                       | tipo                | null | default             | notas / constraints                       | encrypt       |
| ----------------------------- | ------------------- | ---- | ------------------- | ----------------------------------------- | ------------- |
| `id`                          | UUID                | no   | `gen_random_uuid()` | PK                                        | plain         |
| `sale_id`                     | UUID                | no   |                     | FK → `sale(id)` `ON DELETE CASCADE`       | plain         |
| `method`                      | payment_method_enum | no   |                     | CASH / CARD / TRANSFER / QR / ACCOUNT     | plain         |
| `amount`                      | DECIMAL(17,3)       | no   |                     |                                           | plain         |
| `currency`                    | VARCHAR(3)          | no   | `'ARS'`             |                                           | plain         |
| `details`                     | JSONB               | sí   |                     | info no sensible (lote, cuotas, authCode) | plain         |
| `sensitive_details_encrypted` | TEXT                | sí   |                     | tokens/IDs de pasarela cifrados           | encrypted_app |
| `created_at`                  | TIMESTAMPTZ         | no   | `NOW()`             |                                           | plain         |

---

### 2.21. `budget`

Presupuestos que pueden convertirse en venta.

| columna           | tipo               | null | default             | notas / constraints                   | encrypt |
| ----------------- | ------------------ | ---- | ------------------- | ------------------------------------- | ------- |
| `id`              | UUID               | no   | `gen_random_uuid()` | PK                                    | plain   |
| `tenant_id`       | UUID               | no   |                     | FK → `tenant(id)` `ON DELETE CASCADE` | plain   |
| `customer_id`     | UUID               | sí   |                     | FK → `customer(id)`                   | plain   |
| `user_id`         | UUID               | sí   |                     | FK → `app_user(id)`                   | plain   |
| `total_estimated` | DECIMAL(17,3)      | no   | `0`                 |                                       | plain   |
| `valid_until`     | TIMESTAMPTZ        | sí   |                     |                                       | plain   |
| `status`          | budget_status_enum | no   |                     | OPEN / CONVERTED / EXPIRED            | plain   |
| `created_at`      | TIMESTAMPTZ        | no   | `NOW()`             |                                       | plain   |

---




