// SPEC-024: ARCA CAEA Batch Builder
//
// Converts a JSON array of comprobante dicts into ARCA SOAP-compatible
// FECAEADetRequest list. Mirrors Python caea.py:232-302 logic.

use pyo3::prelude::*;
use serde::{Deserialize, Serialize};

use crate::GraviteaError;

// ---------------------------------------------------------------------------
// Default functions for serde
// ---------------------------------------------------------------------------

fn default_mon_id() -> String {
    "PES".to_string()
}

fn default_mon_cotiz() -> String {
    "1".to_string()
}

// ---------------------------------------------------------------------------
// Input structs (Deserialize from Python JSON)
// ---------------------------------------------------------------------------

#[derive(Deserialize)]
struct ComprobanteInput {
    concepto: i32,
    doc_tipo: i32,
    doc_nro: i64,
    cbte_desde: i64,
    cbte_hasta: i64,
    cbte_fch: String,
    imp_total: String,
    imp_tot_conc: String,
    imp_neto: String,
    imp_op_ex: String,
    imp_trib: String,
    imp_iva: String,
    #[serde(default = "default_mon_id")]
    mon_id: String,
    #[serde(default = "default_mon_cotiz")]
    mon_cotiz: String,
    #[serde(default)]
    alic_iva: Option<Vec<AlicIvaInput>>,
    #[serde(default)]
    tributos: Option<Vec<TributoInput>>,
    #[serde(default)]
    cbtes_asoc: Option<Vec<CbteAsocInput>>,
    #[serde(default)]
    fch_serv_desde: Option<String>,
    #[serde(default)]
    fch_serv_hasta: Option<String>,
    #[serde(default)]
    fch_vto_pago: Option<String>,
}

#[derive(Deserialize)]
struct AlicIvaInput {
    iva_id: i32,
    base_imp: String,
    importe: String,
}

#[derive(Deserialize)]
struct TributoInput {
    tributo_id: i32,
    desc: String,
    base_imp: String,
    alic: String,
    importe: String,
}

#[derive(Deserialize)]
struct CbteAsocInput {
    tipo: i32,
    pto_vta: i32,
    nro: i64,
    #[serde(default)]
    cuit: Option<String>,
}

// ---------------------------------------------------------------------------
// Output structs (Serialize to ARCA SOAP-compatible JSON)
// ---------------------------------------------------------------------------

#[derive(Serialize)]
#[serde(rename_all = "PascalCase")]
struct FECAEADetRequest {
    concepto: i32,
    doc_tipo: i32,
    doc_nro: i64,
    cbte_desde: i64,
    cbte_hasta: i64,
    cbte_fch: String,
    imp_total: f64,
    imp_tot_conc: f64,
    imp_neto: f64,
    imp_op_ex: f64,
    imp_trib: f64,
    #[serde(rename = "ImpIVA")]
    imp_iva: f64,
    mon_id: String,
    mon_cotiz: f64,
    #[serde(rename = "CAEA")]
    caea: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    fch_serv_desde: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    fch_serv_hasta: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    fch_vto_pago: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    iva: Option<IvaWrapper>,
    #[serde(skip_serializing_if = "Option::is_none")]
    tributos: Option<TributosWrapper>,
    #[serde(skip_serializing_if = "Option::is_none")]
    cbtes_asoc: Option<CbtesAsocWrapper>,
}

#[derive(Serialize)]
struct IvaWrapper {
    #[serde(rename = "AlicIva")]
    alic_iva: Vec<AlicIvaOutput>,
}

#[derive(Serialize)]
struct AlicIvaOutput {
    #[serde(rename = "Id")]
    id: i32,
    #[serde(rename = "BaseImp")]
    base_imp: f64,
    #[serde(rename = "Importe")]
    importe: f64,
}

#[derive(Serialize)]
struct TributosWrapper {
    #[serde(rename = "Tributo")]
    tributo: Vec<TributoOutput>,
}

#[derive(Serialize)]
struct TributoOutput {
    #[serde(rename = "Id")]
    id: i32,
    #[serde(rename = "Desc")]
    desc: String,
    #[serde(rename = "BaseImp")]
    base_imp: f64,
    #[serde(rename = "Alic")]
    alic: f64,
    #[serde(rename = "Importe")]
    importe: f64,
}

#[derive(Serialize)]
struct CbtesAsocWrapper {
    #[serde(rename = "CbteAsoc")]
    cbte_asoc: Vec<CbteAsocOutput>,
}

#[derive(Serialize)]
struct CbteAsocOutput {
    #[serde(rename = "Tipo")]
    tipo: i32,
    #[serde(rename = "PtoVta")]
    pto_vta: i32,
    #[serde(rename = "Nro")]
    nro: i64,
    #[serde(rename = "Cuit")]
    cuit: String,
}

// ---------------------------------------------------------------------------
// Conversion logic
// ---------------------------------------------------------------------------

fn convert_comprobante(
    cbte: ComprobanteInput,
    caea: &str,
    default_cuit: &str,
) -> Result<FECAEADetRequest, GraviteaError> {
    let parse_f64 = |s: &str, field: &str| -> Result<f64, GraviteaError> {
        s.parse::<f64>()
            .map_err(|e| GraviteaError::ARCABuildError(format!("Invalid {field}: {e}")))
    };

    let imp_trib_f64 = parse_f64(&cbte.imp_trib, "imp_trib")?;

    // Service dates: only for Concepto 2 (services) or 3 (products + services)
    let (fch_serv_desde, fch_serv_hasta, fch_vto_pago) =
        if cbte.concepto == 2 || cbte.concepto == 3 {
            (cbte.fch_serv_desde, cbte.fch_serv_hasta, cbte.fch_vto_pago)
        } else {
            (None, None, None)
        };

    // IVA: present AND non-empty
    let iva = match cbte.alic_iva {
        Some(ref items) if !items.is_empty() => {
            let alic_iva = items
                .iter()
                .map(|item| {
                    Ok(AlicIvaOutput {
                        id: item.iva_id,
                        base_imp: parse_f64(&item.base_imp, "alic_iva.base_imp")?,
                        importe: parse_f64(&item.importe, "alic_iva.importe")?,
                    })
                })
                .collect::<Result<Vec<_>, GraviteaError>>()?;
            Some(IvaWrapper { alic_iva })
        }
        _ => None,
    };

    // Tributos: present AND non-empty AND imp_trib > 0.0
    let tributos_out = match cbte.tributos {
        Some(ref items) if !items.is_empty() && imp_trib_f64 > 0.0 => {
            let tributo = items
                .iter()
                .map(|item| {
                    Ok(TributoOutput {
                        id: item.tributo_id,
                        desc: item.desc.clone(),
                        base_imp: parse_f64(&item.base_imp, "tributo.base_imp")?,
                        alic: parse_f64(&item.alic, "tributo.alic")?,
                        importe: parse_f64(&item.importe, "tributo.importe")?,
                    })
                })
                .collect::<Result<Vec<_>, GraviteaError>>()?;
            Some(TributosWrapper { tributo })
        }
        _ => None,
    };

    // CbtesAsoc: present with CUIT fallback to default_cuit
    let cbtes_asoc_out = match cbte.cbtes_asoc {
        Some(ref items) if !items.is_empty() => {
            let cbte_asoc = items
                .iter()
                .map(|item| CbteAsocOutput {
                    tipo: item.tipo,
                    pto_vta: item.pto_vta,
                    nro: item.nro,
                    cuit: item
                        .cuit
                        .clone()
                        .unwrap_or_else(|| default_cuit.to_string()),
                })
                .collect();
            Some(CbtesAsocWrapper { cbte_asoc })
        }
        _ => None,
    };

    Ok(FECAEADetRequest {
        concepto: cbte.concepto,
        doc_tipo: cbte.doc_tipo,
        doc_nro: cbte.doc_nro,
        cbte_desde: cbte.cbte_desde,
        cbte_hasta: cbte.cbte_hasta,
        cbte_fch: cbte.cbte_fch,
        imp_total: parse_f64(&cbte.imp_total, "imp_total")?,
        imp_tot_conc: parse_f64(&cbte.imp_tot_conc, "imp_tot_conc")?,
        imp_neto: parse_f64(&cbte.imp_neto, "imp_neto")?,
        imp_op_ex: parse_f64(&cbte.imp_op_ex, "imp_op_ex")?,
        imp_trib: imp_trib_f64,
        imp_iva: parse_f64(&cbte.imp_iva, "imp_iva")?,
        mon_id: cbte.mon_id,
        mon_cotiz: parse_f64(&cbte.mon_cotiz, "mon_cotiz")?,
        caea: caea.to_string(),
        fch_serv_desde,
        fch_serv_hasta,
        fch_vto_pago,
        iva,
        tributos: tributos_out,
        cbtes_asoc: cbtes_asoc_out,
    })
}

// ---------------------------------------------------------------------------
// Internal entry point (testable without Python runtime)
// ---------------------------------------------------------------------------

fn _build_internal(
    comprobantes_json: &str,
    caea: &str,
    default_cuit: &str,
) -> Result<String, GraviteaError> {
    let comprobantes: Vec<ComprobanteInput> = serde_json::from_str(comprobantes_json)
        .map_err(|e| GraviteaError::ARCABuildError(format!("JSON parse error: {e}")))?;

    let det_list: Vec<FECAEADetRequest> = comprobantes
        .into_iter()
        .map(|cbte| convert_comprobante(cbte, caea, default_cuit))
        .collect::<Result<_, _>>()?;

    serde_json::to_string(&det_list)
        .map_err(|e| GraviteaError::ARCABuildError(format!("JSON serialize error: {e}")))
}

// ---------------------------------------------------------------------------
// PyO3 entry point
// ---------------------------------------------------------------------------

#[pyfunction]
pub fn build_caea_batch_request(
    py: Python,
    comprobantes_json: &str,
    caea: &str,
    default_cuit: &str,
) -> PyResult<String> {
    let caea_owned = caea.to_owned();
    let default_cuit_owned = default_cuit.to_owned();
    let json_owned = comprobantes_json.to_owned();

    let result = py.detach(|| _build_internal(&json_owned, &caea_owned, &default_cuit_owned));
    result.map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    fn minimal_cbte_json(overrides: &str) -> String {
        let base = r#"{
            "concepto": 1,
            "doc_tipo": 80,
            "doc_nro": 20111111113,
            "cbte_desde": 1,
            "cbte_hasta": 1,
            "cbte_fch": "20260228",
            "imp_total": "121.00",
            "imp_tot_conc": "0",
            "imp_neto": "100.00",
            "imp_op_ex": "0",
            "imp_trib": "0",
            "imp_iva": "21.00"
        }"#;

        if overrides.is_empty() {
            return format!("[{base}]");
        }

        // Merge overrides into the base JSON
        let mut base_val: serde_json::Value = serde_json::from_str(base).unwrap();
        let overrides_val: serde_json::Value = serde_json::from_str(overrides).unwrap();

        if let (serde_json::Value::Object(ref mut b), serde_json::Value::Object(ref o)) =
            (&mut base_val, &overrides_val)
        {
            for (k, v) in o {
                b.insert(k.clone(), v.clone());
            }
        }

        format!("[{}]", serde_json::to_string(&base_val).unwrap())
    }

    #[test]
    fn test_basic_concepto_1() {
        let json = minimal_cbte_json("");
        let result = _build_internal(&json, "12345678901234", "20111111113").unwrap();
        let parsed: Vec<serde_json::Value> = serde_json::from_str(&result).unwrap();

        assert_eq!(parsed.len(), 1);
        let det = &parsed[0];
        assert_eq!(det["Concepto"], 1);
        assert_eq!(det["DocTipo"], 80);
        assert_eq!(det["DocNro"], 20111111113_i64);
        assert_eq!(det["ImpTotal"], 121.0);
        assert_eq!(det["ImpNeto"], 100.0);
        assert_eq!(det["CAEA"], "12345678901234");
        // Service dates must NOT be present for concepto 1
        assert!(det.get("FchServDesde").is_none());
        assert!(det.get("FchServHasta").is_none());
        assert!(det.get("FchVtoPago").is_none());
    }

    #[test]
    fn test_service_dates_concepto_2() {
        let json = minimal_cbte_json(
            r#"{
                "concepto": 2,
                "fch_serv_desde": "20260201",
                "fch_serv_hasta": "20260228",
                "fch_vto_pago": "20260315"
            }"#,
        );
        let result = _build_internal(&json, "CAEA123", "20111111113").unwrap();
        let parsed: Vec<serde_json::Value> = serde_json::from_str(&result).unwrap();
        let det = &parsed[0];

        assert_eq!(det["Concepto"], 2);
        assert_eq!(det["FchServDesde"], "20260201");
        assert_eq!(det["FchServHasta"], "20260228");
        assert_eq!(det["FchVtoPago"], "20260315");
    }

    #[test]
    fn test_service_dates_concepto_3() {
        let json = minimal_cbte_json(
            r#"{
                "concepto": 3,
                "fch_serv_desde": "20260101",
                "fch_serv_hasta": "20260131",
                "fch_vto_pago": "20260215"
            }"#,
        );
        let result = _build_internal(&json, "CAEA456", "20111111113").unwrap();
        let parsed: Vec<serde_json::Value> = serde_json::from_str(&result).unwrap();
        let det = &parsed[0];

        assert_eq!(det["Concepto"], 3);
        assert_eq!(det["FchServDesde"], "20260101");
        assert_eq!(det["FchServHasta"], "20260131");
        assert_eq!(det["FchVtoPago"], "20260215");
    }

    #[test]
    fn test_iva_single_rate() {
        let json = minimal_cbte_json(
            r#"{
                "alic_iva": [
                    {"iva_id": 5, "base_imp": "100.00", "importe": "21.00"}
                ]
            }"#,
        );
        let result = _build_internal(&json, "CAEA789", "20111111113").unwrap();
        let parsed: Vec<serde_json::Value> = serde_json::from_str(&result).unwrap();
        let det = &parsed[0];

        let iva = &det["Iva"];
        assert!(iva.is_object());
        let alic_iva = iva["AlicIva"].as_array().unwrap();
        assert_eq!(alic_iva.len(), 1);
        assert_eq!(alic_iva[0]["Id"], 5);
        assert_eq!(alic_iva[0]["BaseImp"], 100.0);
        assert_eq!(alic_iva[0]["Importe"], 21.0);
    }

    #[test]
    fn test_iva_multi_rate() {
        let json = minimal_cbte_json(
            r#"{
                "alic_iva": [
                    {"iva_id": 5, "base_imp": "80.00", "importe": "16.80"},
                    {"iva_id": 4, "base_imp": "20.00", "importe": "2.10"}
                ]
            }"#,
        );
        let result = _build_internal(&json, "CAEA000", "20111111113").unwrap();
        let parsed: Vec<serde_json::Value> = serde_json::from_str(&result).unwrap();
        let det = &parsed[0];

        let alic_iva = det["Iva"]["AlicIva"].as_array().unwrap();
        assert_eq!(alic_iva.len(), 2);
        assert_eq!(alic_iva[0]["Id"], 5);
        assert_eq!(alic_iva[1]["Id"], 4);
    }

    #[test]
    fn test_tributos_present() {
        let json = minimal_cbte_json(
            r#"{
                "imp_trib": "15.50",
                "tributos": [
                    {
                        "tributo_id": 99,
                        "desc": "Impuesto municipal",
                        "base_imp": "100.00",
                        "alic": "15.5",
                        "importe": "15.50"
                    }
                ]
            }"#,
        );
        let result = _build_internal(&json, "CAEA111", "20111111113").unwrap();
        let parsed: Vec<serde_json::Value> = serde_json::from_str(&result).unwrap();
        let det = &parsed[0];

        let tributos = &det["Tributos"];
        assert!(tributos.is_object());
        let tributo = tributos["Tributo"].as_array().unwrap();
        assert_eq!(tributo.len(), 1);
        assert_eq!(tributo[0]["Id"], 99);
        assert_eq!(tributo[0]["Desc"], "Impuesto municipal");
        assert_eq!(tributo[0]["BaseImp"], 100.0);
        assert_eq!(tributo[0]["Alic"], 15.5);
        assert_eq!(tributo[0]["Importe"], 15.5);
    }

    #[test]
    fn test_tributos_guarded_zero() {
        // imp_trib = "0" → tributos section MUST be omitted even if tributos array present
        let json = minimal_cbte_json(
            r#"{
                "imp_trib": "0",
                "tributos": [
                    {
                        "tributo_id": 99,
                        "desc": "Municipal",
                        "base_imp": "100.00",
                        "alic": "5.0",
                        "importe": "5.00"
                    }
                ]
            }"#,
        );
        let result = _build_internal(&json, "CAEA222", "20111111113").unwrap();
        let parsed: Vec<serde_json::Value> = serde_json::from_str(&result).unwrap();
        let det = &parsed[0];

        // Tributos must NOT be present because imp_trib == 0
        assert!(det.get("Tributos").is_none());
    }

    #[test]
    fn test_cbtes_asoc_with_cuit() {
        let json = minimal_cbte_json(
            r#"{
                "cbtes_asoc": [
                    {"tipo": 1, "pto_vta": 5, "nro": 123, "cuit": "30111111118"}
                ]
            }"#,
        );
        let result = _build_internal(&json, "CAEA333", "20111111113").unwrap();
        let parsed: Vec<serde_json::Value> = serde_json::from_str(&result).unwrap();
        let det = &parsed[0];

        let cbtes_asoc = &det["CbtesAsoc"];
        let cbte_asoc = cbtes_asoc["CbteAsoc"].as_array().unwrap();
        assert_eq!(cbte_asoc.len(), 1);
        assert_eq!(cbte_asoc[0]["Tipo"], 1);
        assert_eq!(cbte_asoc[0]["PtoVta"], 5);
        assert_eq!(cbte_asoc[0]["Nro"], 123);
        assert_eq!(cbte_asoc[0]["Cuit"], "30111111118");
    }

    #[test]
    fn test_cbtes_asoc_cuit_fallback() {
        // When cuit is absent, default_cuit should be used
        let json = minimal_cbte_json(
            r#"{
                "cbtes_asoc": [
                    {"tipo": 6, "pto_vta": 1, "nro": 999}
                ]
            }"#,
        );
        let result = _build_internal(&json, "CAEA444", "20999999990").unwrap();
        let parsed: Vec<serde_json::Value> = serde_json::from_str(&result).unwrap();
        let det = &parsed[0];

        let cbte_asoc = det["CbtesAsoc"]["CbteAsoc"].as_array().unwrap();
        assert_eq!(cbte_asoc[0]["Cuit"], "20999999990");
    }

    #[test]
    fn test_empty_optional_arrays() {
        // No alic_iva, no tributos, no cbtes_asoc → all omitted from output
        let json = minimal_cbte_json("");
        let result = _build_internal(&json, "CAEA555", "20111111113").unwrap();
        let parsed: Vec<serde_json::Value> = serde_json::from_str(&result).unwrap();
        let det = &parsed[0];

        assert!(det.get("Iva").is_none());
        assert!(det.get("Tributos").is_none());
        assert!(det.get("CbtesAsoc").is_none());
    }

    #[test]
    fn test_defaults_mon_id_mon_cotiz() {
        // When mon_id and mon_cotiz are absent, defaults apply
        let json = r#"[{
            "concepto": 1,
            "doc_tipo": 80,
            "doc_nro": 20111111113,
            "cbte_desde": 1,
            "cbte_hasta": 1,
            "cbte_fch": "20260228",
            "imp_total": "100.00",
            "imp_tot_conc": "0",
            "imp_neto": "100.00",
            "imp_op_ex": "0",
            "imp_trib": "0",
            "imp_iva": "0"
        }]"#;
        let result = _build_internal(json, "CAEA666", "20111111113").unwrap();
        let parsed: Vec<serde_json::Value> = serde_json::from_str(&result).unwrap();
        let det = &parsed[0];

        assert_eq!(det["MonId"], "PES");
        assert_eq!(det["MonCotiz"], 1.0);
    }

    #[test]
    fn test_large_batch_100_items() {
        let single = r#"{
            "concepto": 1,
            "doc_tipo": 80,
            "doc_nro": 20111111113,
            "cbte_desde": 1,
            "cbte_hasta": 1,
            "cbte_fch": "20260228",
            "imp_total": "100.00",
            "imp_tot_conc": "0",
            "imp_neto": "100.00",
            "imp_op_ex": "0",
            "imp_trib": "0",
            "imp_iva": "0"
        }"#;
        let items: Vec<&str> = (0..100).map(|_| single).collect();
        let json = format!("[{}]", items.join(","));

        let result = _build_internal(&json, "CAEA_BATCH", "20111111113").unwrap();
        let parsed: Vec<serde_json::Value> = serde_json::from_str(&result).unwrap();
        assert_eq!(parsed.len(), 100);

        // Verify each item has CAEA set
        for det in &parsed {
            assert_eq!(det["CAEA"], "CAEA_BATCH");
        }
    }

    #[test]
    fn test_imp_iva_key_name() {
        // Verify JSON contains "ImpIVA" (NOT "ImpIva" which PascalCase would produce)
        let json = minimal_cbte_json("");
        let result = _build_internal(&json, "CAEA777", "20111111113").unwrap();

        assert!(result.contains("\"ImpIVA\""), "Expected ImpIVA key in output");
        assert!(
            !result.contains("\"ImpIva\""),
            "Must NOT contain ImpIva (wrong casing)"
        );
    }

    #[test]
    fn test_caea_key_name() {
        // Verify JSON contains "CAEA" (NOT "Caea" which PascalCase would produce)
        let json = minimal_cbte_json("");
        let result = _build_internal(&json, "TEST_CAEA_VALUE", "20111111113").unwrap();

        assert!(result.contains("\"CAEA\""), "Expected CAEA key in output");
        assert!(
            !result.contains("\"Caea\""),
            "Must NOT contain Caea (wrong casing)"
        );
        assert!(
            result.contains("\"TEST_CAEA_VALUE\""),
            "Expected CAEA value in output"
        );
    }

    #[test]
    fn test_negative_imp_trib() {
        // imp_trib = "-1.5" → tributos MUST be omitted (not > 0.0)
        let json = minimal_cbte_json(
            r#"{
                "imp_trib": "-1.5",
                "tributos": [
                    {
                        "tributo_id": 1,
                        "desc": "Test",
                        "base_imp": "100.00",
                        "alic": "1.5",
                        "importe": "1.50"
                    }
                ]
            }"#,
        );
        let result = _build_internal(&json, "CAEA888", "20111111113").unwrap();
        let parsed: Vec<serde_json::Value> = serde_json::from_str(&result).unwrap();
        let det = &parsed[0];

        assert!(det.get("Tributos").is_none());
        assert_eq!(det["ImpTrib"], -1.5);
    }

    #[test]
    fn test_invalid_amount_returns_error() {
        let json = minimal_cbte_json(r#"{"imp_total": "not_a_number"}"#);
        let result = _build_internal(&json, "CAEA999", "20111111113");

        assert!(result.is_err());
        let err_msg = result.unwrap_err().to_string();
        assert!(
            err_msg.contains("imp_total"),
            "Error should mention the field name"
        );
    }

    #[test]
    fn test_invalid_json_returns_error() {
        let result = _build_internal("not valid json", "CAEA", "20111111113");
        assert!(result.is_err());
        let err_msg = result.unwrap_err().to_string();
        assert!(
            err_msg.contains("JSON parse error"),
            "Error should mention JSON parse"
        );
    }

    #[test]
    fn test_empty_alic_iva_array_treated_as_absent() {
        // alic_iva: [] → IVA section must be omitted
        let json = minimal_cbte_json(r#"{"alic_iva": []}"#);
        let result = _build_internal(&json, "CAEA_EMPTY", "20111111113").unwrap();
        let parsed: Vec<serde_json::Value> = serde_json::from_str(&result).unwrap();
        let det = &parsed[0];

        assert!(det.get("Iva").is_none(), "Empty alic_iva should not produce Iva key");
    }

    #[test]
    fn test_concepto_1_strips_service_dates() {
        // Even if service dates are provided, concepto 1 must not include them
        let json = minimal_cbte_json(
            r#"{
                "concepto": 1,
                "fch_serv_desde": "20260101",
                "fch_serv_hasta": "20260131",
                "fch_vto_pago": "20260215"
            }"#,
        );
        let result = _build_internal(&json, "CAEA_STRIP", "20111111113").unwrap();
        let parsed: Vec<serde_json::Value> = serde_json::from_str(&result).unwrap();
        let det = &parsed[0];

        assert!(det.get("FchServDesde").is_none());
        assert!(det.get("FchServHasta").is_none());
        assert!(det.get("FchVtoPago").is_none());
    }

    #[test]
    fn test_custom_mon_id_and_cotiz() {
        let json = minimal_cbte_json(
            r#"{
                "mon_id": "DOL",
                "mon_cotiz": "1050.50"
            }"#,
        );
        let result = _build_internal(&json, "CAEA_MON", "20111111113").unwrap();
        let parsed: Vec<serde_json::Value> = serde_json::from_str(&result).unwrap();
        let det = &parsed[0];

        assert_eq!(det["MonId"], "DOL");
        assert_eq!(det["MonCotiz"], 1050.5);
    }

    #[test]
    fn test_full_comprobante_all_sections() {
        let json = r#"[{
            "concepto": 3,
            "doc_tipo": 80,
            "doc_nro": 20333333339,
            "cbte_desde": 10,
            "cbte_hasta": 10,
            "cbte_fch": "20260301",
            "imp_total": "242.00",
            "imp_tot_conc": "0",
            "imp_neto": "200.00",
            "imp_op_ex": "0",
            "imp_trib": "10.00",
            "imp_iva": "32.00",
            "mon_id": "DOL",
            "mon_cotiz": "1100",
            "fch_serv_desde": "20260201",
            "fch_serv_hasta": "20260228",
            "fch_vto_pago": "20260315",
            "alic_iva": [
                {"iva_id": 5, "base_imp": "200.00", "importe": "42.00"}
            ],
            "tributos": [
                {
                    "tributo_id": 1,
                    "desc": "IIBB",
                    "base_imp": "200.00",
                    "alic": "5.0",
                    "importe": "10.00"
                }
            ],
            "cbtes_asoc": [
                {"tipo": 1, "pto_vta": 5, "nro": 50, "cuit": "30222222227"},
                {"tipo": 6, "pto_vta": 5, "nro": 51}
            ]
        }]"#;
        let result = _build_internal(json, "FULL_CAEA", "20111111113").unwrap();
        let parsed: Vec<serde_json::Value> = serde_json::from_str(&result).unwrap();
        assert_eq!(parsed.len(), 1);
        let det = &parsed[0];

        // Core fields
        assert_eq!(det["Concepto"], 3);
        assert_eq!(det["CAEA"], "FULL_CAEA");
        assert_eq!(det["MonId"], "DOL");
        assert_eq!(det["MonCotiz"], 1100.0);

        // Service dates present for concepto 3
        assert_eq!(det["FchServDesde"], "20260201");

        // IVA
        let alic = det["Iva"]["AlicIva"].as_array().unwrap();
        assert_eq!(alic.len(), 1);
        assert_eq!(alic[0]["Id"], 5);

        // Tributos (imp_trib > 0)
        let trib = det["Tributos"]["Tributo"].as_array().unwrap();
        assert_eq!(trib.len(), 1);
        assert_eq!(trib[0]["Desc"], "IIBB");

        // CbtesAsoc with CUIT fallback on second item
        let asoc = det["CbtesAsoc"]["CbteAsoc"].as_array().unwrap();
        assert_eq!(asoc.len(), 2);
        assert_eq!(asoc[0]["Cuit"], "30222222227"); // explicit
        assert_eq!(asoc[1]["Cuit"], "20111111113"); // fallback to default_cuit
    }
}
