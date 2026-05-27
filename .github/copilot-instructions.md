# Project Guidelines

## Scope
- Limit implementation changes to the Flask app surface: [app.py](../app.py), [ar_utils.py](../ar_utils.py), [build_config.py](../build_config.py), [templates/](../templates/), [static/](../static/), [tests/](../tests/), and new Python modules that support the Flask server.
- Do not modify production notebooks under `01_Ssheet_DataCollect/` or `02_ArcGIS_MapUpdater/`, except `.env` path changes when explicitly required.
- Do not modify `03_PowerBI_Dashboard/` unless the task explicitly targets Power BI assets.

## Architecture
- The project is a Flask dashboard for a 7-step pipeline. [app.py](../app.py) serves the UI and API routes, [orchestrator.py](../orchestrator.py) coordinates step execution, and [pipeline_state.py](../pipeline_state.py) persists pipeline status.
- Keep reusable logic in small Python modules or [ar_utils.py](../ar_utils.py); prefer testable functions over route-level inline logic.
- Use [Architecture.md](../Architecture.md) for the top-level repository architecture, [docs/FEATURES.md](../docs/FEATURES.md) for module and endpoint context, and [docs/WORKFLOW_STEPS.md](../docs/WORKFLOW_STEPS.md) for the expected user flow.
- In operator-facing documentation, AGOL vs Smartsheet diagnosis should be explained as Paso 1-a even when backend names still use `paso0`.

## Build And Test
- Use the local virtual environment before running Python commands. Windows helpers are [setup.bat](../setup.bat) and [run.bat](../run.bat).
- Manual setup: `python -m venv .venv` then `.venv\Scripts\activate` then `pip install -r requirements.txt`.
- Run the app with `flask --app app run --host 127.0.0.1 --port 5000` or `python app.py`.
- Run all tests: `pytest tests/`. Run a single file: `pytest tests/test_ar_utils.py -v`. Run a single test: `pytest tests/test_ar_utils.py::test_safe_resolve_valid -v`.
- Many runtime flows depend on `.env`, Smartsheet access, local folders, and ArcGIS Pro. Prefer unit tests and isolated Flask-side validation unless the task requires integration behavior.
- On Windows with OneDrive or strict ACLs, `tmp_path` cleanup can fail. The `conftest.py` fixture `_fix_windows_tmp_cleanup` (autouse) handles this — do not replicate it in individual tests.

## UI And Content Conventions
- Follow the brand rules in [documents/07_DESIGN_PRINCIPLES.md](../documents/07_DESIGN_PRINCIPLES.md). Use the AR color variables and Helvetica Neue stack; do not substitute unrelated green or blue values.
- Preserve the existing dashboard patterns in [templates/dashboard.html](../templates/dashboard.html), [static/app.js](../static/app.js), and [static/style.css](../static/style.css) unless the task requires a broader redesign.
- User-facing help text, print output, and explanatory comments for non-technical users should remain bilingual Spanish/English.
- Keep general filenames and code content in English. Files created under `docs/` must use Spanish filenames and Spanish content. Korean copies belong under `documents/` with an `_kr` suffix only when explicitly requested.

## Security Guidelines (Audit 2026-04-06)
- **Path validation**: All user-provided filesystem paths must pass through `safe_resolve()` from `ar_utils.py` before any filesystem operation. Never use `os.path.join()` or `pathlib.Path()` with user input without validation.
- **ZIP extraction**: Never use `zipfile.ZipFile.extractall()` without first validating all member paths. Use the safe extraction pattern in `ar_utils.py`.
- **SSRF prevention**: Server-side HTTP requests must validate URLs against allowed domain whitelists. The Power BI publish-check only accepts `*.powerbi.com` HTTPS URLs.
- **Debug mode**: Never hardcode `debug=True`. Use `os.getenv("FLASK_DEBUG", "0") == "1"`.
- **XSS prevention**: In `static/app.js`, always use `escapeHtml()` when inserting server data via `innerHTML`. Prefer `textContent` or DOM construction where possible. Never construct inline `onclick` attributes with dynamic content.
- **Design tokens**: Never use inline hex colors in JavaScript. Use CSS utility classes (`.text-error`, `.text-warning`, `.text-success`, `.bg-error`, etc.) defined in `static/style.css`.
- **Error codes**: Use `friendly_error()` for all backend error responses. Add new error codes to the catalog in `app.py` (documented in `documents/03_S3_ERROR_MESSAGES.md`).
- Reference: `documents/plan-audit-remediation.md` for full remediation plan.

## Key Patterns

### Error responses
All backend errors must use `friendly_error(error_code, **kwargs)` from `app.py`. This returns a structured dict with `error_code`, `title`, `message`, and `action` in Spanish (user language). Add new error codes to the `ERROR_MESSAGES` catalog in `app.py`; document them in `documents/03_S3_ERROR_MESSAGES.md`.

### Protected endpoints
Sensitive routes (filesystem paths, ArcGIS Pro control, Power BI launch) are listed in `_PROTECTED_PREFIXES`. They require an `X-Local-Token` header matching the session token (`_LOCAL_TOKEN`) generated at startup. When adding new sensitive routes, add them to that tuple.

### Paso naming vs. backend naming
Backend endpoints named `paso0` implement the AGOL-vs-Smartsheet diagnosis. For operators and all user-facing text this is **Paso 1-a**, not a standalone pre-step. The pipeline proper runs Paso 1–7.

### C2 multi-shapefile handling
Component C2 can have multiple SHP ZIPs per summary row. They coexist in one `-Shapes` folder. `_cdg_mapping.json` stores the full child-row list. AbE narrowing happens inside ArcPy, not by writing separate mapping files per attachment. See `docs/LOGICA_MULTI_SHP_C2.md`.

### Smartsheet response cache
`app.py` caches Smartsheet API responses in `_SS_CACHE` (keyed by component + sheet_id, TTL 300 s). When adding new Smartsheet reads, use or update this cache rather than making unconditional API calls.

## Workflow Conventions
- For substantial feature work, create planning files under [documents/](../documents/): `plan-*.md` for the main plan and `plan-*-parallel.md` for parallel execution. Do not use `.claude/plans/`.
- Link to existing docs instead of duplicating them. Feature-specific UX specs live in [documents/01_S1_WIZARD.md](../documents/01_S1_WIZARD.md) through [documents/06_S6_SUMMARY_DASHBOARD.md](../documents/06_S6_SUMMARY_DASHBOARD.md).
- Use [docs/TEST_COVERAGE_ANALYSIS.md](../docs/TEST_COVERAGE_ANALYSIS.md) when deciding whether to extend or adjust tests.
- Treat [docs/](../docs/) as the final Spanish operator package and [documents/](../documents/) as the internal planning and Korean-draft package. Keep those two layers synchronized when workflow language changes.
- Screenshot-based slide decks and final Wizard copy polishing belong to the final software-goal milestone. Before that milestone, focus on architecture, workflow, manual, and training-guide alignment rather than claiming final UI completion.