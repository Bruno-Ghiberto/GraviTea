---
agent: A3
type: python-expert
model: Sonnet 4.6
mission: "Create seed fixtures and idempotent management command for spec-10"
wave: 2
tasks: [T013, T014, T015, T016, T017, T018]
---

# A3: Seed Data

## Context Files (read FIRST)

Read these files before writing any code:

1. `Docs/PROMPTS/spec-10-grain-reference/10-specify.md` -- FR-010-006 through FR-010-009,
   Critical Domain Facts (ARCA codes, moisture constants, merma formula, campaign years)
2. `Docs/PROMPTS/spec-10-grain-reference/10-plan.md` -- Pattern 7 (Fixture Format),
   Pattern 8 (Management Command)
3. `specs/010-grain-reference/tasks.md` -- tasks T013-T018

## Mission

Create all seed data infrastructure:

1. Run RAG queries FIRST (MANDATORY before writing fixtures)
2. Create 3 fixture files (T013-T015)
3. Create management command directory and init files (T016)
4. Create management command (T017)
5. Write fixture tests (T018)

---

## Assigned Tasks

| Task | User Story | Description |
|------|-----------|-------------|
| T013 | US5 | Create grain type fixture in `backend/apps/acopio/fixtures/grain_types.json` |
| T014 | US5 | Create tolerance table fixture in `backend/apps/acopio/fixtures/tolerance_tables.json` |
| T015 | US5 | Create merma table fixture in `backend/apps/acopio/fixtures/merma_tables.json` |
| T016 | US5 | Create `backend/apps/acopio/management/__init__.py` and `backend/apps/acopio/management/commands/__init__.py` |
| T017 | US5 | Create management command in `backend/apps/acopio/management/commands/seed_grain_reference.py` |
| T018 | US5 | Write fixture and seed command tests in `backend/tests/acopio/test_fixtures.py` |

---

## Domain Knowledge

### RAG Queries (MANDATORY -- run ALL before writing fixtures)

You MUST run these queries and use the results to populate fixture data. Do NOT
invent regulatory values.

```bash
.venv/bin/python scripts/qdrant/qdrant_search.py -q "grain types codes ARCA humidity base" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "tolerance tables bonification rebaja" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "merma calculation formula sequential" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "grain quality parameters humidity moisture" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "ARCA grain commodity codes grain type nomenclature" -l 5
```

### Critical Domain Facts (minimum context from 10-specify.md)

#### ARCA Grain Species Codes (ncespecie)

| Grain | Spanish Name | ARCA Code | Internal Code |
|-------|-------------|-----------|---------------|
| Bread wheat | Trigo pan | 15 | TRI |
| Corn | Maiz | 19 | MAI |
| Soybean | Soja | 23 | SOJ |
| Sunflower | Girasol (in shell) | 2 | GIR |
| Grain sorghum | Sorgo granifero | 22 | SOR |
| Feed barley | Cebada forrajera | 11 | CEB_F |
| Malting barley | Cebada cervecera | 17 | CEB_C |

#### Moisture, Hf, and Fixed Merma Constants per Grain

| Grain | Code | Humedad Base (%) | Hf Secado (%) | Manipuleo (%) | Volatil (%) | Grading |
|-------|------|-----------------|--------------|---------------|-------------|---------|
| Soja | SOJ | 13.50 | **12.50** | 0.25 | 0.50 | TOLERANCE |
| Maiz | MAI | 14.50 | 13.50 | 0.25 | 0.30 | GRADO |
| Trigo pan | TRI | 14.00 | 13.50 | 0.10 | 0.30 | GRADO |
| Girasol | GIR | 11.00 | 10.50 | 0.20 | 0.50 | TOLERANCE |
| Sorgo | SOR | 15.00 | 13.50 | 0.25 | 0.50 | GRADO |
| Cebada forrajera | CEB_F | 14.00 | 13.50 | 0.20 | 0.30 | GRADO |
| Cebada cervecera | CEB_C | 12.00 | 12.00 | 0.00 | 0.30 | TOLERANCE |

**CRITICAL**: Soja `hf_secado_pct` = **12.50** (NOT 13.50). Using the wrong value
produces approximately 168 kg error per 30-tonne truck. This is verified by a
dedicated test (AC-10-011). The Data Model v1.0 lists Soja Hf as 13.0%, but the
implementation uses 12.5% based on Research 2.5 "Tabla de parametros por grano para
la base de datos" (the software-implementation reference from the Camara Arbitral).

#### Grading System

- **Cereals** (trigo, maiz, sorgo, cebada forrajera) use `GRADO`: Grado 1 = bonificacion,
  Grado 2 = neutral, Grado 3 = rebaja.
- **Oleaginosas** (soja, girasol) and cebada cervecera use `TOLERANCE`: progressive
  rebaja per percentage point above tolerance threshold.

Grade-based bonification/rebaja values:

| Grain | Grado 1 | Grado 2 | Grado 3 |
|-------|---------|---------|---------|
| Trigo pan | +1.5% | 0% | -1.0% |
| Maiz | +1.0% | 0% | -1.5% |
| Sorgo | +1.0% | 0% | -1.5% |

#### Merma Zarandeo Bands (example for trigo)

| ME% From | ME% To | Zarandeo Deduction (%) |
|----------|--------|----------------------|
| 0.00 | 1.00 | 0.00 |
| 1.01 | 2.00 | 1.00 |
| 2.01 | 3.00 | 2.00 |
| 3.01 | NULL | 3.00 (+ arbitration) |

Exact thresholds per grain may vary -- use RAG query results.

#### Merma Calculation Order (for reference -- the engine is spec-11 scope)

```
Peso_final = Peso_bruto * (1 - %Z) * (1 - %S) * (1 - %M) * (1 - %V)
```

1. Zarandeo (%Z) -- only if materias_extranas > tolerancia
2. Secado (%S) -- only if humedad > tolerancia; formula: %S = (Hi - Hf) / (100 - Hf) * 100
3. Manipuleo (%M) -- only if secado was applied; fixed from GrainType
4. Volatil (%V) -- always applied; fixed from GrainType

---

## Files to Create

```
backend/apps/acopio/fixtures/grain_types.json
backend/apps/acopio/fixtures/tolerance_tables.json
backend/apps/acopio/fixtures/merma_tables.json
backend/apps/acopio/management/__init__.py
backend/apps/acopio/management/commands/__init__.py
backend/apps/acopio/management/commands/seed_grain_reference.py
backend/tests/acopio/test_fixtures.py
```

---

## Key Patterns

### Pattern: Fixture Format (T013-T015)

Fixtures use standard Django JSON format with `model`, `pk`, and `fields` keys.
The `model` key uses the app label (`gravitea_acopio`) not the app name (`apps.acopio`).

```json
[
  {
    "model": "gravitea_acopio.graintype",
    "pk": "a1b2c3d4-...",
    "fields": {
      "code": "TRI",
      "arca_codigo": 15,
      "name": "Trigo pan",
      "humedad_base_pct": "14.00",
      "hf_secado_pct": "13.50",
      "manipuleo_fijo_pct": "0.10",
      "volatil_fijo_pct": "0.30",
      "grading_system": "GRADO",
      "is_active": true
    }
  }
]
```

HOWEVER, the management command should use `update_or_create` with Python dicts rather
than `loaddata` -- this gives better control over idempotency, logging, and the
`--dry-run` flag. The JSON fixture files serve as the data source that the command
reads, or the command can inline the data as Python dicts.

### Pattern: Management Command with update_or_create (T017)

```python
import json
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.acopio.models import GrainType, MermaTable, ToleranceTable


class Command(BaseCommand):
    help = "Load grain reference data (grain types, tolerances, merma bands) idempotently."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without writing to database.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN -- no changes will be written"))

        self._load_grain_types(dry_run)
        self._load_tolerance_tables(dry_run)
        self._load_merma_tables(dry_run)

        self.stdout.write(self.style.SUCCESS("Seed operation complete."))

    def _load_grain_types(self, dry_run: bool) -> None:
        self.stdout.write("Loading grain types...")
        # Use inline data or load from JSON fixture
        for grain_data in GRAIN_TYPES:
            if dry_run:
                self.stdout.write(f"  Would create/update: {grain_data['code']}")
                continue
            obj, created = GrainType.objects.update_or_create(
                code=grain_data["code"],
                defaults={k: v for k, v in grain_data.items() if k != "code"},
            )
            action = "Created" if created else "Updated"
            self.stdout.write(f"  {action}: {obj}")

    def _load_tolerance_tables(self, dry_run: bool) -> None:
        self.stdout.write("Loading tolerance tables...")
        for entry in TOLERANCE_ENTRIES:
            grain_type = GrainType.objects.get(code=entry["grain_code"])
            lookup = {
                "grain_type": grain_type,
                "parameter": entry["parameter"],
                "grado_base": entry["grado_base"],
                "valid_from": entry["valid_from"],
            }
            defaults = {
                "tolerance_pct": entry["tolerance_pct"],
                "valid_to": entry.get("valid_to"),
                "source_resolution": entry.get("source_resolution"),
            }
            if dry_run:
                self.stdout.write(
                    f"  Would create/update: {entry['grain_code']} "
                    f"{entry['parameter']} G{entry['grado_base']}"
                )
                continue
            obj, created = ToleranceTable.objects.update_or_create(
                **lookup, defaults=defaults,
            )
            action = "Created" if created else "Updated"
            self.stdout.write(f"  {action}: {obj}")

    def _load_merma_tables(self, dry_run: bool) -> None:
        self.stdout.write("Loading merma tables...")
        for entry in MERMA_ENTRIES:
            grain_type = GrainType.objects.get(code=entry["grain_code"])
            lookup = {
                "grain_type": grain_type,
                "materias_extranas_from_pct": entry["materias_extranas_from_pct"],
                "valid_from": entry["valid_from"],
            }
            defaults = {
                "materias_extranas_to_pct": entry.get("materias_extranas_to_pct"),
                "zarandeo_deduction_pct": entry["zarandeo_deduction_pct"],
                "valid_to": entry.get("valid_to"),
            }
            if dry_run:
                self.stdout.write(
                    f"  Would create/update: {entry['grain_code']} "
                    f"ME {entry['materias_extranas_from_pct']}%"
                )
                continue
            obj, created = MermaTable.objects.update_or_create(
                **lookup, defaults=defaults,
            )
            action = "Created" if created else "Updated"
            self.stdout.write(f"  {action}: {obj}")
```

The `GRAIN_TYPES`, `TOLERANCE_ENTRIES`, and `MERMA_ENTRIES` data structures should
be defined at module level in the same file (or loaded from the JSON fixtures).
Populate them with values from the RAG queries.

### Pattern: Fixture Test (T018)

```python
import pytest
from decimal import Decimal

from django.core.management import call_command

from apps.acopio.models import GrainType, MermaTable, ToleranceTable


@pytest.mark.django_db
class TestSeedGrainReference:
    """Tests for the seed_grain_reference management command."""

    def test_seed_creates_grain_types(self):
        call_command("seed_grain_reference")
        assert GrainType.objects.count() >= 7

    def test_seed_idempotency(self):
        call_command("seed_grain_reference")
        count_after_first = GrainType.objects.count()
        call_command("seed_grain_reference")
        count_after_second = GrainType.objects.count()
        assert count_after_first == count_after_second

    def test_seed_dry_run(self):
        call_command("seed_grain_reference", dry_run=True)
        assert GrainType.objects.count() == 0

    def test_soja_hf_correctness(self):
        call_command("seed_grain_reference")
        soja = GrainType.objects.get(code="SOJ")
        assert soja.hf_secado_pct == Decimal("12.50"), (
            f"Soja Hf must be 12.50, got {soja.hf_secado_pct}"
        )

    def test_tolerance_entries_exist(self):
        call_command("seed_grain_reference")
        for code in ["TRI", "MAI", "SOJ", "GIR", "SOR"]:
            gt = GrainType.objects.get(code=code)
            assert ToleranceTable.objects.filter(grain_type=gt).count() > 0

    def test_merma_bands_no_gaps(self):
        call_command("seed_grain_reference")
        trigo = GrainType.objects.get(code="TRI")
        bands = MermaTable.objects.filter(
            grain_type=trigo, valid_to__isnull=True
        ).order_by("materias_extranas_from_pct")
        assert bands.count() > 0
        # Verify progressive ranges
        for i in range(1, len(bands)):
            # Each band's from_pct should be close to previous band's to_pct
            prev_to = bands[i - 1].materias_extranas_to_pct
            curr_from = bands[i].materias_extranas_from_pct
            if prev_to is not None:
                assert curr_from > prev_to or curr_from == prev_to
```

---

## Constraints

- Do NOT invent regulatory values -- use ONLY RAG query results and the inlined
  domain facts above.
- Fixture format: use Python dicts with `update_or_create` in the management command,
  NOT Django `loaddata`. The JSON fixture files serve as documentation/backup.
- Natural keys for `update_or_create`:
  - GrainType: `code`
  - ToleranceTable: `(grain_type, parameter, grado_base, valid_from)`
  - MermaTable: `(grain_type, materias_extranas_from_pct, valid_from)`
- `--dry-run` flag MUST prevent all database writes.
- Idempotent: running twice MUST produce the same result, zero duplicates.
- All tolerance/merma rows must have `valid_from = date(2020, 1, 1)` and
  `valid_to = None` (currently active).
- All function parameters and return values must have type hints.
- All Python commands must use `.venv/bin/python`, never system python.

---

## Gate 2 (Seed) Checks

Run these commands after completing all tasks. Report PASS/FAIL for each.

```bash
# 1. Verify dry-run mode works
cd backend && ../.venv/bin/python manage.py seed_grain_reference --dry-run

# 2. Verify actual seed (requires database)
cd backend && ../.venv/bin/python manage.py seed_grain_reference
cd backend && ../.venv/bin/python -c "
from apps.acopio.models import GrainType, ToleranceTable, MermaTable
gt_count = GrainType.objects.count()
tt_count = ToleranceTable.objects.count()
mt_count = MermaTable.objects.count()
assert gt_count >= 7, f'Expected >= 7 grain types, got {gt_count}'
assert tt_count > 0, f'Expected > 0 tolerance entries, got {tt_count}'
assert mt_count > 0, f'Expected > 0 merma entries, got {mt_count}'
# Critical: Soja Hf must be 12.50, not 13.50
from decimal import Decimal
soja = GrainType.objects.get(code='SOJ')
assert soja.hf_secado_pct == Decimal('12.50'), f'Soja Hf must be 12.50, got {soja.hf_secado_pct}'
print(f'Gate 2 (Seed): PASS -- {gt_count} grains, {tt_count} tolerances, {mt_count} merma bands')
"
```

**Pass criteria**: Dry-run produces no database writes. Actual seed loads >= 7 grain
types, > 0 tolerance entries, > 0 merma bands. Soja Hf = 12.50.
