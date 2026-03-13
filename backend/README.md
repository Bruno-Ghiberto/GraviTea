# GRAVITEA-ERP Backend

Django 5.2 + DRF backend for the GRAVITEA multi-tenant ERP system with offline-first POS synchronization.

## Quick Start

```bash
# Clone and navigate
cd backend

# Start all services (PostgreSQL, Redis, Django)
docker compose up -d

# Verify health
curl http://localhost:8000/health/live
```

For detailed Docker setup instructions, see [claudedocs/DOCKER_SETUP.md](claudedocs/DOCKER_SETUP.md).

---

## Architecture Overview

```mermaid
graph TB
    subgraph "Client Layer"
        FE[Frontend SPA]
        POS[POS Terminal]
    end

    subgraph "API Gateway"
        DRF[Django REST Framework]
        JWT[JWT RS256 Auth]
        RLS[PostgreSQL RLS]
    end

    subgraph "Application Layer"
        AUTH[apps.auth]
        INV[apps.inventario]
        VENTAS[apps.ventas]
        FACT[apps.facturacion]
        SYNC[apps.sync]
        CORE[apps.core]
    end

    subgraph "Data Layer"
        PG[(PostgreSQL 16)]
        REDIS[(Redis 7)]
    end

    subgraph "Observability"
        PROM[Prometheus]
        OTEL[OpenTelemetry]
        STRUCT[Structured Logging]
    end

    FE --> DRF
    POS --> DRF
    DRF --> JWT
    JWT --> RLS
    RLS --> AUTH
    RLS --> INV
    RLS --> VENTAS
    RLS --> FACT
    RLS --> SYNC
    AUTH --> CORE
    INV --> CORE
    VENTAS --> CORE
    VENTAS --> INV
    FACT --> CORE
    FACT --> VENTAS
    SYNC --> CORE
    CORE --> PG
    CORE --> REDIS
    DRF --> PROM
    DRF --> OTEL
    DRF --> STRUCT
```

---

## Application Modules

### `apps.core` - Foundation Layer

The core module provides shared infrastructure for all other modules.

| Component | Status | Description |
|-----------|--------|-------------|
| **Multi-Tenant Models** | ✅ Complete | `Tenant`, `Branch` with RLS isolation |
| **TenantBoundModel** | ✅ Complete | Base mixin enforcing tenant context |
| **TenantBoundManager** | ✅ Complete | QuerySet auto-filtering by tenant |
| **Field-Level Encryption** | ✅ Complete | AES-256-GCM with HMAC-SHA256 blind indexes |
| **Observability** | ✅ Complete | Prometheus metrics, OpenTelemetry tracing |
| **Health Checks** | ✅ Complete | `/health/live`, `/health/ready`, `/health/startup` |
| **Exception Handling** | ✅ Complete | RFC 7807 Problem Details responses |
| **Pagination** | ✅ Complete | Cursor-based pagination (100 default, 500 max) |

**Key Files:**
- `models/tenant.py` - Tenant and Branch models
- `models/mixins.py` - TenantBoundModel base class
- `managers/tenant_manager.py` - Auto-filtered QuerySets
- `encryption/fields.py` - EncryptedCharField, BlindIndexField
- `observability/` - Metrics, tracing, logging configuration

---

### `apps.auth` - Authentication & Authorization

JWT-based authentication with RS256 asymmetric signing.

| Component | Status | Description |
|-----------|--------|-------------|
| **JWT Token Endpoints** | ✅ Complete | Obtain, refresh, verify, logout |
| **User Management** | ✅ Complete | CRUD, password change, profile |
| **Role-Based Access** | ✅ Complete | Roles with permission assignments |
| **Branch Assignment** | ✅ Complete | Users assigned to tenant branches |
| **Token Blacklisting** | ✅ Complete | Refresh token revocation |
| **Rate Limiting** | ✅ Complete | 100/hr anonymous, 1000/hr authenticated |

**API Endpoints:**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/token/` | POST | Obtain JWT token pair |
| `/api/v1/auth/token/refresh/` | POST | Refresh access token |
| `/api/v1/auth/token/verify/` | POST | Verify token validity |
| `/api/v1/auth/logout/` | POST | Revoke refresh token |
| `/api/v1/auth/users/` | GET/POST | List/create users |
| `/api/v1/auth/users/{id}/` | GET/PUT/DELETE | User CRUD |
| `/api/v1/auth/users/me/` | GET/PUT | Current user profile |
| `/api/v1/auth/roles/` | GET/POST | Role management |
| `/api/v1/auth/branches/` | GET | List tenant branches |

**JWT Claims Structure:**
```json
{
  "sub": "user-uuid",
  "tenant_id": "tenant-uuid",
  "branch_id": "branch-uuid",
  "role": "admin",
  "permissions": ["products.read", "products.write"],
  "exp": 1234567890,
  "iat": 1234567890
}
```

---

### `apps.inventario` - Inventory Management

Product catalog with immutable stock movement ledger.

| Component | Status | Description |
|-----------|--------|-------------|
| **Product Catalog** | ✅ Complete | CRUD with encrypted barcodes |
| **Categories** | ✅ Complete | Hierarchical tree structure |
| **Suppliers** | ✅ Complete | Encrypted PII (AES-256-GCM) |
| **Stock Movements** | ✅ Complete | Immutable append-only ledger |
| **Stock Snapshots** | ✅ Complete | Current stock levels per branch |
| **Price Lists** | ✅ Complete | Multiple price lists per tenant |
| **Price/Cost History** | ✅ Complete | SCD Type 2 temporal tracking |

**API Endpoints:**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/inventory/products/` | GET/POST | Product catalog |
| `/api/v1/inventory/products/{id}/` | GET/PUT/DELETE | Product CRUD |
| `/api/v1/inventory/products/search-barcode/` | POST | Encrypted barcode search |
| `/api/v1/inventory/categories/` | GET/POST | Category management |
| `/api/v1/inventory/categories/tree/` | GET | Hierarchical tree view |
| `/api/v1/inventory/suppliers/` | GET/POST | Supplier management |
| `/api/v1/inventory/stock-movements/` | GET/POST | **Immutable** stock ledger |
| `/api/v1/inventory/stock-snapshots/` | GET | Current stock levels |
| `/api/v1/inventory/price-lists/` | GET/POST | Price list management |

**Critical Pattern - Immutable Stock Movements:**

Stock movements are **append-only**. No PUT, PATCH, or DELETE allowed.

```
Movement Types: SALE, PURCHASE, ADJ, TRANS_IN, TRANS_OUT

Corrections:
  ❌ Never modify existing movement
  ✅ Create reversal movement with negative quantity_delta
```

**Monetary Values:**

All money fields use `DECIMAL(17,3)` precision, serialized as strings:
```json
{
  "unit_price": "99.990",
  "cost_price": "49.995",
  "tax_rate": "21.00"
}
```

---

### `apps.ventas` - Sales Management

Customer management and sale order lifecycle with invoice integration.

| Component | Status | Description |
|-----------|--------|-------------|
| **Customer Registry** | ✅ Complete | CUIT-validated customers with fiscal conditions |
| **Sale Orders** | ✅ Complete | DRAFT → CONFIRMED → INVOICED lifecycle |
| **Order Items** | ✅ Complete | Price snapshots, auto-calculated IVA |
| **Invoice Integration** | ✅ Complete | ARCA authorization via facturacion module |
| **Stock Reservation** | ✅ Complete | Deducts stock on confirmation |

**API Endpoints:**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/ventas/customers/` | GET/POST | Customer registry |
| `/api/v1/ventas/customers/{id}/` | GET/PUT/PATCH | Customer CRUD |
| `/api/v1/ventas/customers/{id}/deactivate/` | POST | Soft-delete customer |
| `/api/v1/ventas/orders/` | GET/POST | Sale order management |
| `/api/v1/ventas/orders/{id}/` | GET/PUT/PATCH/DELETE | Order CRUD (DRAFT only) |
| `/api/v1/ventas/orders/{id}/confirm/` | POST | Confirm order, deduct stock |
| `/api/v1/ventas/orders/{id}/authorize/` | POST | ARCA authorization (CAE) |
| `/api/v1/ventas/orders/{id}/invoice/` | GET | Linked invoice details |
| `/api/v1/ventas/orders/{id}/items/` | GET/POST | Order line items |
| `/api/v1/ventas/orders/{id}/items/{item_id}/` | GET/PUT/DELETE | Item CRUD |

**Sale Order Lifecycle:**
```
DRAFT → CONFIRMED → INVOICED
  │         │
  │         └── authorize → Creates Comprobante + CAE
  │
  └── Fully editable (items, customer, data)
```

---

### `apps.facturacion` - Electronic Invoicing (ARCA)

Argentine electronic invoicing via ARCA (ex-AFIP) with WSAA authentication and WSFEv1 integration.

| Component | Status | Description |
|-----------|--------|-------------|
| **WSAA Authentication** | ✅ Complete | Certificate-based auth, token caching |
| **WSFEv1 Integration** | ✅ Complete | CAE request, last-authorized query |
| **Comprobante Types** | ✅ Complete | Factura A/B/C, Nota de Credito/Debito |
| **Amount Validation** | ✅ Complete | ARCA equation: neto + IVA + tributos = total |
| **Fiscal QR Codes** | ✅ Complete | ARCA-compliant QR generation |
| **Punto de Venta** | ✅ Complete | POS number management |
| **ARCA Credentials** | ✅ Complete | Multi-tenant certificate storage |

**API Endpoints:**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/facturacion/comprobantes/` | GET/POST | Invoice registry |
| `/api/v1/facturacion/comprobantes/{id}/` | GET | Invoice detail |
| `/api/v1/facturacion/comprobantes/{id}/authorize/` | POST | Request CAE from ARCA |
| `/api/v1/facturacion/punto-de-venta/` | GET/POST | POS management |
| `/api/v1/facturacion/credentials/` | GET/POST | ARCA credential management |
| `/api/v1/facturacion/health/` | GET | ARCA connectivity check |

---

### `apps.sync` - Offline-First Synchronization

POS terminal synchronization with vector clock conflict resolution.

| Component | Status | Description |
|-----------|--------|-------------|
| **Device Registration** | ✅ Complete | Register POS terminals |
| **Push Operations** | ✅ Complete | Upload offline changes |
| **Pull Operations** | ✅ Complete | Download server changes |
| **Conflict Detection** | ✅ Complete | Vector clock comparison |
| **Conflict Resolution** | ✅ Complete | LWW and custom strategies |
| **Sync Sessions** | ✅ Complete | Transaction boundaries |

**API Endpoints:**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/sync/sessions/` | POST | Start sync session |
| `/api/v1/sync/sessions/{id}/` | GET | Session status |
| `/api/v1/sync/push/` | POST | Upload offline changes |
| `/api/v1/sync/pull/` | GET | Download server changes |

**Sync Flow:**
```mermaid
sequenceDiagram
    participant POS as POS Terminal
    participant API as Sync API
    participant DB as Database

    POS->>API: POST /sync/sessions/ (device_id)
    API->>DB: Create sync session
    API-->>POS: session_id, vector_clock

    POS->>API: POST /sync/push/ (changes[])
    API->>DB: Apply changes, detect conflicts
    API-->>POS: applied, conflicts[]

    POS->>API: GET /sync/pull/ (last_sync_at)
    API->>DB: Query changes since
    API-->>POS: changes[], new_vector_clock
```

---

## Security Architecture

### Defense in Depth

```mermaid
graph LR
    subgraph "Layer 1: API"
        RL[Rate Limiting]
        JWT[JWT Validation]
    end

    subgraph "Layer 2: Application"
        TM[TenantBoundManager]
        IDOR[IDOR Prevention]
    end

    subgraph "Layer 3: Database"
        RLS[PostgreSQL RLS]
        ENC[Field Encryption]
    end

    RL --> JWT --> TM --> IDOR --> RLS --> ENC
```

### Tenant Isolation

1. **JWT Claims**: `tenant_id` embedded in every token
2. **TenantBoundManager**: Auto-filters all queries by tenant
3. **PostgreSQL RLS**: Row-level security as final defense
4. **IDOR Prevention**: Validates all FK references within tenant

### Field-Level Encryption

Sensitive PII encrypted at rest using AES-256-GCM:

| Field | Model | Encryption |
|-------|-------|------------|
| `barcode` | Product | AES-256-GCM + HMAC blind index |
| `tax_id` | Supplier | AES-256-GCM |
| `phone` | Supplier | AES-256-GCM |
| `email` | Supplier | AES-256-GCM |
| `contact_person` | Supplier | AES-256-GCM |

---

## Development Status

### Completed Features ✅

- [x] Multi-tenant architecture with PostgreSQL RLS
- [x] JWT RS256 authentication with 15min/7-day tokens
- [x] User and role management with permissions
- [x] Product catalog with encrypted barcodes
- [x] Hierarchical category tree
- [x] Supplier management with encrypted PII
- [x] Immutable stock movement ledger
- [x] Stock snapshot materialization
- [x] Price lists and price/cost history (SCD Type 2)
- [x] Offline-first POS synchronization
- [x] Vector clock conflict detection
- [x] Prometheus metrics and OpenTelemetry tracing
- [x] Health check endpoints
- [x] RFC 7807 error responses
- [x] Cursor-based pagination
- [x] Docker development environment
- [x] 80%+ test coverage (1713 tests)

- [x] Sales module with order lifecycle (DRAFT → CONFIRMED → INVOICED)
- [x] Customer registry with CUIT Modulo-11 validation
- [x] ARCA electronic invoicing (WSAA + WSFEv1 + CAE)
- [x] Fiscal QR code generation
- [x] Sale-to-invoice integration pipeline

### In Progress 🔄

- [ ] Fiscal printing integration
- [ ] Advanced reporting and analytics
- [ ] Webhook notifications

### Planned 📋

- [ ] Multi-currency support
- [ ] Barcode scanning API
- [ ] Batch import/export
- [ ] Audit log dashboard

---

## Testing

```bash
# Run all tests with Docker infrastructure
python tests/run_tests.py

# Run specific markers
pytest -m "unit"
pytest -m "integration"
pytest -m "security"

# Run with coverage
pytest --cov=apps --cov-report=html
```

**Test Results (Latest Run):**
| Metric | Value |
|--------|-------|
| Tests Collected | 1,713 |
| Tests Passed | 1,675 |
| Tests Skipped | 38 |
| Tests Failed | 0 |
| Coverage | 80.13% |

See [tests/README.md](tests/README.md) for detailed test documentation.

---

## Configuration

### Environment Variables

```bash
# Core
DJANGO_SECRET_KEY=your-secret-key
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=postgres://user:pass@localhost:5432/gravitea

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_PRIVATE_KEY_PATH=/path/to/private.pem
JWT_PUBLIC_KEY_PATH=/path/to/public.pem

# Encryption
FIELD_ENCRYPTION_KEY=base64-encoded-32-byte-key
BLIND_INDEX_KEY=base64-encoded-32-byte-key

# Observability
OTEL_SERVICE_NAME=gravitea-backend
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

See `.env.example` for complete variable list.

---

## Directory Structure

```
backend/
├── apps/
│   ├── auth/           # Authentication & authorization
│   ├── core/           # Shared infrastructure
│   │   ├── encryption/ # AES-256-GCM field encryption
│   │   ├── health/     # Health check endpoints
│   │   ├── managers/   # TenantBoundManager
│   │   ├── models/     # Tenant, Branch, mixins
│   │   └── observability/  # Metrics, tracing, logging
│   ├── inventario/     # Inventory management
│   ├── ventas/         # Sales management
│   ├── facturacion/    # ARCA electronic invoicing
│   └── sync/           # Offline synchronization
├── gravitea/           # Django project settings
├── observability/      # Prometheus, Grafana configs
├── requirements/       # Pip requirements files
├── scripts/            # Utility scripts
├── tests/              # Test suite
├── docker-compose.yml  # Development stack
└── Makefile            # Common commands
```

---

## API Documentation

- **OpenAPI Specs**: See [api/openapi/README.md](../api/openapi/README.md)
- **Auth API**: [api/openapi/auth-api.yaml](../api/openapi/auth-api.yaml)
- **Inventory API**: [api/openapi/inventory-api.yaml](../api/openapi/inventory-api.yaml)
- **Sync API**: [api/openapi/sync-api.yaml](../api/openapi/sync-api.yaml)

---

## Related Documentation

- [Docker Setup Guide](claudedocs/DOCKER_SETUP.md)
- [Testing Guide](tests/README.md)
- [Security Guide](apps/core/SECURITY.md)
- [Sync Logging](apps/sync/LOGGING.md)

---

*Last Updated: February 2026*
*Django 5.2 | Python 3.14.3 | PostgreSQL 18.1 | Redis 7*
