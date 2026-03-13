-- ============================================================
-- Stock Management Functions for Gravitea ERP
-- PostgreSQL 18.1 Required
-- ============================================================
-- Purpose: Database-level functions for stock operations
-- Ensures atomic updates and data integrity
-- Execute: psql -U postgres -d gravitea -f 003_stock_functions.sql
-- Requires: 000_init_database.sql + Django migrations + 002_rls_policies.sql
-- IDEMPOTENT: Safe to run multiple times without errors.
-- ============================================================

-- ============================================================
-- Function: Update Stock Snapshot on Movement
-- ============================================================
-- Automatically updates stock_snapshot table when a stock_movement is created
-- Uses TABLAS.sql column names: quantity_delta, stock_snapshot

CREATE OR REPLACE FUNCTION update_stock_snapshot_on_movement()
RETURNS TRIGGER AS $$
BEGIN
    -- Skip RESERVED movements: Python handles reserved_quantity separately
    -- Only COMMITTED movements should update the physical stock quantity
    IF NEW.status = 'RESERVED' THEN
        RETURN NEW;
    END IF;

    -- Upsert into stock_snapshot (no tenant_id, uses branch_id)
    INSERT INTO stock_snapshot (
        id,
        branch_id,
        product_id,
        quantity,
        reserved_quantity,
        last_updated
    )
    VALUES (
        gen_random_uuid(),
        NEW.branch_id,
        NEW.product_id,
        NEW.quantity_delta,
        0,
        NOW()
    )
    ON CONFLICT (branch_id, product_id)
    DO UPDATE SET
        quantity = stock_snapshot.quantity + EXCLUDED.quantity,
        last_updated = EXCLUDED.last_updated;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION update_stock_snapshot_on_movement() IS
'Trigger function to update stock_snapshot when a stock_movement is inserted.
Ensures atomic stock level updates. Uses quantity_delta from stock_movement.';

-- Create trigger
DROP TRIGGER IF EXISTS trg_update_stock_snapshot ON stock_movement;
CREATE TRIGGER trg_update_stock_snapshot
    AFTER INSERT ON stock_movement
    FOR EACH ROW
    EXECUTE FUNCTION update_stock_snapshot_on_movement();

-- ============================================================
-- Function: Prevent Stock Movement Update/Delete
-- ============================================================
-- Enforces immutability of stock movements at database level

CREATE OR REPLACE FUNCTION prevent_stock_movement_modification()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        RAISE EXCEPTION 'Stock movements are immutable and cannot be updated. Create an adjustment movement instead.'
            USING ERRCODE = 'integrity_constraint_violation';
    ELSIF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Stock movements cannot be deleted. Create a reversal movement instead.'
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION prevent_stock_movement_modification() IS
'Trigger function that prevents updates and deletes on stock_movement table.
Enforces immutable ledger pattern.';

-- Create trigger
DROP TRIGGER IF EXISTS trg_prevent_stock_movement_modification ON stock_movement;
CREATE TRIGGER trg_prevent_stock_movement_modification
    BEFORE UPDATE OR DELETE ON stock_movement
    FOR EACH ROW
    EXECUTE FUNCTION prevent_stock_movement_modification();

-- ============================================================
-- Function: Calculate Stock at Point in Time
-- ============================================================
-- Returns stock quantity for a product/branch at a specific timestamp
-- Uses quantity_delta from TABLAS.sql

CREATE OR REPLACE FUNCTION get_stock_at_time(
    p_tenant_id UUID,
    p_product_id UUID,
    p_branch_id UUID,
    p_timestamp TIMESTAMPTZ
)
RETURNS DECIMAL(16, 4) AS $$
DECLARE
    v_quantity DECIMAL(16, 4);
BEGIN
    SELECT COALESCE(SUM(quantity_delta), 0)
    INTO v_quantity
    FROM stock_movement
    WHERE tenant_id = p_tenant_id
      AND product_id = p_product_id
      AND branch_id = p_branch_id
      AND created_at <= p_timestamp;

    RETURN v_quantity;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

COMMENT ON FUNCTION get_stock_at_time(UUID, UUID, UUID, TIMESTAMPTZ) IS
'Calculates the stock quantity for a product at a specific branch
as of a given timestamp. Useful for historical stock queries.';

-- ============================================================
-- Function: Check Stock Availability
-- ============================================================
-- Verifies if sufficient stock is available for a sale
-- Uses stock_snapshot and accounts for reserved_quantity

CREATE OR REPLACE FUNCTION check_stock_availability(
    p_branch_id UUID,
    p_product_id UUID,
    p_quantity DECIMAL(16, 4)
)
RETURNS BOOLEAN AS $$
DECLARE
    v_available_stock DECIMAL(16, 4);
BEGIN
    SELECT COALESCE(quantity - reserved_quantity, 0)
    INTO v_available_stock
    FROM stock_snapshot
    WHERE branch_id = p_branch_id
      AND product_id = p_product_id;

    RETURN v_available_stock >= p_quantity;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

COMMENT ON FUNCTION check_stock_availability(UUID, UUID, DECIMAL) IS
'Checks if the requested quantity is available in stock (excluding reserved).
Returns TRUE if sufficient stock is available.';

-- ============================================================
-- Function: Reserve Stock for Pending Order
-- ============================================================
-- Reserves stock quantity for a pending sale/order

CREATE OR REPLACE FUNCTION reserve_stock(
    p_branch_id UUID,
    p_product_id UUID,
    p_quantity DECIMAL(16, 4)
)
RETURNS BOOLEAN AS $$
DECLARE
    v_available DECIMAL(16, 4);
BEGIN
    -- Check availability first
    SELECT quantity - reserved_quantity
    INTO v_available
    FROM stock_snapshot
    WHERE branch_id = p_branch_id
      AND product_id = p_product_id
    FOR UPDATE;  -- Lock row

    IF v_available >= p_quantity THEN
        UPDATE stock_snapshot
        SET reserved_quantity = reserved_quantity + p_quantity,
            last_updated = NOW()
        WHERE branch_id = p_branch_id
          AND product_id = p_product_id;
        RETURN TRUE;
    ELSE
        RETURN FALSE;
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION reserve_stock(UUID, UUID, DECIMAL) IS
'Reserves stock for a pending order. Returns TRUE if reservation succeeded.';

-- ============================================================
-- Function: Release Reserved Stock
-- ============================================================
-- Releases previously reserved stock

CREATE OR REPLACE FUNCTION release_reserved_stock(
    p_branch_id UUID,
    p_product_id UUID,
    p_quantity DECIMAL(16, 4)
)
RETURNS VOID AS $$
BEGIN
    UPDATE stock_snapshot
    SET reserved_quantity = GREATEST(0, reserved_quantity - p_quantity),
        last_updated = NOW()
    WHERE branch_id = p_branch_id
      AND product_id = p_product_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION release_reserved_stock(UUID, UUID, DECIMAL) IS
'Releases previously reserved stock quantity.';

-- ============================================================
-- Function: Get Stock Summary by Branch
-- ============================================================
-- Returns stock summary for all products in a branch
-- Uses cost_price from product table (Django model naming)

CREATE OR REPLACE FUNCTION get_branch_stock_summary(
    p_branch_id UUID
)
RETURNS TABLE (
    product_id UUID,
    product_sku TEXT,
    product_name TEXT,
    quantity DECIMAL(16, 4),
    reserved_quantity DECIMAL(16, 4),
    available_quantity DECIMAL(16, 4),
    unit_cost DECIMAL(16, 4),
    total_value DECIMAL(16, 4),
    last_updated TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ss.product_id,
        p.sku AS product_sku,
        p.name AS product_name,
        ss.quantity,
        ss.reserved_quantity,
        (ss.quantity - ss.reserved_quantity) AS available_quantity,
        p.cost_price AS unit_cost,
        (ss.quantity * COALESCE(p.cost_price, 0)) AS total_value,
        ss.last_updated
    FROM stock_snapshot ss
    JOIN product p ON p.id = ss.product_id
    WHERE ss.branch_id = p_branch_id
      AND p.is_active = TRUE
    ORDER BY p.name;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

COMMENT ON FUNCTION get_branch_stock_summary(UUID) IS
'Returns a summary of all products and their stock levels in a branch.
Includes product details and calculated total value.';

-- ============================================================
-- Function: Calculate Stock Value
-- ============================================================
-- Returns total stock value for a branch

CREATE OR REPLACE FUNCTION get_branch_stock_value(
    p_branch_id UUID
)
RETURNS DECIMAL(16, 4) AS $$
DECLARE
    v_total_value DECIMAL(16, 4);
BEGIN
    SELECT COALESCE(SUM(ss.quantity * COALESCE(p.cost_price, 0)), 0)
    INTO v_total_value
    FROM stock_snapshot ss
    JOIN product p ON p.id = ss.product_id
    WHERE ss.branch_id = p_branch_id
      AND p.is_active = TRUE;

    RETURN v_total_value;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

COMMENT ON FUNCTION get_branch_stock_value(UUID) IS
'Calculates the total value of stock in a branch based on current cost prices.';

-- ============================================================
-- Function: Get Low Stock Products
-- ============================================================
-- Returns products with stock below min_stock threshold from product table

CREATE OR REPLACE FUNCTION get_low_stock_products(
    p_branch_id UUID
)
RETURNS TABLE (
    product_id UUID,
    product_sku TEXT,
    product_name TEXT,
    current_quantity DECIMAL(16, 4),
    min_stock DECIMAL(16, 4),
    shortfall DECIMAL(16, 4)
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ss.product_id,
        p.sku AS product_sku,
        p.name AS product_name,
        ss.quantity AS current_quantity,
        p.min_stock,
        (COALESCE(p.min_stock, 0) - ss.quantity) AS shortfall
    FROM stock_snapshot ss
    JOIN product p ON p.id = ss.product_id
    WHERE ss.branch_id = p_branch_id
      AND p.is_active = TRUE
      AND p.min_stock IS NOT NULL
      AND ss.quantity < p.min_stock
    ORDER BY (COALESCE(p.min_stock, 0) - ss.quantity) DESC;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

COMMENT ON FUNCTION get_low_stock_products(UUID) IS
'Returns products with stock quantity below the min_stock threshold from product table.
Useful for reorder alerts and inventory management.';

-- ============================================================
-- Grant Permissions
-- ============================================================

GRANT EXECUTE ON FUNCTION update_stock_snapshot_on_movement() TO gravitea_app;
GRANT EXECUTE ON FUNCTION prevent_stock_movement_modification() TO gravitea_app;
GRANT EXECUTE ON FUNCTION get_stock_at_time(UUID, UUID, UUID, TIMESTAMPTZ) TO gravitea_app;
GRANT EXECUTE ON FUNCTION check_stock_availability(UUID, UUID, DECIMAL) TO gravitea_app;
GRANT EXECUTE ON FUNCTION reserve_stock(UUID, UUID, DECIMAL) TO gravitea_app;
GRANT EXECUTE ON FUNCTION release_reserved_stock(UUID, UUID, DECIMAL) TO gravitea_app;
GRANT EXECUTE ON FUNCTION get_branch_stock_summary(UUID) TO gravitea_app;
GRANT EXECUTE ON FUNCTION get_branch_stock_value(UUID) TO gravitea_app;
GRANT EXECUTE ON FUNCTION get_low_stock_products(UUID) TO gravitea_app;
