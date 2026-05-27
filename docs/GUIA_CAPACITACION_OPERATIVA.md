# Guía de Capacitación Operativa — Wizard y Paso 1-a

Este documento organiza la capacitación del usuario no técnico para que el modo
Wizard y el flujo operativo real trabajen con el mismo lenguaje.

El objetivo no es solo enseñar botones. El objetivo es que la persona operadora
entienda cómo convertir el diagnóstico en trabajo real hasta cerrar todos los
pendientes del trimestre.

---

## Perfil de la persona usuaria

- persona designada para ejecutar la actualización trimestral
- usa Smartsheet, ArcGIS Pro y Power BI, pero no programa
- necesita una secuencia clara, repetible y verificable

---

## Objetivos de la capacitación

Al final de la capacitación, la persona debe poder:

1. distinguir entre modo Wizard y modo Avanzado
2. explicar que el primer bloque operativo es Paso 1-a
3. ejecutar el orden correcto en C2: preview, PPD o PMD, diagnóstico
4. usar el panel derecho como lista de trabajo
5. completar un shapefile con el criterio correcto de cierre

---

## Estructura sugerida de capacitación

### Módulo 1. Entender el sistema

Mensajes clave:
- el sistema muestra muchos bloques, pero el operador debe seguir un hilo claro
- Wizard sirve para guiar el proceso completo
- Avanzado sirve para usuarios con más autonomía

### Módulo 2. Entender Paso 1-a

Secuencia que debe practicarse:

1. elegir componente
2. cargar la vista previa
3. si es C2, elegir primero PPD o PMD
4. si hace falta, filtrar también por contrato y trimestre
5. ejecutar el diagnóstico

Mensaje obligatorio:
- el diagnóstico no es un paso aislado
- primero se arma el contexto y después se diagnostica

### Módulo 3. Leer el diagnóstico como cola de trabajo

Explicación:
- el panel derecho no es un reporte pasivo
- cada actividad pendiente representa una tarea operativa real
- la casilla se marca solo cuando el trabajo terminó de verdad

Criterio de completitud:
- el shapefile fue subido a ArcGIS Pro
- `CÓDIGO DE LA ACTIVIDAD` quedó correctamente insertado

### Módulo 4. Practicar el bucle de shapefiles

Secuencia de práctica:

1. elegir un pendiente en el panel derecho
2. ajustar filtros en la vista previa
3. descargar el shapefile
4. subirlo a ArcGIS Pro
5. insertar o confirmar el código
6. validar el resultado
7. marcar el pendiente como completado

Regla didáctica:
- no trabajar varios shapefiles a la vez
- terminar uno antes de pasar al siguiente

### Módulo 5. Casos especiales de C2

Puntos que deben mostrarse en capacitación:
- la selección PPD o PMD siempre va antes del diagnóstico
- una fila resumen puede tener varios shapefiles
- el operador debe usar diagnóstico y filtros al mismo tiempo para no mezclar casos

### Módulo 6. Continuación después de Paso 1

Cuando el panel derecho ya no tenga pendientes sin marcar, se continúa con:

1. Paso 2 — Control Cruzado
2. Paso 3 — ArcPy
3. Paso 4 — AGOL
4. Paso 5 — Excel maestro y recepción M&E
5. Paso 6 — comparación Power BI
6. Paso 7 — documentación y respaldo

---

## Frases que deben repetirse en la capacitación

1. El primer bloque real de trabajo es Paso 1-a.
2. En C2, primero PPD o PMD.
3. El diagnóstico construye la lista real de trabajo.
4. El panel derecho se usa para gestionar avance.
5. Una actividad solo termina cuando el shapefile y el código quedaron correctos.

---

## Materiales que acompañan esta guía

Orden recomendado de lectura para la persona operadora:

1. `GUIA_INSTALACION.md`
2. `WORKFLOW_STEPS.md`
3. `UI_MOCKUP.md`
4. `MANUAL_OPERATIVO_NO_TECNICO.md`
5. este documento

Orden recomendado para quien prepara la capacitación:

1. `documents/01_S1_WIZARD.md`
2. `documents/WORKFLOW_STEPS_kr.md`
3. `documents/UI_MOCKUP_kr.md`
4. `documents/GUIA_CAPACITACION_OPERATIVA_kr.md`

---

## Ubicación de este documento dentro del paquete documental

Este archivo pertenece al paquete final de operación en español dentro de `docs/`.

Su equivalente de trabajo y alineación conceptual vive en:

- `documents/GUIA_CAPACITACION_OPERATIVA_kr.md`

De esta forma, `documents/` conserva el razonamiento y `docs/` conserva el paquete
listo para capacitación y traspaso.