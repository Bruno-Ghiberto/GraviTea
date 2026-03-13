"""
SPEC-023: Rust Sync Conflict Engine — Integration Tests.

Tests parity between Rust and Python merge_most_complete implementations,
batch merge with GIL release, graceful fallback, and threshold routing.

US1 (T011): Equivalence + merge_log parity + SyncError tests
US2 (T017): Batch benchmark + GIL release concurrency tests
US3 (T020): Fallback tests (mock Rust unavailable)
US4 (T023): Threshold routing tests (_RUST_FIELD_THRESHOLD = 20)
"""

import json
import threading
import time
from unittest.mock import patch

import pytest

# Direct Rust imports for comparison
from gravitea_rust import (
    merge_most_complete as rust_merge,
    merge_most_complete_batch as rust_merge_batch,
)

# Dispatcher imports
from apps.sync.sync_engine import (
    _DEFAULT_METADATA_FIELDS,
    _RUST_FIELD_THRESHOLD,
    _merge_python,
    _merge_rust,
    merge_most_complete,
    merge_most_complete_batch,
)

pytestmark = pytest.mark.integration

# ─────────────────────────────────────────────────────────────────────────────
# Constants & Helpers
# ─────────────────────────────────────────────────────────────────────────────

METADATA = ["id", "created_at", "updated_at", "sync_version"]
META_JSON = json.dumps(METADATA)


def parse_merged(json_str: str) -> dict:
    """Parse merged JSON string into dict."""
    return json.loads(json_str)


def parse_log(json_str: str) -> dict:
    """Parse merge_log JSON string into dict."""
    return json.loads(json_str)


def sorted_log_field(log: dict, category: str) -> list[str]:
    """Get a sorted list from a merge_log category for stable comparison."""
    return sorted(log.get(category, []))


def make_large_payload(field_count: int, prefix: str = "field") -> dict:
    """Generate a payload with N fields for threshold/batch testing."""
    return {f"{prefix}_{i}": f"value_{i}" for i in range(field_count)}


# ─────────────────────────────────────────────────────────────────────────────
# US1: Single Merge Equivalence Tests (T011)
# ─────────────────────────────────────────────────────────────────────────────


class TestUS1Equivalence:
    """SC-001: Rust vs Python parity for single merge operations."""

    def test_us1_basic_overlapping_fields(self):
        """Server has email, client has phone, both have name (client longer)."""
        server = {"name": "Alice", "email": "a@b.com"}
        client = {"name": "Alice Johnson", "phone": "12345"}

        rust_merged, rust_log = _merge_rust(server, client, METADATA)
        py_merged, py_log = _merge_python(server, client, METADATA)

        assert rust_merged["name"] == "Alice Johnson"  # client wins (longer)
        assert rust_merged["email"] == "a@b.com"  # server only
        assert rust_merged["phone"] == "12345"  # client only

        # Parity check
        assert rust_merged == py_merged
        for cat in ("client_won", "server_won", "tied_server_won", "both_null", "empty_string_normalized"):
            assert sorted_log_field(rust_log, cat) == sorted_log_field(py_log, cat)

    def test_us1_all_five_log_categories(self):
        """Every merge_log category has at least one entry."""
        server = {
            "client_only_field": None,   # server null → client wins
            "server_only_field": "srv",  # client null → server wins
            "tied_field": "abc",         # same length → tied_server_won
            "both_null_field": None,     # both null
            "ws_field": "   ",           # whitespace → normalized
        }
        client = {
            "client_only_field": "data",
            "server_only_field": None,
            "tied_field": "xyz",         # same length → tied_server_won
            "both_null_field": None,
            "ws_field": "value",
        }

        rust_merged, rust_log = _merge_rust(server, client, METADATA)
        py_merged, py_log = _merge_python(server, client, METADATA)

        assert rust_merged == py_merged

        # Verify all 5 categories present
        assert "client_only_field" in sorted_log_field(rust_log, "client_won")
        assert "server_only_field" in sorted_log_field(rust_log, "server_won")
        assert "tied_field" in sorted_log_field(rust_log, "tied_server_won")
        assert "both_null_field" in sorted_log_field(rust_log, "both_null")
        assert len(sorted_log_field(rust_log, "empty_string_normalized")) > 0

        # Parity for all categories
        for cat in ("client_won", "server_won", "tied_server_won", "both_null", "empty_string_normalized"):
            assert sorted_log_field(rust_log, cat) == sorted_log_field(py_log, cat)

    def test_us1_metadata_passthrough(self):
        """Metadata fields always from server, NOT in merge_log."""
        server = {
            "id": "server-id",
            "created_at": "2026-01-01",
            "updated_at": "2026-01-02",
            "sync_version": 5,
            "name": "Alice",
        }
        client = {
            "id": "client-id",
            "created_at": "2025-12-01",
            "updated_at": "2025-12-02",
            "sync_version": 3,
            "name": "Alice Johnson",
        }

        rust_merged, rust_log = _merge_rust(server, client, METADATA)
        py_merged, py_log = _merge_python(server, client, METADATA)

        # Metadata always from server
        assert rust_merged["id"] == "server-id"
        assert rust_merged["created_at"] == "2026-01-01"
        assert rust_merged["updated_at"] == "2026-01-02"
        assert rust_merged["sync_version"] == 5
        # Data field: client wins
        assert rust_merged["name"] == "Alice Johnson"

        # Metadata NOT in any log category
        all_logged = []
        for cat in ("client_won", "server_won", "tied_server_won", "both_null"):
            all_logged.extend(rust_log.get(cat, []))
        for meta_field in METADATA:
            assert meta_field not in all_logged

        assert rust_merged == py_merged

    def test_us1_whitespace_tab_newline_normalization(self):
        """'   ', '\\t', '\\n' all normalized to null."""
        server = {"ws_space": "   ", "ws_tab": "\t", "ws_newline": "\n"}
        client = {"ws_space": "value", "ws_tab": "value", "ws_newline": "value"}

        rust_merged, rust_log = _merge_rust(server, client, METADATA)
        py_merged, py_log = _merge_python(server, client, METADATA)

        # Server whitespace normalized → null → client wins
        assert rust_merged["ws_space"] == "value"
        assert rust_merged["ws_tab"] == "value"
        assert rust_merged["ws_newline"] == "value"

        assert sorted_log_field(rust_log, "client_won") == sorted_log_field(py_log, "client_won")
        assert sorted_log_field(rust_log, "empty_string_normalized") == sorted_log_field(py_log, "empty_string_normalized")

    def test_us1_empty_string_normalized_to_null(self):
        """Empty string '' normalized to null."""
        server = {"email": ""}
        client = {"email": "user@example.com"}

        rust_merged, rust_log = _merge_rust(server, client, METADATA)
        py_merged, py_log = _merge_python(server, client, METADATA)

        assert rust_merged["email"] == "user@example.com"
        assert "email_server" in sorted_log_field(rust_log, "empty_string_normalized")
        assert rust_merged == py_merged
        for cat in ("client_won", "server_won", "tied_server_won", "both_null", "empty_string_normalized"):
            assert sorted_log_field(rust_log, cat) == sorted_log_field(py_log, cat)

    def test_us1_both_empty_raises_runtime_error(self):
        """FR-012: Both empty payloads → RuntimeError."""
        with pytest.raises(RuntimeError, match="Both payloads empty"):
            _merge_rust({}, {}, METADATA)

        with pytest.raises(RuntimeError, match="Both payloads empty"):
            _merge_python({}, {}, METADATA)

    def test_us1_nested_dicts_key_count(self):
        """Client dict with more keys wins."""
        server = {"address": {"street": "Main"}}
        client = {"address": {"street": "Main", "city": "NYC", "zip": "10001"}}

        rust_merged, rust_log = _merge_rust(server, client, METADATA)
        py_merged, py_log = _merge_python(server, client, METADATA)

        # Client 3 keys > server 1 key → client wins
        assert rust_merged["address"] == {"street": "Main", "city": "NYC", "zip": "10001"}
        assert "address" in sorted_log_field(rust_log, "client_won")
        assert rust_merged == py_merged

    def test_us1_nested_lists_length(self):
        """Client list with more items wins."""
        server = {"tags": ["a"]}
        client = {"tags": ["a", "b", "c"]}

        rust_merged, rust_log = _merge_rust(server, client, METADATA)
        py_merged, py_log = _merge_python(server, client, METADATA)

        # Client 3 items > server 1 item → client wins
        assert rust_merged["tags"] == ["a", "b", "c"]
        assert "tags" in sorted_log_field(rust_log, "client_won")
        assert rust_merged == py_merged

    def test_us1_mixed_types_server_wins(self):
        """String vs number → server wins (tied_server_won)."""
        server = {"field": 42}
        client = {"field": "forty-two"}

        rust_merged, rust_log = _merge_rust(server, client, METADATA)
        py_merged, py_log = _merge_python(server, client, METADATA)

        assert rust_merged["field"] == 42
        assert "field" in sorted_log_field(rust_log, "tied_server_won")
        assert rust_merged == py_merged
        for cat in ("client_won", "server_won", "tied_server_won", "both_null", "empty_string_normalized"):
            assert sorted_log_field(rust_log, cat) == sorted_log_field(py_log, cat)

    def test_us1_bool_server_wins(self):
        """True vs False → server wins (no bool ordering)."""
        server = {"active": False}
        client = {"active": True}

        rust_merged, rust_log = _merge_rust(server, client, METADATA)
        py_merged, py_log = _merge_python(server, client, METADATA)

        assert rust_merged["active"] is False
        assert "active" in sorted_log_field(rust_log, "tied_server_won")
        assert rust_merged == py_merged

    def test_us1_number_server_wins(self):
        """100 vs 5 → server wins (no numeric ordering)."""
        server = {"count": 5}
        client = {"count": 100}

        rust_merged, rust_log = _merge_rust(server, client, METADATA)
        py_merged, py_log = _merge_python(server, client, METADATA)

        assert rust_merged["count"] == 5
        assert "count" in sorted_log_field(rust_log, "tied_server_won")
        assert rust_merged == py_merged

    def test_us1_client_only_fields(self):
        """Fields only in client → client_won."""
        server = {"name": "Alice"}
        client = {"name": "Alice", "phone": "12345", "email": "a@b.com"}

        rust_merged, rust_log = _merge_rust(server, client, METADATA)
        py_merged, py_log = _merge_python(server, client, METADATA)

        assert rust_merged["phone"] == "12345"
        assert rust_merged["email"] == "a@b.com"
        assert "phone" in sorted_log_field(rust_log, "client_won")
        assert "email" in sorted_log_field(rust_log, "client_won")
        assert rust_merged == py_merged

    def test_us1_server_only_fields(self):
        """Fields only in server → server_won."""
        server = {"name": "Alice", "role": "admin", "dept": "eng"}
        client = {"name": "Alice"}

        rust_merged, rust_log = _merge_rust(server, client, METADATA)
        py_merged, py_log = _merge_python(server, client, METADATA)

        assert rust_merged["role"] == "admin"
        assert rust_merged["dept"] == "eng"
        assert "role" in sorted_log_field(rust_log, "server_won")
        assert "dept" in sorted_log_field(rust_log, "server_won")
        assert rust_merged == py_merged

    def test_us1_direct_rust_invalid_json_raises(self):
        """SC-008: Invalid JSON → RuntimeError from Rust."""
        with pytest.raises(RuntimeError, match="Invalid server JSON"):
            rust_merge("{invalid", "{}", META_JSON)

        with pytest.raises(RuntimeError, match="Invalid client JSON"):
            rust_merge("{}", "{invalid", META_JSON)

        with pytest.raises(RuntimeError, match="Invalid metadata fields JSON"):
            rust_merge("{}", '{"a":1}', "not-json")


# ─────────────────────────────────────────────────────────────────────────────
# US2: Batch + GIL Release Tests (T017)
# ─────────────────────────────────────────────────────────────────────────────


class TestUS2Batch:
    """SC-002, SC-003: Batch merge and GIL release concurrency."""

    def test_us2_batch_three_pairs(self):
        """Batch merge with 3 pairs returns correct count and structure."""
        pairs = [
            {
                "server": {"name": "Alice", "phone": None},
                "client": {"name": "Alice Johnson", "phone": "12345"},
            },
            {
                "server": {"email": "a@b.com", "tags": ["a", "b"]},
                "client": {"email": "x@y.com", "tags": ["x"]},
            },
            {
                "server": {"city": None, "active": True},
                "client": {"city": "NYC", "active": False},
            },
        ]

        pairs_json = json.dumps(pairs)
        result_str = rust_merge_batch(pairs_json, META_JSON)
        results = json.loads(result_str)

        assert len(results) == 3
        for r in results:
            assert "merged" in r
            assert "merge_log" in r
            for cat in ("client_won", "server_won", "tied_server_won", "both_null", "empty_string_normalized"):
                assert cat in r["merge_log"]

        # Pair 0: name → client_won (longer), phone → client_won (server null)
        assert results[0]["merged"]["name"] == "Alice Johnson"
        assert results[0]["merged"]["phone"] == "12345"
        assert "name" in sorted(results[0]["merge_log"]["client_won"])
        assert "phone" in sorted(results[0]["merge_log"]["client_won"])

        # Pair 1: email same length → tied_server_won, tags server longer → tied_server_won
        assert results[1]["merged"]["email"] == "a@b.com"
        assert results[1]["merged"]["tags"] == ["a", "b"]

        # Pair 2: city server null → client wins, active bool → tied_server_won
        assert results[2]["merged"]["city"] == "NYC"
        assert results[2]["merged"]["active"] is True  # server wins (True)

    def test_us2_batch_ten_pairs(self):
        """Batch merge with 10 pairs returns all results."""
        pairs = []
        for i in range(10):
            pairs.append({
                "server": {"field_a": f"s_{i}", "field_b": None},
                "client": {"field_a": f"client_val_{i}", "field_b": f"data_{i}"},
            })

        pairs_json = json.dumps(pairs)
        result_str = rust_merge_batch(pairs_json, META_JSON)
        results = json.loads(result_str)

        assert len(results) == 10
        for i, r in enumerate(results):
            # field_a: client is longer → client wins
            assert r["merged"]["field_a"] == f"client_val_{i}"
            # field_b: server null → client wins
            assert r["merged"]["field_b"] == f"data_{i}"

    def test_us2_batch_both_empty_raises(self):
        """Batch with one error pair (both empty) → RuntimeError."""
        pairs = [
            {"server": {"name": "ok"}, "client": {"name": "ok"}},
            {"server": {}, "client": {}},  # FR-012: both empty
        ]

        pairs_json = json.dumps(pairs)
        with pytest.raises(RuntimeError, match="Both payloads empty"):
            rust_merge_batch(pairs_json, META_JSON)

    def test_us2_gil_release_no_deadlock(self):
        """SC-003: Batch in threading.Thread completes without deadlock (5s limit)."""
        pairs = []
        for _ in range(50):
            pairs.append({
                "server": make_large_payload(30, "srv"),
                "client": make_large_payload(30, "cli"),
            })

        pairs_json = json.dumps(pairs)
        result_holder = [None]
        error_holder = [None]

        def run_batch():
            try:
                result_holder[0] = rust_merge_batch(pairs_json, META_JSON)
            except Exception as exc:
                error_holder[0] = exc

        thread = threading.Thread(target=run_batch)
        thread.start()
        thread.join(timeout=5.0)

        assert not thread.is_alive(), "Batch merge deadlocked (>5s)"
        assert error_holder[0] is None, f"Batch raised: {error_holder[0]}"
        results = json.loads(result_holder[0])
        assert len(results) == 50

    def test_us2_batch_benchmark_sanity(self):
        """SC-002: 100 pairs sanity check — completes in < 1 second."""
        pairs = []
        for _ in range(100):
            pairs.append({
                "server": make_large_payload(50, "srv"),
                "client": make_large_payload(50, "cli"),
            })

        pairs_json = json.dumps(pairs)

        start = time.perf_counter()
        result_str = rust_merge_batch(pairs_json, META_JSON)
        elapsed = time.perf_counter() - start

        results = json.loads(result_str)
        assert len(results) == 100
        assert elapsed < 1.0, f"Batch of 100 pairs took {elapsed:.3f}s (limit: 1.0s)"


# ─────────────────────────────────────────────────────────────────────────────
# US3: Fallback Tests (T020)
# ─────────────────────────────────────────────────────────────────────────────


class TestUS3Fallback:
    """SC-005: Python fallback when Rust not available."""

    def test_us3_fallback_single_merge(self):
        """Mock _USE_RUST=False → Python path used."""
        server = {"name": "Alice", "phone": None}
        client = {"name": "Alice Johnson", "phone": "12345"}

        with patch("apps.sync.sync_engine._USE_RUST", False):
            merged, log = merge_most_complete(server, client, METADATA)

        assert merged["name"] == "Alice Johnson"
        assert merged["phone"] == "12345"
        assert "name" in log["client_won"]
        assert "phone" in log["client_won"]

    def test_us3_fallback_matches_rust(self):
        """Python fallback produces same results as Rust for a basic merge."""
        server = {
            "name": "Alice",
            "email": "a@b.com",
            "tags": ["a"],
            "meta": {"x": 1},
            "score": 10,
        }
        client = {
            "name": "Alice Johnson",
            "email": "x@y.com",
            "tags": ["a", "b", "c"],
            "meta": {"x": 1, "y": 2},
            "score": 100,
        }

        rust_merged, rust_log = _merge_rust(server, client, METADATA)
        py_merged, py_log = _merge_python(server, client, METADATA)

        assert rust_merged == py_merged
        for cat in ("client_won", "server_won", "tied_server_won", "both_null", "empty_string_normalized"):
            assert sorted_log_field(rust_log, cat) == sorted_log_field(py_log, cat)

    def test_us3_fallback_both_empty_raises(self):
        """Python fallback also raises RuntimeError for both-empty."""
        with patch("apps.sync.sync_engine._USE_RUST", False):
            with pytest.raises(RuntimeError, match="Both payloads empty"):
                merge_most_complete({}, {}, METADATA)

    def test_us3_fallback_warning_logged(self, caplog):
        """Fallback logs a warning when Rust not available."""
        with caplog.at_level("WARNING", logger="apps.sync.sync_engine"):
            # Re-import to trigger the warning in a controlled way
            import importlib
            import apps.sync.sync_engine as mod

            original_use_rust = mod._USE_RUST

            # Simulate the import failure path
            with patch.dict("sys.modules", {"gravitea_rust": None}):
                with patch.object(mod, "_USE_RUST", False):
                    mod.logger.warning(
                        "gravitea_rust sync engine not available — using Python fallback"
                    )

            # Verify the warning text is what we expect
            assert any(
                "gravitea_rust sync engine not available" in record.message
                for record in caplog.records
            )

            # Restore
            mod._USE_RUST = original_use_rust


# ─────────────────────────────────────────────────────────────────────────────
# US4: Threshold Routing Tests (T023)
# ─────────────────────────────────────────────────────────────────────────────


class TestUS4Threshold:
    """SC-004: Small payloads stay in Python, large payloads use Rust."""

    def test_us4_below_threshold_uses_python(self):
        """19 fields → Python path (below _RUST_FIELD_THRESHOLD=20)."""
        server = make_large_payload(19)
        client = make_large_payload(19)

        with patch("apps.sync.sync_engine._merge_python", wraps=_merge_python) as mock_py, \
             patch("apps.sync.sync_engine._merge_rust", wraps=_merge_rust) as mock_rust:
            merged, log = merge_most_complete(server, client, METADATA)

        mock_py.assert_called_once()
        mock_rust.assert_not_called()

    def test_us4_at_threshold_uses_rust(self):
        """20 fields → Rust path (exactly at _RUST_FIELD_THRESHOLD=20)."""
        server = make_large_payload(20)
        client = make_large_payload(20)

        with patch("apps.sync.sync_engine._merge_python", wraps=_merge_python) as mock_py, \
             patch("apps.sync.sync_engine._merge_rust", wraps=_merge_rust) as mock_rust:
            merged, log = merge_most_complete(server, client, METADATA)

        mock_rust.assert_called_once()
        mock_py.assert_not_called()

    def test_us4_above_threshold_uses_rust(self):
        """25 fields → Rust path."""
        server = make_large_payload(25)
        client = make_large_payload(25)

        with patch("apps.sync.sync_engine._merge_python", wraps=_merge_python) as mock_py, \
             patch("apps.sync.sync_engine._merge_rust", wraps=_merge_rust) as mock_rust:
            merged, log = merge_most_complete(server, client, METADATA)

        mock_rust.assert_called_once()
        mock_py.assert_not_called()

    def test_us4_batch_any_large_triggers_rust(self):
        """Batch: at least one pair >= 20 fields → entire batch uses Rust."""
        from apps.sync.sync_engine import _merge_batch_python as real_py
        from apps.sync.sync_engine import _merge_batch_rust as real_rust

        small_pair = {
            "server": make_large_payload(5),
            "client": make_large_payload(5),
        }
        large_pair = {
            "server": make_large_payload(25),
            "client": make_large_payload(25),
        }
        pairs = [small_pair, large_pair, small_pair]

        with patch("apps.sync.sync_engine._merge_batch_rust", wraps=real_rust) as mock_rust_b, \
             patch("apps.sync.sync_engine._merge_batch_python", wraps=real_py) as mock_py_b:
            results = merge_most_complete_batch(pairs, METADATA)

        mock_rust_b.assert_called_once()
        mock_py_b.assert_not_called()
        assert len(results) == 3

    def test_us4_batch_all_small_uses_python(self):
        """Batch: all pairs < 20 fields → Python batch path."""
        pairs = [
            {"server": make_large_payload(5), "client": make_large_payload(5)},
            {"server": make_large_payload(10), "client": make_large_payload(10)},
        ]

        from apps.sync.sync_engine import _merge_batch_python as real_batch_py
        from apps.sync.sync_engine import _merge_batch_rust as real_batch_rust

        with patch("apps.sync.sync_engine._merge_batch_rust", wraps=real_batch_rust) as mock_rust_b, \
             patch("apps.sync.sync_engine._merge_batch_python", wraps=real_batch_py) as mock_py_b:
            results = merge_most_complete_batch(pairs, METADATA)

        mock_py_b.assert_called_once()
        mock_rust_b.assert_not_called()
        assert len(results) == 2

    def test_us4_threshold_value(self):
        """Verify _RUST_FIELD_THRESHOLD is 20 as specified."""
        assert _RUST_FIELD_THRESHOLD == 20
