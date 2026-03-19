# ERP Integral para Acopios de Granos

## Descripcion General

Sistema de gestion diseñado especificamente para
acopiadores-consignatarios de granos pequenos y medianos
de la region pampeana argentina.

Combina la operacion diaria de planta (recepcion, analisis
de calidad, almacenamiento) con la gestion comercial (cuentas
corrientes, liquidaciones, canje de insumos) y un ecosistema
de inteligencia artificial que transforma los datos operativos
en ventaja competitiva.

El sistema funciona con o sin conexion a internet, permitiendo
operar durante la cosecha en plantas rurales sin cobertura y
sincronizar cuando la conectividad se restablece.


## Mapa de Modulos

```
+==============================================================+
|                                                              |
|              ERP  INTEGRAL  PARA  ACOPIOS                    |
|                                                              |
+==============================================================+
|                                                              |
|  OPERACIONES DE PLANTA                                       |
|  ---------------------                                       |
|                                                              |
|  +------------------------+ +------------------------------+ |
|  |                        | |                              | |
|  |  RECEPCION (ROMANEO)   | |  ALMACENAMIENTO              | |
|  |                        | |                              | |
|  |  * Ingreso de camion   | |  * Silos y celdas con        | |
|  |  * Carta de Porte      | |    capacidad y estado        | |
|  |    y CTG               | |  * Asignacion por tipo,      | |
|  |  * Pesada bruta        | |    calidad y campana         | |
|  |  * Calado y muestreo   | |  * Posicion de granos:       | |
|  |  * Analisis de calidad | |    que hay, donde, de quien  | |
|  |  * Grado comercial     | |  * Gestion por campana       | |
|  |  * Calculo de mermas   | |    (24/25, 25/26 ...)        | |
|  |  * Tara                | |  * Movimientos entre silos   | |
|  |  * Peso neto conforme  | |                              | |
|  |  * Boleta de romaneo   | +------------------------------+ |
|  |                        | |                              | |
|  |                        | |  CALIDAD                     | |
|  |                        | |                              | |
|  |                        | |  * Tablas de tolerancia      | |
|  |                        | |    por grano (Camara         | |
|  |                        | |    Arbitral de Rosario)      | |
|  |                        | |  * Bonificaciones y rebajas  | |
|  |                        | |  * Tablas de merma           | |
|  |                        | |    por secado                | |
|  |                        | |  * Parametros configurables  | |
|  |                        | |    por planta                | |
|  |                        | |                              | |
|  +------------------------+ +------------------------------+ |
|                                                              |
+==============================================================+
|                                                              |
|  GESTION COMERCIAL                                           |
|  -----------------                                           |
|                                                              |
|  +------------------------+ +------------------------------+ |
|  |                        | |                              | |
|  |  CUENTAS CORRIENTES    | |  LIQUIDACIONES               | |
|  |                        | |                              | |
|  |  * Cuenta por          | |  * Liquidacion Primaria      | |
|  |    productor           | |    (Form. 1116-C)            | |
|  |  * Saldo en granos     | |  * Liquidacion Secundaria    | |
|  |    (kg por tipo)       | |    (Form. 1116-B)            | |
|  |  * Saldo en pesos      | |  * Retenciones               | |
|  |  * Saldo en dolares    | |    (IVA, Ganancias, IIBB)    | |
|  |  * Historial de        | |  * Integracion electronica   | |
|  |    movimientos         | |    con ARCA (WSLPG)          | |
|  |  * Extractos           | |  * Estado SISA del productor | |
|  |                        | |  * Precio por tn / quintal   | |
|  |                        | |                              | |
|  +------------------------+ +------------------------------+ |
|                                                              |
|  +------------------------+ +------------------------------+ |
|  |                        | |                              | |
|  |  FACTURACION           | |  AGRONOMIA (INSUMOS)         | |
|  |                        | |                              | |
|  |  * Factura electronica | |  * Catalogo de productos     | |
|  |    A / B / C           | |    (semillas, fertilizantes, | |
|  |  * Servicios de        | |     agroquimicos, repuestos) | |
|  |    planta: secada,     | |  * Control de stock por      | |
|  |    zarandeo,           | |    lote y vencimiento        | |
|  |    almacenaje,         | |  * Compras a distribuidores  | |
|  |    paritaria           | |  * Ventas a productores      | |
|  |  * Notas de credito    | |  * Listas de precios         | |
|  |    y debito            | |                              | |
|  |  * CAE / CAEA          | |                              | |
|  |    (modo offline)      | |                              | |
|  |                        | |                              | |
|  +------------------------+ +------------------------------+ |
|                                                              |
|  +----------------------------------------------------------+|
|  |                                                          ||
|  |  CANJE                                                   ||
|  |                                                          ||
|  |  El productor entrega granos y retira insumos.           ||
|  |  El sistema compensa automaticamente: credito            ||
|  |  en granos (valuado a precio de pizarra del dia)         ||
|  |  contra debito en insumos. Genera la documentacion       ||
|  |  fiscal correspondiente.                                 ||
|  |                                                          ||
|  +----------------------------------------------------------+|
|                                                              |
+==============================================================+
|                                                              |
|  INTELIGENCIA ARTIFICIAL                                     |
|  -----------------------                                     |
|                                                              |
|  +------------------------+ +------------------------------+ |
|  |                        | |                              | |
|  |  DETECCION Y           | |  OPTIMIZACION                | |
|  |  PREDICCION            | |                              | |
|  |                        | |  * Asignacion inteligente    | |
|  |  * Deteccion de        | |    de silos (maximizar       | |
|  |    anomalias en        | |    calidad de mezcla)        | |
|  |    balanza (fraude)    | |  * Pronostico de precios     | |
|  |  * Prediccion de       | |    (pizarra local y futuros) | |
|  |    calidad de grano    | |  * Prediccion de volumen     | |
|  |    almacenado          | |    de cosecha entrante       | |
|  |  * Alerta temprana     | |  * Programacion optima       | |
|  |    de estado SISA      | |    de aireacion              | |
|  |    del productor       | |                              | |
|  |                        | |                              | |
|  +------------------------+ +------------------------------+ |
|                                                              |
|  +------------------------+ +------------------------------+ |
|  |                        | |                              | |
|  |  VISION ARTIFICIAL     | |  ASISTENTE DE CONOCIMIENTO   | |
|  |                        | |                              | |
|  |  * Lectura automatica  | |  * Consultas en lenguaje     | |
|  |    de Carta de Porte   | |    natural sobre normativa   | |
|  |    (OCR)               | |    y estandares de calidad   | |
|  |  * Clasificacion       | |  * Recomendaciones basadas   | |
|  |    visual de grano     | |    en datos historicos       | |
|  |    (camara)            | |  * Alertas regulatorias      | |
|  |                        | |                              | |
|  +------------------------+ +------------------------------+ |
|                                                              |
+==============================================================+
|                                                              |
|  REPORTES Y ADMINISTRACION                                   |
|  -------------------------                                   |
|                                                              |
|  +------------------------+ +------------------------------+ |
|  |                        | |                              | |
|  |  REPORTES              | |  ADMINISTRACION              | |
|  |                        | |                              | |
|  |  * Posicion diaria     | |  * Usuarios y roles por      | |
|  |    de granos           | |    planta (balancero,        | |
|  |  * Extracto de cuenta  | |    recibidor, laboratorista, | |
|  |    corriente           | |    administrador)            | |
|  |  * Resumen de campana  | |  * Multiples plantas         | |
|  |  * Libro de            | |  * Tablas de calidad y       | |
|  |    movimientos         | |    tarifas por planta        | |
|  |  * Exportacion a       | |  * Certificados ARCA         | |
|  |    formatos fiscales   | |  * Sincronizacion offline    | |
|  |                        | |  * Auditoria de operaciones  | |
|  |                        | |                              | |
|  +------------------------+ +------------------------------+ |
|                                                              |
+==============================================================+
```


## Flujo Operativo Principal

```
              FLUJO DE RECEPCION DE GRANOS
============================================================

+-------------+  +-------------+  +-------------+  +--------+
|             |  |             |  |             |  |        |
|  Llegada    |  |  Pesada     |  |  Calado y   |  |Calculo |
|  del camion |->|  bruta      |->|  analisis   |->|de merma|
|  con CPE /  |  |  (balanza)  |  |  de calidad |  |y peso  |
|  CTG        |  |             |  |  (laborat.) |  |neto    |
|             |  |             |  |             |  |conforme|
+-------------+  +-------------+  +-------------+  +---+----+
                                                        |
                                                        v
                                                   +--------+
                                                   |        |
                                                   |Boleta  |
                                                   |de      |
                                                   |Romaneo |
                                                   |        |
                                                   +---+----+
                                                       |
                                        +--------------+
                                        |              |
                                        v              v
                                  +-----------+  +-----------+
                                  |           |  |           |
                                  |Asignacion |  | Acreditar |
                                  |de silo /  |  | en cuenta |
                                  |celda      |  | corriente |
                                  |           |  | del       |
                                  |           |  | productor |
                                  +-----------+  +-----+-----+
                                                       |
                                        +--------------+
                                        |              |
                                        v              v
                                  +-----------+  +-----------+
                                  |           |  |           |
                                  |Liquidacion|  | Tara      |
                                  |(1116-C)   |  | (camion   |
                                  |o canje    |  |  vacio    |
                                  |por insumos|  |  sale)    |
                                  |           |  |           |
                                  +-----------+  +-----------+
```


## Inventario Dual

El sistema gestiona dos tipos de inventario fundamentalmente
distintos que coexisten dentro de la misma plataforma:

```
+==============================================================+
|                                                              |
|                     INVENTARIO DUAL                          |
|                                                              |
|  +------------------------+    +------------------------+    |
|  |                        |    |                        |    |
|  |  GRANOS                |    |  INSUMOS (AGRONOMIA)   |    |
|  |  (activo liquido)      |    |  (activo contable)     |    |
|  |                        |    |                        |    |
|  |  Inventario continuo   |    |  Inventario discreto   |    |
|  |  medido en kg.         |    |  medido en unidades.   |    |
|  |                        |    |                        |    |
|  |  El stock se deriva    |    |  El stock se cuenta:   |    |
|  |  del peso neto         |    |  N unidades entran,    |    |
|  |  conforme de cada      |    |  N unidades salen.     |    |
|  |  romaneo, ajustado     |    |                        |    |
|  |  por calidad,          |    |  Control por lote,     |    |
|  |  campana y mermas.     |    |  codigo de barras y    |    |
|  |                        |    |  fecha de vencimiento. |    |
|  |  Segregado por:        |    |                        |    |
|  |  tipo de grano,        |    |  Segregado por:        |    |
|  |  campana, calidad,     |    |  categoria, proveedor, |    |
|  |  silo y productor.     |    |  lote y sucursal.      |    |
|  |                        |    |                        |    |
|  +----------+-------------+    +-------------+----------+    |
|             |                                |               |
|             +---------------+----------------+               |
|                             |                                |
|                             v                                |
|              +------------------------------+                |
|              |                              |                |
|              |  CUENTA CORRIENTE            |                |
|              |  DEL PRODUCTOR               |                |
|              |                              |                |
|              |  Unifica ambos mundos:       |                |
|              |  creditos en granos contra   |                |
|              |  debitos en insumos.         |                |
|              |                              |                |
|              |  Saldo en kg (por grano)     |                |
|              |  Saldo en ARS                |                |
|              |  Saldo en USD                |                |
|              |                              |                |
|              +------------------------------+                |
|                                                              |
+==============================================================+
```
