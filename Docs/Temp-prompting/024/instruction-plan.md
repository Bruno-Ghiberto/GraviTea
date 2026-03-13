# Speckit Context: ARCA Batch Builder — PLAN Phase (SPEC-024)

> **Phase**: PLAN — Design implementation plan, research decisions, task breakdown
> **Priority**: MEDIUM | **Wave**: 5 (parallel with SPEC-025)
> **Produces**: `plan.md`, `research.md`, `quickstart.md`
> **Does NOT produce**: data-model.md, api-contract.md
> **Benefits from**: SPEC-023 (serde_json already in Cargo.toml)

---

## Mission

Design the implementation plan for accelerating CAEA quincena batch request construction. Replace the inner loop of `CAEAService.informar_comprobantes()` (caea.py lines 232-302) with a Rust/PyO3 function that serializes 20-100 comprobantes into SOAP-compatible dict structures.

## Key Corrections from Specify Phase

These items from the earlier draft were **wrong** — corrected here based on source code analysis:

| Item | Original (WRONG) | Corrected | Evidence |
|------|------------------|-----------|----------|
| `chrono` crate | "NEW dependency needed" | **NOT needed** — all date fields are pre-formatted YYYYMMDD string passthrough | `caea.py:253-255` — `det["FchServDesde"] = cbte["fch_serv_desde"]` (string copy, no formatting) |
| `rust_decimal` crate | "Shared from SPEC-019 for Decimal→f64" | **NOT needed** — amounts are `str→f64` via `parse()`, not `Decimal→f64` | `caea.py:240` — `float(cbte["imp_total"])` matches `"123.45".parse::<f64>()` exactly (IEEE 754) |
| ARCA-EXPERT agent | "Separate Opus agent for SOAP structure validation" | **Eliminated** — structure is fully documented in instruction-specify.md from source code | `instruction-specify.md` has exact Python code + complete serde struct designs |
| Phase 1 (SOAP Analysis) | "Query Qdrant RAG, document structure" | **Already done** — specify phase completed full analysis via GitNexus + source code reading | See `instruction-specify.md` §Serde Struct Design |
| R-001 through R-004 | "Research topics for research.md" | **All resolved** — see Research Decisions below | Source code is the ground truth |

## Team Architecture

| Agent | Subagent Type | Model | Role |
|-------|--------------|-------|------|
| ORCHESTRATOR (LEAD) | system-architect | Opus 4.6 | Coordinates, validates, documentation, Docker |
| RUST-EXPERT | general-purpose | Opus 4.6 | Implements `arca.rs`, writes cargo tests |
| QA | python-expert | Sonnet 4.6 | Python integration tests, parity verification, benchmarks |

### Why 3 Agents, Not 4

The ARCA-EXPERT role is unnecessary because:
1. The SOAP structure is fully visible in `caea.py` lines 232-302 (the exact code we're replacing)
2. The instruction-specify.md documents every field name, type, nesting level, and edge case
3. Serde struct designs (Input + Output) are already complete and validated against the source
4. No RAG query is needed — the Python source code IS the specification

### Sequential-Thinking MCP

- **MANDATORY**: RUST-EXPERT (serde struct design validation against instruction-specify.md)
- **NOT required**: QA

## Implementation Phases

### Phase 1: Rust Core (RUST-EXPERT)
- **Risk**: HIGH (ARCA rejects on any key name or type mismatch)
- **Prerequisite**: Read `Docs/Temp-prompting/024/instruction-specify.md` §Serde Struct Design
- Tasks:
  1. Add `ARCABuildError(String)` variant to `errors.rs` → maps to `PyRuntimeError`
  2. Create `rust/gravitea-core/src/arca.rs` with serde structs from instruction-specify.md
  3. Implement `build_caea_batch_request(comprobantes_json: &str, caea: &str, default_cuit: &str) -> PyResult<String>`
  4. Handle all transformations:
     - Amount strings → `f64` via `str::parse::<f64>()` (NOT rust_decimal)
     - Date strings → passthrough (no chrono, no parsing)
     - AlicIva → nested `{"Iva": {"AlicIva": [...]}}` with `#[serde(skip_serializing_if)]`
     - Tributos → guarded by `imp_trib > 0.0` check, nested `{"Tributos": {"Tributo": [...]}}`
     - CbtesAsoc → CUIT fallback to `default_cuit` parameter
     - Service dates → conditional on `concepto == 2 || concepto == 3`
  5. Release GIL via `py.detach()` during batch construction
  6. Register `mod arca` + `#[pymodule_export] use super::arca::build_caea_batch_request` in `lib.rs`
  7. Write ≥10 Rust-native tests covering all spec edge cases

### Phase 2: Python Integration (QA + LEAD)
- **Risk**: MEDIUM
- **Prerequisite**: Phase 1 complete (Rust function passes cargo tests)
- Tasks:
  1. Create `backend/apps/facturacion/arca/caea_engine.py` — dispatcher following `sync_engine.py` pattern
  2. Extract Python inner loop from `caea.py` into `_build_python()` fallback function in `caea_engine.py`
  3. Modify `caea.py:informar_comprobantes()` to call `caea_engine.build_det_list(comprobantes, caea, self.cuit)` instead of inline loop
  4. Update `backend/gravitea_rust.pyi` with type stub for `build_caea_batch_request`
  5. Write parity tests: Rust output == Python fallback output for same input
  6. Write threshold guard tests: ≤10 → Python path, >10 → Rust path
  7. Write fallback tests: `_USE_RUST = False` → Python path, correct output
  8. Write benchmark test: 50 comprobantes < 5ms (Rust path)

### Phase 3: Docker + Regression (LEAD)
- **Risk**: LOW
- **Prerequisite**: Phase 2 complete (all pytest pass locally)
- Tasks:
  1. Rebuild Docker: `docker compose build web`
  2. Verify `build_caea_batch_request` importable in container
  3. Run SPEC-024 tests inside Docker
  4. Full test suite — 0 regressions
  5. Update quickstart.md

## Research Decisions (for research.md — ALL RESOLVED)

| ID | Topic | Decision | Evidence |
|----|-------|----------|----------|
| R-001 | FECAEARegInformativo dict structure | **RESOLVED**: Complete field mapping extracted from `caea.py:232-302` | instruction-specify.md §Exact Python Inner Loop |
| R-002 | Date formatting approach | **RESOLVED**: String passthrough — NO chrono needed | `caea.py:253`: `det["FchServDesde"] = cbte["fch_serv_desde"]` (no formatting) |
| R-003 | Amount str→f64 precision | **RESOLVED**: `str::parse::<f64>()` matches Python `float()` for 2-decimal amounts — NO rust_decimal needed | instruction-specify.md caveat #8: IEEE 754 identical |
| R-004 | zeep dict key names | **RESOLVED**: 15 top-level keys documented in spec FR-005, nested keys in FR-008/FR-009/FR-010 | instruction-specify.md §Serde Struct Design |
| R-005 | `CbteAsoc.cuit` fallback | **RESOLVED**: Use `default_cuit` parameter (which is `self.cuit` from `CAEAService`) | `caea.py:296`: `item.get("cuit", self.cuit)` |
| R-006 | Empty `alic_iva` array handling | **RESOLVED**: Treat `[]` as absent — omit IVA section entirely | Spec edge case: "empty array is treated as absent" |

## Crate Dependencies

**ZERO new dependencies.** All crates already exist in `Cargo.toml`:

| Crate | Version | Status | Purpose in SPEC-024 |
|-------|---------|--------|---------------------|
| `serde` | 1.0 | SHARED (SPEC-023) | `#[derive(Deserialize, Serialize)]` for input/output structs |
| `serde_json` | 1.0 | SHARED (SPEC-023) | Parse input JSON, serialize output JSON |
| `pyo3` | 0.28 | SHARED (SPEC-017) | `#[pyfunction]`, GIL release via `py.detach()` |
| `thiserror` | 2.0 | SHARED (SPEC-017) | `ARCABuildError` variant in `GraviteaError` |

**NOT needed (corrected from earlier draft):**
- ~~`chrono 0.4`~~: Date fields are string passthrough, no formatting needed
- ~~`rust_decimal 1.36`~~: Amounts use `str::parse::<f64>()`, not `Decimal::to_f64()`

## Exact File Changes

### New Files (2)

| File | Lines (est.) | Contents |
|------|-------------|----------|
| `rust/gravitea-core/src/arca.rs` | ~400 | Serde structs (Input/Output), `build_caea_batch_request` PyO3 function, conversion logic, tests |
| `backend/apps/facturacion/arca/caea_engine.py` | ~100 | Dispatcher: `_USE_RUST` flag, threshold guard, `_build_rust()`, `_build_python()`, `build_det_list()` |

### Modified Files (4)

| File | Changes |
|------|---------|
| `rust/gravitea-core/src/errors.rs` | +1 variant: `ARCABuildError(String)` → `PyRuntimeError` |
| `rust/gravitea-core/src/lib.rs` | +1 line `mod arca;` + 1 line `#[pymodule_export] use super::arca::build_caea_batch_request;` |
| `backend/apps/facturacion/arca/caea.py` | Replace lines 231-302 (inner loop) with `from .caea_engine import build_det_list` + single call |
| `backend/gravitea_rust.pyi` | +1 function stub: `build_caea_batch_request(comprobantes_json: str, caea: str, default_cuit: str) -> str` |

### New Test File (1)

| File | Tests (est.) | Contents |
|------|-------------|----------|
| `backend/tests/rust_integration/test_arca_024.py` | ~25 | Parity tests, threshold guard, fallback, edge cases, benchmark |

## FFI Boundary (Exact)

```
Python (caea_engine.py)                   Rust (arca.rs)
─────────────────────────                 ────────────────
comprobantes: list[dict]
  → json.dumps(comprobantes)
    → comprobantes_json: &str ──────────► serde_json::from_str::<Vec<ComprobanteInput>>()
caea: str ──────────────────────────────► caea: &str (stamped on every output item)
self.cuit: str ─────────────────────────► default_cuit: &str (CbteAsoc fallback)

                                          Build Vec<FECAEADetRequest>:
                                            - 7 str→f64 conversions per item
                                            - Conditional service dates (concepto 2|3)
                                            - Optional nested IVA/Tributos/CbtesAsoc
                                            - GIL released via py.detach()

                                          serde_json::to_string(&det_list)
  ◄──────────────────────────────────────── → result_json: String
json.loads(result_json) → det_list
```

## Integration Point in caea.py

The modification is surgical — replace lines 231-302 with a single dispatcher call:

```python
# BEFORE (lines 231-302):
det_list = []
for cbte in comprobantes:
    det = { ... }  # 70 lines of dict construction
    det_list.append(det)

# AFTER (3 lines):
from .caea_engine import build_det_list

det_list = build_det_list(comprobantes, caea, self.cuit)
```

The outer `fe_cab_req` (lines 225-229), SOAP call (lines 306-317), response parsing (lines 331-374), and error handling remain **UNCHANGED**.

## Dispatcher Pattern (caea_engine.py)

Follows `sync_engine.py` (SPEC-023) pattern. Key differences:

| Aspect | sync_engine.py (023) | caea_engine.py (024) |
|--------|---------------------|---------------------|
| Threshold | `_RUST_FIELD_THRESHOLD = 20` (field count) | `_RUST_BATCH_THRESHOLD = 10` (batch size) |
| Routing | Field count per payload | `len(comprobantes) > threshold` |
| GIL | Released for batch only | Always released (batch is the only mode) |
| Fallback reason | Small payloads | Small batches OR extension unavailable |

```python
"""CAEA Batch Builder dispatcher — Rust-accelerated det_list construction."""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

_USE_RUST: bool

try:
    from gravitea_rust import (
        build_caea_batch_request as _rust_build,
    )
    _USE_RUST = True
except (ImportError, OSError):
    _USE_RUST = False
    logger.warning(
        "gravitea_rust ARCA batch builder not available — using Python fallback"
    )

_RUST_BATCH_THRESHOLD = 10


def build_det_list(
    comprobantes: list[dict[str, Any]],
    caea: str,
    default_cuit: str,
) -> list[dict[str, Any]]:
    """Build the FECAEADetRequest list for a CAEA batch."""
    if _USE_RUST and len(comprobantes) > _RUST_BATCH_THRESHOLD:
        return _build_rust(comprobantes, caea, default_cuit)
    return _build_python(comprobantes, caea, default_cuit)


def _build_rust(
    comprobantes: list[dict[str, Any]],
    caea: str,
    default_cuit: str,
) -> list[dict[str, Any]]:
    """Rust-accelerated batch build (GIL released)."""
    comprobantes_json = json.dumps(comprobantes)
    result_json = _rust_build(comprobantes_json, caea, default_cuit)
    return json.loads(result_json)


def _build_python(
    comprobantes: list[dict[str, Any]],
    caea: str,
    default_cuit: str,
) -> list[dict[str, Any]]:
    """Python fallback — extracted from caea.py inner loop."""
    det_list = []
    for cbte in comprobantes:
        det: dict[str, Any] = {
            "Concepto": cbte["concepto"],
            "DocTipo": cbte["doc_tipo"],
            "DocNro": cbte["doc_nro"],
            "CbteDesde": cbte["cbte_desde"],
            "CbteHasta": cbte["cbte_hasta"],
            "CbteFch": cbte["cbte_fch"],
            "ImpTotal": float(cbte["imp_total"]),
            "ImpTotConc": float(cbte["imp_tot_conc"]),
            "ImpNeto": float(cbte["imp_neto"]),
            "ImpOpEx": float(cbte["imp_op_ex"]),
            "ImpTrib": float(cbte["imp_trib"]),
            "ImpIVA": float(cbte["imp_iva"]),
            "MonId": cbte.get("mon_id", "PES"),
            "MonCotiz": float(cbte.get("mon_cotiz", 1)),
            "CAEA": caea,
        }

        if cbte.get("concepto") in (2, 3):
            det["FchServDesde"] = cbte["fch_serv_desde"]
            det["FchServHasta"] = cbte["fch_serv_hasta"]
            det["FchVtoPago"] = cbte["fch_vto_pago"]

        alic_iva = cbte.get("alic_iva")
        if alic_iva:
            det["Iva"] = {
                "AlicIva": [
                    {
                        "Id": item["iva_id"],
                        "BaseImp": float(item["base_imp"]),
                        "Importe": float(item["importe"]),
                    }
                    for item in alic_iva
                ]
            }

        tributos = cbte.get("tributos")
        if tributos and float(cbte.get("imp_trib", 0)) > 0:
            det["Tributos"] = {
                "Tributo": [
                    {
                        "Id": item["tributo_id"],
                        "Desc": item["desc"],
                        "BaseImp": float(item["base_imp"]),
                        "Alic": float(item["alic"]),
                        "Importe": float(item["importe"]),
                    }
                    for item in tributos
                ]
            }

        cbtes_asoc = cbte.get("cbtes_asoc")
        if cbtes_asoc:
            det["CbtesAsoc"] = {
                "CbteAsoc": [
                    {
                        "Tipo": item["tipo"],
                        "PtoVta": item["pto_vta"],
                        "Nro": item["nro"],
                        "Cuit": item.get("cuit", default_cuit),
                    }
                    for item in cbtes_asoc
                ]
            }

        det_list.append(det)
    return det_list
```

**Critical difference from `caea.py` original**: The fallback uses `default_cuit` parameter instead of `self.cuit`. This is because the dispatcher is a standalone module, not a method on `CAEAService`. The caller passes `self.cuit` as `default_cuit`.

## Serde Struct Design (FINAL — from instruction-specify.md)

The complete serde struct designs are in `Docs/Temp-prompting/024/instruction-specify.md` §Serde Struct Design. Key points:

1. **Input structs** — `ComprobanteInput`, `AlicIvaInput`, `TributoInput`, `CbteAsocInput` — use `#[derive(Deserialize)]`
2. **Output structs** — `FECAEADetRequest`, `IvaWrapper`, `AlicIvaOutput`, `TributosWrapper`, `TributoOutput`, `CbtesAsocWrapper`, `CbteAsocOutput` — use `#[derive(Serialize)]`
3. **Key naming** — `#[serde(rename_all = "PascalCase")]` on `FECAEADetRequest` + per-field overrides for `ImpIVA` and `CAEA`
4. **Optional fields** — `#[serde(skip_serializing_if = "Option::is_none")]` for service dates, IVA, tributos, cbtes_asoc

Do NOT re-design these structs. They are validated against the Python source code.

## Critical Caveats (Implementation Guards)

1. **`ImpIVA` not `ImpIva`**: Use `#[serde(rename = "ImpIVA")]` — PascalCase auto-rename would produce wrong key
2. **`CAEA` not `Caea`**: Use `#[serde(rename = "CAEA")]` — same issue
3. **Tributos guard is `imp_trib > 0.0`**, not just "tributos present" — both conditions required
4. **Empty `alic_iva: []`** must be treated as absent — check `!vec.is_empty()` before wrapping
5. **`mon_cotiz` default is `"1"` → f64 `1.0`** — serde `#[serde(default)]` with custom default fn
6. **CbteAsoc CUIT fallback**: When `cuit` is `None`, substitute `default_cuit` — this happens during conversion, not serde
7. **Output order**: `Vec` preserves insertion order — serde serializes struct fields in declaration order. Both deterministic.
8. **`float("0") > 0` is `False` in Python** — Rust must use `imp_trib > 0.0` (not `>= 0.0`) to match

## Testing Standards

1. **Rust-native** (`cargo test`): ≥10 tests covering:
   - Basic comprobante (Concepto 1, products only)
   - Service dates (Concepto 2 and 3)
   - IVA breakdown (single rate, multiple rates)
   - Tributos (present + imp_trib > 0, present + imp_trib = 0)
   - CbtesAsoc (with cuit, without cuit → default_cuit)
   - Empty optional arrays
   - Defaults (mon_id absent → "PES", mon_cotiz absent → 1.0)
   - Large batch (100 items)
   - Edge: negative imp_trib
   - Edge: large float values ("99999999.99")
2. **Python integration** (`pytest`): ≥15 tests covering:
   - Parity: Rust vs Python fallback for all test vectors
   - Threshold guard: ≤10 → Python, >10 → Rust
   - Fallback: `_USE_RUST = False` → correct output
   - Benchmark: 50 comprobantes < 5ms (Rust path)
   - Edge cases from spec
3. **Docker**: Import check + SPEC-024 tests in container + 0 regressions
4. **Test file**: `backend/tests/rust_integration/test_arca_024.py`

## Reference Documents

| Document | Purpose | Path |
|----------|---------|------|
| Specify context (solidified) | Architecture decisions, serde struct designs, exact Python code, caveats | `Docs/Temp-prompting/024/instruction-specify.md` |
| Spec | Formal requirements (17 FRs, 6 SCs) | `specs/024-rust-arca-batch/spec.md` |
| Roadmap | OPP-007 details | `Docs/Brainstorming/rust-pyo3-speckit-roadmap.md` §10 |
| Current CAEA | Python implementation (target file) | `backend/apps/facturacion/arca/caea.py` |
| Dispatcher template | sync_engine.py pattern | `backend/apps/sync/sync_engine.py` |
| Rust module registry | Current lib.rs (16 exports) | `rust/gravitea-core/src/lib.rs` |
| Error variants | Current errors.rs (7 variants) | `rust/gravitea-core/src/errors.rs` |
| Type stubs | .pyi pattern | `backend/gravitea_rust.pyi` |
| Invoice skill | ARCA domain patterns | `skills/gravitea-invoice/SKILL.md` |
| Constants | CbteTipo, AlicIvaId enums | `backend/apps/facturacion/constants.py` |

## GitNexus Blast Radius (Verified)

| Check | Result |
|-------|--------|
| `impact(informar_comprobantes, upstream)` | **LOW** — 0 affected symbols, 0 processes |
| `context(CAEAService)` | Incoming: `solicitar` + `sin_movimiento` (views.py) |
| `context(informar_comprobantes)` | Outgoing: `track_soap_call`, `_auth_dict`, `_parse_informar_response` |
| Conclusion | Inner loop replacement is **safe** — output consumed only by zeep SOAP call |
