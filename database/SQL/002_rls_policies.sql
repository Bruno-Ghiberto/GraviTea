-- ============================================================
-- Row Level Security (RLS) Policies for Gravitea ERP
-- PostgreSQL 18.1 Required
-- ============================================================
-- Purpose: Defense-in-depth tenant isolation at database level
-- All tenant-bound tables get RLS policies ensuring data isolation
-- even if application-level checks fail.
-- Execute: psql -U postgres -d gravitea -f 002_rls_policies.sql
-- Requires: 000_init_database.sql + Django migrations executed first
-- IDEMPOTENT: Safe to run multiple times without errors.
-- ============================================================

-- Enable RLS on tenant-bound tables
-- Note: Tables must exist (created by Django migrations)

-- ============================================================
-- Helper Function: Get current tenant from session variable
-- ============================================================

CREATE OR REPLACE FUNCTION get_current_tenant_id()
RETURNS UUID AS $$
BEGIN
    RETURN NULLIF(current_setting('app.current_tenant_id', true), '')::UUID;
EXCEPTION
    WHEN OTHERS THEN
        RETURN NULL;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

COMMENT ON FUNCTION get_current_tenant_id() IS
'Returns the current tenant ID from session variable.
Set via: SET app.current_tenant_id = ''uuid-here'';
Used by RLS policies for tenant isolation.';

-- ============================================================
-- Role Table RLS
-- ============================================================

ALTER TABLE role ENABLE ROW LEVEL SECURITY;
ALTER TABLE role FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS role_tenant_isolation ON role;
CREATE POLICY role_tenant_isolation ON role
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

COMMENT ON POLICY role_tenant_isolation ON role IS
'Ensures roles are only visible/modifiable within their tenant context.';

-- ============================================================
-- AppUser Table RLS
-- ============================================================

ALTER TABLE app_user ENABLE ROW LEVEL SECURITY;
ALTER TABLE app_user FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS app_user_tenant_isolation ON app_user;
CREATE POLICY app_user_tenant_isolation ON app_user
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

COMMENT ON POLICY app_user_tenant_isolation ON app_user IS
'Ensures users are only visible/modifiable within their tenant context.';

-- ============================================================
-- Branch Table RLS
-- ============================================================

ALTER TABLE branch ENABLE ROW LEVEL SECURITY;
ALTER TABLE branch FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS branch_tenant_isolation ON branch;
CREATE POLICY branch_tenant_isolation ON branch
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

COMMENT ON POLICY branch_tenant_isolation ON branch IS
'Ensures branches are only visible/modifiable within their tenant context.';

-- ============================================================
-- Product Table RLS
-- ============================================================

ALTER TABLE product ENABLE ROW LEVEL SECURITY;
ALTER TABLE product FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS product_tenant_isolation ON product;
CREATE POLICY product_tenant_isolation ON product
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

COMMENT ON POLICY product_tenant_isolation ON product IS
'Ensures products are only visible/modifiable within their tenant context.';

-- ============================================================
-- Stock Movement Table RLS
-- ============================================================

ALTER TABLE stock_movement ENABLE ROW LEVEL SECURITY;
ALTER TABLE stock_movement FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS stock_movement_tenant_isolation ON stock_movement;
CREATE POLICY stock_movement_tenant_isolation ON stock_movement
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

COMMENT ON POLICY stock_movement_tenant_isolation ON stock_movement IS
'Ensures stock movements are only visible/modifiable within their tenant context.';

-- ============================================================
-- Stock Snapshot Table RLS (maps to TABLAS.sql stock_snapshot)
-- Note: stock_snapshot doesn't have tenant_id, uses branch.tenant_id
-- ============================================================

ALTER TABLE stock_snapshot ENABLE ROW LEVEL SECURITY;
ALTER TABLE stock_snapshot FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS stock_snapshot_tenant_isolation ON stock_snapshot;
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

COMMENT ON POLICY stock_snapshot_tenant_isolation ON stock_snapshot IS
'Ensures stock snapshots are only visible/modifiable within their tenant context via branch relationship.';

-- ============================================================
-- Sync Session Table RLS
-- ============================================================

ALTER TABLE sync_session ENABLE ROW LEVEL SECURITY;
ALTER TABLE sync_session FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS sync_session_tenant_isolation ON sync_session;
CREATE POLICY sync_session_tenant_isolation ON sync_session
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

COMMENT ON POLICY sync_session_tenant_isolation ON sync_session IS
'Ensures sync sessions are only visible/modifiable within their tenant context.';

-- ============================================================
-- Pending Operation Table RLS
-- ============================================================

ALTER TABLE pending_operation ENABLE ROW LEVEL SECURITY;
ALTER TABLE pending_operation FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS pending_operation_tenant_isolation ON pending_operation;
CREATE POLICY pending_operation_tenant_isolation ON pending_operation
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

COMMENT ON POLICY pending_operation_tenant_isolation ON pending_operation IS
'Ensures pending operations are only visible/modifiable within their tenant context.';

-- ============================================================
-- Product Category Table RLS
-- ============================================================

ALTER TABLE product_category ENABLE ROW LEVEL SECURITY;
ALTER TABLE product_category FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS product_category_tenant_isolation ON product_category;
CREATE POLICY product_category_tenant_isolation ON product_category
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

COMMENT ON POLICY product_category_tenant_isolation ON product_category IS
'Ensures product categories are only visible/modifiable within their tenant context.';

-- ============================================================
-- Price List Table RLS
-- ============================================================

ALTER TABLE price_list ENABLE ROW LEVEL SECURITY;
ALTER TABLE price_list FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS price_list_tenant_isolation ON price_list;
CREATE POLICY price_list_tenant_isolation ON price_list
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

COMMENT ON POLICY price_list_tenant_isolation ON price_list IS
'Ensures price lists are only visible/modifiable within their tenant context.';

-- ============================================================
-- Supplier Table RLS
-- ============================================================

ALTER TABLE supplier ENABLE ROW LEVEL SECURITY;
ALTER TABLE supplier FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS supplier_tenant_isolation ON supplier;
CREATE POLICY supplier_tenant_isolation ON supplier
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

COMMENT ON POLICY supplier_tenant_isolation ON supplier IS
'Ensures suppliers are only visible/modifiable within their tenant context.';

-- ============================================================
-- Customer Table RLS
-- ============================================================

ALTER TABLE customer ENABLE ROW LEVEL SECURITY;
ALTER TABLE customer FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS customer_tenant_isolation ON customer;
CREATE POLICY customer_tenant_isolation ON customer
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

COMMENT ON POLICY customer_tenant_isolation ON customer IS
'Ensures customers are only visible/modifiable within their tenant context.';

-- ============================================================
-- Customer Account Ledger Table RLS
-- Note: Uses customer_id -> customer.tenant_id for isolation
-- ============================================================

ALTER TABLE customer_account_ledger ENABLE ROW LEVEL SECURITY;
ALTER TABLE customer_account_ledger FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS customer_account_ledger_tenant_isolation ON customer_account_ledger;
CREATE POLICY customer_account_ledger_tenant_isolation ON customer_account_ledger
    USING (
        customer_id IN (
            SELECT id FROM customer WHERE tenant_id = get_current_tenant_id()
        )
    )
    WITH CHECK (
        customer_id IN (
            SELECT id FROM customer WHERE tenant_id = get_current_tenant_id()
        )
    );

COMMENT ON POLICY customer_account_ledger_tenant_isolation ON customer_account_ledger IS
'Ensures customer ledger entries are only visible/modifiable within their tenant context via customer relationship.';

-- ============================================================
-- Supplier Account Ledger Table RLS
-- Note: Uses supplier_id -> supplier.tenant_id for isolation
-- ============================================================

ALTER TABLE supplier_account_ledger ENABLE ROW LEVEL SECURITY;
ALTER TABLE supplier_account_ledger FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS supplier_account_ledger_tenant_isolation ON supplier_account_ledger;
CREATE POLICY supplier_account_ledger_tenant_isolation ON supplier_account_ledger
    USING (
        supplier_id IN (
            SELECT id FROM supplier WHERE tenant_id = get_current_tenant_id()
        )
    )
    WITH CHECK (
        supplier_id IN (
            SELECT id FROM supplier WHERE tenant_id = get_current_tenant_id()
        )
    );

COMMENT ON POLICY supplier_account_ledger_tenant_isolation ON supplier_account_ledger IS
'Ensures supplier ledger entries are only visible/modifiable within their tenant context via supplier relationship.';

-- ============================================================
-- Purchase Order Table RLS
-- ============================================================

ALTER TABLE purchase_order ENABLE ROW LEVEL SECURITY;
ALTER TABLE purchase_order FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS purchase_order_tenant_isolation ON purchase_order;
CREATE POLICY purchase_order_tenant_isolation ON purchase_order
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

COMMENT ON POLICY purchase_order_tenant_isolation ON purchase_order IS
'Ensures purchase orders are only visible/modifiable within their tenant context.';

-- ============================================================
-- Purchase Item Table RLS
-- Note: Uses purchase_order_id -> purchase_order.tenant_id for isolation
-- ============================================================

ALTER TABLE purchase_item ENABLE ROW LEVEL SECURITY;
ALTER TABLE purchase_item FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS purchase_item_tenant_isolation ON purchase_item;
CREATE POLICY purchase_item_tenant_isolation ON purchase_item
    USING (
        purchase_order_id IN (
            SELECT id FROM purchase_order WHERE tenant_id = get_current_tenant_id()
        )
    )
    WITH CHECK (
        purchase_order_id IN (
            SELECT id FROM purchase_order WHERE tenant_id = get_current_tenant_id()
        )
    );

COMMENT ON POLICY purchase_item_tenant_isolation ON purchase_item IS
'Ensures purchase items are only visible/modifiable within their tenant context via purchase order relationship.';

-- ============================================================
-- Sale Table RLS
-- ============================================================

ALTER TABLE sale ENABLE ROW LEVEL SECURITY;
ALTER TABLE sale FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS sale_tenant_isolation ON sale;
CREATE POLICY sale_tenant_isolation ON sale
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

COMMENT ON POLICY sale_tenant_isolation ON sale IS
'Ensures sales are only visible/modifiable within their tenant context.';

-- ============================================================
-- Sale Item Table RLS
-- Note: Uses sale_id -> sale.tenant_id for isolation
-- ============================================================

ALTER TABLE sale_item ENABLE ROW LEVEL SECURITY;
ALTER TABLE sale_item FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS sale_item_tenant_isolation ON sale_item;
CREATE POLICY sale_item_tenant_isolation ON sale_item
    USING (
        sale_id IN (
            SELECT id FROM sale WHERE tenant_id = get_current_tenant_id()
        )
    )
    WITH CHECK (
        sale_id IN (
            SELECT id FROM sale WHERE tenant_id = get_current_tenant_id()
        )
    );

COMMENT ON POLICY sale_item_tenant_isolation ON sale_item IS
'Ensures sale items are only visible/modifiable within their tenant context via sale relationship.';

-- ============================================================
-- Payment Table RLS
-- Note: Uses sale_id -> sale.tenant_id for isolation
-- ============================================================

ALTER TABLE payment ENABLE ROW LEVEL SECURITY;
ALTER TABLE payment FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS payment_tenant_isolation ON payment;
CREATE POLICY payment_tenant_isolation ON payment
    USING (
        sale_id IN (
            SELECT id FROM sale WHERE tenant_id = get_current_tenant_id()
        )
    )
    WITH CHECK (
        sale_id IN (
            SELECT id FROM sale WHERE tenant_id = get_current_tenant_id()
        )
    );

COMMENT ON POLICY payment_tenant_isolation ON payment IS
'Ensures payments are only visible/modifiable within their tenant context via sale relationship.';

-- ============================================================
-- Budget Table RLS
-- ============================================================

ALTER TABLE budget ENABLE ROW LEVEL SECURITY;
ALTER TABLE budget FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS budget_tenant_isolation ON budget;
CREATE POLICY budget_tenant_isolation ON budget
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

COMMENT ON POLICY budget_tenant_isolation ON budget IS
'Ensures budgets are only visible/modifiable within their tenant context.';

-- ============================================================
-- Product Price History Table RLS
-- Note: Uses product_id -> product.tenant_id for isolation
-- ============================================================

ALTER TABLE product_price_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE product_price_history FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS product_price_history_tenant_isolation ON product_price_history;
CREATE POLICY product_price_history_tenant_isolation ON product_price_history
    USING (
        product_id IN (
            SELECT id FROM product WHERE tenant_id = get_current_tenant_id()
        )
    )
    WITH CHECK (
        product_id IN (
            SELECT id FROM product WHERE tenant_id = get_current_tenant_id()
        )
    );

COMMENT ON POLICY product_price_history_tenant_isolation ON product_price_history IS
'Ensures product price history is only visible/modifiable within their tenant context via product relationship.';

-- ============================================================
-- Product Cost History Table RLS
-- Note: Uses product_id -> product.tenant_id for isolation
-- ============================================================

ALTER TABLE product_cost_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE product_cost_history FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS product_cost_history_tenant_isolation ON product_cost_history;
CREATE POLICY product_cost_history_tenant_isolation ON product_cost_history
    USING (
        product_id IN (
            SELECT id FROM product WHERE tenant_id = get_current_tenant_id()
        )
    )
    WITH CHECK (
        product_id IN (
            SELECT id FROM product WHERE tenant_id = get_current_tenant_id()
        )
    );

COMMENT ON POLICY product_cost_history_tenant_isolation ON product_cost_history IS
'Ensures product cost history is only visible/modifiable within their tenant context via product relationship.';

-- ============================================================
-- Bypass Policies for Admin Role
-- ============================================================
-- Create a role for admin operations that bypasses RLS
-- Use sparingly and only for migrations/admin tasks

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'gravitea_admin') THEN
        CREATE ROLE gravitea_admin NOLOGIN BYPASSRLS;
        COMMENT ON ROLE gravitea_admin IS
        'Admin role that bypasses RLS. Use for migrations and admin tasks only.';
    END IF;
END
$$;

-- ============================================================
-- Application Role (normal operations)
-- ============================================================

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'gravitea_app') THEN
        CREATE ROLE gravitea_app NOLOGIN;
        COMMENT ON ROLE gravitea_app IS
        'Application role for normal operations. Subject to RLS policies.';
    END IF;
END
$$;

-- Grant permissions to app role
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO gravitea_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO gravitea_app;
GRANT EXECUTE ON FUNCTION get_current_tenant_id() TO gravitea_app;

-- ============================================================
-- Audit Log Table RLS
-- ============================================================
-- Critical: Audit logs must be tenant-isolated to prevent
-- cross-tenant audit data exposure.

ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS audit_log_tenant_isolation ON audit_log;
CREATE POLICY audit_log_tenant_isolation ON audit_log
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

COMMENT ON POLICY audit_log_tenant_isolation ON audit_log IS
'Ensures audit logs are only visible/modifiable within their tenant context.
This is critical for compliance and security audit trails.';

-- ============================================================
-- Verification Query
-- ============================================================
-- Run this to verify RLS is enabled on all tenant-bound tables:

  SELECT
      t.schemaname,
      t.tablename,
      c.relrowsecurity AS rowsecurity,
      c.relforcerowsecurity AS forcerowsecurity
  FROM pg_tables t
  JOIN pg_class c ON c.relname = t.tablename
  JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = t.schemaname
  WHERE t.schemaname = 'public'
  AND t.tablename IN (
      'role', 'app_user', 'branch',
      'product', 'product_category', 'price_list', 'supplier',
      'stock_movement', 'stock_snapshot',
      'product_price_history', 'product_cost_history',
      'customer', 'customer_account_ledger',
      'sale', 'sale_item', 'payment', 'budget',
      'supplier_account_ledger', 'purchase_order', 'purchase_item',
      'sync_session', 'pending_operation',
      'audit_log'
  )
  ORDER BY t.tablename;

