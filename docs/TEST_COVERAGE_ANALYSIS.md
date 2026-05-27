# Analisis de Cobertura de Pruebas

## Estado Actual

**Archivos de prueba: 22 | Framework: pytest | CI/CD: pendiente**

El proyecto cuenta con pruebas unitarias en el directorio `tests/` que cubren los modulos principales del servidor Flask.

---

## Suite de Pruebas Existente

| Archivo de prueba | Modulo cubierto | Descripcion |
|:------------------|:----------------|:------------|
| `test_app_config.py` | `app.py` | Configuracion de rutas y parametros Flask |
| `test_ar_utils.py` | `ar_utils.py` | Validacion de ZIPs, extraccion de shapefiles, rutas seguras |
| `test_build_config.py` | `build_config.py` | Generacion de `config.js` desde `.env` |
| `test_error_messages.py` | `app.py` | Catalogo de mensajes de error bilingues |
| `test_orchestrator.py` | `orchestrator.py` | Orquestador del pipeline (PASOs 1-7) |
| `test_paso_constants.py` | `paso_constants.py` | Constantes del dominio (microcuencas, AbE, areas) |
| `test_paso0_diagnose.py` | `app.py` | Diagnostico AGOL vs Smartsheet |
| `test_paso1_agent.py` | `paso1_agent.py` | Bucle agente: init, mark-complete, mark-skip, reset |
| `test_paso1_quarterly.py` | `paso1_quarterly.py` | Estructura trimestral y colocacion de shapefiles |
| `test_paso2_crosscheck.py` | `paso2_crosscheck.py` | Motor de control cruzado Smartsheet vs GIS |
| `test_paso2_shp_validate.py` | `paso2_shp_validate.py` | Validacion de CdgActvdd en shapefiles |
| `test_paso3_cleaning_stats.py` | `app.py` | Estadisticas antes/despues de limpieza |
| `test_paso3_criteria.py` | `paso3_criteria.py` | CRUD de criterios de limpieza por trimestre |
| `test_paso3_pdf_report.py` | `paso3_pdf_report.py` | Generacion de reporte PDF de solapamiento |
| `test_paso3_scripts.py` | `paso3_scripts.py` | Generadores de scripts ArcPy |
| `test_paso4_3way_verify.py` | `app.py` | Verificacion 3 fuentes: Smartsheet vs GIS vs AGOL |
| `test_paso5_dafne.py` | `paso5_dafne.py` | Validacion y colocacion M&E |
| `test_paso5_me_reception.py` | `paso5_dafne.py` | Recepcion e historial de archivos M&E |
| `test_paso6_compare.py` | `paso6_compare.py` | Comparacion Dafne vs Power BI |
| `test_paso6_pdf_export.py` | `paso6_powerbi.py` | Exportacion PDF desde Power BI |
| `test_paso6_publish_check.py` | `paso6_powerbi.py` | Validacion de URL Publish-to-Web |
| `test_pipeline_state.py` | `pipeline_state.py` | Estado persistente del pipeline |

---

## Resumen del Codigo Base

| Archivo | Proposito | Funciones |
|:--------|:----------|:----------|
| `app.py` | Servidor Flask -- ~72 rutas y endpoints API | Rutas PASO 1-7, orquestador, config |
| `ar_utils.py` | Utilidades: validacion de ZIPs, rutas, Smartsheet, AbE | Extraccion, validacion, safe_resolve |
| `build_config.py` | Generador de `config.js` desde plantilla + `.env` | `load_env`, `apply_defaults`, `render`, `main` |
| `orchestrator.py` | Orquestador del pipeline (PASOs 1-7) | Gestion de estado, avance, reintento |
| `pipeline_state.py` | Estado persistente del pipeline (JSON) | Lectura/escritura de estado, logging con debounce |
| `paso_constants.py` | Constantes del dominio | Microcuencas, tipos AbE, areas, grants |
| `paso1_quarterly.py` | Estructura trimestral y colocacion de shapefiles | `create_quarterly_structure`, `place_shapefile` |
| `paso1_agent.py` | Estado del bucle agente (cola de trabajo) | `init_agent_state`, `update_item`, `load`, `reset` |
| `paso2_crosscheck.py` | Motor de control cruzado Smartsheet vs GIS | Comparacion de codigos, areas, KPI |
| `paso2_shp_validate.py` | Validacion de CdgActvdd en shapefiles | `script_validate_shp_codes` |
| `paso3_scripts.py` | Generadores de scripts ArcPy -- PASO 3 | Merge, import, validate, export, erase |
| `paso3_criteria.py` | CRUD de criterios de limpieza | `save_criteria`, `load_criteria`, `export_criteria_pdf` |
| `paso3_pdf_report.py` | Reporte PDF de solapamiento | `script_overlap_pdf_report` |
| `paso4_scripts.py` | Generadores de scripts AGOL -- PASO 4 | Punto, poligono, exportar shapefiles |
| `paso5_dafne.py` | Validacion, recepcion e historial M&E | `validate_integrado_xlsx`, `place_dafne_file`, `receive_me_data` |
| `paso6_compare.py` | Comparacion M&E Dafne vs Power BI | `load_dafne_values`, `load_pbi_values`, `compare_and_decide` |
| `paso6_powerbi.py` | Generadores de scripts Power BI -- PASO 6 | Refresco, publish-check, embed URL |
| `paso7_reports.py` | Reportes de errores, resumenes y backups | Reporte JSON, backup con timestamp |
| `pbi_refresh.py` | Deteccion y lanzamiento de Power BI Desktop | `find_pbi_executable`, `find_pbi_port`, `launch_pbi_desktop` |

---

## Estrategia de Pruebas Recomendada

### Prioridad 1 -- Funciones de logica pura (Alto valor, facil de probar)

Funciones **sin dependencias externas** que se pueden probar directamente con `pytest`:

#### `build_config.py`
- **`load_env()`** -- Parsear archivos `.env`. Probar: entradas validas, comentarios, lineas en blanco, falta de `=`, archivo vacio.
- **`apply_defaults()`** -- Establecer valores predeterminados. Probar: diccionario vacio recibe defaults, claves existentes no se sobrescriben.
- **`render()`** -- Sustitucion de plantillas. Probar: placeholders conocidos reemplazados, desconocidos quedan vacios.
- **`main()`** -- Generacion de configuracion de extremo a extremo. Probar: con archivos temporales.

#### `paso_constants.py` -- Funciones de clasificacion
- **`trata(microcuenca)`** -- Clasifica microcuencas como "TRATAMIENTO" o "CONTROL".
- **`id_area(area)`** -- Mapea tipo de area a ID numerico (Influencia=3, Intervencion=2, Priorizada=1).
- **`abe_eng(abe)`** -- Traduce abreviaciones de restauracion espanol a ingles.
- **`abe(abe_long)`** -- Abrevia nombres de acciones de restauracion.
- **`grants(contrato_org)`** -- Categoriza tipos de subvencion (PPD=Pequeno, PMD=Mediano).

### Prioridad 2 -- Transformaciones de datos (Esfuerzo medio)

Requieren mocking de DataFrames de `pandas` u objetos del SDK de Smartsheet:

- **`paso2_crosscheck.py`** -- Motor de comparacion cruzada. Probar con datos CSV simulados.
- **`paso3_scripts.py`** -- Verificar que los scripts generados contienen las rutas y parametros correctos.
- **`paso4_scripts.py`** -- Verificar scripts de actualizacion AGOL.

### Prioridad 3 -- Pruebas de integracion (Mayor esfuerzo, alto valor)

- **Integracion con API de Smartsheet** -- Mock del cliente Smartsheet para probar flujos de trabajo.
- **Pipeline de coordenadas** -- Probar cadenas de transformacion DMS a DD a GTM con coordenadas de referencia.
- **Flujo de datos de extremo a extremo** -- Datos de Smartsheet a DataFrame a CSV a tabla ArcGIS con datos de muestra.

---

## Ejecutar las pruebas

```bash
pytest tests/
```

La suite cubre: `app_config`, `ar_utils`, `build_config`, `error_messages`, `orchestrator`, `pipeline_state`, `paso_constants`, `paso0_diagnose`, `paso1_agent`, `paso1_quarterly`, `paso2_crosscheck`, `paso2_shp_validate`, `paso3_cleaning_stats`, `paso3_criteria`, `paso3_pdf_report`, `paso3_scripts`, `paso4_3way_verify`, `paso5_dafne`, `paso5_me_reception`, `paso6_compare`, `paso6_pdf_export`, `paso6_publish_check`.

---

## Impacto Estimado

| Prioridad | Pruebas | Ganancia de cobertura | Esfuerzo |
|:----------|:--------|:----------------------|:---------|
| P1 -- Logica pura | ~40-50 pruebas | Cubre todas las reglas de negocio | Bajo |
| P2 -- Transformaciones | ~20-30 pruebas | Cubre correccion del pipeline | Medio |
| P3 -- Integracion | ~10-15 pruebas | Cubre interacciones entre componentes | Alto |
| P4 -- Seguridad | ~15-20 pruebas | Cubre validacion de rutas, ZIP y SSRF | Medio |

---

## Pruebas de Seguridad (Auditoria 2026-04-06)

Requeridas segun la auditoria de seguridad (`documents/audit-security-gpt54.md`):

### Validacion de rutas (`ar_utils.safe_resolve`)

| Prueba | Que valida |
|:-------|:-----------|
| `test_safe_resolve_allowed_path` | Ruta dentro de directorio permitido se acepta |
| `test_safe_resolve_traversal_rejected` | Ruta con `..` que escapa del directorio raiz se rechaza |
| `test_safe_resolve_absolute_escape` | Ruta absoluta fuera de directorios permitidos se rechaza |
| `test_safe_resolve_empty_path` | Ruta vacia lanza `ValueError` |
| `test_safe_resolve_symlink_escape` | Enlace simbolico que apunta fuera de raiz se rechaza |

### Extraccion segura de ZIP (`ar_utils.extract_and_validate_zip`)

| Prueba | Que valida |
|:-------|:-----------|
| `test_zip_normal_extraction` | ZIP con miembros normales se extrae correctamente |
| `test_zip_slip_parent_traversal` | ZIP con miembros `../malicious.txt` se rechaza |
| `test_zip_slip_absolute_path` | ZIP con miembros de ruta absoluta se rechaza |
| `test_zip_empty_file` | ZIP vacio se maneja sin error |

### Mitigacion SSRF (`paso6_powerbi.check_publish_url`)

| Prueba | Que valida |
|:-------|:-----------|
| `test_publish_check_valid_pbi_url` | URL `https://app.powerbi.com/...` se acepta |
| `test_publish_check_rejects_localhost` | URL `http://localhost:8080` se rechaza |
| `test_publish_check_rejects_http` | URL `http://app.powerbi.com` (sin HTTPS) se rechaza |
| `test_publish_check_rejects_arbitrary` | URL `https://evil.com` se rechaza |
| `test_publish_check_rejects_file_scheme` | URL `file:///etc/passwd` se rechaza |

### Rutas en endpoints de Flask (`app.py`)

| Prueba | Que valida |
|:-------|:-----------|
| `test_download_attachment_path_traversal` | `destFolder` con `../../` devuelve 400 |
| `test_dafne_validate_path_traversal` | `file_path` fuera de raiz devuelve 400 |
| `test_backup_path_traversal` | `sourceFolder` fuera de raiz devuelve 400 |
| `test_config_paths_rejects_dotdot` | `PUT /api/config/paths` rechaza valores con `..` |

### Reintento de Smartsheet (`ar_utils.smartsheet_request`)

| Prueba | Que valida |
|:-------|:-----------|
| `test_smartsheet_retry_on_429` | Reintenta con backoff exponencial en respuesta 429 |
| `test_smartsheet_retry_on_connection_error` | Reintenta en errores de conexion transitorios |
| `test_smartsheet_no_retry_on_400` | No reintenta en errores del cliente (400) |
