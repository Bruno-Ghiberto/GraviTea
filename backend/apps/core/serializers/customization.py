"""
CustomFieldsMixin for DRF serializers.

Validates and manages per-tenant custom fields (custom_data JSONB)
based on TenantFieldDefinition metadata.
"""

import re
from decimal import Decimal

from django.core.cache import cache
from rest_framework import serializers

from apps.core.models import TenantFieldDefinition, TenantModuleConfig

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class CustomFieldsMixin:
    """
    DRF serializer mixin for tenant-scoped custom field validation.

    Subclasses must set ``entity_type`` (e.g. "product").
    Expects ``self.context["request"]`` to carry an authenticated user
    with ``user.tenant_id``.
    """

    entity_type = None

    # ------------------------------------------------------------------
    # Cache helper
    # ------------------------------------------------------------------

    @staticmethod
    def _get_field_definitions(tenant_id, entity_type):
        cache_key = f"field_defs:{tenant_id}:{entity_type}"
        defs = cache.get(cache_key)
        if defs is None:
            defs = list(
                TenantFieldDefinition.objects.filter(
                    tenant_id=tenant_id,
                    entity_type=entity_type,
                    active=True,
                )
            )
            cache.set(cache_key, defs, 60)
        return defs

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self, attrs):
        attrs = super().validate(attrs)

        request = self.context.get("request")
        if not request or not hasattr(request, "user"):
            return attrs

        tenant_id = request.user.tenant_id
        if not self.entity_type or not tenant_id:
            return attrs

        definitions = self._get_field_definitions(tenant_id, self.entity_type)

        custom_data = attrs.get("custom_data")
        if custom_data is None:
            # Check required fields even when custom_data absent
            errors = {}
            for defn in definitions:
                if defn.required:
                    errors[defn.field_key] = ["This field is required."]
            if errors:
                raise serializers.ValidationError({"custom_data": errors})
            return attrs

        from .validation_engine import validate_fields

        errors = validate_fields(definitions, custom_data)

        # On update, merge with existing custom_data before checking required
        check_data = custom_data
        if self.instance and hasattr(self.instance, "custom_data") and self.instance.custom_data:
            check_data = {**self.instance.custom_data, **custom_data}
            check_data = {k: v for k, v in check_data.items() if v is not None}

        # Check required fields missing from (merged) custom_data
        for defn in definitions:
            if defn.required and defn.field_key not in check_data:
                errors[defn.field_key] = ["This field is required."]

        if errors:
            raise serializers.ValidationError({"custom_data": errors})

        return attrs

    @staticmethod
    def _validate_field_value(defn, value):
        """Return an error string if *value* doesn't match *defn*, else None."""
        ft = defn.field_type

        if ft == "text":
            if not isinstance(value, str):
                return "Expected a text value."
        elif ft == "integer":
            if not isinstance(value, int) or isinstance(value, bool):
                return "Expected an integer value."
        elif ft == "decimal":
            if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
                return "Expected a decimal value."
        elif ft == "boolean":
            if not isinstance(value, bool):
                return "Expected a boolean value."
        elif ft == "date":
            if not isinstance(value, str) or not DATE_RE.match(value):
                return "Expected a date in YYYY-MM-DD format."
        elif ft == "select":
            allowed = defn.choices or []
            if value not in allowed:
                return f"Invalid choice. Allowed: {allowed}"

        return None

    # ------------------------------------------------------------------
    # Create — inject defaults
    # ------------------------------------------------------------------

    def create(self, validated_data):
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            tenant_id = request.user.tenant_id
            if self.entity_type and tenant_id:
                definitions = self._get_field_definitions(tenant_id, self.entity_type)
                custom_data = validated_data.get("custom_data") or {}

                for defn in definitions:
                    if (
                        defn.default_value is not None
                        and defn.field_key not in custom_data
                    ):
                        custom_data[defn.field_key] = defn.default_value

                if custom_data:
                    validated_data["custom_data"] = custom_data

        return super().create(validated_data)

    # ------------------------------------------------------------------
    # Update — merge semantics
    # ------------------------------------------------------------------

    def update(self, instance, validated_data):
        incoming = validated_data.get("custom_data")
        if incoming is not None:
            existing = instance.custom_data or {}
            merged = {**existing, **incoming}
            # Keys with null value → remove
            merged = {k: v for k, v in merged.items() if v is not None}
            validated_data["custom_data"] = merged

        return super().update(instance, validated_data)


class FieldDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantFieldDefinition
        fields = [
            "id", "field_key", "label", "entity_type", "field_type",
            "section", "position", "required", "default_value", "choices",
        ]
        read_only_fields = fields


class ModuleConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantModuleConfig
        fields = ["id", "module", "enabled", "settings"]
        read_only_fields = fields
