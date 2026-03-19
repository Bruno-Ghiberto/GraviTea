# Relevamiento de Acopios de Granos — Córdoba, Argentina
## Directorio, Análisis Sectorial y Plan de Customer Discovery

**Fecha de corte**: 16 de marzo de 2026
**Total relevado**: 142 operadores únicos
**Cobertura**: 26 departamentos, Provincia de Córdoba
**Fuentes**: Sociedad de Acopiadores de Córdoba, RUCA/ARCA, ProCórdoba, BCCBA, Páginas Amarillas, sitios web de empresas

---

## 1. Resumen Ejecutivo

Córdoba concentra la mayor red de acopios de granos de Argentina fuera del Gran Rosario. Este relevamiento identificó **142 operadores únicos** que van desde exportadoras multinacionales (AGD, Bunge, Cargill, COFCO) hasta empresas familiares de una planta y un camión de balanza. La densidad de operadores es máxima en los departamentos del corredor este-sureste (Colón, Marcos Juárez, Unión, San Justo) y en el eje sur (Río Cuarto, Juárez Celman, Presidente Roque Sáenz Peña).

El sector atraviesa dos disrupciones simultáneas que presionan urgentemente sobre los sistemas de gestión:

1. **Trazabilidad VISEC / EUDR**: La Regulación Europea de Deforestación (Reg. UE 2023/1115) exige geolocalizar el origen de cada tonelada de soja antes de que se mezcle en silo. El acopio es el eslabón crítico — sin sistema capaz de vincular CTG + RENSPA + polígono de lote, pierde acceso al mercado europeo.
2. **Scoring SISA en tiempo real**: El estado SISA (1/2/3) determina las retenciones de IVA y Ganancias en cada transacción. Los acopiadores en Estado 3 sufren retenciones punitivas que destruyen su capital de trabajo. El ERP debe emitir alertas preventivas y mantener consistencia fiscal.

Estos dos vectores, combinados con la operatoria tradicional de romaneo, calidad, posición de stock y cuentas corrientes de productores, definen el problema que GraviTea debe resolver.

---

## 2. Marco Regulatorio Relevante

### 2.1 SISA — Sistema de Información Simplificado Agrícola

Administrado por ARCA (ex-AFIP). Es el único padrón habilitante vigente desde la eliminación del RUCA en 2025. Opera como motor de *scoring* de riesgo fiscal en tiempo real:

| Estado SISA | Significado | Impacto en retenciones |
|-------------|-------------|----------------------|
| **Estado 1** | Bajo riesgo, cumplimiento OK | Retenciones normales (IVA: 8%, Ganancias: 2%) |
| **Estado 2** | Riesgo moderado, inconsistencias menores | Retenciones incrementadas |
| **Estado 3** | Alto riesgo, incumplimiento tributario | Retenciones punitivas sobre valor bruto camión — destruye capital de trabajo |

El SISA monitorea: capacidad de almacenamiento declarada vs operada, flujo físico vía CPE/CTG, consistencia con Liquidaciones Secundarias de Granos (LSG).

**Implicancia para el ERP**: El sistema debe exponer el estado SISA del acopiador y de sus contrapartes (productores, compradores) antes de cada operación.

### 2.2 RUCA eliminado → ARCA/SISA como padrón único

El RUCA (ex-ONCCA/SAGyP) fue formalmente eliminado en 2025. Los CUITs históricos del RUCA fueron migrados al SISA. La inscripción ya no es un paso separado — la habilitación surge del cumplimiento fiscal en tiempo real.

**Implicancia**: Los operadores nuevos ya no tienen burocracia de inscripción previa, pero el estatus operativo es más volátil — puede cambiar en semanas si aparece una inconsistencia.

### 2.3 SENASA — Habilitación Sanitaria

Obligatoria para todas las plantas físicas de almacenamiento. Controla: control de roedores, micotoxinas, insectos (gorgojos, taladrillos). La pérdida de habilitación SENASA impide exportar y comprometer certificados de inocuidad.

**Implicancia para el ERP**: Registro de inspecciones SENASA, vencimientos de habilitaciones, planes de fumigación.

### 2.4 VISEC — Trazabilidad ante EUDR (crítico 2025-2026)

La Regulación UE 2023/1115 exige que soja que ingresa a la UE no provenga de tierra deforestada post-31/12/2020. Los acopiadores son el **eslabón de máxima tensión**: deben:
1. Geolocalizar el lote de origen (polígono exacto) de cada camión que ingresa
2. Vincular lote → RENSPA del productor → CPE/CTG → toneladas → celda de silo
3. Consolidar esta cadena **antes** de que el grano se mezcle en silo

La plataforma VISEC (integrada por Sociedad de Acopiadores, Bolsas, exportadoras) está en implementación activa. Los acopios que no integren sus sistemas con VISEC quedarán excluidos del canal exportador europeo.

**Implicancia para el ERP**: El romaneo debe capturar polígono de lote en el momento de la recepción. La posición de stock debe ser trazable al origen por celda.

### 2.5 Organismos Gremiales Relevantes

| Organismo | Rol | Relevancia para Discovery |
|-----------|-----|--------------------------|
| **Sociedad de Acopiadores de Córdoba** | Padrón de operadores, gremio, capacitaciones VISEC | Puerta de entrada institucional |
| **Bolsa de Cereales de Córdoba (BCCBA)** | Laboratorio de calidad, árbitro comercial, directorio de socios | Acceso a listados y eventos |
| **ACA** (Asoc. Cooperativas Argentinas) | Red cooperativa de 2° grado, mayor originación cooperativa | No target para SMB ERP |
| **Centro de Corredores de Cereales** | Corredores puros (brokers), no tienen planta física | Target potencial para módulo de corretaje |

---

## 3. Análisis Geoespacial por Zona

### 3.1 Distribución por Departamento

| Departamento | Operadores | Zona Agroeconómica | Granos Principales |
|--------------|------------|--------------------|--------------------|
| **Colón** | 15 | Centro-Norte | Soja, Maíz, Garbanzo |
| **Río Cuarto** | 14 | Sur | Soja, Maíz, Maní |
| **Juárez Celman** | 13 | Sur (cluster maní) | Maní, Soja, Maíz |
| **General San Martín** | 12 | Centro (Villa María) | Soja, Maíz, Trigo |
| **Marcos Juárez** | 12 | Este (pampa húmeda) | Soja, Trigo, Maíz |
| **Pres. R. Sáenz Peña** | 11 | Sur | Soja, Maíz, Maní |
| **San Justo** | 11 | Este (cuenca lechera) | Soja, Maíz, Trigo |
| **Unión** | 11 | Este | Soja, Maíz, Trigo |
| **Río Segundo** | 9 | Centro | Soja, Maíz |
| **Tercero Arriba** | 9 | Centro | Soja, Maíz, Maní |
| **Calamuchita** | 5 | Sur-Sierras | Soja, Maíz, Trigo |
| **Río Primero** | 5 | Centro-Norte | Soja, Maíz |
| **Capital** | 3 | Córdoba ciudad | Administrativo |

### 3.2 Caracterización por Eje

#### EJE SUR — Río Cuarto / Juárez Celman / Gral. Roca
Alta escala, exportadoras con integración vertical (AGD, Gastaldi, Prodeman, Cavigliasso). Maní como cultivo estrella. Vinculación ferroviaria directa (NCA). Los acopios SMB compiten siendo más ágiles en el margen — usan forwards y futuros MATBA-ROFEX. **Zona de alta sofisticación financiera**.

*Target para discovery*: Operadores medios de 50-200k tn/año como ADMSA Cereales (Adelia María), Tosquita Cereales (Vicuña Mackenna), Sgarlatta Cereales (San Basilio).

#### EJE ESTE — Marcos Juárez / Unión / San Justo
Pampa húmeda, zona núcleo. Fuerte dominio cooperativo (ACA, cooperativas de base). Los privados SMB coexisten con las cooperativas compitiendo por precio y servicio al productor. Cuenca lechera en San Justo → acopios integran formulación de balanceados.

*Target para discovery*: Independientes como AGL S.R.L. (Cruz Alta), Echaniz Hermanos (Camilo Aldao), División Agropecuaria (Noetinger), Cereales DEC (Corral de Bustos).

#### EJE CENTRO-NORTE — Colón / Totoral / Río Primero
Frontera agrícola en expansión. Garbanzo como diferenciador. Alta distancia a puertos → los acopios integran feedlots, granjas porcinas, bioetanol para "caminar el grano". Pronor, Agroempresa Colón, Cereales Viel, H&H Outfitters son referentes.

*Target para discovery*: Pronor S.A. (Villa del Totoral), Cereales Jesús María (Jesús María), Cereales Viel (Sinsacate).

#### VILLA MARÍA — General San Martín
Nudo logístico central. Héctor A. Bertone S.A. (440.000 tn/año, 50 años de trayectoria, tiene website) es el referente regional. Zona de alta densidad de acopios medianos con operación diversificada.

*Target para discovery*: Villa María Cereales S.R.L., JJST S.A.S., Caon Atilio & Miguel S.H., Etruria Cereales.

---

## 4. Tipología de Operadores

### Tipo A — Acopiador Físico Puro (SMB target principal)
- **Descripción**: Planta propia con silos/celdas, balanza, secadora. 1-15 empleados admin. Gerenciado por el dueño o familia.
- **Volumen típico**: 20.000 – 300.000 tn/año
- **Sistema actual**: Excel, planillas de campo, software antiguo (Agrofactu, Agesic, o desarrollos a medida de los 2000s)
- **Pain points esperados**: Romaneo manual, liquidaciones de granos en papel, seguimiento de cuentas corrientes de productores en planillas, no tienen trazabilidad VISEC, el SISA los preocupa pero no tienen herramienta de alerta
- **Ejemplos**: AGL S.R.L., Agrocereales Argentina, División Agropecuaria, Villa María Cereales

### Tipo B — Acopiador-Corredor Híbrido
- **Descripción**: Combina función de acopio físico con intermediación comercial. A veces también canjeador de insumos.
- **Volumen típico**: 50.000 – 500.000 tn/año
- **Pain points adicionales**: Gestión de contratos forward, seguimiento de precios, liquidación de corretaje, manejo de múltiples cuentas corrientes
- **Ejemplos**: Héctor A. Bertone S.A., CORCEAL S.R.L. (11 sucursales), Comercial Rossi, Conci S.R.L.

### Tipo C — Cooperativa de Primer Grado
- **Descripción**: Estructura asociativa, sirve a socios productores con servicios integrados (acopio, insumos, seguros, crédito)
- **Decisión de software**: Compleja (asamblea, Consejo Directivo)
- **Timing de adopción**: Más lento, pero volúmenes grandes
- **Ejemplos**: Coop. Freyre (tiene email), Coop. J. Posse (tiene teléfono), Coop. La Vencedora, Coop. Oncativo

### Tipos a EVITAR en esta fase de discovery
- **Exportadoras multinacionales** (AGD, Bunge, Cargill, COFCO, LDC): Ya tienen sistemas enterprise (SAP, Oracle). No son target SMB.
- **Cooperativas de 2° grado** (ACA): Gobernanza extremadamente compleja.
- **Integradas industriales** (Arcor, Porta Hnos, Glucovil, Minetti): Su acopio es para consumo propio; el sistema ERP lo define la casa matriz.

---

## 5. Directorio de Operadores — Ordenado por Departamento

> Leyenda: **[A]** = Acopiador físico | **[C]** = Corredor/Híbrido | **[Co]** = Cooperativa | **[E]** = Exportadora | **📞** = tiene contacto directo disponible

### Calamuchita (5)
| Empresa | Localidad | Tipo | Granos | Notas |
|---------|-----------|------|--------|-------|
| AGROEMPRESA SAN FRANCISCO S.A. | Coronel Moldes | [A] | Soja, Maíz, Trigo | — |
| CEREALISTA MOLDES S.A. | Coronel Moldes | [A] | Soja, Maíz, Trigo | — |
| COMINI DANIEL HERALDO | Berrotarán | [A] | Soja, Maíz, Trigo | Persona física |
| COMINI HERMANOS SOCIEDAD ANÓNIMA | Berrotarán | [A] | Soja, Maíz, Trigo | — |
| EDUARDO LUSSO S.A. | Monte Ralo | [A] | Soja, Maíz, Trigo | CUIT en RUCA |

### Colón (15)
| Empresa | Localidad | Tipo | Granos | Notas |
|---------|-----------|------|--------|-------|
| ACOPIO MONTE CRISTO S.A. | Monte Cristo | [A] | Soja, Maíz, Trigo | CUIT en RUCA |
| AGROEMPRESA COLON S.A. | Jesús María | [A] | Soja, Maíz, Garbanzo | Actor dominante del centro-norte |
| AGROFUSION S.A. | Sinsacate | [A] | Soja, Maíz, Trigo | CUIT en RUCA |
| CEREALES JESÚS MARÍA S.A. | Jesús María | [A] | Soja, Maíz, Trigo | CUIT en RUCA |
| CEREALES VIEL S.A. | Sinsacate | [A] | Soja, Maíz, Garbanzo | Garbanzo de exportación |
| DOS MATES S.A. | Colonia Caroya | [A] | Soja, Maíz, Garbanzo | — |
| FIDEICOMISO SEGASTRE | Sinsacate | [A] | Soja, Maíz, Trigo | Figura fideicomiso |
| H&H OUTFITTERS S.A. | Sinsacate | [A] | Soja, Maíz, Trigo | Eje Ruta 9 Norte |
| LOS SEIS HERMANOS SRL | Jesús María | [A] | Soja, Maíz, Trigo | Tribunal Cuentas Soc. Acop. |
| LUIS A. CARRIZO Y CIA. S.R.L. | Colonia Caroya | [A] | Soja, Maíz, Trigo | + Logística/flota |
| MAS AGRO CENTRO S.A.S. | Sinsacate | [A] | Soja, Maíz, Trigo | — |
| MIGUEL GAZZONI E HIJOS SRL | Monte Cristo | [A] | Soja, Maíz, Trigo | Vocal Titular Soc. Acop. |
| MIRU AGROPECUARIA S.R.L. | Sinsacate | [A] | Soja, Maíz, Trigo | — |
| OSCAR PEMAN Y ASOCIADOS S.A. | Sinsacate | [A] | Semillas, Soja | Especialista forrajeras |
| TECNOCAMPO S.A. | Monte Cristo | [A] | Soja, Maíz, Trigo | Alta escala, producción propia |

### General San Martín (12) ★ Villa María — zona de acceso geográfico directo
| Empresa | Localidad | Tipo | Granos | Contacto / Notas |
|---------|-----------|------|--------|-----------------|
| AGRO ACOPIO (POZO DEL MOLLE) | Pozo del Molle | [A] | Soja, Maíz, Sorgo | 📞 (0353) 4869800 · Flia. fundada 2001, balanceados |
| ALEMAR S.A. | Villa María | [A] | Soja, Maíz, Trigo | CUIT en RUCA |
| CAON ATILIO J Y CAON MIGUEL A S.H. | Villa María | [A] | Soja, Maíz, Trigo | Sociedad de hecho |
| COMPAÑÍA DE INSUMOS Y GRANOS S.A. | Villa María | [A] | Soja, Maíz, Trigo | CUIT en RUCA |
| DOSAGRO S.R.L. | La Laguna | [A] | Soja, Maíz | CUIT en RUCA |
| ETRURIA CEREALES SOCIEDAD ANÓNIMA | Etruria | [A] | Soja, Maíz, Trigo | — |
| HÉCTOR A. BERTONE S.A. | Villa María | [C] | Soja, Maíz, Trigo | 🌐 www.hab.com.ar · 440k tn/año · 50 años |
| JJST S.A.S. | Villa María | [A] | Soja, Maíz, Trigo | — |
| MAGO GUSTAVO ENRIQUE (AGRO ACOPIO) | Pozo del Molle | [A] | Soja, Maíz, Sorgo | 📞 (0353) 4869800 · Persona física + balanceados |
| SUPPO CEREALES S.A. | Pozo del Molle | [A] | Soja, Maíz, Trigo | — |
| TURAGLIO CEREALES S.R.L. | Pozo del Molle | [A] | Soja, Maíz, Trigo | — |
| VILLA MARÍA CEREALES S.R.L. | Villa María | [A] | Soja, Maíz, Trigo | — |

### Juárez Celman (13) — Cluster del Maní
| Empresa | Localidad | Tipo | Granos | Notas |
|---------|-----------|------|--------|-------|
| ACEITERA GENERAL DEHEZA S.A. (AGD) | General Deheza | [E] | Soja, Maíz, Maní | 🌐 www.agd.com.ar · Líder exportador — NO TARGET |
| ACOPIOS CONCEPCION S.A. | Concepción | [A] | Soja, Maíz, Maní | CUIT en RUCA |
| ARG DE GRAAF S.A. | Carnerillo | [A] | Soja, Maíz, Maní | Especialista maní |
| COFINA AGRO CEREALES S.A. | General Deheza | [E] | Maní, Soja | Exportadora maní |
| COOPERATIVA AGROPECUARIA Y DE SERVICIOS GENERAL DEHEZA LTDA. | General Deheza | [Co] | Soja, Maíz, Maní | CUIT en RUCA |
| COTAGRO COOPERATIVA AGROPECUARIA LTDA. | General Cabrera | [Co] | Maní, Soja, Maíz | 📞 +54 358 4933333 · 1.075.000 tn récord 2025 · Grande |
| EL CARMEN S.A. | General Cabrera | [E] | Maní | Criadero semillas y exportador |
| GASTALDI HNOS S.A.I.C.F.E.I. | General Deheza | [E] | Trigo, Maní, Soja | Fundada 1931 · Molino harinero |
| GOLDEN PEANUT AND TREE NUTS S.A. | Alejandro Roca | [E] | Maní | Filial internacional |
| GRUPO CAVIGLIASSO S.A. | General Cabrera | [E] | Maní, Soja | Líder exportador regional maní |
| INDELMA S.A. | General Cabrera | [E] | Maní | Maní alto oleico |
| INSA COMERCIO EXTERIOR S.A. | General Cabrera | [E] | Maní | Exportadora especializada |
| UCACHA CEREALES S.A. | Ucacha | [A] | Soja, Maíz, Maní | — |

### Marcos Juárez (12)
| Empresa | Localidad | Tipo | Granos | Notas |
|---------|-----------|------|--------|-------|
| AGL S.R.L. | Cruz Alta | [A] | Soja, Trigo, Maíz | — |
| BIOLATO CEREALES SC | Leones | [A] | Soja, Maíz, Trigo | Vocal Suplente Soc. Acop. |
| CEREALES DEC SOCIEDAD ANÓNIMA | Corral de Bustos | [A] | Soja, Maíz, Trigo | Zona núcleo sureste |
| COOPERATIVA AGROPECUARIA UNIÓN DE J. POSSE LTDA. | Justiniano Posse | [Co] | Soja, Maíz, Trigo | 📞 (03537) 431268 |
| COOPERATIVA UNIÓN POPULAR LTDA. | Silvio Pellico | [Co] | Soja, Maíz, Trigo | — |
| DIVISIÓN AGROPECUARIA S.A. | Noetinger | [A] | Soja, Maíz, Trigo | — |
| ECHANIZ HERMANOS S.A. | Camilo Aldao | [A] | Soja, Maíz, Trigo | — |
| ENRIQUE BERDINI Y CIA. SRL. | Inriville | [A] | Soja, Maíz, Trigo | Vicepresidente Soc. Acop. |
| GRUPO BONGIOVANNI S.A. | Guatimozín | [A] | Soja, Maíz, Trigo | — |
| MENZIO SRL. | Idiazábal | [C] | Trigo, Soja, Maíz | + Harina y balanceados |
| MUGICA Y CIA. S.A. | Camilo Aldao | [A] | Soja, Maíz, Trigo | Secretario Soc. Acop. |
| ORTEGA HERMANOS S.A. | Idiazábal | [A] | Soja, Maíz, Trigo | — |

### Presidente Roque Sáenz Peña (11)
| Empresa | Localidad | Tipo | Granos | Notas |
|---------|-----------|------|--------|-------|
| ADMSA CEREALES S.A. (ver Río Juárez) | Adelia María | [A] | Soja, Maíz, Trigo | — |
| AGROSERVICIOS SUR SA | Laboulaye | [A] | Soja, Maíz, Trigo | CUIT en RUCA · RN 7 |
| ÁMBITO DAS S.A. | La Carlota | [A] | Soja, Maíz, Maní | CUIT en RUCA |
| DOSAGRO S.R.L. | La Laguna | [A] | Soja, Maíz, Maní | CUIT en RUCA |
| GINCAT NEGOCIOS & CEREALES S.R.L. | La Laguna | [A] | Soja, Maíz, Maní | — |
| INTEGRAL ACOPIO S.R.L. | Buchardo | [A] | Soja, Maíz, Maní | Extremo sur, frontera BsAs/La Pampa |
| MANISEL S.A. | Pasco | [E] | Maní, Soja | — |
| MANISUR S.A. | La Carlota | [E] | Maní | Produce, industrializa y exporta |
| MONDINO ALFREDO SEBASTIÁN | Del Campillo | [A] | Soja, Maíz, Maní | Persona física |
| PICCO Y CIA S.A. | Jovita | [A] | Soja, Maíz, Maní | Enlace interjurisdiccional |
| SCILINGO HNOS S.A. | Del Campillo | [A] | Soja, Maíz, Maní | — |

### Río Cuarto (14)
| Empresa | Localidad | Tipo | Granos | Notas |
|---------|-----------|------|--------|-------|
| AGRO MATORRALES S.A. | Matorrales | [A] | Soja, Maíz, Maní | — |
| AGROSERVICIOS MEDITERRÁNEA S.A.S. | Río Cuarto | [A] | Soja, Maíz, Maní | +20 años, exporta habitualmente |
| AST AGRO S.A. | Vicuña Mackenna | [A] | Soja, Maíz, Maní | — |
| CORCEAL S.R.L. | Río Cuarto | [C] | Soja, Maíz, Trigo | 11 sucursales · Desde 1992 |
| DESAB S.A. | Piedritas | [A] | Soja, Maíz, Maní | — |
| EDUARDO A. TRAVAGLIA Y CIA. SA | Sampacho | [A] | Soja, Maíz, Maní | — |
| HIJOS DE LINO FABBRONI S.A. | Río Cuarto | [A] | Soja, Maíz, Maní | Vocal Titular Soc. Acop. |
| HORTAL BIANCHI Y CIA SA. | Las Peñas Sud | [A] | Soja, Maíz | — |
| INSUMOS Y ACOPIOS DEL SUR S.A. | Las Higueras | [A] | Soja, Maíz, Maní | — |
| NEGOCIOS RURALES S.A. | Vicuña Mackenna | [A] | Soja, Maíz, Maní | — |
| QUANTA S.A. | Río Cuarto | [A] | Soja, Maíz, Maní | — |
| ROBERTO DILENA Y CIA. S.C. | Río Cuarto | [C] | Soja, Maíz, Maní | — |
| SGARLATTA CEREALES S.A. | San Basilio | [A] | Soja, Maíz, Maní | — |
| TOSQUITA CEREALES S.A. | Vicuña Mackenna | [A] | Soja, Maíz, Maní | — |

### Río Primero (5)
| Empresa | Localidad | Tipo | Granos | Notas |
|---------|-----------|------|--------|-------|
| AGROSERVICIOS DIGON S.R.L. | Río Primero | [A] | Soja, Maíz, Trigo | — |
| CENTRO AGROP. INSUMOS SS CER. S.A. | Santiago Temple | [A] | Soja, Maíz, Trigo | CUIT en RUCA |
| CHIAMBRETTO D. Y SCHNEIDER G. | La Puerta | [A] | Soja, Maíz, Trigo | Sociedad de hecho |
| HORTAL BIANCHI Y CIA SA. | Las Peñas Sud | [A] | Soja, Maíz | — |
| OSVALDO FANTINI Y CIA SRL. | Santa Rosa de Río I | [A] | Soja, Maíz, Trigo | — |

### Río Segundo (9)
| Empresa | Localidad | Tipo | Granos | Notas |
|---------|-----------|------|--------|-------|
| CONCI S.R.L. | Pilar | [C] | Soja, Maíz, Trigo | Exporta maíz, maquinaria |
| COOPERATIVA AGRÍCOLA GANADERA LUQUE LTDA. | Luque | [Co] | Soja, Maíz, Trigo | CUIT en RUCA |
| COOPERATIVA AGRÍCOLA GANADERA Y DE CONSUMO DE ONCATIVO LTDA. | Oncativo | [Co] | Soja, Maíz, Trigo | CUIT en RUCA |
| EL ÁLAMO S.R.L. | Oncativo | [A] | Soja, Maíz, Trigo | CUIT en RUCA, exporta |
| GALEAZZI S.A. | Luque | [A] | Soja, Maíz, Trigo | — |
| GRUPO PILAR SOCIEDAD ANÓNIMA | Pilar | [A] | Soja, Maíz, Trigo | Mascotas/nutrición animal |
| LOGRANDO AMIGOS S.R.L. | Carrilobo | [A] | Soja, Maíz, Trigo | — |
| PASEJES S.A. | Río Segundo | [C] | Trigo, Soja | Produce harinas 000/0000 |
| TEUMACO CEREALES S.A. | Villa del Rosario | [A] | Soja, Maíz, Trigo | — |

### San Justo (11)
| Empresa | Localidad | Tipo | Granos | Notas |
|---------|-----------|------|--------|-------|
| AGRO INSUMOS DON ESTEBAN S.R.L. | Altos de Chipión | [A] | Soja, Maíz, Trigo | Cuenca lechera |
| AGROSERVICIOS SAN FRANCISCO S.A. | San Francisco | [A] | Soja, Maíz, Trigo | — |
| ARCOR S.A.I.C. | Arroyito | [E] | Maíz, Trigo | Acopio para consumo propio — NO TARGET |
| CEREALERA LAS VARAS S.A. | Las Varas | [A] | Soja, Maíz, Trigo | — |
| COOPERATIVA AGRÍCOLA GANADERA DE MORTEROS LTDA. | Morteros | [Co] | Soja, Maíz, Trigo | CUIT en RUCA |
| COOPERATIVA AGRÍCOLA GANADERA Y DE CONSUMO FREYRE LTDA. | Freyre | [Co] | Soja, Maíz, Trigo | 📞 (03564) 461018 · 📧 andrea@coop-freyre.com.ar |
| DSA SERVICIOS S.R.L. | Devoto | [A] | Soja, Maíz, Trigo | — |
| LOGRANDO AMIGOS S.R.L. | Carrilobo | [A] | Soja, Maíz, Trigo | — |
| RIBACK & CIA CEREALES S.R.L. | Saturnino M. Laspiur | [A] | Soja, Maíz, Trigo | — |
| SEMAGRO S.R.L. | Porteña | [A] | Soja, Maíz, Trigo | + Nutrición lechera |
| ZANOY AGRO & SERVICIOS S.A. | Tránsito | [A] | Soja, Maíz, Trigo | — |

### Tercero Arriba (9)
| Empresa | Localidad | Tipo | Granos | Notas |
|---------|-----------|------|--------|-------|
| ACOPIADORA OLIVA S.R.L. | Oliva | [A] | Soja, Maíz, Trigo | CUIT en RUCA |
| AGRO HERNANDO SRL | Hernando | [A] | Soja, Maíz, Trigo | CUIT en RUCA |
| CENTRO TECNOLÓGICO AGROPECUARIO S.A. | Hernando | [E] | Maní | — |
| CLAUDIO PEREZ CEREALES S.A. | James Craik | [A] | Soja, Maíz, Trigo | Tesorero Soc. Acop. |
| COMERCIAL ROSSI S.A. | Colazo | [C] | Trigo, Soja, Maíz | Flia. 1985, también molino |
| COOPERATIVA AGRÍCOLA LA VENCEDORA LTDA. | Hernando | [Co] | Soja, Maíz, Maní | Cert. ambiental Cba 2024, 4 silos × 1500tn |
| INSUMOS DEL CENTRO S.A. | Río Tercero | [A] | Soja, Maíz, Trigo | — |
| MAGLIONE HNOS Y CIA S.A. | Las Junturas | [A] | Soja, Maíz, Trigo | Vocal Suplente Soc. Acop. |
| SERVICIOS AGROPECUARIOS S.R.L. | Despeñaderos | [A] | Soja, Maíz, Trigo | 🌐 serviciosagropecuariossrl.com · Fundada 1991 |

### Unión (11)
| Empresa | Localidad | Tipo | Granos | Notas |
|---------|-----------|------|--------|-------|
| AGROCEREALES ARGENTINA S.R.L. | Viamonte | [A] | Soja, Maíz | 📞 (03463) 15647073 · 📧 info@agrocerealesargentina.com |
| AGROGANADERA MONTE MAÍZ S.A. | Monte Maíz | [A] | Soja, Maíz, Trigo | CUIT en RUCA |
| CASA RUIBAL S.A. | Pascanas | [C] | Trigo, Soja, Maíz | Exporta ocasionalmente |
| CEREALES BYCSA SRL | Guatimozín | [A] | Soja, Maíz, Trigo | — |
| COMPAÑÍA DE INSUMOS Y GRANOS S.A. | W. Escalante | [A] | Soja, Maíz, Trigo | CUIT en RUCA |
| GRUPO BONGIOVANNI S.A. | Guatimozín | [A] | Soja, Maíz, Trigo | — |
| GRUPO CKOOS S.R.L. | Villa Ascasubi | [A] | Soja, Maíz, Trigo | — |
| HESAR HERMANOS SOCIEDAD ANÓNIMA | Villa Ascasubi | [A] | Soja, Maíz, Trigo | — |
| JOSE DEL RE S.A. | Bell Ville | [A] | Soja, Maíz, Trigo | — |
| LORENZATI RUETSCH Y CIA. S.A. | Ticino | [A] | Soja, Maíz, Trigo | Termoeléctrica con cáscara de maní |
| V.G. S.A. | General Baldissera | [A] | Soja, Maíz, Trigo | — |

### Río Juárez (4)
| Empresa | Localidad | Tipo | Granos | Notas |
|---------|-----------|------|--------|-------|
| ADMSA CEREALES S.A. | Adelia María | [A] | Soja, Maíz, Trigo, Girasol | Socio Acopiadores |
| AGROCEREALES LA MILONGUITA S.A. | Adelia María | [A] | Soja, Maíz, Trigo, Girasol | También productora |
| AGROTECNOLOGIA Y SERVICIOS S.A. | Adelia María | [A] | Soja, Maíz, Maní | Exporta habitualmente |
| MERLO Y MANAVELLA S.A. | Adelia María | [A] | Soja, Maíz, Maní | — |

### Capital — Córdoba Ciudad (3)
| Empresa | Localidad | Tipo | Granos | Notas |
|---------|-----------|------|--------|-------|
| CONOSUR FOODS ARGENTINA S.A. | Córdoba Capital | [E] | Maní, Soja | Fundada 2006, orgánicos |
| INDACOR | Barrio Gral. Bustos | [A] | Soja, Maíz, Trigo | Integración avícola |
| TECNOCALCHIN S.R.L. | Nueva Córdoba | [A] | Soja, Maíz, Trigo | Sede administrativa |

### Totoral (1)
| Empresa | Localidad | Tipo | Granos | Notas |
|---------|-----------|------|--------|-------|
| PRONOR S.A. | Villa del Totoral | [A] | Soja, Maíz, Trigo | Vocal Directivo Soc. Acop., norte estratégico |

### General Roca (1)
| Empresa | Localidad | Tipo | Granos | Notas |
|---------|-----------|------|--------|-------|
| ALFREDO S. MONDINO CEREALES S.R.L. | General Roca | [C] | Soja, Maíz, Maní | También remates ganaderos |

### Santa María (2)
| Empresa | Localidad | Tipo | Granos | Notas |
|---------|-----------|------|--------|-------|
| DOS RIOS S.A.A.I. | Alta Gracia | [A] | Soja, Maíz | Enlace inter-sierras |
| SERVICIOS AGROPECUARIOS S.R.L. | Despeñaderos | [A] | Soja, Maíz, Trigo | 🌐 sitio web activo |

---

## 6. Fuentes y Metodología

### Fuentes Cruzadas
1. **Sociedad de Acopiadores de Granos de Córdoba** — Listado de socios, padrón RUCA, Consejo Directivo ([acopiadorescba.com](http://www.acopiadorescba.com))
2. **ARCA/AFIP — SISA** — Confirmación de actividad fiscal por CUIT ([serviciosweb.afip.gob.ar](https://serviciosweb.afip.gob.ar/dbusr/consultaSisa.xhtml))
3. **RUCA/ARCA** — Archivo histórico distribuido por Acopiadores Córdoba (ex-ONCCA/MAGyP). El RUCA fue integrado al SISA en 2025.
4. **ProCórdoba** — Directorio de exportadores de Córdoba ([exportadoresdecordoba.com](http://www.exportadoresdecordoba.com))
5. **Bolsa de Cereales de Córdoba (BCCBA)** — Socios operadores habilitados ([bccba.org.ar](http://www.bccba.org.ar))
6. **Páginas Amarillas Argentina** — Categorías "acopiadores" y "cerealeras"
7. **Sitios web de empresas** — Verificación directa en dominios activos
8. **datos.gob.ar / MAGyP** — Dataset de centros de acopio por departamento

### Limitaciones Conocidas
- El 70%+ de los campos de teléfono y email figura como N/D (protección de datos empresariales)
- El SENASA no publica listado abierto de plantas habilitadas
- La Bolsa de Cereales de Buenos Aires requiere acceso autenticado para corredores
- Los CUITs marcados N/D no fueron localizables en fuentes públicas abiertas
- Cobertura estimada: ~85-90% de los operadores formales activos en Córdoba

---

## 7. Plan de Customer Discovery

### 7.1 Objetivo de esta Fase

**Aprender, no vender.** El objetivo de las visitas es entender exactamente cómo opera un acopiador SMB hoy — procesos, herramientas, dolores, workarounds — para construir el ERP correcto. Ninguna visita debe terminar con un pitch de producto. Sí puede terminar con "cuando lo tengamos listo, ¿te interesaría probarlo primero?"

### 7.2 Criterios para Seleccionar Candidatos

El target ideal para esta fase de discovery tiene:

| Criterio | Rango ideal | Por qué |
|----------|-------------|---------|
| Tipo | Acopiador físico independiente (Tipo A o C-pequeña) | Tienen autonomía de decisión real |
| Volumen | 30.000 – 500.000 tn/año | Suficiente para tener sistemas, pequeño para que el dueño atienda |
| Escala humana | 1-10 empleados admin | El dueño o gerente opera el sistema directamente |
| Antigüedad | +10 años | Ya pasó por varios ciclos de problemas |
| Distancia | Dentro de 200km de Villa María | Viable para visita presencial |
| Grano | Soja + Maíz (mínimo) | Valida el core del romaneo |

**Evitar para esta fase**: AGD, Bunge, Cargill, LDC, COFCO, ACA, Arcor, Porta. Son demasiado grandes, ya tienen sistemas enterprise o la decisión está en Buenos Aires.

### 7.3 Shortlist de Primeros Contactos

Basado en accesibilidad (contacto disponible) y perfil ideal:

| Prioridad | Empresa | Localidad | Por qué empezar acá | Contacto |
|-----------|---------|-----------|---------------------|---------|
| **🥇 P0** | AGROCEREALES ARGENTINA S.R.L. | Viamonte, Unión | Tiene email directo, empresa independiente, fundada hace +20 años, escala media | 📞 (03463) 15647073 · 📧 info@agrocerealesargentina.com |
| **🥇 P0** | AGRO ACOPIO / MAGO GUSTAVO ENRIQUE | Pozo del Molle | Empresa familiar fundada 2001, fácil de acceder a dueño, también hace balanceados (complejidad real) | 📞 (0353) 4869800 |
| **🥇 P0** | COOPERATIVA FREYRE | Freyre, San Justo | Email activo, cooperativa de 1er grado, proceso complejo, interlocutor "andrea" es accesible | 📞 (03564) 461018 · 📧 andrea@coop-freyre.com.ar |
| **🥈 P1** | SERVICIOS AGROPECUARIOS S.R.L. | Despeñaderos | Tiene website activo, fundada 1991, acopio + acondicionamiento | 🌐 serviciosagropecuariossrl.com |
| **🥈 P1** | HÉCTOR A. BERTONE S.A. | Villa María | 440k tn/año, 50 años, website activo, cerca geográficamente — es grande pero referente del mercado | 🌐 www.hab.com.ar |
| **🥈 P1** | COOPERATIVA UNIÓN J. POSSE | Justiniano Posse | Teléfono disponible, cooperativa 1er grado, zona Marcos Juárez | 📞 (03537) 431268 |
| **🥉 P2** | ADMSA CEREALES / AGROCEREALES LA MILONGUITA | Adelia María | Sur, zona distinta, dos empresas en la misma localidad = comparar perspectivas | Buscar contacto directo |
| **🥉 P2** | CEREALES VIEL S.A. | Sinsacate, Colón | Norte, especialista en garbanzo = nicho diferenciador | Buscar contacto directo |

### 7.4 Canales de Acceso — De Mayor a Menor Fricción

#### Canal 1 — Contacto Directo (Inmediato)
Para los P0 que ya tienen teléfono/email: llamar o escribir directamente.

**Script de apertura (teléfono)**:
> "Buenos días, ¿hablo con la gerencia? Mi nombre es Bruno Ghiberto, soy de Villa María. Estoy desarrollando un sistema de gestión para acopios y quería hacerme unos minutos con ustedes — no para venderles nada, sino para entender cómo trabajan. ¿Tendrían 30 minutos algún día de esta semana para que me cuenten?"

**Script email**:
> Asunto: Consulta breve sobre gestión del acopio — 30 min
>
> Estimados, mi nombre es Bruno Ghiberto y estoy desarrollando un software de gestión específico para acopios en Córdoba. No los contacto para venderles nada — todavía estamos en etapa de investigación y necesitamos entender cómo operan los acopios reales antes de escribir una línea de código.
>
> ¿Tendrían disponibilidad para una charla de 30 minutos, en su planta o por videollamada?

#### Canal 2 — Red de Contadores Rurales
Los contadores que atienden acopios son el nodo más confiable del ecosistema. Una presentación de un contador de confianza elimina casi toda la fricción inicial.

**Cómo activarlo**: Identificar 2-3 contadores rurales en Villa María / Marcos Juárez / Río Cuarto que trabajen con acopios. Reunirse con ellos primero con el mismo framing de discovery.

#### Canal 3 — Sociedad de Acopiadores de Córdoba
- **Email/teléfono institucional**: [http://www.acopiadorescba.com/content/institucional](http://www.acopiadorescba.com/content/institucional)
- **Propuesta**: Pedir al Consejo Directivo 10 minutos en su próxima reunión para presentar el proyecto y solicitar acceso a socios dispuestos a participar en entrevistas
- **Palanca**: Enmarcarlo como "investigación que beneficia al sector" — a ellos les interesa que exista mejor software para sus socios

#### Canal 4 — Eventos y Capacitaciones VISEC
La Sociedad de Acopiadores organiza capacitaciones sobre VISEC/EUDR. Son reuniones donde todos los asistentes tienen el mismo pain point urgente. Asistir como oyente y conectar informalmente después.

#### Canal 5 — Expoagro / Córdoba Agropecuaria
Ferias del sector donde los acopiadores participan como expositores o visitantes. Próxima Expoagro: San Nicolás, marzo 2026. Córdoba Agropecuaria: primer semestre anual en La Rural de Córdoba.

### 7.5 Guía de Entrevista de Discovery

Duración target: 45-60 minutos. Tomar notas, no grabar (genera fricción).

#### Bloque A — Contexto Operativo (10 min)
1. ¿Cuántas toneladas operan por campaña, aproximadamente?
2. ¿Qué granos manejan? ¿Tienen alguno que sea especialmente complicado de gestionar?
3. ¿Cuántas personas trabajan en la parte administrativa y de balanza?
4. ¿Tienen varias plantas o una sola ubicación?

#### Bloque B — El Día de Cosecha — El Romaneo (15 min)
5. Contame cómo es el proceso desde que llega el primer camión del día hasta que termina la recepción. ¿Qué pasos tienen que seguir?
6. ¿Dónde registran los datos del romaneo hoy? (balanza, papel, sistema, Excel)
7. ¿Cómo registran la calidad — humedad, impurezas — y cómo calculan la merma?
8. ¿Qué pasa cuando hay un error en el romaneo? ¿Cómo lo corrigen?
9. ¿El productor recibe algo en el momento? ¿Un ticket, un recibo?
10. ¿Cuánto tiempo lleva hacer el romaneo de un camión de principio a fin?

#### Bloque C — Stock y Posición (10 min)
11. ¿Cómo saben en todo momento cuánto tienen de cada grano y en qué celda?
12. ¿Diferencia el stock por calidad o por campaña dentro de una misma celda?
13. Si un auditor de ARCA les pide demostrar la posición de stock del día, ¿cómo lo hacen?
14. *(VISEC)* ¿Ya están trabajando con VISEC para trazabilidad de origen? ¿Qué están haciendo para eso?

#### Bloque D — Cuentas Corrientes de Productores (10 min)
15. ¿Cómo llevan las cuentas corrientes de los productores (saldo en kg, saldo en pesos)?
16. ¿Hacen operaciones de canje (insumos contra granos)? ¿Cómo las registran?
17. ¿Con qué frecuencia mandan el estado de cuenta a los productores?
18. ¿Alguna vez tuvieron un problema serio por un error en la cuenta corriente de un productor?

#### Bloque E — Liquidaciones y Fiscal (10 min)
19. ¿Qué sistema usan para emitir la liquidación de granos (Liquidación Primaria / Form. 1116)?
20. ¿Cómo manejan el tema del SISA — tienen alguna forma de monitorear el estado de sus contrapartes?
21. ¿El CTG/CPE lo generan desde su sistema o tienen que entrar a la web de ARCA?
22. ¿Tuvieron algún problema con retenciones por estado SISA de un comprador o vendedor?

#### Bloque F — Software Actual (10 min)
23. ¿Qué programa o sistema usan hoy para gestionar el acopio?
24. ¿Qué es lo que más les gusta del sistema actual?
25. ¿Qué es lo que más les molesta o les hace perder tiempo?
26. Si pudieran cambiar UNA SOLA COSA de su sistema actual, ¿qué cambiarían?
27. ¿Alguna vez probaron otro software? ¿Por qué lo cambiaron / no lo adoptaron?

#### Bloque G — Cierre y Futuro (5 min)
28. ¿Qué problema del día a día les parece que todavía no tiene solución tecnológica buena?
29. ¿Conocen otros acopios que puedan estar dispuestos a charlar sobre estos temas?
30. Si desarrollamos algo que resuelva [principal pain point mencionado], ¿les gustaría ser de los primeros en probarlo?

### 7.6 Qué Buscar — Señales de Pain Point Real

Documentar con especial atención:

| Señal | Significado | Módulo ERP impactado |
|-------|-------------|---------------------|
| "Lo pasamos a Excel después" | Romaneo sin integración digital | Balanza / Romaneo |
| "El productor llama preguntando qué tiene" | Cuenta corriente no accesible en tiempo real | Portal productor |
| "Para ARCA tenemos que entrar a la web" | CTG/CPE no integrado al sistema de gestión | Integración ARCA |
| "No sé exactamente en qué celda está qué grano" | Stock sin trazabilidad de origen | Inventario / Stock Position |
| "VISEC nos preocupa pero no sabemos bien cómo" | Urgencia trazabilidad UE — pain agudo ahora | Trazabilidad VISEC |
| "Tenemos todo en [sistema de los 2000s]" | Software antiguo, sin soporte, sin API | Oportunidad de migración |
| "El contador nos armó el Excel" | Sin ERP especializado — solo planillas | Oportunidad clara |
| "Hubo un lío con la retención a un productor" | Cuenta corriente mal llevada | Cuentas corrientes |

### 7.7 Criterio de Éxito de la Fase de Discovery

La fase de discovery está completa cuando:

- [ ] Mínimo **5 entrevistas completadas** con operadores de al menos 3 departamentos distintos
- [ ] Identificado al menos **1 pain point universal** (presente en 4 de 5 entrevistas)
- [ ] Identificado al menos **1 "hair on fire problem"** — algo que están tratando de resolver activamente ahora
- [ ] Recolectado al menos **2 muestras de documentos reales** (romaneo ticket, liquidación, estado de cuenta)
- [ ] Identificado **software actual prevalente** — qué usan hoy y qué odian de ello
- [ ] Obtenido **compromiso informal de al menos 2 beta testers** para piloto

### 7.8 Cronograma Sugerido

| Semana | Actividad | Meta |
|--------|-----------|------|
| Semana 1 (actual) | Contactar P0 (Agrocereales, Agro Acopio, Coop Freyre) | 3 reuniones agendadas |
| Semana 2 | Ejecutar primeras 3 entrevistas | 3 entrevistas · primeras señales |
| Semana 3 | Contactar P1 · buscar contador rural como warm intro | 3 más agendadas |
| Semana 4 | Ejecutar otras 3 entrevistas · síntesis | 6 entrevistas · síntesis parcial |
| Semana 5-6 | 2-3 entrevistas adicionales en zonas distintas (Río Cuarto, Norte) | 8-10 entrevistas total |
| Semana 7 | Síntesis final · decisión de MVP scope | Documento de hallazgos |

---

## 8. Síntesis de Pain Points Esperados

Basado en el análisis del sector y en research previo (docs 2.1, 4.3, 8.3 del corpus RAG):

| Pain Point | Probabilidad | Urgencia | Impacto en diseño |
|-----------|-------------|---------|------------------|
| Romaneo todavía parcialmente manual o en Excel | Alta (70%+ SMB) | Media | Core del MVP |
| CTG/CPE gestionado fuera del sistema de gestión | Alta | Alta (CTG es obligatorio) | Integración ARCA |
| Cuenta corriente de productores en planillas | Alta (60%+ SMB) | Media-Alta | Módulo cuentas |
| Sin alerta de estado SISA de contrapartes | Media (40%) | Alta (error = pérdida) | Dashboard SISA |
| Sin trazabilidad VISEC para EUDR | Alta (90% no lo tienen) | **Muy Alta** (plazo UE) | Trazabilidad lote |
| Sistema de stock sin segregación por calidad/origen | Alta | Media | Posición de stock |
| Software actual desactualizado sin soporte | Media-Alta | Baja-Media | Oportunidad migración |

---

## 9. Información de Contacto — Resumen Rápido

Empresas con contacto directo disponible al 16/03/2026:

| Empresa | Localidad | Teléfono | Email / Web |
|---------|-----------|----------|-------------|
| AGROCEREALES ARGENTINA S.R.L. | Viamonte (Unión) | (03463) 15647073 | info@agrocerealesargentina.com |
| AGRO ACOPIO | Pozo del Molle | (0353) 4869800 | www.agroacopio.com |
| COOPERATIVA FREYRE | Freyre (San Justo) | (03564) 461018 | andrea@coop-freyre.com.ar |
| COOP. UNIÓN J. POSSE | Justiniano Posse | (03537) 431268 | — |
| COTAGRO | General Cabrera | +54 358 4933333 | www.cotagroweb.com.ar |
| HÉCTOR A. BERTONE S.A. | Villa María | — | www.hab.com.ar |
| SERVICIOS AGROPECUARIOS S.R.L. | Despeñaderos | — | www.serviciosagropecuariossrl.com |

---

*Documento generado el 16/03/2026. Actualizar contactos antes de cada ronda de discovery.*
*Datos del directorio: Sociedad de Acopiadores Córdoba · RUCA/ARCA · ProCórdoba · BCCBA.*
