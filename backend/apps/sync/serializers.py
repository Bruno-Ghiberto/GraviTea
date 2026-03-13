"""
Sync serializers for Gravitea ERP.

Provides serializers for offline synchronization management.
"""

from rest_framework import serializers


from .models import PendingOperation, SyncSession


class SyncSessionSerializer(serializers.ModelSerializer):
    """
    Sync session serializer for read operations.

    Returns sync session details with branch info.
    """

    branch_name = serializers.CharField(source="branch.name", read_only=True)

    class Meta:
        model = SyncSession
        fields = [
            "id",
            "branch",
            "branch_name",
            "device_id",
            "last_sync_at",
            "sync_vector",
            "status",
            "error_message",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "last_sync_at",
            "status",
            "error_message",
            "created_at",
            "updated_at",
        ]


class SyncSessionCreateSerializer(serializers.ModelSerializer):
    """
    Sync session serializer for device registration.

    Registers a new POS terminal for sync.
    """

    class Meta:
        model = SyncSession
        fields = [
            "branch",
            "device_id",
        ]

    def validate_branch(self, value):
        """Validate branch belongs to same tenant."""
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            tenant = request.user.tenant
            if value.tenant_id != tenant.id:
                raise serializers.ValidationError("Branch not found in your organization.")
        return value

    def validate_device_id(self, value):
        """Validate device_id uniqueness within tenant."""
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            tenant = request.user.tenant
            if SyncSession.objects.filter(tenant=tenant, device_id=value).exists():
                raise serializers.ValidationError("A device with this ID is already registered.")
        return value

    def create(self, validated_data):
        """Create sync session with tenant from request context."""
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            validated_data["tenant"] = request.user.tenant
        return super().create(validated_data)


class PendingOperationSerializer(serializers.ModelSerializer):
    """
    Pending operation serializer for read operations.

    Returns operation details.
    """

    class Meta:
        model = PendingOperation
        fields = [
            "id",
            "sync_session",
            "operation_type",
            "entity_type",
            "entity_id",
            "payload",
            "client_timestamp",
            "server_timestamp",
            "status",
            "conflict_data",
            "error_message",
            "processed_at",
        ]
        read_only_fields = [
            "server_timestamp",
            "status",
            "conflict_data",
            "error_message",
            "processed_at",
        ]


class PendingOperationCreateSerializer(serializers.ModelSerializer):
    """
    Pending operation serializer for creating offline operations.

    Accepts operations from POS terminals for later processing.
    """

    # Explicitly declare id as writable for client-generated UUIDs
    id = serializers.UUIDField(required=True)

    class Meta:
        model = PendingOperation
        fields = [
            "id",  # Client-generated UUID for idempotency
            "operation_type",
            "entity_type",
            "entity_id",
            "payload",
            "client_timestamp",
        ]

    def validate(self, attrs):
        """Validate operation data."""
        # Ensure ID is provided for idempotency
        if "id" not in attrs:
            raise serializers.ValidationError(
                {"id": "Client-generated UUID is required for idempotency."}
            )
        return attrs

    def create(self, validated_data):
        """Create pending operation with tenant and session from context."""
        request = self.context.get("request")
        sync_session = self.context.get("sync_session")

        if request and hasattr(request, "user"):
            validated_data["tenant"] = request.user.tenant

        if sync_session:
            validated_data["sync_session"] = sync_session

        return super().create(validated_data)


class SyncPushSerializer(serializers.Serializer):
    """
    Serializer for sync push request.

    Accepts batch of operations from POS terminal.
    """

    device_id = serializers.CharField(max_length=100)
    operations = PendingOperationCreateSerializer(many=True)
    sync_vector = serializers.JSONField(required=False, default=dict)

    def validate_device_id(self, value):
        """Validate device is registered."""
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            tenant = request.user.tenant
            try:
                self.context["sync_session"] = SyncSession.objects.get(
                    tenant=tenant, device_id=value
                )
            except SyncSession.DoesNotExist:
                raise serializers.ValidationError("Device not registered. Please register first.")
        return value


class SyncPullSerializer(serializers.Serializer):
    """
    Serializer for sync pull request.

    Returns changes since last sync for POS terminal.
    """

    device_id = serializers.CharField(max_length=100)
    last_sync_at = serializers.DateTimeField(required=False, allow_null=True)
    entity_types = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        default=list,
        help_text="Entity types to pull (empty for all)",
    )


class SyncPullResponseSerializer(serializers.Serializer):
    """
    Serializer for sync pull response.

    Returns changes to sync to POS terminal.
    """

    server_timestamp = serializers.DateTimeField()
    changes = serializers.JSONField()
    has_more = serializers.BooleanField(default=False)
    next_cursor = serializers.CharField(allow_null=True)
