-- =============================================================================
-- Gravitea ERP - Database Schema REFERENCE (Tables & ENUMs)
-- PostgreSQL 18.1 Required
-- =============================================================================
-- Version: 1.0.0
-- Purpose: REFERENCE ONLY — Documents the schema as originally designed.
--          Django migrations are the single source of truth for table
--          definitions (R5). Do NOT execute this file directly.
-- Original: 001_schema.sql (renamed per R5 schema drift resolution)
-- =============================================================================

-- =============================================================================
-- Note: Extensions are created in 000_init_database.sql
-- This ensures pgcrypto exists for gen_random_uuid()
-- =============================================================================
CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- Idempotent, safe to re-run

-- =============================================================================
-- 1) ENUM Types
-- =============================================================================

CREATE TYPE payment_method_enum AS ENUM (
    'CASH',
    'CREDIT_CARD',
    'DEBIT_CARD',
    'TRANSFER',
    'QR',
    'ACCOUNT'
);

CREATE TYPE stock_movement_type_enum AS ENUM (
    'SALE',
    'PURCHASE',
    'ADJ',
    'TRANS_IN',
    'TRANS_OUT'
);

CREATE TYPE sale_type_enum AS ENUM (
    'FACTURA_A',
    'FACTURA_B',
    'TICKET',
    'NC'
);

CREATE TYPE sale_status_enum AS ENUM (
    'DRAFT',
    'PENDING_AFIP',
    'FISCALIZED',
    'CANCELLED'
);

CREATE TYPE budget_status_enum AS ENUM (
    'OPEN',
    'CONVERTED',
    'EXPIRED'
);

CREATE TYPE customer_ledger_type_enum AS ENUM (
    'DEBIT',
    'CREDIT'
);

CREATE TYPE supplier_ledger_type_enum AS ENUM (
    'DEBIT',
    'CREDIT'
);

CREATE TYPE purchase_order_status_enum AS ENUM (
    'DRAFT',
    'SENT',
    'PARTIAL_RECEIVED',
    'COMPLETED'
);

CREATE TYPE sync_status_enum AS ENUM (
    'PENDING',
    'IN_PROGRESS',
    'COMPLETED',
    'FAILED',
    'CONFLICT'
);

CREATE TYPE operation_type_enum AS ENUM (
    'CREATE',
    'UPDATE',
    'DELETE'
);

CREATE TYPE operation_status_enum AS ENUM (
    'PENDING',
    'PROCESSING',
    'APPLIED',
    'REJECTED',
    'CONFLICT'
);

-- =============================================================================
-- 2) TENANCY & CONFIGURATION
-- =============================================================================

CREATE TABLE tenant (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                TEXT NOT NULL,
    tax_id              TEXT UNIQUE,                    -- CUIT/RUT empresa (unique per system)
    fiscal_config_public JSONB,                        -- datos no sensibles
    fiscal_secrets_ref  TEXT,                          -- referencia a Secret Manager
    plan_type           TEXT NOT NULL,                 -- FREE, PRO, ENTERPRISE
    valid_until         TIMESTAMPTZ,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE branch (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
    name                TEXT NOT NULL,
    address             TEXT,
    phone               TEXT,
    coordinates         JSONB,
    afip_pos_number     INTEGER,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE role (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
    name                TEXT NOT NULL,
    permissions         JSONB NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE app_user (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
    email               TEXT NOT NULL,
    password_hash       TEXT NOT NULL,
    full_name           TEXT,
    role_id             UUID REFERENCES role(id),
    default_branch_id   UUID REFERENCES branch(id) ON DELETE SET NULL,
    last_login          TIMESTAMPTZ,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_app_user_tenant_email UNIQUE (tenant_id, email)
);

-- =============================================================================
-- 3) INVENTORY
-- =============================================================================

CREATE TABLE product_category (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
    name                TEXT NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_product_category_tenant_name UNIQUE (tenant_id, name)
);

CREATE TABLE price_list (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
    name                TEXT NOT NULL,
    margin_pct          NUMERIC(6,2),
    is_default          BOOLEAN NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_price_list_tenant_name UNIQUE (tenant_id, name)
);

CREATE TABLE supplier (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
    name                    TEXT NOT NULL,
    tax_id_encrypted        TEXT,
    tax_id_hash             CHAR(64),
    contact_info_encrypted  TEXT,
    email_encrypted         TEXT,
    email_hash              CHAR(64),
    address_encrypted       TEXT,
    lead_time_days          INTEGER,
    current_balance         NUMERIC(16,2) NOT NULL DEFAULT 0,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_supplier_tenant_taxid_hash ON supplier (tenant_id, tax_id_hash);
CREATE INDEX idx_supplier_tenant_email_hash ON supplier (tenant_id, email_hash);

CREATE TABLE product (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
    sku                 TEXT NOT NULL,
    barcode             TEXT,                              -- Encrypted barcode value
    barcode_blind_idx   CHAR(64),                          -- HMAC-SHA256 blind index for searches
    name                TEXT NOT NULL,
    description         TEXT,
    category_id         UUID REFERENCES product_category(id),
    supplier_id         UUID REFERENCES supplier(id),
    current_cost        NUMERIC(17,3),                     -- Aligned with Django MoneyField
    current_price       NUMERIC(17,3),                     -- Aligned with Django MoneyField
    tax_rate            NUMERIC(5,2),
    min_stock           NUMERIC(16,4),
    max_stock           NUMERIC(16,4),
    attributes          JSONB,
    ml_tags             JSONB,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_product_tenant_sku UNIQUE (tenant_id, sku),
    CONSTRAINT uq_product_tenant_barcode UNIQUE (tenant_id, barcode)
);

CREATE INDEX idx_product_barcode_blind ON product (tenant_id, barcode_blind_idx);

CREATE TABLE product_price_history (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id          UUID NOT NULL REFERENCES product(id) ON DELETE CASCADE,
    price_list_id       UUID NOT NULL REFERENCES price_list(id) ON DELETE CASCADE,
    price               NUMERIC(16,4) NOT NULL,
    valid_from          TIMESTAMPTZ NOT NULL,
    valid_to            TIMESTAMPTZ,
    change_reason       TEXT,
    changed_by_user_id  UUID REFERENCES app_user(id)
);

CREATE TABLE product_cost_history (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id          UUID NOT NULL REFERENCES product(id) ON DELETE CASCADE,
    cost                NUMERIC(16,4) NOT NULL,
    valid_from          TIMESTAMPTZ NOT NULL,
    valid_to            TIMESTAMPTZ,
    source_doc          TEXT
);

CREATE TABLE stock_snapshot (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    branch_id           UUID NOT NULL REFERENCES branch(id) ON DELETE CASCADE,
    product_id          UUID NOT NULL REFERENCES product(id) ON DELETE CASCADE,
    quantity            NUMERIC(16,4) NOT NULL DEFAULT 0,
    reserved_quantity   NUMERIC(16,4) NOT NULL DEFAULT 0,
    last_updated        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_stock_snapshot UNIQUE (branch_id, product_id)
);

CREATE TABLE stock_movement (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
    branch_id           UUID NOT NULL REFERENCES branch(id) ON DELETE CASCADE,
    product_id          UUID NOT NULL REFERENCES product(id) ON DELETE CASCADE,
    quantity_delta      NUMERIC(16,4) NOT NULL,
    cost_snapshot       NUMERIC(16,4),
    type                stock_movement_type_enum NOT NULL,
    reference_id        UUID,
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- 4) CUSTOMERS & ACCOUNT LEDGER
-- =============================================================================

CREATE TABLE customer (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
    name                    TEXT NOT NULL,
    tax_id_encrypted        TEXT,
    tax_id_hash             CHAR(64),
    email_encrypted         TEXT,
    email_hash              CHAR(64),
    phone_encrypted         TEXT,
    address_encrypted       TEXT,
    price_list_id           UUID REFERENCES price_list(id),
    credit_limit            NUMERIC(16,2) NOT NULL DEFAULT 0,
    current_balance         NUMERIC(16,2) NOT NULL DEFAULT 0,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_customer_tenant_taxid_hash ON customer (tenant_id, tax_id_hash);
CREATE INDEX idx_customer_tenant_email_hash ON customer (tenant_id, email_hash);

CREATE TABLE customer_account_ledger (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id         UUID NOT NULL REFERENCES customer(id) ON DELETE CASCADE,
    type                customer_ledger_type_enum NOT NULL,
    amount              NUMERIC(16,2) NOT NULL,
    reference_id        UUID,
    balance_snapshot    NUMERIC(16,2) NOT NULL,
    description         TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- 5) SUPPLIERS ACCOUNT LEDGER & PURCHASES
-- =============================================================================

CREATE TABLE supplier_account_ledger (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supplier_id         UUID NOT NULL REFERENCES supplier(id) ON DELETE CASCADE,
    type                supplier_ledger_type_enum NOT NULL,
    amount              NUMERIC(16,2) NOT NULL,
    reference_id        UUID,
    balance_snapshot    NUMERIC(16,2) NOT NULL,
    description         TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE purchase_order (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
    supplier_id         UUID NOT NULL REFERENCES supplier(id) ON DELETE CASCADE,
    status              purchase_order_status_enum NOT NULL,
    total_estimated     NUMERIC(16,2),
    expected_delivery   TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE purchase_item (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    purchase_order_id   UUID NOT NULL REFERENCES purchase_order(id) ON DELETE CASCADE,
    product_id          UUID NOT NULL REFERENCES product(id) ON DELETE RESTRICT,
    quantity_ordered    NUMERIC(16,4) NOT NULL,
    quantity_received   NUMERIC(16,4) NOT NULL DEFAULT 0,
    unit_cost           NUMERIC(16,4) NOT NULL,
    subtotal            NUMERIC(16,4) NOT NULL
);

-- =============================================================================
-- 6) SALES & POS
-- =============================================================================

CREATE TABLE sale (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
    branch_id           UUID NOT NULL REFERENCES branch(id) ON DELETE CASCADE,
    customer_id         UUID REFERENCES customer(id),
    user_id             UUID REFERENCES app_user(id),
    doc_number          TEXT,
    type                sale_type_enum NOT NULL,
    status              sale_status_enum NOT NULL,
    total_net           NUMERIC(16,2) NOT NULL DEFAULT 0,
    total_tax           NUMERIC(16,2) NOT NULL DEFAULT 0,
    total_gross         NUMERIC(16,2) NOT NULL DEFAULT 0,
    afip_response       JSONB,
    ml_context          JSONB,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sale_tenant_branch_date ON sale (tenant_id, branch_id, created_at);

CREATE TABLE sale_item (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sale_id             UUID NOT NULL REFERENCES sale(id) ON DELETE CASCADE,
    product_id          UUID NOT NULL REFERENCES product(id) ON DELETE RESTRICT,
    description         TEXT NOT NULL,
    quantity            NUMERIC(16,4) NOT NULL,
    unit_price          NUMERIC(16,4) NOT NULL,
    discount_pct        NUMERIC(6,2) NOT NULL DEFAULT 0,
    tax_rate            NUMERIC(5,2),
    subtotal            NUMERIC(16,4) NOT NULL
);

CREATE TABLE payment (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sale_id                     UUID NOT NULL REFERENCES sale(id) ON DELETE CASCADE,
    method                      payment_method_enum NOT NULL,
    amount                      NUMERIC(16,2) NOT NULL,
    currency                    VARCHAR(3) NOT NULL DEFAULT 'ARS',
    details                     JSONB,
    sensitive_details_encrypted TEXT,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE budget (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
    customer_id         UUID REFERENCES customer(id),
    user_id             UUID REFERENCES app_user(id),
    total_estimated     NUMERIC(16,2) NOT NULL DEFAULT 0,
    valid_until         TIMESTAMPTZ,
    status              budget_status_enum NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- 7) SYNC & OFFLINE-FIRST
-- =============================================================================

CREATE TABLE sync_session (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
    branch_id           UUID NOT NULL REFERENCES branch(id) ON DELETE CASCADE,
    device_id           TEXT NOT NULL,
    last_sync_at        TIMESTAMPTZ,
    sync_vector         JSONB NOT NULL DEFAULT '{}',
    status              sync_status_enum NOT NULL DEFAULT 'PENDING',
    error_message       TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_sync_session_tenant_device UNIQUE (tenant_id, device_id)
);

CREATE INDEX idx_sync_session_device ON sync_session (tenant_id, device_id);
CREATE INDEX idx_sync_session_status ON sync_session (tenant_id, status);

CREATE TABLE pending_operation (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
    sync_session_id     UUID NOT NULL REFERENCES sync_session(id) ON DELETE CASCADE,
    operation_type      operation_type_enum NOT NULL,
    entity_type         TEXT NOT NULL,
    entity_id           UUID NOT NULL,
    payload             JSONB NOT NULL,
    client_timestamp    TIMESTAMPTZ NOT NULL,
    server_timestamp    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status              operation_status_enum NOT NULL DEFAULT 'PENDING',
    conflict_data       JSONB,
    error_message       TEXT,
    processed_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_pending_op_session ON pending_operation (sync_session_id, status);
CREATE INDEX idx_pending_op_entity ON pending_operation (tenant_id, entity_type, entity_id);
CREATE INDEX idx_pending_op_status ON pending_operation (tenant_id, status, client_timestamp);

-- =============================================================================
-- 8) AUDIT LOG
-- =============================================================================

CREATE TABLE audit_log (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       UUID NOT NULL,
    table_name      VARCHAR(100) NOT NULL,
    record_id       UUID NOT NULL,
    operation       VARCHAR(10) NOT NULL CHECK (operation IN ('INSERT', 'UPDATE', 'DELETE')),
    old_values      JSONB,
    new_values      JSONB,
    changed_fields  TEXT[],
    user_id         UUID,
    user_email      VARCHAR(255),
    ip_address      INET,
    user_agent      TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_audit_log_tenant_table ON audit_log (tenant_id, table_name, created_at DESC);
CREATE INDEX idx_audit_log_record ON audit_log (tenant_id, record_id, created_at DESC);
CREATE INDEX idx_audit_log_user ON audit_log (tenant_id, user_id, created_at DESC);
CREATE INDEX idx_audit_log_created_at ON audit_log (created_at DESC);

-- =============================================================================
-- END OF SCHEMA
-- =============================================================================
