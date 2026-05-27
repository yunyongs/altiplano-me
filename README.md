# Altiplano Resiliente — Map Updater

> Panel de control web para la actualización trimestral de mapa, validación GIS,
> publicación AGOL y seguimiento Power BI de Altiplano Resiliente.
> Está orientado a una persona operadora no técnica que ejecuta el flujo desde el navegador.

---

## ¿Qué hace este proyecto?

Automatiza el flujo de trabajo trimestral de actualización cartográfica del proyecto Altiplano Resiliente (IUCN/GEF), que conecta:

```
Smartsheet  ──▶  ArcGIS Pro  ──▶  ArcGIS Online  ──▶  Power BI Dashboard
    (datos)        (SIG local)       (publicación)        (reporte web)
```

El servidor Flask actúa como intermediario: lee datos de Smartsheet, genera scripts ArcPy listos para pegar en ArcGIS Pro, coordina el pipeline y mantiene un paquete documental para operación y capacitación.

Además del pipeline principal, la operación actual usa un diagnóstico inicial que,
en la documentación para usuario, debe entenderse como Paso 1-a.

La interfaz es **bilingüe (español / inglés)** con un toggle persistido en
`localStorage`. Los scripts ArcPy generados también respetan el idioma del
operador (`lang: "es" | "en"`).

---

## Dónde empezar

Use esta guía según su perfil.

### Si necesita una vista general del repositorio

- [Architecture overview](Architecture.md)
- [Índice documental](docs/INDICE_DOCUMENTAL.md)

### Si va a operar el sistema

- [Guía de instalación](docs/GUIA_INSTALACION.md)
- [Flujo operativo](docs/WORKFLOW_STEPS.md)
- [Manual operativo no técnico](docs/MANUAL_OPERATIVO_NO_TECNICO.md)
- [Guía de capacitación](docs/GUIA_CAPACITACION_OPERATIVA.md)

### Si va a revisar planes, borradores o alineación interna

- [Índice interno de documentos](documents/INDICE_DOCUMENTOS_kr.md)
- [Especificación Wizard](documents/01_S1_WIZARD.md)
- [Borrador coreano del flujo](documents/WORKFLOW_STEPS_kr.md)

---

## Flujo operativo actual

La interfaz todavía conserva nombres históricos como `paso0` (en endpoints
internos), pero la lectura correcta para operación es esta:

1. Paso 1-a — abrir vista previa, filtrar C2 por PPD o PMD cuando corresponda, conectar AGOL y ejecutar diagnóstico
2. Paso 1 — usar el panel derecho como cola de trabajo y resolver shapefiles pendientes uno por uno
3. Paso 1b — descarga, validación y preparación de shapefiles (incluye fallback Excel→puntos)
4. Paso 3 a Paso 7 — ArcPy, AGOL, Excel, M&E, Power BI, reportes y respaldo

> **Nota:** Paso 2 (Control Cruzado, módulos `paso2_crosscheck.py` y `paso2_shp_validate.py`)
> fue eliminado del sistema. El control cruzado real ahora se realiza dentro del
> Paso 1-a (Diagnóstico AGOL vs Smartsheet) y en el Paso 4 (Verificación 3 fuentes).

## Pipeline — Pasos actuales

| Paso | Nombre | Cómo se ejecuta |
|:----:|:-------|:----------------|
| 1-a | Diagnóstico AGOL vs Smartsheet | Automático — Flask → AGOL OAuth + API Smartsheet |
| 1 | Recolección y saneamiento (Smartsheet) | Automático + bucle agente |
| 1b | Descarga shapefiles + fallback Excel→puntos | Automático + script ArcPy generado |
| 3 | Procesamiento territorial (ArcPy) | Script generado → pegar en ArcGIS Pro |
| 4 | Publicación geoespacial (AGOL) + verificación 3 fuentes | Script generado → pegar en ArcGIS Pro |
| 5 | Excel maestro + recepción Dafne M&E | Automático — Flask → archivo local |
| 6 | Actualización Power BI + comparación M&E | Script generado + comparación interactiva |
| 7 | Documentación, guía PDF, Publish-to-Web y respaldo | Automático — reportes + backup |

El **Orquestador** (`orchestrator.py`) coordina los pasos, rastrea el estado de cada uno y espera confirmación manual para los que requieren ArcGIS Pro.

> Nota operativa: para capacitación y operación diaria, el diagnóstico AGOL vs Smartsheet se enseña como Paso 1-a, no como un paso aislado.

---

## Instalación y uso

### Requisitos
- Python 3.10+
- Token de API de Smartsheet
- ArcGIS Pro (para los pasos 3 y 4)
- Cuenta ArcGIS Online con app OAuth registrada (para pasos 1-a y 4)
- OneDrive sincronizado (opcional, pero recomendado para rutas portables)

### Configurar

```bash
git clone https://github.com/yunyongs/altiplano.git
cd altiplano

# Opción recomendada en Windows
setup.bat

# Opción manual
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# Editar .env con tus credenciales
```

### Ejecutar

```bash
run.bat

# O manualmente
python app.py
```

Abrir en el navegador: **http://localhost:5000**

> Para acceso desde otra máquina en la misma red, use una configuración explícita del servidor Flask y una red de confianza.

---

## Variables de entorno (`.env`)

| Variable | Descripción | Ejemplo |
|:---------|:------------|:--------|
| `SMARTSHEET_TOKEN` | Token de API de Smartsheet | `abc123...` |
| `SHEET_C1` | ID de hoja — Componente 1 | `1234567890` |
| `SHEET_C2` | ID de hoja — Componente 2 | `0987654321` |
| `SHEET_C3` | ID de hoja — Componente 3 | `1122334455` |
| `FOLDER_C1` | Carpeta local de descargas C1 | `${ONEDRIVE_IUCN}\AR\C1` |
| `FOLDER_C2` | Carpeta local de descargas C2 | `${ONEDRIVE_IUCN}\AR\C2` |
| `FOLDER_C3` | Carpeta local de descargas C3 | `${ONEDRIVE_IUCN}\AR\C3` |
| `ARCGIS_ORG_URL` | URL de organización AGOL (también editable desde la UI) | `https://iucn.maps.arcgis.com` |
| `ARCGIS_CLIENT_ID` | Client ID de app OAuth registrada en AGOL | `abcDEF1234...` |
| `AGOL_POLYGON_ITEM_ID` | Item ID de la capa de polígonos AR_EbA_Area | `32-char hex` |
| `AGOL_POINT_ITEM_ID` | Item ID de la capa de puntos AR_EbA_Area | `32-char hex` |
| `AGOL_POLYGON_URL` | URL fallback de capa de polígonos | `https://services.../FeatureServer/0` |
| `AGOL_POINT_URL` | URL fallback de capa de puntos | `https://services.../FeatureServer/0` |
| `APRX` | Ruta al proyecto ArcGIS Pro | `${ONEDRIVE_DATAME}\AR.aprx` |
| `AR_MAP_NAME` | Nombre del mapa dentro del .aprx | `AR_EbA_Area` |
| `CSVPOINT_TO_GDB` | Geodatabase para feature classes de puntos (fallback Excel) | `${ONEDRIVE_DATAME}\AR_Points.gdb` |
| `ARCPY_PYTHON` | Python.exe del conda env de ArcGIS Pro (autodetectado por `setup.bat`) | `C:\...\arcgispro-py3\python.exe` |

> **Marcadores `${ONEDRIVE_*}`**: El módulo `env_paths.py` detecta automáticamente
> `OneDrive - IUCN…` o `OneDrive - DataME` bajo `%USERPROFILE%` y los expande al
> arranque del servidor. Permite que el mismo `.env` funcione en PCs con distintas
> letras de unidad (E:, C:, D:, …). Los placeholders soportados actualmente son
> `${ONEDRIVE_DATAME}` y `${ONEDRIVE_IUCN}`.

---

## Estructura del proyecto

```
altiplano/
│
├── app.py                   # Servidor Flask — rutas y endpoints API (~78 endpoints)
├── ar_utils.py              # Utilidades compartidas: rutas, ZIP, AbE, shapefile, Excel, streaming
├── build_config.py          # Generador de config.js desde .env
├── env_paths.py             # Resolución portable de OneDrive (${ONEDRIVE_*})
├── agol_connect.py          # Conexión AGOL vía OAuth 2.0 PKCE (token, GIS, capas)
├── Architecture.md          # Resumen de arquitectura y mapa documental
│
├── orchestrator.py          # Orquestador del pipeline (PASOs 1–7)
├── pipeline_state.py        # Estado persistente del pipeline (JSON)
│
├── paso1_quarterly.py       # Estructura trimestral + script "agregar SHP al mapa"
├── paso1_agent.py           # Estado del bucle agente (cola de trabajo Paso 1)
├── paso1_excel_to_point.py  # Fallback Excel-de-áreas → CSV → FC de puntos
├── paso3_scripts.py         # Generadores de scripts ArcPy — PASO 3
├── paso3_criteria.py        # CRUD de criterios de limpieza por trimestre
├── paso3_pdf_report.py      # Generación de reporte PDF de solapamiento
├── paso4_scripts.py         # Generadores de scripts AGOL — PASO 4
├── paso5_dafne.py           # Validación y recepción de M&E
├── paso6_compare.py         # Comparación M&E Dafne vs Power BI
├── paso6_powerbi.py         # Generadores de scripts Power BI — PASO 6
├── paso7_reports.py         # Reportes de errores, resúmenes y backups
├── pbi_refresh.py           # Detección y lanzamiento de Power BI Desktop
├── paso_constants.py        # Constantes del dominio (microcuencas, AbE, etc.)
│
├── templates/
│   └── dashboard.html       # Panel de control HTML
├── static/
│   ├── app.js               # Lógica frontend (fetch API, log de actividad)
│   └── style.css            # Estilos responsivos (card-based, dark log)
│
├── tests/                   # Suite de pruebas unitarias (pytest)
│
├── docs/
│   ├── INDICE_DOCUMENTAL.md         # Índice del paquete documental final
│   ├── FEATURES.md                  # Funciones y módulos actuales
│   ├── WORKFLOW_STEPS.md            # Flujo operativo actualizado
│   ├── UI_MOCKUP.md                 # Estructura de pantalla actual
│   ├── GUIA_INSTALACION.md          # Instalación y arranque
│   ├── MANUAL_OPERATIVO_NO_TECNICO.md # Manual para persona operadora
│   ├── GUIA_CAPACITACION_OPERATIVA.md # Guía de capacitación
│   ├── TEST_COVERAGE_ANALYSIS.md    # Análisis de cobertura de pruebas
│   ├── LOGICA_MULTI_SHP_C2.md       # Lógica de múltiples shapefiles C2
│   ├── PIPELINE_ACTUALIZACION_PBI.md # Pipeline de actualización Power BI
│   └── AR_Area_DataSchema.pdf       # Esquema de datos de áreas
│
├── documents/                  # Borradores coreanos, planes, auditorías y diseño
│
├── 01_Ssheet_DataCollect/                 # Notebooks de recolección (producción)
├── 02_ArcGIS_MapUpdater/                  # Notebooks ArcPy (producción)
│
└── requirements.txt
```

---

## Funcionalidades principales

### PASO 1-a — Diagnóstico AGOL vs Smartsheet (vía OAuth)
- Conectar a ArcGIS Online con OAuth 2.0 PKCE (sin contraseñas en el servidor)
- Resolver capas AGOL por Item ID — soporta capas privadas/licenciadas
- Filtrar C2 por PPD o PMD antes de diagnosticar
- Clasificar actividades: `verified_match`, `verified_mismatch`, `new`
- Exportar resultados del diagnóstico a CSV
- Highlight de filas con discrepancia en la vista previa

### PASO 1 — Smartsheet
- Previsualizar datos de la hoja en tabla HTML
- Generar `CÓDIGO DE LA ACTIVIDAD` faltantes automáticamente (regla de inmutabilidad respetada)
- Actualizar estado `Calidad SIG` (Espera / Sí) según adjuntos
- Corregir fechas en formato texto, normalizar AbE y aplicar fill-down con vista previa
- Bucle agente (Agent Loop): cola de trabajo con estado por item (init, mark-complete, mark-skip, mark-pending, reset)

### PASO 1b — Descarga y preparación
- Descargar shapefiles ZIP con validación automática (extracción segura ZIP-Slip + verificación de `.shp`)
- Streaming download con checkpoint para reanudar batches interrumpidos
- Lógica C2 multi-SHP: múltiples ZIPs por fila resumen con desambiguación por pista AbE
- Deduplicación: SHP repetidos en distintos hijos se procesan una sola vez
- **Fallback Excel de áreas**: cuando una fila no tiene shapefile, se descarga el Excel de áreas y se convierte a feature class de puntos (XYTableToPoint, GTM)
- Estructura trimestral: `{base}/{T2026_Q2}/{C1|C2|C3}/{identificador}/`
- Generar script ArcPy para agregar SHP al mapa dentro de group layers (`2026_Q1`, `2026_Q1_point`, `2026_Q1_polygon`)
- Exportar hoja a CSV para importar a ArcGIS Pro

### PASOS 3–4 — Scripts ArcPy
- Generar scripts completos para pegar en la ventana Python de ArcGIS Pro:
  - Merge con field mapping (trimestre actual + oficial anterior)
  - Importar CSV a geodatabase
  - Reparar geometría y calcular hectáreas
  - Análisis de solapamiento y reporte PDF
  - Pipeline de erase
  - Exportar feature class a Excel
  - Sobrescribir capa en ArcGIS Online
- Criterios de limpieza por trimestre con CRUD y exportación PDF
- Estadísticas antes/después de limpieza
- Verificación 3 fuentes (Smartsheet vs GIS vs AGOL)

### PASO 5 — Excel Maestro
- Exportar C1 + C2 + C3 a un único `.xlsx` con una hoja por componente
- Validar y recibir `Tbl_Integrado.xlsx` de Dafne cuando aplica
- Historial de recepciones M&E por trimestre

### PASO 6 — Power BI
- Verificar estado de Power BI Desktop y abrir PBIP
- Consultar tablas disponibles en el modelo Power BI local
- Generar script de actualización del dataset vía autenticación DeviceCode
- Comparar valores M&E entre Dafne y Power BI con drill-down por indicador
- Guardar decisiones finales de la comparación M&E

### PASO 7 — Reportes y Respaldo
- Reporte de errores estructurado (pipeline + control cruzado)
- Resumen de datos del pipeline completo
- Guía PDF para exportar desde Power BI
- Verificación de enlace Publish-to-Web y URL de incrustación
- Backup con marca de tiempo de carpeta local

---

## Seguridad

El servidor Flask opera en `127.0.0.1` (solo acceso local) por defecto.

| Medida | Descripción |
|:-------|:------------|
| Validación de rutas | `safe_resolve()` verifica que rutas del usuario estén dentro de directorios permitidos |
| Protección ZIP-Slip | Se validan miembros del ZIP antes de extraer; se rechazan rutas con `..` |
| Mitigación SSRF | El endpoint de verificación de Power BI solo acepta dominios `*.powerbi.com`; URLs AGOL pasan por `_safe_agol_url()` |
| Token local de sesión | Endpoints sensibles (rutas de config, lanzar Power BI/ArcGIS Pro) requieren cabecera `X-Local-Token` generada al arranque |
| OAuth 2.0 PKCE para AGOL | Sin contraseñas en el servidor; tokens en memoria con refresh automático cada 60 min |
| Modo debug | Controlado por variable `FLASK_DEBUG` (apagado por defecto) |
| Escape XSS | Datos del servidor se escapan con `escapeHtml()` antes de renderizar |
| Reintentos Smartsheet | Backoff exponencial en respuestas 429 y errores transitorios |
| Inmutabilidad de `CÓDIGO DE LA ACTIVIDAD` | El backend nunca sobrescribe ni borra códigos ya asignados |

> Detalles completos: `documents/audit-summary-gpt54.md` y `documents/plan-audit-remediation.md`

---

## Tests

```bash
pytest tests/
```

La suite cubre: `agol_connect`, `app_config`, `ar_utils`, `build_config`, `env_paths`, `error_messages`, `orchestrator`, `pipeline_state`, `paso_constants`, `paso0_diagnose`, `paso1_agent`, `paso1_agent_integration`, `paso1_quarterly`, `paso2_shp_validate` (legado), `paso3_cleaning_stats`, `paso3_criteria`, `paso3_pdf_report`, `paso3_scripts`, `paso4_3way_verify`, `paso5_dafne`, `paso5_me_reception`, `paso6_compare`, `paso6_pdf_export`, `paso6_publish_check`, `ss_filters`.
Pruebas de seguridad: validación de rutas, ZIP-Slip, SSRF, reintentos Smartsheet, expansión segura de `${ONEDRIVE_*}` (ver `docs/TEST_COVERAGE_ANALYSIS.md`).

---

## Documentación adicional

- [Architecture overview](Architecture.md)
- [Índice documental](docs/INDICE_DOCUMENTAL.md)
- [Índice interno de documentos](documents/INDICE_DOCUMENTOS_kr.md)
- [Arquitectura y endpoints completos](docs/FEATURES.md)
- [Guía detallada por paso](docs/WORKFLOW_STEPS.md)
- [Bocetos de interfaz](docs/UI_MOCKUP.md)
- [Guía de instalación y uso](docs/GUIA_INSTALACION.md) (español)
- [Manual operativo no técnico](docs/MANUAL_OPERATIVO_NO_TECNICO.md)
- [Guía de capacitación operativa](docs/GUIA_CAPACITACION_OPERATIVA.md)
- [Especificación Wizard](documents/01_S1_WIZARD.md)
- [Borrador coreano del flujo](documents/WORKFLOW_STEPS_kr.md)
- [Análisis de cobertura de pruebas](docs/TEST_COVERAGE_ANALYSIS.md)
- [Pipeline de actualización Power BI](docs/PIPELINE_ACTUALIZACION_PBI.md)
- [Auditoría de seguridad](documents/audit-security-gpt54.md)
- [Auditoría de integraciones](documents/audit-integrations-gpt54.md)
- [Auditoría de frontend](documents/audit-frontend-gpt54.md)
- [Plan de remediación](documents/plan-audit-remediation.md)

---

## Estado del roadmap documental

Las siguientes tareas pertenecen al hito final del producto y todavía no deben
considerarse terminadas solo por existir estos documentos:

- materiales de capacitación en formato de diapositivas con capturas reales de pantalla
- ajuste final del texto del Wizard y de los botones según la interfaz final

Por ahora, el repositorio mantiene alineados el plan, la arquitectura, el flujo
operativo y el manual de operación.

Para navegar ese conjunto sin perder contexto:

1. empiece en este README
2. pase a `Architecture.md` para entender capas y responsabilidades
3. use `docs/INDICE_DOCUMENTAL.md` para documentos finales en español
4. use `documents/INDICE_DOCUMENTOS_kr.md` para borradores, planes y alineación interna
