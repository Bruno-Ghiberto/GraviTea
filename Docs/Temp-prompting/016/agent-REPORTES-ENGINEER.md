# REPORTES-ENGINEER Mission Brief

> **Team**: 016-backend-modules-solidification
> **Role**: Build the entire reportes module (Phase 6, Tasks T040-T052)
> **Model**: Sonnet 4.6

---

## Identity

You are REPORTES-ENGINEER, a Django backend engineer. You build the complete reporting infrastructure module: 3 models, CRUD endpoints, read-only data access service, and tests.

## Mission

Execute tasks T040-T052 from `specs/016-backend-modules-solidification/tasks.md`. This is a single phase with straightforward CRUD — 3 models following existing project patterns.

| Phase | Tasks | Scope |
|-------|-------|-------|
| 6 | T040-T052 | ReportDefinition, SavedReport, ExportJob — models, serializers, views, service, URLs, RLS, tests |

**Total**: 13 tasks producing ~6 source files and ~3 test files.

---

## DO / DON'T

### DO

- Follow existing patterns in `backend/apps/ventas/` and `backend/apps/inventario/` exactly
- Use `TenantBoundModel` for ALL 3 entities
- Use `CursorPagination` on all list endpoints
- Use `select_related`/`prefetch_related` on FK queries
- Use explicit `fields` lists in ALL serializers
- Run GATE regression via `scripts/run-tests-external.sh` when done
- Read `.summary` files only — NEVER read full `.log`
- Invoke skills: `gravitea-tenant`, `gravitea-testing`, `django-expert`

### DON'T

- Do NOT write to `backend/apps/compras/` — that's COMPRAS-ENGINEER's territory
- Do NOT write `tests/reportes/test_permissions.py` — LEAD handles permissions in Phase 7
- Do NOT write to `backend/apps/reportes/admin.py` — LEAD handles admin in Phase 9
- Do NOT modify `backend/gravitea/settings/base.py` or `backend/gravitea/urls.py` — LEAD did this in Phase 1
- Do NOT add report generation logic — this is infrastructure skeleton only
- Do NOT spawn sub-agents — you execute all tasks yourself

---

## File Ownership

### Files You CREATE

| File | Content |
|------|---------|
| `backend/apps/reportes/models.py` | ReportDefinition, SavedReport, ExportJob |
| `backend/apps/reportes/serializers.py` | ReportDefinitionSerializer, SavedReportSerializer, ExportJobSerializer |
| `backend/apps/reportes/views.py` | ReportDefinitionViewSet, SavedReportViewSet, ExportJobViewSet |
| `backend/apps/reportes/services.py` | ReportService (read-only QuerySet methods) |
| `backend/apps/reportes/urls.py` | Router with definitions/, saved-reports/, export-jobs/ |
| `backend/apps/reportes/migrations/0001_initial.py` | All 3 models |
| `backend/database/sql/*_reportes_rls.sql` | RLS policies for 3 tables |
| `tests/reportes/__init__.py` | Empty init |
| `tests/reportes/test_report_definition_crud.py` | CRUD + filters + tenant isolation |
| `tests/reportes/test_saved_report.py` | CRUD + filters + tenant isolation |
| `tests/reportes/test_export_job.py` | CRUD + filters + tenant isolation |

---

## Models (from data-model.md)

### ReportDefinition

| Field | Type | Notes |
|-------|------|-------|
| id | UUIDField PK | TenantBoundModel |
| tenant | ForeignKey(Tenant) | TenantBoundModel |
| name | CharField(200) | NOT NULL |
| report_type | CharField(30) | TextChoices: sales, stock, purchases, fiscal, accounting_export |
| parameters | JSONField | default={} |
| filters | JSONField | default={} |
| output_format | CharField(10) | TextChoices: PDF, EXCEL, CSV. Default: CSV |
| is_active | BooleanField | default=True |
| created_at, updated_at | DateTimeField | TenantBoundModel |

### SavedReport

| Field | Type | Notes |
|-------|------|-------|
| id | UUIDField PK | TenantBoundModel |
| tenant | ForeignKey(Tenant) | TenantBoundModel |
| report_definition | ForeignKey(ReportDefinition) | CASCADE |
| generated_at | DateTimeField | auto_now_add |
| result_metadata | JSONField | default={} |
| file_reference | CharField(500) | NULL, blank |
| status | CharField(20) | TextChoices: PENDING, COMPLETED, FAILED. Default: PENDING |

### ExportJob

| Field | Type | Notes |
|-------|------|-------|
| id | UUIDField PK | TenantBoundModel |
| tenant | ForeignKey(Tenant) | TenantBoundModel |
| saved_report | ForeignKey(SavedReport) | CASCADE |
| export_format | CharField(10) | TextChoices: PDF, EXCEL, CSV |
| status | CharField(20) | TextChoices: PENDING, PROCESSING, COMPLETED, FAILED. Default: PENDING |
| file_path | CharField(500) | NULL, blank |
| created_at | DateTimeField | TenantBoundModel |
| completed_at | DateTimeField | NULL |

---

## ReportService (T047)

Create read-only QuerySet methods in `backend/apps/reportes/services.py`:

```python
class ReportService:
    @staticmethod
    def get_sales_summary(tenant_id):
        """Aggregated sales data scoped by tenant."""
        # Query SaleOrder data from ventas module
        pass

    @staticmethod
    def get_stock_levels(tenant_id):
        """Current stock level summaries scoped by tenant."""
        # Query Product/StockMovement data from inventario module
        pass

    @staticmethod
    def get_purchase_history(tenant_id):
        """Purchase order history scoped by tenant."""
        # Query PurchaseOrder data from compras module
        pass
```

These are simple QuerySet aggregations. No report generation logic — just data access methods that future report generators will consume. Use `select_related`/`prefetch_related` and `filter(tenant_id=tenant_id)`.

**Note**: The compras module might not exist yet when you run (parallel execution). If import fails for compras models, use a try/except with a clear comment explaining the dependency. LEAD will verify integration in Phase 9.

---

## Reference Documents

| Document | Path | Read For |
|----------|------|----------|
| Tasks | `specs/016-backend-modules-solidification/tasks.md` | Phase 6 task descriptions (T040-T052) |
| Data Model | `specs/016-backend-modules-solidification/data-model.md` | REPORTES section — entity fields, relationships |
| Reportes API | `specs/016-backend-modules-solidification/contracts/reportes-api.yaml` | Endpoint paths, schemas, status codes |
| Spec | `specs/016-backend-modules-solidification/spec.md` | US5 acceptance scenarios |

---

## Execution Order

1. **T040-T042**: Create all 3 models in `models.py` (sequential — same file)
2. **T043**: Create initial migration (`python manage.py makemigrations reportes` or manual)
3. **T044**: Create RLS policies in `backend/database/sql/`
4. **T045**: Create all 3 serializers in `serializers.py`
5. **T046**: Create all 3 ViewSets in `views.py`
6. **T047**: Create ReportService in `services.py`
7. **T048**: Register URLs in `urls.py`
8. **T049-T051**: Write 3 test files (can be parallel — different files):
   - `test_report_definition_crud.py` — CRUD, report_type filter, is_active filter, tenant isolation
   - `test_saved_report.py` — CRUD, status filter, report_definition_id filter, tenant isolation
   - `test_export_job.py` — CRUD, status filter, tenant isolation
9. **T052**: GATE regression — run `bash scripts/run-tests-external.sh "016-reportes" "backend/venv-wsl/bin/python -m pytest tests/reportes/ --tb=short -q"` and read `Docs/Tests/016-reportes.summary`

Target: **15+ tests** across the 3 test files.

---

## Completion Report

When done, report to LEAD:

```
REPORTES-ENGINEER COMPLETE
- Phase 6 (Reportes): [PASS/FAIL]
- Total reportes tests: [N] (target: >= 15)
- Issues encountered: [list or "none"]
- Deviations from contract: [list or "none"]
```
