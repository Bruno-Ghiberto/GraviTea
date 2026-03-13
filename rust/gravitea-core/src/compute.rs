use pyo3::prelude::*;
use rust_decimal::prelude::*;
use rust_decimal_macros::dec;
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, HashMap};

use super::decimal_utils::{decimal_to_string, dual_tolerance_eq, parse_decimal};
use super::errors::GraviteaError;

// ============================================================
// Constants
// ============================================================

/// CbteTipo codes where IVA breakdown is mandatory (A/B/M types)
const IVA_REQUIRED_TIPOS: &[i32] = &[1, 2, 3, 6, 7, 8, 51, 52, 53];
/// CbteTipo codes where IVA breakdown is prohibited (C types)
const IVA_PROHIBITED_TIPOS: &[i32] = &[11, 12, 13];
/// CUIT Modulo-11 weight sequence
const CUIT_WEIGHTS: [u32; 10] = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2];

// ============================================================
// Serde Structs
// ============================================================

#[derive(Deserialize)]
struct LineItem {
    price: String,
    quantity: String,
    iva_rate: String,
}

#[derive(Serialize)]
struct AlicIvaResult {
    iva_id: i32,
    base_imp: String,
    importe: String,
}

#[derive(Deserialize)]
struct StockMovement {
    product_id: String,
    branch_id: String,
    quantity: String,
    movement_type: String,
}

#[derive(Serialize)]
struct StockLevel {
    total: String,
    reserved: String,
    available: String,
}

#[derive(Deserialize)]
#[allow(dead_code)]
struct AlicIvaEntry {
    iva_id: i32,
    base_imp: String,
    importe: String,
}

// ============================================================
// Helpers
// ============================================================

fn iva_rate_to_id(rate: &Decimal) -> i32 {
    let r = rate.normalize();
    if r == dec!(0) {
        3
    } else if r == dec!(2.5) {
        9
    } else if r == dec!(5) {
        8
    } else if r == dec!(10.5) {
        4
    } else if r == dec!(21) {
        5
    } else if r == dec!(27) {
        6
    } else {
        5 // Unknown defaults to IVA_21
    }
}

// ============================================================
// Internal Functions (testable without Python)
// ============================================================

fn validate_importes_internal(
    imp_total: &str,
    imp_neto: &str,
    imp_iva: &str,
    imp_trib: &str,
    imp_op_ex: &str,
    imp_tot_conc: &str,
) -> Result<(), GraviteaError> {
    let total = parse_decimal(imp_total)?;
    let neto = parse_decimal(imp_neto)?;
    let iva = parse_decimal(imp_iva)?;
    let trib = parse_decimal(imp_trib)?;
    let op_ex = parse_decimal(imp_op_ex)?;
    let tot_conc = parse_decimal(imp_tot_conc)?;

    let expected = neto + op_ex + iva + trib + tot_conc;

    if !dual_tolerance_eq(&expected, &total, &dec!(0.01), &dec!(0.0001)) {
        let diff = (total - expected).abs();
        return Err(GraviteaError::ComputeError {
            msg: format!(
                "Amount equation does not balance: \
                 ImpTotal ({}) != \
                 ImpNeto ({}) + ImpOpEx ({}) + \
                 ImpIVA ({}) + ImpTrib ({}) + \
                 ImpTotConc ({}) = {}. \
                 Difference: {}.",
                imp_total,
                imp_neto,
                imp_op_ex,
                imp_iva,
                imp_trib,
                imp_tot_conc,
                decimal_to_string(&expected),
                decimal_to_string(&diff)
            ),
        });
    }
    Ok(())
}

fn calculate_iva_breakdown_internal(items_json: &str) -> Result<String, GraviteaError> {
    let items: Vec<LineItem> =
        serde_json::from_str(items_json).map_err(|e| GraviteaError::ComputeError {
            msg: format!("Invalid JSON: {}", e),
        })?;

    if items.is_empty() {
        return Ok("[]".to_string());
    }

    // Group by normalized rate string
    let mut groups: HashMap<String, (Decimal, Decimal)> = HashMap::new();

    for item in &items {
        let price = parse_decimal(&item.price)?;
        let qty = parse_decimal(&item.quantity)?;
        let rate = parse_decimal(&item.iva_rate)?;

        let base = price * qty;
        let importe = base * rate / dec!(100);

        let rate_key = decimal_to_string(&rate);
        let entry = groups.entry(rate_key).or_insert((Decimal::ZERO, Decimal::ZERO));
        entry.0 += base;
        entry.1 += importe;
    }

    let mut results: Vec<AlicIvaResult> = Vec::new();
    for (rate_str, (base_imp, importe)) in &groups {
        let rate = parse_decimal(rate_str)?;
        results.push(AlicIvaResult {
            iva_id: iva_rate_to_id(&rate),
            base_imp: decimal_to_string(base_imp),
            importe: decimal_to_string(importe),
        });
    }

    // Sort by iva_id for deterministic output
    results.sort_by_key(|r| r.iva_id);

    serde_json::to_string(&results).map_err(|e| GraviteaError::ComputeError {
        msg: format!("JSON serialization error: {}", e),
    })
}

fn validate_cuit_internal(cuit: &str) -> Result<(), GraviteaError> {
    if cuit.len() != 11 {
        return Err(GraviteaError::ComputeError {
            msg: "CUIT must be exactly 11 digits.".to_string(),
        });
    }
    if !cuit.chars().all(|c| c.is_ascii_digit()) {
        return Err(GraviteaError::ComputeError {
            msg: "CUIT must contain only digits.".to_string(),
        });
    }

    let digits: Vec<u32> = cuit.chars().map(|c| c.to_digit(10).unwrap()).collect();

    let sum: u32 = digits[..10]
        .iter()
        .zip(CUIT_WEIGHTS.iter())
        .map(|(d, w)| d * w)
        .sum();

    let mut check = 11 - (sum % 11);
    if check == 11 {
        check = 0;
    } else if check == 10 {
        check = 9;
    }

    if digits[10] != check {
        return Err(GraviteaError::ComputeError {
            msg: "CUIT check digit is invalid.".to_string(),
        });
    }
    Ok(())
}

fn aggregate_internal(movements: &[StockMovement]) -> Result<String, GraviteaError> {
    let mut result: BTreeMap<String, BTreeMap<String, (Decimal, Decimal)>> = BTreeMap::new();

    for m in movements {
        let qty = parse_decimal(&m.quantity)?;
        let branch_map = result.entry(m.product_id.clone()).or_default();
        let (total, reserved) = branch_map
            .entry(m.branch_id.clone())
            .or_insert((Decimal::ZERO, Decimal::ZERO));

        match m.movement_type.as_str() {
            "IN" | "ADJUSTMENT" | "TRANSFER_IN" => *total += qty,
            "OUT" | "TRANSFER_OUT" => *total -= qty,
            "RESERVED" => *reserved += qty,
            "RELEASED" => *reserved -= qty,
            _ => {} // ignore unknown types
        }
    }

    // Convert to serializable output
    let output: BTreeMap<String, BTreeMap<String, StockLevel>> = result
        .into_iter()
        .map(|(pid, branches)| {
            let branch_levels: BTreeMap<String, StockLevel> = branches
                .into_iter()
                .map(|(bid, (total, reserved))| {
                    let available = total - reserved;
                    (
                        bid,
                        StockLevel {
                            total: decimal_to_string(&total),
                            reserved: decimal_to_string(&reserved),
                            available: decimal_to_string(&available),
                        },
                    )
                })
                .collect();
            (pid, branch_levels)
        })
        .collect();

    serde_json::to_string(&output).map_err(|e| GraviteaError::ComputeError {
        msg: format!("JSON serialization error: {}", e),
    })
}

fn validate_iva_breakdown_internal(
    cbte_tipo: i32,
    aliciva_json: &str,
    imp_iva: &str,
    imp_neto: &str,
) -> Result<(), GraviteaError> {
    let entries: Vec<AlicIvaEntry> =
        serde_json::from_str(aliciva_json).map_err(|e| GraviteaError::ComputeError {
            msg: format!("Invalid JSON: {}", e),
        })?;

    let iva_val = parse_decimal(imp_iva)?;
    let neto_val = parse_decimal(imp_neto)?;

    if IVA_REQUIRED_TIPOS.contains(&cbte_tipo) {
        if entries.is_empty() {
            return Err(GraviteaError::ComputeError {
                msg: format!(
                    "IVA breakdown (AlicIva) is mandatory for CbteTipo {}. \
                     At least one IVA rate entry is required.",
                    cbte_tipo
                ),
            });
        }
    } else if IVA_PROHIBITED_TIPOS.contains(&cbte_tipo) {
        if !entries.is_empty() {
            return Err(GraviteaError::ComputeError {
                msg: format!(
                    "IVA breakdown must be empty for CbteTipo {}. \
                     Type C invoices must omit IVA entirely.",
                    cbte_tipo
                ),
            });
        }
        return Ok(());
    }

    if entries.is_empty() {
        return Ok(());
    }

    let mut total_importe = Decimal::ZERO;
    let mut total_base_imp = Decimal::ZERO;

    for entry in &entries {
        total_importe += parse_decimal(&entry.importe)?;
        total_base_imp += parse_decimal(&entry.base_imp)?;
    }

    if !dual_tolerance_eq(&iva_val, &total_importe, &dec!(0.01), &dec!(0.0001)) {
        let diff = (iva_val - total_importe).abs();
        return Err(GraviteaError::ComputeError {
            msg: format!(
                "AlicIva importe sum ({}) does not match \
                 ImpIVA ({}). Difference: {}.",
                decimal_to_string(&total_importe),
                decimal_to_string(&iva_val),
                decimal_to_string(&diff)
            ),
        });
    }

    if !dual_tolerance_eq(&neto_val, &total_base_imp, &dec!(0.01), &dec!(0.0001)) {
        let diff = (neto_val - total_base_imp).abs();
        return Err(GraviteaError::ComputeError {
            msg: format!(
                "AlicIva base_imp sum ({}) does not match \
                 ImpNeto ({}). Difference: {}.",
                decimal_to_string(&total_base_imp),
                decimal_to_string(&neto_val),
                decimal_to_string(&diff)
            ),
        });
    }

    Ok(())
}

// ============================================================
// PyO3 Exports
// ============================================================

#[pyfunction]
pub fn validate_importes(
    imp_total: &str,
    imp_neto: &str,
    imp_iva: &str,
    imp_trib: &str,
    imp_op_ex: &str,
    imp_tot_conc: &str,
) -> PyResult<()> {
    Ok(validate_importes_internal(
        imp_total, imp_neto, imp_iva, imp_trib, imp_op_ex, imp_tot_conc,
    )?)
}

#[pyfunction]
pub fn calculate_iva_breakdown(items_json: &str) -> PyResult<String> {
    Ok(calculate_iva_breakdown_internal(items_json)?)
}

#[pyfunction]
pub fn validate_cuit(cuit: &str) -> PyResult<()> {
    Ok(validate_cuit_internal(cuit)?)
}

#[pyfunction]
pub fn aggregate_stock_levels(py: Python<'_>, movements_json: &str) -> PyResult<String> {
    let movements: Vec<StockMovement> =
        serde_json::from_str(movements_json).map_err(|e| GraviteaError::ComputeError {
            msg: format!("Invalid JSON: {}", e),
        })?;

    let result = py.detach(|| aggregate_internal(&movements))?;
    Ok(result)
}

#[pyfunction]
pub fn validate_iva_breakdown(
    cbte_tipo: i32,
    aliciva_json: &str,
    imp_iva: &str,
    imp_neto: &str,
) -> PyResult<()> {
    Ok(validate_iva_breakdown_internal(
        cbte_tipo, aliciva_json, imp_iva, imp_neto,
    )?)
}

// ============================================================
// Tests
// ============================================================

#[cfg(test)]
mod tests {
    use super::*;

    // ----------------------------------------------------------
    // Test helpers
    // ----------------------------------------------------------

    fn aggregate_from_json(json: &str) -> Result<String, GraviteaError> {
        let movements: Vec<StockMovement> =
            serde_json::from_str(json).map_err(|e| GraviteaError::ComputeError {
                msg: format!("Invalid JSON: {}", e),
            })?;
        aggregate_internal(&movements)
    }

    // ----------------------------------------------------------
    // Phase 3: validate_importes (5 tests)
    // ----------------------------------------------------------

    #[test]
    fn test_validate_importes_valid() {
        // 121.00 = 100.00 + 0.00 + 21.00 + 0.00 + 0.00
        let result = validate_importes_internal(
            "121.00", "100.00", "21.00", "0.00", "0.00", "0.00",
        );
        assert!(result.is_ok());
    }

    #[test]
    fn test_validate_importes_invalid() {
        // 122.00 != 100.00 + 0.00 + 21.00 + 0.00 + 0.00 = 121.00
        let result = validate_importes_internal(
            "122.00", "100.00", "21.00", "0.00", "0.00", "0.00",
        );
        assert!(result.is_err());
        let err = result.unwrap_err();
        assert!(matches!(err, GraviteaError::ComputeError { .. }));
        assert!(err.to_string().contains("Amount equation does not balance"));
    }

    #[test]
    fn test_validate_importes_zero_comprobante() {
        let result = validate_importes_internal(
            "0.00", "0.00", "0.00", "0.00", "0.00", "0.00",
        );
        assert!(result.is_ok());
    }

    #[test]
    fn test_validate_importes_tolerance_absolute() {
        // 121.005 vs expected 121.00 → diff = 0.005 <= 0.01 → passes
        let result = validate_importes_internal(
            "121.005", "100.00", "21.00", "0.00", "0.00", "0.00",
        );
        assert!(result.is_ok());
    }

    #[test]
    fn test_validate_importes_tolerance_fails() {
        // 121.02 vs expected 121.00 → diff = 0.02 > 0.01 abs, > 0.0001*121 = 0.0121 rel → fails
        let result = validate_importes_internal(
            "121.02", "100.00", "21.00", "0.00", "0.00", "0.00",
        );
        assert!(result.is_err());
    }

    // ----------------------------------------------------------
    // Phase 4: calculate_iva_breakdown (6 tests)
    // ----------------------------------------------------------

    #[test]
    fn test_iva_single_rate_21() {
        let items = r#"[{"price":"100.00","quantity":"2","iva_rate":"21"}]"#;
        let result = calculate_iva_breakdown_internal(items).unwrap();
        let parsed: Vec<serde_json::Value> = serde_json::from_str(&result).unwrap();

        assert_eq!(parsed.len(), 1);
        assert_eq!(parsed[0]["iva_id"], 5);
        assert_eq!(parsed[0]["base_imp"].as_str().unwrap(), "200");
        assert_eq!(parsed[0]["importe"].as_str().unwrap(), "42");
    }

    #[test]
    fn test_iva_all_6_rates() {
        let items = r#"[
            {"price":"1000","quantity":"1","iva_rate":"0"},
            {"price":"1000","quantity":"1","iva_rate":"2.5"},
            {"price":"1000","quantity":"1","iva_rate":"5"},
            {"price":"1000","quantity":"1","iva_rate":"10.5"},
            {"price":"1000","quantity":"1","iva_rate":"21"},
            {"price":"1000","quantity":"1","iva_rate":"27"}
        ]"#;
        let result = calculate_iva_breakdown_internal(items).unwrap();
        let parsed: Vec<serde_json::Value> = serde_json::from_str(&result).unwrap();

        assert_eq!(parsed.len(), 6);

        // Sorted by iva_id: 3, 4, 5, 6, 8, 9
        let ids: Vec<i64> = parsed.iter().map(|v| v["iva_id"].as_i64().unwrap()).collect();
        assert_eq!(ids, vec![3, 4, 5, 6, 8, 9]);

        // Verify specific entries
        // iva_id=3 (0%): base=1000, importe=0
        assert_eq!(parsed[0]["base_imp"].as_str().unwrap(), "1000");
        assert_eq!(parsed[0]["importe"].as_str().unwrap(), "0");

        // iva_id=4 (10.5%): base=1000, importe=105
        assert_eq!(parsed[1]["base_imp"].as_str().unwrap(), "1000");
        assert_eq!(parsed[1]["importe"].as_str().unwrap(), "105");

        // iva_id=5 (21%): base=1000, importe=210
        assert_eq!(parsed[2]["base_imp"].as_str().unwrap(), "1000");
        assert_eq!(parsed[2]["importe"].as_str().unwrap(), "210");

        // iva_id=6 (27%): base=1000, importe=270
        assert_eq!(parsed[3]["base_imp"].as_str().unwrap(), "1000");
        assert_eq!(parsed[3]["importe"].as_str().unwrap(), "270");

        // iva_id=8 (5%): base=1000, importe=50
        assert_eq!(parsed[4]["base_imp"].as_str().unwrap(), "1000");
        assert_eq!(parsed[4]["importe"].as_str().unwrap(), "50");

        // iva_id=9 (2.5%): base=1000, importe=25
        assert_eq!(parsed[5]["base_imp"].as_str().unwrap(), "1000");
        assert_eq!(parsed[5]["importe"].as_str().unwrap(), "25");
    }

    #[test]
    fn test_iva_grouping() {
        // 3 items all at 21% → single entry with aggregated amounts
        let items = r#"[
            {"price":"100","quantity":"1","iva_rate":"21"},
            {"price":"200","quantity":"1","iva_rate":"21"},
            {"price":"50","quantity":"2","iva_rate":"21"}
        ]"#;
        let result = calculate_iva_breakdown_internal(items).unwrap();
        let parsed: Vec<serde_json::Value> = serde_json::from_str(&result).unwrap();

        assert_eq!(parsed.len(), 1);
        assert_eq!(parsed[0]["iva_id"], 5);
        // base = 100 + 200 + 100 = 400
        assert_eq!(parsed[0]["base_imp"].as_str().unwrap(), "400");
        // importe = 400 * 0.21 = 84
        assert_eq!(parsed[0]["importe"].as_str().unwrap(), "84");
    }

    #[test]
    fn test_iva_unknown_rate_defaults() {
        let items = r#"[{"price":"100","quantity":"1","iva_rate":"15"}]"#;
        let result = calculate_iva_breakdown_internal(items).unwrap();
        let parsed: Vec<serde_json::Value> = serde_json::from_str(&result).unwrap();

        assert_eq!(parsed.len(), 1);
        assert_eq!(parsed[0]["iva_id"], 5); // defaults to IVA_21
        assert_eq!(parsed[0]["base_imp"].as_str().unwrap(), "100");
        assert_eq!(parsed[0]["importe"].as_str().unwrap(), "15");
    }

    #[test]
    fn test_iva_empty_items() {
        let result = calculate_iva_breakdown_internal("[]").unwrap();
        assert_eq!(result, "[]");
    }

    #[test]
    fn test_iva_negative_quantity() {
        // Credit note: negative quantity
        let items = r#"[{"price":"100","quantity":"-1","iva_rate":"21"}]"#;
        let result = calculate_iva_breakdown_internal(items).unwrap();
        let parsed: Vec<serde_json::Value> = serde_json::from_str(&result).unwrap();

        assert_eq!(parsed.len(), 1);
        assert_eq!(parsed[0]["iva_id"], 5);
        assert_eq!(parsed[0]["base_imp"].as_str().unwrap(), "-100");
        assert_eq!(parsed[0]["importe"].as_str().unwrap(), "-21");
    }

    // ----------------------------------------------------------
    // Phase 5: validate_cuit (7 tests)
    // ----------------------------------------------------------

    #[test]
    fn test_cuit_valid() {
        // 27000000006: sum = 5*2 + 4*7 = 10+28 = 38; 38%11=5; 11-5=6; digit=6 ✓
        assert!(validate_cuit_internal("27000000006").is_ok());
    }

    #[test]
    fn test_cuit_invalid_check() {
        // Changed last digit from 6 to 7
        let result = validate_cuit_internal("27000000007");
        assert!(result.is_err());
        assert!(result
            .unwrap_err()
            .to_string()
            .contains("check digit is invalid"));
    }

    #[test]
    fn test_cuit_too_short() {
        let result = validate_cuit_internal("2700000000");
        assert!(result.is_err());
        assert!(result
            .unwrap_err()
            .to_string()
            .contains("must be exactly 11 digits"));
    }

    #[test]
    fn test_cuit_too_long() {
        let result = validate_cuit_internal("270000000060");
        assert!(result.is_err());
        assert!(result
            .unwrap_err()
            .to_string()
            .contains("must be exactly 11 digits"));
    }

    #[test]
    fn test_cuit_non_numeric() {
        let result = validate_cuit_internal("2012345678a");
        assert!(result.is_err());
        assert!(result
            .unwrap_err()
            .to_string()
            .contains("only digits"));
    }

    #[test]
    fn test_cuit_check_11_becomes_0() {
        // 20000200000: sum = 5*2+6*2 = 10+12 = 22; 22%11=0; 11-0=11→0; digit=0 ✓
        assert!(validate_cuit_internal("20000200000").is_ok());
    }

    #[test]
    fn test_cuit_check_10_becomes_9() {
        // 20000000019: sum = 5*2+2*1 = 10+2 = 12; 12%11=1; 11-1=10→9; digit=9 ✓
        assert!(validate_cuit_internal("20000000019").is_ok());
    }

    // ----------------------------------------------------------
    // Phase 6: aggregate_stock_levels (5 tests)
    // ----------------------------------------------------------

    #[test]
    fn test_aggregate_single_product() {
        let json = r#"[
            {"product_id":"p1","branch_id":"b1","quantity":"10","movement_type":"IN"},
            {"product_id":"p1","branch_id":"b1","quantity":"10","movement_type":"IN"},
            {"product_id":"p1","branch_id":"b1","quantity":"10","movement_type":"IN"},
            {"product_id":"p1","branch_id":"b1","quantity":"5","movement_type":"OUT"}
        ]"#;
        let result = aggregate_from_json(json).unwrap();
        let parsed: serde_json::Value = serde_json::from_str(&result).unwrap();

        assert_eq!(parsed["p1"]["b1"]["total"].as_str().unwrap(), "25");
        assert_eq!(parsed["p1"]["b1"]["reserved"].as_str().unwrap(), "0");
        assert_eq!(parsed["p1"]["b1"]["available"].as_str().unwrap(), "25");
    }

    #[test]
    fn test_aggregate_multi_product_multi_branch() {
        let json = r#"[
            {"product_id":"p1","branch_id":"b1","quantity":"10","movement_type":"IN"},
            {"product_id":"p1","branch_id":"b1","quantity":"3","movement_type":"OUT"},
            {"product_id":"p1","branch_id":"b2","quantity":"5","movement_type":"IN"},
            {"product_id":"p2","branch_id":"b1","quantity":"20","movement_type":"IN"},
            {"product_id":"p2","branch_id":"b2","quantity":"15","movement_type":"IN"},
            {"product_id":"p2","branch_id":"b2","quantity":"5","movement_type":"OUT"}
        ]"#;
        let result = aggregate_from_json(json).unwrap();
        let parsed: serde_json::Value = serde_json::from_str(&result).unwrap();

        assert_eq!(parsed["p1"]["b1"]["total"].as_str().unwrap(), "7");
        assert_eq!(parsed["p1"]["b2"]["total"].as_str().unwrap(), "5");
        assert_eq!(parsed["p2"]["b1"]["total"].as_str().unwrap(), "20");
        assert_eq!(parsed["p2"]["b2"]["total"].as_str().unwrap(), "10");
    }

    #[test]
    fn test_aggregate_empty_input() {
        let result = aggregate_from_json("[]").unwrap();
        assert_eq!(result, "{}");
    }

    #[test]
    fn test_aggregate_decimal_precision() {
        let json = r#"[
            {"product_id":"p1","branch_id":"b1","quantity":"1.2345","movement_type":"IN"},
            {"product_id":"p1","branch_id":"b1","quantity":"2.3456","movement_type":"IN"}
        ]"#;
        let result = aggregate_from_json(json).unwrap();
        let parsed: serde_json::Value = serde_json::from_str(&result).unwrap();

        assert_eq!(parsed["p1"]["b1"]["total"].as_str().unwrap(), "3.5801");
    }

    #[test]
    fn test_aggregate_all_movement_types() {
        let json = r#"[
            {"product_id":"p1","branch_id":"b1","quantity":"100","movement_type":"IN"},
            {"product_id":"p1","branch_id":"b1","quantity":"20","movement_type":"OUT"},
            {"product_id":"p1","branch_id":"b1","quantity":"10","movement_type":"ADJUSTMENT"},
            {"product_id":"p1","branch_id":"b1","quantity":"5","movement_type":"TRANSFER_IN"},
            {"product_id":"p1","branch_id":"b1","quantity":"3","movement_type":"TRANSFER_OUT"},
            {"product_id":"p1","branch_id":"b1","quantity":"15","movement_type":"RESERVED"},
            {"product_id":"p1","branch_id":"b1","quantity":"5","movement_type":"RELEASED"}
        ]"#;
        let result = aggregate_from_json(json).unwrap();
        let parsed: serde_json::Value = serde_json::from_str(&result).unwrap();

        // total = (100 + 10 + 5) - (20 + 3) = 92
        assert_eq!(parsed["p1"]["b1"]["total"].as_str().unwrap(), "92");
        // reserved = 15 - 5 = 10
        assert_eq!(parsed["p1"]["b1"]["reserved"].as_str().unwrap(), "10");
        // available = 92 - 10 = 82
        assert_eq!(parsed["p1"]["b1"]["available"].as_str().unwrap(), "82");
    }

    // ----------------------------------------------------------
    // Phase 7: validate_iva_breakdown (6 tests)
    // ----------------------------------------------------------

    #[test]
    fn test_iva_validation_type_a_mandatory() {
        // cbte_tipo=1 (Factura A), empty AlicIva → error
        let result = validate_iva_breakdown_internal(1, "[]", "0.00", "0.00");
        assert!(result.is_err());
        assert!(result.unwrap_err().to_string().contains("mandatory"));
    }

    #[test]
    fn test_iva_validation_type_c_prohibited() {
        // cbte_tipo=11 (Factura C), non-empty AlicIva → error
        let aliciva = r#"[{"iva_id":5,"base_imp":"100.00","importe":"21.00"}]"#;
        let result = validate_iva_breakdown_internal(11, aliciva, "21.00", "100.00");
        assert!(result.is_err());
        assert!(result.unwrap_err().to_string().contains("must be empty"));
    }

    #[test]
    fn test_iva_validation_sum_match() {
        // cbte_tipo=1, valid sums → passes
        let aliciva = r#"[{"iva_id":5,"base_imp":"100.00","importe":"21.00"}]"#;
        let result = validate_iva_breakdown_internal(1, aliciva, "21.00", "100.00");
        assert!(result.is_ok());
    }

    #[test]
    fn test_iva_validation_importe_mismatch() {
        // imp_iva=22.00 but AlicIva importe sum=21.00 → error
        let aliciva = r#"[{"iva_id":5,"base_imp":"100.00","importe":"21.00"}]"#;
        let result = validate_iva_breakdown_internal(1, aliciva, "22.00", "100.00");
        assert!(result.is_err());
        assert!(result
            .unwrap_err()
            .to_string()
            .contains("importe sum"));
    }

    #[test]
    fn test_iva_validation_base_imp_mismatch() {
        // imp_neto=110.00 but AlicIva base_imp sum=100.00 → error
        let aliciva = r#"[{"iva_id":5,"base_imp":"100.00","importe":"21.00"}]"#;
        let result = validate_iva_breakdown_internal(1, aliciva, "21.00", "110.00");
        assert!(result.is_err());
        assert!(result
            .unwrap_err()
            .to_string()
            .contains("base_imp sum"));
    }

    #[test]
    fn test_iva_validation_type_b_mandatory() {
        // cbte_tipo=6 (Factura B) → mandatory, same as A
        let result = validate_iva_breakdown_internal(6, "[]", "0.00", "0.00");
        assert!(result.is_err());
        assert!(result.unwrap_err().to_string().contains("mandatory"));
    }
}
