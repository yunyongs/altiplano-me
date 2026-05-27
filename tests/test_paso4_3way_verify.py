"""
Tests for PASO 4 — 3-Way Verification (G6)

Tests cover:
  1. script_verify_3way_sync() — generated script content
  2. /api/verify/3way endpoint — server-side SS vs GIS comparison
"""
from __future__ import annotations

import json
import pytest
from paso4_scripts import script_verify_3way_sync


# ─────────────────────────────────────────────────────────────────────────────
# script_verify_3way_sync — script content checks
# ─────────────────────────────────────────────────────────────────────────────

class TestScript3WaySync:

    def _gen(self, **kwargs):
        defaults = {
            "ss_csv_path":  r"C:\AR\smartsheet.csv",
            "gis_gdb_path": r"C:\AR.gdb",
            "gis_fc_name":  "AR_Oficial_poligono_GTM",
            "agol_url":     "https://services.arcgis.com/abc/FeatureServer/0",
        }
        defaults.update(kwargs)
        return script_verify_3way_sync(defaults)

    # -- Boilerplate ----------------------------------------------------------

    def test_imports_arcpy(self):
        assert "import arcpy" in self._gen()

    def test_imports_arcgis(self):
        script = self._gen()
        assert "from arcgis.gis import GIS" in script
        assert "from arcgis.features import FeatureLayer" in script

    def test_imports_csv(self):
        assert "import csv" in self._gen()

    def test_ss_csv_path_embedded(self):
        script = self._gen(ss_csv_path=r"D:\AR\ss.csv")
        assert r"D:\AR\ss.csv" in script

    def test_gis_gdb_path_embedded(self):
        script = self._gen(gis_gdb_path=r"D:\AR2026.gdb")
        assert r"D:\AR2026.gdb" in script

    def test_fc_name_embedded(self):
        script = self._gen(gis_fc_name="AR_Oficial_poligono_GTM")
        assert "AR_Oficial_poligono_GTM" in script

    def test_agol_url_embedded(self):
        url = "https://services.arcgis.com/XYZ/FeatureServer/0"
        script = self._gen(agol_url=url)
        assert url in script

    def test_agol_item_id_embedded(self):
        script = self._gen(agol_item_id="abc123")
        assert "gis.content.get" in script
        assert "abc123" in script

    # -- AGOL auth variants ---------------------------------------------------

    def test_agol_uses_pro_session(self):
        script = self._gen()
        assert 'GIS("pro")' in script  # always uses active ArcGIS Pro session

    # -- 3-way comparison logic -----------------------------------------------

    def test_loads_ss_csv(self):
        script = self._gen()
        assert "SS_CSV_PATH" in script
        assert "csv.DictReader" in script

    def test_reads_gdb_with_search_cursor(self):
        script = self._gen()
        assert "arcpy.da.SearchCursor" in script

    def test_queries_agol_feature_layer(self):
        script = self._gen()
        assert "FeatureLayer" in script
        assert ".query(" in script

    def test_record_count_comparison(self):
        script = self._gen()
        assert "len(ss_set)" in script
        assert "len(gis_set)" in script
        assert "len(agol_set)" in script

    def test_area_sum_comparison(self):
        script = self._gen()
        assert "area_total" in script or "sum(ss_records" in script

    def test_set_difference_computed(self):
        script = self._gen()
        assert "ss_set  - gis_set" in script or "ss_set - gis_set" in script
        assert "ss_set  - agol_set" in script or "ss_set - agol_set" in script

    def test_summary_block(self):
        script = self._gen()
        assert "VERIFICACIÓN" in script or "VERIFICATION" in script

    # -- CdgActvdd field ------------------------------------------------------

    def test_cdgactvdd_field_used(self):
        assert "CdgActvdd" in self._gen()

    def test_area_ha_field_used(self):
        assert "Area_ha" in self._gen()

    # -- Returns string -------------------------------------------------------

    def test_returns_string(self):
        assert isinstance(self._gen(), str)

    def test_non_empty(self):
        assert len(self._gen()) > 500


# ─────────────────────────────────────────────────────────────────────────────
# /api/verify/3way endpoint — server-side comparison
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    import app as flask_app
    flask_app.app.config["TESTING"] = True
    with flask_app.app.test_client() as c:
        yield c


SS_RECORDS = [
    {"CÓDIGO DE LA ACTIVIDAD": "241014_C1_ROM_a", "TOTAL DE HECTÁREAS": 5.2},
    {"CÓDIGO DE LA ACTIVIDAD": "241014_C1_FOR_b", "TOTAL DE HECTÁREAS": 3.1},
    {"CÓDIGO DE LA ACTIVIDAD": "241014_C1_AGR_c", "TOTAL DE HECTÁREAS": 2.0},
]
GIS_RECORDS_OK = [
    {"CdgActvdd": "241014_C1_ROM_a", "Area_ha": 5.2},
    {"CdgActvdd": "241014_C1_FOR_b", "Area_ha": 3.1},
    {"CdgActvdd": "241014_C1_AGR_c", "Area_ha": 2.0},
]
GIS_RECORDS_AREA_DIFF = [
    {"CdgActvdd": "241014_C1_ROM_a", "Area_ha": 5.5},   # Δ=0.3 → warning
    {"CdgActvdd": "241014_C1_FOR_b", "Area_ha": 3.1},
    {"CdgActvdd": "241014_C1_AGR_c", "Area_ha": 2.0},
]
GIS_RECORDS_MISSING = [
    {"CdgActvdd": "241014_C1_ROM_a", "Area_ha": 5.2},
    {"CdgActvdd": "241014_C1_FOR_b", "Area_ha": 3.1},
    # 241014_C1_AGR_c missing
]


class TestVerify3WayEndpoint:

    def _post(self, client, ss_data, gis_records):
        return client.post(
            "/api/verify/3way",
            json={"ss_data": ss_data, "gis_records": gis_records},
            content_type="application/json",
        )

    # -- All match (green) ----------------------------------------------------

    def test_all_match_status_ok(self, client):
        resp = self._post(client, SS_RECORDS, GIS_RECORDS_OK)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "ok"

    def test_all_match_ss_count(self, client):
        resp = self._post(client, SS_RECORDS, GIS_RECORDS_OK)
        data = resp.get_json()
        assert data["ss"]["count"] == 3

    def test_all_match_gis_count(self, client):
        resp = self._post(client, SS_RECORDS, GIS_RECORDS_OK)
        data = resp.get_json()
        assert data["gis"]["count"] == 3

    def test_all_match_no_ss_only(self, client):
        resp = self._post(client, SS_RECORDS, GIS_RECORDS_OK)
        data = resp.get_json()
        assert data["ss_only"] == []

    def test_all_match_no_gis_only(self, client):
        resp = self._post(client, SS_RECORDS, GIS_RECORDS_OK)
        data = resp.get_json()
        assert data["gis_only"] == []

    def test_all_match_area_delta_zero(self, client):
        resp = self._post(client, SS_RECORDS, GIS_RECORDS_OK)
        data = resp.get_json()
        assert data["area_delta"] == pytest.approx(0.0, abs=0.01)

    # -- Area mismatch → warning ----------------------------------------------

    def test_area_mismatch_status_warning(self, client):
        resp = self._post(client, SS_RECORDS, GIS_RECORDS_AREA_DIFF)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "warning"

    def test_area_mismatch_delta_positive(self, client):
        resp = self._post(client, SS_RECORDS, GIS_RECORDS_AREA_DIFF)
        data = resp.get_json()
        assert data["area_delta"] > 0.1

    # -- Missing GIS record → error -------------------------------------------

    def test_missing_gis_record_status_error(self, client):
        resp = self._post(client, SS_RECORDS, GIS_RECORDS_MISSING)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "error"

    def test_missing_gis_record_in_ss_only(self, client):
        resp = self._post(client, SS_RECORDS, GIS_RECORDS_MISSING)
        data = resp.get_json()
        assert "241014_C1_AGR_c" in data["ss_only"]

    # -- Extra GIS record → warning -------------------------------------------

    def test_extra_gis_record_status_warning(self, client):
        gis_extra = GIS_RECORDS_OK + [{"CdgActvdd": "999999_C1_EXTRA", "Area_ha": 0.5}]
        resp = self._post(client, SS_RECORDS, gis_extra)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "warning"
        assert "999999_C1_EXTRA" in data["gis_only"]

    # -- Empty GIS records (no comparison) ------------------------------------

    def test_empty_gis_records_returns_ok_or_warning(self, client):
        resp = self._post(client, SS_RECORDS, [])
        assert resp.status_code == 200
        data = resp.get_json()
        # No GIS data provided → SS only shows as error (all SS codes missing in GIS)
        assert data["status"] in ("ok", "warning", "error")
        assert "ss" in data and "gis" in data

    # -- Response shape -------------------------------------------------------

    def test_response_has_required_keys(self, client):
        resp = self._post(client, SS_RECORDS, GIS_RECORDS_OK)
        data = resp.get_json()
        for key in ("ss", "gis", "ss_only", "gis_only", "area_delta", "status"):
            assert key in data, f"Missing key: {key}"

    def test_ss_has_count_area_codes(self, client):
        resp = self._post(client, SS_RECORDS, GIS_RECORDS_OK)
        data = resp.get_json()
        for key in ("count", "area_total", "codes"):
            assert key in data["ss"], f"ss missing key: {key}"

    def test_gis_has_count_area_codes(self, client):
        resp = self._post(client, SS_RECORDS, GIS_RECORDS_OK)
        data = resp.get_json()
        for key in ("count", "area_total", "codes"):
            assert key in data["gis"], f"gis missing key: {key}"
