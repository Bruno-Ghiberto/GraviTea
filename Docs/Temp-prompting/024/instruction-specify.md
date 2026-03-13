# Speckit Context: ARCA Batch Builder (SPEC-024)

> **Phase**: SPECIFY — Define what we're accelerating and why
> **Priority**: MEDIUM | **Wave**: 5 (parallel with SPEC-025)
> **Depends on**: SPEC-017 (Rust Toolchain Bootstrap) MUST be complete
> **Benefits from**: SPEC-019 (shares `rust_decimal`, `serde`, `decimal_utils.rs`)

---

## Mission Statement

Accelerate batch ARCA request construction for CAEA quincena reporting, where 20-100 comprobantes are serialized into SOAP request dicts. This spec targets the inner loop of `CAEAService.informar_comprobantes()` (lines 232-302 of `caea.py`).

## Why This Matters Now

- **2-3x for batches of 50+**: `serde` builds entire batch request structure in single allocation pass
- **CAEA quincena deadline**: Batch processing must complete reliably — Rust reduces processing time and GC jitter
- **6+ Decimal-to-float conversions per comprobante**: Rust `f64` conversion from `rust_decimal` is branchless
- **Extends SPEC-019**: Uses same `rust_decimal` and `serde_json` crates, shares `decimal_utils.rs`

## Architecture Decisions (FINAL — Do Not Re-Debate)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Serialization | `serde_json` (already from SPEC-023) | Standard Rust JSON |
| Date formatting | `chrono 0.4` (NEW dep) | ARCA requires `YYYYMMDD` strings |
| Decimal handling | `rust_decimal` (already from SPEC-019) | Shared decimal infrastructure |
| Batch threshold | >10 comprobantes | Below 10, FFI overhead negates gain |
| GIL handling | Released during batch build via `py.detach()` | Other Python threads proceed |
| CAEA only | Yes | CAE processes single comprobantes — not worth Rust |
| Output format | JSON string matching zeep SOAP dict structure | Must match exactly or ARCA rejects |
| Error variant | `ARCABuildError` in `errors.rs` → `RuntimeError` in Python | Follows 018-023 pattern |

## Current State (What Exists Today)

| Item | Details |
|------|---------|
| **File** | `backend/apps/facturacion/arca/caea.py` lines 194-329 |
| **Class** | `CAEAService` (line 74) |
| **Function** | `informar_comprobantes()` — inner loop lines 232-302 |
| **Callers** | Views: `solicitar` and `sin_movimiento` in `facturacion/views.py` (GitNexus upstream impact: LOW, 0 affected) |
| **Call frequency** | Once per CAEA quincena deadline (batch of 20-100 comprobantes) |
| **Current cost** | ~5-10ms for 50 comprobantes |
| **Operations** | 6x `float()` conversions, date string passthrough, nested dict construction (AlicIva, Tributo, CbtesAsoc arrays), conditional service dates |

### Exact Python Inner Loop (lines 232-302)

The Rust function must produce **byte-identical JSON** to what this Python loop builds:

```python
det_list = []
for cbte in comprobantes:
    det = {
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

    # Service dates for Concepto 2 or 3
    if cbte.get("concepto") in (2, 3):
        det["FchServDesde"] = cbte["fch_serv_desde"]
        det["FchServHasta"] = cbte["fch_serv_hasta"]
        det["FchVtoPago"] = cbte["fch_vto_pago"]

    # IVA breakdown
    alic_iva = cbte.get("alic_iva")
    if alic_iva:
        det["Iva"] = {
            "AlicIva": [
                {"Id": item["iva_id"], "BaseImp": float(item["base_imp"]),
                 "Importe": float(item["importe"])}
                for item in alic_iva
            ]
        }

    # Tributos
    tributos = cbte.get("tributos")
    if tributos and float(cbte.get("imp_trib", 0)) > 0:
        det["Tributos"] = {
            "Tributo": [
                {"Id": item["tributo_id"], "Desc": item["desc"],
                 "BaseImp": float(item["base_imp"]),
                 "Alic": float(item["alic"]),
                 "Importe": float(item["importe"])}
                for item in tributos
            ]
        }

    # Associated comprobantes
    cbtes_asoc = cbte.get("cbtes_asoc")
    if cbtes_asoc:
        det["CbtesAsoc"] = {
            "CbteAsoc": [
                {"Tipo": item["tipo"], "PtoVta": item["pto_vta"],
                 "Nro": item["nro"],
                 "Cuit": item.get("cuit", self.cuit)}
                for item in cbtes_asoc
            ]
        }

    det_list.append(det)
```

### Outer Wrapper (lines 225-304)

The Rust function does NOT build the outer wrapper. Python remains responsible for:

```python
fe_cab_req = {
    "CantReg": len(comprobantes),
    "PtoVta": first["punto_venta"],
    "CbteTipo": first["cbte_tipo"],
}
fe_det_req = {"FECAEADetRequest": det_list}  # det_list from Rust
```

The Rust function builds only `det_list` (the batch of `FECAEADetRequest` items).

## Target Architecture

### New Rust Source

```
rust/gravitea-core/src/
+-- lib.rs              # Add `mod arca;` + #[pymodule_export] for build_caea_batch_request
+-- arca.rs             # NEW — build_caea_batch_request + serde structs
```

### New Python Source

```
backend/apps/facturacion/arca/
+-- caea_engine.py      # NEW — dispatcher (Rust/Python) following sync_engine.py pattern
```

### Modified Files

```
backend/apps/facturacion/arca/caea.py          # Import from caea_engine, threshold guard
backend/gravitea_rust.pyi                       # +1 stub: build_caea_batch_request
rust/gravitea-core/Cargo.toml                   # +chrono = "0.4"
rust/gravitea-core/src/lib.rs                   # +mod arca + pymodule_export
rust/gravitea-core/src/errors.rs                # +ARCABuildError variant
```

### Functions to Implement

| Function | Rust Signature | Python Wrapper | GIL |
|----------|---------------|----------------|-----|
| `build_caea_batch_request` | `(comprobantes_json: &str, caea: &str, default_cuit: &str, py: Python<'_>) -> PyResult<String>` | `caea_engine.build_det_list(comprobantes, caea, cuit)` | Released via `py.detach()` |

### FFI Boundary

```
Python side:
  comprobantes: list[dict]  →  json.dumps()  →  comprobantes_json: &str
  caea: str                                  →  caea: &str
  self.cuit: str                             →  default_cuit: &str

Rust side:
  Parse JSON → Vec<ComprobanteInput>
  Build Vec<FECAEADetRequest>
  Serialize → JSON string

Python side:
  json.loads(result)  →  det_list: list[dict]  →  used in fe_det_req
```

### Cargo.toml Addition

```toml
chrono = "0.4"
# serde, serde_json already from SPEC-023
# rust_decimal already from SPEC-019
```

## Serde Struct Design

### Input (deserialized from Python JSON)

```rust
#[derive(Deserialize)]
struct ComprobanteInput {
    concepto: i32,
    doc_tipo: i32,
    doc_nro: i64,
    cbte_desde: i64,
    cbte_hasta: i64,
    cbte_fch: String,          // YYYYMMDD — passthrough
    imp_total: String,         // Decimal-as-string
    imp_tot_conc: String,
    imp_neto: String,
    imp_op_ex: String,
    imp_trib: String,
    imp_iva: String,
    #[serde(default = "default_mon_id")]
    mon_id: String,            // default "PES"
    #[serde(default = "default_mon_cotiz")]
    mon_cotiz: String,         // default "1"

    // Optional nested arrays
    #[serde(default)]
    alic_iva: Option<Vec<AlicIvaInput>>,
    #[serde(default)]
    tributos: Option<Vec<TributoInput>>,
    #[serde(default)]
    cbtes_asoc: Option<Vec<CbteAsocInput>>,

    // Service dates (Concepto 2 or 3)
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
    cuit: Option<String>,  // Falls back to default_cuit parameter
}
```

### Output (serialized to JSON for Python)

```rust
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

    // Conditional fields
    #[serde(skip_serializing_if = "Option::is_none")]
    fch_serv_desde: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    fch_serv_hasta: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    fch_vto_pago: Option<String>,

    // Nested optional arrays
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
```

## Dispatcher Pattern (caea_engine.py)

Follows `sync_engine.py` (SPEC-023) pattern exactly:

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
    """Build the FECAEADetRequest list for a CAEA batch.

    Routes to Rust when batch size > _RUST_BATCH_THRESHOLD and
    extension is available. Falls back to Python otherwise.
    """
    if _USE_RUST and len(comprobantes) > _RUST_BATCH_THRESHOLD:
        return _build_rust(comprobantes, caea, default_cuit)
    return _build_python(comprobantes, caea, default_cuit)
```

## FFI Boundary Analysis

| Input | Typical Size | FFI Overhead | Python Work | Rust Work | Net Gain |
|-------|-------------|-------------|-------------|-----------|----------|
| 10 comprobantes (~20KB) | ~20KB | ~30-50us | ~1-2ms | ~0.5-1ms | ~0.5-1ms (marginal) |
| 50 comprobantes (~100KB) | ~100KB | ~50-100us | ~5-10ms | ~1-3ms | **+2-7ms** |
| 100 comprobantes (~200KB) | ~200KB | ~100-200us | ~10-20ms | ~2-5ms | **+5-15ms** |

## Critical Caveats

1. **Below 10 comprobantes, FFI overhead negates gain**: Guard with `_RUST_BATCH_THRESHOLD = 10` — use Rust only when `len(comprobantes) > 10`.
2. **CAEA-specific only**: CAE (per-invoice authorization) processes single comprobantes — not worth Rust.
3. **Date formatting**: ARCA expects `YYYYMMDD` strings. Input dates arrive as strings already formatted — **passthrough only**, no chrono parsing needed for `cbte_fch`. However, `FchServDesde`/`FchServHasta`/`FchVtoPago` also arrive as pre-formatted strings. Chrono is needed only for any future date validation or generation.
4. **SOAP dict key names are EXACT**: `ImpIVA` (not `ImpIva`), `CAEA` (not `Caea`). Use explicit `#[serde(rename = "...")]` attributes. Any key name mismatch = ARCA rejection.
5. **AlicIva + Tributo nested structure**: `{"Iva": {"AlicIva": [...]}}` and `{"Tributos": {"Tributo": [...]}}` — two levels of nesting with specific wrapper keys.
6. **Tributos guard**: Only include `Tributos` when `tributos` is present AND `imp_trib > 0` (matching Python behavior).
7. **CbtesAsoc CUIT fallback**: When `cuit` is absent in a `CbteAsoc` item, use `default_cuit` parameter (which is `self.cuit` from `CAEAService`).
8. **f64 precision**: Python `float("123.45")` and Rust `"123.45".parse::<f64>()` produce identical IEEE 754 values. No precision issues expected for ARCA amounts (2 decimal places max).
9. **PascalCase output keys**: Most output keys use PascalCase (`CbteDesde`, `DocTipo`), but some are ALL-CAPS (`CAEA`, `ImpIVA`). Use per-field `#[serde(rename)]` for exceptions.

## Integration Point in caea.py

The modification to `caea.py` is minimal — replace the inner loop with a dispatcher call:

```python
# BEFORE (lines 231-304):
det_list = []
for cbte in comprobantes:
    ...
fe_det_req = {"FECAEADetRequest": det_list}

# AFTER:
from .caea_engine import build_det_list

det_list = build_det_list(comprobantes, caea, self.cuit)
fe_det_req = {"FECAEADetRequest": det_list}
```

The outer `fe_cab_req`, SOAP call, response parsing, and error handling remain UNCHANGED.

## Success Criteria

1. `cargo test` passes with >= 10 ARCA batch tests (empty arrays, single, small batch, large batch, service dates, IVA, tributos, cbtes_asoc, mixed, edge cases)
2. Parity test: Python fallback and Rust produce identical JSON output for same input
3. Output matches exact zeep SOAP dict structure (key names, nesting, types)
4. Decimal-to-float conversion matches Python `float()` output for all ARCA amount fields
5. Batch of 50 comprobantes builds in < 5ms (Rust path)
6. Threshold guard: batches <= 10 fall back to Python
7. Fallback works without Rust extension (`_USE_RUST = False`)
8. Docker builds with ARCA batch function available and importable
9. Full test suite passes with 0 regressions (including existing `test_caea.py`)

## Test File Location

```
backend/tests/rust_integration/test_arca_024.py   # Parity + benchmark + fallback tests
```

Follows established pattern from SPEC-018 through SPEC-023.

## Reference Documents

| Document | Purpose | Path |
|----------|---------|------|
| Roadmap | OPP-007 details | `Docs/Brainstorming/rust-pyo3-speckit-roadmap.md` section 10 |
| Acceleration opps | Deep analysis | `Docs/Brainstorming/rust-acceleration-opportunities.md` |
| Current CAEA | Python implementation | `backend/apps/facturacion/arca/caea.py` |
| Invoice skill | ARCA patterns | `skills/gravitea-invoice/SKILL.md` |
| ARCA RAG | Qdrant collections | `arca_api_specs`, `arca_dev_guides` |
| Dispatcher template | sync_engine.py | `backend/apps/sync/sync_engine.py` |
| Rust module registry | lib.rs | `rust/gravitea-core/src/lib.rs` |
| Type stubs | .pyi pattern | `backend/gravitea_rust.pyi` |
| Constants | CbteTipo, AlicIvaId | `backend/apps/facturacion/constants.py` |

## GitNexus Blast Radius Analysis

| Check | Result |
|-------|--------|
| `impact(informar_comprobantes, upstream)` | **LOW** — 0 affected symbols, 0 processes, 0 modules |
| `context(CAEAService)` | Incoming calls: `solicitar` + `sin_movimiento` (views.py) |
| `context(informar_comprobantes)` | Outgoing: `track_soap_call`, `_auth_dict`, `_parse_informar_response`, `ARCARequestError` |
| Process flows | `proc_178`: Informar_comprobantes -> CAEAInformarResult (3 steps) |
| Conclusion | Inner loop replacement is **safe** — no upstream callers affected, output structure consumed only by zeep SOAP call |
