# REST API Design - Gravitea ERP

## 1. Metadatos del Documento
| Campo | Valor |
| --- | --- |
| **Owner** | Tech Lead |
| **Implementación** | Backend Team (Django + DRF) |
| **Versión** | 0.3 |
| **Last Updated** | 2026-03-01 |
| **Estado** | **Activo — 9 Contratos OpenAPI, 79 Paths, 137 Operaciones** |
| **Fuente autoritativa** | `api/openapi/*.yaml` (9 contratos generados por drf-spectacular) |
| **Relacionados** | PRD, Data Model & Domain Model, High-Level Design (HLD), Low-Level Design (LLD) |

## 2. Objetivo y Alcance

Este documento describe la **API REST** del backend de Gravitea ERP, implementada con **Django 5.2 + Django REST Framework (DRF)**. La especificación completa y autoritativa de cada endpoint (schemas, validaciones, ejemplos) se encuentra en los archivos OpenAPI YAML generados automáticamente:

### Contratos OpenAPI (Marzo 2026)

| Contrato | Módulo | Paths | Schemas | Acceso |
| --- | --- | --- | --- | --- |
| `auth-api.yaml` | AUTH | JWT, usuarios, roles, sucursales | Auth schemas | `GET /api/v1/schema/` |
| `inventario-api.yaml` | INVENTARIO | Productos, categorías, proveedores, stock | Inventory schemas | — |
| `ventas-api.yaml` | VENTAS | Clientes, órdenes de venta, ítems | Sales schemas | — |
| `facturacion-api.yaml` | FACTURACION | Comprobantes, CAE/CAEA, credenciales | ARCA schemas | — |
| `sync-api.yaml` | SYNC | Sesiones, push, pull | Sync schemas | — |
| `customization-api.yaml` | CUSTOMIZATION | Campos custom, module config | Config schemas | — |
| `compras-api.yaml` | COMPRAS | Órdenes de compra, proveedores | Purchase schemas | — |
| `core-api.yaml` | CORE | Field definitions, module config | Core schemas | — |
| `reportes-api.yaml` | REPORTES | Report defs, export jobs, saved reports | Report schemas | — |

**Total**: 9 contratos, **79 paths**, **154 schemas**, **137 operaciones** (generados por `drf-spectacular` + script de split por prefijo con resolución transitiva de schemas).

| Recurso | Acceso |
| --- | --- |
| Spec completa (OpenAPI 3.1.0) | `GET /api/v1/schema/` |
| Swagger UI | `GET /api/v1/schema/swagger-ui/` |
| ReDoc | `GET /api/v1/schema/redoc/` |

La API expone servicios para los siguientes módulos **implementados**:

- **AUTH** — JWT RS256, usuarios, roles, sucursales
- **INVENTARIO** — Productos, categorías, proveedores, listas de precios, stock
- **VENTAS** — Clientes, órdenes de venta, ítems
- **FACTURACION** — ARCA: comprobantes, CAE/CAEA, puntos de venta, credenciales
- **SYNC** — Sincronización offline-first: sesiones, push, pull
- **CUSTOMIZATION** — Definiciones de campos y configuración de módulos
- **COMPRAS** — Órdenes de compra, proveedores (parcial — workflow de órdenes pendiente)
- **CORE** — Field definitions, module config (infraestructura de personalización)
- **REPORTES** — Report definitions, export jobs, saved reports (definiciones de API; lógica pendiente)

> **Nota sobre aceleración Rust**: Varios endpoints utilizan internamente módulos Rust/PyO3 para procesamiento CPU-bound (SSRF validation en security.rs, IVA/CUIT validation en compute.rs, export CSV/XLSX en export.rs, field validation en validation.rs). Esto es transparente para el consumidor de la API — la interfaz REST es idéntica con o sin Rust.

> **Nota para desarrolladores**: Este documento describe la superficie de API a nivel de referencia rápida. Para schemas completos, reglas de validación, y ejemplos de request/response, consultar los archivos OpenAPI YAML generados por `drf-spectacular`.

## 3. Principios de Diseño de la API

- **RESTful pragmático**: recursos claros (`/products/`, `/ventas/orders/`, `/facturacion/comprobantes/`) con métodos HTTP estándar.
- **Versionado explícito**: todas las rutas bajo `/api/v1/` (v2+ sólo cuando haya cambios breaking).
- **JSON only**: `Content-Type: application/json` en requests/responses.
- **Stateless + multi-tenant**: el contexto de tenant, sucursal y usuario se determina por el token JWT.
- **Seguridad by default**: autenticación obligatoria salvo endpoints explícitamente públicos (`/health/`, `/metrics`).
- **Offline-friendly**: endpoints especiales para batch/sync (`/sync/push/`, `/sync/pull/`) con idempotencia via UUID de cliente.
- **Error estructurado**: todas las respuestas de error usan formato **Problem+JSON (RFC 9457)**.

## 4. Convenciones Globales

### 4.1 Base URL y Versionado

- Base URL: `https://{host}/api/v1/`
- Ejemplos:
  - `GET /api/v1/products/`
  - `POST /api/v1/ventas/orders/`
  - `POST /api/v1/sync/push/`

### 4.2 Autenticación

- Esquema: **JWT Bearer (RS256)**.
- Header requerido en todos los endpoints autenticados:

```http
Authorization: Bearer <access_token>
```

- El token JWT contiene claims personalizados: `tenant_id`, `branch_id`, `role_id`, `permissions`.
- Rotación de token: `POST /api/v1/auth/token/refresh/` (refresh token en body).
- Blacklisting: `POST /api/v1/auth/logout/` invalida el refresh token activo.

### 4.3 Formato de Errores — Problem+JSON (RFC 9457)

Todas las respuestas de error usan el formato **Problem+JSON** (RFC 7807/9457):

```http
HTTP/1.1 422 Unprocessable Entity
Content-Type: application/problem+json

{
  "type": "https://gravitea.com/errors/validation-error",
  "title": "Validation Error",
  "status": 422,
  "detail": "El campo 'imp_total' es requerido para emitir un comprobante.",
  "instance": "/api/v1/facturacion/comprobantes/",
  "errors": {
    "imp_total": ["Este campo es requerido."]
  }
}
```

Ejemplos de tipos de error:
- `validation-error` (422)
- `authentication-required` (401)
- `permission-denied` (403)
- `not-found` (404)
- `arca-rejection` (422) — rechazo fiscal de ARCA con `arca_observations` y `arca_errors`
- `tenant-isolation-violation` (403)

El manejador de excepciones `problem_detail_exception_handler` está configurado en DRF como handler global. Los schemas de error están enriquecidos en la spec OpenAPI vía `drf-spectacular` post-processing hooks.

### 4.4 Paginación, Orden y Filtros

- **Paginación cursor-based** (default global):
  - `StandardCursorPagination` con `PAGE_SIZE=100`.
  - Parámetros: `?cursor=<opaque_cursor>` (para navegación de página).
  - Respuesta incluye: `next`, `previous`, `results`.
  - Superior a offset-based para datasets en movimiento (consistencia en sincronización).
- **Orden**:
  - `?ordering=created_at` / `?ordering=-name`
- **Filtros**:
  - `DjangoFilterBackend` activo globalmente.
  - Filtros específicos por módulo (ej: `?status=DRAFT`, `?branch_id=...`).
- **Throttling**:
  - Anónimo: 100 req/hour.
  - Autenticado: 1000 req/hour.
  - Login: 3 niveles de rate limiting (5/min → 3/min → lockout 15 min).

## 5. Módulos y Recursos

### 5.1 AUTH — Autenticación y Gestión de Usuarios

**Base**: `/api/v1/auth/`

| Método | Path | Descripción |
| --- | --- | --- |
| POST | `/auth/token/` | Login con email/password. Devuelve access + refresh JWT. |
| POST | `/auth/token/refresh/` | Rotación de access token usando refresh token. |
| POST | `/auth/token/verify/` | Verifica validez del access token. |
| POST | `/auth/logout/` | Invalida (blacklist) el refresh token activo. |
| GET | `/auth/users/` | Lista usuarios del tenant. |
| POST | `/auth/users/` | Crear usuario. |
| GET | `/auth/users/{id}/` | Detalle de usuario. |
| PATCH | `/auth/users/{id}/` | Edición parcial de usuario. |
| DELETE | `/auth/users/{id}/` | Eliminar usuario. |
| GET | `/auth/users/me/` | Perfil del usuario autenticado (con claims JWT). |
| POST | `/auth/users/me/change-password/` | Cambiar contraseña del usuario actual. |
| GET | `/auth/roles/` | Lista de roles del tenant. |
| POST | `/auth/roles/` | Crear rol con permisos (`module.action`). |
| GET | `/auth/roles/{id}/` | Detalle de rol. |
| PATCH | `/auth/roles/{id}/` | Actualizar rol. |
| GET | `/auth/branches/` | Lista de sucursales (solo lectura). |
| GET | `/auth/branches/{id}/` | Detalle de sucursal. |

### 5.2 INVENTARIO — Productos y Stock

**Base**: `/api/v1/` (inventario no tiene prefijo propio)

| Método | Path | Descripción |
| --- | --- | --- |
| GET | `/products/` | Lista de productos con filtros y paginación. |
| POST | `/products/` | Alta de producto. |
| GET | `/products/{id}/` | Detalle de producto. |
| PUT/PATCH | `/products/{id}/` | Edición de producto. |
| DELETE | `/products/{id}/` | Eliminar producto (soft delete si aplica). |
| GET | `/products/{id}/stock/` | Stock actual del producto por sucursal. |
| GET | `/products/search/` | Búsqueda por barcode (índice ciego, descifrado). |
| GET | `/categories/` | Árbol de categorías. |
| POST | `/categories/` | Crear categoría. |
| GET | `/categories/{id}/` | Detalle. |
| PUT/PATCH | `/categories/{id}/` | Actualizar. |
| DELETE | `/categories/{id}/` | Eliminar. |
| GET | `/categories/tree/` | Árbol jerárquico completo. |
| GET | `/suppliers/` | Lista de proveedores. |
| POST | `/suppliers/` | Alta de proveedor (PII cifrada automáticamente). |
| GET | `/suppliers/{id}/` | Detalle. |
| PUT/PATCH | `/suppliers/{id}/` | Actualizar. |
| DELETE | `/suppliers/{id}/` | Eliminar. |
| GET | `/suppliers/search/` | Búsqueda por índice ciego (tax_id, email). |
| GET | `/price-lists/` | Listas de precios disponibles. |
| POST | `/price-lists/` | Crear lista de precios. |
| GET | `/price-lists/{id}/` | Detalle. |
| PUT/PATCH | `/price-lists/{id}/` | Actualizar. |
| DELETE | `/price-lists/{id}/` | Eliminar. |
| POST | `/price-lists/{id}/set-default/` | Marcar como lista default del tenant. |
| GET | `/movements/` | Lista de movimientos de stock (solo lectura). |
| POST | `/movements/` | Registrar movimiento (ledger inmutable). |
| GET | `/movements/{id}/` | Detalle de movimiento. |
| GET | `/price-history/` | Historial de precios (solo lectura). |
| GET | `/cost-history/` | Historial de costos (solo lectura). |

> **Nota**: `GET /movements/` y `POST /movements/` son los únicos métodos permitidos. No hay PUT/PATCH/DELETE (ledger inmutable).

### 5.3 COMPRAS — Estado Parcial

Solo el modelo `Supplier` está implementado (incluido en INVENTARIO). El workflow completo de órdenes de compra (`PurchaseOrder`, recepción de mercadería, factura de proveedor) es **Planificado — no implementado**.

### 5.4 VENTAS — Clientes y Órdenes de Venta

**Base**: `/api/v1/ventas/`

| Método | Path | Descripción |
| --- | --- | --- |
| GET | `/ventas/customers/` | Lista de clientes del tenant. |
| POST | `/ventas/customers/` | Alta de cliente (con CUIT, condición IVA). |
| GET | `/ventas/customers/{id}/` | Detalle de cliente. |
| PUT/PATCH | `/ventas/customers/{id}/` | Edición de cliente. |
| DELETE | `/ventas/customers/{id}/` | Soft delete de cliente. |
| GET | `/ventas/orders/` | Lista de órdenes de venta. |
| POST | `/ventas/orders/` | Crear orden de venta (estado DRAFT). |
| GET | `/ventas/orders/{id}/` | Detalle de orden. |
| PUT/PATCH | `/ventas/orders/{id}/` | Actualizar orden (solo en estado DRAFT). |
| DELETE | `/ventas/orders/{id}/` | Eliminar orden (solo en estado DRAFT). |
| POST | `/ventas/orders/{id}/confirm/` | Confirmar orden (DRAFT → CONFIRMED). |
| POST | `/ventas/orders/{id}/authorize/` | Autorizar orden. |
| POST | `/ventas/orders/{id}/invoice/` | Facturar orden (CONFIRMED → INVOICED, crea Comprobante). |
| GET | `/ventas/orders/{id}/items/` | Items de la orden. |
| POST | `/ventas/orders/{id}/items/` | Agregar item. |
| GET | `/ventas/orders/{id}/items/{item_id}/` | Detalle de item. |
| PUT/PATCH | `/ventas/orders/{id}/items/{item_id}/` | Actualizar item. |
| DELETE | `/ventas/orders/{id}/items/{item_id}/` | Eliminar item. |

**Ciclo de vida SaleOrder**: `DRAFT → CONFIRMED → INVOICED`
- `INVOICED` es estado terminal inmutable.
- Un `SaleOrder` en estado `INVOICED` tiene un `Comprobante` asociado (OneToOne).

### 5.5 FACTURACION — ARCA (ex-AFIP)

**Base**: `/api/v1/facturacion/`

| Método | Path | Descripción |
| --- | --- | --- |
| GET | `/facturacion/puntos-de-venta/` | Lista de puntos de venta activos. |
| POST | `/facturacion/puntos-de-venta/` | Crear punto de venta. |
| GET | `/facturacion/puntos-de-venta/{id}/` | Detalle. |
| PUT/PATCH | `/facturacion/puntos-de-venta/{id}/` | Actualizar. |
| GET | `/facturacion/credentials/` | Lista de credenciales ARCA. |
| POST | `/facturacion/credentials/` | Cargar credencial (certificado cifrado). |
| GET | `/facturacion/credentials/{id}/` | Detalle (sin exponer clave privada). |
| PUT/PATCH | `/facturacion/credentials/{id}/` | Actualizar credencial. |
| GET | `/facturacion/comprobantes/` | Lista de comprobantes. |
| POST | `/facturacion/comprobantes/` | Crear comprobante en estado DRAFT. |
| GET | `/facturacion/comprobantes/{id}/` | Detalle de comprobante. |
| POST | `/facturacion/comprobantes/{id}/emitir/` | Emitir comprobante vía WSAA/WSFEv1 (CAE online). |
| GET | `/facturacion/comprobantes/{id}/qr/` | Generar QR fiscal (para impresión). |
| POST | `/facturacion/comprobantes/{id}/authorize/` | Autorizar manualmente (flujo alternativo). |
| GET | `/facturacion/caeas/` | Lista de CAEA (autorización offline). |
| POST | `/facturacion/caeas/solicitar/` | Solicitar CAEA para período. |
| POST | `/facturacion/caeas/{id}/sin-movimiento/` | Informar CAEA sin movimiento. |

**Ciclo de vida Comprobante**: `DRAFT → AUTORIZADO | OBSERVADO | RECHAZADO`
- `AUTORIZADO` y `OBSERVADO` son **estados terminales inmutables** (compliance fiscal).
- El endpoint `/emitir/` invoca WSAA (autenticación) y WSFEv1 (emisión) en ARCA.
- Las respuestas de error fiscal usan Problem+JSON con campo `arca_observations` y `arca_errors`.

**Ejemplo de error ARCA (Problem+JSON)**:

```http
HTTP/1.1 422 Unprocessable Entity
Content-Type: application/problem+json

{
  "type": "https://gravitea.com/errors/arca-rejection",
  "title": "ARCA Rejection",
  "status": 422,
  "detail": "El comprobante fue rechazado por ARCA.",
  "instance": "/api/v1/facturacion/comprobantes/abc-123/emitir/",
  "arca_result": "R",
  "arca_observations": ["Obs 10016: El campo ImpTotal no coincide con la suma de conceptos."],
  "arca_errors": [{"code": "10016", "message": "..."}]
}
```

### 5.6 REPORTES — Contrato Definido, Lógica Pendiente

El módulo REPORTES tiene un contrato OpenAPI definido (`reportes-api.yaml`) con endpoints para report definitions, export jobs y saved reports. La lógica de negocio está pendiente de implementación. El motor de exportación CSV/XLSX está disponible via Rust (export.rs, spec 020).

### 5.7 SYNC — Sincronización Offline-First

**Base**: `/api/v1/sync/`

| Método | Path | Descripción |
| --- | --- | --- |
| GET | `/sync/sessions/` | Lista de sesiones de sincronización del tenant. |
| POST | `/sync/sessions/` | Crear sesión de dispositivo. |
| DELETE | `/sync/sessions/{id}/` | Eliminar sesión. |
| POST | `/sync/push/` | Batch push idempotente de operaciones del dispositivo. |
| GET | `/sync/pull/` | Pull cursor-based de cambios del servidor. |
| GET | `/sync/status/{device_id}/` | Estado del dispositivo: pendientes, conflictos. |

**Idempotencia**: el push usa UUIDs generados por el cliente para garantizar idempotencia.
**Conflictos**: operaciones conflictuadas quedan en estado `CONFLICTED` en `PendingOperation`.

### 5.8 CUSTOMIZATION — Campos y Configuración

**Base**: `/api/v1/`

| Método | Path | Descripción |
| --- | --- | --- |
| GET | `/field-definitions/` | Lista de definiciones de campos custom del tenant. |
| GET | `/field-definitions/{id}/` | Detalle de una definición. |
| GET | `/module-config/` | Configuración de módulos habilitados del tenant. |
| GET | `/module-config/{id}/` | Detalle de configuración de un módulo. |

Ambos endpoints son **solo lectura** (read-only ViewSets). La configuración se gestiona a nivel de administración del tenant.

## 6. Contratos y Esquemas — OpenAPI Autoritativo

Los contratos completos (request/response schemas, validaciones, enums, códigos de estado exactos) se encuentran en los 9 archivos OpenAPI generados por `drf-spectacular`:

```bash
# Generar schema monolítica
python manage.py spectacular --file api/openapi/schema.yaml

# Split por módulo (9 contratos)
python scripts/split_openapi.py api/openapi/schema.yaml api/openapi/

# Contratos individuales generados:
ls api/openapi/
# auth-api.yaml, inventario-api.yaml, ventas-api.yaml,
# facturacion-api.yaml, sync-api.yaml, customization-api.yaml,
# compras-api.yaml, core-api.yaml, reportes-api.yaml

# Acceso en desarrollo
GET /api/v1/schema/           # YAML
GET /api/v1/schema/swagger-ui/ # UI interactiva
GET /api/v1/schema/redoc/      # Documentación legible
```

**Configuración DRF relevante**:
- `DEFAULT_AUTHENTICATION_CLASSES`: `TenantAwareJWTAuthentication`
- `DEFAULT_PERMISSION_CLASSES`: `IsAuthenticated`
- `DEFAULT_PAGINATION_CLASS`: `StandardCursorPagination` (PAGE_SIZE=100)
- `DEFAULT_FILTER_BACKENDS`: `DjangoFilterBackend`
- `EXCEPTION_HANDLER`: `problem_detail_exception_handler` (RFC 9457)
- `COERCE_DECIMAL_TO_STRING`: `True` (campos Decimal se serializan como string para precisión)

## 7. Trazabilidad con Otros Documentos

- **Modelo de datos**: ver `Data Model & Domain Model.md` para la definición de entidades y relaciones.
- **Arquitectura**: ver `High-Level Design (HLD).md` y `Low-Level Design (LLD).md` para el contexto de despliegue.
- **Decisiones técnicas**: ver `Architecture Decision Records (ADR).md` — especialmente ADR-004 (RS256 JWT), ADR-005 (Ledger inmutable), ADR-009 (Problem+JSON), ADR-015 (Rust/PyO3 Acceleration Layer), ADR-016 (Vertical SaaS Pivot Research).
- **Workflow de desarrollo**: ver `Development Workflow.md` para guía de testing de endpoints.
- **Onboarding**: ver `Developer Onboarding Guide.md` para setup del entorno local y prueba de la API.
