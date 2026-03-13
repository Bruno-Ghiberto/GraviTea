# Feature Specification: ARCA CAEA Batch Builder Acceleration

**Feature Branch**: `024-rust-arca-batch`
**Created**: 2026-02-28
**Status**: Draft
**Input**: Accelerate CAEA batch request construction for ARCA quincena reporting with Rust/PyO3. Targets the inner loop of `CAEAService.informar_comprobantes()` where 20-100 comprobantes are serialized into SOAP request structures.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - CAEA Batch Reporting Under Deadline (Priority: P1)

A tenant accountant with offline point-of-sale locations needs to report all comprobantes issued during a CAEA fortnight before the ARCA deadline (fch_tope_inf). The system must build the batch request structure for 20-100 comprobantes reliably and quickly, freeing the application to handle other requests during the build.

**Why this priority**: This is the core use case. CAEA quincena deadlines are non-negotiable — late reporting results in ARCA penalties. The batch builder must complete without GC jitter or timeout risk.

**Independent Test**: Can be fully tested by providing a batch of 50 sample comprobantes and verifying the output matches the exact ARCA SOAP structure, with the accelerated path completing in under 5ms.

**Acceptance Scenarios**:

1. **Given** a batch of 50 comprobantes with IVA breakdowns and tributos, **When** the system builds the batch request, **Then** the output matches the exact ARCA SOAP dict structure with correct key names, nesting, and float values.
2. **Given** a batch of 50 comprobantes, **When** the system uses the accelerated path, **Then** the batch builds in under 5ms and does not block other operations during construction.
3. **Given** a batch of 100 comprobantes (maximum expected), **When** the system builds the request, **Then** all comprobantes are correctly serialized with no data loss or truncation.

---

### User Story 2 - Small Batch Fallback (Priority: P2)

When a tenant reports fewer than 11 comprobantes in a CAEA period (common for low-volume locations), the system should use the standard processing path since the overhead of cross-language communication negates any speed benefit for small batches.

**Why this priority**: Ensures the threshold guard works correctly, avoiding unnecessary overhead for small batches while maintaining correctness.

**Independent Test**: Can be tested by sending a batch of 5 comprobantes and verifying the standard path is used, producing identical output to the accelerated path.

**Acceptance Scenarios**:

1. **Given** a batch of 5 comprobantes, **When** the system builds the batch request, **Then** the standard processing path is used (not the accelerated path).
2. **Given** a batch of 11 comprobantes, **When** the system builds the batch request, **Then** the accelerated path is used.
3. **Given** a batch of exactly 10 comprobantes, **When** the system builds the batch request, **Then** the standard path is used (threshold is >10, not >=10).

---

### User Story 3 - Graceful Degradation (Priority: P2)

When the accelerated processing engine is unavailable (e.g., deployment without the compiled extension), the system must automatically fall back to the standard Python processing path with a logged warning, ensuring CAEA reporting is never blocked.

**Why this priority**: Deployment flexibility — the system must work in environments where the compiled extension cannot be installed.

**Independent Test**: Can be tested by simulating absence of the compiled extension and verifying the batch builds correctly using the fallback path.

**Acceptance Scenarios**:

1. **Given** the accelerated engine is unavailable, **When** a batch of 50 comprobantes is processed, **Then** the system uses the standard path and produces correct output.
2. **Given** the accelerated engine is unavailable, **When** the system initializes, **Then** a warning is logged indicating fallback mode.
3. **Given** the accelerated engine becomes unavailable after deployment, **When** any batch is processed, **Then** no errors are raised and output remains correct.

---

### User Story 4 - Output Parity Guarantee (Priority: P1)

Regardless of which processing path is used (accelerated or standard), the output must be structurally identical. ARCA rejects requests with any deviation in key names, nesting structure, or value types. A single misnamed key means the entire batch is rejected.

**Why this priority**: ARCA integration correctness is non-negotiable. The accelerated path must produce identical output to the standard path for any given input.

**Independent Test**: Can be tested by running the same batch through both paths and comparing the JSON output character-by-character.

**Acceptance Scenarios**:

1. **Given** a batch with all optional fields populated (IVA, tributos, associated comprobantes, service dates), **When** processed by both paths, **Then** the outputs are identical.
2. **Given** a comprobante with Concepto 2 (services), **When** processed, **Then** service date fields (`FchServDesde`, `FchServHasta`, `FchVtoPago`) are included in the output.
3. **Given** a comprobante with Concepto 1 (products), **When** processed, **Then** service date fields are absent from the output.
4. **Given** amount fields like `"123.45"`, **When** converted to float, **Then** both paths produce identical IEEE 754 values.

---

### Edge Cases

- What happens when a comprobante has tributos data but `imp_trib` is `"0"`? The tributos section must be omitted (matching current behavior where `float("0") > 0` is False).
- What happens when a `CbteAsoc` item lacks a `cuit` field? The system must use the tenant's CUIT (the `default_cuit` parameter) as fallback.
- What happens when `mon_id` is absent? Default to `"PES"` (Argentine Peso).
- What happens when `mon_cotiz` is absent? Default to `1` (1:1 exchange rate).
- What happens when `alic_iva` is present but empty (`[]`)? The IVA section must be omitted — an empty array is treated as absent.
- What happens when the batch contains a single comprobante and is above the threshold? Should never occur (threshold is >10), but both paths handle single items correctly.
- What happens with very large float values (e.g., `"99999999.99"`)? Both paths must produce the same f64 representation without precision loss for 2-decimal amounts.
- What happens when `imp_trib` is negative? The tributos guard checks `> 0`, so negative values cause tributos to be omitted even if tributos data is present.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST build the CAEA batch request detail list (`det_list`) from a list of comprobante dicts, a CAEA code, and a default CUIT.
- **FR-002**: System MUST route batches of >10 comprobantes to the accelerated processing path when available.
- **FR-003**: System MUST route batches of <=10 comprobantes to the standard processing path regardless of accelerated engine availability.
- **FR-004**: System MUST fall back to the standard processing path when the accelerated engine is unavailable, logging a warning at initialization.
- **FR-005**: System MUST produce output with exact ARCA SOAP key names: `Concepto`, `DocTipo`, `DocNro`, `CbteDesde`, `CbteHasta`, `CbteFch`, `ImpTotal`, `ImpTotConc`, `ImpNeto`, `ImpOpEx`, `ImpTrib`, `ImpIVA`, `MonId`, `MonCotiz`, `CAEA`.
- **FR-006**: System MUST convert all amount fields (`imp_total`, `imp_neto`, `imp_iva`, `imp_trib`, `imp_op_ex`, `imp_tot_conc`, `mon_cotiz`) from decimal-as-string to float, matching Python `float()` output exactly.
- **FR-007**: System MUST include service date fields (`FchServDesde`, `FchServHasta`, `FchVtoPago`) only when `concepto` is 2 (services) or 3 (products and services).
- **FR-008**: System MUST build the IVA breakdown as `{"Iva": {"AlicIva": [{"Id": int, "BaseImp": float, "Importe": float}]}}` when `alic_iva` is present and non-empty.
- **FR-009**: System MUST build the tributos section as `{"Tributos": {"Tributo": [{"Id": int, "Desc": str, "BaseImp": float, "Alic": float, "Importe": float}]}}` only when `tributos` is present, non-empty, AND `imp_trib > 0`.
- **FR-010**: System MUST build associated comprobantes as `{"CbtesAsoc": {"CbteAsoc": [{"Tipo": int, "PtoVta": int, "Nro": int, "Cuit": str}]}}` when `cbtes_asoc` is present and non-empty.
- **FR-011**: System MUST use the `default_cuit` parameter as fallback when a `CbteAsoc` item does not include a `cuit` value.
- **FR-012**: System MUST default `mon_id` to `"PES"` when absent from input.
- **FR-013**: System MUST default `mon_cotiz` to `"1"` (converting to float `1.0`) when absent from input.
- **FR-014**: System MUST omit optional sections (IVA, Tributos, CbtesAsoc, service dates) entirely from the output when not applicable — never include them as null, empty objects, or empty arrays.
- **FR-015**: System MUST release the processing thread during accelerated batch construction so other operations can proceed concurrently.
- **FR-016**: System MUST NOT modify the outer request wrapper (`fe_cab_req`, `fe_det_req` structure) — only the inner detail list construction is accelerated.
- **FR-017**: System MUST produce identical output from both processing paths (accelerated and standard) for any given input (parity guarantee).

### Key Entities

- **Comprobante Input**: A dict representing one invoice to report. Contains identification fields (tipo, document, number range), amount fields (6 decimal-as-string values), optional nested arrays (IVA rates, tributos, associated comprobantes), and conditional service dates (for Concepto 2 or 3).
- **FECAEADetRequest**: The output structure for one comprobante in ARCA's SOAP format. Contains PascalCase keys (with exceptions: `ImpIVA` and `CAEA` are ALL-CAPS), float amounts, and nested wrapper objects for IVA/tributos/associated comprobantes.
- **CAEA Code**: A 14-digit authorization code pre-obtained from ARCA for offline invoicing, stamped on every comprobante in the batch.
- **Default CUIT**: The tenant's CUIT used as fallback for associated comprobante references lacking their own CUIT.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Batch of 50 comprobantes (with IVA and tributos) builds in under 5ms via the accelerated path.
- **SC-002**: Both processing paths produce identical output for any batch of 1-100 comprobantes with all field combinations (parity verified by automated tests).
- **SC-003**: At least 10 automated tests cover: small batch, large batch, service dates, IVA breakdown, tributos, associated comprobantes, defaults, edge cases, parity, and fallback.
- **SC-004**: The containerized deployment includes the accelerated engine and can import it successfully.
- **SC-005**: Full existing test suite passes with zero regressions after integration.
- **SC-006**: Batches of <=10 comprobantes are processed by the standard path (threshold guard verified).

## Assumptions

- Input comprobante dicts always contain the required keys (`concepto`, `doc_tipo`, `doc_nro`, `cbte_desde`, `cbte_hasta`, `cbte_fch`, and all 6 amount fields). Missing required keys are a caller error, not handled by this spec.
- Amount values arrive as string representations of decimal numbers with at most 2 decimal places.
- Date fields (`cbte_fch`, `fch_serv_desde`, `fch_serv_hasta`, `fch_vto_pago`) arrive as pre-formatted `YYYYMMDD` strings — no date parsing or validation is performed by the batch builder.
- All comprobantes in a batch share the same `cbte_tipo` and `punto_venta` (enforced by the caller, not the batch builder).
- The existing `CAEAService.informar_comprobantes()` method continues to handle the outer wrapper, SOAP call, response parsing, and error handling.
- Maximum batch size in practice is ~100 comprobantes per CAEA fortnight per punto de venta.

## Dependencies

- SPEC-017 (Rust Toolchain Bootstrap) — MUST be complete (provides PyO3, Maturin, Docker integration).
- SPEC-019 (Rust Fiscal Compute) — benefits from shared decimal infrastructure and serialization crates.
- SPEC-023 (Rust Sync Conflict) — benefits from shared JSON serialization and dispatcher pattern template.
