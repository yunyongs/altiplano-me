"""
PASO 3 — Overlap PDF Report script generator.

Generates an ArcPy script (for the ArcGIS Pro Python window) that:
  1. Runs CountOverlappingFeatures on official + current-quarter polygons
  2. Runs PairwiseIntersect to capture overlap geometry and attributes
  3. Exports the intersect result to a GDB table
  4. Uses arcpy.mp to export a layout to PDF

NOTE: arcpy is NOT available in the Flask server environment.
      This module only builds a script *string* — arcpy lives inside that string.
"""
from __future__ import annotations

import textwrap


def script_overlap_pdf_report(p: dict) -> str:
    """Generate an ArcPy script that produces an Overlap PDF report.

    Args in p:
      - official_polygon  : AR_Oficial_poligono_GTM layer path
      - current_polygon   : Merged current-quarter polygon layer path
      - output_pdf        : Output PDF file path
      - current_qt        : Quarter identifier, e.g. "T2026_Q1"
      - aprx_path         : ArcGIS Pro .aprx project file path
      - layout_name       : Layout name to export (default: "Overlap_Report")
      - gdb_path          : Scratch GDB path for intermediate outputs

    Returns:
        A complete Python script string ready to run in the ArcGIS Pro Python window.
    """
    official_polygon = p.get("official_polygon", "AR_Oficial_poligono_GTM")
    current_polygon = p.get("current_polygon", r"C:\Path\To\current_polygon")
    output_pdf = p.get("output_pdf", r"C:\Path\To\Overlap_Report.pdf")
    current_qt = p.get("current_qt", "T2026_Q1")
    aprx_path = p.get("aprx_path", r"C:\Path\To\Project.aprx")
    layout_name = p.get("layout_name", "Overlap_Report")
    gdb_path = p.get("gdb_path", r"C:\Path\To\Scratch.gdb")

    return textwrap.dedent(f"""\
        # PASO 3 — Reporte PDF de Solapamientos / Overlap PDF Report
        # Ejecutar en la ventana Python de ArcGIS Pro
        # Run in the ArcGIS Pro Python window
        import arcpy
        import os

        # ── Parámetros / Parameters ──────────────────────────────────────────
        gdb             = r"{gdb_path}"
        official_polygon = "{official_polygon}"
        current_polygon  = r"{current_polygon}"
        current_qt       = "{current_qt}"
        aprx_path        = r"{aprx_path}"
        layout_name      = "{layout_name}"
        output_pdf       = r"{output_pdf}"

        arcpy.env.workspace = gdb
        arcpy.env.overwriteOutput = True

        # Nombres de capas intermedias / Intermediate layer names
        count_ovlp_fc  = os.path.join(gdb, f"{{current_qt}}_CountOverlapping")
        intersect_fc   = os.path.join(gdb, f"{{current_qt}}_PairIntersect")
        summary_table  = os.path.join(gdb, f"{{current_qt}}_OverlapSummary")

        # ── Paso 1: CountOverlappingFeatures ─────────────────────────────────
        # ES: Cuenta features que se solapan entre la capa oficial y la del trimestre actual
        # EN: Count features overlapping between the official layer and the current-quarter layer
        print("Ejecutando CountOverlappingFeatures / Running CountOverlappingFeatures...")
        arcpy.analysis.CountOverlappingFeatures(
            in_features=[official_polygon, current_polygon],
            out_feature_class=count_ovlp_fc,
            min_overlap_count=2,
            out_overlap_table=None,
        )
        print(f"  → {{count_ovlp_fc}}")

        # ── Paso 2: PairwiseIntersect ─────────────────────────────────────────
        # ES: Genera polígonos de solapamiento con atributos de ambas capas
        # EN: Generate overlap polygons with attributes from both layers
        print("Ejecutando PairwiseIntersect / Running PairwiseIntersect...")
        arcpy.analysis.PairwiseIntersect(
            in_features=[official_polygon, current_polygon],
            out_feature_class=intersect_fc,
            join_attributes="ALL",
            cluster_tolerance=None,
            output_type="INPUT",
        )
        print(f"  → {{intersect_fc}}")

        # ── Paso 3: Extraer campos relevantes / Extract relevant fields ───────
        # ES: CdgActvdd, ACCIONES_DE_RESTAURACION_AbE, Area_ha, Shape_Type
        # EN: Read overlap records for the report table
        print("Extrayendo datos de solapamiento / Extracting overlap data...")
        overlap_rows = []
        fields_to_read = ["CdgActvdd", "ACCIONES_DE_RESTAURACION_AbE", "Area_ha", "SHAPE@TYPE"]
        available_fields = [f.name for f in arcpy.ListFields(intersect_fc)]

        read_fields = []
        for fld in fields_to_read:
            if fld in available_fields:
                read_fields.append(fld)
            else:
                print(f"  [!]  Campo no encontrado / Field not found: {{fld}}")

        if read_fields:
            with arcpy.da.SearchCursor(intersect_fc, read_fields) as cursor:
                for row in cursor:
                    row_dict = dict(zip(read_fields, row))
                    # ES: Segundo segmento de CdgActvdd es el componente (C1/C2/C3)
                    # EN: Second segment of CdgActvdd identifies the component
                    cdg = row_dict.get("CdgActvdd", "")
                    parts = cdg.split("_") if cdg else []
                    component = parts[1] if len(parts) > 1 else "N/A"
                    overlap_rows.append({{
                        "CdgActvdd": cdg,
                        "AbE_type": row_dict.get("ACCIONES_DE_RESTAURACION_AbE", ""),
                        "Component": component,
                        "Geom_type": row_dict.get("SHAPE@TYPE", ""),
                        "Area_ha": round(row_dict.get("Area_ha", 0) or 0, 4),
                    }})

        total_overlaps = len(overlap_rows)
        print(f"  → {{total_overlaps}} solapamiento(s) encontrado(s) / overlap(s) found")

        # Resumen por consola / Console summary
        print("\\n── Tabla de solapamientos / Overlap table ──────────────────────")
        print(f"  {{\'AbE\':<40}} {{\'Comp\':<5}} {{\'Geometría\':<10}} {{\'Área (ha)\':<12}}")
        print("  " + "-" * 70)
        for r in overlap_rows:
            print(f"  {{r[\'AbE_type\']:<40}} {{r[\'Component\']:<5}} {{r[\'Geom_type\']:<10}} {{r[\'Area_ha\']:<12}}")
        print()

        # ── Paso 4: Exportar tabla resumen / Export summary table ─────────────
        # ES: Guarda los resultados en una tabla GDB para referencia futura
        # EN: Save results to a GDB table for future reference
        print("Exportando tabla resumen / Exporting summary table...")
        arcpy.conversion.ExportTable(
            in_table=intersect_fc,
            out_table=summary_table,
            where_clause=None,
            use_field_alias_as_name="NOT_USE_ALIAS",
            field_mapping=None,
        )
        print(f"  → {{summary_table}}")

        # ── Paso 5: Exportar PDF desde Layout / Export PDF from Layout ────────
        # ES: Usa el Layout del proyecto .aprx para generar el PDF del reporte
        # EN: Use the .aprx project Layout to generate the report PDF
        print("Exportando PDF / Exporting PDF...")
        aprx = arcpy.mp.ArcGISProject(aprx_path)
        layouts = aprx.listLayouts(layout_name)

        if not layouts:
            print(f"  [X] Layout '{{layout_name}}' no encontrado en {{aprx_path}}")
            print("     Layouts disponibles / Available layouts:")
            for lyt in aprx.listLayouts():
                print(f"       - {{lyt.name}}")
        else:
            layout = layouts[0]
            layout.exportToPDF(output_pdf, resolution=150, image_quality="BETTER")
            print(f"  [OK] PDF exportado / PDF exported: {{output_pdf}}")

        # ── Resumen final / Final summary ──────────────────────────────────────
        print()
        print("═" * 60)
        print(f"Trimestre / Quarter : {{current_qt}}")
        print(f"Solapamientos total / Total overlaps: {{total_overlaps}}")
        print(f"Tabla resumen / Summary table : {{summary_table}}")
        print(f"PDF exportado / PDF exported  : {{output_pdf}}")
        print("═" * 60)
    """)
