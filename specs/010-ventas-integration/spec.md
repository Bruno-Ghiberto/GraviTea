# Feature Specification: Ventas Integration Module

**Feature Branch**: `010-ventas-integration`
**Created**: 2026-02-11
**Status**: Draft
**Input**: Instruction document `Docs/Temp-prompting/instruction-spec.md` — bridging isolated inventory and invoicing modules with atomic sale transactions.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Online Sale with Automatic Invoicing (Priority: P1)

A cashier at a branch creates a sale that simultaneously deducts stock from inventory and generates a fiscalized invoice with a valid authorization code. Today, inventory management and invoicing are completely disconnected — staff must manually track stock changes and separately issue invoices, leading to discrepancies and compliance risks.

**Why this priority**: This is the core value proposition. Without this, the ERP cannot function as an integrated system. Every retail operation depends on the sale-to-invoice-to-stock pipeline working atomically.

**Independent Test**: Can be fully tested by creating a sale with line items, verifying stock deduction, and confirming invoice authorization — delivers the fundamental integrated sale experience.

**Acceptance Scenarios**:

1. **Given** a branch with sufficient stock for all requested products, **When** a cashier creates a sale with one or more line items, **Then** the system deducts stock for each product, generates a fiscalized invoice with a valid authorization code, and returns the completed sale with the linked invoice.
2. **Given** a branch where one product has insufficient stock, **When** a cashier attempts to create a sale including that product, **Then** the system rejects the entire sale with a clear message identifying which product(s) lack sufficient stock, and no stock is deducted for any product.
3. **Given** a valid sale request, **When** the fiscal authority is unreachable during invoice authorization, **Then** the entire sale is cancelled — no stock is deducted, no partial records remain — and the cashier receives a clear error message.
4. **Given** a completed, fiscalized sale, **When** anyone attempts to modify the sale record, **Then** the system rejects the modification — fiscalized sales are immutable.

---

### User Story 2 - Offline Sale for POS Devices (Priority: P2)

A POS device operating without internet connectivity creates a draft sale that deducts stock immediately but defers invoice authorization until the device reconnects. This enables rural or connectivity-challenged locations to continue selling without interruption.

**Why this priority**: Offline-first is a core architectural requirement for the target market (small-to-medium businesses in areas with unreliable connectivity). Without this, the system is unusable for a significant portion of the user base.

**Independent Test**: Can be tested by creating a sale on a device without network access, verifying stock deduction occurs locally, and confirming the sale is flagged as pending authorization.

**Acceptance Scenarios**:

1. **Given** a POS device with no internet connectivity and sufficient local stock, **When** the operator creates a sale, **Then** the system deducts stock immediately, creates a draft invoice pending authorization, marks the sale as "pending fiscalization", and returns the completed sale to the operator.
2. **Given** an offline sale with pending fiscalization, **When** the device is still offline, **Then** the sale remains in "pending" status and the operator can continue creating new sales.
3. **Given** multiple offline sales created on a device, **When** the device reconnects, **Then** all pending sales are queued for fiscalization in the order they were created.

---

### User Story 3 - Sync and Fiscalize Pending Sales (Priority: P3)

When a POS device reconnects to the network, all pending sales are automatically submitted for fiscal authorization. Successfully authorized sales are updated with their authorization codes. Failed authorizations are retried on subsequent sync cycles.

**Why this priority**: Completes the offline sale lifecycle. Without this, offline sales would remain in limbo indefinitely, creating fiscal compliance gaps.

**Independent Test**: Can be tested by creating offline sales, simulating reconnection, and verifying that each pending sale receives fiscal authorization or is correctly queued for retry.

**Acceptance Scenarios**:

1. **Given** a device with 5 pending offline sales that reconnects to the network, **When** the sync process runs, **Then** each pending sale is submitted for fiscal authorization, and successfully authorized sales are updated to "fiscalized" status with their authorization codes.
2. **Given** a pending sale whose fiscal authorization fails (e.g., authority timeout), **When** the sync process encounters the failure, **Then** the sale remains in "pending" status, the error is logged, and the sale will be retried on the next sync cycle.
3. **Given** a pending sale where stock was adjusted while the device was offline (e.g., admin correction), **When** the sale is fiscalized during sync, **Then** the sale is still fiscalized (stock was already deducted at creation time), but if stock went negative due to the adjustment, the sale is flagged for administrative review.

---

### User Story 4 - Sale Cancellation via Credit Note (Priority: P4)

A branch manager cancels a fiscalized sale by issuing a credit note that references the original invoice and reverses the stock deductions. This handles returns and corrections while maintaining full fiscal compliance and audit trails.

**Why this priority**: Returns and corrections are essential for any retail operation, but this builds on top of the core sale flow (P1) and can be implemented after the primary path works.

**Independent Test**: Can be tested by fiscalizing a sale, then cancelling it, and verifying that a credit note is issued, stock is restored, and the sale is marked as cancelled.

**Acceptance Scenarios**:

1. **Given** a fiscalized sale with 3 line items, **When** a branch manager cancels the sale, **Then** the system creates a credit note referencing the original invoice, reverses stock for all 3 products (restoring the deducted quantities), and marks the sale as "cancelled".
2. **Given** a sale in "pending fiscalization" status, **When** someone attempts to cancel it, **Then** the system rejects the cancellation — only fiscalized sales can be cancelled via credit note.
3. **Given** a sale that has already been cancelled, **When** someone attempts to cancel it again, **Then** the system rejects the duplicate cancellation.

---

### User Story 5 - Invoicing Module Stabilization (Priority: P0 — Pre-Requisite)

Before any integration work begins, the existing invoicing module must be fully stabilized. There are 60 pre-existing test failures that must be resolved to ensure the invoicing foundation is reliable. Additionally, three deferred architectural issues must be addressed: service layer bypass in offline invoice endpoints, missing data isolation policies on child tables, and absent edge-case tests.

**Why this priority**: P0 because integration cannot safely build on an unstable foundation. The invoicing module has known issues that, if left unresolved, would propagate into the integrated sale flow.

**Independent Test**: Can be tested by running the full invoicing test suite and confirming all 297 tests pass with zero regressions.

**Acceptance Scenarios**:

1. **Given** the current invoicing module with 60 pre-existing test failures, **When** all root causes are resolved (validator signatures, mock mismatches, missing type codes, encoding issues, fixture problems), **Then** all 297 invoicing tests pass.
2. **Given** offline invoice endpoints that bypass the service layer, **When** they are refactored to use the service layer with proper transaction safety, **Then** offline invoice creation follows the same validated path as online invoices.
3. **Given** invoice child tables without independent data isolation policies, **When** policies are added, **Then** each child table enforces tenant isolation independently, consistent with the inventory module's patterns.

---

### User Story 6 - Cross-Module Tenant Isolation (Priority: P5)

Every table in the sales module enforces tenant data isolation at every layer. No tenant can see, modify, or infer data belonging to another tenant — this applies to sales, line items, and all related records.

**Why this priority**: Security is non-negotiable but implemented as a cross-cutting concern alongside the functional stories above.

**Independent Test**: Can be tested by creating sales under two different tenants and confirming that neither tenant can access the other's data through any endpoint or query path.

**Acceptance Scenarios**:

1. **Given** Tenant A with 10 sales and Tenant B with 5 sales, **When** Tenant A lists their sales, **Then** only Tenant A's 10 sales are returned — Tenant B's data is completely invisible.
2. **Given** a sale belonging to Tenant A, **When** Tenant B attempts to access it by ID (guessing or enumerating IDs), **Then** the system returns "not found" (not "forbidden") to prevent information leakage.
3. **Given** the sales and line items tables, **When** inspected at the data storage level, **Then** tenant isolation is enforced by the storage layer itself — not just by application logic — for every tenant-bound table.

---

### User Story 7 - Containerized Deployment Readiness (Priority: P6)

The full integrated stack (authentication, inventory, invoicing, and sales) runs correctly in a containerized environment with proper health checks, migration sequencing, and service dependencies.

**Why this priority**: Lowest priority because it's an operational concern that can be addressed after functional correctness is established.

**Independent Test**: Can be tested by starting the containerized environment and verifying that the sales endpoints respond correctly and all database schemas are applied.

**Acceptance Scenarios**:

1. **Given** a fresh containerized environment, **When** all services start up, **Then** database migrations run in the correct order (auth, inventory, invoicing, sales), all health checks pass, and the sales endpoints return valid responses.
2. **Given** the containerized stack running, **When** an operator creates a sale through the sales endpoint, **Then** the full integrated flow works identically to the non-containerized environment.

---

### Edge Cases

- What happens when two cashiers simultaneously attempt to purchase the last unit of a product? The system must handle concurrent stock deduction without overselling or deadlocking.
- What happens when a product's price changes between the time a line item is added and the sale is submitted? Prices are locked at the moment the line item is created — price changes after that point do not affect the sale.
- What happens when the fiscal authority returns an "observed" status (authorized with warnings) instead of a clean authorization? The sale is still considered fiscalized, and the warnings are recorded for review.
- What happens when a sale cancellation is attempted but the fiscal authority rejects the credit note? The cancellation fails, the sale remains fiscalized, and the error is surfaced to the branch manager.
- What happens when a POS device creates many offline sales and stock is adjusted by an administrator while the device is offline? The sales stand (stock was deducted at creation), but any resulting negative stock balances are flagged for administrative review.
- What happens when a line item has a discount applied? The discount (percentage or fixed amount) is applied per line, reducing the subtotal before tax calculation. The total line amount reflects the discounted price plus applicable taxes.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST create a sale record that atomically deducts stock and generates a fiscalized invoice in a single operation — if any step fails, all changes are rolled back.
- **FR-002**: The system MUST validate stock availability for every line item before committing a sale — insufficient stock for any single item rejects the entire sale.
- **FR-003**: The system MUST support offline sale creation where stock is deducted immediately but invoice authorization is deferred until network connectivity is restored.
- **FR-004**: The system MUST automatically fiscalize pending offline sales when the device reconnects, retrying failed authorizations on subsequent sync cycles.
- **FR-005**: The system MUST support sale cancellation by issuing a credit note that references the original invoice and reverses all stock deductions.
- **FR-006**: The system MUST enforce immutability on fiscalized sales — no modification or deletion is permitted after fiscal authorization.
- **FR-007**: The system MUST enforce tenant data isolation on all sales-related tables, preventing any cross-tenant data access.
- **FR-008**: The system MUST calculate line item totals as: subtotal = quantity * unit price - discount, tax amount = subtotal * tax rate, line total = subtotal + tax amount.
- **FR-009**: The system MUST ensure that the sale total always equals the sum of all line item totals — this constraint is enforced, not just calculated.
- **FR-010**: The system MUST prevent deletion of products that have associated sales (referential integrity).
- **FR-011**: The system MUST track payment method on each sale (cash, card, transfer, or other) for reporting and reconciliation purposes.
- **FR-012**: The system MUST support the following sale lifecycle statuses: Draft, Pending Fiscalization, Fiscalized, Cancelled — transitions are strictly ordered and irreversible.
- **FR-013**: The system MUST resolve all 60 pre-existing invoicing test failures before integration work begins, achieving 297/297 test pass rate.
- **FR-014**: The system MUST add independent data isolation policies to invoicing child tables (tax breakdown, additional taxes, associated receipts) for consistency with inventory patterns.
- **FR-015**: The system MUST refactor offline invoicing endpoints to use the service layer with transaction safety, eliminating direct database manipulation.
- **FR-016**: The system MUST support both percentage-based and fixed-amount discounts per line item, applied before tax calculation.
- **FR-017**: The system MUST record who created each sale (audit trail) beyond simple timestamps.
- **FR-018**: The system MUST support the containerized deployment of the full integrated stack with correct migration ordering and health checks.
- **FR-019**: The system MUST handle concurrent sale creation gracefully — two simultaneous sales for the last unit of stock must result in exactly one success and one rejection, with no overselling.
- **FR-020**: The system MUST integrate pending sales into the existing offline sync mechanism, supporting serialization of pending sales on push and fiscalization on pull.

### Key Entities

- **Sale**: A business transaction representing the exchange of products for payment at a specific branch. Attributes: branch, customer identification, customer tax status, date, status (Draft/Pending/Fiscalized/Cancelled), payment method, linked invoice (after fiscalization), total amount, discount information, notes. Immutable after fiscalization. Belongs to exactly one tenant.
- **Sale Line Item**: An individual product within a sale. Attributes: linked sale, linked product, quantity, unit price, discount (percentage or fixed), subtotal, tax rate, tax amount, line total. Constrained so totals are mathematically consistent. Cannot exist without a parent sale. Products referenced by line items cannot be deleted.
- **Invoice** (existing): The fiscal document generated by the invoicing module. Linked 1:1 with a fiscalized sale. Contains the fiscal authorization code.
- **Stock Movement** (existing): An immutable ledger entry recording inventory changes. Sale creation generates "sale" type movements; cancellation generates "adjustment" type reversal movements.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Cashiers can complete an online sale (stock deduction + invoice authorization) in under 5 seconds from submission, including fiscal authority response time.
- **SC-002**: POS devices can create offline sales in under 1 second, with stock deducted immediately and no user-perceptible delay.
- **SC-003**: When a POS device reconnects, 95% of pending sales are successfully fiscalized on the first sync attempt.
- **SC-004**: All 297 invoicing module tests pass with zero regressions after stabilization work.
- **SC-005**: Sales module achieves greater than 80% test coverage across all new functionality.
- **SC-006**: No tenant can access another tenant's sale data through any endpoint or query path — verified by dedicated security tests.
- **SC-007**: Sale totals are always mathematically consistent with line item totals — verified by constraint enforcement, not just application logic.
- **SC-008**: Failed sale operations leave zero residual state — no orphaned stock movements, no partial invoices, no dangling line items.
- **SC-009**: The containerized stack starts up and passes all health checks within 60 seconds of initialization.
- **SC-010**: Sale cancellation (credit note + stock reversal) completes within 5 seconds.

## Assumptions

- **A-001**: Prices are locked at the moment a line item is created. If a product's price changes between line item creation and sale submission, the original price at creation time is used.
- **A-002**: Payment method is tracked at the sale level as a simple categorization (cash, card, transfer, other). Payment processing integration is out of scope for this feature.
- **A-003**: Discount support includes both percentage-based and fixed-amount discounts per line item. Volume discounts, promotional campaigns, and coupon systems are out of scope.
- **A-004**: Audit trail includes the identity of the user who created and (where applicable) cancelled each sale, beyond automatic timestamps.
- **A-005**: The offline sale flow uses the standard deferred authorization model only (no authorization code until sync). CAEA (pre-authorized offline invoicing) is explicitly out of scope for this feature — it may be added in a future iteration once the deferred model is proven stable.
- **A-006**: The existing sync module's pending operation mechanism is sufficient to handle sale synchronization without major architectural changes.
- **A-007**: Stock that goes negative due to offline adjustments is flagged for administrative review but does not block the sale from being fiscalized — the principle is "the sale happened, deal with the stock discrepancy separately".
- **A-008**: Concurrent stock access uses a strict locking strategy to prevent overselling — the system locks stock records during the sale transaction rather than detecting conflicts after the fact. This favors correctness (no overselling) over throughput, which is appropriate for retail point-of-sale where stock accuracy matters more than high concurrency.

## Dependencies

- **DEP-001**: Invoicing module (facturacion) must be stabilized (297/297 tests passing) before integration work begins.
- **DEP-002**: Inventory module must provide a reliable stock availability check and stock deduction mechanism.
- **DEP-003**: Authentication module must provide tenant context for all sale operations.
- **DEP-004**: Sync module must support extensibility for new pending operation types.

## Scope Boundaries

**In scope**:
- Atomic sale creation (stock + invoice in one operation)
- Offline sale creation with deferred fiscalization
- Sale cancellation via credit note with stock reversal
- Line item discount support (percentage and fixed amount)
- Payment method tracking (categorization only)
- Tenant isolation for all new tables
- Invoicing module stabilization (60 test failures + 3 deferred items)
- Containerized deployment of the integrated stack

**Out of scope**:
- Payment processing (gateway integration, transaction management)
- Partial returns (returning individual line items from a sale)
- Multi-currency support beyond the existing invoicing module's currency handling
- Reporting and analytics dashboards for sales data
- Customer management (CRM-style customer records)
- Promotional campaigns, coupons, or volume discount engines
- Point-of-sale hardware integration (receipt printers, barcode scanners)
