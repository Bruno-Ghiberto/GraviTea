---
agent: A2
role: "Rust Merma Engine"
agent_type: "general-purpose"
model: "sonnet"
spec: "011"
wave: 1
depends_on: []
---

# Agent A2: Rust Merma Engine

## Mission

Create the Rust merma calculation engine in `rust/gravitea-core/src/merma.rs` with
PyO3 bindings, implementing the sequential merma formula (zarandeo, secado,
manipuleo, volatil) using `rust_decimal` for precision. Register the module in
`lib.rs`, write Rust unit tests, and verify the PyO3 function is callable from
Python.

## Context Files (read FIRST)

- `Docs/PROMPTS/spec-11-romaneo-core/11-implement.md` -- orchestrator context
- `Docs/PROMPTS/spec-11-romaneo-core/11-specify.md` -- FR-011-005 (Rust engine), calculation rules, input/output JSON schemas
- `Docs/PROMPTS/spec-11-romaneo-core/11-plan.md` -- code patterns (Pattern 7, Pattern 8)
- `specs/011-romaneo-core/spec.md` -- user story 4 (merma calculation), AC-011-006, AC-011-007
- `specs/011-romaneo-core/tasks.md` -- task assignments T010-T013

**Reference files (read for existing patterns):**

- `rust/gravitea-core/src/compute.rs` -- serde structs, `parse_decimal`, `decimal_to_string`, `GraviteaError`
- `rust/gravitea-core/src/decimal_utils.rs` -- `parse_decimal()`, `decimal_to_string()`
- `rust/gravitea-core/src/errors.rs` -- `GraviteaError` enum
- `rust/gravitea-core/src/lib.rs` -- PyO3 module registration pattern

## Assigned Tasks

| Task | Description |
|------|-------------|
| T010 | Create `rust/gravitea-core/src/merma.rs` with MermaInput/MermaOutput serde structs, `calculate_merma_internal()`, and `#[pyfunction] pub fn calculate_merma()` PyO3 wrapper |
| T011 | Add `mod merma;` declaration and `#[pymodule_export] use super::merma::calculate_merma;` to `rust/gravitea-core/src/lib.rs` |
| T012 | Add Rust unit tests in `merma.rs` (`#[cfg(test)]` module) covering at least 10 test cases |
| T013 | Build Rust module with `maturin develop --release` and verify `from gravitea_rust import calculate_merma` works from Python |

## Files to Create

```
rust/gravitea-core/src/merma.rs
```

## Files to Modify

- `rust/gravitea-core/src/lib.rs` -- add `mod merma;` and `#[pymodule_export] use super::merma::calculate_merma;`

---

## Domain Knowledge

### RAG Queries (MUST run before writing code)

```bash
.venv/bin/python scripts/qdrant/qdrant_search.py \
    -q "merma zarandeo secado manipuleo volatil calculation formula sequential" -l 5

.venv/bin/python scripts/qdrant/qdrant_search.py \
    -q "secado formula humidity regulatory final moisture hf" -l 5

.venv/bin/python scripts/qdrant/qdrant_search.py \
    -q "manipuleo applied only when secado drying occurs" -l 5
```

### Critical Domain Facts

#### Sequential Merma Formula (Circular CAC 10/86)

Each step operates on the result of the previous step, NOT on the original weight:

```
Step 1 -- Zarandeo:    peso_post_zarandeo  = peso_neto_bruto * (1 - %Z / 100)
Step 2 -- Secado:      peso_post_secado    = peso_post_zarandeo * (1 - %S / 100)
Step 3 -- Manipuleo:   peso_post_manipuleo = peso_post_secado * (1 - %M / 100)
Step 4 -- Volatil:     peso_final          = peso_post_manipuleo * (1 - %V / 100)
```

**Secado formula:**
```
if Hi > Hf:
    %S = (Hi - Hf) / (100 - Hf) * 100
else:
    %S = 0
```

Where:
- `Hi` = `humedad_pct` (measured sample moisture)
- `Hf` = `hf_secado_pct` (REGULATORY final moisture, NOT humedad_base_pct)

**Manipuleo rule:** Applied ONLY when secado > 0 (drying occurred). If no drying,
manipuleo = 0 regardless of the fixed percentage value.

**Volatil rule:** Always applied as the final step.

#### CRITICAL: Hf vs humedad_base

- `Hf = GrainType.hf_secado_pct` -- regulatory final moisture for secado formula
- `humedad_base_pct` -- commercial base moisture (different business meaning)
- For trigo: Hf = 13.5%, base = 14.0%
- Using base instead of Hf yields approximately 168 kg error per 30-tonne truck

#### Input JSON Schema

```json
{
  "peso_neto_bruto_kg": "30000.000",
  "humedad_pct": "15.2",
  "hf_secado_pct": "13.5",
  "materias_extranas_pct": "1.8",
  "zarandeo_deduction_pct": "1.00",
  "manipuleo_fijo_pct": "0.25",
  "volatil_fijo_pct": "0.30"
}
```

#### Output JSON Schema

```json
{
  "zarandeo_pct": "1.00",
  "secado_pct": "1.97",
  "manipuleo_pct": "0.25",
  "volatil_pct": "0.30",
  "peso_post_zarandeo_kg": "29700.000",
  "peso_post_secado_kg": "29116.301",
  "peso_post_manipuleo_kg": "29043.510",
  "peso_final_kg": "28956.379",
  "total_merma_kg": "1043.621",
  "total_factor_pct": "0.9652"
}
```

---

## Key Patterns

### Pattern 7: Rust PyO3 Function with Serde

See 11-plan.md Pattern 7 for the complete implementation including:

- `MermaInput` serde Deserialize struct (all fields as String)
- `MermaOutput` serde Serialize struct (all fields as String)
- `calculate_merma_internal()` function with error handling
- `#[pyfunction] pub fn calculate_merma()` PyO3 wrapper
- Input validation (positive weight, percentage ranges)
- Use `parse_decimal()` from `decimal_utils` for all numeric conversions
- Use `decimal_to_string()` for all output formatting
- Use `GraviteaError` from `errors` for error propagation

### Pattern 8: PyO3 Module Registration

See 11-plan.md Pattern 8. Add to `lib.rs`:

```rust
mod merma;  // After existing mod declarations

// Inside #[pymodule] mod gravitea_rust { ... }:
    #[pymodule_export]
    use super::merma::calculate_merma;
```

---

## Constraints

- ALL numeric calculations must use `rust_decimal::Decimal`, never `f64`.
- Use `dec!()` macro from `rust_decimal_macros` for literal decimal constants.
- All input/output values are string-encoded decimals (JSON string, not number).
- Error handling must use `GraviteaError` variants: `ComputeError` for JSON/calc errors, `InvalidInput` for validation failures.
- Validation rules: `peso_neto_bruto_kg` must be positive, percentage fields must be in range 0-100.
- Function must be deterministic -- same input always produces same output.
- Rust unit tests must cover at least 10 cases (see test scenarios below).
- Do NOT add new dependencies to `Cargo.toml` -- all needed crates are already present.

### Required Rust Unit Tests (T012)

Write these in a `#[cfg(test)]` module within `merma.rs`:

1. **Trigo reference vector**: Hi=15.2%, Hf=13.5%, ME=1.8%, zarandeo=1.0%, manipuleo=0.10%, volatil=0.30%, peso=30000 kg. Verify all intermediate weights and final peso_final.
2. **Soja dry case**: Hi=12.0%, Hf=12.5%. Verify secado=0, manipuleo NOT applied (effective=0), only zarandeo + volatil applied.
3. **Zero foreign matter**: zarandeo_deduction=0.0%. Verify peso_post_zarandeo == peso_neto_bruto.
4. **Hi equals Hf**: Hi=13.5%, Hf=13.5%. Verify secado=0.00, manipuleo NOT applied.
5. **All parameters zero/minimum**: peso=30000, Hi=0, Hf=0, zarandeo=0, manipuleo=0, volatil=0. Verify peso_final == peso_neto_bruto.
6. **Negative weight rejection**: peso=-1000. Expect error.
7. **Invalid JSON rejection**: malformed string. Expect error.
8. **Large weight**: peso=999999.999. Verify calculation completes without overflow.
9. **Maximum humidity**: Hi=99.0%, Hf=13.5%. Verify secado calculation handles high moisture.
10. **Precision verification**: Verify that intermediate steps use full decimal precision (not float truncation).

---

## Checkpoint

**Gate 1 (Rust)** -- run after completing all tasks:

```bash
# 1. Verify Rust builds
cd /home/brunoghiberto/Documents/Projects/GraviTea/rust/gravitea-core && \
cargo build 2>&1 | tail -3

# 2. Verify Rust tests pass
cd /home/brunoghiberto/Documents/Projects/GraviTea/rust/gravitea-core && \
cargo test merma 2>&1 | tail -10

# 3. Build PyO3 module
cd /home/brunoghiberto/Documents/Projects/GraviTea && \
.venv/bin/maturin develop --release -m rust/gravitea-core/Cargo.toml 2>&1 | tail -5

# 4. Verify PyO3 module loads from Python
cd /home/brunoghiberto/Documents/Projects/GraviTea && \
.venv/bin/python -c "from gravitea_rust import calculate_merma; print('Gate 1 (Rust FFI): PASS')"
```

**Pass criteria**: Rust compiles without errors. All unit tests pass. PyO3 function
is importable from Python.
