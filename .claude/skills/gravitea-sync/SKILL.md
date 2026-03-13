---
name: gravitea-sync
description: >
  Offline-first synchronization patterns for GRAVITEA-ERP including conflict resolution strategies, sync sessions, and pending operations.
  Trigger: When editing apps/sync/, working with offline sync, conflict resolution, or push/pull operations.
license: MIT
metadata:
  author: gravitea-team
  version: "1.0"
---

# Gravitea Sync Skill

Patterns for offline-first synchronization with conflict resolution, vector clocks, and multi-device coordination in a multi-tenant context.

## When to Use

- Creating or modifying sync models (SyncSession, PendingOperation)
- Implementing conflict resolution logic
- Working with push/pull synchronization endpoints
- Building offline queue management
- Implementing vector clock logic for causality tracking

---

## Critical Patterns

### Pattern 1: Conflict Resolution Strategy Selection

**Different entity types require different conflict resolution strategies based on their business semantics.**

```python
# apps/sync/conflict_resolver.py
class ResolutionRule(Enum):
    """Conflict resolution strategies."""
    SERVER_WINS = "server_wins"           # Configuration data
    LAST_WRITE_WINS = "last_write_wins"   # Inventory levels
    ADDITIVE = "additive"                 # Sales transactions
    MOST_COMPLETE_WINS = "most_complete"  # Customer data
    SERVER_ASSIGNS_FINAL = "server_final" # Fiscal documents

# Entity-to-resolution mapping
ENTITY_RESOLUTION_MAP = {
    # Configuration (server is source of truth)
    "Product": ResolutionRule.SERVER_WINS,
    "ProductCategory": ResolutionRule.SERVER_WINS,
    "PriceList": ResolutionRule.SERVER_WINS,
    "Settings": ResolutionRule.SERVER_WINS,

    # Inventory (last write wins with audit trail)
    "StockMovement": ResolutionRule.LAST_WRITE_WINS,
    "StockSnapshot": ResolutionRule.LAST_WRITE_WINS,

    # Sales (additive - never delete transactions)
    "Sale": ResolutionRule.ADDITIVE,
    "SaleItem": ResolutionRule.ADDITIVE,
    "Payment": ResolutionRule.ADDITIVE,

    # Customer (merge fields, prefer completeness)
    "Customer": ResolutionRule.MOST_COMPLETE_WINS,

    # Fiscal (server assigns final values)
    "FiscalDocument": ResolutionRule.SERVER_ASSIGNS_FINAL,
    "CAE": ResolutionRule.SERVER_ASSIGNS_FINAL,
}
```

---

### Pattern 2: SyncSession Model

**SyncSession tracks device synchronization state with vector clocks for causality tracking.**

```python
# apps/sync/models.py
class SyncSession(TenantBoundModel):
    """
    Tracks synchronization state between client device and server.

    Each device has its own sync session tracking:
    - Last successful sync timestamp
    - Vector clock for causality ordering
    - Current sync status and progress
    """

    class SyncStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"
        CONFLICT = "CONFLICT", "Conflict Detected"

    device_id = models.UUIDField(db_index=True)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    status = PostgresEnumField(enum_type=SYNC_STATUS_ENUM, ...)
    vector_clock = models.JSONField(default=dict)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    operations_pushed = models.IntegerField(default=0)
    operations_pulled = models.IntegerField(default=0)
    conflicts_resolved = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "device_id", "branch_id"],
                name="unique_sync_session_per_device_branch"
            ),
        ]
```

**Status Flow:**
```
PENDING → IN_PROGRESS → COMPLETED
                     ↘ FAILED
                     ↘ CONFLICT
```

---

### Pattern 3: PendingOperation Queue

**PendingOperation queues offline changes for sync with full audit context.**

```python
# apps/sync/models.py
class PendingOperation(TenantBoundModel):
    """
    Queued offline operation awaiting synchronization.

    Operations are stored with full context for:
    - Conflict resolution (entity type, operation type)
    - Audit trail (device, user, timestamp)
    - Replay capability (full payload)
    """

    class OperationType(models.TextChoices):
        CREATE = "CREATE", "Create"
        UPDATE = "UPDATE", "Update"
        DELETE = "DELETE", "Delete"

    class OperationStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"
        CONFLICT = "CONFLICT", "Conflict"

    sync_session = models.ForeignKey(SyncSession, on_delete=models.CASCADE)
    entity_type = models.CharField(max_length=100, db_index=True)
    entity_id = models.UUIDField(db_index=True)
    operation_type = PostgresEnumField(enum_type=OPERATION_TYPE_ENUM, ...)
    status = PostgresEnumField(enum_type=OPERATION_STATUS_ENUM, ...)
    payload = models.JSONField()
    client_timestamp = models.DateTimeField()
    server_timestamp = models.DateTimeField(null=True, blank=True)
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    error_message = models.TextField(blank=True)
    resolved_payload = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ["client_timestamp"]  # Process in order
        indexes = [
            models.Index(fields=["tenant_id", "status"]),
            models.Index(fields=["entity_type", "entity_id"]),
        ]
```

---

### Pattern 4: Conflict Resolution Strategies

**Each strategy has specific logic for merging conflicting changes.**

```python
# apps/sync/conflict_resolver.py
class ConflictResolver:
    """Resolves sync conflicts using entity-specific strategies."""

    def resolve(
        self,
        entity_type: str,
        client_data: dict,
        server_data: dict,
        client_timestamp: datetime,
        server_timestamp: datetime,
    ) -> ConflictResult:
        """
        Resolve conflict between client and server versions.

        Returns ConflictResult with:
        - resolved_data: The merged/winning data
        - winner: "client" | "server" | "merged"
        - changes_applied: List of field changes
        - audit_log: Full conflict audit trail
        """
        rule = self._get_resolution_rule(entity_type)

        if rule == ResolutionRule.SERVER_WINS:
            return self._resolve_server_wins(server_data)
        elif rule == ResolutionRule.LAST_WRITE_WINS:
            return self._resolve_last_write_wins(
                client_data, server_data,
                client_timestamp, server_timestamp
            )
        elif rule == ResolutionRule.ADDITIVE:
            return self._resolve_additive(client_data, server_data)
        elif rule == ResolutionRule.MOST_COMPLETE_WINS:
            return self._resolve_most_complete(client_data, server_data)
        elif rule == ResolutionRule.SERVER_ASSIGNS_FINAL:
            return self._resolve_server_assigns_final(
                client_data, server_data
            )

    def _resolve_server_wins(self, server_data: dict) -> ConflictResult:
        """Server data always wins (configuration data)."""
        return ConflictResult(
            resolved_data=server_data,
            winner="server",
            changes_applied=[],
            audit_log={"strategy": "server_wins"}
        )

    def _resolve_last_write_wins(
        self,
        client_data: dict,
        server_data: dict,
        client_ts: datetime,
        server_ts: datetime,
    ) -> ConflictResult:
        """Most recent timestamp wins (inventory)."""
        if client_ts > server_ts:
            return ConflictResult(
                resolved_data=client_data,
                winner="client",
                changes_applied=self._diff(server_data, client_data),
                audit_log={"strategy": "last_write_wins", "winner_ts": client_ts}
            )
        return ConflictResult(
            resolved_data=server_data,
            winner="server",
            changes_applied=[],
            audit_log={"strategy": "last_write_wins", "winner_ts": server_ts}
        )

    def _resolve_additive(
        self,
        client_data: dict,
        server_data: dict,
    ) -> ConflictResult:
        """
        Additive merge for transactions (sales).

        - Never delete transactions
        - Client additions preserved
        - Server additions preserved
        - Duplicates detected via UUID
        """
        merged = self._merge_without_delete(client_data, server_data)
        return ConflictResult(
            resolved_data=merged,
            winner="merged",
            changes_applied=self._diff(server_data, merged),
            audit_log={"strategy": "additive"}
        )

    def _resolve_most_complete(
        self,
        client_data: dict,
        server_data: dict,
    ) -> ConflictResult:
        """
        Field-by-field merge preferring non-null values (customer data).

        - Prefer non-null over null
        - Prefer longer strings (more complete)
        - Preserve all email/phone variations
        """
        merged = {}
        for key in set(client_data.keys()) | set(server_data.keys()):
            client_val = client_data.get(key)
            server_val = server_data.get(key)
            merged[key] = self._select_most_complete(client_val, server_val)

        return ConflictResult(
            resolved_data=merged,
            winner="merged",
            changes_applied=self._diff(server_data, merged),
            audit_log={"strategy": "most_complete_wins"}
        )

    def _resolve_server_assigns_final(
        self,
        client_data: dict,
        server_data: dict,
    ) -> ConflictResult:
        """
        Server assigns authoritative values (fiscal documents).

        - Client provides draft data
        - Server assigns: CAE, document number, fiscal timestamp
        - Client data preserved for non-fiscal fields
        """
        # Start with client data
        merged = client_data.copy()

        # Server overwrites fiscal fields
        fiscal_fields = ["cae", "document_number", "fiscal_timestamp", "status"]
        for field in fiscal_fields:
            if field in server_data:
                merged[field] = server_data[field]

        return ConflictResult(
            resolved_data=merged,
            winner="merged",
            changes_applied=self._diff(client_data, merged),
            audit_log={"strategy": "server_assigns_final"}
        )
```

---

### Pattern 5: Sync Push/Pull Endpoints

**Push uploads local changes, Pull downloads server changes.**

```python
# apps/sync/views.py
class SyncPushView(APIView):
    """
    Upload pending local operations to server.

    POST /api/v1/sync/push/
    {
        "device_id": "uuid",
        "branch_id": "uuid",
        "operations": [
            {
                "entity_type": "Sale",
                "entity_id": "uuid",
                "operation_type": "CREATE",
                "payload": {...},
                "client_timestamp": "2026-01-20T15:30:00Z"
            }
        ]
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SyncPushSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Get or create sync session
        session = self._get_or_create_session(
            tenant=request.user.tenant,
            device_id=serializer.validated_data["device_id"],
            branch_id=serializer.validated_data["branch_id"],
        )

        # Process operations
        results = []
        for op_data in serializer.validated_data["operations"]:
            result = self._process_operation(session, op_data)
            results.append(result)

        # Update session stats
        session.operations_pushed = len(results)
        session.conflicts_resolved = sum(1 for r in results if r.had_conflict)
        session.save()

        return Response({
            "session_id": session.id,
            "processed": len(results),
            "conflicts": session.conflicts_resolved,
            "results": results,
        })


class SyncPullView(APIView):
    """
    Download server changes since last sync.

    GET /api/v1/sync/pull/?device_id=xxx&branch_id=xxx&since=timestamp

    Returns changes filtered by:
    - Tenant isolation (automatic)
    - Branch filter (explicit)
    - Timestamp filter (since last sync)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        device_id = request.query_params.get("device_id")
        branch_id = request.query_params.get("branch_id")
        since = request.query_params.get("since")

        # Get session for last sync timestamp
        session = SyncSession.objects.filter(
            tenant=request.user.tenant,
            device_id=device_id,
            branch_id=branch_id,
        ).first()

        since_dt = parse_datetime(since) if since else session.last_sync_at

        # Gather changes for each entity type
        changes = self._gather_changes(
            tenant=request.user.tenant,
            branch_id=branch_id,
            since=since_dt,
        )

        # Update session
        if session:
            session.operations_pulled = sum(len(c) for c in changes.values())
            session.last_sync_at = timezone.now()
            session.save()

        return Response({
            "changes": changes,
            "sync_timestamp": timezone.now().isoformat(),
            "has_more": False,  # Pagination if needed
        })


class SyncStatusView(APIView):
    """
    Check sync status and pending operations count.

    GET /api/v1/sync/status/?device_id=xxx&branch_id=xxx
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        device_id = request.query_params.get("device_id")
        branch_id = request.query_params.get("branch_id")

        session = SyncSession.objects.filter(
            tenant=request.user.tenant,
            device_id=device_id,
            branch_id=branch_id,
        ).first()

        pending_count = PendingOperation.objects.filter(
            sync_session=session,
            status=PendingOperation.OperationStatus.PENDING,
        ).count() if session else 0

        return Response({
            "session_id": session.id if session else None,
            "status": session.status if session else "NO_SESSION",
            "last_sync_at": session.last_sync_at if session else None,
            "pending_operations": pending_count,
            "vector_clock": session.vector_clock if session else {},
        })
```

---

## Decision Tree

```
Implementing sync feature?
|-- Client-side queue? -> Use _outbox pattern (SQLite)
|-- Server-side processing? -> Use PendingOperation model
+-- Conflict detected?
    |-- Configuration data? -> SERVER_WINS
    |-- Inventory data? -> LAST_WRITE_WINS
    |-- Transaction data? -> ADDITIVE
    |-- Customer data? -> MOST_COMPLETE_WINS
    +-- Fiscal data? -> SERVER_ASSIGNS_FINAL

Sync operation type?
|-- Upload local changes? -> POST /sync/push/
|-- Download server changes? -> GET /sync/pull/
+-- Check sync state? -> GET /sync/status/

Handling sync failure?
|-- Network error? -> Queue for retry with exponential backoff
|-- Validation error? -> Mark operation FAILED, log error
|-- Conflict? -> Apply resolution strategy, log audit
+-- Max retries exceeded? -> Mark FAILED, alert user
```

---

## Anti-Patterns (What NOT to Do)

### Anti-Pattern 1: Deleting Transactions During Sync

```python
# FORBIDDEN - Never delete sales transactions
if operation_type == "DELETE" and entity_type == "Sale":
    Sale.objects.get(id=entity_id).delete()  # WRONG!

# CORRECT - Use ADDITIVE strategy, mark as cancelled
if operation_type == "DELETE" and entity_type == "Sale":
    sale = Sale.objects.get(id=entity_id)
    sale.status = SaleStatus.CANCELLED
    sale.cancelled_at = timezone.now()
    sale.cancelled_by = user
    sale.save()
```

### Anti-Pattern 2: Ignoring Conflict Resolution

```python
# FORBIDDEN - Blindly overwriting server data
def sync_push(operation):
    Entity.objects.filter(id=operation.entity_id).update(**operation.payload)

# CORRECT - Apply appropriate resolution strategy
def sync_push(operation):
    resolver = ConflictResolver()
    server_data = Entity.objects.get(id=operation.entity_id)

    if has_conflict(operation, server_data):
        result = resolver.resolve(
            entity_type=operation.entity_type,
            client_data=operation.payload,
            server_data=model_to_dict(server_data),
            client_timestamp=operation.client_timestamp,
            server_timestamp=server_data.updated_at,
        )
        server_data.update(**result.resolved_data)
        log_conflict_resolution(result.audit_log)
```

### Anti-Pattern 3: Missing Tenant Context in Sync

```python
# FORBIDDEN - Syncing without tenant validation
def gather_changes(since):
    return Product.objects.filter(updated_at__gt=since)  # Cross-tenant leak!

# CORRECT - Always filter by tenant
def gather_changes(tenant, since):
    return Product.objects.filter(
        tenant=tenant,
        updated_at__gt=since,
    )
```

### Anti-Pattern 4: Processing Operations Out of Order

```python
# FORBIDDEN - Parallel processing without ordering
async def process_operations(operations):
    await asyncio.gather(*[process(op) for op in operations])

# CORRECT - Process in timestamp order for causality
def process_operations(operations):
    sorted_ops = sorted(operations, key=lambda x: x.client_timestamp)
    results = []
    for op in sorted_ops:
        result = process_operation(op)
        results.append(result)
    return results
```

---

## Testing Sync

```python
# tests/sync/test_conflict_resolution.py
import pytest
from datetime import datetime, timedelta

@pytest.mark.integration
@pytest.mark.django_db
class TestConflictResolution:
    def test_server_wins_for_products(self, conflict_resolver):
        """Product conflicts: server data wins."""
        client_data = {"name": "Client Name", "price": "10.00"}
        server_data = {"name": "Server Name", "price": "15.00"}

        result = conflict_resolver.resolve(
            entity_type="Product",
            client_data=client_data,
            server_data=server_data,
            client_timestamp=datetime.now(),
            server_timestamp=datetime.now() - timedelta(hours=1),
        )

        assert result.winner == "server"
        assert result.resolved_data == server_data

    def test_last_write_wins_for_stock(self, conflict_resolver):
        """StockMovement conflicts: most recent wins."""
        client_data = {"quantity_delta": "50"}
        server_data = {"quantity_delta": "30"}
        client_ts = datetime.now()
        server_ts = datetime.now() - timedelta(minutes=5)

        result = conflict_resolver.resolve(
            entity_type="StockMovement",
            client_data=client_data,
            server_data=server_data,
            client_timestamp=client_ts,
            server_timestamp=server_ts,
        )

        assert result.winner == "client"
        assert result.resolved_data["quantity_delta"] == "50"

    def test_additive_preserves_both_sales(self, conflict_resolver):
        """Sale conflicts: both versions preserved."""
        client_data = {"items": [{"id": "a", "qty": 1}]}
        server_data = {"items": [{"id": "b", "qty": 2}]}

        result = conflict_resolver.resolve(
            entity_type="Sale",
            client_data=client_data,
            server_data=server_data,
            client_timestamp=datetime.now(),
            server_timestamp=datetime.now(),
        )

        assert result.winner == "merged"
        assert len(result.resolved_data["items"]) == 2

    def test_most_complete_merges_customer(self, conflict_resolver):
        """Customer conflicts: non-null fields preferred."""
        client_data = {"name": "John", "email": None, "phone": "123"}
        server_data = {"name": "John Doe", "email": "john@example.com", "phone": None}

        result = conflict_resolver.resolve(
            entity_type="Customer",
            client_data=client_data,
            server_data=server_data,
            client_timestamp=datetime.now(),
            server_timestamp=datetime.now(),
        )

        assert result.winner == "merged"
        assert result.resolved_data["name"] == "John Doe"  # Longer
        assert result.resolved_data["email"] == "john@example.com"  # Non-null
        assert result.resolved_data["phone"] == "123"  # Non-null


@pytest.mark.integration
@pytest.mark.django_db
class TestSyncPush:
    def test_push_creates_pending_operations(
        self, authenticated_client, sync_session, product
    ):
        """Push endpoint creates PendingOperation records."""
        response = authenticated_client.post("/api/v1/sync/push/", {
            "device_id": str(sync_session.device_id),
            "branch_id": str(sync_session.branch_id),
            "operations": [{
                "entity_type": "Product",
                "entity_id": str(product.id),
                "operation_type": "UPDATE",
                "payload": {"name": "Updated Name"},
                "client_timestamp": datetime.now().isoformat(),
            }]
        })

        assert response.status_code == 200
        assert response.json()["processed"] == 1

    def test_push_resolves_conflicts(
        self, authenticated_client, sync_session, product
    ):
        """Push with conflict triggers resolution."""
        # Modify product on server
        product.name = "Server Version"
        product.save()

        response = authenticated_client.post("/api/v1/sync/push/", {
            "device_id": str(sync_session.device_id),
            "branch_id": str(sync_session.branch_id),
            "operations": [{
                "entity_type": "Product",
                "entity_id": str(product.id),
                "operation_type": "UPDATE",
                "payload": {"name": "Client Version"},
                "client_timestamp": (datetime.now() - timedelta(hours=1)).isoformat(),
            }]
        })

        assert response.status_code == 200
        assert response.json()["conflicts"] == 1
        # Server wins for Product
        product.refresh_from_db()
        assert product.name == "Server Version"
```

---

## Commands

```bash
# Run sync tests
cd backend && pytest tests/sync/ -v

# Test conflict resolution
cd backend && pytest tests/sync/test_conflict_resolution.py -v

# Test sync endpoints
cd backend && pytest tests/sync/test_views.py -v -k "push or pull"

# Run integration tests
cd backend && pytest -m "integration" tests/sync/ -v

# Check pending operations for a device
cd backend && python manage.py shell -c "
from apps.sync.models import PendingOperation
print(PendingOperation.objects.filter(status='PENDING').count())
"
```

---

## Developer Checklist

Before submitting sync-related code, verify:

- [ ] Correct resolution strategy for entity type
- [ ] Conflict audit logging implemented
- [ ] Tenant isolation in all queries
- [ ] Operations processed in timestamp order
- [ ] No direct transaction deletions (use cancellation)
- [ ] Vector clock updated on sync
- [ ] Retry logic with exponential backoff
- [ ] Error messages don't leak tenant info
- [ ] Push/Pull endpoints have proper auth
- [ ] Tests cover all resolution strategies

---

## Resources

- **Models**: See `backend/apps/sync/models.py`
- **Conflict Resolver**: See `backend/apps/sync/conflict_resolver.py`
- **Views**: See `backend/apps/sync/views.py`
- **Tests**: See `backend/tests/sync/`
- **LLD Section 4**: See `Docs/Project Blueprint/Low-Level Design (LLD).md`
- **Frontend Sync**: See `frontend/AGENTS.MD` (offline-first architecture)

---

*Last updated: 2026-01-20*
*Models: SyncSession, PendingOperation*
*Resolution Strategies: SERVER_WINS, LAST_WRITE_WINS, ADDITIVE, MOST_COMPLETE_WINS, SERVER_ASSIGNS_FINAL*
