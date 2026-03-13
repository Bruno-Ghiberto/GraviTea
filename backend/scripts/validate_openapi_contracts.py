#!/usr/bin/env python
"""
OpenAPI Contract Drift Detection Script.

Compares manual API contracts (api/openapi/*.yaml) against auto-generated
schema from drf-spectacular to detect drift and inconsistencies.

Usage:
    python scripts/validate_openapi_contracts.py [--verbose] [--strict]

Exit codes:
    0 - No drift detected
    1 - Drift detected
    2 - Script error
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required. Install with: pip install pyyaml")
    sys.exit(2)


# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MANUAL_CONTRACTS_DIR = PROJECT_ROOT / "api" / "openapi"
AUTO_GENERATED_SPEC = PROJECT_ROOT / "backend" / "openapi-generated.yaml"

# Contract to path prefix mapping
# Manual contracts use relative paths, generated uses /api/v1/ prefix
CONTRACT_MAPPING = {
    "auth-api.yaml": {
        "manual_prefix": "/auth/",  # Manual paths start with /auth/
        "generated_prefix": "/api/v1/auth/",  # Generated paths
    },
    "inventory-api.yaml": {
        "manual_prefix": "/",  # Manual paths at root (e.g., /products/)
        "generated_prefix": "/api/v1/",  # Generated has /api/v1/ prefix
        "exclude_prefixes": ["/api/v1/auth/", "/api/v1/sync/", "/api/v1/schema/", "/api/v1/health/"],
    },
    "sync-api.yaml": {
        "manual_prefix": "/sync/",  # Manual paths start with /sync/
        "generated_prefix": "/api/v1/sync/",  # Generated paths
    },
}


def load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML file and return its contents."""
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"ERROR: File not found: {path}")
        sys.exit(2)
    except yaml.YAMLError as e:
        print(f"ERROR: Invalid YAML in {path}: {e}")
        sys.exit(2)


def extract_endpoints(
    spec: dict[str, Any],
    path_prefix: str = "",
    exclude_prefixes: list[str] | None = None,
) -> dict[str, set[str]]:
    """
    Extract endpoints from an OpenAPI spec.

    Returns dict mapping path -> set of HTTP methods.
    """
    endpoints: dict[str, set[str]] = {}
    paths = spec.get("paths", {})
    exclude_prefixes = exclude_prefixes or []

    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue

        # Normalize path (remove trailing slash for comparison)
        normalized_path = path.rstrip("/")

        # Filter by prefix if provided
        if path_prefix and not normalized_path.startswith(path_prefix.rstrip("/")):
            continue

        # Exclude certain prefixes (for inventory to exclude auth/sync)
        should_exclude = False
        for exclude in exclude_prefixes:
            if normalized_path.startswith(exclude.rstrip("/")):
                should_exclude = True
                break
        if should_exclude:
            continue

        http_methods = set()
        for method in methods:
            if method.lower() in ("get", "post", "put", "patch", "delete", "head", "options"):
                http_methods.add(method.lower())

        if http_methods:
            endpoints[normalized_path] = http_methods

    return endpoints


def normalize_path(path: str, from_prefix: str, to_prefix: str) -> str:
    """Normalize a path by replacing one prefix with another."""
    normalized = path.rstrip("/")
    if normalized.startswith(from_prefix.rstrip("/")):
        return to_prefix.rstrip("/") + normalized[len(from_prefix.rstrip("/")):]
    return normalized


def extract_schemas(spec: dict[str, Any]) -> set[str]:
    """Extract schema names from components/schemas."""
    schemas = spec.get("components", {}).get("schemas", {})
    return set(schemas.keys())


def compare_endpoints(
    manual: dict[str, set[str]],
    generated: dict[str, set[str]],
    contract_name: str,
) -> list[str]:
    """Compare endpoints between manual and generated specs."""
    issues: list[str] = []

    # Check for endpoints in manual but not in generated
    for path, methods in manual.items():
        if path not in generated:
            issues.append(f"[{contract_name}] Endpoint {path} exists in manual but NOT in generated")
        else:
            missing_methods = methods - generated[path]
            if missing_methods:
                issues.append(
                    f"[{contract_name}] {path}: methods {missing_methods} in manual but NOT in generated"
                )

    return issues


def validate_contract(
    manual_path: Path,
    generated_spec: dict[str, Any],
    config: dict[str, Any],
    verbose: bool = False,
) -> list[str]:
    """Validate a single manual contract against the generated spec."""
    issues: list[str] = []
    contract_name = manual_path.name

    manual_prefix = config.get("manual_prefix", "/")
    generated_prefix = config.get("generated_prefix", "/api/v1/")
    exclude_prefixes = config.get("exclude_prefixes", [])

    if verbose:
        print(f"\nValidating {contract_name}...")
        print(f"  Manual prefix: {manual_prefix}")
        print(f"  Generated prefix: {generated_prefix}")

    manual_spec = load_yaml(manual_path)

    # Extract endpoints from manual spec
    manual_endpoints = extract_endpoints(manual_spec)

    # Extract endpoints from generated spec with filtering
    generated_endpoints = extract_endpoints(
        generated_spec,
        path_prefix=generated_prefix,
        exclude_prefixes=exclude_prefixes,
    )

    if verbose:
        print(f"  Manual endpoints: {len(manual_endpoints)}")
        print(f"  Generated endpoints: {len(generated_endpoints)}")

    # Normalize generated paths to match manual path format
    normalized_generated: dict[str, set[str]] = {}
    for gen_path, methods in generated_endpoints.items():
        # Convert generated path to manual path format
        # e.g., /api/v1/auth/token/ -> /auth/token
        norm_path = normalize_path(gen_path, generated_prefix, manual_prefix)
        normalized_generated[norm_path] = methods

    if verbose:
        print(f"  Normalized generated: {len(normalized_generated)}")

    # Compare - check if manual endpoints exist in generated
    for manual_path_str, manual_methods in manual_endpoints.items():
        normalized_manual = manual_path_str.rstrip("/")
        if normalized_manual not in normalized_generated:
            # Try with different normalization
            found = False
            for gen_path in normalized_generated:
                if gen_path.rstrip("/") == normalized_manual or normalized_manual == gen_path.rstrip("/"):
                    found = True
                    # Check methods
                    missing_methods = manual_methods - normalized_generated[gen_path]
                    if missing_methods:
                        issues.append(
                            f"[{contract_name}] {manual_path_str}: methods {missing_methods} in manual but NOT in generated"
                        )
                    break
            if not found:
                issues.append(f"[{contract_name}] Endpoint {manual_path_str} exists in manual but NOT in generated")
        else:
            missing_methods = manual_methods - normalized_generated[normalized_manual]
            if missing_methods:
                issues.append(
                    f"[{contract_name}] {manual_path_str}: methods {missing_methods} in manual but NOT in generated"
                )

    # Check OpenAPI version
    manual_version = manual_spec.get("openapi", "")
    generated_version = generated_spec.get("openapi", "")
    if manual_version != generated_version:
        issues.append(
            f"[{contract_name}] OpenAPI version mismatch: manual={manual_version}, generated={generated_version}"
        )

    return issues


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate OpenAPI contracts for drift detection"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("OpenAPI Contract Drift Detection")
    print("=" * 60)

    # Check if auto-generated spec exists
    if not AUTO_GENERATED_SPEC.exists():
        print(f"\nWARNING: Auto-generated spec not found: {AUTO_GENERATED_SPEC}")
        print("Generate it by running: python manage.py spectacular --file openapi-generated.yaml")
        if args.strict:
            return 1
        return 0

    # Load generated spec
    print(f"\nLoading generated spec: {AUTO_GENERATED_SPEC.name}")
    generated_spec = load_yaml(AUTO_GENERATED_SPEC)

    all_issues: list[str] = []
    validated_contracts = 0

    # Validate each manual contract
    for contract_file, config in CONTRACT_MAPPING.items():
        contract_path = MANUAL_CONTRACTS_DIR / contract_file

        if not contract_path.exists():
            print(f"\nWARNING: Manual contract not found: {contract_path}")
            continue

        issues = validate_contract(
            contract_path,
            generated_spec,
            config,
            verbose=args.verbose,
        )
        all_issues.extend(issues)
        validated_contracts += 1

    # Output results
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)

    if args.json:
        result = {
            "validated_contracts": validated_contracts,
            "issues_found": len(all_issues),
            "issues": all_issues,
            "status": "PASS" if not all_issues else "DRIFT_DETECTED",
        }
        print(json.dumps(result, indent=2))
    else:
        print(f"\nContracts validated: {validated_contracts}")
        print(f"Issues found: {len(all_issues)}")

        if all_issues:
            print("\nDRIFT DETECTED:")
            for issue in all_issues:
                print(f"  - {issue}")
            print("\nAction required: Synchronize manual contracts with backend implementation")
        else:
            print("\n[PASS] All contracts are synchronized - no drift detected")

    return 1 if all_issues else 0


if __name__ == "__main__":
    sys.exit(main())
