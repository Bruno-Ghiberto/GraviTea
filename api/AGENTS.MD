# GRAVITEA API Specifications - AI Agent Ruleset

> **Skills Reference**: For detailed patterns, use these skills:
> - [`gravitea-auth`](../skills/gravitea-auth/SKILL.md) - JWT authentication endpoints
> - [`gravitea-tenant`](../skills/gravitea-tenant/SKILL.md) - Multi-tenant API design
> - [`django-expert`](../skills/django-expert/SKILL.md) - DRF serializer patterns

### Auto-invoke Skills

When performing these actions, ALWAYS invoke the corresponding skill FIRST:

| Action | Skill |
|--------|-------|
| Creating/modifying OpenAPI specs | Review existing contracts first |
| Adding authentication endpoints | `gravitea-auth` |
| Adding tenant-scoped resources | `gravitea-tenant` |
| Defining request/response schemas | `django-expert` |

---

## CRITICAL RULES - NON-NEGOTIABLE

### OpenAPI Specifications

- ALWAYS: OpenAPI 3.1 format
- ALWAYS: Version in file name: `<module>-api.yaml`
- ALWAYS: Include `securitySchemes` with JWT Bearer
- ALWAYS: Document all error responses (400, 401, 403, 404, 500)
- NEVER: Publish specs without corresponding backend implementation
- NEVER: Include sensitive data examples in specs

### ID Format

- ALWAYS: UUID v4 for all resource IDs
- ALWAYS: Represent as `string` type with `format: uuid`
- NEVER: Integer IDs for business entities

### Monetary Values

- ALWAYS: `type: string` for monetary values (precision preservation)
- ALWAYS: Document as DECIMAL(17,3) in description
- NEVER: `type: number` for financial data (floating point issues)

### Dates and Times

- ALWAYS: ISO 8601 format with timezone
- ALWAYS: `format: date-time` in OpenAPI
- ALWAYS: UTC timezone (`Z` suffix)
- Example: `"2026-01-20T15:30:00Z"`

### Pagination

- ALWAYS: Cursor-based pagination for list endpoints
- ALWAYS: Include `next`, `previous`, `results` fields
- ALWAYS: Default page size: 20 items
- NEVER: Offset-based pagination (performance issues at scale)

---

## DECISION TREES

### New Endpoint Design

```
Adding new endpoint?
|-- Is it tenant-scoped?
|   |-- Yes -> Require JWT auth, auto-filter by tenant_id
|   +-- No -> System endpoint (rare, needs justification)
|
|-- What HTTP method?
|   |-- GET single -> 200 OK, 404 Not Found
|   |-- GET list -> 200 OK with pagination
|   |-- POST create -> 201 Created, 400 Validation Error
|   |-- PATCH update -> 200 OK, 400/404
|   |-- DELETE -> 204 No Content, 404
```

### Schema Reuse

```
Defining response schema?
|-- Used by multiple endpoints?
|   |-- Yes -> Define in components/schemas
|   +-- No -> Define inline (keep spec readable)
|
|-- Has nested objects?
|   |-- Yes -> Create separate schema, use $ref
|   +-- No -> Inline properties
```

---

## PROJECT STRUCTURE

```
api/
├── openapi/
│   ├── README.md              # API documentation guide
│   ├── auth-api.yaml          # Authentication API
│   ├── compras-api.yaml       # Procurement (Compras) API
│   ├── core-api.yaml          # Core Configuration API (field-definitions, module-config)
│   ├── facturacion-api.yaml   # Electronic Invoicing (ARCA) API
│   ├── health-api.yaml        # Health Check API
│   ├── inventario-api.yaml    # Inventory API
│   ├── reportes-api.yaml      # Reports API (definitions, export-jobs, saved-reports)
│   ├── sync-api.yaml          # Sync API (offline-first)
│   └── ventas-api.yaml        # Sales (Ventas) API
└── AGENTS.MD                  # This file
```

---

## CONTRACT STATUS

All contracts auto-generated from Django DRF Spectacular (2026-02-28).
Source of truth: backend Python views and serializers.

| Contract | Paths | Operations | Schemas | Lines | Status |
|----------|-------|------------|---------|-------|--------|
| **auth-api.yaml** | 12 | 21 | 18 | 1,427 | Production |
| **compras-api.yaml** | 10 | 18 | 17 | 1,192 | Production |
| **core-api.yaml** | 4 | 4 | 7 | 397 | Production |
| **facturacion-api.yaml** | 13 | 21 | 29 | 2,685 | Production |
| **health-api.yaml** | 4 | 4 | 3 | 321 | Production |
| **inventario-api.yaml** | 16 | 29 | 36 | 3,182 | Production |
| **reportes-api.yaml** | 6 | 13 | 13 | 919 | Production |
| **sync-api.yaml** | 5 | 7 | 10 | 839 | Production |
| **ventas-api.yaml** | 9 | 20 | 21 | 2,379 | Production |
| **TOTAL** | **79** | **137** | **154** | **13,341** | |

Regenerate: `DJANGO_SETTINGS_MODULE=gravitea.settings.development venv-wsl/bin/python manage.py spectacular --file /tmp/full.yaml`

---

## API BASE URLS

```
Development:  http://localhost:8000/api/v1/
Production:   https://api.gravitea.app/api/v1/

Swagger UI:   http://localhost:8000/api/v1/schema/swagger-ui/
ReDoc:        http://localhost:8000/api/v1/schema/redoc/
Raw Schema:   http://localhost:8000/api/v1/schema/
```

---

## OPENAPI TEMPLATE

When creating new API specifications, follow this structure:

```yaml
openapi: 3.1.0
info:
  title: Gravitea <Module> API
  version: 1.0.0
  description: |
    <Module description>

    ## Authentication
    All endpoints require JWT Bearer authentication.

    ## Multi-Tenant
    Resources are automatically filtered by tenant_id from JWT claims.

servers:
  - url: http://localhost:8000/api/v1
    description: Development
  - url: https://api.gravitea.app/api/v1
    description: Production

security:
  - bearerAuth: []

components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT

  schemas:
    Error:
      type: object
      properties:
        detail:
          type: string
        code:
          type: string

    PaginatedResponse:
      type: object
      properties:
        next:
          type: string
          nullable: true
        previous:
          type: string
          nullable: true
        results:
          type: array
          items: {}

paths:
  /resource/:
    get:
      summary: List resources
      operationId: listResources
      tags:
        - Resources
      responses:
        '200':
          description: Successful response
        '401':
          description: Unauthorized
```

---

## RESPONSE CONVENTIONS

### Success Responses

```yaml
# Single resource
200 OK:
  {
    "id": "uuid",
    "name": "Resource Name",
    "created_at": "2026-01-20T15:30:00Z"
  }

# List with pagination
200 OK:
  {
    "next": "?cursor=abc123",
    "previous": null,
    "results": [...]
  }

# Create
201 Created:
  {
    "id": "new-uuid",
    ...
  }

# Delete
204 No Content
```

### Error Responses

```yaml
# Validation error
400 Bad Request:
  {
    "detail": "Validation error",
    "errors": {
      "field_name": ["Error message"]
    }
  }

# Authentication required
401 Unauthorized:
  {
    "detail": "Authentication credentials were not provided.",
    "code": "not_authenticated"
  }

# Permission denied
403 Forbidden:
  {
    "detail": "You do not have permission to perform this action.",
    "code": "permission_denied"
  }

# Resource not found (also used for IDOR - never reveal existence)
404 Not Found:
  {
    "detail": "Not found.",
    "code": "not_found"
  }
```

---

## SECURITY REQUIREMENTS

### All Endpoints Must

1. **Require Authentication**: `security: [bearerAuth: []]`
2. **Validate Tenant Context**: Auto-filter by JWT `tenant_id` claim
3. **Return Generic Errors**: Never reveal tenant mismatch details
4. **Document Error Codes**: All possible error responses

### Never Include

- Sensitive data in examples (real emails, tokens)
- Internal error details in responses
- Stack traces in production responses
- Tenant-identifying information in errors

---

## QA CHECKLIST

Before committing OpenAPI changes:

- [ ] OpenAPI 3.1 validation passes
- [ ] All endpoints have authentication requirement
- [ ] All error responses documented
- [ ] No sensitive data in examples
- [ ] Monetary values are strings (not numbers)
- [ ] IDs are UUID format
- [ ] Dates are ISO 8601 with timezone
- [ ] Pagination follows cursor-based pattern
- [ ] Backend implementation exists for all endpoints
- [ ] Swagger UI renders correctly

---

## COMMANDS

```bash
# Validate OpenAPI spec
npx @redocly/cli lint api/openapi/auth-api.yaml

# Generate client SDK (future)
npx openapi-generator-cli generate -i api/openapi/auth-api.yaml -g typescript-fetch -o generated/

# View live documentation
# Start backend: cd backend && python manage.py runserver
# Open: http://localhost:8000/api/v1/schema/swagger-ui/
```

---

## RELATED DOCUMENTS

- **REST API Design**: See `Docs/Project Blueprint/REST API Design.md`
- **Backend Implementation**: See `backend/apps/` for Django code
- **Data Model**: See `Docs/Project Blueprint/Data Model & Domain Model.md`

---

*Last updated: 2026-02-28*
*Total Paths: 79 | Total Operations: 137 | Modules: 9*
