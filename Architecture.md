# Architecture Overview

This document summarizes the current repository architecture, the operator-facing
workflow model, and the documentation structure used to keep planning and
handoff materials aligned.

Related entry points:

- `README.md` for repository overview and quick start
- `docs/INDICE_DOCUMENTAL.md` for the final Spanish operator package
- `documents/INDICE_DOCUMENTOS_kr.md` for internal planning and Korean drafts

---

## Reading Paths

Use the document set by role.

### For repository orientation

1. `README.md`
2. `Architecture.md`
3. `docs/FEATURES.md`

### For operator-facing workflow understanding

1. `docs/GUIA_INSTALACION.md`
2. `docs/WORKFLOW_STEPS.md`
3. `docs/UI_MOCKUP.md`
4. `docs/MANUAL_OPERATIVO_NO_TECNICO.md`
5. `docs/GUIA_CAPACITACION_OPERATIVA.md`

### For internal alignment and planning

1. `documents/INDICE_DOCUMENTOS_kr.md`
2. `documents/01_S1_WIZARD.md`
3. `documents/WORKFLOW_STEPS_kr.md`
4. `documents/UI_MOCKUP_kr.md`
5. `documents/GUIA_CAPACITACION_OPERATIVA_kr.md`

---

## System Purpose

This repository implements the **Monitoring and Evaluation (M&E) system** for the
**Altiplano Resiliente (IUCN)** project. It is structured as a **data pipeline and
workflow** that runs the project's quarterly M&E cycle: collecting field-reported
data, processing it into geospatial information and indicators, publishing it, and
making it available for tracking and decision-making.

The system orchestrates work across:

- Smartsheet (field M&E data)
- ArcGIS Pro (geospatial processing)
- ArcGIS Online (geospatial publication)
- Power BI (M&E indicators / reporting)
- local filesystem workflows

The **Map Updater** — the quarterly cartographic update — is **one component** of
this M&E system (the geospatial pipeline). Around it, the system also covers data
collection and cleaning, M&E reception (Dafne), indicator comparison, and reporting.

A Flask-based dashboard is the operator-facing surface of the system. It is designed
for a non-technical operator who can execute the pipeline from the browser while
still relying on ArcGIS Pro for manual script execution in selected stages.

> **Scope note.** The M&E system design will continue to grow over time. This
> document describes the current state (centered on the geospatial pipeline /
> Map Updater) and will be updated as new monitoring and evaluation modules are
> added.

---

## Architectural Layers

### 1. Flask application layer

- `app.py` exposes the UI and ~78 API routes; mounts the local-token
  middleware that protects sensitive endpoints (config writes, ArcGIS Pro /
  Power BI launchers) with a per-session `X-Local-Token`
- `orchestrator.py` coordinates major steps and substeps
- `pipeline_state.py` persists step status, warnings, and failures

### 2. Environment and connection layer

- `env_paths.py` resolves portable OneDrive roots and expands
  `${ONEDRIVE_DATAME}` / `${ONEDRIVE_IUCN}` placeholders inside `.env` at
  startup, so the same `.env` works across PCs with different drive letters
- `agol_connect.py` centralises AGOL authentication via OAuth 2.0 PKCE,
  token lifecycle (60-min refresh), GIS singleton, and Item-ID-to-FeatureLayer
  resolution with caching; raw token is also exposed via `get_token()` for
  REST-based feature queries against private layers
- `build_config.py` generates `config.js` from `.env` and template

### 3. Domain and integration layer

- `ar_utils.py` handles reusable logic: path validation, ZIP-Slip-safe
  extraction, AbE normalisation, Smartsheet request retries, shapefile and
  DBF introspection (pure Python, no arcpy), streaming downloads, plus
  filename heuristics (`is_shape_zip_attachment`, `is_area_excel_attachment`,
  `extract_abe_hint_from_filename`, `extract_hectares_from_filename`)
- `paso_constants.py` provides domain constants: microcuencas, AbE types, areas, grants
- `paso1_quarterly.py` manages quarterly folder structure, placement of
  shapefiles, and the ArcPy `script_add_shapefiles_to_map` generator that
  builds `2026_Q1`, `2026_Q1_point`, and `2026_Q1_polygon` group layers
- `paso1_agent.py` manages the agent loop work queue state: init, update,
  load, mark-pending, and reset per item
- `paso1_excel_to_point.py` provides the Excel fallback path: parses *área*
  workbooks (DMS → decimal degrees, WGS84 ↔ GTM transformation), generates
  the CSV, and emits an ArcPy `XYTableToPoint` script that lands the FC in
  `CSVPOINT_TO_GDB` and adds it to the configured map
- `paso3_scripts.py` and `paso4_scripts.py` generate ArcPy scripts (bilingual)
- `paso3_criteria.py` handles CRUD for cleaning criteria by quarter
- `paso3_pdf_report.py` generates overlap analysis PDF reports
- `paso5_dafne.py` covers M&E validation, reception, and history
- `paso6_compare.py` compares M&E values between Dafne and Power BI
  with drill-down and decision saving
- `paso6_powerbi.py` covers Power BI refresh, publish-check, and embed URL
- `paso7_reports.py` provides summaries, error reports, and backup behavior
- `pbi_refresh.py` detects Power BI Desktop, finds the local MCP port,
  and launches the PBIP file

> **Removed legacy modules:** `paso2_crosscheck.py` (Smartsheet vs GIS engine)
> and `paso2_shp_validate.py` are no longer wired into `app.py`. The
> cross-check function migrated into the Paso 1-a diagnosis and the Paso 4
> three-source verification. The `paso2_shp_validate.py` test still runs as
> coverage of legacy helper code.

### 4. Frontend layer

- `templates/dashboard.html` defines the main dashboard layout with
  per-element bilingual spans (`lang-es` / `lang-en`) and `data-title-*`,
  `data-aria-*` attributes for tooltips and accessibility labels
- `static/app.js` implements UI behavior, API calls, wizard state, logging,
  result rendering, and the language toggle (preference persisted to
  `localStorage`)
- `static/style.css` provides shared styles, design tokens (AR Green,
  AR Blue), and the language-visibility rules

### 5. Validation layer

- `tests/` contains unit and integration-oriented tests for Flask-side logic
  including `test_agol_connect.py` (OAuth PKCE flow + token caching),
  `test_env_paths.py` (OneDrive detection + placeholder expansion),
  `test_paso1_agent_integration.py` (full agent-loop life cycle)
- documentation in `docs/TEST_COVERAGE_ANALYSIS.md` tracks current coverage focus

---

## Operational Workflow Model

The repository still contains backend naming such as `paso0`, but the operator
workflow should be read differently.

### Diagnosis is treated as Paso 1-a

For implementation and documentation purposes:

- the diagnosis endpoint may still be named `paso0`
- the operator should treat diagnosis as Paso 1-a
- diagnosis is not a standalone pre-step in user training

Expected operator sequence:

1. select work quarter
2. select component
3. click **Conectar AGOL** (OAuth 2.0 PKCE flow; browser redirect to
   `http://localhost:5000/oauth/callback`)
4. load sheet preview
5. for C2, choose PPD or PMD first
6. run diagnosis in that filtered context
7. use the right-side diagnosis panel as the work queue
8. process pending shapefiles one by one until all are complete

### Completion rule

A diagnosis item is only complete when both conditions are true:

- the shapefile was actually uploaded to ArcGIS Pro
- `CÓDIGO DE LA ACTIVIDAD` was inserted correctly (and never modified
  afterwards — the backend treats it as immutable)

---

## Excel Fallback Path

When a Smartsheet row has no shapefile ZIP attachment but does carry an
*área* Excel workbook (filename keywords: `área`, `area`, `_ha`, `puntos`, …),
the Paso 1 agent calls `/api/smartsheet/excel-area-download` followed by
`/api/arcpy/run-excel-to-point`.  The Excel is parsed by
`paso1_excel_to_point.parse_area_excel()`:

- second sheet (with fallback to first) is read with pandas
- X / Y columns are cleaned, DMS strings are converted to decimal degrees,
  forward-filled, and aggregated by `(X, Y)` summing `Área (ha)` and counting
  beneficiarios
- if coordinates look like WGS84 lat/lon (Guatemala bounding box) they are
  re-projected to GTM (Transverse Mercator, central meridian −90.5)
- a UTF-8 BOM CSV is written next to the Excel

The generated ArcPy script calls `XYTableToPoint`, creates the FC in
`CSVPOINT_TO_GDB`, and adds it to the configured map inside the
`{quarter}_point` group layer (creating the group on the fly via a
temporary `.lyrx` if needed).

---

## C2 Multi-SHP Handling

Component C2 can contain multiple shapefile ZIP attachments for a single summary row.

Current behavior:

- one folder per summary row identifier
- multiple SHP ZIPs can coexist in the same `-Shapes` folder
- `_cdg_mapping.json` stores the full child-row list for matching
- AbE-specific narrowing happens later in ArcPy matching logic, not by writing
  separate mapping files per attachment

This behavior is documented in `docs/LOGICA_MULTI_SHP_C2.md`.

---

## Documentation Architecture

The repository uses two documentation layers.

### `docs/`

Spanish final-use package for:

- installation
- operations
- training
- user handoff

Core files:

- `docs/INDICE_DOCUMENTAL.md`
- `docs/GUIA_INSTALACION.md`
- `docs/FEATURES.md`
- `docs/WORKFLOW_STEPS.md`
- `docs/UI_MOCKUP.md`
- `docs/MANUAL_OPERATIVO_NO_TECNICO.md`
- `docs/GUIA_CAPACITACION_OPERATIVA.md`

Navigation notes:

- start from `docs/INDICE_DOCUMENTAL.md` if you are curating the final package
- use `docs/WORKFLOW_STEPS.md` as the operational source of truth
- use `docs/MANUAL_OPERATIVO_NO_TECNICO.md` and `docs/GUIA_CAPACITACION_OPERATIVA.md`
  for handoff and training

### `documents/`

Internal package for:

- Korean drafts
- implementation plans
- design specifications
- audits
- alignment notes

Core files:

- `documents/INDICE_DOCUMENTOS_kr.md`
- `documents/01_S1_WIZARD.md`
- `documents/WORKFLOW_STEPS_kr.md`
- `documents/UI_MOCKUP_kr.md`
- `documents/MANUAL_OPERATIVO_NO_TECNICO_kr.md`
- `documents/GUIA_CAPACITACION_OPERATIVA_kr.md`

Navigation notes:

- start from `documents/INDICE_DOCUMENTOS_kr.md` when reviewing draft structure
- use `documents/01_S1_WIZARD.md` for product-intent and guidance model
- use the `_kr` workflow, mockup, manual, and training files to stage wording changes

### Synchronization rule

When the operator flow changes:

1. update the working draft in `documents/`
2. update the operator-facing version in `docs/`
3. verify that Wizard, Workflow, UI Mockup, Manual, and Training Guide use the same language

---

## Deferred Final-Goal Items

The following items belong to the final software-goal milestone, not the current
planning and implementation route:

- slide-style training documents based on real screen captures
- final Wizard UI wording and button copy aligned to the completed product

Until that milestone is reached, keep planning documents, workflow documents,
and operator manuals aligned without claiming final UI completion.

See also:

- `README.md` for quick navigation
- `docs/INDICE_DOCUMENTAL.md` for the Spanish package map
- `documents/INDICE_DOCUMENTOS_kr.md` for the internal working map