use pyo3::exceptions::{PyIOError, PyRuntimeError, PyValueError};
use pyo3::PyErr;
use thiserror::Error;

#[derive(Error, Debug)]
pub enum GraviteaError {
    #[error("Invalid input: {0}")]
    InvalidInput(String),

    #[error("Crypto error: {0}")]
    CryptoError(String),

    #[error("IO error: {0}")]
    IoError(#[from] std::io::Error),

    #[error("Compute error: {msg}")]
    ComputeError { msg: String },

    #[error("Export error: {0}")]
    ExportError(String),

    #[error("Security error: {0}")]
    SecurityError(String),

    #[error("Sync error: {0}")]
    SyncError(String),

    #[error("ARCA build error: {0}")]
    ARCABuildError(String),

    #[error("Validation error: {0}")]
    ValidationFieldError(String),
}

impl From<GraviteaError> for PyErr {
    fn from(err: GraviteaError) -> PyErr {
        match err {
            GraviteaError::InvalidInput(msg) => PyValueError::new_err(msg),
            GraviteaError::CryptoError(msg) => PyRuntimeError::new_err(msg),
            GraviteaError::IoError(err) => PyIOError::new_err(err.to_string()),
            GraviteaError::ComputeError { msg } => PyRuntimeError::new_err(msg),
            GraviteaError::ExportError(msg) => PyRuntimeError::new_err(msg),
            GraviteaError::SecurityError(msg) => PyRuntimeError::new_err(msg),
            GraviteaError::SyncError(msg) => PyRuntimeError::new_err(msg),
            GraviteaError::ARCABuildError(msg) => PyRuntimeError::new_err(msg),
            GraviteaError::ValidationFieldError(msg) => PyValueError::new_err(msg),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_error_display() {
        let err = GraviteaError::InvalidInput("bad data".to_string());
        assert_eq!(format!("{err}"), "Invalid input: bad data");
    }

    #[test]
    fn test_io_error_from() {
        let io_err = std::io::Error::new(std::io::ErrorKind::NotFound, "file not found");
        let err: GraviteaError = io_err.into();
        assert!(matches!(err, GraviteaError::IoError(_)));
    }

    #[test]
    fn test_sync_error_display() {
        let err = GraviteaError::SyncError("merge failed".to_string());
        assert_eq!(format!("{err}"), "Sync error: merge failed");
    }
}
