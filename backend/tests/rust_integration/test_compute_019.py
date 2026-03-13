"""SPEC-019: Rust Fiscal Compute Engine — Integration Tests.

Tests for validate_importes, calculate_iva_breakdown, validate_iva_breakdown,
aggregate_stock_levels, and validate_cuit via PyO3 bindings.

Test coverage:
  T012 — validate_importes ARCA vectors (Rust)
  T013 — validate_importes Python fallback + benchmark
  T018 — calculate_iva_breakdown all IVA rates + mixed
  T019 — calculate_iva_breakdown fallback equivalence + benchmark
  T025 — validate_cuit CUIT corpus (Rust)
  T026 — validate_cuit Python fallback (ventas + serializer inline)
  T031 — aggregate_stock_levels shaped data (Rust)
  T032 — aggregate_stock_levels fallback + benchmark + empty
  T037 — validate_iva_breakdown type rules + sum checks + fallback
"""

import json
import time
from collections import defaultdict
from decimal import Decimal

import pytest

try:
    import gravitea_rust

    _USE_RUST = True
except (ImportError, OSError):
    _USE_RUST = False

pytestmark = pytest.mark.skipif(not _USE_RUST, reason="gravitea_rust not available")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_cuit(prefix: str) -> str:
    """Compute a valid 11-digit CUIT from a 10-digit numeric prefix."""
    weights = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    total = sum(int(d) * w for d, w in zip(prefix, weights))
    check = 11 - (total % 11)
    if check == 11:
        check = 0
    elif check == 10:
        check = 9
    return prefix + str(check)


def _build_movements_json(n_products: int, n_branches: int, per_combo: int) -> str:
    """Build a JSON movements array for aggregate_stock_levels tests."""
    movements = []
    for p in range(n_products):
        for b in range(n_branches):
            for _ in range(per_combo):
                movements.append(
                    {
                        "product_id": f"product-{p:03d}",
                        "branch_id": f"branch-{b:02d}",
                        "quantity": "10.00",
                        "movement_type": "IN",
                    }
                )
    return json.dumps(movements)


# ---------------------------------------------------------------------------
# T012: validate_importes — direct Rust ARCA vectors
# ---------------------------------------------------------------------------

VALID_IMPORTES_VECTORS = [
    # (imp_total, imp_neto, imp_iva, imp_trib, imp_op_ex, imp_tot_conc)
    ("100.00", "82.64", "17.36", "0.00", "0.00", "0.00"),        # balanced
    ("1000.00", "826.45", "173.55", "0.00", "0.00", "0.00"),      # larger amount
    ("500.00", "413.22", "86.78", "0.00", "0.00", "0.00"),        # balanced
    ("300.00", "200.00", "42.00", "18.00", "0.00", "40.00"),      # op_ex + trib
    ("100.005", "82.64", "17.36", "0.00", "0.00", "0.00"),        # within abs 0.01 tol
]

INVALID_IMPORTES_VECTORS = [
    ("100.05", "82.64", "17.36", "0.00", "0.00", "0.00"),         # off by 0.05 > 0.01
    ("200.00", "100.00", "0.00", "0.00", "0.00", "0.00"),         # missing IVA portion
    ("100.00", "82.64", "17.36", "10.00", "0.00", "0.00"),        # extra trib
    ("90.00", "82.64", "17.36", "0.00", "0.00", "0.00"),          # total too small
    ("100.00", "80.00", "10.00", "0.00", "0.00", "0.00"),         # wrong components
]


@pytest.mark.parametrize("args", VALID_IMPORTES_VECTORS)
def test_validate_importes_valid(args):
    """T012: Valid ARCA amount vectors must not raise."""
    gravitea_rust.validate_importes(*args)


@pytest.mark.parametrize("args", INVALID_IMPORTES_VECTORS)
def test_validate_importes_invalid(args):
    """T012: Invalid ARCA amount vectors must raise RuntimeError."""
    with pytest.raises(RuntimeError):
        gravitea_rust.validate_importes(*args)


# ---------------------------------------------------------------------------
# T013: validate_importes — Python fallback equivalence + benchmark
# ---------------------------------------------------------------------------


def test_validate_importes_fallback(monkeypatch):
    """T013: Python fallback validates the same vectors as Rust."""
    from django.core.exceptions import ValidationError

    from apps.facturacion.validators import validate_importes

    monkeypatch.setattr("apps.facturacion.validators._USE_RUST_COMPUTE", False)

    # Valid: must not raise
    validate_importes(
        imp_total=Decimal("100.00"),
        imp_neto=Decimal("82.64"),
        imp_iva=Decimal("17.36"),
        imp_trib=Decimal("0.00"),
        imp_op_ex=Decimal("0.00"),
        imp_tot_conc=Decimal("0.00"),
    )

    # Invalid: must raise
    with pytest.raises(ValidationError):
        validate_importes(
            imp_total=Decimal("100.05"),
            imp_neto=Decimal("82.64"),
            imp_iva=Decimal("17.36"),
            imp_trib=Decimal("0.00"),
            imp_op_ex=Decimal("0.00"),
            imp_tot_conc=Decimal("0.00"),
        )


@pytest.mark.slow
def test_validate_importes_benchmark():
    """T013: 1000 Rust validate_importes iterations complete in under 5 s."""
    start = time.monotonic()
    for _ in range(1000):
        gravitea_rust.validate_importes(
            "1000.00", "826.45", "173.55", "0.00", "0.00", "0.00"
        )
    elapsed = time.monotonic() - start
    assert elapsed < 5.0, f"1000 iterations took {elapsed:.2f}s"


# ---------------------------------------------------------------------------
# T018: calculate_iva_breakdown — all IVA rates + mixed + empty
# ---------------------------------------------------------------------------

# (iva_rate string, expected_iva_id) — from Rust iva_rate_to_id()
IVA_RATE_CASES = [
    ("0", 3),      # IVA_0
    ("2.5", 9),    # IVA_2_5
    ("5", 8),      # IVA_5
    ("10.5", 4),   # IVA_10_5
    ("21", 5),     # IVA_21
    ("27", 6),     # IVA_27
]


@pytest.mark.parametrize("rate,expected_id", IVA_RATE_CASES)
def test_calculate_iva_single_rate(rate, expected_id):
    """T018: Each IVA rate produces the correct iva_id."""
    items_json = json.dumps([{"price": "100.00", "quantity": "1", "iva_rate": rate}])
    result = json.loads(gravitea_rust.calculate_iva_breakdown(items_json))
    assert len(result) == 1
    assert result[0]["iva_id"] == expected_id


def test_calculate_iva_mixed_rates():
    """T018: Mixed rates produce one aggregated entry per rate."""
    items_json = json.dumps(
        [
            {"price": "100.00", "quantity": "1", "iva_rate": "21"},
            {"price": "50.00", "quantity": "2", "iva_rate": "10.5"},
            {"price": "200.00", "quantity": "1", "iva_rate": "21"},
        ]
    )
    result = json.loads(gravitea_rust.calculate_iva_breakdown(items_json))
    ids = {entry["iva_id"] for entry in result}
    assert ids == {5, 4}  # IVA_21 and IVA_10_5


def test_calculate_iva_empty_input():
    """T018: Empty items list returns empty result."""
    result = json.loads(gravitea_rust.calculate_iva_breakdown("[]"))
    assert result == []


# ---------------------------------------------------------------------------
# T019: calculate_iva_breakdown — fallback equivalence + benchmark
# ---------------------------------------------------------------------------


def test_calculate_iva_fallback_equivalence():
    """T019: Inline Python grouping logic matches Rust results."""
    items = [
        {"price": "100.00", "quantity": "1", "iva_rate": "21"},
        {"price": "50.00", "quantity": "2", "iva_rate": "21"},
        {"price": "80.00", "quantity": "1", "iva_rate": "10.5"},
    ]
    rust_result = json.loads(gravitea_rust.calculate_iva_breakdown(json.dumps(items)))

    # Python equivalent grouping
    groups: dict = defaultdict(lambda: {"base_imp": Decimal(0), "importe": Decimal(0)})
    for item in items:
        price = Decimal(item["price"])
        qty = Decimal(item["quantity"])
        rate = Decimal(item["iva_rate"])
        base = price * qty
        key = item["iva_rate"]
        groups[key]["base_imp"] += base
        groups[key]["importe"] += base * rate / 100

    assert len(rust_result) == 2
    rust_by_id = {entry["iva_id"]: entry for entry in rust_result}
    iva21 = rust_by_id[5]   # IVA_21
    iva10 = rust_by_id[4]   # IVA_10_5

    assert abs(Decimal(iva21["base_imp"]) - groups["21"]["base_imp"]) < Decimal("0.02")
    assert abs(Decimal(iva21["importe"]) - groups["21"]["importe"]) < Decimal("0.02")
    assert abs(Decimal(iva10["base_imp"]) - groups["10.5"]["base_imp"]) < Decimal("0.02")


@pytest.mark.slow
def test_calculate_iva_benchmark():
    """T019: 500 iterations of a 20-item invoice complete in under 5 s."""
    items_json = json.dumps(
        [{"price": "150.00", "quantity": "1", "iva_rate": "21"}] * 20
    )
    start = time.monotonic()
    for _ in range(500):
        gravitea_rust.calculate_iva_breakdown(items_json)
    elapsed = time.monotonic() - start
    assert elapsed < 5.0, f"500 iterations took {elapsed:.2f}s"


# ---------------------------------------------------------------------------
# T025: validate_cuit — CUIT corpus
# ---------------------------------------------------------------------------

_CUIT_1 = _make_cuit("2023456789")   # e.g. "20234567897"
_WRONG_LAST = _CUIT_1[:-1] + str((int(_CUIT_1[-1]) + 1) % 10)

VALID_CUITS = [
    _make_cuit("2023456789"),
    _make_cuit("2712345678"),
    _make_cuit("3012345678"),
    _make_cuit("2000000000"),
    _make_cuit("2734567890"),
]

INVALID_CUITS = [
    "12345",            # too short
    "123456789012",     # too long
    "99999999999",      # wrong check digit (correct is 5)
    _WRONG_LAST,        # valid format, wrong check digit
    "20000000009",      # correct prefix "2000000000", check should be 1 not 9
]


@pytest.mark.parametrize("cuit", VALID_CUITS)
def test_validate_cuit_valid(cuit):
    """T025: Valid CUITs must not raise."""
    gravitea_rust.validate_cuit(cuit)


@pytest.mark.parametrize("cuit", INVALID_CUITS)
def test_validate_cuit_invalid(cuit):
    """T025: Invalid CUITs must raise RuntimeError."""
    with pytest.raises(RuntimeError):
        gravitea_rust.validate_cuit(cuit)


# ---------------------------------------------------------------------------
# T026: validate_cuit — Python fallback equivalence
# ---------------------------------------------------------------------------


def test_validate_cuit_ventas_fallback(monkeypatch):
    """T026: ventas.validators.validate_cuit Python fallback is equivalent to Rust."""
    from django.core.exceptions import ValidationError

    from apps.ventas.validators import validate_cuit

    monkeypatch.setattr("apps.ventas.validators._USE_RUST_COMPUTE", False)

    valid_cuit = _make_cuit("2023456789")
    validate_cuit(valid_cuit)  # must not raise

    with pytest.raises(ValidationError):
        validate_cuit("12345")

    with pytest.raises(ValidationError):
        validate_cuit(_WRONG_LAST)


def test_validate_cuit_serializer_inline():
    """T026: Inline Python Modulo-11 (serializer logic) agrees with Rust on all corpus CUITs."""
    import re

    _CUIT_PATTERN = re.compile(r"^\d{11}$")
    _WEIGHTS = (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)

    def _py_validate(value: str) -> bool:
        if not _CUIT_PATTERN.match(value):
            return False
        digits = [int(d) for d in value]
        total = sum(d * w for d, w in zip(digits[:10], _WEIGHTS))
        check = 11 - (total % 11)
        if check == 11:
            check = 0
        elif check == 10:
            check = 9
        return digits[10] == check

    for cuit in VALID_CUITS:
        assert _py_validate(cuit), f"{cuit} should be valid"
        gravitea_rust.validate_cuit(cuit)  # Rust agrees

    for cuit in INVALID_CUITS:
        assert not _py_validate(cuit), f"{cuit} should be invalid"
        with pytest.raises(RuntimeError):
            gravitea_rust.validate_cuit(cuit)  # Rust agrees


# ---------------------------------------------------------------------------
# T031: aggregate_stock_levels — shaped data (direct Rust)
# ---------------------------------------------------------------------------


def test_aggregate_stock_shaped_data():
    """T031: 500 movements across 50 products × 3 branches aggregates correctly."""
    movements = json.loads(_build_movements_json(n_products=50, n_branches=3, per_combo=3))
    movements_json = json.dumps(movements[:500])

    result = json.loads(gravitea_rust.aggregate_stock_levels(movements_json))

    assert len(result) == 50
    for _pid, branches in result.items():
        assert len(branches) == 3
        for _bid, vals in branches.items():
            total = Decimal(vals["total"])
            reserved = Decimal(vals["reserved"])
            available = Decimal(vals["available"])
            assert total > 0
            assert available == total - reserved


def test_aggregate_stock_empty():
    """T032: Empty input returns empty dict."""
    result = json.loads(gravitea_rust.aggregate_stock_levels("[]"))
    assert result == {}


@pytest.mark.slow
def test_aggregate_stock_benchmark():
    """T032: 100 × 500-movement aggregation completes in under 10 s."""
    movements = json.loads(_build_movements_json(n_products=50, n_branches=3, per_combo=3))
    movements_json = json.dumps(movements[:500])

    start = time.monotonic()
    for _ in range(100):
        gravitea_rust.aggregate_stock_levels(movements_json)
    elapsed = time.monotonic() - start
    assert elapsed < 10.0, f"100 × 500-movement batch took {elapsed:.2f}s"


def test_aggregate_stock_fallback_equivalence():
    """T032: Python fallback logic produces the same results as Rust."""
    movements = [
        {"product_id": "p1", "branch_id": "b1", "quantity": "10.00", "movement_type": "IN"},
        {"product_id": "p1", "branch_id": "b1", "quantity": "3.00", "movement_type": "OUT"},
        {"product_id": "p1", "branch_id": "b1", "quantity": "2.00", "movement_type": "RESERVED"},
        {"product_id": "p2", "branch_id": "b1", "quantity": "5.00", "movement_type": "IN"},
        {"product_id": "p1", "branch_id": "b1", "quantity": "1.00", "movement_type": "RELEASED"},
    ]
    movements_json = json.dumps(movements)
    rust_result = json.loads(gravitea_rust.aggregate_stock_levels(movements_json))

    # Python fallback logic — mirrors Rust aggregation
    _IN = {"IN", "ADJUSTMENT", "TRANSFER_IN"}
    _OUT = {"OUT", "TRANSFER_OUT"}
    _RESERVE = {"RESERVED"}
    _RELEASE = {"RELEASED"}
    acc: dict = {}
    for m in movements:
        pid = m["product_id"]
        bid = m["branch_id"]
        qty = Decimal(m["quantity"])
        mtype = m["movement_type"]
        bucket = acc.setdefault(pid, {}).setdefault(
            bid, {"total": Decimal(0), "reserved": Decimal(0)}
        )
        if mtype in _IN:
            bucket["total"] += qty
        elif mtype in _OUT:
            bucket["total"] -= qty
        elif mtype in _RESERVE:
            bucket["reserved"] += qty
        elif mtype in _RELEASE:
            bucket["reserved"] -= qty

    assert set(rust_result.keys()) == set(acc.keys())
    for pid in acc:
        for bid in acc[pid]:
            rust_total = Decimal(rust_result[pid][bid]["total"])
            rust_reserved = Decimal(rust_result[pid][bid]["reserved"])
            py_total = acc[pid][bid]["total"]
            py_reserved = acc[pid][bid]["reserved"]
            assert abs(rust_total - py_total) < Decimal("0.001")
            assert abs(rust_reserved - py_reserved) < Decimal("0.001")


# ---------------------------------------------------------------------------
# T037: validate_iva_breakdown — type rules, sum checks, fallback
# ---------------------------------------------------------------------------

IVA_REQUIRED_TIPOS = [1, 2, 3, 6, 7, 8, 51, 52, 53]   # A, B, M
IVA_PROHIBITED_TIPOS = [11, 12, 13]                      # C

_SAMPLE_ALICIVA = json.dumps(
    [{"iva_id": 5, "base_imp": "100.00", "importe": "21.00"}]
)


@pytest.mark.parametrize("cbte_tipo", IVA_REQUIRED_TIPOS)
def test_validate_iva_required_empty_fails(cbte_tipo):
    """T037: A/B/M types with empty IVA breakdown must raise."""
    with pytest.raises(RuntimeError):
        gravitea_rust.validate_iva_breakdown(cbte_tipo, "[]", "21.00", "100.00")


@pytest.mark.parametrize("cbte_tipo", IVA_REQUIRED_TIPOS)
def test_validate_iva_required_valid_passes(cbte_tipo):
    """T037: A/B/M types with valid IVA breakdown must not raise."""
    gravitea_rust.validate_iva_breakdown(cbte_tipo, _SAMPLE_ALICIVA, "21.00", "100.00")


@pytest.mark.parametrize("cbte_tipo", IVA_PROHIBITED_TIPOS)
def test_validate_iva_prohibited_nonempty_fails(cbte_tipo):
    """T037: C types with non-empty IVA breakdown must raise."""
    with pytest.raises(RuntimeError):
        gravitea_rust.validate_iva_breakdown(cbte_tipo, _SAMPLE_ALICIVA, "0.00", "0.00")


@pytest.mark.parametrize("cbte_tipo", IVA_PROHIBITED_TIPOS)
def test_validate_iva_prohibited_empty_passes(cbte_tipo):
    """T037: C types with empty IVA breakdown must not raise."""
    gravitea_rust.validate_iva_breakdown(cbte_tipo, "[]", "0.00", "0.00")


def test_validate_iva_sum_importe_mismatch():
    """T037: importe sum != imp_iva must raise."""
    aliciva_json = json.dumps([{"iva_id": 5, "base_imp": "100.00", "importe": "21.00"}])
    with pytest.raises(RuntimeError):
        # imp_iva=30.00 but importe sum=21.00
        gravitea_rust.validate_iva_breakdown(1, aliciva_json, "30.00", "100.00")


def test_validate_iva_sum_base_mismatch():
    """T037: base_imp sum != imp_neto must raise."""
    aliciva_json = json.dumps([{"iva_id": 5, "base_imp": "100.00", "importe": "21.00"}])
    with pytest.raises(RuntimeError):
        # imp_neto=200.00 but base_imp sum=100.00
        gravitea_rust.validate_iva_breakdown(1, aliciva_json, "21.00", "200.00")


def test_validate_iva_breakdown_fallback(monkeypatch):
    """T037: Python fallback for validate_iva_breakdown matches Rust behaviour."""
    from django.core.exceptions import ValidationError

    from apps.facturacion.validators import validate_iva_breakdown

    monkeypatch.setattr("apps.facturacion.validators._USE_RUST_COMPUTE", False)

    # Type A with valid breakdown — must not raise
    validate_iva_breakdown(
        cbte_tipo=1,
        aliciva_list=[
            {"iva_id": 5, "base_imp": Decimal("100.00"), "importe": Decimal("21.00")}
        ],
        imp_iva=Decimal("21.00"),
        imp_neto=Decimal("100.00"),
    )

    # Type A with empty list — must raise
    with pytest.raises(ValidationError):
        validate_iva_breakdown(
            cbte_tipo=1,
            aliciva_list=[],
            imp_iva=Decimal("0.00"),
            imp_neto=Decimal("0.00"),
        )

    # Type C with non-empty list — must raise
    with pytest.raises(ValidationError):
        validate_iva_breakdown(
            cbte_tipo=11,
            aliciva_list=[
                {"iva_id": 5, "base_imp": Decimal("100.00"), "importe": Decimal("21.00")}
            ],
            imp_iva=Decimal("21.00"),
            imp_neto=Decimal("100.00"),
        )
