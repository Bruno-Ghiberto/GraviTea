"""Idempotent seed command for grain reference data (GrainType, ToleranceTable, MermaTable)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from django.core.management.base import BaseCommand

from apps.acopio.models import GrainType, MermaTable, ToleranceTable

# ---------------------------------------------------------------------------
# Inline data — authoritative values from ARCA / Camara Arbitral
# ---------------------------------------------------------------------------

GRAIN_TYPES: list[dict[str, Any]] = [
    {
        "code": "TRI",
        "arca_codigo": 15,
        "name": "Trigo pan",
        "humedad_base_pct": Decimal("14.00"),
        "hf_secado_pct": Decimal("13.50"),
        "manipuleo_fijo_pct": Decimal("0.10"),
        "volatil_fijo_pct": Decimal("0.30"),
        "grading_system": "GRADO",
        "is_active": True,
    },
    {
        "code": "MAI",
        "arca_codigo": 19,
        "name": "Maiz",
        "humedad_base_pct": Decimal("14.50"),
        "hf_secado_pct": Decimal("13.50"),
        "manipuleo_fijo_pct": Decimal("0.25"),
        "volatil_fijo_pct": Decimal("0.30"),
        "grading_system": "GRADO",
        "is_active": True,
    },
    {
        "code": "SOJ",
        "arca_codigo": 23,
        "name": "Soja",
        "humedad_base_pct": Decimal("13.50"),
        "hf_secado_pct": Decimal("12.50"),  # CRITICAL: 12.50 NOT 13.50
        "manipuleo_fijo_pct": Decimal("0.25"),
        "volatil_fijo_pct": Decimal("0.50"),
        "grading_system": "TOLERANCE",
        "is_active": True,
    },
    {
        "code": "GIR",
        "arca_codigo": 2,
        "name": "Girasol",
        "humedad_base_pct": Decimal("11.00"),
        "hf_secado_pct": Decimal("10.50"),
        "manipuleo_fijo_pct": Decimal("0.20"),
        "volatil_fijo_pct": Decimal("0.50"),
        "grading_system": "TOLERANCE",
        "is_active": True,
    },
    {
        "code": "SOR",
        "arca_codigo": 22,
        "name": "Sorgo granifero",
        "humedad_base_pct": Decimal("15.00"),
        "hf_secado_pct": Decimal("13.50"),
        "manipuleo_fijo_pct": Decimal("0.25"),
        "volatil_fijo_pct": Decimal("0.50"),
        "grading_system": "GRADO",
        "is_active": True,
    },
    {
        "code": "CEB_F",
        "arca_codigo": 11,
        "name": "Cebada forrajera",
        "humedad_base_pct": Decimal("14.00"),
        "hf_secado_pct": Decimal("13.50"),
        "manipuleo_fijo_pct": Decimal("0.20"),
        "volatil_fijo_pct": Decimal("0.30"),
        "grading_system": "GRADO",
        "is_active": True,
    },
    {
        "code": "CEB_C",
        "arca_codigo": 17,
        "name": "Cebada cervecera",
        "humedad_base_pct": Decimal("12.00"),
        "hf_secado_pct": Decimal("12.00"),
        "manipuleo_fijo_pct": Decimal("0.00"),
        "volatil_fijo_pct": Decimal("0.30"),
        "grading_system": "TOLERANCE",
        "is_active": True,
    },
]

# Tolerance entries: (grain_code, parameter, grado_base, tolerance_pct)
# GRADO grains: bonificacion_rebaja per grade (Grado 1 = bonus, 2 = neutral, 3 = penalty)
# TOLERANCE grains: materias_extranas base tolerance (grado_base = 0)
TOLERANCE_ENTRIES: list[dict[str, Any]] = [
    # --- Trigo pan (GRADO) ---
    {"grain_code": "TRI", "parameter": "bonificacion_rebaja", "grado_base": 1, "tolerance_pct": Decimal("1.50")},
    {"grain_code": "TRI", "parameter": "bonificacion_rebaja", "grado_base": 2, "tolerance_pct": Decimal("0.00")},
    {"grain_code": "TRI", "parameter": "bonificacion_rebaja", "grado_base": 3, "tolerance_pct": Decimal("-1.00")},
    # --- Maiz (GRADO) ---
    {"grain_code": "MAI", "parameter": "bonificacion_rebaja", "grado_base": 1, "tolerance_pct": Decimal("1.00")},
    {"grain_code": "MAI", "parameter": "bonificacion_rebaja", "grado_base": 2, "tolerance_pct": Decimal("0.00")},
    {"grain_code": "MAI", "parameter": "bonificacion_rebaja", "grado_base": 3, "tolerance_pct": Decimal("-1.50")},
    # --- Soja (TOLERANCE) ---
    {"grain_code": "SOJ", "parameter": "materias_extranas", "grado_base": 0, "tolerance_pct": Decimal("1.00")},
    # --- Girasol (TOLERANCE) ---
    {"grain_code": "GIR", "parameter": "materias_extranas", "grado_base": 0, "tolerance_pct": Decimal("1.00")},
    # --- Sorgo (GRADO) ---
    {"grain_code": "SOR", "parameter": "bonificacion_rebaja", "grado_base": 1, "tolerance_pct": Decimal("1.00")},
    {"grain_code": "SOR", "parameter": "bonificacion_rebaja", "grado_base": 2, "tolerance_pct": Decimal("0.00")},
    {"grain_code": "SOR", "parameter": "bonificacion_rebaja", "grado_base": 3, "tolerance_pct": Decimal("-1.50")},
]

# Merma zarandeo bands: progressive ranges per grain (same structure for all 5 primary grains)
_MERMA_BANDS: list[dict[str, Decimal | None]] = [
    {"from": Decimal("0.00"), "to": Decimal("1.00"), "deduction": Decimal("0.00")},
    {"from": Decimal("1.01"), "to": Decimal("2.00"), "deduction": Decimal("1.00")},
    {"from": Decimal("2.01"), "to": Decimal("3.00"), "deduction": Decimal("2.00")},
    {"from": Decimal("3.01"), "to": None, "deduction": Decimal("3.00")},
]

MERMA_ENTRIES: list[dict[str, Any]] = [
    {
        "grain_code": grain_code,
        "materias_extranas_from_pct": band["from"],
        "materias_extranas_to_pct": band["to"],
        "zarandeo_deduction_pct": band["deduction"],
    }
    for grain_code in ("TRI", "MAI", "SOJ", "GIR", "SOR")
    for band in _MERMA_BANDS
]

_VALID_FROM = date(2020, 1, 1)


class Command(BaseCommand):
    help = "Load grain reference data (grain types, tolerances, merma bands) idempotently."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without writing to database.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        dry_run: bool = options["dry_run"]
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN -- no changes will be written"))

        self._load_grain_types(dry_run)
        self._load_tolerance_tables(dry_run)
        self._load_merma_tables(dry_run)

        self.stdout.write(self.style.SUCCESS("Seed operation complete."))

    def _load_grain_types(self, dry_run: bool) -> None:
        self.stdout.write("Loading grain types...")
        for grain_data in GRAIN_TYPES:
            code = grain_data["code"]
            if dry_run:
                self.stdout.write(f"  Would create/update: {code}")
                continue
            obj, created = GrainType.objects.update_or_create(
                code=code,
                defaults={k: v for k, v in grain_data.items() if k != "code"},
            )
            action = "Created" if created else "Updated"
            self.stdout.write(f"  {action}: {obj}")

    def _load_tolerance_tables(self, dry_run: bool) -> None:
        self.stdout.write("Loading tolerance tables...")
        for entry in TOLERANCE_ENTRIES:
            grain_code = entry["grain_code"]
            if dry_run:
                self.stdout.write(
                    f"  Would create/update: {grain_code} "
                    f"{entry['parameter']} G{entry['grado_base']}"
                )
                continue
            grain_type = GrainType.objects.get(code=grain_code)
            obj, created = ToleranceTable.objects.update_or_create(
                grain_type=grain_type,
                parameter=entry["parameter"],
                grado_base=entry["grado_base"],
                valid_from=_VALID_FROM,
                defaults={
                    "tolerance_pct": entry["tolerance_pct"],
                    "valid_to": None,
                    "source_resolution": None,
                },
            )
            action = "Created" if created else "Updated"
            self.stdout.write(f"  {action}: {obj}")

    def _load_merma_tables(self, dry_run: bool) -> None:
        self.stdout.write("Loading merma tables...")
        for entry in MERMA_ENTRIES:
            grain_code = entry["grain_code"]
            if dry_run:
                self.stdout.write(
                    f"  Would create/update: {grain_code} "
                    f"ME {entry['materias_extranas_from_pct']}%"
                )
                continue
            grain_type = GrainType.objects.get(code=grain_code)
            obj, created = MermaTable.objects.update_or_create(
                grain_type=grain_type,
                materias_extranas_from_pct=entry["materias_extranas_from_pct"],
                valid_from=_VALID_FROM,
                defaults={
                    "materias_extranas_to_pct": entry["materias_extranas_to_pct"],
                    "zarandeo_deduction_pct": entry["zarandeo_deduction_pct"],
                    "valid_to": None,
                },
            )
            action = "Created" if created else "Updated"
            self.stdout.write(f"  {action}: {obj}")
