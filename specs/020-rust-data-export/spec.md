# Feature Specification: Rust Data Export Pipeline

**Feature Branch**: `020-rust-data-export`
**Created**: 2026-02-26
**Status**: Draft
**Input**: Rust CSV and XLSX data export engine for the reportes app's ExportJob processing
**Depends on**: SPEC-017 (Rust Toolchain Bootstrap)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - CSV Export Generation (Priority: P1)

A back-office user triggers a report export in CSV format. The system generates a CSV file from the report data containing properly ordered columns, Spanish-accented characters (á, é, ñ, ü), and a UTF-8 BOM so the file opens correctly in Microsoft Excel without manual encoding configuration.

**Why this priority**: CSV is the most common export format. Users frequently open exports in Excel, and broken Spanish characters cause immediate support escalations. The UTF-8 BOM is critical for the Argentine market where every business name and address contains accented characters.

**Independent Test**: Can be fully tested by providing a list of rows with Spanish text and verifying the output bytes contain the BOM prefix and correctly encoded characters. Delivers immediate value — users get working CSV exports.

**Acceptance Scenarios**:

1. **Given** a dataset of 100 rows with 5 columns including Spanish text, **When** CSV generation is requested with an ordered header list, **Then** the output is a byte array starting with UTF-8 BOM (`\xEF\xBB\xBF`) followed by correctly ordered CSV content.
2. **Given** a dataset with columns ["Producto", "Precio", "Cantidad"], **When** CSV generation is requested with headers in that order, **Then** the CSV header row matches that exact column order regardless of dictionary key order.
3. **Given** an empty header list, **When** CSV generation is requested, **Then** the output contains only the UTF-8 BOM (3 bytes).
4. **Given** a row where a column name in the header list has no matching key in the row data, **When** CSV generation is requested, **Then** the missing value is written as an empty cell (not an error).

---

### User Story 2 - XLSX Export Generation (Priority: P1)

A back-office user triggers a report export in Excel format. The system generates an XLSX file from the report data with numeric values detected and written as Excel numbers (not text), column widths optionally customizable, and Spanish characters rendered correctly.

**Why this priority**: Excel is the preferred format for accountants and managers who need to perform calculations on exported data. Numbers stored as text break SUM/AVERAGE formulas — automatic numeric detection is essential.

**Independent Test**: Can be fully tested by providing rows with mixed string and numeric values, generating the XLSX, and verifying that numeric cells are stored as numbers and text cells as text. Delivers immediate value — users get calculation-ready Excel exports.

**Acceptance Scenarios**:

1. **Given** a dataset where column "Precio" contains "1250.50", **When** XLSX generation is requested, **Then** the cell is written as the number 1250.50 (not the string "1250.50").
2. **Given** a dataset where column "Nombre" contains "Compañía Argentina S.A.", **When** XLSX generation is requested, **Then** the cell contains the text with accented characters preserved.
3. **Given** column width overrides `{"Nombre": 30.0, "Precio": 12.0}`, **When** XLSX generation is requested, **Then** the "Nombre" column is 30 units wide, "Precio" is 12 units wide, and all other columns use auto-width.
4. **Given** no column width overrides (parameter omitted), **When** XLSX generation is requested, **Then** all columns use auto-width.
5. **Given** a value "not-a-number" in a numeric-looking column, **When** XLSX generation is requested, **Then** the value is written as text (no error from failed numeric parse).

---

### User Story 3 - Large Dataset Performance (Priority: P2)

A back-office user exports a large report (10,000+ rows). The system generates the export file within the performance target while releasing the processing thread so other users' requests continue to be served without delay.

**Why this priority**: Large exports are less frequent than small ones, but when they happen, blocking other users creates a poor experience for everyone. Thread release ensures the system remains responsive during heavy exports.

**Independent Test**: Can be tested by generating a 10,000-row dataset and measuring generation time. Thread release can be verified by confirming concurrent operations complete during generation.

**Acceptance Scenarios**:

1. **Given** a dataset of 10,000 rows with 10 columns, **When** CSV generation is requested, **Then** the output is produced in under 2 seconds.
2. **Given** a dataset of 10,000 rows with 10 columns, **When** XLSX generation is requested, **Then** the output is produced in under 2 seconds.
3. **Given** a large export is in progress, **When** another user makes a concurrent request, **Then** the concurrent request is served without waiting for the export to complete.

---

### User Story 4 - Graceful Fallback (Priority: P3)

When the accelerated export engine is unavailable (e.g., missing native extension after a deployment issue), the system falls back to a standard implementation so exports still work, even if slower.

**Why this priority**: Operational resilience. A deployment issue with the native extension should degrade performance, not break functionality entirely.

**Independent Test**: Can be tested by simulating the absence of the native extension and verifying that export functions still produce valid output.

**Acceptance Scenarios**:

1. **Given** the native export engine is not available, **When** CSV generation is requested, **Then** the system uses a fallback implementation and produces a valid CSV with BOM.
2. **Given** the native export engine is not available, **When** XLSX generation is requested, **Then** the system uses a fallback implementation and produces a valid XLSX file.
3. **Given** the native engine becomes available again, **When** the next export is requested, **Then** the system automatically uses the accelerated engine without manual intervention.

---

### Edge Cases

- What happens when a row contains a value with commas, quotes, or newlines? CSV output must properly escape these per RFC 4180.
- What happens when a numeric-looking value is extremely large (e.g., "99999999999999999.99")? The system should handle it without overflow — write as text if it exceeds float64 precision.
- What happens when `headers` contains duplicate column names? The system should write all columns (duplicates included) in the specified order.
- What happens when `rows` is an empty list but `headers` is non-empty? CSV should output the header row with BOM. XLSX should output a workbook with headers only.
- What happens when a column width override references a column not in `headers`? The orphan width entry is silently ignored.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST generate CSV output as a byte array with UTF-8 BOM prefix (`\xEF\xBB\xBF`).
- **FR-002**: System MUST order CSV and XLSX columns according to the provided header list, not by dictionary key order.
- **FR-003**: System MUST write missing column values (header present but no matching key in row) as empty cells.
- **FR-004**: System MUST generate XLSX output as a valid .xlsx byte array openable by Microsoft Excel.
- **FR-005**: System MUST auto-detect numeric values in XLSX generation — values parseable as floating-point numbers are written as Excel numbers; all others as text.
- **FR-006**: System MUST support optional per-column width overrides for XLSX generation, with unspecified columns using auto-width.
- **FR-007**: System MUST properly escape CSV values containing commas, double quotes, or newlines per RFC 4180.
- **FR-008**: System MUST release the processing thread during generation so concurrent requests are not blocked.
- **FR-009**: System MUST handle empty inputs gracefully — empty headers produce a minimal valid file; empty rows with headers produce a headers-only file.
- **FR-010**: System MUST provide a fallback implementation when the accelerated engine is unavailable, producing identical output format (CSV with BOM, valid XLSX).
- **FR-011**: System MUST preserve Spanish and other UTF-8 characters (á, é, í, ó, ú, ñ, ü) in both CSV and XLSX output.
- **FR-012**: System MUST be available within the containerized deployment without additional runtime dependencies.

### Key Entities

- **Export Request**: A request containing rows (list of key-value records), an ordered header list, and optional format-specific settings (column widths for XLSX).
- **Export Output**: A byte array representing the generated file (CSV or XLSX), ready to be written to storage or streamed to the user.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A 10,000-row, 10-column dataset generates a CSV file in under 2 seconds.
- **SC-002**: A 10,000-row, 10-column dataset generates an XLSX file in under 2 seconds.
- **SC-003**: Generated CSV files open in Microsoft Excel with Spanish characters displayed correctly (no mojibake) without manual encoding selection.
- **SC-004**: Generated XLSX files contain numeric cells that participate in Excel formulas (SUM, AVERAGE) without "number stored as text" warnings.
- **SC-005**: Concurrent user requests complete without measurable delay while a large export is being generated.
- **SC-006**: Export functions produce valid output when the accelerated engine is unavailable (fallback mode).
- **SC-007**: The containerized deployment includes the export engine and passes all export-related automated tests.
- **SC-008**: The full automated test suite passes with zero regressions after the export engine is added.

## Assumptions

- All data values are pre-converted to strings by the calling application before reaching the export engine. The engine does not perform type conversion from dates, decimals, or booleans — it receives strings only.
- Column width units for XLSX follow the standard Excel character-width unit (approximately the width of the character "0" in the default font).
- The calling application is responsible for file storage, naming, and delivery to the user. The export engine only produces in-memory byte arrays.
- PDF export is explicitly excluded from this specification and remains in the calling application's domain.
- The `reportes` app skeleton already exists with models for `ReportDefinition`, `SavedReport`, and `ExportJob`. Wiring the export engine to these models is a separate specification.
