"""Tests for /api/paso0/diagnose — targeted AGOL query logic."""
from __future__ import annotations

import json
import time
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def client(monkeypatch):
    import app as app_module

    monkeypatch.setenv("SMARTSHEET_TOKEN", "fake-token")
    monkeypatch.setenv("AGOL_POLYGON_URL", "https://services9.arcgis.com/test/arcgis/rest/services/polygon/FeatureServer/0")
    monkeypatch.setenv("AGOL_POINT_URL", "https://services9.arcgis.com/test/arcgis/rest/services/point/FeatureServer/0")
    monkeypatch.setenv("FOLDER_C1", "E:\\test\\C1")
    monkeypatch.setenv("FOLDER_C2", "E:\\test\\C2")
    monkeypatch.setenv("FOLDER_C3", "E:\\test\\C3")

    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as flask_client:
        flask_client._app_module = app_module
        yield flask_client


def _make_ss_cache(comp, rows):
    """Build a Smartsheet cache entry with given rows."""
    return {
        "ts": time.time(),
        "data": {
            "name": f"Monitoreo_{comp}",
            "totalRows": len(rows),
            "columns": [
                "CÓDIGO DE LA ACTIVIDAD",
                "TOTAL DE HECTÁREAS",
                "FECHA DE LA ACTIVIDAD",
                "NÚMERO DE CONTRATO",
                "ORGANIZACIÓN",
                "TRIMESTRE QUE REPORTA",
            ],
            "rows": rows,
        },
    }


def _make_ss_row(row_number, code, ha, fecha="2025-01-15", contrato="", org="", trimestre=""):
    return {
        "rowNumber": row_number,
        "id": str(row_number * 100),
        "cells": {
            "CÓDIGO DE LA ACTIVIDAD": code,
            "TOTAL DE HECTÁREAS": ha,
            "FECHA DE LA ACTIVIDAD": fecha,
            "NÚMERO DE CONTRATO": contrato,
            "ORGANIZACIÓN": org,
            "TRIMESTRE QUE REPORTA": trimestre,
        },
        "attachments": [],
    }


def _make_agol_response(code_area_pairs):
    """Build AGOL JSON response from [(code, area), ...] pairs."""
    features = [
        {"attributes": {"CdgActvdd": code, "Area_ha": area}}
        for code, area in code_area_pairs
    ]
    return {"features": features, "exceededTransferLimit": False}


class TestDiagnoseTargetedQuery:
    """Verify that diagnose uses CdgActvdd IN (...) targeted AGOL queries."""

    def test_targeted_query_uses_ss_codes(self, client, monkeypatch):
        """AGOL should be queried with CdgActvdd IN (...) based on SS codes."""
        import app as app_module

        rows = [
            _make_ss_row(1, "250115_C1_JUA_a", 5.0),
            _make_ss_row(2, "250201_C1_LPZ_b", 10.0),
            _make_ss_row(3, "250301_C1_CBB_c", 3.0),
        ]
        cache_entry = _make_ss_cache("C1", rows)
        monkeypatch.setattr(app_module, "_sheet_id", lambda comp: "12345")

        # Pre-populate SS cache
        app_module._SS_CACHE["C1:12345"] = cache_entry
        app_module._AGOL_CACHE.clear()

        # Track AGOL POST calls
        agol_calls = []

        class FakeResponse:
            ok = True
            status_code = 200

            def __init__(self, data):
                self._data = data

            def json(self):
                return self._data

        original_post = None

        def mock_post(url, data=None, timeout=None, **kwargs):
            agol_calls.append({"url": url, "data": data})
            # Return matching features for the codes in the IN clause
            where = data.get("where", "") if data else ""
            features = []
            if "250115_C1_JUA_a" in where:
                features.append({"attributes": {"CdgActvdd": "250115_C1_JUA_a", "Area_ha": 5.0}})
            if "250201_C1_LPZ_b" in where:
                features.append({"attributes": {"CdgActvdd": "250201_C1_LPZ_b", "Area_ha": 8.0}})
            return FakeResponse({"features": features, "exceededTransferLimit": False})

        import requests
        monkeypatch.setattr(requests, "post", mock_post)

        resp = client.post("/api/paso0/diagnose", json={
            "component": "C1",
            "rowStart": 1,
            "rowEnd": 100,
        })

        assert resp.status_code == 200
        data = resp.get_json()

        # Verify targeted query was used
        diag = data["diagnostics"]
        assert diag["agol_targeted"] is True

        # Verify AGOL calls used IN clauses (not broad output= queries)
        assert len(agol_calls) > 0
        for call in agol_calls:
            where = call["data"].get("where", "")
            assert "CdgActvdd IN" in where, f"Expected targeted IN clause, got: {where}"

    def test_codes_match_correctly(self, client, monkeypatch):
        """Matching codes should show verified_match, missing should show new."""
        import app as app_module
        import requests

        rows = [
            _make_ss_row(1, "250115_C1_JUA_a", 5.0),
            _make_ss_row(2, "250201_C1_LPZ_b", 10.0),
            _make_ss_row(3, "250301_C1_CBB_c", 3.0),
        ]
        cache_entry = _make_ss_cache("C1", rows)
        monkeypatch.setattr(app_module, "_sheet_id", lambda comp: "12345")

        app_module._SS_CACHE["C1:12345"] = cache_entry
        app_module._AGOL_CACHE.clear()

        class FakeResponse:
            ok = True
            status_code = 200

            def __init__(self, data):
                self._data = data

            def json(self):
                return self._data

        def mock_post(url, data=None, timeout=None, **kwargs):
            # Return only 2 of 3 codes (250301_C1_CBB_c is "new")
            return FakeResponse({
                "features": [
                    {"attributes": {"CdgActvdd": "250115_C1_JUA_a", "Area_ha": 5.0}},
                    {"attributes": {"CdgActvdd": "250201_C1_LPZ_b", "Area_ha": 8.0}},
                ],
                "exceededTransferLimit": False,
            })

        monkeypatch.setattr(requests, "post", mock_post)

        resp = client.post("/api/paso0/diagnose", json={
            "component": "C1",
            "rowStart": 1,
            "rowEnd": 100,
        })

        assert resp.status_code == 200
        data = resp.get_json()
        summary = data["summary"]

        assert summary["verified_match"] == 1     # JUA matches (5.0 == 5.0)
        assert summary["verified_mismatch"] == 1   # LPZ differs (10.0 vs 8.0)
        assert summary["new_this_quarter"] == 1    # CBB not in AGOL

    def test_empty_codes_uses_broad_fallback(self, client, monkeypatch):
        """When all SS rows have no codes, should use broad output= query."""
        import app as app_module
        import requests

        rows = [
            _make_ss_row(1, "", None, fecha="2025-01-15"),  # no code, no ha
            _make_ss_row(2, "", None, fecha="2025-02-01"),
        ]
        cache_entry = _make_ss_cache("C1", rows)
        monkeypatch.setattr(app_module, "_sheet_id", lambda comp: "12345")

        app_module._SS_CACHE["C1:12345"] = cache_entry
        app_module._AGOL_CACHE.clear()

        agol_calls = []

        class FakeResponse:
            ok = True
            status_code = 200

            def __init__(self, data):
                self._data = data

            def json(self):
                return self._data

        def mock_post(url, data=None, timeout=None, **kwargs):
            agol_calls.append(data)
            return FakeResponse({"features": [], "exceededTransferLimit": False})

        monkeypatch.setattr(requests, "post", mock_post)

        resp = client.post("/api/paso0/diagnose", json={
            "component": "C1",
            "rowStart": 1,
            "rowEnd": 100,
        })

        assert resp.status_code == 200
        data = resp.get_json()

        # Should have used broad query since no SS codes
        diag = data["diagnostics"]
        assert diag["agol_targeted"] is False

    def test_batches_large_code_sets(self, client, monkeypatch):
        """Many codes should be split into batches of AGOL_BATCH_SIZE."""
        import app as app_module
        import requests

        # Create 250 rows with unique codes
        rows = [
            _make_ss_row(i, f"250101_C1_ORG{i:03d}_a", float(i))
            for i in range(1, 251)
        ]
        cache_entry = _make_ss_cache("C1", rows)
        monkeypatch.setattr(app_module, "_sheet_id", lambda comp: "12345")

        app_module._SS_CACHE["C1:12345"] = cache_entry
        app_module._AGOL_CACHE.clear()

        agol_calls = []

        class FakeResponse:
            ok = True
            status_code = 200

            def __init__(self, data):
                self._data = data

            def json(self):
                return self._data

        def mock_post(url, data=None, timeout=None, **kwargs):
            agol_calls.append(data)
            return FakeResponse({"features": [], "exceededTransferLimit": False})

        monkeypatch.setattr(requests, "post", mock_post)

        resp = client.post("/api/paso0/diagnose", json={
            "component": "C1",
            "rowStart": 1,
            "rowEnd": 999,
        })

        assert resp.status_code == 200

        # 250 codes / 100 per batch = 3 batches × 2 layers (polygon + point) = 6 calls
        # (or 3 per layer if both URLs configured)
        assert len(agol_calls) >= 3, f"Expected at least 3 batch calls, got {len(agol_calls)}"

        # Each call should use IN clause
        for call in agol_calls:
            where = call.get("where", "")
            assert "CdgActvdd IN" in where

    def test_filtered_row_numbers_limits_agol_query(self, client, monkeypatch):
        """Only codes from filteredRowNumbers should be used for AGOL query."""
        import app as app_module
        import requests

        rows = [
            _make_ss_row(1, "250115_C1_JUA_a", 5.0),
            _make_ss_row(2, "250201_C1_LPZ_b", 10.0),
            _make_ss_row(3, "250301_C1_CBB_c", 3.0),
        ]
        cache_entry = _make_ss_cache("C1", rows)
        monkeypatch.setattr(app_module, "_sheet_id", lambda comp: "12345")

        app_module._SS_CACHE["C1:12345"] = cache_entry
        app_module._AGOL_CACHE.clear()

        agol_where_clauses = []

        class FakeResponse:
            ok = True
            status_code = 200

            def __init__(self, data):
                self._data = data

            def json(self):
                return self._data

        def mock_post(url, data=None, timeout=None, **kwargs):
            agol_where_clauses.append(data.get("where", ""))
            return FakeResponse({
                "features": [
                    {"attributes": {"CdgActvdd": "250115_C1_JUA_a", "Area_ha": 5.0}},
                ],
                "exceededTransferLimit": False,
            })

        monkeypatch.setattr(requests, "post", mock_post)

        # Only pass row 1 as filtered
        resp = client.post("/api/paso0/diagnose", json={
            "component": "C1",
            "rowNumbers": [1],
        })

        assert resp.status_code == 200

        # AGOL WHERE should only contain JUA code (from row 1)
        for where in agol_where_clauses:
            assert "250115_C1_JUA_a" in where
            assert "250201_C1_LPZ_b" not in where
            assert "250301_C1_CBB_c" not in where

    def test_agol_cache_hit_for_same_codes(self, client, monkeypatch):
        """Second call with same codes should use AGOL cache."""
        import app as app_module
        import requests

        rows = [
            _make_ss_row(1, "250115_C1_JUA_a", 5.0),
        ]
        cache_entry = _make_ss_cache("C1", rows)
        monkeypatch.setattr(app_module, "_sheet_id", lambda comp: "12345")

        app_module._SS_CACHE["C1:12345"] = cache_entry
        app_module._AGOL_CACHE.clear()

        call_count = 0

        class FakeResponse:
            ok = True
            status_code = 200

            def __init__(self, data):
                self._data = data

            def json(self):
                return self._data

        def mock_post(url, data=None, timeout=None, **kwargs):
            nonlocal call_count
            call_count += 1
            return FakeResponse({
                "features": [
                    {"attributes": {"CdgActvdd": "250115_C1_JUA_a", "Area_ha": 5.0}},
                ],
                "exceededTransferLimit": False,
            })

        monkeypatch.setattr(requests, "post", mock_post)

        # First call
        resp1 = client.post("/api/paso0/diagnose", json={
            "component": "C1",
            "rowStart": 1,
            "rowEnd": 100,
        })
        assert resp1.status_code == 200
        first_count = call_count

        # Second call — should use cache
        resp2 = client.post("/api/paso0/diagnose", json={
            "component": "C1",
            "rowStart": 1,
            "rowEnd": 100,
        })
        assert resp2.status_code == 200
        data2 = resp2.get_json()
        assert data2["diagnostics"]["agol_cache_hit"] is True
        assert call_count == first_count  # No new AGOL calls


class TestAgolUrlSsrfDefense:
    """SSRF defense: only *.arcgis.com domains allowed for AGOL URLs."""

    def test_agol_url_ssrf_rejected(self, client):
        """Internal/non-AGOL URLs must be rejected."""
        resp = client.post("/api/paso0/diagnose", json={
            "component": "C1",
            "agol_polygon_url": "http://169.254.169.254/latest/meta-data/",
        })
        assert resp.status_code == 400
        assert "ArcGIS" in resp.get_json().get("error", "")

    def test_agol_url_localhost_rejected(self, client):
        """Localhost URLs must be rejected."""
        resp = client.post("/api/paso0/diagnose", json={
            "component": "C1",
            "agol_polygon_url": "http://localhost:8080/evil",
        })
        assert resp.status_code == 400
        assert "ArcGIS" in resp.get_json().get("error", "")

    def test_agol_url_spoofed_domain_rejected(self, client):
        """Domain that contains arcgis.com but isn't a subdomain must be rejected."""
        resp = client.post("/api/paso0/diagnose", json={
            "component": "C1",
            "agol_polygon_url": "https://evil.com/arcgis.com",
        })
        assert resp.status_code == 400

    def test_agol_url_valid_accepted(self):
        """Legitimate AGOL URLs should pass validation."""
        from app import _is_allowed_agol_url
        assert _is_allowed_agol_url("https://services.arcgis.com/org123/arcgis/rest/services/layer/FeatureServer")
        assert _is_allowed_agol_url("https://services9.arcgis.com/org/rest/services/x/FeatureServer")
        assert not _is_allowed_agol_url("http://localhost:8080/evil")
        assert not _is_allowed_agol_url("https://evil.com/arcgis.com")
        assert not _is_allowed_agol_url("http://169.254.169.254/latest/meta-data/")
        assert not _is_allowed_agol_url("ftp://services.arcgis.com/test")
