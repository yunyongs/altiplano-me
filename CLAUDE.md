# Project Rules

## Critical: Do NOT modify Jupyter notebooks
The `.ipynb` files in the following directories are **production notebooks** actively used by the consultant. Never modify them except for `.env` path changes:
- `01_Ssheet_DataCollect/` (e.g., `1_1_AR_Ssheet_Automation.ipynb`)
- `02_ArcGIS_MapUpdater/` (e.g., `2_2_AR_Oficial_ArcPy.ipynb`, `AR_AGL_PowerBI_API.ipynb`)

**Exception:** When the user gives an explicit, unambiguous instruction to modify a specific notebook (e.g., "이 노트북의 커널을 바꿔줘", "edit cell N in this .ipynb"), the modification is permitted. Always create a `.bak` backup before editing, limit changes to exactly what the user requested, and confirm the scope back to the user. Ambiguous or implicit requests still fall under the default prohibition.

## Critical: CÓDIGO DE LA ACTIVIDAD is immutable
Once a `CÓDIGO DE LA ACTIVIDAD` value is set on a Smartsheet row, the system must NEVER modify or clear it. Only the user can change it manually. This is a core data integrity rule for all endpoints.

## Scope of modifications
All implementation work (create/edit/delete) must be limited to Flask server files:
- `app.py`, `ar_utils.py`, `build_config.py`
- `templates/`, `static/`
- `tests/`
- New Python modules as needed for the Flask app
- Repository-level documentation updates are also allowed when they support the Flask dashboard workflow, including `README.md`, `Architecture.md`, and this `CLAUDE.md`.
- Do not modify `03_PowerBI_Dashboard/` unless the task explicitly targets Power BI assets.

## Project context
This repository is the **Monitoring & Evaluation (M&E) system** for the Altiplano Resiliente (IUCN) project — a data pipeline and workflow across Smartsheet → ArcGIS Pro → ArcGIS Online → Power BI. The Map Updater (quarterly cartographic update) is one component (the geospatial pipeline). A Flask dashboard is the operator-facing surface, designed for a non-technical operator who runs the pipeline from the browser. The pipeline runs Paso 1–7; backend endpoints named `paso0` implement the AGOL-vs-Smartsheet diagnosis, surfaced to operators as **Paso 1-a**.

Keep reusable logic in small, testable Python modules or `ar_utils.py`; prefer testable functions over route-level inline logic. Use `Architecture.md` for top-level architecture, `docs/FEATURES.md` for module/endpoint context, and `docs/WORKFLOW_STEPS.md` for the expected user flow.

## Build and test
- Use the local virtual environment before running Python commands. Windows helpers are `setup.bat` (install, run once) and `run.bat` (start the app).
- Manual setup: `python -m venv .venv` then `.venv\Scripts\activate` then `pip install -r requirements.txt`.
- Run the app: `flask --app app run --host 127.0.0.1 --port 5000` or `python app.py`.
- Run all tests: `pytest tests/`. Single file: `pytest tests/test_ar_utils.py -v`. Single test: `pytest tests/test_ar_utils.py::test_safe_resolve_valid -v`.
- Many runtime flows depend on `.env`, Smartsheet access, local folders, and ArcGIS Pro. Prefer unit tests and isolated Flask-side validation unless the task requires integration behavior.
- On Windows with OneDrive or strict ACLs, `tmp_path` cleanup can fail. The autouse `conftest.py` fixture `_fix_windows_tmp_cleanup` handles this — do not replicate it in individual tests.

## Security guidelines (Audit 2026-04-06)
- **Path validation**: All user-provided filesystem paths must pass through `safe_resolve()` from `ar_utils.py` before any filesystem operation. Never use `os.path.join()` or `pathlib.Path()` with user input without validation.
- **ZIP extraction**: Never use `zipfile.ZipFile.extractall()` without first validating all member paths. Use the safe extraction pattern in `ar_utils.py`.
- **SSRF prevention**: Server-side HTTP requests must validate URLs against allowed domain whitelists. The Power BI publish-check only accepts `*.powerbi.com` HTTPS URLs; AGOL URLs go through `_safe_agol_url()`.
- **Debug mode**: Never hardcode `debug=True`. Use `os.getenv("FLASK_DEBUG", "0") == "1"`.
- **XSS prevention**: In `static/app.js`, always use `escapeHtml()` when inserting server data via `innerHTML`. Prefer `textContent` or DOM construction where possible. Never construct inline `onclick` attributes with dynamic content.
- **Design tokens**: Never use inline hex colors in JavaScript. Use CSS utility classes (`.text-error`, `.text-warning`, `.text-success`, `.bg-error`, etc.) defined in `static/style.css`.
- Reference: `documents/plan-audit-remediation.md` for the full remediation plan.

## Key patterns
- **Error responses**: All backend errors must use `friendly_error(error_code, **kwargs)` from `app.py`. It returns a structured dict with `error_code`, `title`, `message`, and `action` in Spanish (user language). Add new error codes to the `ERROR_MESSAGES` catalog in `app.py`; document them in `documents/03_S3_ERROR_MESSAGES.md`.
- **Protected endpoints**: Sensitive routes (filesystem paths, ArcGIS Pro control, Power BI launch) are listed in `_PROTECTED_PREFIXES` and require an `X-Local-Token` header matching the session token (`_LOCAL_TOKEN`) generated at startup. When adding new sensitive routes, add them to that tuple.
- **C2 multi-shapefile handling**: Component C2 can have multiple SHP ZIPs per summary row; they coexist in one `-Shapes` folder. `_cdg_mapping.json` stores the full child-row list. AbE narrowing happens inside ArcPy, not by writing separate mapping files per attachment. See `docs/LOGICA_MULTI_SHP_C2.md`.
- **Smartsheet response cache**: `app.py` caches Smartsheet API responses in `_SS_CACHE` (keyed by component + sheet_id, TTL 300 s). When adding new Smartsheet reads, use or update this cache rather than making unconditional API calls.

## 문서 생성에는 다음 규칙을 적용한다.
- docs/ 폴더 아래는 파일명과 내용 모두 스페인어로 작성한다. 프로그래머의 요구가 있을 시 복사본을 documents/폴더 아래 파일은 내용은 한국어로 작성하고 '_kr' suffix를 단다.
- 그 외 모든 내용과 파일명은 영어로 작성한다. 사용자-스페인어 사용자(코딩 경험 없음)-를 위한 프린터문, 주석은 스페인어/영어를 병기한다.
- docs/ 는 최종 운영·설치·교육 패키지로 유지하고, documents/ 는 한국어 초안·설계·감사·계획 패키지로 유지한다.
- 운영 문서에서는 Diagnose 를 독립 Paso 0가 아니라 Paso 1-a 로 해석한다. 엔드포인트나 내부 코드 이름이 `paso0` 인 것은 허용된다.
- 실제 화면 캡처 기반 슬라이드형 교육 자료와 최종 Wizard UI 문구 정리는 최종 소프트웨어 목표 달성 후에만 진행한다. 그 전에는 계획, 구현, 운영 루트 문서 정합성을 우선한다.


## Design Principles (Libro de Marca Altiplano Resiliente)

Full spec: `documents/07_DESIGN_PRINCIPLES.md`

### Brand Colors — MUST USE in all UI work
- **AR Green `#70b62c`** (Pantone P 154-8 C): primary action buttons, success states, nature/forest
- **AR Blue `#003f6e`** (Pantone P 108-8 C): headers, sidebar, active states, trust/water
- Sidebar background: `#002d4f` (AR Blue Dark)
- Success: `#70b62c` (AR Green) — NOT `#16a34a`
- Active/Focus: `#003f6e` (AR Blue) — NOT `#1e40af`

### Typography
- Primary: `'Helvetica Neue', Helvetica, Arial, sans-serif`
- Titles: Bold 700, Body: Regular 400

### CSS Custom Properties (use these, not raw hex)
```css
--ar-green: #70b62c;  --ar-blue: #003f6e;
--ar-green-light: #e8f5e0;  --ar-blue-light: #e0ecf5;
--ar-green-dark: #4a8c1a;  --ar-blue-dark: #002d4f;
```

## 병렬 구현 프로세스

대규모 기능 구현 시:

1. **플랜 수립**: `documents/` 에 `plan-*` 파일로 저장 (`.claude/plans/` 사용 금지)
2. **병렬 구현 문서**: `documents/` 에 `plan-*-parallel.md` 생성
   - 의존성 그래프 명시
   - 각 채팅(Chat A/B/C/D...)별 독립 실행 가능한 상세 프롬프트 포함
   - 각 채팅별 파일 범위, 완료 기준 체크리스트
   - 최소 4개 채팅에서 동시 작업 가능하도록 분할
3. **병렬 실행**: 의존성 없는 작업 동시 시작 → 의존성 있는 작업 순차 실행 → 통합