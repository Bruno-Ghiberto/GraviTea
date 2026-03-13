"""
Unit tests for observability alert rules.

Tests YAML validity and rule structure.
Per 004-observability-metrics spec FR-021 through FR-025.
"""

import os
from pathlib import Path

import pytest
import yaml


@pytest.mark.unit
class TestAlertRuleYAML:
    """Test alert rule YAML files are valid."""

    @pytest.fixture
    def alerts_dir(self):
        """Get the alerts directory path."""
        base_dir = Path(__file__).resolve().parent.parent.parent.parent
        return base_dir / "observability" / "alerts"

    @pytest.fixture
    def slo_alerts_path(self, alerts_dir):
        """Get the SLO alerts file path."""
        return alerts_dir / "slo_alerts.yml"

    def test_slo_alerts_file_exists(self, slo_alerts_path):
        """T048: Test SLO alerts file exists."""
        assert slo_alerts_path.exists(), f"SLO alerts file not found at {slo_alerts_path}"

    def test_slo_alerts_valid_yaml(self, slo_alerts_path):
        """T048: Test SLO alerts file is valid YAML."""
        with open(slo_alerts_path) as f:
            try:
                data = yaml.safe_load(f)
                assert data is not None
            except yaml.YAMLError as e:
                pytest.fail(f"Invalid YAML in SLO alerts: {e}")

    def test_slo_alerts_has_groups(self, slo_alerts_path):
        """T048: Test SLO alerts has groups key."""
        with open(slo_alerts_path) as f:
            data = yaml.safe_load(f)

        assert "groups" in data, "SLO alerts must have 'groups' key"
        assert isinstance(data["groups"], list), "'groups' must be a list"
        assert len(data["groups"]) > 0, "'groups' must not be empty"

    def test_slo_alerts_group_structure(self, slo_alerts_path):
        """T048: Test each alert group has required fields."""
        with open(slo_alerts_path) as f:
            data = yaml.safe_load(f)

        for group in data["groups"]:
            assert "name" in group, "Each group must have a 'name'"
            assert "rules" in group, "Each group must have 'rules'"
            assert isinstance(group["rules"], list), "'rules' must be a list"

    def test_slo_alerts_rule_structure(self, slo_alerts_path):
        """T048: Test each alert rule has required fields."""
        with open(slo_alerts_path) as f:
            data = yaml.safe_load(f)

        for group in data["groups"]:
            for rule in group["rules"]:
                assert "alert" in rule, f"Rule in {group['name']} must have 'alert' name"
                assert "expr" in rule, f"Rule {rule.get('alert', 'unknown')} must have 'expr'"
                assert "labels" in rule, f"Rule {rule['alert']} must have 'labels'"
                assert "annotations" in rule, f"Rule {rule['alert']} must have 'annotations'"

    def test_slo_alerts_have_severity_labels(self, slo_alerts_path):
        """T048: Test all alerts have severity labels."""
        with open(slo_alerts_path) as f:
            data = yaml.safe_load(f)

        valid_severities = {"critical", "warning", "info"}

        for group in data["groups"]:
            for rule in group["rules"]:
                labels = rule.get("labels", {})
                assert "severity" in labels, f"Rule {rule['alert']} must have severity label"
                assert labels["severity"] in valid_severities, \
                    f"Rule {rule['alert']} has invalid severity: {labels['severity']}"

    def test_slo_alerts_have_summary_annotation(self, slo_alerts_path):
        """T048: Test all alerts have summary annotation."""
        with open(slo_alerts_path) as f:
            data = yaml.safe_load(f)

        for group in data["groups"]:
            for rule in group["rules"]:
                annotations = rule.get("annotations", {})
                assert "summary" in annotations, f"Rule {rule['alert']} must have summary annotation"
                assert len(annotations["summary"]) > 0, f"Rule {rule['alert']} summary must not be empty"

    def test_slo_alerts_have_description_annotation(self, slo_alerts_path):
        """T048: Test all alerts have description annotation."""
        with open(slo_alerts_path) as f:
            data = yaml.safe_load(f)

        for group in data["groups"]:
            for rule in group["rules"]:
                annotations = rule.get("annotations", {})
                assert "description" in annotations, \
                    f"Rule {rule['alert']} must have description annotation"

    def test_required_slo_alerts_exist(self, slo_alerts_path):
        """T048: Test required SLO alerts are defined."""
        with open(slo_alerts_path) as f:
            data = yaml.safe_load(f)

        # Collect all alert names
        alert_names = set()
        for group in data["groups"]:
            for rule in group["rules"]:
                alert_names.add(rule["alert"])

        # Required alerts per spec
        required_alerts = {
            "HighErrorRate",
            "HighLatencyP99",
            "SyncQueueLagHigh",
            "HealthCheckFailure",
        }

        for required in required_alerts:
            assert required in alert_names, f"Required alert '{required}' not found"


@pytest.mark.unit
class TestAlertmanagerConfig:
    """Test Alertmanager configuration validity."""

    @pytest.fixture
    def alertmanager_path(self):
        """Get the Alertmanager config path."""
        base_dir = Path(__file__).resolve().parent.parent.parent.parent
        return base_dir / "observability" / "alertmanager.yml"

    def test_alertmanager_config_exists(self, alertmanager_path):
        """T048: Test Alertmanager config exists."""
        assert alertmanager_path.exists(), f"Alertmanager config not found at {alertmanager_path}"

    def test_alertmanager_config_valid_yaml(self, alertmanager_path):
        """T048: Test Alertmanager config is valid YAML."""
        with open(alertmanager_path) as f:
            try:
                data = yaml.safe_load(f)
                assert data is not None
            except yaml.YAMLError as e:
                pytest.fail(f"Invalid YAML in Alertmanager config: {e}")

    def test_alertmanager_has_route(self, alertmanager_path):
        """T048: Test Alertmanager config has route."""
        with open(alertmanager_path) as f:
            data = yaml.safe_load(f)

        assert "route" in data, "Alertmanager config must have 'route'"
        assert "receiver" in data["route"], "Route must have default 'receiver'"

    def test_alertmanager_has_receivers(self, alertmanager_path):
        """T048: Test Alertmanager config has receivers."""
        with open(alertmanager_path) as f:
            data = yaml.safe_load(f)

        assert "receivers" in data, "Alertmanager config must have 'receivers'"
        assert len(data["receivers"]) > 0, "Must have at least one receiver"

        # Each receiver must have a name
        for receiver in data["receivers"]:
            assert "name" in receiver, "Each receiver must have a 'name'"

    def test_alertmanager_receiver_referenced_exists(self, alertmanager_path):
        """T048: Test all referenced receivers exist."""
        with open(alertmanager_path) as f:
            data = yaml.safe_load(f)

        # Collect all receiver names
        receiver_names = {r["name"] for r in data["receivers"]}

        # Check default receiver
        default_receiver = data["route"]["receiver"]
        assert default_receiver in receiver_names, \
            f"Default receiver '{default_receiver}' not defined"

        # Check route receivers
        def check_routes(routes):
            if not routes:
                return
            for route in routes:
                if "receiver" in route:
                    assert route["receiver"] in receiver_names, \
                        f"Receiver '{route['receiver']}' not defined"
                if "routes" in route:
                    check_routes(route["routes"])

        check_routes(data["route"].get("routes", []))
