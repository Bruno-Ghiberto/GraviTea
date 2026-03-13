# Sync API Schema Documentation

## Overview

This document describes the drf-spectacular schema definitions for the sync app's offline-first POS synchronization endpoints.

## Files Created/Modified

### Created Files

- **`backend/apps/sync/schema.py`**: Complete drf-spectacular schema definitions for all sync endpoints

### Modified Files

- **`backend/apps/sync/views.py`**: Applied schema decorators to all views and viewsets

## Schema Components

### RFC 7807 Error Response Serializers

The schema definitions include RFC 7807 compliant error response serializers:

- **`FieldErrorSerializer`**: Field-level validation errors
- **`ProblemDetailSerializer`**: Complete RFC 7807 error response format

These serializers integrate with the existing `apps.core.exceptions.problem_detail` module to provide consistent error documentation across the API.

### Response Serializers

- **`SyncPushResponseSerializer`**: Documents push operation responses with created/skipped/error counts
- **`SyncStatusResponseSerializer`**: Documents sync status endpoint responses

### OpenAPI Examples

Comprehensive examples for all endpoints:

#### Sync Session Management
- **`SYNC_SESSION_CREATE_EXAMPLE`**: Device registration request
- **`SYNC_SESSION_RESPONSE_EXAMPLE`**: Successful registration response
- **`ERROR_CONFLICT_EXAMPLE`**: Device already registered error

#### Push Operations
- **`SYNC_PUSH_REQUEST_EXAMPLE`**: Batch of offline operations
- **`SYNC_PUSH_RESPONSE_EXAMPLE`**: Successful push acceptance

#### Pull Operations
- **`SYNC_PULL_REQUEST_EXAMPLE`**: Request for server changes
- **`SYNC_PULL_RESPONSE_EXAMPLE`**: Server changes response with pagination

#### Status Monitoring
- **`SYNC_STATUS_RESPONSE_EXAMPLE`**: Current device sync status

#### Error Examples
- **`ERROR_VALIDATION_EXAMPLE`**: Validation error with field details
- **`ERROR_NOT_FOUND_EXAMPLE`**: Device not found error

## Schema Decorators Applied

### SyncSessionViewSet

Applied `@sync_session_viewset_schema` decorator documenting:

1. **`list`**: List all registered POS terminals
   - Returns sync sessions with status and branch info
   - Supports monitoring all devices

2. **`create`**: Register new POS terminal
   - Documents complete sync session lifecycle
   - Explains device_id uniqueness requirements
   - Provides onboarding workflow guidance

3. **`retrieve`**: Get session details
   - Documents sync vector state inspection
   - Explains status monitoring use cases

4. **`destroy`**: Unregister POS terminal
   - Warns about irreversible operation
   - Documents pending operation deletion

### SyncPushView

Applied `@sync_push_schema` decorator documenting:

- Batch operation submission from offline terminals
- Client-generated UUID idempotency mechanism
- Operation processing workflow (validate → queue → skip duplicates)
- Sync vector usage for state tracking
- Response format with detailed counts

### SyncPullView

Applied `@sync_pull_schema` decorator documenting:

- Server change retrieval since last sync
- Timestamp-based change detection
- Entity type filtering (Product, BranchStock, etc.)
- Cursor-based pagination for large changesets
- Pull process workflow

### SyncStatusView

Applied `@sync_status_schema` decorator documenting:

- Real-time sync health monitoring
- Status value meanings (pending/processing/completed/error)
- Monitoring recommendations and alert thresholds
- Pending operation and conflict detection

## Key Documentation Features

### Comprehensive Workflow Documentation

Each endpoint includes detailed workflow descriptions:

- **Sync Session Lifecycle**: Registration → Push → Pull → Monitor → Unregister
- **Operation Processing**: Validation → Idempotency check → Queue → Process
- **Pull Process**: Timestamp tracking → Change retrieval → Pagination → Update local DB

### Business Context

Documentation includes business-focused explanations:

- Why operations use client-generated UUIDs (offline idempotency)
- How sync vectors track client state per entity type
- When to poll status endpoint and alert thresholds
- Impact of device unregistration on pending operations

### Error Handling Guidance

All endpoints document:

- RFC 7807 error response formats
- Field-level validation error details
- Common error scenarios (device not found, already registered, etc.)
- Authentication requirements

### Operational Recommendations

Status endpoint includes monitoring guidance:

- Poll interval recommendations (5-10 minutes during business hours)
- Alert thresholds (pending operations, conflict detection)
- Status value interpretation for operations teams

## API Documentation Tags

All endpoints organized under consistent tags:

- **Sync Management**: Session registration and lifecycle management
- **Sync Operations**: Push, pull, and status monitoring

## Response Documentation

### Success Responses

Each endpoint documents:
- HTTP status codes (200, 201, 204)
- Response body structure and field meanings
- Example responses with realistic data

### Error Responses

Each endpoint documents:
- RFC 7807 error format compliance
- Field-level validation errors (400)
- Authentication errors (401)
- Not found errors (404)
- Example error responses

## Integration Notes

### Core Module Integration

The schema definitions integrate with:
- `apps.core.exceptions.problem_detail.ProblemDetail`: RFC 7807 error responses
- `apps.core.exceptions.problem_detail.FieldError`: Field-level validation errors

### Serializer Reuse

Schema definitions reference existing serializers:
- `SyncSessionSerializer`, `SyncSessionCreateSerializer`
- `SyncPushSerializer`, `SyncPullSerializer`
- `SyncPullResponseSerializer`
- `PendingOperationSerializer`, `PendingOperationCreateSerializer`

## Testing the Schema

To verify the schema is correctly applied:

```bash
# Generate OpenAPI schema
python manage.py spectacular --file schema.yaml

# Check for sync endpoints
grep -A 10 "/api/v1/sync" schema.yaml

# Verify error response schemas
grep -A 5 "ProblemDetail" schema.yaml
```

## Next Steps

1. **Review Generated Schema**: Inspect the OpenAPI schema output for completeness
2. **Test API Documentation**: Verify documentation renders correctly in Swagger UI
3. **Validate Examples**: Ensure all examples match actual API behavior
4. **Update Frontend**: Use generated TypeScript types for sync API integration

## Related Documentation

- **FR-001 to FR-006**: RFC 7807 error response requirements (spec.md)
- **H-003**: Retry logic for transient database errors (architecture decision)
- **Sync App README**: Offline-first synchronization architecture overview
