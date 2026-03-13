# Feature Specification: Custom Field Type Validator Acceleration

**Feature Branch**: `025-rust-custom-field-validator`
**Created**: 2026-02-28
**Status**: Draft
**Input**: Accelerate tenant-scoped custom field type validation by replacing the per-field Python type-checking loop with a single-pass compiled validator, following established acceleration patterns from SPEC-023/024.

## User Scenarios & Testing

### User Story 1 — Accelerated Batch Validation for Custom Fields (Priority: P1)

A tenant administrator has configured 20+ custom fields (text, integer, decimal, boolean, date, select) for their products. When a warehouse operator submits a product update with all custom fields populated, the system validates every field's type in a single compiled pass rather than iterating through Python type checks one by one.

**Why this priority**: This is the core acceleration — replacing N individual Python type checks with a single compiled call. Delivers the primary performance benefit and establishes the validation function.

**Independent Test**: Submit a product with 25 custom fields (mix of all 6 types, including a select field with 50+ choices), verify all fields validate correctly with correct error messages, and the accelerated path completes faster than the Python equivalent.

**Acceptance Scenarios**:

1. **Given** a tenant with 20 custom field definitions across all 6 types, **When** a user submits valid values for all fields, **Then** validation succeeds with zero errors returned.
2. **Given** a tenant with 20 custom field definitions, **When** a user submits intentionally wrong types (string for integer, number for boolean, etc.), **Then** each invalid field returns its specific error message matching the existing format exactly.
3. **Given** a select field with 50 choices, **When** a user submits a value not in the allowed list, **Then** the error message displays the allowed choices in the same format as the current system.
4. **Given** a date field, **When** a user submits "2026-13-45" (invalid but matching YYYY-MM-DD format), **Then** validation passes (format-only check, matching current behavior).

---

### User Story 2 — Output Parity Guarantee (Priority: P1)

Both the accelerated and standard validation paths produce identical results for any given input. Error messages, field ordering in error responses, and edge case handling are byte-for-byte equivalent.

**Why this priority**: Tied with US1 because incorrect validation would break data integrity for 5 production serializers across 3 business modules (sales, inventory, purchasing).

**Independent Test**: Run the same set of field definitions and custom data through both paths and compare output character-by-character for every field type and edge case.

**Acceptance Scenarios**:

1. **Given** valid values for each of the 6 field types, **When** validated through both paths, **Then** both return empty error results.
2. **Given** invalid values for each of the 6 field types, **When** validated through both paths, **Then** both return identical error messages for every field.
3. **Given** a select field with choices ["acero", "aluminio", "bronce"], **When** an invalid value is submitted, **Then** both paths return `Invalid choice. Allowed: ['acero', 'aluminio', 'bronce']` (with single quotes in the list format).
4. **Given** a boolean value submitted for an integer field, **When** validated through both paths, **Then** both reject it (boolean is NOT a valid integer despite subclass relationship).
5. **Given** a decimal value submitted for a decimal field (e.g., 9.99), **When** validated through both paths, **Then** both accept it.
6. **Given** fields with null values, **When** validated through both paths, **Then** both skip null values silently.
7. **Given** keys in custom data not present in field definitions, **When** validated through both paths, **Then** both ignore undefined keys.

---

### User Story 3 — Small Field Set Fallback (Priority: P2)

When a tenant has 5 or fewer custom field definitions, the system uses the standard validation path because the overhead of data serialization negates any acceleration benefit for small field counts.

**Why this priority**: Ensures the acceleration only activates where it provides real benefit, avoiding overhead for simple cases.

**Independent Test**: Submit custom data with 3 field definitions and verify the standard path is used; submit with 6 field definitions and verify the accelerated path is used.

**Acceptance Scenarios**:

1. **Given** a tenant with 3 custom field definitions, **When** custom data is validated, **Then** the standard path is used.
2. **Given** a tenant with 5 custom field definitions, **When** custom data is validated, **Then** the standard path is used (threshold is >5, not >=5).
3. **Given** a tenant with 6 custom field definitions, **When** custom data is validated, **Then** the accelerated path is used.

---

### User Story 4 — Graceful Degradation (Priority: P2)

When the compiled validator is not available (e.g., extension not installed), the system falls back to the standard Python validation path with a logged warning, ensuring zero downtime.

**Why this priority**: Production resilience — the system must never fail to validate custom fields, even without the acceleration module.

**Independent Test**: Simulate the compiled validator being unavailable, submit a batch of custom fields, verify correct validation output and a warning in the log.

**Acceptance Scenarios**:

1. **Given** the compiled validator is not available, **When** custom data with 20 fields is submitted, **Then** validation produces correct results using the standard path.
2. **Given** the compiled validator is not available, **When** the system initializes, **Then** a warning is logged indicating fallback mode.
3. **Given** the compiled validator is not available, **When** any request with custom fields is processed, **Then** no errors are raised due to the missing module.

---

### Edge Cases

- What happens when custom_data contains a key not defined in field definitions? → Silently ignored (not an error).
- What happens when a field value is null? → Skipped (null means "remove field" in merge semantics).
- What happens when a boolean value is submitted for an integer field? → Rejected (boolean is not a valid integer despite type hierarchy).
- What happens when a boolean value is submitted for a decimal field? → Rejected (boolean is not a valid decimal).
- What happens when an integer value (e.g., 5) is submitted for a decimal field? → Accepted (integers are valid decimals).
- What happens when a Decimal value is submitted for a decimal field? → Accepted (Decimal values are converted to float during serialization).
- What happens when the date "2026-02-29" is submitted? → Accepted (format-only validation, no calendar checks).
- What happens when the date "not-a-date" is submitted? → Rejected (does not match YYYY-MM-DD format).
- What happens when a select field has an empty choices list? → Any value is invalid (empty allowed list).
- What happens when a select field has null choices? → Any value is invalid (null treated as empty list).
- What happens when custom_data is an empty dict? → No errors (nothing to validate).
- What happens when all field definitions are inactive (empty definitions list)? → No errors (no definitions to check against).
- What happens with an unknown field type not in the 6 supported types? → Silently passes (no validation applied).

## Requirements

### Functional Requirements

- **FR-001**: System MUST validate all 6 custom field types: text (string), integer (whole number, not boolean), decimal (numeric including whole numbers, not boolean), boolean (true/false only), date (YYYY-MM-DD format string), and select (value from allowed choices list).
- **FR-002**: System MUST produce error messages identical to the current validation format for each field type: "Expected a text value.", "Expected an integer value.", "Expected a decimal value.", "Expected a boolean value.", "Expected a date in YYYY-MM-DD format.", and "Invalid choice. Allowed: ['choice1', 'choice2']".
- **FR-003**: System MUST return errors in the existing error structure format: a mapping of field key to list of error messages (e.g., `{"field_key": ["error message"]}`).
- **FR-004**: System MUST skip null values in custom data without producing errors (null = field removal in merge semantics).
- **FR-005**: System MUST silently ignore keys in custom data that have no corresponding field definition.
- **FR-006**: System MUST reject boolean values for integer fields (boolean is not a valid integer).
- **FR-007**: System MUST reject boolean values for decimal fields (boolean is not a valid decimal).
- **FR-008**: System MUST accept whole number values for decimal fields (a whole number is a valid decimal).
- **FR-009**: System MUST validate date fields using format-only pattern matching (YYYY-MM-DD), without calendar or leap year validation.
- **FR-010**: System MUST validate select fields using efficient lookup, returning the allowed choices list in the error message with single-quote formatting matching the current output.
- **FR-011**: System MUST use the accelerated path only when field definition count exceeds 5; otherwise use the standard path.
- **FR-012**: System MUST fall back to the standard validation path when the accelerated module is unavailable, with a warning logged at initialization.
- **FR-013**: System MUST preserve the existing `_validate_field_value()` method for backward compatibility (direct callers, including unit tests, must continue to work).
- **FR-014**: System MUST NOT modify required field checking, merge semantics, cache lookup, or default injection logic — these remain in the existing code.
- **FR-015**: System MUST produce zero new regressions in the existing 40+ custom field tests across 4 test files.

### Key Entities

- **TenantFieldDefinition**: Per-tenant custom field metadata — defines field_key, field_type (one of 6 types), choices (for select type), required flag, and other configuration. Scoped by tenant and entity type.
- **Custom Data**: A key-value mapping submitted with entity create/update requests. Keys correspond to field_key values; values are the user-provided data to validate against field type rules.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Validation of 20+ custom fields completes at least 2x faster via the accelerated path compared to the standard path.
- **SC-002**: Both validation paths produce byte-identical error output for all 6 field types across valid, invalid, and edge case inputs (0 parity differences).
- **SC-003**: Automated test suite includes at least 10 compiled-level tests covering each field type (valid + invalid) and edge cases, plus at least 15 integration tests covering parity, threshold routing, and fallback behavior.
- **SC-004**: All existing 40+ custom field tests pass with zero modifications (backward compatibility preserved).
- **SC-005**: System correctly routes to standard path for field counts of 5 or fewer and to accelerated path for counts above 5.
- **SC-006**: System operates correctly without the acceleration module, logging a warning and using the standard path with no errors or degraded functionality.

## Assumptions

- The instruction document `Docs/Temp-prompting/025/instruction-specify.md` provides the authoritative technical context and architecture decisions for implementation.
- Custom field definitions are cached with a 60-second TTL on the application side; no additional caching is needed within the validator itself.
- The acceleration threshold of >5 fields balances serialization overhead against validation gain based on prior analysis (serialization overhead ~15-30 microseconds).
- Date format validation intentionally does NOT validate calendar correctness (e.g., February 30th passes) — this matches the current system behavior and changing it is out of scope.
- The select field error message format uses single-quoted list representation (e.g., `['a', 'b']`) — the accelerated path must reproduce this exactly.
- Five production serializers across three modules (sales, inventory, purchasing) depend on the custom field mixin; parity testing must cover this blast radius.

## Scope Boundaries

**In scope**:
- Type validation logic for 6 field types (the inner loop)
- Dispatcher with threshold guard and fallback
- Parity tests between both validation paths
- Integration with existing validation flow

**Out of scope**:
- Required field checking (stays in existing code — requires merge context with existing data)
- Default value injection (stays in existing code)
- Cache management for field definitions (stays in existing code)
- Schema migration or model changes
- UI changes
- New field types beyond the existing 6

## Dependencies

- SPEC-017 (Rust Toolchain Bootstrap) — MUST be complete (provides build infrastructure)
- SPEC-023/024 — provides established dispatcher pattern to follow
