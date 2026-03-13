-- ============================================================
-- Hardening Constraints for Gravitea ERP
-- PostgreSQL 18.1 Required
-- ============================================================
-- Purpose: Additional CHECK constraints and indexes for data integrity
-- and query performance. Run after Django migrations + 002-004 scripts.
-- Execute: psql -U postgres -d gravitea -f 005_hardening_constraints.sql
-- IDEMPOTENT: Safe to run multiple times without errors.
-- ============================================================

-- ============================================================
-- CHECK Constraints for Monetary Fields
-- ============================================================
-- Ensures monetary values cannot be negative at the database level,
-- providing defense-in-depth beyond application validation.
-- Uses DO $$ ... EXCEPTION WHEN duplicate_object $$ for idempotency.

-- Product price/cost constraints
DO $$ BEGIN
    ALTER TABLE product
        ADD CONSTRAINT chk_product_unit_price_positive
        CHECK (unit_price IS NULL OR unit_price >= 0);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE product
        ADD CONSTRAINT chk_product_cost_price_positive
        CHECK (cost_price IS NULL OR cost_price >= 0);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Product tax_rate range constraint (0-100%)
DO $$ BEGIN
    ALTER TABLE product
        ADD CONSTRAINT chk_product_tax_rate_range
        CHECK (tax_rate IS NULL OR (tax_rate >= 0 AND tax_rate <= 100));
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Sale item price constraint
DO $$ BEGIN
    ALTER TABLE sale_item
        ADD CONSTRAINT chk_sale_item_unit_price_positive
        CHECK (unit_price >= 0);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Sale item tax_rate range constraint
DO $$ BEGIN
    ALTER TABLE sale_item
        ADD CONSTRAINT chk_sale_item_tax_rate_range
        CHECK (tax_rate IS NULL OR (tax_rate >= 0 AND tax_rate <= 100));
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Price list margin constraint
DO $$ BEGIN
    ALTER TABLE price_list
        ADD CONSTRAINT chk_price_list_margin_range
        CHECK (margin_pct IS NULL OR (margin_pct >= 0 AND margin_pct <= 100));
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Stock quantity constraints (cannot be negative)
DO $$ BEGIN
    ALTER TABLE stock_snapshot
        ADD CONSTRAINT chk_stock_snapshot_quantity_non_negative
        CHECK (quantity >= 0);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE stock_snapshot
        ADD CONSTRAINT chk_stock_snapshot_reserved_non_negative
        CHECK (reserved_quantity >= 0);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Price history constraint
DO $$ BEGIN
    ALTER TABLE product_price_history
        ADD CONSTRAINT chk_price_history_price_positive
        CHECK (price >= 0);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Cost history constraint
DO $$ BEGIN
    ALTER TABLE product_cost_history
        ADD CONSTRAINT chk_cost_history_cost_positive
        CHECK (cost >= 0);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- ============================================================
-- Missing Foreign Key Indexes
-- ============================================================
-- Foreign keys without indexes cause slow JOINs and constraint checks.
-- These indexes complement the existing unique constraints.

-- Product foreign keys
CREATE INDEX IF NOT EXISTS idx_product_category_id ON product(category_id);
CREATE INDEX IF NOT EXISTS idx_product_supplier_id ON product(supplier_id);

-- Stock movement foreign keys
CREATE INDEX IF NOT EXISTS idx_stock_movement_branch_id ON stock_movement(branch_id);
CREATE INDEX IF NOT EXISTS idx_stock_movement_product_id ON stock_movement(product_id);

-- Sale item foreign keys
CREATE INDEX IF NOT EXISTS idx_sale_item_sale_id ON sale_item(sale_id);
CREATE INDEX IF NOT EXISTS idx_sale_item_product_id ON sale_item(product_id);

-- Purchase item foreign keys
CREATE INDEX IF NOT EXISTS idx_purchase_item_purchase_order_id ON purchase_item(purchase_order_id);
CREATE INDEX IF NOT EXISTS idx_purchase_item_product_id ON purchase_item(product_id);

-- Payment foreign keys
CREATE INDEX IF NOT EXISTS idx_payment_sale_id ON payment(sale_id);

-- Customer account ledger foreign keys
CREATE INDEX IF NOT EXISTS idx_customer_account_ledger_customer_id ON customer_account_ledger(customer_id);

-- Supplier account ledger foreign keys
CREATE INDEX IF NOT EXISTS idx_supplier_account_ledger_supplier_id ON supplier_account_ledger(supplier_id);

-- Price history foreign keys
CREATE INDEX IF NOT EXISTS idx_product_price_history_product_id ON product_price_history(product_id);
CREATE INDEX IF NOT EXISTS idx_product_price_history_price_list_id ON product_price_history(price_list_id);

-- Cost history foreign keys
CREATE INDEX IF NOT EXISTS idx_product_cost_history_product_id ON product_cost_history(product_id);

-- Pending operation foreign keys
CREATE INDEX IF NOT EXISTS idx_pending_operation_sync_session_id ON pending_operation(sync_session_id);

-- ============================================================
-- Verification Queries
-- ============================================================

-- Verify CHECK constraints are in place
SELECT
    tc.table_name,
    tc.constraint_name,
    tc.constraint_type,
    cc.check_clause
FROM information_schema.table_constraints tc
JOIN information_schema.check_constraints cc
    ON tc.constraint_name = cc.constraint_name
WHERE tc.constraint_type = 'CHECK'
    AND tc.table_schema = 'public'
    AND tc.constraint_name LIKE 'chk_%'
ORDER BY tc.table_name, tc.constraint_name;

-- Verify indexes exist for foreign keys
SELECT
    i.relname AS index_name,
    t.relname AS table_name,
    a.attname AS column_name
FROM pg_index ix
JOIN pg_class i ON i.oid = ix.indexrelid
JOIN pg_class t ON t.oid = ix.indrelid
JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
WHERE i.relname LIKE 'idx_%'
    AND t.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
ORDER BY t.relname, i.relname;
