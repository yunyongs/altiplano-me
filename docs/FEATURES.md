# Panel de Control AR -- Vision General Actualizada

Este documento resume el conjunto actual de funciones del panel Flask de
Altiplano Resiliente segun la implementacion vigente.

---

## Vision del Sistema

El sistema es un panel web para operadores no tecnicos que conecta:

- Smartsheet
- ArcGIS Pro
- ArcGIS Online
- Power BI
- sistema de archivos local

El servidor Flask actua como capa intermedia para:

- leer configuracion local
- proteger credenciales y rutas
- llamar APIs externas
- generar scripts para ArcPy y Power BI
- consolidar reportes y estados del pipeline

---

## Estructura Operativa

La forma mas precisa de entender el sistema actual es separarlo en tres capas.

### 1. Diagnostico operativo inicial

- El backend sigue usando el endpoint `paso0`, pero para el operador debe
	entenderse como Paso 1-a dentro del trabajo sobre Smartsheet.

### 2. Pipeline principal

- Paso 1 a Paso 7 cubren Smartsheet, GIS, ArcPy, AGOL, Excel, Power BI y documentacion.

### 3. Funciones de correccion y validacion

- correccion de fechas
- correccion AbE
- fill-down con vista previa
- validacion de codigos SHP
- verificacion 3 fuentes
- criterios de limpieza
- recepcion de Dafne
- comparacion M&E

---

## Matriz de Funcionalidades

| Funcionalidad | Que hace | Paso |
|:--------------|:---------|:-----|
| Conectar AGOL (OAuth PKCE) | Login a ArcGIS Online via OAuth 2.0 PKCE; token en memoria (60 min) y refresh automatico | Paso 1-a |
| Resolver capas AGOL por Item ID | Convierte Item IDs (.env) a Feature Layers; soporta capas privadas | Paso 1-a |
| Diagnostico AGOL vs Smartsheet | Compara AGOL contra Smartsheet actual; clasifica verified_match / verified_mismatch / new | Paso 1-a |
| Exportar CSV diagnostico | Exporta resultados del diagnostico a CSV para revision externa | Paso 1-a |
| Cargar vista previa | Carga filas y muestra tabla de Smartsheet (con highlight de discrepancias) | Paso 1 |
| Comentarios diferidos | Carga comentarios de filas solo cuando se necesitan | Paso 1 |
| Generar codigos | Crea codigos faltantes sin tocar codigos ya existentes (regla de inmutabilidad) | Paso 1 |
| Actualizar revision | Ajusta `Calidad SIG` a `Espera` o `Sí` | Paso 1 |
| Fix Dates | Corrige fechas en formato texto | Paso 1 |
| Set Calidad | Ajusta `Calidad SIG` en bloque | Paso 1 |
| Fix AbE | Normaliza valores AbE | Paso 1 |
| Fill Down | Rellena valores hacia abajo con vista previa | Paso 1 |
| Bucle agente (Agent Loop) | Cola de trabajo con estado por item: init, mark-complete, mark-skip, mark-pending, reset | Paso 1 |
| Listar adjuntos | Muestra adjuntos por fila | Paso 1b |
| Descarga batch + validar | Descarga ZIPs en streaming, extrae seguro (ZIP-Slip), valida SHP y reanuda con checkpoint | Paso 1b |
| Logica C2 multi-SHP | Maneja multiples ZIPs SHP en una sola fila C2, desambigua por pista AbE del nombre original | Paso 1b |
| Deduplicacion SHP | SHP repetidos en distintos hijos se procesan una sola vez | Paso 1b |
| Descarga Excel de areas | Fallback cuando no hay shapefile: descarga el Excel de áreas (`/api/smartsheet/excel-area-download`) | Paso 1b |
| Excel → puntos (XYTableToPoint) | Parsea Excel, convierte DMS, transforma WGS84→GTM y agrega FC de puntos al mapa | Paso 1b |
| Agregar SHP al mapa | Genera o ejecuta script para agregar SHP al mapa de ArcGIS Pro dentro de `{Q}_polygon` / `{Q}_point` | Paso 1b |
| Estructura trimestral | Crea carpetas `{base}/{T2026_Q2}/{C1|C2|C3}/{identificador}/` | Paso 1b |
| ~~Control cruzado~~ | ~~Compara Smartsheet contra GIS CSV~~ | ~~Paso 2~~ (Removed) |
| ~~Script validar SHP~~ | ~~Verifica archivo SHP vs `CdgActvdd`~~ | ~~Paso 2~~ (Removed) |
| Scripts ArcPy guiados | Genera scripts del procesamiento territorial | Paso 3 |
| Criterios de limpieza | Guarda decisiones de limpieza por trimestre | Paso 3 |
| Exportar criterios PDF | Genera PDF con criterios de limpieza por trimestre | Paso 3 |
| Reporte solapamiento PDF | Genera reporte PDF de analisis de solapamiento | Paso 3 |
| Resultados de limpieza | Compara antes y despues de limpieza | Paso 3 |
| Scripts AGOL | Actualiza capas web y exporta shapefiles | Paso 4 |
| Verificacion 3 fuentes | Compara Smartsheet, GIS y AGOL | Paso 4 |
| Excel maestro | Genera XLSX consolidado de C1/C2/C3 | Paso 5 |
| Recepcion Dafne | Valida, coloca y registra `Tbl_Integrado.xlsx` | Paso 5 |
| Historial Dafne | Consulta historial y trimestres de recepciones M&E | Paso 5 |
| Estado Power BI Desktop | Verifica estado local y abre PBIP | Paso 6 |
| Tablas Power BI | Consulta tablas disponibles en el modelo Power BI local | Paso 6 |
| Script refresh Power BI | Genera script de refresco | Paso 6 |
| Comparacion M&E | Compara Dafne vs Power BI y guarda decisiones | Paso 6 |
| Drill-down M&E | Detalla discrepancias por indicador entre Dafne y PBI | Paso 6 |
| Reporte M&E | Genera reporte consolidado de la comparacion M&E | Paso 6 |
| Reporte de errores | Resume errores y advertencias del pipeline | Paso 7 |
| Resumen de datos | Resume metricas y estado general | Paso 7 |
| Guia PDF Power BI | Genera guia manual para exportar PDF | Paso 7 |
| Verificacion Publish-to-Web | Comprueba enlace publico de Power BI | Paso 7 |
| URL de incrustacion | Genera URL de embed para Power BI | Paso 7 |
| Respaldo | Crea copia con marca de tiempo | Paso 7 |
| Orquestador | Controla pasos y subpasos, incluyendo avance de subpasos | Global |
| Configuracion de rutas | Lee y actualiza las rutas de carpetas desde la interfaz | Global |

---

## Cambios Relevantes del Sistema Actual

### El diagnostico se presenta aparte, pero se opera como Paso 1-a

Aunque el endpoint y parte de la interfaz conservan el nombre Paso 0, la
operación correcta es tratar el diagnóstico como la primera parte del Paso 1.

Secuencia operativa esperada:

- cargar la vista previa
- en C2, elegir primero PPD o PMD
- ejecutar el diagnóstico
- usar el panel derecho como cola de trabajo

### Paso 1 ahora incluye saneamiento de datos

El sistema actual no solo carga datos. Tambien puede:

- corregir fechas
- normalizar AbE
- aplicar cambios de `Calidad SIG`
- hacer relleno hacia abajo

### Paso 1b soporta descargas robustas

- checkpoint para reanudar
- descarga en streaming
- validacion segura de rutas y ZIPs
- soporte para C2 con multiples shapefiles por fila

### Paso 3 y Paso 4 tienen mas evidencia operativa

- criterios de limpieza con PDF
- comparacion antes/despues de limpieza
- verificacion de 3 fuentes antes o despues de publicar

### Paso 5 y Paso 6 ya cubren M&E de extremo a extremo

- recepcion del archivo de Dafne
- validacion y colocacion en BasePath
- comparacion contra Power BI
- guardado de decisiones del valor final

### Paso 7 es un cierre operativo, no solo un visor

- resumen y errores
- guia PDF para Power BI
- chequeo de enlaces publicos
- respaldo local

---

## Modulos Principales

| Modulo | Proposito actual |
|:-------|:-----------------|
| `app.py` | Rutas Flask (~78 endpoints), middleware de token local, integracion principal y orquestacion |
| `ar_utils.py` | utilidades de seguridad, ZIP-Slip safe, rutas, Smartsheet (retries), AbE, SHP/DBF reader, Excel area helper, streaming downloads |
| `env_paths.py` | deteccion portable de OneDrive y expansion de `${ONEDRIVE_DATAME}` / `${ONEDRIVE_IUCN}` en `.env` |
| `agol_connect.py` | OAuth 2.0 PKCE para AGOL, singleton GIS, cache de Item ID → FeatureLayer, refresh de token |
| `build_config.py` | generacion de `config.js` desde `.env` y plantilla |
| `orchestrator.py` | coordinacion del pipeline |
| `pipeline_state.py` | estado persistente, errores, advertencias y subpasos |
| `paso_constants.py` | constantes del dominio: microcuencas, tipos AbE, areas, grants |
| `paso1_quarterly.py` | estructura trimestral + script `add_shapefiles_to_map` (bilingue) |
| `paso1_agent.py` | estado del bucle agente: init, update, load, mark-pending, reset por item |
| `paso1_excel_to_point.py` | fallback Excel de areas → CSV (DMS→DD, WGS84↔GTM) → ArcPy XYTableToPoint script |
| `paso2_crosscheck.py` | ~~motor del control cruzado~~ (Removed -- modulo ya no se importa) |
| `paso2_shp_validate.py` | ~~script de validacion de CdgActvdd en shapefiles~~ (Removed -- modulo ya no se importa) |
| `paso3_scripts.py` | scripts ArcPy del procesamiento territorial (bilingues) |
| `paso3_criteria.py` | CRUD de criterios de limpieza por trimestre |
| `paso3_pdf_report.py` | generacion de reporte PDF de solapamiento |
| `paso4_scripts.py` | scripts ArcPy de publicacion AGOL (bilingues) |
| `paso5_dafne.py` | validacion, recepcion e historial de M&E |
| `paso6_compare.py` | comparacion M&E Dafne vs Power BI con drill-down y decisiones |
| `paso6_powerbi.py` | refresco, enlace publico, embed y guia PDF |
| `paso7_reports.py` | resumenes, errores y respaldos |
| `pbi_refresh.py` | deteccion de Power BI Desktop, lanzamiento y MCP local |
| `templates/dashboard.html` | interfaz principal bilingue (lang-es / lang-en) con tooltips y aria-labels duales |
| `static/app.js` | logica de cliente, llamadas API, language toggle (`setLang`, `i18n`) y renderizado |
| `static/style.css` | estilos responsivos con tokens de marca AR (AR Green #70b62c, AR Blue #003f6e) |

---

## Endpoints Principales por Categoria

### Smartsheet

- `/api/smartsheet/load`
- `/api/smartsheet/comments`
- `/api/smartsheet/diagnose`
- `/api/smartsheet/cache/clear`
- `/api/smartsheet/generate-codes`
- `/api/smartsheet/fix-dates`
- `/api/smartsheet/update-review`
- `/api/smartsheet/set-calidad`
- `/api/smartsheet/fix-abe`
- `/api/smartsheet/fill-down-preview`
- `/api/smartsheet/fill-down`
- `/api/smartsheet/attachments`
- `/api/smartsheet/download-attachment`
- `/api/smartsheet/batch-download`
- `/api/smartsheet/batch-checkpoint`
- `/api/smartsheet/excel-area-download` (fallback Excel cuando no hay shapefile)
- `/api/smartsheet/add-to-map-script`
- `/api/smartsheet/export-csv`

### Configuracion

- `/api/config`
- `/api/config/paths` (GET, PUT) -- protegido con token local

### AGOL (OAuth 2.0 PKCE)

- `/api/agol/auth/start` -- inicia flujo OAuth
- `/oauth/callback` -- recibe authorization code y crea sesion
- `/api/agol/status` -- estado de conexion, username, org, edad de sesion
- `/api/agol/disconnect` -- limpia sesion, tokens y cache de capas

### Diagnostico, GIS y ArcPy

- `/api/paso0/diagnose` -- diagnostico AGOL vs Smartsheet (operado como Paso 1-a)
- `/api/paso0/csv` -- exporta resultados del diagnostico a CSV
- ~~`/api/crosscheck/upload-gis-summary`~~ (Removed)
- ~~`/api/crosscheck/run`~~ (Removed)
- ~~`/api/crosscheck/report`~~ (Removed)
- ~~`/api/shp-validate/script`~~ (Removed)
- `/api/arcpy/generate-script`
- `/api/arcpy/open-pro` -- protegido con token local
- `/api/arcpy/close-pro` -- protegido con token local
- `/api/arcpy/run-add-to-map` -- protegido con token local
- `/api/arcpy/run-excel-to-point` -- protegido con token local (Excel → FC de puntos)
- `/api/verify/3way`
- `/api/verify/3way/script`

### Estructura trimestral y agente

- `/api/quarterly/create`
- `/api/paso1-agent/state`
- `/api/paso1-agent/init`
- `/api/paso1-agent/mark-complete`
- `/api/paso1-agent/mark-skip`
- `/api/paso1-agent/reset`

### Criterios y resultados de limpieza

- `/api/criteria/`
- `/api/criteria/<quarter>`
- `/api/criteria/<quarter>/add`
- `/api/criteria/<quarter>/export-pdf`
- `/api/pipeline/cleaning-stats`

### Excel, Dafne y comparacion M&E

- `/api/paso5/generate-excel`
- `/api/dafne/validate`
- `/api/dafne/place`
- `/api/dafne/status`
- `/api/dafne/receive`
- `/api/dafne/history`
- `/api/dafne/quarters`
- `/api/compare/me`
- `/api/compare/me/drill`
- `/api/compare/me/decision`
- `/api/compare/me/report`

### Power BI, reportes y respaldo

- `/api/pbi/status`
- `/api/pbi/launch`
- `/api/pbi/wait`
- `/api/pbi/tables`
- `/api/pbi/publish-check`
- `/api/pbi/embed-url`
- `/api/pbi/export-pdf`
- `/api/paso7/error-report`
- `/api/paso7/data-summary`
- `/api/paso7/backup`

### Orquestador

- `/api/orchestrator/start`
- `/api/orchestrator/status`
- `/api/orchestrator/advance`
- `/api/orchestrator/retry`
- `/api/orchestrator/advance-substep`

---

## Modelo de Seguridad y Operacion

| Aspecto | Estado actual |
|:--------|:--------------|
| Tokens y credenciales | permanecen del lado del servidor |
| OAuth AGOL | flujo PKCE sin contraseña; token en memoria con TTL 60 min |
| Token local de sesion | endpoints sensibles (rutas, ArcGIS Pro, Power BI, Excel→puntos) requieren `X-Local-Token` |
| Validacion de rutas | todas las rutas de usuario deben pasar por `safe_resolve()` |
| Extraccion ZIP | se valida cada miembro antes de extraer (ZIP-Slip) |
| Debug mode | controlado por `FLASK_DEBUG` |
| SSRF | `publish-check` acepta solo dominios permitidos de Power BI; URLs AGOL filtradas |
| Render seguro | el frontend usa escape de HTML para datos del servidor |
| Integridad de codigo | `CÓDIGO DE LA ACTIVIDAD` no debe modificarse una vez asignado |
| Rutas portables | `${ONEDRIVE_*}` se expande al arranque desde `env_paths.py` |

---

## Resumen Ejecutivo

La implementacion actual ya no es solo un panel lineal de 7 pasos. Es una
herramienta operativa completa que combina:

- diagnostico inicial operado como Paso 1-a (con login OAuth a AGOL)
- carga y correccion de datos
- descarga robusta de shapefiles con fallback Excel-a-puntos
- estructura de carpetas y group layers de ArcGIS Pro por trimestre
- validaciones GIS y AGOL
- recepcion de M&E desde Dafne
- comparacion contra Power BI
- documentacion y cierre con respaldo
- interfaz bilingue (espanol / ingles) y scripts ArcPy bilingues
- rutas `.env` portables entre PCs gracias a `${ONEDRIVE_*}`

Por eso, los documentos de flujo y funcionalidades deben leerse como guias de
operacion actual, no como una descripcion historica del primer pipeline.