"""
Tests for Product ML metadata (ml_tags) and custom_data JSONFields.

This module tests the ML metadata storage and retrieval for predictive analytics,
including proper JSON serialization, default values, and complex nested structures.

Tests:
    - T094: ML metadata JSONField storage and retrieval
    - JSONField default values (empty dict)
    - Complex nested JSON structures
    - Serialization/deserialization
"""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.inventario.models import Product, ProductCategory
from apps.inventario.serializers import (ProductCreateSerializer,
                                         ProductSerializer)

User = get_user_model()


@pytest.fixture
def category(db, tenant_context):
    """Create a test product category."""
    return ProductCategory.objects.create(tenant=tenant_context, name="Electronics")


@pytest.fixture
def product_data(tenant_context, category):
    """Base product data for creating test products."""
    return {
        "tenant": tenant_context,
        "sku": "TEST-001",
        "name": "Test Product",
        "category": category,
        "unit_price": Decimal("100.00"),
        "cost_price": Decimal("50.00"),
    }


@pytest.mark.django_db
class TestMLTagsJSONField:
    """Tests for Product.ml_tags JSONField."""

    def test_ml_tags_default_value(self, product_data):
        """Test that ml_tags defaults to empty dict when not provided."""
        product = Product.objects.create(**product_data)

        assert product.ml_tags is not None
        assert product.ml_tags == {}
        assert isinstance(product.ml_tags, dict)

    def test_ml_tags_storage_and_retrieval(self, product_data):
        """Test storing and retrieving ML tags."""
        ml_tags = {
            "category_auto": "electronics",
            "seasonality": "all_year",
            "price_sensitivity": "medium",
            "demand_pattern": "steady",
            "reorder_prediction": 15.5,
        }

        product = Product.objects.create(**product_data, ml_tags=ml_tags)

        # Retrieve from database
        saved_product = Product.objects.get(pk=product.pk)

        assert saved_product.ml_tags == ml_tags
        assert saved_product.ml_tags["category_auto"] == "electronics"
        assert saved_product.ml_tags["seasonality"] == "all_year"
        assert saved_product.ml_tags["price_sensitivity"] == "medium"
        assert saved_product.ml_tags["demand_pattern"] == "steady"
        assert saved_product.ml_tags["reorder_prediction"] == 15.5

    def test_ml_tags_partial_data(self, product_data):
        """Test ml_tags with partial schema (not all fields required)."""
        ml_tags = {"category_auto": "electronics", "demand_pattern": "volatile"}

        product = Product.objects.create(**product_data, ml_tags=ml_tags)

        saved_product = Product.objects.get(pk=product.pk)
        assert saved_product.ml_tags == ml_tags
        assert "seasonality" not in saved_product.ml_tags
        assert "price_sensitivity" not in saved_product.ml_tags

    def test_ml_tags_update(self, product_data):
        """Test updating ml_tags on existing product."""
        product = Product.objects.create(**product_data)

        # Initial ml_tags
        product.ml_tags = {"category_auto": "electronics"}
        product.save()

        # Update ml_tags
        product.ml_tags = {
            "category_auto": "consumer_electronics",
            "seasonality": "summer",
            "price_sensitivity": "high",
            "demand_pattern": "trending_up",
            "reorder_prediction": 7.2,
        }
        product.save()

        saved_product = Product.objects.get(pk=product.pk)
        assert saved_product.ml_tags["category_auto"] == "consumer_electronics"
        assert saved_product.ml_tags["seasonality"] == "summer"
        assert saved_product.ml_tags["reorder_prediction"] == 7.2

    def test_ml_tags_nested_structure(self, product_data):
        """Test ml_tags with complex nested JSON structure."""
        ml_tags = {
            "category_auto": "electronics",
            "predictions": {
                "demand": {"next_7_days": 150, "next_30_days": 600, "confidence": 0.87},
                "reorder": {
                    "days_until_stockout": 15,
                    "recommended_quantity": 200,
                    "confidence": 0.92,
                },
            },
            "seasonality": {
                "pattern": "summer",
                "peak_months": [6, 7, 8],
                "multipliers": {"jan": 0.8, "feb": 0.9, "jun": 1.5, "jul": 1.8, "aug": 1.6},
            },
            "metadata": {
                "last_updated": "2024-11-27T12:00:00Z",
                "model_version": "1.2.3",
                "accuracy_score": 0.89,
            },
        }

        product = Product.objects.create(**product_data, ml_tags=ml_tags)

        saved_product = Product.objects.get(pk=product.pk)

        assert saved_product.ml_tags["predictions"]["demand"]["next_7_days"] == 150
        assert saved_product.ml_tags["predictions"]["reorder"]["confidence"] == 0.92
        assert saved_product.ml_tags["seasonality"]["peak_months"] == [6, 7, 8]
        assert saved_product.ml_tags["seasonality"]["multipliers"]["jul"] == 1.8
        assert saved_product.ml_tags["metadata"]["model_version"] == "1.2.3"

    def test_ml_tags_null_handling(self, product_data):
        """Test that ml_tags defaults to empty dict (cannot be None)."""
        # Without explicit ml_tags, should default to empty dict
        product = Product.objects.create(**product_data)

        saved_product = Product.objects.get(pk=product.pk)
        # Should default to empty dict, not None
        assert saved_product.ml_tags == {}
        assert saved_product.ml_tags is not None


@pytest.mark.django_db
class TestCustomDataJSONField:
    """Tests for Product.custom_data JSONField."""

    def test_custom_data_default_value(self, product_data):
        """Test that custom_data defaults to empty dict when not provided."""
        product = Product.objects.create(**product_data)

        assert product.custom_data is not None
        assert product.custom_data == {}
        assert isinstance(product.custom_data, dict)

    def test_custom_data_storage_and_retrieval(self, product_data):
        """Test storing and retrieving custom data."""
        custom_data = {
            "color": "black",
            "size": "medium",
            "weight": 1.5,
            "material": "plastic",
            "brand": "TestBrand",
        }

        product = Product.objects.create(**product_data, custom_data=custom_data)

        saved_product = Product.objects.get(pk=product.pk)

        assert saved_product.custom_data == custom_data
        assert saved_product.custom_data["color"] == "black"
        assert saved_product.custom_data["size"] == "medium"
        assert saved_product.custom_data["weight"] == 1.5
        assert saved_product.custom_data["material"] == "plastic"
        assert saved_product.custom_data["brand"] == "TestBrand"

    def test_custom_data_flexible_schema(self, product_data):
        """Test that custom_data supports flexible tenant-defined schema."""
        # Different tenants can have completely different custom data structures
        custom_data_1 = {"color": "red", "warranty_months": 12, "energy_rating": "A++"}

        custom_data_2 = {
            "vintage": "2020",
            "alcohol_content": 13.5,
            "region": "Mendoza",
            "grape_variety": ["Malbec", "Cabernet Sauvignon"],
        }

        product_1 = Product.objects.create(
            **{**product_data, "sku": "PROD-001"}, custom_data=custom_data_1
        )

        product_2 = Product.objects.create(
            **{**product_data, "sku": "PROD-002"}, custom_data=custom_data_2
        )

        saved_1 = Product.objects.get(pk=product_1.pk)
        saved_2 = Product.objects.get(pk=product_2.pk)

        assert saved_1.custom_data == custom_data_1
        assert saved_2.custom_data == custom_data_2
        assert "warranty_months" in saved_1.custom_data
        assert "vintage" in saved_2.custom_data

    def test_custom_data_nested_structure(self, product_data):
        """Test custom_data with complex nested structure."""
        custom_data = {
            "dimensions": {"length": 30.5, "width": 20.0, "height": 15.0, "unit": "cm"},
            "technical_specs": {
                "processor": "Intel i7",
                "ram": "16GB",
                "storage": {"type": "SSD", "capacity": "512GB"},
            },
            "certifications": ["CE", "FCC", "RoHS"],
            "included_accessories": [
                {"name": "Power Adapter", "quantity": 1},
                {"name": "USB Cable", "quantity": 2},
                {"name": "User Manual", "quantity": 1},
            ],
        }

        product = Product.objects.create(**product_data, custom_data=custom_data)

        saved_product = Product.objects.get(pk=product.pk)

        assert saved_product.custom_data["dimensions"]["length"] == 30.5
        assert saved_product.custom_data["technical_specs"]["storage"]["type"] == "SSD"
        assert "CE" in saved_product.custom_data["certifications"]
        assert saved_product.custom_data["included_accessories"][1]["name"] == "USB Cable"

    def test_custom_data_update(self, product_data):
        """Test updating custom_data on existing product."""
        product = Product.objects.create(
            **product_data, custom_data={"color": "black", "size": "medium"}
        )

        # Update custom_data
        product.custom_data = {"color": "blue", "size": "large", "weight": 2.0, "material": "metal"}
        product.save()

        saved_product = Product.objects.get(pk=product.pk)
        assert saved_product.custom_data["color"] == "blue"
        assert saved_product.custom_data["size"] == "large"
        assert saved_product.custom_data["weight"] == 2.0
        assert saved_product.custom_data["material"] == "metal"

    def test_custom_data_null_handling(self, product_data):
        """Test that custom_data defaults to empty dict (cannot be None)."""
        # Without explicit custom_data, should default to empty dict
        product = Product.objects.create(**product_data)

        saved_product = Product.objects.get(pk=product.pk)
        # Should default to empty dict, not None
        assert saved_product.custom_data == {}
        assert saved_product.custom_data is not None


@pytest.mark.django_db
class TestJSONFieldSerialization:
    """Tests for JSON field serialization in API responses."""

    def test_product_serializer_includes_json_fields(self, product_data):
        """Test that ProductSerializer includes custom_data and ml_tags."""
        ml_tags = {"category_auto": "electronics", "demand_pattern": "steady"}
        custom_data = {"color": "black", "brand": "TestBrand"}

        product = Product.objects.create(**product_data, ml_tags=ml_tags, custom_data=custom_data)

        serializer = ProductSerializer(product)
        data = serializer.data

        assert "ml_tags" in data
        assert "custom_data" in data
        assert data["ml_tags"] == ml_tags
        assert data["custom_data"] == custom_data

    def test_product_create_serializer_json_fields_writable(self, product_data, admin_user):
        """Test that ProductCreateSerializer accepts ml_tags and custom_data."""
        create_data = {
            "sku": "CREATE-001",
            "name": "Created Product",
            "unit_price": "100.00",
            "cost_price": "50.00",
            "category": product_data["category"].id,
            "ml_tags": {"category_auto": "test_category", "seasonality": "all_year"},
            "custom_data": {"color": "red", "size": "large"},
        }

        serializer = ProductCreateSerializer(
            data=create_data, context={"request": type("Request", (), {"user": admin_user})()}
        )

        assert serializer.is_valid(), serializer.errors
        product = serializer.save()

        assert product.ml_tags == create_data["ml_tags"]
        assert product.custom_data == create_data["custom_data"]

    def test_json_fields_empty_dict_serialization(self, product_data):
        """Test that empty dicts serialize correctly."""
        product = Product.objects.create(**product_data)

        serializer = ProductSerializer(product)
        data = serializer.data

        assert data["ml_tags"] == {}
        assert data["custom_data"] == {}

    def test_json_fields_complex_nested_serialization(self, product_data):
        """Test serialization of complex nested JSON structures."""
        ml_tags = {
            "predictions": {"demand": {"next_7_days": 150, "confidence": 0.87}},
            "seasonality": {"peak_months": [6, 7, 8]},
        }

        custom_data = {
            "dimensions": {"length": 30.5, "width": 20.0},
            "certifications": ["CE", "FCC"],
        }

        product = Product.objects.create(**product_data, ml_tags=ml_tags, custom_data=custom_data)

        serializer = ProductSerializer(product)
        data = serializer.data

        assert data["ml_tags"]["predictions"]["demand"]["next_7_days"] == 150
        assert data["ml_tags"]["seasonality"]["peak_months"] == [6, 7, 8]
        assert data["custom_data"]["dimensions"]["length"] == 30.5
        assert "CE" in data["custom_data"]["certifications"]

    def test_json_fields_update_via_serializer(self, product_data, admin_user):
        """Test updating JSON fields via serializer.

        CustomFieldsMixin applies merge semantics on update: incoming keys
        merge with existing, unstated keys are preserved, null removes keys.
        """
        product = Product.objects.create(
            **product_data, ml_tags={"old": "data"}, custom_data={"old": "attribute"}
        )

        update_data = {
            "ml_tags": {"category_auto": "new_category", "demand_pattern": "trending_up"},
            "custom_data": {"color": "blue", "material": "metal"},
        }

        serializer = ProductCreateSerializer(
            product,
            data=update_data,
            partial=True,
            context={"request": type("Request", (), {"user": admin_user})()},
        )

        assert serializer.is_valid(), serializer.errors
        updated_product = serializer.save()

        assert updated_product.ml_tags == update_data["ml_tags"]
        # Merge semantics: existing "old" key preserved, new keys added
        assert updated_product.custom_data == {
            "old": "attribute",
            "color": "blue",
            "material": "metal",
        }


@pytest.mark.django_db
class TestJSONFieldEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_string_in_json_field(self, product_data):
        """Test handling of various data types in JSON fields."""
        custom_data = {
            "string_field": "text",
            "number_field": 42,
            "float_field": 3.14,
            "bool_field": True,
            "null_field": None,
            "empty_string": "",
            "empty_list": [],
            "empty_dict": {},
        }

        product = Product.objects.create(**product_data, custom_data=custom_data)

        saved_product = Product.objects.get(pk=product.pk)

        assert saved_product.custom_data["string_field"] == "text"
        assert saved_product.custom_data["number_field"] == 42
        assert saved_product.custom_data["float_field"] == 3.14
        assert saved_product.custom_data["bool_field"] is True
        assert saved_product.custom_data["null_field"] is None
        assert saved_product.custom_data["empty_string"] == ""
        assert saved_product.custom_data["empty_list"] == []
        assert saved_product.custom_data["empty_dict"] == {}

    def test_large_json_structure(self, product_data):
        """Test handling of large JSON structures."""
        # Create a large but reasonable JSON structure
        ml_tags = {f"category_{i}": f"value_{i}" for i in range(50)}
        ml_tags["predictions"] = {
            f"metric_{i}": {"value": i * 1.5, "confidence": 0.8 + (i * 0.001)} for i in range(20)
        }

        product = Product.objects.create(**product_data, ml_tags=ml_tags)

        saved_product = Product.objects.get(pk=product.pk)
        assert len(saved_product.ml_tags) > 50
        assert saved_product.ml_tags["category_25"] == "value_25"
        assert saved_product.ml_tags["predictions"]["metric_10"]["value"] == 15.0

    def test_unicode_in_json_fields(self, product_data):
        """Test handling of unicode characters in JSON fields."""
        custom_data = {
            "spanish": "Año 2024 - Región Española",
            "chinese": "产品描述",
            "emoji": "Test 🎉 Product 🚀",
            "special": "Ñoño & Café",
        }

        product = Product.objects.create(**product_data, custom_data=custom_data)

        saved_product = Product.objects.get(pk=product.pk)
        assert saved_product.custom_data["spanish"] == "Año 2024 - Región Española"
        assert saved_product.custom_data["chinese"] == "产品描述"
        assert saved_product.custom_data["emoji"] == "Test 🎉 Product 🚀"
        assert saved_product.custom_data["special"] == "Ñoño & Café"
