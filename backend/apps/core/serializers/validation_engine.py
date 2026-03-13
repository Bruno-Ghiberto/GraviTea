"""Custom field validation dispatcher — Rust-accelerated type checking."""
import json
import logging
from decimal import Decimal
from typing import Any

logger = logging.getLogger(__name__)

_USE_RUST: bool

try:
    from gravitea_rust import validate_custom_fields as _rust_validate
    _USE_RUST = True
except (ImportError, OSError):
    _USE_RUST = False
    logger.warning("gravitea_rust custom field validator not available — using Python fallback")

_RUST_FIELD_THRESHOLD = 5


class _DecimalEncoder(json.JSONEncoder):
    """Handle Decimal values that may appear in custom_data from programmatic code."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def validate_fields(definitions, custom_data):
    """Validate custom_data values against field definitions.

    Args:
        definitions: List of TenantFieldDefinition ORM objects (active only).
        custom_data: Dict of custom field values from request.

    Returns:
        Dict of errors: {} if valid, {"field_key": ["error"]} if errors.
    """
    if _USE_RUST and len(definitions) > _RUST_FIELD_THRESHOLD:
        return _validate_rust(definitions, custom_data)
    return _validate_python(definitions, custom_data)


def _validate_rust(definitions, custom_data):
    """Rust path: serialize → FFI → deserialize."""
    defs_json = json.dumps([
        {"field_key": d.field_key, "field_type": d.field_type, "choices": d.choices}
        for d in definitions
    ])
    filtered = {k: v for k, v in custom_data.items() if v is not None}
    data_json = json.dumps(filtered, cls=_DecimalEncoder)
    result_json = _rust_validate(defs_json, data_json)
    return json.loads(result_json)


def _validate_python(definitions, custom_data):
    """Python fallback: original _validate_field_value logic."""
    import re
    DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    defined_keys = {d.field_key: d for d in definitions}
    errors = {}

    for key, value in custom_data.items():
        if value is None:
            continue
        defn = defined_keys.get(key)
        if defn is None:
            continue
        ft = defn.field_type
        err = None
        if ft == "text":
            if not isinstance(value, str):
                err = "Expected a text value."
        elif ft == "integer":
            if not isinstance(value, int) or isinstance(value, bool):
                err = "Expected an integer value."
        elif ft == "decimal":
            if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
                err = "Expected a decimal value."
        elif ft == "boolean":
            if not isinstance(value, bool):
                err = "Expected a boolean value."
        elif ft == "date":
            if not isinstance(value, str) or not DATE_RE.match(value):
                err = "Expected a date in YYYY-MM-DD format."
        elif ft == "select":
            allowed = defn.choices or []
            if value not in allowed:
                err = f"Invalid choice. Allowed: {allowed}"
        if err:
            errors[key] = [err]

    return errors
