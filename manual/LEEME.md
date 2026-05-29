# Manual de Operación — Altiplano Resiliente · Actualizador de Mapa

Esta carpeta contiene el **manual ilustrado** para la persona operadora del
Actualizador de Mapa, más esta guía de **instalación desde cero**.

- **¿Ya está instalado el sistema?** → abra **`index.html`** y siga el manual.
- **¿Es un computador nuevo, sin el sistema?** → siga primero la sección
  *“A. Instalación desde cero”* de abajo.

---

## Contenido de esta carpeta

| Archivo / carpeta | Descripción |
|:------------------|:------------|
| `index.html`      | El manual de operación completo (página única, con capturas reales). |
| `img/`            | Imágenes (capturas de pantalla) usadas en el manual. |
| `LEEME.md`        | Este archivo: instalación, ejecución y cómo abrir/guardar el manual. |

Las capturas se tomaron de la interfaz real en español. No contienen datos
sensibles: muestran solo la estructura de pantalla.

---

# A. Instalación desde cero

Siga estos pasos **una sola vez** en cada computador nuevo. Si el sistema ya
está instalado, salte a la sección *“C. Ejecutar el sistema cada día”*.

> **Sistema operativo:** estas instrucciones son para **Windows**.

## Paso A1 — Instalar Python (si aún no lo tiene)

1. Abra el navegador y vaya a **<https://www.python.org/downloads/>**.
2. Descargue **Python 3.10 o superior** (el botón amarillo grande).
3. Ejecute el instalador. **Muy importante:** en la primera pantalla marque la
   casilla **“Add Python to PATH”** (Agregar Python al PATH) antes de pulsar
   *Install Now*.
4. Para comprobar que quedó instalado: abra el menú Inicio, escriba
   `cmd`, abra la *Símbolo del sistema* y escriba:
   ```
   python --version
   ```
   Debe aparecer algo como `Python 3.12.x`.

## Paso A2 — Descargar el programa desde GitHub

Tiene **dos formas**. La opción 1 (ZIP) es la más sencilla y **no requiere
instalar nada extra**.

### Opción 1 — Descargar el ZIP (recomendada, más fácil)

1. Abra el navegador y vaya a la página del proyecto en GitHub:
   **<https://github.com/yunyongs/altiplano-me>**
2. Pulse el botón verde **`< > Code`** (arriba a la derecha de la lista de archivos).
3. En el menú que se abre, elija **“Download ZIP”**.
4. Se descargará un archivo llamado, por ejemplo,
   `altiplano-me-main.zip`, normalmente en la carpeta *Descargas*.
5. Haga clic derecho sobre el ZIP → **“Extraer todo…”** → elija una carpeta
   estable, por ejemplo `C:\altiplano-me`, y pulse *Extraer*.

> **Consejo:** evite carpetas con espacios raros o muy profundas. Una ruta corta
> como `C:\altiplano-me` funciona mejor.

### Opción 2 — Con Git (si sabe usarlo)

Si tiene **Git** instalado (<https://git-scm.com/download/win>), abra la
*Símbolo del sistema* y escriba:

```
cd C:\
git clone https://github.com/yunyongs/altiplano-me.git
```

Esto crea la carpeta `C:\altiplano-me` con el programa.

## Paso A3 — Instalar el sistema (setup.bat)

1. Abra la carpeta donde extrajo/clonó el programa
   (por ejemplo `C:\altiplano-me`).
2. Haga **doble clic** en **`setup.bat`**.
3. Se abrirá una ventana negra que hará todo automáticamente:
   - crea el entorno de Python e instala los paquetes necesarios;
   - detecta la instalación de ArcGIS Pro;
   - crea el archivo de credenciales `.env`.
4. **Si es la primera instalación del equipo**, el script le pedirá escribir las
   credenciales compartidas. Téngalas a mano:

   | Le pedirá | Qué escribir |
   |:----------|:-------------|
   | Smartsheet API Token | El token de Smartsheet del proyecto. |
   | Sheet ID — C1 | El identificador de la hoja del Componente 1. |
   | Sheet ID — C2 / C3 | Identificadores de C2 y C3 (Enter si no aplica). |
   | ArcGIS Client ID | El App ID de ArcGIS Online (OAuth). |
   | ArcGIS Client Secret | El secreto de esa aplicación. |

   > **No tiene estas credenciales?** Pídalas al administrador del sistema.
   > Sin el token de Smartsheet el tablero no podrá leer los datos.

5. Cuando termine, verá el mensaje **“Instalación completa!”**. Pulse una tecla
   para cerrar la ventana.

> **¿No encontró ArcGIS Pro?** No es un problema para instalar: puede continuar
> y completar esa ruta más tarde. Los pasos que usan ArcGIS Pro (Paso 3 y 4) la
> necesitarán; vuelva a ejecutar `setup.bat` después de instalar ArcGIS Pro.

## Paso A4 — Carpetas en OneDrive de IUCN

Este sistema guarda **todos** sus archivos (descargas, datos de Smartsheet,
geodatabase, proyecto de ArcGIS Pro) dentro de su **OneDrive de IUCN**, es
decir, la carpeta `OneDrive - IUCN…` que aparece bajo su usuario de Windows.

**¿Por qué OneDrive de IUCN?** Cada computador monta OneDrive en una letra de
unidad distinta (`E:`, `C:`, `D:`…). El sistema detecta automáticamente su
carpeta `OneDrive - IUCN…` y arma las rutas a partir de ella. Así, la misma
configuración funciona en cualquier PC del equipo sin reescribir las rutas.

Requisitos para que funcione:

1. Tenga **OneDrive de IUCN iniciado y sincronizado** en este PC (debe verse la
   carpeta `OneDrive - IUCN…` bajo `C:\Users\<su usuario>\`).
2. Dentro de ese OneDrive debe existir la carpeta del proyecto (por ejemplo
   `…\OneDrive - IUCN…\AR\`) con sus subcarpetas. Si no existe, pídala al
   administrador o cree la estructura que él le indique.

Después, confirme o ajuste las subcarpetas **dentro del tablero**, una sola vez:

1. Ejecute el sistema (vea la sección C).
2. En el menú izquierdo, abra **Configuración** y pulse
   **“Rutas Locales (este PC)”**.
3. Verifique las carpetas (ya vienen apuntando a su OneDrive de IUCN) y, si hace
   falta, ajústelas; luego pulse **“Guardar en .env”**.

> Estos valores se guardan en el archivo `.env` local y **nunca** se suben a
> internet. (Más detalle en el manual, sección *6. Rutas locales del PC*.)

---

# B. Requisitos (resumen)

| Requisito | Necesario para |
|:----------|:---------------|
| **Windows** | Todo el sistema. |
| **Python 3.10+** | Ejecutar el tablero. |
| **Token de Smartsheet** | Leer los datos del proyecto. |
| **Cuenta de ArcGIS Online (OAuth)** | Diagnóstico (Paso 1-a) y publicación (Paso 4). |
| **ArcGIS Pro** | Procesamiento del mapa (Pasos 3 y 4). |
| **OneDrive de IUCN sincronizado** | **Necesario:** todas las rutas del sistema se basan en la carpeta `OneDrive - IUCN…` de cada PC. |

---

# C. Ejecutar el sistema cada día

Una vez instalado, abrir el tablero es muy simple:

1. En la carpeta del programa, haga **doble clic** en **`run.bat`**.
2. Se abre una ventana negra (la “consola”). **No la cierre** mientras trabaja:
   es el motor del tablero.
3. Abra el navegador (Chrome, Edge o Firefox) y vaya a:
   ```
   http://127.0.0.1:5000
   ```
   (también funciona `http://localhost:5000`).
4. Aparece el tablero. A partir de aquí, siga el **manual** (`index.html`).

**Para terminar:** cierre la pestaña del navegador y luego cierre la ventana
negra (o pulse `Ctrl + C` dentro de ella).

> **Seguridad:** el tablero funciona solo en este computador (`localhost`).
> Nadie de fuera puede verlo.

---

# D. Cómo abrir y guardar el manual

## Abrir el manual

Haga **doble clic** en **`index.html`**: se abre en su navegador. Use el índice
de la izquierda para saltar a cualquier sección. (No necesita que el sistema
esté corriendo para leer el manual.)

## Guardar el manual como PDF

1. Abra `index.html` en el navegador.
2. Pulse `Ctrl + P` (o menú **Imprimir**).
3. En *Destino*, elija **“Guardar como PDF”**.
4. Guarde el archivo.

> El diseño está preparado para impresión: el índice lateral se oculta y las
> imágenes no se cortan entre páginas.

---

# E. Problemas durante la instalación

| Síntoma | Qué revisar |
|:--------|:------------|
| `python` no se reconoce | Reinstale Python marcando **“Add Python to PATH”** (Paso A1). |
| `setup.bat` falla al instalar paquetes | Verifique su conexión a internet y vuelva a ejecutarlo. |
| `run.bat` dice “no se encuentra .venv” | No se completó la instalación: ejecute primero `setup.bat`. |
| `run.bat` dice “falta el archivo .env” | Ejecute `setup.bat` para crearlo, o pida el `.env` al administrador. |
| El navegador no abre el tablero | ¿Está abierta la ventana negra de `run.bat`? Use `http://127.0.0.1:5000`. |
| Las rutas aparecen con `${ONEDRIVE_IUCN}` sin reemplazar | El sistema no encontró su carpeta `OneDrive - IUCN…`. Inicie y sincronice OneDrive de IUCN, o defina `ONEDRIVE_IUCN` manualmente en `.env`. |
| “No se encuentra la carpeta…” al descargar | Falta la subcarpeta del proyecto dentro de OneDrive de IUCN. Créela o pídala al administrador. |
| No tengo el token / credenciales | Solicítelos al administrador del sistema. |

> Para problemas **durante la operación** (ya con el tablero abierto), consulte
> la sección *19. Problemas frecuentes* del manual (`index.html`).
