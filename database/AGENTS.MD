# GRAVITEA Database - AI Agent Ruleset

> **Skills Reference**: For detailed patterns, use these skills:
> - [`gravitea-tenant`](../skills/gravitea-tenant/SKILL.md) - RLS policies, tenant isolation
> - [`django-expert`](../skills/django-expert/SKILL.md) - Django ORM integration
> - [`gravitea-encryption`](../skills/gravitea-encryption/SKILL.md) - Encrypted fields, blind indexes

### Auto-invoke Skills

When performing these actions, ALWAYS invoke the corresponding skill FIRST:

| Action | Skill |
|--------|-------|
| Adding RLS policies | `gravitea-tenant` |
| Creating new tables | Review existing schema patterns |
| Adding triggers/functions | Follow naming conventions |
| Working with encrypted fields | `gravitea-encryption` |
| Modifying seed data | Review existing test scenarios |

---

## CRITICAL RULES - NON-NEGOTIABLE

### SQL File Ordering

- ALWAYS: Use numeric prefix for execution order: `000_`, `001_`, etc.
- ALWAYS: Include header comment with purpose and dependencies
- ALWAYS: Include `-- Requires: <previous_file>` dependency note
- NEVER: Create SQL files without proper ordering prefix
- NEVER: Skip sequence numbers (no 000, 002, 003)

### Primary Keys

- ALWAYS: UUID as primary key: `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`
- ALWAYS: Use `pgcrypto` extension for `gen_random_uuid()`
- NEVER: Auto-increment integers for business entities
- NEVER: Sequential UUIDs (use random UUIDs)

### Tenant Isolation

- ALWAYS: Add `tenant_id UUID NOT NULL REFERENCES tenant(id)` to tenant-bound tables
- ALWAYS: Enable RLS: `ALTER TABLE <table> ENABLE ROW LEVEL SECURITY;`
- ALWAYS: Force RLS: `ALTER TABLE <table> FORCE ROW LEVEL SECURITY;`
- ALWAYS: Create isolation policy using `get_current_tenant_id()`
- NEVER: Tables with tenant data without RLS policies

### Monetary Values

- ALWAYS: `NUMERIC(17,3)` for prices/costs (aligned with Django MoneyField)
- ALWAYS: `NUMERIC(16,2)` for totals and balances
- NEVER: `FLOAT` or `DOUBLE` for financial data
- NEVER: Integer cents (use DECIMAL precision)

### Session Variables

- ALWAYS: Set `app.current_tenant_id` before tenant queries
- ALWAYS: Set `app.current_user_id` for audit context
- ALWAYS: Use `current_setting('app.variable', true)` for safe retrieval
- NEVER: Trust session variables without application-level validation

---

## DECISION TREES

### New Table Creation

```
Creating new table?
|-- Contains tenant-specific data?
|   |-- Yes -> Add tenant_id FK, create RLS policy
|   +-- No -> System table (rare, needs justification)
|
|-- Has monetary values?
|   |-- Price/Cost -> NUMERIC(17,3)
|   +-- Total/Balance -> NUMERIC(16,2)
|
|-- Has encrypted fields?
|   |-- Yes -> Add _encrypted suffix + _hash column for search
|   +-- No -> Plain text with appropriate constraints
```

### RLS Policy Type

```
Table has direct tenant_id?
|-- Yes -> Simple policy: tenant_id = get_current_tenant_id()
+-- No -> Nested policy via parent relationship
    |-- Example: stock_snapshot via branch.tenant_id
    |-- Example: sale_item via sale.tenant_id
```

### Trigger Function

```
Need database-level automation?
|-- Immutable record (ledger)?
|   +-- Create prevention trigger for UPDATE/DELETE
|
|-- Derived value update?
|   +-- Create AFTER INSERT trigger (stock_snapshot)
|
|-- Audit required?
|   +-- Apply audit_trigger_function()
```

---

## TECH STACK

| Component | Version |
|-----------|---------|
| PostgreSQL | 18.1 |
| Extension: pgcrypto | Built-in |
| Connection Pooling | PgBouncer (optional) |

---

## PROJECT STRUCTURE

```
database/
├── SQL/
│   ├── 000_init_database.sql    # Database, roles, extensions
│   ├── 001_schema.sql           # ENUM types and tables
│   ├── 002_rls_policies.sql     # Row Level Security policies
│   ├── 003_stock_functions.sql  # Stock triggers/functions
│   └── 004_audit_functions.sql  # Audit trail triggers/functions
├── seeds/
│   ├── test_data.sql            # Test fixtures
│   ├── test_scenarios.sql       # Scenario-based test data
│   └── SeedData.md              # Seed data documentation
├── Database Docs/
│   └── Database_schemas.md      # Schema documentation
└── AGENTS.MD                    # This file
```

---

## SQL FILE EXECUTION ORDER

```bash
# Execute in strict order (dependencies enforced)
psql -U postgres -f 000_init_database.sql
psql -U postgres -d gravitea -f 001_schema.sql
psql -U postgres -d gravitea -f 002_rls_policies.sql
psql -U postgres -d gravitea -f 003_stock_functions.sql
psql -U postgres -d gravitea -f 004_audit_functions.sql

# Optional: Load test data
psql -U postgres -d gravitea -f seeds/test_data.sql
```

---

## DATABASE ROLES

| Role | Purpose | RLS Behavior |
|------|---------|--------------|
| `gravitea_admin` | Migrations, admin tasks | BYPASSRLS |
| `gravitea_app` | Application operations | Subject to RLS |
| `gravitea_user` | Django connection user | Inherits `gravitea_app` |

---

## SESSION VARIABLES

Set these via Django middleware before database operations:

| Variable | Type | Purpose |
|----------|------|---------|
| `app.current_tenant_id` | UUID | RLS tenant filtering |
| `app.current_user_id` | UUID | Audit: who made change |
| `app.current_user_email` | TEXT | Audit: user identifier |
| `app.client_ip` | INET | Audit: request origin |
| `app.user_agent` | TEXT | Audit: client info |

**Usage in SQL:**
```sql
SET app.current_tenant_id = 'uuid-here';
SELECT * FROM product;  -- Only returns tenant's products
```

---

## RLS POLICY PATTERNS

### Pattern 1: Direct Tenant Column

```sql
-- Table has tenant_id column
ALTER TABLE product ENABLE ROW LEVEL SECURITY;
ALTER TABLE product FORCE ROW LEVEL SECURITY;

CREATE POLICY product_tenant_isolation ON product
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());
```

### Pattern 2: Nested via Parent

```sql
-- Table has FK to tenant-bound table (no direct tenant_id)
CREATE POLICY stock_snapshot_tenant_isolation ON stock_snapshot
    USING (
        branch_id IN (
            SELECT id FROM branch WHERE tenant_id = get_current_tenant_id()
        )
    )
    WITH CHECK (
        branch_id IN (
            SELECT id FROM branch WHERE tenant_id = get_current_tenant_id()
        )
    );
```

---

## TRIGGER PATTERNS

### Pattern 1: Immutable Ledger

```sql
-- Prevent UPDATE/DELETE on ledger tables
CREATE OR REPLACE FUNCTION prevent_stock_movement_modification()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        RAISE EXCEPTION 'Stock movements are immutable. Create adjustment instead.'
            USING ERRCODE = 'integrity_constraint_violation';
    ELSIF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Stock movements cannot be deleted. Create reversal instead.'
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;
```

### Pattern 2: Automatic Snapshot Update

```sql
-- Update derived table on INSERT
CREATE OR REPLACE FUNCTION update_stock_snapshot_on_movement()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO stock_snapshot (...)
    VALUES (...)
    ON CONFLICT (branch_id, product_id)
    DO UPDATE SET quantity = stock_snapshot.quantity + EXCLUDED.quantity;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

### Pattern 3: Audit Trail

```sql
-- Generic audit for all sensitive tables
CREATE TRIGGER trg_audit_product
    AFTER INSERT OR UPDATE OR DELETE ON product
    FOR EACH ROW
    EXECUTE FUNCTION audit_trigger_function();
```

---

## ENUM TYPES

Define all ENUMs in `001_schema.sql`:

| ENUM | Values | Used By |
|------|--------|---------|
| `payment_method_enum` | CASH, CREDIT_CARD, DEBIT_CARD, TRANSFER, QR, ACCOUNT | payment |
| `stock_movement_type_enum` | SALE, PURCHASE, ADJ, TRANS_IN, TRANS_OUT | stock_movement |
| `sale_type_enum` | FACTURA_A, FACTURA_B, TICKET, NC | sale |
| `sale_status_enum` | DRAFT, PENDING_AFIP, FISCALIZED, CANCELLED | sale |
| `sync_status_enum` | PENDING, IN_PROGRESS, COMPLETED, FAILED, CONFLICT | sync_session |
| `operation_type_enum` | CREATE, UPDATE, DELETE | pending_operation |

---

## ENCRYPTED FIELD CONVENTIONS

For PII fields (customer tax_id, email, phone, address):

```sql
-- Encrypted value column
tax_id_encrypted        TEXT,
-- Blind index for search (HMAC-SHA256)
tax_id_hash             CHAR(64),

-- Index for efficient lookups
CREATE INDEX idx_customer_tenant_taxid_hash
    ON customer (tenant_id, tax_id_hash);
```

---

## COMMANDS

```bash
# Connect to database
psql -U gravitea_user -d gravitea

# Verify RLS is enabled
SELECT tablename, rowsecurity, forcerowsecurity
FROM pg_tables t
JOIN pg_class c ON c.relname = t.tablename
WHERE schemaname = 'public';

# Test tenant isolation
SET app.current_tenant_id = 'tenant-uuid-here';
SELECT COUNT(*) FROM product;  -- Should only show tenant's products

# View audit log
SELECT * FROM get_audit_history(
    'tenant-uuid',
    'product',
    NULL,
    NOW() - INTERVAL '1 day',
    NOW(),
    50
);

# Backup database
pg_dump -U postgres gravitea > backup.sql

# Restore database
psql -U postgres -d gravitea < backup.sql
```

---

## NAMING CONVENTIONS

| Entity | Pattern | Example |
|--------|---------|---------|
| Table | `snake_case` | `stock_movement` |
| Column | `snake_case` | `tenant_id` |
| ENUM type | `<entity>_<field>_enum` | `sale_status_enum` |
| Index | `idx_<table>_<columns>` | `idx_product_barcode_blind` |
| Constraint | `uq_<table>_<columns>` | `uq_product_tenant_sku` |
| Policy | `<table>_tenant_isolation` | `product_tenant_isolation` |
| Trigger | `trg_<action>_<table>` | `trg_audit_product` |
| Function | `verb_noun_context()` | `get_current_tenant_id()` |

---

## QA CHECKLIST

Before committing database changes:

- [ ] SQL file has proper numeric prefix (000-004+)
- [ ] Header comment includes purpose and dependencies
- [ ] New tables have UUID primary key
- [ ] Tenant-bound tables have RLS policy
- [ ] RLS uses `get_current_tenant_id()` function
- [ ] Monetary columns use NUMERIC(17,3) or NUMERIC(16,2)
- [ ] ENUMs defined before tables using them
- [ ] Triggers use `SECURITY DEFINER` where needed
- [ ] Permissions granted to `gravitea_app` role
- [ ] Audit triggers applied to sensitive tables
- [ ] Encrypted fields have blind index columns
- [ ] Django migrations align with SQL schema

---

## RELATED DOCUMENTS

- **Data Model**: See `Docs/Project Blueprint/Data Model & Domain Model.md`
- **Django Models**: See `backend/apps/core/models/` for ORM implementation
- **Schema Docs**: See `Database Docs/Database_schemas.md`
- **Seed Data Guide**: See `seeds/SeedData.md`

---

*Last updated: 2026-01-20*
*PostgreSQL 18.1 | pgcrypto extension | RLS enabled*
