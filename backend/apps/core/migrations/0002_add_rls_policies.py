"""
Add Row Level Security (RLS) policies for core tables.

Defense-in-depth: PostgreSQL RLS ensures tenant isolation at the database
level, complementing Django's TenantBoundManager at the application level.
The branch table has tenant_id and gets a direct RLS policy.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                # Branch RLS
                "ALTER TABLE branch ENABLE ROW LEVEL SECURITY;",
                "ALTER TABLE branch FORCE ROW LEVEL SECURITY;",
                """
                CREATE POLICY branch_tenant_isolation
                    ON branch
                    USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
                    WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid);
                """,
            ],
            reverse_sql=[
                # Reverse: drop policy and disable RLS
                "DROP POLICY IF EXISTS branch_tenant_isolation ON branch;",
                "ALTER TABLE branch DISABLE ROW LEVEL SECURITY;",
            ],
        ),
    ]
