"""
Add Row Level Security (RLS) policies for auth tables.

Defense-in-depth: PostgreSQL RLS ensures tenant isolation at the database
level, complementing Django's TenantBoundManager at the application level.
Both auth tables (role, app_user) have tenant_id and get direct RLS policies.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("gravitea_auth", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                # Role RLS
                "ALTER TABLE role ENABLE ROW LEVEL SECURITY;",
                "ALTER TABLE role FORCE ROW LEVEL SECURITY;",
                """
                CREATE POLICY role_tenant_isolation
                    ON role
                    USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
                    WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid);
                """,
                # AppUser RLS
                "ALTER TABLE app_user ENABLE ROW LEVEL SECURITY;",
                "ALTER TABLE app_user FORCE ROW LEVEL SECURITY;",
                """
                CREATE POLICY app_user_tenant_isolation
                    ON app_user
                    USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
                    WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid);
                """,
            ],
            reverse_sql=[
                # Reverse: drop policies and disable RLS
                "DROP POLICY IF EXISTS role_tenant_isolation ON role;",
                "ALTER TABLE role DISABLE ROW LEVEL SECURITY;",
                "DROP POLICY IF EXISTS app_user_tenant_isolation ON app_user;",
                "ALTER TABLE app_user DISABLE ROW LEVEL SECURITY;",
            ],
        ),
    ]
