# Feature Specification: Backend Modules Solidification

**Feature Branch**: `016-backend-modules-solidification`
**Created**: 2026-02-24
**Status**: Draft
**Input**: Restructure the GRAVITEA-ERP backend into a well-defined 8-module architecture. Create the COMPRAS module (migrate Supplier, build purchase workflow), create the REPORTES module (infrastructure skeleton for future BI), expand JSONB customization to new entities, and solidify module boundaries.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Supplier Migration to Purchases Module (Priority: P1)

The Supplier entity is currently housed within the inventory module but semantically belongs to the purchasing domain. A system administrator performs a data migration that moves the Supplier entity to the new purchases module. All existing supplier records, their relationships to products, and their custom fields remain intact. Existing workflows that reference suppliers continue to function without data loss or disruption.

**Why this priority**: This is the foundational change that everything else depends on. The new purchases module cannot be built without owning the Supplier entity. Every subsequent user story (purchase orders, goods receipts) requires Supplier in the correct module. This is also the riskiest change — if the migration fails, data integrity is compromised.

**Independent Test**: Can be fully tested by executing the migration, then verifying that all existing supplier records are accessible from the new module, all product-supplier relationships are intact, all supplier custom fields still work, and no existing tests break.

**Acceptance Scenarios**:

1. **Given** existing supplier records in the system, **When** the migration is executed, **Then** all supplier data (name, contact info, tax identifiers, encrypted PII) is preserved without any data loss.
2. **Given** products linked to suppliers via foreign key, **When** the migration completes, **Then** all product-supplier relationships remain valid and queryable.
3. **Given** tenants with custom field definitions for suppliers, **When** the migration completes, **Then** supplier custom fields continue to validate and store data correctly.
4. **Given** the migration has been applied, **When** a user accesses suppliers through the purchases module endpoints, **Then** the full CRUD operations work identically to the previous inventory module endpoints.
5. **Given** the migration has been applied, **When** the full existing test suite is executed, **Then** zero new test failures occur (all regressions from the move are resolved).
6. **Given** multi-tenant supplier data, **When** querying suppliers after migration, **Then** tenant isolation is strictly maintained — each tenant sees only their own suppliers.

---

### User Story 2 - Purchase Order Lifecycle (Priority: P1)

A purchasing manager creates a purchase order to request goods from a supplier. The order specifies which products are needed, in what quantities, and at what unit price. The purchase order progresses through defined states: it starts as a draft (editable), then is confirmed (locked for receiving), and eventually marked as received (fully or partially). Each state transition enforces business rules — confirmed orders cannot be edited, and only confirmed orders can receive goods.

**Why this priority**: The purchase workflow is the core business capability of the COMPRAS module and is MVP-required per the project roadmap. Without purchase orders, the ERP cannot track procurement, which is fundamental for any retail or wholesale business.

**Independent Test**: Can be fully tested by creating a purchase order with line items, confirming it, and verifying state transitions and business rule enforcement at each stage. Delivers immediate procurement tracking value.

**Acceptance Scenarios**:

1. **Given** a valid supplier and products exist, **When** a user creates a purchase order in draft state with line items (product, quantity, unit price), **Then** the order is saved with a calculated total and is editable.
2. **Given** a draft purchase order, **When** the user confirms it, **Then** the order transitions to confirmed state and its line items become read-only.
3. **Given** a confirmed purchase order, **When** a user attempts to edit line items or add new ones, **Then** the system rejects the change with a clear error indicating the order is locked.
4. **Given** a draft purchase order, **When** a user attempts to record a goods receipt against it, **Then** the system rejects the action — only confirmed orders can receive goods.
5. **Given** a confirmed purchase order with 100 units ordered, **When** a goods receipt records 60 units received, **Then** the order transitions to a partial-received state.
6. **Given** a partial-received purchase order, **When** subsequent goods receipts bring the total received to 100 units, **Then** the order transitions to fully received state.
7. **Given** any purchase order, **When** queried by a different tenant's user, **Then** the system returns no results (tenant isolation enforced).
8. **Given** a purchase order, **When** the user views it, **Then** the response includes all line items with product details, quantities, unit prices, and line totals.

---

### User Story 3 - Goods Receipt and Stock Update (Priority: P1)

When goods arrive from a supplier, a warehouse operator records a goods receipt against an existing confirmed purchase order. The receipt specifies actual quantities received for each line item. Upon saving, the system automatically creates stock movements to increase inventory levels for the received products. This follows the same append-only ledger pattern used for sales-driven stock movements.

**Why this priority**: Goods receipt is the bridge between purchasing and inventory — it closes the procurement loop. Without it, purchase orders are just records with no operational impact on stock levels. The stock update must follow the existing immutable ledger pattern to maintain data integrity.

**Independent Test**: Can be fully tested by confirming a purchase order, recording a goods receipt with specific quantities, and verifying that corresponding stock movements are created and inventory levels are updated correctly.

**Acceptance Scenarios**:

1. **Given** a confirmed purchase order with 50 units of Product A, **When** the operator records a goods receipt for 50 units of Product A, **Then** a stock movement of type "purchase inbound" is created for 50 units, and the purchase order transitions to received state.
2. **Given** a confirmed purchase order with 100 units, **When** the operator records a goods receipt for 40 units, **Then** a stock movement is created for 40 units, the order shows 40 of 100 received, and the order transitions to partial-received state.
3. **Given** a goods receipt has been recorded, **When** the stock levels are queried, **Then** the received quantities are reflected in the current stock totals.
4. **Given** a goods receipt, **When** a user attempts to edit or delete it after creation, **Then** the system rejects the change — goods receipts are immutable (append-only ledger).
5. **Given** a purchase order that is already fully received, **When** a user attempts to record an additional goods receipt, **Then** the system rejects the action with a clear error.
6. **Given** a goods receipt is recorded, **When** viewing stock movement history, **Then** the movement includes a reference back to the originating purchase order for full traceability.

---

### User Story 4 - Purchase Order Custom Fields (Priority: P2)

Tenants can define custom fields on purchase orders, following the same customization framework used for products, customers, suppliers, and sale orders. This allows each tenant to capture procurement-specific data unique to their business (e.g., customs reference numbers, project codes, delivery terms) without requiring system-wide changes.

**Why this priority**: Custom fields are a core value proposition of the tenant customization framework (Feature 014). Extending them to purchase orders ensures consistency across all major business entities. Lower priority than the core workflow (US1-3) because purchase orders are functional without custom fields.

**Independent Test**: Can be fully tested by creating field definitions for purchase orders, then creating/updating a purchase order with custom data and verifying validation runs correctly.

**Acceptance Scenarios**:

1. **Given** a tenant has defined custom fields for purchase orders (e.g., `project_code` as text, `customs_ref` as text), **When** the user creates a purchase order with matching custom data, **Then** the order is saved with the custom data validated and stored.
2. **Given** a required custom field definition for purchase orders, **When** the user creates a purchase order without that field, **Then** the system returns a validation error identifying the missing field.
3. **Given** a tenant with NO custom field definitions for purchase orders, **When** the user creates a purchase order without custom data, **Then** the order is created successfully (custom fields are optional).
4. **Given** existing custom data on a purchase order, **When** the user updates with partial custom data, **Then** the system merges incoming keys with existing values (consistent with the product/customer/supplier/sale order merge behavior).

---

### User Story 5 - Reporting Module Infrastructure (Priority: P2)

The system provides a reporting module that serves as the foundation for future business intelligence capabilities. Administrators can define report configurations (specifying report type, parameters, and filters) and the system can store references to generated reports. This infrastructure establishes the data access layer that external BI tools can connect to for advanced analytics.

**Why this priority**: The reporting module is MVP-required per the roadmap, but full BI capabilities (embedded dashboards, custom report generators) depend on cloud deployment and all transactional modules being solid first. This story delivers only the infrastructure skeleton — models, basic management endpoints, and read-only data access — so the module exists and can be incrementally enhanced.

**Independent Test**: Can be fully tested by creating report definitions with various configurations, saving report references, and verifying the read-only data access layer returns correct cross-module data.

**Acceptance Scenarios**:

1. **Given** an authenticated user with reporting permissions, **When** they create a report definition specifying type (e.g., sales summary, stock levels, purchase history), parameters, and filters, **Then** the definition is saved and retrievable.
2. **Given** a report definition exists, **When** a user retrieves it, **Then** all configuration details (type, parameters, filters, output format) are returned.
3. **Given** a saved report reference, **When** a user retrieves it, **Then** execution metadata (creation date, status, file reference) is returned.
4. **Given** report definitions belong to different tenants, **When** each tenant queries their report definitions, **Then** each sees only their own (tenant isolation enforced).
5. **Given** the reporting data access layer, **When** an external BI tool connects to the read-only data views, **Then** it can query aggregated sales, stock, and purchase data scoped to the connecting tenant.
6. **Given** a user without reporting permissions, **When** they attempt to access reporting endpoints, **Then** the system returns an authorization error.

---

### User Story 6 - Permission Controls for New Modules (Priority: P2)

The role-based permission system is extended to include purchasing and reporting capabilities. Administrators can grant users specific permissions for the new modules: read, write, and admin for purchases; read and export for reports. These permissions integrate with the existing permission vocabulary and enforcement mechanisms.

**Why this priority**: Without permissions, the new modules are either fully open or fully closed to all users. Granular access control is essential for multi-user business environments where not everyone should create purchase orders or export reports.

**Independent Test**: Can be fully tested by creating roles with various permission combinations, assigning them to users, and verifying that access is correctly granted or denied for each module's endpoints.

**Acceptance Scenarios**:

1. **Given** a role with purchasing read permission, **When** the user views purchase orders, **Then** access is granted; **When** they attempt to create a purchase order, **Then** access is denied.
2. **Given** a role with purchasing write permission, **When** the user creates and confirms purchase orders, **Then** access is granted.
3. **Given** a role with reporting read permission, **When** the user views report definitions and saved reports, **Then** access is granted.
4. **Given** a role with reporting export permission, **When** the user triggers an export operation, **Then** access is granted.
5. **Given** a role with NO purchasing or reporting permissions, **When** the user attempts to access any purchasing or reporting endpoint, **Then** the system returns an authorization error.
6. **Given** the permission vocabulary, **When** an administrator views available permissions, **Then** purchasing permissions (read, write, admin) and reporting permissions (read, export) are listed alongside existing module permissions.

---

### User Story 7 - Seed Data for New Modules (Priority: P3)

The system provides sample data for the purchases and reporting modules to facilitate development, testing, and demonstration. Seed data includes sample suppliers (if not already seeded), purchase orders in various states, goods receipts, and report definitions. The seed command integrates with the existing unified seed workflow.

**Why this priority**: Seed data is a developer/tester convenience, not a user-facing feature. However, it significantly accelerates development velocity and enables meaningful demos. Lowest priority because the modules are functional without it.

**Independent Test**: Can be fully tested by running the seed command on a clean database and verifying that the expected sample data is created for all new entities.

**Acceptance Scenarios**:

1. **Given** a clean database with base tenant data, **When** the seed command for purchases is executed, **Then** sample purchase orders (in draft, confirmed, and received states), purchase order items, and goods receipts are created.
2. **Given** a clean database, **When** the seed command for reporting is executed, **Then** sample report definitions covering different report types (sales, stock, purchases) are created.
3. **Given** existing data in the database, **When** the seed command is run again, **Then** it is idempotent — no duplicate data is created.
4. **Given** the unified seed workflow, **When** the full seed command is executed, **Then** it includes the new purchases and reporting seed data in the correct order (after inventory and sales data, since purchase orders reference products and suppliers).

---

### Edge Cases

- **Supplier migration with concurrent access**: What happens if a user is editing a supplier record during the migration window? The migration must be atomic — either all supplier data moves or none does.
- **Purchase order with deleted products**: If a product referenced by a purchase order line item is soft-deleted, the line item must retain the product reference for historical accuracy.
- **Goods receipt exceeding ordered quantity**: The system rejects over-receipt in MVP — quantities received cannot exceed quantities ordered per line item. This can be relaxed in a future iteration if business needs require it.
- **Partial receipt followed by order cancellation**: If a purchase order is partially received and then needs to be cancelled, the already-received goods (and their stock movements) must remain — only the unreceived portion is cancelled.
- **Custom fields on purchase order in non-draft state**: Custom data follows the same editability rules as other PO fields — editable in draft, locked after confirmation.
- **Report definition with invalid filter references**: If a report definition references entities or fields that don't exist, the system validates at creation time, not at report generation time.
- **Tenant with purchasing module disabled**: If a tenant's module configuration has purchasing disabled, purchase-related endpoints return appropriate errors.

## Requirements *(mandatory)*

### Functional Requirements

**COMPRAS Module — Supplier Migration**

- **FR-001**: System MUST migrate the Supplier entity from the inventory module to the purchases module without any data loss.
- **FR-002**: System MUST preserve all existing foreign key relationships between products and suppliers after migration.
- **FR-003**: System MUST maintain supplier custom field definitions and stored custom data through the migration.
- **FR-004**: System MUST maintain encrypted PII fields (supplier contact information) through the migration with no re-encryption needed.
- **FR-005**: System MUST provide supplier CRUD operations through the purchases module endpoints after migration.

**COMPRAS Module — Purchase Order Workflow**

- **FR-006**: System MUST allow creation of purchase orders with a reference to a supplier, one or more line items (product, quantity, unit price), and a calculated total.
- **FR-007**: System MUST enforce a purchase order state machine: DRAFT → CONFIRMED → PARTIAL_RECEIVED → RECEIVED.
- **FR-008**: System MUST prevent editing of purchase order line items after the order is confirmed.
- **FR-009**: System MUST prevent goods receipt recording against orders that are not in confirmed or partial-received state.
- **FR-010**: System MUST automatically transition purchase order state based on cumulative received quantities vs. ordered quantities.
- **FR-011**: System MUST enforce tenant isolation on all purchase order data — users can only access purchase orders belonging to their tenant.

**COMPRAS Module — Goods Receipt**

- **FR-012**: System MUST allow recording of goods receipts against confirmed purchase orders, specifying actual received quantities per line item.
- **FR-013**: System MUST automatically create stock movements (type: purchase inbound) when a goods receipt is recorded.
- **FR-014**: System MUST enforce immutability on goods receipts — once created, they cannot be edited or deleted.
- **FR-015**: System MUST reject goods receipts where received quantity would exceed ordered quantity for any line item.
- **FR-016**: System MUST include a reference from stock movements back to the originating purchase order for traceability.

**COMPRAS Module — Custom Fields**

- **FR-017**: System MUST support custom field definitions for the purchase order entity type, following the same framework as products, customers, suppliers, and sale orders.
- **FR-018**: System MUST validate purchase order custom data against the tenant's field definitions on creation and update.
- **FR-019**: System MUST merge partial custom data updates with existing values (consistent with existing entity behavior).

**REPORTES Module — Infrastructure**

- **FR-020**: System MUST provide a report definition entity that stores report type, configurable parameters, filters, and output format preferences.
- **FR-021**: System MUST provide a saved report entity that stores a reference to a generated report (file path or key) and execution metadata.
- **FR-022**: System MUST provide an export job entity that tracks export format and status.
- **FR-023**: System MUST provide basic CRUD endpoints for report definitions and saved reports.
- **FR-024**: System MUST enforce tenant isolation on all reporting data.
- **FR-025**: System MUST provide a read-only data access service layer (Django QuerySet methods per R-006) that aggregates cross-module data (sales, stock, purchases) scoped by tenant. This service layer is consumed internally by future report generation logic and can be exposed via standard list endpoints for external BI tools.

**Permissions**

- **FR-026**: System MUST add purchasing permissions (read, write, admin) to the permission vocabulary.
- **FR-027**: System MUST add reporting permissions (read, export) to the permission vocabulary.
- **FR-028**: System MUST enforce purchasing and reporting permissions on all new module endpoints.

**Stock Movement Extension**

- **FR-029**: System MUST use the existing PURCHASE stock movement type for goods receipt operations (type already exists in MovementType enum per R-007).

**Seed Data**

- **FR-030**: System MUST provide seed data for the purchases module (sample purchase orders, items, goods receipts).
- **FR-031**: System MUST provide seed data for the reporting module (sample report definitions).
- **FR-032**: System MUST integrate new seed data with the existing unified seed workflow.

**Backward Compatibility**

- **FR-033**: System MUST ensure all existing tests continue to pass after the supplier migration (zero regressions).
- **FR-034**: System MUST perform a clean URL migration of supplier endpoints from `/api/v1/inventario/suppliers/` to `/api/v1/compras/suppliers/` (no redirect — there are no external consumers per R-003). All internal references and test imports MUST be updated.

### Key Entities

- **Supplier** (migrated): Represents a goods or services provider. Key attributes: business name, tax identifier (CUIT), contact information (encrypted PII), payment terms, custom data. Moves from inventory to purchases module.
- **PurchaseOrder**: Represents a request to buy goods from a supplier. Key attributes: supplier reference, order date, state (draft/confirmed/partial_received/received), line items, total amount, custom data. Tenant-scoped.
- **PurchaseOrderItem**: Represents a line item within a purchase order. Key attributes: product reference, ordered quantity, unit price, line total. Belongs to a purchase order.
- **GoodsReceipt**: Records actual goods received against a purchase order. Key attributes: purchase order reference, receipt date, received quantities per item, notes. Immutable after creation. Tenant-scoped.
- **ReportDefinition**: Defines a report configuration. Key attributes: report type (sales, stock, purchases, fiscal, accounting export), parameters, filters, output format. Tenant-scoped.
- **SavedReport**: Stores a reference to a generated report. Key attributes: report definition reference, file reference (path or key), execution status, execution metadata. Tenant-scoped.
- **ExportJob**: Tracks an export operation. Key attributes: saved report reference, export format (PDF, Excel, CSV), status, file path. Tenant-scoped.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The purchases module exists and is fully operational with supplier management, purchase order lifecycle, and goods receipt recording.
- **SC-002**: Supplier migration completes with zero data loss — all existing supplier records, relationships, custom fields, and encrypted data are intact and accessible through the purchases module.
- **SC-003**: All existing tests continue to pass after the supplier migration, with zero new test failures introduced.
- **SC-004**: Purchase order state machine correctly enforces all transitions and business rules, verified by at least 60 new tests covering creation, state transitions, validation, and tenant isolation.
- **SC-005**: Goods receipt automatically updates stock levels, with stock movement traceability back to the originating purchase order.
- **SC-006**: Custom fields work on purchase orders with the same validation, merge, and retrieval behavior as existing entities (products, customers, suppliers, sale orders).
- **SC-007**: The reporting module infrastructure exists with tenant-isolated models, basic management endpoints, and a read-only data access layer suitable for external BI tool connection.
- **SC-008**: Reporting module has at least 15 new tests covering model creation, CRUD operations, and tenant isolation.
- **SC-009**: Purchasing and reporting permissions are enforced on all new endpoints — unauthorized users receive clear access denied responses.
- **SC-010**: Seed data for both new modules is available and integrates with the existing unified seed workflow.
- **SC-011**: All new entities enforce tenant isolation — verified through dedicated cross-tenant access tests.
- **SC-012**: Goods receipts are immutable — attempts to modify or delete return clear rejection errors.
- **SC-013**: The system maintains or improves its current test coverage percentage after all changes.
- **SC-014**: All new REST endpoints are documented in the system's API specification.

### Assumptions

- The existing tenant customization framework (Feature 014) is stable and supports adding new entity types without structural changes.
- The existing stock movement ledger pattern supports adding new movement types without changing the core ledger logic.
- The supplier migration can be achieved through the system's standard migration tooling without requiring manual database operations.
- Over-receipt (receiving more than ordered) is rejected in MVP; this can be relaxed in a future iteration if business needs require it.
- The reporting module in this feature is strictly infrastructure — no report generation logic, no embedded BI dashboards, no scheduled reports. Those are future scope.
- Blueprint documentation updates resulting from these changes will be handled in a separate follow-up specification.
