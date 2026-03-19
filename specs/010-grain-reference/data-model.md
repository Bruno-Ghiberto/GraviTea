# Data Model: Grain Reference Data

**Feature**: 010-grain-reference | **Date**: 2026-03-18

## Entity Relationship Overview

```text
                    ┌──────────────────┐
                    │    GrainType     │  GLOBAL
                    │  (models.Model)  │
                    └──────┬───────────┘
                           │ FK (PROTECT)
              ┌────────────┼────────────┐
              │            │            │
    ┌─────────▼──────┐ ┌──▼───────────┐│
    │ ToleranceTable │ │  MermaTable  ││
    │   (GLOBAL)     │ │  (GLOBAL)    ││
    └────────────────┘ └──────────────┘│
                                       │
                    ┌──────────────────┐│
                    │  CampanaConfig   ││  TENANT-SCOPED
                    │(TenantBoundModel)││
                    └──────────────────┘│
                           │ FK (PROTECT)
                    ┌──────▼───────────┐
                    │     Tenant       │  (from core)
                    └──────────────────┘
```

Note: CampanaConfig has NO FK to GrainType. Campaigns are not grain-specific — a single campaign covers all grain types for an organization.

## Entities

### GrainType (GLOBAL)

An officially recognized grain species with ARCA code and regulatory parameters.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK, auto-generated | Primary key |
| code | String(5) | UNIQUE, NOT NULL | Internal shortcode (TRI, MAI, SOJ, CEB_F, CEB_C) |
| arca_codigo | PositiveSmallInt | UNIQUE, NOT NULL | Official ARCA ncespecie code (15, 19, 23, etc.) |
| name | String(100) | NOT NULL | Full Spanish name |
| humedad_base_pct | Decimal(5,2) | NOT NULL | Base moisture % for grading reference |
| hf_secado_pct | Decimal(5,2) | NOT NULL | Hf for drying formula (CRITICAL: != humedad_base_pct) |
| manipuleo_fijo_pct | Decimal(5,2) | NOT NULL | Fixed manipuleo deduction % |
| volatil_fijo_pct | Decimal(5,2) | NOT NULL | Fixed volatil deduction % |
| grading_system | Enum(GRADO, TOLERANCE) | NOT NULL, default GRADO | Grading classification |
| is_active | Boolean | NOT NULL, default True | Soft-disable flag |

**Inheritance**: `django.db.models.Model` (NOT TenantBoundModel)
**Manager**: `models.Manager()` (standard, no tenant filtering)
**RLS**: None
**Uniqueness**: Dual unique constraints on `code` and `arca_codigo`

### CampanaConfig (TENANT-SCOPED)

Agricultural campaign year configuration per organization.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK, auto-generated | Primary key |
| tenant | FK(Tenant) | PROTECT, NOT NULL | Owning organization |
| campaign_code | String(7) | NOT NULL, regex `^\d{4}/\d{2}$` | Format "YYYY/YY" |
| start_date | Date | NOT NULL | Campaign start |
| end_date | Date | NOT NULL, > start_date | Campaign end |
| is_active | Boolean | NOT NULL, default False | Active flag |
| notes | Text | NULL | Optional notes |

**Inheritance**: `TenantBoundModel`
**Manager**: `TenantBoundManager` + `AllObjectsManager`
**RLS**: Yes (`acopio_rls.sql`)
**Constraints**:
- `UniqueConstraint(tenant, campaign_code)` — no duplicate codes per tenant
- `UniqueConstraint(tenant, is_active) WHERE is_active=True` — one active per tenant (ADR-011)

**Validation**:
- `campaign_code` format: YYYY/YY with consecutive years
- `end_date > start_date`

**Computed Property**: `wslpg_code` — converts "2024/25" to "2425" for ARCA submission

### ToleranceTable (GLOBAL)

Versioned quality parameter tolerance thresholds per grain type and grade level.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK, auto-generated | Primary key |
| grain_type | FK(GrainType) | PROTECT, NOT NULL | Referenced grain |
| valid_from | Date | NOT NULL | Version start date |
| valid_to | Date | NULL | NULL = currently active |
| parameter | String(50) | NOT NULL | Parameter name (humedad, materias_extranas, etc.) |
| tolerance_pct | Decimal(5,2) | NOT NULL | Tolerance threshold % |
| grado_base | Integer | NOT NULL | Reference grade (1, 2, 3) |
| source_resolution | String(100) | NULL | SAGPyA/SENASA resolution |

**Inheritance**: `django.db.models.Model`
**Manager**: `models.Manager()`
**RLS**: None
**Versioning**: `valid_to = NULL` means currently active. One active version per `(grain_type, parameter, grado_base)`.
**Indexes**: `(grain_type_id, valid_to)`, `(grain_type_id, parameter, grado_base, valid_to)`

### MermaTable (GLOBAL)

Versioned zarandeo (screening) deduction bands per grain type.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK, auto-generated | Primary key |
| grain_type | FK(GrainType) | PROTECT, NOT NULL | Referenced grain |
| valid_from | Date | NOT NULL | Version start date |
| valid_to | Date | NULL | NULL = currently active |
| materias_extranas_from_pct | Decimal(5,2) | NOT NULL | Lower bound of ME% range (inclusive) |
| materias_extranas_to_pct | Decimal(5,2) | NULL | Upper bound (NULL = unbounded) |
| zarandeo_deduction_pct | Decimal(5,2) | NOT NULL | Deduction for this range |

**Inheritance**: `django.db.models.Model`
**Manager**: `models.Manager()`
**RLS**: None
**Versioning**: Same pattern as ToleranceTable.
**Indexes**: `(grain_type_id, valid_to)`, `(grain_type_id, materias_extranas_from_pct, valid_to)`

## State Transitions

### CampanaConfig Lifecycle

```text
CREATED (is_active=False)
    │
    ▼
ACTIVATED (is_active=True)  ← only one per tenant at a time
    │
    ▼
DEACTIVATED (is_active=False)  ← admin must deactivate before activating another
```

Activation is controlled by the `is_active` boolean flag with a partial unique constraint ensuring only one active campaign per tenant. There is no automatic deactivation — the administrator must explicitly deactivate the current campaign before activating a new one.

### ToleranceTable / MermaTable Versioning

```text
VERSION 1: valid_from=2020-01-01, valid_to=NULL (active)
    │
    │  Regulatory change occurs
    ▼
VERSION 1: valid_from=2020-01-01, valid_to=2026-04-01 (closed)
VERSION 2: valid_from=2026-04-01, valid_to=NULL (active)
```

New versions are created by closing the previous version (setting `valid_to`) and inserting a new row with `valid_to=NULL`.

## Seed Data Summary

| Entity | Seed Count | Key Source |
|--------|------------|------------|
| GrainType | 7 minimum (trigo, maiz, soja, girasol, sorgo, cebada forr., cebada cerv.) | ARCA ncespecie + Camara Arbitral tables |
| ToleranceTable | ~30-50 rows (5 grains x parameters x grades) | SAGPyA/SENASA resolutions |
| MermaTable | ~20-30 rows (5 grains x 4-5 zarandeo bands each) | Circular CAC 10/86, JNG 22027/81 |
| CampanaConfig | 0 (created per-tenant by administrators) | N/A |
