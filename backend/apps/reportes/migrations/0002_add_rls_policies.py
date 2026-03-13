"""
Add Row Level Security (RLS) policies for reportes tables.

Defense-in-depth: PostgreSQL RLS ensures tenant isolation at the database
level, complementing Django's TenantBoundManager at the application level.
All three reportes tables have direct tenant_id columns.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("gravitea_reportes", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                # ReportDefinition RLS
                "ALTER TABLE reportes_reportdefinition ENABLE ROW LEVEL SECURITY;",
                "ALTER TABLE reportes_reportdefinition FORCE ROW LEVEL SECURITY;",
                """
                CREATE POLICY reportdefinition_tenant_isolation
                    ON reportes_reportdefinition
                    USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
                    WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid);
                """,
                # SavedReport RLS
                "ALTER TABLE reportes_savedreport ENABLE ROW LEVEL SECURITY;",
                "ALTER TABLE reportes_savedreport FORCE ROW LEVEL SECURITY;",
                """
                CREATE POLICY savedreport_tenant_isolation
                    ON reportes_savedreport
                    USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
                    WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid);
                """,
                # ExportJob RLS
                "ALTER TABLE reportes_exportjob ENABLE ROW LEVEL SECURITY;",
                "ALTER TABLE reportes_exportjob FORCE ROW LEVEL SECURITY;",
                """
                CREATE POLICY exportjob_tenant_isolation
                    ON reportes_exportjob
                    USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
                    WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid);
                """,
            ],
            reverse_sql=[
                # Reverse: drop policies and disable RLS
                "DROP POLICY IF EXISTS reportdefinition_tenant_isolation ON reportes_reportdefinition;",
                "ALTER TABLE reportes_reportdefinition DISABLE ROW LEVEL SECURITY;",
                "DROP POLICY IF EXISTS savedreport_tenant_isolation ON reportes_savedreport;",
                "ALTER TABLE reportes_savedreport DISABLE ROW LEVEL SECURITY;",
                "DROP POLICY IF EXISTS exportjob_tenant_isolation ON reportes_exportjob;",
                "ALTER TABLE reportes_exportjob DISABLE ROW LEVEL SECURITY;",
            ],
        ),
    ]
