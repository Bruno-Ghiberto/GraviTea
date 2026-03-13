# Sync Logging Examples - Real-World Scenarios

## Scenario 1: Successful Push Operation

### Request Flow
1. POS-001 sends 5 offline operations
2. 4 operations are new, 1 already exists (idempotent)
3. All operations processed successfully
4. No conflicts detected

### Log Output

```json
{
  "timestamp": "2024-01-15T14:05:00.000Z",
  "event_type": "SYNC_PUSH_START",
  "severity": "INFO",
  "message": "Sync push started: device=POS-001, operations=5",
  "tenant_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "device_id": "POS-001",
  "operation_count": 5,
  "user_id": "u1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "session_id": "s1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "request_ip": "192.168.1.100"
}

{
  "timestamp": "2024-01-15T14:05:00.050Z",
  "event_type": "SYNC_OPERATION_APPLIED",
  "severity": "DEBUG",
  "message": "Operation applied: CREATE Product",
  "operation_id": "op1-1234-5678-90ab-cdef12345678",
  "entity_type": "Product",
  "operation_type": "CREATE",
  "entity_id": "prod-123",
  "tenant_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "device_id": "POS-001",
  "processing_time_ms": 8.2
}

{
  "timestamp": "2024-01-15T14:05:00.075Z",
  "event_type": "SYNC_OPERATION_SKIPPED",
  "severity": "DEBUG",
  "message": "Operation skipped: Product - already_exists",
  "operation_id": "op2-1234-5678-90ab-cdef12345678",
  "entity_type": "Product",
  "reason": "already_exists",
  "tenant_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "device_id": "POS-001"
}

{
  "timestamp": "2024-01-15T14:05:00.250Z",
  "event_type": "SYNC_PUSH_COMPLETE",
  "severity": "INFO",
  "message": "Sync push complete: device=POS-001, applied=4/5",
  "tenant_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "device_id": "POS-001",
  "operations_count": 5,
  "operations_applied": 4,
  "operations_skipped": 1,
  "operations_rejected": 0,
  "conflicts_detected": 0,
  "duration_ms": 250.0,
  "session_id": "s1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "success_rate": 80.0
}
```

## Scenario 2: Pull Operation with Changes

### Request Flow
1. POS-002 requests changes since last sync
2. Server returns 15 changes (10 Products, 5 Sales)
3. Pull completes successfully

### Log Output

```json
{
  "timestamp": "2024-01-15T14:10:00.000Z",
  "event_type": "SYNC_PULL_START",
  "severity": "INFO",
  "message": "Sync pull started: device=POS-002, since=2024-01-15T13:00:00Z",
  "tenant_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "device_id": "POS-002",
  "since_timestamp": "2024-01-15T13:00:00Z",
  "entity_types": ["Product", "Sale"],
  "user_id": "u1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "session_id": "s2b2c3d4-e5f6-7890-abcd-ef1234567890",
  "request_ip": "192.168.1.101"
}

{
  "timestamp": "2024-01-15T14:10:00.150Z",
  "event_type": "SYNC_PULL_COMPLETE",
  "severity": "INFO",
  "message": "Sync pull complete: device=POS-002, changes=15",
  "tenant_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "device_id": "POS-002",
  "changes_count": 15,
  "entity_breakdown": {
    "Product": 10,
    "Sale": 5
  },
  "duration_ms": 150.2,
  "has_more": false,
  "session_id": "s2b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

## Scenario 3: Conflict Detection and Resolution

### Request Flow
1. POS-001 tries to update Product price
2. Server detects conflict (product updated on server)
3. Conflict resolver applies "server_wins" rule
4. Server data takes precedence

### Log Output

```json
{
  "timestamp": "2024-01-15T14:15:00.000Z",
  "event_type": "SYNC_CONFLICT_DETECTED",
  "severity": "WARNING",
  "message": "Conflict detected: Product prod-456 - server_wins",
  "operation_id": "op3-1234-5678-90ab-cdef12345678",
  "entity_type": "Product",
  "entity_id": "prod-456",
  "resolution_rule": "server_wins",
  "tenant_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "device_id": "POS-001",
  "conflict_details": {
    "operation_type": "UPDATE",
    "client_timestamp": "2024-01-15T14:00:00Z",
    "server_timestamp": "2024-01-15T14:10:00Z",
    "has_server_data": true,
    "conflict_data": {
      "field_differences": ["price", "updated_at"]
    }
  }
}

{
  "timestamp": "2024-01-15T14:15:00.025Z",
  "event_type": "SYNC_CONFLICT_RESOLVED",
  "severity": "INFO",
  "message": "Conflict resolved: Product - SERVER_OVERRIDE",
  "operation_id": "op3-1234-5678-90ab-cdef12345678",
  "entity_type": "Product",
  "entity_id": "prod-456",
  "resolution_rule": "server_wins",
  "resolution_action": "SERVER_OVERRIDE",
  "tenant_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "device_id": "POS-001",
  "audit_log": {
    "operation_id": "op3-1234-5678-90ab-cdef12345678",
    "entity_type": "Product",
    "entity_id": "prod-456",
    "operation_type": "UPDATE",
    "resolution_rule": "server_wins",
    "client_timestamp": "2024-01-15T14:00:00Z",
    "server_timestamp": "2024-01-15T14:10:00Z",
    "reason": "Configuration data: server always wins",
    "client_payload": {"price": 100.00},
    "server_payload": {"price": 95.00},
    "action_taken": "Client changes rejected, server data preserved"
  },
  "merged_payload": false
}
```

## Scenario 4: Operation Failure with Retry

### Request Flow
1. Stock movement operation fails (database timeout)
2. System attempts retry (1 of 3)
3. Retry succeeds on second attempt

### Log Output

```json
{
  "timestamp": "2024-01-15T14:20:00.000Z",
  "event_type": "SYNC_OPERATION_FAILED",
  "severity": "ERROR",
  "message": "Operation failed: StockMovement - Database connection timeout",
  "operation_id": "op4-1234-5678-90ab-cdef12345678",
  "entity_type": "StockMovement",
  "error": "Database connection timeout",
  "tenant_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "device_id": "POS-001",
  "retry_count": 0,
  "will_retry": true
}

{
  "timestamp": "2024-01-15T14:20:05.000Z",
  "event_type": "SYNC_RETRY_ATTEMPT",
  "severity": "WARNING",
  "message": "Retry attempt 1/3: StockMovement",
  "operation_id": "op4-1234-5678-90ab-cdef12345678",
  "entity_type": "StockMovement",
  "retry_count": 1,
  "max_retries": 3,
  "tenant_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "device_id": "POS-001",
  "previous_error": "Database connection timeout"
}

{
  "timestamp": "2024-01-15T14:20:05.150Z",
  "event_type": "SYNC_RETRY_SUCCESS",
  "severity": "INFO",
  "message": "Retry successful after 1 attempts: StockMovement",
  "operation_id": "op4-1234-5678-90ab-cdef12345678",
  "entity_type": "StockMovement",
  "retry_count": 1,
  "tenant_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "device_id": "POS-001"
}
```

## Scenario 5: Failed Push Operation

### Request Flow
1. POS-003 sends batch of operations
2. Database connection fails after 3 operations
3. Push fails, requiring client retry

### Log Output

```json
{
  "timestamp": "2024-01-15T14:25:00.000Z",
  "event_type": "SYNC_PUSH_START",
  "severity": "INFO",
  "message": "Sync push started: device=POS-003, operations=10",
  "tenant_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "device_id": "POS-003",
  "operation_count": 10,
  "user_id": "u1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "session_id": "s3b2c3d4-e5f6-7890-abcd-ef1234567890",
  "request_ip": "192.168.1.103"
}

{
  "timestamp": "2024-01-15T14:25:00.050Z",
  "event_type": "SYNC_OPERATION_APPLIED",
  "severity": "DEBUG",
  "message": "Operation applied: CREATE Sale",
  "operation_id": "op5-1234-5678-90ab-cdef12345678",
  "entity_type": "Sale",
  "operation_type": "CREATE",
  "entity_id": "sale-123",
  "tenant_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "device_id": "POS-003"
}

{
  "timestamp": "2024-01-15T14:25:00.180Z",
  "event_type": "SYNC_PUSH_FAILED",
  "severity": "ERROR",
  "message": "Sync push failed: device=POS-003, error=Connection to database lost",
  "tenant_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "device_id": "POS-003",
  "error": "Connection to database lost",
  "error_code": "PUSH_PROCESSING_ERROR",
  "operation_count": 10,
  "operations_processed": 3,
  "session_id": "s3b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

## Scenario 6: Operation Rejection (Validation Failure)

### Request Flow
1. POS-001 tries to delete a Sale (not allowed)
2. Operation rejected by conflict resolver
3. Push continues with remaining operations

### Log Output

```json
{
  "timestamp": "2024-01-15T14:30:00.100Z",
  "event_type": "SYNC_OPERATION_REJECTED",
  "severity": "WARNING",
  "message": "Operation rejected: Sale - Sales transactions: deletions not allowed",
  "operation_id": "op6-1234-5678-90ab-cdef12345678",
  "entity_type": "Sale",
  "operation_type": "DELETE",
  "reason": "Sales transactions: deletions not allowed",
  "tenant_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "device_id": "POS-001",
  "validation_errors": {
    "operation": "DELETE not allowed for sales",
    "suggested_action": "Use void/cancel instead"
  }
}
```

## Scenario 7: Retry Exhaustion

### Request Flow
1. Stock update fails repeatedly
2. System retries 3 times
3. All retries fail
4. Operation marked as permanently failed

### Log Output

```json
{
  "timestamp": "2024-01-15T14:35:00.000Z",
  "event_type": "SYNC_OPERATION_FAILED",
  "severity": "ERROR",
  "message": "Operation failed: StockMovement - Insufficient stock quantity",
  "operation_id": "op7-1234-5678-90ab-cdef12345678",
  "entity_type": "StockMovement",
  "error": "Insufficient stock quantity",
  "tenant_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "device_id": "POS-001",
  "retry_count": 0,
  "will_retry": true
}

{
  "timestamp": "2024-01-15T14:35:15.000Z",
  "event_type": "SYNC_RETRY_EXHAUSTED",
  "severity": "ERROR",
  "message": "Retry exhausted after 3 attempts: StockMovement",
  "operation_id": "op7-1234-5678-90ab-cdef12345678",
  "entity_type": "StockMovement",
  "retry_count": 3,
  "tenant_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "device_id": "POS-001",
  "final_error": "Insufficient stock quantity after 3 attempts"
}
```

## Log Analysis Examples

### Find All Failed Operations for Tenant

```bash
grep '"tenant_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"' logs/sync.log | \
  grep '"severity": "ERROR"' | \
  jq -r '[.timestamp, .device_id, .event_type, .error] | @csv'
```

Output:
```
"2024-01-15T14:20:00.000Z","POS-001","SYNC_OPERATION_FAILED","Database connection timeout"
"2024-01-15T14:25:00.180Z","POS-003","SYNC_PUSH_FAILED","Connection to database lost"
"2024-01-15T14:35:15.000Z","POS-001","SYNC_RETRY_EXHAUSTED","Insufficient stock quantity after 3 attempts"
```

### Calculate Average Sync Duration by Device

```bash
grep '"event_type": "SYNC_PUSH_COMPLETE"' logs/sync.log | \
  jq -r '[.device_id, .duration_ms] | @csv' | \
  awk -F',' '{sum[$1]+=$2; count[$1]++} END {for (d in sum) print d, sum[d]/count[d]}'
```

Output:
```
POS-001 245.5
POS-002 180.3
POS-003 320.7
```

### Count Conflicts by Resolution Rule

```bash
grep '"event_type": "SYNC_CONFLICT_RESOLVED"' logs/sync.log | \
  jq -r '.resolution_rule' | \
  sort | uniq -c | sort -rn
```

Output:
```
45 server_wins
23 last_write_wins
12 most_complete_wins
8 additive
3 server_assigns_final
```
