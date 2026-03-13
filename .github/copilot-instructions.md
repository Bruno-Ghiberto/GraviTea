# GRAVITEA-ERP AI Agent Skills

> **Single Source of Truth** - This file is the master for all AI assistants.
> Skills provide on-demand context and patterns for working with this codebase.
> Run `./skills/setup.sh` to configure your AI assistant.

## Project Overview

**GRAVITEA-ERP** is a multi-tenant Enterprise Resource Planning system designed for small-to-medium businesses with offline-first capabilities. The system enforces strict tenant isolation using a defense-in-depth strategy combining application-level managers, PostgreSQL Row Level Security (RLS), and IDOR validation.

### Core Capabilities

- **Multi-Tenant Architecture**: Complete data isolation per tenant with RLS enforcement
- **JWT Authentication**: RS256-signed tokens with custom claims for tenant context
- **Offline-First Sync**: Device session management with conflict resolution
- **Field-Level Encryption**: AES-256-GCM for PII with blind index search
- **Observability**: Prometheus metrics with sanitized labels, OpenTelemetry tracing

## Technology Stack

| Layer | Technology | Version |
|-------|------------|---------|
| Language | Python | 3.14.3 |
| Framework | Django + DRF | 5.2.x |
| Database | PostgreSQL | 18.1 |
| Cache | Redis | 7.x |
| Auth | djangorestframework-simplejwt | Latest |
| Password | Argon2 (argon2-cffi) | Latest |
| Encryption | cryptography (AES-256-GCM) | Latest |
| Testing | pytest + pytest-django | Latest |
| Metrics | prometheus-client | Latest |

## Available Skills

### Repository-Specific Skills

| Skill | Description | Trigger |
|-------|-------------|---------|
| [`gravitea-auth`](skills/gravitea-auth/SKILL.md) | JWT authentication, rate limiting, token lifecycle, vulnerability mitigation | Editing `apps/auth/`, login/logout, token refresh |
| [`gravitea-tenant`](skills/gravitea-tenant/SKILL.md) | Multi-tenant isolation, RLS, TenantBoundManager, IDOR prevention | Editing tenant models, cross-tenant queries |
| `gravitea-inventory` | Product, StockMovement, immutable ledger patterns | Editing `apps/inventario/` |
| `gravitea-sync` | Offline-first sync, conflict resolution, device sessions | Editing `apps/sync/` |
| `gravitea-observability` | Prometheus metrics, tracing, label sanitization | Editing `apps/core/observability/` |
| `gravitea-encryption` | AES-256-GCM, encrypted fields, blind index search | Working with PII, encrypted fields |
| [`gravitea-testing`](skills/gravitea-testing/SKILL.md) | Pytest patterns, fixtures, markers, cache isolation | Writing tests |
| `gravitea-docker` | Docker Compose, health checks, graceful shutdown | Editing Docker configs |
| [`gravitea-invoice`](skills/gravitea-invoice/SKILL.md) | ARCA electronic invoicing, WSAA auth, WSFEv1, CAE lifecycle, fiscal QR | Editing `apps/facturacion/`, ARCA integration |

### Framework Skills

| Skill | Description | Trigger |
|-------|-------------|---------|
| [`django-expert`](skills/django-expert/SKILL.md) | Django 5.2 enterprise patterns, ORM optimization, ASGI, security hardening | Creating models, views, migrations, queries |

### Workflow Skills

| Skill | Description | Trigger |
|-------|-------------|---------|
| [`skill-creator`](skills/skill-creator/SKILL.md) | Creates new AI agent skills following Gravitea spec | Creating new skills, documenting patterns for AI |

### Marketplace Skills (agentskills.io)

Skills installed from the [Agent Skills marketplace](https://agentskills.io). Source: `.agents/skills/`.

| Skill | Description | Trigger |
|-------|-------------|---------|
| [`vercel-react-best-practices`](.agents/skills/vercel-react-best-practices/SKILL.md) | React and Next.js performance optimization (45 rules across 8 categories) from Vercel Engineering | Writing React/Next.js components, data fetching, bundle optimization, performance improvements |

## Auto-Invoke Rules

When performing these actions, **ALWAYS** invoke the corresponding skill FIRST:

| File Pattern | Action | Invoke Skill | Why |
|--------------|--------|--------------|-----|
| `apps/auth/**` | Any edit | `gravitea-auth` | JWT security, rate limiting patterns |
| `**/views.py` + auth | Token endpoint | `gravitea-auth` | Algorithm whitelist, claim validation |
| `apps/core/models/**` | New model | `gravitea-tenant` | TenantBoundModel inheritance |
| `**/models.py` + FK | Foreign key to tenant model | `gravitea-tenant` | IDOR prevention validation |
| `apps/facturacion/**` | Any edit | `gravitea-invoice` | ARCA invoicing, CAE, fiscal QR |
| `**/views.py` + invoice/factura | Invoice endpoint | `gravitea-invoice` | WSFEv1 patterns, amount validation |
| `**/arca/**` or `**/wsfe/**` | ARCA integration | `gravitea-invoice` | WSAA auth, certificate management |
| `apps/inventario/**` | Any edit | `gravitea-inventory` | Immutable ledger, stock calculations |
| `apps/sync/**` | Any edit | `gravitea-sync` | Conflict resolution patterns |
| `apps/core/observability/**` | Metrics/tracing | `gravitea-observability` | Label sanitization rules |
| `**/encryption/**` | PII handling | `gravitea-encryption` | Encryption field patterns |
| `tests/**` | Writing tests | `gravitea-testing` | Fixtures, markers, test IDs |
| `docker-compose*.yml` | Docker config | `gravitea-docker` | Health checks, shutdown |
| `**/models.py` | Creating/editing models | `django-expert` | ORM patterns, constraints, migrations |
| `**/views.py` | Creating/editing views | `django-expert` | CBV patterns, query optimization |
| `gravitea/settings/**` | Settings config | `django-expert` | Security hardening, ASGI/WSGI |
| `skills/**/SKILL.md` | Creating new skill | `skill-creator` | Skill structure, naming, registration |
| `frontend/**/*.{tsx,jsx}` | React/Next.js code | `vercel-react-best-practices` | Performance optimization patterns |
| `frontend/**/page.{tsx,jsx}` | Next.js pages | `vercel-react-best-practices` | Waterfall elimination, Suspense |

## How Skills Work

1. **Auto-detection**: AI agents read AGENTS.md for skill triggers
2. **Context matching**: When editing relevant files, skills load automatically
3. **Pattern application**: AI follows exact patterns from the skill
4. **First-time-correct**: No trial and error - skills provide exact conventions

## Directory Structure

```text
GRAVITEA-ERP/
|-- AGENTS.md                    # This file - Single Source of Truth
|-- skills/                      # SOURCE 1: Custom skills (git-tracked)
|   |-- setup.sh                 # Two-source merge script
|   |-- setup_test.sh            # Unit tests for setup.sh
|   |-- django-expert/
|   |   +-- SKILL.md             # Django 5.2 enterprise patterns
|   |-- gravitea-auth/
|   |   +-- SKILL.md             # JWT authentication patterns
|   |-- gravitea-tenant/
|   |   +-- SKILL.md             # Multi-tenant isolation
|   |-- gravitea-testing/
|   |   +-- SKILL.md             # Pytest patterns and fixtures
|   |-- gravitea-invoice/
|   |   +-- SKILL.md             # ARCA electronic invoicing patterns
|   +-- ... (other skills)
|-- .agents/skills/              # SOURCE 2: Marketplace skills (agentskills.io)
|   +-- vercel-react-best-practices/
|       |-- SKILL.md             # Frontmatter + summary
|       |-- AGENTS.md            # Full compiled instructions
|       +-- rules/               # Individual rule files
|-- .claude/skills/              # OUTPUT: Generated by setup.sh (do not edit)
|-- .codex/skills/               # OUTPUT: Generated by setup.sh (do not edit)
|-- .gemini/skills/              # OUTPUT: Generated by setup.sh (do not edit)
|-- backend/
|   |-- gravitea/
|   |   +-- settings/            # Django settings (base, dev, test, prod)
|   |-- apps/
|   |   |-- core/                # Shared infrastructure
|   |   |   |-- models/          # Tenant, Branch, base models
|   |   |   |-- encryption/      # AES-256-GCM utilities
|   |   |   |-- observability/   # Prometheus metrics, tracing
|   |   |   +-- rate_limiter.py  # Rate limiting implementation
|   |   |-- auth/                # Authentication (gravitea_auth)
|   |   |   |-- views.py         # Token endpoints
|   |   |   |-- jwt.py           # Custom token serializer
|   |   |   +-- permissions.py   # Custom permissions
|   |   |-- inventario/          # Inventory management
|   |   |-- facturacion/         # ARCA electronic invoicing
|   |   |   |-- arca/            # WSAA + WSFEv1 clients
|   |   |   |-- constants.py     # CbteTipo, DocTipo, CondicionIVA
|   |   |   |-- validators.py    # Amount validation
|   |   |   +-- qr.py            # Fiscal QR code generation
|   |   +-- sync/                # Offline-first sync
|   |-- tests/                   # Pytest test suite
|   |   |-- auth/                # Auth-specific tests
|   |   |-- security/            # Security tests (OWASP, tenant isolation)
|   |   +-- conftest.py          # Root fixtures
|   +-- database/sql/            # RLS policies, functions
+-- claudedocs/                  # AI-generated documentation
```

## Security Philosophy

We adopt **Defense in Depth** for all security-critical operations:

```text
Layer 1: Application (Managers, Middleware)
    |
    v
Layer 2: Database (PostgreSQL RLS)
    |
    v
Layer 3: Validation (IDOR checks, claim validation)
```

### Critical Security Rules

1. **Never trust the client** - Validate all inputs server-side
2. **Never trust the JWT header** - Enforce algorithm whitelist
3. **Never log secrets** - Only log `jti` or `sub`, never full tokens
4. **Always validate claims** - Check `iss`, `aud`, `exp` on every request
5. **Always isolate tenants** - Use TenantBoundManager for all queries

## GGA Integration (Gentleman Guardian Angel)

This project uses **GGA** for automated AI code review via git pre-commit hooks.

### Configuration

| File | Purpose |
|------|---------|
| `.gga` | Provider config (Claude Opus 4.5, file patterns) |
| `AGENTS.md` | Coding standards and rules for AI review |

### GGA Commands

```bash
# Initialize GGA in project (already done)
gga init

# Install git pre-commit hook
gga install

# Run manual review on staged files
gga run

# Check current configuration
gga config

# Clear review cache
gga cache clear

# Uninstall hook
gga uninstall
```

### Review Focus Areas

GGA enforces these critical patterns on every commit:

1. **Security** - JWT algorithm whitelist, input validation, no secrets in logs
2. **Tenant Isolation** - TenantBoundModel inheritance, IDOR prevention
3. **Immutability** - StockMovement and authorized Comprobantes append-only, no UPDATE/DELETE
4. **Type Hints** - All function parameters and returns typed
5. **Testing** - New code must have corresponding tests

### Windows Usage

Run GGA from Git Bash (not PowerShell/CMD):

```bash
# Git Bash terminal
cd /c/Users/Ghibe/Documents/Gravitea/GRAVITEA-ERP
gga run
```

---

## Contributing Skills

### Adding a Custom Skill

1. Create skill directory: `skills/{skill-name}/`
2. Add `SKILL.md` following the template below
3. Register in this file under "Available Skills"
4. Add auto-invoke rule if applicable
5. Run `./skills/setup.sh --all` to propagate to all agent directories

### Adding a Marketplace Skill

1. Install from [agentskills.io](https://agentskills.io) (installs to `.agents/skills/`)
2. Register in this file under "Marketplace Skills"
3. Run `./skills/setup.sh --all` to propagate to all agent directories
4. Commit `.agents/skills/{skill-name}/` to git for team sharing

### SKILL.md Template

```markdown
---
name: gravitea-{component}
description: >
  {Description of the skill}.
  Trigger: {When the AI should load this skill}.
license: MIT
metadata:
  author: gravitea-team
  version: "1.0"
---

## When to Use

- Condition 1
- Condition 2

## Critical Patterns

### Pattern 1: Name
{Code example with explanation}

## Decision Tree

\```text
Question?
|-- Option A? -> Action A
|-- Option B? -> Action B
+-- Default -> Action C
\```

## Code Examples

### Example 1: Description
\```python
# Code here
\```

## Commands

\```bash
# Relevant commands
\```

## Resources

- **File**: See `path/to/file.py` for implementation
```

## Quick Reference

### Common Commands

```bash
# Run all tests
cd backend && pytest

# Run auth tests only
cd backend && pytest tests/auth/ -v

# Run security tests
cd backend && pytest -m "security" -v

# Run with coverage
cd backend && pytest --cov=apps --cov-report=term-missing

# Start development server
cd backend && python manage.py runserver

# Apply migrations
cd backend && python manage.py migrate
```

### Test Markers

| Marker | Description |
|--------|-------------|
| `@pytest.mark.unit` | Fast tests, no external deps |
| `@pytest.mark.integration` | Requires database |
| `@pytest.mark.security` | Security-focused tests |
| `@pytest.mark.auth` | Authentication tests |
| `@pytest.mark.tenant` | Tenant isolation tests |
| `@pytest.mark.slow` | Long-running tests |
| `@pytest.mark.docker` | Requires Docker |

---

*Last updated: 2026-02-07*
*Maintained by: GRAVITEA Team*
