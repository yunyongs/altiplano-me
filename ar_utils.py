"""
Pure utility functions extracted from Jupyter notebooks for testability.

Sources:
  - 02_ArcGIS_MapUpdater/2_1_AR_Ssheet_to_ArcGIS.ipynb
  - 02_ArcGIS_MapUpdater/2_2_AR_Oficial_ArcPy.ipynb
  - 01_Ssheet_DataCollect/1_1_AR_Ssheet_Automation.ipynb
"""
from __future__ import annotations

import os
import pathlib
import re
import time as _time
import unicodedata
import zipfile

import requests as _requests


# ---------------------------------------------------------------------------
# Path safety  /  Seguridad de rutas
# ---------------------------------------------------------------------------

def safe_resolve(user_path: str, allowed_roots: list[str]) -> pathlib.Path:
    """Resolve user_path and verify it falls under one of allowed_roots.

    Raises ValueError if path escapes allowed directories.
    / Resuelve user_path y verifica que esté dentro de allowed_roots.
    Lanza ValueError si la ruta escapa de los directorios permitidos.
    """
    if not user_path or not user_path.strip():
        raise ValueError("Empty path")
    resolved = pathlib.Path(user_path).resolve()
    for root in allowed_roots:
        root_resolved = pathlib.Path(root).resolve()
        if resolved == root_resolved or str(resolved).startswith(str(root_resolved) + os.sep):
            return resolved
    raise ValueError(f"Path outside allowed directories: {resolved}")


# ---------------------------------------------------------------------------
# Classification / mapping helpers  (from 2_1_AR_Ssheet_to_ArcGIS.ipynb)
# ---------------------------------------------------------------------------

_TRATAMIENTO = [
    "Balanyá", "Cotoyá", "Eschaquichoj", "Espumpujá", "Joj", "La Unión",
    "Mactzul", "Paguisis", "Paxocol", "Pinut", "Pixcayá 1",
    "Pixcayá-Papumay", "Puxal", "Quiejel", "Sacabaj", "SacGuexá",
    "Sacputub A", "Sepelá 1", "Sepelá 2", "Sigüilá", "Tzunamá",
    "Xayá-Coyolate", "Xepocol", "Xequijel",
]

_CONTROL = [
    "Arriquib 196", "Chacap 157", "El Arco 176", "El Tumbadero 177",
    "Motagua Alto 156", "Pabacul 112", "Pachita 183", "Samalá 151",
    "Samalá 166", "Sepelá 154",
]


def trata(microcuenca: str) -> str:
    """Classify a microcuenca as TRATAMIENTO, CONTROL, or empty string."""
    if microcuenca in _TRATAMIENTO:
        return "TRATAMIENTO"
    if microcuenca in _CONTROL:
        return "CONTROL"
    return ""


def id_area(area: str) -> int:
    """Map an area type string to its numeric ID."""
    mapping = {"Influence": 3, "Intervention": 2, "Prioritized": 1}
    return mapping.get(area, 0)


_ABE_ENG_MAP = {
    "Sistema Agroforestal | Cultivos anuales": "1. AFS w annual Crops",
    "Sistema Agroforestal | Cultivos perennes": "1. AFS w perennial Crops",
    "Sistema Silvopastoril": "Silvopastoril system",
    "Plantaciones Forestales": "2. Forest plantation",
    "Bosque Natural con Fines de Producción": "2. Natural forest production",
    "Bosque Natural con Fines de Protección": "3. Natural forest protection",
    "Reforestación con Fines de Restauración": "3. Natural forest restoration",
}


def abe_eng(abe_value: str) -> str:
    """Translate a Spanish AbE type to its English description."""
    return _ABE_ENG_MAP.get(abe_value, "")


_ABE_ABBR_MAP = {
    # 8 valid AbE categories / 8 categorías válidas AbE
    "Sistema Agroforestal | Cultivos anuales": "anual",
    "Sistema Agroforestal | Cultivos perennes": "peren",
    "Sistema Silvopastoril": "silvo",
    "Plantaciones Forestales": "plant",
    "Bosque Natural con Fines de Producción": "produ",
    "Bosque Natural con Fines de Protección": "prote",
    "Reforestación con Fines de Restauración": "refor",
    "Sistema Agroforestal | Conservación de suelo y agua": "sueloyagua",
    "Conservación de suelo y agua | Sistema Agroforestal": "sueloyagua",
}

# Short/common variants that map to a canonical abbreviation
# / Variantes cortas/comunes que mapean a una abreviación canónica
_ABE_VARIANT_MAP = {
    "forestal": "plant",           # shortened "Plantaciones Forestales"
    "reforestacion": "refor",      # missing accent
    "silvopastoril": "silvo",      # without "Sistema"
}

# Pre-built normalised lookup: built lazily after normalize() is defined
# / Lookup normalizado preconstruido: construido perezosamente
_ABE_NORM_MAP: dict[str, str] = {}


def _ensure_norm_map() -> dict[str, str]:
    """Build the normalised ABE map on first use."""
    if not _ABE_NORM_MAP:
        _ABE_NORM_MAP.update({normalize(k): v for k, v in _ABE_ABBR_MAP.items()})
    return _ABE_NORM_MAP


def abe(abe_long: str) -> str:
    """Abbreviate a Spanish AbE type to a 5-character code.

    Matching order / Orden de coincidencia:
      1. Exact match / Coincidencia exacta
      2. Normalised match (accent-stripped, lowercase) / Normalizado (sin acentos, minúsculas)
      3. Known short variants / Variantes cortas conocidas
      4. Partial match (normalised input contains a known key) / Coincidencia parcial
    Falls back to ``"error"`` if nothing matches.
    """
    if not abe_long or not isinstance(abe_long, str):
        return "error"

    # 1. Exact match / Coincidencia exacta
    exact = _ABE_ABBR_MAP.get(abe_long)
    if exact:
        return exact

    # 2. Normalised match / Coincidencia normalizada
    norm = normalize(abe_long)
    norm_map = _ensure_norm_map()
    norm_hit = norm_map.get(norm)
    if norm_hit:
        return norm_hit

    # 3. Known short variants / Variantes cortas conocidas
    variant_hit = _ABE_VARIANT_MAP.get(norm)
    if variant_hit:
        return variant_hit

    # 4. Partial match — normalised input contains a canonical key
    # / Coincidencia parcial — entrada normalizada contiene una clave canónica
    for key, abbr in norm_map.items():
        if key in norm or norm in key:
            return abbr

    return "error"


def validate_abe(abe_value: str | None) -> dict:
    """Check whether an ABE value from Smartsheet is valid.
    / Verificar si un valor AbE de Smartsheet es válido.

    Returns:
        {
          "valid": bool,
          "abbr":  str or None,    # abbreviation if valid
          "value": str,            # original value
          "message": str or None,  # human-readable error if invalid
        }
    """
    if not abe_value or not isinstance(abe_value, str) or not abe_value.strip():
        return {
            "valid": False, "abbr": None, "value": abe_value or "",
            "message": "AbE vacío / AbE is empty",
        }
    abbr = abe(abe_value)
    if abbr != "error":
        return {"valid": True, "abbr": abbr, "value": abe_value, "message": None}
    return {
        "valid": False, "abbr": None, "value": abe_value,
        "message": (
            f"Valor AbE no válido: \"{abe_value}\" — "
            "corrija en Smartsheet / Invalid AbE value — fix in Smartsheet"
        ),
    }


def grants(contrato_org: str | None) -> str:
    """Map a contract-org code (e.g. 'XX-PPD-YY') to grant size label."""
    if contrato_org is None:
        return ""
    split_values = contrato_org.split("-")
    if len(split_values) < 2:
        return ""
    if split_values[1] == "PPD":
        return "Small Grants"
    if split_values[1] == "PMD":
        return "Medium Grants"
    return ""


def cada_punto(total, parcelas):
    """Compute area per beneficiary point (total / parcelas)."""
    if parcelas is None:
        return None
    return total / parcelas


# ---------------------------------------------------------------------------
# Text normalisation  (from 2_2_AR_Oficial_ArcPy.ipynb)
# ---------------------------------------------------------------------------

def normalize(text: str | None) -> str:
    """Remove accents and convert to lowercase ASCII."""
    return (
        unicodedata.normalize("NFKD", text or "")
        .encode("ASCII", "ignore")
        .decode("ASCII")
        .lower()
    )


# ---------------------------------------------------------------------------
# Shapefile helpers  (from 1_1_AR_Ssheet_Automation.ipynb)
# ---------------------------------------------------------------------------

def sanitize_shapefile_basename(name: str) -> str:
    """Replace dots and special characters with underscores for ArcGIS."""
    sanitized = name.replace(".", "_")
    sanitized = re.sub(r"[^A-Za-z0-9_\-]", "_", sanitized)
    return sanitized


def is_shape_zip_attachment(name: str) -> bool:
    """Check whether a filename looks like a shapefile zip archive.

    Includes .zip files with 'shape', 'shp', 'area', or 'área' in the name,
    as well as files whose name contains a known AbE keyword (e.g. SAF,
    perennes, proteccion).
    Excludes files with 'annexo'/'anexo' UNLESS the name also contains a
    shape-specific keyword (saf, puntos, poligonos, shp, shape).
    """
    lower = (name or "").lower()
    if not lower.endswith(".zip"):
        return False
    stem = lower.rsplit(".", 1)[0]
    has_anexo = "annexo" in lower or "anexo" in lower
    # Direct shape/area keywords — always match even inside anexo names
    if re.search(r"shp|shape|area|área|puntos|poligonos|polígonos", lower):
        return True
    # AbE keyword detection (e.g. SAF_perennes_y_anuales.zip)
    norm = re.sub(r"[^a-z0-9]", "", stem).upper()
    for keyword, _ in _FILENAME_ABE_HINTS:
        if keyword in norm:
            return True
    # Exclude generic anexo files that didn't match any AbE keyword
    if has_anexo:
        return False
    return False


def is_c1_row_shape_zip(
    name: str,
    total_zip_count: int,
    has_hectares: bool,
    has_abe: bool,
) -> bool:
    """Row-aware shape ZIP detection for C1 attachments.

    / Detección de ZIP de shapefile consciente del contexto de la fila C1.

    Decision rules / Reglas de decisión:
      1. If ``is_shape_zip_attachment(name)`` matches by keyword → ``True``
         (filename evidence is already strong enough).
      2. Otherwise, treat the ZIP as a shapefile when ALL of:
           - the row has exactly one ``.zip`` attachment
           - ``TOTAL DE HECTÁREAS`` has a value
           - ``ACCIONES DE RESTAURACIÓN AbE`` has a value
         These three signals together indicate the row is geometry-bearing
         even when the user uploaded a ZIP with a non-descriptive name.

    The second branch is intentionally conservative — it only fires when
    there is a single ZIP candidate per row, so it cannot pick up the
    wrong file when multiple ZIPs are attached.
    / La segunda rama solo se activa con un único ZIP por fila para no
    elegir el archivo incorrecto cuando hay varios adjuntos.
    """
    if not (name or "").lower().endswith(".zip"):
        return False
    if is_shape_zip_attachment(name):
        return True
    return total_zip_count == 1 and has_hectares and has_abe


# ---------------------------------------------------------------------------
# ABE hint extraction from original attachment filenames
# / Extracción de pista AbE del nombre de archivo original
# ---------------------------------------------------------------------------

# Keyword → canonical ABE abbreviation.  Matched against the uppercase,
# dot-stripped, accent-stripped original ZIP filename.
# / Palabra clave → abreviación canónica AbE.
_FILENAME_ABE_HINTS: list[tuple[str, str]] = [
    # Order matters: more specific patterns first / Orden importa: patrones más específicos primero
    ("SUELOYAGUA", "sueloyagua"),
    ("AGUAYSUELO", "sueloyagua"),
    ("CS", "sueloyagua"),          # common abbreviation for Conservación de suelo y agua
    ("ANUAL", "anual"),            # Cultivos anuales
    ("PEREN", "peren"),            # Cultivos perennes
    ("SILVO", "silvo"),            # Sistema Silvopastoril
    ("PLANT", "plant"),            # Plantaciones Forestales
    ("FORESTAL", "plant"),
    ("PRODU", "produ"),            # Bosque Natural — Producción
    ("PROTE", "prote"),            # Bosque Natural — Protección
    ("BNP", "prote"),              # abbreviation "BN Protección"
    ("REFOR", "refor"),            # Reforestación
    ("SAF", "saf"),                # SAF = Sistema AgroForestal (generic, matches any SAF subtype)
]


def extract_abe_hint_from_filename(name: str) -> str:
    """Extract an ABE abbreviation hint from the original attachment filename.

    Scans the filename (without extension) for known ABE keyword fragments.
    Returns the canonical abbreviation (e.g. ``"anual"``, ``"sueloyagua"``)
    or ``""`` if no hint is found.

    / Extrae una pista de AbE del nombre original del archivo adjunto.
    Retorna la abreviación canónica o cadena vacía si no se detecta.

    Examples:
        >>> extract_abe_hint_from_filename("SHP_Q4_CS_AYUDAGT.zip")
        'sueloyagua'
        >>> extract_abe_hint_from_filename("SHP_Q4_SAF.ANUALAYUDAGT.zip")
        'anual'
        >>> extract_abe_hint_from_filename("random_file.zip")
        ''
    """
    if not name or not isinstance(name, str):
        return ""
    # Strip extension and normalise: uppercase, remove dots/hyphens/underscores
    stem = os.path.splitext(name)[0].upper()
    # Keep only alphanumerics for matching
    norm = re.sub(r"[^A-Z0-9]", "", stem)
    for keyword, abbr in _FILENAME_ABE_HINTS:
        if keyword in norm:
            return abbr
    return ""


def extract_hectares_from_filename(name: str) -> float | None:
    """Extract a hectare value from a ZIP filename containing 'ha'.

    Recognises patterns like ``SAF_23.60 ha.zip``, ``BNProteccion 5.17 ha.zip``,
    ``Shape_plantacion 21.49 ha.zip``.  Returns the numeric value or ``None``.

    / Extrae el valor de hectáreas de un nombre de archivo ZIP que contiene 'ha'.
    Retorna el valor numérico o None.

    Examples:
        >>> extract_hectares_from_filename("SAF_23.60 ha.zip")
        23.6
        >>> extract_hectares_from_filename("BNProteccion 5.17 ha.zip")
        5.17
        >>> extract_hectares_from_filename("random_file.zip")
    """
    if not name or not isinstance(name, str):
        return None
    lower = (name or "").lower()
    if not lower.endswith(".zip"):
        return None
    stem = lower.rsplit(".", 1)[0]  # remove .zip
    # Match number (possibly with decimals) followed by optional space + "ha"
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*ha\b", stem)
    if m:
        return float(m.group(1).replace(",", "."))
    return None


def find_shapefiles(folder: str) -> list[str]:
    """Walk *folder* and return paths of all .shp files found."""
    shapefiles = []
    for root, _, files in os.walk(folder):
        for f in files:
            if f.lower().endswith(".shp"):
                shapefiles.append(os.path.join(root, f))
    return shapefiles


def is_area_excel_attachment(name: str) -> bool:
    """Check whether a filename looks like an *area* Excel workbook.

    Used as a fallback when a row has no shapefile ZIP attachment: an
    Excel file whose name contains area/hectare-related keywords is
    treated as a point-list source (X, Y, Area, Beneficiario).

    / Verifica si un archivo es un Excel de áreas (fallback cuando no
    hay shapefile adjunto).
    """
    lower = (name or "").lower()
    if not (lower.endswith(".xls") or lower.endswith(".xlsx")):
        return False
    keywords = ("área", "area", "areas", "áreas", "hectares", "_ha",
                "_ha.", " ha ", "_has_", "_reas_", "puntos")
    return any(term in lower for term in keywords)


# ---------------------------------------------------------------------------
# Pure-Python shapefile introspection (no arcpy required)
# / Inspección de shapefile sin arcpy
# ---------------------------------------------------------------------------

# .shp header shape type → human label
_SHP_GEOM_TYPES = {
    0: "null", 1: "point", 3: "polyline", 5: "polygon", 8: "multipoint",
    11: "point", 13: "polyline", 15: "polygon", 18: "multipoint",  # Z variants
    21: "point", 23: "polyline", 25: "polygon", 28: "multipoint",  # M variants
}


def read_shp_geometry_type(shp_path: str) -> str:
    """Read the geometry type from a .shp file header (bytes 32-35).
    Returns 'point', 'polygon', 'polyline', 'multipoint', or 'unknown'.
    / Lee el tipo de geometría del encabezado .shp. Sin arcpy.
    """
    import struct
    try:
        with open(shp_path, "rb") as f:
            f.seek(32)
            raw = f.read(4)
            if len(raw) < 4:
                return "unknown"
            shape_type = struct.unpack("<i", raw)[0]
            return _SHP_GEOM_TYPES.get(shape_type, "unknown")
    except OSError:
        return "unknown"


def read_dbf_field_value(dbf_path: str, field_pattern: str) -> str | None:
    """Read the first non-empty value of a field matching *field_pattern* from a .dbf file.
    Pure Python — no external DBF library needed.
    / Lee el primer valor no vacío de un campo que coincida con field_pattern en un .dbf.

    Args:
        dbf_path: path to the .dbf file
        field_pattern: regex pattern to match against field names (case-insensitive)
    Returns:
        The decoded string value, or None if the field or value is not found.
    """
    import struct
    try:
        with open(dbf_path, "rb") as f:
            # DBF header
            header = f.read(32)
            if len(header) < 32:
                return None
            num_records = struct.unpack("<I", header[4:8])[0]
            header_size = struct.unpack("<H", header[8:10])[0]
            record_size = struct.unpack("<H", header[10:12])[0]

            # Read field descriptors (32 bytes each, terminated by 0x0D)
            fields: list[tuple[str, int, int]] = []  # (name, offset, length)
            offset = 1  # skip deletion flag byte
            while True:
                desc = f.read(32)
                if len(desc) < 32 or desc[0] == 0x0D:
                    break
                fname = desc[:11].split(b"\x00")[0].decode("ascii", errors="replace").strip()
                flen = desc[16]
                fields.append((fname, offset, flen))
                offset += flen

            # Find matching field
            pat = re.compile(field_pattern, re.IGNORECASE)
            target = None
            for fname, foffset, flen in fields:
                if pat.search(fname):
                    target = (foffset, flen)
                    break
            if target is None:
                return None

            # Read records until we find a non-empty value
            f.seek(header_size)
            foffset, flen = target
            for _ in range(min(num_records, 100)):  # check first 100 rows max
                rec = f.read(record_size)
                if len(rec) < record_size:
                    break
                raw = rec[foffset:foffset + flen]
                # Try common encodings / Probar codificaciones comunes
                for enc in ("utf-8", "latin-1", "cp1252"):
                    try:
                        val = raw.decode(enc).strip()
                        break
                    except (UnicodeDecodeError, ValueError):
                        val = ""
                if val:
                    return val
        return None
    except OSError:
        return None


# ---------------------------------------------------------------------------
# ZIP extraction and validation
# ---------------------------------------------------------------------------

_REQUIRED_EXTENSIONS = {".shp", ".shx", ".dbf", ".prj"}


def extract_and_validate_zip(
    zip_path: str, dest_folder: str
) -> dict:
    """Extract a shapefile ZIP and validate that companion files exist.

    Returns a dict with keys: ``ok``, ``shapefiles``, ``errors``.
    """
    result: dict = {"ok": True, "shapefiles": [], "errors": []}
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            dest_path = pathlib.Path(dest_folder).resolve()
            for member in zf.infolist():
                member_target = (dest_path / member.filename).resolve()
                if member_target != dest_path and not str(member_target).startswith(str(dest_path) + os.sep):
                    return {"ok": False, "shapefiles": [], "errors": [f"ZIP member escapes target directory: {member.filename}"]}
            zf.extractall(dest_folder)
    except (zipfile.BadZipFile, OSError) as exc:
        return {"ok": False, "shapefiles": [], "errors": [str(exc)]}

    shp_files = find_shapefiles(dest_folder)
    if not shp_files:
        return {"ok": False, "shapefiles": [], "errors": ["No .shp file found in ZIP"]}

    for shp in shp_files:
        base = os.path.splitext(shp)[0]
        missing = [ext for ext in _REQUIRED_EXTENSIONS if not os.path.exists(base + ext)]
        if missing:
            result["errors"].append(f"{os.path.basename(shp)}: missing {', '.join(missing)}")
            result["ok"] = False
        result["shapefiles"].append(shp)

    return result



# ---------------------------------------------------------------------------
# Streaming download helper  /  Descarga en streaming
# ---------------------------------------------------------------------------

def stream_download_to_file(url: str, dest_path: str, timeout: int = 60,
                             chunk_size: int = 8192) -> bool:
    """Download a URL to a file using streaming to avoid memory spikes.
    / Descargar una URL a un archivo usando streaming para evitar picos de memoria.

    Returns True on success, raises on failure.
    """
    r = _requests.get(url, timeout=timeout, stream=True)
    r.raise_for_status()
    with open(dest_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=chunk_size):
            if chunk:
                f.write(chunk)
    return True


# ---------------------------------------------------------------------------
# Smartsheet API retry wrapper
# ---------------------------------------------------------------------------

def smartsheet_request(method: str, url: str, **kwargs) -> _requests.Response:
    """Smartsheet API request with exponential backoff on 429 and transient errors."""
    max_retries = 3
    resp = None
    for attempt in range(max_retries + 1):
        try:
            resp = _requests.request(method, url, **kwargs)
            if resp.status_code == 429 and attempt < max_retries:
                retry_after = int(resp.headers.get("Retry-After", 2 ** attempt))
                _time.sleep(min(retry_after, 30))
                continue
            return resp
        except _requests.exceptions.ConnectionError:
            if attempt < max_retries:
                _time.sleep(2 ** attempt)
                continue
            raise
    return resp  # Return last response
