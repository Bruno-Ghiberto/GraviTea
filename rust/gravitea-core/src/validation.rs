use std::collections::{HashMap, HashSet};

use pyo3::prelude::*;
use pyo3::exceptions::PyValueError;
use regex::Regex;
use serde::Deserialize;
use serde_json::Value;
use std::sync::LazyLock;

use crate::errors::GraviteaError;

static DATE_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^\d{4}-\d{2}-\d{2}$").unwrap()
});

#[derive(Deserialize)]
struct FieldDefinition {
    field_key: String,
    field_type: String,
    choices: Option<Vec<String>>,
}

fn validate_text(value: &Value) -> Option<String> {
    if value.is_string() {
        None
    } else {
        Some("Expected a text value.".to_string())
    }
}

fn validate_integer(value: &Value) -> Option<String> {
    if value.is_boolean() {
        return Some("Expected an integer value.".to_string());
    }
    match value {
        Value::Number(n) if n.is_i64() => None,
        _ => Some("Expected an integer value.".to_string()),
    }
}

fn validate_decimal(value: &Value) -> Option<String> {
    if value.is_boolean() {
        return Some("Expected a decimal value.".to_string());
    }
    if value.is_number() {
        None
    } else {
        Some("Expected a decimal value.".to_string())
    }
}

fn validate_boolean(value: &Value) -> Option<String> {
    if value.is_boolean() {
        None
    } else {
        Some("Expected a boolean value.".to_string())
    }
}

fn validate_date(value: &Value) -> Option<String> {
    match value.as_str() {
        Some(s) if DATE_RE.is_match(s) => None,
        _ => Some("Expected a date in YYYY-MM-DD format.".to_string()),
    }
}

fn validate_select(value: &Value, choices: &Option<Vec<String>>) -> Option<String> {
    let allowed: Vec<&String> = match choices {
        Some(ref c) => c.iter().collect(),
        None => Vec::new(),
    };
    let allowed_set: HashSet<&str> = allowed.iter().map(|s| s.as_str()).collect();

    match value.as_str() {
        Some(s) if allowed_set.contains(s) => None,
        _ => {
            let formatted = format!(
                "[{}]",
                allowed
                    .iter()
                    .map(|s| format!("'{}'", s))
                    .collect::<Vec<_>>()
                    .join(", ")
            );
            Some(format!("Invalid choice. Allowed: {}", formatted))
        }
    }
}

fn validate_field(defn: &FieldDefinition, value: &Value) -> Option<String> {
    match defn.field_type.as_str() {
        "text" => validate_text(value),
        "integer" => validate_integer(value),
        "decimal" => validate_decimal(value),
        "boolean" => validate_boolean(value),
        "date" => validate_date(value),
        "select" => validate_select(value, &defn.choices),
        _ => None, // Unknown field types pass silently
    }
}

#[pyfunction]
pub fn validate_custom_fields(
    defs_json: &str,
    data_json: &str,
) -> PyResult<String> {
    _validate_internal(defs_json, data_json)
        .map_err(|e| PyValueError::new_err(e.to_string()))
}

fn _validate_internal(
    defs_json: &str,
    data_json: &str,
) -> Result<String, GraviteaError> {
    let definitions: Vec<FieldDefinition> = serde_json::from_str(defs_json)
        .map_err(|e| GraviteaError::ValidationFieldError(
            format!("Invalid definitions JSON: {}", e),
        ))?;

    let custom_data: HashMap<String, Value> = serde_json::from_str(data_json)
        .map_err(|e| GraviteaError::ValidationFieldError(
            format!("Invalid data JSON: {}", e),
        ))?;

    let lookup: HashMap<&str, &FieldDefinition> = definitions
        .iter()
        .map(|d| (d.field_key.as_str(), d))
        .collect();

    let mut errors: HashMap<String, Vec<String>> = HashMap::new();

    for (key, value) in &custom_data {
        if value.is_null() {
            continue;
        }

        let defn = match lookup.get(key.as_str()) {
            Some(d) => d,
            None => continue,
        };

        if let Some(err_msg) = validate_field(defn, value) {
            errors.insert(key.clone(), vec![err_msg]);
        }
    }

    serde_json::to_string(&errors)
        .map_err(|e| GraviteaError::ValidationFieldError(
            format!("Failed to serialize errors: {}", e),
        ))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn defs(entries: &[(&str, &str, Option<Vec<&str>>)]) -> String {
        let items: Vec<String> = entries
            .iter()
            .map(|(key, ft, choices)| {
                let choices_json = match choices {
                    Some(c) => {
                        let items: Vec<String> =
                            c.iter().map(|s| format!("\"{}\"", s)).collect();
                        format!("[{}]", items.join(", "))
                    }
                    None => "null".to_string(),
                };
                format!(
                    r#"{{"field_key":"{}","field_type":"{}","choices":{}}}"#,
                    key, ft, choices_json
                )
            })
            .collect();
        format!("[{}]", items.join(", "))
    }

    fn parse_errors(json: &str) -> HashMap<String, Vec<String>> {
        serde_json::from_str(json).unwrap()
    }

    // T006 Test 1: text valid
    #[test]
    fn test_text_valid() {
        let d = defs(&[("name", "text", None)]);
        let data = r#"{"name": "hello"}"#;
        let result = _validate_internal(&d, data).unwrap();
        let errors = parse_errors(&result);
        assert!(errors.is_empty());
    }

    // T006 Test 2: text invalid
    #[test]
    fn test_text_invalid() {
        let d = defs(&[("name", "text", None)]);
        let data = r#"{"name": 42}"#;
        let result = _validate_internal(&d, data).unwrap();
        let errors = parse_errors(&result);
        assert_eq!(errors["name"], vec!["Expected a text value."]);
    }

    // T006 Test 3: integer valid
    #[test]
    fn test_integer_valid() {
        let d = defs(&[("qty", "integer", None)]);
        let data = r#"{"qty": 5}"#;
        let result = _validate_internal(&d, data).unwrap();
        let errors = parse_errors(&result);
        assert!(errors.is_empty());
    }

    // T006 Test 4: integer bool rejected
    #[test]
    fn test_integer_bool_rejected() {
        let d = defs(&[("qty", "integer", None)]);
        let data = r#"{"qty": true}"#;
        let result = _validate_internal(&d, data).unwrap();
        let errors = parse_errors(&result);
        assert_eq!(errors["qty"], vec!["Expected an integer value."]);
    }

    // T006 Test 5: decimal valid float
    #[test]
    fn test_decimal_valid_float() {
        let d = defs(&[("price", "decimal", None)]);
        let data = r#"{"price": 9.99}"#;
        let result = _validate_internal(&d, data).unwrap();
        let errors = parse_errors(&result);
        assert!(errors.is_empty());
    }

    // T006 Test 6: decimal int accepted
    #[test]
    fn test_decimal_int_accepted() {
        let d = defs(&[("price", "decimal", None)]);
        let data = r#"{"price": 5}"#;
        let result = _validate_internal(&d, data).unwrap();
        let errors = parse_errors(&result);
        assert!(errors.is_empty());
    }

    // T006 Test 7: decimal bool rejected
    #[test]
    fn test_decimal_bool_rejected() {
        let d = defs(&[("price", "decimal", None)]);
        let data = r#"{"price": true}"#;
        let result = _validate_internal(&d, data).unwrap();
        let errors = parse_errors(&result);
        assert_eq!(errors["price"], vec!["Expected a decimal value."]);
    }

    // T006 Test 8: boolean valid
    #[test]
    fn test_boolean_valid() {
        let d = defs(&[("active", "boolean", None)]);
        let data = r#"{"active": true}"#;
        let result = _validate_internal(&d, data).unwrap();
        let errors = parse_errors(&result);
        assert!(errors.is_empty());
    }

    // T006 Test 9: boolean invalid
    #[test]
    fn test_boolean_invalid() {
        let d = defs(&[("active", "boolean", None)]);
        let data = r#"{"active": "yes"}"#;
        let result = _validate_internal(&d, data).unwrap();
        let errors = parse_errors(&result);
        assert_eq!(errors["active"], vec!["Expected a boolean value."]);
    }

    // T006 Test 10: date valid format
    #[test]
    fn test_date_valid_format() {
        let d = defs(&[("expiry", "date", None)]);
        let data = r#"{"expiry": "2024-12-31"}"#;
        let result = _validate_internal(&d, data).unwrap();
        let errors = parse_errors(&result);
        assert!(errors.is_empty());
    }

    // T006 Test 11: date format only (no calendar validation)
    #[test]
    fn test_date_format_only() {
        let d = defs(&[("expiry", "date", None)]);
        let data = r#"{"expiry": "2026-02-29"}"#;
        let result = _validate_internal(&d, data).unwrap();
        let errors = parse_errors(&result);
        assert!(errors.is_empty(), "2026-02-29 must be accepted (format-only, no calendar check)");
    }

    // T006 Test 12: date invalid
    #[test]
    fn test_date_invalid() {
        let d = defs(&[("expiry", "date", None)]);
        let data = r#"{"expiry": "not-a-date"}"#;
        let result = _validate_internal(&d, data).unwrap();
        let errors = parse_errors(&result);
        assert_eq!(errors["expiry"], vec!["Expected a date in YYYY-MM-DD format."]);
    }

    // T006 Test 13: select valid
    #[test]
    fn test_select_valid() {
        let d = defs(&[("material", "select", Some(vec!["acero", "aluminio", "bronce"]))]);
        let data = r#"{"material": "acero"}"#;
        let result = _validate_internal(&d, data).unwrap();
        let errors = parse_errors(&result);
        assert!(errors.is_empty());
    }

    // T006 Test 14: select invalid with single-quote format
    #[test]
    fn test_select_invalid_format() {
        let d = defs(&[("material", "select", Some(vec!["acero", "aluminio", "bronce"]))]);
        let data = r#"{"material": "cobre"}"#;
        let result = _validate_internal(&d, data).unwrap();
        let errors = parse_errors(&result);
        assert_eq!(
            errors["material"],
            vec!["Invalid choice. Allowed: ['acero', 'aluminio', 'bronce']"]
        );
    }

    // T006 Test 15: null values skipped
    #[test]
    fn test_null_values_skipped() {
        let d = defs(&[("name", "text", None)]);
        let data = r#"{"name": null}"#;
        let result = _validate_internal(&d, data).unwrap();
        let errors = parse_errors(&result);
        assert!(errors.is_empty());
    }

    // T006 Test 16: undefined keys ignored
    #[test]
    fn test_undefined_keys_ignored() {
        let d = defs(&[("name", "text", None)]);
        let data = r#"{"unknown_key": 42}"#;
        let result = _validate_internal(&d, data).unwrap();
        let errors = parse_errors(&result);
        assert!(errors.is_empty());
    }

    // T006 Test 17: unknown field type passes
    #[test]
    fn test_unknown_field_type_passes() {
        let d = defs(&[("custom", "custom_type", None)]);
        let data = r#"{"custom": "anything"}"#;
        let result = _validate_internal(&d, data).unwrap();
        let errors = parse_errors(&result);
        assert!(errors.is_empty());
    }

    // T006 Test 18: empty custom data
    #[test]
    fn test_empty_custom_data() {
        let d = defs(&[("name", "text", None)]);
        let data = r#"{}"#;
        let result = _validate_internal(&d, data).unwrap();
        let errors = parse_errors(&result);
        assert!(errors.is_empty());
    }

    // T006 Test 19: empty definitions
    #[test]
    fn test_empty_definitions() {
        let d = "[]";
        let data = r#"{"name": "hello"}"#;
        let result = _validate_internal(&d, data).unwrap();
        let errors = parse_errors(&result);
        assert!(errors.is_empty());
    }
}
