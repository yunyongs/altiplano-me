# Pasos del Flujo de Trabajo -- Guia Actualizada

Este documento describe el flujo operativo actual del panel de Altiplano Resiliente
segun la interfaz vigente y las rutas activas del servidor Flask.

El cambio principal es que el diagnostico AGOL vs Smartsheet ya no debe leerse
como un Paso 0 independiente. Operativamente debe tratarse como Paso 1-a,
es decir, como la primera parte del trabajo sobre Smartsheet.

---

## Flujo General

1. Paso 1-a -- Preparar vista previa y diagnostico
2. Paso 1 -- Revisar resultados del diagnostico y ejecutar el bucle de shapefiles
3. Paso 1b -- Descargar y preparar shapefiles
4. ~~Paso 2 -- Ejecutar control cruzado~~ (Removed)
5. Paso 3 -- Procesamiento ArcPy y criterios de limpieza
6. Paso 4 -- Publicacion AGOL y verificacion 3 fuentes
7. Paso 5 -- Excel maestro y recepcion M&E de Dafne
8. Paso 6 -- Power BI y comparacion M&E
9. Paso 7 -- Documentacion, guia PDF, chequeo de enlace y respaldo

---

## Paso 1-a -- Preparar vista previa y diagnostico

### 1.0 Conectar AGOL (una vez por sesion)

El diagnostico necesita una sesion AGOL viva.

- en la barra lateral, abrir Configuracion y hacer clic en **Conectar AGOL**
- el navegador abre la pagina de autenticacion OAuth de ArcGIS Online
- al volver, el panel muestra `Conectado` con el usuario y la organizacion
- la sesion dura 60 minutos; despues se vuelve a conectar con un clic

Notas:
- esto requiere que `ARCGIS_CLIENT_ID` y `ARCGIS_ORG_URL` esten definidos
  (la URL tambien se puede ingresar en la UI)
- los Item IDs de las capas AGOL (`AGOL_POLYGON_ITEM_ID`, `AGOL_POINT_ITEM_ID`)
  permiten usar capas privadas / licenciadas

### 1.1 Cargar vista previa de la hoja

El operador debe iniciar con la hoja ya seleccionada por componente.

Funcion:
- cargar la hoja de Smartsheet en la vista principal
- abrir la tabla y el resumen
- dejar listo el contexto de filtros y rango de filas

Interpretacion operativa:
- el diagnostico no se usa aislado
- primero se abre la hoja y luego se diagnostica sobre esa seleccion

### 1.1.1 En C2, elegir PPD o PMD

Para C2, antes del diagnostico, se debe elegir el tipo de subvencion.

Secuencia:
- cargar la vista previa
- en los filtros C2, seleccionar PPD o PMD
- si hace falta, ajustar tambien contrato y trimestre

Motivo:
- el diagnostico debe ejecutarse sobre un subconjunto operativo manejable
- esto evita mezclar grupos distintos dentro del mismo ciclo de trabajo

### 1.1.2 Ejecutar el diagnostico

En este momento ya existe un contexto claro:

- componente seleccionado
- en C2, PPD o PMD ya elegido
- rango o filtros ya definidos

El diagnostico hace lo siguiente:
- compara Smartsheet con las capas AGOL de poligono y punto
- clasifica actividades como verified_match, verified_mismatch o new
- identifica cuales actividades todavia requieren trabajo real con shapefiles

Nota operativa:
- en la interfaz actual el boton sigue apareciendo como una tarjeta separada,
  pero el operador debe leerlo como Paso 1-a.

---

## Paso 1 -- Revisar resultados del diagnostico y ejecutar el bucle de shapefiles

### 1.2 Leer el diagnostico en el panel derecho

Los resultados del diagnostico se observan en el panel derecho.

Ese panel sirve para:
- ver que actividades ya estan verificadas
- ver cuales tienen discrepancia
- ver cuales todavia requieren trabajo de shapefile
- seguir el avance de ejecucion

Modelo operativo recomendado:
- cada fila pendiente debe tener una casilla de verificacion
- la casilla no representa solo lectura, sino trabajo completado

### 1.2.1 Cuando una actividad se marca como completada

Una actividad se considera completada solo cuando se cumple el objetivo real:

- el archivo fue subido a ArcGIS Pro
- CÓDIGO DE LA ACTIVIDAD quedo correctamente insertado

El orden puede variar:
- subir primero y luego insertar codigo
- insertar primero y luego subir

En ambos casos, la casilla se marca solo cuando el resultado final es correcto.

### 1.2.2 Usar el diagnostico como cola de trabajo

El panel derecho debe leerse como la cola de trabajo pendiente.

Mientras el operador lo revisa:
- ajusta los filtros de la vista previa
- localiza el registro exacto
- confirma adjuntos, codigo, estado y contexto del grupo

En otras palabras:
- el diagnostico dice que falta hacer
- la vista previa permite encontrar y ejecutar cada caso

### 1.2.3 Bucle operativo por cada shapefile pendiente

Para cada shapefile no ejecutado, se repite el siguiente ciclo:

1. elegir una actividad pendiente en el panel derecho
2. ajustar filtros en la vista previa para aislarla
3. descargar el shapefile correspondiente
4. subirlo a ArcGIS Pro
5. insertar o confirmar CÓDIGO DE LA ACTIVIDAD
6. validar que el resultado final este correcto
7. marcar la casilla de esa actividad
8. pasar al siguiente pendiente

Este bucle se repite hasta completar todos los shapefiles que el diagnostico
marco como pendientes de ejecucion.

### 1.3 Herramientas auxiliares dentro del Paso 1

Durante ese ciclo pueden usarse las herramientas de saneamiento del Paso 1:

- generar codigos faltantes
- actualizar revision
- corregir fechas
- ajustar Calidad SIG
- corregir AbE
- aplicar fill-down con vista previa

Estas herramientas ayudan a dejar la fila lista antes de descargar o subir el archivo.

---

## Paso 1b -- Descargar y preparar shapefiles

Paso 1b sigue existiendo como bloque funcional, pero en la operacion real suele
ejecutarse varias veces dentro del bucle definido en el Paso 1.

### 1.4 Listar adjuntos

- muestra los adjuntos por fila
- resalta ZIPs que parecen shapefiles

### 1.5 Descarga batch y validacion

Funciones:
- descargar shapefiles ZIP
- extraer de forma segura
- validar el contenido SHP
- crear estructura por trimestre
- reanudar con checkpoint si hubo interrupcion

### 1.6 Caso especial C2 con multiples SHP

La logica actual de C2 permite:
- varios ZIPs SHP por una sola fila resumen
- diferenciacion por pista AbE tomada del nombre original
- una sola carpeta final por fila C2
- _cdg_mapping.json con lista completa de hijos
- deduplicacion: los SHP repetidos en distintos hijos se procesan una sola vez

Esto es especialmente importante cuando el operador procesa C2 por PPD o PMD.

### 1.7 Agregar shapefiles al mapa

Despues de descargar:
- se puede generar un script para agregar SHP al mapa de ArcGIS Pro
- el script ubica los shapefiles dentro de group layers por trimestre
  (`2026_Q1`, `2026_Q1_polygon`)
- si ARCPY_PYTHON existe, el servidor tambien puede ejecutarlo
- los mensajes del script respetan el idioma activo (es / en)

### 1.8 Caso fallback Excel de areas (sin shapefile)

Cuando una fila no tiene shapefile adjunto pero si trae un Excel de areas
(nombre con `area`, `_ha`, `puntos`, etc.), el bucle agente:

1. descarga el Excel con `/api/smartsheet/excel-area-download`
2. parsea el Excel (segunda hoja por defecto) convirtiendo DMS a decimal
   y reproyectando WGS84 a GTM si las coordenadas estan en lat/lon
3. genera un CSV listo para XYTableToPoint
4. ejecuta un script ArcPy que crea el feature class en `CSVPOINT_TO_GDB`
   y lo agrega al mapa dentro del group layer `{Q}_point`

Este camino permite cerrar el Paso 1-b incluso cuando el reportero solo
entrego puntos en Excel.

---

## ~~Paso 2 -- Control Cruzado~~ (Removed)

> Este paso ha sido eliminado del sistema. Las funciones `uploadGisCsv`,
> `runCrosscheck` y `validateShpCodes` ya no estan disponibles. Los endpoints
> `/api/crosscheck/*` y `/api/shp-validate/*` han sido removidos.

---

## Paso 3 -- Procesamiento ArcPy

Scripts disponibles:
- import
- merge_field_mapping
- overlap_analysis
- duplicate_detection
- erase_pipeline
- spatial_join_micro
- incentive_validation
- append_official
- gis_vs_ss_comparison
- backup_cumulative
- export_excel

Funciones complementarias:
- criterios de limpieza por trimestre
- exportacion PDF de criterios
- estadisticas antes/despues de limpieza

---

## Paso 4 -- Publicacion en AGOL y verificacion 3 fuentes

- actualizar punto
- actualizar poligono
- exportar shapefiles
- verificar Smartsheet vs GIS vs AGOL

---

## Paso 5 -- Excel maestro y recepcion M&E

### 5a Excel maestro

- genera un XLSX con C1, C2 y C3

### 5b Recepcion M&E de Dafne

- validar Tbl_Integrado.xlsx
- colocarlo en BasePath
- revisar estado
- guardar historial por trimestre
- actualizar subpaso 5b

---

## Paso 6 -- Power BI y comparacion M&E

- revisar estado de Power BI Desktop
- abrir PBIP
- generar script de refresh
- comparar Dafne vs Power BI
- analizar discrepancias
- guardar decisiones finales

---

## Paso 7 -- Documentacion y cierre

- reporte de errores
- resumen de datos
- guia PDF manual para Power BI
- chequeo de enlace Publish-to-Web
- respaldo local

---

## Principios Operativos Clave

1. Antes del diagnostico, conectar AGOL via OAuth (una vez por sesion de 60 min).
2. El diagnostico AGOL vs Smartsheet debe tratarse como Paso 1-a.
3. Primero se carga la vista previa; despues se diagnostica.
4. En C2, primero se elige PPD o PMD.
5. El panel derecho del diagnostico funciona como cola de trabajo.
6. Cada shapefile pendiente se procesa uno por uno hasta quedar correctamente cargado y codificado.
7. Cuando no hay shapefile pero si hay Excel de areas, se usa el fallback Excel→puntos.
8. El `CÓDIGO DE LA ACTIVIDAD` nunca se modifica una vez asignado.
9. Solo entonces se marca como completado.
10. El bucle termina cuando no quedan pendientes sin marcar.