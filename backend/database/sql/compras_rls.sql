-- ============================================================
-- Row Level Security (RLS) Policies for Compras Module
-- PostgreSQL 18.1 Required
-- ============================================================
-- Purpose: Defense-in-depth tenant isolation for purchasing tables.
-- PurchaseOrder and Supplier have tenant_id directly.
-- PurchaseOrderItem inherits isolation via purchase_order → tenant_id join.
-- ============================================================

-- ============================================================
-- Supplier Table RLS (already exists in core — no-op if already applied)
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
-- PurchaseOrder Table RLS
-- ============================================================

ALTER TABLE compras_purchaseorder ENABLE ROW LEVEL SECURITY;
ALTER TABLE compras_purchaseorder FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS purchaseorder_tenant_isolation ON compras_purchaseorder;
CREATE POLICY purchaseorder_tenant_isolation ON compras_purchaseorder
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

COMMENT ON POLICY purchaseorder_tenant_isolation ON compras_purchaseorder IS
'Ensures purchase orders are only visible/modifiable within their tenant context.';

-- ============================================================
-- PurchaseOrderItem Table RLS (via join to PO)
-- ============================================================

ALTER TABLE compras_purchaseorderitem ENABLE ROW LEVEL SECURITY;
ALTER TABLE compras_purchaseorderitem FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS purchaseorderitem_tenant_isolation ON compras_purchaseorderitem;
CREATE POLICY purchaseorderitem_tenant_isolation ON compras_purchaseorderitem
    USING (
        EXISTS (
            SELECT 1 FROM compras_purchaseorder po
            WHERE po.id = purchase_order_id
            AND po.tenant_id = get_current_tenant_id()
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM compras_purchaseorder po
            WHERE po.id = purchase_order_id
            AND po.tenant_id = get_current_tenant_id()
        )
    );

COMMENT ON POLICY purchaseorderitem_tenant_isolation ON compras_purchaseorderitem IS
'Ensures PO items are only accessible within their parent PO tenant context.';

-- ============================================================
-- GoodsReceipt Table RLS
-- ============================================================

ALTER TABLE compras_goodsreceipt ENABLE ROW LEVEL SECURITY;
ALTER TABLE compras_goodsreceipt FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS goodsreceipt_tenant_isolation ON compras_goodsreceipt;
CREATE POLICY goodsreceipt_tenant_isolation ON compras_goodsreceipt
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

COMMENT ON POLICY goodsreceipt_tenant_isolation ON compras_goodsreceipt IS
'Ensures goods receipts are only visible/modifiable within their tenant context.';

-- ============================================================
-- GoodsReceiptLine Table RLS (via join to GR)
-- ============================================================

ALTER TABLE compras_goodsreceiptline ENABLE ROW LEVEL SECURITY;
ALTER TABLE compras_goodsreceiptline FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS goodsreceiptline_tenant_isolation ON compras_goodsreceiptline;
CREATE POLICY goodsreceiptline_tenant_isolation ON compras_goodsreceiptline
    USING (
        EXISTS (
            SELECT 1 FROM compras_goodsreceipt gr
            WHERE gr.id = goods_receipt_id
            AND gr.tenant_id = get_current_tenant_id()
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM compras_goodsreceipt gr
            WHERE gr.id = goods_receipt_id
            AND gr.tenant_id = get_current_tenant_id()
        )
    );

COMMENT ON POLICY goodsreceiptline_tenant_isolation ON compras_goodsreceiptline IS
'Ensures GR lines are only accessible within their parent GR tenant context.';
