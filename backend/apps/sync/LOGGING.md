# Sync Operation Logging - SC-022 Compliance

## Overview

Comprehensive structured logging for all sync operations in Gravitea ERP. All logs are JSON-formatted with full context for audit trails, troubleshooting, and compliance.

## Log Configuration

Add to Django settings:

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            'format': '%(message)s'
        },
    },
    'handlers': {
        'sync_file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/sync.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
            'formatter': 'json',
        },
    },
    'loggers': {
        'sync': {
            'handlers': ['sync_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
```

## Event Types

### Push Operations
- `SYNC_PUSH_START`: Push operation initiated
- `SYNC_PUSH_COMPLETE`: Push completed successfully
- `SYNC_PUSH_FAILED`: Push operation failed

### Pull Operations
- `SYNC_PULL_START`: Pull operation initiated
- `SYNC_PULL_COMPLETE`: Pull completed successfully
- `SYNC_PULL_FAILED`: Pull operation failed

### Operation Processing
- `SYNC_OPERATION_APPLIED`: Operation successfully applied
- `SYNC_OPERATION_REJECTED`: Operation rejected (validation failed)
- `SYNC_OPERATION_SKIPPED`: Operation skipped (idempotency)
- `SYNC_OPERATION_FAILED`: Operation processing failed

### Conflict Handling
- `SYNC_CONFLICT_DETECTED`: Conflict detected, resolution required
- `SYNC_CONFLICT_RESOLVED`: Conflict successfully resolved
- `SYNC_CONFLICT_FAILED`: Conflict resolution failed

### Retry Handling
- `SYNC_RETRY_ATTEMPT`: Retry attempt in progress
- `SYNC_RETRY_EXHAUSTED`: All retry attempts exhausted
- `SYNC_RETRY_SUCCESS`: Retry succeeded

## Log Entry Structure

All log entries follow this JSON structure:

```json
{
  "timestamp": "2024-01-15T14:05:00.123456Z",
  "event_type": "SYNC_PUSH_COMPLETE",
  "severity": "INFO",
  "message": "Sync push complete: device=POS-001, applied=4/5",
  "tenant_id": "uuid-string",
  "device_id": "POS-001",
  "operation_count": 5,
  "operations_applied": 4,
  "operations_skipped": 1,
  "operations_rejected": 0,
  "conflicts_detected": 0,
  "duration_ms": 250.5,
  "session_id": "uuid-string",
  "success_rate": 80.0
}
```

## Severity Levels

- **ERROR**: Operation failures, sync failures, exhausted retries
- **WARNING**: Conflicts detected, operations rejected, retries in progress
- **INFO**: Successful operations, conflict resolutions, push/pull completion
- **DEBUG**: Individual operation processing, detailed tracking

## Usage Examples

### Push Operation Logging

```python
from apps.sync.logging import SyncLogger

# At start of push
SyncLogger.log_sync_push_start(
    tenant_id=tenant.id,
    device_id='POS-001',
    operation_count=5,
    user_id=user.id,
    session_id=session.id,
    request_ip='192.168.1.100',
)

# After processing operations
SyncLogger.log_sync_push_complete(
    tenant_id=tenant.id,
    device_id='POS-001',
    operations_count=5,
    operations_applied=4,
    operations_skipped=1,
    operations_rejected=0,
    conflicts_detected=0,
    duration_ms=250.5,
    session_id=session.id,
)

# On failure
SyncLogger.log_sync_push_failed(
    tenant_id=tenant.id,
    device_id='POS-001',
    error='Database connection timeout',
    operation_count=5,
    operations_processed=3,
    session_id=session.id,
    error_code='DB_TIMEOUT',
)
```

### Pull Operation Logging

```python
# At start of pull
SyncLogger.log_sync_pull_start(
    tenant_id=tenant.id,
    device_id='POS-001',
    since_timestamp=last_sync,
    entity_types=['Product', 'Sale'],
    user_id=user.id,
    session_id=session.id,
    request_ip='192.168.1.100',
)

# After pulling changes
SyncLogger.log_sync_pull_complete(
    tenant_id=tenant.id,
    device_id='POS-001',
    changes_count=15,
    entity_breakdown={'Product': 10, 'Sale': 5},
    duration_ms=150.2,
    has_more=False,
    session_id=session.id,
)
```

### Operation Processing Logging

```python
# Operation applied successfully
SyncLogger.log_operation_applied(
    operation_id=operation.id,
    entity_type='Product',
    operation_type='CREATE',
    entity_id='prod-123',
    tenant_id=tenant.id,
    device_id='POS-001',
    processing_time_ms=10.5,
)

# Operation rejected
SyncLogger.log_operation_rejected(
    operation_id=operation.id,
    entity_type='Sale',
    operation_type='DELETE',
    reason='Sales cannot be deleted',
    tenant_id=tenant.id,
    device_id='POS-001',
    validation_errors={'operation': 'DELETE not allowed'},
)

# Operation skipped (idempotency)
SyncLogger.log_operation_skipped(
    operation_id=operation.id,
    entity_type='Product',
    reason='already_exists',
    tenant_id=tenant.id,
    device_id='POS-001',
)

# Operation failed
SyncLogger.log_operation_failed(
    operation_id=operation.id,
    entity_type='StockMovement',
    error='Insufficient stock quantity',
    tenant_id=tenant.id,
    device_id='POS-001',
    retry_count=1,
    will_retry=True,
)
```

### Conflict Resolution Logging

```python
# Conflict detected
SyncLogger.log_conflict_detected(
    operation_id=operation.id,
    entity_type='Product',
    entity_id='prod-123',
    resolution_rule='server_wins',
    tenant_id=tenant.id,
    device_id='POS-001',
    conflict_details={
        'client_version': 1,
        'server_version': 2,
        'field_differences': ['price', 'stock'],
    },
)

# Conflict resolved
SyncLogger.log_conflict_resolved(
    operation_id=operation.id,
    entity_type='Product',
    entity_id='prod-123',
    resolution_rule='server_wins',
    resolution_action='SERVER_OVERRIDE',
    tenant_id=tenant.id,
    device_id='POS-001',
    audit_log={
        'reason': 'Configuration data: server always wins',
        'client_payload': {...},
        'server_payload': {...},
    },
    merged_payload=False,
)

# Conflict resolution failed
SyncLogger.log_conflict_failed(
    operation_id=operation.id,
    entity_type='Product',
    error='Unknown entity type',
    tenant_id=tenant.id,
    device_id='POS-001',
    resolution_rule='server_wins',
)
```

### Retry Logging

```python
# Retry attempt
SyncLogger.log_retry_attempt(
    operation_id=operation.id,
    entity_type='StockMovement',
    retry_count=2,
    max_retries=3,
    tenant_id=tenant.id,
    device_id='POS-001',
    previous_error='Connection timeout',
)

# Retries exhausted
SyncLogger.log_retry_exhausted(
    operation_id=operation.id,
    entity_type='StockMovement',
    retry_count=3,
    tenant_id=tenant.id,
    device_id='POS-001',
    final_error='Connection timeout after 3 attempts',
)

# Retry succeeded
SyncLogger.log_retry_success(
    operation_id=operation.id,
    entity_type='StockMovement',
    retry_count=2,
    tenant_id=tenant.id,
    device_id='POS-001',
)
```

## Log Analysis Queries

### Find all sync failures for a device

```bash
grep '"device_id": "POS-001"' logs/sync.log | grep '"severity": "ERROR"'
```

### Count operations by type

```bash
grep '"event_type": "SYNC_OPERATION_APPLIED"' logs/sync.log | wc -l
```

### Analyze conflict resolution patterns

```bash
grep '"event_type": "SYNC_CONFLICT_RESOLVED"' logs/sync.log | \
  jq -r '.resolution_rule' | sort | uniq -c
```

### Calculate success rates

```bash
grep '"event_type": "SYNC_PUSH_COMPLETE"' logs/sync.log | \
  jq -r '.success_rate' | \
  awk '{sum+=$1; count++} END {print "Average:", sum/count "%"}'
```

### Find slow sync operations

```bash
grep '"duration_ms"' logs/sync.log | \
  jq 'select(.duration_ms > 1000)' | \
  jq -r '[.timestamp, .event_type, .device_id, .duration_ms] | @csv'
```

## Integration with Log Aggregation

### Elasticsearch/Kibana

Logs are JSON-formatted for easy ingestion:

```
filebeat.inputs:
  - type: log
    enabled: true
    paths:
      - /var/log/gravitea/sync.log
    json.keys_under_root: true
    json.add_error_key: true
```

### CloudWatch Logs

AWS CloudWatch Log Insights queries:

```
# Failed operations by device
fields @timestamp, device_id, error
| filter event_type like /FAILED/
| stats count() by device_id
| sort count desc

# Conflict resolution effectiveness
fields @timestamp, resolution_rule, resolution_action
| filter event_type = "SYNC_CONFLICT_RESOLVED"
| stats count() by resolution_rule, resolution_action
```

## Compliance Checklist

- [x] All sync operations logged with full context
- [x] Conflict detection and resolution logged
- [x] Retry attempts and failures logged
- [x] Tenant ID and device ID included in all logs
- [x] Structured JSON format for aggregation
- [x] Duration tracking for performance monitoring
- [x] Error codes for categorization
- [x] Audit trail for all resolutions
- [x] UUID serialization handled correctly
- [x] Severity levels properly assigned

## Performance Considerations

- Logs are written asynchronously (standard Python logging)
- JSON formatting is minimal overhead
- UUID to string conversion is cached
- Rotating file handlers prevent disk space issues
- Debug-level logs can be disabled in production

## Security Notes

- Log files should be protected with appropriate permissions (600)
- Sensitive payload data should be sanitized before logging
- Personal information (PII) should not be logged
- Log retention policies should comply with data regulations
- Access to log files should be restricted and audited
