# Architecture Gaps Analysis - 2025-11-28

## Critical Missing Modules (P0 Blockers)

### Fiscal Module (apps/fiscal/)
- AFIP/ARCA integration for electronic invoicing
- WSAA authentication service
- WSFE CAE generation service
- Legal requirement for Argentine operations
- Estimated effort: 3-4 weeks

### Sales/POS Module (apps/sales/)
- Sale transactions, line items, payments
- Cash register operations
- Integration with inventory (stock deduction)
- Integration with fiscal (CAE generation)
- Estimated effort: 2-3 weeks

### Customer Module (apps/customers/)
- Customer CRUD with encrypted PII
- Account ledger (immutable)
- Credit limit enforcement
- Estimated effort: 1-2 weeks

## Infrastructure Gaps (P1 High Priority)

### Async Task Queue (Celery)
- Background CAE requests to AFIP
- Offline sync processing
- Stock recalculations
- Estimated effort: 1 week

### Redis Caching
- Tenant configuration caching
- Stock level caching
- AFIP token caching
- Target: 80% cache hit rate
- Estimated effort: 3-5 days

### Database Connection Pooling (pgBouncer)
- Support 1000 client connections
- Pool 25 DB connections per tenant
- Estimated effort: 2-3 days

## Quality Gaps (P0 Blockers)

### Test Coverage
- Current: 72.23% (target: 80%)
- Critical gaps:
  - sync/conflict_resolver.py: 0%
  - stock_service.py: 34%
  - secrets.py: 0%
- Estimated effort: 1-2 weeks

### Performance Issues
- 3 failing performance tests
- N+1 query in product list (105 queries → target: 6)
- Barcode field naming error
- Missing database indexes
- Estimated effort: 3-5 days

## Production Readiness Timeline

### Phase 1 (Weeks 1-3): Stabilization
- Fix performance tests
- Achieve 80% test coverage
- Optimize database queries
- Expand seed data

### Phase 2 (Weeks 4-7): Fiscal Compliance
- AFIP WSAA/WSFE integration
- CAE generation
- Contingency mode

### Phase 3 (Weeks 8-10): Revenue Features
- Sales/POS module
- Payment processing
- Sales-Inventory-Fiscal integration

### Phase 4 (Weeks 11-12): Performance
- Celery + Redis setup
- Async task migration
- Caching implementation

### Phase 5 (Weeks 13-14): CRM
- Customer module
- Account ledger

**Total Time to Production**: 10-12 weeks (2.5-3 months)

## Risk Factors

### High Risk (P0)
- AFIP integration complexity (mitigate: start early, hire expert)
- Test coverage gaps (mitigate: dedicated testing sprint)
- Performance under load (mitigate: early load testing)

### Medium Risk (P1)
- Celery/Redis setup complexity
- Customer PII encryption issues
