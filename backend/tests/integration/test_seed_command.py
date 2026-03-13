"""Integration tests for seed_data management command.

Tests seed command functionality including scenario-based seeding
and deterministic UUID generation.

Per spec.md FR-025 through FR-028 requirements:
- T057-T059: Integration tests for seed command
"""

from __future__ import annotations

from io import StringIO

import pytest
from django.core.management import call_command

from apps.core.management.commands.seed_utils import (
    KnownUUIDs,
    SeedScenario,
    list_available_scenarios,
    load_scenario,
)


@pytest.mark.django_db(transaction=True)
class TestSeedScenarioLoading:
    """Test suite for scenario file loading."""

    def test_list_available_scenarios(self):
        """list_available_scenarios returns scenario names."""
        scenarios = list_available_scenarios()

        assert isinstance(scenarios, list)
        assert "minimal" in scenarios
        assert "standard" in scenarios
        assert "multi_tenant" in scenarios

    def test_load_minimal_scenario(self):
        """Minimal scenario loads correctly."""
        scenario = load_scenario("minimal")

        assert scenario.name == "minimal"
        assert len(scenario.tenants) == 1
        assert scenario.tenants[0].identifier == "demo"
        assert len(scenario.users) == 1
        assert len(scenario.branches) == 1

    def test_load_standard_scenario(self):
        """Standard scenario loads with expected entities."""
        scenario = load_scenario("standard")

        assert scenario.name == "standard"
        assert len(scenario.tenants) == 1
        assert len(scenario.users) == 3  # admin, manager, cashier
        assert len(scenario.branches) == 2  # main, north
        assert len(scenario.categories) == 3  # beverages, food, cleaning
        assert len(scenario.products) == 3
        assert len(scenario.stock_levels) == 5

    def test_load_multi_tenant_scenario(self):
        """Multi-tenant scenario loads with two tenants."""
        scenario = load_scenario("multi_tenant")

        assert scenario.name == "multi_tenant"
        assert len(scenario.tenants) == 2
        tenant_ids = [t.identifier for t in scenario.tenants]
        assert "alpha" in tenant_ids
        assert "beta" in tenant_ids
        assert len(scenario.branches) == 2  # one per tenant

    def test_load_nonexistent_scenario_raises_error(self):
        """Loading nonexistent scenario raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_scenario("nonexistent_scenario")


@pytest.mark.django_db(transaction=True)
class TestSeedScenarioUUIDs:
    """Test deterministic UUID generation from scenarios."""

    def test_scenario_uuid_is_deterministic(self):
        """Same scenario produces same UUIDs."""
        scenario1 = load_scenario("minimal")
        scenario2 = load_scenario("minimal")

        uuid1 = scenario1.get_uuid("tenant", "demo")
        uuid2 = scenario2.get_uuid("tenant", "demo")

        assert uuid1 == uuid2

    def test_different_scenarios_produce_different_uuids(self):
        """Different scenarios produce different UUIDs for same entity."""
        minimal = load_scenario("minimal")
        standard = load_scenario("standard")

        minimal_uuid = minimal.get_uuid("tenant", "demo")
        standard_uuid = standard.get_uuid("tenant", "demo")

        # Note: UUIDs include scenario name as prefix
        assert minimal_uuid != standard_uuid

    def test_known_uuids_match_scenario_uuids(self):
        """KnownUUIDs class values match scenario-generated UUIDs."""
        minimal = load_scenario("minimal")
        standard = load_scenario("standard")
        multi_tenant = load_scenario("multi_tenant")

        # Minimal scenario
        assert minimal.get_uuid("tenant", "demo") == KnownUUIDs.MINIMAL_TENANT
        assert minimal.get_uuid("branch", "main") == KnownUUIDs.MINIMAL_BRANCH
        assert minimal.get_uuid("user", "admin") == KnownUUIDs.MINIMAL_ADMIN

        # Standard scenario
        assert standard.get_uuid("tenant", "demo") == KnownUUIDs.STANDARD_TENANT
        assert standard.get_uuid("branch", "main") == KnownUUIDs.STANDARD_BRANCH_MAIN
        assert standard.get_uuid("branch", "north") == KnownUUIDs.STANDARD_BRANCH_NORTH

        # Multi-tenant scenario
        assert multi_tenant.get_uuid("tenant", "alpha") == KnownUUIDs.TENANT_ALPHA
        assert multi_tenant.get_uuid("tenant", "beta") == KnownUUIDs.TENANT_BETA


@pytest.mark.django_db(transaction=True)
class TestSeedCommandExecution:
    """Test seed_data command execution."""

    def test_seed_command_executes_without_error(self):
        """seed_data command runs successfully."""
        out = StringIO()

        call_command("seed_data", "--clear", stdout=out)

        output = out.getvalue()
        assert "Seeding database" in output or "seeded successfully" in output.lower()

    def test_seed_command_is_idempotent(self):
        """Running seed_data twice produces consistent results."""
        out1 = StringIO()
        out2 = StringIO()

        call_command("seed_data", "--clear", stdout=out1)
        call_command("seed_data", stdout=out2)  # Run again without clear

        # Second run should detect existing data
        output2 = out2.getvalue()
        assert "Exists" in output2 or "already exists" in output2.lower()

    def test_seed_command_clear_removes_data(self):
        """--clear flag removes existing data before seeding."""
        out1 = StringIO()
        out2 = StringIO()

        # First run creates data
        call_command("seed_data", "--clear", stdout=out1)

        # Second run with clear should recreate
        call_command("seed_data", "--clear", stdout=out2)

        output2 = out2.getvalue()
        # Should create new data, not find existing
        assert "Created" in output2 or "Creating" in output2


@pytest.mark.django_db(transaction=True)
class TestSeedScenarioValidation:
    """Test scenario data structure validation."""

    def test_minimal_scenario_has_required_structure(self):
        """Minimal scenario has all required fields."""
        scenario = load_scenario("minimal")

        assert scenario.name
        assert scenario.description
        assert scenario.version == "1.0.0"
        assert isinstance(scenario.tenants, list)
        assert isinstance(scenario.users, list)
        assert isinstance(scenario.branches, list)

    def test_entity_configs_have_required_fields(self):
        """Entity configs have entity_type, identifier, and data."""
        scenario = load_scenario("standard")

        for tenant in scenario.tenants:
            assert tenant.entity_type == "tenant"
            assert tenant.identifier
            assert isinstance(tenant.data, dict)

        for user in scenario.users:
            assert user.entity_type == "user"
            assert user.identifier
            assert "email" in user.data or "dependencies" in user.data or user.dependencies

    def test_dependencies_are_properly_formatted(self):
        """Entity dependencies follow entity_type:identifier format."""
        scenario = load_scenario("standard")

        for user in scenario.users:
            for dep in user.dependencies:
                parts = dep.split(":")
                assert len(parts) == 2, f"Invalid dependency format: {dep}"
                assert parts[0] in ["tenant", "role", "branch", "category", "product"]

    def test_scenario_to_dict_roundtrip(self):
        """Scenario can be serialized and deserialized."""
        original = load_scenario("minimal")
        as_dict = original.to_dict()
        restored = SeedScenario.from_dict(as_dict)

        assert restored.name == original.name
        assert restored.description == original.description
        assert len(restored.tenants) == len(original.tenants)
        assert len(restored.users) == len(original.users)
