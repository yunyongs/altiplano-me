"""
Tests for paso6_compare.py — M&E Comparison Engine (G8).

Coverage:
  - All values match → 0 discrepancies
  - Area_ha mismatch → 1 discrepancy in output
  - decide_final_value: dafne / pbi / manual, save + load roundtrip
  - find_discrepancy_cause: field-level detection
  - load_pbi_values: inline and excel types
  - get_comparison_report: summary counts
"""
from __future__ import annotations

import json
import pathlib
import shutil
import tempfile

import pytest

# Ensure project root is importable
import sys
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from paso6_compare import (
    _COMPARE_DIR,
    compare_me_values,
    decide_final_value,
    find_discrepancy_cause,
    get_comparison_report,
    load_dafne_values,
    load_pbi_values,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

def _make_dafne_data(area_ha=100.0, bnf=5, org=3, outcome_rows=None):
    """Build a minimal dafne_data dict matching load_dafne_values output."""
    rows = outcome_rows or {"ACT001": {"Area_ha": area_ha, "pct_logro": 0.0}}
    return {
        "output": {"area_ha": area_ha, "beneficiarios": bnf, "organizaciones": org},
        "outcome": {
            cdg: {"area_ha": float(r.get("Area_ha", 0)), "pct_logro": float(r.get("pct_logro", 0))}
            for cdg, r in rows.items()
        },
        "impact": {"total_area_ha": area_ha, "kpi_threshold": None},
        "rows": rows,
        "error": None,
    }


def _make_pbi_data(area_ha=100.0, bnf=5, org=3, outcome_rows=None):
    """Build a minimal pbi_data dict matching load_pbi_values output."""
    rows = outcome_rows or {"ACT001": {"Area_ha": area_ha, "pct_logro": 0.0}}
    return {
        "output": {"area_ha": area_ha, "beneficiarios": bnf, "organizaciones": org},
        "outcome": {
            cdg: {"area_ha": float(r.get("Area_ha", 0)), "pct_logro": float(r.get("pct_logro", 0))}
            for cdg, r in rows.items()
        },
        "impact": {"total_area_ha": area_ha, "kpi_threshold": None},
        "rows": rows,
        "error": None,
    }


@pytest.fixture(autouse=True)
def isolate_compare_dir(tmp_path, monkeypatch):
    """Redirect _COMPARE_DIR to a temp directory for test isolation."""
    import paso6_compare as mod
    orig = mod._COMPARE_DIR
    tmp_compare = tmp_path / "compare"
    tmp_compare.mkdir()
    monkeypatch.setattr(mod, "_COMPARE_DIR", tmp_compare)
    yield tmp_compare
    monkeypatch.setattr(mod, "_COMPARE_DIR", orig)


# ─────────────────────────────────────────────────────────────────────────────
# compare_me_values
# ─────────────────────────────────────────────────────────────────────────────

class TestCompareMeValues:

    def test_all_match_zero_discrepancies(self):
        """All values identical → 0 discrepancies, summary.mismatches == 0."""
        dafne = _make_dafne_data(area_ha=250.0, bnf=10, org=4)
        pbi = _make_pbi_data(area_ha=250.0, bnf=10, org=4)

        result = compare_me_values(dafne, pbi)

        assert result["summary"]["mismatches"] == 0
        assert result["discrepancies"] == []
        assert result["summary"]["matches"] == result["summary"]["total_metrics"]

    def test_area_ha_mismatch_one_discrepancy(self):
        """Dafne area_ha ≠ PBI area_ha → exactly 1 output.area_ha discrepancy."""
        dafne = _make_dafne_data(area_ha=100.0, bnf=5, org=3)
        pbi = _make_pbi_data(area_ha=150.0, bnf=5, org=3)

        result = compare_me_values(dafne, pbi, metrics=["output"])

        disc = result["discrepancies"]
        assert len(disc) == 1
        assert disc[0]["metric"] == "output"
        assert disc[0]["field"] == "area_ha"
        assert abs(disc[0]["delta"] - 50.0) < 0.01

    def test_within_tolerance_is_match(self):
        """Values within 0.01 tolerance should be considered a match."""
        dafne = _make_dafne_data(area_ha=100.005)
        pbi = _make_pbi_data(area_ha=100.005)  # intentionally identical

        result = compare_me_values(dafne, pbi, metrics=["output"])
        # Also test just barely in tolerance
        dafne2 = _make_dafne_data(area_ha=100.0)
        pbi2 = _make_pbi_data(area_ha=100.009)
        result2 = compare_me_values(dafne2, pbi2, metrics=["output"])
        assert result2["output"]["area_ha"]["match"] is True

    def test_outcome_mismatch_detected(self):
        """Outcome row area_ha differs → discrepancy with cdg field set."""
        dafne = _make_dafne_data(outcome_rows={"ACT001": {"Area_ha": 50.0, "pct_logro": 0.8}})
        pbi = _make_pbi_data(outcome_rows={"ACT001": {"Area_ha": 60.0, "pct_logro": 0.8}})

        result = compare_me_values(dafne, pbi, metrics=["outcome"])

        disc = result["discrepancies"]
        assert any(d.get("cdg") == "ACT001" and "area_ha" in d["field"] for d in disc)

    def test_impact_mismatch_detected(self):
        """Impact total_area_ha differs → impact discrepancy."""
        dafne = _make_dafne_data(area_ha=200.0)
        pbi = _make_pbi_data(area_ha=180.0)

        result = compare_me_values(dafne, pbi, metrics=["impact"])

        assert result["summary"]["mismatches"] >= 1
        assert result["impact"]["total_area_ha"]["match"] is False

    def test_result_structure(self):
        """Result always includes output, outcome, impact, discrepancies, summary."""
        dafne = _make_dafne_data()
        pbi = _make_pbi_data()
        result = compare_me_values(dafne, pbi)

        assert "output" in result
        assert "outcome" in result
        assert "impact" in result
        assert "discrepancies" in result
        assert "summary" in result
        assert "total_metrics" in result["summary"]
        assert "matches" in result["summary"]
        assert "mismatches" in result["summary"]


# ─────────────────────────────────────────────────────────────────────────────
# decide_final_value  (save + load roundtrip)
# ─────────────────────────────────────────────────────────────────────────────

class TestDecideFinalValue:

    def test_decide_dafne(self, isolate_compare_dir):
        """decision='dafne' → final_value equals dafne_val."""
        entry = decide_final_value(
            metric="output.area_ha",
            dafne_val=100.0,
            pbi_val=150.0,
            decision="dafne",
            quarter="T2026_Q2",
        )
        assert entry["final_value"] == 100.0
        assert entry["decision"] == "dafne"

    def test_decide_pbi(self, isolate_compare_dir):
        """decision='pbi' → final_value equals pbi_val."""
        entry = decide_final_value(
            metric="output.area_ha",
            dafne_val=100.0,
            pbi_val=150.0,
            decision="pbi",
            quarter="T2026_Q2",
        )
        assert entry["final_value"] == 150.0
        assert entry["decision"] == "pbi"

    def test_decide_manual(self, isolate_compare_dir):
        """decision='manual' + manual_val → final_value equals manual_val."""
        entry = decide_final_value(
            metric="output.area_ha",
            dafne_val=100.0,
            pbi_val=150.0,
            decision="manual",
            manual_val=125.0,
            quarter="T2026_Q2",
        )
        assert entry["final_value"] == 125.0
        assert entry["decision"] == "manual"

    def test_manual_without_value_raises(self, isolate_compare_dir):
        """decision='manual' without manual_val raises ValueError."""
        with pytest.raises(ValueError):
            decide_final_value(
                metric="output.area_ha",
                dafne_val=100.0,
                pbi_val=150.0,
                decision="manual",
                quarter="T2026_Q2",
            )

    def test_invalid_decision_raises(self, isolate_compare_dir):
        """Unknown decision value raises ValueError."""
        with pytest.raises(ValueError):
            decide_final_value(
                metric="output.area_ha",
                dafne_val=100.0,
                pbi_val=150.0,
                decision="unknown",
                quarter="T2026_Q2",
            )

    def test_save_load_roundtrip(self, isolate_compare_dir):
        """Saved decision can be loaded back via get_comparison_report."""
        decide_final_value(
            metric="output.area_ha",
            dafne_val=100.0,
            pbi_val=150.0,
            decision="dafne",
            quarter="T2026_Q2",
        )
        decide_final_value(
            metric="output.beneficiarios",
            dafne_val=5,
            pbi_val=6,
            decision="pbi",
            quarter="T2026_Q2",
        )

        report = get_comparison_report("T2026_Q2")
        metrics_saved = {d["metric"] for d in report["decisions"]}
        assert "output.area_ha" in metrics_saved
        assert "output.beneficiarios" in metrics_saved
        assert report["summary"]["total_decisions"] == 2
        assert report["summary"]["dafne"] == 1
        assert report["summary"]["pbi"] == 1

    def test_upsert_replaces_existing_metric(self, isolate_compare_dir):
        """Saving the same metric twice overwrites the first entry (upsert)."""
        decide_final_value("output.area_ha", 100.0, 150.0, "dafne", quarter="T2026_Q2")
        decide_final_value("output.area_ha", 100.0, 150.0, "pbi", quarter="T2026_Q2")

        report = get_comparison_report("T2026_Q2")
        entries = [d for d in report["decisions"] if d["metric"] == "output.area_ha"]
        assert len(entries) == 1
        assert entries[0]["decision"] == "pbi"


# ─────────────────────────────────────────────────────────────────────────────
# find_discrepancy_cause
# ─────────────────────────────────────────────────────────────────────────────

class TestFindDiscrepancyCause:

    def test_no_difference_returns_match(self):
        """Identical rows → field_diffs empty, match True."""
        row = {"Area_ha": 50.0, "Pct_Logro": 0.9, "Nombre": "Test"}
        result = find_discrepancy_cause(row, row.copy(), "ACT001")
        assert result["match"] is True
        assert result["field_diffs"] == []

    def test_area_ha_diff_detected(self):
        """Different Area_ha → field_diffs contains Area_ha."""
        dafne_row = {"Area_ha": 50.0, "Pct_Logro": 0.9}
        pbi_row = {"Area_ha": 60.0, "Pct_Logro": 0.9}
        result = find_discrepancy_cause(dafne_row, pbi_row, "ACT001")
        assert result["match"] is False
        fields = [d["field"] for d in result["field_diffs"]]
        assert "Area_ha" in fields

    def test_multiple_field_diffs(self):
        """Two differing fields → two entries in field_diffs."""
        dafne_row = {"Area_ha": 50.0, "Pct_Logro": 0.9, "Estado": "activo"}
        pbi_row = {"Area_ha": 60.0, "Pct_Logro": 0.8, "Estado": "activo"}
        result = find_discrepancy_cause(dafne_row, pbi_row, "ACT001")
        assert len(result["field_diffs"]) == 2

    def test_none_vs_value_is_diff(self):
        """None vs numeric → treated as a field difference."""
        dafne_row = {"Area_ha": None}
        pbi_row = {"Area_ha": 10.0}
        result = find_discrepancy_cause(dafne_row, pbi_row, "ACT002")
        assert result["match"] is False

    def test_cdg_returned_correctly(self):
        """cdg field in result matches the argument."""
        result = find_discrepancy_cause({}, {}, "ACT_XYZ")
        assert result["cdg"] == "ACT_XYZ"


# ─────────────────────────────────────────────────────────────────────────────
# load_pbi_values — inline and excel types
# ─────────────────────────────────────────────────────────────────────────────

class TestLoadPbiValues:

    def test_inline_type(self):
        """inline pbi_source passthrough."""
        src = {
            "type": "inline",
            "output": {"area_ha": 100.0, "beneficiarios": 5, "organizaciones": 3},
            "outcome": {},
            "impact": {"total_area_ha": 100.0},
        }
        result = load_pbi_values(src)
        assert result["error"] is None
        assert result["output"]["area_ha"] == 100.0

    def test_unknown_type_returns_error(self):
        """Unknown pbi_source type → error set."""
        src = {"type": "graphql"}
        result = load_pbi_values(src)
        assert result["error"] is not None

    def test_excel_missing_file_returns_error(self):
        """Excel path that doesn't exist → error set."""
        src = {"type": "excel", "path": "/nonexistent/path.xlsx"}
        result = load_pbi_values(src)
        assert result["error"] is not None


# ─────────────────────────────────────────────────────────────────────────────
# load_dafne_values — missing file
# ─────────────────────────────────────────────────────────────────────────────

class TestLoadDafneValues:

    def test_missing_file_returns_error(self):
        """File that doesn't exist → error set."""
        result = load_dafne_values("/nonexistent/Tbl_Integrado.xlsx")
        assert result["error"] is not None


# ─────────────────────────────────────────────────────────────────────────────
# get_comparison_report — empty quarter
# ─────────────────────────────────────────────────────────────────────────────

class TestGetComparisonReport:

    def test_empty_quarter_returns_empty(self, isolate_compare_dir):
        """Quarter with no decisions → empty decisions list, zeros in summary."""
        report = get_comparison_report("T2099_Q9")
        assert report["decisions"] == []
        assert report["summary"]["total_decisions"] == 0
        assert report["summary"]["dafne"] == 0
        assert report["summary"]["pbi"] == 0
        assert report["summary"]["manual"] == 0
