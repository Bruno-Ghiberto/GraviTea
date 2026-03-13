"""
Add Row Level Security (RLS) policies for sync tables.

Defense-in-depth: PostgreSQL RLS ensures tenant isolation at the database
level, complementing Django's TenantBoundManager at the application level.
Both sync tables (sync_session, pending_operation) have tenant_id and get
direct RLS policies.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("sync", "0004_remove_pendingoperation_idx_pending_op_queue_and_more"),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                # SyncSession RLS
                "ALTER TABLE sync_session ENABLE ROW LEVEL SECURITY;",
                "ALTER TABLE sync_session FORCE ROW LEVEL SECURITY;",
                """
                CREATE POLICY sync_session_tenant_isolation
                    ON sync_session
                    USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
                    WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid);
                """,
                # PendingOperation RLS
                "ALTER TABLE pending_operation ENABLE ROW LEVEL SECURITY;",
                "ALTER TABLE pending_operation FORCE ROW LEVEL SECURITY;",
                """
                CREATE POLICY pending_operation_tenant_isolation
                    ON pending_operation
                    USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
                    WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid);
                """,
            ],
            reverse_sql=[
                # Reverse: drop policies and disable RLS
                "DROP POLICY IF EXISTS sync_session_tenant_isolation ON sync_session;",
                "ALTER TABLE sync_session DISABLE ROW LEVEL SECURITY;",
                "DROP POLICY IF EXISTS pending_operation_tenant_isolation ON pending_operation;",
                "ALTER TABLE pending_operation DISABLE ROW LEVEL SECURITY;",
            ],
        ),
    ]
