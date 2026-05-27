"""Tests for Paso 1 Agent Loop — paso1_agent.py + API endpoints."""
from __future__ import annotations

import json
import os
import tempfile

import pytest

import paso1_agent


# ── Fixtures ──────────────────────────────────────────────────

@pytest.fixture()
def tmp_dir(tmp_path):
    """Provide a temp directory that is also an allowed root."""
    return str(tmp_path)


SAMPLE_DIAGNOSE = {
    "groups": [
        {
            "grant_type": "",
            "contrato": "",
            "quarter": "T2026_Q2",
            "rows": [
                {"rowNumber": 10, "rowId": "111", "code": "250115_C1_JUA_a",
                 "cmp_status": "verified_match", "ss_ha": 5.0, "agol_ha": 5.0},
                {"rowNumber": 20, "rowId": "222", "code": "250201_C1_LPZ_b",
                 "cmp_status": "verified_mismatch", "ss_ha": 10.0, "agol_ha": 8.0},
                {"rowNumber": 30, "rowId": "333", "code": "",
                 "cmp_status": "new", "ss_ha": 3.0, "agol_ha": None},
            ],
        }
    ]
}

SAMPLE_DIAGNOSE_C2 = {
    "groups": [
        {
            "grant_type": "PPD",
            "contrato": "PPD-001",
            "org": "ORG_A",
            "quarter": "T2026_Q2",
            "summaryRowNumber": 4,
            "rows": [
                {"rowNumber": 5, "rowId": "500", "code": "250101_C2_PPD_a",
                 "cmp_status": "new", "ss_ha": 2.0, "agol_ha": None},
            ],
        },
        {
            "grant_type": "PMD",
            "contrato": "PMD-002",
            "org": "ORG_B",
            "quarter": "T2026_Q2",
            "summaryRowNumber": 14,
            "rows": [
                {"rowNumber": 15, "rowId": "600", "code": "250301_C2_PMD_x",
                 "cmp_status": "verified_mismatch", "ss_ha": 7.0, "agol_ha": 5.5},
                {"rowNumber": 16, "rowId": "601", "code": "250301_C2_PMD_y",
                 "cmp_status": "verified_match", "ss_ha": 4.0, "agol_ha": 4.0},
            ],
        },
    ]
}


# ── Unit tests: paso1_agent module ────────────────────────────

class TestInitAgentState:
    def test_creates_state_file(self, tmp_dir):
        state = paso1_agent.init_agent_state(
            tmp_dir, "C1", "T2026_Q2", SAMPLE_DIAGNOSE, [tmp_dir],
        )
        assert (paso1_agent.Path(tmp_dir) / ".paso1_agent_state.json").exists()
        assert state["version"] == 1
        assert state["component"] == "C1"

    def test_filters_verified_match(self, tmp_dir):
        state = paso1_agent.init_agent_state(
            tmp_dir, "C1", "T2026_Q2", SAMPLE_DIAGNOSE, [tmp_dir],
        )
        # Only mismatch + new = 2 items (row 20 and 30)
        assert len(state["items"]) == 2
        ids = [i["id"] for i in state["items"]]
        assert "C1_row20" in ids
        assert "C1_row30" in ids
        assert "C1_row10" not in ids

    def test_c2_ppd_pmd_separate(self, tmp_dir):
        state = paso1_agent.init_agent_state(
            tmp_dir, "C2", "T2026_Q2", SAMPLE_DIAGNOSE_C2, [tmp_dir],
        )
        # C2: one item per group (contrato+quarter), not per row.
        # PPD group: 1 pending row → 1 group item.
        # PMD group: row15 mismatch + row16 match (excluded) → 1 group item.
        assert len(state["items"]) == 2
        ppd_items = [i for i in state["items"] if i["grant_type"] == "PPD"]
        pmd_items = [i for i in state["items"] if i["grant_type"] == "PMD"]
        assert len(ppd_items) == 1
        assert len(pmd_items) == 1
        # C2 group items use the summary row number (the one with SHP attachment)
        assert ppd_items[0]["rowNumber"] == 4
        assert pmd_items[0]["rowNumber"] == 14
        # C2 group items carry child codes for CdgActvdd mapping
        assert ppd_items[0]["child_codes"] == ["250101_C2_PPD_a"]
        assert pmd_items[0]["child_codes"] == ["250301_C2_PMD_x"]

    def test_summary_counts(self, tmp_dir):
        state = paso1_agent.init_agent_state(
            tmp_dir, "C1", "T2026_Q2", SAMPLE_DIAGNOSE, [tmp_dir],
        )
        s = state["summary"]
        assert s["total"] == 2
        assert s["pending"] == 2
        assert s["done"] == 0


class TestLoadAgentState:
    def test_roundtrip(self, tmp_dir):
        original = paso1_agent.init_agent_state(
            tmp_dir, "C1", "T2026_Q2", SAMPLE_DIAGNOSE, [tmp_dir],
        )
        loaded = paso1_agent.load_agent_state(tmp_dir, [tmp_dir])
        assert loaded is not None
        assert loaded["component"] == original["component"]
        assert len(loaded["items"]) == len(original["items"])

    def test_returns_none_when_missing(self, tmp_dir):
        result = paso1_agent.load_agent_state(tmp_dir, [tmp_dir])
        assert result is None


class TestUpdateItem:
    def test_marks_done(self, tmp_dir):
        paso1_agent.init_agent_state(
            tmp_dir, "C1", "T2026_Q2", SAMPLE_DIAGNOSE, [tmp_dir],
        )
        state = paso1_agent.update_item(
            tmp_dir, "C1_row20",
            {"item_state": "done", "step_reached": "done"},
            [tmp_dir],
        )
        item = next(i for i in state["items"] if i["id"] == "C1_row20")
        assert item["item_state"] == "done"
        assert item["step_reached"] == "done"
        assert item["updated_at"] is not None
        assert state["summary"]["done"] == 1
        assert state["summary"]["pending"] == 1

    def test_not_found_raises(self, tmp_dir):
        paso1_agent.init_agent_state(
            tmp_dir, "C1", "T2026_Q2", SAMPLE_DIAGNOSE, [tmp_dir],
        )
        with pytest.raises(KeyError):
            paso1_agent.update_item(
                tmp_dir, "NONEXISTENT", {"item_state": "done"}, [tmp_dir],
            )

    def test_no_state_file_raises(self, tmp_dir):
        with pytest.raises(FileNotFoundError):
            paso1_agent.update_item(
                tmp_dir, "C1_row20", {"item_state": "done"}, [tmp_dir],
            )


class TestResetAgentState:
    def test_removes_file(self, tmp_dir):
        paso1_agent.init_agent_state(
            tmp_dir, "C1", "T2026_Q2", SAMPLE_DIAGNOSE, [tmp_dir],
        )
        assert paso1_agent.reset_agent_state(tmp_dir, [tmp_dir]) is True
        assert not (paso1_agent.Path(tmp_dir) / ".paso1_agent_state.json").exists()

    def test_returns_false_when_absent(self, tmp_dir):
        assert paso1_agent.reset_agent_state(tmp_dir, [tmp_dir]) is False


class TestComputeSummary:
    def test_mixed_states(self):
        items = [
            {"item_state": "done"},
            {"item_state": "done"},
            {"item_state": "skipped"},
            {"item_state": "error"},
            {"item_state": "pending"},
            {"item_state": "in_progress"},
        ]
        s = paso1_agent._compute_summary(items)
        assert s == {
            "total": 6, "done": 2, "skipped": 1,
            "error": 1, "pending": 1, "in_progress": 1,
        }


class TestSmartMerge:
    def test_same_quarter_preserves_done(self, tmp_dir):
        """Re-init with same quarter+component carries over done item_state."""
        paso1_agent.init_agent_state(
            tmp_dir, "C1", "T2026_Q2", SAMPLE_DIAGNOSE, [tmp_dir],
        )
        paso1_agent.update_item(
            tmp_dir, "C1_row20",
            {"item_state": "done", "step_reached": "manual"},
            [tmp_dir],
        )
        state2 = paso1_agent.init_agent_state(
            tmp_dir, "C1", "T2026_Q2", SAMPLE_DIAGNOSE, [tmp_dir],
        )
        item20 = next(i for i in state2["items"] if i["id"] == "C1_row20")
        assert item20["item_state"] == "done"
        assert item20["step_reached"] == "preserved"

    def test_different_quarter_resets(self, tmp_dir):
        """Re-init with a different quarter starts fresh (no merge)."""
        paso1_agent.init_agent_state(
            tmp_dir, "C1", "T2026_Q2", SAMPLE_DIAGNOSE, [tmp_dir],
        )
        paso1_agent.update_item(
            tmp_dir, "C1_row20",
            {"item_state": "done", "step_reached": "manual"},
            [tmp_dir],
        )
        state2 = paso1_agent.init_agent_state(
            tmp_dir, "C1", "T2026_Q3", SAMPLE_DIAGNOSE, [tmp_dir],
        )
        item20 = next(i for i in state2["items"] if i["id"] == "C1_row20")
        assert item20["item_state"] == "pending"

    def test_c2_group_key_preserved(self, tmp_dir):
        """C2 groups are matched by item ID (C2_grp_{contrato}_{quarter})."""
        state1 = paso1_agent.init_agent_state(
            tmp_dir, "C2", "T2026_Q2", SAMPLE_DIAGNOSE_C2, [tmp_dir],
        )
        ppd_id = next(i["id"] for i in state1["items"] if i["grant_type"] == "PPD")
        paso1_agent.update_item(
            tmp_dir, ppd_id,
            {"item_state": "done", "step_reached": "manual"},
            [tmp_dir],
        )
        state2 = paso1_agent.init_agent_state(
            tmp_dir, "C2", "T2026_Q2", SAMPLE_DIAGNOSE_C2, [tmp_dir],
        )
        ppd2 = next(i for i in state2["items"] if i["grant_type"] == "PPD")
        assert ppd2["item_state"] == "done"
        assert ppd2["step_reached"] == "preserved"
        pmd2 = next(i for i in state2["items"] if i["grant_type"] == "PMD")
        assert pmd2["item_state"] == "pending"

    def test_no_existing_state_normal_init(self, tmp_dir):
        """When no prior state file exists, init works as before (no merge)."""
        state = paso1_agent.init_agent_state(
            tmp_dir, "C1", "T2026_Q2", SAMPLE_DIAGNOSE, [tmp_dir],
        )
        assert all(i["item_state"] == "pending" for i in state["items"])


class TestPathTraversal:
    def test_rejects_traversal(self, tmp_dir):
        with pytest.raises(ValueError):
            paso1_agent.init_agent_state(
                tmp_dir + "/../../etc",
                "C1", "T2026_Q2", SAMPLE_DIAGNOSE, [tmp_dir],
            )


# ── API endpoint tests ───────────────────────────────────────

@pytest.fixture()
def client(tmp_path, monkeypatch):
    """Flask test client with a temp allowed root."""
    import app as app_module
    monkeypatch.setattr(app_module, "_allowed_roots", lambda: [str(tmp_path)])
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        c._tmp = str(tmp_path)
        yield c


class TestApiInit:
    def test_success(self, client):
        resp = client.post("/api/paso1-agent/init", json={
            "component": "C1",
            "quarter": "T2026_Q2",
            "destFolder": client._tmp,
            "diagnoseData": SAMPLE_DIAGNOSE,
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["component"] == "C1"
        assert len(data["items"]) == 2

    def test_missing_params(self, client):
        resp = client.post("/api/paso1-agent/init", json={
            "component": "C1",
        })
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error_code"] == "agent_missing_params"


class TestApiGetState:
    def test_uninitialized(self, client):
        resp = client.get("/api/paso1-agent/state?destFolder=" + client._tmp)
        assert resp.status_code == 200
        assert resp.get_json()["initialized"] is False

    def test_initialized(self, client):
        client.post("/api/paso1-agent/init", json={
            "component": "C1", "quarter": "T2026_Q2",
            "destFolder": client._tmp, "diagnoseData": SAMPLE_DIAGNOSE,
        })
        resp = client.get("/api/paso1-agent/state?destFolder=" + client._tmp)
        data = resp.get_json()
        assert data["initialized"] is True
        assert data["component"] == "C1"

    def test_no_dest(self, client):
        resp = client.get("/api/paso1-agent/state")
        assert resp.status_code == 400


class TestApiMarkComplete:
    def test_marks_item_done(self, client):
        client.post("/api/paso1-agent/init", json={
            "component": "C1", "quarter": "T2026_Q2",
            "destFolder": client._tmp, "diagnoseData": SAMPLE_DIAGNOSE,
        })
        resp = client.post("/api/paso1-agent/mark-complete", json={
            "destFolder": client._tmp,
            "itemId": "C1_row20",
            "stepReached": "done",
        })
        assert resp.status_code == 200
        data = resp.get_json()
        item = next(i for i in data["items"] if i["id"] == "C1_row20")
        assert item["item_state"] == "done"


class TestApiMarkSkip:
    def test_marks_item_skipped(self, client):
        client.post("/api/paso1-agent/init", json={
            "component": "C1", "quarter": "T2026_Q2",
            "destFolder": client._tmp, "diagnoseData": SAMPLE_DIAGNOSE,
        })
        resp = client.post("/api/paso1-agent/mark-skip", json={
            "destFolder": client._tmp,
            "itemId": "C1_row30",
            "reason": "user_skipped",
        })
        assert resp.status_code == 200
        data = resp.get_json()
        item = next(i for i in data["items"] if i["id"] == "C1_row30")
        assert item["item_state"] == "skipped"


class TestApiReset:
    def test_resets(self, client):
        client.post("/api/paso1-agent/init", json={
            "component": "C1", "quarter": "T2026_Q2",
            "destFolder": client._tmp, "diagnoseData": SAMPLE_DIAGNOSE,
        })
        resp = client.post("/api/paso1-agent/reset", json={
            "destFolder": client._tmp,
        })
        assert resp.status_code == 200
        assert resp.get_json()["reset"] is True
        # State should be gone
        resp2 = client.get("/api/paso1-agent/state?destFolder=" + client._tmp)
        assert resp2.get_json()["initialized"] is False


class TestApiPathTraversal:
    def test_init_rejects_traversal(self, client):
        resp = client.post("/api/paso1-agent/init", json={
            "component": "C1", "quarter": "T2026_Q2",
            "destFolder": client._tmp + "/../../etc",
            "diagnoseData": SAMPLE_DIAGNOSE,
        })
        assert resp.status_code == 400

    def test_state_rejects_traversal(self, client):
        resp = client.get("/api/paso1-agent/state?destFolder=" +
                          client._tmp + "/../../etc")
        assert resp.status_code == 400

    def test_reset_rejects_traversal(self, client):
        resp = client.post("/api/paso1-agent/reset", json={
            "destFolder": client._tmp + "/../../etc",
        })
        assert resp.status_code == 400


class TestApiMarkPending:
    def test_mark_pending_resets_done_item(self, client):
        """POST mark-pending sets item_state back to pending."""
        client.post("/api/paso1-agent/init", json={
            "component": "C1", "quarter": "T2026_Q2",
            "destFolder": client._tmp, "diagnoseData": SAMPLE_DIAGNOSE,
        })
        client.post("/api/paso1-agent/mark-complete", json={
            "destFolder": client._tmp, "itemId": "C1_row20", "stepReached": "manual",
        })
        resp = client.post("/api/paso1-agent/mark-pending", json={
            "destFolder": client._tmp,
            "itemId": "C1_row20",
        })
        assert resp.status_code == 200
        data = resp.get_json()
        item = next(i for i in data["items"] if i["id"] == "C1_row20")
        assert item["item_state"] == "pending"

    def test_mark_pending_unknown_item_returns_400(self, client):
        client.post("/api/paso1-agent/init", json={
            "component": "C1", "quarter": "T2026_Q2",
            "destFolder": client._tmp, "diagnoseData": SAMPLE_DIAGNOSE,
        })
        resp = client.post("/api/paso1-agent/mark-pending", json={
            "destFolder": client._tmp,
            "itemId": "C1_row999",
        })
        assert resp.status_code == 400
