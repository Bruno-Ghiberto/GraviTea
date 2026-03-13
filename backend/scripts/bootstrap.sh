#!/bin/bash
# ============================================================
# GRAVITEA-ERP Bootstrap Script (R6)
# ============================================================
# Called as Docker ENTRYPOINT. Runs initialization then exec's CMD.
#
# Flow: wait-for-db → pre-migrate SQL → Django migrate → post-migrate SQL → exec CMD
#
# Environment:
#   DATABASE_URL    - PostgreSQL connection string (required)
#   SQL_INIT_DIR    - Path to infrastructure SQL scripts (default: /app/sql-init)
#   APP_SQL_DIR     - Path to app-level SQL scripts (default: /app/database/sql)
#   SEED_DATA       - Run seed commands if "true" (default: false)
#   DB_WAIT_RETRIES - Max retries for DB readiness (default: 30)
#   DB_WAIT_DELAY   - Seconds between retries (default: 2)
# ============================================================
set -euo pipefail

# --- Configuration ---
SQL_INIT_DIR="${SQL_INIT_DIR:-/app/sql-init}"
APP_SQL_DIR="${APP_SQL_DIR:-/app/database/sql}"
DB_WAIT_RETRIES="${DB_WAIT_RETRIES:-30}"
DB_WAIT_DELAY="${DB_WAIT_DELAY:-2}"

# --- Parse DATABASE_URL ---
parse_database_url() {
    if [ -z "${DATABASE_URL:-}" ]; then
        echo "[bootstrap] ERROR: DATABASE_URL is not set"
        exit 1
    fi

    # Extract components: postgresql://user:password@host:port/dbname
    eval "$(python3 -c "
from urllib.parse import urlparse
import os
url = urlparse(os.environ['DATABASE_URL'])
print(f'DB_HOST={url.hostname or \"localhost\"}')
print(f'DB_PORT={url.port or 5432}')
print(f'DB_USER={url.username or \"gravitea\"}')
print(f'DB_PASSWORD={url.password or \"\"}')
print(f'DB_NAME={url.path.lstrip(\"/\") or \"gravitea_dev\"}')
")"

    export PGPASSWORD="$DB_PASSWORD"
}

# --- Helper: run a single SQL file (errors are non-fatal) ---
run_sql_file() {
    local path="$1"
    local script
    script=$(basename "$path")
    echo "[bootstrap]   -> ${script}"
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
        -f "$path" --quiet --no-psqlrc 2>&1 || true
}

# --- Step 1: Wait for PostgreSQL ---
wait_for_db() {
    echo "[bootstrap] Waiting for PostgreSQL at ${DB_HOST}:${DB_PORT}..."
    local retries=0
    until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -q; do
        retries=$((retries + 1))
        if [ "$retries" -ge "$DB_WAIT_RETRIES" ]; then
            echo "[bootstrap] ERROR: PostgreSQL not ready after ${DB_WAIT_RETRIES} attempts"
            exit 1
        fi
        echo "[bootstrap] Attempt ${retries}/${DB_WAIT_RETRIES} - waiting ${DB_WAIT_DELAY}s..."
        sleep "$DB_WAIT_DELAY"
    done
    echo "[bootstrap] PostgreSQL is ready."
}

# --- Step 2: Pre-migrate SQL (roles, extensions — no table dependencies) ---
run_pre_migrate_sql() {
    if [ -d "$SQL_INIT_DIR" ]; then
        local script="${SQL_INIT_DIR}/000_init_database.sql"
        if [ -f "$script" ]; then
            echo "[bootstrap] Running pre-migrate SQL..."
            run_sql_file "$script"
        fi
    fi
}

# --- Step 3: Django migrations ---
run_migrations() {
    echo "[bootstrap] Running Django migrations..."
    python manage.py migrate --noinput
    echo "[bootstrap] Migrations complete."
}

# --- Step 4: Post-migrate SQL (RLS, functions, constraints — needs tables) ---
run_post_migrate_sql() {
    # Infrastructure scripts that reference Django-managed tables
    local post_scripts=(
        "002_rls_policies.sql"
        "003_stock_functions.sql"
        "004_audit_functions.sql"
        "005_hardening_constraints.sql"
    )

    if [ -d "$SQL_INIT_DIR" ]; then
        echo "[bootstrap] Running post-migrate infrastructure SQL..."
        for script in "${post_scripts[@]}"; do
            local path="${SQL_INIT_DIR}/${script}"
            if [ -f "$path" ]; then
                run_sql_file "$path"
            else
                echo "[bootstrap]   -> ${script} (not found, skipping)"
            fi
        done
    fi

    # App-level RLS scripts (facturacion, ventas)
    if [ -d "$APP_SQL_DIR" ]; then
        echo "[bootstrap] Running app-level SQL scripts from ${APP_SQL_DIR}..."
        for path in "${APP_SQL_DIR}"/*.sql; do
            [ -f "$path" ] || continue
            run_sql_file "$path"
        done
    fi
}

# --- Step 5: Optional seed data ---
run_seed() {
    if [ "${SEED_DATA:-false}" = "true" ]; then
        echo "[bootstrap] Seeding data..."
        python manage.py seed_all 2>&1 || true
        echo "[bootstrap] Seed complete."
    fi
}

# --- Main ---
main() {
    echo "[bootstrap] GRAVITEA-ERP initialization starting..."

    parse_database_url
    wait_for_db
    run_pre_migrate_sql
    run_migrations
    run_post_migrate_sql
    run_seed

    echo "[bootstrap] Initialization complete. Starting application..."
    exec "$@"
}

main "$@"
