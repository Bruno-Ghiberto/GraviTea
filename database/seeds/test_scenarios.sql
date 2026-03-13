-- =============================================================================
-- GRAVITEA ERP Extended Test Scenarios - Hardware Store (Ferreteria)
-- =============================================================================
-- This file contains additional test data for comprehensive testing scenarios.
-- Run AFTER test_data.sql
--
-- Usage:
--   psql -d gravitea_dev -f database/seeds/test_scenarios.sql
--
-- Scenarios covered:
--   - Typical hardware store sales patterns
--   - Contractor bulk purchases
--   - Stock replenishment from warehouse
--   - Seasonal demand (summer garden equipment)
--   - Damaged/returned merchandise
--   - Reserved stock for pending orders
--   - Low stock alerts
-- =============================================================================

-- Temporarily disable RLS for seeding
SET session_replication_role = replica;

-- =============================================================================
-- EXTENDED MOVEMENT HISTORY - Hardware Store Patterns
-- =============================================================================

-- ============ CASA CENTRAL (branch_id = 1) - High traffic main store ============

INSERT INTO inventario_stockmovement (tenant_id, branch_id, product_id, movement_type, quantity, reference, notes, created_by_id, created_at)
VALUES
    -- ==========  LUNES - Inicio de semana, ventas normales ==========
    -- Electricista profesional comprando herramientas
    (1, 1, 1, 'sale', -1, 'VTA-2025-001001', 'Venta electricista - Taladro DeWalt', 3, NOW() - INTERVAL '7 days'),
    (1, 1, 23, 'sale', -2, 'VTA-2025-001001', 'Destornilladores aislados 1000V', 3, NOW() - INTERVAL '7 days'),
    (1, 1, 74, 'sale', -3, 'VTA-2025-001001', 'Anteojos seguridad', 3, NOW() - INTERVAL '7 days'),

    -- Constructor comprando fijaciones
    (1, 1, 81, 'sale', -5, 'VTA-2025-001002', 'Tornillos autoperforantes x5 cajas', 3, NOW() - INTERVAL '7 days'),
    (1, 1, 83, 'sale', -3, 'VTA-2025-001002', 'Tarugos nylon surtidos', 3, NOW() - INTERVAL '7 days'),
    (1, 1, 67, 'sale', -2, 'VTA-2025-001002', 'Mechas widia pared', 3, NOW() - INTERVAL '7 days'),

    -- ==========  MARTES - Soldador comprando insumos ==========
    (1, 1, 57, 'sale', -2, 'VTA-2025-001010', 'Electrodos punta azul - Taller mecanico', 3, NOW() - INTERVAL '6 days'),
    (1, 1, 53, 'sale', -1, 'VTA-2025-001010', 'Mascara fotosensible', 3, NOW() - INTERVAL '6 days'),
    (1, 1, 73, 'sale', -5, 'VTA-2025-001010', 'Guantes cuero descarne x5 pares', 3, NOW() - INTERVAL '6 days'),
    (1, 1, 59, 'sale', -2, 'VTA-2025-001010', 'Delantal cuero soldador', 3, NOW() - INTERVAL '6 days'),

    -- Venta mostrador - cliente particular
    (1, 1, 36, 'sale', -3, 'VTA-2025-001011', 'Cintas metricas 5m', 3, NOW() - INTERVAL '6 days'),
    (1, 1, 40, 'sale', -5, 'VTA-2025-001011', 'Cutters profesionales', 3, NOW() - INTERVAL '6 days'),
    (1, 1, 97, 'sale', -4, 'VTA-2025-001011', 'WD-40 lubricante', 3, NOW() - INTERVAL '6 days'),

    -- ==========  MIERCOLES - Contratista grande (pedido especial) ==========
    (1, 1, 4, 'sale', -3, 'VTA-2025-001020', 'Amoladoras 115mm - Obra construccion', 3, NOW() - INTERVAL '5 days'),
    (1, 1, 61, 'sale', -10, 'VTA-2025-001020', 'Discos corte metal x10 cajas', 3, NOW() - INTERVAL '5 days'),
    (1, 1, 63, 'sale', -5, 'VTA-2025-001020', 'Discos desbaste', 3, NOW() - INTERVAL '5 days'),
    (1, 1, 77, 'sale', -10, 'VTA-2025-001020', 'Cascos seguridad - Obra', 3, NOW() - INTERVAL '5 days'),
    (1, 1, 78, 'sale', -10, 'VTA-2025-001020', 'Chalecos reflectivos', 3, NOW() - INTERVAL '5 days'),
    (1, 1, 71, 'sale', -5, 'VTA-2025-001020', 'Zapatos seguridad', 3, NOW() - INTERVAL '5 days'),

    -- ==========  JUEVES - Reposicion desde deposito ==========
    (1, 1, 4, 'transfer_in', 10, 'TRF-2025-001001', 'Reposicion amoladoras desde deposito', 5, NOW() - INTERVAL '4 days'),
    (1, 1, 61, 'transfer_in', 20, 'TRF-2025-001001', 'Reposicion discos corte', 5, NOW() - INTERVAL '4 days'),
    (1, 1, 77, 'transfer_in', 15, 'TRF-2025-001001', 'Reposicion cascos', 5, NOW() - INTERVAL '4 days'),
    (1, 4, 4, 'transfer_out', -10, 'TRF-2025-001001', 'Envio a Casa Central', 5, NOW() - INTERVAL '4 days'),
    (1, 4, 61, 'transfer_out', -20, 'TRF-2025-001001', 'Envio a Casa Central', 5, NOW() - INTERVAL '4 days'),
    (1, 4, 77, 'transfer_out', -15, 'TRF-2025-001001', 'Envio a Casa Central', 5, NOW() - INTERVAL '4 days'),

    -- Carpintero comprando herramientas madera
    (1, 1, 6, 'sale', -1, 'VTA-2025-001030', 'Sierra circular carpintero', 3, NOW() - INTERVAL '4 days'),
    (1, 1, 13, 'sale', -1, 'VTA-2025-001030', 'Cepillo electrico madera', 3, NOW() - INTERVAL '4 days'),
    (1, 1, 68, 'sale', -2, 'VTA-2025-001030', 'Mechas paleta madera', 3, NOW() - INTERVAL '4 days'),
    (1, 1, 39, 'sale', -1, 'VTA-2025-001030', 'Escuadra carpintero', 3, NOW() - INTERVAL '4 days'),

    -- ==========  VIERNES - Dia fuerte de ventas ==========
    -- Plomero
    (1, 1, 28, 'sale', -2, 'VTA-2025-001040', 'Llaves Stillson plomeria', 3, NOW() - INTERVAL '3 days'),
    (1, 1, 96, 'sale', -10, 'VTA-2025-001040', 'Cinta teflon x10 rollos', 3, NOW() - INTERVAL '3 days'),
    (1, 1, 92, 'sale', -5, 'VTA-2025-001040', 'Silicona neutra', 3, NOW() - INTERVAL '3 days'),

    -- Cliente jardineria (temporada alta)
    (1, 1, 44, 'sale', -1, 'VTA-2025-001041', 'Desmalezadora', 3, NOW() - INTERVAL '3 days'),
    (1, 1, 49, 'sale', -3, 'VTA-2025-001041', 'Tijeras de podar', 3, NOW() - INTERVAL '3 days'),
    (1, 1, 50, 'sale', -2, 'VTA-2025-001041', 'Manguera riego 25m', 3, NOW() - INTERVAL '3 days'),

    -- Mecanico automotriz
    (1, 1, 21, 'sale', -1, 'VTA-2025-001042', 'Juego llaves combinadas', 3, NOW() - INTERVAL '3 days'),
    (1, 1, 29, 'sale', -2, 'VTA-2025-001042', 'Llaves Allen set', 3, NOW() - INTERVAL '3 days'),
    (1, 1, 24, 'sale', -2, 'VTA-2025-001042', 'Pinzas universales', 3, NOW() - INTERVAL '3 days'),

    -- ==========  SABADO - Ajustes de inventario ==========
    (1, 1, 8, 'adjustment', -1, 'ADJ-2025-001001', 'Lijadora orbital danada - devolucion proveedor', 5, NOW() - INTERVAL '2 days'),
    (1, 1, 92, 'adjustment', -2, 'ADJ-2025-001002', 'Silicona vencida - baja', 5, NOW() - INTERVAL '2 days'),
    (1, 1, 70, 'adjustment', 5, 'ADJ-2025-001003', 'Correccion conteo puntas atornillador', 5, NOW() - INTERVAL '2 days'),

    -- ==========  DOMINGO - Ventas menores ==========
    (1, 1, 22, 'sale', -2, 'VTA-2025-001050', 'Juegos destornilladores - venta domingo', 3, NOW() - INTERVAL '1 day'),
    (1, 1, 94, 'sale', -3, 'VTA-2025-001050', 'Cinta aisladora', 3, NOW() - INTERVAL '1 day'),
    (1, 1, 91, 'sale', -2, 'VTA-2025-001050', 'Adhesivo Poxiran', 3, NOW() - INTERVAL '1 day');

-- ============ SUCURSAL NORTE (branch_id = 2) - Zona comercial/oficinas ============
INSERT INTO inventario_stockmovement (tenant_id, branch_id, product_id, movement_type, quantity, reference, notes, created_by_id, created_at)
VALUES
    -- Mantenimiento de edificios
    (1, 2, 12, 'sale', -2, 'VTA-2025-002001', 'Pistolas calor - mantenimiento edificio', 4, NOW() - INTERVAL '6 days'),
    (1, 2, 97, 'sale', -6, 'VTA-2025-002001', 'WD-40 lubricante', 4, NOW() - INTERVAL '6 days'),
    (1, 2, 83, 'sale', -4, 'VTA-2025-002001', 'Tarugos nylon', 4, NOW() - INTERVAL '5 days'),
    (1, 2, 82, 'sale', -3, 'VTA-2025-002001', 'Tornillos fix madera', 4, NOW() - INTERVAL '5 days'),

    -- Empresa limpieza comprando EPP
    (1, 2, 72, 'sale', -10, 'VTA-2025-002010', 'Guantes nitrilo x10 cajas - empresa limpieza', 4, NOW() - INTERVAL '4 days'),
    (1, 2, 80, 'sale', -5, 'VTA-2025-002010', 'Mascarillas N95', 4, NOW() - INTERVAL '4 days'),
    (1, 2, 74, 'sale', -10, 'VTA-2025-002010', 'Anteojos seguridad', 4, NOW() - INTERVAL '4 days'),

    -- Reposicion desde deposito
    (1, 2, 72, 'transfer_in', 15, 'TRF-2025-002001', 'Reposicion guantes desde deposito', 5, NOW() - INTERVAL '3 days'),
    (1, 4, 72, 'transfer_out', -15, 'TRF-2025-002001', 'Envio a Sucursal Norte', 5, NOW() - INTERVAL '3 days'),

    -- Electricista zona norte
    (1, 2, 94, 'sale', -8, 'VTA-2025-002020', 'Cinta aisladora - electricista', 4, NOW() - INTERVAL '2 days'),
    (1, 2, 23, 'sale', -1, 'VTA-2025-002020', 'Destornilladores aislados', 4, NOW() - INTERVAL '2 days');

-- ============ SUCURSAL ZONA OESTE (branch_id = 3) - Zona industrial ============
INSERT INTO inventario_stockmovement (tenant_id, branch_id, product_id, movement_type, quantity, reference, notes, created_by_id, created_at)
VALUES
    -- Taller metalurgico grande
    (1, 3, 51, 'sale', -2, 'VTA-2025-003001', 'Soldadoras Inverter - Taller metalurgico', 3, NOW() - INTERVAL '5 days'),
    (1, 3, 57, 'sale', -5, 'VTA-2025-003001', 'Electrodos x5 bolsas', 3, NOW() - INTERVAL '5 days'),
    (1, 3, 58, 'sale', -3, 'VTA-2025-003001', 'Alambre soldar', 3, NOW() - INTERVAL '5 days'),
    (1, 3, 60, 'sale', -2, 'VTA-2025-003001', 'Escuadras magneticas', 3, NOW() - INTERVAL '5 days'),

    -- Fabrica local
    (1, 3, 5, 'sale', -2, 'VTA-2025-003010', 'Amoladoras 230mm - Fabrica', 3, NOW() - INTERVAL '4 days'),
    (1, 3, 62, 'sale', -8, 'VTA-2025-003010', 'Discos corte 180mm', 3, NOW() - INTERVAL '4 days'),
    (1, 3, 64, 'sale', -6, 'VTA-2025-003010', 'Discos flap lija', 3, NOW() - INTERVAL '4 days'),

    -- Compra maquinaria pesada
    (1, 3, 19, 'sale', -1, 'VTA-2025-003020', 'Compresor 50L - Taller neumatico', 3, NOW() - INTERVAL '3 days'),
    (1, 3, 18, 'sale', -1, 'VTA-2025-003020', 'Aspiradora industrial', 3, NOW() - INTERVAL '3 days'),

    -- Ajuste por robo menor
    (1, 3, 40, 'adjustment', -5, 'ADJ-2025-003001', 'Diferencia inventario - cutters', 2, NOW() - INTERVAL '2 days');

-- =============================================================================
-- UPDATE STOCK SNAPSHOTS TO REFLECT MOVEMENTS
-- =============================================================================

-- Actualizar stock Casa Central basado en ventas
UPDATE inventario_stocksnapshot SET
    quantity = quantity - 1 - 3 + 10,  -- Amoladoras 115mm
    last_movement_at = NOW(),
    updated_at = NOW()
WHERE branch_id = 1 AND product_id = 4;

UPDATE inventario_stocksnapshot SET
    quantity = quantity - 10 + 20,  -- Discos corte
    last_movement_at = NOW(),
    updated_at = NOW()
WHERE branch_id = 1 AND product_id = 61;

UPDATE inventario_stocksnapshot SET
    quantity = quantity - 10 + 15,  -- Cascos
    last_movement_at = NOW(),
    updated_at = NOW()
WHERE branch_id = 1 AND product_id = 77;

-- Actualizar Deposito (descontar transferencias)
UPDATE inventario_stocksnapshot SET
    quantity = quantity - 10,
    last_movement_at = NOW(),
    updated_at = NOW()
WHERE branch_id = 4 AND product_id = 4;

UPDATE inventario_stocksnapshot SET
    quantity = quantity - 20,
    last_movement_at = NOW(),
    updated_at = NOW()
WHERE branch_id = 4 AND product_id = 61;

UPDATE inventario_stocksnapshot SET
    quantity = quantity - 15 - 15,  -- Envios a ambas sucursales
    last_movement_at = NOW(),
    updated_at = NOW()
WHERE branch_id = 4 AND product_id = 77;

-- =============================================================================
-- LOW STOCK SCENARIOS (For Alert Testing)
-- =============================================================================

-- Productos con stock critico para probar alertas
UPDATE inventario_stocksnapshot SET
    quantity = 2,  -- Critico - producto popular
    last_movement_at = NOW(),
    updated_at = NOW()
WHERE branch_id = 1 AND product_id = 61;  -- Discos corte 115mm

UPDATE inventario_stocksnapshot SET
    quantity = 1,  -- Casi agotado
    last_movement_at = NOW(),
    updated_at = NOW()
WHERE branch_id = 2 AND product_id = 72;  -- Guantes nitrilo

UPDATE inventario_stocksnapshot SET
    quantity = 0,  -- Sin stock
    last_movement_at = NOW(),
    updated_at = NOW()
WHERE branch_id = 3 AND product_id = 51;  -- Soldadoras Inverter

UPDATE inventario_stocksnapshot SET
    quantity = 3,  -- Stock bajo maquinaria cara
    last_movement_at = NOW(),
    updated_at = NOW()
WHERE branch_id = 1 AND product_id = 10;  -- Rotomartillo SDS Plus

-- =============================================================================
-- RESERVED STOCK SCENARIOS (Pending Orders)
-- =============================================================================

-- Pedidos pendientes de entrega
UPDATE inventario_stocksnapshot SET
    reserved_quantity = 5,  -- Reservado para constructor
    updated_at = NOW()
WHERE branch_id = 1 AND product_id = 4;  -- 5 Amoladoras reservadas

UPDATE inventario_stocksnapshot SET
    reserved_quantity = 3,  -- Pedido empresa
    updated_at = NOW()
WHERE branch_id = 1 AND product_id = 51;  -- 3 Soldadoras reservadas

UPDATE inventario_stocksnapshot SET
    reserved_quantity = 20,  -- Pedido grande EPP
    updated_at = NOW()
WHERE branch_id = 1 AND product_id = 77;  -- 20 Cascos reservados

UPDATE inventario_stocksnapshot SET
    reserved_quantity = 10,  -- Reserva insumos obra
    updated_at = NOW()
WHERE branch_id = 4 AND product_id = 81;  -- Tornillos deposito

-- =============================================================================
-- ADDITIONAL PRODUCTS FOR EDGE CASE TESTING
-- =============================================================================

-- Producto descontinuado
INSERT INTO inventario_product (id, tenant_id, name, sku, barcode, category_id, base_price, cost_price, is_active, created_at, updated_at)
VALUES
    (103, 1, 'Taladro Modelo Antiguo (Descontinuado)', 'HE999', '7790001999999', 9, 95000.00, 73000.00, false, NOW() - INTERVAL '180 days', NOW())
ON CONFLICT (id) DO UPDATE SET
    is_active = false,
    updated_at = NOW();

-- Producto nuevo sin stock aun
INSERT INTO inventario_product (id, tenant_id, name, sku, barcode, category_id, base_price, cost_price, is_active, created_at, updated_at)
VALUES
    (104, 1, 'Taladro Inalambrico 20V NUEVO', 'HE101', '7790001000101', 9, 225000.00, 173000.00, true, NOW(), NOW())
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    updated_at = NOW();

-- Producto premium alto valor
INSERT INTO inventario_product (id, tenant_id, name, sku, barcode, category_id, base_price, cost_price, is_active, created_at, updated_at)
VALUES
    (105, 1, 'Centro de Mecanizado CNC Portatil', 'HE102', '7790001000102', 1, 8500000.00, 6500000.00, true, NOW(), NOW())
ON CONFLICT (id) DO UPDATE SET
    base_price = 8500000.00,
    updated_at = NOW();

SELECT setval('inventario_product_id_seq', (SELECT MAX(id) FROM inventario_product));

-- =============================================================================
-- ROLE-BASED TEST DATA
-- =============================================================================

-- Roles para Ferreteria El Constructor
INSERT INTO auth_role (id, tenant_id, name, permissions, is_active, created_at, updated_at)
VALUES
    (1, 1, 'Administrador', '["*"]', true, NOW(), NOW()),
    (2, 1, 'Gerente', '["inventory.*", "sales.*", "reports.read", "users.read"]', true, NOW(), NOW()),
    (3, 1, 'Vendedor', '["sales.create", "sales.read", "inventory.read", "products.read"]', true, NOW(), NOW()),
    (4, 1, 'Deposito', '["inventory.*", "transfers.*"]', true, NOW(), NOW()),
    (5, 1, 'Solo Lectura', '["*.read"]', true, NOW(), NOW()),
    (6, 2, 'Administrador', '["*"]', true, NOW(), NOW())
ON CONFLICT (id) DO UPDATE SET
    permissions = EXCLUDED.permissions,
    updated_at = NOW();

SELECT setval('auth_role_id_seq', (SELECT MAX(id) FROM auth_role));

-- =============================================================================
-- PRICE LIST TEST DATA
-- =============================================================================

-- Lista de precios para diferentes tipos de cliente
INSERT INTO inventario_pricelist (id, tenant_id, name, is_default, discount_percentage, is_active, created_at, updated_at)
VALUES
    (1, 1, 'Precio Mostrador', true, 0.00, true, NOW(), NOW()),
    (2, 1, 'Precio Contratista', false, 10.00, true, NOW(), NOW()),
    (3, 1, 'Precio Mayorista', false, 15.00, true, NOW(), NOW()),
    (4, 1, 'Precio Empleado', false, 20.00, true, NOW(), NOW())
ON CONFLICT (id) DO UPDATE SET
    discount_percentage = EXCLUDED.discount_percentage,
    updated_at = NOW();

SELECT setval('inventario_pricelist_id_seq', (SELECT MAX(id) FROM inventario_pricelist));

-- =============================================================================
-- VERIFICATION
-- =============================================================================

-- Re-enable RLS
SET session_replication_role = DEFAULT;

-- Summary of extended test data
SELECT 'Extended Test Scenarios Loaded - Hardware Store' AS status;

SELECT
    'Stock Movements' AS entity,
    COUNT(*) AS count
FROM inventario_stockmovement
UNION ALL
SELECT
    'Reserved Stock Items' AS entity,
    COUNT(*) AS count
FROM inventario_stocksnapshot WHERE reserved_quantity > 0
UNION ALL
SELECT
    'Low Stock Items (<=5)' AS entity,
    COUNT(*) AS count
FROM inventario_stocksnapshot WHERE quantity <= 5
UNION ALL
SELECT
    'Out of Stock Items' AS entity,
    COUNT(*) AS count
FROM inventario_stocksnapshot WHERE quantity = 0;

-- Movement summary by type
SELECT
    movement_type,
    COUNT(*) AS count,
    SUM(quantity) AS total_quantity
FROM inventario_stockmovement
WHERE tenant_id = 1
GROUP BY movement_type
ORDER BY movement_type;

-- Top 10 productos mas vendidos
SELECT
    p.name AS producto,
    SUM(ABS(sm.quantity)) AS total_vendido
FROM inventario_stockmovement sm
JOIN inventario_product p ON p.id = sm.product_id
WHERE sm.movement_type = 'sale' AND sm.tenant_id = 1
GROUP BY p.id, p.name
ORDER BY total_vendido DESC
LIMIT 10;

-- =============================================================================
-- END OF EXTENDED SCENARIOS
-- =============================================================================
