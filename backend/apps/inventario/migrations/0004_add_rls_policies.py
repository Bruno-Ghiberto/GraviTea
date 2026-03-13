"""
Add Row Level Security (RLS) policies for inventario tables.

Defense-in-depth: PostgreSQL RLS ensures tenant isolation at the database
level, complementing Django's TenantBoundManager at the application level.

Direct tenant_id tables: product_category, supplier, price_list, product,
stock_movement.

FK-based tables (no direct tenant_id):
- product_price_history: isolated via product_id -> product.tenant_id
- product_cost_history: isolated via product_id -> product.tenant_id
- stock_snapshot: isolated via branch_id -> branch.tenant_id
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("inventario", "0003_add_movement_status_and_links"),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                # ProductCategory RLS
                "ALTER TABLE product_category ENABLE ROW LEVEL SECURITY;",
                "ALTER TABLE product_category FORCE ROW LEVEL SECURITY;",
                """
                CREATE POLICY product_category_tenant_isolation
                    ON product_category
                    USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
                    WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid);
                """,
                # Supplier RLS
                "ALTER TABLE supplier ENABLE ROW LEVEL SECURITY;",
                "ALTER TABLE supplier FORCE ROW LEVEL SECURITY;",
                """
                CREATE POLICY supplier_tenant_isolation
                    ON supplier
                    USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
                    WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid);
                """,
                # PriceList RLS
                "ALTER TABLE price_list ENABLE ROW LEVEL SECURITY;",
                "ALTER TABLE price_list FORCE ROW LEVEL SECURITY;",
                """
                CREATE POLICY price_list_tenant_isolation
                    ON price_list
                    USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
                    WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid);
                """,
                # Product RLS
                "ALTER TABLE product ENABLE ROW LEVEL SECURITY;",
                "ALTER TABLE product FORCE ROW LEVEL SECURITY;",
                """
                CREATE POLICY product_tenant_isolation
                    ON product
                    USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
                    WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid);
                """,
                # StockMovement RLS
                "ALTER TABLE stock_movement ENABLE ROW LEVEL SECURITY;",
                "ALTER TABLE stock_movement FORCE ROW LEVEL SECURITY;",
                """
                CREATE POLICY stock_movement_tenant_isolation
                    ON stock_movement
                    USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
                    WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid);
                """,
                # ProductPriceHistory RLS (FK-based via product_id -> product.tenant_id)
                "ALTER TABLE product_price_history ENABLE ROW LEVEL SECURITY;",
                "ALTER TABLE product_price_history FORCE ROW LEVEL SECURITY;",
                """
                CREATE POLICY product_price_history_tenant_isolation
                    ON product_price_history
                    USING (
                        product_id IN (
                            SELECT id FROM product
                            WHERE tenant_id = current_setting('app.current_tenant_id')::uuid
                        )
                    )
                    WITH CHECK (
                        product_id IN (
                            SELECT id FROM product
                            WHERE tenant_id = current_setting('app.current_tenant_id')::uuid
                        )
                    );
                """,
                # ProductCostHistory RLS (FK-based via product_id -> product.tenant_id)
                "ALTER TABLE product_cost_history ENABLE ROW LEVEL SECURITY;",
                "ALTER TABLE product_cost_history FORCE ROW LEVEL SECURITY;",
                """
                CREATE POLICY product_cost_history_tenant_isolation
                    ON product_cost_history
                    USING (
                        product_id IN (
                            SELECT id FROM product
                            WHERE tenant_id = current_setting('app.current_tenant_id')::uuid
                        )
                    )
                    WITH CHECK (
                        product_id IN (
                            SELECT id FROM product
                            WHERE tenant_id = current_setting('app.current_tenant_id')::uuid
                        )
                    );
                """,
                # StockSnapshot RLS (FK-based via branch_id -> branch.tenant_id)
                "ALTER TABLE stock_snapshot ENABLE ROW LEVEL SECURITY;",
                "ALTER TABLE stock_snapshot FORCE ROW LEVEL SECURITY;",
                """
                CREATE POLICY stock_snapshot_tenant_isolation
                    ON stock_snapshot
                    USING (
                        branch_id IN (
                            SELECT id FROM branch
                            WHERE tenant_id = current_setting('app.current_tenant_id')::uuid
                        )
                    )
                    WITH CHECK (
                        branch_id IN (
                            SELECT id FROM branch
                            WHERE tenant_id = current_setting('app.current_tenant_id')::uuid
                        )
                    );
                """,
            ],
            reverse_sql=[
                # Reverse: drop policies and disable RLS
                "DROP POLICY IF EXISTS product_category_tenant_isolation ON product_category;",
                "ALTER TABLE product_category DISABLE ROW LEVEL SECURITY;",
                "DROP POLICY IF EXISTS supplier_tenant_isolation ON supplier;",
                "ALTER TABLE supplier DISABLE ROW LEVEL SECURITY;",
                "DROP POLICY IF EXISTS price_list_tenant_isolation ON price_list;",
                "ALTER TABLE price_list DISABLE ROW LEVEL SECURITY;",
                "DROP POLICY IF EXISTS product_tenant_isolation ON product;",
                "ALTER TABLE product DISABLE ROW LEVEL SECURITY;",
                "DROP POLICY IF EXISTS stock_movement_tenant_isolation ON stock_movement;",
                "ALTER TABLE stock_movement DISABLE ROW LEVEL SECURITY;",
                "DROP POLICY IF EXISTS product_price_history_tenant_isolation ON product_price_history;",
                "ALTER TABLE product_price_history DISABLE ROW LEVEL SECURITY;",
                "DROP POLICY IF EXISTS product_cost_history_tenant_isolation ON product_cost_history;",
                "ALTER TABLE product_cost_history DISABLE ROW LEVEL SECURITY;",
                "DROP POLICY IF EXISTS stock_snapshot_tenant_isolation ON stock_snapshot;",
                "ALTER TABLE stock_snapshot DISABLE ROW LEVEL SECURITY;",
            ],
        ),
    ]
