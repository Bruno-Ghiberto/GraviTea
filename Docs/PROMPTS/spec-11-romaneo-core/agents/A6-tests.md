---
agent: A6
role: "Test Suite"
agent_type: "quality-engineer"
model: "sonnet"
spec: "011"
wave: 4
depends_on: [A1, A2, A3, A4, A5]
---

# Agent A6: Test Suite

## Mission

Write the comprehensive test suite for spec-11 covering all models, state machine
transitions, immutability enforcement, merma calculation correctness (with
hand-calculated reference vectors), API integration tests, Rust-Python parity,
quality analysis lifecycle, and tenant isolation. Minimum 40 tests with 90%+ line
coverage on new code.

## Context Files (read FIRST)

- `Docs/PROMPTS/spec-11-romaneo-core/11-implement.md` -- orchestrator context, testing protocol
- `Docs/PROMPTS/spec-11-romaneo-core/11-specify.md` -- acceptance criteria AC-011-001 through AC-011-014
- `Docs/PROMPTS/spec-11-romaneo-core/11-plan.md` -- code patterns (Pattern 12 for test fixtures), test categories table, test execution commands
- `specs/011-romaneo-core/spec.md` -- user stories, acceptance scenarios
- `specs/011-romaneo-core/tasks.md` -- task assignments T036-T042

**Reference files (read for existing patterns):**

- `backend/tests/acopio/conftest.py` -- existing spec-10 fixtures (grain_type_factory, campana_factory, seed_grain_types)
- `backend/tests/conftest.py` -- root fixtures (tenant_context, other_tenant, authenticated_client, admin_user)

## Assigned Tasks

| Task | Description |
|------|-------------|
| T036 | Update `backend/tests/acopio/conftest.py` with romaneo fixtures |
| T037 | Create model unit tests in `backend/tests/acopio/test_romaneo_models.py` |
| T038 | Create QA tests in `backend/tests/acopio/test_quality_analysis.py` |
| T039 | Create merma correctness tests in `backend/tests/acopio/test_merma_calculation.py` |
| T040 | Create Rust FFI parity tests in `backend/tests/acopio/test_merma_rust.py` |
| T041 | Create API integration tests in `backend/tests/acopio/test_romaneo_api.py` |
| T042 | Run full test suite via `scripts/run-tests-external.sh` and verify results |

## Files to Create

```
backend/tests/acopio/test_romaneo_models.py
backend/tests/acopio/test_quality_analysis.py
backend/tests/acopio/test_merma_calculation.py
backend/tests/acopio/test_merma_rust.py
backend/tests/acopio/test_romaneo_api.py
```

## Files to Modify

- `backend/tests/acopio/conftest.py` -- add romaneo fixtures (factories, state helpers)

---

## Domain Knowledge

### Critical Domain Facts

#### Reference Test Vectors

**Trigo reference vector (Hi=15.2%, Hf=13.5%):**

- peso_neto_bruto_kg = 30000.000
- humedad_pct (Hi) = 15.2
- hf_secado_pct (Hf) = 13.5
- materias_extranas_pct = 1.8
- zarandeo_deduction_pct = 1.00
- manipuleo_fijo_pct = 0.10
- volatil_fijo_pct = 0.30
- Expected: secado > 0, manipuleo applied, all 4 deductions active
- Hand-calculate each intermediate step to verify

**Soja dry case (Hi=12.0%, Hf=12.5%):**

- Hi <= Hf, therefore secado_pct = 0.00
- manipuleo NOT applied (because no drying occurred)
- Only zarandeo and volatil deductions applied

**Hf vs humedad_base assertion:**

- For trigo: Hf=13.5%, humedad_base=14.0%
- Calculate peso_final using Hf=13.5% (correct)
- Calculate peso_final using Hf=14.0% (wrong)
- The difference must be approximately 168 kg on a 30-tonne truck
- This test documents the error magnitude

#### State Machine Transition Tests

Valid transitions (6 total):
1. PENDIENTE -> EN_PROCESO
2. EN_PROCESO -> PESADO
3. PESADO -> ANALIZADO
4. ANALIZADO -> CONFORME
5. CONFORME -> CERRADO

Invalid transitions (test all rejections):
1. PENDIENTE -> PESADO (skip EN_PROCESO)
2. PENDIENTE -> ANALIZADO (skip 2 states)
3. EN_PROCESO -> ANALIZADO (skip PESADO)
4. EN_PROCESO -> CONFORME (skip 2 states)
5. CERRADO -> anything (terminal state)

#### Immutability Tests

CONFORME gate:
- Try changing `grain_type` on CONFORME romaneo -> ValueError
- Try changing `peso_bruto_kg` on CONFORME romaneo -> ValueError
- Allowed: changing `tara_kg`, `peso_neto_bruto_kg`, `ts_tara`, `status` to CERRADO

CERRADO gate:
- Try changing ANY field -> ValueError (fully immutable terminal state)

MermaCalculation immutability:
- Create MermaCalculation, then try `save()` again -> ValueError
- Try `delete()` -> ValueError

---

## Key Patterns

### Pattern 12: Test Fixtures (conftest.py Updates)

See 11-plan.md Pattern 12 for the complete fixture code. Add these fixtures to
`backend/tests/acopio/conftest.py`:

- `merma_table_factory(db)` -- factory for MermaTable instances
- `tolerance_table_factory(db)` -- factory for ToleranceTable instances
- `romaneo_factory(tenant_context, grain_type_factory, campana_factory, user_factory)` -- factory for Romaneo in PENDIENTE
- `romaneo_en_proceso(romaneo_factory)` -- romaneo advanced to EN_PROCESO
- `romaneo_pesado(romaneo_en_proceso)` -- romaneo advanced to PESADO with peso_bruto
- `romaneo_analizado(romaneo_pesado, quality_analysis_factory)` -- romaneo advanced to ANALIZADO with QA
- `romaneo_conforme(romaneo_analizado)` -- romaneo advanced to CONFORME with MermaCalculation
- `quality_analysis_factory(tenant_context)` -- factory for QualityAnalysis instances

NOTE: The `user_factory` fixture should be checked in the root `conftest.py`.
If it does not exist, create a minimal fixture that creates a Django user for
the `operator_id` FK.

### External Test Runner Protocol

NEVER run pytest directly inside Claude Code. ALWAYS use `scripts/run-tests-external.sh`:

```bash
# Run all acopio tests
bash scripts/run-tests-external.sh -n spec11 tests/acopio/

# Check results
cat Docs/Tests/spec11.status     # PASSED | FAILED | RUNNING
cat Docs/Tests/spec11.summary    # ~20 lines
grep "FAILED" Docs/Tests/spec11.log  # Only if FAILED

# Run specific test files
bash scripts/run-tests-external.sh -n spec11-models tests/acopio/test_romaneo_models.py
bash scripts/run-tests-external.sh -n spec11-api tests/acopio/test_romaneo_api.py
bash scripts/run-tests-external.sh -n spec11-merma tests/acopio/test_merma_calculation.py
bash scripts/run-tests-external.sh -n spec11-rust tests/acopio/test_merma_rust.py
```

---

## Test Categories and Estimated Counts

### test_romaneo_models.py (12-15 tests)

| Test | What It Verifies | AC |
|------|-----------------|-----|
| test_romaneo_creation_all_fields | 31 fields populated correctly | AC-011-001 |
| test_romaneo_number_auto_generation | ROM-YYYY-NNNNN format per branch | AC-011-011 |
| test_romaneo_number_sequential_per_branch | Branch-independent numbering | AC-011-011 |
| test_valid_transition_pendiente_to_en_proceso | Linear state machine | AC-011-002 |
| test_valid_transition_en_proceso_to_pesado | Linear state machine | AC-011-002 |
| test_valid_transition_pesado_to_analizado | Linear state machine | AC-011-002 |
| test_valid_transition_analizado_to_conforme | Linear state machine | AC-011-002 |
| test_valid_transition_conforme_to_cerrado | Linear state machine | AC-011-002 |
| test_invalid_transition_skip_state | Rejects PENDIENTE -> PESADO | AC-011-002 |
| test_invalid_transition_cerrado_terminal | Rejects any change after CERRADO | AC-011-002 |
| test_conforme_immutability_blocks_field_change | ValueError on field change | AC-011-003 |
| test_conforme_allows_tare_capture | tara_kg allowed at CONFORME | AC-011-003 |
| test_cerrado_fully_immutable | ValueError on any change | AC-011-003 |
| test_timestamp_set_on_transition | ts_entrada, ts_pesada_bruta, etc. | AC-011-012 |

### test_quality_analysis.py (5-7 tests)

| Test | What It Verifies | AC |
|------|-----------------|-----|
| test_qa_creation_all_parameters | 9+ parameters at correct precision | AC-011-004 |
| test_qa_one_to_one_constraint | IntegrityError on duplicate | AC-011-004 |
| test_qa_grain_specific_nullable | hectolitre cereals, protein trigo, green soja | AC-011-004 |
| test_qa_update_allowed_in_analizado | Update succeeds when ANALIZADO | AC-011-004 |
| test_qa_update_blocked_in_conforme | 409 when CONFORME | AC-011-004 |

### test_merma_calculation.py (8-10 tests)

| Test | What It Verifies | AC |
|------|-----------------|-----|
| test_trigo_reference_vector | All intermediates match hand-calculated values | AC-011-006 |
| test_soja_dry_case | secado=0, manipuleo NOT applied | AC-011-006 |
| test_all_zero_parameters | Only volatil applied | AC-011-006 |
| test_hf_vs_humedad_base_error | ~168 kg error documented | AC-011-008 |
| test_merma_immutability_save | ValueError on update attempt | AC-011-005 |
| test_merma_immutability_delete | ValueError on delete attempt | AC-011-005 |
| test_tolerance_table_version_pinning | Table update does not change grade | AC-011-013 |
| test_merma_band_not_found | Clear error for unmatched ME% | AC-011-006 |

### test_merma_rust.py (5-8 tests)

| Test | What It Verifies | AC |
|------|-----------------|-----|
| test_rust_python_parity_trigo | Identical results for trigo vector | AC-011-007 |
| test_rust_python_parity_soja | Identical results for soja vector | AC-011-007 |
| test_rust_python_parity_maiz | Identical results for maiz vector | AC-011-007 |
| test_rust_python_parity_girasol | Identical results for girasol vector | AC-011-007 |
| test_rust_python_parity_sorgo | Identical results for sorgo vector | AC-011-007 |
| test_rust_python_parity_cebada | Identical results for cebada vector | AC-011-007 |
| test_rust_error_invalid_json | Error on malformed JSON | AC-011-007 |
| test_rust_error_negative_weight | Error on negative peso | AC-011-007 |

### test_romaneo_api.py (12-15 tests)

| Test | What It Verifies | AC |
|------|-----------------|-----|
| test_create_romaneo_201 | POST creates romaneo with auto-number | AC-011-010 |
| test_list_romaneos_200_paginated | GET returns paginated list | AC-011-010 |
| test_retrieve_romaneo_nested_qa_mc | GET detail includes QA + MC | AC-011-010 |
| test_patch_pendiente_200 | PATCH allowed on PENDIENTE | AC-011-010 |
| test_patch_conforme_409 | PATCH blocked on CONFORME | AC-011-003, AC-011-010 |
| test_confirmar_arribo_202 | POST action returns 202 | AC-011-010 |
| test_peso_bruto_200 | POST sets peso_bruto, transitions to PESADO | AC-011-010 |
| test_analizar_200 | POST creates QA, transitions to ANALIZADO | AC-011-010 |
| test_confirmar_200 | POST triggers merma, transitions to CONFORME | AC-011-010 |
| test_tara_200 | POST captures tare, computes net weight | AC-011-010 |
| test_cerrar_202 | POST transitions to CERRADO | AC-011-010 |
| test_merma_preview_200 | GET returns projected values without DB record | AC-011-010 |
| test_invalid_state_transition_409 | Wrong state returns 409 with type/current/attempted | AC-011-002 |
| test_tenant_isolation_404 | Cross-tenant access returns 404 | AC-011-009 |

**Total estimated: 42-55 tests (minimum 40 required).**

---

## Constraints

- NEVER run pytest directly inside Claude Code -- ALWAYS use `scripts/run-tests-external.sh`.
- All test functions must have descriptive names following `test_{what}_{expected}` pattern.
- Each test must be independent -- no test should depend on the execution order of other tests.
- Use factories from conftest.py for model creation -- never hardcode model construction in tests.
- API integration tests must use `authenticated_client` fixture from root conftest.
- Tenant isolation tests must use `other_tenant` and `other_tenant_client` fixtures.
- Merma parity tests must import both Rust and Python implementations and compare outputs.
- Merma parity tests should use `pytest.importorskip("gravitea_rust")` if Rust may not be available.
- All function parameters and return values must have type hints.
- Use `.venv/bin/python` for all Python commands, never system python.

---

## Checkpoint

**Gate 4 (Tests)** -- run after completing all tasks:

```bash
# 1. Run all acopio tests
bash /home/brunoghiberto/Documents/Projects/GraviTea/scripts/run-tests-external.sh \
    -n spec11-verify tests/acopio/

# 2. Poll for completion (repeat until not RUNNING)
cat /home/brunoghiberto/Documents/Projects/GraviTea/Docs/Tests/spec11-verify.status

# 3. Read summary when status is PASSED or FAILED
cat /home/brunoghiberto/Documents/Projects/GraviTea/Docs/Tests/spec11-verify.summary

# 4. If FAILED, debug specific failures
grep "FAILED" /home/brunoghiberto/Documents/Projects/GraviTea/Docs/Tests/spec11-verify.log
```

**Pass criteria**: `.status` reads `PASSED`. Summary shows 0 failures, 0 errors.
Minimum 40 tests collected. 90%+ coverage on new code. If FAILED, fix failures
and re-run.
