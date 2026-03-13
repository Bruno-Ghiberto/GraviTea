"""
Seed data utilities for deterministic data generation.

Provides utilities for generating reproducible seed data across environments:
- UUID5 deterministic generation from namespace and name
- SeedScenario dataclass for scenario configuration
- Entity builders for consistent data creation

Per spec.md FR-025 through FR-028 requirements:
- T060: Implement SeedScenario dataclass
- T061: Implement UUID5 deterministic generator
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any


# Namespace UUID for GRAVITEA seed data
# This is a fixed UUID that serves as the base for all deterministic UUIDs
GRAVITEA_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


def deterministic_uuid(entity_type: str, identifier: str) -> uuid.UUID:
    """Generate a deterministic UUID5 from entity type and identifier.

    The same inputs will always produce the same UUID, making seed data
    reproducible across different environments and runs.

    Args:
        entity_type: Type of entity (e.g., "tenant", "product", "user")
        identifier: Unique identifier within the entity type (e.g., "demo", "SKU-001")

    Returns:
        A deterministic UUID5 based on the inputs

    Example:
        >>> deterministic_uuid("tenant", "demo")
        UUID('...')  # Always the same for these inputs
        >>> deterministic_uuid("product", "SKU-001")
        UUID('...')  # Different but also deterministic
    """
    # Combine entity type and identifier into a unique name
    name = f"{entity_type}:{identifier}"
    return uuid.uuid5(GRAVITEA_NAMESPACE, name)


def deterministic_uuid_from_parts(*parts: str) -> uuid.UUID:
    """Generate a deterministic UUID5 from multiple name parts.

    Useful for composite identifiers like branch-product combinations.

    Args:
        *parts: Variable number of string parts to combine

    Returns:
        A deterministic UUID5

    Example:
        >>> deterministic_uuid_from_parts("stock", "branch-1", "product-1")
        UUID('...')
    """
    name = ":".join(parts)
    return uuid.uuid5(GRAVITEA_NAMESPACE, name)


@dataclass
class EntityConfig:
    """Configuration for a single entity in a seed scenario."""

    entity_type: str
    identifier: str
    data: dict[str, Any]
    dependencies: list[str] = field(default_factory=list)

    @property
    def uuid(self) -> uuid.UUID:
        """Get the deterministic UUID for this entity."""
        return deterministic_uuid(self.entity_type, self.identifier)


@dataclass
class SeedScenario:
    """Configuration for a seed data scenario.

    A scenario defines a complete set of seed data including:
    - Tenants and their configuration
    - Users and roles
    - Branches
    - Products and categories
    - Initial stock levels

    Scenarios are loaded from JSON files and produce deterministic UUIDs
    for all entities, ensuring reproducibility across environments.

    Attributes:
        name: Scenario identifier (e.g., "minimal", "standard", "multi_tenant")
        description: Human-readable description
        version: Schema version for compatibility checking
        tenants: List of tenant configurations
        users: List of user configurations
        branches: List of branch configurations
        categories: List of category configurations
        products: List of product configurations
        suppliers: List of supplier configurations
        stock_levels: List of initial stock configurations
    """

    name: str
    description: str
    version: str = "1.0.0"
    tenants: list[EntityConfig] = field(default_factory=list)
    users: list[EntityConfig] = field(default_factory=list)
    roles: list[EntityConfig] = field(default_factory=list)
    branches: list[EntityConfig] = field(default_factory=list)
    categories: list[EntityConfig] = field(default_factory=list)
    products: list[EntityConfig] = field(default_factory=list)
    suppliers: list[EntityConfig] = field(default_factory=list)
    price_lists: list[EntityConfig] = field(default_factory=list)
    stock_levels: list[EntityConfig] = field(default_factory=list)

    @classmethod
    def from_json_file(cls, path: str | Path) -> SeedScenario:
        """Load a seed scenario from a JSON file.

        Args:
            path: Path to the JSON scenario file

        Returns:
            SeedScenario instance populated from the file

        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the JSON is invalid or missing required fields
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Scenario file not found: {path}")

        with path.open() as f:
            data = json.load(f)

        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SeedScenario:
        """Create a SeedScenario from a dictionary.

        Args:
            data: Dictionary with scenario configuration

        Returns:
            SeedScenario instance
        """
        scenario = cls(
            name=data.get("name", "unnamed"),
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
        )

        # Parse entity configurations
        entity_types = [
            "tenants",
            "users",
            "roles",
            "branches",
            "categories",
            "products",
            "suppliers",
            "price_lists",
            "stock_levels",
        ]

        for entity_type in entity_types:
            entities = data.get(entity_type, [])
            entity_configs = []
            for entity in entities:
                config = EntityConfig(
                    entity_type=entity_type.rstrip("s"),  # Remove plural
                    identifier=entity.get("id", entity.get("identifier", "")),
                    data=entity.get("data", entity),
                    dependencies=entity.get("dependencies", []),
                )
                entity_configs.append(config)
            setattr(scenario, entity_type, entity_configs)

        return scenario

    def get_uuid(self, entity_type: str, identifier: str) -> uuid.UUID:
        """Get a deterministic UUID for an entity in this scenario.

        Args:
            entity_type: Type of entity
            identifier: Entity identifier

        Returns:
            Deterministic UUID
        """
        # Prefix with scenario name for scenario-specific UUIDs
        return deterministic_uuid(entity_type, f"{self.name}:{identifier}")

    def to_dict(self) -> dict[str, Any]:
        """Convert scenario to a dictionary.

        Returns:
            Dictionary representation of the scenario
        """
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "tenants": [
                {"identifier": e.identifier, "data": e.data, "dependencies": e.dependencies}
                for e in self.tenants
            ],
            "users": [
                {"identifier": e.identifier, "data": e.data, "dependencies": e.dependencies}
                for e in self.users
            ],
            "roles": [
                {"identifier": e.identifier, "data": e.data, "dependencies": e.dependencies}
                for e in self.roles
            ],
            "branches": [
                {"identifier": e.identifier, "data": e.data, "dependencies": e.dependencies}
                for e in self.branches
            ],
            "categories": [
                {"identifier": e.identifier, "data": e.data, "dependencies": e.dependencies}
                for e in self.categories
            ],
            "products": [
                {"identifier": e.identifier, "data": e.data, "dependencies": e.dependencies}
                for e in self.products
            ],
            "suppliers": [
                {"identifier": e.identifier, "data": e.data, "dependencies": e.dependencies}
                for e in self.suppliers
            ],
            "price_lists": [
                {"identifier": e.identifier, "data": e.data, "dependencies": e.dependencies}
                for e in self.price_lists
            ],
            "stock_levels": [
                {"identifier": e.identifier, "data": e.data, "dependencies": e.dependencies}
                for e in self.stock_levels
            ],
        }


def get_scenario_path(scenario_name: str) -> Path:
    """Get the path to a scenario JSON file.

    Args:
        scenario_name: Name of the scenario (e.g., "minimal", "standard")

    Returns:
        Path to the scenario file

    Raises:
        FileNotFoundError: If the scenario file doesn't exist
    """
    # Look in the fixtures directory
    base_path = Path(__file__).parent.parent.parent.parent.parent  # backend/
    scenarios_dir = base_path / "tests" / "fixtures" / "seed_scenarios"
    scenario_path = scenarios_dir / f"{scenario_name}.json"

    if not scenario_path.exists():
        raise FileNotFoundError(
            f"Scenario '{scenario_name}' not found at {scenario_path}"
        )

    return scenario_path


def load_scenario(scenario_name: str) -> SeedScenario:
    """Load a seed scenario by name.

    Args:
        scenario_name: Name of the scenario (e.g., "minimal", "standard")

    Returns:
        Loaded SeedScenario instance

    Raises:
        FileNotFoundError: If the scenario doesn't exist
    """
    path = get_scenario_path(scenario_name)
    return SeedScenario.from_json_file(path)


def list_available_scenarios() -> list[str]:
    """List all available seed scenarios.

    Returns:
        List of scenario names
    """
    base_path = Path(__file__).parent.parent.parent.parent.parent  # backend/
    scenarios_dir = base_path / "tests" / "fixtures" / "seed_scenarios"

    if not scenarios_dir.exists():
        return []

    return [f.stem for f in scenarios_dir.glob("*.json")]


# Pre-computed deterministic UUIDs for common test entities
# These provide stable references for tests
class KnownUUIDs:
    """Pre-computed deterministic UUIDs for common test scenarios.

    These UUIDs are stable across all environments and test runs,
    enabling reliable integration testing and cross-environment validation.
    """

    # Minimal scenario
    MINIMAL_TENANT = deterministic_uuid("tenant", "minimal:demo")
    MINIMAL_BRANCH = deterministic_uuid("branch", "minimal:main")
    MINIMAL_ADMIN = deterministic_uuid("user", "minimal:admin")
    MINIMAL_ROLE = deterministic_uuid("role", "minimal:admin")

    # Standard scenario
    STANDARD_TENANT = deterministic_uuid("tenant", "standard:demo")
    STANDARD_BRANCH_MAIN = deterministic_uuid("branch", "standard:main")
    STANDARD_BRANCH_NORTH = deterministic_uuid("branch", "standard:north")
    STANDARD_ADMIN = deterministic_uuid("user", "standard:admin")
    STANDARD_MANAGER = deterministic_uuid("user", "standard:manager")
    STANDARD_CASHIER = deterministic_uuid("user", "standard:cashier")

    # Multi-tenant scenario
    TENANT_ALPHA = deterministic_uuid("tenant", "multi_tenant:alpha")
    TENANT_BETA = deterministic_uuid("tenant", "multi_tenant:beta")
    ALPHA_BRANCH = deterministic_uuid("branch", "multi_tenant:alpha-main")
    BETA_BRANCH = deterministic_uuid("branch", "multi_tenant:beta-main")
    ALPHA_ADMIN = deterministic_uuid("user", "multi_tenant:alpha-admin")
    BETA_ADMIN = deterministic_uuid("user", "multi_tenant:beta-admin")

    # Product UUIDs for testing
    PRODUCT_001 = deterministic_uuid("product", "standard:SKU-001")
    PRODUCT_002 = deterministic_uuid("product", "standard:SKU-002")
    PRODUCT_003 = deterministic_uuid("product", "standard:SKU-003")

    # Category UUIDs
    CATEGORY_BEVERAGES = deterministic_uuid("category", "standard:beverages")
    CATEGORY_FOOD = deterministic_uuid("category", "standard:food")
    CATEGORY_CLEANING = deterministic_uuid("category", "standard:cleaning")


def decimal_str(value: str) -> Decimal:
    """Convert string to Decimal for JSON serialization compatibility.

    Args:
        value: Decimal value as string

    Returns:
        Decimal instance
    """
    return Decimal(value)
