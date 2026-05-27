"""
Tests for paso5_dafne: G7 functions
  - receive_me_data
  - get_reception_history
  - list_reception_quarters
  - pipeline_state substep_status
  - orchestrator run_paso5 substep separation
"""
from __future__ import annotations

import json
import pathlib

import pytest

from paso5_dafne import (
    DEFAULT_FILENAME,
    REQUIRED_SHEETS,
    get_reception_history,
    list_reception_quarters,
    receive_me_data,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

def _make_xlsx(path: pathlib.Path, sheets: list[str]) -> pathlib.Path:
    import openpyxl
    wb = openpyxl.Workbook()
    for i, name in enumerate(sheets):
        if i == 0:
            ws = wb.active
            ws.title = name
        else:
            wb.create_sheet(name)
    wb.save(str(path))
    return path


@pytest.fixture()
def valid_xlsx(tmp_path):
    fp = tmp_path / "src" / DEFAULT_FILENAME
    fp.parent.mkdir()
    _make_xlsx(fp, REQUIRED_SHEETS)
    return fp


@pytest.fixture()
def invalid_xlsx(tmp_path):
    fp = tmp_path / "src" / DEFAULT_FILENAME
    fp.parent.mkdir()
    _make_xlsx(fp, ["WrongSheet"])
    return fp


@pytest.fixture()
def base_path(tmp_path):
    bp = tmp_path / "base"
    bp.mkdir()
    return bp


@pytest.fixture(autouse=True)
def patch_history_dir(tmp_path, monkeypatch):
    """Redirect history writes to tmp_path so tests don't pollute data/."""
    history_dir = tmp_path / "history"
    history_dir.mkdir()
    import paso5_dafne
    monkeypatch.setattr(paso5_dafne, "_HISTORY_DIR", history_dir)
    monkeypatch.setattr(paso5_dafne, "_allowed_roots", lambda: [str(tmp_path)])
    return history_dir


# ─────────────────────────────────────────────────────────────────────────────
# receive_me_data — success path
# ─────────────────────────────────────────────────────────────────────────────

class TestReceiveMeDataSuccess:
    def test_returns_success_true(self, valid_xlsx, base_path):
        result = receive_me_data(str(valid_xlsx), "T2026_Q2", str(base_path))
        assert result["success"] is True

    def test_validation_dict_present(self, valid_xlsx, base_path):
        result = receive_me_data(str(valid_xlsx), "T2026_Q2", str(base_path))
        assert result["validation"]["valid"] is True

    def test_placement_dict_present(self, valid_xlsx, base_path):
        result = receive_me_data(str(valid_xlsx), "T2026_Q2", str(base_path))
        assert result["placement"]["success"] is True
        assert pathlib.Path(result["placement"]["dest"]).exists()

    def test_history_entry_written(self, valid_xlsx, base_path):
        receive_me_data(str(valid_xlsx), "T2026_Q2", str(base_path))
        history = get_reception_history("T2026_Q2")
        assert len(history) == 1
        assert history[0]["success"] is True
        assert history[0]["quarter"] == "T2026_Q2"

    def test_metadata_stored_in_history(self, valid_xlsx, base_path):
        meta = {"received_by": "coord", "notes": "test run", "version_label": "v1"}
        receive_me_data(str(valid_xlsx), "T2026_Q2", str(base_path), metadata=meta)
        history = get_reception_history("T2026_Q2")
        assert history[0]["received_by"] == "coord"
        assert history[0]["notes"] == "test run"
        assert history[0]["version_label"] == "v1"


# ─────────────────────────────────────────────────────────────────────────────
# receive_me_data — validation failure path
# ─────────────────────────────────────────────────────────────────────────────

class TestReceiveMeDataValidationFailure:
    def test_invalid_file_returns_success_false(self, invalid_xlsx, base_path):
        result = receive_me_data(str(invalid_xlsx), "T2026_Q2", str(base_path))
        assert result["success"] is False

    def test_placement_is_none_when_invalid(self, invalid_xlsx, base_path):
        result = receive_me_data(str(invalid_xlsx), "T2026_Q2", str(base_path))
        assert result["placement"] is None

    def test_history_still_recorded_on_failure(self, invalid_xlsx, base_path):
        # ES: El historial se registra aunque la validación falle
        # EN: History is recorded even when validation fails
        receive_me_data(str(invalid_xlsx), "T2026_Q2", str(base_path))
        history = get_reception_history("T2026_Q2")
        assert len(history) == 1
        assert history[0]["valid"] is False
        assert history[0]["placed"] is False

    def test_missing_file_returns_error(self, tmp_path, base_path):
        result = receive_me_data(str(tmp_path / "none.xlsx"), "T2026_Q2", str(base_path))
        assert result["success"] is False


# ─────────────────────────────────────────────────────────────────────────────
# get_reception_history
# ─────────────────────────────────────────────────────────────────────────────

class TestGetReceptionHistory:
    def test_empty_when_no_history(self):
        assert get_reception_history("T2026_Q9") == []

    def test_multiple_entries_newest_first(self, valid_xlsx, base_path):
        receive_me_data(str(valid_xlsx), "T2026_Q1", str(base_path))
        receive_me_data(str(valid_xlsx), "T2026_Q1", str(base_path))
        history = get_reception_history("T2026_Q1")
        assert len(history) == 2
        # Newest first means received_at of [0] >= [1]
        assert history[0]["received_at"] >= history[1]["received_at"]

    def test_different_quarters_isolated(self, valid_xlsx, base_path, tmp_path):
        base2 = tmp_path / "base2"
        base2.mkdir()
        receive_me_data(str(valid_xlsx), "T2026_Q1", str(base_path))
        receive_me_data(str(valid_xlsx), "T2026_Q2", str(base2))

        assert len(get_reception_history("T2026_Q1")) == 1
        assert len(get_reception_history("T2026_Q2")) == 1


# ─────────────────────────────────────────────────────────────────────────────
# list_reception_quarters
# ─────────────────────────────────────────────────────────────────────────────

class TestListReceptionQuarters:
    def test_empty_when_no_history(self):
        assert list_reception_quarters() == []

    def test_returns_quarters_after_reception(self, valid_xlsx, base_path, tmp_path):
        base2 = tmp_path / "base2"
        base2.mkdir()
        receive_me_data(str(valid_xlsx), "T2026_Q1", str(base_path))
        receive_me_data(str(valid_xlsx), "T2026_Q2", str(base2))

        quarters = list_reception_quarters()
        assert "T2026_Q1" in quarters
        assert "T2026_Q2" in quarters
        assert quarters == sorted(quarters)


# ─────────────────────────────────────────────────────────────────────────────
# pipeline_state substep_status
# ─────────────────────────────────────────────────────────────────────────────

class TestPipelineStateSubstep:
    def test_set_substep_stores_status(self, tmp_path):
        from pipeline_state import PipelineState, STATUS_SUCCESS
        state = PipelineState(state_dir=tmp_path)
        state.set_substep("5a", STATUS_SUCCESS)
        assert state.substep_status["5a"] == STATUS_SUCCESS

    def test_set_substep_in_to_dict(self, tmp_path):
        from pipeline_state import PipelineState
        state = PipelineState(state_dir=tmp_path)
        state.set_substep("5b", "awaiting_manual")
        d = state.to_dict()
        assert d["substep_status"]["5b"] == "awaiting_manual"

    def test_invalid_substep_status_raises(self, tmp_path):
        from pipeline_state import PipelineState
        state = PipelineState(state_dir=tmp_path)
        with pytest.raises(ValueError):
            state.set_substep("5a", "not_a_valid_status")

    def test_substep_cleared_on_start_pipeline(self, tmp_path):
        from pipeline_state import PipelineState
        state = PipelineState(state_dir=tmp_path)
        state.set_substep("5a", "success")
        state.start_pipeline()
        assert state.substep_status == {}


# ─────────────────────────────────────────────────────────────────────────────
# orchestrator run_paso5 substeps
# ─────────────────────────────────────────────────────────────────────────────

class TestOrchestratorPaso5Substeps:
    def test_run_paso5_sets_both_substeps_awaiting(self, tmp_path):
        from pipeline_state import PipelineState
        from orchestrator import PipelineOrchestrator

        state = PipelineState(state_dir=tmp_path)
        orch = PipelineOrchestrator(state=state)
        orch.run_paso5()

        assert state.substep_status.get("5a") == "awaiting_manual"
        assert state.substep_status.get("5b") == "awaiting_manual"

    def test_run_paso5_sets_paso5_awaiting(self, tmp_path):
        from pipeline_state import PipelineState, STATUS_AWAITING
        from orchestrator import PipelineOrchestrator

        state = PipelineState(state_dir=tmp_path)
        orch = PipelineOrchestrator(state=state)
        orch.run_paso5()

        assert state.paso_status[5] == STATUS_AWAITING
