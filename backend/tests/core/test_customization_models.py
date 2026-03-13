"""
Test suite for tenant customization models (Phase 2 — 014-tenant-customization).

Covers:
- TenantFieldDefinition: UniqueConstraint, field_key regex, select choices,
  entity_type/field_type choices, Meta ordering, defaults, default_value JSON types
- TenantModuleConfig: UniqueConstraint, invalid module, enabled/settings defaults
- BusinessTemplate: slug uniqueness, NOT tenant-bound, JSON field defaults
"""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.core.models import BusinessTemplate, TenantFieldDefinition, TenantModuleConfig
from apps.core.models.customization import EntityType, FieldType, ModuleChoice


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_field_def(tenant, field_key="peso_kg", entity_type=EntityType.PRODUCT,
                    field_type=FieldType.TEXT, **kwargs):
    """Create a TenantFieldDefinition with the minimum required fields."""
    return TenantFieldDefinition.objects.create(
        tenant=tenant,
        field_key=field_key,
        label="Test Field",
        entity_type=entity_type,
        field_type=field_type,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# TenantFieldDefinition — UniqueConstraint
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTenantFieldDefinitionUniqueConstraint:
    """UniqueConstraint(tenant, entity_type, field_key) enforcement."""

    def test_duplicate_raises_integrity_error(self, tenant):
        """DB-level UniqueConstraint rejects same tenant+entity_type+field_key.

        We bypass model-level full_clean() (which raises ValidationError early)
        via bulk_create, so the IntegrityError originates from the database.
        """
        _make_field_def(tenant, field_key="weight", entity_type=EntityType.PRODUCT)
        duplicate = TenantFieldDefinition(
            tenant=tenant,
            field_key="weight",
            label="Duplicate",
            entity_type=EntityType.PRODUCT,
            field_type=FieldType.TEXT,
        )
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                TenantFieldDefinition.objects.bulk_create([duplicate])

    def test_same_key_different_entity_type_allowed(self, tenant):
        """Same field_key for two different entity_types on the same tenant is fine."""
        fd_product = _make_field_def(tenant, field_key="notes", entity_type=EntityType.PRODUCT)
        fd_customer = _make_field_def(tenant, field_key="notes", entity_type=EntityType.CUSTOMER)
        assert fd_product.pk is not None
        assert fd_customer.pk is not None


# ---------------------------------------------------------------------------
# TenantFieldDefinition — field_key regex validation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTenantFieldDefinitionFieldKeyValidation:
    """field_key RegexValidator: ^[a-z][a-z0-9_]{0,49}$"""

    def test_uppercase_rejected(self, tenant):
        """field_key with uppercase characters should raise ValidationError."""
        with pytest.raises(ValidationError):
            _make_field_def(tenant, field_key="Weight")

    def test_space_rejected(self, tenant):
        """field_key containing a space should raise ValidationError."""
        with pytest.raises(ValidationError):
            _make_field_def(tenant, field_key="my field")

    def test_starts_with_digit_rejected(self, tenant):
        """field_key starting with a digit should raise ValidationError."""
        with pytest.raises(ValidationError):
            _make_field_def(tenant, field_key="1field")

    def test_hyphen_rejected(self, tenant):
        """field_key with a hyphen (not snake_case) should raise ValidationError."""
        with pytest.raises(ValidationError):
            _make_field_def(tenant, field_key="my-field")

    def test_empty_string_rejected(self, tenant):
        """Empty field_key should raise ValidationError."""
        with pytest.raises(ValidationError):
            _make_field_def(tenant, field_key="")

    def test_valid_snake_case_accepted(self, tenant):
        """Valid snake_case key 'peso_kg' should succeed."""
        fd = _make_field_def(tenant, field_key="peso_kg")
        assert fd.pk is not None
        assert fd.field_key == "peso_kg"

    def test_valid_alphanumeric_with_underscore_accepted(self, tenant):
        """Valid key 'my_field_1' should succeed."""
        fd = _make_field_def(tenant, field_key="my_field_1")
        assert fd.pk is not None
        assert fd.field_key == "my_field_1"

    def test_single_letter_accepted(self, tenant):
        """Single lowercase letter is the minimum valid field_key."""
        fd = _make_field_def(tenant, field_key="a")
        assert fd.pk is not None


# ---------------------------------------------------------------------------
# TenantFieldDefinition — Select field_type choices validation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTenantFieldDefinitionSelectValidation:
    """TenantFieldDefinition.clean() enforces choices rules for select fields."""

    def test_select_without_choices_raises(self, tenant):
        """field_type='select' with choices=None should raise ValidationError."""
        with pytest.raises(ValidationError):
            _make_field_def(
                tenant,
                field_key="material",
                field_type=FieldType.SELECT,
                choices=None,
            )

    def test_select_with_empty_list_raises(self, tenant):
        """field_type='select' with choices=[] should raise ValidationError."""
        with pytest.raises(ValidationError):
            _make_field_def(
                tenant,
                field_key="material",
                field_type=FieldType.SELECT,
                choices=[],
            )

    def test_select_with_integer_choices_raises(self, tenant):
        """field_type='select' with non-string choices should raise ValidationError."""
        with pytest.raises(ValidationError):
            _make_field_def(
                tenant,
                field_key="qty_class",
                field_type=FieldType.SELECT,
                choices=[1, 2, 3],
            )

    def test_select_with_valid_string_choices_accepted(self, tenant):
        """field_type='select' with a non-empty list of strings should succeed."""
        fd = _make_field_def(
            tenant,
            field_key="material",
            field_type=FieldType.SELECT,
            choices=["acero", "aluminio", "plastico"],
        )
        assert fd.pk is not None
        assert fd.choices == ["acero", "aluminio", "plastico"]

    def test_non_select_with_choices_is_allowed(self, tenant):
        """Non-select field_type with choices set should NOT raise an error."""
        fd = _make_field_def(
            tenant,
            field_key="size_hint",
            field_type=FieldType.TEXT,
            choices=["S", "M", "L"],
        )
        assert fd.pk is not None


# ---------------------------------------------------------------------------
# TenantFieldDefinition — entity_type and field_type choices enforcement
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTenantFieldDefinitionChoicesEnforcement:
    """Invalid entity_type / field_type values must be rejected by full_clean()."""

    def test_invalid_entity_type_rejected(self, tenant):
        """entity_type not in EntityType choices should raise ValidationError."""
        with pytest.raises(ValidationError):
            TenantFieldDefinition.objects.create(
                tenant=tenant,
                field_key="extra",
                label="Extra",
                entity_type="invoice",  # not a valid EntityType
                field_type=FieldType.TEXT,
            )

    def test_invalid_field_type_rejected(self, tenant):
        """field_type not in FieldType choices should raise ValidationError."""
        with pytest.raises(ValidationError):
            TenantFieldDefinition.objects.create(
                tenant=tenant,
                field_key="extra2",
                label="Extra 2",
                entity_type=EntityType.PRODUCT,
                field_type="json",  # not a valid FieldType
            )

    def test_all_valid_entity_types_accepted(self, tenant):
        """All defined EntityType values should be accepted without error."""
        for i, entity_type in enumerate(EntityType.values):
            fd = TenantFieldDefinition.objects.create(
                tenant=tenant,
                field_key=f"field_{i}",
                label=f"Field {i}",
                entity_type=entity_type,
                field_type=FieldType.TEXT,
            )
            assert fd.entity_type == entity_type

    def test_all_valid_field_types_accepted(self, tenant):
        """All defined FieldType values (except select, which needs choices) should be accepted."""
        non_select_types = [ft for ft in FieldType.values if ft != FieldType.SELECT]
        for i, field_type in enumerate(non_select_types):
            fd = TenantFieldDefinition.objects.create(
                tenant=tenant,
                field_key=f"typed_{i}",
                label=f"Typed {i}",
                entity_type=EntityType.PRODUCT,
                field_type=field_type,
            )
            assert fd.field_type == field_type


# ---------------------------------------------------------------------------
# TenantFieldDefinition — defaults, Meta ordering, and default_value JSON types
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTenantFieldDefinitionMetaAndDefaults:
    """Default field values and Meta ordering."""

    def test_active_defaults_to_true(self, tenant):
        """active should default to True."""
        fd = _make_field_def(tenant, field_key="status_code")
        assert fd.active is True

    def test_required_defaults_to_false(self, tenant):
        """required should default to False."""
        fd = _make_field_def(tenant, field_key="opt_field")
        assert fd.required is False

    def test_section_defaults_to_custom_fields(self, tenant):
        """section should default to 'custom_fields'."""
        fd = _make_field_def(tenant, field_key="my_field")
        assert fd.section == "custom_fields"

    def test_position_defaults_to_zero(self, tenant):
        """position should default to 0."""
        fd = _make_field_def(tenant, field_key="pos_field")
        assert fd.position == 0

    def test_ordering_is_section_position_field_key(self):
        """Meta.ordering must be ['section', 'position', 'field_key']."""
        assert list(TenantFieldDefinition._meta.ordering) == [
            "section",
            "position",
            "field_key",
        ]

    def test_default_value_accepts_null(self, tenant):
        """default_value=None (JSON null) should be stored as None."""
        fd = _make_field_def(tenant, field_key="nullable_field", default_value=None)
        assert fd.default_value is None

    def test_default_value_accepts_string(self, tenant):
        """default_value as a string should round-trip correctly."""
        fd = _make_field_def(tenant, field_key="str_default", default_value="pending")
        assert fd.default_value == "pending"

    def test_default_value_accepts_integer(self, tenant):
        """default_value as an integer should round-trip correctly."""
        fd = _make_field_def(tenant, field_key="int_default", default_value=42)
        assert fd.default_value == 42

    def test_default_value_accepts_list(self, tenant):
        """default_value as a list should round-trip correctly."""
        fd = _make_field_def(tenant, field_key="list_default", default_value=[1, 2, 3])
        assert fd.default_value == [1, 2, 3]


# ---------------------------------------------------------------------------
# TenantModuleConfig
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTenantModuleConfig:
    """TenantModuleConfig model constraints and defaults."""

    def test_duplicate_module_raises_integrity_error(self, tenant):
        """Same tenant + module combination should raise IntegrityError."""
        TenantModuleConfig.objects.create(
            tenant=tenant,
            module=ModuleChoice.INVENTARIO,
        )
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                TenantModuleConfig.objects.create(
                    tenant=tenant,
                    module=ModuleChoice.INVENTARIO,
                )

    def test_invalid_module_rejected_by_full_clean(self, tenant):
        """Module value not in ModuleChoice choices should fail full_clean()."""
        config = TenantModuleConfig(
            tenant=tenant,
            module="accounting",  # not a valid ModuleChoice
        )
        with pytest.raises(ValidationError):
            config.full_clean()

    def test_enabled_defaults_to_true(self, tenant):
        """enabled should default to True."""
        config = TenantModuleConfig.objects.create(
            tenant=tenant,
            module=ModuleChoice.VENTAS,
        )
        assert config.enabled is True

    def test_settings_defaults_to_empty_dict(self, tenant):
        """settings should default to {}."""
        config = TenantModuleConfig.objects.create(
            tenant=tenant,
            module=ModuleChoice.SYNC,
        )
        assert config.settings == {}

    def test_different_modules_same_tenant_allowed(self, tenant):
        """Different modules for the same tenant can each be created."""
        c1 = TenantModuleConfig.objects.create(
            tenant=tenant, module=ModuleChoice.INVENTARIO
        )
        c2 = TenantModuleConfig.objects.create(
            tenant=tenant, module=ModuleChoice.FACTURACION
        )
        assert c1.pk is not None
        assert c2.pk is not None
        assert c1.module != c2.module

    def test_enabled_can_be_set_to_false(self, tenant):
        """enabled=False should be stored correctly."""
        config = TenantModuleConfig.objects.create(
            tenant=tenant,
            module=ModuleChoice.SYNC,
            enabled=False,
        )
        assert config.enabled is False

    def test_settings_accepts_custom_dict(self, tenant):
        """settings should accept an arbitrary dict."""
        custom = {"max_retries": 3, "timeout": 30}
        config = TenantModuleConfig.objects.create(
            tenant=tenant,
            module=ModuleChoice.VENTAS,
            settings=custom,
        )
        assert config.settings == custom


# ---------------------------------------------------------------------------
# BusinessTemplate
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestBusinessTemplate:
    """BusinessTemplate model: slug uniqueness, not tenant-bound, JSON defaults."""

    def test_duplicate_slug_raises_integrity_error(self):
        """Duplicate slug should raise IntegrityError."""
        BusinessTemplate.objects.create(slug="ferreteria", name="Ferretería")
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                BusinessTemplate.objects.create(
                    slug="ferreteria",
                    name="Ferretería Duplicada",
                )

    def test_not_tenant_bound_model(self):
        """BusinessTemplate must NOT inherit from TenantBoundModel."""
        from apps.core.models.mixins import TenantBoundModel

        assert not issubclass(BusinessTemplate, TenantBoundModel)

    def test_no_tenant_field(self):
        """BusinessTemplate must not have a 'tenant' FK or 'tenant_id' field."""
        field_names = [f.name for f in BusinessTemplate._meta.get_fields()]
        assert "tenant" not in field_names

    def test_modules_defaults_to_empty_list(self):
        """modules JSONField should default to []."""
        template = BusinessTemplate.objects.create(
            slug="blank-template",
            name="Blank Template",
        )
        assert template.modules == []

    def test_field_definitions_defaults_to_empty_list(self):
        """field_definitions JSONField should default to []."""
        template = BusinessTemplate.objects.create(
            slug="blank-template-b",
            name="Blank Template B",
        )
        assert template.field_definitions == []

    def test_can_store_modules_list(self):
        """modules should accept and persist a list of module names."""
        template = BusinessTemplate.objects.create(
            slug="retail",
            name="Retail",
            modules=["inventario", "ventas"],
        )
        assert template.modules == ["inventario", "ventas"]

    def test_can_store_field_definitions(self):
        """field_definitions should accept and persist a list of dicts."""
        defs = [
            {
                "field_key": "color",
                "entity_type": "product",
                "field_type": "text",
                "label": "Color",
            }
        ]
        template = BusinessTemplate.objects.create(
            slug="retail-with-fields",
            name="Retail With Fields",
            field_definitions=defs,
        )
        assert template.field_definitions == defs

    def test_different_slugs_coexist(self):
        """Two templates with different slugs should both be creatable."""
        t1 = BusinessTemplate.objects.create(slug="ferreteria", name="Ferretería")
        t2 = BusinessTemplate.objects.create(slug="tienda-ropa", name="Tienda de Ropa")
        assert t1.pk != t2.pk
