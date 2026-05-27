"""Integration tests for Paso 1 Agent end-to-end data flow.

These tests verify that:
1. paso0_diagnose() output matches AgentController expectations
2. generate-codes response matches Agent Step A parsing
3. Empty rowIds are properly rejected
"""
import json
import time

import pytest


# -- Fixture: realistic diagnose output shape --

REALISTIC_DIAGNOSE = {
    "component": "C1",
    "sheet_name": "TestSheet",
    "groups": [{
        "key": "default",
        "grant_type": "",
        "contrato": "",
        "org": "TestOrg",
        "quarter": "T2026_Q1",
        "rows": [
            {
                "rowNumber": 5,
                "rowId": 98765,       # Must be present after Chat A fix
                "code": "240101_C1_ROM_a",
                "cmp_status": "verified_mismatch",
                "ss_ha": 10.0,
                "agol_ha": 9.5,
                "ha_diff": 0.5,
                "date": "2026-01-15",
                "contrato": "",
                "org": "TestOrg",
                "quarter": "T2026_Q1",
            },
            {
                "rowNumber": 6,
                "rowId": 98766,
                "code": "",
                "cmp_status": "new",
                "ss_ha": 5.0,
                "agol_ha": None,
                "ha_diff": None,
                "date": "",
                "contrato": "",
                "org": "TestOrg",
                "quarter": "T2026_Q1",
            },
        ],
        "total": 2,
        "verified_match": 0,
        "verified_mismatch": 1,
    }],
}


# -- Flask test client fixture --

@pytest.fixture()
def client(tmp_path, monkeypatch):
    """Flask test client with a temp allowed root and fake SS env."""
    import app as app_module

    monkeypatch.setenv("SMARTSHEET_TOKEN", "fake-token")
    monkeypatch.setenv("FOLDER_C1", "E:\\test\\C1")
    monkeypatch.setenv("FOLDER_C2", "E:\\test\\C2")
    monkeypatch.setenv("FOLDER_C3", "E:\\test\\C3")
    monkeypatch.setattr(app_module, "_allowed_roots", lambda: [str(tmp_path)])
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        c._tmp = str(tmp_path)
        yield c


# -- Agent init tests --

class TestAgentInitFromDiagnose:
    """Verify Agent correctly initializes from paso0_diagnose output."""

    def test_items_have_rowid(self, tmp_path):
        from paso1_agent import init_agent_state
        state = init_agent_state(
            diagnose_data=REALISTIC_DIAGNOSE,
            component="C1",
            quarter="T2026_Q1",
            dest_folder=str(tmp_path),
            allowed_roots=[str(tmp_path)],
        )
        for item in state["items"]:
            assert "rowId" in item, f"Item {item['id']} missing rowId"
            assert item["rowId"] is not None

    def test_verified_match_skipped(self, tmp_path):
        """Rows with cmp_status=verified_match should not appear in queue."""
        data = json.loads(json.dumps(REALISTIC_DIAGNOSE))
        data["groups"][0]["rows"][0]["cmp_status"] = "verified_match"
        from paso1_agent import init_agent_state
        state = init_agent_state(
            diagnose_data=data,
            component="C1",
            quarter="T2026_Q1",
            dest_folder=str(tmp_path),
            allowed_roots=[str(tmp_path)],
        )
        row_numbers = [i["rowNumber"] for i in state["items"]]
        assert 5 not in row_numbers  # verified_match row skipped
        assert 6 in row_numbers      # new row included

    def test_all_fields_propagated(self, tmp_path):
        """All expected fields from diagnose row must appear in agent item."""
        from paso1_agent import init_agent_state
        state = init_agent_state(
            diagnose_data=REALISTIC_DIAGNOSE,
            component="C1",
            quarter="T2026_Q1",
            dest_folder=str(tmp_path),
            allowed_roots=[str(tmp_path)],
        )
        expected_keys = {
            "id", "rowNumber", "rowId", "code", "cmp_status",
            "ss_ha", "agol_ha", "grant_type", "contrato",
            "item_state", "step_reached", "updated_at",
        }
        for item in state["items"]:
            missing = expected_keys - set(item.keys())
            assert not missing, f"Item {item['id']} missing keys: {missing}"

    def test_state_persisted_to_disk(self, tmp_path):
        """init_agent_state must write state JSON to dest_folder."""
        from paso1_agent import init_agent_state
        init_agent_state(
            diagnose_data=REALISTIC_DIAGNOSE,
            component="C1",
            quarter="T2026_Q1",
            dest_folder=str(tmp_path),
            allowed_roots=[str(tmp_path)],
        )
        state_files = list(tmp_path.rglob("*agent_state*.json"))
        assert len(state_files) >= 1, "Agent state file not written to disk"


# -- generate-codes contract tests --

class TestGenerateCodesContract:
    """Verify generate-codes response matches Agent expectations."""

    def test_empty_rowids_rejected(self, client):
        resp = client.post("/api/smartsheet/generate-codes",
                           json={"component": "C1", "rowIds": []})
        assert resp.status_code == 400
        data = resp.get_json()
        assert "rowIds" in data.get("error", "")

    def test_missing_rowids_not_rejected(self, client, monkeypatch):
        """Omitting rowIds entirely should NOT trigger the empty guard."""
        import app as app_module

        monkeypatch.setattr(app_module, "_sheet_id", lambda comp: "12345")

        # Mock smartsheet_request to return a minimal sheet
        class FakeResponse:
            ok = True
            status_code = 200

            def __init__(self, data):
                self._data = data

            def json(self):
                return self._data

            @property
            def text(self):
                return json.dumps(self._data)

        def mock_ss_request(method, url, **kwargs):
            if method == "GET" and "/sheets/" in url:
                return FakeResponse({
                    "columns": [
                        {"id": 1, "title": "CÓDIGO DE LA ACTIVIDAD"},
                        {"id": 2, "title": "FECHA DE LA ACTIVIDAD"},
                        {"id": 3, "title": "NOMBRE DE QUIEN REPORTA"},
                    ],
                    "rows": [],
                })
            return FakeResponse({})

        import ar_utils
        monkeypatch.setattr(ar_utils, "smartsheet_request", mock_ss_request)
        monkeypatch.setattr(app_module, "smartsheet_request", mock_ss_request)

        resp = client.post("/api/smartsheet/generate-codes",
                           json={"component": "C1"})
        # Should not be 400 — no rowIds means "use row range"
        assert resp.status_code == 200

    def test_response_has_patches_field(self, client, monkeypatch):
        """generate-codes must return 'patches' (not 'updated')."""
        import app as app_module
        import ar_utils

        monkeypatch.setattr(app_module, "_sheet_id", lambda comp: "12345")

        class FakeResponse:
            ok = True
            status_code = 200

            def __init__(self, data):
                self._data = data

            def json(self):
                return self._data

            @property
            def text(self):
                return json.dumps(self._data)

        def mock_ss_request(method, url, **kwargs):
            if method == "GET" and "/sheets/" in url:
                return FakeResponse({
                    "columns": [
                        {"id": 1, "title": "CÓDIGO DE LA ACTIVIDAD"},
                        {"id": 2, "title": "FECHA DE LA ACTIVIDAD"},
                        {"id": 3, "title": "NOMBRE DE QUIEN REPORTA"},
                    ],
                    "rows": [
                        {
                            "id": 98765,
                            "rowNumber": 1,
                            "cells": [
                                {"columnId": 1, "value": None},
                                {"columnId": 2, "value": "2026-01-15"},
                                {"columnId": 3, "value": "Juan"},
                            ],
                        },
                    ],
                })
            if method == "PUT":
                return FakeResponse({"message": "SUCCESS"})
            return FakeResponse({})

        monkeypatch.setattr(ar_utils, "smartsheet_request", mock_ss_request)
        monkeypatch.setattr(app_module, "smartsheet_request", mock_ss_request)

        resp = client.post("/api/smartsheet/generate-codes",
                           json={"component": "C1", "rowStart": 1, "rowEnd": 1})
        assert resp.status_code == 200
        data = resp.get_json()

        # Must have 'patches' field (not 'updated')
        assert "patches" in data, f"Response missing 'patches' field: {list(data.keys())}"
        assert "generated" in data

        # Patches must have correct structure
        if data["generated"] > 0:
            patch = data["patches"][0]
            assert "rowId" in patch, "patch missing rowId"
            assert "cells" in patch, "patch missing cells"
            assert isinstance(patch["cells"], dict)
            assert "CÓDIGO DE LA ACTIVIDAD" in patch["cells"]
