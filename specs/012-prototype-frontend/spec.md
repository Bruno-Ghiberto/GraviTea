# Feature Specification: Prototype Frontend for Backend API Testing

**Feature Branch**: `012-prototype-frontend`
**Created**: 2026-02-17
**Status**: Draft
**Input**: Developer-only prototype frontend to interact with all 62 GRAVITEA-ERP backend API endpoints across 6 modules (auth, health, inventario, ventas, facturacion, sync). Ultra-minimal testing harness — not a production UI.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Developer Login and Authentication (Priority: P1)

A developer opens the prototype, enters their email and password, and receives a valid JWT. After login, they can see their decoded token claims (tenant, user, expiration), refresh the token, change their password, and log out. The auth page also provides admin management for users, branches, and roles. All other pages require authentication.

**Why this priority**: Without authentication, no other module can be tested — every endpoint requires a valid JWT with tenant context.

**Independent Test**: Can be fully tested by logging in with a seeded user account and verifying token claims are displayed, then refreshing and logging out. Delivers: validated auth flow and session management.

**Acceptance Scenarios**:

1. **Given** the developer is not logged in, **When** they open any page, **Then** they are redirected to the login screen.
2. **Given** the developer is on the login screen, **When** they enter valid credentials, **Then** they receive tokens and see their decoded JWT claims (tenant_id, user_id, exp).
3. **Given** the developer is logged in, **When** they click refresh, **Then** the access token is renewed without re-entering credentials.
4. **Given** the developer is logged in, **When** they click logout, **Then** the refresh token is invalidated, tokens are cleared, and they are redirected to login.
5. **Given** the developer is logged in, **When** they view their profile, **Then** they see their user details (email, name, roles, branch).
6. **Given** the developer is logged in, **When** they submit a change password form, **Then** the password is updated and a success confirmation is shown.
7. **Given** the developer enters wrong credentials, **When** they submit login, **Then** the backend error message is displayed clearly.
8. **Given** the developer is on the auth page, **When** they view the users section, **Then** they see a list of users with create, edit, and delete actions.
9. **Given** the developer is on the auth page, **When** they view branches, **Then** they see a list of tenant branches with detail view.
10. **Given** the developer is on the auth page, **When** they view roles, **Then** they see a list of roles with create, edit, and delete actions.

---

### User Story 2 - Health Check Dashboard (Priority: P1)

A developer navigates to the health page to verify the backend system is running. They see a status indicator (pass/fail), the response time, and can view the raw JSON response with database, cache, and system details.

**Why this priority**: Health check is the simplest validation that the backend is reachable and functional — a prerequisite for all other testing.

**Independent Test**: Can be tested by loading the health page and verifying the status badge and response time display. Delivers: backend connectivity confirmation.

**Acceptance Scenarios**:

1. **Given** the developer navigates to the health page, **When** the page loads, **Then** the health endpoint is called and a green/red status badge is displayed.
2. **Given** the health check succeeds, **When** the developer expands the details, **Then** they see the raw JSON response including database and cache status.
3. **Given** the developer clicks the refresh button, **When** the call completes, **Then** the status and response time are updated.
4. **Given** the backend is unreachable, **When** the health check fails, **Then** a red badge and the error details are displayed.

---

### User Story 3 - Inventory Management (Priority: P2)

A developer manages the full inventory module: products (CRUD, search, stock levels), categories (CRUD, tree view), suppliers (CRUD, search), stock movements (create-only, immutable), price lists (CRUD, set default), and read-only price/cost history.

**Why this priority**: Inventario is the largest module (19 endpoints) and the data foundation for sales and invoicing. Testing it validates the core CRUD patterns used across the system.

**Independent Test**: Can be tested by creating a product, adding a stock movement, creating a price list, and verifying all lists display correctly. Delivers: validated inventory CRUD and immutable ledger behavior.

**Acceptance Scenarios**:

1. **Given** the developer is on the inventory page, **When** they create a new product, **Then** the product appears in the product list.
2. **Given** a product exists, **When** the developer views its stock, **Then** the current stock level is displayed.
3. **Given** a product exists, **When** the developer searches for it, **Then** matching results are shown.
4. **Given** the developer creates a stock movement, **When** it is saved, **Then** it appears in the movement list and cannot be edited or deleted.
5. **Given** categories exist, **When** the developer views the category tree, **Then** the hierarchical structure is displayed.
6. **Given** the developer creates a price list, **When** they mark it as default, **Then** it becomes the default price list.
7. **Given** price or cost changes have occurred, **When** the developer views history, **Then** the read-only history entries are displayed.
8. **Given** the developer submits invalid data, **When** the backend returns validation errors, **Then** the specific field errors are displayed on the form.

---

### User Story 4 - Sales Operations (Priority: P2)

A developer manages customers (CRUD) and sale orders (CRUD with nested items). They can transition orders through status states (confirm, authorize) and view linked invoices.

**Why this priority**: Sales is the primary business workflow and connects to invoicing. Testing order lifecycle validates the state machine and cross-module linking.

**Independent Test**: Can be tested by creating a customer, creating an order with items, confirming it, and verifying status changes. Delivers: validated sales lifecycle and nested resource management.

**Acceptance Scenarios**:

1. **Given** the developer is on the sales page, **When** they create a customer, **Then** the customer appears in the customer list.
2. **Given** a customer exists, **When** the developer creates a sale order, **Then** the order appears with a status badge.
3. **Given** an order exists, **When** the developer adds items to it, **Then** the items appear nested within the order detail.
4. **Given** an order is in draft status, **When** the developer clicks "Confirm", **Then** the order status changes to confirmed.
5. **Given** an order is confirmed, **When** the developer clicks "Authorize", **Then** the order status changes to authorized.
6. **Given** an order has a linked invoice, **When** the developer clicks the invoice link, **Then** the linked invoice data is displayed.

---

### User Story 5 - Electronic Invoicing (ARCA) (Priority: P3)

A developer manages ARCA credentials, puntos de venta, comprobantes (invoices), and CAEAs. They can emit comprobantes, request CAE authorization, view fiscal QR codes, request CAEAs, and report periods without movements.

**Why this priority**: Facturacion depends on ARCA (Argentina's tax authority) connectivity. While the workflow is critical, it requires real certificates to fully test, making it lower priority for initial prototype validation.

**Independent Test**: Can be tested by creating credentials and a punto de venta, creating a comprobante via the emit form, and attempting CAE authorization (which may fail without real ARCA certificates — the error display validates error handling). Delivers: validated invoicing forms and ARCA error display.

**Acceptance Scenarios**:

1. **Given** the developer is on the facturacion page, **When** they create ARCA credentials, **Then** the credentials appear in the list.
2. **Given** credentials exist, **When** the developer creates a punto de venta, **Then** it appears in the puntos de venta list.
3. **Given** a punto de venta exists, **When** the developer fills the emit comprobante form and submits, **Then** the comprobante is created and listed.
4. **Given** a comprobante exists, **When** the developer clicks "Authorize", **Then** CAE authorization is attempted and the result (success or ARCA error) is displayed.
5. **Given** an authorized comprobante exists, **When** the developer views the QR code, **Then** the fiscal QR data is displayed.
6. **Given** the developer requests a new CAEA, **When** the request completes, **Then** the CAEA appears in the list with its status.
7. **Given** a CAEA exists for a period, **When** the developer reports "Sin Movimiento", **Then** the period is marked as having no movements.
8. **Given** ARCA returns an error, **When** the response is received, **Then** the error code and message are displayed clearly.

---

### User Story 6 - Sync Operations (Priority: P3)

A developer manages sync sessions, triggers push/pull operations, and checks device sync status. Raw payloads are visible for inspection.

**Why this priority**: Sync is a specialized module for offline-first devices. It's important for completeness but less frequently tested than core CRUD modules.

**Independent Test**: Can be tested by creating a sync session, triggering push and pull, and checking device status. Delivers: validated sync lifecycle and payload inspection.

**Acceptance Scenarios**:

1. **Given** the developer is on the sync page, **When** they create a sync session, **Then** the session appears in the list.
2. **Given** a session exists, **When** the developer triggers a push, **Then** the request and response payloads are displayed.
3. **Given** a session exists, **When** the developer triggers a pull, **Then** the response payload is displayed.
4. **Given** the developer enters a device ID, **When** they check status, **Then** the sync status for that device is displayed.
5. **Given** a session exists, **When** the developer closes (deletes) it, **Then** it is removed from the list.
6. **Given** any API call is made, **When** the developer toggles "Raw JSON", **Then** the full request/response payload is visible.

---

### Edge Cases

- What happens when the JWT access token expires mid-session? The system should automatically attempt a token refresh and retry the failed request; if refresh also fails, redirect to login.
- What happens when the backend returns a 500 error? A generic error boundary should catch it and display the raw error response.
- What happens when a developer tries to delete an authorized comprobante? The backend rejects it — the error should be displayed, not a client-side crash.
- What happens when the developer creates a stock movement with a negative quantity that would cause negative stock? The backend validation error should be shown.
- What happens when the network connection drops during a sync push? The error response (or timeout) should be displayed clearly.
- What happens when the developer navigates to a page with an expired token and no refresh token? They should be redirected to login immediately.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST authenticate developers via email and password, obtaining JWT access and refresh tokens from the backend.
- **FR-002**: System MUST inject the JWT access token into every API request automatically.
- **FR-003**: System MUST redirect unauthenticated users to the login screen.
- **FR-004**: System MUST display decoded JWT claims (tenant_id, user_id, expiration) after successful login.
- **FR-005**: System MUST allow developers to refresh tokens, verify tokens, change their password, view their profile, and log out.
- **FR-021**: System MUST support full CRUD operations for users and roles, and read-only listing with detail view for branches, on the auth module page.
- **FR-006**: System MUST provide navigation to all six backend modules (auth, health, inventario, ventas, facturacion, sync).
- **FR-007**: System MUST display the backend health status with a pass/fail indicator and response time.
- **FR-008**: System MUST support full CRUD operations for: products, categories, suppliers, price lists, customers, sale orders, order items, ARCA credentials, and puntos de venta.
- **FR-009**: System MUST support create-only (immutable) operations for stock movements.
- **FR-010**: System MUST support read-only views for: price history, cost history, and comprobante details.
- **FR-011**: System MUST support product search, supplier search, and category tree viewing.
- **FR-012**: System MUST support sale order status transitions (confirm, authorize) and display the linked invoice.
- **FR-013**: System MUST support comprobante emission, CAE authorization, and fiscal QR code display.
- **FR-014**: System MUST support CAEA management: listing, requesting new CAEAs, and reporting periods without movements.
- **FR-015**: System MUST support sync session management, push/pull operations, and device status checking.
- **FR-016**: System MUST display backend validation errors at the field level on forms.
- **FR-017**: System MUST provide a "Raw JSON" toggle on every API response for developer inspection.
- **FR-022**: System MUST provide a "Load More" button on paginated list views that fetches the next page using the backend's cursor and appends results to the existing table.
- **FR-018**: System MUST handle unexpected errors gracefully, displaying the raw error response instead of crashing.
- **FR-019**: System MUST attempt automatic token refresh when a request receives a 401 response before redirecting to login.
- **FR-020**: System MUST store tokens in memory only — no persistent storage of credentials.

### Key Entities

- **User Session**: The authenticated developer's JWT tokens and decoded claims. Exists only in memory during the session.
- **API Response**: Every backend response (success or error) that can be inspected as raw JSON by the developer.
- **Module Page**: A single page per backend module containing all the forms, tables, and actions needed to exercise that module's endpoints.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Developers can exercise all 62 backend API endpoints through the prototype interface without needing external tools (curl, Postman).
- **SC-002**: Developers can complete a full login-to-logout cycle (login, call any endpoint, refresh token, logout) in under 2 minutes.
- **SC-003**: Every backend validation error is visible to the developer with specific field-level detail — zero silent failures.
- **SC-004**: Every API response can be viewed as raw JSON within one click from the result display.
- **SC-005**: An unauthenticated or expired-token request results in automatic redirect to login within 3 seconds.
- **SC-006**: The prototype page load (after initial build) takes under 1 second on localhost.
- **SC-007**: A developer unfamiliar with the prototype can navigate to any module and perform a basic CRUD operation within 5 minutes (sidebar navigation is self-explanatory).
- **SC-008**: The prototype container builds in under 60 seconds and the resulting image is under 200MB.

## Clarifications

### Session 2026-02-17

- Q: Should the auth module page include admin UI for managing users, branches, and roles (beyond personal auth flows)? → A: Yes — auth page includes Users, Branches, and Roles management to cover all 12 auth endpoints per SC-001.
- Q: How should list views handle cursor-based pagination from the backend? → A: "Load More" button at the bottom of each table — appends next page of results following the cursor.
- Q: Should data tables include generic filter/search controls beyond the two explicitly mentioned (product search, supplier search)? → A: No — only implement the two explicit search endpoints as defined in the API. Other filtering is out of scope.

## Assumptions

- **A-001**: The backend database is pre-seeded with at least one tenant, user, and basic data (via `seed_ventas` management command or manual setup). The prototype does not seed data.
- **A-002**: The backend API is running and accessible at a known URL (locally or via Docker network).
- **A-003**: Backend API contracts are stable — source of truth is `api/openapi/*.yaml` (auto-generated from Django views via drf-spectacular).
- **A-004**: ARCA (Argentina tax authority) endpoints may return errors without real certificates — the prototype displays these errors transparently rather than mocking them.
- **A-005**: No testing framework is needed for the prototype itself — it IS the testing tool.
- **A-006**: A single-page-per-module layout with sidebar navigation is sufficient. No nested routing or multi-page workflows are needed.
- **A-007**: The developer has a modern browser (Chrome, Firefox, Edge) — no legacy browser support required.

## Dependencies

- **DEP-001**: Backend API must be running with all 62 endpoints available (auth, health, inventario, ventas, facturacion, sync modules).
- **DEP-002**: At least one seeded tenant with a user account for authentication.
- **DEP-003**: The `api/openapi/*.yaml` contracts as reference for endpoint paths, request/response schemas.
