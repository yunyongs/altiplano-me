# Lógica de Múltiples Shapefiles por Fila C2

## Contexto

En el Componente 2 (C2), una fila resumen de Smartsheet puede tener **múltiples
archivos ZIP de shapefiles** adjuntos, cada uno correspondiente a un tipo de
Acción de Restauración (AbE) diferente.

### Ejemplo real

Fila resumen **4170** (contrato AR-PPD-050, organización AYUDA-GT, trimestre 2025-Q4):

| Archivo adjunto original       | Tipo AbE detectado                                 | Abreviación |
|--------------------------------|----------------------------------------------------|-------------|
| `SHP_Q4_CS_AYUDAGT.zip`       | Sistema Agroforestal \| Conservación de suelo y agua | `sueloyagua` |
| `SHP_Q4_SAF.ANUALAYUDAGT.zip` | Sistema Agroforestal \| Cultivos anuales            | `anual`      |

Filas hijas con códigos:

| CÓDIGO              | AbE                                                 | Hectáreas |
|---------------------|-----------------------------------------------------|-----------|
| 251203_C2_AYUDA-GT_a | Sistema Agroforestal \| Cultivos anuales            | 3.96      |
| 251208_C2_AYUDA-GT_a | Sistema Agroforestal \| Cultivos anuales            | 20.46     |
| 251215_C2_AYUDA-GT_a | Sistema Agroforestal \| Conservación de suelo y agua | 0.26      |
| 251222_C2_AYUDA-GT_a | Sistema Agroforestal \| Conservación de suelo y agua | 2.64      |

---

## Flujo de Procesamiento

### Paso 1: Detección de pista AbE en nombre de archivo

La función `extract_abe_hint_from_filename()` en `ar_utils.py` analiza el nombre
original del archivo adjunto para extraer una pista de tipo AbE:

```
SHP_Q4_CS_AYUDAGT.zip       → "sueloyagua"  (CS = Conservación de Suelo)
SHP_Q4_SAF.ANUALAYUDAGT.zip → "anual"       (ANUAL = Cultivos anuales)
```

**Palabras clave reconocidas**: CS, AGUAYSUELO, SUELOYAGUA, ANUAL, PEREN, SILVO,
PLANT, FORESTAL, PRODU, PROTE, REFOR.

### Paso 2: Descarga diferenciada

Cuando se detecta una pista AbE, el nombre del ZIP descargado incluye el sufijo:

```
AR-PPD-050_AYUDA-GT_2025-Q4-anual.zip
AR-PPD-050_AYUDA-GT_2025-Q4-sueloyagua.zip
```

Esto evita que un archivo sobrescriba al otro durante la descarga.

### Paso 3: Carpeta única por fila C2

**Ambos ZIPs se extraen en la misma carpeta** basada en el identificador C2:

```
{destino}/AR-PPD-050_AYUDA-GT_2025-Q4/
    AR-PPD-050_AYUDA-GT_2025-Q4-Shapes/
        AR-PPD-050_AYUDA-GT_2025-Q4-anual_polygon.shp
        AR-PPD-050_AYUDA-GT_2025-Q4-anual_polygon.dbf
        AR-PPD-050_AYUDA-GT_2025-Q4-anual_polygon.prj
        AR-PPD-050_AYUDA-GT_2025-Q4-sueloyagua_polygon.shp
        AR-PPD-050_AYUDA-GT_2025-Q4-sueloyagua_polygon.dbf
        AR-PPD-050_AYUDA-GT_2025-Q4-sueloyagua_polygon.prj
        _cdg_mapping.json
        _orig_names.json
```

**Regla clave**: El `identifier` (nombre de carpeta) NO incluye la pista AbE.
Solo el nombre del ZIP descargado y los archivos SHP renombrados incluyen el
tipo AbE.

### Paso 4: Asignación de CdgActvdd (3 niveles) en ArcPy

El archivo `_cdg_mapping.json` contiene **TODAS** las filas hijas (no filtradas).
El matching de 3 niveles existente en `_score_mapping()` funciona así:

1. **Filtro AbE**: Extrae la abreviación del nombre del shapefile (`anual`,
   `sueloyagua`) y filtra los hijos que coincidan.
2. **Fecha/Ubicación**: Entre los coincidentes, busca coincidencia por fecha
   o nombre de ubicación.
3. **Hectáreas**: Como último recurso, compara hectáreas del shapefile con las
   de cada fila hija.

**Ejemplo**:
- `AR-PPD-050_AYUDA-GT_2025-Q4-anual_polygon.shp` → AbE = "anual"
  → Candidatos: 251203_C2_AYUDA-GT_a (3.96 ha), 251208_C2_AYUDA-GT_a (20.46 ha)
  → Decisión final por hectáreas o fecha.

- `AR-PPD-050_AYUDA-GT_2025-Q4-sueloyagua_polygon.shp` → AbE = "sueloyagua"
  → Candidatos: 251215_C2_AYUDA-GT_a (0.26 ha), 251222_C2_AYUDA-GT_a (2.64 ha)
  → Decisión final por hectáreas o fecha.

---

## Casos Especiales

### Un solo shapefile + una sola fila hija
Se mantiene la lógica existente sin cambios. No se detecta pista AbE (o no es
necesaria), y el código se asigna directamente.

### Un solo shapefile + múltiples filas hijas
Se mantiene la lógica existente de 3 niveles de matching.

### Múltiples shapefiles sin pista AbE en nombre
Si el nombre original no contiene una palabra clave reconocida, la función
`extract_abe_hint_from_filename()` retorna `""` y se usa la lógica estándar (ABE
se lee del campo `.dbf` del shapefile o del valor de la fila resumen).

---

## Archivos Modificados

| Archivo | Cambio |
|---------|--------|
| `ar_utils.py` | Nueva función `extract_abe_hint_from_filename()` |
| `app.py` (`ss_batch_download`) | Diferenciación de `safe_name` con sufijo AbE; `identifier` sin sufijo |
| `paso1_quarterly.py` (`place_shapefile`) | Excluir archivos ya en `-Shapes`; merge de `_orig_names.json` |
| `tests/test_ar_utils.py` | 12 tests para `extract_abe_hint_from_filename` |
| `tests/test_paso1_quarterly.py` | Test `test_multi_shp_same_folder` |
