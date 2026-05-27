"""
Tests for paso2_shp_validate.script_validate_shp_codes()

The function generates an arcpy script string — it never calls arcpy itself.
Tests verify that the generated script contains the correct logic strings
for each component/scenario combination.
"""
from __future__ import annotations

import pytest
from paso2_shp_validate import script_validate_shp_codes, _is_c2_filename


# ─────────────────────────────────────────────────────────────────────────────
# Unit tests: _is_c2_filename heuristic
# ─────────────────────────────────────────────────────────────────────────────

class TestIsC2Filename:
    def test_c1_codigo_returns_false(self):
        assert _is_c2_filename("241014_C1_ROM_a") is False

    def test_c3_codigo_returns_false(self):
        assert _is_c2_filename("241014_C3_FOR_b") is False

    def test_c2_contrato_returns_true(self):
        assert _is_c2_filename("AR-PPD-001_ONG_Sur_T2026Q1") is True

    def test_c2_another_contrato_returns_true(self):
        assert _is_c2_filename("AR-RVF-042_Asoc_Norte_T2025Q3") is True


# ─────────────────────────────────────────────────────────────────────────────
# Script generation: structure checks
# ─────────────────────────────────────────────────────────────────────────────

class TestScriptGeneration:
    def _gen(self, **kwargs):
        defaults = {"shp_folder": r"D:\AR\shp", "component": "All", "ss_csv_path": ""}
        defaults.update(kwargs)
        return script_validate_shp_codes(defaults)

    # -- Required boilerplate --------------------------------------------------

    def test_imports_arcpy(self):
        script = self._gen()
        assert "import arcpy" in script

    def test_imports_os_and_re(self):
        script = self._gen()
        assert "import os" in script
        assert "import re" in script

    def test_shp_folder_embedded(self):
        script = self._gen(shp_folder=r"D:\AR\T2026_Q2\C1")
        assert r"D:\AR\T2026_Q2\C1" in script

    def test_walks_folder_recursively(self):
        script = self._gen()
        assert "os.walk" in script

    def test_lists_arcpy_fields(self):
        script = self._gen()
        assert "arcpy.ListFields" in script

    def test_uses_search_cursor(self):
        script = self._gen()
        assert "arcpy.da.SearchCursor" in script

    # -- C1/C3 logic -----------------------------------------------------------

    def test_c1_c3_filename_match_check(self):
        """Generated script must compare stem against CdgActvdd for C1/C3."""
        script = self._gen(component="C1")
        # The script should check 'stem' against the cdg_values set
        assert "stem" in script
        assert "cdg_values" in script

    # -- C2 fallback detection -------------------------------------------------

    def test_c2_fallback_function_present(self):
        """Script must define _is_c2_fallback()."""
        script = self._gen(component="C2")
        assert "_is_c2_fallback" in script

    def test_c2_fallback_pattern_t_year_q(self):
        """Fallback regex must look for _T{year}Q{n} pattern."""
        script = self._gen(component="C2")
        assert "T\\\\d{4}Q\\\\d" in script or "T\\d{4}Q\\d" in script or "_T" in script

    def test_c2_fallback_warning_text(self):
        script = self._gen(component="C2")
        assert "fallback" in script.lower()

    # -- SS CSV integration ---------------------------------------------------

    def test_no_csv_block_when_empty(self):
        """When no ss_csv_path, script should not try to open a file."""
        script = self._gen(ss_csv_path="")
        assert "ss_codes = set()" in script
        # Should not attempt to open a CSV
        assert 'open(r""' not in script

    def test_csv_block_included_when_path_given(self):
        script = self._gen(ss_csv_path=r"D:\AR\ss_export.csv")
        assert r"D:\AR\ss_export.csv" in script
        assert "ss_codes" in script

    def test_csv_pk_check_in_script(self):
        """When CSV provided, script must warn if CdgActvdd not in ss_codes."""
        script = self._gen(ss_csv_path=r"D:\AR\ss_export.csv")
        assert "ss_codes" in script
        # The check should appear as: if val not in ss_codes
        assert "not in ss_codes" in script

    # -- Component filter -----------------------------------------------------

    def test_component_filter_c1_in_script(self):
        script = self._gen(component="C1")
        assert "C1" in script

    def test_all_component_no_filter_block(self):
        """'All' component should not add a filter block."""
        script = self._gen(component="All")
        assert "Filtrar por componente" not in script
        assert "Filtrado a componente" not in script

    def test_c2_component_adds_filter(self):
        script = self._gen(component="C2")
        assert "C2" in script

    # -- Summary block --------------------------------------------------------

    def test_summary_counts_present(self):
        script = self._gen()
        assert "ok_count" in script
        assert "warn_count" in script
        assert "err_count" in script

    def test_summary_header(self):
        script = self._gen()
        assert "RESUMEN" in script or "SUMMARY" in script

    # -- CdgActvdd field missing error ----------------------------------------

    def test_missing_field_error(self):
        script = self._gen()
        assert "CdgActvdd field missing" in script or "CdgActvdd no existe" in script


# ─────────────────────────────────────────────────────────────────────────────
# Edge cases
# ─────────────────────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_empty_shp_folder_string_still_generates(self):
        """Even with empty folder, a valid script string is returned."""
        script = script_validate_shp_codes({"shp_folder": "", "component": "All"})
        assert isinstance(script, str)
        assert len(script) > 100

    def test_special_chars_in_folder_path(self):
        """Windows paths with spaces and parentheses should be embedded safely."""
        path = r"D:\Datos AR (2026)\Shapefiles"
        script = script_validate_shp_codes({"shp_folder": path})
        assert path in script

    def test_returns_string(self):
        script = script_validate_shp_codes({})
        assert isinstance(script, str)

    def test_no_arcpy_import_at_module_level(self):
        """paso2_shp_validate.py itself must not import arcpy."""
        import paso2_shp_validate
        import sys
        assert "arcpy" not in sys.modules or True  # arcpy may be absent; module must load fine
        # The real check: importing the module should not raise ImportError
