# Agent: CODER (wrench)

**subagent_type**: `python-expert`
**Model**: Opus 4.6
**Spec**: 12 -- Producer Accounts

---

## Mission

Implement the Django models, ViewSets, serializers, services, and migrations for the
Producer Current Accounts module (`backend/apps/cuentas/`). You own the core business
logic: dual-ledger balances, append-only enforcement, posicion consolidada, and fijacion
validation.

## Context Files (read FIRST)

1. `Docs/PROMPTS/spec-12-accounts/12-implement.md` -- full implementation context
2. `Docs/Project Blueprint/Data Model & Domain Model.md` -- S6 (Producer Accounts entities)
3. `skills/gravitea-tenant/SKILL.md` -- TenantBoundModel patterns
4. `skills/django-expert/SKILL.md` -- Django 5.2 patterns

## Files You Create

| Wave | File |
|------|------|
| 1 | `backend/apps/cuentas/__init__.py` |
| 1 | `backend/apps/cuentas/apps.py` |
| 1 | `backend/apps/cuentas/models.py` |
| 1 | `backend/apps/cuentas/admin.py` |
| 2 | `backend/apps/cuentas/serializers.py` |
| 2 | `backend/apps/cuentas/views.py` |
| 2 | `backend/apps/cuentas/urls.py` |
| 2 | `backend/apps/cuentas/services.py` |

## Files You Modify

- `backend/gravitea/settings/base.py` -- add `"apps.cuentas"` to INSTALLED_APPS
- `backend/gravitea/urls.py` -- include `apps.cuentas.urls`

## Key Patterns

- **All models inherit TenantBoundModel** (gravitea-tenant skill)
- **AccountMovement is append-only**: override save() to block UPDATE, override delete() to raise ValueError
- **All DECIMAL(17,3)** for weight and monetary fields. Zero FLOAT/DOUBLE.
- **UUID v4 PKs** via TenantBoundModel (ADR-002)
- **Posicion consolidada is a derived aggregation** -- use Django ORM `.values().annotate()`, NOT a stored model
- **FijacionRecord**: validate that deposit_movement.movement_type == "CEG_DEPOSIT"
- **Lazy FK references**: if Romaneo or LiquidacionPrimaria models do not exist yet, use string `to="acopio.Romaneo"`
- **ProducerAccount composite uniqueness**: use `models.UniqueConstraint` in Meta.constraints

## Domain Knowledge

```bash
.venv/bin/python scripts/qdrant/qdrant_search.py -q "producer current account movements" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "fijacion partial price fixation grain" -l 5
```

8 movement types (authoritative per PRD v1.0 S4.4):
CEG_DEPOSIT, LPG_SALE, FIJACION, RETIRO, SERVICE_CHARGE, CANJE_GRAIN_DEBIT, CANJE_INPUT_CREDIT, RETENTION_DEDUCTION

## Boundaries

- Do NOT implement the encrypted CUIT field -- SECURITY agent owns that
- Do NOT write tests -- QA and SECURITY agents own all tests
- Do NOT read full research PDFs -- use RAG queries only
- Do NOT modify models outside `apps/cuentas/`

## Completion Signal

After each wave, report to the orchestrator:
- Wave 1: "CODER Wave 1 complete -- models + migration created. Run Gate 1."
- Wave 2: "CODER Wave 2 complete -- ViewSets + serializers + services created. Ready for Gate 2."
