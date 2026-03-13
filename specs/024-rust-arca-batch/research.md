# Research: ARCA CAEA Batch Builder Acceleration

**Feature Branch**: `024-rust-arca-batch`
**Date**: 2026-02-28
**Status**: Complete — all decisions resolved

## Research Summary

All research topics were resolved during the specify phase via direct source code analysis of `caea.py` (lines 232-302) and GitNexus blast radius checks. No external documentation queries or RAG lookups were needed — the Python source code IS the ground truth for the ARCA SOAP structure.

## Decisions

### R-001: FECAEARegInformativo Dict Structure

**Decision**: Complete field mapping extracted directly from `caea.py:232-302`.

**Rationale**: The Python inner loop defines the exact dict structure that zeep sends to ARCA. This is the authoritative source — not ARCA documentation, which may describe the WSDL abstractly. The Rust function must produce byte-identical output to the Python loop.

**Alternatives considered**:
- Qdrant RAG query for `arca_api_specs` collection → Rejected: source code is more precise than documentation
- ARCA WSDL parsing → Rejected: zeep already handles WSDL; we need the dict structure zeep expects, not raw WSDL types

**Evidence**: `caea.py` lines 232-302 show 15 top-level keys, 3 conditional nested sections (Iva, Tributos, CbtesAsoc), and 3 conditional service date fields.

### R-002: Date Formatting Approach

**Decision**: String passthrough — no `chrono` crate needed.

**Rationale**: All date fields in the CAEA batch arrive as pre-formatted YYYYMMDD strings from the caller. The inner loop copies them directly without any parsing or formatting:
- `det["CbteFch"] = cbte["cbte_fch"]` (line 239)
- `det["FchServDesde"] = cbte["fch_serv_desde"]` (line 253)
- `det["FchServHasta"] = cbte["fch_serv_hasta"]` (line 254)
- `det["FchVtoPago"] = cbte["fch_vto_pago"]` (line 255)

**Alternatives considered**:
- `chrono 0.4` for date validation/formatting → Rejected: spec Assumptions section explicitly states "no date parsing or validation is performed by the batch builder"
- Custom date validation → Rejected: caller responsibility per spec

**Impact**: Zero new Cargo dependencies for this feature.

### R-003: Amount String-to-Float Precision

**Decision**: Use `str::parse::<f64>()` — no `rust_decimal` crate needed.

**Rationale**: The Python code converts amounts with `float()`, which produces IEEE 754 f64 values. Rust's `str::parse::<f64>()` produces identical IEEE 754 values for the same input string. ARCA amounts have at most 2 decimal places (per spec Assumptions), so there is no precision loss concern.

**Alternatives considered**:
- `rust_decimal::Decimal::to_f64()` → Rejected: unnecessary intermediate step. Input is string, output needs f64. Direct parse is correct and simpler.
- `f64::from_str()` with custom error handling → Rejected: `str::parse::<f64>()` already provides `Result<f64, ParseFloatError>`

**Evidence**: Instruction-specify.md caveat #8: "Python `float('123.45')` and Rust `'123.45'.parse::<f64>()` produce identical IEEE 754 values."

### R-004: Zeep Dict Key Names

**Decision**: 15 top-level keys documented in spec FR-005, nested keys in FR-008/FR-009/FR-010. Complete key mapping:

| Python key (output) | Serde rename | Notes |
|---------------------|-------------|-------|
| `Concepto` | PascalCase auto | — |
| `DocTipo` | PascalCase auto | — |
| `DocNro` | PascalCase auto | — |
| `CbteDesde` | PascalCase auto | — |
| `CbteHasta` | PascalCase auto | — |
| `CbteFch` | PascalCase auto | — |
| `ImpTotal` | PascalCase auto | — |
| `ImpTotConc` | PascalCase auto | — |
| `ImpNeto` | PascalCase auto | — |
| `ImpOpEx` | PascalCase auto | — |
| `ImpTrib` | PascalCase auto | — |
| `ImpIVA` | `#[serde(rename = "ImpIVA")]` | ALL-CAPS exception |
| `MonId` | PascalCase auto | — |
| `MonCotiz` | PascalCase auto | — |
| `CAEA` | `#[serde(rename = "CAEA")]` | ALL-CAPS exception |

**Rationale**: Extracted from caea.py source code. Two keys require explicit rename overrides because `#[serde(rename_all = "PascalCase")]` would produce `ImpIva` and `Caea` — both wrong.

**Alternatives considered**: None — key names are dictated by ARCA WSDL and cannot be changed.

### R-005: CbteAsoc CUIT Fallback

**Decision**: Use `default_cuit` parameter passed from `CAEAService.informar_comprobantes()` as `self.cuit`.

**Rationale**: `caea.py:296` shows `item.get("cuit", self.cuit)`. Since the Rust function and dispatcher are standalone (not methods on CAEAService), the caller must pass `self.cuit` explicitly as `default_cuit`. The dispatcher signature is: `build_det_list(comprobantes, caea, default_cuit)`.

**Alternatives considered**:
- Thread `CAEAService` instance into Rust → Rejected: unnecessary complexity, breaks FFI boundary
- Require CUIT on every CbteAsoc item → Rejected: breaks backward compatibility with existing callers

### R-006: Empty `alic_iva` Array Handling

**Decision**: Treat `[]` as absent — omit IVA section entirely.

**Rationale**: Python truthy check `if alic_iva:` (caea.py:259) evaluates `[]` as falsy. Rust must replicate: check `!vec.is_empty()` before wrapping in `IvaWrapper`. The serde `#[serde(skip_serializing_if = "Option::is_none")]` handles omission when the wrapper is `None`.

**Alternatives considered**: None — must match Python behavior exactly (FR-017).
