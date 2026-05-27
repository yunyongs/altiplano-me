"""Tests for orchestrator.py and pipeline_state.py."""
import pytest
from pipeline_state import (
    PipelineState,
    PipelineLog,
    STATUS_PENDING,
    STATUS_RUNNING,
    STATUS_AWAITING,
    STATUS_SUCCESS,
    STATUS_ERROR,
    STATUS_SKIPPED,
    PASO_NAMES,
)
from orchestrator import PipelineOrchestrator


@pytest.fixture
def state(tmp_path):
    return PipelineState(state_dir=tmp_path)


@pytest.fixture
def orch(state):
    return PipelineOrchestrator(state)


class TestPipelineLog:
    def test_to_dict(self):
        log = PipelineLog("test message", "info", 1)
        d = log.to_dict()
        assert d["message"] == "test message"
        assert d["severity"] == "info"
        assert d["paso"] == 1
        assert "timestamp" in d


class TestPipelineState:
    def test_initial_state(self, state):
        d = state.to_dict()
        assert d["current_paso"] is None
        assert d["started_at"] is None
        for v in d["paso_status"].values():
            assert v == STATUS_PENDING

    def test_start_pipeline(self, state):
        state.start_pipeline()
        d = state.to_dict()
        assert d["started_at"] is not None

    def test_start_paso(self, state):
        state.start_paso(1)
        d = state.to_dict()
        assert d["paso_status"]["1"] == STATUS_RUNNING
        assert d["current_paso"] == 1

    def test_complete_paso(self, state):
        state.start_paso(3)
        state.complete_paso(3)
        d = state.to_dict()
        assert d["paso_status"]["3"] == STATUS_SUCCESS

    def test_fail_paso(self, state):
        state.start_paso(2)
        state.fail_paso(2, "something broke")
        d = state.to_dict()
        assert d["paso_status"]["2"] == STATUS_ERROR
        assert len(d["errors"]) == 1

    def test_await_manual(self, state):
        state.start_paso(4)
        state.await_manual(4, "run script")
        d = state.to_dict()
        assert d["paso_status"]["4"] == STATUS_AWAITING

    def test_skip_paso(self, state):
        state.skip_paso(5)
        d = state.to_dict()
        assert d["paso_status"]["5"] == STATUS_SKIPPED

    def test_finish_pipeline(self, state):
        state.start_pipeline()
        state.finish_pipeline()
        d = state.to_dict()
        assert d["completed_at"] is not None

    def test_persistence(self, state, tmp_path):
        state.start_pipeline()
        state.start_paso(1)
        # File should exist
        state_file = tmp_path / "pipeline_state.json"
        assert state_file.exists()

    def test_add_warning(self, state):
        state.add_warning(1, "something unusual")
        d = state.to_dict()
        assert len(d["warnings"]) == 1


class TestPasoNames:
    def test_all_seven_pasos(self):
        for i in range(1, 8):
            assert i in PASO_NAMES


class TestPipelineOrchestrator:
    def test_start_pipeline_all_pasos(self, orch):
        result = orch.start_pipeline()
        assert "paso_status" in result
        # All pasos should be awaiting_manual (the orchestrator sets them)
        for i in range(1, 8):
            assert result["paso_status"][str(i)] == STATUS_AWAITING

    def test_start_pipeline_subset(self, orch):
        result = orch.start_pipeline(pasos=[1, 3, 5])
        assert result["paso_status"]["1"] == STATUS_AWAITING
        assert result["paso_status"]["3"] == STATUS_AWAITING
        assert result["paso_status"]["5"] == STATUS_AWAITING

    def test_advance_paso(self, orch):
        orch.start_pipeline()
        result = orch.advance_paso(1)
        assert result["paso_status"]["1"] == STATUS_SUCCESS

    def test_advance_all_completes_pipeline(self, orch):
        orch.start_pipeline()
        for i in range(1, 8):
            result = orch.advance_paso(i)
        assert result["completed_at"] is not None

    def test_retry_paso(self, orch):
        orch.start_pipeline()
        orch.advance_paso(1)
        result = orch.retry_paso(1)
        # After retry, paso should be back to awaiting_manual
        assert result["paso_status"]["1"] == STATUS_AWAITING

    def test_get_status(self, orch):
        result = orch.get_status()
        assert "paso_status" in result
