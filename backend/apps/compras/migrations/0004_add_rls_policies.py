"""
Add Row Level Security (RLS) policies for compras tables.

Defense-in-depth: PostgreSQL RLS ensures tenant isolation at the database
level, complementing Django's TenantBoundManager at the application level.

Direct tenant_id tables: compras_purchaseorder, compras_goodsreceipt.
FK-based tables (no direct tenant_id):
- compras_purchaseorderitem: isolated via purchase_order_id -> compras_purchaseorder.tenant_id
- compras_goodsreceiptline: isolated via goods_receipt_id -> compras_goodsreceipt.tenant_id

Note: The supplier table already has RLS from inventario/0004_add_rls_policies.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("gravitea_compras", "0003_goods_receipt_models"),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                # PurchaseOrder RLS (direct tenant_id)
                "ALTER TABLE compras_purchaseorder ENABLE ROW LEVEL SECURITY;",
                "ALTER TABLE compras_purchaseorder FORCE ROW LEVEL SECURITY;",
                """
                CREATE POLICY purchaseorder_tenant_isolation
                    ON compras_purchaseorder
                    USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
                    WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid);
                """,
                # PurchaseOrderItem RLS (FK-based via purchase_order_id)
                "ALTER TABLE compras_purchaseorderitem ENABLE ROW LEVEL SECURITY;",
                "ALTER TABLE compras_purchaseorderitem FORCE ROW LEVEL SECURITY;",
                """
                CREATE POLICY purchaseorderitem_tenant_isolation
                    ON compras_purchaseorderitem
                    USING (
                        purchase_order_id IN (
                            SELECT id FROM compras_purchaseorder
                            WHERE tenant_id = current_setting('app.current_tenant_id')::uuid
                        )
                    )
                    WITH CHECK (
                        purchase_order_id IN (
                            SELECT id FROM compras_purchaseorder
                            WHERE tenant_id = current_setting('app.current_tenant_id')::uuid
                        )
                    );
                """,
                # GoodsReceipt RLS (direct tenant_id)
                "ALTER TABLE compras_goodsreceipt ENABLE ROW LEVEL SECURITY;",
                "ALTER TABLE compras_goodsreceipt FORCE ROW LEVEL SECURITY;",
                """
                CREATE POLICY goodsreceipt_tenant_isolation
                    ON compras_goodsreceipt
                    USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
                    WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid);
                """,
                # GoodsReceiptLine RLS (FK-based via goods_receipt_id)
                "ALTER TABLE compras_goodsreceiptline ENABLE ROW LEVEL SECURITY;",
                "ALTER TABLE compras_goodsreceiptline FORCE ROW LEVEL SECURITY;",
                """
                CREATE POLICY goodsreceiptline_tenant_isolation
                    ON compras_goodsreceiptline
                    USING (
                        goods_receipt_id IN (
                            SELECT id FROM compras_goodsreceipt
                            WHERE tenant_id = current_setting('app.current_tenant_id')::uuid
                        )
                    )
                    WITH CHECK (
                        goods_receipt_id IN (
                            SELECT id FROM compras_goodsreceipt
                            WHERE tenant_id = current_setting('app.current_tenant_id')::uuid
                        )
                    );
                """,
            ],
            reverse_sql=[
                # Reverse: drop policies and disable RLS
                "DROP POLICY IF EXISTS purchaseorder_tenant_isolation ON compras_purchaseorder;",
                "ALTER TABLE compras_purchaseorder DISABLE ROW LEVEL SECURITY;",
                "DROP POLICY IF EXISTS purchaseorderitem_tenant_isolation ON compras_purchaseorderitem;",
                "ALTER TABLE compras_purchaseorderitem DISABLE ROW LEVEL SECURITY;",
                "DROP POLICY IF EXISTS goodsreceipt_tenant_isolation ON compras_goodsreceipt;",
                "ALTER TABLE compras_goodsreceipt DISABLE ROW LEVEL SECURITY;",
                "DROP POLICY IF EXISTS goodsreceiptline_tenant_isolation ON compras_goodsreceiptline;",
                "ALTER TABLE compras_goodsreceiptline DISABLE ROW LEVEL SECURITY;",
            ],
        ),
    ]
