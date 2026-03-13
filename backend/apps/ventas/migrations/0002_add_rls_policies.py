"""
Add Row Level Security (RLS) policies for ventas tables.

Defense-in-depth: PostgreSQL RLS ensures tenant isolation at the database
level, complementing Django's TenantBoundManager at the application level.
All three ventas tables (customer, saleorder, saleorderitem) have tenant_id
and get direct RLS policies.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("gravitea_ventas", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                # Customer RLS
                "ALTER TABLE ventas_customer ENABLE ROW LEVEL SECURITY;",
                "ALTER TABLE ventas_customer FORCE ROW LEVEL SECURITY;",
                """
                CREATE POLICY customer_tenant_isolation
                    ON ventas_customer
                    USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
                    WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid);
                """,
                # SaleOrder RLS
                "ALTER TABLE ventas_saleorder ENABLE ROW LEVEL SECURITY;",
                "ALTER TABLE ventas_saleorder FORCE ROW LEVEL SECURITY;",
                """
                CREATE POLICY saleorder_tenant_isolation
                    ON ventas_saleorder
                    USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
                    WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid);
                """,
                # SaleOrderItem RLS
                "ALTER TABLE ventas_saleorderitem ENABLE ROW LEVEL SECURITY;",
                "ALTER TABLE ventas_saleorderitem FORCE ROW LEVEL SECURITY;",
                """
                CREATE POLICY saleorderitem_tenant_isolation
                    ON ventas_saleorderitem
                    USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
                    WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid);
                """,
            ],
            reverse_sql=[
                # Reverse: drop policies and disable RLS
                "DROP POLICY IF EXISTS customer_tenant_isolation ON ventas_customer;",
                "ALTER TABLE ventas_customer DISABLE ROW LEVEL SECURITY;",
                "DROP POLICY IF EXISTS saleorder_tenant_isolation ON ventas_saleorder;",
                "ALTER TABLE ventas_saleorder DISABLE ROW LEVEL SECURITY;",
                "DROP POLICY IF EXISTS saleorderitem_tenant_isolation ON ventas_saleorderitem;",
                "ALTER TABLE ventas_saleorderitem DISABLE ROW LEVEL SECURITY;",
            ],
        ),
    ]
