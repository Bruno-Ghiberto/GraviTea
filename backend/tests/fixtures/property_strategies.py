"""
Hypothesis property-based testing strategies.

Provides reusable strategies for:
- Inventory quantities (FR-021)
- Price calculations (FR-022)
- Tenant validation (FR-023)
- Data consistency properties (FR-024)
"""

from decimal import Decimal
from uuid import UUID

from hypothesis import strategies as st


# ==============================================================
# Inventory Quantity Strategies (FR-021)
# ==============================================================

# General inventory quantity (can be negative for adjustments)
inventory_quantity = st.decimals(
    min_value=Decimal("-10000"),
    max_value=Decimal("10000000"),
    places=4,
    allow_nan=False,
    allow_infinity=False,
)

# Valid stock quantity (non-negative)
valid_stock_quantity = st.decimals(
    min_value=Decimal("0"),
    max_value=Decimal("10000000"),
    places=4,
    allow_nan=False,
    allow_infinity=False,
)

# Stock movement delta (purchase, sale, adjustment)
stock_movement_delta = st.decimals(
    min_value=Decimal("-99999.9999"),
    max_value=Decimal("99999.9999"),
    places=4,
    allow_nan=False,
    allow_infinity=False,
)


# ==============================================================
# Price Strategies (FR-022)
# Per constitution: DECIMAL(17,3)
# ==============================================================

# Unit price - must be positive
unit_price = st.decimals(
    min_value=Decimal("0.001"),
    max_value=Decimal("99999999999999.999"),
    places=3,
    allow_nan=False,
    allow_infinity=False,
)

# Cost price - must be positive
cost_price = st.decimals(
    min_value=Decimal("0.001"),
    max_value=Decimal("99999999999999.999"),
    places=3,
    allow_nan=False,
    allow_infinity=False,
)

# Tax rate - percentage 0-100
tax_rate = st.decimals(
    min_value=Decimal("0.00"),
    max_value=Decimal("100.00"),
    places=2,
    allow_nan=False,
    allow_infinity=False,
)

# Discount percentage
discount_percentage = st.decimals(
    min_value=Decimal("0.00"),
    max_value=Decimal("100.00"),
    places=2,
    allow_nan=False,
    allow_infinity=False,
)


# ==============================================================
# Tenant ID Strategies (FR-023)
# ==============================================================

tenant_id = st.uuids()

branch_id = st.uuids()


# ==============================================================
# Text Strategies for Product Data
# ==============================================================

# SKU - alphanumeric with dashes, uppercase
sku_strategy = st.text(
    min_size=1,
    max_size=50,
    alphabet=st.sampled_from("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-"),
).filter(lambda x: not x.startswith("-") and not x.endswith("-") and "--" not in x)

# Product name - any printable text
product_name = st.text(min_size=1, max_size=200).filter(
    lambda x: x.strip() == x and len(x.strip()) > 0
)

# Barcode - numeric, 8-13 digits (EAN-8, EAN-13, UPC)
barcode = st.text(min_size=8, max_size=13, alphabet=st.sampled_from("0123456789"))

# Email address
email_strategy = st.emails()

# Phone number (Argentine format)
phone_number = st.from_regex(r"\+54-\d{2}-\d{4}-\d{4}", fullmatch=True)


# ==============================================================
# Composite Strategies
# ==============================================================


@st.composite
def product_data(draw):
    """Generate valid product data for property-based testing."""
    return {
        "sku": draw(sku_strategy),
        "name": draw(product_name),
        "unit_price": draw(unit_price),
        "cost_price": draw(cost_price),
        "tax_rate": draw(tax_rate),
        "is_active": draw(st.booleans()),
    }


@st.composite
def stock_movement_data(draw):
    """Generate valid stock movement data."""
    movement_type = draw(st.sampled_from(["PURCHASE", "SALE", "ADJUSTMENT", "TRANSFER"]))

    # Purchases are positive, sales are negative
    if movement_type == "SALE":
        qty = -abs(draw(stock_movement_delta))
    else:
        qty = abs(draw(stock_movement_delta))

    return {
        "type": movement_type,
        "quantity_delta": qty,
        "cost_snapshot": draw(cost_price),
        "notes": draw(st.text(max_size=500)),
    }


@st.composite
def price_calculation_scenario(draw):
    """Generate price calculation test scenarios."""
    base_price = draw(unit_price)
    tax = draw(tax_rate)
    discount = draw(discount_percentage)
    quantity = draw(st.integers(min_value=1, max_value=10000))

    return {
        "base_price": base_price,
        "tax_rate": tax,
        "discount_percentage": discount,
        "quantity": quantity,
    }


@st.composite
def tenant_resource_data(draw):
    """Generate tenant-scoped resource data."""
    return {
        "tenant_id": draw(tenant_id),
        "branch_id": draw(branch_id),
        "resource_id": draw(st.uuids()),
    }


@st.composite
def user_data(draw):
    """Generate valid user data for property-based testing."""
    return {
        "email": draw(email_strategy),
        "full_name": draw(st.text(min_size=2, max_size=100).filter(lambda x: x.strip() == x)),
        "phone": draw(st.one_of(st.none(), phone_number)),
        "is_active": draw(st.booleans()),
    }


# ==============================================================
# Edge Case Strategies
# ==============================================================

# Boundary values for prices
boundary_prices = st.sampled_from(
    [
        Decimal("0.001"),  # Minimum valid
        Decimal("0.01"),
        Decimal("1.00"),
        Decimal("999.999"),
        Decimal("9999.999"),
        Decimal("99999999999999.999"),  # Maximum valid
    ]
)

# Boundary values for quantities
boundary_quantities = st.sampled_from(
    [
        Decimal("0.0000"),  # Zero
        Decimal("0.0001"),  # Minimum positive
        Decimal("1.0000"),
        Decimal("100.0000"),
        Decimal("10000000.0000"),  # Maximum valid
    ]
)

# Invalid SKU patterns for negative testing
invalid_sku_patterns = st.sampled_from(
    [
        "",  # Empty
        " ",  # Whitespace only
        "a" * 51,  # Too long
        "-INVALID",  # Starts with dash
        "INVALID-",  # Ends with dash
        "IN--VALID",  # Double dash
        "lower-case",  # Lowercase
        "WITH SPACE",  # Contains space
        "special@char",  # Special characters
    ]
)
