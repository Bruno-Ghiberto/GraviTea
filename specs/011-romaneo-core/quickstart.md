# Quickstart: Romaneo Core

**Feature**: 011-romaneo-core | **Date**: 2026-03-19

## Prerequisites

- spec-10 (Grain Reference Data) must be complete and merged
- Python 3.14.3 with `.venv` activated
- Rust 1.93.1 with Maturin 1.12.4
- PostgreSQL or SQLite for development

## Setup

```bash
# 1. Checkout branch
git checkout 011-romaneo-core

# 2. Install Python dependencies
cd backend && ../.venv/bin/pip install -r requirements.txt

# 3. Build Rust module
cd rust/gravitea-core && maturin develop --release

# 4. Run migrations
cd backend && ../.venv/bin/python manage.py migrate

# 5. Verify models load
cd backend && ../.venv/bin/python -c "from apps.acopio.models import Romaneo, QualityAnalysis, MermaCalculation; print('OK')"

# 6. Verify Rust FFI
.venv/bin/python -c "from gravitea_rust import calculate_merma; print('OK')"
```

## Running Tests

```bash
# All acopio tests (recommended)
bash scripts/run-tests-external.sh -n spec11 tests/acopio/

# Check results
cat Docs/Tests/spec11.status
cat Docs/Tests/spec11.summary

# Rust unit tests
cd rust/gravitea-core && cargo test merma
```

## Key Files

| File | Purpose |
|------|---------|
| `backend/apps/acopio/models/romaneo.py` | Romaneo model (31 fields, state machine) |
| `backend/apps/acopio/models/quality_analysis.py` | QualityAnalysis (1:1 satellite) |
| `backend/apps/acopio/models/merma_calculation.py` | MermaCalculation (1:1 immutable) |
| `backend/apps/acopio/services/merma_engine.py` | Rust FFI wrapper + Python fallback |
| `rust/gravitea-core/src/merma.rs` | Rust merma engine |
| `backend/apps/acopio/views/romaneo.py` | RomaneoViewSet + QualityAnalysisViewSet |

## API Quick Test

```bash
# Create a romaneo
curl -X POST http://localhost:8000/api/v1/acopio/romaneos/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "grain_type": "<grain-type-uuid>",
    "campaign": "<campaign-uuid>",
    "branch": "<branch-uuid>",
    "patente_chasis": "AB123CD",
    "driver_name": "Juan Perez",
    "driver_dni": "12345678",
    "cpe_numero": "CPE-00001234",
    "producer_cuit": "20123456789",
    "origin_locality": "Pergamino, Buenos Aires"
  }'
```
