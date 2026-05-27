"""
paso1_excel_to_point.py — Convert area Excel workbooks into ArcGIS Pro point
feature classes.  Fallback used by the Paso 1 agent when a Smartsheet row has
no shapefile ZIP attachment but does have an Excel ``Área (ha)`` workbook.

/ Convierte hojas Excel de áreas en feature classes de puntos para ArcGIS Pro.
Se usa como respaldo en el agente Paso 1 cuando una fila de Smartsheet no
tiene shapefile adjunto pero sí un Excel con columnas X/Y/Área/Beneficiario.

Original logic lives in
``01_Ssheet_DataCollect/1_2_Optional_excel_to_point.ipynb`` and is mirrored
here so the dashboard can invoke it without modifying the notebook.
"""
from __future__ import annotations

import os
import re
import textwrap


COORD_SYSTEM_GTM = (
    'PROJCS["GTM",GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",'
    'SPHEROID["WGS_1984",6378137.0,298.257223563]],'
    'PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],'
    'PROJECTION["Transverse_Mercator"],PARAMETER["False_Easting",500000.0],'
    'PARAMETER["False_Northing",0.0],PARAMETER["Central_Meridian",-90.5],'
    'PARAMETER["Scale_Factor",0.9998],PARAMETER["Latitude_Of_Origin",0.0],'
    'UNIT["Meter",1.0]]'
)


def find_area_excel(folder: str) -> str | None:
    """Return the absolute path of the first ``área`` Excel found in folder.

    Looks for ``.xls`` / ``.xlsx`` whose lowercase name contains any of the
    area/hectare keywords used in the consultant's notebook.
    Returns ``None`` if no candidate is found.

    / Devuelve la ruta del primer Excel de áreas encontrado en la carpeta.
    """
    if not folder or not os.path.isdir(folder):
        return None
    keywords = ("área", "area", "areas", "áreas", "hectares", "_ha",
                "_has_", "_reas_", "puntos")
    candidates: list[str] = []
    for name in os.listdir(folder):
        lower = name.lower()
        if not (lower.endswith(".xls") or lower.endswith(".xlsx")):
            continue
        if any(k in lower for k in keywords):
            candidates.append(os.path.join(folder, name))
    if not candidates:
        return None
    candidates.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return candidates[0]


def _dms_to_dd(dms: str) -> float | None:
    """Convert a DMS coordinate string to decimal degrees.

    Replicates ``dms_to_dd`` from
    ``01_Ssheet_DataCollect/1_2_Optional_excel_to_point.ipynb``.
    Returns ``None`` if parsing fails.
    """
    if not isinstance(dms, str):
        return None
    pattern_with_dir = re.compile(
        r"(\d+)[°]?\s*(\d+)'?\s*([\d.]+)\"?\s*([NSEWO]?)", re.IGNORECASE,
    )
    pattern_no_dir = re.compile(
        r"(\d+)[°]?\s*(\d+)'?\s*([\d.]+)\"?", re.IGNORECASE,
    )
    m = pattern_with_dir.match(dms)
    if m:
        degrees, minutes, seconds, direction = m.groups()
        dd = float(degrees) + float(minutes) / 60 + float(seconds) / 3600
        if direction.upper() in ("S", "W", "O") or (
            not direction and 88 <= float(degrees) <= 92
        ):
            dd *= -1
        return dd
    m = pattern_no_dir.match(dms)
    if m:
        degrees, minutes, seconds = m.groups()
        dd = float(degrees) + float(minutes) / 60 + float(seconds) / 3600
        if 88 <= float(degrees) <= 92:
            dd *= -1
        return dd
    return None


def _convert_coord(value) -> float | None:
    """Best-effort coordinate conversion — DMS string or numeric.
    / Conversión flexible: cadena DMS o numérico.
    """
    if isinstance(value, str) and "°" in value:
        return _dms_to_dd(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_area_excel(xlsx_path: str, cdg: str) -> dict:
    """Parse an area Excel and produce a CSV ready for ``XYTableToPoint``.

    Replicates the consultant's notebook logic:
      - Read the second sheet
      - Clean X / Y columns, convert DMS to decimal degrees if needed
      - Forward-fill X / Y; group by (X, Y) summing ``Área (ha)`` and
        counting beneficiarios
      - Detect coordinate system (WGS84 vs GTM) and transform when needed
      - Write a UTF-8 CSV next to the Excel

    / Reproduce la lógica del notebook 1_2_Optional_excel_to_point.ipynb
    para generar un CSV listo para ``XYTableToPoint``.

    Returns:
        {
          "ok": bool,
          "csv_path": str,           # absolute path of generated CSV (when ok)
          "rows": int,               # number of point rows
          "errors": list[str],
        }
    """
    result: dict = {"ok": False, "csv_path": "", "rows": 0, "errors": []}
    if not xlsx_path or not os.path.isfile(xlsx_path):
        result["errors"].append(f"Excel not found: {xlsx_path}")
        return result

    try:
        import pandas as pd
    except ImportError as exc:
        result["errors"].append(f"pandas not installed: {exc}")
        return result

    try:
        df = pd.read_excel(xlsx_path, sheet_name=1)
    except Exception as exc:
        # Fall back to first sheet if the second sheet is missing
        try:
            df = pd.read_excel(xlsx_path, sheet_name=0)
        except Exception as exc2:
            result["errors"].append(f"Read error: {exc2}")
            return result

    required = ["X", "Y", "Área (ha)", "Beneficiario"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        result["errors"].append(
            f"Missing columns: {missing} (have {list(df.columns)})"
        )
        return result

    # Clean X / Y, convert DMS / Limpiar X/Y, convertir DMS
    for col in ("X", "Y"):
        df[col] = df[col].astype(str).str.strip()
        df[col] = df[col].str.replace(r"[^0-9°'\". NSEWO\-]", "", regex=True)
        df[col] = df[col].apply(_convert_coord)
        df[col] = pd.to_numeric(df[col], errors="coerce").ffill()

    df["Área (ha)"] = pd.to_numeric(df["Área (ha)"], errors="coerce")
    valid = df["Área (ha)"].notna() & df["Beneficiario"].notna()

    # Coordinate system heuristic — WGS84 lat/lon vs GTM meters
    # / Heurística de sistema de coordenadas — WGS84 vs GTM
    mean_x = df["X"].mean()
    mean_y = df["Y"].mean()
    if 13 <= mean_x <= 18 and -92 <= mean_y <= -88:
        try:
            import pyproj
            transformer = pyproj.Transformer.from_crs(
                "EPSG:4326", COORD_SYSTEM_GTM, always_xy=True,
            )
            new_x, new_y = transformer.transform(df["Y"].values, df["X"].values)
            df["X"], df["Y"] = new_x, new_y
        except ImportError:
            result["errors"].append(
                "pyproj not installed — cannot transform WGS84→GTM",
            )
            return result
    else:
        # Swap X/Y if reversed
        if not (350000 <= mean_x <= 500000) or not (1500000 <= mean_y <= 1800000):
            if (350000 <= mean_y <= 500000) and (1500000 <= mean_x <= 1800000):
                df["X"], df["Y"] = df["Y"], df["X"]

    df_valid = df[valid]
    if df_valid.empty:
        result["errors"].append("No valid rows after cleaning")
        return result

    if pd.to_numeric(df_valid["Beneficiario"], errors="coerce").notna().all():
        grouped = df_valid.groupby(["X", "Y"]).agg({
            "Área (ha)": "sum", "Beneficiario": "sum",
        }).reset_index()
    else:
        grouped = df_valid.groupby(["X", "Y"]).agg({
            "Área (ha)": "sum", "Beneficiario": "size",
        }).reset_index()

    grouped.rename(columns={"Beneficiario": "num_bnf"}, inplace=True)
    grouped["CadaParcelas"] = grouped["Área (ha)"] / grouped["num_bnf"]
    grouped["CdgActvdd"] = cdg
    grouped["Area_ha"] = grouped["Área (ha)"]

    folder = os.path.dirname(xlsx_path)
    csv_path = os.path.join(folder, f"{cdg}.csv")
    try:
        grouped.to_csv(csv_path, encoding="utf-8-sig", index=False)
    except OSError as exc:
        result["errors"].append(f"CSV write error: {exc}")
        return result

    result["ok"] = True
    result["csv_path"] = os.path.abspath(csv_path)
    result["rows"] = len(grouped)
    return result


def script_excel_to_point(p: dict) -> str:
    """Generate an ArcPy script that imports CSVs as point feature classes.

    Expected keys in *p*:
      - csvs: list of dicts, each ``{"csv_path": ..., "cdg": ..., "quarter": ...}``
      - gdb_path: target file geodatabase (CSVPOINT_TO_GDB)
      - aprx, map_name: ArcGIS Pro project + map (so the FC is added to the map)
      - lang: "es" or "en"

    / Genera un script ArcPy que importa CSVs como feature classes de puntos.
    """
    csvs = p.get("csvs", []) or []
    gdb_path = p.get("gdb_path", "")
    aprx = p.get("aprx", "")
    map_name = p.get("map_name", "AR_EbA_Area")
    lang = p.get("lang", "es")
    if lang not in ("es", "en"):
        lang = "es"

    # Build the csv-task literal
    tasks_literal = "[\n"
    for c in csvs:
        csv_path = c.get("csv_path", "")
        cdg = c.get("cdg", "")
        quarter = c.get("quarter", "")
        safe_cdg = re.sub(r"[^\w_]+", "", cdg or "")
        safe_qt = re.sub(r"[^A-Za-z0-9_]", "_", quarter or "")
        fc_name = f"{safe_qt}_{safe_cdg}" if safe_qt else safe_cdg
        tasks_literal += (
            "            {"
            f"'csv': r'{csv_path}', "
            f"'cdg': '{cdg}', "
            f"'quarter': '{safe_qt}', "
            f"'fc': '{fc_name}'"
            "},\n"
        )
    tasks_literal += "        ]"

    return textwrap.dedent(f"""\
        # ══════════════════════════════════════════════════════════════════
        # PASO 1b (fallback): Excel area workbook -> point feature class
        # ══════════════════════════════════════════════════════════════════
        import arcpy, os

        _LANG = "{lang}"
        def _msg(en, es):
            return es if _LANG == "es" else en

        aprx_path = r"{aprx}"
        map_name = "{map_name}"
        gdb_path = r"{gdb_path}"
        coord_system = '''{COORD_SYSTEM_GTM}'''
        tasks = {tasks_literal}

        if not gdb_path or not arcpy.Exists(gdb_path):
            print(_msg(
                f"CSVPOINT_TO_GDB not found: {{gdb_path}}",
                f"CSVPOINT_TO_GDB no encontrado: {{gdb_path}}",
            ))
            raise SystemExit(1)

        arcpy.env.workspace = gdb_path
        arcpy.env.overwriteOutput = True

        aprx = arcpy.mp.ArcGISProject(aprx_path)
        map_obj = aprx.listMaps(map_name)[0]

        # Locate or create the {{quarter}}_point group layer.  Mirrors
        # the logic used by paso1_quarterly.script_add_shapefiles_to_map.
        # / Localizar o crear el group layer {{quarter}}_point.
        def _get_or_create_group(m, name, parent=None):
            candidates = parent.listLayers() if parent else m.listLayers()
            for lyr in candidates:
                if lyr.isGroupLayer and lyr.name == name:
                    print(_msg(
                        f"Group layer found: {{name}}",
                        f"Group layer encontrado: {{name}}",
                    ))
                    return lyr
            import json as _json, tempfile
            lyrx_path = os.path.join(tempfile.gettempdir(), f"{{name}}.lyrx")
            lyrx_content = {{
                "type": "CIMLayerDocument", "version": "3.0.0",
                "layers": [f"CIMPATH=map/{{name}}.json"],
                "layerDefinitions": [{{
                    "type": "CIMGroupLayer", "name": name,
                    "uRI": f"CIMPATH=map/{{name}}.json",
                    "layers": [], "visibility": True, "expanded": True,
                }}],
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
                    return lyr
            return None

        added = 0
        for task in tasks:
            csv_path = task["csv"]
            cdg = task["cdg"]
            quarter = task["quarter"]
            fc_name = task["fc"]

            if not os.path.isfile(csv_path):
                print(_msg(
                    f"CSV missing, skipping: {{csv_path}}",
                    f"CSV no existe, omitiendo: {{csv_path}}",
                ))
                continue

            fc_full = os.path.join(gdb_path, fc_name)
            try:
                arcpy.management.XYTableToPoint(
                    in_table=csv_path,
                    out_feature_class=fc_full,
                    x_field="X", y_field="Y",
                    coordinate_system=coord_system,
                )
            except Exception as e:
                print(_msg(
                    f"XYTableToPoint failed for {{cdg}}: {{e}}",
                    f"XYTableToPoint falló para {{cdg}}: {{e}}",
                ))
                continue

            # Strip leading 'T' from quarter (T2026_Q1 -> 2026_Q1) to match
            # the convention used by the polygon group-layer logic.
            # / Quitar 'T' inicial del trimestre para igualar la convención.
            import re as _re
            display_qt = _re.sub(r'^T(?=\\d{{4}}_Q[1-4]$)', '', quarter) if quarter else ""
            if display_qt:
                grp_root = _get_or_create_group(map_obj, display_qt)
                grp_point = _get_or_create_group(
                    map_obj, f"{{display_qt}}_point", grp_root,
                )
            else:
                grp_point = None

            try:
                feature_layer = map_obj.addDataFromPath(fc_full)
                if grp_point:
                    map_obj.addLayerToGroup(grp_point, feature_layer)
                    map_obj.removeLayer(feature_layer)
                added += 1
                print(_msg(
                    f"Added point FC: {{fc_name}}",
                    f"FC de puntos agregado: {{fc_name}}",
                ))
            except Exception as e:
                print(_msg(
                    f"addDataFromPath failed for {{fc_name}}: {{e}}",
                    f"addDataFromPath falló para {{fc_name}}: {{e}}",
                ))

        # Save project / Guardar proyecto
        import time as _time
        for _attempt in range(3):
            try:
                aprx.save()
                break
            except OSError as _se:
                print(_msg(
                    f"Save attempt {{_attempt + 1}} failed: {{_se}}",
                    f"Intento de guardado {{_attempt + 1}} falló: {{_se}}",
                ))
                _time.sleep(2)
        del aprx

        print(_msg(
            f"== Done: {{added}} point FC(s) added to map '{{map_name}}'. ==",
            f"== Listo: {{added}} FC(s) de puntos agregados al mapa '{{map_name}}'. ==",
        ))
    """)
