"""Tests for paso3_scripts.py — ArcPy script generators."""
import pytest
from paso3_scripts import PASO3_SCRIPTS


SAMPLE_PARAMS = {
    "gdb": r"C:\AR.gdb",
    "csvPath": r"C:\export.csv",
    "component": "C1",
    "currentQt": "T2025_Q1",
    "officialPolygon": "AR_Oficial_poligono_GTM",
    "officialPoint": "AR_Oficial_punto_GTM",
    "baseMicroMuni": "BASE_Micro_MUNI",
    "smartsheetTable": "ssheet",
}


class TestPaso3Registry:
    def test_registry_not_empty(self):
        assert len(PASO3_SCRIPTS) >= 9

    def test_expected_steps(self):
        expected = [
            "merge_field_mapping",
            "overlap_analysis",
            "erase_pipeline",
            "spatial_join_micro",
            "duplicate_detection",
            "incentive_validation",
            "append_official",
            "gis_vs_ss_comparison",
            "backup_cumulative",
        ]
        for step in expected:
            assert step in PASO3_SCRIPTS, f"Missing step: {step}"


class TestScriptGeneration:
    """Each script generator must return a non-empty Python string."""

    @pytest.mark.parametrize("step", list(PASO3_SCRIPTS.keys()))
    def test_returns_string(self, step):
        gen = PASO3_SCRIPTS[step]
        result = gen(SAMPLE_PARAMS)
        assert isinstance(result, str)
        assert len(result) > 50

    @pytest.mark.parametrize("step", list(PASO3_SCRIPTS.keys()))
    def test_contains_import_arcpy(self, step):
        gen = PASO3_SCRIPTS[step]
        result = gen(SAMPLE_PARAMS)
        assert "arcpy" in result


class TestMergeScript:
    def test_contains_merge_call(self):
        script = PASO3_SCRIPTS["merge_field_mapping"](SAMPLE_PARAMS)
        assert "Merge" in script

    def test_uses_gdb_param(self):
        script = PASO3_SCRIPTS["merge_field_mapping"](SAMPLE_PARAMS)
        assert r"C:\AR.gdb" in script


class TestOverlapScript:
    def test_contains_count_overlapping(self):
        script = PASO3_SCRIPTS["overlap_analysis"](SAMPLE_PARAMS)
        assert "CountOverlappingFeatures" in script or "Intersect" in script


class TestEraseScript:
    def test_contains_erase(self):
        script = PASO3_SCRIPTS["erase_pipeline"](SAMPLE_PARAMS)
        assert "Erase" in script or "erase" in script


class TestAppendScript:
    def test_contains_append(self):
        script = PASO3_SCRIPTS["append_official"](SAMPLE_PARAMS)
        assert "Append" in script

    def test_contains_field_mapping(self):
        script = PASO3_SCRIPTS["append_official"](SAMPLE_PARAMS)
        assert "field_mapping" in script.lower() or "NO_TEST" in script


class TestDuplicateDetection:
    def test_contains_are_identical_to(self):
        script = PASO3_SCRIPTS["duplicate_detection"](SAMPLE_PARAMS)
        assert "ARE_IDENTICAL_TO" in script


class TestGisVsSsComparison:
    def test_contains_search_cursor(self):
        script = PASO3_SCRIPTS["gis_vs_ss_comparison"](SAMPLE_PARAMS)
        assert "SearchCursor" in script or "cursor" in script.lower()
