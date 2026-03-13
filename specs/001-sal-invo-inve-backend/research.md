# Research: Sales-Invoicing-Inventory Integration

**Feature**: 001-sal-invo-inve-backend
**Date**: 2026-02-14
**Status**: Complete — No NEEDS CLARIFICATION items

---

## Research Summary

The feature spec has zero open questions. All critical decisions were resolved during specification using existing project standards, Argentine tax authority requirements, and codebase analysis. This document captures the design decisions and rationale discovered during code review.

---

## Decision 1: Stock Reservation Architecture

**Context**: FR-011 requires creating stock movement records with "reserved" status. The current `StockMovement` model is fully immutable (save/delete both raise ValueError for existing records). Adding a mutable `status` field contradicts the immutability pattern.

**Decision**: Introduce limited mutability for `StockMovement` status transitions only.

**Rationale**:
- `StockSnapshot` already has `reserved_quantity` and `StockService` already has `reserve_stock()`/`release_stock()` methods — the snapshot-level reservation infrastructure exists.
- FR-011 explicitly requires movement *records* (not just snapshot counters) for audit trail.
- The immutability constraint applies to financial data (amounts, products, quantities). Status transitions record lifecycle events, not data mutations.

**Implementation**:
- Add `status` field: `RESERVED | COMMITTED | CANCELLED` (default `COMMITTED` for backward compatibility with existing movements).
- Modify `save()` to allow ONLY these transitions: `RESERVED → COMMITTED`, `RESERVED → CANCELLED`. All other updates remain blocked.
- COMMITTED and CANCELLED movements are fully immutable (no further changes).
- Use dual mechanism: StockMovement record (audit trail) + StockSnapshot.reserved_quantity (fast availability check).

**Alternatives Rejected**:
- *Snapshot-only reservations*: Rejected because FR-011 requires movement records and FR-016 requires traceability.
- *Counter-entry pattern* (create reversal movements): Rejected because FR-014 says "transition reserved stock to committed" — not create new records.
- *Separate ReservationMovement model*: Over-engineered; adds table without benefit.

---

## Decision 2: Quantity Field Precision

**Context**: The constitution mandates `DECIMAL(17,3)` for financial amounts. Existing `StockMovement.quantity_delta` uses `DECIMAL(16,4)`. New `SaleOrderItem.quantity` needs precision alignment.

**Decision**: Use `DECIMAL(17,3)` for money fields (via `MoneyField`), `DECIMAL(16,4)` for quantity fields to match existing `inventario` patterns.

**Rationale**:
- `MoneyField` (17,3) is for monetary values: prices, costs, totals, amounts.
- Quantity fields (16,4) are for unit counts, which may need fractional precision (e.g., 2.5kg).
- Changing existing `StockMovement.quantity_delta` precision would require a data migration on the immutable ledger table — high risk for zero benefit.
- Spec says "3 decimal places" for quantities, but 4 decimal places (existing) is a superset and doesn't violate the spec.

**Implementation**:
- `SaleOrderItem.quantity`: `DecimalField(max_digits=16, decimal_places=4)` — matches `StockMovement.quantity_delta`.
- `SaleOrderItem.unit_price`, `subtotal`: `MoneyField()` — `DECIMAL(17,3)`.
- `SaleOrder.total_amount`: `MoneyField()` — `DECIMAL(17,3)`.

---

## Decision 3: Customer Model Location

**Context**: Spec requires a Customer entity. Possible locations: `apps/ventas/` (new module) or `apps/core/` (shared).

**Decision**: Place `Customer` in `apps/ventas/`.

**Rationale**:
- Customer is a sales domain entity. The `core` module is for infrastructure (encryption, managers, tenant model).
- Constitution Section III defines `ventas` as a module boundary.
- Future `clientes` CRM module (deferred) may eventually own customer data, but for now sales owns it.
- Simpler dependency graph: `ventas` depends on `core`, `inventario`, `facturacion`; not the other way around.

**Alternatives Rejected**:
- *Place in `core`*: Violates modular architecture. Core should not contain business entities.
- *Create separate `clientes` module*: Over-engineering for current scope. Spec explicitly says customer management is part of sales.

---

## Decision 4: Invoice Type Determination

**Context**: FR-018 requires auto-determining invoice type (A/B/C) based on customer tax status.

**Decision**: Reuse existing `resolver_tipo_comprobante()` from `apps/facturacion/constants.py`.

**Rationale**:
- The function already handles emitter → receiver condition mapping to CbteTipo codes.
- It supports all required mappings: RI→RI=A, RI→CF/Mono/Exento=B, Mono/Exento→any=C.
- No new logic needed — just wire Customer.condicion_iva into the resolver.

**Implementation**:
- `Customer.condicion_iva` stores the ARCA `CondicionIVA` code.
- On sale confirmation: call `resolver_tipo_comprobante(emitter_condition, customer.condicion_iva)`.
- Emitter condition comes from `ARCACredential` configuration (tenant is always Responsable Inscripto initially).

---

## Decision 5: CbteNro Sequencing

**Context**: FR-029 requires strictly monotonic invoice numbering per (PtoVta, CbteTipo).

**Decision**: Leverage existing `InvoiceService._issue_with_transaction()` pattern.

**Rationale**:
- The existing service already uses `select_for_update()` on PuntoDeVenta to serialize concurrent CbteNro allocation.
- Already calls `wsfe.get_ultimo_comprobante()` for next number.
- Already handles timeout recovery via `_recover_from_timeout()`.

**Implementation**:
- Extend `InvoiceService.issue_comprobante()` to accept a `sale_order` parameter.
- The new integration service (`SaleService`) calls `InvoiceService` — no CbteNro logic duplication.
- Rejection recovery reuses existing patterns.

---

## Decision 6: Integration Service Architecture

**Context**: The spec requires atomic transactions spanning three modules: ventas (sale confirmation) → inventario (stock reservation) → facturacion (invoice creation + ARCA authorization).

**Decision**: Create a `SaleService` in `apps/ventas/services/` that orchestrates cross-module operations.

**Rationale**:
- Views should be thin (constitution Section III: "Views remain lightweight — orchestration only").
- Business invariants reside in domain services.
- `SaleService.confirm_sale()` is the atomic boundary: reserve stock + create invoice draft.
- `SaleService.authorize_sale()` delegates to `InvoiceService` for ARCA authorization, then updates stock and sale status based on result.

**Implementation**:
- `SaleService.confirm_sale(sale_order_id)`: `@transaction.atomic` — validate stock → reserve → create Comprobante DRAFT → set sale CONFIRMED.
- `SaleService.authorize_sale(sale_order_id)`: Call `InvoiceService.issue_comprobante()` → on success: commit stock → set sale INVOICED. On rejection: release stock → set sale CONFIRMED (retry-ready).
- Separation: `SaleService` owns the sales workflow; `InvoiceService` owns ARCA communication; `StockService` owns stock operations.

---

## Decision 7: Comprobante Enhancement Strategy

**Context**: Existing Comprobante model needs `sale_order` and `customer` FKs. 334 existing tests must keep passing.

**Decision**: Add nullable FKs with database migration. Do NOT break existing tests.

**Rationale**:
- Existing comprobantes don't have sales orders (standalone invoicing flow).
- New FKs must be `null=True, blank=True` to not break existing records or tests.
- The `customer` FK replaces standalone doc_nro/doc_tipo for sales-originated invoices, but standalone invoicing must remain supported.

**Implementation**:
- Add `sale_order = ForeignKey('ventas.SaleOrder', null=True, blank=True, on_delete=PROTECT)`.
- Add `customer = ForeignKey('ventas.Customer', null=True, blank=True, on_delete=PROTECT)`.
- Existing InvoiceService continues to work without sale_order (standalone mode).
- New SaleService populates both FKs when creating invoice from sale.
- Validation: if sale_order is set, customer must match sale_order.customer.

---

## Decision 8: CUIT Validation Algorithm

**Context**: FR-001/FR-003 require CUIT validation with check digit algorithm.

**Decision**: Implement Modulo-11 check digit validation as a standalone utility.

**Rationale**:
- CUIT format: 11 digits = 2 (type) + 8 (DNI) + 1 (check digit).
- Modulo-11 algorithm with weights [5,4,3,2,7,6,5,4,3,2] is the standard.
- Needed in Customer model validation and serializer validation.

**Implementation**:
- `apps/ventas/validators.py`: `validate_cuit(cuit: str) -> bool` with Modulo-11 check.
- Used in `Customer.clean()` and `CustomerSerializer.validate_cuit()`.
- Also useful for `Comprobante.doc_nro` validation when `doc_tipo == DocTipo.CUIT`.

---

## Decision 9: Emitter CondicionIVA Source

**Context**: `resolver_tipo_comprobante()` needs emitter's CondicionIVA. Where does it come from?

**Decision**: Store emitter CondicionIVA in a tenant configuration or derive from ARCACredential.

**Rationale**:
- In Argentina, the emitter's IVA condition is tied to the company (tenant), not the individual user.
- Most Gravitea tenants will be Responsable Inscripto (CondicionIVA=1) since they use electronic invoicing.
- Monotributistas (CondicionIVA=6) can also use electronic invoicing but emit Type C.

**Implementation**:
- Add `condicion_iva` field to `Tenant` model or use a dedicated `TenantFiscalConfig` model.
- For MVP: hardcode as `CondicionIVA.RESPONSABLE_INSCRIPTO` (1) since ARCA electronic invoicing is primarily for RI emitters.
- Future: configurable per tenant when Monotributista support is needed.
- Decision: Add to `ARCACredential` as `emitter_condicion_iva` field — it's per-credential, not per-tenant (a tenant could theoretically have different conditions in different environments).

---

## Decision 10: Sale Order Status Transitions and Immutability

**Context**: FR-005 defines states: Draft → Confirmed → Invoiced. FR-009 prevents editing after confirmation.

**Decision**: Enforce via model `save()` override with explicit allowed transitions.

**Rationale**:
- Same pattern as Comprobante immutability enforcement.
- Must allow: DRAFT → CONFIRMED (on confirm_sale), CONFIRMED → INVOICED (on authorize), CONFIRMED → DRAFT (on rejection/reset for retry).
- SaleOrderItem edits blocked for non-DRAFT parent.

**Implementation**:
- `SaleOrder.save()` checks if status changed and validates transition.
- Only `SaleService` methods should trigger status changes (not direct model saves from views).
- INVOICED is fully immutable (no further transitions).
- CONFIRMED → DRAFT transition allowed for rejection recovery (FR-032).

---

## Technology Decisions Summary

| Decision | Choice | Key Rationale |
|----------|--------|---------------|
| Stock reservation | Limited mutability on StockMovement status | FR-011 requires movement records; COMMITTED remains immutable |
| Quantity precision | DECIMAL(16,4) for quantities | Match existing inventario patterns |
| Money precision | DECIMAL(17,3) via MoneyField | Constitution mandate |
| Customer location | apps/ventas/ | Sales domain entity; modular architecture |
| Invoice type | Reuse resolver_tipo_comprobante() | Already implemented and tested |
| CbteNro sequencing | Reuse InvoiceService pattern | Already handles locking and recovery |
| Integration | SaleService orchestrator | Thin views; domain services own logic |
| Comprobante FKs | Nullable additions | Backward compatibility with 334 tests |
| CUIT validation | Modulo-11 utility | Standard Argentine algorithm |
| Emitter condition | ARCACredential.emitter_condicion_iva | Per-credential configuration |
