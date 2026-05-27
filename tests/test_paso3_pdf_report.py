"""Tests for paso3_pdf_report.py — Overlap PDF Report script generator."""
import pytest
from paso3_pdf_report import script_overlap_pdf_report


SAMPLE_PARAMS = {
    "official_polygon": "AR_Oficial_poligono_GTM",
    "current_polygon": r"C:\AR.gdb\T2026_Q1_polygon",
    "output_pdf": r"C:\Reports\Overlap_T2026_Q1.pdf",
    "current_qt": "T2026_Q1",
    "aprx_path": r"C:\Projects\AR.aprx",
    "layout_name": "Overlap_Report",
    "gdb_path": r"C:\AR.gdb",
}


class TestScriptGeneration:
    def test_returns_string(self):
        result = script_overlap_pdf_report(SAMPLE_PARAMS)
        assert isinstance(result, str)
        assert len(result) > 50

    def test_contains_import_arcpy(self):
        result = script_overlap_pdf_report(SAMPLE_PARAMS)
        assert "import arcpy" in result

    def test_default_params(self):
        """Generator must work with empty params dict (uses sensible defaults)."""
        result = script_overlap_pdf_report({})
        assert isinstance(result, str)
        assert "import arcpy" in result


class TestScriptContents:
    def test_contains_count_overlapping_features(self):
        result = script_overlap_pdf_report(SAMPLE_PARAMS)
        assert "CountOverlappingFeatures" in result

    def test_contains_pairwise_intersect(self):
        result = script_overlap_pdf_report(SAMPLE_PARAMS)
        assert "PairwiseIntersect" in result

    def test_contains_export_to_pdf(self):
        result = script_overlap_pdf_report(SAMPLE_PARAMS)
        assert "exportToPDF" in result

    def test_contains_export_table(self):
        result = script_overlap_pdf_report(SAMPLE_PARAMS)
        assert "ExportTable" in result

    def test_contains_arcgis_project(self):
        result = script_overlap_pdf_report(SAMPLE_PARAMS)
        assert "ArcGISProject" in result

    def test_params_injected(self):
        result = script_overlap_pdf_report(SAMPLE_PARAMS)
        assert "T2026_Q1" in result
        assert "AR_Oficial_poligono_GTM" in result
        assert r"C:\AR.gdb" in result

    def test_uses_cdg_actividad_field(self):
        """Script must read CdgActvdd for component extraction."""
        result = script_overlap_pdf_report(SAMPLE_PARAMS)
        assert "CdgActvdd" in result

    def test_component_extraction(self):
        """Script must split CdgActvdd to get C1/C2/C3 segment."""
        result = script_overlap_pdf_report(SAMPLE_PARAMS)
        assert "split" in result

    def test_layout_name_injected(self):
        result = script_overlap_pdf_report(SAMPLE_PARAMS)
        assert "Overlap_Report" in result

    def test_contains_search_cursor(self):
        """Script must iterate over intersect rows with a SearchCursor."""
        result = script_overlap_pdf_report(SAMPLE_PARAMS)
        assert "SearchCursor" in result


class TestRegistryIntegration:
    def test_registered_in_paso3_scripts(self):
        """overlap_pdf_report must appear in the PASO3_SCRIPTS registry."""
        from paso3_scripts import PASO3_SCRIPTS
        assert "overlap_pdf_report" in PASO3_SCRIPTS

    def test_registry_returns_same_function(self):
        from paso3_scripts import PASO3_SCRIPTS
        result = PASO3_SCRIPTS["overlap_pdf_report"](SAMPLE_PARAMS)
        assert isinstance(result, str)
        assert "CountOverlappingFeatures" in result
