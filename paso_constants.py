"""
Field mapping constants and naming conventions extracted from the production
notebooks.  These constants are consumed by the ArcPy script generators
(paso3_scripts, paso4_scripts) so the generated scripts faithfully reproduce
the notebook workflow.

Source notebooks (read-only, NEVER modify):
  - 02_ArcGIS_MapUpdater/2_2_AR_Oficial_ArcPy.ipynb
  - 01_Ssheet_DataCollect/1_1_AR_Ssheet_Automation.ipynb
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# 1. Merge field details  (notebook Section 1.3)
#    Used by create_field_mapping_string() for arcpy.management.Merge
# ---------------------------------------------------------------------------

FIELD_DETAILS_POINT: dict[str, dict] = {
    "Area_ha":    {"type": "Double", "length": 19},
    "CdgActvdd":  {"type": "Text",   "length": 254},
    "Agrupados":  {"type": "Text",   "length": 254, "nullable": True},
    "NumPrclBnf": {"type": "Short",  "length": 0,   "nullable": True},
}

FIELD_DETAILS_POLYGON: dict[str, dict] = {
    "CdgActvdd":  {"type": "Text",  "length": 254},
    "Agrupados":  {"type": "Text",  "length": 254, "nullable": True},
    "NumPrclBnf": {"type": "Short", "length": 0,   "nullable": True},
}


# ---------------------------------------------------------------------------
# 2. Append field mapping templates  (notebook Section 5.1)
#    {input_fc} is replaced at script-generation time with the actual FC name
# ---------------------------------------------------------------------------

# 40-field mapping for Polygon Append to Official
APPEND_FIELD_MAPPING_POLYGON_TEMPLATE: list[str] = [
    'Area_ha "Area_ha" true true false 8 Double 0 0,First,#,{input_fc},Area_ha,-1,-1',
    'CdgActvdd "CdgActvdd" true true false 255 Text 0 0,First,#,{input_fc},CdgActvdd,0,253',
    'AbE_ENG "AbE_ENG" true true false 8000 Text 0 0,First,#',
    'OUTPUT "OUTPUT" true true false 512 Text 0 0,First,#,{input_fc},OUTPUT,0,254',
    'TRATAMIENTO_OLD "TRATAMIENTO_OLD" true true false 512 Text 0 0,First,#',
    'DEPT_ID "DEPT_ID" true true false 5 Text 0 0,First,#,{input_fc},DEPT_ID,-1,-1',
    'MUNI_ID "MUNI_ID" true true false 5 Text 0 0,First,#,{input_fc},MUNI_ID,-1,-1',
    'MUNI_NOMBRE "MUNI_NOMBRE" true true false 75 Text 0 0,First,#,{input_fc},MUNI_NOMBRE,0,74',
    'DEPTO_NOMBRE "DEPTO_NOMBRE" true true false 50 Text 0 0,First,#,{input_fc},DEPTO_NOMBRE,0,49',
    'MICRO_NOMBRE "MICRO_NOMBRE" true true false 50 Text 0 0,First,#,{input_fc},MICRO_NOMBRE,0,49',
    'CUENCA_NOMBRE "CUENCA_NOMBRE" true true false 50 Text 0 0,First,#,{input_fc},CUENCA_NOMBRE,0,49',
    'MICRO_HA "MICRO_HA" true true false 8 Double 0 0,First,#,{input_fc},MICRO_HA,-1,-1',
    'MICRO_ID "MICRO_ID" true true false 8 Double 0 0,First,#,{input_fc},MICRO_ID,-1,-1',
    'AREA_TYPE_1_ESP "TIPO_DE_AREA_1" true true false 254 Text 0 0,First,#,{input_fc},AREA_TYPE_1_ESP,0,253',
    'AREA_TYPE_2_ESP "TIPO_DE_AREA_2" true true false 255 Text 0 0,First,#,{input_fc},AREA_TYPE_2_ESP,0,254',
    'AREA_TYPE_1_ENG "TIPO_DE_AREA_1_ENG" true true false 255 Text 0 0,First,#,{input_fc},AREA_TYPE_1_ENG,0,254',
    'AREA_TYPE_2_ENG "TIPO_DE_AREA_2_ENG" true true false 255 Text 0 0,First,#,{input_fc},AREA_TYPE_2_ENG,0,254',
    'CUENCA_ID "CUENCA_ID" true true false 2 Short 0 0,First,#,{input_fc},CUENCA_ID,-1,-1',
    'AREA_ID "AREA_ID" true true false 2 Short 0 0,First,#,{input_fc},AREA_ID,-1,-1',
    'TRATAMIENTO "TRATAMIENTO" true true false 512 Text 0 0,First,#,{input_fc},TRATAMIENTO,0,511',
    'MICRO_ID_UNIQ "MICRO_ID_UNIQ" true true false 2 Short 0 0,First,#,{input_fc},MICRO_ID_UNIQ,-1,-1',
    'MICRO_NOMBRE_OLD "MICRO_NOMBRE_OLD" true true false 512 Text 0 0,First,#',
    'Shp_x_center "Shp_x_center" true true false 8 Double 0 0,First,#,{input_fc},Shp_x_center,-1,-1',
    'Shp_y_center "Shp_y_center" true true false 8 Double 0 0,First,#,{input_fc},Shp_y_center,-1,-1',
    'MICRO_Centroid_X "MICRO_Centroid_X" true true false 8 Double 0 0,First,#,{input_fc},MICRO_Centroid_X,-1,-1',
    'MICRO_Centroid_Y "MICRO_Centroid_Y" true true false 8 Double 0 0,First,#,{input_fc},MICRO_Centroid_Y,-1,-1',
    'FECHA_DE_LA_ACTIVIDAD "FECHA DE LA ACTIVIDAD" true true false 8 Date 0 0,First,#,{input_fc},FECHA_DE_LA_ACTIVIDAD,-1,-1',
    'CÓDIGO_DE_LA_ACTIVIDAD "CÓDIGO DE LA ACTIVIDAD" true true false 8000 Text 0 0,First,#,{input_fc},CÓDIGO_DE_LA_ACTIVIDAD,0,7999',
    'NOMBRE_DE_LA_ACTIVIDAD "NOMBRE DE LA ACTIVIDAD" true true false 8000 Text 0 0,First,#,{input_fc},NOMBRE_DE_LA_ACTIVIDAD,0,7999',
    'ACCIONES_DE_RESTAURACIÓN_AbE "ACCIONES DE RESTAURACIÓN AbE" true true false 8000 Text 0 0,First,#,{input_fc},ACCIONES_DE_RESTAURACIÓN_AbE,0,7999',
    'TIPO_DE_BOSQUE "TIPO DE BOSQUE" true true false 8000 Text 0 0,First,#,{input_fc},TIPO_DE_BOSQUE,0,7999',
    'TOTAL_DE_HECTÁREAS "TOTAL DE HECTÁREAS" true true false 8 Double 0 0,First,#,{input_fc},TOTAL_DE_HECTÁREAS,-1,-1',
    'COUNTRY "COUNTRY" true true false 512 Text 0 0,First,#,{input_fc},COUNTRY,0,253',
    'NÚMERO_DE_CONTRATO "NÚMERO DE CONTRATO" true true false 8000 Text 0 0,First,#,{input_fc},NÚMERO_DE_CONTRATO,0,7999',
    'ORGANIZACIÓN "ORGANIZACIÓN" true true false 8000 Text 0 0,First,#,{input_fc},ORGANIZACIÓN,0,7999',
    'Revision "Revision" true true false 512 Text 0 0,First,#',
    'Calidad_SIG "Calidad SIG" true true false 512 Text 0 0,First,#,{input_fc},Calidad_SIG,0,7999',
    'Agrupado "Agrupado" true true false 512 Text 0 0,First,#,{input_fc},Agrupados,0,253',
    'Num_Parcelas "Num_Parcelas" true true false 2 Short 0 0,First,#,{input_fc},NumPrclBnf,-1,-1',
]

# Point Append to Official — same structure, different source variable
APPEND_FIELD_MAPPING_POINT_TEMPLATE: list[str] = [
    'Area_ha "Area_ha" true true false 8 Double 0 0,First,#,{input_fc},Area_ha,-1,-1',
    'CdgActvdd "CdgActvdd" true true false 255 Text 0 0,First,#,{input_fc},CdgActvdd,0,253',
    'AbE_ENG "AbE_ENG" true true false 8000 Text 0 0,First,#',
    'OUTPUT "OUTPUT" true true false 512 Text 0 0,First,#,{input_fc},OUTPUT,0,254',
    'TRATAMIENTO_OLD "TRATAMIENTO_OLD" true true false 512 Text 0 0,First,#',
    'DEPT_ID "DEPT_ID" true true false 5 Text 0 0,First,#,{input_fc},DEPT_ID,-1,-1',
    'MUNI_ID "MUNI_ID" true true false 5 Text 0 0,First,#,{input_fc},MUNI_ID,-1,-1',
    'MUNI_NOMBRE "MUNI_NOMBRE" true true false 75 Text 0 0,First,#,{input_fc},MUNI_NOMBRE,0,74',
    'DEPTO_NOMBRE "DEPTO_NOMBRE" true true false 50 Text 0 0,First,#,{input_fc},DEPTO_NOMBRE,0,49',
    'MICRO_NOMBRE "MICRO_NOMBRE" true true false 50 Text 0 0,First,#,{input_fc},MICRO_NOMBRE,0,49',
    'CUENCA_NOMBRE "CUENCA_NOMBRE" true true false 50 Text 0 0,First,#,{input_fc},CUENCA_NOMBRE,0,49',
    'MICRO_HA "MICRO_HA" true true false 8 Double 0 0,First,#,{input_fc},MICRO_HA,-1,-1',
    'MICRO_ID "MICRO_ID" true true false 8 Double 0 0,First,#,{input_fc},MICRO_ID,-1,-1',
    'AREA_TYPE_1_ESP "TIPO_DE_AREA_1" true true false 254 Text 0 0,First,#,{input_fc},AREA_TYPE_1_ESP,0,253',
    'AREA_TYPE_2_ESP "TIPO_DE_AREA_2" true true false 255 Text 0 0,First,#,{input_fc},AREA_TYPE_2_ESP,0,254',
    'AREA_TYPE_1_ENG "TIPO_DE_AREA_1_ENG" true true false 255 Text 0 0,First,#,{input_fc},AREA_TYPE_1_ENG,0,254',
    'AREA_TYPE_2_ENG "TIPO_DE_AREA_2_ENG" true true false 255 Text 0 0,First,#,{input_fc},AREA_TYPE_2_ENG,0,254',
    'CUENCA_ID "CUENCA_ID" true true false 2 Short 0 0,First,#,{input_fc},CUENCA_ID,-1,-1',
    'AREA_ID "AREA_ID" true true false 2 Short 0 0,First,#,{input_fc},AREA_ID,-1,-1',
    'TRATAMIENTO "TRATAMIENTO" true true false 512 Text 0 0,First,#,{input_fc},TRATAMIENTO,0,511',
    'MICRO_ID_UNIQ "MICRO_ID_UNIQ" true true false 2 Short 0 0,First,#,{input_fc},MICRO_ID_UNIQ,-1,-1',
    'MICRO_NOMBRE_OLD "MICRO_NOMBRE_OLD" true true false 512 Text 0 0,First,#',
    'Shp_x_center "Shp_x_center" true true false 8 Double 0 0,First,#,{input_fc},Shp_x_center,-1,-1',
    'Shp_y_center "Shp_y_center" true true false 8 Double 0 0,First,#,{input_fc},Shp_y_center,-1,-1',
    'MICRO_Centroid_X "MICRO_Centroid_X" true true false 8 Double 0 0,First,#,{input_fc},MICRO_Centroid_X,-1,-1',
    'MICRO_Centroid_Y "MICRO_Centroid_Y" true true false 8 Double 0 0,First,#,{input_fc},MICRO_Centroid_Y,-1,-1',
    'FECHA_DE_LA_ACTIVIDAD "FECHA DE LA ACTIVIDAD" true true false 8 Date 0 0,First,#,{input_fc},FECHA_DE_LA_ACTIVIDAD,-1,-1',
    'CÓDIGO_DE_LA_ACTIVIDAD "CÓDIGO DE LA ACTIVIDAD" true true false 8000 Text 0 0,First,#,{input_fc},CÓDIGO_DE_LA_ACTIVIDAD,0,7999',
    'NOMBRE_DE_LA_ACTIVIDAD "NOMBRE DE LA ACTIVIDAD" true true false 8000 Text 0 0,First,#,{input_fc},NOMBRE_DE_LA_ACTIVIDAD,0,7999',
    'ACCIONES_DE_RESTAURACIÓN_AbE "ACCIONES DE RESTAURACIÓN AbE" true true false 8000 Text 0 0,First,#,{input_fc},ACCIONES_DE_RESTAURACIÓN_AbE,0,7999',
    'TIPO_DE_BOSQUE "TIPO DE BOSQUE" true true false 8000 Text 0 0,First,#,{input_fc},TIPO_DE_BOSQUE,0,7999',
    'TOTAL_DE_HECTÁREAS "TOTAL DE HECTÁREAS" true true false 8 Double 0 0,First,#,{input_fc},TOTAL_DE_HECTÁREAS,-1,-1',
    'COUNTRY "COUNTRY" true true false 512 Text 0 0,First,#,{input_fc},COUNTRY,0,253',
    'NÚMERO_DE_CONTRATO "NÚMERO DE CONTRATO" true true false 8000 Text 0 0,First,#,{input_fc},NÚMERO_DE_CONTRATO,0,7999',
    'ORGANIZACIÓN "ORGANIZACIÓN" true true false 8000 Text 0 0,First,#,{input_fc},ORGANIZACIÓN,0,7999',
    'Revision "Revision" true true false 512 Text 0 0,First,#',
    'Calidad_SIG "Calidad SIG" true true false 512 Text 0 0,First,#,{input_fc},Calidad_SIG,0,7999',
    'Agrupado "Agrupado" true true false 512 Text 0 0,First,#,{input_fc},Agrupados,0,253',
    'Num_Parcelas "Num_Parcelas" true true false 2 Short 0 0,First,#,{input_fc},NumPrclBnf,-1,-1',
]


# ---------------------------------------------------------------------------
# 3. WFL (ArcGIS Online) Append field mappings  (notebook Section 7)
#    {gdb_path} is replaced with the actual GDB path at generation time
# ---------------------------------------------------------------------------

# Template parts for WFL Point Append — each entry is "field_spec,source"
# The notebook hardcodes the full GDB path; we parameterise it as {gdb_path}
WFL_FIELD_MAPPING_POINT: list[dict] = [
    {"field": "CdgActvdd",  "alias": "CdgActvdd",  "length": 255, "type": "Text",   "src": "CdgActvdd",  "range": "0,254"},
    {"field": "OUTPUT",     "alias": "OUTPUT",      "length": 512, "type": "Text",   "src": "OUTPUT",     "range": "0,511"},
    {"field": "Area_ha",    "alias": "Area_ha",     "length": 0,   "type": "Double", "src": "Area_ha",    "range": "-1,-1"},
    {"field": "MICRO_ID",   "alias": "MICRO_ID",    "length": 0,   "type": "Double", "src": "MICRO_ID",   "range": "-1,-1"},
    {"field": "MICRO_NOMBRE", "alias": "MICRO_NOMBRE", "length": 50, "type": "Text", "src": "MICRO_NOMBRE", "range": "0,49"},
    {"field": "CUENCA_NOMBRE", "alias": "CUENCA_NOMBRE", "length": 50, "type": "Text", "src": "CUENCA_NOMBRE", "range": "0,49"},
    {"field": "AREA_TYPE_1_ESP", "alias": "TIPO_DE_AREA_1", "length": 254, "type": "Text", "src": "AREA_TYPE_1_ESP", "range": "0,253"},
    {"field": "AREA_TYPE_2_ESP", "alias": "TIPO_DE_AREA_2", "length": 255, "type": "Text", "src": "AREA_TYPE_2_ESP", "range": "0,254"},
    {"field": "TRATAMIENTO", "alias": "TRATAMIENTO", "length": 512, "type": "Text", "src": "TRATAMIENTO", "range": "0,511"},
    {"field": "MUNI_NOMBRE", "alias": "MUNI_NOMBRE", "length": 75, "type": "Text", "src": "MUNI_NOMBRE", "range": "0,74"},
    {"field": "DEPTO_NOMBRE", "alias": "DEPTO_NOMBRE", "length": 50, "type": "Text", "src": "DEPTO_NOMBRE", "range": "0,49"},
    {"field": "AbE_ENG",    "alias": "AbE_ENG",     "length": 8000, "type": "Text",  "src": "AbE_ENG",    "range": "0,7999"},
    {"field": "FECHA_DE_LA_ACTIVIDAD", "alias": "FECHA DE LA ACTIVIDAD", "length": 8, "type": "Date", "src": "FECHA_DE_LA_ACTIVIDAD", "range": "-1,-1"},
    {"field": "NOMBRE_DE_LA_ACTIVIDAD", "alias": "NOMBRE DE LA ACTIVIDAD", "length": 8000, "type": "Text", "src": "NOMBRE_DE_LA_ACTIVIDAD", "range": "0,7999"},
    {"field": "ACCIONES_DE_RESTAURACIÓN_AbE", "alias": "ACCIONES DE RESTAURACIÓN AbE", "length": 8000, "type": "Text", "src": "ACCIONES_DE_RESTAURACIÓN_AbE", "range": "0,7999"},
    {"field": "TIPO_DE_BOSQUE", "alias": "TIPO DE BOSQUE", "length": 8000, "type": "Text", "src": "TIPO_DE_BOSQUE", "range": "0,7999"},
    {"field": "TOTAL_DE_HECTÁREAS", "alias": "TOTAL DE HECTÁREAS", "length": 0, "type": "Double", "src": "TOTAL_DE_HECTÁREAS", "range": "-1,-1"},
    {"field": "NÚMERO_DE_CONTRATO", "alias": "NÚMERO DE CONTRATO", "length": 8000, "type": "Text", "src": "NÚMERO_DE_CONTRATO", "range": "0,7999"},
    {"field": "ORGANIZACIÓN", "alias": "ORGANIZACIÓN", "length": 8000, "type": "Text", "src": "ORGANIZACIÓN", "range": "0,7999"},
    {"field": "MICRO_ID_UNIQ", "alias": "MICRO_ID_UNIQ", "length": 0, "type": "Short", "src": "MICRO_ID_UNIQ", "range": "-1,-1"},
    {"field": "MICRO_HA",  "alias": "MICRO_HA",    "length": 0,   "type": "Double", "src": "MICRO_HA",   "range": "-1,-1"},
    {"field": "MICRO_Centroid_X", "alias": "MICRO_Centroid_X", "length": 0, "type": "Double", "src": "MICRO_Centroid_X", "range": "-1,-1"},
    {"field": "MICRO_Centroid_Y", "alias": "MICRO_Centroid_Y", "length": 0, "type": "Double", "src": "MICRO_Centroid_Y", "range": "-1,-1"},
    {"field": "CUENCA_ID", "alias": "CUENCA_ID",   "length": 0,   "type": "Short",  "src": "CUENCA_ID",  "range": "-1,-1"},
    {"field": "AREA_ID",   "alias": "AREA_ID",     "length": 0,   "type": "Short",  "src": "AREA_ID",    "range": "-1,-1"},
    {"field": "AREA_TYPE_1_ENG", "alias": "TIPO_DE_AREA_1_ENG", "length": 255, "type": "Text", "src": "AREA_TYPE_1_ENG", "range": "0,254"},
    {"field": "AREA_TYPE_2_ENG", "alias": "TIPO_DE_AREA_2_ENG", "length": 255, "type": "Text", "src": "AREA_TYPE_2_ENG", "range": "0,254"},
    {"field": "MUNI_ID",   "alias": "MUNI_ID",     "length": 5,   "type": "Text",   "src": "MUNI_ID",    "range": "0,4"},
    {"field": "DEPT_ID",   "alias": "DEPT_ID",     "length": 5,   "type": "Text",   "src": "DEPT_ID",    "range": "0,4"},
    {"field": "COUNTRY",   "alias": "COUNTRY",     "length": 512, "type": "Text",   "src": "COUNTRY",    "range": "0,511"},
    {"field": "Shp_x_center", "alias": "Shp_x_center", "length": 0, "type": "Double", "src": "Shp_x_center", "range": "-1,-1"},
    {"field": "Shp_y_center", "alias": "Shp_y_center", "length": 0, "type": "Double", "src": "Shp_y_center", "range": "-1,-1"},
    {"field": "CÓDIGO_DE_LA_ACTIVIDAD", "alias": "CÓDIGO DE LA ACTIVIDAD", "length": 8000, "type": "Text", "src": "CÓDIGO_DE_LA_ACTIVIDAD", "range": "0,7999"},
    {"field": "Agupados",  "alias": "Agupados",    "length": 512, "type": "Text",   "src": "Agupados",   "range": "0,511"},
    {"field": "Num_Parcelas", "alias": "Num_Parcelas", "length": 0, "type": "Short", "src": "Num_Parcelas", "range": "-1,-1"},
    {"field": "Shapes",    "alias": "Shapes",      "length": 512, "type": "Text",   "src": "Shapes",     "range": "0,511"},
    {"field": "buffer_m",  "alias": "buffer_m",    "length": 0,   "type": "Double", "src": "buffer_m",   "range": "-1,-1"},
]

# WFL Polygon Append — similar fields, slightly different order
WFL_FIELD_MAPPING_POLYGON: list[dict] = [
    {"field": "CdgActvdd", "alias": "CdgActvdd", "length": 255, "type": "Text", "src": "CdgActvdd", "range": "0,254"},
    {"field": "OUTPUT", "alias": "OUTPUT", "length": 512, "type": "Text", "src": "OUTPUT", "range": "0,511"},
    {"field": "ORGANIZACIÓN", "alias": "ORGANIZACIÓN", "length": 8000, "type": "Text", "src": "ORGANIZACIÓN", "range": "0,7999"},
    {"field": "Area_ha", "alias": "Area_ha", "length": 0, "type": "Double", "src": "Area_ha", "range": "-1,-1"},
    {"field": "ACCIONES_DE_RESTAURACIÓN_AbE", "alias": "ACCIONES DE RESTAURACIÓN AbE", "length": 8000, "type": "Text", "src": "ACCIONES_DE_RESTAURACIÓN_AbE", "range": "0,7999"},
    {"field": "AbE_ENG", "alias": "AbE_ENG", "length": 8000, "type": "Text", "src": "AbE_ENG", "range": "0,7999"},
    {"field": "DEPT_ID", "alias": "DEPT_ID", "length": 5, "type": "Text", "src": "DEPT_ID", "range": "0,4"},
    {"field": "MUNI_ID", "alias": "MUNI_ID", "length": 5, "type": "Text", "src": "MUNI_ID", "range": "0,4"},
    {"field": "MUNI_NOMBRE", "alias": "MUNI_NOMBRE", "length": 75, "type": "Text", "src": "MUNI_NOMBRE", "range": "0,74"},
    {"field": "DEPTO_NOMBRE", "alias": "DEPTO_NOMBRE", "length": 50, "type": "Text", "src": "DEPTO_NOMBRE", "range": "0,49"},
    {"field": "MICRO_NOMBRE", "alias": "MICRO_NOMBRE", "length": 50, "type": "Text", "src": "MICRO_NOMBRE", "range": "0,49"},
    {"field": "CUENCA_NOMBRE", "alias": "CUENCA_NOMBRE", "length": 50, "type": "Text", "src": "CUENCA_NOMBRE", "range": "0,49"},
    {"field": "MICRO_HA", "alias": "MICRO_HA", "length": 0, "type": "Double", "src": "MICRO_HA", "range": "-1,-1"},
    {"field": "MICRO_ID", "alias": "MICRO_ID", "length": 0, "type": "Double", "src": "MICRO_ID", "range": "-1,-1"},
    {"field": "AREA_TYPE_1_ESP", "alias": "TIPO_DE_AREA_1", "length": 254, "type": "Text", "src": "AREA_TYPE_1_ESP", "range": "0,253"},
    {"field": "AREA_TYPE_2_ESP", "alias": "TIPO_DE_AREA_2", "length": 255, "type": "Text", "src": "AREA_TYPE_2_ESP", "range": "0,254"},
    {"field": "AREA_TYPE_1_ENG", "alias": "TIPO_DE_AREA_1_ENG", "length": 255, "type": "Text", "src": "AREA_TYPE_1_ENG", "range": "0,254"},
    {"field": "AREA_TYPE_2_ENG", "alias": "TIPO_DE_AREA_2_ENG", "length": 255, "type": "Text", "src": "AREA_TYPE_2_ENG", "range": "0,254"},
    {"field": "CUENCA_ID", "alias": "CUENCA_ID", "length": 0, "type": "Short", "src": "CUENCA_ID", "range": "-1,-1"},
    {"field": "AREA_ID", "alias": "AREA_ID", "length": 0, "type": "Short", "src": "AREA_ID", "range": "-1,-1"},
    {"field": "TRATAMIENTO", "alias": "TRATAMIENTO", "length": 512, "type": "Text", "src": "TRATAMIENTO", "range": "0,511"},
    {"field": "MICRO_ID_UNIQ", "alias": "MICRO_ID_UNIQ", "length": 0, "type": "Short", "src": "MICRO_ID_UNIQ", "range": "-1,-1"},
    {"field": "Shp_x_center", "alias": "Shp_x_center", "length": 0, "type": "Double", "src": "Shp_x_center", "range": "-1,-1"},
    {"field": "Shp_y_center", "alias": "Shp_y_center", "length": 0, "type": "Double", "src": "Shp_y_center", "range": "-1,-1"},
    {"field": "MICRO_Centroid_X", "alias": "MICRO_Centroid_X", "length": 0, "type": "Double", "src": "MICRO_Centroid_X", "range": "-1,-1"},
    {"field": "MICRO_Centroid_Y", "alias": "MICRO_Centroid_Y", "length": 0, "type": "Double", "src": "MICRO_Centroid_Y", "range": "-1,-1"},
    {"field": "FECHA_DE_LA_ACTIVIDAD", "alias": "FECHA DE LA ACTIVIDAD", "length": 8, "type": "Date", "src": "FECHA_DE_LA_ACTIVIDAD", "range": "-1,-1"},
    {"field": "CÓDIGO_DE_LA_ACTIVIDAD", "alias": "CÓDIGO DE LA ACTIVIDAD", "length": 8000, "type": "Text", "src": "CÓDIGO_DE_LA_ACTIVIDAD", "range": "0,7999"},
    {"field": "NOMBRE_DE_LA_ACTIVIDAD", "alias": "NOMBRE DE LA ACTIVIDAD", "length": 8000, "type": "Text", "src": "NOMBRE_DE_LA_ACTIVIDAD", "range": "0,7999"},
    {"field": "TIPO_DE_BOSQUE", "alias": "TIPO DE BOSQUE", "length": 8000, "type": "Text", "src": "TIPO_DE_BOSQUE", "range": "0,7999"},
    {"field": "TOTAL_DE_HECTÁREAS", "alias": "TOTAL DE HECTÁREAS", "length": 0, "type": "Double", "src": "TOTAL_DE_HECTÁREAS", "range": "-1,-1"},
    {"field": "COUNTRY", "alias": "COUNTRY", "length": 512, "type": "Text", "src": "COUNTRY", "range": "0,511"},
    {"field": "NÚMERO_DE_CONTRATO", "alias": "NÚMERO DE CONTRATO", "length": 8000, "type": "Text", "src": "NÚMERO_DE_CONTRATO", "range": "0,7999"},
    {"field": "Shapes", "alias": "Shapes", "length": 512, "type": "Text", "src": "Shapes", "range": "0,511"},
    {"field": "Agrupado", "alias": "Agrupado", "length": 512, "type": "Text", "src": "Agrupado", "range": "0,511"},
    {"field": "Num_Parcelas", "alias": "Num_Parcelas", "length": 0, "type": "Short", "src": "Num_Parcelas", "range": "-1,-1"},
]


# ---------------------------------------------------------------------------
# 4. Erase criteria fields  (notebook Section 2.2.3)
# ---------------------------------------------------------------------------

ERASE_CURSOR_FIELDS: list[str] = [
    "OBJECTID",
    "oficial_OUTPUT",
    "OUTPUT",
    "oficial_ACCIONES_DE_RESTAURACIÓN_AbE",
    "ACCIONES_DE_RESTAURACIÓN_AbE",
    "Area_ha_Overlapping",
    "Erase_FC",
    "Erase_Rule",
]


# ---------------------------------------------------------------------------
# 5. Incentive MONTO yearly fields  (notebook validation section)
# ---------------------------------------------------------------------------

MONTO_YEARLY_FIELDS: list[str] = [
    "F2020___MONTO_DEL_INCENTIVO__QQ_",
    "F2021___MONTO_DEL_INCENTIVO__QQ_",
    "F2022___MONTO_DEL_INCENTIVO__QQ_",
    "F2023___MONTO_DEL_INCENTIVO__QQ_",
    "F2024___MONTO_DEL_INCENTIVO__QQ_",
    "F2025___MONTO_DEL_INCENTIVO__QQ_",
    "F2026___MONTO_DEL_INCENTIVO__QQ_",
]


# ---------------------------------------------------------------------------
# 6. Official layer names
# ---------------------------------------------------------------------------

OFFICIAL_POLYGON = "AR_Oficial_poligono_GTM"
OFFICIAL_POINT = "AR_Oficial_punto_GTM"
OFFICIAL_GDB = "AR_Oficial_Acumulado.gdb"
QUARTERLY_GDB = "AR_Quarterly_Partial.gdb"

WFL_POINT = r"Oficial_WFL\AR_Oficial_punto_GTM_WFL"
WFL_POLYGON = r"Oficial_WFL\AR_Oficial_poligono_GTM_WFL"
GDB_POINT = r"Oficial_GDB\AR_Oficial_punto_GTM_GDB"
GDB_POLYGON = r"Oficial_GDB\AR_Oficial_poligono_GTM_GDB"

BASE_MICRO_MUNI = "BASE_Micro_MUNI"


# ---------------------------------------------------------------------------
# 7. Smartsheet column names used across the pipeline
# ---------------------------------------------------------------------------

SS_COL_ACTIVITY_CODE = "CÓDIGO DE LA ACTIVIDAD"
SS_COL_ACTIVITY_DATE = "FECHA DE LA ACTIVIDAD"
SS_COL_REPORTER = "NOMBRE DE QUIEN REPORTA"
SS_COL_ORG = "ORGANIZACIÓN"
SS_COL_CONTRACT = "NÚMERO DE CONTRATO"
SS_COL_QUARTER = "TRIMESTRE QUE REPORTA"
SS_COL_TOTAL_HA = "TOTAL DE HECTÁREAS"
SS_COL_CALIDAD_SIG = "Calidad SIG"
SS_COL_ABE = "ACCIONES DE RESTAURACIÓN AbE"


# ---------------------------------------------------------------------------
# 8. GTM Projected Coordinate System (used in CalculateGeometryAttributes)
# ---------------------------------------------------------------------------

GTM_WKT = (
    'PROJCS["GTM",GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",'
    'SPHEROID["WGS_1984",6378137.0,298.257223563]],'
    'PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],'
    'PROJECTION["Transverse_Mercator"],'
    'PARAMETER["False_Easting",500000.0],'
    'PARAMETER["False_Northing",0.0],'
    'PARAMETER["Central_Meridian",-90.5],'
    'PARAMETER["Scale_Factor",0.9998],'
    'PARAMETER["Latitude_Of_Origin",0.0],'
    'UNIT["Meter",1.0]]'
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def build_wfl_field_mapping(fields: list[dict], gdb_fc_path: str) -> str:
    """Build a WFL Append field_mapping string from structured field defs."""
    parts = []
    for f in fields:
        nullable = "true" if f["type"] != "GlobalID" else "false"
        base = (
            f'{f["field"]} "{f["alias"]}" {nullable} {nullable} false '
            f'{f["length"]} {f["type"]} 0 0,First,#'
        )
        src = f",{gdb_fc_path},{f['src']},{f['range']}"
        parts.append(base + src)
    return ";".join(parts)


def build_append_field_mapping(template: list[str], input_fc: str) -> str:
    """Render an Append field mapping template with the actual input FC path."""
    rendered = [entry.replace("{input_fc}", input_fc) for entry in template]
    return ";".join(rendered)


def quarter_name(year: int, quarter: int) -> str:
    """Return the standard quarter naming convention, e.g. T2025_Q3."""
    return f"T{year}_Q{quarter}"
