---
spec: "010"
name: "Grain Reference Data"
type: Implementation
branch: 010-grain-reference
created: 2026-03-18
depends_on: [spec-03, spec-09]
blocks: [spec-11, spec-12]
deliverable: "backend/apps/acopio/ — Django models, fixtures, management command, DRF API, tests"
qdrant_collections: [acopio_research, arca_dev_guides]
agents: [A1, A2, A3, A4]
---

# Spec-10: Grain Reference Data -- Specification Context

## Feature Description

Implement the grain reference data layer -- the foundational data models that every
downstream acopio spec depends on. This spec creates the `backend/apps/acopio/` Django
application with the following deliverables:

1. **Django models** for `GrainType`, `ToleranceTable`, `MermaTable`, and `CampanaConfig`
   as specified in the Data Model v1.0 Section 5.1--5.2.
2. **Seed fixtures** with official ARCA grain species codes and regulatory reference values
   from the Camara Arbitral de Cereales.
3. **Management command** (`seed_grain_reference`) to load fixtures idempotently.
4. **DRF serializers and viewsets** implementing REST API Design v1.0 Section 4
   (`/api/v1/acopio/grain-types/`, `/api/v1/acopio/tolerance-tables/`,
   `/api/v1/acopio/merma-tables/`, `/api/v1/acopio/campaigns/`).
5. **Test suite** covering models, serializers, API endpoints, and fixture loading.

This is the first implementation spec. No acopio code exists yet -- the entire
`backend/apps/acopio/` application is created from scratch.

---

## Current State

### What Exists

- `backend/apps/core/models/mixins.py` -- `TenantBoundModel`, `TimestampedModel`,
  `SoftDeleteModel` abstract base classes are fully implemented and tested.
- `backend/apps/core/managers/tenant_bound.py` -- `TenantBoundManager` with fail-closed
  tenant filtering and `AllObjectsManager` for unscoped system access.
- `backend/apps/` -- contains `auth`, `compras`, `core`, `facturacion`, `inventario`,
  `reportes`, `sync`, `ventas`. No `acopio/` directory.

### What Needs Creating

- `backend/apps/acopio/` -- entire Django app (models, serializers, views, urls, admin,
  fixtures, management commands, tests).
- Django app registration in `INSTALLED_APPS`.
- URL routing for `/api/v1/acopio/` endpoints.
- Initial database migration (`0001_initial.py`).
- Seed data fixture file(s).

---

## Research Inputs

### RAG Queries (run these FIRST -- do NOT read full research files)

```bash
# Query 1: ARCA grain species codes
.venv/bin/python scripts/qdrant/qdrant_search.py -q "grain types codes ARCA humidity base" -l 5

# Query 2: Quality tolerance and bonification tables
.venv/bin/python scripts/qdrant/qdrant_search.py -q "tolerance tables bonification rebaja" -l 5

# Query 3: Campaign year lifecycle
.venv/bin/python scripts/qdrant/qdrant_search.py -q "campaign year management agricultural" -l 5

# Query 4: Quality parameters per grain type
.venv/bin/python scripts/qdrant/qdrant_search.py -q "grain quality parameters humidity moisture" -l 5

# Query 5: Grain codes and quality parameter reference
.venv/bin/python scripts/qdrant/qdrant_search.py -q "grain types quality parameters reference" -l 5

# Query 6: Merma calculation formulas
.venv/bin/python scripts/qdrant/qdrant_search.py -q "merma calculation formula sequential" -l 5

# Query 7: ARCA official commodity nomenclature
.venv/bin/python scripts/qdrant/qdrant_search.py -q "ARCA grain commodity codes grain type nomenclature" -l 5
```

### Source Documents (for reference only -- prefer RAG)

| Doc | Path | Relevant Sections |
|-----|------|-------------------|
| Data Model v1.0 | `Docs/Project Blueprint/Data Model & Domain Model.md` | Section 5.1 (Reference Data), 5.2 (Regulatory Tables) |
| REST API Design v1.0 | `Docs/Project Blueprint/REST API Design.md` | Section 4 (Grain Reference API: 4.1--4.4) |
| ADR v1.0 | `Docs/Project Blueprint/Architecture Decision Records (ADR).md` | ADR-010, ADR-011, ADR-014, ADR-015 |
| ARCA Grain Integration Guide | `Docs/Project Blueprint/ARCA Grain Integration Guide.md` | ARCA grain species codes, WSCPE/WSLPG grain type fields |
| Research 8.1 | `Docs/Researches/Markdown/8.1 Grain Types and Quality Parameter Reference Data.md` | Full ARCA ncespecie code table |
| Research 2.2 | `Docs/Researches/Markdown/2.2 Grain Quality Management Standards.md` | Grade tables per grain, tolerance thresholds |
| Research 2.5 | `Docs/Researches/Markdown/2.5 Merma (Grain Loss) Calculations and Tolerance Tables.md` | Merma formulas, per-grain parameters, zarandeo tables |
| Research 2.6 | `Docs/Researches/Markdown/2.6 Campaign Year Management.md` | Marketing year start/end by grain, naming conventions |

### Critical Domain Facts (minimum context)

#### ARCA Grain Species Codes (ncespecie)

Official codes used in CTG, Form 1116, WSCPE, and WSLPG web services:

| Grain | Spanish Name | ARCA Code | Internal Code |
|-------|-------------|-----------|---------------|
| Bread wheat | Trigo pan | 15 | TRI |
| Corn | Maiz | 19 | MAI |
| Soybean | Soja | 23 | SOJ |
| Sunflower | Girasol (in shell) | 2 | GIR |
| Grain sorghum | Sorgo granifero | 22 | SOR |
| Feed barley | Cebada forrajera | 11 | CEB_F |
| Malting barley | Cebada cervecera | 17 | CEB_C |
| Durum wheat | Trigo candeal | 14 | TRI_D |
| Feed wheat | Trigo forrajero | 10 | TRI_F |
| Popcorn | Maiz pisingallo | 27 | MAI_P |
| Flint corn | Maiz flint/plata | 26 | MAI_F |
| Paddy rice | Arroz cascara | 21 | ARR |
| Oats | Avena | 16 | AVE |
| Rye | Centeno | 18 | CEN |
| Triticale | Triticale | 28 | TRT |
| Flaxseed | Lino | 1 | LIN |
| Canola | Colza 00/Canola | 9 | COL |
| Millet | Mijo | 20 | MIJ |

The initial fixture MUST include at minimum the top 7 grains (trigo pan, maiz, soja,
girasol, sorgo, cebada forrajera, cebada cervecera). Extended grain types can be added
as additional fixture files.

#### Moisture, Hf, and Fixed Merma Constants per Grain

| Grain | Code | Humedad Base (%) | Hf Secado (%) | Tolerancia Recibo Humedad (%) | Manipuleo (%) | Volatil (%) |
|-------|------|-----------------|--------------|------------------------------|---------------|-------------|
| Soja | SOJ | 13.5 | 12.5 | 13.5 | 0.25 | 0.50 |
| Maiz | MAI | 14.5 | 13.5 | 14.5 | 0.25 | 0.30 |
| Trigo pan | TRI | 14.0 | 13.5 | 14.0 | 0.10 | 0.30 |
| Girasol | GIR | 11.0 | 10.5 | 14.0 | 0.20 | 0.50 |
| Sorgo | SOR | 15.0 | 13.5 | 15.0 | 0.25 | 0.50 |
| Cebada forrajera | CEB_F | 14.0 | 13.5 | 14.0 | 0.20 | 0.30 |
| Cebada cervecera | CEB_C | 12.0 | (contract) | 12.5 | -- | 0.30 |

CRITICAL: `Hf` (final moisture for secado formula) is NOT the same as `humedad_base_pct`.
Using the wrong value yields approximately 168 kg error per 30-tonne truck (trigo example).

NOTE: The Data Model v1.0 Section 5.1 reference table lists Soja Hf as 13.0%. This
implementation uses 12.5% based on Research 2.5 "Tabla de parametros por grano para la
base de datos" (the software-implementation reference table from the Camara Arbitral
source), which explicitly lists Soja Hf calculo = 12.5%. The JNG source data shows both
values ("13,0 (base) / 12,5") reflecting different calculation contexts. The 12.5% value
is used here because it aligns with the practical drying-formula reference table designed
for software implementation. This is not a deviation -- it reconciles the Data Model
blueprint with the authoritative RAG-sourced regulatory data.

#### Grading System

Two distinct systems (per Data Model v1.0 Section 5.1, GrainType.grading_system field):

- **Cereals** (trigo, maiz, sorgo) use `GRADO` system: Grado 1 = bonificacion, Grado 2
  = neutral, Grado 3 = rebaja.
- **Oleaginosas** (soja, girasol) use `TOLERANCE` system: progressive rebaja per
  percentage point above tolerance threshold. No grades 1/2/3.

Grade-based bonification/rebaja values:

| Grain | Grado 1 | Grado 2 | Grado 3 |
|-------|---------|---------|---------|
| Trigo pan | +1.5% | 0% | -1.0% |
| Maiz | +1.0% | 0% | -1.5% |
| Sorgo | +1.0% | 0% | -1.5% |

#### Quality Parameters per Grain

Common parameters (all grains): humedad (%), materias extranas (%), granos danados (%),
granos quebrados (%).

Grain-specific parameters:

| Grain | Additional Parameters |
|-------|---------------------|
| Trigo pan | peso hectolitrico (kg/hl), proteina (%), granos ardidos (%), panza blanca (%) |
| Maiz | peso hectolitrico (kg/hl), tipo (duro/dentado), color (%), chamico |
| Soja | granos verdes (%), granos negros (%), chamico |
| Girasol | materia grasa (% s/sustancia seca), acidez materia grasa |
| Sorgo | taninos condensados, color, chamico |

NOTE: Per ADR-015, quality parameters are NOT modeled as a separate entity. They are
inline fields on the `QualityAnalysis` model (spec-11 scope). Spec-10 does NOT create
a QualityParameter model. This is documented here for cross-reference.

#### Merma Calculation Order

Sequential application per Circular CAC 10/86 and Articulo 5 Resolucion JNG 22027/81:

```
Peso_final = Peso_bruto * (1 - %Z) * (1 - %S) * (1 - %M) * (1 - %V)
```

1. Zarandeo (%Z) -- only if materias_extranas > tolerancia
2. Secado (%S) -- only if humedad > tolerancia; formula: %S = (Hi - Hf) / (100 - Hf) * 100
3. Manipuleo (%M) -- only if secado was applied; fixed value from GrainType
4. Volatil (%V) -- always applied; fixed value from GrainType

NOTE: The merma engine itself is spec-11 scope (Rust implementation). Spec-10 provides
the reference data (Hf, manipuleo_fijo_pct, volatil_fijo_pct on GrainType; zarandeo
bands on MermaTable) that the engine consumes.

#### Campaign Year

- Format: "YYYY/YY" (e.g., "2025/26"). Always store full format.
- Each grain type has a different marketing year start month:

| Grain | Marketing Year Start | Example |
|-------|---------------------|---------|
| Trigo / Cebada | December | 2025/26 starts Dec 2025 |
| Maiz / Sorgo / Girasol | March | 2025/26 starts Mar 2026 |
| Soja | April | 2025/26 starts Apr 2026 |

- WSLPG campaign code format: "XXYY" (e.g., "2425" for 2024/25).
- CampanaConfig is per-tenant with `UniqueConstraint` enforcing one active campaign.

---

## Functional Requirements

### FR-010-001: Create `backend/apps/acopio/` Django Application

Create the Django application with standard structure: `__init__.py`, `apps.py`,
`models/`, `serializers/`, `views/`, `urls.py`, `admin.py`, `management/commands/`,
`fixtures/`. Register as `"apps.acopio"` in `INSTALLED_APPS`.

### FR-010-002: GrainType Model (GLOBAL -- No Tenant FK)

Implement `GrainType` model as specified in Data Model v1.0 Section 5.1. This model
does NOT inherit `TenantBoundModel` (ADR-010). Fields:

| Field | Django Type | Precision | Null | Default | Description |
|-------|-------------|-----------|------|---------|-------------|
| `id` | UUIDField PK | -- | No | uuid4 | Auto-generated |
| `code` | CharField | max_length=5 | No | -- | Internal short code (TRI, MAI, SOJ, etc.) |
| `arca_codigo` | PositiveSmallIntegerField | -- | No | -- | ARCA ncespecie code (15, 19, 23, etc.) |
| `name` | CharField | max_length=100 | No | -- | Full name in Spanish |
| `humedad_base_pct` | DecimalField | (5,2) | No | -- | Base moisture for grading reference |
| `hf_secado_pct` | DecimalField | (5,2) | No | -- | Hf for secado formula. CRITICAL: != humedad_base_pct |
| `manipuleo_fijo_pct` | DecimalField | (5,2) | No | -- | Fixed manipuleo deduction (ADR-014) |
| `volatil_fijo_pct` | DecimalField | (5,2) | No | -- | Fixed volatil deduction (ADR-014) |
| `grading_system` | CharField choices | -- | No | GRADO | GRADO (cereals) or TOLERANCE (oleaginosas) |
| `is_active` | BooleanField | -- | No | True | Soft-disable for rare/deprecated grain types |

Constraints:
- `UniqueConstraint(fields=['code'])` -- internal code is unique
- `UniqueConstraint(fields=['arca_codigo'])` -- ARCA code is unique

NOTE: The Data Model v1.0 specifies `code` as `CharField(max_length=3)`. The
implementation MUST increase this to `max_length=5` to accommodate extended codes like
`CEB_F` and `CEB_C`. The `arca_codigo` field is added to store the ARCA ncespecie
integer code; this field is present in the REST API spec (Section 4.1, field `codigo`)
but was not explicitly listed in the Data Model field table. This is not a deviation --
it reconciles the Data Model with the REST API specification.

### FR-010-003: CampanaConfig Model (Inherits TenantBoundModel)

Implement `CampanaConfig` as specified in Data Model v1.0 Section 5.1. Inherits
`TenantBoundModel` (per-tenant). Fields:

| Field | Django Type | Precision | Null | Default | Description |
|-------|-------------|-----------|------|---------|-------------|
| `id` | UUIDField PK | -- | No | uuid4 | -- |
| `tenant` | ForeignKey(Tenant) PROTECT | -- | No | -- | Owning tenant |
| `campaign_code` | CharField | max_length=7 | No | -- | Format "YYYY/YY" e.g. "2025/26" |
| `start_date` | DateField | -- | No | -- | Campaign start date |
| `end_date` | DateField | -- | No | -- | Campaign end date |
| `is_active` | BooleanField | -- | No | False | Only one active per tenant |
| `notes` | TextField | -- | Yes | -- | Optional notes |

Constraints:
- `UniqueConstraint(fields=['tenant', 'campaign_code'])` -- no duplicate campaigns per
  tenant. NOTE: This constraint is not explicitly listed in the Data Model v1.0 but is a
  necessary addition to prevent duplicate campaign codes within a tenant. The Data Model
  only documents the partial unique constraint below.
- `UniqueConstraint(fields=['tenant', 'is_active'], condition=Q(is_active=True))` -- only
  one active campaign per tenant (ADR-011)

Validators:
- `campaign_code` must match regex `^\d{4}/\d{2}$`
- `end_date` must be after `start_date`

### FR-010-004: ToleranceTable Model (GLOBAL -- No Tenant FK)

Implement `ToleranceTable` as specified in Data Model v1.0 Section 5.2. GLOBAL entity
(ADR-010). Fields:

| Field | Django Type | Precision | Null | Default | Description |
|-------|-------------|-----------|------|---------|-------------|
| `id` | UUIDField PK | -- | No | uuid4 | -- |
| `grain_type` | ForeignKey(GrainType) PROTECT | -- | No | -- | -- |
| `valid_from` | DateField | -- | No | -- | Start of version validity |
| `valid_to` | DateField | -- | Yes | -- | NULL = currently active version |
| `parameter` | CharField | max_length=50 | No | -- | Parameter name (e.g., "humedad", "materias_extranas") |
| `tolerance_pct` | DecimalField | (5,2) | No | -- | Tolerance threshold percentage |
| `grado_base` | IntegerField | -- | No | -- | Reference grade for this tolerance |
| `source_resolution` | CharField | max_length=100 | Yes | -- | SAGPyA/SENASA resolution number |

Versioning: `valid_to = NULL` means currently active. At any point in time, exactly one
version per (grain_type, parameter, grado_base) combination must have `valid_to = NULL`.

### FR-010-005: MermaTable Model (GLOBAL -- No Tenant FK)

Implement `MermaTable` as specified in Data Model v1.0 Section 5.2. GLOBAL entity
(ADR-010, ADR-014). Covers zarandeo thresholds ONLY. Fields:

| Field | Django Type | Precision | Null | Default | Description |
|-------|-------------|-----------|------|---------|-------------|
| `id` | UUIDField PK | -- | No | uuid4 | -- |
| `grain_type` | ForeignKey(GrainType) PROTECT | -- | No | -- | -- |
| `valid_from` | DateField | -- | No | -- | Start of version validity |
| `valid_to` | DateField | -- | Yes | -- | NULL = currently active version |
| `materias_extranas_from_pct` | DecimalField | (5,2) | No | -- | Lower bound of ME% range (inclusive) |
| `materias_extranas_to_pct` | DecimalField | (5,2) | Yes | -- | Upper bound (NULL = unbounded) |
| `zarandeo_deduction_pct` | DecimalField | (5,2) | No | -- | Zarandeo deduction for this ME% range |

### FR-010-006: GrainType Seed Fixture

Create JSON fixture file `backend/apps/acopio/fixtures/grain_types.json` with the
7 primary grain types pre-loaded with all regulatory values:

```json
[
  {
    "code": "TRI", "arca_codigo": 15, "name": "Trigo pan",
    "humedad_base_pct": "14.00", "hf_secado_pct": "13.50",
    "manipuleo_fijo_pct": "0.10", "volatil_fijo_pct": "0.30",
    "grading_system": "GRADO"
  },
  {
    "code": "MAI", "arca_codigo": 19, "name": "Maiz",
    "humedad_base_pct": "14.50", "hf_secado_pct": "13.50",
    "manipuleo_fijo_pct": "0.25", "volatil_fijo_pct": "0.30",
    "grading_system": "GRADO"
  },
  {
    "code": "SOJ", "arca_codigo": 23, "name": "Soja",
    "humedad_base_pct": "13.50", "hf_secado_pct": "12.50",
    "manipuleo_fijo_pct": "0.25", "volatil_fijo_pct": "0.50",
    "grading_system": "TOLERANCE"
  },
  {
    "code": "GIR", "arca_codigo": 2, "name": "Girasol",
    "humedad_base_pct": "11.00", "hf_secado_pct": "10.50",
    "manipuleo_fijo_pct": "0.20", "volatil_fijo_pct": "0.50",
    "grading_system": "TOLERANCE"
  },
  {
    "code": "SOR", "arca_codigo": 22, "name": "Sorgo granifero",
    "humedad_base_pct": "15.00", "hf_secado_pct": "13.50",
    "manipuleo_fijo_pct": "0.25", "volatil_fijo_pct": "0.50",
    "grading_system": "GRADO"
  },
  {
    "code": "CEB_F", "arca_codigo": 11, "name": "Cebada forrajera",
    "humedad_base_pct": "14.00", "hf_secado_pct": "13.50",
    "manipuleo_fijo_pct": "0.20", "volatil_fijo_pct": "0.30",
    "grading_system": "GRADO"
  },
  {
    "code": "CEB_C", "arca_codigo": 17, "name": "Cebada cervecera",
    "humedad_base_pct": "12.00", "hf_secado_pct": "12.00",
    "manipuleo_fijo_pct": "0.00", "volatil_fijo_pct": "0.30",
    "grading_system": "TOLERANCE"
  }
]
```

Source: Research 8.1, RAG query results from `acopio_research` collection.

### FR-010-007: ToleranceTable Seed Fixture

Create JSON fixture `backend/apps/acopio/fixtures/tolerance_tables.json` with initial
tolerance values for the 5 primary grains. Tolerance values sourced from SAGPyA/SENASA
resolutions via RAG query results.

Minimum seed rows (per grain, per grade where applicable):

- **Trigo**: humedad 14.0% base, materias extranas tolerances per grado (1/2/3),
  peso hectolitrico minimums (75/72/69 kg/hl).
- **Maiz**: humedad 14.5% base, materias extranas and granos danados per grado,
  peso hectolitrico minimums.
- **Soja**: humedad 13.5% base, materias extranas 1.0% tolerance, progressive
  rebaja tiers (1% per point up to 3%, then 1.5% per point above 3%).
- **Girasol**: humedad 11.0% base (14.0% tolerance recibo), materias extranas 3.0%.
- **Sorgo**: humedad 15.0% base, materias extranas per grado.

All tolerance rows must have `valid_from = date(2020, 1, 1)` (or earliest applicable
date from the source resolution) and `valid_to = None` (currently active).

### FR-010-008: MermaTable Seed Fixture

Create JSON fixture `backend/apps/acopio/fixtures/merma_tables.json` with zarandeo
deduction bands for the 5 primary grains. Example bands for trigo:

| ME% From | ME% To | Zarandeo Deduction (%) |
|----------|--------|----------------------|
| 0.00 | 1.00 | 0.00 |
| 1.01 | 2.00 | 1.00 |
| 2.01 | 3.00 | 2.00 |
| 3.01 | NULL | 3.00 (+ arbitration) |

Exact thresholds per grain from RAG queries on research 2.5 and 2.2.

### FR-010-009: Management Command `seed_grain_reference`

Create `backend/apps/acopio/management/commands/seed_grain_reference.py`:

- Loads all three fixtures (grain_types, tolerance_tables, merma_tables) idempotently.
- Uses `update_or_create` keyed on `code` (GrainType), or `(grain_type, parameter,
  grado_base, valid_from)` (ToleranceTable), or `(grain_type, materias_extranas_from_pct,
  valid_from)` (MermaTable).
- Accepts `--dry-run` flag to preview without writing.
- Logs each created/updated/skipped record.
- Returns exit code 0 on success.

### FR-010-010: DRF Serializers

Implement read-only serializers for all four models matching the REST API Design v1.0
Section 4 response schemas:

- `GrainTypeSerializer` -- exposes API-spec fields per REST API Design v1.0 Section 4.1.
  Field mappings: `codigo` (API) maps to `arca_codigo` (model), `nombre` (API) maps to
  `name` (model). Additionally exposes `code` and `grading_system` beyond the API-spec
  minimum for frontend consumption.
- `ToleranceTableSerializer` -- nested entries as array.
- `MermaTableSerializer` -- nested entries as array.
- `CampanaConfigSerializer` -- all model fields; tenant-scoped. NOTE: The REST API Design
  v1.0 Section 4.4 response schema includes `grain_type` (UUID) and `label` (string)
  fields. `label` is a computed display field derived from `campaign_code` (e.g.,
  "2025/26" becomes "Campana 2025/2026"). `grain_type` in the API spec is a design
  inconsistency -- CampanaConfig in the Data Model v1.0 has no grain_type FK because
  campaigns are not grain-specific (a campaign covers all grains). The serializer omits
  `grain_type` to match the Data Model. This should be reconciled with the API spec
  authors in a future blueprint update.

### FR-010-011: DRF ViewSets

Implement viewsets matching REST API Design v1.0 Section 4:

- `GrainTypeViewSet` -- read-only (`list`, `retrieve`). No tenant filtering (GLOBAL).
  Query parameter: `?is_active=true`.
- `ToleranceTableViewSet` -- read-only. No tenant filtering (GLOBAL).
  Query parameters: `?grain_type={uuid}&valid_from_before={date}`.
- `MermaTableViewSet` -- read-only. No tenant filtering (GLOBAL).
  Query parameter: `?grain_type={uuid}`.
- `CampanaConfigViewSet` -- full CRUD. Tenant-filtered via `TenantBoundManager`.
  Query parameters: `?is_active=true&active_now=true`.

All viewsets require JWT authentication (`IsAuthenticated`). GLOBAL viewsets use standard
Django `models.Manager` (not `TenantBoundManager`).

### FR-010-012: URL Configuration

Register acopio URLs at `/api/v1/acopio/` using DRF `DefaultRouter`:

```python
# backend/apps/acopio/urls.py
router = DefaultRouter()
router.register(r"grain-types", GrainTypeViewSet, basename="grain-type")
router.register(r"tolerance-tables", ToleranceTableViewSet, basename="tolerance-table")
router.register(r"merma-tables", MermaTableViewSet, basename="merma-table")
router.register(r"campaigns", CampanaConfigViewSet, basename="campaign")
```

### FR-010-013: Django Admin Registration

Register all four models in `admin.py` with appropriate list displays, filters, and
search fields. GrainType admin must display the `arca_codigo` alongside `code` and `name`.

---

## Non-Functional Requirements

### NF-010-001: Global Models Must NOT Use TenantBoundModel

`GrainType`, `ToleranceTable`, and `MermaTable` must use standard `django.db.models.Model`
as their base class (not `TenantBoundModel`). They must use `models.Manager()` as their
default manager. Per ADR-010, these are GLOBAL entities shared across all tenants.

### NF-010-002: CampanaConfig Must Inherit TenantBoundModel

`CampanaConfig` must inherit `TenantBoundModel` and use `TenantBoundManager` as its
default manager. It must include `tenant_id` field and participate in RLS policies.

### NF-010-003: Decimal Precision Convention

All percentage fields: `DecimalField(max_digits=5, decimal_places=2)`.
All weight/money fields: `DecimalField(max_digits=17, decimal_places=3)`.
Per ADR-007.

### NF-010-004: UUID Primary Keys

All models must use `UUIDField(primary_key=True, default=uuid.uuid4, editable=False)`.
Per ADR-002.

### NF-010-005: Test Coverage

Minimum 90% line coverage for all new code in `backend/apps/acopio/`. Tests must use
pytest with `pytest-django`. Follow the patterns in `gravitea-testing` skill.

### NF-010-006: Fixture Idempotency

Running `seed_grain_reference` multiple times must produce the same result. No duplicate
records. Use `update_or_create` with natural key lookups.

### NF-010-007: API Response Pagination

All list endpoints must use page-number pagination (per REST API Design Section 2.6).
Envelope: `{ "count": N, "next": "...", "previous": "...", "results": [...] }`.

### NF-010-008: Type Hints

All function parameters and return values must have type hints. Per project coding standard.

### NF-010-009: Versioned Table Lookup Performance

Tolerance and merma table lookups by `(grain_type, valid_to IS NULL)` must complete in
under 5ms. Add composite index: `(grain_type_id, valid_to)` for both tables.

### NF-010-010: No RLS for Global Tables

PostgreSQL RLS policies must NOT be created for `GrainType`, `ToleranceTable`, or
`MermaTable` tables. Only `CampanaConfig` receives an RLS policy matching the
existing pattern in `backend/database/sql/`.

---

## Key Technical Details

### Application Structure

```
backend/apps/acopio/
|-- __init__.py
|-- apps.py                         # AcopioConfig
|-- models/
|   |-- __init__.py                 # re-export all models
|   |-- grain_type.py               # GrainType (GLOBAL)
|   |-- campana_config.py           # CampanaConfig (TenantBound)
|   |-- tolerance_table.py          # ToleranceTable (GLOBAL)
|   +-- merma_table.py              # MermaTable (GLOBAL)
|-- serializers/
|   |-- __init__.py
|   +-- reference_data.py           # All 4 serializers
|-- views/
|   |-- __init__.py
|   +-- reference_data.py           # All 4 viewsets
|-- urls.py                         # Router registration
|-- admin.py                        # Admin site registration
|-- fixtures/
|   |-- grain_types.json
|   |-- tolerance_tables.json
|   +-- merma_tables.json
+-- management/
    +-- commands/
        +-- seed_grain_reference.py
```

### Model Inheritance Decision Tree

```
Is this a regulatory / government-mandated reference table?
|-- YES (GrainType, ToleranceTable, MermaTable)
|   +-- Inherit django.db.models.Model
|       Use models.Manager() as default manager
|       Do NOT add tenant_id field
|       Do NOT create RLS policy
|
+-- NO (CampanaConfig, and all future operational models)
    +-- Inherit TenantBoundModel
        TenantBoundManager auto-applied
        tenant_id field auto-added
        Create RLS policy in database/sql/
```

### GrainType.code vs arca_codigo Reconciliation

The Data Model v1.0 defines `GrainType.code` as a 3-character internal shortcode (TRI,
MAI, SOJ). The REST API Design v1.0 Section 4.1 response includes `codigo` described as
"ARCA grain code (e.g., 23 for soja)." These are two distinct identifiers:

- `code` (CharField) = internal ERP shortcode for display and filtering
- `arca_codigo` (PositiveSmallIntegerField) = official ARCA ncespecie integer used in
  WSCPE, WSLPG, and WSCDC web service calls

The REST API response field `codigo` maps to the model field `arca_codigo`, not `code`.
The serializer must handle this mapping.

### CampanaConfig Validation

```python
def clean(self):
    # Validate campaign_code format
    if not re.match(r"^\d{4}/\d{2}$", self.campaign_code):
        raise ValidationError("Campaign code must be YYYY/YY format")

    # Validate date range
    if self.end_date <= self.start_date:
        raise ValidationError("end_date must be after start_date")

    # Validate year consistency
    start_year = int(self.campaign_code[:4])
    end_suffix = int(self.campaign_code[5:])
    if end_suffix != (start_year + 1) % 100:
        raise ValidationError("Campaign code years must be consecutive")
```

### WSLPG Campaign Code Conversion

The CampanaConfig stores campaigns as "2024/25" but WSLPG expects "2425". Provide a
property method for conversion:

```python
@property
def wslpg_code(self) -> str:
    """Convert 'YYYY/YY' to 'XXYY' format for WSLPG submission."""
    parts = self.campaign_code.split("/")
    return f"{parts[0][2:]}{parts[1]}"
```

### Migration Strategy

1. Create `0001_initial.py` migration with all four models.
2. Add composite indexes for performance:
   - `ToleranceTable`: `(grain_type_id, valid_to)`, `(grain_type_id, parameter, grado_base, valid_to)`
   - `MermaTable`: `(grain_type_id, valid_to)`, `(grain_type_id, materias_extranas_from_pct, valid_to)`
3. Run `seed_grain_reference` after migration to load initial data.

---

## Acceptance Criteria

### AC-10-001: GrainType Model Complete

GrainType model exists with all specified fields, both unique constraints (`code` and
`arca_codigo`), and does NOT inherit `TenantBoundModel`. Verified by migration and model
unit tests.

### AC-10-002: GrainType Fixture Loaded

Running `python manage.py seed_grain_reference` loads at minimum 7 grain types with
correct ARCA codes, humidity values, Hf values, and fixed merma constants. Verified by
checking `GrainType.objects.count() >= 7` and spot-checking soja (arca_codigo=23,
hf_secado_pct=12.50, not 13.50).

### AC-10-003: CampanaConfig Model with Tenant Isolation

CampanaConfig inherits `TenantBoundModel`. The `UniqueConstraint` for one active campaign
per tenant is enforced. Attempting to activate a second campaign for the same tenant raises
`IntegrityError`. Verified by model unit tests.

### AC-10-004: ToleranceTable Versioning

ToleranceTable supports temporal versioning via `valid_from`/`valid_to`. Querying with
`valid_to__isnull=True` returns only the currently active version. Fixture loads at least
one tolerance entry per grain type for the 5 primary grains.

### AC-10-005: MermaTable Zarandeo Bands

MermaTable contains zarandeo deduction bands for at least the 5 primary grains. Querying
`MermaTable.objects.filter(grain_type__code="TRI", valid_to__isnull=True)` returns
multiple rows representing different materias_extranas ranges with correct deduction
percentages.

### AC-10-006: API Endpoints Functional

All four API endpoints return correct responses:
- `GET /api/v1/acopio/grain-types/` returns paginated grain type list.
- `GET /api/v1/acopio/tolerance-tables/?grain_type={uuid}` returns filtered results.
- `GET /api/v1/acopio/merma-tables/?grain_type={uuid}` returns filtered results.
- `GET /api/v1/acopio/campaigns/?is_active=true` returns tenant-filtered campaigns.
All require JWT authentication. Verified by API integration tests.

### AC-10-007: Global Tables No Tenant Filtering

Requesting `GET /api/v1/acopio/grain-types/` from two different tenants returns the
SAME results. No tenant filtering is applied to GrainType, ToleranceTable, or MermaTable.
Verified by multi-tenant API integration test.

### AC-10-008: CampanaConfig Tenant Isolation

Requesting `GET /api/v1/acopio/campaigns/` from two different tenants returns DIFFERENT
results (each tenant sees only their own campaigns). Cross-tenant access is prevented.
Verified by multi-tenant API integration test.

### AC-10-009: Fixture Idempotency

Running `seed_grain_reference` twice produces no duplicates. Second run updates existing
records without creating new ones. Verified by management command test.

### AC-10-010: Test Suite Passing

All tests in `backend/tests/acopio/` pass with `pytest`. Minimum test count: 20 tests
covering model creation, constraints, fixture loading, API endpoints (list/detail/filter),
serializer field mapping, and tenant isolation for CampanaConfig.

### AC-10-011: Hf vs Humedad Base Correctness

GrainType fixture values are verified: for trigo pan, `hf_secado_pct = 13.50` and
`humedad_base_pct = 14.00` (they must NOT be equal). A dedicated unit test asserts
`hf_secado_pct != humedad_base_pct` for all grains where they differ.

### AC-10-012: ARCA Code Uniqueness

No two GrainType records share the same `arca_codigo`. Attempting to create a duplicate
raises `IntegrityError`. Verified by constraint test.

---

## Dependencies

### Depends On

- **spec-03** (Data Model v1.0) -- entity definitions for GrainType, CampanaConfig,
  ToleranceTable, MermaTable (Sections 5.1--5.2).
- **spec-09** (ARCA Knowledge Update) -- enriched ARCA grain species codes and
  integration field names in blueprint documents.
- **All blueprint specs** (01--08) -- REST API Design Section 4, ADR-010/011/014/015,
  HLD acopio module architecture.

### Blocks

- **spec-11** (Romaneo Core) -- requires GrainType, ToleranceTable, and MermaTable
  models to exist. Romaneo has FK to GrainType and CampanaConfig.
- **spec-12** (Storage & Position) -- requires GrainType for StorageUnit.current_grain_type
  and GrainLot.grain_type FKs.

---

## Agent Team Structure

| Agent | Role | Deliverables |
|-------|------|-------------|
| **A1** | Models & Migrations | `models/grain_type.py`, `models/campana_config.py`, `models/tolerance_table.py`, `models/merma_table.py`, `models/__init__.py`, `apps.py`, `0001_initial.py` migration, RLS policy for CampanaConfig |
| **A2** | API Layer | `serializers/reference_data.py`, `views/reference_data.py`, `urls.py`, `admin.py` -- all 4 serializers, viewsets, router config, admin registration |
| **A3** | Seed Data | `fixtures/grain_types.json`, `fixtures/tolerance_tables.json`, `fixtures/merma_tables.json`, `management/commands/seed_grain_reference.py` -- all fixture files and idempotent load command |
| **A4** | Tests | `tests/acopio/test_models.py`, `tests/acopio/test_api.py`, `tests/acopio/test_fixtures.py`, `tests/acopio/conftest.py` -- model unit tests, API integration tests, fixture idempotency tests, tenant isolation tests |

### Agent Coordination Notes

- A1 must complete models before A2 (serializers depend on models) and A3 (fixtures
  depend on model schema).
- A3 must complete fixtures before A4 (fixture tests depend on fixture files).
- A2 and A3 can work in parallel once A1 delivers models.
- A4 can write test stubs in parallel with A1, then fill in assertions once models and
  API are available.

### Execution Order

```
Phase 1 (sequential): A1 creates models + migration
Phase 2 (parallel):   A2 creates API layer  |  A3 creates fixtures + command
Phase 3 (sequential): A4 writes and runs full test suite
Phase 4 (all):        Integration verification -- all agents confirm AC-10-001 through AC-10-012
```

---

## Execution Notes

**Type**: Implementation -- multi-agent execution (A1--A4)

**Base class reference**: `backend/apps/core/models/mixins.py` lines 28--137
(`TenantBoundModel`), lines 139--148 (`TimestampedModel`), lines 151--169
(`SoftDeleteModel`).

**Manager reference**: `backend/apps/core/managers/tenant_bound.py` lines 202--299
(`TenantBoundManager`), lines 156--199 (`TenantBoundQuerySet`).

**Test pattern reference**: `backend/tests/core/test_tenant_isolation.py` --
`TestTenantBoundManager` and `TestTenantBoundModel` classes demonstrate the testing
patterns for tenant-scoped and IDOR validation tests.

**Writing persona**: Implementation agents should follow `django-expert` skill for
Django 5.2 patterns and `gravitea-testing` skill for pytest conventions.

**RAG discipline**: Agents should run the RAG queries listed above before writing fixture
data. Do NOT invent tolerance/merma values -- use only values confirmed via RAG from
official Camara Arbitral sources.
