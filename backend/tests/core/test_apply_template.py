"""
T023 — Tests for the apply_template management command.

Verifies that the `apply_template` command correctly bootstraps a tenant with
module configs and field definitions from the embedded "ferreteria" template.

Covered scenarios:
- First run creates the expected number of module configs and field definitions
- Second run is idempotent (get_or_create — no duplicates, stdout says "Already exists")
- Invalid slug raises CommandError (surfaced as SystemExit)
- Field definition attributes match the embedded template data exactly
- Module configs (inventario, ventas, facturacion) are all created with enabled=True
"""

import pytest
from django.core.management import call_command
from io import StringIO

from apps.core.models import TenantFieldDefinition, TenantModuleConfig


@pytest.mark.django_db
class TestApplyTemplateCommand:
    """T023: Tests for the apply_template management command."""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _run(slug: str, tenant_id: str, *, capture_stdout: bool = True):
        """Invoke apply_template and return captured stdout string."""
        out = StringIO()
        call_command(
            "apply_template",
            slug,
            f"--tenant-id={tenant_id}",
            stdout=out,
        )
        return out.getvalue()

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    def test_first_run_creates_module_configs_and_field_definitions(
        self, tenant_context
    ):
        """First application of ferreteria template creates expected objects.

        The embedded ferreteria template contains:
        - 3 module configs  (inventario, ventas, facturacion)
        - 7 field definitions (peso_kg, largo_cm, ancho_cm, alto_cm,
                               material, marca, codigo_proveedor)
        """
        self._run("ferreteria", str(tenant_context.id))

        module_count = TenantModuleConfig.objects.filter(
            tenant=tenant_context
        ).count()
        field_count = TenantFieldDefinition.objects.filter(
            tenant=tenant_context
        ).count()

        assert module_count == 3, (
            f"Expected 3 module configs, got {module_count}"
        )
        assert field_count == 7, (
            f"Expected 7 field definitions, got {field_count}"
        )

    def test_second_run_is_idempotent(self, tenant_context):
        """Re-applying the same template does not create duplicate records.

        get_or_create semantics mean the command is safe to run multiple times.
        The output must contain 'Already exists' messages on the second run.
        """
        self._run("ferreteria", str(tenant_context.id))

        # Second run
        output = self._run("ferreteria", str(tenant_context.id))

        module_count = TenantModuleConfig.objects.filter(
            tenant=tenant_context
        ).count()
        field_count = TenantFieldDefinition.objects.filter(
            tenant=tenant_context
        ).count()

        assert module_count == 3, "Idempotency violated: unexpected module count"
        assert field_count == 7, "Idempotency violated: unexpected field count"
        assert "Already exists" in output, (
            "Expected 'Already exists' in second-run output"
        )

    def test_invalid_slug_raises_command_error(self, tenant_context):
        """An unrecognised template slug must cause the command to fail.

        call_command raises CommandError directly for invalid slugs.
        """
        from django.core.management.base import CommandError

        with pytest.raises(CommandError, match="not found"):
            call_command(
                "apply_template",
                "nonexistent_slug_xyz",
                f"--tenant-id={str(tenant_context.id)}",
            )

    def test_field_definition_attributes_match_template(self, tenant_context):
        """Created field definitions have the exact attributes from the template.

        Spot-checks the 'material' field (select type with choices) and the
        'peso_kg' field (decimal type in dimensiones section) for correctness.
        """
        self._run("ferreteria", str(tenant_context.id))

        # Verify 'material' — select field with choices
        material = TenantFieldDefinition.objects.get(
            tenant=tenant_context,
            field_key="material",
        )
        assert material.label == "Material"
        assert material.entity_type == "product"
        assert material.field_type == "select"
        assert material.section == "caracteristicas"
        assert material.position == 0
        assert material.choices == [
            "acero", "aluminio", "bronce", "cobre", "hierro", "plastico", "madera"
        ]

        # Verify 'peso_kg' — decimal field in dimensiones section
        peso = TenantFieldDefinition.objects.get(
            tenant=tenant_context,
            field_key="peso_kg",
        )
        assert peso.label == "Peso (kg)"
        assert peso.entity_type == "product"
        assert peso.field_type == "decimal"
        assert peso.section == "dimensiones"
        assert peso.position == 0
        assert peso.choices is None

    def test_module_configs_are_all_enabled(self, tenant_context):
        """All three module configs created by the template are enabled=True.

        Verifies inventario, ventas, and facturacion modules are present
        and enabled after applying the ferreteria template.
        """
        self._run("ferreteria", str(tenant_context.id))

        expected_modules = {"inventario", "ventas", "facturacion"}
        configs = TenantModuleConfig.objects.filter(tenant=tenant_context)

        created_modules = {c.module for c in configs}
        assert created_modules == expected_modules, (
            f"Expected modules {expected_modules}, got {created_modules}"
        )
        for config in configs:
            assert config.enabled is True, (
                f"Module '{config.module}' should be enabled but enabled={config.enabled}"
            )
