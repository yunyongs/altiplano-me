# Guia de Instalacion y Uso — Altiplano Resiliente

> Esta guia esta dirigida a personal no tecnico que necesita instalar y usar
> la herramienta web de actualizacion de mapas en su computadora.

---

## Requisitos previos

Antes de comenzar, asegurese de tener lo siguiente:

| Requisito | Detalle |
|:----------|:--------|
| Windows 10 o 11 | El sistema solo funciona en Windows |
| Python 3.10 o superior | Descargar de https://www.python.org/downloads/ |
| ArcGIS Pro | Necesario para los pasos 3 y 4 del pipeline |
| Conexion a internet | Para descargar paquetes y conectarse a Smartsheet |
| Credenciales compartidas | Token de Smartsheet, IDs de hojas, credenciales de ArcGIS Online |

### Como verificar si Python esta instalado

1. Presione `Win + R`, escriba `cmd` y presione Enter
2. Escriba `python --version` y presione Enter
3. Si aparece algo como `Python 3.12.x`, esta listo
4. Si dice que no se reconoce el comando, necesita instalar Python

### Instalar Python (si no lo tiene)

1. Vaya a https://www.python.org/downloads/
2. Descargue la version mas reciente (boton amarillo grande)
3. **IMPORTANTE**: Al iniciar el instalador, marque la casilla **"Add Python to PATH"** en la parte inferior
4. Haga clic en "Install Now"
5. Espere a que termine y cierre el instalador

---

## Paso 1: Obtener el programa

### Opcion A — Descargar como ZIP (mas sencillo)

1. Vaya al repositorio del proyecto en GitHub
2. Haga clic en el boton verde **"Code"**
3. Seleccione **"Download ZIP"**
4. Descomprima el archivo en una carpeta de su eleccion (por ejemplo `C:\AR\altiplano-me`)

### Opcion B — Clonar con Git (si tiene Git instalado)

```
git clone https://github.com/yunyongs/altiplano-me.git
```

---

## Paso 2: Ejecutar el instalador automatico

1. Abra la carpeta donde descomprimio o clono el proyecto
2. Haga **doble clic** en el archivo **`setup.bat`**
3. El instalador hara lo siguiente automaticamente:
   - Verificar que Python esta instalado
   - Crear un entorno virtual (carpeta `.venv`)
   - Instalar los paquetes necesarios
   - Detectar ArcGIS Pro en su computadora
4. Si es la **primera vez**, le pedira que ingrese las credenciales compartidas del equipo:

| Dato solicitado | Que es | Quien se lo proporciona |
|:----------------|:-------|:------------------------|
| Smartsheet API Token | Clave de acceso a Smartsheet | El administrador del equipo |
| Sheet ID - C1 | Identificador de la hoja Componente 1 | El administrador del equipo |
| Sheet ID - C2 | Identificador de la hoja Componente 2 (opcional) | El administrador del equipo |
| Sheet ID - C3 | Identificador de la hoja Componente 3 (opcional) | El administrador del equipo |
| ArcGIS Client ID | Credencial de la app OAuth de ArcGIS Online | El administrador del equipo |
| ArcGIS Org URL | URL de la organizacion (ej. `https://iucn.maps.arcgis.com`) | El administrador del equipo |
| AGOL Polygon / Point Item ID | IDs de las capas AR_EbA_Area | El administrador del equipo |

5. Cuando termine, vera el mensaje **"Instalacion completa!"**

> **Nota:** Si ya tiene un archivo `.env` de una instalacion anterior, el instalador
> solo actualizara la informacion de ArcGIS Pro sin tocar sus credenciales.

> **OAuth (sin contrasena):** El sistema ya no usa Client Secret. En su lugar
> usa OAuth 2.0 PKCE: al hacer clic en **Conectar AGOL** dentro de la
> aplicacion, se abre el navegador para que usted inicie sesion en
> ArcGIS Online y conceda permisos. El token se guarda solo en memoria y
> dura 60 minutos.

---

## Paso 3: Iniciar la aplicacion

1. Haga **doble clic** en el archivo **`run.bat`**
2. Se abrira una ventana negra (terminal) con el mensaje:
   ```
   Servidor: http://localhost:5000
   ```
3. Abra su navegador web (Chrome, Edge, Firefox)
4. Escriba en la barra de direccion: **http://localhost:5000**
5. Vera el panel de control de Altiplano Resiliente

> **IMPORTANTE:** No cierre la ventana negra mientras usa la aplicacion.
> Si la cierra, el servidor se detendra y la pagina dejara de funcionar.

---

## Paso 4: Configurar las rutas locales

La primera vez que abra la aplicacion, necesita configurar las rutas de carpetas
locales de su computadora:

1. En la barra lateral izquierda, haga clic en **"Rutas Locales"**
2. Complete los campos con las rutas correspondientes a su PC:

| Campo | Descripcion | Ejemplo |
|:------|:------------|:--------|
| FOLDER_C1 | Carpeta de descargas del Componente 1 | `${ONEDRIVE_IUCN}\AR\C1` |
| FOLDER_C2 | Carpeta de descargas del Componente 2 | `${ONEDRIVE_IUCN}\AR\C2` |
| FOLDER_C3 | Carpeta de descargas del Componente 3 | `${ONEDRIVE_IUCN}\AR\C3` |
| WORKSPACE_PATH | Carpeta de trabajo de ArcGIS Pro | `${ONEDRIVE_DATAME}\ArcGIS\Projects\AR` |
| APRX | Ruta al archivo de proyecto ArcGIS Pro | `${ONEDRIVE_DATAME}\AR.aprx` |
| CSVPOINT_TO_GDB | Geodatabase para puntos (fallback Excel) | `${ONEDRIVE_DATAME}\AR_Points.gdb` |

3. Haga clic en **"Guardar"**

> **Marcadores `${ONEDRIVE_*}`**: El sistema detecta automaticamente las
> carpetas `OneDrive - IUCN…` y `OneDrive - DataME` bajo su perfil de Windows,
> sin importar la letra de unidad (E:, C:, D:, …). Esto permite que la misma
> configuracion funcione cuando trabaja en distintas PCs o cuando OneDrive
> cambia de letra.
>
> Soportado: `${ONEDRIVE_DATAME}` y `${ONEDRIVE_IUCN}`. Si OneDrive no esta
> sincronizado, escriba la ruta completa manualmente (ej. `C:\AR\C1`).

---

## Uso diario

### Abrir la aplicacion

1. Doble clic en **`run.bat`**
2. Abrir el navegador en **http://localhost:5000**

### Cerrar la aplicacion

1. Vaya a la ventana negra (terminal)
2. Presione **Ctrl + C**
3. Cierre la ventana

### Flujo de trabajo

La aplicacion guia el proceso de actualizacion en los siguientes pasos:

| Paso | Que hace | Como |
|:----:|:---------|:-----|
| 1-a | Conecta a AGOL y diagnostica AGOL vs Smartsheet | Clic en "Conectar AGOL", luego "Diagnosticar" |
| 1 | Saneamiento de datos de Smartsheet + bucle agente | Automatico — botones del Paso 1 |
| 1b | Descarga shapefiles ZIP o fallback Excel→puntos | Automatico — incluye script para ArcGIS Pro |
| 3 | Genera scripts para ArcGIS Pro (merge, limpieza, etc.) | Copie el script y peguelo en ArcGIS Pro |
| 4 | Publica datos en ArcGIS Online y verifica 3 fuentes | Copie el script y peguelo en ArcGIS Pro |
| 5 | Genera el archivo Excel maestro y recibe Dafne M&E | Automatico |
| 6 | Actualiza el dashboard de Power BI y compara M&E | Copie el script y ejecutelo |
| 7 | Genera reportes y crea respaldos | Automatico |

> **Nota:** Paso 2 (Control Cruzado) fue eliminado. El control real se hace en
> el diagnostico del Paso 1-a y en la verificacion de 3 fuentes del Paso 4.

### Cambio de idioma

En la barra superior hay un toggle **ES / EN**. La preferencia se guarda en el
navegador. Los scripts ArcPy generados tambien respetan el idioma activo.

> **Recomendación de lectura para operación real:** Después de instalar, no use
> esta guía como único material. Continúe con `WORKFLOW_STEPS.md`,
> `MANUAL_OPERATIVO_NO_TECNICO.md` y `GUIA_CAPACITACION_OPERATIVA.md`.

---

## Solucion de problemas

### "No se reconoce Python"
- Python no esta instalado o no se agrego al PATH
- Reinstale Python marcando la casilla **"Add Python to PATH"**

### "No se encontro .venv"
- Ejecute `setup.bat` antes de `run.bat`

### "No se encontro .env"
- Ejecute `setup.bat` para crear el archivo de configuracion

### La pagina no carga en el navegador
- Verifique que la ventana negra esta abierta y dice "Running on http://localhost:5000"
- Intente cerrar y volver a abrir el navegador
- Verifique que no haya otro programa usando el puerto 5000

### ArcGIS Pro no se detecta
- Asegurese de que ArcGIS Pro esta instalado
- Ejecute `setup.bat` nuevamente despues de instalar ArcGIS Pro

### Los scripts de ArcPy no funcionan
- Asegurese de pegarlos en la ventana **Python** de ArcGIS Pro (no en el Notebook)
- Verifique que las rutas locales esten bien configuradas en "Rutas Locales"

### La aplicacion dice "Path outside allowed directories"
- Las rutas configuradas en "Rutas Locales" definen los directorios permitidos
- Asegurese de que las carpetas de descarga y respaldo esten dentro de las rutas configuradas
- Si necesita usar una carpeta diferente, agreguelo primero en la configuracion de Rutas Locales

### Error al extraer archivos ZIP
- El sistema verifica que los archivos ZIP sean seguros antes de extraerlos
- Si ve "ZIP member escapes target directory", el archivo ZIP puede estar corrupto
- Pida al reportero que reenvie el archivo ZIP

---

## Configuracion avanzada

### Variable de entorno `FLASK_DEBUG`

Por defecto, el modo debug esta **desactivado**. Si necesita activar el modo debug
para diagnosticar problemas (solo para desarrollo):

1. Abra el archivo `.env` con un editor de texto
2. Agregue la linea: `FLASK_DEBUG=1`
3. Reinicie la aplicacion (cierre y vuelva a abrir `run.bat`)

> **Importante:** No deje `FLASK_DEBUG=1` activado en uso normal.
> El modo debug muestra informacion tecnica detallada que no es necesaria para el uso diario.

---

## Estructura de archivos importantes

```
altiplano-me/
|
|-- setup.bat          <-- Ejecutar UNA VEZ para instalar
|-- run.bat            <-- Ejecutar CADA VEZ para iniciar la app
|-- .env               <-- Credenciales y configuracion (NO compartir)
|
|-- app.py             <-- Servidor (no modificar)
|-- templates/         <-- Interfaz web (no modificar)
|-- static/            <-- Estilos y scripts web (no modificar)
```

> **Regla importante:** No modifique ningun archivo del programa.
> Toda la configuracion se hace a traves de `setup.bat` y la interfaz web.

---

## Contacto y soporte

Si tiene problemas con la instalacion o el uso de la herramienta,
contacte al administrador del equipo que le proporciono las credenciales.
