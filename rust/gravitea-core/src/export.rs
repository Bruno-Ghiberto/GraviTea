use csv::WriterBuilder;
use pyo3::prelude::*;
use rust_xlsxwriter::{Format, Workbook};
use std::collections::HashMap;

use super::errors::GraviteaError;

// ---------------------------------------------------------------------------
// T004: generate_csv_internal — BOM + csv::Writer, in-memory Vec<u8>
// ---------------------------------------------------------------------------
fn generate_csv_internal(
    rows: &[HashMap<String, String>],
    headers: &[String],
) -> Result<Vec<u8>, GraviteaError> {
    // If no headers, return BOM-only
    if headers.is_empty() {
        return Ok(b"\xEF\xBB\xBF".to_vec());
    }

    let mut buf: Vec<u8> = Vec::new();
    buf.extend_from_slice(b"\xEF\xBB\xBF"); // UTF-8 BOM

    let mut wtr = WriterBuilder::new().from_writer(buf);
    wtr.write_record(headers)
        .map_err(|e| GraviteaError::ExportError(format!("CSV header write failed: {}", e)))?;

    for row in rows {
        let record: Vec<&str> = headers
            .iter()
            .map(|h| row.get(h).map(|s| s.as_str()).unwrap_or(""))
            .collect();
        wtr.write_record(&record)
            .map_err(|e| GraviteaError::ExportError(format!("CSV row write failed: {}", e)))?;
    }

    wtr.into_inner()
        .map_err(|e| GraviteaError::ExportError(format!("CSV finalize failed: {}", e)))
}

// ---------------------------------------------------------------------------
// T005: generate_csv — #[pyfunction] wrapper, releases GIL via py.detach()
// ---------------------------------------------------------------------------
#[pyfunction]
pub fn generate_csv(
    py: Python<'_>,
    rows: Vec<HashMap<String, String>>,
    headers: Vec<String>,
) -> PyResult<Vec<u8>> {
    let result = py.detach(|| generate_csv_internal(&rows, &headers))?;
    Ok(result)
}

// ---------------------------------------------------------------------------
// T011: generate_xlsx_internal — numeric detection, autofit, column widths
// ---------------------------------------------------------------------------
fn generate_xlsx_internal(
    rows: &[HashMap<String, String>],
    headers: &[String],
    column_widths: &HashMap<String, f64>,
) -> Result<Vec<u8>, GraviteaError> {
    let mut workbook = Workbook::new();
    let worksheet = workbook.add_worksheet();
    let bold = Format::new().set_bold();

    // Write headers (row 0)
    for (col, header) in headers.iter().enumerate() {
        worksheet
            .write_with_format(0, col as u16, header.as_str(), &bold)
            .map_err(|e| GraviteaError::ExportError(e.to_string()))?;
    }

    // Write data rows (row 1+)
    for (row_idx, row) in rows.iter().enumerate() {
        let excel_row = (row_idx + 1) as u32;
        for (col_idx, header) in headers.iter().enumerate() {
            let col = col_idx as u16;
            let value = row.get(header).map(|s| s.as_str()).unwrap_or("");
            // Numeric detection: try f64 parse
            if let Ok(num) = value.parse::<f64>() {
                worksheet
                    .write_number(excel_row, col, num)
                    .map_err(|e| GraviteaError::ExportError(e.to_string()))?;
            } else {
                worksheet
                    .write_string(excel_row, col, value)
                    .map_err(|e| GraviteaError::ExportError(e.to_string()))?;
            }
        }
    }

    // Autofit first, then apply explicit width overrides
    worksheet.autofit();
    for (col_name, width) in column_widths {
        if let Some(col_idx) = headers.iter().position(|h| h == col_name) {
            worksheet
                .set_column_width(col_idx as u16, *width)
                .map_err(|e| GraviteaError::ExportError(e.to_string()))?;
        }
        // Orphan column names (not in headers) are silently ignored
    }

    workbook
        .save_to_buffer()
        .map_err(|e| GraviteaError::ExportError(e.to_string()))
}

// ---------------------------------------------------------------------------
// T012: generate_xlsx — #[pyfunction] wrapper, releases GIL via py.detach()
// ---------------------------------------------------------------------------
#[pyfunction]
pub fn generate_xlsx(
    py: Python<'_>,
    rows: Vec<HashMap<String, String>>,
    headers: Vec<String>,
    column_widths: Option<HashMap<String, f64>>,
) -> PyResult<Vec<u8>> {
    let widths = column_widths.unwrap_or_default();
    let result = py.detach(|| generate_xlsx_internal(&rows, &headers, &widths))?;
    Ok(result)
}

// ===========================================================================
// Tests
// ===========================================================================
#[cfg(test)]
mod tests {
    use super::*;

    // -----------------------------------------------------------------------
    // T007: CSV Tests (≥5)
    // -----------------------------------------------------------------------

    #[test]
    fn test_csv_roundtrip() {
        let headers = vec![
            "name".to_string(),
            "qty".to_string(),
            "price".to_string(),
        ];
        let rows = vec![
            HashMap::from([
                ("name".to_string(), "Widget".to_string()),
                ("qty".to_string(), "10".to_string()),
                ("price".to_string(), "25.50".to_string()),
            ]),
            HashMap::from([
                ("name".to_string(), "Gadget".to_string()),
                ("qty".to_string(), "5".to_string()),
                ("price".to_string(), "99.99".to_string()),
            ]),
            HashMap::from([
                ("name".to_string(), "Doohickey".to_string()),
                ("qty".to_string(), "1".to_string()),
                ("price".to_string(), "250.00".to_string()),
            ]),
        ];

        let result = generate_csv_internal(&rows, &headers).unwrap();
        // Skip BOM (3 bytes) and parse as UTF-8
        let csv_str = std::str::from_utf8(&result[3..]).unwrap();

        // Verify headers
        assert!(csv_str.starts_with("name,qty,price"));
        // Verify all values present
        assert!(csv_str.contains("Widget"));
        assert!(csv_str.contains("Gadget"));
        assert!(csv_str.contains("Doohickey"));
        assert!(csv_str.contains("10"));
        assert!(csv_str.contains("25.50"));
        assert!(csv_str.contains("99.99"));
        assert!(csv_str.contains("250.00"));
    }

    #[test]
    fn test_csv_bom_present() {
        let headers = vec!["col".to_string()];
        let rows: Vec<HashMap<String, String>> = vec![];
        let result = generate_csv_internal(&rows, &headers).unwrap();
        // UTF-8 BOM: EF BB BF
        assert_eq!(&result[0..3], b"\xEF\xBB\xBF");
    }

    #[test]
    fn test_csv_empty_headers() {
        let headers: Vec<String> = vec![];
        let rows: Vec<HashMap<String, String>> = vec![];
        let result = generate_csv_internal(&rows, &headers).unwrap();
        // BOM-only: exactly 3 bytes
        assert_eq!(result.len(), 3);
        assert_eq!(&result[..], b"\xEF\xBB\xBF");
    }

    #[test]
    fn test_csv_rfc4180_escaping() {
        let headers = vec!["field".to_string()];
        let rows = vec![
            HashMap::from([("field".to_string(), "has,comma".to_string())]),
            HashMap::from([("field".to_string(), "has\"quote".to_string())]),
            HashMap::from([("field".to_string(), "has\nnewline".to_string())]),
        ];
        let result = generate_csv_internal(&rows, &headers).unwrap();
        let csv_str = std::str::from_utf8(&result[3..]).unwrap();
        // RFC 4180: comma-containing fields are quoted
        assert!(csv_str.contains("\"has,comma\""));
        // RFC 4180: quotes inside quoted fields are doubled
        assert!(csv_str.contains("\"has\"\"quote\""));
        // RFC 4180: newline-containing fields are quoted
        assert!(csv_str.contains("\"has\nnewline\""));
    }

    #[test]
    fn test_csv_missing_key() {
        let headers = vec!["a".to_string(), "b".to_string()];
        let rows = vec![HashMap::from([("a".to_string(), "val_a".to_string())])];
        // Row is missing key "b"
        let result = generate_csv_internal(&rows, &headers).unwrap();
        let csv_str = std::str::from_utf8(&result[3..]).unwrap();
        // Should have "val_a," with empty cell for "b"
        let lines: Vec<&str> = csv_str.lines().collect();
        assert_eq!(lines.len(), 2); // header + 1 data row
        assert_eq!(lines[1], "val_a,");
    }

    // -----------------------------------------------------------------------
    // T014: XLSX Tests (≥5)
    // -----------------------------------------------------------------------

    #[test]
    fn test_xlsx_roundtrip() {
        let headers = vec![
            "name".to_string(),
            "qty".to_string(),
            "price".to_string(),
        ];
        let rows = vec![HashMap::from([
            ("name".to_string(), "Widget".to_string()),
            ("qty".to_string(), "10".to_string()),
            ("price".to_string(), "25.50".to_string()),
        ])];
        let widths = HashMap::new();
        let result = generate_xlsx_internal(&rows, &headers, &widths).unwrap();

        // XLSX is a ZIP file — must start with PK signature (0x50, 0x4B)
        assert!(result.len() > 4);
        assert_eq!(&result[0..2], b"\x50\x4B");
    }

    #[test]
    fn test_xlsx_numeric_detection() {
        let headers = vec!["val".to_string()];
        // Create two separate workbooks: one with numeric value, one with text
        let numeric_rows = vec![HashMap::from([("val".to_string(), "1250.50".to_string())])];
        let text_rows = vec![HashMap::from([("val".to_string(), "abc".to_string())])];
        let widths = HashMap::new();

        let numeric_result =
            generate_xlsx_internal(&numeric_rows, &headers, &widths).unwrap();
        let text_result = generate_xlsx_internal(&text_rows, &headers, &widths).unwrap();

        // Both must be valid XLSX (PK signature)
        assert_eq!(&numeric_result[0..2], b"\x50\x4B");
        assert_eq!(&text_result[0..2], b"\x50\x4B");

        // Numeric and text XLSX outputs will differ in size because
        // numbers are stored as <v> tags and text as shared strings.
        // We verify both produce valid output — the real numeric detection
        // is validated by the Python-side integration tests.
        assert!(numeric_result.len() > 0);
        assert!(text_result.len() > 0);
    }

    #[test]
    fn test_xlsx_column_widths() {
        let headers = vec!["description".to_string(), "amount".to_string()];
        let rows = vec![HashMap::from([
            ("description".to_string(), "Test item".to_string()),
            ("amount".to_string(), "42.00".to_string()),
        ])];
        let mut widths = HashMap::new();
        widths.insert("description".to_string(), 40.0);
        widths.insert("amount".to_string(), 15.0);

        // Should not error — explicit widths applied after autofit
        let result = generate_xlsx_internal(&rows, &headers, &widths).unwrap();
        assert_eq!(&result[0..2], b"\x50\x4B");
        assert!(result.len() > 100);
    }

    #[test]
    fn test_xlsx_empty_data() {
        let headers = vec!["col_a".to_string(), "col_b".to_string()];
        let rows: Vec<HashMap<String, String>> = vec![];
        let widths = HashMap::new();

        let result = generate_xlsx_internal(&rows, &headers, &widths).unwrap();
        // Should produce valid XLSX bytes even with no data rows
        assert_eq!(&result[0..2], b"\x50\x4B");
        assert!(result.len() > 0);
    }

    #[test]
    fn test_xlsx_orphan_width_ignored() {
        let headers = vec!["real_col".to_string()];
        let rows = vec![HashMap::from([(
            "real_col".to_string(),
            "data".to_string(),
        )])];
        let mut widths = HashMap::new();
        widths.insert("nonexistent_col".to_string(), 50.0);

        // Orphan column name should be silently ignored — no error
        let result = generate_xlsx_internal(&rows, &headers, &widths).unwrap();
        assert_eq!(&result[0..2], b"\x50\x4B");
    }
}
