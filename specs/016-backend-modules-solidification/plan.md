# Implementation Plan: Backend Modules Solidification

**Branch**: `016-backend-modules-solidification` | **Date**: 2026-02-24 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/016-backend-modules-solidification/spec.md`

## Summary

Restructure the GRAVITEA-ERP backend into a well-defined 8-module architecture by:
1. Creating `apps/compras/` — migrate Supplier from inventario, build PurchaseOrder lifecycle with GoodsReceipt→StockMovement integration
2. Creating `apps/reportes/` — infrastructure skeleton (models, CRUD endpoints, read-only data access) for future BI
3. Extending JSONB customization to PurchaseOrder entities
4. Solidifying module boundaries with permission enforcement and seed data

Technical approach: Django `SeparateDatabaseAndState` migration for zero-downtime Supplier move (R-001), nested serializer pattern from SaleOrder for PO+Items (R-005), existing `MovementType.PURCHASE` for stock integration (R-007), Django QuerySets for REPORTES read-only access (R-006).

## Technical Context

**Language/Version**: Python 3.14.3
**Primary Dependencies**: Django 5.2.x, Django REST Framework, djangorestframework-simplejwt, cryptography (AES-256-GCM)
**Storage**: PostgreSQL 18.1 (Cloud SQL Enterprise Plus), Redis 7.x (cache)
**Testing**: pytest + pytest-django, target >= 78% coverage
**Target Platform**: Linux server (WSL2 dev, GKE prod)
**Project Type**: Web application (Django monolithic modular backend)
**Performance Goals**: Cursor-based pagination on all list endpoints, `select_related`/`prefetch_related` on all FK/M2M
**Constraints**: Multi-tenant RLS isolation on all new tables, DECIMAL(17,3) for all financial fields, append-only ledger for stock movements
**Scale/Scope**: 7 new entities, 5 modified entities, 2 new Django apps, ~30 new API endpoints, 75+ new tests

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Status | Notes |
|---|-----------|--------|-------|
| I | Ironclad Data Model | PASS | DECIMAL(17,3) for quantity/unit_price/line_total/total_amount. CHECK constraints for non-negative. ON DELETE RESTRICT on Supplier→PO, Product→POItem. GoodsReceipt is append-only (immutable). |
| II | Multi-Tenant Isolation (RLS) | PASS | All 7 new entities inherit TenantBoundModel. RLS policies required on compras + reportes tables. |
| III | Modular Django Architecture | PASS | Creates `compras` and `reportes` apps with clear boundaries. Views are lightweight; business logic in services (GoodsReceiptService). |
| IV | Application-Level Encryption | PASS | Supplier encrypted fields preserved through migration (no re-encryption). No new PII fields introduced. |
| V | Secure Authentication & Sessions | PASS | JWT auth unchanged. IDOR prevention via TenantBoundModel._validate_tenant_references() on all new models. |
| VI | Fiscal Compliance (ARCA) | N/A | No fiscal changes in this feature. |
| VII | Offline-First & Contingency | N/A | No sync changes. Purchase orders are online-only in MVP. |
| VIII | Query Optimization | PASS | All ViewSets must use select_related for FK (supplier, product, purchase_order) and prefetch_related for reverse FK (items, lines). |
| IX | Secure Data Operations | PASS | All serializers use explicit `fields` lists. No `fields = '__all__'`. Bulk operations for GoodsReceiptLine creation. |
| X | Test-Driven Development | PASS | 60+ compras tests, 15+ reportes tests. Coverage target >= 78%. |
| XI | JWT Authentication | PASS | No JWT changes. Existing middleware provides tenant_id/branch_id context. |
| XII | Rate Limiting | N/A | No new auth endpoints. |
| XIII | Cursor-Based Pagination | PASS | All list endpoints use CursorPagination with `created_at` ordering. |
| XIV | API Documentation | PASS | OpenAPI contracts in contracts/. drf-spectacular annotations on all new ViewSets. |

**Post-Design Re-Check**: All gates PASS. No violations.

## Project Structure

### Documentation (this feature)

```text
specs/016-backend-modules-solidification/
├── plan.md              # This file
├── research.md          # R-001 through R-007 + additional findings
├── data-model.md        # Entity definitions + 3 Mermaid ERDs
├── quickstart.md        # 8-phase execution guide with gates
├── contracts/
│   ├── compras-api.yaml   # OpenAPI 3.0.3 — suppliers, POs, goods receipts
│   └── reportes-api.yaml  # OpenAPI 3.0.3 — definitions, saved reports, export jobs
└── tasks.md             # Phase 2 output (NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
backend/
├── apps/
│   ├── compras/                    # NEW — Purchases module
│   │   ├── __init__.py
│   │   ├── apps.py                 # ComprasConfig (app_label: gravitea_compras)
│   │   ├── models.py               # Supplier (migrated), PurchaseOrder, PurchaseOrderItem, GoodsReceipt, GoodsReceiptLine
│   │   ├── serializers.py          # SupplierSerializer, PurchaseOrderSerializer (nested items), GoodsReceiptSerializer (nested lines)
│   │   ├── views.py                # SupplierViewSet, PurchaseOrderViewSet (confirm/cancel actions), GoodsReceiptViewSet
│   │   ├── services.py             # GoodsReceiptService (stock movement creation, PO state transitions)
│   │   ├── urls.py                 # Router registration under /api/v1/compras/
│   │   ├── admin.py                # PurchaseOrderAdmin, GoodsReceiptAdmin
│   │   └── migrations/
│   │       ├── 0001_initial.py     # SeparateDatabaseAndState — claim Supplier in state
│   │       └── 0002_purchase_models.py  # PurchaseOrder, PurchaseOrderItem, GoodsReceipt, GoodsReceiptLine
│   ├── reportes/                   # NEW — Reporting infrastructure
│   │   ├── __init__.py
│   │   ├── apps.py                 # ReportesConfig (app_label: gravitea_reportes)
│   │   ├── models.py               # ReportDefinition, SavedReport, ExportJob
│   │   ├── serializers.py          # ReportDefinitionSerializer, SavedReportSerializer, ExportJobSerializer
│   │   ├── views.py                # ReportDefinitionViewSet, SavedReportViewSet, ExportJobViewSet
│   │   ├── services.py             # ReportService (read-only QuerySet methods for cross-module data)
│   │   ├── urls.py                 # Router registration under /api/v1/reportes/
│   │   ├── admin.py
│   │   └── migrations/
│   │       └── 0001_initial.py     # ReportDefinition, SavedReport, ExportJob
│   ├── inventario/
│   │   ├── models.py               # MODIFIED: Product.supplier FK → compras.Supplier
│   │   └── migrations/
│   │       └── 00XX_remove_supplier_state.py  # SeparateDatabaseAndState — remove Supplier from state
│   └── core/
│       └── models/
│           └── customization.py    # MODIFIED: Add PURCHASE_ORDER to EntityType choices
├── gravitea/
│   ├── settings/base.py            # MODIFIED: Add 'apps.compras', 'apps.reportes' to INSTALLED_APPS
│   └── urls.py                     # MODIFIED: Include compras.urls and reportes.urls
└── tests/
    ├── compras/                    # NEW — 60+ tests
    │   ├── __init__.py
    │   ├── test_supplier_migration.py
    │   ├── test_purchase_order_crud.py
    │   ├── test_purchase_order_state_machine.py
    │   ├── test_goods_receipt.py
    │   ├── test_stock_integration.py
    │   ├── test_custom_fields.py
    │   └── test_permissions.py
    └── reportes/                   # NEW — 15+ tests
        ├── __init__.py
        ├── test_report_definition_crud.py
        ├── test_saved_report.py
        ├── test_export_job.py
        └── test_permissions.py
```

**Structure Decision**: Extends existing Django monolithic modular pattern (backend/apps/). Two new apps (`compras`, `reportes`) follow the same conventions as existing apps (`inventario`, `ventas`, `facturacion`). Tests in `tests/compras/` and `tests/reportes/` follow existing test directory convention.

## Phase Summary

| Phase | Scope | Risk | Dependencies | Gate |
|-------|-------|------|-------------|------|
| 1 | COMPRAS app + Supplier migration | HIGH | None | Full regression — 0 new failures |
| 2 | PurchaseOrder + Items | MEDIUM | Phase 1 | Regression green |
| 3 | GoodsReceipt + Stock integration | MEDIUM | Phase 2 | Regression green |
| 4 | JSONB Custom Fields on PO | LOW | Phase 2 | Regression green |
| 5 | REPORTES skeleton | LOW | None (parallel-safe after Phase 1) | Regression green |
| 6 | Permissions | LOW | Phases 2, 3, 5 | Regression green |
| 7 | Seed Data | LOW | Phases 2, 3, 5 | Regression green |
| 8 | Final Validation | LOW | All phases | Full suite, coverage >= 78% |

## Key Design Decisions

| Decision | Choice | Rationale | Research |
|----------|--------|-----------|----------|
| Supplier migration strategy | SeparateDatabaseAndState | Zero data copy, state-only change | R-001 |
| Product FK update | Same migration batch | Prevent intermediate invalid state | R-002 |
| Supplier URL | Clean break to /api/v1/compras/suppliers/ | No external consumers, clean semantics | R-003 |
| PO INVOICED state | Deferred | YAGNI — supplier invoicing is separate feature | R-004 |
| Receipt granularity | GoodsReceiptLine per PO item | Spec requires per-line tracking | R-005 |
| REPORTES data access | Django QuerySets | No existing VIEW patterns, auto tenant isolation | R-006 |
| Stock movement type | Existing PURCHASE | Already in MovementType enum | R-007 |

## Complexity Tracking

> No constitution violations requiring justification. All principles satisfied.

| Item | Status | Notes |
|------|--------|-------|
| No DECIMAL violations | CLEAN | All financial fields use DECIMAL(17,3) |
| No encryption changes | CLEAN | Supplier encrypted fields preserved as-is |
| No new auth endpoints | CLEAN | Existing JWT middleware provides tenant context |
| No RLS gaps | REQUIRES WORK | New tables need RLS policies in Phase 1 migration |

## Related Artifacts

- **Research**: [research.md](./research.md) — 7 research decisions + 3 additional findings
- **Data Model**: [data-model.md](./data-model.md) — 3 ERDs, 7 new entity definitions, 5 modified entities
- **API Contracts**: [contracts/compras-api.yaml](./contracts/compras-api.yaml), [contracts/reportes-api.yaml](./contracts/reportes-api.yaml)
- **Quickstart**: [quickstart.md](./quickstart.md) — 8-phase execution guide with gates and test commands
- **Spec**: [spec.md](./spec.md) — 7 user stories, 34 FRs, 14 SCs
