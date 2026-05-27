"""
Pipeline state management for the 7-PASO orchestrator.

Tracks which PASOs have been executed, their status, errors, and provides
persistence to a JSON file so the UI can poll progress.
"""
from __future__ import annotations

import json
import os
import pathlib
import threading
from datetime import datetime
from typing import Any

PASO_NAMES = {
    1: "Recolección de datos (Smartsheet)",
    2: "Control cruzado",
    3: "Procesamiento territorial (ArcPy)",
    4: "Publicación geoespacial (AGOL)",
    5: "Integración Excel maestro",
    6: "Actualización dashboard (Power BI)",
    7: "Documentación y respaldo",
}

STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_AWAITING = "awaiting_manual"  # user must run a script manually
STATUS_SUCCESS = "success"
STATUS_ERROR = "error"
STATUS_SKIPPED = "skipped"

_VALID_STATUSES = {
    STATUS_PENDING, STATUS_RUNNING, STATUS_AWAITING,
    STATUS_SUCCESS, STATUS_ERROR, STATUS_SKIPPED,
}


class PipelineLog:
    """A single timestamped log entry."""

    def __init__(self, message: str, severity: str = "info", paso: int | None = None):
        self.timestamp = datetime.now().isoformat(timespec="seconds")
        self.message = message
        self.severity = severity  # info, warn, error
        self.paso = paso

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "message": self.message,
            "severity": self.severity,
            "paso": self.paso,
        }


class PipelineState:
    """Thread-safe pipeline execution state with JSON persistence."""

    def __init__(self, state_dir: str | pathlib.Path | None = None):
        self._lock = threading.RLock()
        self._state_dir = pathlib.Path(state_dir) if state_dir else pathlib.Path("downloads")
        self._state_file = self._state_dir / "pipeline_state.json"
        self._save_timer: threading.Timer | None = None
        self._save_pending = False
        self._SAVE_DEBOUNCE = 1.0  # seconds

        self.current_paso: int | None = None
        self.started_at: str | None = None
        self.completed_at: str | None = None
        self.paso_status: dict[int, str] = {i: STATUS_PENDING for i in range(1, 8)}
        self.errors: list[dict] = []
        self.warnings: list[dict] = []
        self.logs: list[dict] = []
        self.cleaning_stats: dict = {}
        # Schema: {"before": {"count": int, "area_ha": float},
        #          "after":  {"count": int, "area_ha": float},
        #          "removed": [{"cdg": str, "area_ha": float, "reason": str}, ...]}
        self.pdf_export: dict = {}
        # Schema: {"exported": bool, "strategy": str, "pdf_path": str,
        #          "quarter": str, "generated_at": str}
        self.substep_status: dict[str, str] = {}
        # Schema: {"5a": "success", "5b": "awaiting_manual", ...}
        # Used for pasos with discrete sub-steps (e.g. PASO 5: 5a=Excel, 5b=M&E).

    # -- Status mutations ---------------------------------------------------

    def set_substep(self, key: str, status: str) -> None:
        """Record a substep status (e.g. set_substep("5b", "success"))."""
        with self._lock:
            if status not in _VALID_STATUSES:
                raise ValueError(f"Invalid status: {status}")
            self.substep_status[key] = status
            self._log(f"Substep {key} → {status}", "info")
            self._save()

    def start_pipeline(self) -> None:
        with self._lock:
            self.started_at = datetime.now().isoformat(timespec="seconds")
            self.completed_at = None
            self.paso_status = {i: STATUS_PENDING for i in range(1, 8)}
            self.substep_status = {}
            self.errors.clear()
            self.warnings.clear()
            self.logs.clear()
            self._log("Pipeline iniciado", "info")
            self._save_immediate()

    def start_paso(self, paso: int) -> None:
        with self._lock:
            self.current_paso = paso
            self.paso_status[paso] = STATUS_RUNNING
            self._log(f"PASO {paso} iniciado: {PASO_NAMES.get(paso, '')}", "info", paso)
            self._save_immediate()

    def complete_paso(self, paso: int) -> None:
        with self._lock:
            self.paso_status[paso] = STATUS_SUCCESS
            self._log(f"PASO {paso} completado", "info", paso)
            self._save_immediate()

    def fail_paso(self, paso: int, error_msg: str) -> None:
        with self._lock:
            self.paso_status[paso] = STATUS_ERROR
            entry = PipelineLog(error_msg, "error", paso).to_dict()
            self.errors.append(entry)
            self._log(f"PASO {paso} error: {error_msg}", "error", paso)
            self._save_immediate()

    def await_manual(self, paso: int, message: str = "") -> None:
        with self._lock:
            self.paso_status[paso] = STATUS_AWAITING
            self._log(
                f"PASO {paso} esperando ejecución manual: {message}",
                "warn", paso,
            )
            self._save()

    def skip_paso(self, paso: int) -> None:
        with self._lock:
            self.paso_status[paso] = STATUS_SKIPPED
            self._log(f"PASO {paso} omitido", "info", paso)
            self._save()

    def finish_pipeline(self) -> None:
        with self._lock:
            self.completed_at = datetime.now().isoformat(timespec="seconds")
            self._log("Pipeline finalizado", "info")
            self._save_immediate()

    def add_warning(self, paso: int, message: str) -> None:
        with self._lock:
            entry = PipelineLog(message, "warn", paso).to_dict()
            self.warnings.append(entry)
            self._log(message, "warn", paso)
            self._save()

    # -- Query --------------------------------------------------------------

    def set_cleaning_stats(self, stats: dict) -> None:
        with self._lock:
            self.cleaning_stats = stats
            self._log("Cleaning stats actualizados", "info", 3)
            self._save()

    def record_pdf_export(
        self, strategy: str = "manual", pdf_path: str = "", quarter: str = ""
    ) -> None:
        """Record a PDF export event in pipeline state.
        / Registrar un evento de exportación PDF en el estado del pipeline.
        """
        with self._lock:
            self.pdf_export = {
                "exported": True,
                "strategy": strategy,
                "pdf_path": pdf_path,
                "quarter": quarter,
                "generated_at": datetime.now().isoformat(timespec="seconds"),
            }
            self._log(f"PDF export guide generated (strategy={strategy})", "info", 7)
            self._save()

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            return {
                "current_paso": self.current_paso,
                "started_at": self.started_at,
                "completed_at": self.completed_at,
                "paso_status": {str(k): v for k, v in self.paso_status.items()},
                "paso_names": {str(k): v for k, v in PASO_NAMES.items()},
                "errors": self.errors[-50:],
                "warnings": self.warnings[-50:],
                "logs": self.logs[-100:],
                "cleaning_stats": self.cleaning_stats,
                "pdf_export": self.pdf_export,
                "substep_status": self.substep_status,
            }

    # -- Persistence --------------------------------------------------------

    def _log(self, message: str, severity: str = "info", paso: int | None = None) -> None:
        self.logs.append(PipelineLog(message, severity, paso).to_dict())

    def _save(self) -> None:
        """Schedule a debounced save. Writes at most once per _SAVE_DEBOUNCE seconds."""
        self._save_pending = True
        if self._save_timer is None or not self._save_timer.is_alive():
            self._save_timer = threading.Timer(self._SAVE_DEBOUNCE, self._flush_save)
            self._save_timer.daemon = True
            self._save_timer.start()

    def _save_immediate(self) -> None:
        """Write state to disk immediately. Used for critical transitions."""
        if self._save_timer is not None:
            self._save_timer.cancel()
            self._save_timer = None
        self._save_pending = False
        os.makedirs(self._state_dir, exist_ok=True)
        with open(self._state_file, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    def _flush_save(self) -> None:
        """Timer callback — performs the actual save if still pending."""
        with self._lock:
            if self._save_pending:
                self._save_immediate()

    def flush(self) -> None:
        """Force any pending debounced save to disk immediately.
        Useful in tests and at process shutdown.
        """
        with self._lock:
            if self._save_pending:
                self._save_immediate()

    def load(self) -> bool:
        """Load state from disk. Returns True if a saved state was found."""
        if not self._state_file.exists():
            return False
        try:
            with open(self._state_file, encoding="utf-8") as f:
                data = json.load(f)
            self.current_paso = data.get("current_paso")
            self.started_at = data.get("started_at")
            self.completed_at = data.get("completed_at")
            self.paso_status = {int(k): v for k, v in data.get("paso_status", {}).items()}
            self.errors = data.get("errors", [])
            self.warnings = data.get("warnings", [])
            self.logs = data.get("logs", [])
            self.cleaning_stats = data.get("cleaning_stats", {})
            self.pdf_export = data.get("pdf_export", {})
            self.substep_status = data.get("substep_status", {})
            return True
        except (json.JSONDecodeError, KeyError):
            return False
