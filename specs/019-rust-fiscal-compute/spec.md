# Feature Specification: Rust Fiscal Compute Engine

**Feature Branch**: `019-rust-fiscal-compute`
**Created**: 2026-02-26
**Status**: Draft
**Input**: Implement Rust versions of ARCA fiscal calculations, IVA breakdown computation, stock aggregation, and CUIT Modulo-11 validation via PyO3, consolidating duplicated fiscal math into a single Rust module.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - ARCA Amount Validation at Invoice Emission (Priority: P1)

When a business operator emits an electronic invoice through GRAVITEA, the system validates the master amount equation (ImpTotal = ImpNeto + ImpOpEx + ImpIVA + ImpTrib + ImpTotConc) before submitting to ARCA. Today this runs in Python; the Rust implementation must produce identical validation results with improved throughput on high-volume invoice batches.

**Why this priority**: This is the fiscal compliance gate — ARCA rejects invoices with centavo-level mismatches. Any deviation breaks invoice emission for all tenants. Must be bit-for-bit equivalent to the current Python validation.

**Independent Test**: Can be fully tested by submitting known ARCA test vectors (valid and invalid amount combinations) and verifying accept/reject decisions match the Python implementation exactly.

**Acceptance Scenarios**:

1. **Given** a set of 6 Decimal amount fields that satisfy the ARCA equation within dual tolerance (ABSOLUTE=0.01, RELATIVE=0.0001), **When** the system validates importes, **Then** validation passes without error.
2. **Given** a set of amount fields where the equation does NOT balance beyond tolerance, **When** the system validates importes, **Then** a validation error is raised with the exact same error message format as the current Python implementation.
3. **Given** the Rust module is unavailable (import fails), **When** the system validates importes, **Then** the Python fallback executes transparently with identical behavior.

---

### User Story 2 - IVA Breakdown Computation for Sales (Priority: P1)

When creating a sale that will become an electronic invoice, the system must compute the AlicIva breakdown — grouping line items by IVA rate and calculating per-rate neto (base imponible) and IVA importe. This breakdown is required by ARCA for Type A/B/M comprobantes. The Rust implementation computes this from raw line items and IVA rates, replacing the scattered Python logic.

**Why this priority**: Tied with P1 because every sale-to-invoice flow requires this computation. The AlicIva array structure must exactly match what ARCA's WSFEv1 expects.

**Independent Test**: Can be tested by providing a list of line items (price, quantity, IVA rate) and verifying the output AlicIva array matches expected per-rate subtotals, including the rate-to-ARCA-ID mapping (21% -> 5, 10.5% -> 4, etc.).

**Acceptance Scenarios**:

1. **Given** 5 line items across 3 IVA rates (21%, 10.5%, 0%), **When** the system computes IVA breakdown, **Then** it returns 3 AlicIva entries with correct base_imp and importe per rate, and correct ARCA IVA IDs.
2. **Given** line items that all share the same IVA rate, **When** the system computes IVA breakdown, **Then** it returns a single AlicIva entry with aggregated amounts.
3. **Given** a line item with an unknown IVA rate, **When** the system computes IVA breakdown, **Then** it defaults to IVA_21 (ARCA ID=5) for that item.

---

### User Story 3 - CUIT Validation Consolidation (Priority: P2)

Business operators enter CUIT numbers (Argentine tax IDs) when creating customers, suppliers, and invoice recipients. The Modulo-11 check digit validation is currently duplicated in two separate Python files. The Rust implementation provides a single authoritative validation function, eliminating the duplication.

**Why this priority**: Lower risk than amount validation (simpler algorithm), but high DRY value — consolidates logic from 2 files into 1 function.

**Independent Test**: Can be tested with a corpus of known valid CUITs, known invalid CUITs (bad check digit, wrong length, non-numeric), and boundary cases.

**Acceptance Scenarios**:

1. **Given** a valid 11-digit CUIT with correct Modulo-11 check digit, **When** the system validates the CUIT, **Then** validation passes without error.
2. **Given** a CUIT with an incorrect check digit, **When** the system validates it, **Then** a validation error is raised.
3. **Given** input that is not 11 digits or contains non-numeric characters, **When** the system validates it, **Then** a validation error is raised with a descriptive message.
4. **Given** a CUIT where Modulo-11 yields 10 (special case), **When** the system validates it, **Then** check digit 9 is expected per ARCA spec.

---

### User Story 4 - Batch Stock Aggregation with Concurrency (Priority: P2)

When the system displays stock summaries across multiple products and branches (e.g., a warehouse dashboard), it must aggregate stock levels from individual movement records. The Rust implementation performs this aggregation in a batch, releasing the Python GIL so other Django request threads can proceed during the computation.

**Why this priority**: Impacts UI responsiveness on stock-heavy views but doesn't block fiscal compliance. The GIL release is the key differentiator — without it, large aggregations block the entire Django process.

**Independent Test**: Can be tested by providing a batch of stock movement records (product, branch, quantity, type) and verifying aggregated results match per-product ORM queries.

**Acceptance Scenarios**:

1. **Given** 500 stock movement records across 50 products and 3 branches, **When** the system aggregates stock levels, **Then** per-product-branch totals match individual ORM-computed values exactly.
2. **Given** the aggregation is running, **When** another Django thread receives a request, **Then** the other thread is NOT blocked by the aggregation (GIL is released).
3. **Given** movement records with Decimal quantities, **When** passed to the Rust function as string representations, **Then** Decimal precision is preserved (no floating-point drift).

---

### User Story 5 - IVA Breakdown Validation (Priority: P3)

After the AlicIva array is computed or manually provided, the system validates that the breakdown entries are consistent with the comprobante header amounts (sum of AlicIva.importe = imp_iva, sum of AlicIva.base_imp = imp_neto) and that the breakdown is present/absent according to comprobante type rules (mandatory for A/B/M, prohibited for C).

**Why this priority**: This is the validation counterpart to US-2 (computation). Lower priority because it builds on the same rate-mapping infrastructure.

**Independent Test**: Can be tested with AlicIva arrays that intentionally mismatch header amounts, plus comprobante type edge cases.

**Acceptance Scenarios**:

1. **Given** a Type A comprobante with an empty AlicIva list, **When** the system validates IVA breakdown, **Then** a validation error is raised (AlicIva mandatory for Type A).
2. **Given** a Type C comprobante with a non-empty AlicIva list, **When** the system validates IVA breakdown, **Then** a validation error is raised (AlicIva prohibited for Type C).
3. **Given** AlicIva entries whose importe sum differs from imp_iva beyond tolerance, **When** the system validates IVA breakdown, **Then** a validation error is raised.

---

### Edge Cases

- What happens when all 6 amount fields in `validate_importes` are zero? (Valid — zero-value comprobantes exist for adjustments)
- How does the system handle Decimal values at the boundary of `rust_decimal`'s 28-digit precision? (GRAVITEA uses DECIMAL(17,3) — well within range, but edge tests should confirm)
- What happens when `aggregate_stock_levels` receives an empty list of movements? (Returns empty aggregation, no error)
- How does CUIT validation handle leading zeros? (The 11-digit string representation preserves them — "20-12345678-9" stored as "20123456789")
- What happens when the Rust module raises a RuntimeError? (Python wrapper catches and re-raises as ValueError for backward compatibility, per SPEC-018 pattern)
- What if a line item has a negative quantity or price? (Valid for credit notes — the system must handle negative Decimals correctly in IVA breakdown computation)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST validate the ARCA master amount equation (ImpTotal = ImpNeto + ImpOpEx + ImpIVA + ImpTrib + ImpTotConc) using dual-tolerance comparison (ABSOLUTE=0.01, RELATIVE=0.0001).
- **FR-002**: System MUST compute AlicIva breakdown from a list of line items, grouping by IVA rate and calculating per-rate base imponible and IVA importe.
- **FR-003**: System MUST map IVA percentage rates to ARCA AlicIva IDs (0%->3, 2.5%->9, 5%->8, 10.5%->4, 21%->5, 27%->6), defaulting to 21% (ID=5) for unknown rates.
- **FR-004**: System MUST validate CUIT numbers using the Modulo-11 algorithm, rejecting non-11-digit, non-numeric, or invalid-check-digit inputs.
- **FR-005**: System MUST handle the Modulo-11 special case where remainder equals 10 (expected check digit becomes 9).
- **FR-006**: System MUST aggregate stock levels across multiple products and branches from a batch of movement records, preserving Decimal precision.
- **FR-007**: System MUST release the Python GIL during batch stock aggregation to avoid blocking other request threads.
- **FR-008**: System MUST validate IVA breakdown entries against comprobante header amounts (sum checks within tolerance) and enforce presence/absence rules per comprobante type (mandatory for A/B/M, prohibited for C).
- **FR-009**: System MUST transport all Decimal values as strings across the language boundary (Python str -> Rust rust_decimal -> str -> Python Decimal) to preserve precision.
- **FR-010**: System MUST fall back to Python implementations when the Rust module is unavailable, with identical behavior visible to callers.
- **FR-011**: System MUST map Rust errors to the same Python exception types that callers currently expect (ValueError for validation failures) for backward compatibility.
- **FR-012**: System MUST handle empty and whitespace-only string inputs in Python wrappers before dispatching to Rust, matching existing Python guard behavior.

### Key Entities

- **Comprobante Amount Set**: The 6 Decimal fields (imp_total, imp_neto, imp_iva, imp_trib, imp_op_ex, imp_tot_conc) that form the ARCA balance equation.
- **AlicIva Entry**: A per-rate IVA breakdown record containing iva_id (ARCA rate code), base_imp (taxable base), and importe (IVA amount).
- **Line Item**: A sale line with price, quantity, and IVA rate percentage — input to IVA breakdown computation.
- **CUIT**: An 11-digit Argentine tax identification number validated by Modulo-11 algorithm.
- **Stock Movement Record**: A record with product ID, branch ID, quantity (Decimal), and movement type — input to batch aggregation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All fiscal validation functions produce identical accept/reject decisions as current Python implementations across a test corpus of 100+ known ARCA test vectors.
- **SC-002**: `validate_importes` and `calculate_iva_breakdown` execute at least 3x faster than their Python equivalents when measured on representative invoice data.
- **SC-003**: `aggregate_stock_levels` processes 500 movement records at least 3x faster than equivalent per-product ORM queries, and does not block concurrent Django request threads during computation.
- **SC-004**: `validate_cuit` is invoked from a single consolidated location, eliminating the current duplication across 2 files.
- **SC-005**: Decimal precision is preserved across the language boundary for all GRAVITEA field sizes (up to DECIMAL(17,3)) — no rounding drift or truncation compared to Python Decimal.
- **SC-006**: All functions operate correctly when the Rust module is absent, with Python fallbacks producing identical results.
- **SC-007**: The system's full test suite passes with zero regressions after the Rust compute functions are integrated.
- **SC-008**: The Docker image builds successfully with the compute functions available inside the container.

## Assumptions

- ARCA's 6 known IVA rates (0, 2.5, 5, 10.5, 21, 27) are exhaustive for current operations. If new rates are introduced, the Rust match expression and Python fallback must both be updated.
- `rust_decimal`'s 28 significant digits are sufficient for all GRAVITEA monetary fields (max DECIMAL(17,3) = 17 digits).
- Stock movement quantities are always representable as Decimal strings (no special float values like NaN or Infinity).
- The Python GIL release for `aggregate_stock_levels` is only beneficial for batch sizes above ~10 records; smaller batches can use the GIL-holding path without measurable impact.
- CUIT format is always stored as an 11-digit numeric string without hyphens or other separators.
- The existing `validate_iva_breakdown` function in `facturacion/validators.py` is the authoritative reference for IVA breakdown validation rules (FR-008).

## Dependencies

- **SPEC-017** (Rust Toolchain Bootstrap): Provides the PyO3/Maturin build pipeline, `gravitea_rust` package structure, and Docker multi-stage build.
- **SPEC-018** (Crypto Acceleration): Establishes the patterns for fallback dispatch, `_internal` test functions, error type mapping (RuntimeError -> ValueError), and backward-compatible Python wrappers.
