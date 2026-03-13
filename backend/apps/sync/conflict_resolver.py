"""
Conflict Resolution Module for Sync System

Implements 5 conflict resolution strategies:
1. Configuration Data (server_wins)
2. Inventory Levels (last_write_wins)
3. Sales Transactions (additive)
4. Customer Data (most_complete_wins)
5. Document Numbering (server_assigns_final)

SC-022 Compliance: All resolutions are logged with full audit trail.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional

from django.utils import timezone

from apps.sync.logging import SyncLogger
from apps.sync.models import PendingOperation
from apps.sync.sync_engine import merge_most_complete as _engine_merge

logger = logging.getLogger(__name__)


class ResolutionAction(str, Enum):
    """Actions that can be taken after conflict resolution."""

    APPLY = "APPLY"  # Apply operation as-is
    REJECT = "REJECT"  # Reject operation completely
    MERGE = "MERGE"  # Merge with existing data
    SERVER_OVERRIDE = "SERVER_OVERRIDE"  # Server data takes precedence


class ResolutionRule(str, Enum):
    """Available conflict resolution rules."""

    SERVER_WINS = "server_wins"
    LAST_WRITE_WINS = "last_write_wins"
    ADDITIVE = "additive"
    MOST_COMPLETE_WINS = "most_complete_wins"
    SERVER_ASSIGNS_FINAL = "server_assigns_final"


@dataclass
class ConflictResolution:
    """
    Result of conflict resolution.

    Attributes:
        action: Action to take (APPLY/REJECT/MERGE/SERVER_OVERRIDE)
        merged_payload: Final payload after resolution (if MERGE)
        audit_log: Detailed log of resolution process
        resolution_rule: Rule that was applied
        metadata: Additional resolution metadata
    """

    action: ResolutionAction
    merged_payload: Optional[Dict[str, Any]] = None
    audit_log: Dict[str, Any] = field(default_factory=dict)
    resolution_rule: ResolutionRule = ResolutionRule.SERVER_WINS
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert resolution to dictionary for storage."""
        return {
            "action": self.action.value,
            "merged_payload": self.merged_payload,
            "audit_log": self.audit_log,
            "resolution_rule": self.resolution_rule.value,
            "metadata": self.metadata,
            "resolved_at": timezone.now().isoformat(),
        }


class ConflictResolver:
    """
    Main conflict resolution engine.

    Routes conflicts to appropriate resolution strategy based on entity type
    and maintains full audit trail for SC-022 compliance.
    """

    # Entity type to resolution rule mapping
    ENTITY_RESOLUTION_MAP: Dict[str, ResolutionRule] = {
        # Configuration entities → server_wins
        "Product": ResolutionRule.SERVER_WINS,
        "PriceList": ResolutionRule.SERVER_WINS,
        "PriceListItem": ResolutionRule.SERVER_WINS,
        "Branch": ResolutionRule.SERVER_WINS,
        "Settings": ResolutionRule.SERVER_WINS,
        "TaxRate": ResolutionRule.SERVER_WINS,
        "PaymentMethod": ResolutionRule.SERVER_WINS,
        # Inventory entities → last_write_wins
        "StockMovement": ResolutionRule.LAST_WRITE_WINS,
        "StockSnapshot": ResolutionRule.LAST_WRITE_WINS,
        "InventoryAdjustment": ResolutionRule.LAST_WRITE_WINS,
        # Sales entities → additive
        "Sale": ResolutionRule.ADDITIVE,
        "SaleItem": ResolutionRule.ADDITIVE,
        "Payment": ResolutionRule.ADDITIVE,
        # Customer entities → most_complete_wins
        "Customer": ResolutionRule.MOST_COMPLETE_WINS,
        "Address": ResolutionRule.MOST_COMPLETE_WINS,
        "Contact": ResolutionRule.MOST_COMPLETE_WINS,
        # Document entities → server_assigns_final
        "FiscalDocument": ResolutionRule.SERVER_ASSIGNS_FINAL,
        "CAEAssignment": ResolutionRule.SERVER_ASSIGNS_FINAL,
        "Invoice": ResolutionRule.SERVER_ASSIGNS_FINAL,
    }

    def __init__(self):
        """Initialize resolver with strategy mapping."""
        self._strategy_map: Dict[ResolutionRule, Callable] = {
            ResolutionRule.SERVER_WINS: self._resolve_server_wins,
            ResolutionRule.LAST_WRITE_WINS: self._resolve_last_write_wins,
            ResolutionRule.ADDITIVE: self._resolve_additive,
            ResolutionRule.MOST_COMPLETE_WINS: self._resolve_most_complete_wins,
            ResolutionRule.SERVER_ASSIGNS_FINAL: self._resolve_server_assigns_final,
        }

    def resolve(
        self, pending_operation: PendingOperation, server_data: Optional[Dict[str, Any]] = None
    ) -> ConflictResolution:
        """
        Resolve conflict for a pending operation.

        Args:
            pending_operation: Operation that needs conflict resolution
            server_data: Current server state (if available)

        Returns:
            ConflictResolution with action and merged data

        Raises:
            ValueError: If entity type is unknown or resolution fails
            TypeError: If inputs are invalid (H-001)
        """
        # H-001: Validate inputs for edge cases
        if pending_operation is None:
            raise TypeError("pending_operation cannot be None")

        if not hasattr(pending_operation, "entity_type") or not pending_operation.entity_type:
            raise ValueError("pending_operation must have a valid entity_type")

        if not hasattr(pending_operation, "entity_id") or not pending_operation.entity_id:
            raise ValueError("pending_operation must have a valid entity_id")

        entity_type = pending_operation.entity_type
        entity_id = pending_operation.entity_id
        tenant_id = pending_operation.tenant_id
        device_id = (
            pending_operation.sync_session.device_id
            if pending_operation.sync_session
            else "unknown"
        )

        # Determine resolution rule
        resolution_rule = self._get_resolution_rule(entity_type)

        # Prepare conflict details for logging
        conflict_details = {
            "operation_type": pending_operation.operation_type,
            "client_timestamp": (
                pending_operation.client_timestamp.isoformat()
                if pending_operation.client_timestamp
                else None
            ),
            "server_timestamp": (
                pending_operation.server_timestamp.isoformat()
                if pending_operation.server_timestamp
                else None
            ),
            "has_server_data": server_data is not None,
            "conflict_data": pending_operation.conflict_data,
        }

        # Log conflict detection
        SyncLogger.log_conflict_detected(
            operation_id=pending_operation.id,
            entity_type=entity_type,
            entity_id=entity_id,
            resolution_rule=resolution_rule.value,
            tenant_id=tenant_id,
            device_id=device_id,
            conflict_details=conflict_details,
        )

        # Get resolution strategy
        strategy = self._strategy_map.get(resolution_rule)
        if not strategy:
            error_msg = f"No resolution strategy for rule: {resolution_rule}"
            logger.error(error_msg)

            # Log conflict resolution failure
            SyncLogger.log_conflict_failed(
                operation_id=pending_operation.id,
                entity_type=entity_type,
                error=error_msg,
                tenant_id=tenant_id,
                device_id=device_id,
                resolution_rule=resolution_rule.value,
            )
            raise ValueError(error_msg)

        # Execute resolution strategy
        try:
            resolution = strategy(pending_operation, server_data)

            # Add audit trail
            resolution.audit_log.update(
                {
                    "operation_id": str(pending_operation.id),
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "operation_type": pending_operation.operation_type,
                    "resolution_rule": resolution_rule.value,
                    "client_timestamp": (
                        pending_operation.client_timestamp.isoformat()
                        if pending_operation.client_timestamp
                        else None
                    ),
                    "server_timestamp": (
                        pending_operation.server_timestamp.isoformat()
                        if pending_operation.server_timestamp
                        else None
                    ),
                    "conflict_data": pending_operation.conflict_data,
                }
            )

            # Log successful conflict resolution
            SyncLogger.log_conflict_resolved(
                operation_id=pending_operation.id,
                entity_type=entity_type,
                entity_id=entity_id,
                resolution_rule=resolution_rule.value,
                resolution_action=resolution.action.value,
                tenant_id=tenant_id,
                device_id=device_id,
                audit_log=resolution.audit_log,
                merged_payload=resolution.merged_payload is not None,
            )

            return resolution

        except Exception as e:
            error_msg = str(e)
            logger.error(
                f"Conflict resolution failed: {error_msg}",
                extra={
                    "operation_id": pending_operation.id,
                    "entity_type": entity_type,
                    "error": error_msg,
                },
                exc_info=True,
            )

            # Log conflict resolution failure
            SyncLogger.log_conflict_failed(
                operation_id=pending_operation.id,
                entity_type=entity_type,
                error=error_msg,
                tenant_id=tenant_id,
                device_id=device_id,
                resolution_rule=resolution_rule.value,
            )
            raise

    def _get_resolution_rule(self, entity_type: str) -> ResolutionRule:
        """
        Get resolution rule for entity type.

        Args:
            entity_type: Type of entity

        Returns:
            Appropriate resolution rule

        Raises:
            ValueError: If entity type is unknown
        """
        rule = self.ENTITY_RESOLUTION_MAP.get(entity_type)
        if not rule:
            error_msg = f"Unknown entity type: {entity_type}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        return rule

    def _resolve_server_wins(
        self, pending_operation: PendingOperation, server_data: Optional[Dict[str, Any]]
    ) -> ConflictResolution:
        """
        Rule 1: Configuration Data (server_wins)

        Server configuration always takes precedence. Client changes are rejected
        with notification to sync latest server data.

        Use case: Prices, products, branch settings, tax rates
        """
        logger.debug(
            f"Applying server_wins rule for {pending_operation.entity_type}",
            extra={"operation_id": pending_operation.id},
        )

        return ConflictResolution(
            action=ResolutionAction.SERVER_OVERRIDE,
            merged_payload=server_data,
            audit_log={
                "reason": "Configuration data: server always wins",
                "client_payload": pending_operation.payload,
                "server_payload": server_data,
                "action_taken": "Client changes rejected, server data preserved",
            },
            resolution_rule=ResolutionRule.SERVER_WINS,
            metadata={
                "client_notified": True,
                "sync_required": True,
                "message": f"Server {pending_operation.entity_type} configuration takes precedence. Please sync to get latest data.",
            },
        )

    def _resolve_last_write_wins(
        self, pending_operation: PendingOperation, server_data: Optional[Dict[str, Any]]
    ) -> ConflictResolution:
        """
        Rule 2: Inventory Levels (last_write_wins)

        Most recent timestamp wins. Full audit trail maintained for reconciliation.

        Use case: Stock movements, inventory adjustments, snapshots
        """
        logger.debug(
            f"Applying last_write_wins rule for {pending_operation.entity_type}",
            extra={"operation_id": pending_operation.id},
        )

        client_ts = pending_operation.client_timestamp or timezone.now()
        server_ts = pending_operation.server_timestamp or timezone.now()

        # Compare timestamps
        if client_ts > server_ts:
            # Client has newer data
            action = ResolutionAction.APPLY
            final_payload = pending_operation.payload
            winner = "client"
        else:
            # Server has newer or equal data
            action = ResolutionAction.SERVER_OVERRIDE
            final_payload = server_data
            winner = "server"

        return ConflictResolution(
            action=action,
            merged_payload=final_payload,
            audit_log={
                "reason": "Inventory: most recent timestamp wins",
                "client_timestamp": client_ts.isoformat(),
                "server_timestamp": server_ts.isoformat(),
                "winner": winner,
                "client_payload": pending_operation.payload,
                "server_payload": server_data,
                "time_diff_seconds": abs((client_ts - server_ts).total_seconds()),
            },
            resolution_rule=ResolutionRule.LAST_WRITE_WINS,
            metadata={
                "winner": winner,
                "timestamp_diff": (client_ts - server_ts).total_seconds(),
                "reconciliation_required": True,
            },
        )

    def _resolve_additive(
        self, pending_operation: PendingOperation, server_data: Optional[Dict[str, Any]]
    ) -> ConflictResolution:
        """
        Rule 3: Sales Transactions (additive)

        All sales are preserved. No deletions. Merge all records with full audit.

        Use case: Sales, payments, sale items
        """
        logger.debug(
            f"Applying additive rule for {pending_operation.entity_type}",
            extra={"operation_id": pending_operation.id},
        )

        # DELETE operations are rejected for sales
        if pending_operation.operation_type == "DELETE":
            return ConflictResolution(
                action=ResolutionAction.REJECT,
                merged_payload=None,
                audit_log={
                    "reason": "Sales transactions: deletions not allowed",
                    "operation_type": "DELETE",
                    "action_taken": "DELETE operation rejected",
                    "entity_id": pending_operation.entity_id,
                },
                resolution_rule=ResolutionRule.ADDITIVE,
                metadata={
                    "deletion_rejected": True,
                    "message": "Sales transactions cannot be deleted. Use void/cancel instead.",
                },
            )

        # CREATE and UPDATE are always applied (additive)
        return ConflictResolution(
            action=ResolutionAction.APPLY,
            merged_payload=pending_operation.payload,
            audit_log={
                "reason": "Sales transactions: additive model",
                "operation_type": pending_operation.operation_type,
                "action_taken": "Operation applied, all sales preserved",
                "client_payload": pending_operation.payload,
                "server_payload": server_data,
            },
            resolution_rule=ResolutionRule.ADDITIVE,
            metadata={
                "additive": True,
                "audit_required": True,
                "message": "Sales transaction added/updated successfully.",
            },
        )

    def _resolve_most_complete_wins(
        self, pending_operation: PendingOperation, server_data: Optional[Dict[str, Any]]
    ) -> ConflictResolution:
        """
        Rule 4: Customer Data (most_complete_wins)

        Merge fields, prefer non-null values, server wins ties.

        Use case: Customer records, addresses, contacts

        Edge cases handled (H-001):
        - Null/empty field values in both client and server data
        - Empty strings vs None values
        - Whitespace-only strings treated as empty
        - Missing keys in either payload
        - Concurrent modifications to different fields
        """
        logger.debug(
            f"Applying most_complete_wins rule for {pending_operation.entity_type}",
            extra={"operation_id": pending_operation.id},
        )

        # H-001: Handle null/empty payloads gracefully
        client_payload = pending_operation.payload or {}
        server_payload = server_data or {}

        # Edge case: Both payloads empty
        if not client_payload and not server_payload:
            logger.warning(
                f"Both client and server payloads empty for {pending_operation.entity_type}",
                extra={"operation_id": pending_operation.id},
            )
            return ConflictResolution(
                action=ResolutionAction.REJECT,
                merged_payload=None,
                audit_log={
                    "reason": "Both payloads empty - cannot merge",
                    "client_payload": client_payload,
                    "server_payload": server_payload,
                },
                resolution_rule=ResolutionRule.MOST_COMPLETE_WINS,
                metadata={"error": "empty_payloads"},
            )

        # Delegate field-level merge to sync_engine (Rust or Python fallback)
        merged, merge_log = _engine_merge(server_payload, client_payload)

        return ConflictResolution(
            action=ResolutionAction.MERGE,
            merged_payload=merged,
            audit_log={
                "reason": "Customer data: most complete wins",
                "client_payload": client_payload,
                "server_payload": server_payload,
                "merge_decisions": merge_log,
                "fields_from_client": len(merge_log["client_won"]),
                "fields_from_server": len(merge_log["server_won"])
                + len(merge_log["tied_server_won"]),
            },
            resolution_rule=ResolutionRule.MOST_COMPLETE_WINS,
            metadata={
                "merged": True,
                "completeness_analysis": merge_log,
            },
        )

    def _resolve_server_assigns_final(
        self, pending_operation: PendingOperation, server_data: Optional[Dict[str, Any]]
    ) -> ConflictResolution:
        """
        Rule 5: Document Numbering (server_assigns_final)

        Server assigns final document numbers and CAE. Client placeholders replaced.

        Use case: Fiscal documents, invoices, CAE assignments
        """
        logger.debug(
            f"Applying server_assigns_final rule for {pending_operation.entity_type}",
            extra={"operation_id": pending_operation.id},
        )

        client_payload = pending_operation.payload or {}

        # Extract client placeholder values
        client_doc_number = client_payload.get("document_number")
        client_cae = client_payload.get("cae")

        # Server will assign final values
        merged = client_payload.copy()

        # Mark fields for server assignment
        fields_to_assign = []

        if client_doc_number and str(client_doc_number).startswith("TEMP-"):
            merged["document_number"] = None  # Server will assign
            fields_to_assign.append("document_number")

        if client_cae and str(client_cae).startswith("TEMP-"):
            merged["cae"] = None  # Server will assign
            fields_to_assign.append("cae")

        # Add server assignment metadata
        merged["_server_assignment_required"] = fields_to_assign

        return ConflictResolution(
            action=ResolutionAction.MERGE,
            merged_payload=merged,
            audit_log={
                "reason": "Document numbering: server assigns final values",
                "client_document_number": client_doc_number,
                "client_cae": client_cae,
                "fields_for_server_assignment": fields_to_assign,
                "client_payload": client_payload,
            },
            resolution_rule=ResolutionRule.SERVER_ASSIGNS_FINAL,
            metadata={
                "server_assignment_required": True,
                "fields_to_assign": fields_to_assign,
                "placeholder_detected": len(fields_to_assign) > 0,
                "message": f'Server will assign final values for: {", ".join(fields_to_assign)}',
            },
        )


# Convenience function for direct usage
def resolve_conflict(
    pending_operation: PendingOperation, server_data: Optional[Dict[str, Any]] = None
) -> ConflictResolution:
    """
    Convenience function to resolve a conflict.

    Args:
        pending_operation: Operation that needs conflict resolution
        server_data: Current server state (if available)

    Returns:
        ConflictResolution with action and merged data
    """
    resolver = ConflictResolver()
    return resolver.resolve(pending_operation, server_data)
