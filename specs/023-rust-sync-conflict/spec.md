# Feature Specification: Rust Sync Conflict Engine

**Feature Branch**: `023-rust-sync-conflict`
**Created**: 2026-02-27
**Status**: Draft
**Input**: Replace `_resolve_most_complete_wins()` in `conflict_resolver.py` with a Rust/PyO3 JSON merge function using `serde_json`. Accelerate the only non-trivial conflict resolution strategy for offline sync batch operations.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Single Conflict Resolution Parity (Priority: P1)

When a mobile user syncs a modified customer record while the server also has changes, the system merges both payloads by selecting the most complete value for each field. The merged result and the audit trail of merge decisions must be identical whether the merge runs in the native implementation or the accelerated path.

**Why this priority**: Correctness is non-negotiable. If the accelerated merge produces different results from the original implementation, data corruption occurs silently during sync.

**Independent Test**: Run the same 50+ field customer payload through both the original and accelerated merge paths. Compare merged output and merge decision log field-by-field. Can be validated with a single equivalence test suite.

**Acceptance Scenarios**:

1. **Given** a server payload and a client payload with overlapping fields, **When** the system resolves using `most_complete_wins`, **Then** the merged payload is byte-identical to the result from the original implementation
2. **Given** a merge operation on any payload, **When** the merge completes, **Then** the returned audit log contains exactly 5 categories (`client_won`, `server_won`, `tied_server_won`, `both_null`, `empty_string_normalized`) with identical field assignments as the original implementation
3. **Given** a field with a whitespace-only string on the client side and a non-empty value on the server side, **When** merged, **Then** the whitespace string is treated as empty and the server value wins

---

### User Story 2 - Batch Sync Acceleration (Priority: P2)

When a field worker reconnects after an offline session with 100+ pending operations, the batch merge of all `most_complete_wins` conflicts completes significantly faster than processing them one-by-one in the original implementation, reducing total sync time.

**Why this priority**: The primary performance motivation. Individual merges see modest speedup (2-4x), but batch processing of 100+ operations amplifies gains to 3-6x due to reduced garbage collection pressure and single-crossing overhead.

**Independent Test**: Generate 100 synthetic conflict pairs with 50-field payloads, time batch merge vs sequential original-implementation merge. Validate that batch path is at least 3x faster.

**Acceptance Scenarios**:

1. **Given** 100 conflict pairs each with 50 fields, **When** resolved as a batch, **Then** total merge time is at least 3x faster than processing them individually in the original implementation
2. **Given** a batch merge in progress, **When** other operations need to proceed, **Then** the batch merge does not block them (concurrency is maintained)

---

### User Story 3 - Graceful Fallback (Priority: P2)

When the accelerated merge component is unavailable (not installed, build failure, or import error), the system transparently falls back to the original Python implementation with no change in behavior or data integrity.

**Why this priority**: Equal to batch acceleration — a broken fallback means deployment failures or silent data loss.

**Independent Test**: Simulate unavailability of the accelerated component, run the full sync flow, verify all operations complete correctly using the original path.

**Acceptance Scenarios**:

1. **Given** the accelerated merge component is not available, **When** a `most_complete_wins` conflict is resolved, **Then** the original implementation handles it identically
2. **Given** a system log, **When** fallback occurs, **Then** a warning is logged indicating the fallback with the reason

---

### User Story 4 - Small Payload Efficiency Guard (Priority: P3)

When a conflict involves a payload with fewer than 20 fields, the system uses the original implementation directly, avoiding the overhead of serialization across the FFI boundary which would negate any performance benefit.

**Why this priority**: Without this guard, small payloads would be slower through the accelerated path than the original, due to serialization overhead (~20-40us) exceeding the merge time savings.

**Independent Test**: Merge a 5-field payload, verify it routes to the original implementation. Merge a 25-field payload, verify it routes to the accelerated path.

**Acceptance Scenarios**:

1. **Given** a payload with fewer than 20 fields, **When** `most_complete_wins` is invoked, **Then** the original implementation is used (no FFI crossing)
2. **Given** a payload with 20 or more fields, **When** `most_complete_wins` is invoked, **Then** the accelerated path is used

---

### Edge Cases

- What happens when both client and server payloads are empty? System raises a runtime error (SyncError) with a descriptive message. This intentionally diverges from the original implementation (which returns empty) as a new guard clause (FR-012).
- What happens when a field exists only in the client payload but not in the server? Client value is used (client wins for that field).
- What happens when both values are `null` for a field? The merged value is `null`, logged under `both_null`.
- What happens when a string field contains only whitespace (`"   "`, `"\t"`)? Normalized to `null` before comparison, logged under `empty_string_normalized`.
- What happens when client has a string and server has a number for the same field (mixed types)? Server value wins (falls to the catch-all branch).
- What happens when both values are booleans? Server value wins (no boolean comparison logic exists).
- What happens when both values are numbers? Server value wins (no numeric comparison logic exists).
- What happens with metadata fields (`id`, `created_at`, `updated_at`, `sync_version`)? Always take server value, skip comparison entirely.
- What happens when invalid JSON is passed to the accelerated merge? A runtime error is raised, the system falls back to the original implementation.
- What happens with deeply nested dict values? Only top-level key count is compared for dict fields; the dict with more keys wins. No recursive merge occurs.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST merge two JSON payloads by selecting the most complete value for each field, producing a result identical to the existing `_resolve_most_complete_wins()` logic (exception: both-empty guard clause per FR-012, which is new behavior not present in the original)
- **FR-002**: System MUST normalize whitespace-only strings (as determined by stripping all whitespace) to null before comparison
- **FR-003**: System MUST compare string fields by stripped length, list fields by element count, and dict fields by key count — client wins only when strictly greater; ties go to server
- **FR-004**: System MUST assign server value for all non-comparable types (booleans, numbers, mixed types) without any type-specific comparison
- **FR-005**: System MUST always use server value for metadata fields (`id`, `created_at`, `updated_at`, `sync_version`), skipping comparison entirely
- **FR-006**: System MUST accept a configurable list of metadata field names rather than hardcoding them
- **FR-007**: System MUST return both the merged payload and a merge decision log with exactly 5 categories: `client_won`, `server_won`, `tied_server_won`, `both_null`, `empty_string_normalized`
- **FR-008**: System MUST provide a batch entry point that processes multiple conflict pairs in a single call, allowing concurrent operations to proceed during batch processing
- **FR-009**: System MUST fall back to the original implementation when the accelerated component is unavailable, logging a warning
- **FR-010**: System MUST use the original implementation for payloads with fewer than 20 fields (configurable threshold)
- **FR-011**: System MUST raise a runtime error when given malformed input (invalid JSON), allowing the caller to handle it
- **FR-012**: System MUST reject merge operations where both payloads are empty by raising a runtime error (via the dedicated sync error type from FR-013) with a descriptive message. This is a new guard clause not present in the original implementation, which would silently return an empty result. Equivalence tests (SC-001) must exclude this edge case.
- **FR-013**: System MUST add a dedicated error type for sync-related failures, mapped to a standard runtime error at the FFI boundary
- **FR-014**: System MUST build and be available in the Docker container without additional configuration
- **FR-015**: System MUST pass the full existing test suite with zero regressions

### Key Entities

- **Conflict Pair**: Two JSON payloads (server and client) representing the same entity at different versions, requiring field-by-field merge resolution
- **Merge Decision Log**: A structured audit record tracking which side won each field and why, containing 5 categories that map to the merge rules
- **Metadata Fields**: A configurable set of field names that always take the server value without comparison (e.g., `id`, `created_at`, `updated_at`, `sync_version`)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Accelerated merge produces byte-identical merged payloads and identical merge decision logs as the original implementation for all test payloads
- **SC-002**: Batch processing of 100 conflict pairs (50 fields each) completes at least 3x faster than sequential original-implementation processing
- **SC-003**: Batch merge operations do not block concurrent operations (verified with a concurrency test)
- **SC-004**: Single merge operations (sub-20 fields) do not incur FFI overhead (routed to original implementation)
- **SC-005**: System operates correctly when the accelerated component is absent — all sync operations complete via fallback
- **SC-006**: Native test suite includes at least 8 test cases covering basic merge, deep nesting, null handling, type comparison, empty payloads, metadata passthrough, and mixed types
- **SC-007**: Merge decision log contains the same 5 categories with identical field assignments as the original implementation
- **SC-008**: Invalid JSON input raises a runtime error (mapped from the dedicated sync error type)
- **SC-009**: Docker container builds with sync functions available and importable
- **SC-010**: Full existing test suite passes with zero regressions
