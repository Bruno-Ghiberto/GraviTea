# Agent A1: Models, Services, Migration & RLS

**Agent Type**: `python-expert`
**Model**: Sonnet 4.6
**Mission**: Create the 3 new Django models (StorageUnit, GrainLot, GrainMovement), the service layer, migration, RLS policies, management command, and test fixtures.

---

## Context Files — Read FIRST

1. `Docs/PROMPTS/spec-12-storage/12-implement.md` — Orchestration protocol, wave order, code patterns
2. `specs/012-storage-position/data-model.md` — Entity definitions, fields, constraints, indexes
3. `specs/012-storage-position/quickstart.md` — Mental model, invariants, transaction patterns
4. `specs/012-storage-position/tasks.md` — Full task list with descriptions

---

## Assigned Tasks

### Wave 1: Foundation (T001–T008)

| Task | Description |
|------|-------------|
| T001 | Add `storage_unit_factory`, `grain_lot_factory`, `grain_movement_factory`, `romaneo_conforme` fixtures to `backend/tests/acopio/conftest.py` |
| T002 | Create `StorageUnit` model in `backend/apps/acopio/models/storage_unit.py` |
| T003 | Create `GrainLot` model in `backend/apps/acopio/models/grain_lot.py` |
| T004 | Create `GrainMovement` model (IMMUTABLE) in `backend/apps/acopio/models/grain_movement.py` |
| T005 | Add `storage_unit` + `grain_lot` FKs to `backend/apps/acopio/models/romaneo.py`; update CONFORME mutable-fields allowlist |
| T006 | Update `backend/apps/acopio/models/__init__.py` exports + register in `backend/apps/acopio/admin.py` |
| T007 | Run `makemigrations` to generate `0003_storage_position.py`; verify with `migrate --check` |
| T008 | Append RLS policies to `backend/database/sql/acopio_rls.sql` |

### Wave 2: Deposit Service (T016)

| Task | Description |
|------|-------------|
| T016 | Create `backend/apps/acopio/services/storage.py` with `create_deposit_from_romaneo()` + `_generate_lot_code()` |

### Wave 3: P2 Services (T023, T027, T031, T035)

| Task | Description |
|------|-------------|
| T023 | Add `suggest_cell()` + `CellSuggestion` dataclass |
| T027 | Add `create_withdrawal()` |
| T031 | Add `transfer_grain()` |
| T035 | Add `generate_stock_report()` |

### Wave 4: P3 Services (T039, T041, T044)

| Task | Description |
|------|-------------|
| T039 | Add `reconcile()` |
| T041 | Create `backend/apps/acopio/management/commands/check_grain_balance.py` |
| T044 | Add `CampaignCloseService` + `close_campaign()` |

---

## Files to Create

| File | Description |
|------|-------------|
| `backend/apps/acopio/models/storage_unit.py` | StorageUnit model |
| `backend/apps/acopio/models/grain_lot.py` | GrainLot model |
| `backend/apps/acopio/models/grain_movement.py` | GrainMovement model (immutable) |
| `backend/apps/acopio/services/storage.py` | All service functions (grows incrementally) |
| `backend/apps/acopio/management/__init__.py` | Package init |
| `backend/apps/acopio/management/commands/__init__.py` | Package init |
| `backend/apps/acopio/management/commands/check_grain_balance.py` | Balance consistency check |

## Files to Modify

| File | What Changes |
|------|--------------|
| `backend/apps/acopio/models/romaneo.py` | Add 2 nullable FKs + update CONFORME allowlist (line ~201) |
| `backend/apps/acopio/models/__init__.py` | Add 3 new model exports |
| `backend/apps/acopio/admin.py` | Register 3 new models |
| `backend/database/sql/acopio_rls.sql` | Append 3 RLS policy blocks |
| `backend/tests/acopio/conftest.py` | Add storage fixtures |

---

## Domain Knowledge

### RAG Queries (run if you need additional context)

```bash
.venv/bin/python scripts/qdrant/qdrant_search.py -q "grain storage silo position tracking" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "RG 3593 grain inventory campaign segregation" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "immutable ledger append-only stock movement" -l 5
```

### Critical Domain Facts (Inlined)

1. **GrainMovement is FULLY IMMUTABLE**: `save()` raises `ValueError` if `self._state.adding` is False. `delete()` raises `ValueError` always. Follow `MermaCalculation` pattern exactly.
2. **GrainLot composite key**: `(tenant, branch, grain_type, campaign, grado, storage_unit)` — 6-field UniqueConstraint.
3. **`total_kg >= 0`**: CheckConstraint on GrainLot. Also enforced in service layer before withdrawal.
4. **`current_occupancy_kg` is NOT a field**: It is computed via annotated queryset. Do NOT add it to StorageUnit model.
5. **5 movement types**: DEPOSIT, WITHDRAWAL, TRANSFER_IN, TRANSFER_OUT, ADJUSTMENT.
6. **WITHDRAWAL and TRANSFER_OUT store negative `quantity_kg`**.
7. **`lot_code` auto-generated on first save**: Pattern: `{BRANCH_CODE}-{GRAIN_CODE}-{CAMPAIGN_CODE}-{GRADO}`.
8. **Romaneo CONFORME allowlist** is at `romaneo.py:201`. Current: `{"tara_kg", "peso_neto_bruto_kg", "ts_tara", "status"}`. Add: `"storage_unit_id", "grain_lot_id"`. The attname for FK fields includes `_id` suffix.
9. **`is_own_grain=False`** is the default for spec-12 deposit flow (third-party custody). Own-grain config deferred to spec-13.
10. **GrainMovement has NO `updated_at` field** — intentionally omitted (immutable model).
11. **RLS for GrainMovement**: Grant only `SELECT, INSERT` (no UPDATE, DELETE) to `gravitea_app`.
12. **Transfer deadlock prevention**: Lock both GrainLot rows in ascending PK order (`sorted([pk1, pk2])`).

---

## Key Patterns & Constraints

### Model Field Conventions

```python
# All kg fields: DECIMAL(17,3)
total_kg = models.DecimalField(max_digits=17, decimal_places=3, default=Decimal("0.000"))

# All FKs to tenant-scoped models: on_delete=PROTECT
branch = models.ForeignKey("core.Branch", on_delete=models.PROTECT, related_name="storage_units")

# Nullable FKs (optional references): on_delete=SET_NULL
romaneo = models.ForeignKey("acopio.Romaneo", on_delete=models.SET_NULL, null=True, blank=True, related_name="grain_movements")

# TextChoices for enum fields
class UnitType(models.TextChoices):
    SILO_VERTICAL = "SILO_VERTICAL", "Silo Vertical"
    CELDA_HORIZONTAL = "CELDA_HORIZONTAL", "Celda Horizontal"
    SECADERO_BIN = "SECADERO_BIN", "Secadero / Bin"
```

### Admin Registration for Immutable Model

```python
@admin.register(GrainMovement)
class GrainMovementAdmin(admin.ModelAdmin):
    list_display = ["id", "grain_lot", "movement_type", "quantity_kg", "movement_at"]
    list_filter = ["movement_type"]
    readonly_fields = [f.name for f in GrainMovement._meta.get_fields() if hasattr(f, "name")]

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
```

### RLS Policy Pattern

```sql
-- GrainMovement: IMMUTABLE — only SELECT + INSERT
ALTER TABLE acopio_grainmovement ENABLE ROW LEVEL SECURITY;
ALTER TABLE acopio_grainmovement FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS grainmovement_tenant_isolation ON acopio_grainmovement;
CREATE POLICY grainmovement_tenant_isolation ON acopio_grainmovement
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

COMMENT ON POLICY grainmovement_tenant_isolation ON acopio_grainmovement IS
'Ensures grain movements are only visible/insertable within their tenant context.';

GRANT SELECT, INSERT ON acopio_grainmovement TO gravitea_app;
-- NOTE: No UPDATE or DELETE grant — immutable table
```

### Fixture Pattern (conftest.py)

Follow the existing `romaneo_factory` pattern — create shared resources once outside the closure:

```python
@pytest.fixture
def storage_unit_factory(tenant_context, branch, admin_user, db):
    _counter = [0]
    def create(**kwargs):
        _counter[0] += 1
        defaults = {
            "tenant": tenant_context,
            "branch": branch,
            "name": f"Silo {_counter[0]}",
            "unit_type": StorageUnit.UnitType.SILO_VERTICAL,
            "capacity_tonnes": Decimal("500.000"),
            "created_by": admin_user,
        }
        defaults.update(kwargs)
        return StorageUnit.objects.create(**defaults)
    return create
```

---

## NEVER

- NEVER add `current_occupancy_kg` as a model field on StorageUnit
- NEVER add `updated_at` to GrainMovement
- NEVER import StockMovement from `apps/inventario` for grain tracking
- NEVER read full research PDFs — use RAG queries above if needed
- NEVER run pytest directly — tests are handled by A3 via `scripts/run-tests-external.sh`
