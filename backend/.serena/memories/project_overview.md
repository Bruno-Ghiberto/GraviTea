# Gravitea ERP Backend - Project Overview

## Purpose
Gravitea ERP is a multi-tenant Enterprise Resource Planning system built for inventory management, sales, and supplier operations. It targets small-to-medium businesses in Argentina with fiscal compliance (AFIP) integration.

## Tech Stack

### Core Framework
- **Django 5.2** - Web framework
- **Django REST Framework 3.15** - REST API
- **Python 3.x** - Programming language

### Database & Cache
- **PostgreSQL 18** - Primary database (with custom ENUMs)
- **Redis 7** - Caching and Celery broker
- **django-redis** - Redis cache backend

### Authentication & Security
- **djangorestframework-simplejwt** - JWT authentication
- **Argon2** - Password hashing (primary)
- **cryptography** - Field-level encryption for PII
- **Google Secret Manager** - Production secrets management

### Background Processing
- **Celery 5.3** - Async task queue with Redis broker

### Observability
- **OpenTelemetry** - Distributed tracing
- **Prometheus** - Metrics collection
- **Jaeger** - Trace visualization
- **Loki** - Log aggregation
- **python-json-logger** - Structured JSON logging

### API Documentation
- **drf-spectacular** - OpenAPI 3.1 schema generation

### Testing
- **pytest** - Test runner (80% coverage minimum)
- **pytest-django** - Django integration
- **hypothesis** - Property-based testing
- **locust** - Load testing
- **schemathesis** - API fuzzing
- **testcontainers** - Docker integration tests

## Architecture

### Multi-Tenant Design
- **Tenant** - Root entity for customer organizations
- **TenantBoundModel** - Base mixin enforcing tenant isolation
- **TenantBoundManager** - Automatic tenant filtering
- All business data scoped to tenant via FK relationships

### Application Structure
```
apps/
├── auth/       # User authentication, JWT, roles
├── core/       # Shared utilities, encryption, middleware, observability
├── inventario/ # Product catalog, stock movements, price history
└── sync/       # Data synchronization with external systems
```

### Key Patterns
- **Immutable Ledger** - Stock movements are append-only
- **Encrypted Fields** - PII stored with AES-256 + blind indexes
- **Cursor Pagination** - Standard pagination across endpoints
- **RFC 7807 Problem Details** - Standardized error responses

### Middleware Stack
1. SecurityMiddleware
2. TraceMiddleware (trace ID correlation)
3. SessionMiddleware
4. CorsMiddleware
5. TenantContextMiddleware

## Environment
- **Primary Location**: Argentina (es-ar, America/Argentina/Buenos_Aires)
- **Development Platform**: Windows
- **Containerization**: Docker + Docker Compose
