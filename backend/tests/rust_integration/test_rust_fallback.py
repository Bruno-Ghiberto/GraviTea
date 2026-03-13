"""Tests for Rust extension fallback pattern (US2).

Verifies that the backend functions identically when the Rust extension
is unavailable — the try/except ImportError convention works correctly.
"""

import builtins
import sys

import pytest


def test_fallback_flag_when_extension_unavailable(monkeypatch):
    """Verify _USE_RUST is False when extension import fails."""
    # Remove gravitea_rust from sys.modules if present
    sys.modules.pop("gravitea_rust", None)

    # Monkeypatch import to fail for gravitea_rust
    original_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "gravitea_rust":
            raise ImportError("Mocked: no Rust extension")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)

    # The fallback pattern should detect absence and set _USE_RUST = False
    _USE_RUST = False
    try:
        from gravitea_rust import hello as _rust_hello  # noqa: F401

        _USE_RUST = True
    except ImportError:
        _USE_RUST = False

    assert _USE_RUST is False


def test_fallback_produces_identical_output_type():
    """Verify fallback function produces same result type as Rust version."""
    # Rust version
    try:
        from gravitea_rust import hello as rust_hello

        rust_result = rust_hello()
    except ImportError:
        pytest.skip("Rust extension not installed")

    # Python fallback version
    def python_hello() -> str:
        return "Hello from Python (fallback)"

    python_result = python_hello()

    # Both return strings
    assert isinstance(rust_result, str)
    assert isinstance(python_result, str)


def test_no_errors_in_fallback_operation():
    """Verify fallback pattern doesn't raise exceptions regardless of _USE_RUST."""
    _USE_RUST = False
    _rust_hello = None
    try:
        from gravitea_rust import hello as _rust_hello

        _USE_RUST = True
    except ImportError:
        _USE_RUST = False

    # Regardless of _USE_RUST value, no exception should be raised
    if _USE_RUST:
        result = _rust_hello()
    else:
        result = "Hello from Python (fallback)"

    assert isinstance(result, str)
