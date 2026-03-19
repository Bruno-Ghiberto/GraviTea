use pyo3::prelude::*;

mod arca;
mod compute;
mod crypto;
mod decimal_utils;
mod errors;
mod export;
mod observability;
mod security;
mod sync;
mod merma;
mod validation;
pub use errors::*;

/// Returns a greeting from Rust, proving the PyO3 bridge works.
#[pyfunction]
fn hello() -> String {
    "Hello from Rust".to_string()
}

#[pymodule]
mod gravitea_rust {
    #[pymodule_export]
    use super::hello;
    #[pymodule_export]
    use super::crypto::encrypt_value;
    #[pymodule_export]
    use super::crypto::decrypt_value;
    #[pymodule_export]
    use super::crypto::compute_blind_index;
    #[pymodule_export]
    use super::compute::validate_importes;
    #[pymodule_export]
    use super::compute::calculate_iva_breakdown;
    #[pymodule_export]
    use super::compute::validate_iva_breakdown;
    #[pymodule_export]
    use super::compute::aggregate_stock_levels;
    #[pymodule_export]
    use super::compute::validate_cuit;
    #[pymodule_export]
    use super::export::generate_csv;
    #[pymodule_export]
    use super::export::generate_xlsx;
    #[pymodule_export]
    use super::observability::normalize_path;
    #[pymodule_export]
    use super::observability::sanitize_endpoint_label;
    #[pymodule_export]
    use super::security::validate_url_safety;
    #[pymodule_export]
    use super::security::check_resolved_ip;
    #[pymodule_export]
    use super::sync::merge_most_complete;
    #[pymodule_export]
    use super::sync::merge_most_complete_batch;
    #[pymodule_export]
    use super::arca::build_caea_batch_request;
    #[pymodule_export]
    use super::validation::validate_custom_fields;
    #[pymodule_export]
    use super::merma::calculate_merma;
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_hello() {
        assert_eq!(hello(), "Hello from Rust");
    }
}
