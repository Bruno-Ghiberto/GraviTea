"""
OpenAPI schema validation utilities for contract testing.

Provides utilities for validating API responses against OpenAPI specifications
and detecting schema drift between actual responses and documented contracts.

Per spec.md FR-009 through FR-015 requirements:
- T049: Create OpenAPI schema validator utility
- T050: Create schema comparison helper for drift detection
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID


@dataclass
class SchemaValidationError:
    """Represents a single schema validation error."""

    path: str
    message: str
    expected: Any | None = None
    actual: Any | None = None

    def __str__(self) -> str:
        result = f"{self.path}: {self.message}"
        if self.expected is not None:
            result += f" (expected: {self.expected}, actual: {self.actual})"
        return result


@dataclass
class SchemaValidationResult:
    """Result of schema validation."""

    valid: bool
    errors: list[SchemaValidationError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.valid


class OpenAPISchemaValidator:
    """Validates API responses against OpenAPI schema definitions.

    This validator provides:
    - Type checking against JSON Schema types
    - Required field validation
    - Format validation (uuid, date-time, uri, email)
    - Nested object and array validation
    - Enum value validation

    Usage:
        validator = OpenAPISchemaValidator()
        result = validator.validate(response_data, schema_definition)
        if not result.valid:
            for error in result.errors:
                print(error)
    """

    # JSON Schema type to Python type mapping
    TYPE_MAP = {
        "string": str,
        "integer": int,
        "number": (int, float, Decimal),
        "boolean": bool,
        "array": list,
        "object": dict,
        "null": type(None),
    }

    # Format validators
    FORMAT_PATTERNS = {
        "uuid": re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
            re.IGNORECASE,
        ),
        "date-time": re.compile(
            r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?$"
        ),
        "date": re.compile(r"^\d{4}-\d{2}-\d{2}$"),
        "time": re.compile(r"^\d{2}:\d{2}:\d{2}(?:\.\d+)?$"),
        "uri": re.compile(r"^https?://", re.IGNORECASE),
        "email": re.compile(r"^[^@]+@[^@]+\.[^@]+$"),
    }

    def validate(
        self, data: Any, schema: dict[str, Any], path: str = "$"
    ) -> SchemaValidationResult:
        """Validate data against an OpenAPI schema.

        Args:
            data: The response data to validate
            schema: The OpenAPI schema definition
            path: Current path in the document (for error reporting)

        Returns:
            SchemaValidationResult with validation status and any errors
        """
        errors: list[SchemaValidationError] = []
        warnings: list[str] = []

        self._validate_node(data, schema, path, errors, warnings)

        return SchemaValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def _validate_node(
        self,
        data: Any,
        schema: dict[str, Any],
        path: str,
        errors: list[SchemaValidationError],
        warnings: list[str],
    ) -> None:
        """Recursively validate a node in the data."""
        # Handle nullable
        if data is None:
            if schema.get("nullable") or "null" in schema.get("type", []):
                return
            if schema.get("type") != "null":
                errors.append(
                    SchemaValidationError(
                        path=path,
                        message="Value is null but schema does not allow null",
                    )
                )
                return
            return

        # Handle allOf
        if "allOf" in schema:
            for i, sub_schema in enumerate(schema["allOf"]):
                self._validate_node(data, sub_schema, path, errors, warnings)
            return

        # Handle oneOf
        if "oneOf" in schema:
            valid_count = 0
            sub_errors: list[SchemaValidationError] = []
            for sub_schema in schema["oneOf"]:
                result = self.validate(data, sub_schema, path)
                if result.valid:
                    valid_count += 1
                else:
                    sub_errors.extend(result.errors)

            if valid_count == 0:
                errors.append(
                    SchemaValidationError(
                        path=path,
                        message="Value does not match any oneOf schema",
                    )
                )
            elif valid_count > 1:
                warnings.append(f"{path}: Value matches multiple oneOf schemas")
            return

        # Handle anyOf
        if "anyOf" in schema:
            matched = False
            for sub_schema in schema["anyOf"]:
                result = self.validate(data, sub_schema, path)
                if result.valid:
                    matched = True
                    break

            if not matched:
                errors.append(
                    SchemaValidationError(
                        path=path,
                        message="Value does not match any anyOf schema",
                    )
                )
            return

        # Validate type
        schema_type = schema.get("type")
        if schema_type:
            if not self._validate_type(data, schema_type):
                errors.append(
                    SchemaValidationError(
                        path=path,
                        message="Type mismatch",
                        expected=schema_type,
                        actual=type(data).__name__,
                    )
                )
                return

        # Validate format
        format_spec = schema.get("format")
        if format_spec and isinstance(data, str):
            if not self._validate_format(data, format_spec):
                errors.append(
                    SchemaValidationError(
                        path=path,
                        message=f"Format mismatch",
                        expected=format_spec,
                        actual=data[:50] if len(data) > 50 else data,
                    )
                )

        # Validate enum
        enum_values = schema.get("enum")
        if enum_values is not None and data not in enum_values:
            errors.append(
                SchemaValidationError(
                    path=path,
                    message="Value not in enum",
                    expected=enum_values,
                    actual=data,
                )
            )

        # Validate object properties
        if schema_type == "object" or isinstance(data, dict):
            self._validate_object(data, schema, path, errors, warnings)

        # Validate array items
        if schema_type == "array" or isinstance(data, list):
            self._validate_array(data, schema, path, errors, warnings)

        # Validate string constraints
        if schema_type == "string" and isinstance(data, str):
            self._validate_string_constraints(data, schema, path, errors)

        # Validate number constraints
        if schema_type in ("integer", "number") and isinstance(data, (int, float, Decimal)):
            self._validate_number_constraints(data, schema, path, errors)

    def _validate_type(self, data: Any, schema_type: str | list[str]) -> bool:
        """Validate that data matches the expected type."""
        if isinstance(schema_type, list):
            return any(self._validate_type(data, t) for t in schema_type)

        expected_types = self.TYPE_MAP.get(schema_type)
        if expected_types is None:
            return True  # Unknown type, assume valid

        return isinstance(data, expected_types)

    def _validate_format(self, data: str, format_spec: str) -> bool:
        """Validate string format."""
        pattern = self.FORMAT_PATTERNS.get(format_spec)
        if pattern is None:
            return True  # Unknown format, assume valid

        return bool(pattern.match(data))

    def _validate_object(
        self,
        data: dict[str, Any],
        schema: dict[str, Any],
        path: str,
        errors: list[SchemaValidationError],
        warnings: list[str],
    ) -> None:
        """Validate object against schema properties."""
        if not isinstance(data, dict):
            return

        properties = schema.get("properties", {})
        required = schema.get("required", [])
        additional_properties = schema.get("additionalProperties", True)

        # Check required fields
        for field_name in required:
            if field_name not in data:
                errors.append(
                    SchemaValidationError(
                        path=f"{path}.{field_name}",
                        message="Required field is missing",
                    )
                )

        # Validate each property
        for field_name, field_value in data.items():
            field_path = f"{path}.{field_name}"

            if field_name in properties:
                field_schema = properties[field_name]
                self._validate_node(field_value, field_schema, field_path, errors, warnings)
            elif additional_properties is False:
                warnings.append(f"{field_path}: Unexpected property (additionalProperties=false)")
            elif isinstance(additional_properties, dict):
                self._validate_node(field_value, additional_properties, field_path, errors, warnings)

    def _validate_array(
        self,
        data: list[Any],
        schema: dict[str, Any],
        path: str,
        errors: list[SchemaValidationError],
        warnings: list[str],
    ) -> None:
        """Validate array against schema items."""
        if not isinstance(data, list):
            return

        items_schema = schema.get("items", {})
        min_items = schema.get("minItems")
        max_items = schema.get("maxItems")

        # Validate array length
        if min_items is not None and len(data) < min_items:
            errors.append(
                SchemaValidationError(
                    path=path,
                    message="Array has too few items",
                    expected=f">= {min_items}",
                    actual=len(data),
                )
            )

        if max_items is not None and len(data) > max_items:
            errors.append(
                SchemaValidationError(
                    path=path,
                    message="Array has too many items",
                    expected=f"<= {max_items}",
                    actual=len(data),
                )
            )

        # Validate each item
        for i, item in enumerate(data):
            item_path = f"{path}[{i}]"
            self._validate_node(item, items_schema, item_path, errors, warnings)

    def _validate_string_constraints(
        self,
        data: str,
        schema: dict[str, Any],
        path: str,
        errors: list[SchemaValidationError],
    ) -> None:
        """Validate string-specific constraints."""
        min_length = schema.get("minLength")
        max_length = schema.get("maxLength")
        pattern = schema.get("pattern")

        if min_length is not None and len(data) < min_length:
            errors.append(
                SchemaValidationError(
                    path=path,
                    message="String is too short",
                    expected=f">= {min_length} chars",
                    actual=len(data),
                )
            )

        if max_length is not None and len(data) > max_length:
            errors.append(
                SchemaValidationError(
                    path=path,
                    message="String is too long",
                    expected=f"<= {max_length} chars",
                    actual=len(data),
                )
            )

        if pattern is not None:
            if not re.match(pattern, data):
                errors.append(
                    SchemaValidationError(
                        path=path,
                        message="String does not match pattern",
                        expected=pattern,
                        actual=data[:50] if len(data) > 50 else data,
                    )
                )

    def _validate_number_constraints(
        self,
        data: int | float | Decimal,
        schema: dict[str, Any],
        path: str,
        errors: list[SchemaValidationError],
    ) -> None:
        """Validate number-specific constraints."""
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        exclusive_minimum = schema.get("exclusiveMinimum")
        exclusive_maximum = schema.get("exclusiveMaximum")

        if minimum is not None and data < minimum:
            errors.append(
                SchemaValidationError(
                    path=path,
                    message="Number is below minimum",
                    expected=f">= {minimum}",
                    actual=data,
                )
            )

        if maximum is not None and data > maximum:
            errors.append(
                SchemaValidationError(
                    path=path,
                    message="Number is above maximum",
                    expected=f"<= {maximum}",
                    actual=data,
                )
            )

        if exclusive_minimum is not None and data <= exclusive_minimum:
            errors.append(
                SchemaValidationError(
                    path=path,
                    message="Number is not above exclusive minimum",
                    expected=f"> {exclusive_minimum}",
                    actual=data,
                )
            )

        if exclusive_maximum is not None and data >= exclusive_maximum:
            errors.append(
                SchemaValidationError(
                    path=path,
                    message="Number is not below exclusive maximum",
                    expected=f"< {exclusive_maximum}",
                    actual=data,
                )
            )


@dataclass
class SchemaDrift:
    """Represents a schema drift between expected and actual schemas."""

    location: str
    drift_type: str
    expected: Any | None = None
    actual: Any | None = None
    severity: str = "warning"  # "error", "warning", "info"

    def __str__(self) -> str:
        msg = f"[{self.severity.upper()}] {self.location}: {self.drift_type}"
        if self.expected is not None:
            msg += f" (expected: {self.expected}, actual: {self.actual})"
        return msg


@dataclass
class SchemaDriftReport:
    """Report of schema drift detection."""

    timestamp: datetime
    base_schema_path: str | None
    drifts: list[SchemaDrift] = field(default_factory=list)
    summary: dict[str, int] = field(default_factory=dict)

    @property
    def has_errors(self) -> bool:
        return any(d.severity == "error" for d in self.drifts)

    @property
    def has_warnings(self) -> bool:
        return any(d.severity == "warning" for d in self.drifts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "base_schema_path": self.base_schema_path,
            "drifts": [
                {
                    "location": d.location,
                    "drift_type": d.drift_type,
                    "expected": d.expected,
                    "actual": d.actual,
                    "severity": d.severity,
                }
                for d in self.drifts
            ],
            "summary": self.summary,
        }


class SchemaComparisonHelper:
    """Compares OpenAPI schemas to detect drift between versions.

    This helper detects:
    - Added/removed endpoints
    - Changed request/response schemas
    - Modified field requirements
    - Type changes
    - Enum value changes

    Usage:
        helper = SchemaComparisonHelper()
        report = helper.compare(base_schema, current_schema)
        if report.has_errors:
            print("Breaking changes detected!")
            for drift in report.drifts:
                print(drift)
    """

    def compare(
        self,
        base_schema: dict[str, Any],
        current_schema: dict[str, Any],
        base_path: str | None = None,
    ) -> SchemaDriftReport:
        """Compare two OpenAPI schemas and detect drift.

        Args:
            base_schema: The reference/expected schema
            current_schema: The current/actual schema
            base_path: Optional path to the base schema file

        Returns:
            SchemaDriftReport containing all detected drifts
        """
        drifts: list[SchemaDrift] = []
        summary: dict[str, int] = {
            "error": 0,
            "warning": 0,
            "info": 0,
        }

        # Compare paths (endpoints)
        self._compare_paths(
            base_schema.get("paths", {}),
            current_schema.get("paths", {}),
            drifts,
        )

        # Compare components/schemas
        self._compare_components(
            base_schema.get("components", {}).get("schemas", {}),
            current_schema.get("components", {}).get("schemas", {}),
            drifts,
        )

        # Update summary
        for drift in drifts:
            summary[drift.severity] = summary.get(drift.severity, 0) + 1

        return SchemaDriftReport(
            timestamp=datetime.now(),
            base_schema_path=base_path,
            drifts=drifts,
            summary=summary,
        )

    def _compare_paths(
        self,
        base_paths: dict[str, Any],
        current_paths: dict[str, Any],
        drifts: list[SchemaDrift],
    ) -> None:
        """Compare API paths/endpoints."""
        base_keys = set(base_paths.keys())
        current_keys = set(current_paths.keys())

        # Detect removed endpoints (breaking change)
        for removed in base_keys - current_keys:
            drifts.append(
                SchemaDrift(
                    location=f"paths.{removed}",
                    drift_type="endpoint_removed",
                    expected=removed,
                    actual=None,
                    severity="error",
                )
            )

        # Detect added endpoints (non-breaking)
        for added in current_keys - base_keys:
            drifts.append(
                SchemaDrift(
                    location=f"paths.{added}",
                    drift_type="endpoint_added",
                    expected=None,
                    actual=added,
                    severity="info",
                )
            )

        # Compare common endpoints
        for path in base_keys & current_keys:
            self._compare_path_item(
                path,
                base_paths[path],
                current_paths[path],
                drifts,
            )

    def _compare_path_item(
        self,
        path: str,
        base_item: dict[str, Any],
        current_item: dict[str, Any],
        drifts: list[SchemaDrift],
    ) -> None:
        """Compare operations within a path item."""
        methods = {"get", "post", "put", "patch", "delete", "head", "options"}

        for method in methods:
            base_op = base_item.get(method)
            current_op = current_item.get(method)

            if base_op and not current_op:
                drifts.append(
                    SchemaDrift(
                        location=f"paths.{path}.{method}",
                        drift_type="method_removed",
                        expected=method,
                        actual=None,
                        severity="error",
                    )
                )
            elif not base_op and current_op:
                drifts.append(
                    SchemaDrift(
                        location=f"paths.{path}.{method}",
                        drift_type="method_added",
                        expected=None,
                        actual=method,
                        severity="info",
                    )
                )
            elif base_op and current_op:
                self._compare_operation(
                    f"paths.{path}.{method}",
                    base_op,
                    current_op,
                    drifts,
                )

    def _compare_operation(
        self,
        location: str,
        base_op: dict[str, Any],
        current_op: dict[str, Any],
        drifts: list[SchemaDrift],
    ) -> None:
        """Compare individual operations."""
        # Compare response codes
        base_responses = set(base_op.get("responses", {}).keys())
        current_responses = set(current_op.get("responses", {}).keys())

        for removed in base_responses - current_responses:
            drifts.append(
                SchemaDrift(
                    location=f"{location}.responses.{removed}",
                    drift_type="response_code_removed",
                    expected=removed,
                    actual=None,
                    severity="warning",
                )
            )

        # Compare parameters
        base_params = {p.get("name"): p for p in base_op.get("parameters", [])}
        current_params = {p.get("name"): p for p in current_op.get("parameters", [])}

        for removed in set(base_params.keys()) - set(current_params.keys()):
            if base_params[removed].get("required"):
                drifts.append(
                    SchemaDrift(
                        location=f"{location}.parameters.{removed}",
                        drift_type="required_parameter_removed",
                        expected=removed,
                        actual=None,
                        severity="error",
                    )
                )

        for added in set(current_params.keys()) - set(base_params.keys()):
            if current_params[added].get("required"):
                drifts.append(
                    SchemaDrift(
                        location=f"{location}.parameters.{added}",
                        drift_type="required_parameter_added",
                        expected=None,
                        actual=added,
                        severity="error",  # Breaking change
                    )
                )

    def _compare_components(
        self,
        base_schemas: dict[str, Any],
        current_schemas: dict[str, Any],
        drifts: list[SchemaDrift],
    ) -> None:
        """Compare schema components."""
        base_keys = set(base_schemas.keys())
        current_keys = set(current_schemas.keys())

        # Removed schemas
        for removed in base_keys - current_keys:
            drifts.append(
                SchemaDrift(
                    location=f"components.schemas.{removed}",
                    drift_type="schema_removed",
                    expected=removed,
                    actual=None,
                    severity="warning",
                )
            )

        # Added schemas
        for added in current_keys - base_keys:
            drifts.append(
                SchemaDrift(
                    location=f"components.schemas.{added}",
                    drift_type="schema_added",
                    expected=None,
                    actual=added,
                    severity="info",
                )
            )

        # Compare common schemas
        for name in base_keys & current_keys:
            self._compare_schema_definition(
                f"components.schemas.{name}",
                base_schemas[name],
                current_schemas[name],
                drifts,
            )

    def _compare_schema_definition(
        self,
        location: str,
        base_schema: dict[str, Any],
        current_schema: dict[str, Any],
        drifts: list[SchemaDrift],
    ) -> None:
        """Compare individual schema definitions."""
        # Compare required fields
        base_required = set(base_schema.get("required", []))
        current_required = set(current_schema.get("required", []))

        for added in current_required - base_required:
            drifts.append(
                SchemaDrift(
                    location=f"{location}.required",
                    drift_type="required_field_added",
                    expected=None,
                    actual=added,
                    severity="error",  # Breaking change
                )
            )

        for removed in base_required - current_required:
            drifts.append(
                SchemaDrift(
                    location=f"{location}.required",
                    drift_type="required_field_removed",
                    expected=removed,
                    actual=None,
                    severity="info",
                )
            )

        # Compare properties
        base_props = base_schema.get("properties", {})
        current_props = current_schema.get("properties", {})

        for prop_name in base_props:
            if prop_name not in current_props:
                drifts.append(
                    SchemaDrift(
                        location=f"{location}.properties.{prop_name}",
                        drift_type="property_removed",
                        expected=prop_name,
                        actual=None,
                        severity="warning",
                    )
                )
            else:
                # Check type changes
                base_type = base_props[prop_name].get("type")
                current_type = current_props[prop_name].get("type")
                if base_type != current_type:
                    drifts.append(
                        SchemaDrift(
                            location=f"{location}.properties.{prop_name}",
                            drift_type="type_changed",
                            expected=base_type,
                            actual=current_type,
                            severity="error",
                        )
                    )


def load_openapi_schema(path: str | Path) -> dict[str, Any]:
    """Load an OpenAPI schema from a file.

    Supports both YAML and JSON formats.

    Args:
        path: Path to the OpenAPI schema file

    Returns:
        Parsed schema as a dictionary
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Schema file not found: {path}")

    content = path.read_text()

    if path.suffix in (".yml", ".yaml"):
        try:
            import yaml

            return yaml.safe_load(content)
        except ImportError:
            raise ImportError("PyYAML is required to load YAML schemas. Install with: pip install pyyaml")
    else:
        return json.loads(content)


def validate_response_against_schema(
    response_data: Any,
    schema: dict[str, Any],
) -> SchemaValidationResult:
    """Convenience function to validate a response against a schema.

    Args:
        response_data: The API response data
        schema: The expected schema definition

    Returns:
        SchemaValidationResult with validation status
    """
    validator = OpenAPISchemaValidator()
    return validator.validate(response_data, schema)
