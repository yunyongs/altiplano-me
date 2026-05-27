"""
Pipeline orchestrator — coordinates sequential execution of PASOs 1-7.

PASOs 3-4 generate scripts for manual execution in ArcGIS Pro, so the
orchestrator marks them as "awaiting_manual" and waits for user confirmation.
"""
from __future__ import annotations

from pipeline_state import PipelineState


class PipelineOrchestrator:
    """Runs the 7-PASO pipeline with error handling and status tracking."""

    def __init__(self, state: PipelineState | None = None):
        self.state = state or PipelineState()

    def run_paso1(self, **kwargs) -> bool:
        """PASO 1: Smartsheet data collection.

        This is handled by the existing Flask endpoints (ss_load, ss_generate_codes,
        ss_update_review, ss_attachments, batch-download).  The orchestrator just
        marks it as running and waits for the user to confirm completion via the UI.
        """
        self.state.start_paso(1)
        try:
            self.state.await_manual(1, "Ejecute las acciones de PASO 1 en el panel lateral.")
            return True
        except Exception as exc:
            self.state.fail_paso(1, str(exc))
            return False

    def run_paso2(self, **kwargs) -> bool:
        """PASO 2: Cross-check. Runs server-side if GIS data is uploaded."""
        self.state.start_paso(2)
        try:
            self.state.await_manual(2, "Suba el CSV de GIS y ejecute el control cruzado.")
            return True
        except Exception as exc:
            self.state.fail_paso(2, str(exc))
            return False

    def run_paso3(self, **kwargs) -> bool:
        """PASO 3: ArcPy scripts. Generated server-side, executed manually."""
        self.state.start_paso(3)
        try:
            self.state.await_manual(
                3, "Genere los scripts y ejecútelos en ArcGIS Pro Python window."
            )
            return True
        except Exception as exc:
            self.state.fail_paso(3, str(exc))
            return False

    def run_paso4(self, **kwargs) -> bool:
        """PASO 4: AGOL update scripts. Generated server-side, executed manually."""
        self.state.start_paso(4)
        try:
            self.state.await_manual(
                4, "Genere los scripts WFL y ejecútelos en ArcGIS Pro."
            )
            return True
        except Exception as exc:
            self.state.fail_paso(4, str(exc))
            return False

    def run_paso5(self, **kwargs) -> bool:
        """PASO 5: 5a = Excel master generation, 5b = M&E data reception (Dafne).

        Both substeps are manual UI actions; the orchestrator marks them as
        awaiting_manual so the user can complete them from the dashboard.
        PASO 5 is considered complete when both 5a and 5b are advanced via
        /api/orchestrator/advance-substep.
        """
        self.state.start_paso(5)
        try:
            self.state.set_substep("5a", "awaiting_manual")
            self.state.set_substep("5b", "awaiting_manual")
            self.state.await_manual(
                5,
                "5a: Genere el Excel maestro desde el panel. "
                "5b: Reciba y coloque Tbl_Integrado.xlsx (Dafne).",
            )
            return True
        except Exception as exc:
            self.state.fail_paso(5, str(exc))
            return False

    def run_paso6(self, **kwargs) -> bool:
        """PASO 6: Power BI refresh. Requires interactive auth."""
        self.state.start_paso(6)
        try:
            self.state.await_manual(
                6, "Ejecute el refresh en Power BI Desktop y exporte PDF."
            )
            return True
        except Exception as exc:
            self.state.fail_paso(6, str(exc))
            return False

    def run_paso7(self, **kwargs) -> bool:
        """PASO 7: Documentation and backup."""
        self.state.start_paso(7)
        try:
            self.state.await_manual(7, "Genere los reportes y ejecute el backup.")
            return True
        except Exception as exc:
            self.state.fail_paso(7, str(exc))
            return False

    def start_pipeline(self, pasos: list[int] | None = None) -> dict:
        """Initialize the pipeline and set all requested PASOs to pending."""
        self.state.start_pipeline()
        target_pasos = pasos or list(range(1, 8))

        runners = {
            1: self.run_paso1,
            2: self.run_paso2,
            3: self.run_paso3,
            4: self.run_paso4,
            5: self.run_paso5,
            6: self.run_paso6,
            7: self.run_paso7,
        }

        for paso in target_pasos:
            if paso in runners:
                runners[paso]()
            else:
                self.state.skip_paso(paso)

        return self.state.to_dict()

    def advance_paso(self, paso: int) -> dict:
        """User confirms that a manual paso has been completed."""
        self.state.complete_paso(paso)

        # Check if all PASOs are done
        all_done = all(
            s in ("success", "skipped")
            for s in self.state.paso_status.values()
        )
        if all_done:
            self.state.finish_pipeline()

        return self.state.to_dict()

    def retry_paso(self, paso: int) -> dict:
        """Re-run a failed paso."""
        runners = {
            1: self.run_paso1, 2: self.run_paso2, 3: self.run_paso3,
            4: self.run_paso4, 5: self.run_paso5, 6: self.run_paso6,
            7: self.run_paso7,
        }
        if paso in runners:
            runners[paso]()
        return self.state.to_dict()

    def get_status(self) -> dict:
        return self.state.to_dict()
