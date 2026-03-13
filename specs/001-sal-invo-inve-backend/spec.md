# Feature Specification: Integrated Sales-Invoicing-Inventory Backend System

**Feature Branch**: `001-sal-invo-inve-backend`
**Created**: 2026-02-12
**Status**: Draft
**Input**: Integrated Sales-Invoicing-Inventory Backend System with ARCA Electronic Invoicing

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Complete Sale with Electronic Invoice Authorization (Priority: P1)

A sales representative creates a sale order, confirms it to reserve inventory, and obtains tax authority authorization (CAE) to legally invoice the customer - all within a single transaction flow.

**Why this priority**: This is the core business transaction that generates revenue and ensures fiscal compliance. Without this, the ERP system cannot legally process sales in Argentina's regulated environment.

**Independent Test**: Can be fully tested by creating a sale order with valid customer and products, confirming it, and receiving a CAE number from the tax authority, demonstrating the complete revenue-to-compliance workflow.

**Acceptance Scenarios**:

1. **Given** a confirmed sale order with available stock, **When** the invoice is submitted to ARCA for authorization, **Then** the system receives a CAE (Electronic Authorization Code) and marks the sale as invoiced with stock committed
2. **Given** a sale order with products in stock, **When** the user confirms the sale, **Then** inventory is reserved and an invoice draft is created automatically
3. **Given** an authorized invoice with CAE, **When** the user views the invoice, **Then** a fiscal QR code is displayed for customer verification

---

### User Story 2 - Recover from Authorization Rejection (Priority: P1)

When the tax authority rejects an invoice authorization request due to data errors, the system automatically releases reserved inventory and allows the user to correct and retry without losing the sale.

**Why this priority**: Authorization rejections are common (incorrect tax IDs, invalid amounts, missing data) and must be handled gracefully to prevent inventory lockup and lost sales.

**Independent Test**: Can be tested by submitting an invoice with intentionally invalid data (wrong customer tax ID format), verifying stock is released, correcting the data, and successfully reauthorizing.

**Acceptance Scenarios**:

1. **Given** an invoice rejected by ARCA, **When** the system processes the rejection, **Then** reserved inventory is released and the sale returns to confirmed status for editing
2. **Given** a rejected invoice with error details, **When** the user corrects the invalid data, **Then** the system retries authorization with the same invoice number (not incrementing)
3. **Given** multiple authorization attempts, **When** the system logs all attempts, **Then** a complete audit trail shows all status transitions with timestamps and reasons

---

### User Story 3 - Prevent Stock Overselling (Priority: P1)

When multiple users attempt to confirm sales simultaneously for the same product, the system prevents overselling by checking actual available stock under database-level locks.

**Why this priority**: Stock accuracy is critical for customer satisfaction and prevents accepting orders that cannot be fulfilled. Concurrent access control prevents race conditions.

**Independent Test**: Can be tested by simulating two concurrent sale confirmations for a product with limited stock, verifying only one succeeds and the other receives a clear "insufficient stock" message.

**Acceptance Scenarios**:

1. **Given** two concurrent sale confirmations for the same product, **When** both attempt to reserve stock, **Then** only one succeeds and the other receives an insufficient stock error
2. **Given** a sale confirmation request, **When** stock availability is checked, **Then** the system uses database locks to prevent time-of-check-time-of-use (TOCTOU) race conditions
3. **Given** insufficient stock for a sale, **When** confirmation is attempted, **Then** no stock reservation occurs and the sale remains in draft status

---

### User Story 4 - Manage Customer Tax Status (Priority: P2)

Business administrators register customers with their tax authority status (tax registered, tax exempt, final consumer) to ensure invoices use the correct type and format required by law.

**Why this priority**: Argentine tax law requires different invoice types based on customer tax status. Incorrect types result in rejected invoices and compliance issues.

**Independent Test**: Can be tested by creating customers with different tax statuses and verifying that sales automatically generate the correct invoice type without manual selection.

**Acceptance Scenarios**:

1. **Given** a customer registered as "Tax Registered", **When** a sale is created for them, **Then** the system automatically generates a Type A invoice format
2. **Given** a customer registered as "Final Consumer", **When** a sale is created for them, **Then** the system automatically generates a Type B invoice format
3. **Given** a customer's tax ID number (CUIT), **When** entered, **Then** the system validates the format and check digit according to Argentine tax authority rules

---

### User Story 5 - Recover from Network Timeouts (Priority: P2)

When network issues interrupt communication with the tax authority during authorization, the system automatically checks if authorization was granted and reconciles state accordingly.

**Why this priority**: Network timeouts are inevitable in production systems. Without recovery logic, interrupted authorizations create orphaned stock reservations and unclear invoice states.

**Independent Test**: Can be tested by simulating a network timeout during authorization, verifying the system queries the tax authority for the authorization status, and correctly reconciles based on whether CAE was granted.

**Acceptance Scenarios**:

1. **Given** a network timeout during authorization submission, **When** the system recovers, **Then** it queries the tax authority to check if CAE was granted before the timeout
2. **Given** a timeout where CAE was actually granted, **When** status is reconciled, **Then** the invoice is marked authorized with the CAE and stock is committed
3. **Given** a timeout where CAE was not granted, **When** status is reconciled, **Then** the system safely retries with the same invoice number

---

### User Story 6 - Track Sale-to-Invoice-to-Stock Audit Trail (Priority: P3)

Auditors and managers can trace any stock movement back to its originating sale order and authorized invoice for complete transaction accountability.

**Why this priority**: Audit trails are required for tax compliance and financial reporting. Lower priority because the system functions without explicit audit views initially.

**Independent Test**: Can be tested by completing a sale, confirming the invoice, and verifying that the stock movement record contains references to both the sale order ID and invoice CAE.

**Acceptance Scenarios**:

1. **Given** a completed sale with authorized invoice, **When** viewing stock movements, **Then** each movement shows the originating sale order ID and invoice CAE
2. **Given** an invoice with CAE, **When** viewing invoice details, **Then** the linked sale order and all related stock movements are accessible
3. **Given** a sale order, **When** viewing order history, **Then** all status transitions (draft → confirmed → invoiced) are logged with timestamps

---

### Edge Cases

- What happens when ARCA's authorization service is completely unavailable (prolonged outage)?
  - Sales can be confirmed and inventory reserved, but invoicing waits for service restoration
  - System queues authorization requests for retry with exponential backoff
  - Stock remains in "reserved" state with clear status indicators

- How does the system handle duplicate authorization requests for the same invoice?
  - System checks if invoice already has CAE before submitting to ARCA
  - Idempotency ensures same invoice number is never submitted twice if already authorized
  - If authorization in progress, subsequent requests wait for completion

- What happens when a customer's tax status changes after sale creation but before invoicing?
  - System validates customer tax status at invoice creation time (not just sale creation)
  - If status changed and produces a different invoice type, the API returns a validation error requiring the client to re-confirm with the updated type
  - Historical sales preserve the tax status at time of transaction

- How does system handle fractional quantities in sales (e.g., 2.5 units)?
  - All quantity fields support 4 decimal places for precision (DECIMAL(16,4), matching existing inventario patterns)
  - Stock movements track fractional quantities accurately
  - Monetary amounts use 3 decimal places (DECIMAL(17,3)) for calculation accuracy; display rounds to 2 decimals

- What happens when multi-tenant certificate credentials expire?
  - System validates certificate expiration before authorization attempts
  - Clear error messages indicate which tenant's certificate needs renewal
  - Authorization fails with actionable error, not cryptic technical message

- How does the system handle sales spanning multiple tax years?
  - Sale order creation date determines tax period
  - Invoice inherits tax period from sale order, not authorization date
  - Year-end cutoffs are handled by invoice numbering per point-of-sale sequence

## Requirements *(mandatory)*

### Functional Requirements

#### Customer Management
- **FR-001**: System MUST store customer tax authority identification number (CUIT) in 11-digit format with validation
- **FR-002**: System MUST classify customers by tax status (Tax Registered, Tax Exempt, Final Consumer, Simplified Tax Regime)
- **FR-003**: System MUST validate customer tax IDs using check digit algorithm before allowing sales
- **FR-004**: System MUST prevent creating sales for customers without valid tax status classification

#### Sales Order Processing
- **FR-005**: System MUST support sales order lifecycle states: Draft, Confirmed, Invoiced
- **FR-006**: System MUST allow adding multiple line items to a sale order with product, quantity, and unit price
- **FR-007**: System MUST calculate order totals automatically from line items
- **FR-008**: System MUST validate stock availability before allowing order confirmation
- **FR-009**: System MUST prevent editing line items after order confirmation
- **FR-010**: System MUST link each sale order to a single branch/location

#### Inventory Reservation
- **FR-011**: System MUST create stock movement records with "reserved" status when sale is confirmed
- **FR-012**: System MUST use database-level locks to prevent concurrent stock depletion race conditions
- **FR-013**: System MUST calculate available stock as: physical stock minus reserved stock
- **FR-014**: System MUST transition reserved stock to "committed" status only after invoice authorization
- **FR-015**: System MUST release (cancel) reserved stock if invoice authorization is rejected
- **FR-016**: System MUST link stock movements to originating sale order for traceability

#### Invoice Generation
- **FR-017**: System MUST automatically create invoice draft when sale order is confirmed
- **FR-018**: System MUST determine invoice type (A/B/C) based on customer tax status
- **FR-019**: System MUST query tax authority for next valid invoice number before creation
- **FR-020**: System MUST populate invoice amounts from sale order line items
- **FR-021**: System MUST calculate tax (IVA) breakdown based on invoice type and line items
- **FR-022**: System MUST prevent creating multiple invoices for the same sale order

#### Tax Authority Authorization (ARCA)
- **FR-023**: System MUST authenticate with tax authority using tenant-specific digital certificates
- **FR-024**: System MUST cache authentication tokens per tenant with 11-hour validity
- **FR-025**: System MUST submit invoices to tax authority for authorization with all required fiscal data
- **FR-026**: System MUST handle three authorization result types: Approved (CAE granted), Approved with Warnings (CAE granted), Rejected (no CAE)
- **FR-027**: System MUST store Electronic Authorization Code (CAE) when granted
- **FR-028**: System MUST store authorization errors and warnings for user review
- **FR-029**: System MUST use strictly monotonic invoice numbering per point-of-sale and invoice type
- **FR-030**: System MUST generate fiscal QR code containing invoice and CAE data for customer verification

#### Error Recovery
- **FR-031**: *(See FR-015)* System MUST automatically release reserved stock when invoice authorization is rejected
- **FR-032**: System MUST revert sale order to confirmed status when authorization fails (allowing retry)
- **FR-033**: System MUST allow retrying authorization with same invoice number after rejection
- **FR-034**: System MUST detect network timeouts and query tax authority for authorization status
- **FR-035**: System MUST reconcile invoice state after timeout based on tax authority confirmation

#### Transaction Integrity
- **FR-036**: System MUST ensure tenant isolation: all customer, sale, invoice, and stock records belong to same tenant
- **FR-037**: System MUST validate cross-entity tenant references before saving (prevent IDOR vulnerabilities)
- **FR-038**: System MUST use atomic database transactions for: (1) sale confirmation + stock reservation, (2) invoice authorization + stock commitment
- **FR-039**: System MUST log all state transitions with timestamp, user, and reason

#### Multi-Tenant Certificate Management
- **FR-040**: System MUST store digital certificates per tenant for tax authority authentication
- **FR-041**: System MUST encrypt certificate private keys at rest
- **FR-042**: System MUST support both testing and production tax authority environments per tenant
- **FR-043**: System MUST prevent authentication token reuse across tenants

### Key Entities

- **Customer**: Represents business clients with tax identification (CUIT), name, address, and tax status classification (Tax Registered/Exempt/Final Consumer/Simplified). Determines invoice type and format requirements.

- **Sale Order**: Represents a pending or completed sale transaction with customer reference, line items, total amount, status (Draft/Confirmed/Invoiced), and linked invoice. Contains multiple sale order items.

- **Sale Order Item**: Individual line in a sale order specifying product, quantity, unit price, and calculated subtotal. Locked after sale confirmation.

- **Invoice (Comprobante)**: Legal fiscal document submitted to tax authority for authorization, containing customer data, line item totals, tax breakdown, invoice type (A/B/C), status (Draft/Validating/Authorized/Rejected/Observed), CAE when granted, and link to originating sale order.

- **Stock Movement**: Immutable ledger entry recording inventory changes with product, quantity (negative for sales), movement type, status (Reserved/Committed/Cancelled), reference to sale order, and timestamp. Cannot be updated or deleted once created.

- **Point of Sale (Punto de Venta)**: Tax authority registered sales terminal with unique number per branch, used for invoice numbering sequence and authorization.

- **Tax Authority Credential (ARCACredential)**: Tenant-specific digital certificate for authenticating with tax authority, including encrypted private key, CUIT (company tax ID), and environment (testing/production).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can complete a sale from creation to authorized invoice in under 3 minutes for standard transactions
- **SC-002**: System successfully authorizes 95% of invoices on first attempt (remaining 5% are legitimate data errors)
- **SC-003**: Zero stock discrepancies between reserved and committed inventory (100% reconciliation)
- **SC-004**: System handles 50 concurrent sale confirmations without stock overselling or deadlocks
- **SC-005**: Tax authority authorization requests complete within 10 seconds in 90% of cases
- **SC-006**: 100% of rejected invoices automatically release reserved stock within 1 second
- **SC-007**: Network timeout recovery successfully reconciles invoice state in 100% of timeout scenarios
- **SC-008**: Complete audit trail exists for 100% of transactions (sale → invoice → stock movement linkage)
- **SC-009**: Zero cross-tenant data leakage (100% isolation between tenants)
- **SC-010**: Invoice numbering maintains strict monotonic sequence with zero gaps or duplicates
- **SC-011**: System supports at least 10,000 sales orders per tenant per month without performance degradation
- **SC-012**: Users receive clear, actionable error messages in 100% of authorization rejection cases

## Assumptions

1. **Tax Authority Availability**: ARCA's authorization service is available 99% of the time during business hours (8am-8pm local time)
2. **Network Reliability**: Internal network latency to tax authority servers is under 200ms in normal conditions
3. **Certificate Management**: Tenants have obtained and provided valid digital certificates from tax authority before going live
4. **Single Currency**: All sales are in Argentine Pesos (PES); multi-currency support is out of scope
5. **Single Branch Sales**: Each sale order pulls inventory from a single branch; multi-branch fulfillment is out of scope
6. **No Partial Invoicing**: Each sale order generates exactly one invoice; partial invoicing is out of scope
7. **Tax Rates**: IVA (value-added tax) rates are configured externally and provided to the system; rate management is out of scope
8. **Customer Pre-Registration**: Customers are registered in the system before sales creation; point-of-sale customer registration is out of scope
9. **Product Catalog**: Product data (including prices) is maintained externally; product master data management is out of scope
10. **Authentication**: Users are authenticated via existing auth system; user management is out of scope

## Dependencies

### External Systems
- **ARCA (Tax Authority)**: Provides WSAA authentication service and WSFEv1 invoice authorization service
- **Redis**: Required for caching authentication tokens with tenant isolation
- **PostgreSQL 18.1+**: Required for Row Level Security (RLS) multi-tenant isolation

### Existing Modules
- **Inventory Module** (`apps/inventario/`): Provides Product, StockMovement, BranchStock models and stock calculation logic
- **Invoice Module** (`apps/facturacion/`): Provides Comprobante, ARCA clients (WSAA/WSFEv1), certificate management (334 passing tests)
- **Auth Module** (`apps/auth/`): Provides JWT authentication, tenant context middleware, user session management
- **Core Module** (`apps/core/`): Provides TenantBoundModel, multi-tenant managers, encryption utilities

### Technical Dependencies
- **WSAA Protocol**: SOAP-based authentication with CMS/PKCS#7 signed requests
- **WSFEv1 Protocol**: SOAP-based invoice authorization with structured XML requests/responses
- **Digital Certificates**: X.509 certificates with RSA 2048-bit keys for signing authentication requests

## Constraints

### Business Constraints
- **Argentine Tax Law**: All invoices must comply with ARCA regulations for electronic invoicing (RG 4291/2018)
- **Invoice Types**: System supports only Type A (Tax Registered), Type B (Final Consumer), and Type C (Exempt/Simplified) invoices
- **CAE Validity**: Electronic authorization codes are valid for specific periods (typically 10 days to 6 months depending on invoice type)
- **Audit Requirements**: All fiscal transactions must maintain immutable audit trails for 10 years

### Technical Constraints
- **Amount Precision**: Financial amounts stored with 3 decimal places (`DECIMAL(17,3)`) for calculation accuracy
- **Invoice Numbering**: Strictly sequential per (Point-of-Sale, Invoice Type) combination with no gaps allowed
- **Immutability**: Authorized invoices and committed stock movements cannot be modified or deleted
- **Multi-Tenant Isolation**: Defense-in-depth strategy with application-level filtering, database RLS policies, and IDOR validation
- **Certificate Format**: Digital certificates must be in PEM format with separate private key files
- **Token Lifetime**: Authentication tokens valid for ~12 hours with 11-hour cache TTL (1 hour safety margin)

### Scope Constraints
- **No Credit Notes**: Credit notes (Type NC) and debit notes (Type ND) are deferred to future phase
- **No CAEA**: Batch authorization for offline scenarios not included in this phase
- **No Export Invoices**: Type E (export) invoices not supported
- **No Multi-Currency**: All transactions in Argentine Pesos only
- **No Partial Invoicing**: One sale order generates exactly one invoice
- **No Returns/Refunds**: Return processing and refund workflows out of scope
- **Backend Only**: No frontend UI implementation in this feature

## Open Questions

None - all critical decisions have been made based on existing project standards and Argentine tax authority requirements.
