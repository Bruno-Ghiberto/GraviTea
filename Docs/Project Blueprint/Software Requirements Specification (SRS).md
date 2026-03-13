# Software Requirements Specification (SRS) - Gravitea ERP

## 1. Introducción

### 1.1 Propósito

Este documento especifica, con nivel de detalle suficiente para desarrollo e implementación, los **requisitos de software** del sistema Gravitea ERP.
Sirve como contrato entre:

- Stakeholders de negocio (dueños de comercios, responsables comerciales, contadores).
- Equipo de producto (Product Owner).
- Equipo técnico (CTO, Tech Lead, Backend, Frontend, DevOps, QA).

La SRS debe ser lo bastante precisa como para:

- Guiar el diseño técnico (HLD/LLD) y la API (`REST API Design.md`).
- Definir criterios de aceptación para QA y UAT.
- Permitir futuras extensiones sin romper el núcleo de requisitos.

**Última Actualización**: 2026-03-01
**Estado**: Features 001-025 Completas — Aceleración Rust Done — Fase de Investigación Vertical SaaS

### 1.2 Alcance

Gravitea ERP es un sistema ERP **cloud-first, multi-tenant y offline-first** para PyMEs de retail físico (especialmente ferreterías, corralones, pinturerías).
El sistema cubre el ciclo comercial completo:

- **INVENTARIO**: catálogo, stock (ledger inmutable), movimientos, ajustes. ✅ Implementado
- **VENTAS (POS)**: órdenes de venta, clientes, facturación fiscal/no fiscal, cobros. ✅ Backend implementado
- **FACTURACIÓN ARCA**: comprobantes fiscales, CAE online, CAEA offline, QR fiscal. ✅ Implementado
- **COMPRAS**: proveedores (implementado), órdenes de compra (pendiente).
- **CLIENTES**: alta/gestión, listas de precios, cuentas corrientes.
- **REPORTES**: reportes operativos y agregados. (No iniciado)
- **SYNC/API offline**: operación offline en sucursal con sincronización diferida. ✅ Backend implementado
- **AUTH/Seguridad**: multi-tenancy, RBAC, auditoría. ✅ Implementado
- **PERSONALIZACIÓN**: campos personalizados por tenant, configuración de módulos, templates. ✅ Implementado

El alcance de esta SRS se centra en el **MVP definido en `Product Vision & Scope.md` y `PRD.md`**, estructurado en forma de requisitos de software.

### 1.3 Definiciones, Acrónimos y Abreviaturas

- **Tenant**: organización cliente (comercio/empresa). UUID como PK, plan_type FREE/PRO/ENTERPRISE.
- **Sucursal / Branch**: punto de venta físico asociado a un tenant. `afip_pos_number` 1-99999.
- **TenantBoundModel**: clase abstracta Django que aísla datos por tenant (TenantBoundManager + RLS + validación IDOR).
- **POS**: Point of Sale (Punto de Venta). Backend implementado; cliente de escritorio Electron planificado.
- **ARCA**: organismos fiscales para facturación electrónica en Argentina.
- **CAE**: Código de Autorización Electrónico (modalidad online).
- **CAEA**: Código de Autorización Electrónico Anticipado (modalidad offline).
- **RLS**: Row Level Security (seguridad a nivel de fila en PostgreSQL 18.1).
- **MVP**: Minimum Viable Product. Objetivo original: 1 de mayo de 2026 (en revisión — fase de investigación Vertical SaaS).
- **DRF**: Django REST Framework.
- **PyO3**: Bridge FFI Rust↔Python. Versión 0.28.
- **Maturin**: Herramienta de build para paquetes Rust/Python. Versión 1.12.4.
- **Problem+JSON**: RFC 7807/9457 — formato estándar de errores en la API REST.

### 1.4 Referencias

- `Product Vision & Scope.md`
- `PRD.md`
- `Roadmap.md`
- `Data Model & Domain Model.md`
- `High-Level Design (HLD).md`
- `Low-Level Design (LLD).md`
- `REST API Design.md`
- `Developer Onboarding Guide.md`

### 1.5 Visión General del Documento

- **Capítulo 2**: describe el contexto general del sistema y sus usuarios.
- **Capítulo 3**: especifica características y requisitos funcionales por módulo.
- **Capítulo 4**: define requisitos de interfaces externas (UI, API, integraciones).
- **Capítulo 5**: establece requisitos no funcionales (NFRs).
- **Capítulo 6**: resume requisitos de datos y multi-tenant.
- **Capítulo 7**: otros requisitos (legales, localización, etc.).

---

## 2. Descripción General

### 2.1 Perspectiva del Producto

Gravitea ERP se compone de los siguientes elementos, distinguiendo entre el **estado actual (implementado)** y el **estado planificado (producción)**:

**Implementado actualmente**:
- **Backend**: Django 5.2 + DRF en Docker Compose (dev), con PostgreSQL 18.1 como única fuente de verdad. 137 operaciones API en 79 paths, 9 contratos OpenAPI, 23 migraciones.
- **Capa de Aceleración Rust/PyO3**: 9 módulos nativos Rust (specs 017-025) compilados con PyO3 0.28 y Maturin 1.12.4. Speedups 2.1x-8.7x en hot-paths CPU-bound (criptografía, IVA, exportación, SSRF, sync merge). Todos con fallback a Python puro.
- **Frontend de Desarrollo**: Next.js 16 (App Router) — 9 rutas, 52 archivos fuente, JWT en memoria. Este es el frontend **activo en el entorno de desarrollo**.
- **Suite de Tests**: ~2,500+ funciones de test en 111+ archivos, incluyendo 131 tests de integración Rust (cargo + pytest).

**Planificado para producción**:
- **Cliente de Escritorio**: Electron para POS y operación diaria en sucursales. Incluirá SQLite cifrado local y Sync Worker.
- **Servicios GCP**: Cloud Run (Django backend), Cloud SQL (PostgreSQL), Memorystore (Redis), Pub/Sub, Cloud Tasks.

El sistema es **multi-tenant** (un solo despliegue para muchos clientes) y **offline-first** en sucursales (planificado para cliente Electron).

### 2.2 Funciones del Producto (Vista de Módulo)

1. **INVENTARIO** ✅ Implementado
   - Gestión de catálogo de productos: SKU único por tenant, barcode cifrado, custom_data (JSONB).
   - Control de stock por sucursal mediante ledger de movimientos (StockMovement — append-only).
   - Ajustes de stock auditados. Historial de precios y costos (SCD Type 2).
   - Proveedores con PII cifrado (tax_id, email, address — AES-256-GCM + blind index).

2. **VENTAS** ✅ Implementado (Backend)
   - Órdenes de venta con ciclo DRAFT→CONFIRMED→INVOICED. Estado INVOICED inmutable.
   - Clientes con CUIT, doc_tipo, condicion_iva, razon_social, custom_data.
   - Items con unit_price snapshot, subtotal e IVA calculados automáticamente.

3. **FACTURACIÓN ARCA** ✅ Implementado
   - Integración directa WSAA + WSFEv1 (SOAP). Certificados cifrados por tenant.
   - CAE online y CAEA offline. Comprobantes inmutables. QR fiscal.

4. **COMPRAS** Parcial
   - Alta y gestión de proveedores (implementado — PII cifrado).
   - Órdenes de compra, recepciones parciales/completas (pendiente).
   - Registro de facturas de proveedor y actualización de costos/precios (pendiente).

5. **CLIENTES** ✅ Implementado
   - ABM de clientes con soft delete.
   - custom_data JSONB para campos adicionales.
   - Asignación de listas de precios y condiciones comerciales.

6. **REPORTES** Contrato Definido
   - Reportes de ventas, stock, clientes y compras (contrato OpenAPI definido, lógica pendiente).
   - Exportaciones CSV/XLSX aceleradas por Rust (`export.rs`, spec 020) con fallback Python (openpyxl).

7. **SYNC / API offline** ✅ Backend implementado
   - Descarga periódica de datos críticos (inventario, precios, clientes frecuentes) — API lista.
   - Envío de ventas y ajustes hechos offline — Push/Pull idempotente implementado.
   - Manejo de conflictos y reintentos — vector clocks, retry_count, status CONFLICTED/REJECTED.

8. **AUTH / Seguridad** ✅ Implementado
   - Autenticación JWT RS256 con claims personalizados (tenant_id, branch_id, role_id, permissions).
   - Roles y permisos (RBAC) — permissions como lista `module.action` en JSONField.
   - Aislamiento multi-tenant con RLS (Defense-in-Depth: 3 capas).

9. **PERSONALIZACIÓN** ✅ Implementado
   - TenantFieldDefinition (6 tipos de campo por 4 tipos de entidad).
   - TenantModuleConfig (habilitar/deshabilitar módulos con settings JSON).
   - BusinessTemplate (templates de onboarding del sistema).

### 2.3 Clases de Usuarios y Características

- **Dueño / Gerente**
  - Perfil: toma decisiones, poco tiempo, alta necesidad de métricas y control remoto.
  - Uso: reportes, configuración de precios, control de stock, vistas web (Next.js actual) / móvil (planificado).

- **Cajero / Vendedor**
  - Perfil: alta rotación, orientación operativa, foco en velocidad.
  - Uso: POS en Next.js (actualmente) / Electron (producción planificada), búsqueda de productos, cobros, tickets/facturas.

- **Responsable de Depósito**
  - Perfil: organiza stock y recepción de mercadería.
  - Uso: ajustes de stock, recepciones de compras, transferencias entre sucursales.

- **Contador / Asesor Fiscal**
  - Perfil: foco en compliance, IVA, retenciones.
  - Uso: reportes fiscales, exportaciones, conciliaciones, revisión de comprobantes.

### 2.4 Entorno Operativo

**Entorno de desarrollo actual**:
- **Servidor**: Docker Compose local — Django backend (:8000), PostgreSQL 18.1 (:5432), Redis (:6379).
- **Frontend**: Navegadores modernos (Chrome/Firefox/Edge) accediendo a Next.js 16 dev server (:3000).
- **Tests**: Python 3.14.3, pytest-django, venv WSL o Docker exec.

**Entorno de producción planificado**:
- **Servidores**: Google Cloud Run (Django backend), Cloud SQL (PostgreSQL), Memorystore (Redis).
- **Clientes de sucursal**: PCs Windows 10/11 x64 con al menos 4 GB de RAM, ejecutando cliente Electron.
- **Red**: conexión a Internet variable, con cortes frecuentes; se asume al menos una conexión diaria para sincronización fiscal.
- **Base de datos local** (Electron — planificado): SQLite cifrado (SQLCipher) en el cliente de escritorio.

### 2.5 Restricciones de Diseño e Implementación

**Restricciones implementadas (vigentes)**:
- Debe utilizarse **PostgreSQL 18.1** con RLS para aislamiento multi-tenant.
- Debe utilizarse **Django 5.2.x + DRF** en el backend.
- Cifrado de campos PII: **AES-256-GCM** (`EncryptedCharField`, `EncryptedTextField`) con blind indexes HMAC-SHA256 para búsqueda. Acelerado por Rust `crypto.rs` (8.7x speedup, spec 018).
- JWT: exclusivamente **RS256** (4096-bit RSA). Los algoritmos HS256/HS384/HS512 están explícitamente prohibidos.
- Errores de API: formato **Problem+JSON** (RFC 7807/9457) — `problem_detail_exception_handler`.
- Paginación: **cursor-based** por defecto (`StandardCursorPagination`, PAGE_SIZE=100).

**Restricciones del entorno de producción planificado**:
- La app de escritorio para sucursales **debe ser Electron** (Node + Chromium + SQLite cifrado).
- El deployment en producción debe ser **Google Cloud Run + Cloud SQL**.
- Cumplimiento con requisitos fiscales de **ARCA** (implementado para Argentina; adaptable a LATAM).

**Aclaración dual-entorno**:
- El entorno de desarrollo actual utiliza **Next.js 16** como frontend web.
- El cliente de escritorio **Electron** es la restricción del entorno de producción planificado para sucursales.
- Ambos se comunican con el mismo backend Django vía REST API.

### 2.6 Supuestos y Dependencias

- Los clientes gestionan sus propios certificados fiscales ARCA (el sistema avisa vencimientos).
- Siempre existirá al menos un canal de comunicación con el contador (exportación de reportes — planificado).
- Los lectores de código de barras son dispositivos HID que actúan como teclado.
- El módulo de Reportes se completará antes del lanzamiento MVP (1 de mayo de 2026).

---

## 3. Requisitos Funcionales por Módulo

> Los IDs de requisitos (`INV-01`, `POS-01`, etc.) se alinean con `PRD.md` cuando aplica.
> Cada requisito indica su estado actual: **✅ Implementado**, **Parcial**, o **Planificado**.

### 3.1 Módulo INVENTARIO ✅ Implementado

**INV-01: Ledger de Stock** ✅
- El sistema mantiene el stock mediante `StockMovement` (append-only). No se sobrescribe la cantidad actual.
- Cada movimiento registra: `product_id`, `branch_id`, `quantity_delta`, `movement_type` (PG ENUM), `status` (PG ENUM), `reference_number`, `sale_order` (FK opcional), `comprobante` (FK opcional), `tenant_id`.

**INV-02: Vista de Stock Actual** ✅
- Endpoint `/api/v1/products/{id}/stock/` devuelve stock actual por producto/sucursal.
- Basado en `StockSnapshot` (BranchStock) — tabla materializada, actualizada por trigger SQL.

**INV-03: Ajustes de Stock** ✅
- Usuarios con rol adecuado pueden registrar ajustes (`movement_type=ADJUSTMENT`).
- Los ajustes quedan auditados (tenant_id, branch_id, created_at, reference_number).

**INV-04: Catálogo de Productos** ✅
- Alta, baja lógica (`is_active`) y modificación de productos.
- Cada producto tiene: SKU único por tenant, nombre, descripción, categoría (jerárquica), barcode (cifrado AES-256-GCM + blind index), unit_of_measure, custom_data (JSONB).

### 3.2 Módulo COMPRAS (Parcial)

**COMP-01: Gestión de Proveedores** ✅
- ABM de proveedores con PII cifrado (razón social, CUIT/tax_id, contactos).
- Blind index HMAC-SHA256 para búsqueda en campos cifrados (`/suppliers/search/`).
- custom_data JSONB para campos adicionales por tenant.

**COMP-02: Órdenes de Compra** Planificado
- Crear órdenes de compra por sucursal y proveedor.
- Registrar estado: DRAFT, SENT, PARTIAL_RECEIVED, COMPLETED.

**COMP-03: Recepción de Mercadería** Planificado
- Registrar recepciones parciales o totales sobre una orden.
- Cada recepción debe generar movimientos de stock y actualización de costos.

**COMP-04: Facturas de Proveedor** Planificado
- Registrar facturas asociadas a órdenes de compra.

### 3.3 Módulo CLIENTES ✅ Implementado

**CLI-01: ABM de Clientes** ✅
- Alta, edición y baja lógica de clientes (soft delete).
- Datos: razon_social, CUIT, doc_tipo (código ARCA), condicion_iva (código ARCA), email, phone, address, custom_data (JSONB).

**CLI-02: Listas de Precios por Cliente** ✅ (vía PriceList)
- Asociar una lista de precios por defecto a cada cliente.

**CLI-03: Cuentas Corrientes** Planificado
- Registrar cargos (ventas) y pagos sobre la cuenta corriente.

### 3.4 Módulo VENTAS (POS) ✅ Backend Implementado

**POS-01: Facturación con Contingencia Offline** ✅ Backend / Planificado Electron
- Backend soporta emisión de comprobantes (ARCA CAE online, CAEA offline).
- Cliente Electron para operación offline completa: planificado para producción.

**POS-02: Búsqueda Rápida de Productos** Parcial
- Backend: búsqueda por barcode (blind index). FTS full text: planificado.
- Cliente Electron con SQLite FTS5: planificado para producción.

**POS-03: Flujo de Venta** ✅ Backend
- Endpoints: `POST /ventas/orders/` (DRAFT), `POST .../confirm`, `POST .../invoice`.
- Items anidados: `POST /ventas/orders/{order_pk}/items/`.
- Estado INVOICED es inmutable terminal — vinculado a Comprobante AUTORIZADO.

### 3.5 Módulo REPORTES (No iniciado)

**REP-01: Reporte de Ventas** Planificado
- Ver ventas agregadas por fecha, sucursal, vendedor y cliente.
- Exportar a formatos estándar (CSV, XLSX).

**REP-02: Reporte de Stock** Planificado
- Mostrar stock actual, rotación y quiebres de stock.

**REP-03: Reportes para Contabilidad** Planificado
- Generar reportes para libros IVA, resúmenes de ventas, retenciones/percepciones.

### 3.6 Módulo SYNC / API Offline ✅ Backend Implementado

**SYNC-01: Descarga de Datasets Críticos** ✅
- `GET /sync/pull/?cursor=...` — cursor-based, entity filtering, idempotente.
- `GET /sync/status/{device_id}/` — device status + pending/conflict counts.

**SYNC-02: Cola de Operaciones** ✅ Backend / Planificado Electron
- `PendingOperation`: UUID único (idempotencia), operation_type (CREATE/UPDATE/DELETE), entity_type, payload (JSON), client/server timestamps, status, retry_count.
- `POST /sync/push/` — batch push idempotente con UUIDs generados por cliente.

**SYNC-03: Reintentos y Conflictos** ✅
- Reintentos con retry_count en PendingOperation; backoff manejado por cliente.
- Conflictos: status CONFLICTED/REJECTED en PendingOperation con resolución documentada.

### 3.7 AUTH / Seguridad ✅ Implementado

**AUTH-01: Autenticación JWT** ✅
- Login por email/password → access token (RS256) + refresh token.
- Refresh tokens revocables (token_blacklist) y rotables.
- Logout: `POST /auth/logout/` — blacklistea el refresh token.

**AUTH-02: RBAC** ✅
- `Role` con permissions JSONField: lista de strings `module.action`.
- `AppUser` vinculado a Role y Tenant; email único por tenant (UniqueConstraint).

**AUTH-03: Multi-Tenancy** ✅
- `TenantContextMiddleware` extrae `tenant_id` del JWT y establece la variable de sesión PG `app.current_tenant_id`.
- Defense-in-Depth: TenantBoundManager (Capa 1) + RLS (Capa 2) + validación IDOR (Capa 3).

**AUTH-04: Rate Limiting** ✅
- 3 niveles: 5 intentos/min → 3 intentos/min → lockout 15min después de 5 fallos.

---

## 4. Requisitos de Interfaces Externas

### 4.1 Interfaces de Usuario

- **Next.js 16 (Implementado — Desarrollo)**:
  - Frontend web actual para desarrollo y prototipado.
  - 9 rutas (login, inventario, ventas, facturación, sync, health, auth-admin, root, protected-layout).
  - JWT en React Context (memoria); TanStack Query v5 para data fetching.

- **Electron POS (Planificado — Producción)**:
  - Interfaz optimizada para teclado/códigos de barras en sucursales.
  - Pantallas principales: POS, búsqueda de productos, cobros, consulta rápida de stock.
  - Base de datos SQLite local cifrada (SQLCipher).

- **Web Admin (Next.js — Futuro)**:
  - Módulos: Inventario, Clientes, Compras, Reportes, Configuración.
  - Soporte para múltiples roles (RBAC).

### 4.2 Interfaces de Software

- **ARCA** ✅ Implementado:
  - WSAA (autenticación) + WSFEv1 (facturación electrónica) — integración SOAP directa.
  - Manejo de homologación (`is_production=False`) vs producción (`is_production=True`).

- **Procesadores de pago (ej. MercadoPago)**: Planificado.

### 4.3 Interfaces de Datos

- **API REST**: OpenAPI 3.1.0 via drf-spectacular. 9 contratos, 79 paths, 154 schemas, 137 operaciones. Disponible en `/api/v1/schema/swagger-ui/`.
- **Exportaciones**: CSV/XLSX acelerado por Rust `export.rs` (spec 020) con fallback Python (openpyxl). Motor disponible, pendiente integración con Módulo REPORTES.
- **Errores**: Problem+JSON (RFC 7807/9457) — campo `type`, `title`, `status`, `detail`.

### 4.4 Interfaces de Comunicaciones

- Todas las comunicaciones backend deben ser **HTTPS** en producción.
- El cliente Electron debe validar certificados del servidor.
- Paginación: cursor-based (`StandardCursorPagination`, PAGE_SIZE=100).
- Throttling: anon=100/hora, user=1000/hora.

---

## 5. Requisitos No Funcionales (NFR)

### 5.1 Rendimiento

- Latencia p95 de principales endpoints de API: < 200ms bajo carga nominal.
- Tiempo de carga de POS en Electron: < 3 segundos en máquinas objetivo (planificado).
- Búsqueda de productos: < 50ms para catálogos de hasta 50.000 ítems (SQLite FTS5 — planificado para Electron).
- **Aceleración Rust/PyO3** ✅: 9 módulos nativos aceleran hot-paths CPU-bound. Benchmarks verificados: AES-256-GCM 8.7x, IVA breakdown 4.4x, CUIT validation 3.1x, stock aggregation 2.1x, endpoint sanitization 2.6x. Todos los dispatchers incluyen fallback a Python puro.

### 5.2 Disponibilidad

- Uptime backend y frontend > 99.9% mensual (planificado en GCP Cloud Run).
- La venta local debe seguir operativa aun con caída total de Internet (cliente Electron — planificado).
- CAEA offline permite facturación sin conexión a ARCA durante el período autorizado.

### 5.3 Seguridad

- Cifrado en tránsito (HTTPS) y en reposo (AES-256-GCM para PII, acelerado por Rust `crypto.rs` 8.7x; Argon2 para passwords).
- RLS estricta en base de datos multi-tenant (Defense-in-Depth, 3 capas).
- Auditoría de acciones sensibles (StockMovement y Comprobante son append-only; inmutables una vez autorizados).
- JWT RS256 con whitelist de algoritmos; HS256/HS384/HS512 explícitamente prohibidos.
- Validación SSRF via Rust `security.rs` (spec 022): 5 formatos IP, 10 rangos CIDR, 9 patrones regex, corpus adversarial de 83 entradas.

### 5.4 Usabilidad

- Un cajero nuevo debe poder operar el POS con menos de 4 horas de capacitación.

### 5.5 Mantenibilidad

- Código siguiendo estándares definidos en `Development Workflow.md` (lint, tests, tipos).
- Arquitectura modular para permitir nuevos módulos sin romper el núcleo.
- ~2,500+ test functions en 111+ archivos (incluyendo 131 tests de integración Rust), 0 regresiones nuevas.
- Cobertura de test verificada en cada feature branch.

---

## 6. Requisitos de Datos y Multi-Tenant

- Todos los datos deben estar asociados a un `tenant_id` (UUID, FK→Tenant).
- Se debe registrar `branch_id` cuando aplique (FK→Branch, `afip_pos_number` único 1-99999).
- Los historiales (StockMovement, Comprobante, PriceHistory, CostHistory) no deben truncarse; enfoque append-only.
- `TenantBoundModel`: clase abstracta base para todos los modelos tenant-aware. `AllObjectsManager` disponible para consultas administrativas.
- `BusinessTemplate`: única excepción — modelo de sistema global (NOT tenant-bound) para onboarding.

---

## 7. Otros Requisitos

- **Localización**: soporte inicial para español (es-AR/es-LATAM). API y documentación en inglés.
- **Regulatorios**: cumplimiento con normativa fiscal vigente ARCA (implementado para Argentina; adaptable a LATAM mediante configuración).
- **Extensibilidad**: el diseño permite la futura incorporación de módulos (E-commerce B2B, App móvil para dueños) sin reescribir el core — gracias al sistema de TenantFieldDefinition y TenantModuleConfig.
- **Objetivo MVP**: Originalmente 1 de mayo de 2026. Actualmente en revisión debido a la fase de investigación de pivot a Vertical SaaS (ver ADR-016). Pendientes antes del lanzamiento: Módulo REPORTES, cliente Electron POS, despliegue GCP, CI/CD.
