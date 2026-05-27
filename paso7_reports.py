"""
PASO 7 — Documentation, error reports, and backup management.
"""
from __future__ import annotations

import json
import os
import pathlib
import shutil
from datetime import datetime
from typing import Any

from ar_utils import safe_resolve

_PROJECT_ROOT = pathlib.Path(__file__).parent


def _allowed_roots() -> list[str]:
    """Gather allowed filesystem roots from .env configuration."""
    roots = [str(_PROJECT_ROOT / "downloads")]
    for key in ("WORKSPACE_PATH", "FOLDER_C1", "FOLDER_C2", "FOLDER_C3",
                "SMARTSHEET_ATTACH_DIR", "CSVPOINT_TO_GDB"):
        val = os.getenv(key, "")
        if val:
            roots.append(val)
    return roots


def generate_error_report(
    pipeline_state: dict,
) -> dict[str, Any]:
    """Generate a structured error/duplicate report.

    Returns a dict suitable for JSON serialisation or rendering in the UI.
    """
    report: dict[str, Any] = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "pipeline_errors": pipeline_state.get("errors", []),
        "pipeline_warnings": pipeline_state.get("warnings", []),
        "paso_status": pipeline_state.get("paso_status", {}),
    }

    return report


def generate_data_summary(
    pipeline_state: dict,
) -> dict[str, Any]:
    """Generate a 1-2 page data summary with KPIs and variations.

    Returns a structured dict with sections for rendering.
    """
    summary: dict[str, Any] = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "sections": [],
    }

    # Section 1: Pipeline status
    paso_status = pipeline_state.get("paso_status", {})
    completed = sum(1 for v in paso_status.values() if v == "success")
    total = len(paso_status)
    summary["sections"].append({
        "title": "Estado del Pipeline",
        "content": {
            "completed": completed,
            "total": total,
            "started_at": pipeline_state.get("started_at"),
            "completed_at": pipeline_state.get("completed_at"),
            "paso_detail": paso_status,
        },
    })

    # Section 2: Error summary
    errors = pipeline_state.get("errors", [])
    warnings = pipeline_state.get("warnings", [])
    summary["sections"].append({
        "title": "Resumen de Errores",
        "content": {
            "error_count": len(errors),
            "warning_count": len(warnings),
            "recent_errors": errors[-5:],
            "recent_warnings": warnings[-5:],
        },
    })

    # Section 4: PDF export status
    # EN: Populated by /api/pbi/export-pdf when a guide has been generated.
    # ES: Completado por /api/pbi/export-pdf cuando se genera una guía.
    pdf_export = pipeline_state.get("pdf_export", {})
    summary["sections"].append({
        "title": "Exportación PDF Power BI",
        "content": {
            "pdf_exported": pdf_export.get("exported", False),
            "pdf_path": pdf_export.get("pdf_path", ""),
            "export_strategy": pdf_export.get("strategy", "manual"),
            "guide_generated_at": pdf_export.get("generated_at", ""),
            "quarter": pdf_export.get("quarter", ""),
        },
    })

    return summary


def manage_backups(
    source_folder: str,
    backup_folder: str,
    patterns: list[str] | None = None,
    allowed_roots: list[str] | None = None,
) -> dict[str, Any]:
    """Copy verificadores and other files from source to backup folder.

    Args:
        source_folder: Path containing files to back up.
        backup_folder: Destination backup directory.
        patterns: Optional list of file extensions to include (e.g. ['.xlsx', '.pdf']).
                  If None, copies all files.

    Returns a summary dict with copied file count and any errors.
    """
    result: dict[str, Any] = {"copied": [], "errors": [], "backup_folder": backup_folder}

    # Validate paths against allowed directories
    roots = allowed_roots if allowed_roots is not None else _allowed_roots()
    try:
        safe_resolve(source_folder, roots)
        safe_resolve(backup_folder, roots)
    except ValueError as e:
        result["errors"].append(f"Path outside allowed directories: {e}")
        return result

    if not os.path.isdir(source_folder):
        result["errors"].append(f"Source folder not found: {source_folder}")
        return result

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    dest = os.path.join(backup_folder, f"backup_{timestamp}")
    os.makedirs(dest, exist_ok=True)

    for root, _dirs, files in os.walk(source_folder):
        for fname in files:
            if patterns:
                ext = os.path.splitext(fname)[1].lower()
                if ext not in patterns:
                    continue
            src_path = os.path.join(root, fname)
            rel = os.path.relpath(src_path, source_folder)
            dst_path = os.path.join(dest, rel)
            os.makedirs(os.path.dirname(dst_path), exist_ok=True)
            try:
                shutil.copy2(src_path, dst_path)
                result["copied"].append(rel)
            except OSError as exc:
                result["errors"].append(f"{rel}: {exc}")

    return result
