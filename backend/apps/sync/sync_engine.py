"""
Sync Conflict Engine dispatcher — Rust-accelerated merge_most_complete
with Python fallback.

SPEC-023: Replaces _resolve_most_complete_wins() field-level merge logic
with compiled Rust serde_json merge via PyO3.

Two functions:
  merge_most_complete(server_json, client_json, metadata_fields_json)
    → (merged_json, merge_log_json)
  merge_most_complete_batch(pairs_json, metadata_fields_json)
    → JSON array of {merged, merge_log}
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

_USE_RUST: bool

try:
    from gravitea_rust import (  # type: ignore[import-untyped]
        merge_most_complete as _rust_merge,
        merge_most_complete_batch as _rust_merge_batch,
    )
    _USE_RUST = True
except (ImportError, OSError):
    _USE_RUST = False
    logger.warning(
        "gravitea_rust sync engine not available — using Python fallback"
    )

# Threshold: payloads with fewer fields than this stay in Python path.
# Payloads with >= this many fields are routed to Rust.
_RUST_FIELD_THRESHOLD = 20

_DEFAULT_METADATA_FIELDS = ["id", "created_at", "updated_at", "sync_version"]


def merge_most_complete(
    server_data: dict[str, Any],
    client_data: dict[str, Any],
    metadata_fields: list[str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Merge two payloads using most-complete-wins strategy.

    Dispatches to Rust for payloads with >= _RUST_FIELD_THRESHOLD fields
    when the Rust extension is available. Falls back to Python otherwise.

    Args:
        server_data: Server-side payload dict.
        client_data: Client-side payload dict.
        metadata_fields: Fields that always use server value (not compared).

    Returns:
        (merged_dict, merge_log_dict)

    Raises:
        RuntimeError: If both payloads are empty (FR-012).
    """
    if metadata_fields is None:
        metadata_fields = _DEFAULT_METADATA_FIELDS

    field_count = len(set(server_data.keys()) | set(client_data.keys()))

    if _USE_RUST and field_count >= _RUST_FIELD_THRESHOLD:
        return _merge_rust(server_data, client_data, metadata_fields)
    return _merge_python(server_data, client_data, metadata_fields)


def merge_most_complete_batch(
    pairs: list[dict[str, dict[str, Any]]],
    metadata_fields: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Batch merge multiple server/client pairs.

    Dispatches to Rust batch function (GIL released) when available
    and all pairs exceed the field threshold. Falls back to Python otherwise.

    Args:
        pairs: List of {"server": {...}, "client": {...}} dicts.
        metadata_fields: Fields that always use server value.

    Returns:
        List of {"merged": {...}, "merge_log": {...}} dicts.
    """
    if metadata_fields is None:
        metadata_fields = _DEFAULT_METADATA_FIELDS

    if _USE_RUST and _should_use_rust_batch(pairs):
        return _merge_batch_rust(pairs, metadata_fields)
    return _merge_batch_python(pairs, metadata_fields)


def _should_use_rust_batch(pairs: list[dict[str, dict[str, Any]]]) -> bool:
    """Check if any pair in the batch has enough fields for Rust routing."""
    for pair in pairs:
        server = pair.get("server", {})
        client = pair.get("client", {})
        field_count = len(set(server.keys()) | set(client.keys()))
        if field_count >= _RUST_FIELD_THRESHOLD:
            return True
    return False


def _merge_rust(
    server_data: dict[str, Any],
    client_data: dict[str, Any],
    metadata_fields: list[str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Rust-accelerated single merge."""
    server_json = json.dumps(server_data)
    client_json = json.dumps(client_data)
    meta_json = json.dumps(metadata_fields)

    merged_str, log_str = _rust_merge(server_json, client_json, meta_json)

    return json.loads(merged_str), json.loads(log_str)


def _merge_batch_rust(
    pairs: list[dict[str, dict[str, Any]]],
    metadata_fields: list[str],
) -> list[dict[str, Any]]:
    """Rust-accelerated batch merge (GIL released)."""
    pairs_json = json.dumps(pairs)
    meta_json = json.dumps(metadata_fields)

    result_str = _rust_merge_batch(pairs_json, meta_json)
    return json.loads(result_str)


def _merge_python(
    server_data: dict[str, Any],
    client_data: dict[str, Any],
    metadata_fields: list[str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Python fallback for single merge — mirrors conflict_resolver.py logic."""
    if not server_data and not client_data:
        raise RuntimeError("Both payloads empty")

    metadata_set = set(metadata_fields)
    merged: dict[str, Any] = {}
    merge_log: dict[str, list[str]] = {
        "client_won": [],
        "server_won": [],
        "tied_server_won": [],
        "both_null": [],
        "empty_string_normalized": [],
    }

    all_keys = set(server_data.keys()) | set(client_data.keys())

    for key in all_keys:
        server_value = server_data.get(key)
        client_value = client_data.get(key)

        if key in metadata_set:
            merged[key] = server_value
            continue

        # Normalize whitespace-only strings to None
        if isinstance(client_value, str) and not client_value.strip():
            client_value = None
            merge_log["empty_string_normalized"].append(f"{key}_client")

        if isinstance(server_value, str) and not server_value.strip():
            server_value = None
            merge_log["empty_string_normalized"].append(f"{key}_server")

        # Null comparison
        if client_value is None and server_value is None:
            merged[key] = None
            merge_log["both_null"].append(key)
        elif client_value is not None and server_value is None:
            merged[key] = client_value
            merge_log["client_won"].append(key)
        elif client_value is None and server_value is not None:
            merged[key] = server_value
            merge_log["server_won"].append(key)
        else:
            # Both non-null — compare completeness
            if isinstance(client_value, str) and isinstance(server_value, str):
                if len(client_value.strip()) > len(server_value.strip()):
                    merged[key] = client_value
                    merge_log["client_won"].append(key)
                else:
                    merged[key] = server_value
                    merge_log["tied_server_won"].append(key)
            elif isinstance(client_value, list) and isinstance(server_value, list):
                if len(client_value) > len(server_value):
                    merged[key] = client_value
                    merge_log["client_won"].append(key)
                else:
                    merged[key] = server_value
                    merge_log["tied_server_won"].append(key)
            elif isinstance(client_value, dict) and isinstance(server_value, dict):
                if len(client_value) > len(server_value):
                    merged[key] = client_value
                    merge_log["client_won"].append(key)
                else:
                    merged[key] = server_value
                    merge_log["tied_server_won"].append(key)
            else:
                merged[key] = server_value
                merge_log["tied_server_won"].append(key)

    return merged, merge_log


def _merge_batch_python(
    pairs: list[dict[str, dict[str, Any]]],
    metadata_fields: list[str],
) -> list[dict[str, Any]]:
    """Python fallback for batch merge."""
    results = []
    for pair in pairs:
        server = pair.get("server", {})
        client = pair.get("client", {})
        merged, merge_log = _merge_python(server, client, metadata_fields)
        results.append({"merged": merged, "merge_log": merge_log})
    return results
