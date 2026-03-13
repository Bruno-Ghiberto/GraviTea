"""
Test suite for conflict resolver edge cases (H-001).

Tests edge case handling in conflict resolution:
- Null/empty field values
- Empty strings vs None
- Whitespace-only strings
- Missing keys in payloads
- Concurrent modifications
- Invalid input validation
"""

import pytest
from uuid import uuid4
from datetime import datetime, timezone as dt_timezone

from apps.sync.conflict_resolver import (
    ConflictResolver,
    ConflictResolution,
    ResolutionAction,
    ResolutionRule,
)
from apps.sync.models import PendingOperation


@pytest.mark.django_db
class TestConflictResolverEdgeCases:
    """Test edge case handling in conflict resolution (H-001)."""

    def test_null_pending_operation_raises_type_error(self):
        """H-001: None pending_operation should raise TypeError."""
        resolver = ConflictResolver()

        with pytest.raises(TypeError, match="pending_operation cannot be None"):
            resolver.resolve(None, {})

    def test_missing_entity_type_raises_value_error(self, tenant_context, sync_session):
        """H-001: Missing entity_type should raise ValueError."""
        # Create operation with missing entity_type
        op = PendingOperation(
            id=uuid4(),
            tenant=tenant_context,
            sync_session=sync_session,
            operation_type="CREATE",
            entity_type="",  # Empty entity_type
            entity_id=uuid4(),
            payload={},
            client_timestamp=datetime.now(dt_timezone.utc),
        )

        resolver = ConflictResolver()

        with pytest.raises(ValueError, match="valid entity_type"):
            resolver.resolve(op, {})

    def test_empty_payloads_both_sides(self, tenant_context, sync_session):
        """H-001: Both client and server payloads empty should be handled."""
        op = PendingOperation(
            id=uuid4(),
            tenant=tenant_context,
            sync_session=sync_session,
            operation_type="UPDATE",
            entity_type="Customer",
            entity_id=uuid4(),
            payload={},  # Empty payload
            client_timestamp=datetime.now(dt_timezone.utc),
        )

        resolver = ConflictResolver()

        # Empty payloads should be rejected for most_complete_wins
        resolution = resolver.resolve(op, {})  # Empty server data too

        assert resolution.action == ResolutionAction.REJECT
        assert "empty" in resolution.audit_log.get("reason", "").lower()

    def test_empty_string_vs_none_normalization(self, tenant_context, sync_session):
        """H-001: Empty strings should be normalized to None."""
        op = PendingOperation(
            id=uuid4(),
            tenant=tenant_context,
            sync_session=sync_session,
            operation_type="UPDATE",
            entity_type="Customer",
            entity_id=uuid4(),
            payload={
                "name": "John Doe",
                "email": "",  # Empty string
                "phone": "   ",  # Whitespace only
                "address": None,  # Explicit None
            },
            client_timestamp=datetime.now(dt_timezone.utc),
        )

        server_data = {
            "name": "Jane Doe",
            "email": None,
            "phone": "555-1234",
            "address": "",  # Empty string
        }

        resolver = ConflictResolver()
        resolution = resolver.resolve(op, server_data)

        # Verify empty strings were normalized
        assert "empty_string_normalized" in resolution.audit_log.get("merge_decisions", {})

        # phone: client has whitespace (normalized to None), server has value → server wins
        # email: both None → both_null
        assert resolution.merged_payload["phone"] == "555-1234"

    def test_whitespace_only_strings_treated_as_empty(self, tenant_context, sync_session):
        """H-001: Whitespace-only strings should be treated as None."""
        op = PendingOperation(
            id=uuid4(),
            tenant=tenant_context,
            sync_session=sync_session,
            operation_type="UPDATE",
            entity_type="Customer",
            entity_id=uuid4(),
            payload={
                "name": "   \t\n   ",  # Whitespace only
                "description": "Valid text",
            },
            client_timestamp=datetime.now(dt_timezone.utc),
        )

        server_data = {
            "name": "Server Name",
            "description": "Server description",
        }

        resolver = ConflictResolver()
        resolution = resolver.resolve(op, server_data)

        # Whitespace-only name should be normalized to None
        # Server value should win
        assert resolution.merged_payload["name"] == "Server Name"

    def test_missing_keys_in_one_payload(self, tenant_context, sync_session):
        """H-001: Missing keys in one payload should be handled gracefully."""
        op = PendingOperation(
            id=uuid4(),
            tenant=tenant_context,
            sync_session=sync_session,
            operation_type="UPDATE",
            entity_type="Customer",
            entity_id=uuid4(),
            payload={
                "name": "John Doe",
                "email": "john@example.com",
                # phone missing
            },
            client_timestamp=datetime.now(dt_timezone.utc),
        )

        server_data = {
            "name": "Jane Doe",
            # email missing
            "phone": "555-1234",
        }

        resolver = ConflictResolver()
        resolution = resolver.resolve(op, server_data)

        # Should merge all keys from both payloads
        assert "name" in resolution.merged_payload
        assert "email" in resolution.merged_payload
        assert "phone" in resolution.merged_payload

        # email only in client → client wins
        assert resolution.merged_payload["email"] == "john@example.com"
        # phone only in server → server wins
        assert resolution.merged_payload["phone"] == "555-1234"

    def test_concurrent_modification_different_fields(self, tenant_context, sync_session):
        """H-001: Concurrent mods to different fields should merge successfully."""
        op = PendingOperation(
            id=uuid4(),
            tenant=tenant_context,
            sync_session=sync_session,
            operation_type="UPDATE",
            entity_type="Customer",
            entity_id=uuid4(),
            payload={
                "name": "Original Name",
                "email": "client.updated.email@example.com",  # Client updated email (32 chars, longer)
                "phone": "555-0000",  # No change
            },
            client_timestamp=datetime.now(dt_timezone.utc),
        )

        server_data = {
            "name": "Original Name",
            "email": "old@example.com",  # Server email (15 chars, shorter)
            "phone": "555-1234",  # Server updated phone (8 chars vs client's 8 chars - tied, server wins)
        }

        resolver = ConflictResolver()
        resolution = resolver.resolve(op, server_data)

        # Both updates should be preserved via merge
        assert resolution.action == ResolutionAction.MERGE
        # Client's email wins (longer: 32 > 15)
        assert resolution.merged_payload["email"] == "client.updated.email@example.com"
        # Server's phone wins (same length, server wins ties)
        assert resolution.merged_payload["phone"] == "555-1234"

    def test_list_field_completeness_comparison(self, tenant_context, sync_session):
        """H-001: Lists should be compared by length for completeness."""
        op = PendingOperation(
            id=uuid4(),
            tenant=tenant_context,
            sync_session=sync_session,
            operation_type="UPDATE",
            entity_type="Customer",
            entity_id=uuid4(),
            payload={
                "tags": ["tag1", "tag2", "tag3"],  # 3 items
            },
            client_timestamp=datetime.now(dt_timezone.utc),
        )

        server_data = {
            "tags": ["tag1", "tag2"],  # 2 items
        }

        resolver = ConflictResolver()
        resolution = resolver.resolve(op, server_data)

        # Client has more complete list (longer) → client wins
        assert resolution.merged_payload["tags"] == ["tag1", "tag2", "tag3"]
        assert "client_won" in resolution.audit_log["merge_decisions"]
        assert "tags" in resolution.audit_log["merge_decisions"]["client_won"]

    def test_dict_field_completeness_comparison(self, tenant_context, sync_session):
        """H-001: Dicts should be compared by key count for completeness."""
        op = PendingOperation(
            id=uuid4(),
            tenant=tenant_context,
            sync_session=sync_session,
            operation_type="UPDATE",
            entity_type="Customer",
            entity_id=uuid4(),
            payload={
                "metadata": {
                    "source": "app",
                    "version": "1.0",
                    "locale": "en_US",
                },  # 3 keys
            },
            client_timestamp=datetime.now(dt_timezone.utc),
        )

        server_data = {
            "metadata": {
                "source": "web",
                "version": "2.0",
            },  # 2 keys
        }

        resolver = ConflictResolver()
        resolution = resolver.resolve(op, server_data)

        # Client has more complete dict (more keys) → client wins
        assert len(resolution.merged_payload["metadata"]) == 3
        assert resolution.merged_payload["metadata"]["locale"] == "en_US"

    def test_mixed_type_fields_server_wins(self, tenant_context, sync_session):
        """H-001: Mixed types (incompatible) should default to server wins."""
        op = PendingOperation(
            id=uuid4(),
            tenant=tenant_context,
            sync_session=sync_session,
            operation_type="UPDATE",
            entity_type="Customer",
            entity_id=uuid4(),
            payload={
                "data": ["list", "value"],  # List
            },
            client_timestamp=datetime.now(dt_timezone.utc),
        )

        server_data = {
            "data": {"key": "value"},  # Dict
        }

        resolver = ConflictResolver()
        resolution = resolver.resolve(op, server_data)

        # Mixed types → server wins
        assert resolution.merged_payload["data"] == {"key": "value"}

    def test_metadata_fields_always_from_server(self, tenant_context, sync_session):
        """H-001: Metadata fields (id, created_at, etc.) always use server values."""
        entity_id = uuid4()
        op = PendingOperation(
            id=uuid4(),
            tenant=tenant_context,
            sync_session=sync_session,
            operation_type="UPDATE",
            entity_type="Customer",
            entity_id=entity_id,
            payload={
                "id": uuid4(),  # Client trying to change ID
                "created_at": "2024-01-01T00:00:00Z",  # Client timestamp
                "updated_at": "2024-01-01T00:00:00Z",
                "name": "Client Name",
            },
            client_timestamp=datetime.now(dt_timezone.utc),
        )

        server_id = uuid4()
        server_data = {
            "id": server_id,
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-12-31T00:00:00Z",
            "name": "Server Name",
        }

        resolver = ConflictResolver()
        resolution = resolver.resolve(op, server_data)

        # Metadata fields should always use server values
        assert resolution.merged_payload["id"] == server_id
        assert resolution.merged_payload["created_at"] == "2023-01-01T00:00:00Z"


@pytest.mark.django_db
class TestConflictResolverValidation:
    """Test input validation for conflict resolver (H-001)."""

    def test_unknown_entity_type_raises_error(self, tenant_context, sync_session):
        """H-001: Unknown entity type should raise ValueError."""
        op = PendingOperation(
            id=uuid4(),
            tenant=tenant_context,
            sync_session=sync_session,
            operation_type="CREATE",
            entity_type="UnknownEntityType",
            entity_id=uuid4(),
            payload={"name": "Test"},
            client_timestamp=datetime.now(dt_timezone.utc),
        )

        resolver = ConflictResolver()

        with pytest.raises(ValueError, match="Unknown entity type"):
            resolver.resolve(op, {})

    def test_null_payload_with_valid_server_data(self, tenant_context, sync_session):
        """H-001: Null client payload with valid server data should handle gracefully."""
        op = PendingOperation(
            id=uuid4(),
            tenant=tenant_context,
            sync_session=sync_session,
            operation_type="UPDATE",
            entity_type="Customer",
            entity_id=uuid4(),
            payload=None,  # Null payload
            client_timestamp=datetime.now(dt_timezone.utc),
        )

        server_data = {
            "name": "Server Name",
            "email": "server@example.com",
        }

        resolver = ConflictResolver()
        resolution = resolver.resolve(op, server_data)

        # Should handle gracefully - normalized to empty dict
        # All server fields should win
        assert resolution.merged_payload["name"] == "Server Name"
