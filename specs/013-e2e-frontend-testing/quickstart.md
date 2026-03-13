# Quickstart: E2E Acceptance Testing

**Feature**: 013-e2e-frontend-testing
**Date**: 2026-02-18

## Prerequisites

- Docker Desktop running (Windows)
- WSL (Windows Subsystem for Linux) installed with tmux
- Claude Code CLI with `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`
- Playwright MCP configured in `.claude.json`
- Chrome DevTools MCP configured (optional, for advanced debugging)
- `scripts/run-tests-external.sh` accessible (for pytest execution)

## Step 1: Start Infrastructure

```bash
# From repo root: C:/Users/Ghibe/Documents/Gravitea/GRAVITEA-ERP

# 1. Start core stack (postgres, redis, backend, frontend)
docker compose up -d

# 2. Wait for all containers to be healthy (~30-60s)
docker compose ps

# 3. Seed test data
docker compose exec web python manage.py seed_all

# 4. Start observability stack
docker compose -f backend/docker-compose.observability.yml up -d

# 5. Verify health
curl http://localhost:8000/api/v1/health/
```

## Step 2: Verify Access Points

| Service | URL | Expected |
|---------|-----|----------|
| Frontend | http://localhost:3000 | Login page |
| Backend API | http://localhost:8000/api/v1/health/ | `{"status":"healthy"}` |
| Prometheus | http://localhost:9090 | Targets page |
| Grafana | http://localhost:3002 | Dashboard |
| Jaeger | http://localhost:16686 | Search page |

## Step 3: Login Credentials

| User | Email | Password | Role |
|------|-------|----------|------|
| Admin | admin@gravitea-demo.com | admin123 | Administrador |
| Vendedor | vendedor@gravitea-demo.com | vendedor123 | Vendedor |
| Gerente | gerente@gravitea-demo.com | gerente123 | Gerente |
| Deposito | deposito@gravitea-demo.com | deposito123 | Deposito |

## Step 4: Launch Multi-Agent Team (WSL + tmux)

The 9-agent team runs in **WSL with tmux** for multi-pane session management. Each agent gets its own tmux pane.

```bash
# From WSL terminal:

# 1. Start a tmux session
tmux new-session -s gravitea-e2e

# 2. Launch the test execution via speckit
/speckit.implement Read Docs/Temp-prompting/instruction-implement.md for orchestration context
```

This will launch the 9-agent team as defined in the plan. Agent Teams (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`) uses filesystem-based coordination (JSON mailboxes) across tmux panes.

## Step 5: Test Runner for Pytest (Token Efficiency)

Any agent that needs to run backend pytest tests **MUST** use the external test runner to avoid consuming tokens with verbose output:

```bash
# CORRECT — delegated execution, token-efficient
bash scripts/run-tests-external.sh "pytest backend/tests/auth/ --tb=short -q"

# After execution, read ONLY the summary:
# Docs/Tests/<name>.summary  (~20 lines)
# Docs/Tests/<name>.status   (1-line: PASS/FAIL)

# For debugging failures, grep the log — NEVER read it in full:
# grep "FAIL\|Error" Docs/Tests/<name>.log
```

**NEVER** run `pytest` directly inside a Claude Code instance.

## Step 6: Human-in-the-Loop

During execution, ORCHESTRATOR will pause for your input at:

1. **Phase gates**: Approve proceeding to next phase
2. **Bug fix approvals**: Review ERROR-HANDLER reports and approve/reject CODER fixes
3. **CRITICAL issues**: Immediate attention required
4. **ARCA module entry**: Confirm whether to attempt ARCA-dependent scenarios
5. **Test completion**: Accept final report or request additional tests

## Key Documents

| Document | Path | Purpose |
|----------|------|---------|
| Test Scenarios | `specs/013-e2e-frontend-testing/test-scenarios.md` | 80 scenarios — TESTER follows these |
| Spec | `specs/013-e2e-frontend-testing/spec.md` | 33 FRs — requirements reference |
| Plan | `specs/013-e2e-frontend-testing/plan.md` | Phase structure + agent assignments |
| Report Output | `Docs/Tests/REPORT-13.md` | TECHNICAL-REPORT writes here continuously |
| OpenAPI Specs | `api/openapi/*.yaml` | BACKEND-EXPERT references these |
| Test Runner | `scripts/run-tests-external.sh` | MANDATORY for all pytest execution |

## Navigation Rules

Due to JWT stored in React Context (memory only):
- **NEVER** navigate by typing URLs directly — this clears the auth token
- **ALWAYS** navigate via sidebar link clicks after login
- Only `/login` can be navigated to directly
- If the page goes blank or redirects to login unexpectedly, the JWT was lost — re-login

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Frontend shows blank page | JWT cleared | Re-login at /login |
| `seed_all` creates duplicates | Previous uncleared seed data | Run `seed_all --clear` first |
| Observability can't reach backend | Network not shared | Verify `gravitea-shared` Docker network |
| Playwright can't navigate | MCP not configured | Check `.claude.json` for Playwright MCP entry |
| ARCA authorize fails | No real certificates | Expected behavior — document the error |
| Pytest output floods context | Agent ran pytest directly | Always use `scripts/run-tests-external.sh` |
| Test runner output not found | Wrong working directory | Run from repo root; outputs go to `Docs/Tests/` |
