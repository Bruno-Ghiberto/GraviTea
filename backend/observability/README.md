# Observability Configuration

This directory contains configuration files for the GRAVITEA ERP observability stack.

## Structure

```
observability/
├── alerts/                      # Prometheus/Alertmanager alert rules
│   └── slo_alerts.yml
├── dashboards/                  # Grafana dashboard JSON definitions
│   ├── overview.json            # System health overview
│   ├── system-metrics.json      # Detailed system performance
│   ├── business-metrics.json    # Orders, inventory, sync, auth
│   └── slo.json                 # SLO tracking dashboard
├── alertmanager.yml             # Alertmanager routing configuration
├── loki.yml                     # Loki log aggregation configuration
├── prometheus.yml               # Prometheus scrape configuration
├── promtail.yml                 # Promtail log shipping configuration
└── OBSERVABILITY.md             # Detailed documentation
```

**Parent Directory**: `backend/docker-compose.observability.yml` - Full observability stack

## Alert Rules

Alert rules are defined in YAML format compatible with Prometheus Alertmanager.

### SLO-Based Alerts (slo_alerts.yml)
- **HighErrorRate**: Error rate > 1% for 5 minutes (critical)
- **HighLatency**: P99 latency > 500ms for 5 minutes (warning)
- **SyncLagHigh**: Sync processing lag > 60 seconds (warning)
- **ServiceDown**: No requests for 5 minutes (critical)

## Grafana Dashboards

Dashboard JSON files can be imported directly into Grafana or provisioned via Grafana's provisioning system.

### Overview Dashboard (overview.json)
- System health statistics (status, error rate, latency, request rate)
- Request performance graphs
- Sync lag and queue depth monitoring
- Template variables for tenant filtering

### System Metrics Dashboard (system-metrics.json)
- Request performance by endpoint
- Status code breakdown with color coding
- Database query performance
- Process metrics (memory, CPU)

### Business Metrics Dashboard (business-metrics.json)
- Order rate by status and branch
- Inventory movements by operation and product type
- Sync operations and queue depth
- Authentication attempts and failure reasons

### SLO Tracking Dashboard (slo.json)
- Availability SLO gauge (target: 99.9%)
- Latency SLO gauge (target: P99 < 500ms)
- Sync Lag SLO gauge (target: < 60s)
- Error budget tracking
- SLO breach history

## Local Development

Start the observability stack:

```bash
docker-compose -f docker-compose.observability.yml up -d
```

Access:
- Grafana: http://localhost:3000 (admin/admin)
- Prometheus: http://localhost:9090
- Jaeger: http://localhost:16686
- Alertmanager: http://localhost:9093

## Production Deployment

For production, configure:
1. External Prometheus/Alertmanager cluster
2. Persistent storage for metrics
3. Alert routing to PagerDuty/Slack/Email
4. Grafana with LDAP/OAuth authentication
