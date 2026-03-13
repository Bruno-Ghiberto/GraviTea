"""
Custom Django model fields for Gravitea ERP.

Provides standardized fields for financial precision, data integrity,
and PostgreSQL ENUM type support.
"""

from decimal import Decimal

from django.db import models


class PostgresEnumField(models.CharField):
    """
    A Django field that maps to a PostgreSQL ENUM type.

    Usage:
        class MyModel(models.Model):
            status = PostgresEnumField(
                enum_type='my_status_enum',
                choices=MyChoices.choices,
                max_length=20  # Fallback for non-PostgreSQL databases
            )

    The enum_type must be created in PostgreSQL before migrations run.
    Create it in your SQL schema file (e.g., TABLAS.sql):
        CREATE TYPE my_status_enum AS ENUM ('VALUE1', 'VALUE2', 'VALUE3');

    Attributes:
        enum_type: The PostgreSQL ENUM type name
        choices: Django choices tuple for validation and admin display
    """

    def __init__(self, enum_type: str, *args, **kwargs):
        """
        Initialize the PostgresEnumField.

        Args:
            enum_type: PostgreSQL ENUM type name (e.g., 'stock_movement_type_enum')
            *args: Positional arguments passed to CharField
            **kwargs: Keyword arguments passed to CharField
        """
        self.enum_type = enum_type
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        """Support for Django migrations."""
        name, path, args, kwargs = super().deconstruct()
        kwargs["enum_type"] = self.enum_type
        return name, path, args, kwargs

    def db_type(self, connection):
        """
        Return the database column type.

        For PostgreSQL, returns the ENUM type name.
        For other databases, falls back to VARCHAR.
        """
        if connection.vendor == "postgresql":
            return self.enum_type
        # Fallback for non-PostgreSQL (e.g., SQLite in tests)
        return super().db_type(connection)

    def get_prep_value(self, value):
        """Prepare value for database insertion."""
        if value is None:
            return None
        return str(value)

    def from_db_value(self, value, expression, connection):
        """Convert database value to Python value."""
        if value is None:
            return None
        return str(value)


# Pre-defined ENUM types matching TABLAS.sql
# These constants help ensure consistency between Django and PostgreSQL
STOCK_MOVEMENT_TYPE_ENUM = "stock_movement_type_enum"
PAYMENT_METHOD_ENUM = "payment_method_enum"
SALE_TYPE_ENUM = "sale_type_enum"
SALE_STATUS_ENUM = "sale_status_enum"
BUDGET_STATUS_ENUM = "budget_status_enum"
CUSTOMER_LEDGER_TYPE_ENUM = "customer_ledger_type_enum"
SUPPLIER_LEDGER_TYPE_ENUM = "supplier_ledger_type_enum"
PURCHASE_ORDER_STATUS_ENUM = "purchase_order_status_enum"
SYNC_STATUS_ENUM = "sync_status_enum"
OPERATION_TYPE_ENUM = "operation_type_enum"
OPERATION_STATUS_ENUM = "operation_status_enum"


class MoneyField(models.DecimalField):
    """
    Standardized monetary field with DECIMAL(17,3) precision.

    Per FR-005 and Database_schemas.md, all monetary values must use
    DECIMAL(17,3) to:
    - Avoid floating-point rounding errors
    - Support 3 decimal places for fractional units
    - Handle large values (up to 99,999,999,999,999.999)

    Usage:
        current_cost = MoneyField()
        current_price = MoneyField(null=True, blank=True)
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_digits", 17)
        kwargs.setdefault("decimal_places", 3)
        kwargs.setdefault("default", Decimal("0.000"))
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        # Remove defaults for migration clarity
        if kwargs.get("max_digits") == 17:
            del kwargs["max_digits"]
        if kwargs.get("decimal_places") == 3:
            del kwargs["decimal_places"]
        if kwargs.get("default") == Decimal("0.000"):
            del kwargs["default"]
        return name, path, args, kwargs
