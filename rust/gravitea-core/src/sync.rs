// SPEC-023: Rust Sync Conflict Engine — merge_most_complete + batch
//
// Replaces _resolve_most_complete_wins() in conflict_resolver.py (lines 426-564)
// with Rust/PyO3 JSON merge using serde_json.

use std::collections::HashSet;

use pyo3::prelude::*;
use serde_json::{Map, Value};

use crate::errors::GraviteaError;

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

/// Normalize whitespace-only strings to null. All other types pass through.
/// Empty lists [], dicts {}, numbers 0, booleans false are NOT normalized (R-002).
fn normalize_value(value: &Value) -> Value {
    match value {
        Value::String(s) if s.trim().is_empty() => Value::Null,
        other => other.clone(),
    }
}

/// Result of comparing two non-null values for "completeness".
enum CompletionResult {
    ClientWins,
    TiedServerWins,
}

/// Compare two non-null values for completeness (R-001).
/// - String: stripped len, client wins only if strictly greater
/// - Array: len, client wins only if strictly greater
/// - Object: key count, client wins only if strictly greater
/// - All other (bool, number, mixed): server wins (TiedServerWins)
fn compare_completeness(server: &Value, client: &Value) -> CompletionResult {
    match (server, client) {
        (Value::String(s), Value::String(c)) => {
            let s_len = s.trim().len();
            let c_len = c.trim().len();
            if c_len > s_len {
                CompletionResult::ClientWins
            } else {
                CompletionResult::TiedServerWins
            }
        }
        (Value::Array(s), Value::Array(c)) => {
            if c.len() > s.len() {
                CompletionResult::ClientWins
            } else {
                CompletionResult::TiedServerWins
            }
        }
        (Value::Object(s), Value::Object(c)) => {
            if c.len() > s.len() {
                CompletionResult::ClientWins
            } else {
                CompletionResult::TiedServerWins
            }
        }
        _ => CompletionResult::TiedServerWins,
    }
}

// ---------------------------------------------------------------------------
// Internal merge logic (returns Result, testable without Python runtime)
// ---------------------------------------------------------------------------

fn merge_most_complete_internal(
    server_json: &str,
    client_json: &str,
    metadata_fields_json: &str,
) -> Result<(String, String), GraviteaError> {
    // Parse inputs
    let server: Map<String, Value> = serde_json::from_str(server_json).map_err(|e| {
        GraviteaError::SyncError(format!("Invalid server JSON: {e}"))
    })?;

    let client: Map<String, Value> = serde_json::from_str(client_json).map_err(|e| {
        GraviteaError::SyncError(format!("Invalid client JSON: {e}"))
    })?;

    let metadata_fields: Vec<String> =
        serde_json::from_str(metadata_fields_json).map_err(|e| {
            GraviteaError::SyncError(format!("Invalid metadata fields JSON: {e}"))
        })?;
    let metadata_set: HashSet<String> = metadata_fields.into_iter().collect();

    // FR-012: Both empty → error
    if server.is_empty() && client.is_empty() {
        return Err(GraviteaError::SyncError(
            "Both payloads empty".to_string(),
        ));
    }

    // Key union
    let mut all_keys: Vec<&String> = Vec::new();
    for k in server.keys() {
        all_keys.push(k);
    }
    for k in client.keys() {
        if !server.contains_key(k) {
            all_keys.push(k);
        }
    }

    let mut merged = Map::new();
    let mut log_client_won: Vec<String> = Vec::new();
    let mut log_server_won: Vec<String> = Vec::new();
    let mut log_tied_server_won: Vec<String> = Vec::new();
    let mut log_both_null: Vec<String> = Vec::new();
    let mut log_empty_string_normalized: Vec<String> = Vec::new();

    for key in &all_keys {
        let server_raw = server.get(*key).unwrap_or(&Value::Null);
        let client_raw = client.get(*key).unwrap_or(&Value::Null);

        // Metadata fields: always server, skip comparison, no log
        if metadata_set.contains(*key) {
            merged.insert((*key).clone(), server_raw.clone());
            continue;
        }

        // Normalize values
        let server_val = normalize_value(server_raw);
        let client_val = normalize_value(client_raw);

        // Track empty string normalizations
        if server_raw != &server_val {
            log_empty_string_normalized.push(format!("{}_server", key));
        }
        if client_raw != &client_val {
            log_empty_string_normalized.push(format!("{}_client", key));
        }

        // Null comparison table
        match (&server_val, &client_val) {
            (Value::Null, Value::Null) => {
                merged.insert((*key).clone(), Value::Null);
                log_both_null.push((*key).clone());
            }
            (Value::Null, _) => {
                // Server null, client has value → client wins
                merged.insert((*key).clone(), client_val);
                log_client_won.push((*key).clone());
            }
            (_, Value::Null) => {
                // Client null, server has value → server wins
                merged.insert((*key).clone(), server_val);
                log_server_won.push((*key).clone());
            }
            _ => {
                // Both non-null → compare completeness
                match compare_completeness(&server_val, &client_val) {
                    CompletionResult::ClientWins => {
                        merged.insert((*key).clone(), client_val);
                        log_client_won.push((*key).clone());
                    }
                    CompletionResult::TiedServerWins => {
                        merged.insert((*key).clone(), server_val);
                        log_tied_server_won.push((*key).clone());
                    }
                }
            }
        }
    }

    // Build merge_log
    let merge_log = serde_json::json!({
        "client_won": log_client_won,
        "server_won": log_server_won,
        "tied_server_won": log_tied_server_won,
        "both_null": log_both_null,
        "empty_string_normalized": log_empty_string_normalized,
    });

    let merged_json =
        serde_json::to_string(&Value::Object(merged)).map_err(|e| {
            GraviteaError::SyncError(format!("Failed to serialize merged: {e}"))
        })?;

    let merge_log_json = serde_json::to_string(&merge_log).map_err(|e| {
        GraviteaError::SyncError(format!("Failed to serialize merge_log: {e}"))
    })?;

    Ok((merged_json, merge_log_json))
}

// ---------------------------------------------------------------------------
// PyO3 exported functions
// ---------------------------------------------------------------------------

/// Single merge: server + client → (merged_json, merge_log_json).
/// GIL NOT released (single operation, fast).
#[pyfunction]
pub fn merge_most_complete(
    server_json: &str,
    client_json: &str,
    metadata_fields_json: &str,
) -> PyResult<(String, String)> {
    merge_most_complete_internal(server_json, client_json, metadata_fields_json)
        .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))
}

/// Batch merge: JSON array of {server, client} pairs → JSON array of {merged, merge_log}.
/// GIL RELEASED for the entire batch processing loop.
#[pyfunction]
pub fn merge_most_complete_batch(
    py: Python,
    pairs_json: &str,
    metadata_fields_json: &str,
) -> PyResult<String> {
    // Clone inputs for the closure (py.detach requires owned data)
    let pairs_owned = pairs_json.to_string();
    let metadata_owned = metadata_fields_json.to_string();

    py.detach(move || {
        let pairs: Vec<Value> = serde_json::from_str(&pairs_owned).map_err(|e| {
            GraviteaError::SyncError(format!("Invalid pairs JSON: {e}"))
        })?;

        let mut results: Vec<Value> = Vec::with_capacity(pairs.len());

        for (i, pair) in pairs.iter().enumerate() {
            let server = pair
                .get("server")
                .ok_or_else(|| {
                    GraviteaError::SyncError(format!(
                        "Pair {i} missing 'server' key"
                    ))
                })?;
            let client = pair
                .get("client")
                .ok_or_else(|| {
                    GraviteaError::SyncError(format!(
                        "Pair {i} missing 'client' key"
                    ))
                })?;

            let server_str = serde_json::to_string(server).map_err(|e| {
                GraviteaError::SyncError(format!(
                    "Pair {i} server serialize: {e}"
                ))
            })?;
            let client_str = serde_json::to_string(client).map_err(|e| {
                GraviteaError::SyncError(format!(
                    "Pair {i} client serialize: {e}"
                ))
            })?;

            let (merged_json, merge_log_json) =
                merge_most_complete_internal(&server_str, &client_str, &metadata_owned)?;

            let merged_val: Value =
                serde_json::from_str(&merged_json).map_err(|e| {
                    GraviteaError::SyncError(format!(
                        "Pair {i} merged parse: {e}"
                    ))
                })?;
            let log_val: Value =
                serde_json::from_str(&merge_log_json).map_err(|e| {
                    GraviteaError::SyncError(format!(
                        "Pair {i} log parse: {e}"
                    ))
                })?;

            results.push(serde_json::json!({
                "merged": merged_val,
                "merge_log": log_val,
            }));
        }

        serde_json::to_string(&results).map_err(|e| {
            GraviteaError::SyncError(format!("Failed to serialize batch results: {e}"))
        })
    })
    .map_err(|e: GraviteaError| {
        pyo3::exceptions::PyRuntimeError::new_err(e.to_string())
    })
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    const META: &str = r#"["id", "created_at", "updated_at", "sync_version"]"#;

    /// Helper: parse merge_log JSON into a Value for assertions.
    fn parse_log(log_json: &str) -> Value {
        serde_json::from_str(log_json).unwrap()
    }

    /// Helper: parse merged JSON into a Map for assertions.
    fn parse_merged(merged_json: &str) -> Map<String, Value> {
        serde_json::from_str(merged_json).unwrap()
    }

    /// Helper: sort a JSON array value for stable comparison.
    fn sorted_strings(val: &Value) -> Vec<String> {
        let mut v: Vec<String> = val
            .as_array()
            .unwrap()
            .iter()
            .map(|x| x.as_str().unwrap().to_string())
            .collect();
        v.sort();
        v
    }

    // T008 test 1: Basic merge with overlapping + unique fields
    #[test]
    fn test_basic_merge_overlapping() {
        let server = json!({"name": "Alice", "email": "a@b.com", "server_only": "s"}).to_string();
        let client = json!({"name": "Alice Johnson", "phone": "12345", "server_only": "c"}).to_string();
        let (merged_json, log_json) =
            merge_most_complete_internal(&server, &client, META).unwrap();

        let merged = parse_merged(&merged_json);
        // "Alice Johnson" (13 stripped) > "Alice" (5 stripped) → client wins
        assert_eq!(merged["name"], json!("Alice Johnson"));
        // email: only server has → server wins
        assert_eq!(merged["email"], json!("a@b.com"));
        // phone: only client has → client wins
        assert_eq!(merged["phone"], json!("12345"));
        // server_only: both have, "s" (1) vs "c" (1) → tied, server wins
        assert_eq!(merged["server_only"], json!("s"));

        let log = parse_log(&log_json);
        assert!(sorted_strings(&log["client_won"]).contains(&"name".to_string()));
        assert!(sorted_strings(&log["client_won"]).contains(&"phone".to_string()));
        assert!(sorted_strings(&log["server_won"]).contains(&"email".to_string()));
        assert!(sorted_strings(&log["tied_server_won"]).contains(&"server_only".to_string()));
    }

    // T008 test 2: Deep nesting — dict key count comparison
    #[test]
    fn test_deep_nesting() {
        let server = json!({"address": {"street": "Main"}}).to_string();
        let client = json!({"address": {"street": "Main", "city": "NYC", "zip": "10001"}}).to_string();
        let (merged_json, log_json) =
            merge_most_complete_internal(&server, &client, META).unwrap();

        let merged = parse_merged(&merged_json);
        // client dict has 3 keys vs server 1 → client wins
        assert_eq!(
            merged["address"],
            json!({"street": "Main", "city": "NYC", "zip": "10001"})
        );

        let log = parse_log(&log_json);
        assert!(sorted_strings(&log["client_won"]).contains(&"address".to_string()));
    }

    // T008 test 3: Null handling — both null, one null/one value
    #[test]
    fn test_null_handling() {
        let server = json!({"a": null, "b": null, "c": "value"}).to_string();
        let client = json!({"a": null, "b": "data", "c": null}).to_string();
        let (merged_json, log_json) =
            merge_most_complete_internal(&server, &client, META).unwrap();

        let merged = parse_merged(&merged_json);
        assert_eq!(merged["a"], json!(null)); // both null
        assert_eq!(merged["b"], json!("data")); // client has, server null → client
        assert_eq!(merged["c"], json!("value")); // server has, client null → server

        let log = parse_log(&log_json);
        assert!(sorted_strings(&log["both_null"]).contains(&"a".to_string()));
        assert!(sorted_strings(&log["client_won"]).contains(&"b".to_string()));
        assert!(sorted_strings(&log["server_won"]).contains(&"c".to_string()));
    }

    // T008 test 4: String comparison — longer stripped string wins
    #[test]
    fn test_string_comparison() {
        let server = json!({"name": "Bob"}).to_string();
        let client = json!({"name": "Bobby"}).to_string();
        let (merged_json, log_json) =
            merge_most_complete_internal(&server, &client, META).unwrap();

        let merged = parse_merged(&merged_json);
        assert_eq!(merged["name"], json!("Bobby")); // 5 > 3 → client wins

        let log = parse_log(&log_json);
        assert!(sorted_strings(&log["client_won"]).contains(&"name".to_string()));
    }

    // T008 test 5: List comparison — longer list wins
    #[test]
    fn test_list_comparison() {
        let server = json!({"tags": ["a"]}).to_string();
        let client = json!({"tags": ["a", "b", "c"]}).to_string();
        let (merged_json, log_json) =
            merge_most_complete_internal(&server, &client, META).unwrap();

        let merged = parse_merged(&merged_json);
        assert_eq!(merged["tags"], json!(["a", "b", "c"])); // 3 > 1 → client wins

        let log = parse_log(&log_json);
        assert!(sorted_strings(&log["client_won"]).contains(&"tags".to_string()));
    }

    // T008 test 6: Dict comparison — more keys wins
    #[test]
    fn test_dict_comparison() {
        let server = json!({"meta": {"a": 1, "b": 2, "c": 3}}).to_string();
        let client = json!({"meta": {"x": 1}}).to_string();
        let (merged_json, _) =
            merge_most_complete_internal(&server, &client, META).unwrap();

        let merged = parse_merged(&merged_json);
        // server has 3 keys, client has 1 → server wins (tied)
        assert_eq!(merged["meta"], json!({"a": 1, "b": 2, "c": 3}));
    }

    // T008 test 7: Both empty payloads → SyncError (FR-012)
    #[test]
    fn test_both_empty_error() {
        let result =
            merge_most_complete_internal("{}", "{}", META);
        assert!(result.is_err());
        let err = result.unwrap_err();
        assert!(matches!(err, GraviteaError::SyncError(_)));
        assert!(err.to_string().contains("Both payloads empty"));
    }

    // T008 test 8: Metadata passthrough — always server value, not in log
    #[test]
    fn test_metadata_passthrough() {
        let server = json!({
            "id": "server-id",
            "created_at": "2026-01-01",
            "updated_at": "2026-01-02",
            "sync_version": 5,
            "name": "Alice"
        })
        .to_string();
        let client = json!({
            "id": "client-id",
            "created_at": "2025-12-01",
            "updated_at": "2025-12-02",
            "sync_version": 3,
            "name": "Alice Johnson"
        })
        .to_string();
        let (merged_json, log_json) =
            merge_most_complete_internal(&server, &client, META).unwrap();

        let merged = parse_merged(&merged_json);
        assert_eq!(merged["id"], json!("server-id"));
        assert_eq!(merged["created_at"], json!("2026-01-01"));
        assert_eq!(merged["updated_at"], json!("2026-01-02"));
        assert_eq!(merged["sync_version"], json!(5));
        assert_eq!(merged["name"], json!("Alice Johnson")); // client wins (longer)

        // Metadata fields must NOT appear in any log category
        let log = parse_log(&log_json);
        let all_logged: Vec<String> = ["client_won", "server_won", "tied_server_won", "both_null"]
            .iter()
            .flat_map(|cat| sorted_strings(&log[*cat]))
            .collect();
        assert!(!all_logged.contains(&"id".to_string()));
        assert!(!all_logged.contains(&"created_at".to_string()));
        assert!(!all_logged.contains(&"updated_at".to_string()));
        assert!(!all_logged.contains(&"sync_version".to_string()));
    }

    // T008 test 9: Mixed types — str vs number → server wins (tied_server_won)
    #[test]
    fn test_mixed_types() {
        let server = json!({"field": 42}).to_string();
        let client = json!({"field": "forty-two"}).to_string();
        let (merged_json, log_json) =
            merge_most_complete_internal(&server, &client, META).unwrap();

        let merged = parse_merged(&merged_json);
        assert_eq!(merged["field"], json!(42)); // server wins

        let log = parse_log(&log_json);
        assert!(sorted_strings(&log["tied_server_won"]).contains(&"field".to_string()));
    }

    // T008 test 10: Invalid JSON → SyncError
    #[test]
    fn test_invalid_json() {
        let result =
            merge_most_complete_internal("{invalid", "{}", META);
        assert!(result.is_err());
        assert!(result.unwrap_err().to_string().contains("Invalid server JSON"));

        let result2 =
            merge_most_complete_internal("{}", "{invalid", META);
        assert!(result2.is_err());
        assert!(result2.unwrap_err().to_string().contains("Invalid client JSON"));
    }

    // T008 test 11: Whitespace normalization
    #[test]
    fn test_whitespace_normalization() {
        let server = json!({"phone": "   ", "name": "Alice"}).to_string();
        let client = json!({"phone": "12345", "name": "\t"}).to_string();
        let (merged_json, log_json) =
            merge_most_complete_internal(&server, &client, META).unwrap();

        let merged = parse_merged(&merged_json);
        // server phone "   " normalized to null, client has "12345" → client wins
        assert_eq!(merged["phone"], json!("12345"));
        // client name "\t" normalized to null, server has "Alice" → server wins
        assert_eq!(merged["name"], json!("Alice"));

        let log = parse_log(&log_json);
        let normalized = sorted_strings(&log["empty_string_normalized"]);
        assert!(normalized.contains(&"phone_server".to_string()));
        assert!(normalized.contains(&"name_client".to_string()));
    }

    // T008 test 12: Bool server wins — no bool comparison
    #[test]
    fn test_bool_server_wins() {
        let server = json!({"active": false}).to_string();
        let client = json!({"active": true}).to_string();
        let (merged_json, log_json) =
            merge_most_complete_internal(&server, &client, META).unwrap();

        let merged = parse_merged(&merged_json);
        assert_eq!(merged["active"], json!(false)); // server wins, no bool comparison

        let log = parse_log(&log_json);
        assert!(sorted_strings(&log["tied_server_won"]).contains(&"active".to_string()));
    }

    // T008 test 13: Number server wins — no numeric comparison
    #[test]
    fn test_number_server_wins() {
        let server = json!({"count": 5}).to_string();
        let client = json!({"count": 100}).to_string();
        let (merged_json, log_json) =
            merge_most_complete_internal(&server, &client, META).unwrap();

        let merged = parse_merged(&merged_json);
        assert_eq!(merged["count"], json!(5)); // server wins, no numeric comparison

        let log = parse_log(&log_json);
        assert!(sorted_strings(&log["tied_server_won"]).contains(&"count".to_string()));
    }

    // T015: Batch test — 3 pairs, verify JSON array output
    #[test]
    fn test_batch_merge() {
        let pairs = json!([
            {
                "server": {"name": "Alice", "phone": null},
                "client": {"name": "Alice Johnson", "phone": "12345"}
            },
            {
                "server": {"email": "a@b.com", "tags": ["a", "b"]},
                "client": {"email": "x@y.com", "tags": ["x"]}
            },
            {
                "server": {"city": null, "active": true},
                "client": {"city": "NYC", "active": false}
            }
        ]);

        // Simulate batch internally (no Python runtime needed)
        let pairs_arr = pairs.as_array().unwrap();
        let mut results: Vec<Value> = Vec::new();

        for pair in pairs_arr {
            let server_str = serde_json::to_string(pair.get("server").unwrap()).unwrap();
            let client_str = serde_json::to_string(pair.get("client").unwrap()).unwrap();
            let (merged_json, log_json) =
                merge_most_complete_internal(&server_str, &client_str, META).unwrap();
            let merged_val: Value = serde_json::from_str(&merged_json).unwrap();
            let log_val: Value = serde_json::from_str(&log_json).unwrap();
            results.push(json!({"merged": merged_val, "merge_log": log_val}));
        }

        assert_eq!(results.len(), 3);

        // Pair 1: name → client_won (longer), phone → client_won (server null)
        let log0 = &results[0]["merge_log"];
        assert!(sorted_strings(&log0["client_won"]).contains(&"name".to_string()));
        assert!(sorted_strings(&log0["client_won"]).contains(&"phone".to_string()));

        // Pair 2: email → tied_server_won (same len), tags → server_won (server 2 > client 1)
        let log1 = &results[1]["merge_log"];
        assert!(sorted_strings(&log1["tied_server_won"]).contains(&"tags".to_string()));

        // Pair 3: city → client_won (server null), active → tied_server_won (bool)
        let log2 = &results[2]["merge_log"];
        assert!(sorted_strings(&log2["client_won"]).contains(&"city".to_string()));
        assert!(sorted_strings(&log2["tied_server_won"]).contains(&"active".to_string()));

        // Each entry has "merged" and "merge_log" keys
        for r in &results {
            assert!(r.get("merged").is_some());
            assert!(r.get("merge_log").is_some());
        }
    }
}
