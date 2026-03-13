"""
Tests for CustomFieldsMixin (apps/core/serializers/customization.py).

Covers:
- Valid/invalid values for all 6 field types (text, integer, decimal, boolean, date, select)
- Merge semantics on update (merge, null-remove, unstated keys preserved)
- Default injection on create (absent keys only, not on update)
- Inactive field skipping (active=False excluded from validation)
- Error format: {"custom_data": {"key": ["msg"]}}
- Cache hit/miss behavior
- Undefined keys silently ignored
- Required field enforcement
"""

import pytest
from decimal import Decimal
from unittest import mock

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.core.models import TenantFieldDefinition
from apps.core.models.customization import EntityType, FieldType
from apps.core.serializers.customization import CustomFieldsMixin
from apps.inventario.models import Product


# ---------------------------------------------------------------------------
# Minimal test serializer — does NOT override validate(), so mixin is called
# ---------------------------------------------------------------------------


class MinimalProductSerializer(CustomFieldsMixin, serializers.ModelSerializer):
    """Minimal serializer to test CustomFieldsMixin cleanly."""

    entity_type = "product"

    class Meta:
        model = Product
        fields = [
            "sku",
            "name",
            "unit_price",
            "cost_price",
            "tax_rate",
            "custom_data",
            "is_active",
        ]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_request(user):
    """Create a minimal request-like object carrying an authenticated user."""
    return type("Request", (), {"user": user})()


def _make_field_def(tenant, field_key, field_type, **kwargs):
    """Create a TenantFieldDefinition with minimal required fields."""
    return TenantFieldDefinition.objects.create(
        tenant=tenant,
        field_key=field_key,
        label=field_key.replace("_", " ").title(),
        entity_type=EntityType.PRODUCT,
        field_type=field_type,
        **kwargs,
    )


def _base_attrs(custom_data=None):
    """Return a minimal attrs dict (post-field-validation) for validate() calls."""
    attrs = {
        "sku": "TEST-001",
        "name": "Test Product",
        "unit_price": Decimal("10.000"),
        "cost_price": Decimal("5.000"),
        "tax_rate": Decimal("21.00"),
        "is_active": True,
    }
    if custom_data is not None:
        attrs["custom_data"] = custom_data
    return attrs


# ---------------------------------------------------------------------------
# Unit tests: _validate_field_value() — no DB required
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestValidateFieldValueUnit:
    """Unit tests for CustomFieldsMixin._validate_field_value (no DB)."""

    def _defn(self, field_type, choices=None):
        """Return a mock definition with the given field_type."""
        defn = mock.Mock()
        defn.field_type = field_type
        defn.choices = choices
        return defn

    # --- text ---

    def test_text_valid_string(self):
        assert CustomFieldsMixin._validate_field_value(self._defn("text"), "hello") is None

    def test_text_invalid_integer(self):
        err = CustomFieldsMixin._validate_field_value(self._defn("text"), 42)
        assert err == "Expected a text value."

    def test_text_invalid_none(self):
        err = CustomFieldsMixin._validate_field_value(self._defn("text"), None)
        assert err == "Expected a text value."

    # --- integer ---

    def test_integer_valid(self):
        assert CustomFieldsMixin._validate_field_value(self._defn("integer"), 5) is None

    def test_integer_valid_negative(self):
        assert CustomFieldsMixin._validate_field_value(self._defn("integer"), -10) is None

    def test_integer_invalid_string(self):
        err = CustomFieldsMixin._validate_field_value(self._defn("integer"), "5")
        assert err == "Expected an integer value."

    def test_integer_invalid_bool(self):
        """bool is subclass of int but must be rejected for integer fields."""
        err = CustomFieldsMixin._validate_field_value(self._defn("integer"), True)
        assert err == "Expected an integer value."

    # --- decimal ---

    def test_decimal_valid_int(self):
        assert CustomFieldsMixin._validate_field_value(self._defn("decimal"), 10) is None

    def test_decimal_valid_float(self):
        assert CustomFieldsMixin._validate_field_value(self._defn("decimal"), 3.14) is None

    def test_decimal_valid_decimal_type(self):
        assert CustomFieldsMixin._validate_field_value(self._defn("decimal"), Decimal("9.99")) is None

    def test_decimal_invalid_string(self):
        err = CustomFieldsMixin._validate_field_value(self._defn("decimal"), "3.14")
        assert err == "Expected a decimal value."

    def test_decimal_invalid_bool(self):
        """bool must be rejected even though it is a numeric subtype."""
        err = CustomFieldsMixin._validate_field_value(self._defn("decimal"), False)
        assert err == "Expected a decimal value."

    # --- boolean ---

    def test_boolean_valid_true(self):
        assert CustomFieldsMixin._validate_field_value(self._defn("boolean"), True) is None

    def test_boolean_valid_false(self):
        assert CustomFieldsMixin._validate_field_value(self._defn("boolean"), False) is None

    def test_boolean_invalid_integer(self):
        err = CustomFieldsMixin._validate_field_value(self._defn("boolean"), 1)
        assert err == "Expected a boolean value."

    def test_boolean_invalid_string(self):
        err = CustomFieldsMixin._validate_field_value(self._defn("boolean"), "true")
        assert err == "Expected a boolean value."

    # --- date ---

    def test_date_valid_format(self):
        assert CustomFieldsMixin._validate_field_value(self._defn("date"), "2024-01-15") is None

    def test_date_invalid_format_slash(self):
        err = CustomFieldsMixin._validate_field_value(self._defn("date"), "01/15/2024")
        assert err == "Expected a date in YYYY-MM-DD format."

    def test_date_invalid_format_dmy(self):
        err = CustomFieldsMixin._validate_field_value(self._defn("date"), "15-01-2024")
        assert err == "Expected a date in YYYY-MM-DD format."

    def test_date_invalid_type_integer(self):
        err = CustomFieldsMixin._validate_field_value(self._defn("date"), 20240115)
        assert err == "Expected a date in YYYY-MM-DD format."

    # --- select ---

    def test_select_valid_choice(self):
        defn = self._defn("select", choices=["acero", "aluminio"])
        assert CustomFieldsMixin._validate_field_value(defn, "acero") is None

    def test_select_invalid_choice(self):
        defn = self._defn("select", choices=["acero", "aluminio"])
        err = CustomFieldsMixin._validate_field_value(defn, "plastico")
        assert err is not None
        assert "acero" in err or "aluminio" in err

    def test_select_empty_choices_rejects_any_value(self):
        defn = self._defn("select", choices=[])
        err = CustomFieldsMixin._validate_field_value(defn, "anything")
        assert err is not None


# ---------------------------------------------------------------------------
# Integration tests: full validation via MinimalProductSerializer
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestCustomFieldsValidation:
    """Integration tests for mixin validate() through MinimalProductSerializer."""

    def _run_validate(self, admin_user, custom_data):
        """Invoke serializer.validate() with the given custom_data."""
        request = _make_request(admin_user)
        serializer = MinimalProductSerializer(context={"request": request})
        return serializer.validate(_base_attrs(custom_data=custom_data))

    # --- Valid values for all 6 field types ---

    def test_valid_text_passes(self, admin_user, tenant_context):
        _make_field_def(tenant_context, "color", FieldType.TEXT)
        result = self._run_validate(admin_user, {"color": "red"})
        assert result["custom_data"]["color"] == "red"

    def test_valid_integer_passes(self, admin_user, tenant_context):
        _make_field_def(tenant_context, "weight_kg", FieldType.INTEGER)
        result = self._run_validate(admin_user, {"weight_kg": 5})
        assert result["custom_data"]["weight_kg"] == 5

    def test_valid_decimal_passes(self, admin_user, tenant_context):
        _make_field_def(tenant_context, "cost_factor", FieldType.DECIMAL)
        result = self._run_validate(admin_user, {"cost_factor": 1.5})
        assert result["custom_data"]["cost_factor"] == 1.5

    def test_valid_boolean_passes(self, admin_user, tenant_context):
        _make_field_def(tenant_context, "is_fragile", FieldType.BOOLEAN)
        result = self._run_validate(admin_user, {"is_fragile": True})
        assert result["custom_data"]["is_fragile"] is True

    def test_valid_date_passes(self, admin_user, tenant_context):
        _make_field_def(tenant_context, "expiry_date", FieldType.DATE)
        result = self._run_validate(admin_user, {"expiry_date": "2024-12-31"})
        assert result["custom_data"]["expiry_date"] == "2024-12-31"

    def test_valid_select_passes(self, admin_user, tenant_context):
        _make_field_def(tenant_context, "material", FieldType.SELECT, choices=["acero", "aluminio"])
        result = self._run_validate(admin_user, {"material": "acero"})
        assert result["custom_data"]["material"] == "acero"

    # --- Invalid values for all 6 field types ---

    def test_invalid_text_value_raises(self, admin_user, tenant_context):
        _make_field_def(tenant_context, "color", FieldType.TEXT)
        with pytest.raises(ValidationError) as exc:
            self._run_validate(admin_user, {"color": 123})
        assert "custom_data" in exc.value.detail
        assert "color" in exc.value.detail["custom_data"]

    def test_invalid_integer_value_raises(self, admin_user, tenant_context):
        _make_field_def(tenant_context, "qty_class", FieldType.INTEGER)
        with pytest.raises(ValidationError) as exc:
            self._run_validate(admin_user, {"qty_class": "five"})
        assert "qty_class" in exc.value.detail["custom_data"]

    def test_invalid_decimal_value_raises(self, admin_user, tenant_context):
        _make_field_def(tenant_context, "ratio", FieldType.DECIMAL)
        with pytest.raises(ValidationError) as exc:
            self._run_validate(admin_user, {"ratio": "1.5x"})
        assert "ratio" in exc.value.detail["custom_data"]

    def test_invalid_boolean_value_raises(self, admin_user, tenant_context):
        _make_field_def(tenant_context, "is_hazardous", FieldType.BOOLEAN)
        with pytest.raises(ValidationError) as exc:
            self._run_validate(admin_user, {"is_hazardous": 0})
        assert "is_hazardous" in exc.value.detail["custom_data"]

    def test_invalid_date_value_raises(self, admin_user, tenant_context):
        _make_field_def(tenant_context, "manufacture_date", FieldType.DATE)
        with pytest.raises(ValidationError) as exc:
            self._run_validate(admin_user, {"manufacture_date": "31-12-2024"})
        assert "manufacture_date" in exc.value.detail["custom_data"]

    def test_invalid_select_value_raises(self, admin_user, tenant_context):
        _make_field_def(tenant_context, "grade", FieldType.SELECT, choices=["A", "B", "C"])
        with pytest.raises(ValidationError) as exc:
            self._run_validate(admin_user, {"grade": "D"})
        assert "grade" in exc.value.detail["custom_data"]

    # --- Error format ---

    def test_error_format_is_nested_dict_with_list_message(self, admin_user, tenant_context):
        """Errors must be returned as {custom_data: {key: [msg_string]}}."""
        _make_field_def(tenant_context, "size", FieldType.TEXT)
        with pytest.raises(ValidationError) as exc:
            self._run_validate(admin_user, {"size": 99})
        detail = exc.value.detail
        assert "custom_data" in detail
        assert isinstance(detail["custom_data"], dict)
        assert "size" in detail["custom_data"]
        error_list = detail["custom_data"]["size"]
        assert isinstance(error_list, list)
        assert len(error_list) == 1

    # --- Undefined keys silently ignored ---

    def test_undefined_keys_silently_pass_through(self, admin_user, tenant_context):
        """Keys not in any active definition pass through without error."""
        # No field definitions created — all keys are undefined
        result = self._run_validate(admin_user, {"mystery_field": "anything"})
        assert result["custom_data"]["mystery_field"] == "anything"

    # --- Inactive field skipping ---

    def test_inactive_field_excluded_from_validation(self, admin_user, tenant_context):
        """Definitions with active=False are excluded — any value passes."""
        _make_field_def(tenant_context, "hidden_field", FieldType.INTEGER, active=False)
        # "not-an-int" would normally fail INTEGER validation
        result = self._run_validate(admin_user, {"hidden_field": "not-an-int"})
        assert result["custom_data"]["hidden_field"] == "not-an-int"

    # --- Multiple errors ---

    def test_multiple_invalid_fields_all_reported(self, admin_user, tenant_context):
        """Multiple invalid fields must all appear in the error detail."""
        _make_field_def(tenant_context, "alpha", FieldType.TEXT)
        _make_field_def(tenant_context, "beta", FieldType.INTEGER)
        with pytest.raises(ValidationError) as exc:
            self._run_validate(admin_user, {"alpha": 1, "beta": "x"})
        errors = exc.value.detail["custom_data"]
        assert "alpha" in errors
        assert "beta" in errors

    # --- Required field enforcement ---

    def test_required_field_present_passes(self, admin_user, tenant_context):
        """Required field that is present must not raise."""
        _make_field_def(tenant_context, "sku_alt", FieldType.TEXT, required=True)
        result = self._run_validate(admin_user, {"sku_alt": "ALT-001"})
        assert result["custom_data"]["sku_alt"] == "ALT-001"

    def test_required_field_missing_from_custom_data_raises(self, admin_user, tenant_context):
        """Required field key absent from custom_data → ValidationError."""
        _make_field_def(tenant_context, "required_tag", FieldType.TEXT, required=True)
        with pytest.raises(ValidationError) as exc:
            self._run_validate(admin_user, {"unrelated_field": "value"})
        assert "required_tag" in exc.value.detail["custom_data"]

    def test_required_field_no_custom_data_at_all_raises(self, admin_user, tenant_context):
        """Required field + custom_data key entirely absent from attrs → error."""
        _make_field_def(tenant_context, "mandatory", FieldType.TEXT, required=True)
        request = _make_request(admin_user)
        serializer = MinimalProductSerializer(context={"request": request})
        attrs = _base_attrs()  # no custom_data key at all
        with pytest.raises(ValidationError) as exc:
            serializer.validate(attrs)
        assert "mandatory" in exc.value.detail["custom_data"]

    # --- Edge cases: context / tenant guards ---

    def test_no_request_context_skips_validation(self, admin_user, tenant_context):
        """Missing request in context → validation silently skipped."""
        _make_field_def(tenant_context, "mandatory", FieldType.TEXT, required=True)
        serializer = MinimalProductSerializer(context={})
        attrs = _base_attrs(custom_data={"mandatory": 99})  # would fail if validated
        result = serializer.validate(attrs)
        assert result == attrs  # unchanged, no error raised

    def test_no_entity_type_skips_validation(self, admin_user, tenant_context):
        """entity_type = None on serializer → validation silently skipped."""
        _make_field_def(tenant_context, "some_field", FieldType.TEXT, required=True)

        class NoEntitySerializer(CustomFieldsMixin, serializers.ModelSerializer):
            entity_type = None

            class Meta:
                model = Product
                fields = ["sku", "name", "unit_price", "cost_price", "tax_rate", "is_active"]

        request = _make_request(admin_user)
        serializer = NoEntitySerializer(context={"request": request})
        attrs = _base_attrs()
        result = serializer.validate(attrs)  # must not raise
        assert result == attrs


# ---------------------------------------------------------------------------
# Integration tests: merge semantics on update
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestMergeSemantics:
    """Tests for CustomFieldsMixin.update() merge behavior."""

    def _do_update(self, admin_user, product, incoming_validated_data):
        """Call serializer.update() and capture what is passed to ModelSerializer.update."""
        request = _make_request(admin_user)
        serializer = MinimalProductSerializer(product, context={"request": request})

        captured = {}

        def fake_super_update(instance, validated_data):
            captured.update(validated_data)
            return instance

        with mock.patch.object(serializers.ModelSerializer, "update", side_effect=fake_super_update):
            serializer.update(product, incoming_validated_data)

        return captured

    def test_incoming_merges_with_existing(self, admin_user, tenant_context, product):
        """Incoming keys are added to existing custom_data."""
        product.custom_data = {"existing_key": "existing_val", "other": "other_val"}
        product.save()

        captured = self._do_update(admin_user, product, {"custom_data": {"new_key": "new_val"}})
        merged = captured["custom_data"]
        assert merged["existing_key"] == "existing_val"
        assert merged["other"] == "other_val"
        assert merged["new_key"] == "new_val"

    def test_null_value_removes_key(self, admin_user, tenant_context, product):
        """Incoming null value causes key to be removed from the merged result."""
        product.custom_data = {"to_remove": "bye", "to_keep": "stays"}
        product.save()

        captured = self._do_update(admin_user, product, {"custom_data": {"to_remove": None}})
        merged = captured["custom_data"]
        assert "to_remove" not in merged
        assert merged["to_keep"] == "stays"

    def test_unstated_keys_preserved(self, admin_user, tenant_context, product):
        """Keys not mentioned in the incoming update are preserved unchanged."""
        product.custom_data = {"alpha": "a", "beta": "b", "gamma": "c"}
        product.save()

        captured = self._do_update(admin_user, product, {"custom_data": {"gamma": "new_c"}})
        merged = captured["custom_data"]
        assert merged["alpha"] == "a"
        assert merged["beta"] == "b"
        assert merged["gamma"] == "new_c"

    def test_no_custom_data_key_in_update_leaves_existing_unchanged(
        self, admin_user, tenant_context, product
    ):
        """If incoming validated_data has no custom_data key, it is not touched."""
        product.custom_data = {"existing": "value"}
        product.save()

        captured = self._do_update(admin_user, product, {"name": "New Name"})
        assert "custom_data" not in captured


# ---------------------------------------------------------------------------
# Integration tests: default injection on create
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDefaultInjection:
    """Tests for CustomFieldsMixin.create() default value injection."""

    def _do_create(self, admin_user, validated_data):
        """Call serializer.create() and capture what is passed to ModelSerializer.create."""
        request = _make_request(admin_user)
        serializer = MinimalProductSerializer(context={"request": request})

        captured = {}

        def fake_super_create(vd):
            captured.update(vd)
            return mock.Mock()

        with mock.patch.object(serializers.ModelSerializer, "create", side_effect=fake_super_create):
            serializer.create(validated_data)

        return captured

    def _base_create_data(self):
        return {
            "sku": "TEST-DEF",
            "name": "Test",
            "unit_price": Decimal("10.000"),
            "cost_price": Decimal("5.000"),
            "tax_rate": Decimal("0.00"),
            "is_active": True,
        }

    def test_default_injected_for_absent_key(self, admin_user, tenant_context):
        """Default value is injected on create when the key is absent."""
        _make_field_def(tenant_context, "color", FieldType.TEXT, default_value="white")

        captured = self._do_create(admin_user, self._base_create_data())
        assert captured.get("custom_data", {}).get("color") == "white"

    def test_default_not_injected_if_key_already_present(self, admin_user, tenant_context):
        """Default value must NOT overwrite an explicitly provided value."""
        _make_field_def(tenant_context, "color", FieldType.TEXT, default_value="white")

        data = self._base_create_data()
        data["custom_data"] = {"color": "black"}
        captured = self._do_create(admin_user, data)
        assert captured["custom_data"]["color"] == "black"

    def test_default_not_injected_on_update(self, admin_user, tenant_context, product):
        """Default values are injected by create(), NOT by update()."""
        _make_field_def(tenant_context, "badge", FieldType.TEXT, default_value="gold")
        product.custom_data = {}
        product.save()

        request = _make_request(admin_user)
        serializer = MinimalProductSerializer(product, context={"request": request})

        captured = {}

        def fake_super_update(instance, vd):
            captured.update(vd)
            return instance

        with mock.patch.object(serializers.ModelSerializer, "update", side_effect=fake_super_update):
            serializer.update(product, {"custom_data": {"other": "val"}})

        merged = captured.get("custom_data", {})
        assert "badge" not in merged  # default NOT injected by update


# ---------------------------------------------------------------------------
# Integration tests: caching behavior
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestCacheBehavior:
    """Tests for CustomFieldsMixin._get_field_definitions() caching."""

    def test_cache_miss_queries_db_and_stores_result(self, tenant_context):
        """On cache miss, DB is queried and result stored with cache.set()."""
        _make_field_def(tenant_context, "cached_field", FieldType.TEXT)

        with mock.patch("apps.core.serializers.customization.cache.get", return_value=None) as mock_get, \
             mock.patch("apps.core.serializers.customization.cache.set") as mock_set:
            defs = CustomFieldsMixin._get_field_definitions(tenant_context.id, "product")

        mock_get.assert_called_once()
        mock_set.assert_called_once()
        assert len(defs) >= 1

    def test_cache_hit_returns_cached_without_storing(self, tenant_context):
        """On cache hit, cached value is returned immediately; cache.set not called."""
        cached_defs = [mock.Mock()]  # Pretend these came from cache

        with mock.patch("apps.core.serializers.customization.cache.get", return_value=cached_defs) as mock_get, \
             mock.patch("apps.core.serializers.customization.cache.set") as mock_set:
            defs = CustomFieldsMixin._get_field_definitions(tenant_context.id, "product")

        mock_get.assert_called_once()
        mock_set.assert_not_called()
        assert defs is cached_defs

    def test_cache_key_includes_tenant_id_and_entity_type(self, tenant_context):
        """Cache key must scope by both tenant_id and entity_type."""
        captured_keys = []

        def fake_get(key):
            captured_keys.append(key)
            return None

        with mock.patch("apps.core.serializers.customization.cache.get", side_effect=fake_get), \
             mock.patch("apps.core.serializers.customization.cache.set"):
            CustomFieldsMixin._get_field_definitions(tenant_context.id, "product")

        assert len(captured_keys) == 1
        cache_key = captured_keys[0]
        assert str(tenant_context.id) in cache_key
        assert "product" in cache_key
