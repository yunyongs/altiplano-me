"""
PASO 3 — ArcPy script generators.

Each function returns a complete Python script string ready to paste
into the ArcGIS Pro Python window.  The scripts faithfully reproduce
the workflow in ``2_2_AR_Oficial_ArcPy.ipynb``.
"""
from __future__ import annotations

import textwrap

from paso3_pdf_report import script_overlap_pdf_report
from paso_constants import (
    APPEND_FIELD_MAPPING_POINT_TEMPLATE,
    APPEND_FIELD_MAPPING_POLYGON_TEMPLATE,
    ERASE_CURSOR_FIELDS,
    MONTO_YEARLY_FIELDS,
)


def _indent_list(items: list[str], var_name: str, indent: str = "    ") -> str:
    """Format a Python list literal across multiple lines."""
    lines = [f"{var_name} = ["]
    for item in items:
        lines.append(f'{indent}r\'{item}\',')
    lines.append("]")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# 3a. Merge with Field Mapping  (notebook Section 1.3)
# ─────────────────────────────────────────────────────────────────────────────

def script_merge_with_field_mapping(p: dict) -> str:
    gdb = p.get("gdb", r"C:\Path\To\Your.gdb")
    current_qt = p.get("currentQt", "T2025_Q1")
    return textwrap.dedent(f"""\
        # PASO 3a: Merge with Field Mapping
        # Faithful reproduction of notebook Section 1.3
        import arcpy, os, atexit

        gdb = r"{gdb}"
        current_qt = "{current_qt}"
        arcpy.env.workspace = gdb
        arcpy.env.overwriteOutput = True
        atexit.register(arcpy.ClearWorkspaceCache_management)

        # ── Helper: create field mapping string ──
        def create_field_mapping_string(layer_list, field_details):
            field_mapping_parts = []
            for field, details in field_details.items():
                fmf = [f'{{field}} "{{field}}" true true false {{details["length"]}} {{details["type"]}} 0 0,First,#']
                for layer in layer_list:
                    if field in [f.name for f in arcpy.ListFields(layer)]:
                        fmf.append(f'{{layer}},{{field}},-1,-1')
                field_mapping_parts.append(','.join(fmf))
            return ';'.join(field_mapping_parts)

        # ── Field details ──
        field_details_point = {{
            'Area_ha':    {{'type': 'Double', 'length': 19}},
            'CdgActvdd':  {{'type': 'Text',   'length': 254}},
            'Agrupados':  {{'type': 'Text',   'length': 254}},
            'NumPrclBnf': {{'type': 'Short',  'length': 0}},
        }}
        field_details_polygon = {{
            'CdgActvdd':  {{'type': 'Text',  'length': 254}},
            'Agrupados':  {{'type': 'Text',  'length': 254}},
            'NumPrclBnf': {{'type': 'Short', 'length': 0}},
        }}

        # ── List your input feature layers here ──
        # Replace with your actual feature layer paths
        feature_layers_point = [
            # r"path_to_point_layer_1",
            # r"path_to_point_layer_2",
        ]
        feature_layers_polygon = [
            # r"path_to_polygon_layer_1",
            # r"path_to_polygon_layer_2",
        ]

        current_merged_point = f"{{current_qt}}_point"
        current_merged_polygon = f"{{current_qt}}_polygon"

        # ── Merge Points ──
        if feature_layers_point:
            fm = create_field_mapping_string(feature_layers_point, field_details_point)
            arcpy.management.Merge(
                inputs=feature_layers_point,
                output=current_merged_point,
                field_mappings=fm,
                add_source="NO_SOURCE_INFO"
            )
            print(f"Merge completed for point layers in {{current_merged_point}}.")

        # ── Merge Polygons ──
        if feature_layers_polygon:
            fm = create_field_mapping_string(feature_layers_polygon, field_details_polygon)
            arcpy.management.Merge(
                inputs=feature_layers_polygon,
                output=current_merged_polygon,
                field_mappings=fm,
                add_source="NO_SOURCE_INFO"
            )
            print("Merge completed for polygon layers.")

            # Add Area_ha field and calculate
            if 'Area_ha' not in [f.name for f in arcpy.ListFields(current_merged_polygon)]:
                arcpy.AddField_management(current_merged_polygon, 'Area_ha', 'DOUBLE')
            arcpy.CalculateField_management(
                current_merged_polygon, 'Area_ha',
                'round(!shape.area@hectares!, 2)', 'PYTHON3'
            )
            print("Area calculation completed for polygon layers.")

        # ── Add OUTPUT and REPORTER fields ──
        for layer_path in [current_merged_point, current_merged_polygon]:
            if arcpy.Exists(layer_path):
                arcpy.AddField_management(layer_path, "OUTPUT", "TEXT")
                arcpy.AddField_management(layer_path, "REPORTER", "TEXT")
                print(f"OUTPUT and REPORTER fields added to {{layer_path}}.")
    """)


# ─────────────────────────────────────────────────────────────────────────────
# 3b. Overlap Analysis  (notebook Section 2.1)
# ─────────────────────────────────────────────────────────────────────────────

def script_overlap_analysis(p: dict) -> str:
    gdb = p.get("gdb", r"C:\Path\To\Your.gdb")
    current_qt = p.get("currentQt", "T2025_Q1")
    official_polygon = p.get("officialPolygon", "AR_Oficial_poligono_GTM")
    return textwrap.dedent(f"""\
        # PASO 3b: Overlap Analysis
        # Faithful reproduction of notebook Section 2.1
        import arcpy

        gdb = r"{gdb}"
        current_qt = "{current_qt}"
        arcpy.env.workspace = gdb
        arcpy.env.overwriteOutput = True

        official_polygon = "{official_polygon}"
        current_merged_polygon = f"{{current_qt}}_polygon"
        count_ovlp = f"{{current_qt}}_polygon_CountOverlapp"
        pair_int = f"{{current_qt}}_polygon_CountOverlapp_PairIntersect"

        # ── 2.1.1 Count Overlapping Features ──
        arcpy.analysis.CountOverlappingFeatures(
            in_features=[official_polygon, current_merged_polygon],
            out_feature_class=count_ovlp,
            min_overlap_count=2,
            out_overlap_table=None
        )
        print(f"CountOverlappingFeatures completed: {{count_ovlp}}")

        # ── 2.1.2 PairwiseIntersect for self-overlap ──
        arcpy.analysis.PairwiseIntersect(
            in_features=[count_ovlp, current_merged_polygon],
            out_feature_class=pair_int,
            join_attributes="ALL",
            cluster_tolerance=None,
            output_type="INPUT"
        )
        print(f"PairwiseIntersect completed: {{pair_int}}")

        # ── 2.2 Duplicate Detection (ARE_IDENTICAL_TO) ──
        target_lyr = pair_int
        compare_lyr = official_polygon

        field_name = "DuplicateCheck"
        if field_name not in [f.name for f in arcpy.ListFields(target_lyr)]:
            arcpy.management.AddField(target_lyr, field_name, "TEXT", field_length=20)

        # Initialize all to "Unique"
        arcpy.management.CalculateField(
            target_lyr, field_name, "'Unique'", expression_type="PYTHON3"
        )

        # Select geometrically identical features
        arcpy.management.SelectLayerByLocation(
            in_layer=target_lyr,
            overlap_type="ARE_IDENTICAL_TO",
            select_features=compare_lyr,
            selection_type="NEW_SELECTION"
        )

        # Mark selected as "Duplicate"
        arcpy.management.CalculateField(
            target_lyr, field_name, "'Duplicate'", expression_type="PYTHON3"
        )

        arcpy.management.SelectLayerByAttribute(target_lyr, "CLEAR_SELECTION")
        print("Identicals marked: 'Duplicate' — others set to 'Unique'.")
    """)


# ─────────────────────────────────────────────────────────────────────────────
# 3c. Erase Pipeline  (notebook Section 3)
# ─────────────────────────────────────────────────────────────────────────────

def script_erase_pipeline(p: dict) -> str:
    gdb = p.get("gdb", r"C:\Path\To\Your.gdb")
    current_qt = p.get("currentQt", "T2025_Q1")
    official_polygon = p.get("officialPolygon", "AR_Oficial_poligono_GTM")
    return textwrap.dedent(f"""\
        # PASO 3c: Erase Pipeline
        # Faithful reproduction of notebook Section 3
        import arcpy

        gdb = r"{gdb}"
        current_qt = "{current_qt}"
        arcpy.env.workspace = gdb
        arcpy.env.overwriteOutput = True

        official_polygon = "{official_polygon}"
        pair_int = f"{{current_qt}}_polygon_CountOverlapp_PairIntersect"
        erase_tool_layer = "erase_tool_layer"
        current_merged_polygon = f"{{current_qt}}_polygon"
        current_merged_polygon_Erased = f"{{current_qt}}_polygon_Erased"
        AR_Oficial_poligono_GTM_Erased = f"{{official_polygon}}_{{current_qt}}_Erased"
        AR_Oficial_poligono_GTM_Erased_backup = f"{{AR_Oficial_poligono_GTM_Erased}}_backup"

        # ── Pre-erase stats ──
        before_count_curr = int(arcpy.management.GetCount(current_merged_polygon)[0])
        before_area_curr = sum(r[0] for r in arcpy.da.SearchCursor(current_merged_polygon, ["Area_ha"]) if r[0] is not None)
        before_count_off = int(arcpy.management.GetCount(official_polygon)[0])
        before_area_off = sum(r[0] for r in arcpy.da.SearchCursor(official_polygon, ["Area_ha"]) if r[0] is not None)

        # ── 3.1.1 Erase: Current Quarter ──
        arcpy.MakeFeatureLayer_management(pair_int, erase_tool_layer)
        query = "Erase_FC = 'Current Quarter'"
        arcpy.SelectLayerByAttribute_management(erase_tool_layer, "NEW_SELECTION", query)
        selected_erase_features = arcpy.management.CopyFeatures(erase_tool_layer, "in_memory/selectedEraseFeatures")

        # PairwiseErase on current polygon
        arcpy.analysis.PairwiseErase(
            in_features=current_merged_polygon,
            erase_features=selected_erase_features,
            out_feature_class=current_merged_polygon_Erased,
            cluster_tolerance=None
        )
        arcpy.Delete_management("in_memory/selectedEraseFeatures")

        # ── 3.1.2 Update Area_ha after erase (current) ──
        in_lyr_current = current_merged_polygon_Erased
        arcpy.MakeFeatureLayer_management(pair_int, erase_tool_layer)
        arcpy.SelectLayerByAttribute_management(erase_tool_layer, "NEW_SELECTION", query)
        slct_lyr = arcpy.management.CopyFeatures(erase_tool_layer, "in_memory/selectedEraseFeatures")
        arcpy.SelectLayerByLocation_management(
            in_layer=in_lyr_current,
            overlap_type="INTERSECT",
            select_features=slct_lyr,
            selection_type="NEW_SELECTION"
        )
        arcpy.CalculateField_management(in_lyr_current, 'Area_ha', 'round(!shape.area@hectares!, 2)', 'PYTHON3')
        print(f"Area calculation completed for {{in_lyr_current}}")
        arcpy.SelectLayerByAttribute_management(in_lyr_current, "CLEAR_SELECTION")
        arcpy.Delete_management("in_memory/selectedEraseFeatures")

        # ── 3.2 Erase: Official polygon ──
        arcpy.MakeFeatureLayer_management(pair_int, erase_tool_layer)
        query_official = "Erase_FC = 'Official'"
        arcpy.SelectLayerByAttribute_management(erase_tool_layer, "NEW_SELECTION", query_official)
        selected_erase_features = arcpy.management.CopyFeatures(erase_tool_layer, "in_memory/selectedEraseFeatures")

        arcpy.analysis.PairwiseErase(
            in_features=official_polygon,
            erase_features=selected_erase_features,
            out_feature_class=AR_Oficial_poligono_GTM_Erased,
            cluster_tolerance=None
        )
        arcpy.Delete_management("in_memory/selectedEraseFeatures")

        # Backup before area update
        arcpy.CopyFeatures_management(AR_Oficial_poligono_GTM_Erased, AR_Oficial_poligono_GTM_Erased_backup)

        # Update Area_ha for official erased
        in_lyr_official = AR_Oficial_poligono_GTM_Erased
        arcpy.MakeFeatureLayer_management(pair_int, erase_tool_layer)
        arcpy.SelectLayerByAttribute_management(erase_tool_layer, "NEW_SELECTION", query_official)
        selected_erase_features = arcpy.management.CopyFeatures(erase_tool_layer, "in_memory/selectedEraseFeatures")
        arcpy.SelectLayerByLocation_management(
            in_layer=in_lyr_official,
            overlap_type="INTERSECT",
            select_features=selected_erase_features,
            selection_type="NEW_SELECTION"
        )
        arcpy.CalculateField_management(in_lyr_official, 'Area_ha', 'round(!shape.area@hectares!, 2)', 'PYTHON3')
        print(f"Area calculation completed for {{in_lyr_official}}")
        arcpy.SelectLayerByAttribute_management(in_lyr_official, "CLEAR_SELECTION")
        arcpy.Delete_management("in_memory/selectedEraseFeatures")

        # ── Post-erase stats ──
        after_count_curr = int(arcpy.management.GetCount(current_merged_polygon_Erased)[0])
        after_area_curr = sum(r[0] for r in arcpy.da.SearchCursor(current_merged_polygon_Erased, ["Area_ha"]) if r[0] is not None)
        after_count_off = int(arcpy.management.GetCount(AR_Oficial_poligono_GTM_Erased)[0])
        after_area_off = sum(r[0] for r in arcpy.da.SearchCursor(AR_Oficial_poligono_GTM_Erased, ["Area_ha"]) if r[0] is not None)

        print(f"CLEANING_STATS:erase:current:before={{before_count_curr}},{{before_area_curr:.2f}}:after={{after_count_curr}},{{after_area_curr:.2f}}")
        print(f"CLEANING_STATS:erase:official:before={{before_count_off}},{{before_area_off:.2f}}:after={{after_count_off}},{{after_area_off:.2f}}")
        print("Erase pipeline completed.")
    """)


# ─────────────────────────────────────────────────────────────────────────────
# 3d. Spatial Join with Micro  (notebook Section 4)
# ─────────────────────────────────────────────────────────────────────────────

def script_spatial_join_micro(p: dict) -> str:
    gdb = p.get("gdb", r"C:\Path\To\Your.gdb")
    current_qt = p.get("currentQt", "T2025_Q1")
    base_micro = p.get("baseMicroMuni", "BASE_Micro_MUNI")
    ss_table = p.get("smartsheetTable", "ssheet")
    return textwrap.dedent(f"""\
        # PASO 3d: Spatial Join with Microcuencas
        # Faithful reproduction of notebook Section 4
        import arcpy

        gdb = r"{gdb}"
        current_qt = "{current_qt}"
        arcpy.env.workspace = gdb
        arcpy.env.overwriteOutput = True

        BASE_Micro_MUNI = "{base_micro}"
        current_merged_polygon_Erased = f"{{current_qt}}_polygon_Erased"
        current_merged_polygon_Erased_pair_mico = f"{{current_qt}}_polygon_Erased_pair_micro"

        current_merged_point = f"{{current_qt}}_point"
        Current_point_cleaned_pair_micro = f"{{current_qt}}_point_cleaned_pair_micro"

        ss_table = "{ss_table}"

        # ── 4.1 PairwiseIntersect: Polygon x Micro ──
        arcpy.analysis.PairwiseIntersect(
            in_features=[current_merged_polygon_Erased, BASE_Micro_MUNI],
            out_feature_class=current_merged_polygon_Erased_pair_mico,
            join_attributes="ALL",
            cluster_tolerance=None,
            output_type="INPUT"
        )
        print(f"PairwiseIntersect (polygon) completed: {{current_merged_polygon_Erased_pair_mico}}")

        # Update Area_ha + centroids for polygon
        arcpy.CalculateField_management(
            current_merged_polygon_Erased_pair_mico, 'Area_ha',
            'round(!shape.area@hectares!, 2)', 'PYTHON3'
        )
        arcpy.CalculateField_management(
            current_merged_polygon_Erased_pair_mico, 'Shp_x_center',
            '!shape.centroid.X!', 'PYTHON3'
        )
        arcpy.CalculateField_management(
            current_merged_polygon_Erased_pair_mico, 'Shp_y_center',
            '!shape.centroid.Y!', 'PYTHON3'
        )

        # ── 4.2 PairwiseIntersect: Point x Micro ──
        arcpy.analysis.PairwiseIntersect(
            in_features=[current_merged_point, BASE_Micro_MUNI],
            out_feature_class=Current_point_cleaned_pair_micro,
            join_attributes="ALL",
            cluster_tolerance=None,
            output_type="INPUT"
        )
        print(f"PairwiseIntersect (point) completed: {{Current_point_cleaned_pair_micro}}")

        # Update centroids for point
        arcpy.CalculateField_management(
            Current_point_cleaned_pair_micro, 'Shp_x_center',
            '!shape.centroid.X!', 'PYTHON3'
        )
        arcpy.CalculateField_management(
            Current_point_cleaned_pair_micro, 'Shp_y_center',
            '!shape.centroid.Y!', 'PYTHON3'
        )

        # ── 4.3 JoinField from Smartsheet table ──
        join_field = "CÓDIGO_DE_LA_ACTIVIDAD"
        arcpy.management.JoinField(
            in_data=current_merged_polygon_Erased_pair_mico,
            in_field="CdgActvdd",
            join_table=ss_table,
            join_field=join_field
        )
        arcpy.management.JoinField(
            in_data=Current_point_cleaned_pair_micro,
            in_field="CdgActvdd",
            join_table=ss_table,
            join_field=join_field
        )
        print("JoinField from Smartsheet completed for polygon and point.")
    """)


# ─────────────────────────────────────────────────────────────────────────────
# 3e. Duplicate Detection  (notebook Section 2.1.2)
# ─────────────────────────────────────────────────────────────────────────────

def script_duplicate_detection(p: dict) -> str:
    gdb = p.get("gdb", r"C:\Path\To\Your.gdb")
    current_qt = p.get("currentQt", "T2025_Q1")
    official_polygon = p.get("officialPolygon", "AR_Oficial_poligono_GTM")
    return textwrap.dedent(f"""\
        # PASO 3e: Duplicate Detection
        # Faithful reproduction of notebook Section 2.1.2
        import arcpy

        gdb = r"{gdb}"
        current_qt = "{current_qt}"
        arcpy.env.workspace = gdb
        arcpy.env.overwriteOutput = True

        official_polygon = "{official_polygon}"
        pair_int = f"{{current_qt}}_polygon_CountOverlapp_PairIntersect"

        target_lyr = pair_int
        compare_lyr = official_polygon

        # Ensure DuplicateCheck field exists
        field_name = "DuplicateCheck"
        if field_name not in [f.name for f in arcpy.ListFields(target_lyr)]:
            arcpy.management.AddField(target_lyr, field_name, "TEXT", field_length=20)

        # Initialize all to "Unique"
        arcpy.management.CalculateField(
            target_lyr, field_name, "'Unique'", expression_type="PYTHON3"
        )

        # Select geometrically identical features
        arcpy.management.SelectLayerByLocation(
            in_layer=target_lyr,
            overlap_type="ARE_IDENTICAL_TO",
            select_features=compare_lyr,
            selection_type="NEW_SELECTION"
        )

        # Mark duplicates
        arcpy.management.CalculateField(
            target_lyr, field_name, "'Duplicate'", expression_type="PYTHON3"
        )

        arcpy.management.SelectLayerByAttribute(target_lyr, "CLEAR_SELECTION")
        print("Identicals marked: 'Duplicate' — others set to 'Unique'.")

        # ── Erase_FC auto-assignment with rule engine ──
        fc = pair_int
        existing = [f.name for f in arcpy.ListFields(fc)]
        if "Erase_FC" not in existing:
            arcpy.AddField_management(fc, "Erase_FC", "TEXT", field_length=20)
        if "Erase_Rule" not in existing:
            arcpy.AddField_management(fc, "Erase_Rule", "TEXT", field_length=1)

        fields = {ERASE_CURSOR_FIELDS}

        with arcpy.da.UpdateCursor(fc, fields) as cursor:
            for row in cursor:
                oid, off_out, cur_out, off_abe, cur_abe, overlap, _, _ = row
                erase = "Manual"
                rule = ""

                # Rule A: zero overlap → keep official
                if overlap is not None and overlap == 0:
                    erase, rule = "Current Quarter", "A"
                # Rule B: OUTPUT1 vs OUTPUT2
                elif off_out == "OUTPUT1" and cur_out == "OUTPUT2":
                    erase, rule = "Official", "B"
                elif off_out == "OUTPUT2" and cur_out == "OUTPUT1":
                    erase, rule = "Current Quarter", "B"
                # Rule C: Proteccion priority
                elif off_abe and "Protección" in str(off_abe) and (not cur_abe or "Protección" not in str(cur_abe)):
                    erase, rule = "Official", "C"
                elif cur_abe and "Protección" in str(cur_abe) and (not off_abe or "Protección" not in str(off_abe)):
                    erase, rule = "Current Quarter", "C"
                # Rule D: Agroforestal priority
                elif cur_abe and "Sistema Agroforestal" in str(cur_abe) and (not off_abe or "Sistema Agroforestal" not in str(off_abe)):
                    erase, rule = "Official", "D"
                elif off_abe and "Sistema Agroforestal" in str(off_abe) and (not cur_abe or "Sistema Agroforestal" not in str(cur_abe)):
                    erase, rule = "Current Quarter", "D"
                # Rule E: same OUTPUT & same AbE
                elif off_out == cur_out and off_abe == cur_abe:
                    erase, rule = "Current Quarter", "E"

                row[6] = erase
                row[7] = rule
                cursor.updateRow(row)
                print(f"OID {{oid}}: Erase_FC = {{erase}} (Rule {{rule}})")

        print("Erase_FC auto-assignment completed.")
    """)


# ─────────────────────────────────────────────────────────────────────────────
# 3f. Incentive Validation  (notebook validation section)
# ─────────────────────────────────────────────────────────────────────────────

def script_incentive_validation(p: dict) -> str:
    gdb = p.get("gdb", r"C:\Path\To\Your.gdb")
    fc = p.get("featureClass", "AR_Oficial_poligono_GTM")
    monto_fields = MONTO_YEARLY_FIELDS
    fields_str = ", ".join(f'"{f}"' for f in monto_fields)
    return textwrap.dedent(f"""\
        # PASO 3f: Incentive Amount Validation
        import arcpy

        gdb = r"{gdb}"
        arcpy.env.workspace = gdb
        fc = "{fc}"

        # Yearly MONTO fields
        monto_fields = [{fields_str}]

        # Add sum field
        sum_field = 'sum_monto_incentivo'
        existing = [f.name for f in arcpy.ListFields(fc)]
        if sum_field not in existing:
            arcpy.AddField_management(fc, sum_field, 'DOUBLE')

        # Calculate sum of all yearly MONTO fields (handle None)
        parts = [f"(0 if !{{f}}! is None else !{{f}}!)" for f in monto_fields]
        expr = " + ".join(parts)
        arcpy.CalculateField_management(fc, sum_field, expr, "PYTHON3")
        print(f"Calculated {{sum_field}} for {{fc}}")

        # Compare with MONTO_DEL_INCENTIVO__QQ_
        total_field = 'MONTO_DEL_INCENTIVO__QQ_'
        if total_field in existing:
            differences = []
            with arcpy.da.SearchCursor(fc, [sum_field, total_field, 'OBJECTID']) as cursor:
                for row in cursor:
                    calc_sum = row[0] or 0
                    reported = row[1] or 0
                    diff = round(calc_sum - reported, 2)
                    if abs(diff) > 0.01:
                        differences.append({{'oid': row[2], 'sum': calc_sum, 'reported': reported, 'diff': diff}})

            print(f"\\nRecords with non-zero differences: {{len(differences)}}")
            if differences:
                diffs_vals = [d['diff'] for d in differences]
                print(f"  Min diff: {{min(diffs_vals):.2f}}")
                print(f"  Max diff: {{max(diffs_vals):.2f}}")
                print(f"  Avg diff: {{sum(diffs_vals)/len(diffs_vals):.2f}}")
                for d in differences[:10]:
                    print(f"  OID {{d['oid']}}: sum={{d['sum']:.2f}}, reported={{d['reported']:.2f}}, diff={{d['diff']:.2f}}")
        else:
            print(f"Field '{{total_field}}' not found in {{fc}} — skipping comparison.")
    """)


# ─────────────────────────────────────────────────────────────────────────────
# 3g. Append to Official  (notebook Section 5.1)
# ─────────────────────────────────────────────────────────────────────────────

def script_append_to_official(p: dict) -> str:
    gdb = p.get("gdb", r"C:\Path\To\Your.gdb")
    current_qt = p.get("currentQt", "T2025_Q1")
    official_polygon = p.get("officialPolygon", "AR_Oficial_poligono_GTM")
    official_point = p.get("officialPoint", "AR_Oficial_punto_GTM")

    poly_input = f"{current_qt}_polygon_Erased_pair_micro"
    point_input = f"{current_qt}_point_cleaned_pair_micro"

    # Build field mapping string representations
    poly_fm_lines = []
    for entry in APPEND_FIELD_MAPPING_POLYGON_TEMPLATE:
        poly_fm_lines.append(f"    f'{entry}',")
    point_fm_lines = []
    for entry in APPEND_FIELD_MAPPING_POINT_TEMPLATE:
        point_fm_lines.append(f"    f'{entry}',")

    poly_fm_block = "\n".join(poly_fm_lines)
    point_fm_block = "\n".join(point_fm_lines)

    return textwrap.dedent(f"""\
        # PASO 3g: Append to Official
        # Faithful reproduction of notebook Section 5.1
        import arcpy

        gdb = r"{gdb}"
        current_qt = "{current_qt}"
        arcpy.env.workspace = gdb
        arcpy.env.overwriteOutput = True

        official_polygon = "{official_polygon}"
        official_point = "{official_point}"
        input_fc_polygon = "{poly_input}"
        input_fc_point = "{point_input}"

        # ── 5.0.1 Backup official before append ──
        arcpy.management.Copy(official_polygon, f"{{official_polygon}}_{{current_qt}}_backup")
        arcpy.management.Copy(official_point, f"{{official_point}}_{{current_qt}}_backup")
        print("Backup of official layers created.")

        # ── Pre-append stats ──
        pre_count_poly = int(arcpy.management.GetCount(official_polygon)[0]) if arcpy.Exists(official_polygon) else 0
        pre_area_poly = sum(r[0] for r in arcpy.da.SearchCursor(official_polygon, ["Area_ha"]) if r[0] is not None) if pre_count_poly > 0 else 0.0
        new_count_poly = int(arcpy.management.GetCount(input_fc_polygon)[0]) if arcpy.Exists(input_fc_polygon) else 0
        new_area_poly = sum(r[0] for r in arcpy.da.SearchCursor(input_fc_polygon, ["Area_ha"]) if r[0] is not None) if new_count_poly > 0 else 0.0

        # ── 5.1 Append Polygon ──
        input_fc = input_fc_polygon
        field_mapping_parts_polygon = [
{poly_fm_block}
        ]
        field_mapping = ";".join(field_mapping_parts_polygon)

        # Determine target
        AR_Oficial_poligono_GTM_Erased = f"{{official_polygon}}_{{current_qt}}_Erased"
        if arcpy.Exists(AR_Oficial_poligono_GTM_Erased):
            target = AR_Oficial_poligono_GTM_Erased
        elif arcpy.Exists(official_polygon):
            target = official_polygon
        else:
            print("Polygon target not found. Skipping.")
            target = None

        if target:
            arcpy.management.Append(
                inputs=input_fc,
                target=target,
                schema_type="NO_TEST",
                field_mapping=field_mapping,
                subtype="",
                expression="",
                match_fields=None,
                update_geometry="NOT_UPDATE_GEOMETRY"
            )
            print(f"Append operation completed for polygon at {{target}}")

        # ── 5.2 Append Point ──
        input_fc = input_fc_point
        field_mapping_parts_point = [
{point_fm_block}
        ]
        field_mapping = ";".join(field_mapping_parts_point)

        target = official_point
        arcpy.management.Append(
            inputs=input_fc,
            target=target,
            schema_type="NO_TEST",
            field_mapping=field_mapping,
            subtype="",
            expression="",
            match_fields=None,
            update_geometry="NOT_UPDATE_GEOMETRY"
        )
        print(f"Append operation completed for point at {{target}}")

        # ── Post-append stats ──
        post_count_poly = int(arcpy.management.GetCount(official_polygon)[0]) if arcpy.Exists(official_polygon) else 0
        post_area_poly = sum(r[0] for r in arcpy.da.SearchCursor(official_polygon, ["Area_ha"]) if r[0] is not None) if post_count_poly > 0 else 0.0
        print(f"CLEANING_STATS:append:official_polygon:before={{pre_count_poly}},{{pre_area_poly:.2f}}:after={{post_count_poly}},{{post_area_poly:.2f}}:added={{new_count_poly}},{{new_area_poly:.2f}}")
    """)


# ─────────────────────────────────────────────────────────────────────────────
# 3h. GIS vs Smartsheet Comparison  (notebook Section 6)
# ─────────────────────────────────────────────────────────────────────────────

def script_gis_vs_ss_comparison(p: dict) -> str:
    gdb = p.get("gdb", r"C:\Path\To\Your.gdb")
    official_polygon = p.get("officialPolygon", "AR_Oficial_poligono_GTM")
    ss_table = p.get("smartsheetTable", "ssheet")
    return textwrap.dedent(f"""\
        # PASO 3h: GIS vs Smartsheet Comparison
        # Faithful reproduction of notebook Section 6
        import arcpy
        import pandas as pd

        gdb = r"{gdb}"
        arcpy.env.workspace = gdb

        gis_layer = "{official_polygon}"
        ss_table = "{ss_table}"

        # ── Read GIS data ──
        gis_data = []
        fields = [f.name for f in arcpy.ListFields(gis_layer)]
        with arcpy.da.SearchCursor(gis_layer, fields) as cursor:
            for row in cursor:
                gis_data.append(dict(zip(fields, row)))
        gis_df = pd.DataFrame(gis_data)

        # ── Read Smartsheet data ──
        ss_data = []
        ss_fields = [f.name for f in arcpy.ListFields(ss_table)]
        with arcpy.da.SearchCursor(ss_table, ss_fields) as cursor:
            for row in cursor:
                ss_data.append(dict(zip(ss_fields, row)))
        ss_df = pd.DataFrame(ss_data)

        # ── Group GIS by activity code ──
        join_col = "CÓDIGO_DE_LA_ACTIVIDAD"
        if join_col in gis_df.columns and "Area_ha" in gis_df.columns:
            gis_grouped = gis_df.groupby(join_col).agg(
                Area_ha_gis=("Area_ha", "sum")
            ).reset_index()
        else:
            print(f"Required columns not found in GIS layer.")
            gis_grouped = pd.DataFrame()

        # ── Rename SS columns ──
        ss_ha_col = "TOTAL_DE_HECTÁREAS"
        if join_col in ss_df.columns and ss_ha_col in ss_df.columns:
            ss_renamed = ss_df[[join_col, ss_ha_col]].rename(columns={{ss_ha_col: "Area_ha_ss"}})
            ss_renamed = ss_renamed.groupby(join_col).agg(Area_ha_ss=("Area_ha_ss", "sum")).reset_index()
        else:
            print(f"Required columns not found in Smartsheet table.")
            ss_renamed = pd.DataFrame()

        # ── Merge and Compare ──
        if not gis_grouped.empty and not ss_renamed.empty:
            merged_df = pd.merge(gis_grouped, ss_renamed, on=join_col, suffixes=('_gis', '_ss'))
            merged_df['Areas_Equal'] = (merged_df['Area_ha_gis'].round(2) == merged_df['Area_ha_ss'].round(2))
            merged_df['diff'] = (merged_df['Area_ha_gis'] - merged_df['Area_ha_ss']).round(2)

            mismatched = merged_df[~merged_df['Areas_Equal']]
            print(f"\\nTotal compared: {{len(merged_df)}}")
            print(f"Matched: {{merged_df['Areas_Equal'].sum()}}")
            print(f"Mismatched: {{len(mismatched)}}")

            if len(mismatched) > 0:
                print(f"\\nMismatch details:")
                print(f"  Min diff: {{mismatched['diff'].min():.2f}} ha")
                print(f"  Max diff: {{mismatched['diff'].max():.2f}} ha")
                print(f"  Avg diff: {{mismatched['diff'].mean():.2f}} ha")
                print(mismatched[[join_col, 'Area_ha_gis', 'Area_ha_ss', 'diff']].to_string())

            # Completitud KPI
            ss_total = len(ss_renamed)
            gis_matched = len(merged_df)
            completitud = round(gis_matched / max(ss_total, 1) * 100, 1)
            print(f"\\nCompletitud KPI: {{completitud}}% (target >= 90%)")
            if completitud >= 90:
                print("KPI MET")
            else:
                print(f"WARNING: KPI NOT MET (gap: {{90 - completitud:.1f}}%)")
    """)


# ─────────────────────────────────────────────────────────────────────────────
# 3i. Backup and Cumulative  (notebook backup logic)
# ─────────────────────────────────────────────────────────────────────────────

def script_backup_and_cumulative(p: dict) -> str:
    gdb = p.get("gdb", r"C:\Path\To\Your.gdb")
    current_qt = p.get("currentQt", "T2025_Q1")
    official_polygon = p.get("officialPolygon", "AR_Oficial_poligono_GTM")
    official_point = p.get("officialPoint", "AR_Oficial_punto_GTM")
    return textwrap.dedent(f"""\
        # PASO 3i: Backup and Cumulative
        import arcpy

        gdb = r"{gdb}"
        current_qt = "{current_qt}"
        arcpy.env.workspace = gdb
        arcpy.env.overwriteOutput = True

        official_polygon = "{official_polygon}"
        official_point = "{official_point}"

        # ── Backup previous quarter official data ──
        backup_polygon = f"{{official_polygon}}_{{current_qt}}_backup"
        backup_point = f"{{official_point}}_{{current_qt}}_backup"

        if not arcpy.Exists(backup_polygon):
            arcpy.management.Copy(official_polygon, backup_polygon)
            print(f"Backup created: {{backup_polygon}}")
        else:
            print(f"Backup already exists: {{backup_polygon}}")

        if not arcpy.Exists(backup_point):
            arcpy.management.Copy(official_point, backup_point)
            print(f"Backup created: {{backup_point}}")
        else:
            print(f"Backup already exists: {{backup_point}}")

        # ── Verify counts ──
        poly_count = int(arcpy.management.GetCount(official_polygon)[0])
        point_count = int(arcpy.management.GetCount(official_point)[0])
        print(f"\\nCurrent official polygon count: {{poly_count}}")
        print(f"Current official point count: {{point_count}}")
        print("Backup and cumulative step completed.")
    """)


# ─────────────────────────────────────────────────────────────────────────────
# 3d-extra. Export to Excel  (notebook TableToExcel)
# ─────────────────────────────────────────────────────────────────────────────

def script_export_excel(p: dict) -> str:
    gdb = p.get("gdb", r"C:\Path\To\Your.gdb")
    fc = p.get("featureClass", "AR_Oficial_poligono_GTM")
    excel_path = p.get("excelPath", r"C:\Path\To\output.xlsx")
    return textwrap.dedent(f"""\
        # PASO 3 — Export to Excel
        import arcpy

        gdb = r"{gdb}"
        arcpy.env.workspace = gdb
        fc = "{fc}"
        excel = r"{excel_path}"

        arcpy.conversion.TableToExcel(fc, excel, "ALIAS")
        print(f"Exported {{fc}} to {{excel}}")
    """)


# ─────────────────────────────────────────────────────────────────────────────
# Script registry — maps step names to generator functions
# ─────────────────────────────────────────────────────────────────────────────

PASO3_SCRIPTS = {
    "merge_field_mapping":  script_merge_with_field_mapping,
    "overlap_analysis":     script_overlap_analysis,
    "erase_pipeline":       script_erase_pipeline,
    "spatial_join_micro":   script_spatial_join_micro,
    "duplicate_detection":  script_duplicate_detection,
    "incentive_validation": script_incentive_validation,
    "append_official":      script_append_to_official,
    "gis_vs_ss_comparison": script_gis_vs_ss_comparison,
    "backup_cumulative":    script_backup_and_cumulative,
    "export_excel":         script_export_excel,
    "overlap_pdf_report":   script_overlap_pdf_report,
}
