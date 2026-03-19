---
agent: A3
role: "Python Merma Service"
agent_type: "python-expert"
model: "sonnet"
spec: "011"
wave: 2
depends_on: [A1, A2]
---

# Agent A3: Python Merma Service

## Mission

Create the Python merma calculation service in
`backend/apps/acopio/services/merma_engine.py` that wraps the Rust FFI call with
a pure-Python fallback, implements MermaTable lookup logic for zarandeo deduction
bands, and provides the merma preview API consumed by the views layer. This service
is the bridge between the Rust computation engine and the Django application.

## Context Files (read FIRST)

- `Docs/PROMPTS/spec-11-romaneo-core/11-implement.md` -- orchestrator context
- `Docs/PROMPTS/spec-11-romaneo-core/11-specify.md` -- FR-011-005 (Rust engine), FR-011-009 (merma preview), calculation rules
- `Docs/PROMPTS/spec-11-romaneo-core/11-plan.md` -- code patterns (Pattern 9)
- `specs/011-romaneo-core/spec.md` -- user stories US4 (merma calculation), US5 (preview), US7 (grading)
- `specs/011-romaneo-core/tasks.md` -- task assignments T014, T031

## Assigned Tasks

| Task | Description |
|------|-------------|
| T014 | Create `backend/apps/acopio/services/merma_engine.py` with: `try/except ImportError` Rust FFI wrapper, `_python_calculate_merma()` pure-Python fallback, `calculate_merma_deductions()` public API function |
| T031 | Add merma service integration: MermaTable lookup by grain_type + materias_extranas_pct + ts_entrada, input JSON construction, and `calculate_merma_deductions()` enhancement |

## Files to Create

```
backend/apps/acopio/services/merma_engine.py
```

## Files to Modify

None -- this is a new file only.

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

.venv/bin/python scripts/qdrant/qdrant_search.py \
    -q "merma table zarandeo deduction bands foreign matter lookup" -l 5
```

### Critical Domain Facts

#### Sequential Merma Formula

See A2-rust.md Domain Knowledge for the full formula. The Python fallback must
implement the IDENTICAL formula using `decimal.Decimal` for precision parity.

```
Step 1 -- Zarandeo:    peso_post_zarandeo  = peso_neto_bruto * (1 - %Z / 100)
Step 2 -- Secado:      peso_post_secado    = peso_post_zarandeo * (1 - %S / 100)
Step 3 -- Manipuleo:   peso_post_manipuleo = peso_post_secado * (1 - %M / 100)
Step 4 -- Volatil:     peso_final          = peso_post_manipuleo * (1 - %V / 100)
```

#### Secado Formula

```
if Hi > Hf:
    %S = (Hi - Hf) / (100 - Hf) * 100
else:
    %S = 0
```

- `Hi` = `QualityAnalysis.humedad_pct`
- `Hf` = `GrainType.hf_secado_pct` (NOT `humedad_base_pct`)
- Manipuleo applied ONLY when secado > 0

#### CRITICAL: Hf vs humedad_base

For trigo: Hf = 13.5%, base = 14.0%. Using the wrong field yields approximately
168 kg error per 30-tonne truck. The service MUST explicitly use `hf_secado_pct`.

#### MermaTable Lookup Logic

The zarandeo deduction percentage is NOT a fixed value -- it comes from MermaTable
bands that map foreign matter ranges to deduction percentages:

1. Query MermaTable filtered by `grain_type` and where `valid_to IS NULL` (active version).
2. Pin the version to the one active at `ts_entrada` (romaneo arrival timestamp):
   `valid_from <= ts_entrada` AND (`valid_to IS NULL` OR `valid_to > ts_entrada`).
3. Find the band where `materias_extranas_from_pct <= QA.materias_extranas_pct`
   AND (`materias_extranas_to_pct > QA.materias_extranas_pct` OR `materias_extranas_to_pct IS NULL`).
4. If no matching band found, raise a clear error (do NOT silently default to zero).

#### Tolerance Table Version Pinning

The tolerance table version active at `ts_entrada` is stored on the romaneo. Query:
`ToleranceTable.objects.filter(grain_type=grain_type, valid_from__lte=ts_entrada)`
with `valid_to IS NULL` OR `valid_to > ts_entrada`.

---

## Key Patterns

### Pattern 9: Python FFI Wrapper with Fallback

See 11-plan.md Pattern 9 for the complete implementation. Key structure:

```python
try:
    from gravitea_rust import calculate_merma as _rust_calculate_merma
    _USE_RUST = True
except ImportError:
    _USE_RUST = False

def _python_calculate_merma(input_data: dict[str, str]) -> dict[str, str]:
    """Pure-Python reference implementation."""
    # ... identical formula using decimal.Decimal ...

def calculate_merma_deductions(input_data: dict[str, str]) -> dict[str, str]:
    """Public API -- delegates to Rust or Python."""
    if _USE_RUST:
        input_json = json.dumps(input_data)
        result_json = _rust_calculate_merma(input_json)
        return json.loads(result_json)
    return _python_calculate_merma(input_data)
```

### Additional Functions to Implement

Beyond the base FFI wrapper from Pattern 9, implement these functions:

```python
def lookup_zarandeo_deduction(
    grain_type_id: str,
    materias_extranas_pct: Decimal,
    ts_entrada: datetime,
) -> tuple[Decimal, MermaTable]:
    """
    Look up the zarandeo deduction band from MermaTable.

    Returns (zarandeo_deduction_pct, merma_table_instance).
    Raises ValueError if no matching band found.
    """

def build_merma_input(
    romaneo: "Romaneo",
    quality_analysis: "QualityAnalysis",
    merma_table: "MermaTable",
) -> dict[str, str]:
    """
    Construct the input dict for calculate_merma_deductions() from
    Django model instances. Uses GrainType.hf_secado_pct (NOT humedad_base_pct).
    """

def preview_merma(romaneo: "Romaneo") -> dict[str, str]:
    """
    Non-persisting merma preview. Looks up MermaTable, constructs input,
    runs calculation, returns projected deductions without creating any record.
    Raises ValueError if romaneo has no quality analysis.
    """
```

---

## Constraints

- All calculations must use `decimal.Decimal`, never `float`.
- The Python fallback must produce results IDENTICAL to the Rust implementation for the same inputs.
- `_python_calculate_merma()` must be a standalone function that takes a dict of string values and returns a dict of string values (same interface as the Rust function).
- MermaTable lookup must pin the version to `ts_entrada`, not current time.
- If no matching MermaTable band is found, raise `ValueError` with a clear message including the grain type and foreign matter percentage.
- The `build_merma_input()` function must explicitly use `GrainType.hf_secado_pct`, NOT `humedad_base_pct`.
- All function parameters and return values must have type hints.
- Use `.venv/bin/python` for all Python commands, never system python.

---

## Checkpoint

**Gate 2 (Merma Service)** -- run after completing all tasks:

```bash
cd /home/brunoghiberto/Documents/Projects/GraviTea/backend && \
../.venv/bin/python -c "
from apps.acopio.services.merma_engine import calculate_merma_deductions
result = calculate_merma_deductions({
    'peso_neto_bruto_kg': '30000.000',
    'humedad_pct': '15.2',
    'hf_secado_pct': '13.5',
    'materias_extranas_pct': '1.8',
    'zarandeo_deduction_pct': '1.00',
    'manipuleo_fijo_pct': '0.10',
    'volatil_fijo_pct': '0.30',
})
print(f'peso_final_kg: {result[\"peso_final_kg\"]}')
print('Gate 2 (Merma Service): PASS')
"
```

**Pass criteria**: Service returns valid merma result for test vector.
