# Boceto de Interfaz del Dashboard -- Estructura Actualizada

Este documento describe la estructura actual de la pantalla y la forma correcta
de interpretarla operativamente.

La diferencia clave es que el diagnostico AGOL vs Smartsheet debe entenderse como
Paso 1-a, aunque visualmente siga apareciendo como una tarjeta separada.

---

## Estructura General de la Pantalla

```text
+================================================================================================+
| Altiplano Resiliente                                                                          |
+================================================================================================+
| Barra lateral izquierda                  | Vista principal                         | Panel derecho   |
|------------------------------------------+-----------------------------------------+-----------------|
| Configuración                            | Topbar                                  | Diagnóstico     |
| Paso 1-a Preparación + Diagnose          | Pipeline progress                       | Descarga batch  |
| Paso 1 Smartsheet                        | Summary panel                           | Otros resultados|
| Paso 1b Descarga                         | Sheet preview + filtros                 |                 |
| ~~Paso 2 Control Cruzado~~ (Removed)     | Paneles de scripts y comparación        |                 |
| Paso 3 ArcPy                             |                                         |                 |
| Paso 4 AGOL                              |                                         |                 |
| Paso 5 Excel + M&E                       |                                         |                 |
| Paso 6 Power BI                          |                                         |                 |
| Paso 7 Documentación                     |                                         |                 |
| Orquestador                              |                                         |                 |
+================================================================================================+
| Capa inferior de log                                                                         |
+================================================================================================+
```

---

## Cómo debe leerse el bloque de diagnóstico

En la implementación actual, el botón Diagnosticar aparece como una sección propia.
Sin embargo, el flujo correcto para el operador es este:

1. seleccionar componente
2. cargar la vista previa
3. si el componente es C2, elegir PPD o PMD
4. ejecutar el diagnóstico
5. revisar los resultados en el panel derecho

Por eso, en la operación diaria, ese bloque debe considerarse Paso 1-a.

---

## Vista principal: Preview + filtros

```text
+----------------------------------------------------------------------------------------------+
| Vista Previa de Hoja                                                                         |
|----------------------------------------------------------------------------------------------|
| [Tipo: PPD/PMD] [Contrato] [Trimestre] [Sin código] [Con shapefile] [Calidad SIG] [Fecha]   |
| [Fila inicio] [Fila fin] [Aplicar rango]                                                     |
|----------------------------------------------------------------------------------------------|
| # | Fecha | Código | Organización | Calidad SIG | Hectáreas | Adjuntos | Comentario         |
|---+-------+--------+--------------+-------------+-----------+----------+--------------------|
|   |       |        |              |             |           |          |                    |
+----------------------------------------------------------------------------------------------+
```

Función operativa:
- no es solo una tabla de lectura
- sirve para localizar una actividad exacta mientras se revisa el diagnóstico
- los filtros se ajustan continuamente durante el trabajo

---

## Preparación especial para C2

```text
1. Elegir C2
2. Cargar la vista previa
3. En el filtro Tipo, escoger PPD o PMD
4. Si hace falta, acotar por contrato y trimestre
5. Ejecutar Diagnose
```

Esto es importante porque el diagnóstico debe correrse sobre el subconjunto que
realmente se va a trabajar.

---

## Panel derecho: resultados del diagnóstico como cola de trabajo

```text
+----------------------------------------------------------------------------------+
| Diagnóstico AGOL vs Smartsheet                                                   |
|----------------------------------------------------------------------------------|
| Resumen: verified match / mismatch / new                                         |
|----------------------------------------------------------------------------------|
| [ ] 251215_C2_AYUDA-GT_a   Discrepancia / pendiente                              |
| [ ] 251222_C2_AYUDA-GT_a   Nuevo / pendiente                                     |
| [x] 251203_C2_AYUDA-GT_a   Verificado                                            |
|                                                                                  |
| Cada fila puede mostrar contrato, trimestre, AbE y diferencia de área            |
+----------------------------------------------------------------------------------+
```

Interpretación:
- cada fila del diagnóstico debe comportarse como un ítem de trabajo
- la casilla representa avance real, no solo lectura

### Cuándo se marca una casilla

La casilla se marca solo cuando la actividad ya alcanzó la meta operativa:

- el archivo fue subido a ArcGIS Pro
- CÓDIGO DE LA ACTIVIDAD quedó correctamente insertado

El orden puede ser cualquiera:
- subir primero y luego insertar código
- insertar primero y luego subir

---

## Bucle visual de trabajo por shapefile pendiente

```text
Diagnóstico en panel derecho → elegir pendiente
        ↓
Ajustar filtros en la vista previa
        ↓
Ir a Paso 1b y descargar shapefile
        ↓
Subir a ArcGIS Pro
        ↓
Insertar o confirmar CÓDIGO DE LA ACTIVIDAD
        ↓
Validar que quedó correcto
        ↓
Marcar la casilla en el panel derecho
        ↓
Repetir con el siguiente pendiente
```

Este ciclo continúa hasta completar todos los shapefiles pendientes detectados por el diagnóstico.

---

## Lectura recomendada de la barra lateral

- Configuración: confirmar entorno, **trimestre de trabajo**, componente,
  carpeta de trabajo y conectar AGOL (botón OAuth)
- Paso 1-a: preparar preview, filtros y diagnóstico
- Paso 1: revisar filas, corregir datos y seguir la cola de trabajo
- Paso 1b: descargar, validar y preparar shapefiles (incluye fallback Excel→puntos)
- Paso 3 en adelante: verificar, procesar, publicar y cerrar (Paso 2 Control Cruzado has been removed)

### Estado del botón AGOL

- Antes de conectar: **Conectar AGOL** (azul)
- Conectado: muestra usuario y organización, edad de la sesión (max 60 min)
- Expirado: vuelve al estado inicial — un clic basta para reconectar

Esto permite reconciliar la estructura visual actual con la lógica operativa esperada.

---

## Puntos que el mockup debe conservar

1. El diagnóstico sigue visible en el panel de resultados.
2. Los resultados del diagnóstico deben poder leerse como checklist operativa.
3. La vista previa y los filtros siguen siendo el espacio principal para aislar cada caso.
4. En C2, la selección PPD o PMD debe entenderse como condición previa del diagnóstico.
5. El operador trabaja en bucle hasta que no queden pendientes sin marcar.