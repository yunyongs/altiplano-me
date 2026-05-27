"""Tests for PipelineState debounce behavior."""
import json
import time

import pytest

from pipeline_state import PipelineState


def test_debounced_save_batches_writes(tmp_path):
    """Multiple rapid mutations result in fewer disk writes."""
    ps = PipelineState(state_dir=str(tmp_path))

    save_count = 0
    original_immediate = ps._save_immediate

    def counting_save():
        nonlocal save_count
        save_count += 1
        original_immediate()

    ps._save_immediate = counting_save

    # Rapid mutations: 2 immediate + 2 debounced
    ps.start_pipeline()        # immediate
    ps.start_paso(1)           # immediate
    ps.add_warning(1, "test warning")   # debounced
    ps.await_manual(1, "waiting")       # debounced

    # Wait for debounce timer to fire
    time.sleep(1.5)

    # start_pipeline + start_paso = 2 immediate writes
    # add_warning + await_manual collapse into at most 1 debounced write
    assert save_count <= 3


def test_critical_transitions_save_immediately(tmp_path):
    """fail_paso and finish_pipeline save immediately without waiting for timer."""
    ps = PipelineState(state_dir=str(tmp_path))
    ps.start_pipeline()
    ps.start_paso(1)
    ps.fail_paso(1, "test error")

    state_file = tmp_path / "pipeline_state.json"
    assert state_file.exists()
    with open(state_file) as f:
        data = json.load(f)
    assert data["paso_status"]["1"] == "error"


def test_debounced_save_does_not_write_immediately(tmp_path):
    """Non-critical mutations do not write to disk immediately."""
    ps = PipelineState(state_dir=str(tmp_path))
    state_file = tmp_path / "pipeline_state.json"

    ps.add_warning(1, "no rush")
    # File should not exist yet (debounce window not elapsed)
    assert not state_file.exists()

    # Wait for debounce to flush
    time.sleep(1.5)
    assert state_file.exists()


def test_immediate_save_cancels_pending_timer(tmp_path):
    """Calling _save_immediate() while a debounce timer is pending cancels the timer."""
    ps = PipelineState(state_dir=str(tmp_path))

    save_count = 0
    original_immediate = ps._save_immediate

    def counting_save():
        nonlocal save_count
        save_count += 1
        original_immediate()

    ps._save_immediate = counting_save

    ps.add_warning(1, "debounced")   # starts timer
    ps.start_paso(1)                 # immediate, should cancel timer

    time.sleep(1.5)  # let timer window pass

    # Only 1 write: the immediate from start_paso (timer was cancelled)
    assert save_count == 1


def test_timer_is_daemon(tmp_path):
    """Save timer must be a daemon thread so it doesn't block process exit."""
    ps = PipelineState(state_dir=str(tmp_path))
    ps.add_warning(1, "daemon check")
    assert ps._save_timer is not None
    assert ps._save_timer.daemon is True
    # Cleanup
    ps._save_timer.cancel()
