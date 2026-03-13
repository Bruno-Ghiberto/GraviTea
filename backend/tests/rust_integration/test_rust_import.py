"""Tests for Rust extension import and basic functionality (US1)."""

import pytest


def test_import_succeeds():
    """Verify gravitea_rust module can be imported."""
    import gravitea_rust  # noqa: F401

    assert hasattr(gravitea_rust, "hello")


def test_hello_returns_expected_string():
    """Verify hello() returns exactly 'Hello from Rust'."""
    from gravitea_rust import hello

    result = hello()
    assert result == "Hello from Rust"
    assert isinstance(result, str)


def test_hello_consistent_across_calls():
    """Verify hello() returns the same value across 1000 calls."""
    from gravitea_rust import hello

    expected = "Hello from Rust"
    for _ in range(1000):
        assert hello() == expected
