"""
paso1_quarterly.py — Quarterly folder structure creation and shapefile placement.
/ Creación de estructura de carpetas por trimestre y ubicación de shapefiles.

PASO 1 extension: when a work quarter is selected during batch-download,
shapefiles are placed in:
  {base_dir}/{quarter}/{component}/{identifier}/
"""

import os
import pathlib
import re
import shutil
import zipfile
from datetime import date


# ---------------------------------------------------------------------------
# Quarter helpers  /  Utilidades de trimestre
# ---------------------------------------------------------------------------

def current_quarter() -> str:
    """
    Return the current quarter identifier, e.g. "T2026_Q2".
    / Devuelve el identificador del trimestre actual, e.g. "T2026_Q2".
    """
    today = date.today()
    q = (today.month - 1) // 3 + 1  # Q1=1-3, Q2=4-6, Q3=7-9, Q4=10-12
    return f"T{today.year}_Q{q}"


def quarter_options(n_past: int = 2, n_future: int = 1) -> list[dict]:
    """
    Return a list of quarter dicts for use in a <select> dropdown.
    / Devuelve lista de trimestres para usar en un <select> desplegable.

    Each dict: {"value": "T2026_Q2", "label": "2026 T2 (Abr–Jun)"}
    """
    MONTH_RANGES = {
        1: "Ene–Mar",
        2: "Abr–Jun",
        3: "Jul–Sep",
        4: "Oct–Dic",
    }
    today = date.today()
    current_q = (today.month - 1) // 3 + 1
    current_year = today.year

    options = []
    for offset in range(-n_past, n_future + 1):
        year = current_year
        q = current_q + offset
        while q < 1:
            q += 4
            year -= 1
        while q > 4:
            q -= 4
            year += 1
        value = f"T{year}_Q{q}"
        label = f"{year} T{q} ({MONTH_RANGES[q]})"
        options.append({"value": value, "label": label})

    return options


# ---------------------------------------------------------------------------
# Folder structure  /  Estructura de carpetas
# ---------------------------------------------------------------------------

def create_quarterly_structure(base_dir: str, quarter: str, component: str) -> str:
    """
    Create and return the quarterly sub-folder path.
    / Crea y devuelve la ruta de la sub-carpeta trimestral.

    Args:
        base_dir:  Root download directory / Directorio raíz de descarga
                   (e.g. value of DOWNLOAD_DIR in .env)
        quarter:   Quarter identifier / Identificador de trimestre
                   (e.g. "T2026_Q2")
        component: Pipeline component / Componente del pipeline
                   (e.g. "C1", "C2", "C3")

    Returns:
        Absolute path of the created folder / Ruta absoluta de la carpeta creada
        → {base_dir}/{quarter}/{component}/
    """
    if not quarter or not component:
        raise ValueError("quarter and component must be non-empty / quarter y component no pueden estar vacíos")

    # Sanitize inputs / Sanitizar entradas
    safe_quarter = re.sub(r"[^\w\-]", "_", quarter)
    safe_component = re.sub(r"[^\w\-]", "_", component)

    folder = os.path.join(base_dir, safe_quarter, safe_component)
    os.makedirs(folder, exist_ok=True)
    return os.path.abspath(folder)


# ---------------------------------------------------------------------------
# Shapefile placement  /  Colocación de shapefiles
# ---------------------------------------------------------------------------

def place_shapefile(
    zip_path: str,
    dest_folder: str,
    identifier: str,
    component: str,
    abe_value: str = "",
    orig_att_name: str = "",
) -> dict:
    """
    Extract a ZIP into a sub-folder of dest_folder named by identifier,
    then reorganise all shapefiles into a ``-Shapes`` sub-folder with
    standardised names: ``{identifier}-{abe_abbr}_{geom_type}.ext``

    / Extrae un ZIP en una sub-carpeta de dest_folder con el nombre del
    identificador, luego reorganiza todos los shapefiles en una sub-carpeta
    ``-Shapes`` con nombres estandarizados.

    Naming rules / Reglas de nomenclatura:
      C1/C3: identifier = CODIGO (e.g. "241014_C1_ROM_a")
             → {dest_folder}/{codigo}/
      C2:    identifier = "{CONTRATO}_{ORG}_{QUARTER}" (e.g. "AR-PPD-001_ONG_Sur_T2026Q1")
             → {dest_folder}/{contrato_org_qt}/
             (The filename is NOT the CODIGO for C2; the CdgActvdd field is
              determined later via area-matching in PASO 2.)

    Args:
        zip_path:    Full path to the downloaded ZIP / Ruta completa al ZIP descargado
        dest_folder: Target base folder (quarterly/component) / Carpeta base destino
        identifier:  Sub-folder name / Nombre de sub-carpeta
        component:   "C1", "C2", or "C3"
        abe_value:   Full ABE action name from Smartsheet column
                     "ACCIONES DE RESTAURACIÓN AbE" (optional; falls back to
                     reading .dbf if empty)

    Returns:
        {
          "folder": str,        # absolute path of the -Shapes folder (or extract_dir if reorg failed)
          "shp_count": int,     # number of .shp files found
          "files": list[str],   # basenames of all reorganised files
          "component": str,
          "ok": bool,
          "errors": list[str],
        }
    """
    from ar_utils import (
        abe as abe_abbreviation,
        find_shapefiles,
        read_dbf_field_value,
        read_shp_geometry_type,
    )

    safe_id = re.sub(r"[^\w.\-]", "_", identifier.strip())
    extract_dir = os.path.join(dest_folder, safe_id)
    os.makedirs(extract_dir, exist_ok=True)

    result: dict = {
        "folder": os.path.abspath(extract_dir),
        "shp_count": 0,
        "files": [],
        "component": component,
        "ok": False,
        "errors": [],
    }

    # Extract ZIP / Extraer ZIP
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            dest_path = pathlib.Path(extract_dir).resolve()
            for member in zf.infolist():
                member_target = (dest_path / member.filename).resolve()
                if member_target != dest_path and not str(member_target).startswith(str(dest_path) + os.sep):
                    result["errors"].append(f"ZIP member escapes target: {member.filename}")
                    return result
            zf.extractall(extract_dir)
    except (zipfile.BadZipFile, OSError) as exc:
        result["errors"].append(f"ZIP error: {exc}")
        return result

    # Find all .shp files recursively / Buscar archivos .shp recursivamente
    shp_paths = find_shapefiles(extract_dir)
    # Exclude files already in the -Shapes folder (from prior calls
    # for the same identifier, e.g. C2 rows with multiple SHP ZIPs).
    # / Excluir archivos ya en la carpeta -Shapes (de llamadas previas).
    shapes_dir = os.path.join(extract_dir, f"{safe_id}-Shapes")
    shapes_dir_abs = os.path.abspath(shapes_dir) + os.sep
    shp_paths = [p for p in shp_paths
                 if not os.path.abspath(p).startswith(shapes_dir_abs)]
    result["shp_count"] = len(shp_paths)

    if result["shp_count"] == 0:
        result["errors"].append("No .shp file found in ZIP / No se encontró .shp en el ZIP")
        return result

    # -- Reorganise into -Shapes folder / Reorganizar en carpeta -Shapes ------
    shapes_dir = os.path.join(extract_dir, f"{safe_id}-Shapes")
    os.makedirs(shapes_dir, exist_ok=True)

    # Companion extensions to move alongside each .shp
    _SHP_COMPANIONS = (".shp", ".shx", ".dbf", ".prj", ".cpg", ".qmd", ".sbn", ".sbx", ".fbn", ".fbx", ".ain", ".aih", ".atx", ".ixs", ".mxs", ".xml", ".shp.xml")

    renamed_files: list[str] = []

    for shp_path in shp_paths:
        # Detect geometry type / Detectar tipo de geometría
        geom = read_shp_geometry_type(shp_path)

        # Determine ABE abbreviation / Determinar abreviación AbE
        # For C2 with multiple child AbE types, read from .dbf first
        # / Para C2 con múltiples tipos AbE hijos, leer del .dbf primero
        abbr = ""
        dbf_path = os.path.splitext(shp_path)[0] + ".dbf"
        if os.path.isfile(dbf_path):
            raw_abe = read_dbf_field_value(dbf_path, r"ACCIONES|AbE|RESTAUR")
            if raw_abe:
                abbr = abe_abbreviation(raw_abe)
        if not abbr and abe_value:
            abbr = abe_abbreviation(abe_value)
        if not abbr:
            abbr = "unknown"

        # Preserve original stem for uniqueness when multiple ZIPs
        # share the same identifier+abe (prevents overwrites)
        # / Preservar nombre original para evitar sobreescrituras
        orig_stem = os.path.splitext(os.path.basename(shp_path))[0]
        new_base = f"{safe_id}-{abbr}_{geom}"

        # If target already exists in -Shapes, check if it's a duplicate
        # (same file size ⇒ same shapefile re-extracted). Skip duplicates
        # rather than creating a second copy with a longer name.
        # / Si el destino ya existe, comprobar si es un duplicado
        # (mismo tamaño ⇒ mismo shapefile re-extraído). Omitir duplicados.
        existing_shp = os.path.join(shapes_dir, new_base + ".shp")
        if os.path.isfile(existing_shp):
            try:
                existing_size = os.path.getsize(existing_shp)
                new_size = os.path.getsize(shp_path)
            except OSError:
                existing_size, new_size = -1, -2
            if existing_size == new_size:
                # Duplicate — skip this shapefile entirely
                continue
            # Genuinely different data — include original stem for uniqueness
            # Sanitize original stem
            orig_safe = re.sub(r"[^\w.\-]", "_", orig_stem)
            new_base = f"{safe_id}-{abbr}-{orig_safe}_{geom}"

        # Truncate new_base if full path would exceed Windows MAX_PATH (260)
        # Longest companion ext is .shp.xml (8 chars)
        _max_base = 259 - len(shapes_dir) - 1 - 8  # 1 for sep
        if len(new_base) > _max_base > 0:
            new_base = new_base[:_max_base]

        # Move all companion files / Mover archivos asociados
        # On Windows + OneDrive, shutil.move() may fail with PermissionError
        # because the sync agent locks files briefly. Use copy2 + delete as
        # a fallback, with a short retry for the delete.
        # / En Windows + OneDrive, shutil.move() puede fallar con PermissionError
        #   por el bloqueo del agente de sincronización. Usar copy2 + delete
        #   como alternativa, con reintento breve para el delete.
        shp_base = os.path.splitext(shp_path)[0]
        shp_dir = os.path.dirname(shp_path)
        for ext in _SHP_COMPANIONS:
            src = shp_base + ext
            if os.path.isfile(src):
                dst = os.path.join(shapes_dir, new_base + ext)
                try:
                    shutil.move(src, dst)
                except PermissionError:
                    # Fallback: copy then delete with retry
                    shutil.copy2(src, dst)
                    for _attempt in range(3):
                        try:
                            os.remove(src)
                            break
                        except PermissionError:
                            import time as _time
                            _time.sleep(0.3)
                renamed_files.append(os.path.basename(dst))

    # Save original-to-renamed name mapping for ArcPy matching
    # / Guardar mapeo de nombres originales para emparejamiento en ArcPy
    # Merge with existing mapping if present (C2 multi-SHP same folder).
    orig_map = {}
    orig_path = os.path.join(shapes_dir, "_orig_names.json")
    if os.path.isfile(orig_path):
        try:
            import json as _json_load
            with open(orig_path, "r", encoding="utf-8") as ef:
                orig_map = _json_load.load(ef)
        except Exception:
            pass
    for shp_path, new_name in zip(shp_paths, [
        f for f in renamed_files if f.lower().endswith(".shp")
    ]):
        entry = {"orig": os.path.splitext(os.path.basename(shp_path))[0]}
        if orig_att_name:
            entry["zip_name"] = orig_att_name
        orig_map[new_name] = entry
    if orig_map:
        import json as _json_orig
        try:
            with open(orig_path, "w", encoding="utf-8") as of:
                _json_orig.dump(orig_map, of, ensure_ascii=False, indent=2)
        except OSError:
            pass

    result["folder"] = os.path.abspath(shapes_dir)
    result["files"] = renamed_files
    result["ok"] = True
    return result


# ---------------------------------------------------------------------------
# ArcGIS Pro map integration script  /  Script de integración con mapa ArcGIS Pro
# ---------------------------------------------------------------------------

def script_add_shapefiles_to_map(p: dict) -> str:
    """
    Generate an ArcPy script that adds downloaded shapefiles to an ArcGIS Pro
    map inside group layers (point / polygon) for the current quarter.
    / Genera un script ArcPy que agrega shapefiles descargados a un mapa de
    ArcGIS Pro dentro de group layers (punto / polígono) del trimestre actual.

    Expected keys in *p*:
      - aprx:       path to .aprx  (from .env APRX)
      - mapName:    map name       (from .env AR_MAP_NAME)
      - shpFolders: list of absolute folder paths containing extracted .shp files
      - quarter:    e.g. "2025-Q4"
      - component:  "C1", "C2", or "C3"
    """
    import textwrap

    aprx = p.get("aprx", r"C:\\Path\\To\\Project.aprx")
    map_name = p.get("mapName", "AR_EbA_Area")
    shp_folders = p.get("shpFolders", [])
    quarter = p.get("quarter", "T2025_Q4")
    component = p.get("component", "C1")
    lang = p.get("lang", "es")  # "es" or "en"
    if lang not in ("es", "en"):
        lang = "es"

    # Sanitize quarter for group layer name (e.g. "2025-Q4" → "2025_Q4")
    safe_qt = re.sub(r"[^A-Za-z0-9_]", "_", quarter)
    display_qt = re.sub(r"^T(?=\d{4}_Q[1-4]$)", "", safe_qt)

    # Build Python list literal for folders
    # Indent contents to match the 8-space template indentation so
    # textwrap.dedent works correctly.
    folders_literal = "[\n"
    for f in shp_folders:
        folders_literal += f'            r\'{f}\',\n'
    folders_literal += "        ]"

    return textwrap.dedent(f"""\
        # ══════════════════════════════════════════════════════════════════
        # PASO 1b: Add downloaded shapefiles to ArcGIS Pro map
        # ══════════════════════════════════════════════════════════════════
        import arcpy, os, json

        _LANG = "{lang}"  # "es" or "en"
        def _msg(en, es):
            return es if _LANG == "es" else en

        aprx_path = r"{aprx}"
        map_name = "{map_name}"
        component = "{component}"
        quarter = "{safe_qt}"
        quarter_group = "{display_qt}"
        shp_folders = {folders_literal}

        # Group layer names / Nombres de group layers
        group_root = quarter_group
        group_point = f"{{quarter_group}}_point"
        group_polygon = f"{{quarter_group}}_polygon"

        aprx = arcpy.mp.ArcGISProject(aprx_path)
        map_obj = aprx.listMaps(map_name)[0]

        # ── Find or create group layers / Buscar o crear group layers ──
        def get_or_create_group(m, name, parent=None):
            candidates = parent.listLayers() if parent else m.listLayers()
            for lyr in candidates:
                if lyr.isGroupLayer and lyr.name == name:
                    print(f"{{_msg('Group layer found', 'Group layer encontrado')}}: {{name}}")
                    return lyr
            # Create a minimal .lyrx (CIM JSON) for an empty group layer
            # / Crear un .lyrx mínimo (CIM JSON) para un group layer vacío
            import json as _json, tempfile
            lyrx_path = os.path.join(tempfile.gettempdir(), f"{{name}}.lyrx")
            lyrx_content = {{
                "type": "CIMLayerDocument",
                "version": "3.0.0",
                "layers": [f"CIMPATH=map/{{name}}.json"],
                "layerDefinitions": [{{
                    "type": "CIMGroupLayer",
                    "name": name,
                    "uRI": f"CIMPATH=map/{{name}}.json",
                    "layers": [],
                    "visibility": True,
                    "expanded": True
                }}]
            }}
            with open(lyrx_path, "w", encoding="utf-8") as _f:
                _json.dump(lyrx_content, _f)
            lyr_file = arcpy.mp.LayerFile(lyrx_path)
            if parent:
                m.addLayerToGroup(parent, lyr_file, "TOP")
            else:
                m.addLayer(lyr_file, "TOP")
            candidates = parent.listLayers() if parent else m.listLayers()
            for lyr in candidates:
                if lyr.isGroupLayer and lyr.name == name:
                    print(f"{{_msg('Group layer created', 'Group layer creado')}}: {{name}}")
                    return lyr
            if not parent:
                # Last resort: return first group layer at top
                gl = m.listLayers()[0]
                gl.name = name
                print(f"{{_msg('Group layer created (renamed)', 'Group layer creado (renombrado)')}}: {{name}}")
                return gl
            raise RuntimeError(f"{{_msg('Could not create subgroup', 'No se pudo crear el subgrupo')}}: {{name}}")

        grp_root = get_or_create_group(map_obj, group_root)
        grp_point = get_or_create_group(map_obj, group_point, grp_root)
        grp_polygon = get_or_create_group(map_obj, group_polygon, grp_root)

        # ── Remove stale schema locks / Eliminar bloqueos de esquema obsoletos ──
        def _clear_schema_locks(shp_path):
            \"\"\"Delete .srlk files that ArcGIS Pro leaves behind.\"\"\"
            import glob as _glob
            base = os.path.splitext(shp_path)[0]
            for lock_file in _glob.glob(base + "*.srlk"):
                try:
                    os.remove(lock_file)
                except OSError:
                    pass

        # ── Add CdgActvdd field / Agregar campo CdgActvdd ──
        def add_cdg_field(shp_path, cdg_value):
            _clear_schema_locks(shp_path)
            field_name = "CdgActvdd"
            existing = [f.name for f in arcpy.ListFields(shp_path)]
            if field_name not in existing:
                arcpy.AddField_management(shp_path, field_name, "TEXT", field_length=254)
            arcpy.CalculateField_management(shp_path, field_name, f"'{{cdg_value}}'", "PYTHON3")

            # Ensure UTF-8 codepage / Asegurar codepage UTF-8
            cpg_path = shp_path.replace(".shp", ".cpg")
            try:
                with open(cpg_path, "w", encoding="utf-8") as f:
                    f.write("UTF-8")
            except Exception:
                pass

        def _load_cdg_mapping(folder):
            \"\"\"Load C2 child-row mapping JSON if present.

            Returns (children_list, meta_dict) tuple.
            Supports both old format (plain list) and new format (dict with _meta).
            / Carga el mapeo JSON de filas hijas C2. Soporta formato antiguo (lista)
            y nuevo (dict con _meta).
            \"\"\"
            mp = os.path.join(folder, "_cdg_mapping.json")
            if os.path.isfile(mp):
                try:
                    with open(mp, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if isinstance(data, dict) and "children" in data:
                        return data["children"], data.get("_meta", {{}})
                    # Old format: plain list of children
                    return data, {{}}
                except Exception:
                    pass
            return None, {{}}

        def _shp_total_hectares(shp_path):
            \"\"\"Sum geometry area (hectares) of all features in shapefile.\"\"\"
            try:
                total = 0.0
                with arcpy.da.SearchCursor(shp_path, ["SHAPE@AREA"]) as cur:
                    for row in cur:
                        total += (row[0] or 0.0)
                # Area is in CRS units; assume projected meters -> convert to ha
                # / El area esta en unidades CRS; asumir metros proyectados -> convertir a ha
                return total / 10000.0
            except Exception:
                return 0.0

        def _extract_abe_from_fname(fname, orig_info=None):
            \"\"\"Extract AbE abbreviation from shapefile name.
            orig_info: optional dict from _orig_names (new format).
            If renamed name does not yield a known abbreviation, try zip_name.
            \"\"\"
            _KNOWN_ABE = {{
                "sueloyagua", "aguaysuelo", "anual", "peren", "silvo",
                "plant", "produ", "prote", "refor", "saf",
            }}
            base = os.path.splitext(fname)[0]
            parts = base.rsplit("_", 1)
            abe = ""
            if len(parts) >= 2:
                prefix = parts[0]
                abe = prefix.rsplit("-", 1)[-1] if "-" in prefix else ""
            # If we got a known abbreviation, return it
            if abe and abe.lower() in _KNOWN_ABE:
                return abe
            # Try extracting from the original ZIP name
            if orig_info and isinstance(orig_info, dict):
                zn = orig_info.get("zip_name", "").lower()
                if zn:
                    import re as _abe_re
                    # Known AbE prefixes in ZIP filenames
                    _ZIP_ABE = [
                        ("bnprotec", "prote"), ("bnproduc", "produ"),
                        ("refor", "refor"), ("silvo", "silvo"),
                        ("sueloyagua", "sueloyagua"), ("aguaysuelo", "sueloyagua"),
                        ("saf", "saf"),  # generic SAF
                    ]
                    for prefix, hint in _ZIP_ABE:
                        if prefix in zn:
                            return hint
            return abe or ""

        def _extract_date_from_fname(fname):
            \"\"\"
            Extract date hint from original filename (e.g. '251203' → '2025-12-03').
            Many original names embed YYMMDD at the start.
            / Extraer fecha del nombre original del archivo.
            \"\"\"
            import re as _re
            base = os.path.splitext(fname)[0]
            # Pattern: 6-digit date YYMMDD at start of name or after underscore
            m = _re.search(r'(?:^|[_\\-])(\\d{{6}})(?:[_\\-]|$)', base)
            if m:
                d = m.group(1)
                yy, mm, dd = d[:2], d[2:4], d[4:6]
                yr = int(yy) + 2000
                return f"{{yr}}-{{mm}}-{{dd}}"
            return ""

        def _load_orig_names(folder):
            \"\"\"Load original-name mapping JSON if present.
            Returns dict: renamed_shp_name → {{"orig": original_stem, "zip_name": ...}}.
            Handles both old format (string value) and new format (dict value).
            / Cargar mapeo de nombres originales si existe.
            \"\"\"
            mp = os.path.join(folder, "_orig_names.json")
            if os.path.isfile(mp):
                try:
                    with open(mp, "r", encoding="utf-8") as f:
                        raw = json.load(f)
                    # Normalise old format (string) to new format (dict)
                    result = {{}}
                    for k, v in raw.items():
                        if isinstance(v, str):
                            result[k] = {{"orig": v}}
                        else:
                            result[k] = v
                    return result
                except Exception:
                    pass
            return {{}}

        def _read_shp_locations(shp_path):
            \"\"\"
            Read unique location names (municipio/comunidad) from shapefile.
            Returns set of lowercase location strings.
            / Leer nombres de ubicación únicos del shapefile.
            \"\"\"
            locations = set()
            try:
                fields = [f.name for f in arcpy.ListFields(shp_path)]
                loc_fields = [f for f in fields
                              if any(k in f.upper() for k in
                                     ("MUNI", "COMUNIDAD", "LOCALIDAD",
                                      "LUGAR", "ALDEA", "MICRO"))]
                if loc_fields:
                    with arcpy.da.SearchCursor(shp_path, loc_fields) as cur:
                        for row in cur:
                            for val in row:
                                if val and str(val).strip():
                                    locations.add(str(val).strip().lower())
            except Exception:
                pass
            return locations

        def _read_shp_dates(shp_path):
            \"\"\"
            Read unique date values from shapefile FECHA field.
            Returns set of date strings 'YYYY-MM-DD'.
            / Leer valores únicos de fecha del campo FECHA del shapefile.
            \"\"\"
            dates = set()
            try:
                fields = [f.name for f in arcpy.ListFields(shp_path)]
                date_fields = [f for f in fields
                               if "FECHA" in f.upper() or "DATE" in f.upper()]
                if date_fields:
                    with arcpy.da.SearchCursor(shp_path, date_fields) as cur:
                        for row in cur:
                            for val in row:
                                if val:
                                    # val may be datetime or string
                                    s = str(val)[:10]
                                    if len(s) >= 10:
                                        dates.add(s)
            except Exception:
                pass
            return dates

        def _score_mapping(mapping, abe_part, shp_ha, shp_path=None, orig_name="", ha_hint=None):
            \"\"\"
            3-tier matching: AbE filter → date/location → hectares.
            1. Filter children by AbE match (required)
            2. Among matches: try date matching (from original filename or .dbf)
            3. If no date match: try location matching (shapefile vs SS nombre)
            4. Fallback: hectares ratio per individual child row
            If only ONE child has AbE + hectares, return it directly.
            ha_hint: hectares value extracted from original ZIP filename
                     (e.g. 23.6 from 'SAF_23.60 ha.zip') — used as additional
                     evidence for matching when shapefile actual ha is unavailable.
            / Emparejamiento en 3 niveles: filtro AbE → fecha/ubicación → hectáreas.
            ha_hint: hectáreas del nombre de archivo ZIP original — evidencia adicional.
            \"\"\"
            if not mapping:
                return None

            # ── Step 1: Filter children by AbE match ──
            # SAF / saf is a generic prefix for all "Sistema Agroforestal" types
            # (anual, peren, sueloyagua).  Treat it as a broad matcher.
            # / SAF es un prefijo genérico para todos los tipos "Sistema Agroforestal".
            abe_matches = []
            for child in mapping:
                child_code = child.get("code", "")
                child_abe = child.get("value", "")
                if not child_code:
                    continue
                if abe_part and child_abe:
                    abe_lower = abe_part.lower()
                    child_abe_lower = child_abe.lower()
                    # SAF/saf matches any "sistema agroforestal" subtype
                    if abe_lower == "saf" and "sistema agroforestal" in child_abe_lower:
                        abe_matches.append(child)
                    elif (abe_lower in child_abe_lower
                            or child_abe_lower.startswith(abe_lower[:3])):
                        abe_matches.append(child)

            if not abe_matches:
                # No AbE match — fall back to group-level ha matching
                # Sum all children ha with same AbE for group match
                abe_groups = {{}}
                for child in mapping:
                    child_code = child.get("code", "")
                    child_abe = child.get("value", "")
                    if not child_code:
                        continue
                    gk = child_abe.strip().lower() if child_abe else "none"
                    if gk not in abe_groups:
                        abe_groups[gk] = {{"codes": [], "total_ha": 0.0, "abe": child_abe}}
                    abe_groups[gk]["codes"].append(child_code)
                    abe_groups[gk]["total_ha"] += float(child.get("hectares", 0))
                best = None
                best_r = 0
                for gk, grp in abe_groups.items():
                    if grp["total_ha"] > 0 and shp_ha > 0:
                        r = min(shp_ha, grp["total_ha"]) / max(shp_ha, grp["total_ha"])
                        if r > best_r:
                            best_r = r
                            best = grp["codes"][0]
                return best if best_r >= 0.7 else None

            # Only ONE child with this AbE — return directly
            if len(abe_matches) == 1:
                return abe_matches[0]["code"]

            # ── Step 2: Date matching ──
            # Try original filename date hint first, then shapefile .dbf dates
            fname_date = _extract_date_from_fname(orig_name) if orig_name else ""
            shp_dates = set()
            if shp_path:
                shp_dates = _read_shp_dates(shp_path)

            all_dates = set()
            if fname_date:
                all_dates.add(fname_date)
            all_dates.update(shp_dates)

            if all_dates:
                for child in abe_matches:
                    child_fecha = child.get("fecha", "")[:10]
                    if child_fecha and child_fecha in all_dates:
                        print(f"    {{_msg('Date match', 'Coincidencia de fecha')}}: "
                              f"{{child_fecha}} -> {{child.get('code')}}")
                        return child["code"]

            # ── Step 3: Location matching ──
            if shp_path:
                shp_locs = _read_shp_locations(shp_path)
                if shp_locs:
                    best_loc_child = None
                    best_loc_score = 0
                    for child in abe_matches:
                        nombre = child.get("nombre", "").lower()
                        if not nombre:
                            continue
                        # Check if any shapefile location word appears in activity name
                        loc_score = 0
                        for loc in shp_locs:
                            # Split location into words for partial matching
                            for word in loc.split():
                                if len(word) >= 3 and word in nombre:
                                    loc_score += 1
                        if loc_score > best_loc_score:
                            best_loc_score = loc_score
                            best_loc_child = child
                    if best_loc_child and best_loc_score > 0:
                        print(f"    {{_msg('Location match', 'Coincidencia de ubicación')}}: "
                              f"{{best_loc_child.get('code')}}")
                        return best_loc_child["code"]

            # ── Step 4: Hectares per-child matching (fallback) ──
            # Use shapefile actual ha; if unavailable, fall back to ha_hint
            # from original ZIP filename as evidence.
            # / Usar ha real del shapefile; si no disponible, usar ha_hint
            # del nombre del archivo ZIP como evidencia.
            effective_ha = shp_ha if shp_ha > 0 else (ha_hint or 0)
            best_child = None
            best_ratio = 0
            for child in abe_matches:
                child_ha = float(child.get("hectares", 0))
                if child_ha > 0 and effective_ha > 0:
                    ratio = min(effective_ha, child_ha) / max(effective_ha, child_ha)
                    if ratio > best_ratio:
                        best_ratio = ratio
                        best_child = child

            # If ha_hint is available and shapefile ha also matches, boost confidence
            if best_child and ha_hint and ha_hint > 0 and shp_ha > 0:
                ha_hint_ratio = min(ha_hint, float(best_child.get("hectares", 0))) / max(ha_hint, float(best_child.get("hectares", 0))) if float(best_child.get("hectares", 0)) > 0 else 0
                if ha_hint_ratio >= 0.8:
                    # Both filename ha and shapefile ha agree — strong evidence
                    print(f"    {{_msg('Hectares match (filename+shp confirmed)', 'Coincidencia ha (archivo+shp confirmado)')}}: "
                          f"{{best_child.get('code')}} (ratio={{best_ratio:.2f}}, "
                          f"filename_ha={{ha_hint}})")
                    return best_child["code"]

            if best_child and best_ratio >= 0.5:
                src = "filename_ha" if shp_ha <= 0 and ha_hint else "shp_ha"
                print(f"    {{_msg('Hectares match', 'Coincidencia de hectáreas')}}: "
                      f"{{best_child.get('code')}} (ratio={{best_ratio:.2f}}, src={{src}})")
                return best_child["code"]

            # ── Last resort: sum of AbE group ha vs effective ha ──
            group_ha = sum(float(c.get("hectares", 0)) for c in abe_matches)
            if group_ha > 0 and effective_ha > 0:
                ratio = min(effective_ha, group_ha) / max(effective_ha, group_ha)
                if ratio >= 0.7:
                    return abe_matches[0]["code"]

            # Return first AbE match code if AbE matched
            return abe_matches[0]["code"]

        def _match_cdg_from_mapping(mapping, shp_path, fname, orig_name="", ha_hint=None, orig_info=None):
            \"\"\"
            Match a shapefile to a C2 child row using 3-tier matching:
            AbE → date/location → hectares.
            Returns CODIGO if matched, else None.
            ha_hint: hectares from original ZIP filename (additional evidence).
            orig_info: dict from _orig_names (new format) with zip_name etc.
            / Emparejar un shapefile con una fila hija C2 usando emparejamiento en 3 niveles.
            \"\"\"
            if not mapping:
                return None
            abe_part = _extract_abe_from_fname(fname, orig_info=orig_info)
            shp_ha = _shp_total_hectares(shp_path)
            return _score_mapping(mapping, abe_part, shp_ha,
                                  shp_path=shp_path, orig_name=orig_name,
                                  ha_hint=ha_hint)

        def _match_paired_shapefiles(mapping, fname_paths, unmatched_fnames, orig_names_map=None):
            \"\"\"
            For C2 shapefiles that couldn't be matched individually,
            pair polygon+point by base name and sum their hectares.
            If the pair's combined ha matches a child row, assign both.
            Also: if only ONE child row has hectares, assign all unmatched to it.
            fname_paths: dict mapping fname → absolute path.
            orig_names_map: dict from _load_orig_names (for zip_name extraction).
            / Para shapefiles C2 sin coincidencia individual, emparejar
            polygon+point por nombre base y sumar sus hectáreas.
            \"\"\"
            if not mapping or not unmatched_fnames:
                return {{}}

            # Group unmatched files by base name (strip geometry suffix)
            pairs = {{}}  # base_name → {{geom_type: fname}}
            ungrouped = []
            for fname in unmatched_fnames:
                base = os.path.splitext(fname)[0]
                lower = base.lower()
                grouped = False
                for suffix in ("_polygon", "_point", "_polyline"):
                    if lower.endswith(suffix):
                        base_key = base[:len(base) - len(suffix)]
                        geom = suffix[1:]
                        pairs.setdefault(base_key, {{}})[geom] = fname
                        grouped = True
                        break
                if not grouped:
                    ungrouped.append(fname)

            results = {{}}  # fname → cdg_value

            for base_key, geom_files in pairs.items():
                if len(geom_files) < 2:
                    continue

                # Sum hectares across all geometry files in this pair
                total_ha = 0.0
                for geom, fn in geom_files.items():
                    sp = fname_paths.get(fn, fn)
                    total_ha += _shp_total_hectares(sp)

                if total_ha <= 0:
                    continue

                abe_part = _extract_abe_from_fname(
                    list(geom_files.values())[0],
                    orig_info=(orig_names_map or {{}}).get(list(geom_files.values())[0])
                )
                matched = _score_mapping(mapping, abe_part, total_ha)
                if matched:
                    for fn in geom_files.values():
                        results[fn] = matched
                    print(f"  CdgActvdd {{_msg('paired match', 'emparejado combinado')}}: "
                          f"{{list(geom_files.values())}} -> {{matched}} "
                          f"(combined ha={{total_ha:.2f}})")

            # Last resort: if only ONE child row has hectares, assign
            # all still-unmatched to that sole row
            still_unmatched = [f for f in unmatched_fnames if f not in results]
            if still_unmatched:
                ha_children = [c for c in mapping
                               if float(c.get("hectares", 0)) > 0 and c.get("code")]
                if len(ha_children) == 1:
                    sole_code = ha_children[0]["code"]
                    for fn in still_unmatched:
                        results[fn] = sole_code
                    print(f"  CdgActvdd {{_msg('sole-row match', 'única fila con ha')}}: "
                          f"{{still_unmatched}} -> {{sole_code}}")

            return results

        # ── Process each folder / Procesar cada carpeta ──
        added_count = 0
        for folder in shp_folders:
            if not os.path.isdir(folder):
                print(f"{{_msg('Folder not found', 'Carpeta no encontrada')}}: {{folder}}")
                continue

            # ── Clean up empty subfolders left after file moves ──
            # EN: After place_shapefile() moves .shp files to the -Shapes
            #     subfolder, the original ZIP extraction folders remain empty.
            #     Remove them so only actual data folders remain.
            # ES: Después de mover archivos .shp a la subcarpeta -Shapes,
            #     las carpetas originales de extracción quedan vacías. Eliminarlas.
            for sub in os.listdir(folder):
                sub_path = os.path.join(folder, sub)
                if not os.path.isdir(sub_path):
                    continue
                # Check if folder is empty (no .shp files anywhere inside)
                has_shp = False
                for _root, _dirs, _files in os.walk(sub_path):
                    if any(f.lower().endswith(".shp") for f in _files):
                        has_shp = True
                        break
                if not has_shp:
                    import shutil
                    shutil.rmtree(sub_path, ignore_errors=True)
                    print(f"  {{_msg('Removed empty folder', 'Carpeta vacía eliminada')}}: {{sub}}")

            # Load C2 child-row mapping if present / Cargar mapeo C2 si existe
            cdg_mapping, cdg_meta = _load_cdg_mapping(folder)

            # Load original filename mapping if present / Cargar mapeo de nombres originales
            orig_names = _load_orig_names(folder)

            # Default CdgActvdd from folder name / CdgActvdd por defecto del nombre de carpeta
            default_cdg = os.path.basename(folder)
            # Strip "-Shapes" suffix if present / Quitar sufijo "-Shapes" si existe
            if default_cdg.endswith("-Shapes"):
                default_cdg = default_cdg[:-7]

            # ── Collect all .shp files recursively from folder + subfolders ──
            # EN: Shapefiles may be in the root folder or in subfolders like
            #     -Shapes/. Walk the tree to find them all.
            # ES: Los shapefiles pueden estar en la carpeta raíz o en
            #     subcarpetas como -Shapes/. Recorrer el árbol para encontrarlos.
            shp_files = []  # list of (relative_path, abs_path)
            for _walk_root, _walk_dirs, _walk_files in os.walk(folder):
                for fname in _walk_files:
                    if fname.lower().endswith(".shp"):
                        abs_path = os.path.join(_walk_root, fname)
                        shp_files.append((fname, abs_path))

            if not shp_files:
                print(f"  {{_msg('No shapefiles found in', 'No se encontraron shapefiles en')}} {{folder}}")
                continue

            # ── Deduplicate: remove long-named duplicates left by older runs.
            # Short name pattern: ID-abe_geom.shp
            # Long (dup) pattern: ID-abe-origStem_geom.shp  — same data
            # If both exist with the same file size, delete the long one on disk
            # so it never reaches ArcGIS Pro.
            _GEOM_SFX = ("_point", "_polygon", "_polyline", "_multipoint")
            _short_map = {{}}  # (prefix_lower, geom_lower) → (fname, size)
            for fname, abs_path in shp_files:
                stem = fname[:-4] if fname.lower().endswith(".shp") else fname
                geom_hit = None
                for gs in _GEOM_SFX:
                    if stem.lower().endswith(gs):
                        geom_hit = gs[1:]
                        prefix = stem[:len(stem) - len(gs)]
                        break
                if geom_hit is None:
                    continue
                key = (prefix.lower(), geom_hit)
                sz = os.path.getsize(abs_path)
                if key not in _short_map or len(prefix) < len(_short_map[key][0]):
                    _short_map[key] = (prefix, fname, sz)

            _dupes = set()
            for fname, abs_path in shp_files:
                stem = fname[:-4] if fname.lower().endswith(".shp") else fname
                for gs in _GEOM_SFX:
                    if stem.lower().endswith(gs):
                        prefix = stem[:len(stem) - len(gs)]
                        geom_hit = gs[1:]
                        break
                else:
                    continue
                key = (prefix.lower(), geom_hit)
                if key not in _short_map or _short_map[key][1] == fname:
                    continue
                # This file is longer-named; check if it shares a prefix with a shorter one
                short_pfx = _short_map[key][0]
                if prefix.startswith(short_pfx + "-") and os.path.getsize(abs_path) == _short_map[key][2]:
                    _dupes.add(fname)
                    # Delete duplicate companion files from disk
                    base_no_ext = abs_path[:-4]
                    _COMP_EXT = (".shp",".shx",".dbf",".prj",".cpg",".qmd",
                                 ".sbn",".sbx",".xml",".shp.xml")
                    for ce in _COMP_EXT:
                        cf = base_no_ext + ce
                        if os.path.isfile(cf):
                            os.remove(cf)
                    print(f"  {{_msg('Removed duplicate', 'Duplicado eliminado')}}: {{fname}}")

            if _dupes:
                shp_files = [(f, p) for f, p in shp_files if f not in _dupes]

            print(f"  {{_msg('Found', 'Encontrados')}} {{len(shp_files)}} shapefiles {{_msg('in', 'en')}} {{os.path.basename(folder)}}")

            # First pass: try individual matching, collect unmatched
            matched_map = {{}}  # fname → cdg_value
            unmatched = []
            unmatched_paths = {{}}  # fname → abs_path

            # ha_hint from original ZIP filename — additional evidence for matching
            # Per-file: extract from _orig_names zip_name for each shapefile.
            # Fallback: _meta ha_hint (last-downloaded ZIP).
            meta_ha_hint = cdg_meta.get("ha_hint") if cdg_meta else None

            def _per_file_ha(fname):
                \"\"\"Extract ha_hint for *this* shapefile from its original ZIP name.\"\"\"
                import re as _re2
                info = orig_names.get(fname)
                if info and isinstance(info, dict):
                    zn = info.get("zip_name", "")
                    if zn:
                        m = _re2.search(r'(\\d+[.,]\\d+)\\s*ha\\b', zn, _re2.IGNORECASE)
                        if m:
                            return float(m.group(1).replace(",", "."))
                # Fallback to meta-level ha_hint (single value for folder)
                return meta_ha_hint

            for fname, abs_path in shp_files:
                if cdg_mapping:
                    info = orig_names.get(fname)
                    if isinstance(info, dict):
                        orig_name = info.get("orig", fname)
                    else:
                        orig_name = info if info else fname
                    file_ha_hint = _per_file_ha(fname)
                    matched = _match_cdg_from_mapping(cdg_mapping, abs_path, fname,
                                                      orig_name=orig_name,
                                                      ha_hint=file_ha_hint,
                                                      orig_info=info)
                    if matched:
                        matched_map[fname] = matched
                        print(f"  CdgActvdd {{_msg('matched', 'emparejado')}}: {{fname}} -> {{matched}}")
                    else:
                        unmatched.append(fname)
                        unmatched_paths[fname] = abs_path
                else:
                    matched_map[fname] = default_cdg

            # Second pass: try paired matching for unmatched shapefiles
            if unmatched and cdg_mapping:
                # Use the paths dict for paired matching
                paired = _match_paired_shapefiles(cdg_mapping, unmatched_paths, unmatched,
                                                    orig_names_map=orig_names)
                # If paired matching used folder root, also try with actual paths
                if not paired:
                    # Try with individual file paths for pairs across subfolders
                    paired = {{}}
                    pair_groups = {{}}
                    for fname in unmatched:
                        base = os.path.splitext(fname)[0].lower()
                        for suffix in ("_polygon", "_point", "_polyline"):
                            if base.endswith(suffix):
                                base_key = base[:len(base) - len(suffix)]
                                pair_groups.setdefault(base_key, []).append(fname)
                                break
                    for base_key, fnames in pair_groups.items():
                        if len(fnames) >= 2:
                            total_ha = sum(_shp_total_hectares(unmatched_paths[f])
                                           for f in fnames)
                            if total_ha > 0:
                                abe_part = _extract_abe_from_fname(
                                    fnames[0],
                                    orig_info=(orig_names or {{}}).get(fnames[0])
                                )
                                m = _score_mapping(cdg_mapping, abe_part, total_ha)
                                if m:
                                    for f in fnames:
                                        paired[f] = m
                                    print(f"  CdgActvdd cross-folder paired: {{fnames}} -> {{m}} (ha={{total_ha:.2f}})")

                matched_map.update(paired)

                # Last resort for still-unmatched
                still_unmatched = [f for f in unmatched if f not in matched_map]
                if still_unmatched:
                    ha_children = [c for c in cdg_mapping
                                   if float(c.get("hectares", 0)) > 0 and c.get("code")]
                    if len(ha_children) == 1:
                        sole_code = ha_children[0]["code"]
                        for fname in still_unmatched:
                            matched_map[fname] = sole_code
                        print(f"  CdgActvdd sole-row match: {{still_unmatched}} -> {{sole_code}}")
                    else:
                        # Use filename (without extension) as CdgActvdd so user
                        # can identify the file during manual review.
                        # / Usar nombre de archivo (sin extensión) como CdgActvdd
                        # para que el usuario pueda identificar el archivo en revisión.
                        no_match_files = []
                        for fname in still_unmatched:
                            fallback_cdg = os.path.splitext(fname)[0]
                            matched_map[fname] = fallback_cdg
                            no_match_files.append(fname)
                        # Emit prominent warning / Emitir advertencia prominente
                        ss_link = cdg_meta.get("permalink", "")
                        if not ss_link:
                            sheet_id = cdg_meta.get("sheet_id", "")
                            if sheet_id:
                                ss_link = f"https://app.smartsheet.com/sheets/{{sheet_id}}"
                        summary_row = cdg_meta.get("summary_row", "")
                        print("")
                        print("=" * 70)
                        print(f"  [!] {{_msg('REVIEW NEEDED', 'REVISION NECESARIA')}}")
                        print(f"  {{len(no_match_files)}} {{_msg('shapefile(s) with no CdgActvdd match', 'shapefile(s) sin coincidencia de CdgActvdd')}}:")
                        for nf in no_match_files:
                            print(f"    - {{nf}} -> {{os.path.splitext(nf)[0]}}")
                        print(f"  {{_msg('Folder', 'Carpeta')}}: {{os.path.basename(folder)}}")
                        if ss_link:
                            print(f"  Smartsheet: {{ss_link}}")
                        if summary_row:
                            print(f"  SummaryRow: {{summary_row}}")
                        print(f"  {{_msg('Action: Verify CdgActvdd in ArcGIS Pro and correct manually.', 'Acción: Verificar CdgActvdd en ArcGIS Pro y corregir manualmente.')}}")
                        print("=" * 70)
                        print("")

            # Pass 1: Write CdgActvdd to all shapefiles BEFORE adding to map.
            # addDataFromPath acquires schema locks, so CalculateField must
            # run first while no locks are held.
            # / Paso 1: Escribir CdgActvdd en todos los shapefiles ANTES de
            # agregarlos al mapa. addDataFromPath adquiere bloqueos de esquema.
            for fname, abs_path in shp_files:
                cdg_value = matched_map.get(fname, default_cdg)
                try:
                    add_cdg_field(abs_path, cdg_value)
                    print(f"  CdgActvdd {{_msg('matched', 'emparejado')}}: {{fname}} -> {{cdg_value}}")
                except Exception as e:
                    print(f"  {{_msg('Error adding CdgActvdd to', 'Error al agregar CdgActvdd a')}} {{fname}}: {{e}}")

            # Pass 2: Add shapefiles to map group layers (skip duplicates).
            # / Paso 2: Agregar shapefiles a los group layers (omitir duplicados).
            # Build set of data sources already in each group / Construir set de fuentes ya en cada grupo
            def _existing_sources(grp):
                sources = set()
                try:
                    for lyr in grp.listLayers():
                        if not lyr.isGroupLayer and hasattr(lyr, "dataSource"):
                            sources.add(os.path.normcase(os.path.normpath(lyr.dataSource)))
                except Exception:
                    pass
                return sources

            existing_point = _existing_sources(grp_point)
            existing_polygon = _existing_sources(grp_polygon)

            for fname, abs_path in shp_files:
                desc = arcpy.Describe(abs_path)
                geom_type = desc.shapeType  # Point, Polyline, Polygon, MultiPoint, etc.

                if geom_type in ("Point", "MultiPoint"):
                    target_group = grp_point
                    existing = existing_point
                else:
                    target_group = grp_polygon
                    existing = existing_polygon

                # Skip if already in group / Omitir si ya está en el grupo
                norm_path = os.path.normcase(os.path.normpath(abs_path))
                if norm_path in existing:
                    print(f"  {{_msg('Already in map, skipping', 'Ya en mapa, omitiendo')}}: {{fname}}")
                    continue

                try:
                    feature_layer = map_obj.addDataFromPath(abs_path)
                except Exception as _add_err:
                    print(f"  addDataFromPath {{_msg('failed', 'falló')}}: {{fname}}: {{_add_err}}")
                    print(f"  {{_msg('Skipping map add for', 'Omitiendo agregar al mapa')}}: {{fname}}")
                    continue

                try:
                    map_obj.addLayerToGroup(target_group, feature_layer)
                    map_obj.removeLayer(feature_layer)  # remove from root / eliminar de raíz
                except Exception as _grp_err:
                    print(f"  {{_msg('Error moving to group', 'Error al mover al grupo')}}: {{fname}}: {{_grp_err}}")

                added_count += 1
                print(f"  {{_msg('Added', 'Agregado')}}: {{fname}} -> {{target_group.name}} ({{geom_type}})")

        # ── Save project / Guardar proyecto ──
        # ArcGIS Pro should already be closed by the dashboard before this runs.
        # / ArcGIS Pro ya deberia estar cerrado por el dashboard antes de ejecutar esto.
        import time as _time
        _save_ok = False
        for _attempt in range(3):
            try:
                aprx.save()
                _save_ok = True
                break
            except OSError as _se:
                _att_n = _attempt + 1
                print(f"{{_msg(f'Save attempt {{_att_n}} failed', f'Intento de guardado {{_att_n}} falló')}}: {{_se}}")
                # Delete stale .srlk lock on the .aprx itself
                _aprx_lock = aprx_path.replace(".aprx", ".srlk")
                if os.path.isfile(_aprx_lock):
                    try:
                        os.remove(_aprx_lock)
                        print(f"{{_msg('Removed lock file', 'Eliminado archivo de bloqueo')}}: {{_aprx_lock}}")
                    except OSError:
                        pass
                _time.sleep(2)
        del aprx
        if _save_ok:
            print(f"\\n{{_msg('Project saved', 'Proyecto guardado')}}: {{aprx_path}}")
        else:
            print(f"\\n{{_msg('WARNING: Could not save project (layers were added but project not saved).', 'ADVERTENCIA: No se pudo guardar el proyecto (las capas se agregaron pero el proyecto no se guardó).')}}")
            print(f"{{_msg('Please open ArcGIS Pro and save manually.', 'Abra ArcGIS Pro y guarde manualmente.')}}")

        print(f"\\n== {{_msg('Done', 'Listo')}}: {{added_count}} {{_msg('shapefiles added to map', 'shapefiles agregados al mapa')}} '{{map_name}}'. ==")
    """)
