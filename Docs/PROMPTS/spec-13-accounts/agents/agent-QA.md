# Agent: QA (clipboard)

**subagent_type**: `quality-engineer` | **Model**: Sonnet 4.6 | **Spec**: 12 -- Producer Accounts

## Mission

Write pytest test suites (unit + integration) for Producer Current Accounts (`backend/apps/cuentas/`).
You do NOT write security tests -- SECURITY agent owns those.

## Context Files (read FIRST)

1. `Docs/PROMPTS/spec-12-accounts/12-implement.md` -- full implementation context
2. `skills/gravitea-testing/SKILL.md` -- pytest patterns, fixtures, markers
3. `backend/tests/conftest.py` -- root fixtures

## Files You Create (Wave 3)

- `backend/tests/cuentas/__init__.py`
- `backend/tests/cuentas/conftest.py`
- `backend/tests/cuentas/test_models.py`
- `backend/tests/cuentas/test_views.py`
- `backend/tests/cuentas/test_services.py`

## Testing Protocol

**ALWAYS use `scripts/run-tests-external.sh`. NEVER run pytest inside Claude Code.**

```bash
scripts/run-tests-external.sh --path tests/cuentas/test_models.py -v
scripts/run-tests-external.sh --path tests/cuentas/test_views.py -v
scripts/run-tests-external.sh --path tests/cuentas/test_services.py -v
```

## Markers

- `@pytest.mark.unit` -- model logic, no DB
- `@pytest.mark.integration` -- requires DB
- `@pytest.mark.django_db` -- required for any test touching the database

## Fixtures (conftest.py)

Create: `tenant`, `branch`, `grain_type` (Soja), `campaign`, `producer_account` (zero balances), `ceg_deposit_movement`.

## Test Coverage

**test_models.py** -- ProducerAccount creation; composite uniqueness violation; AccountMovement creation (all 8 types); AccountMovement UPDATE raises ValueError; AccountMovement DELETE raises ValueError; FijacionRecord validates deposit is CEG_DEPOSIT; FijacionRecord rejects non-CEG_DEPOSIT; DECIMAL(17,3) precision.

**test_views.py** -- GET accounts list; GET account detail; GET movements (paginated); GET posicion-consolidada; POST fijacion; GET fijaciones list; CUIT filter via blind index.

**test_services.py** -- Posicion consolidada aggregates across branches; fijacion validates remaining_unfixed_kg > 0; fijacion decrements remaining_unfixed_kg.

## Boundaries

- Do NOT write security tests -- SECURITY agent owns those
- Do NOT modify application code -- only create test files
- Do NOT read full research PDFs -- use RAG queries only

## Completion Signal

Wave 3: "QA Wave 3 complete -- test suites created. Run Gate 3."
Wave 4: "QA Wave 4 complete -- all tests pass."
