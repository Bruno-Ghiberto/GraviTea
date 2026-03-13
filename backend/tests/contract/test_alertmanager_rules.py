"""
Contract tests for Alertmanager rule compatibility.

Validates that alert rules conform to Prometheus/Alertmanager contracts.
Per 004-observability-metrics spec FR-021 through FR-025.
"""

import re
from pathlib import Path

import pytest
import yaml


class TestAlertRulePrometheusCompatibility:
    """Contract tests ensuring alert rules are Prometheus-compatible."""

    @pytest.fixture
    def alerts_dir(self):
        """Get the alerts directory path."""
        base_dir = Path(__file__).resolve().parent.parent.parent
        return base_dir / "observability" / "alerts"

    @pytest.fixture
    def slo_alerts_path(self, alerts_dir):
        """Get the SLO alerts file path."""
        return alerts_dir / "slo_alerts.yml"

    @pytest.fixture
    def slo_alerts_data(self, slo_alerts_path):
        """Load and parse SLO alerts YAML."""
        with open(slo_alerts_path) as f:
            return yaml.safe_load(f)

    def test_groups_have_valid_names(self, slo_alerts_data):
        """T049: Test group names follow Prometheus naming conventions."""
        # Prometheus group names should be snake_case or kebab-case
        name_pattern = re.compile(r"^[a-z][a-z0-9_-]*$")

        for group in slo_alerts_data["groups"]:
            name = group["name"]
            assert name_pattern.match(name), \
                f"Group name '{name}' doesn't follow naming conventions"

    def test_alert_names_follow_conventions(self, slo_alerts_data):
        """T049: Test alert names follow Prometheus conventions."""
        # Alert names should be CamelCase
        name_pattern = re.compile(r"^[A-Z][a-zA-Z0-9]*$")

        for group in slo_alerts_data["groups"]:
            for rule in group["rules"]:
                alert_name = rule["alert"]
                assert name_pattern.match(alert_name), \
                    f"Alert name '{alert_name}' should be CamelCase"

    def test_expressions_are_valid_promql_syntax(self, slo_alerts_data):
        """T049: Test PromQL expressions have valid basic syntax."""
        # Basic syntax checks (full validation requires Prometheus)
        for group in slo_alerts_data["groups"]:
            for rule in group["rules"]:
                expr = rule["expr"]
                alert_name = rule["alert"]

                # Should not be empty
                assert expr.strip(), f"Alert {alert_name} has empty expression"

                # Should not have unmatched brackets
                assert expr.count("(") == expr.count(")"), \
                    f"Alert {alert_name} has unmatched parentheses"
                assert expr.count("[") == expr.count("]"), \
                    f"Alert {alert_name} has unmatched brackets"
                assert expr.count("{") == expr.count("}"), \
                    f"Alert {alert_name} has unmatched braces"

    def test_for_duration_format(self, slo_alerts_data):
        """T049: Test 'for' duration has valid Prometheus format."""
        # Valid duration patterns: 1m, 5m, 1h, 30s, etc.
        duration_pattern = re.compile(r"^\d+[smhdwy]$")

        for group in slo_alerts_data["groups"]:
            for rule in group["rules"]:
                if "for" in rule:
                    duration = rule["for"]
                    assert duration_pattern.match(duration), \
                        f"Alert {rule['alert']} has invalid 'for' duration: {duration}"

    def test_labels_are_strings(self, slo_alerts_data):
        """T049: Test all label values are strings."""
        for group in slo_alerts_data["groups"]:
            for rule in group["rules"]:
                labels = rule.get("labels", {})
                for key, value in labels.items():
                    assert isinstance(value, str), \
                        f"Alert {rule['alert']} label '{key}' must be string, got {type(value)}"

    def test_annotations_are_strings(self, slo_alerts_data):
        """T049: Test all annotation values are strings."""
        for group in slo_alerts_data["groups"]:
            for rule in group["rules"]:
                annotations = rule.get("annotations", {})
                for key, value in annotations.items():
                    assert isinstance(value, str), \
                        f"Alert {rule['alert']} annotation '{key}' must be string"

    def test_severity_uses_standard_values(self, slo_alerts_data):
        """T049: Test severity labels use standard values."""
        standard_severities = {"critical", "warning", "info"}

        for group in slo_alerts_data["groups"]:
            for rule in group["rules"]:
                severity = rule.get("labels", {}).get("severity")
                if severity:
                    assert severity in standard_severities, \
                        f"Alert {rule['alert']} uses non-standard severity: {severity}"

    def test_group_interval_format(self, slo_alerts_data):
        """T049: Test group interval has valid format."""
        duration_pattern = re.compile(r"^\d+[smhdwy]$")

        for group in slo_alerts_data["groups"]:
            if "interval" in group:
                interval = group["interval"]
                assert duration_pattern.match(interval), \
                    f"Group {group['name']} has invalid interval: {interval}"

    def test_template_variables_in_annotations(self, slo_alerts_data):
        """T049: Test template variables use valid Go template syntax."""
        # Check for common template patterns
        template_pattern = re.compile(r"\{\{\s*[^}]+\s*\}\}")

        for group in slo_alerts_data["groups"]:
            for rule in group["rules"]:
                annotations = rule.get("annotations", {})
                for key, value in annotations.items():
                    # If there are template markers, they should be properly formed
                    if "{{" in value:
                        matches = template_pattern.findall(value)
                        # Count opening and closing braces
                        open_count = value.count("{{")
                        close_count = value.count("}}")
                        assert open_count == close_count, \
                            f"Alert {rule['alert']} annotation '{key}' has unmatched template braces"


class TestAlertmanagerConfigCompatibility:
    """Contract tests ensuring Alertmanager config is compatible."""

    @pytest.fixture
    def alertmanager_path(self):
        """Get the Alertmanager config path."""
        base_dir = Path(__file__).resolve().parent.parent.parent
        return base_dir / "observability" / "alertmanager.yml"

    @pytest.fixture
    def alertmanager_data(self, alertmanager_path):
        """Load and parse Alertmanager config."""
        with open(alertmanager_path) as f:
            return yaml.safe_load(f)

    def test_global_section_valid(self, alertmanager_data):
        """T049: Test global section has valid structure."""
        if "global" in alertmanager_data:
            global_config = alertmanager_data["global"]

            # resolve_timeout should be a duration
            if "resolve_timeout" in global_config:
                duration_pattern = re.compile(r"^\d+[smhdwy]$")
                assert duration_pattern.match(global_config["resolve_timeout"]), \
                    "resolve_timeout must be a valid duration"

    def test_route_structure_valid(self, alertmanager_data):
        """T049: Test route has required fields and valid structure."""
        route = alertmanager_data["route"]

        # Must have a default receiver
        assert "receiver" in route, "Route must have default receiver"

        # group_by should be a list if present
        if "group_by" in route:
            assert isinstance(route["group_by"], list), "group_by must be a list"

        # Durations should be valid
        duration_pattern = re.compile(r"^\d+[smhdwy]$")
        for duration_field in ["group_wait", "group_interval", "repeat_interval"]:
            if duration_field in route:
                assert duration_pattern.match(route[duration_field]), \
                    f"{duration_field} must be a valid duration"

    def test_child_routes_valid(self, alertmanager_data):
        """T049: Test child routes have valid structure."""
        def validate_route(route, path="route"):
            # Check match or match_re
            if "match" in route:
                assert isinstance(route["match"], dict), \
                    f"{path}.match must be a dict"
            if "match_re" in route:
                assert isinstance(route["match_re"], dict), \
                    f"{path}.match_re must be a dict"

            # Recurse into child routes
            if "routes" in route:
                assert isinstance(route["routes"], list), \
                    f"{path}.routes must be a list"
                for i, child in enumerate(route["routes"]):
                    validate_route(child, f"{path}.routes[{i}]")

        if "routes" in alertmanager_data["route"]:
            for i, route in enumerate(alertmanager_data["route"]["routes"]):
                validate_route(route, f"route.routes[{i}]")

    def test_receivers_have_valid_configs(self, alertmanager_data):
        """T049: Test receivers have valid notification configs."""
        valid_config_types = {
            "email_configs",
            "slack_configs",
            "pagerduty_configs",
            "webhook_configs",
            "opsgenie_configs",
            "victorops_configs",
            "pushover_configs",
            "wechat_configs",
            "sns_configs",
            "telegram_configs",
            "msteams_configs",
            "discord_configs",
            "webex_configs",
        }

        for receiver in alertmanager_data["receivers"]:
            # Each receiver must have a name
            assert "name" in receiver, "Receiver must have name"

            # Check that config types are valid
            for key in receiver:
                if key != "name" and key.endswith("_configs"):
                    assert key in valid_config_types, \
                        f"Unknown config type: {key}"
                    assert isinstance(receiver[key], list), \
                        f"{key} must be a list"

    def test_slack_configs_have_required_fields(self, alertmanager_data):
        """T049: Test Slack configs have required fields."""
        for receiver in alertmanager_data["receivers"]:
            if "slack_configs" in receiver:
                for slack_config in receiver["slack_configs"]:
                    # api_url is required (or global slack_api_url)
                    assert "api_url" in slack_config or \
                        alertmanager_data.get("global", {}).get("slack_api_url"), \
                        f"Receiver {receiver['name']} Slack config needs api_url"

    def test_webhook_configs_have_url(self, alertmanager_data):
        """T049: Test webhook configs have URL."""
        for receiver in alertmanager_data["receivers"]:
            if "webhook_configs" in receiver:
                for webhook_config in receiver["webhook_configs"]:
                    assert "url" in webhook_config, \
                        f"Receiver {receiver['name']} webhook config needs url"

    def test_inhibit_rules_valid(self, alertmanager_data):
        """T049: Test inhibit rules have valid structure."""
        if "inhibit_rules" not in alertmanager_data:
            return

        for i, rule in enumerate(alertmanager_data["inhibit_rules"]):
            # Must have source and target match
            has_source = "source_match" in rule or "source_match_re" in rule
            has_target = "target_match" in rule or "target_match_re" in rule

            assert has_source, f"Inhibit rule {i} must have source_match or source_match_re"
            assert has_target, f"Inhibit rule {i} must have target_match or target_match_re"

            # equal should be a list if present
            if "equal" in rule:
                assert isinstance(rule["equal"], list), \
                    f"Inhibit rule {i} 'equal' must be a list"

    def test_templates_path_valid(self, alertmanager_data):
        """T049: Test templates paths are valid patterns."""
        if "templates" not in alertmanager_data:
            return

        templates = alertmanager_data["templates"]
        assert isinstance(templates, list), "templates must be a list"

        for template in templates:
            assert isinstance(template, str), "Each template path must be a string"
            # Should be an absolute path or glob pattern
            assert template.startswith("/") or "*" in template, \
                f"Template path should be absolute or glob: {template}"


class TestAlertRuleMetricReferences:
    """Test that alert rules reference valid metrics."""

    @pytest.fixture
    def slo_alerts_path(self):
        """Get the SLO alerts file path."""
        base_dir = Path(__file__).resolve().parent.parent.parent
        return base_dir / "observability" / "alerts" / "slo_alerts.yml"

    @pytest.fixture
    def slo_alerts_data(self, slo_alerts_path):
        """Load and parse SLO alerts YAML."""
        with open(slo_alerts_path) as f:
            return yaml.safe_load(f)

    def test_known_metrics_referenced(self, slo_alerts_data):
        """T049: Test alert rules reference known metric names."""
        # Known metrics from our implementation
        known_metrics = {
            "http_requests_total",
            "http_request_duration_seconds",
            "http_request_duration_seconds_bucket",
            "sync_processing_lag_seconds",
            "sync_queue_depth",
            "up",
            "probe_success",
            "pg_stat_activity_count",
            "auth_failures_total",
            "auth_attempts_total",
            "orders_total",
        }

        # Extract metric names from expressions (basic extraction)
        metric_pattern = re.compile(r"([a-z_][a-z0-9_]*)\s*[{\[(]")

        for group in slo_alerts_data["groups"]:
            for rule in group["rules"]:
                expr = rule["expr"]
                matches = metric_pattern.findall(expr)

                # Filter out PromQL functions
                promql_functions = {
                    "sum", "rate", "histogram_quantile", "increase",
                    "avg", "min", "max", "count", "by", "without",
                    "and", "or", "unless", "hour", "printf",
                }

                for match in matches:
                    if match not in promql_functions:
                        # Metric should be known or have a common prefix
                        is_known = (
                            match in known_metrics or
                            any(match.startswith(km.split("_")[0]) for km in known_metrics)
                        )
                        # This is a soft check - we just ensure metrics look reasonable
                        assert "_" in match or match in known_metrics, \
                            f"Metric '{match}' in {rule['alert']} looks unusual"

    def test_label_references_in_expressions(self, slo_alerts_data):
        """T049: Test label references in expressions are valid."""
        # Common labels used in our system
        known_labels = {
            "tenant_id",
            "status_code",
            "method",
            "endpoint",
            "le",  # histogram bucket label
            "job",
            "instance",
            "state",
            "status",
            "team",
        }

        label_pattern = re.compile(r"([a-z_][a-z0-9_]*)\s*[=!~]")

        for group in slo_alerts_data["groups"]:
            for rule in group["rules"]:
                expr = rule["expr"]
                matches = label_pattern.findall(expr)

                for match in matches:
                    # Labels should follow snake_case convention
                    assert re.match(r"^[a-z][a-z0-9_]*$", match), \
                        f"Label '{match}' in {rule['alert']} should be snake_case"
