"""Tests for _apply_ss_filters server-side row filtering.
/ Pruebas para el filtrado de filas del lado del servidor."""

import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import _apply_ss_filters  # noqa: E402


def _row(num, contrato="", trimestre=""):
    return {
        "rowNumber": num,
        "id": num,
        "cells": {
            "NÚMERO DE CONTRATO": contrato,
            "TRIMESTRE QUE REPORTA": trimestre,
        },
        "attachments": [],
        "comment": None,
    }


ROWS = [
    _row(1, "AR-PPD-001", "2025-Q1"),
    _row(2, "AR-PPD-001", "2025-Q2"),
    _row(3, "AR-PMD-010", "2025-Q1"),
    _row(4, "AR-PMD-010", "2025-Q3"),
    _row(5, "AR-PPD-002", "2025-Q3"),
]


class TestRowRangeFilter:
    def test_range(self):
        result = _apply_ss_filters(ROWS, {"rowStart": 2, "rowEnd": 4})
        assert [r["rowNumber"] for r in result] == [2, 3, 4]

    def test_no_range(self):
        result = _apply_ss_filters(ROWS, {})
        assert len(result) == 5


class TestTrimestreFilter:
    def test_single(self):
        result = _apply_ss_filters(ROWS, {"filterTrimestres": ["2025-Q1"]})
        assert len(result) == 2
        assert all(r["cells"]["TRIMESTRE QUE REPORTA"] == "2025-Q1" for r in result)

    def test_multiple(self):
        result = _apply_ss_filters(ROWS, {"filterTrimestres": ["2025-Q1", "2025-Q3"]})
        assert len(result) == 4

    def test_empty_list_no_effect(self):
        result = _apply_ss_filters(ROWS, {"filterTrimestres": []})
        assert len(result) == 5

    def test_none_no_effect(self):
        result = _apply_ss_filters(ROWS, {"filterTrimestres": None})
        assert len(result) == 5


class TestTipoFilter:
    def test_ppd(self):
        result = _apply_ss_filters(ROWS, {"filterTipos": ["PPD"]})
        assert len(result) == 3
        assert all("PPD" in r["cells"]["NÚMERO DE CONTRATO"] for r in result)

    def test_pmd(self):
        result = _apply_ss_filters(ROWS, {"filterTipos": ["PMD"]})
        assert len(result) == 2

    def test_both(self):
        result = _apply_ss_filters(ROWS, {"filterTipos": ["PPD", "PMD"]})
        assert len(result) == 5

    def test_case_insensitive(self):
        result = _apply_ss_filters(ROWS, {"filterTipos": ["ppd"]})
        assert len(result) == 3


class TestContratoFilter:
    def test_exact(self):
        result = _apply_ss_filters(ROWS, {"filterContratos": ["AR-PPD-001"]})
        assert len(result) == 2

    def test_multiple(self):
        result = _apply_ss_filters(ROWS, {"filterContratos": ["AR-PPD-001", "AR-PMD-010"]})
        assert len(result) == 4

    def test_contrato_overrides_tipo(self):
        """When both filterContratos and filterTipos are given, contrato wins."""
        result = _apply_ss_filters(ROWS, {
            "filterTipos": ["PMD"],
            "filterContratos": ["AR-PPD-001"],
        })
        assert len(result) == 2
        assert all(r["cells"]["NÚMERO DE CONTRATO"] == "AR-PPD-001" for r in result)


class TestCombinedFilters:
    def test_trimestre_and_tipo(self):
        result = _apply_ss_filters(ROWS, {
            "filterTrimestres": ["2025-Q1"],
            "filterTipos": ["PPD"],
        })
        assert len(result) == 1
        assert result[0]["rowNumber"] == 1

    def test_range_and_trimestre(self):
        result = _apply_ss_filters(ROWS, {
            "rowStart": 1,
            "rowEnd": 3,
            "filterTrimestres": ["2025-Q1"],
        })
        assert len(result) == 2
        assert [r["rowNumber"] for r in result] == [1, 3]

    def test_all_filters(self):
        result = _apply_ss_filters(ROWS, {
            "rowStart": 1,
            "rowEnd": 5,
            "filterTrimestres": ["2025-Q1", "2025-Q3"],
            "filterContratos": ["AR-PMD-010"],
        })
        assert len(result) == 2
        assert [r["rowNumber"] for r in result] == [3, 4]
