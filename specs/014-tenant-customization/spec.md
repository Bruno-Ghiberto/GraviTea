# Feature Specification: Tenant Customization Framework

**Feature Branch**: `014-tenant-customization`
**Created**: 2026-02-20
**Status**: Draft
**Input**: Tenant customization framework enabling per-tenant ERP personalization without per-tenant database migrations

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Product with Validated Custom Fields (Priority: P1)

A user creates or updates a Product with tenant-specific custom fields (e.g., peso_kg, material) stored in a `custom_data` flexible storage field. The system validates each value against the tenant's field definitions before saving.

**Why this priority**: Products are the most customized entity across all business types. The existing Product flexible storage field already holds unstructured data with zero validation. Adding type-checked, tenant-scoped validation is the core value proposition of the framework.

**Independent Test**: Can be fully tested by creating field definitions for a tenant, then creating/updating a Product with custom_data values and verifying validation runs correctly. Delivers immediate value for any tenant that needs structured product attributes.

**Acceptance Scenarios**:

1. **Given** a tenant has field definitions for Product (e.g., `peso_kg` as decimal/required, `material` as select with choices ["acero","aluminio","plastico"]), **When** the user creates a Product with `custom_data: {"peso_kg": 2.5, "material": "acero"}`, **Then** the Product is created successfully with the custom data stored and returned in the response.
2. **Given** a required field definition exists, **When** the user creates a Product without that required field in `custom_data`, **Then** the system returns a validation error identifying the missing field by its key and label.
3. **Given** a `select` field definition with choices, **When** the user submits a value not in the choices list, **Then** the system returns a validation error showing the invalid value and the allowed choices.
4. **Given** a field definition with type `integer`, **When** the user submits `custom_data: {"qty_pack": "not_a_number"}`, **Then** the system returns a type validation error.
5. **Given** a tenant with NO field definitions for Product, **When** the user creates a Product without `custom_data` or with `custom_data: {}`, **Then** the Product is created successfully (custom fields are optional infrastructure).
6. **Given** an existing Product with `custom_data: {"peso_kg": 2.5, "material": "acero"}`, **When** the user updates the Product with `custom_data: {"peso_kg": 3.0}`, **Then** the system merges the incoming keys with the existing values, resulting in `{"peso_kg": 3.0, "material": "acero"}`. To remove a key, the client sends `null` for that key (e.g., `{"material": null}` removes it).
7. **Given** the existing Product flexible storage field contains seed data, **When** the system is upgraded, **Then** the field is renamed to `custom_data` with zero data loss (other system-managed fields remain unchanged).

---

### User Story 2 - Field Definitions Retrieval (Priority: P1)

A frontend application queries the field definitions to retrieve the current tenant's custom field configuration for a given entity type, enabling dynamic form rendering.

**Why this priority**: This is the bridge between backend definitions and frontend rendering. Without it, the frontend cannot know what fields to render. Required for US4.

**Independent Test**: Can be fully tested by creating field definitions for different tenants and entity types, then querying the read-only endpoint and verifying correct tenant-scoped, filtered results.

**Acceptance Scenarios**:

1. **Given** a tenant has field definitions for entity_type=product, **When** the frontend requests field definitions filtered by entity_type=product, **Then** the response contains all active field definitions for that tenant and entity type, ordered by section and position.
2. **Given** a tenant has field definitions for multiple entity types, **When** the frontend requests field definitions without an entity_type filter, **Then** all active field definitions for that tenant are returned.
3. **Given** a field definition is marked inactive, **When** the field definitions are queried, **Then** inactive definitions are excluded from the response.
4. **Given** tenant A and tenant B each have different field definitions, **When** each tenant queries field definitions, **Then** each sees only their own definitions (tenant-scoped isolation).
5. **Given** no authentication token, **When** the field definitions are requested, **Then** the system returns an authentication error.

---

### User Story 3 - Template-Based Tenant Onboarding (Priority: P1)

An administrator onboards a new tenant by applying a business template that bootstraps module configurations and custom field definitions appropriate for the tenant's business type. The first available template is "ferreteria" (industrial hardware store).

**Why this priority**: Without templates, every tenant setup requires manual field-by-field configuration. Templates make onboarding repeatable, error-free, and fast.

**Independent Test**: Can be fully tested by running the template application command for a tenant and verifying that module configurations and field definitions are created correctly with the expected defaults.

**Acceptance Scenarios**:

1. **Given** a "ferreteria" business template exists in the system, **When** the administrator applies the template to a tenant, **Then** module configurations are created for inventario, ventas, and facturacion (all enabled), and field definitions are created for Product with hardware-store fields (peso_kg, largo_cm, ancho_cm, alto_cm, material, marca, codigo_proveedor).
2. **Given** a template has already been applied to a tenant, **When** the administrator applies the same template again, **Then** the operation is idempotent — existing configurations are not duplicated and no error is raised.
3. **Given** the business template data model, **When** a team member views it in the admin interface, **Then** the slug, name, description, module list, and field definitions content are visible and editable.
4. **Given** the business template model is NOT tenant-bound, **When** querying templates, **Then** all templates are visible regardless of which tenant is in context (system-wide resource).

---

### User Story 4 - Frontend Renders Dynamic Product Fields (Priority: P2)

A user opening the Product create/edit form sees dynamically rendered custom fields (based on the tenant's field definitions) alongside the standard Product fields. The form validates and submits custom data correctly.

**Why this priority**: Without a frontend consumer, the field definitions have no proof of usability. The Product form is the first and most important consumer. Depends on US2 existing first.

**Independent Test**: Can be fully tested by configuring field definitions for a tenant, opening the Product form, and verifying that each field type renders as the correct input control with validation.

**Acceptance Scenarios**:

1. **Given** a tenant has field definitions for Product, **When** the user opens the Product create form, **Then** a "Custom Fields" section appears below the standard fields, rendering each field definition as the appropriate input type (text input, number input, checkbox, date picker, select dropdown).
2. **Given** a `select` field definition with choices ["acero","aluminio","plastico"], **When** the form renders, **Then** a dropdown component shows those choices.
3. **Given** a `required` field definition, **When** the user submits the form without filling it, **Then** client-side validation shows an error before the request is made.
4. **Given** a `boolean` field definition, **When** the form renders, **Then** a toggle or checkbox component appears with the correct default value.
5. **Given** a `date` field definition, **When** the form renders, **Then** a date input component appears.
6. **Given** an existing Product with saved `custom_data`, **When** the user opens the edit form, **Then** the custom fields are pre-populated with the existing values.
7. **Given** a tenant with NO field definitions for Product, **When** the user opens the Product form, **Then** the "Custom Fields" section is not rendered (graceful absence, not an error).
8. **Given** the user fills custom fields and submits, **When** the backend rejects a value, **Then** the field-level error is displayed next to the corresponding input.

---

### User Story 5 - Custom Data on Other Business Entities (Priority: P2)

A user creates or updates a Customer, Supplier, or SaleOrder with tenant-specific custom fields, using the same custom_data + field definitions pattern established for Product.

**Why this priority**: The framework must be reusable across entity types. Adding custom_data to these models and wiring the same validation proves the pattern generalizes. Depends on US1 working first.

**Independent Test**: Can be fully tested by creating field definitions for Customer/Supplier/SaleOrder, then creating records with custom_data and verifying validation runs against entity-specific definitions.

**Acceptance Scenarios**:

1. **Given** a tenant has field definitions for Customer (e.g., `razon_visita` as text, `descuento_especial` as decimal), **When** the user creates a Customer with matching custom_data, **Then** the Customer is created with validated custom data.
2. **Given** field definitions exist for Supplier, **When** the user creates a Supplier with custom_data, **Then** validation runs against the Supplier-specific definitions (not Product definitions).
3. **Given** field definitions exist for SaleOrder, **When** the user creates a SaleOrder with custom_data, **Then** the order stores the custom data alongside its existing fields.
4. **Given** no custom_data storage exists on these models today, **When** the system is upgraded, **Then** a flexible storage field is added to Customer, Supplier, and SaleOrder without affecting existing data.

---

### User Story 6 - Module Activation (Priority: P3)

An administrator enables or disables ERP modules per tenant, controlling which functional areas each tenant has access to.

**Why this priority**: Module activation is the outermost customization layer. It defines which modules a tenant can use, but enforcement middleware is deferred — this story only defines the data model and the read endpoint.

**Independent Test**: Can be fully tested by creating module configuration records for a tenant and verifying the read endpoint returns correct enabled/disabled status per module.

**Acceptance Scenarios**:

1. **Given** a module configuration model with fields (tenant, module, enabled, settings), **When** the administrator creates a config for tenant X with module=inventario and enabled=true, **Then** the module config is stored with the tenant's settings.
2. **Given** module configs exist, **When** the frontend requests module configuration, **Then** the response lists all modules and their enabled/disabled status for the current tenant.
3. **Given** module choices include inventario, ventas, facturacion, and sync, **When** a config row is created, **Then** only these module values are accepted.
4. **Given** a tenant, **When** two config rows are created for the same module, **Then** the unique constraint prevents the duplicate.

---

### User Story 7 - Admin Interface for Field Management (Priority: P3)

A team member uses the admin interface to create, edit, and deactivate field definitions and module configurations for any tenant.

**Why this priority**: This is the initial management interface before any client-facing admin UI exists. The team needs to configure tenants during onboarding and testing.

**Independent Test**: Can be fully tested by navigating the admin interface, creating/editing/deactivating field definitions, and verifying the list views show correct filters and search.

**Acceptance Scenarios**:

1. **Given** the admin interface, **When** a team member navigates to field definitions, **Then** the list view shows field_key, label, entity_type, field_type, section, and active status with filters on entity_type, field_type, section, active and search on field_key, label.
2. **Given** the admin interface, **When** a team member navigates to module configurations, **Then** the list view shows tenant, module, and enabled status with filters on module and enabled.
3. **Given** the admin interface, **When** a team member navigates to business templates, **Then** the list view shows slug and name with the content fields editable.
4. **Given** a team member deactivates a field definition, **When** a user next creates a Product with custom_data, **Then** the deactivated field is no longer required and its value is ignored during validation but preserved if already stored.

---

### Edge Cases

- What happens when a field definition is deactivated while Products already have values for that field? Values are preserved in storage but excluded from validation and not returned to the frontend.
- What happens when a required field definition is added after Products already exist without that field? Existing Products are unaffected (validation only runs on create/update), but new creates and updates must include the required field.
- What happens when custom_data contains keys not defined in any field definition? Undefined keys are silently ignored (not validated, not rejected) to allow forward-compatibility.
- What happens when a field definition's choices list is updated and existing Products have values no longer in the list? Existing stored values are preserved. Validation only enforces the current choices list on new creates and updates.
- What happens when a template is applied to a tenant that already has manually-created field definitions? The template adds its field definitions using idempotent logic — existing definitions with the same field_key are not duplicated or overwritten.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a tenant-scoped field definition model that stores field key, label, entity type, field type, section, position, required flag, default value, choices list, and active flag.
- **FR-002**: System MUST support six field types: text, integer, decimal, boolean, date, and select.
- **FR-003**: System MUST validate custom_data values against the tenant's active field definitions before saving any entity (Product, Customer, Supplier, SaleOrder).
- **FR-004**: System MUST return validation errors in a field-keyed structure compatible with the existing error response pattern (each field_key maps to a list of error strings).
- **FR-005**: System MUST rename the existing Product flexible storage field to `custom_data` via migration with zero data loss.
- **FR-006**: System MUST add a `custom_data` flexible storage field to Customer, Supplier, and SaleOrder models.
- **FR-007**: System MUST provide a read-only endpoint for field definitions, filterable by entity_type, scoped to the current tenant, returning only active definitions ordered by section and position.
- **FR-008**: System MUST provide a read-only endpoint for module configuration, scoped to the current tenant.
- **FR-009**: System MUST provide a business template model (system-wide, not tenant-bound) with slug, name, description, module list, and field definitions content.
- **FR-010**: System MUST provide a management command to apply a business template to a tenant, creating module configs and field definitions idempotently.
- **FR-011**: System MUST provide a "ferreteria" business template with hardware-store-specific field definitions for Product (peso_kg, largo_cm, ancho_cm, alto_cm, material, marca, codigo_proveedor).
- **FR-012**: System MUST provide a module configuration model with tenant, module choice, enabled flag, and settings, enforcing a unique constraint on (tenant, module).
- **FR-013**: System MUST support module choices: inventario, ventas, facturacion, sync.
- **FR-014**: System MUST provide admin interface views for field definitions, module configurations, and business templates with appropriate list displays, filters, and search fields.
- **FR-015**: System MUST cache field definitions with a short time-to-live keyed by tenant and entity type, invalidating on field definition changes.
- **FR-016**: System MUST add a search-optimized index on each custom_data column for efficient queries.
- **FR-017**: System MUST skip validation for inactive field definitions while preserving their stored values.
- **FR-018**: System MUST render a "Custom Fields" section in the Product create/edit form that dynamically generates input controls from the field definitions endpoint.
- **FR-019**: System MUST map field types to appropriate input controls: text to text input, integer/decimal to number input, boolean to toggle/checkbox, date to date input, select to dropdown.
- **FR-020**: System MUST provide client-side validation for required fields before submitting the form.
- **FR-021**: System MUST display backend validation errors next to the corresponding custom field input.
- **FR-022**: System MUST NOT render the "Custom Fields" section when no field definitions exist for the current tenant and entity type.
- **FR-023**: Validation errors for custom_data MUST follow the existing error response pattern where each field_key maps to a list of error strings.
- **FR-024**: System MUST provide a reusable validation component (mixin or utility) that can be applied to any entity's serializer without code duplication.
- **FR-025**: System MUST use merge semantics when updating custom_data — incoming keys are merged with existing stored values; only explicitly sent keys are updated; sending `null` for a key removes it from storage.
- **FR-026**: System MUST apply field definition default values only during entity creation and only when the field key is absent from the submitted custom_data. Updates never auto-apply defaults. The default value is also included in the field definitions API response for frontend pre-population.
- **FR-027**: System MUST enforce field_key format: snake_case only (lowercase letters, digits, and underscores), must start with a letter, maximum 50 characters (e.g., `peso_kg`, `codigo_proveedor`).

### Key Entities

- **TenantFieldDefinition**: Represents a custom field configuration for a specific tenant and entity type. Contains the field key (unique per tenant+entity_type), human-readable label, entity type (product, customer, supplier, sale_order), field type (text, integer, decimal, boolean, date, select), display section, sort position, required flag, default value, choices list (for select type), and active flag. Belongs to a tenant (tenant-scoped).
- **TenantModuleConfig**: Represents which ERP modules are enabled for a specific tenant. Contains the module identifier (inventario, ventas, facturacion, sync), enabled flag, and optional settings. Has a unique constraint on tenant + module combination. Belongs to a tenant (tenant-scoped).
- **BusinessTemplate**: Represents a reusable onboarding template for a business type. Contains a unique slug, name, description, list of modules to enable, and field definitions to create. System-wide (NOT tenant-bound) — visible to all tenants.
- **Product.custom_data**: Renamed from the existing `attributes` field. Flexible storage for tenant-defined custom field values. Validated against TenantFieldDefinition before save.
- **Customer.custom_data**: New flexible storage field for tenant-defined custom field values.
- **Supplier.custom_data**: New flexible storage field for tenant-defined custom field values.
- **SaleOrder.custom_data**: New flexible storage field for tenant-defined custom field values.

### Models That Do NOT Get custom_data

- **Comprobante** — immutable fiscal document, custom fields would violate fiscal compliance
- **StockMovement** — immutable ledger, no custom data
- **Role, Branch, AppUser** — system/auth models, not business entities

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can create a Product with 7 custom fields in the same time it takes to create one without custom fields (no perceptible delay from validation).
- **SC-002**: A new tenant can be fully onboarded with a business template in under 30 seconds (including field definitions and module configurations).
- **SC-003**: The custom fields section renders on the Product form within 1 second of page load, with all field types displaying correctly.
- **SC-004**: 100% of field type validations (text, integer, decimal, boolean, date, select) correctly accept valid values and reject invalid values.
- **SC-005**: Tenant A cannot see or access Tenant B's field definitions under any circumstance (tenant isolation maintained).
- **SC-006**: The Product flexible storage field rename preserves 100% of existing data with zero data loss.
- **SC-007**: Applying the same template twice to the same tenant produces identical results (idempotent operation).
- **SC-008**: All existing tests continue to pass after the framework is added (zero regressions).
- **SC-009**: Custom field validation works identically across all 4 entity types (Product, Customer, Supplier, SaleOrder) using the same reusable component.
- **SC-010**: Deactivating a field definition stops validation and frontend rendering while preserving all previously stored values.

## Clarifications

### Session 2026-02-20

- Q: Should custom_data updates use full replacement or merge semantics? → A: Merge — server merges incoming keys with existing stored values; sending `null` for a key removes it.
- Q: When should field definition default values be applied? → A: Create-only, absent fields — defaults applied only on entity creation when the field key is not present in custom_data; updates never auto-apply defaults; default value included in API response for frontend pre-population.
- Q: What format constraints should field_key follow? → A: snake_case only — lowercase letters, digits, underscores; must start with a letter; max 50 characters.

## Assumptions

- The existing Product `attributes` JSONField contains only tenant-defined flexible data (no system-critical data beyond `ml_tags`, which is a separate field).
- The "ferreteria" template field definitions (peso_kg, largo_cm, etc.) are representative and may be adjusted during implementation planning.
- Write endpoints (POST/PUT/DELETE) for field definitions are deferred — the team configures via admin interface or management commands for now.
- Module activation enforcement middleware (blocking requests to disabled modules) is deferred to a future spec.
- Frontend dynamic fields are implemented only for the Product form in this spec — Customer, Supplier, and SaleOrder forms are deferred.
- Field definitions change rarely (admin/onboarding only) so caching with a short TTL is appropriate.
- Undefined keys in custom_data are silently ignored rather than rejected, supporting forward-compatibility.

## Explicitly Out of Scope

| Item | Reason | When to Revisit |
|------|--------|-----------------|
| Dynamic fields on Customer/Supplier/SaleOrder forms | Backend ready, frontend deferred | When those entity forms need customization |
| Client-facing field management UI | Team configures for now | When 10+ tenants need self-service |
| Write endpoints for field definitions | Team uses admin/commands | When client admin self-service is needed |
| Custom business logic per tenant | Requires strategy pattern design from real requirements | When 2+ tenants need different calculation rules |
| Relational custom fields (FK to other models) | Complexity explosion | When a real client needs linked custom entities |
| Custom workflows / approval chains | Separate architectural concern | When a client specifically requests it |
| Module-level permission middleware | Model defined here, enforcement deferred | Future spec decides task ordering |
