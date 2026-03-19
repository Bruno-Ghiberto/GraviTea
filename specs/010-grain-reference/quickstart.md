# Quickstart: Grain Reference Data

**Feature**: 010-grain-reference | **Date**: 2026-03-18

## Prerequisites

- Python 3.14.3 with venv at `.venv/`
- PostgreSQL 18.1 running
- Backend dependencies installed (`pip install -r requirements.txt`)
- Django migrations up to date

## Setup

```bash
# 1. Apply the new acopio migration
cd backend && ../.venv/bin/python manage.py migrate gravitea_acopio

# 2. Load seed data (grain types, tolerances, merma bands)
cd backend && ../.venv/bin/python manage.py seed_grain_reference

# 3. Verify (optional — preview mode)
cd backend && ../.venv/bin/python manage.py seed_grain_reference --dry-run
```

## Quick Verification

```bash
# Check grain types loaded
cd backend && ../.venv/bin/python -c "
from apps.acopio.models import GrainType
print(f'Grain types: {GrainType.objects.count()}')
for g in GrainType.objects.all():
    print(f'  {g.code} (ARCA {g.arca_codigo}): {g.name}')
"

# Check API endpoints (requires running server + valid JWT)
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/acopio/grain-types/
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/acopio/tolerance-tables/
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/acopio/merma-tables/
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/acopio/campaigns/
```

## Running Tests

```bash
# ALWAYS use the external test runner (never pytest inside Claude Code)
bash scripts/run-tests-external.sh -n spec10 tests/acopio/

# Check results
cat Docs/Tests/spec10.status    # PASSED | FAILED | RUNNING
cat Docs/Tests/spec10.summary   # ~20 lines with counts and failures
```

## Key Files

| File | Purpose |
|------|---------|
| `backend/apps/acopio/models/` | 4 Django models |
| `backend/apps/acopio/fixtures/` | 3 seed data files (JSON) |
| `backend/apps/acopio/management/commands/seed_grain_reference.py` | Idempotent loader |
| `backend/apps/acopio/serializers/reference_data.py` | 4 DRF serializers |
| `backend/apps/acopio/views/reference_data.py` | 4 DRF viewsets |
| `backend/apps/acopio/urls.py` | Router registration |
| `backend/database/sql/acopio_rls.sql` | RLS policy (CampanaConfig only) |
| `backend/tests/acopio/` | Test suite (20+ tests) |

## Agent Execution

This spec uses 4 agents in a tmux layout. See `Docs/PROMPTS/spec-10-grain-reference/10-plan.md` for:
- tmux session setup commands
- Wave execution order (W1→W2→W3→W4)
- Checkpoint gates per wave
- Agent instruction files in `agents/` directory
