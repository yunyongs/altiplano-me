"""
env_paths.py — Portable OneDrive path resolution for the AR dashboard.

Different PCs mount OneDrive on different drive letters (E:, C:, D:, …),
so the ``.env`` file uses ``${ONEDRIVE_DATAME}``, ``${ONEDRIVE_IUCN}`` etc.
placeholders.  When the Flask app starts, ``apply_onedrive_placeholders()``
discovers the actual OneDrive roots on the current PC and expands every
matching ``${...}`` token inside ``os.environ``.

/ Diferentes PCs montan OneDrive en distintas letras de unidad, por eso
``.env`` usa marcadores ``${ONEDRIVE_DATAME}`` etc. y ``apply_onedrive_placeholders``
los sustituye por la ruta real en cada PC.

Detection sources (in order) / Fuentes de detección (en orden):
  1. The ``ONEDRIVE_*`` env var, if already set (manual override)
  2. ``%OneDriveCommercial%`` (work tenant) / ``%OneDrive%`` (default tenant)
     when the trailing folder matches the requested suffix
  3. Scan ``%USERPROFILE%`` for directories whose name starts with
     ``"OneDrive - "`` followed by the requested organisation
"""
from __future__ import annotations

import os
import re
from pathlib import Path


# Mapping: placeholder name → list of organisation-name fragments to look for
# under ``%USERPROFILE%\OneDrive - <org>``.  The first folder whose name
# contains any fragment (case-insensitive) wins.
# / Marcador → lista de fragmentos de nombre de organización a buscar.
_ONEDRIVE_PLACEHOLDERS: dict[str, list[str]] = {
    "ONEDRIVE_DATAME": ["DataME"],
    "ONEDRIVE_IUCN": [
        "IUCN International Union for Conservation of Nature",
        "IUCN",
    ],
}


def _candidate_onedrive_roots() -> list[Path]:
    """Return directories that look like ``OneDrive - <org>`` folders.

    Searches:
      - ``%USERPROFILE%`` (the standard OneDrive install location)
      - The parent directory of any ``%OneDrive*%`` env var (covers the
        case where OneDrive lives at a drive root like ``E:\\``)

    / Busca carpetas ``OneDrive - <org>`` en %USERPROFILE% y en el directorio
    padre de las variables ``%OneDrive*%`` (cubre el caso de OneDrive en la
    raíz de una unidad como ``E:\\``).
    """
    bases: list[Path] = []
    profile = os.environ.get("USERPROFILE") or os.path.expanduser("~")
    if profile:
        bases.append(Path(profile))
    for env_name in ("OneDriveCommercial", "OneDrive", "OneDriveConsumer"):
        val = os.environ.get(env_name)
        if val:
            parent = Path(val).parent
            if parent not in bases:
                bases.append(parent)

    out: list[Path] = []
    seen: set[Path] = set()
    for base in bases:
        if not base.is_dir():
            continue
        try:
            for entry in base.iterdir():
                if not entry.is_dir():
                    continue
                if not entry.name.lower().startswith("onedrive"):
                    continue
                resolved = entry.resolve()
                if resolved in seen:
                    continue
                seen.add(resolved)
                out.append(entry)
        except OSError:
            continue
    return out


def detect_onedrive_root(placeholder: str) -> str | None:
    """Return the absolute path of the OneDrive folder for *placeholder*.

    Returns ``None`` if no candidate is found.  The result is **not** cached —
    callers that need to detect path renames at runtime can re-invoke it.

    / Devuelve la ruta absoluta de la carpeta OneDrive para *placeholder*,
    o ``None`` si no se encuentra ningún candidato.
    """
    fragments = _ONEDRIVE_PLACEHOLDERS.get(placeholder, [])

    # 1. Manual override / Anulación manual
    direct = os.environ.get(placeholder)
    if direct and os.path.isdir(direct):
        return direct

    # 2. Windows built-in vars (work / personal tenants)
    # / Variables integradas de Windows (cuentas comerciales / personales)
    for env_name in ("OneDriveCommercial", "OneDrive", "OneDriveConsumer"):
        candidate = os.environ.get(env_name)
        if not candidate or not os.path.isdir(candidate):
            continue
        folder_name = os.path.basename(candidate.rstrip("\\/"))
        if not fragments:
            return candidate
        if any(frag.lower() in folder_name.lower() for frag in fragments):
            return candidate

    # 3. Scan %USERPROFILE% and OneDrive parent dirs
    # / Recorrer %USERPROFILE% y carpetas padre de OneDrive
    for root in _candidate_onedrive_roots():
        folder_name = root.name
        if not fragments:
            return str(root)
        if any(frag.lower() in folder_name.lower() for frag in fragments):
            return str(root)

    return None


_PLACEHOLDER_RE = re.compile(r"\$\{([A-Z_][A-Z0-9_]*)\}")


def expand_placeholders(value: str, lookup: dict[str, str]) -> str:
    """Replace every ``${NAME}`` in *value* using *lookup*.

    Unknown placeholders are left untouched (so downstream code can decide
    whether to raise).  Quotes around the original value are stripped to
    match python-dotenv semantics.
    / Reemplaza ``${NAME}`` en *value* usando *lookup*. Los marcadores
    desconocidos se dejan tal cual.
    """
    if value is None:
        return value
    stripped = value.strip().strip('"').strip("'")

    def repl(match: re.Match) -> str:
        key = match.group(1)
        return lookup.get(key, match.group(0))

    return _PLACEHOLDER_RE.sub(repl, stripped)


def apply_onedrive_placeholders(env: dict | None = None) -> dict[str, str]:
    """Expand OneDrive placeholders inside *env* (defaults to ``os.environ``).

    Detected roots are also published as actual env vars so other modules
    (and child ArcPy processes spawned via ``subprocess.run``) can resolve
    them without re-running detection.

    Returns the mapping of placeholder → detected root (with ``""`` for
    placeholders that could not be resolved).
    / Expande los marcadores OneDrive en *env* y devuelve el mapeo
    marcador → raíz detectada.
    """
    target = os.environ if env is None else env

    detected: dict[str, str] = {}
    # Only resolved roots feed the expansion table — unresolved placeholders
    # stay literal so the operator can spot the missing OneDrive in the UI.
    # / Solo las raíces resueltas se usan en la expansión; los marcadores
    # sin resolver se conservan para que el operador los detecte.
    expansion_lookup: dict[str, str] = {}
    for placeholder in _ONEDRIVE_PLACEHOLDERS:
        root = detect_onedrive_root(placeholder) or ""
        detected[placeholder] = root
        if root:
            target[placeholder] = root
            expansion_lookup[placeholder] = root

    for key, raw in list(target.items()):
        if not isinstance(raw, str) or "${" not in raw:
            continue
        expanded = expand_placeholders(raw, expansion_lookup)
        if expanded != raw:
            target[key] = expanded

    return detected
