# Research: Infrastructure Verification Checklist

**Feature**: 013-e2e-frontend-testing
**Date**: 2026-02-18
**Purpose**: Phase 0 infrastructure verification. Unlike standard research (resolving unknowns), this documents pre-test infrastructure readiness.

## Verification Items

### 1. Core Docker Stack

| Check | Command | Expected | Status |
|-------|---------|----------|--------|
| PostgreSQL healthy | `docker compose ps gravitea-postgres` | healthy | PENDING |
| Redis healthy | `docker compose ps gravitea-redis` | healthy | PENDING |
| Backend healthy | `docker compose ps gravitea-web` | healthy, port 8000 | PENDING |
| Frontend healthy | `docker compose ps gravitea-frontend` | healthy, port 3000 | PENDING |
| Health endpoint | `curl http://localhost:8000/api/v1/health/` | `{"status":"healthy"}` | PENDING |

### 2. Seed Data

| Check | Command | Expected | Status |
|-------|---------|----------|--------|
| seed_all runs | `docker compose exec web python manage.py seed_all` | No errors | PENDING |
| Users count | Check via API | 4-5 users (admin, vendedor, gerente, deposito) | PENDING |
| Products count | Check via API | ~10 products with categories | PENDING |
| Movements count | Check via API | ~26 movements | PENDING |
| Customers count | Check via API | ~3 customers | PENDING |
| Orders count | Check via API | ~3 orders (DRAFT/CONFIRMED/INVOICED) | PENDING |
| Comprobantes count | Check via API | ~5 comprobantes | PENDING |
| ARCA credential | Check via API | 1 credential | PENDING |
| Puntos de venta | Check via API | 3 PtoVta | PENDING |
| CAEA | Check via API | 1 CAEA | PENDING |

### 3. Observability Stack

| Check | Command | Expected | Status |
|-------|---------|----------|--------|
| Prometheus | `curl http://localhost:9090/-/ready` | ready | PENDING |
| Grafana | `curl http://localhost:3002/api/health` | ok | PENDING |
| Jaeger UI | `curl http://localhost:16686/` | loads | PENDING |
| Loki | `curl http://localhost:3100/ready` | ready | PENDING |
| Alertmanager | `curl http://localhost:9093/-/ready` | ready | PENDING |
| Prometheus scrapes web | Check Prometheus targets | `gravitea-web` target UP | PENDING |
| OTEL traces flowing | Check Jaeger for recent traces | traces visible | PENDING |

### 4. Frontend Accessibility

| Check | Method | Expected | Status |
|-------|--------|----------|--------|
| Login page loads | Browser to `http://localhost:3000` | Login form renders | PENDING |
| No console errors | Browser DevTools | 0 errors on login page | PENDING |
| Sidebar renders after login | Login as admin | 6 module links visible | PENDING |

### 5. Playwright MCP

| Check | Method | Expected | Status |
|-------|--------|----------|--------|
| Navigate to URL | `browser_navigate` to localhost:3000 | Page loads | PENDING |
| Take screenshot | `browser_take_screenshot` | Screenshot captured | PENDING |
| Click element | `browser_click` on login button | Element responds | PENDING |
| Fill form | `browser_fill` on email input | Value entered | PENDING |

### 6. Redis Connectivity

| Check | Command | Expected | Status |
|-------|---------|----------|--------|
| Ping | `redis-cli -h localhost ping` | PONG | PENDING |
| Keys accessible | `redis-cli keys '*'` | List of keys (may be empty) | PENDING |
| Connection count | `redis-cli info clients` | `connected_clients` > 0 | PENDING |

### 7. Network Connectivity

| Check | Command | Expected | Status |
|-------|---------|----------|--------|
| gravitea-shared network | `docker network ls \| grep gravitea-shared` | exists | PENDING |
| Observability → core | Prometheus targets page | web target reachable | PENDING |

### 8. WSL + tmux (Agent Execution Environment)

| Check | Command | Expected | Status |
|-------|---------|----------|--------|
| WSL installed | `wsl --status` (from PowerShell) | WSL version 2 running | PENDING |
| tmux available | `tmux -V` (inside WSL) | tmux 3.x+ | PENDING |
| Repo accessible from WSL | `ls /mnt/c/Users/Ghibe/Documents/Gravitea/GRAVITEA-ERP` | Files listed | PENDING |
| Docker accessible from WSL | `docker ps` (inside WSL) | Containers listed | PENDING |

### 9. Test Runner Script

| Check | Command | Expected | Status |
|-------|---------|----------|--------|
| Script exists | `ls scripts/run-tests-external.sh` | File found | PENDING |
| Script executable | `bash scripts/run-tests-external.sh --help` or similar | Usage info or no error | PENDING |
| Output directory exists | `ls Docs/Tests/` | Directory exists (create if needed) | PENDING |
| WSL venv available | `ls backend/venv-wsl/bin/python` (inside WSL) | Python binary found | PENDING |

## Decisions

| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| Use Playwright MCP for all browser interactions | Built-in MCP tool, no external dependencies | Chrome DevTools MCP (also available but Playwright is more standardized for E2E) |
| Test in single-tenant mode only | seed_all creates 1 tenant; multi-tenant E2E requires separate seed scripts | Multi-tenant testing (deferred — out of scope per spec clarification) |
| ARCA scenarios marked as "may skip" | No real ARCA homologacion certificates available | Skip ARCA entirely (rejected — we still test error handling) |
| test-scenarios.md as canonical source | Derived from actual OpenAPI specs + frontend tabs | TEST-ERP-WORKFLOW.md (rejected — was from previous manual test, not aligned with current API state) |
| WSL + tmux for agent team | Windows native Claude Code + tmux panes for parallel agent sessions | Git Bash only (no tmux support), PowerShell (no POSIX tools) |
| run-tests-external.sh for all pytest | Avoids token consumption from verbose pytest output inside Claude Code instances | Direct pytest (rejected — floods context with 1000s of lines) |

## Issues & Resolutions

*To be filled during Phase 0 execution. Each issue gets: Problem → Root Cause → Resolution → Verified.*
