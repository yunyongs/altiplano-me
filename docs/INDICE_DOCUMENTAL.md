# Índice Documental del Proyecto

Este documento organiza el contenido actual de las carpetas `docs/` y `documents/`
para que el equipo sepa qué leer, en qué idioma, y con qué propósito.

Documentos raíz relacionados:

- `README.md` para vista general del repositorio
- `Architecture.md` para capas del sistema y reglas de sincronización
- `documents/INDICE_DOCUMENTOS_kr.md` para el paquete interno de trabajo

---

## Ruta rápida de lectura

### Si usted es persona operadora

1. `GUIA_INSTALACION.md`
2. `WORKFLOW_STEPS.md`
3. `UI_MOCKUP.md`
4. `MANUAL_OPERATIVO_NO_TECNICO.md`
5. `GUIA_CAPACITACION_OPERATIVA.md`

### Si usted necesita entender el sistema antes de operar

1. `../README.md`
2. `../Architecture.md`
3. `FEATURES.md`
4. `WORKFLOW_STEPS.md`

### Si usted está alineando documentos con borradores internos

1. `../documents/INDICE_DOCUMENTOS_kr.md`
2. `../documents/01_S1_WIZARD.md`
3. `../documents/WORKFLOW_STEPS_kr.md`

---

## 1. Carpeta `docs/`

`docs/` contiene el paquete operativo final en español.

Aquí deben vivir los documentos que se usan para:

- instalación
- operación diaria
- capacitación
- entrega al usuario no técnico

Orden recomendado de lectura:

1. `GUIA_INSTALACION.md`
2. `FEATURES.md`
3. `WORKFLOW_STEPS.md`
4. `UI_MOCKUP.md`
5. `MANUAL_OPERATIVO_NO_TECNICO.md`
6. `GUIA_CAPACITACION_OPERATIVA.md`
7. `TEST_COVERAGE_ANALYSIS.md`
8. `LOGICA_MULTI_SHP_C2.md`
9. `PIPELINE_ACTUALIZACION_PBI.md`

---

## 2. Carpeta `documents/`

`documents/` contiene el paquete de trabajo interno.

Aquí deben vivir:

- borradores coreanos
- planes de implementación
- especificaciones de diseño
- auditorías
- notas de alineación conceptual

Orden recomendado para revisar el rediseño operativo actual:

1. `01_S1_WIZARD.md`
2. `WORKFLOW_STEPS_kr.md`
3. `UI_MOCKUP_kr.md`
4. `MANUAL_OPERATIVO_NO_TECNICO_kr.md`
5. `GUIA_CAPACITACION_OPERATIVA_kr.md`

---

## 3. Regla de sincronización

Cuando cambie un flujo operativo o una regla de capacitación:

1. se ajusta primero el borrador o documento de trabajo en `documents/`
2. luego se actualiza la versión operativa en `docs/`
3. finalmente se valida que Wizard, Workflow, UI Mockup, Manual y Guía de Capacitación usen el mismo lenguaje

---

## 4. Tema central de la reorganización actual

La reorganización actual gira alrededor de esta interpretación:

- el diagnóstico ya no se explica como Paso 0 aislado
- operativamente debe enseñarse como Paso 1-a
- el panel derecho del diagnóstico funciona como cola de trabajo
- cada shapefile pendiente se resuelve uno por uno hasta quedar cargado y codificado correctamente
- cuando no hay shapefile pero sí Excel de áreas, se usa el fallback Excel→puntos
- la conexión AGOL usa OAuth 2.0 PKCE (botón **Conectar AGOL**, sin contraseña)
- las rutas del `.env` usan placeholders `${ONEDRIVE_*}` para ser portables entre PCs
- la interfaz es bilingüe (ES / EN) con toggle persistido

Este criterio debe repetirse en todos los documentos de operación y capacitación.

---

## Enlaces de ida y vuelta

- volver al panorama general: `../README.md`
- revisar arquitectura: `../Architecture.md`
- revisar borradores internos: `../documents/INDICE_DOCUMENTOS_kr.md`