// SPEC-011: Merma Calculation Engine (Circular CAC 10/86)
//
// Sequential grain weight deduction formula:
//   1. Zarandeo (screening) — removes foreign matter
//   2. Secado (drying) — reduces moisture above threshold
//   3. Manipuleo (handling) — fixed %, ONLY if secado was applied
//   4. Volatil — always applied, fixed %

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use rust_decimal::Decimal;
use serde::{Deserialize, Serialize};

// ---------------------------------------------------------------------------
// Serde Structs
// ---------------------------------------------------------------------------

#[derive(Deserialize)]
struct MermaInput {
    #[serde(with = "rust_decimal::serde::str")]
    peso_neto_bruto_kg: Decimal,
    #[serde(with = "rust_decimal::serde::str")]
    humedad_pct: Decimal,
    #[serde(with = "rust_decimal::serde::str")]
    hf_secado_pct: Decimal,
    #[serde(with = "rust_decimal::serde::str")]
    #[allow(dead_code)]
    materias_extranas_pct: Decimal,
    #[serde(with = "rust_decimal::serde::str")]
    zarandeo_deduction_pct: Decimal,
    #[serde(with = "rust_decimal::serde::str")]
    manipuleo_fijo_pct: Decimal,
    #[serde(with = "rust_decimal::serde::str")]
    volatil_fijo_pct: Decimal,
}

#[derive(Serialize, Debug)]
struct MermaOutput {
    #[serde(with = "rust_decimal::serde::str")]
    zarandeo_pct: Decimal,
    #[serde(with = "rust_decimal::serde::str")]
    secado_pct: Decimal,
    #[serde(with = "rust_decimal::serde::str")]
    manipuleo_pct: Decimal,
    #[serde(with = "rust_decimal::serde::str")]
    volatil_pct: Decimal,
    #[serde(with = "rust_decimal::serde::str")]
    peso_post_zarandeo_kg: Decimal,
    #[serde(with = "rust_decimal::serde::str")]
    peso_post_secado_kg: Decimal,
    #[serde(with = "rust_decimal::serde::str")]
    peso_post_manipuleo_kg: Decimal,
    #[serde(with = "rust_decimal::serde::str")]
    peso_final_kg: Decimal,
    #[serde(with = "rust_decimal::serde::str")]
    total_merma_kg: Decimal,
    #[serde(with = "rust_decimal::serde::str")]
    total_factor_pct: Decimal,
}

// ---------------------------------------------------------------------------
// Validation helpers
// ---------------------------------------------------------------------------

fn validate_pct_range(value: &Decimal, name: &str) -> Result<(), String> {
    let hundred = Decimal::from(100);
    if *value < Decimal::ZERO || *value > hundred {
        return Err(format!("{name} must be between 0 and 100, got {value}"));
    }
    Ok(())
}

fn validate_non_negative(value: &Decimal, name: &str) -> Result<(), String> {
    if *value < Decimal::ZERO {
        return Err(format!("{name} must be non-negative, got {value}"));
    }
    Ok(())
}

// ---------------------------------------------------------------------------
// Core calculation
// ---------------------------------------------------------------------------

fn calculate_merma_internal(input: &MermaInput) -> Result<MermaOutput, String> {
    // --- Validate inputs ---
    if input.peso_neto_bruto_kg <= Decimal::ZERO {
        return Err("peso_neto_bruto_kg must be positive".to_string());
    }
    validate_pct_range(&input.humedad_pct, "humedad_pct")?;
    validate_pct_range(&input.hf_secado_pct, "hf_secado_pct")?;
    validate_non_negative(&input.zarandeo_deduction_pct, "zarandeo_deduction_pct")?;
    validate_non_negative(&input.manipuleo_fijo_pct, "manipuleo_fijo_pct")?;
    validate_non_negative(&input.volatil_fijo_pct, "volatil_fijo_pct")?;

    let hundred = Decimal::from(100);

    // --- Step 1: Zarandeo (screening) ---
    let zarandeo_pct = input.zarandeo_deduction_pct;
    let peso_post_zarandeo =
        input.peso_neto_bruto_kg * (Decimal::ONE - zarandeo_pct / hundred);

    // --- Step 2: Secado (drying) ---
    let secado_pct = if input.humedad_pct <= input.hf_secado_pct {
        Decimal::ZERO
    } else {
        (input.humedad_pct - input.hf_secado_pct)
            / (hundred - input.hf_secado_pct)
            * hundred
    };
    let peso_post_secado = if secado_pct == Decimal::ZERO {
        peso_post_zarandeo
    } else {
        peso_post_zarandeo * (Decimal::ONE - secado_pct / hundred)
    };

    // --- Step 3: Manipuleo (handling) — only if secado was applied ---
    let manipuleo_pct = if secado_pct == Decimal::ZERO {
        Decimal::ZERO
    } else {
        input.manipuleo_fijo_pct
    };
    let peso_post_manipuleo = if manipuleo_pct == Decimal::ZERO {
        peso_post_secado
    } else {
        peso_post_secado * (Decimal::ONE - manipuleo_pct / hundred)
    };

    // --- Step 4: Volatil (always applied) ---
    let volatil_pct = input.volatil_fijo_pct;
    let peso_final = peso_post_manipuleo * (Decimal::ONE - volatil_pct / hundred);

    // --- Derived totals ---
    let total_merma = input.peso_neto_bruto_kg - peso_final;
    let total_factor = peso_final / input.peso_neto_bruto_kg;

    // Round: 3 dp for weights, 2 dp for percentages, 4 dp for factor
    Ok(MermaOutput {
        zarandeo_pct: zarandeo_pct.round_dp(2),
        secado_pct: secado_pct.round_dp(2),
        manipuleo_pct: manipuleo_pct.round_dp(2),
        volatil_pct: volatil_pct.round_dp(2),
        peso_post_zarandeo_kg: peso_post_zarandeo.round_dp(3),
        peso_post_secado_kg: peso_post_secado.round_dp(3),
        peso_post_manipuleo_kg: peso_post_manipuleo.round_dp(3),
        peso_final_kg: peso_final.round_dp(3),
        total_merma_kg: total_merma.round_dp(3),
        total_factor_pct: total_factor.round_dp(4),
    })
}

// ---------------------------------------------------------------------------
// PyO3 entry-point
// ---------------------------------------------------------------------------

/// Calculate grain weight deductions (merma) per Circular CAC 10/86.
///
/// Takes a JSON string with the input parameters and returns a JSON string
/// with the full breakdown of deductions and intermediate weights.
#[pyfunction]
pub fn calculate_merma(input_json: &str) -> PyResult<String> {
    let input: MermaInput = serde_json::from_str(input_json)
        .map_err(|e| PyValueError::new_err(format!("Invalid input JSON: {e}")))?;

    let output = calculate_merma_internal(&input)
        .map_err(|e| PyValueError::new_err(e))?;

    serde_json::to_string(&output)
        .map_err(|e| PyValueError::new_err(format!("Failed to serialize output: {e}")))
}

// ===========================================================================
// Tests
// ===========================================================================

#[cfg(test)]
mod tests {
    use super::*;
    use rust_decimal_macros::dec;

    /// Helper: build a standard MermaInput
    fn make_input(
        peso: Decimal,
        humedad: Decimal,
        hf_secado: Decimal,
        materias_extranas: Decimal,
        zarandeo: Decimal,
        manipuleo: Decimal,
        volatil: Decimal,
    ) -> MermaInput {
        MermaInput {
            peso_neto_bruto_kg: peso,
            humedad_pct: humedad,
            hf_secado_pct: hf_secado,
            materias_extranas_pct: materias_extranas,
            zarandeo_deduction_pct: zarandeo,
            manipuleo_fijo_pct: manipuleo,
            volatil_fijo_pct: volatil,
        }
    }

    /// Helper: build JSON string for PyO3 interface tests
    fn make_json(
        peso: &str,
        humedad: &str,
        hf_secado: &str,
        materias_extranas: &str,
        zarandeo: &str,
        manipuleo: &str,
        volatil: &str,
    ) -> String {
        format!(
            r#"{{"peso_neto_bruto_kg":"{}","humedad_pct":"{}","hf_secado_pct":"{}","materias_extranas_pct":"{}","zarandeo_deduction_pct":"{}","manipuleo_fijo_pct":"{}","volatil_fijo_pct":"{}"}}"#,
            peso, humedad, hf_secado, materias_extranas, zarandeo, manipuleo, volatil
        )
    }

    // ------------------------------------------------------------------
    // 1. Reference vector: Trigo (wheat)
    // ------------------------------------------------------------------
    #[test]
    fn test_trigo_reference_vector() {
        // Input from api.md contract
        let input = make_input(
            dec!(30000.000),
            dec!(15.2),
            dec!(13.5),
            dec!(1.8),
            dec!(1.00),
            dec!(0.25),
            dec!(0.30),
        );
        let out = calculate_merma_internal(&input).unwrap();

        // zarandeo_pct = 1.00
        assert_eq!(out.zarandeo_pct, dec!(1.00));
        // peso_post_zarandeo = 30000 * (1 - 0.01) = 29700.000
        assert_eq!(out.peso_post_zarandeo_kg, dec!(29700.000));

        // secado_pct = (15.2 - 13.5) / (100 - 13.5) * 100 = 1.70/86.5*100 ≈ 1.97
        assert_eq!(out.secado_pct, dec!(1.97));

        // manipuleo_pct = 0.25 (because secado > 0)
        assert_eq!(out.manipuleo_pct, dec!(0.25));
        // volatil_pct = 0.30
        assert_eq!(out.volatil_pct, dec!(0.30));

        // peso_final ≈ 28956.379
        assert_eq!(out.peso_final_kg, dec!(28956.379));
        // total_merma ≈ 1043.621
        assert_eq!(out.total_merma_kg, dec!(1043.621));
        // total_factor ≈ 0.9652
        assert_eq!(out.total_factor_pct, dec!(0.9652));
    }

    // ------------------------------------------------------------------
    // 2. Soja dry case: Hi <= Hf → no secado, no manipuleo
    // ------------------------------------------------------------------
    #[test]
    fn test_soja_dry_case() {
        let input = make_input(
            dec!(25000.000),
            dec!(12.0),    // Hi
            dec!(12.5),    // Hf — Hi <= Hf
            dec!(0.5),
            dec!(0.50),    // zarandeo
            dec!(0.25),    // manipuleo (should NOT apply)
            dec!(0.30),    // volatil
        );
        let out = calculate_merma_internal(&input).unwrap();

        assert_eq!(out.secado_pct, dec!(0.00));
        assert_eq!(out.manipuleo_pct, dec!(0.00));

        // Only zarandeo and volatil apply
        // post_zarandeo = 25000 * 0.995 = 24875.000
        assert_eq!(out.peso_post_zarandeo_kg, dec!(24875.000));
        // post_secado = same (no secado)
        assert_eq!(out.peso_post_secado_kg, dec!(24875.000));
        // post_manipuleo = same (no manipuleo)
        assert_eq!(out.peso_post_manipuleo_kg, dec!(24875.000));
        // peso_final = 24875 * (1 - 0.003) = 24875 * 0.997 = 24800.375
        assert_eq!(out.peso_final_kg, dec!(24800.375));
    }

    // ------------------------------------------------------------------
    // 3. Zero foreign matter (zarandeo_deduction = 0)
    // ------------------------------------------------------------------
    #[test]
    fn test_zero_foreign_matter() {
        let input = make_input(
            dec!(20000.000),
            dec!(16.0),
            dec!(14.0),
            dec!(0.0),     // no foreign matter
            dec!(0.00),    // no zarandeo deduction
            dec!(0.20),
            dec!(0.25),
        );
        let out = calculate_merma_internal(&input).unwrap();

        assert_eq!(out.zarandeo_pct, dec!(0.00));
        assert_eq!(out.peso_post_zarandeo_kg, dec!(20000.000));
        // secado should still apply
        assert!(out.secado_pct > Decimal::ZERO);
        // manipuleo should apply (secado > 0)
        assert_eq!(out.manipuleo_pct, dec!(0.20));
    }

    // ------------------------------------------------------------------
    // 4. Only volatil applied (no secado, no zarandeo)
    // ------------------------------------------------------------------
    #[test]
    fn test_only_volatil() {
        let input = make_input(
            dec!(10000.000),
            dec!(10.0),    // well below threshold
            dec!(14.0),    // high threshold
            dec!(0.0),
            dec!(0.00),    // no zarandeo
            dec!(0.50),    // manipuleo (won't apply)
            dec!(0.50),    // volatil
        );
        let out = calculate_merma_internal(&input).unwrap();

        assert_eq!(out.zarandeo_pct, dec!(0.00));
        assert_eq!(out.secado_pct, dec!(0.00));
        assert_eq!(out.manipuleo_pct, dec!(0.00));
        assert_eq!(out.volatil_pct, dec!(0.50));

        // Only volatil: 10000 * (1 - 0.005) = 9950.000
        assert_eq!(out.peso_final_kg, dec!(9950.000));
        assert_eq!(out.total_merma_kg, dec!(50.000));
    }

    // ------------------------------------------------------------------
    // 5. Negative weight rejected
    // ------------------------------------------------------------------
    #[test]
    fn test_negative_weight_rejected() {
        let input = make_input(
            dec!(-1000.000),
            dec!(15.0),
            dec!(13.5),
            dec!(1.0),
            dec!(1.00),
            dec!(0.25),
            dec!(0.30),
        );
        let result = calculate_merma_internal(&input);
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("peso_neto_bruto_kg must be positive"));
    }

    // ------------------------------------------------------------------
    // 6. Invalid JSON rejected (PyO3 interface)
    // ------------------------------------------------------------------
    #[test]
    fn test_invalid_json_rejected() {
        let result = calculate_merma("not valid json at all");
        assert!(result.is_err());
    }

    // ------------------------------------------------------------------
    // 7. Out of range humidity rejected
    // ------------------------------------------------------------------
    #[test]
    fn test_out_of_range_humidity() {
        let input = make_input(
            dec!(10000.000),
            dec!(150.0),   // invalid: > 100
            dec!(13.5),
            dec!(1.0),
            dec!(1.00),
            dec!(0.25),
            dec!(0.30),
        );
        let result = calculate_merma_internal(&input);
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("humedad_pct must be between 0 and 100"));
    }

    // ------------------------------------------------------------------
    // 8. Maiz calculation
    // ------------------------------------------------------------------
    #[test]
    fn test_maiz_calculation() {
        // Maiz: Hi=16.5, Hf=14.5, ME=2.0, peso=40000
        let input = make_input(
            dec!(40000.000),
            dec!(16.5),
            dec!(14.5),
            dec!(2.0),
            dec!(1.20),    // zarandeo
            dec!(0.25),    // manipuleo
            dec!(0.30),    // volatil
        );
        let out = calculate_merma_internal(&input).unwrap();

        // secado = (16.5 - 14.5) / (100 - 14.5) * 100 = 2/85.5*100 ≈ 2.34
        assert_eq!(out.secado_pct, dec!(2.34));
        // manipuleo applies (secado > 0)
        assert_eq!(out.manipuleo_pct, dec!(0.25));
        // Verify intermediate weights make sense
        assert!(out.peso_post_zarandeo_kg < dec!(40000.000));
        assert!(out.peso_post_secado_kg < out.peso_post_zarandeo_kg);
        assert!(out.peso_post_manipuleo_kg < out.peso_post_secado_kg);
        assert!(out.peso_final_kg < out.peso_post_manipuleo_kg);
        assert!(out.peso_final_kg > Decimal::ZERO);
    }

    // ------------------------------------------------------------------
    // 9. Girasol calculation
    // ------------------------------------------------------------------
    #[test]
    fn test_girasol_calculation() {
        // Girasol: Hi=12.0, Hf=11.0, ME=3.0, peso=35000
        let input = make_input(
            dec!(35000.000),
            dec!(12.0),
            dec!(11.0),
            dec!(3.0),
            dec!(1.50),    // zarandeo
            dec!(0.30),    // manipuleo
            dec!(0.25),    // volatil
        );
        let out = calculate_merma_internal(&input).unwrap();

        // secado = (12.0 - 11.0) / (100 - 11.0) * 100 = 1/89*100 ≈ 1.12
        assert_eq!(out.secado_pct, dec!(1.12));
        // manipuleo applies
        assert_eq!(out.manipuleo_pct, dec!(0.30));
        // Verify chain is monotonically decreasing
        assert!(out.peso_post_zarandeo_kg < dec!(35000.000));
        assert!(out.peso_post_secado_kg < out.peso_post_zarandeo_kg);
        assert!(out.peso_post_manipuleo_kg < out.peso_post_secado_kg);
        assert!(out.peso_final_kg < out.peso_post_manipuleo_kg);
    }

    // ------------------------------------------------------------------
    // 10. Total factor correctness
    // ------------------------------------------------------------------
    #[test]
    fn test_total_factor_correctness() {
        let input = make_input(
            dec!(50000.000),
            dec!(18.0),
            dec!(14.0),
            dec!(2.5),
            dec!(1.50),
            dec!(0.25),
            dec!(0.30),
        );
        let out = calculate_merma_internal(&input).unwrap();

        // total_factor should equal peso_final / peso_neto_bruto (rounded to 4dp)
        let expected_factor =
            (out.peso_final_kg / dec!(50000.000)).round_dp(4);
        assert_eq!(out.total_factor_pct, expected_factor);

        // total_merma should equal peso_neto_bruto - peso_final (rounded to 3dp)
        let expected_merma =
            (dec!(50000.000) - out.peso_final_kg).round_dp(3);
        assert_eq!(out.total_merma_kg, expected_merma);
    }

    // ------------------------------------------------------------------
    // 11. JSON roundtrip via PyO3 interface
    // ------------------------------------------------------------------
    #[test]
    fn test_json_roundtrip() {
        let json_in = make_json(
            "30000.000", "15.2", "13.5", "1.8", "1.00", "0.25", "0.30",
        );
        let result = calculate_merma(&json_in).unwrap();
        let parsed: serde_json::Value = serde_json::from_str(&result).unwrap();

        // Verify key fields are present and are strings (serde::str)
        assert!(parsed["peso_final_kg"].is_string());
        assert!(parsed["total_merma_kg"].is_string());
        assert!(parsed["total_factor_pct"].is_string());
        assert!(parsed["zarandeo_pct"].is_string());
    }

    // ------------------------------------------------------------------
    // 12. Zero weight rejected
    // ------------------------------------------------------------------
    #[test]
    fn test_zero_weight_rejected() {
        let input = make_input(
            dec!(0.000),
            dec!(15.0),
            dec!(13.5),
            dec!(1.0),
            dec!(1.00),
            dec!(0.25),
            dec!(0.30),
        );
        let result = calculate_merma_internal(&input);
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("peso_neto_bruto_kg must be positive"));
    }

    // ------------------------------------------------------------------
    // 13. Humidity exactly at threshold (boundary)
    // ------------------------------------------------------------------
    #[test]
    fn test_humidity_at_threshold() {
        let input = make_input(
            dec!(20000.000),
            dec!(13.5),    // Hi == Hf
            dec!(13.5),
            dec!(1.0),
            dec!(1.00),
            dec!(0.25),
            dec!(0.30),
        );
        let out = calculate_merma_internal(&input).unwrap();

        // secado should be zero when Hi == Hf
        assert_eq!(out.secado_pct, dec!(0.00));
        assert_eq!(out.manipuleo_pct, dec!(0.00));
    }
}
