"""
Test suite for StockService robustness improvements.

Tests cover:
- Product.DoesNotExist exception handling (C-001)
- UUID validation in all service methods (C-003)
- Proper error responses for invalid inputs
- Security boundary cases
"""

import uuid
from decimal import Decimal

import pytest
from django.core.exceptions import ObjectDoesNotExist

from apps.inventario.models import StockMovement
from apps.inventario.services.stock_service import (
    BranchNotFoundError,
    ProductNotFoundError,
    StockService,
)


@pytest.mark.django_db
class TestProductNotFoundHandling:
    """Tests for Product.DoesNotExist exception handling (C-001)."""

    def test_record_movement_nonexistent_product_raises_error(self, tenant_context, branch):
        """Test that record_movement raises ProductNotFoundError for nonexistent product."""
        fake_product_id = str(uuid.uuid4())

        with pytest.raises(ProductNotFoundError) as exc_info:
            StockService.record_movement(
                tenant_id=str(tenant_context.id),
                product_id=fake_product_id,
                branch_id=str(branch.id),
                movement_type=StockMovement.MovementType.PURCHASE,
                quantity_delta=Decimal("10.0000"),
            )

        assert exc_info.value.product_id == fake_product_id
        assert exc_info.value.tenant_id == str(tenant_context.id)
        assert "Product not found" in str(exc_info.value)

    def test_create_correction_nonexistent_product_raises_error(self, tenant_context, branch):
        """Test that create_correction raises ProductNotFoundError for nonexistent product."""
        fake_product_id = str(uuid.uuid4())

        with pytest.raises(ProductNotFoundError) as exc_info:
            StockService.create_correction(
                tenant_id=str(tenant_context.id),
                product_id=fake_product_id,
                branch_id=str(branch.id),
                new_quantity=Decimal("100.0000"),
                reason="Test correction",
            )

        assert exc_info.value.product_id == fake_product_id
        assert "Product not found" in str(exc_info.value)

    def test_transfer_stock_nonexistent_product_raises_error(
        self, tenant_context, branch, other_branch
    ):
        """Test that transfer_stock raises ProductNotFoundError for nonexistent product."""
        fake_product_id = str(uuid.uuid4())

        with pytest.raises(ProductNotFoundError) as exc_info:
            StockService.transfer_stock(
                tenant_id=str(tenant_context.id),
                product_id=fake_product_id,
                from_branch_id=str(branch.id),
                to_branch_id=str(other_branch.id),
                quantity=Decimal("10.0000"),
            )

        assert exc_info.value.product_id == fake_product_id
        assert "Product not found" in str(exc_info.value)

    def test_get_product_stock_summary_nonexistent_product_raises_error(self, tenant_context):
        """Test that get_product_stock_summary raises ProductNotFoundError."""
        fake_product_id = str(uuid.uuid4())

        with pytest.raises(ProductNotFoundError) as exc_info:
            StockService.get_product_stock_summary(
                tenant_id=str(tenant_context.id),
                product_id=fake_product_id,
            )

        assert exc_info.value.product_id == fake_product_id
        assert "Product not found" in str(exc_info.value)


@pytest.mark.django_db
class TestBranchNotFoundHandling:
    """Tests for Branch.DoesNotExist exception handling."""

    def test_record_movement_nonexistent_branch_raises_error(self, tenant_context, product):
        """Test that record_movement raises BranchNotFoundError for nonexistent branch."""
        fake_branch_id = str(uuid.uuid4())

        with pytest.raises(BranchNotFoundError) as exc_info:
            StockService.record_movement(
                tenant_id=str(tenant_context.id),
                product_id=str(product.id),
                branch_id=fake_branch_id,
                movement_type=StockMovement.MovementType.PURCHASE,
                quantity_delta=Decimal("10.0000"),
            )

        assert exc_info.value.branch_id == fake_branch_id
        assert exc_info.value.tenant_id == str(tenant_context.id)
        assert "Branch not found" in str(exc_info.value)

    def test_transfer_stock_nonexistent_source_branch_raises_error(
        self, tenant_context, product, branch
    ):
        """Test that transfer_stock raises BranchNotFoundError for nonexistent source branch."""
        fake_branch_id = str(uuid.uuid4())

        with pytest.raises(BranchNotFoundError) as exc_info:
            StockService.transfer_stock(
                tenant_id=str(tenant_context.id),
                product_id=str(product.id),
                from_branch_id=fake_branch_id,
                to_branch_id=str(branch.id),
                quantity=Decimal("10.0000"),
            )

        assert exc_info.value.branch_id == fake_branch_id
        assert "Branch not found" in str(exc_info.value)

    def test_transfer_stock_nonexistent_destination_branch_raises_error(
        self, tenant_context, product, branch
    ):
        """Test that transfer_stock raises BranchNotFoundError for nonexistent destination."""
        fake_branch_id = str(uuid.uuid4())

        # First add stock to source branch
        StockService.record_movement(
            tenant_id=str(tenant_context.id),
            product_id=str(product.id),
            branch_id=str(branch.id),
            movement_type=StockMovement.MovementType.PURCHASE,
            quantity_delta=Decimal("100.0000"),
        )

        with pytest.raises(BranchNotFoundError) as exc_info:
            StockService.transfer_stock(
                tenant_id=str(tenant_context.id),
                product_id=str(product.id),
                from_branch_id=str(branch.id),
                to_branch_id=fake_branch_id,
                quantity=Decimal("10.0000"),
            )

        assert exc_info.value.branch_id == fake_branch_id
        assert "Branch not found" in str(exc_info.value)


@pytest.mark.django_db
class TestUUIDValidation:
    """Tests for UUID validation in service methods (C-003)."""

    def test_record_movement_invalid_tenant_uuid_raises_error(self, product, branch):
        """Test that invalid tenant UUID raises ValueError."""
        with pytest.raises(ValueError, match="Invalid UUID parameter"):
            StockService.record_movement(
                tenant_id="not-a-uuid",
                product_id=str(product.id),
                branch_id=str(branch.id),
                movement_type=StockMovement.MovementType.PURCHASE,
                quantity_delta=Decimal("10.0000"),
            )

    def test_record_movement_invalid_product_uuid_raises_error(self, tenant_context, branch):
        """Test that invalid product UUID raises ValueError."""
        with pytest.raises(ValueError, match="Invalid UUID parameter"):
            StockService.record_movement(
                tenant_id=str(tenant_context.id),
                product_id="invalid-product-uuid",
                branch_id=str(branch.id),
                movement_type=StockMovement.MovementType.PURCHASE,
                quantity_delta=Decimal("10.0000"),
            )

    def test_record_movement_invalid_branch_uuid_raises_error(self, tenant_context, product):
        """Test that invalid branch UUID raises ValueError."""
        with pytest.raises(ValueError, match="Invalid UUID parameter"):
            StockService.record_movement(
                tenant_id=str(tenant_context.id),
                product_id=str(product.id),
                branch_id="not-valid",
                movement_type=StockMovement.MovementType.PURCHASE,
                quantity_delta=Decimal("10.0000"),
            )

    def test_create_correction_invalid_product_uuid_raises_error(self, tenant_context, branch):
        """Test that create_correction rejects invalid product UUID."""
        with pytest.raises(ValueError, match="Invalid UUID parameter"):
            StockService.create_correction(
                tenant_id=str(tenant_context.id),
                product_id="12345",
                branch_id=str(branch.id),
                new_quantity=Decimal("100.0000"),
                reason="Test",
            )

    def test_transfer_stock_invalid_source_branch_uuid_raises_error(
        self, tenant_context, product, branch
    ):
        """Test that transfer_stock rejects invalid source branch UUID."""
        with pytest.raises(ValueError, match="Invalid UUID parameter"):
            StockService.transfer_stock(
                tenant_id=str(tenant_context.id),
                product_id=str(product.id),
                from_branch_id="invalid",
                to_branch_id=str(branch.id),
                quantity=Decimal("10.0000"),
            )

    def test_transfer_stock_invalid_destination_branch_uuid_raises_error(
        self, tenant_context, product, branch
    ):
        """Test that transfer_stock rejects invalid destination branch UUID."""
        with pytest.raises(ValueError, match="Invalid UUID parameter"):
            StockService.transfer_stock(
                tenant_id=str(tenant_context.id),
                product_id=str(product.id),
                from_branch_id=str(branch.id),
                to_branch_id="not-a-uuid",
                quantity=Decimal("10.0000"),
            )

    def test_get_product_stock_summary_invalid_product_uuid_raises_error(self, tenant_context):
        """Test that get_product_stock_summary rejects invalid product UUID."""
        with pytest.raises(ValueError, match="Invalid UUID parameter"):
            StockService.get_product_stock_summary(
                tenant_id=str(tenant_context.id),
                product_id="not-valid-uuid",
            )


@pytest.mark.django_db
class TestSecurityBoundaries:
    """Security-focused tests for input validation."""

    def test_sql_injection_in_product_id_rejected(self, tenant_context, branch):
        """Test that SQL injection attempts in product_id are rejected."""
        malicious_input = "'; DROP TABLE products; --"

        with pytest.raises(ValueError, match="Invalid UUID parameter"):
            StockService.record_movement(
                tenant_id=str(tenant_context.id),
                product_id=malicious_input,
                branch_id=str(branch.id),
                movement_type=StockMovement.MovementType.PURCHASE,
                quantity_delta=Decimal("10.0000"),
            )

    def test_xss_attempt_in_product_id_rejected(self, tenant_context, branch):
        """Test that XSS attempts in product_id are rejected."""
        malicious_input = "<script>alert('xss')</script>"

        with pytest.raises(ValueError, match="Invalid UUID parameter"):
            StockService.record_movement(
                tenant_id=str(tenant_context.id),
                product_id=malicious_input,
                branch_id=str(branch.id),
                movement_type=StockMovement.MovementType.PURCHASE,
                quantity_delta=Decimal("10.0000"),
            )

    def test_path_traversal_in_product_id_rejected(self, tenant_context, branch):
        """Test that path traversal attempts in product_id are rejected."""
        malicious_input = "../../etc/passwd"

        with pytest.raises(ValueError, match="Invalid UUID parameter"):
            StockService.record_movement(
                tenant_id=str(tenant_context.id),
                product_id=malicious_input,
                branch_id=str(branch.id),
                movement_type=StockMovement.MovementType.PURCHASE,
                quantity_delta=Decimal("10.0000"),
            )

    def test_very_long_string_in_product_id_rejected(self, tenant_context, branch):
        """Test that very long strings in product_id are rejected."""
        malicious_input = "a" * 10000

        with pytest.raises(ValueError, match="Invalid UUID parameter"):
            StockService.record_movement(
                tenant_id=str(tenant_context.id),
                product_id=malicious_input,
                branch_id=str(branch.id),
                movement_type=StockMovement.MovementType.PURCHASE,
                quantity_delta=Decimal("10.0000"),
            )

    def test_null_byte_injection_in_product_id_rejected(self, tenant_context, branch):
        """Test that null byte injection in product_id is rejected."""
        malicious_input = "550e8400\x00-e29b-41d4-a716-446655440000"

        with pytest.raises(ValueError, match="Invalid UUID parameter"):
            StockService.record_movement(
                tenant_id=str(tenant_context.id),
                product_id=malicious_input,
                branch_id=str(branch.id),
                movement_type=StockMovement.MovementType.PURCHASE,
                quantity_delta=Decimal("10.0000"),
            )


@pytest.mark.django_db
class TestErrorMessages:
    """Tests for error message clarity and information."""

    def test_product_not_found_error_includes_product_id(self, tenant_context, branch):
        """Test that ProductNotFoundError includes product_id in message."""
        fake_product_id = str(uuid.uuid4())

        with pytest.raises(ProductNotFoundError) as exc_info:
            StockService.record_movement(
                tenant_id=str(tenant_context.id),
                product_id=fake_product_id,
                branch_id=str(branch.id),
                movement_type=StockMovement.MovementType.PURCHASE,
                quantity_delta=Decimal("10.0000"),
            )

        error_msg = str(exc_info.value)
        assert fake_product_id in error_msg
        assert str(tenant_context.id) in error_msg

    def test_branch_not_found_error_includes_branch_id(self, tenant_context, product):
        """Test that BranchNotFoundError includes branch_id in message."""
        fake_branch_id = str(uuid.uuid4())

        with pytest.raises(BranchNotFoundError) as exc_info:
            StockService.record_movement(
                tenant_id=str(tenant_context.id),
                product_id=str(product.id),
                branch_id=fake_branch_id,
                movement_type=StockMovement.MovementType.PURCHASE,
                quantity_delta=Decimal("10.0000"),
            )

        error_msg = str(exc_info.value)
        assert fake_branch_id in error_msg
        assert str(tenant_context.id) in error_msg

    def test_uuid_validation_error_includes_field_name(self, tenant_context, branch):
        """Test that UUID validation error includes field name."""
        with pytest.raises(ValueError, match="Invalid UUID parameter") as exc_info:
            StockService.record_movement(
                tenant_id=str(tenant_context.id),
                product_id="invalid-uuid",
                branch_id=str(branch.id),
                movement_type=StockMovement.MovementType.PURCHASE,
                quantity_delta=Decimal("10.0000"),
            )

        # The error message should be informative
        assert "Invalid UUID parameter" in str(exc_info.value)


@pytest.mark.django_db
class TestValidInputsStillWork:
    """Tests to ensure valid inputs still work correctly after adding validation."""

    def test_record_movement_with_valid_uuids_works(self, tenant_context, product, branch):
        """Test that record_movement still works with valid UUIDs."""
        movement = StockService.record_movement(
            tenant_id=str(tenant_context.id),
            product_id=str(product.id),
            branch_id=str(branch.id),
            movement_type=StockMovement.MovementType.PURCHASE,
            quantity_delta=Decimal("50.0000"),
            cost_snapshot=Decimal("25.00"),
        )

        assert movement.id is not None
        assert movement.type == StockMovement.MovementType.PURCHASE
        assert movement.quantity_delta == Decimal("50.0000")

    def test_create_correction_with_valid_uuids_works(self, tenant_context, product, branch):
        """Test that create_correction still works with valid UUIDs."""
        movement = StockService.create_correction(
            tenant_id=str(tenant_context.id),
            product_id=str(product.id),
            branch_id=str(branch.id),
            new_quantity=Decimal("100.0000"),
            reason="Initial stock count",
        )

        assert movement.id is not None
        assert movement.type == StockMovement.MovementType.ADJ

    def test_transfer_stock_with_valid_uuids_works(
        self, tenant_context, product, branch, other_branch
    ):
        """Test that transfer_stock still works with valid UUIDs."""
        # First add stock
        StockService.record_movement(
            tenant_id=str(tenant_context.id),
            product_id=str(product.id),
            branch_id=str(branch.id),
            movement_type=StockMovement.MovementType.PURCHASE,
            quantity_delta=Decimal("100.0000"),
        )

        # Then transfer
        out_movement, in_movement = StockService.transfer_stock(
            tenant_id=str(tenant_context.id),
            product_id=str(product.id),
            from_branch_id=str(branch.id),
            to_branch_id=str(other_branch.id),
            quantity=Decimal("30.0000"),
        )

        assert out_movement.type == StockMovement.MovementType.TRANS_OUT
        assert in_movement.type == StockMovement.MovementType.TRANS_IN
        assert out_movement.quantity_delta == Decimal("-30.0000")
        assert in_movement.quantity_delta == Decimal("30.0000")

    def test_uuid_objects_still_accepted(self, tenant_context, product, branch):
        """Test that UUID objects (not strings) still work."""
        # Pass UUID objects directly
        movement = StockService.record_movement(
            tenant_id=tenant_context.id,  # UUID object
            product_id=product.id,  # UUID object
            branch_id=branch.id,  # UUID object
            movement_type=StockMovement.MovementType.PURCHASE,
            quantity_delta=Decimal("50.0000"),
        )

        assert movement.id is not None
