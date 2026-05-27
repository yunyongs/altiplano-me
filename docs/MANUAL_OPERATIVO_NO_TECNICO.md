# Manual Operativo para Usuario No Técnico

Este manual está pensado para la persona operadora que usa el panel sin programar.

Su objetivo es explicar el trabajo real del trimestre con pasos simples y con una
regla clara: terminar un shapefile a la vez hasta que no queden pendientes.

---

## Antes de empezar

Verifique estas cuatro cosas:

1. El componente correcto está seleccionado.
2. Las rutas locales configuradas son correctas.
3. ArcGIS Pro está disponible en este equipo.
4. Si trabajará con Power BI o Dafne, las rutas de salida y BasePath están listas.

---

## Paso 1-a: abrir la hoja y preparar el diagnóstico

1. Seleccione el componente.
2. Haga clic en Cargar Vista Previa.
3. Si el componente es C2, en los filtros elija primero PPD o PMD.
4. Si hace falta, reduzca también por contrato o trimestre.
5. Ejecute Diagnosticar.

Importante:
- aunque en la interfaz el diagnóstico parezca otro bloque, en la operación debe leerse como Paso 1-a
- primero se abre la hoja y después se corre el diagnóstico

---

## Paso 1: usar el panel derecho como lista de trabajo

Después del diagnóstico, mire el panel derecho.

Ese panel le dice:
- qué ya está verificado
- qué tiene discrepancia
- qué todavía necesita trabajo real

Lea cada actividad pendiente como una tarea.

### Cuándo una tarea se considera terminada

Marque una actividad como completada solo cuando:

- el shapefile ya fue subido a ArcGIS Pro
- CÓDIGO DE LA ACTIVIDAD quedó correctamente insertado

El orden puede variar:
- subir primero y luego insertar código
- insertar primero y luego subir

Lo importante es el estado final correcto.

---

## Bucle de trabajo: un shapefile a la vez

Repita este ciclo para cada actividad pendiente:

1. Elija una fila pendiente en el panel derecho.
2. Ajuste los filtros de la vista previa para encontrar exactamente esa actividad.
3. Descargue el shapefile correspondiente.
4. Súbalo a ArcGIS Pro.
5. Inserte o confirme CÓDIGO DE LA ACTIVIDAD.
6. Revise que todo quedó correcto.
7. Marque esa actividad como completada.

No pase a la siguiente hasta terminar la actual.

---

## Herramientas que puede usar durante el trabajo

Si encuentra datos incompletos o inconsistentes, puede usar estas funciones:

- Generar Códigos Faltantes
- Actualizar Revisión
- corregir fechas
- corregir AbE
- aplicar fill-down

Estas herramientas sirven para dejar la fila en condiciones antes de descargar o subir archivos.

---

## Paso 1b: descarga y preparación

Use Paso 1b cuando necesite:

- listar adjuntos
- descargar ZIPs de shapefiles
- validar que el contenido sea correcto
- organizar carpetas por trimestre

En C2, puede haber varios shapefiles en una sola fila resumen. El sistema ya está preparado para eso.

---

## Después del bucle de shapefiles

Cuando ya no queden pendientes sin marcar, continúe así:

1. ~~Paso 2 -- Control Cruzado~~ (Removed)
2. Paso 3 -- Procesamiento ArcPy
3. Paso 4 -- Publicación en AGOL
4. Paso 5 -- Excel maestro y recepción M&E
5. Paso 6 -- Power BI y comparación M&E
6. Paso 7 -- Reportes, PDF, enlace y respaldo

---

## Errores comunes que debe evitar

1. Ejecutar el diagnóstico en C2 sin elegir primero PPD o PMD.
2. Tratar varias actividades al mismo tiempo y perder el control del avance.
3. Marcar una actividad como terminada antes de confirmar el código.
4. Leer el panel derecho como reporte pasivo, en vez de usarlo como lista de trabajo.

---

## Regla más importante

Mientras existan actividades pendientes sin marcar, el Paso 1 no ha terminado.

La meta no es solo descargar archivos.
La meta es que cada shapefile pendiente quede realmente trabajado en ArcGIS Pro y con su CÓDIGO DE LA ACTIVIDAD correcto.