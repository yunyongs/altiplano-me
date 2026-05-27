"""Tests for G9 — Power BI PDF export guide (Strategy B: no Azure AD)."""
import pytest
from paso6_powerbi import generate_pdf_export_guide


# ---------------------------------------------------------------------------
# generate_pdf_export_guide — Strategy B (manual / no API)
# ---------------------------------------------------------------------------

class TestGeneratePdfExportGuide:
    def test_returns_string(self):
        result = generate_pdf_export_guide({})
        assert isinstance(result, str)
        assert len(result) > 50

    def test_contains_report_name(self):
        result = generate_pdf_export_guide({"report_name": "AR_Dashboard_2026"})
        assert "AR_Dashboard_2026" in result

    def test_default_report_name(self):
        result = generate_pdf_export_guide({})
        assert "AR_Dashboard" in result

    def test_contains_output_path(self):
        result = generate_pdf_export_guide({"output_path": "D:\\informes\\q2\\"})
        assert "D:\\informes\\q2\\" in result

    def test_default_output_path(self):
        result = generate_pdf_export_guide({})
        # EN: Default path must appear in guide / ES: Ruta por defecto debe aparecer
        assert "C:\\" in result

    def test_contains_quarter(self):
        result = generate_pdf_export_guide({"quarter": "T2026_Q2"})
        assert "T2026_Q2" in result

    def test_no_quarter_no_label(self):
        result = generate_pdf_export_guide({"quarter": ""})
        # EN: Quarter label only appears when quarter is given
        assert "T2026" not in result

    def test_contains_bilingual_text(self):
        result = generate_pdf_export_guide({})
        # EN: Guide must have Spanish text / ES: Guía debe tener texto en español
        assert "Exportar" in result or "Exportación" in result or "exportar" in result
        # EN: Guide must have English text
        assert "Export" in result

    def test_contains_azure_note(self):
        # EN: Guide must mention Azure AD limitation / ES: Debe mencionar limitación Azure AD
        result = generate_pdf_export_guide({})
        assert "Azure AD" in result

    def test_mcp_section_included_by_default(self):
        result = generate_pdf_export_guide({})
        # EN: MCP DAX verification step appears when include_mcp is True (default)
        assert "MCP" in result or "dax_query" in result

    def test_mcp_section_excluded(self):
        result = generate_pdf_export_guide({"include_mcp": False})
        # EN: MCP step should not appear when include_mcp is False
        assert "dax_query_operations" not in result

    def test_print_statement_present(self):
        result = generate_pdf_export_guide({})
        assert "print(" in result


# ---------------------------------------------------------------------------
# generate_pdf_export_guide — all params combined
# ---------------------------------------------------------------------------

class TestGeneratePdfExportGuideFull:
    def test_full_params(self):
        result = generate_pdf_export_guide({
            "report_name": "AR_Reporte_M_E",
            "output_path": "E:\\proyectos\\altiplano\\reportes\\",
            "quarter": "T2026_Q1",
            "include_mcp": True,
        })
        assert "AR_Reporte_M_E" in result
        assert "T2026_Q1" in result
        assert "E:\\proyectos\\altiplano\\reportes\\" in result
        assert "dax_query_operations" in result

    def test_filename_contains_quarter(self):
        # EN: PDF filename in guide should incorporate the quarter
        result = generate_pdf_export_guide({
            "report_name": "AR_Dash",
            "quarter": "T2026_Q3",
        })
        assert "AR_Dash_T2026_Q3" in result
