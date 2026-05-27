# Pipeline de Actualización de Power BI / Power BI Refresh Pipeline

## Resumen / Overview

Este pipeline permite actualizar los datos del dashboard AR_Dashboard desde VS Code,
utilizando Power BI Desktop + MCP (Model Context Protocol).

### Arquitectura

```
[Excel/Smartsheet/ArcGIS] → [Power Query M] → [PBI Desktop AS Engine] → [Dashboard]
                                                       ↑
                                            [VS Code MCP Connection]
```

## Requisitos / Requirements

- **Power BI Desktop** instalado (versión PBIP compatible)
- **VS Code** con extensión Power BI Model MCP
- Archivos de datos en `BasePath` (OneDrive sincronizado)

## Parámetro BasePath

El modelo usa un parámetro `BasePath` que apunta a la raíz de OneDrive:

```
BasePath = "E:\OneDrive - IUCN International Union for Conservation of Nature"
```

Para cambiar la ubicación de datos, solo modifique este valor en:
- `expressions.tmdl` línea 1
- O vía MCP: `named_expression_operations` → Update

## Procedimiento de Actualización

### Paso 1: Abrir Power BI Desktop

```bash
python pbi_refresh.py full
```

O manualmente: abrir `03_PowerBI_Dashboard/AR_Dashboard.pbip` con Power BI Desktop.

### Paso 2: Conectar MCP al modelo activo

En VS Code Copilot, ejecutar:

```
connection_operations → ListLocalInstances
```

Luego conectar:

```json
{
  "operation": "Connect",
  "ConnectionString": "Provider=MSOLAP;Data Source=localhost:<PORT>"
}
```

### Paso 3: Actualizar datos

#### Opción A: Actualizar todo (recomendado)

Usar `partition_operations → Refresh` para cada tabla con datos externos:

**Tablas con fuente Excel:**
| Tabla | Fuente |
|-------|--------|
| Area_Indicator_ID | Area_Indicator_ID.xlsx |
| BASE_Indicator | Tbl_Integrado.xlsx |
| Index_Pp | Tbl_Integrado.xlsx |
| KOICA_ORG_DIM_TARGET | KOICA_DATA_MODEL_v1.xlsx |
| KOICA_ORG_FACT_AREA | KOICA_DATA_MODEL_v1.xlsx |
| KOICA_ORG_FACT_BNF | KOICA_DATA_MODEL_v1.xlsx |
| KOICA_ORG_FACT_ORG | KOICA_DATA_MODEL_v1.xlsx |
| KOICA_ORG_FACT_PRJ_OBJ | KOICA_DATA_MODEL_v1.xlsx |
| Location_Grants | Grants_X_YDD.xls |
| Tbl_Actvdd_m_e_data | Tbl_Integrado.xlsx |
| Tbl_Actvdd_TIPO_me | Tbl_Integrado.xlsx |
| Tbl_Gender | data_structure_Gender... .xlsx |
| Tbl_Pp | Tbl_Integrado.xlsx |
| Tbl_Grants | Tbl_Integrado.xlsx |

**Tablas con fuente Folder (Excel múltiples):**
| Tabla | Carpeta |
|-------|---------|
| Tbl_Area | AR_3_Area/0. Database_oficial |
| Tbl_Area_poli | AR_3_Area/0. Database_oficial |
| Comités-Microcuencas | Monster-File/.../Comités-Microcuencas |
| ESMP_1_2 | Monster-File/.../1.2. Comités-Microcuencas |
| ESMP_G_1 | Monster-File/.../1.2. Comités-Microcuencas |

**Tablas con fuente Smartsheet (requiere autenticación):**
| Tabla | Workspace Key |
|-------|---------------|
| Tbl_Actvdd_ss | 7709708342585220 (3 sheets combinados) |

**Tablas con fuente Erosion (Excel SWY):**
| Tabla | Archivo |
|-------|---------|
| ZonalSt_SWY_BL_aet | SWY_indicadores_BalanceH_LB.xlsx |
| ZonalSt_SWY_BL_L | SWY_indicadores_BalanceH_LB.xlsx |
| ZonalSt_SWY_BL_P | SWY_indicadores_BalanceH_LB.xlsx |
| ZonalSt_SWY_BL_QF | SWY_indicadores_BalanceH_LB.xlsx |

#### Opción B: Actualizar tabla específica

```json
{
  "operation": "Refresh",
  "RefreshDefinitions": [
    {
      "TableName": "Tbl_Actvdd_m_e_data",
      "PartitionName": "Tbl_Actvdd_m_e_data-713314a4-07b8-480a-a473-b982b9642590",
      "RefreshType": "Full"
    }
  ]
}
```

### Paso 4: Verificar datos

Ejecutar consulta DAX para verificar:

```json
{
  "operation": "Execute",
  "Query": "EVALUATE ROW(\"Rows\", COUNTROWS('Tbl_Actvdd_m_e_data'))"
}
```

### Paso 5: Guardar en PBI Desktop

Después de actualizar, guardar el archivo en Power BI Desktop (Ctrl+S).
Los cambios se reflejan automáticamente en los archivos TMDL.

## Detección de Puerto de Power BI Desktop

`pbi_refresh.py` detecta automáticamente el puerto del motor Analysis Services de Power BI Desktop.

**Comportamiento mejorado (Auditoría 2026-04-06):**

- Escanea **todos** los workspaces en `AnalysisServicesWorkspaces`, no solo el primero
- Si se configura `PBIP_PATH` en `.env`, intenta correlacionar el workspace con el proyecto PBIP activo
- Si solo hay un workspace activo, lo usa directamente
- Si hay múltiples workspaces y no se puede correlacionar, usa el primero con una advertencia en el log

> Referencia: `documents/audit-integrations-gpt54.md` — Finding #6

---

## Limitaciones / Limitations

| Limitación | Descripción |
|------------|-------------|
| Offline TMDL | La conexión TMDL offline es de solo lectura — no puede ejecutar Refresh |
| PBI Desktop requerido | Se necesita PBI Desktop ejecutándose para actualizar datos |
| Smartsheet OAuth | Las tablas Smartsheet requieren autenticación activa en PBI Desktop |
| ArcGIS Online | Los datos GIS son pre-procesados por notebooks (01_/02_) antes de llegar al dashboard |
| Múltiples instancias PBI | Si hay varias instancias de PBI Desktop, configure `PBIP_PATH` en `.env` para asegurar detección correcta |

## Flujo de Datos Completo

```
1. Smartsheet API → Notebooks (01_Ssheet_DataCollect) → Excel files
2. ArcGIS Online → Notebooks (02_ArcGIS_MapUpdater) → Feature layers + Excel
3. Excel files (OneDrive) → Power Query M (BasePath) → PBI Semantic Model
4. PBI Desktop → Refresh → Updated Dashboard
```
