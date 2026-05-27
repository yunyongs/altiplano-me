"""
PASO 5 — Dafne M&E data reception and BasePath placement.

G11: place_dafne_file, validate_integrado_xlsx, get_integrado_status
G7:  receive_me_data, get_reception_history, list_reception_quarters

Workflow:
  1. validate_integrado_xlsx(file_path)  — check required sheets/columns
  2. place_dafne_file(src, base_path)    — copy to PBI BasePath with backup
  3. receive_me_data(...)                — records history entry to JSON log

History is written to:
  data/me_reception/{quarter}_history.json
"""
from __future__ import annotations

import json
import os
import pathlib
import shutil
from datetime import datetime
from typing import Optional

from ar_utils import safe_resolve

# ES: Directorio raíz del proyecto / EN: Project root directory
_PROJECT_ROOT = pathlib.Path(__file__).parent

# ES: Directorio de historial de recepciones / EN: Reception history directory
_HISTORY_DIR = _PROJECT_ROOT / "data" / "me_reception"


def _allowed_roots() -> list[str]:
    """Gather allowed filesystem roots from .env configuration."""
    roots = [str(_PROJECT_ROOT / "downloads")]
    for key in ("WORKSPACE_PATH", "FOLDER_C1", "FOLDER_C2", "FOLDER_C3",
                "SMARTSHEET_ATTACH_DIR", "CSVPOINT_TO_GDB"):
        val = os.getenv(key, "")
        if val:
            roots.append(val)
    return roots

# ES: Hojas requeridas en Tbl_Integrado.xlsx / EN: Required sheets in Tbl_Integrado.xlsx
REQUIRED_SHEETS = ["Tbl_Actvdd_m_e_data", "Tbl_Beneficiarios", "Tbl_Org"]

# ES: Nombre por defecto del archivo M&E / EN: Default M&E filename
DEFAULT_FILENAME = "Tbl_Integrado.xlsx"


# ─────────────────────────────────────────────────────────────────────────────
# G11: File placement
# ─────────────────────────────────────────────────────────────────────────────

def place_dafne_file(
    src_path: str,
    base_path: str,
    filename: str = DEFAULT_FILENAME,
    allowed_roots: list[str] | None = None,
) -> dict:
    """
    Copy src_path to base_path/filename (Power BI BasePath).
    If a file already exists at the destination, it is backed up as
    .bak_{timestamp} before being overwritten.

    Args:
        src_path:  Absolute path to the source Tbl_Integrado.xlsx.
        base_path: Target directory (Power BI BasePath parameter).
        filename:  Destination filename (default "Tbl_Integrado.xlsx").

    Returns:
        {
            "success": bool,
            "dest":    str   — absolute destination path,
            "backup":  str | None — path of backup file created (or None),
            "error":   str | None
        }

    # ES: Copia el archivo al BasePath de Power BI, creando backup si ya existe.
    # EN: Copies file to Power BI BasePath, creating a .bak backup if it exists.
    """
    # Validate paths against allowed directories
    roots = allowed_roots if allowed_roots is not None else _allowed_roots()
    try:
        safe_resolve(src_path, roots)
        safe_resolve(base_path, roots)
    except ValueError:
        return {
            "success": False,
            "dest": "",
            "backup": None,
            "error": "Path outside allowed directories / Ruta fuera de directorios permitidos",
        }

    src = pathlib.Path(src_path)
    dest_dir = pathlib.Path(base_path)
    dest = dest_dir / filename

    if not src.exists():
        return {
            "success": False,
            "dest": str(dest),
            "backup": None,
            "error": f"Archivo origen no encontrado / Source file not found: {src_path}",
        }

    try:
        os.makedirs(dest_dir, exist_ok=True)
    except OSError as exc:
        return {
            "success": False,
            "dest": str(dest),
            "backup": None,
            "error": f"No se pudo crear el directorio / Could not create directory: {exc}",
        }

    # ES: Hacer backup del archivo existente / EN: Back up existing file
    backup_path: Optional[str] = None
    if dest.exists():
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        bak = dest.with_suffix(f".bak_{ts}")
        try:
            shutil.copy2(str(dest), str(bak))
            backup_path = str(bak)
        except OSError as exc:
            return {
                "success": False,
                "dest": str(dest),
                "backup": None,
                "error": f"No se pudo crear backup / Could not create backup: {exc}",
            }

    try:
        shutil.copy2(str(src), str(dest))
    except OSError as exc:
        return {
            "success": False,
            "dest": str(dest),
            "backup": backup_path,
            "error": f"Error al copiar archivo / File copy error: {exc}",
        }

    return {
        "success": True,
        "dest": str(dest),
        "backup": backup_path,
        "error": None,
    }


def validate_integrado_xlsx(file_path: str) -> dict:
    """
    Validate that Tbl_Integrado.xlsx contains the required sheets.
    Uses openpyxl (read-only mode for performance).

    Required sheets: Tbl_Actvdd_m_e_data, Tbl_Beneficiarios, Tbl_Org

    Returns:
        {
            "valid":          bool,
            "missing_sheets": list[str],
            "found_sheets":   list[str],
            "warnings":       list[str],
            "error":          str | None
        }

    # ES: Valida que el archivo contenga las hojas requeridas por el modelo Power BI.
    # EN: Validates that the file contains the sheets required by the Power BI model.
    """
    fp = pathlib.Path(file_path)
    if not fp.exists():
        return {
            "valid": False,
            "missing_sheets": [],
            "found_sheets": [],
            "warnings": [],
            "error": f"Archivo no encontrado / File not found: {file_path}",
        }

    try:
        import openpyxl
        wb = openpyxl.load_workbook(str(fp), read_only=True, data_only=True)
        found = wb.sheetnames
        wb.close()
    except Exception as exc:  # noqa: BLE001
        return {
            "valid": False,
            "missing_sheets": [],
            "found_sheets": [],
            "warnings": [],
            "error": f"No se pudo abrir el archivo / Could not open file: {exc}",
        }

    missing = [s for s in REQUIRED_SHEETS if s not in found]
    warnings: list[str] = []

    # ES: Advertencia si hay hojas extra no esperadas / EN: Warn if unexpected sheets present
    extra = [s for s in found if s not in REQUIRED_SHEETS]
    if extra:
        warnings.append(
            f"Hojas adicionales encontradas / Additional sheets found: {', '.join(extra)}"
        )

    return {
        "valid": len(missing) == 0,
        "missing_sheets": missing,
        "found_sheets": list(found),
        "warnings": warnings,
        "error": None,
    }


def get_integrado_status(
    base_path: str,
    filename: str = DEFAULT_FILENAME,
) -> dict:
    """
    Check whether Tbl_Integrado.xlsx exists at base_path and return metadata.

    Returns:
        {
            "exists":      bool,
            "path":        str,
            "modified_at": str | None  — ISO timestamp,
            "size_kb":     float | None
        }

    # ES: Verifica si el archivo existe en el BasePath y devuelve metadatos.
    # EN: Checks if the file exists in BasePath and returns metadata.
    """
    target = pathlib.Path(base_path) / filename
    if not target.exists():
        return {
            "exists": False,
            "path": str(target),
            "modified_at": None,
            "size_kb": None,
        }

    stat = target.stat()
    modified_at = datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds")
    size_kb = round(stat.st_size / 1024, 1)

    return {
        "exists": True,
        "path": str(target),
        "modified_at": modified_at,
        "size_kb": size_kb,
    }


# ─────────────────────────────────────────────────────────────────────────────
# G7: Reception workflow
# ─────────────────────────────────────────────────────────────────────────────

def receive_me_data(
    file_path: str,
    quarter: str,
    base_path: str,
    metadata: Optional[dict] = None,
    allowed_roots: list[str] | None = None,
) -> dict:
    """
    Integrated M&E data reception function.

    Steps:
      1. validate_integrado_xlsx(file_path)
      2. place_dafne_file(file_path, base_path)   — only if valid
      3. Record history entry to data/me_reception/{quarter}_history.json

    Args:
        file_path: Path to the received Tbl_Integrado.xlsx.
        quarter:   Quarter identifier (e.g. "T2026_Q2").
        base_path: Power BI BasePath target directory.
        metadata:  Optional extra info (received_by, notes, version_label).

    Returns:
        {
            "success":       bool,
            "validation":    dict  — result of validate_integrado_xlsx,
            "placement":     dict | None — result of place_dafne_file,
            "history_entry": dict  — the entry written to history
        }

    # ES: Función integrada de recepción: valida, coloca y registra el historial.
    # EN: Integrated reception: validates, places the file, and records history.
    """
    ts = datetime.now().isoformat(timespec="seconds")
    meta = metadata or {}

    # Step 1: Validate
    validation = validate_integrado_xlsx(file_path)

    placement: Optional[dict] = None
    success = False

    if validation["valid"]:
        # Step 2: Place
        placement = place_dafne_file(file_path, base_path, allowed_roots=allowed_roots)
        success = placement["success"]
    else:
        placement = None

    # Step 3: Record history regardless of outcome
    history_entry = {
        "received_at": ts,
        "quarter": quarter,
        "file_path": file_path,
        "filename": pathlib.Path(file_path).name,
        "base_path": base_path,
        "valid": validation["valid"],
        "missing_sheets": validation.get("missing_sheets", []),
        "placed": placement["success"] if placement else False,
        "dest": placement["dest"] if placement else None,
        "backup": placement["backup"] if placement else None,
        "received_by": meta.get("received_by", ""),
        "notes": meta.get("notes", ""),
        "version_label": meta.get("version_label", ""),
        "success": success,
    }
    _append_history(quarter, history_entry)

    return {
        "success": success,
        "validation": validation,
        "placement": placement,
        "history_entry": history_entry,
    }


def get_reception_history(quarter: str) -> list[dict]:
    """
    Load reception history for a given quarter.
    Returns entries sorted newest-first.

    # ES: Carga el historial de recepciones de un trimestre.
    # EN: Loads the reception history for a quarter.
    """
    history_file = _HISTORY_DIR / f"{quarter}_history.json"
    if not history_file.exists():
        return []
    try:
        with open(history_file, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return list(reversed(data))
        return []
    except (json.JSONDecodeError, OSError):
        return []


def list_reception_quarters() -> list[str]:
    """
    Return sorted list of quarters that have reception history files.

    # ES: Lista los trimestres con historial de recepción.
    # EN: Lists quarters that have reception history.
    """
    if not _HISTORY_DIR.exists():
        return []
    quarters = []
    for p in _HISTORY_DIR.glob("*_history.json"):
        quarters.append(p.stem.replace("_history", ""))
    return sorted(quarters)


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _append_history(quarter: str, entry: dict) -> None:
    """Append one entry to the quarter history JSON file (creates if absent)."""
    os.makedirs(_HISTORY_DIR, exist_ok=True)
    history_file = _HISTORY_DIR / f"{quarter}_history.json"
    existing: list[dict] = []
    if history_file.exists():
        try:
            with open(history_file, encoding="utf-8") as f:
                existing = json.load(f)
            if not isinstance(existing, list):
                existing = []
        except (json.JSONDecodeError, OSError):
            existing = []
    existing.append(entry)
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
