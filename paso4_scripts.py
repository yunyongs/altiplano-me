"""
PASO 4 — AGOL (ArcGIS Online) update script generators.

Faithfully reproduces the WFL update workflow from notebook Section 7:
  SelectByLocation(ARE_IDENTICAL_TO) → SWITCH_SELECTION → Append NEW only
And the shapefile export from Section 8.
"""
from __future__ import annotations

import textwrap

from paso_constants import (
    GTM_WKT,
    WFL_FIELD_MAPPING_POINT,
    WFL_FIELD_MAPPING_POLYGON,
    build_wfl_field_mapping,
)


# ─────────────────────────────────────────────────────────────────────────────
# 4a. Update WFL Point  (notebook Section 7.1)
# ─────────────────────────────────────────────────────────────────────────────

def script_update_wfl_point(p: dict) -> str:
    gdb_fc = p.get("gdbPointPath", r"Oficial_GDB\AR_Oficial_punto_GTM_GDB")
    wfl_target = p.get("wflPointPath", r"Oficial_WFL\AR_Oficial_punto_GTM_WFL")
    gdb_path = p.get("gdbFullPath", "")

    # Build the field mapping from constants
    fm_str = build_wfl_field_mapping(WFL_FIELD_MAPPING_POINT, gdb_path) if gdb_path else "<FILL_GDB_PATH>"

    return textwrap.dedent(f"""\
        # PASO 4a: Update WFL Point
        # Faithful reproduction of notebook Section 7.1
        import arcpy

        # ── Paths ──
        input_features = r"{gdb_fc}"
        selecting_features = r"{wfl_target}"

        # ── 7.1.1 Select by Location: ARE_IDENTICAL_TO ──
        arcpy.management.SelectLayerByLocation(
            in_layer=input_features,
            overlap_type="ARE_IDENTICAL_TO",
            select_features=selecting_features,
            selection_type="NEW_SELECTION"
        )
        print("Selection completed (identical features selected).")

        # ── 7.1.2 Switch selection → only NEW data ──
        arcpy.management.SelectLayerByAttribute(input_features, "SWITCH_SELECTION")
        print("Selection switched — now selecting NEW features only.")

        # ── 7.1.3 Append NEW data to WFL ──
        field_mapping = r'{fm_str}'

        arcpy.management.Append(
            inputs=input_features,
            target=selecting_features,
            schema_type="NO_TEST",
            field_mapping=field_mapping,
            subtype="",
            expression="",
            match_fields=None,
            update_geometry="NOT_UPDATE_GEOMETRY"
        )
        print(f"Append completed: NEW point features added to {{selecting_features}}")
    """)


# ─────────────────────────────────────────────────────────────────────────────
# 4b. Update WFL Polygon  (notebook Section 7.2)
# ─────────────────────────────────────────────────────────────────────────────

def script_update_wfl_polygon(p: dict) -> str:
    gdb_fc = p.get("gdbPolygonPath", r"Oficial_GDB\AR_Oficial_poligono_GTM_GDB")
    wfl_target = p.get("wflPolygonPath", r"Oficial_WFL\AR_Oficial_poligono_GTM_WFL")
    gdb_path = p.get("gdbFullPath", "")

    fm_str = build_wfl_field_mapping(WFL_FIELD_MAPPING_POLYGON, gdb_path) if gdb_path else "<FILL_GDB_PATH>"

    return textwrap.dedent(f"""\
        # PASO 4b: Update WFL Polygon
        # Faithful reproduction of notebook Section 7.2
        import arcpy

        # ── Paths ──
        input_features = r"{gdb_fc}"
        selecting_features = r"{wfl_target}"

        # ── 7.2.1 Select by Location: ARE_IDENTICAL_TO ──
        arcpy.management.SelectLayerByLocation(
            in_layer=input_features,
            overlap_type="ARE_IDENTICAL_TO",
            select_features=selecting_features,
            selection_type="NEW_SELECTION"
        )
        print("Selection completed (identical polygon features selected).")

        # ── 7.2.2 Switch selection → only NEW data ──
        arcpy.management.SelectLayerByAttribute(input_features, "SWITCH_SELECTION")
        print("Selection switched — now selecting NEW polygon features only.")

        # ── 7.2.3 Append NEW data to WFL ──
        field_mapping = r'{fm_str}'

        arcpy.management.Append(
            inputs=input_features,
            target=selecting_features,
            schema_type="NO_TEST",
            field_mapping=field_mapping,
            subtype="",
            expression="",
            match_fields=None,
            update_geometry="NOT_UPDATE_GEOMETRY"
        )
        print(f"Append completed: NEW polygon features added to {{selecting_features}}")

        # ── Recalculate Area_ha in GTM projection ──
        arcpy.management.CalculateGeometryAttributes(
            in_features=selecting_features,
            geometry_property="Area_ha AREA",
            length_unit="",
            area_unit="HECTARES",
            coordinate_system=r'{GTM_WKT}',
            coordinate_format="SAME_AS_INPUT"
        )
        print("Area_ha recalculated in GTM projection.")
    """)


# ─────────────────────────────────────────────────────────────────────────────
# 4c. Export Shapefiles  (notebook Section 8)
# ─────────────────────────────────────────────────────────────────────────────

def script_export_shapefiles(p: dict) -> str:
    current_qt = p.get("currentQt", "T2025_Q1")
    official_polygon = p.get("officialPolygon", r"Oficial\AR_Oficial_poligono_GTM")
    official_point = p.get("officialPoint", r"Oficial\AR_Oficial_punto_GTM")
    export_folder = p.get("exportFolder", r"C:\Path\To\Shapes")
    return textwrap.dedent(f"""\
        # PASO 4c: Export Shapefiles
        # Faithful reproduction of notebook Section 8
        import arcpy, os

        current_qt = "{current_qt}"
        export_folder = r"{export_folder}"
        os.makedirs(export_folder, exist_ok=True)

        # ── Export Point ──
        export_point = os.path.join(export_folder, f"{{current_qt}}_Point.shp")
        arcpy.conversion.ExportFeatures(
            in_features=r"{official_point}",
            out_features=export_point,
            where_clause="",
            use_field_alias_as_name="NOT_USE_ALIAS",
            sort_field=None
        )
        print(f"Exported point shapefile: {{export_point}}")

        # ── Export Polygon ──
        export_polygon = os.path.join(export_folder, f"{{current_qt}}_Polygon.shp")
        arcpy.conversion.ExportFeatures(
            in_features=r"{official_polygon}",
            out_features=export_polygon,
            where_clause="",
            use_field_alias_as_name="NOT_USE_ALIAS",
            sort_field=None
        )
        print(f"Exported polygon shapefile: {{export_polygon}}")
        print(f"\\nShapefile export completed in: {{export_folder}}")
    """)


# ─────────────────────────────────────────────────────────────────────────────
# Script registry
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# 4d. 3-Way Sync Verification  (G6)
# ─────────────────────────────────────────────────────────────────────────────

def script_verify_3way_sync(p: dict) -> str:
    """
    Generate an ArcGIS Pro Python window script that compares:
      - Smartsheet (ground truth, loaded from CSV)
      - GIS GDB Feature Class (via arcpy)
      - AGOL Feature Layer (via arcgis Python API)

    Comparison items:
      1. Record count (unique CdgActvdd values)
      2. Area_ha sum (TOTAL_DE_HECTÁREAS vs Area_ha)
      3. CdgActvdd set differences (who has extras / is missing)

    Args in p:
      - ss_csv_path: path to Smartsheet CSV export
      - gis_gdb_path: GDB path (e.g. D:\\AR_2026.gdb)
      - gis_fc_name: Feature Class name (e.g. AR_Oficial_poligono_GTM)
      - agol_url: AGOL Feature Layer URL (can be empty if using Item ID)
      - agol_item_id: AGOL Item ID (preferred over URL)
      - agol_portal_url: Organisation portal URL (e.g. https://iucn.maps.arcgis.com)
    """
    ss_csv_path    = p.get("ss_csv_path", r"C:\Path\To\smartsheet_export.csv")
    gis_gdb_path   = p.get("gis_gdb_path", r"C:\Path\To\AR.gdb")
    gis_fc_name    = p.get("gis_fc_name", "AR_Oficial_poligono_GTM")
    agol_url       = p.get("agol_url", "")
    agol_item_id   = p.get("agol_item_id", "")
    agol_portal_url = p.get("agol_portal_url", "")

    # Build authentication block for the generated script
    # Uses active ArcGIS Pro session (OAuth is handled in the browser)
    agol_auth_block = (
        '# Usa la sesión activa de ArcGIS Pro / Uses active ArcGIS Pro session\n'
        '    gis = GIS("pro")'
    )

    # Build layer access block: Item ID preferred over URL
    if agol_item_id:
        agol_layer_block = (
            f'item = gis.content.get("{agol_item_id}")\n'
            f'        if item is None:\n'
            f'            raise ValueError("Item ID \\"{agol_item_id}\\" no encontrado / not found")\n'
            f'        fl = item.layers[0]\n'
            f'        print(f"  Capa / Layer: {{item.title}} ({{fl.url}})")'
        )
    elif agol_url:
        agol_layer_block = (
            f'fl = FeatureLayer("{agol_url}", gis=gis)\n'
            f'        print(f"  Capa / Layer: {{fl.url}}")'
        )
    else:
        agol_layer_block = (
            '# [!] Configure AGOL_URL o AGOL_ITEM_ID\n'
            '        fl = FeatureLayer("https://services.arcgis.com/...", gis=gis)'
        )

    return textwrap.dedent(f"""\
        # ═══════════════════════════════════════════════════════════════════════
        # PASO 4d: Verificación 3 Fuentes / 3-Way Sync Verification
        # Smartsheet (ground truth) ↔ GIS GDB ↔ AGOL Feature Layer
        # Ejecutar en / Run in: ArcGIS Pro Python window
        # ═══════════════════════════════════════════════════════════════════════
        import arcpy
        import csv
        import os
        from arcgis.gis import GIS
        from arcgis.features import FeatureLayer

        # ── Configuración / Configuration ──────────────────────────────────────
        SS_CSV_PATH  = r"{ss_csv_path}"
        GIS_GDB_PATH = r"{gis_gdb_path}"
        GIS_FC_NAME  = "{gis_fc_name}"
        {"# AGOL via Item ID: " + agol_item_id if agol_item_id else 'AGOL_URL     = "' + agol_url + '"'}
        AREA_TOL_HA  = 0.1  # Tolerancia de área / Area tolerance in ha

        # ── 1. Cargar Smartsheet CSV / Load Smartsheet CSV (ground truth) ───────
        print("\\n1. Cargando Smartsheet CSV / Loading Smartsheet CSV…")
        ss_records = {{}}  # {{CdgActvdd: area_ha}}
        ss_area_col = None
        ss_code_col = None
        try:
            with open(SS_CSV_PATH, newline='', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # ES: Buscar columnas flexiblemente / EN: Flexible column search
                    if ss_code_col is None:
                        for k in row.keys():
                            if 'DIGO' in k.upper() or 'CODIGO' in k.upper():
                                ss_code_col = k; break
                    if ss_area_col is None:
                        for k in row.keys():
                            if 'HECT' in k.upper() or 'AREA' in k.upper():
                                ss_area_col = k; break
                    code = row.get(ss_code_col, '').strip()
                    area_str = row.get(ss_area_col, '0') if ss_area_col else '0'
                    try:
                        area = float(area_str.replace(',', '.')) if area_str else 0.0
                    except ValueError:
                        area = 0.0
                    if code:
                        ss_records[code] = ss_records.get(code, 0.0) + area
            print(f"  SS: {{len(ss_records)}} registros, área total = {{sum(ss_records.values()):.2f}} ha")
        except Exception as e:
            print(f"  [X] Error leyendo SS CSV / Error reading SS CSV: {{e}}")
            ss_records = {{}}

        # ── 2. Cargar GIS GDB / Load GIS GDB ──────────────────────────────────
        print("\\n2. Leyendo GIS GDB / Reading GIS GDB…")
        gis_records = {{}}  # {{CdgActvdd: area_ha}}
        try:
            fc_path = os.path.join(GIS_GDB_PATH, GIS_FC_NAME)
            fields = [f.name for f in arcpy.ListFields(fc_path)]
            cdg_field = 'CdgActvdd' if 'CdgActvdd' in fields else None
            area_field = 'Area_ha' if 'Area_ha' in fields else None
            if not cdg_field:
                print(f"  [X] Campo CdgActvdd no encontrado en {{fc_path}}")
            else:
                cursor_fields = [cdg_field] + ([area_field] if area_field else [])
                with arcpy.da.SearchCursor(fc_path, cursor_fields) as cur:
                    for row in cur:
                        code = str(row[0]).strip() if row[0] else ''
                        area = float(row[1]) if area_field and row[1] is not None else 0.0
                        if code:
                            gis_records[code] = gis_records.get(code, 0.0) + area
            print(f"  GIS: {{len(gis_records)}} registros, área total = {{sum(gis_records.values()):.2f}} ha")
        except Exception as e:
            print(f"  [X] Error leyendo GIS GDB / Error reading GIS GDB: {{e}}")

        # ── 3. Cargar AGOL Feature Layer / Load AGOL Feature Layer ────────────
        print("\\n3. Consultando AGOL / Querying AGOL Feature Layer…")
        agol_records = {{}}  # {{CdgActvdd: area_ha}}
        try:
            {agol_auth_block}
            {agol_layer_block}
            result = fl.query(out_fields="CdgActvdd,Area_ha", return_geometry=False)
            for feat in result.features:
                attrs = feat.attributes
                code = str(attrs.get('CdgActvdd', '') or '').strip()
                area = float(attrs.get('Area_ha', 0) or 0)
                if code:
                    agol_records[code] = agol_records.get(code, 0.0) + area
            print(f"  AGOL: {{len(agol_records)}} registros, área total = {{sum(agol_records.values()):.2f}} ha")
        except Exception as e:
            print(f"  [X] Error consultando AGOL / Error querying AGOL: {{e}}")

        # ── 4. Comparación 3-way / 3-way comparison ────────────────────────────
        print("\\n" + "═" * 70)
        print("4. VERIFICACIÓN 3 FUENTES / 3-WAY VERIFICATION")
        print("   Ground truth: Smartsheet | Comparado con: GIS + AGOL")
        print("=" * 70)

        ss_set   = set(ss_records.keys())
        gis_set  = set(gis_records.keys())
        agol_set = set(agol_records.keys())

        ss_area_total   = sum(ss_records.values())
        gis_area_total  = sum(gis_records.values())
        agol_area_total = sum(agol_records.values())

        # 4a. Conteo de registros / Record count
        print(f"\\n  [A] Conteo de registros / Record count:")
        print(f"      Smartsheet: {{len(ss_set):>5}}")
        _gis_delta_n = len(gis_set) - len(ss_set)
        _agol_delta_n = len(agol_set) - len(ss_set)
        if len(gis_set) == len(ss_set):
            print(f"      GIS:        {{len(gis_set):>5}}  [OK]")
        elif abs(_gis_delta_n) <= 2:
            print(f"      GIS:        {{len(gis_set):>5}}  [!] (Δ={{_gis_delta_n:+d}})")
        else:
            print(f"      GIS:        {{len(gis_set):>5}}  [X] (Δ={{_gis_delta_n:+d}})")
        if len(agol_set) == len(ss_set):
            print(f"      AGOL:       {{len(agol_set):>5}}  [OK]")
        elif abs(_agol_delta_n) <= 2:
            print(f"      AGOL:       {{len(agol_set):>5}}  [!] (Δ={{_agol_delta_n:+d}})")
        else:
            print(f"      AGOL:       {{len(agol_set):>5}}  [X] (Δ={{_agol_delta_n:+d}})")

        # 4b. Suma de áreas / Area sum
        print(f"\\n  [B] Suma de áreas (ha) / Area sum (ha):")
        print(f"      Smartsheet: {{ss_area_total:>10.2f}} ha")
        gis_delta  = abs(gis_area_total  - ss_area_total)
        agol_delta = abs(agol_area_total - ss_area_total)
        _gis_sym  = "[OK]" if gis_delta  <= AREA_TOL_HA else ("[!]" if gis_delta  <= 1.0 else "[X]")
        _agol_sym = "[OK]" if agol_delta <= AREA_TOL_HA else ("[!]" if agol_delta <= 1.0 else "[X]")
        print(f"      GIS:        {{gis_area_total:>10.2f}} ha  (Δ={{gis_delta:.2f}}) {{_gis_sym}}")
        print(f"      AGOL:       {{agol_area_total:>10.2f}} ha  (Δ={{agol_delta:.2f}}) {{_agol_sym}}")

        # 4c. Diferencias de CdgActvdd / CdgActvdd set differences
        print(f"\\n  [C] Diferencias de CdgActvdd / CdgActvdd set differences:")
        ss_only_vs_gis  = ss_set  - gis_set
        gis_only        = gis_set - ss_set
        ss_only_vs_agol = ss_set  - agol_set
        agol_only       = agol_set - ss_set

        if not ss_only_vs_gis and not gis_only:
            print("      SS ↔ GIS:  [OK] Coincidencia exacta / Exact match")
        else:
            if ss_only_vs_gis:
                _sample = ', '.join(sorted(ss_only_vs_gis)[:10])
                _ellip  = "…" if len(ss_only_vs_gis) > 10 else ""
                print(f"      SS→GIS faltantes ({{len(ss_only_vs_gis)}}): [X] {{_sample}}{{_ellip}}")
            if gis_only:
                _sample = ', '.join(sorted(gis_only)[:10])
                _ellip  = "…" if len(gis_only) > 10 else ""
                print(f"      GIS extra ({{len(gis_only)}}):         [!] {{_sample}}{{_ellip}}")

        if not ss_only_vs_agol and not agol_only:
            print("      SS ↔ AGOL: [OK] Coincidencia exacta / Exact match")
        else:
            if ss_only_vs_agol:
                _sample = ', '.join(sorted(ss_only_vs_agol)[:10])
                _ellip  = "…" if len(ss_only_vs_agol) > 10 else ""
                print(f"      SS→AGOL faltantes ({{len(ss_only_vs_agol)}}): [X] {{_sample}}{{_ellip}}")
            if agol_only:
                _sample = ', '.join(sorted(agol_only)[:10])
                _ellip  = "…" if len(agol_only) > 10 else ""
                print(f"      AGOL extra ({{len(agol_only)}}):         [!] {{_sample}}{{_ellip}}")

        # ── Resumen final / Final summary ──────────────────────────────────────
        print("\\n" + "═" * 70)
        has_errors   = bool(ss_only_vs_gis or ss_only_vs_agol)
        has_warnings = bool(gis_only or agol_only or gis_delta > AREA_TOL_HA or agol_delta > AREA_TOL_HA)
        if has_errors:
            print("[X]  VERIFICACIÓN FALLIDA — faltan registros en GIS o AGOL.")
            print("[X]  VERIFICATION FAILED — records missing in GIS or AGOL.")
        elif has_warnings:
            print("[!]   VERIFICACIÓN CON ADVERTENCIAS — revisar diferencias arriba.")
            print("[!]   VERIFICATION WITH WARNINGS — review differences above.")
        else:
            print("[OK]  VERIFICACIÓN EXITOSA — las 3 fuentes coinciden.")
            print("[OK]  VERIFICATION PASSED — all 3 sources match.")
        print("═" * 70)
    """)


PASO4_SCRIPTS = {
    "update_wfl_point":   script_update_wfl_point,
    "update_wfl_polygon": script_update_wfl_polygon,
    "export_shapefiles":  script_export_shapefiles,
    "verify_3way_sync":   script_verify_3way_sync,
}
