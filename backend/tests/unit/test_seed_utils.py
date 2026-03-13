"""Unit tests for seed data utilities.

Tests deterministic UUID generation and SeedScenario dataclass functionality.
Per spec.md FR-025 through FR-028 requirements:
- T056: Unit test for UUID5 deterministic generation
"""

from __future__ import annotations

import json
import tempfile
import uuid
from pathlib import Path

import pytest

from apps.core.management.commands.seed_utils import (
    GRAVITEA_NAMESPACE,
    EntityConfig,
    KnownUUIDs,
    SeedScenario,
    deterministic_uuid,
    deterministic_uuid_from_parts,
)


@pytest.mark.unit
class TestDeterministicUUID:
    """Test suite for deterministic UUID generation."""

    def test_same_inputs_produce_same_uuid(self):
        """Same entity_type and identifier always produce identical UUID."""
        uuid1 = deterministic_uuid("tenant", "demo")
        uuid2 = deterministic_uuid("tenant", "demo")

        assert uuid1 == uuid2
        assert isinstance(uuid1, uuid.UUID)

    def test_different_inputs_produce_different_uuids(self):
        """Different inputs produce different UUIDs."""
        uuid1 = deterministic_uuid("tenant", "demo")
        uuid2 = deterministic_uuid("tenant", "other")
        uuid3 = deterministic_uuid("user", "demo")

        assert uuid1 != uuid2
        assert uuid1 != uuid3
        assert uuid2 != uuid3

    def test_uuid_is_version_5(self):
        """Generated UUIDs are version 5 (SHA-1 based)."""
        result = deterministic_uuid("product", "SKU-001")

        assert result.version == 5

    def test_uuid_uses_gravitea_namespace(self):
        """UUIDs are generated using GRAVITEA_NAMESPACE."""
        expected = uuid.uuid5(GRAVITEA_NAMESPACE, "tenant:demo")
        result = deterministic_uuid("tenant", "demo")

        assert result == expected

    def test_reproducible_across_calls(self):
        """UUID generation is reproducible across multiple calls."""
        results = [deterministic_uuid("branch", "main") for _ in range(100)]

        assert all(r == results[0] for r in results)


@pytest.mark.unit
class TestDeterministicUUIDFromParts:
    """Test suite for multi-part UUID generation."""

    def test_single_part(self):
        """Single part generates valid UUID."""
        result = deterministic_uuid_from_parts("tenant")

        assert isinstance(result, uuid.UUID)
        assert result.version == 5

    def test_multiple_parts(self):
        """Multiple parts are joined correctly."""
        result = deterministic_uuid_from_parts("stock", "branch-1", "product-1")
        expected = uuid.uuid5(GRAVITEA_NAMESPACE, "stock:branch-1:product-1")

        assert result == expected

    def test_order_matters(self):
        """Part order affects the generated UUID."""
        uuid1 = deterministic_uuid_from_parts("a", "b", "c")
        uuid2 = deterministic_uuid_from_parts("c", "b", "a")

        assert uuid1 != uuid2


@pytest.mark.unit
class TestEntityConfig:
    """Test suite for EntityConfig dataclass."""

    def test_basic_creation(self):
        """EntityConfig can be created with required fields."""
        config = EntityConfig(
            entity_type="tenant",
            identifier="demo",
            data={"name": "Demo Tenant"},
        )

        assert config.entity_type == "tenant"
        assert config.identifier == "demo"
        assert config.data == {"name": "Demo Tenant"}
        assert config.dependencies == []

    def test_with_dependencies(self):
        """EntityConfig correctly stores dependencies."""
        config = EntityConfig(
            entity_type="user",
            identifier="admin",
            data={"email": "admin@test.com"},
            dependencies=["tenant:demo", "role:admin"],
        )

        assert config.dependencies == ["tenant:demo", "role:admin"]

    def test_uuid_property(self):
        """UUID property returns deterministic UUID."""
        config = EntityConfig(
            entity_type="product",
            identifier="SKU-001",
            data={},
        )

        expected = deterministic_uuid("product", "SKU-001")
        assert config.uuid == expected


@pytest.mark.unit
class TestSeedScenario:
    """Test suite for SeedScenario dataclass."""

    def test_basic_creation(self):
        """SeedScenario can be created with minimal fields."""
        scenario = SeedScenario(
            name="test",
            description="Test scenario",
        )

        assert scenario.name == "test"
        assert scenario.description == "Test scenario"
        assert scenario.version == "1.0.0"
        assert scenario.tenants == []
        assert scenario.users == []
        assert scenario.branches == []

    def test_from_dict(self):
        """SeedScenario can be created from dictionary."""
        data = {
            "name": "minimal",
            "description": "Minimal test data",
            "version": "1.0.0",
            "tenants": [
                {
                    "id": "demo",
                    "data": {"name": "Demo Tenant"},
                }
            ],
            "users": [
                {
                    "identifier": "admin",
                    "data": {"email": "admin@test.com"},
                    "dependencies": ["tenant:demo"],
                }
            ],
        }

        scenario = SeedScenario.from_dict(data)

        assert scenario.name == "minimal"
        assert len(scenario.tenants) == 1
        assert scenario.tenants[0].identifier == "demo"
        assert len(scenario.users) == 1
        assert scenario.users[0].identifier == "admin"
        assert scenario.users[0].dependencies == ["tenant:demo"]

    def test_from_json_file(self):
        """SeedScenario can be loaded from JSON file."""
        data = {
            "name": "file_test",
            "description": "Test from file",
            "tenants": [{"id": "test", "data": {"name": "Test"}}],
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(data, f)
            temp_path = f.name

        try:
            scenario = SeedScenario.from_json_file(temp_path)

            assert scenario.name == "file_test"
            assert len(scenario.tenants) == 1
        finally:
            Path(temp_path).unlink()

    def test_from_json_file_not_found(self):
        """SeedScenario raises FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            SeedScenario.from_json_file("/nonexistent/path.json")

    def test_get_uuid(self):
        """get_uuid returns scenario-prefixed deterministic UUID."""
        scenario = SeedScenario(name="standard", description="Standard scenario")

        tenant_uuid = scenario.get_uuid("tenant", "demo")
        expected = deterministic_uuid("tenant", "standard:demo")

        assert tenant_uuid == expected

    def test_to_dict(self):
        """to_dict serializes scenario correctly."""
        scenario = SeedScenario(
            name="test",
            description="Test",
            version="2.0.0",
        )
        scenario.tenants.append(
            EntityConfig(
                entity_type="tenant",
                identifier="demo",
                data={"name": "Demo"},
            )
        )

        result = scenario.to_dict()

        assert result["name"] == "test"
        assert result["version"] == "2.0.0"
        assert len(result["tenants"]) == 1
        assert result["tenants"][0]["identifier"] == "demo"


@pytest.mark.unit
class TestKnownUUIDs:
    """Test suite for pre-computed known UUIDs."""

    def test_minimal_tenant_uuid(self):
        """Minimal tenant UUID matches expected generation."""
        expected = deterministic_uuid("tenant", "minimal:demo")
        assert KnownUUIDs.MINIMAL_TENANT == expected

    def test_standard_tenant_uuid(self):
        """Standard tenant UUID matches expected generation."""
        expected = deterministic_uuid("tenant", "standard:demo")
        assert KnownUUIDs.STANDARD_TENANT == expected

    def test_multi_tenant_alpha(self):
        """Multi-tenant alpha UUID matches expected generation."""
        expected = deterministic_uuid("tenant", "multi_tenant:alpha")
        assert KnownUUIDs.TENANT_ALPHA == expected

    def test_product_uuids(self):
        """Product UUIDs match expected generation."""
        expected_001 = deterministic_uuid("product", "standard:SKU-001")
        expected_002 = deterministic_uuid("product", "standard:SKU-002")

        assert KnownUUIDs.PRODUCT_001 == expected_001
        assert KnownUUIDs.PRODUCT_002 == expected_002

    def test_all_uuids_are_unique(self):
        """All pre-computed UUIDs are unique."""
        all_uuids = [
            KnownUUIDs.MINIMAL_TENANT,
            KnownUUIDs.MINIMAL_BRANCH,
            KnownUUIDs.MINIMAL_ADMIN,
            KnownUUIDs.MINIMAL_ROLE,
            KnownUUIDs.STANDARD_TENANT,
            KnownUUIDs.STANDARD_BRANCH_MAIN,
            KnownUUIDs.STANDARD_BRANCH_NORTH,
            KnownUUIDs.STANDARD_ADMIN,
            KnownUUIDs.STANDARD_MANAGER,
            KnownUUIDs.STANDARD_CASHIER,
            KnownUUIDs.TENANT_ALPHA,
            KnownUUIDs.TENANT_BETA,
            KnownUUIDs.ALPHA_BRANCH,
            KnownUUIDs.BETA_BRANCH,
            KnownUUIDs.ALPHA_ADMIN,
            KnownUUIDs.BETA_ADMIN,
            KnownUUIDs.PRODUCT_001,
            KnownUUIDs.PRODUCT_002,
            KnownUUIDs.PRODUCT_003,
            KnownUUIDs.CATEGORY_BEVERAGES,
            KnownUUIDs.CATEGORY_FOOD,
            KnownUUIDs.CATEGORY_CLEANING,
        ]

        assert len(all_uuids) == len(set(all_uuids))

    def test_uuids_are_stable(self):
        """Known UUIDs are stable across module reloads."""
        # Re-compute the expected values
        expected_minimal = deterministic_uuid("tenant", "minimal:demo")
        expected_standard = deterministic_uuid("tenant", "standard:demo")

        # These should always be the same
        assert KnownUUIDs.MINIMAL_TENANT == expected_minimal
        assert KnownUUIDs.STANDARD_TENANT == expected_standard
