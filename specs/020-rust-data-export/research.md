# Research: Rust Data Export Pipeline (SPEC-020)

**Branch**: `020-rust-data-export` | **Date**: 2026-02-26

## R-001: rust_xlsxwriter Column Width API

**Decision**: Use `worksheet.set_column_width(col_index, width)` with character-width units. Use `worksheet.autofit()` for columns without explicit overrides.

**Rationale**: The `rust_xlsxwriter 0.92` API provides:
- `set_column_width(col: u16, width: f64)` — character-width units (Excel default)
- `set_column_width_pixels(col: u16, pixels: u16)` — pixel units (alternative)
- `autofit()` — automatic width calculation based on cell content
- Maximum width: 255 characters (Excel hard limit)

Column index is 0-based `u16`, not column name. Our Rust code must map header names to column indices via the `headers` list position.

**Implementation pattern**:
```
1. Write all data to worksheet
2. Call worksheet.autofit() for baseline widths
3. For each entry in column_widths HashMap:
   a. Find column index from headers list
   b. Call worksheet.set_column_width(index, width) to override
```

Autofit runs first, then explicit overrides apply on top. This means columns with overrides get the user-specified width; columns without get auto-calculated width.

**Alternatives considered**:
- Pixel-based widths: Rejected — character-width units match the spec and are the Excel standard.
- Manual width calculation (no autofit): Rejected — autofit is built-in and well-tested.

## R-002: UTF-8 BOM Detection by Excel Versions

**Decision**: Prepend `\xEF\xBB\xBF` (3-byte UTF-8 BOM) to all CSV output. This is the only reliable way to ensure Excel opens CSV with correct encoding.

**Rationale**:
- **Excel 2016+**: Requires UTF-8 BOM to detect encoding. Without BOM, Excel defaults to the system's legacy codepage (e.g., Windows-1252), garbling Spanish characters.
- **Excel 365**: Same behavior as Excel 2016+ — BOM required.
- **LibreOffice Calc**: Handles UTF-8 BOM correctly during import. Preserves BOM on re-save when present.
- **Google Sheets**: Handles UTF-8 with or without BOM.

**Risk**: None. BOM is universally supported across modern spreadsheet applications. The 3 bytes are invisible to end users.

**Alternatives considered**:
- Relying on Excel's auto-detection: Rejected — fails for non-ASCII characters without BOM.
- Using UTF-16 encoding: Rejected — doubles file size, incompatible with standard CSV tools.

## R-003: Vec<HashMap> Serialization Cost for 10K Rows

**Decision**: Use `Vec<HashMap<String, String>>` as the PyO3 function signature. Accept ~50-100ms FFI conversion overhead as acceptable.

**Rationale**:
- PyO3 performs a **deep copy** when converting `list[dict[str, str]]` to `Vec<HashMap<String, String>>`. Each string is copied from Python heap to Rust heap.
- For 10K rows x 10 columns = 100K string entries, estimated overhead is 50-100ms.
- This is acceptable because the actual generation work (500ms-2s) dominates. The FFI cost is <10% of total time.
- After conversion completes, `py.allow_threads()` releases the GIL so CSV/XLSX generation runs without blocking other Python threads.

**Conversion flow**:
```
Python: list[dict[str, str]]  →  PyO3 FromPyObject  →  Rust: Vec<HashMap<String, String>>
                                  ~50-100ms                (data now fully owned by Rust)
                                  GIL held                  GIL released for generation
```

**Alternatives considered**:
- JSON string serialization (`json.dumps()` in Python, `serde_json` in Rust): Could be faster for very large datasets but adds complexity. The 018/019 specs use JSON for complex nested structures, but our data is flat key-value pairs — native PyO3 extraction is simpler.
- `Vec<Vec<String>>` (list of lists): ~20-30% faster extraction but loses column-name semantics. Would require passing headers separately and indexing by position. Rejected for API clarity.
- `Py<PyList>` lazy access: Zero upfront cost but requires GIL for each cell access. Defeats the purpose of GIL release during generation. Rejected.

## R-004: Streaming vs Buffered CSV Output

**Decision**: Use `csv::WriterBuilder::new().from_writer(Vec::new())` for in-memory buffered output. No streaming to disk.

**Rationale**:
- Our functions return `Vec<u8>` (in-memory bytes), not writing to files. Streaming to disk is not applicable.
- The `csv::Writer` is automatically buffered internally — no need to wrap in `BufWriter`.
- For 10K rows x 10 columns, the output CSV is ~1-5MB, well within memory constraints.
- The writer accumulates bytes in the `Vec<u8>`, then `into_inner()` extracts the complete byte array.

**Pattern**:
```rust
let mut buf = Vec::new();
buf.extend_from_slice(b"\xEF\xBB\xBF");  // UTF-8 BOM
let mut wtr = csv::WriterBuilder::new().from_writer(buf);
wtr.write_record(&headers)?;
for row in &rows {
    let record: Vec<&str> = headers.iter()
        .map(|h| row.get(h).map(|s| s.as_str()).unwrap_or(""))
        .collect();
    wtr.write_record(&record)?;
}
wtr.into_inner()?
```

**Memory profile**: For 10K rows x 10 cols x ~20 chars/cell = ~2MB input + ~2MB output = ~4MB total. Acceptable for per-request allocation.

**Alternatives considered**:
- Streaming to file: Not applicable — spec requires returning `Vec<u8>`.
- Pre-allocating Vec capacity: Minor optimization, could estimate `rows.len() * cols * avg_cell_size`. Worth adding if benchmarks show allocation pressure.

## Summary of Decisions

| ID | Topic | Decision |
|----|-------|----------|
| R-001 | Column width API | `set_column_width(col, width)` + `autofit()`, character-width units |
| R-002 | UTF-8 BOM | Always prepend `\xEF\xBB\xBF`, confirmed compatible Excel 2016+/365/LibreOffice |
| R-003 | FFI overhead | `Vec<HashMap<String, String>>` native extraction, ~50-100ms accepted |
| R-004 | CSV output pattern | `csv::Writer::from_writer(Vec::new())`, in-memory buffered, ~4MB for 10K rows |
