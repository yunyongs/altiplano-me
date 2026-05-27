"""
Tests for paso3_criteria.py

EN: Verifies save/load roundtrip, per-quarter isolation, add_criterion,
    list_criteria_quarters, and export_criteria_pdf path return.
ES: Verifica save/load ida y vuelta, aislamiento por trimestre,
    add_criterion, list_criteria_quarters y retorno de ruta de export_criteria_pdf.
"""
from __future__ import annotations

import json
import os
import pathlib
import tempfile

import pytest

# ---------------------------------------------------------------------------
# Fixture: isolate data directory to a temp folder for each test
# EN: Redirect _DATA_DIR so tests never write to the real data/criteria/.
# ES: Redirige _DATA_DIR para que los tests nunca escriban en data/criteria/ real.
# ---------------------------------------------------------------------------
import paso3_criteria as criteria_mod


@pytest.fixture(autouse=True)
def _isolated_data_dir(tmp_path: pathlib.Path, monkeypatch):
    """Point _DATA_DIR to a temp directory for every test."""
    fake_dir = tmp_path / "criteria"
    monkeypatch.setattr(criteria_mod, "_DATA_DIR", fake_dir)
    yield fake_dir


# ---------------------------------------------------------------------------
# save / load roundtrip
# EN: Saved entries must be retrievable exactly as saved.
# ES: Las entradas guardadas deben recuperarse exactamente como se guardaron.
# ---------------------------------------------------------------------------

def test_save_and_load_roundtrip():
    entries = [
        {
            "layer": "AR_Oficial_poligono_GTM",
            "reason": "Duplicado con C2",
            "decision": "Eliminar usando Erase",
            "cdg_actividad": "241014_C2_XYZ_a",
            "recorded_by": "coordinator",
        }
    ]
    saved = criteria_mod.save_criteria("T2026_Q1", entries)
    loaded = criteria_mod.load_criteria("T2026_Q1")

    assert loaded["quarter"] == "T2026_Q1"
    assert len(loaded["entries"]) == 1
    entry = loaded["entries"][0]
    assert entry["layer"] == "AR_Oficial_poligono_GTM"
    assert entry["reason"] == "Duplicado con C2"
    assert entry["decision"] == "Eliminar usando Erase"
    assert entry["cdg_actividad"] == "241014_C2_XYZ_a"
    # EN: id must be assigned / ES: el id debe estar asignado
    assert entry.get("id") == 1


def test_load_returns_empty_for_missing_quarter():
    # EN: No file → empty entries list / ES: Sin archivo → lista de entradas vacía
    result = criteria_mod.load_criteria("T2099_Q9")
    assert result["quarter"] == "T2099_Q9"
    assert result["entries"] == []
    assert result["recorded_at"] is None


# ---------------------------------------------------------------------------
# Per-quarter isolation
# EN: Criteria for different quarters must not interfere.
# ES: Los criterios de distintos trimestres no deben interferir.
# ---------------------------------------------------------------------------

def test_per_quarter_isolation():
    criteria_mod.save_criteria("T2026_Q1", [
        {"layer": "L1", "reason": "R1", "decision": "D1", "cdg_actividad": "C1"}
    ])
    criteria_mod.save_criteria("T2026_Q2", [
        {"layer": "L2", "reason": "R2", "decision": "D2", "cdg_actividad": "C2"},
        {"layer": "L3", "reason": "R3", "decision": "D3", "cdg_actividad": "C3"},
    ])

    q1 = criteria_mod.load_criteria("T2026_Q1")
    q2 = criteria_mod.load_criteria("T2026_Q2")

    assert len(q1["entries"]) == 1
    assert len(q2["entries"]) == 2
    assert q1["entries"][0]["layer"] == "L1"
    assert q2["entries"][0]["layer"] == "L2"


# ---------------------------------------------------------------------------
# add_criterion
# EN: Single-entry append must increment id and persist.
# ES: El append de una entrada debe incrementar el id y persistir.
# ---------------------------------------------------------------------------

def test_add_criterion_increments_id():
    criteria_mod.save_criteria("T2026_Q1", [
        {"layer": "L1", "reason": "R1", "decision": "D1"}
    ])
    new_entry = criteria_mod.add_criterion("T2026_Q1", {
        "layer": "L2", "reason": "R2", "decision": "D2"
    })
    assert new_entry["id"] == 2

    loaded = criteria_mod.load_criteria("T2026_Q1")
    assert len(loaded["entries"]) == 2
    assert loaded["entries"][1]["layer"] == "L2"


def test_add_criterion_to_empty_quarter():
    entry = criteria_mod.add_criterion("T2026_Q3", {
        "layer": "LNew", "reason": "RNew", "decision": "DNew"
    })
    assert entry["id"] == 1
    loaded = criteria_mod.load_criteria("T2026_Q3")
    assert len(loaded["entries"]) == 1


# ---------------------------------------------------------------------------
# list_criteria_quarters
# EN: Returns sorted list of quarters with saved files.
# ES: Devuelve lista ordenada de trimestres con archivos guardados.
# ---------------------------------------------------------------------------

def test_list_criteria_quarters_empty():
    assert criteria_mod.list_criteria_quarters() == []


def test_list_criteria_quarters_multiple():
    criteria_mod.save_criteria("T2026_Q2", [{"layer": "L", "reason": "R", "decision": "D"}])
    criteria_mod.save_criteria("T2026_Q1", [{"layer": "L", "reason": "R", "decision": "D"}])
    quarters = criteria_mod.list_criteria_quarters()
    assert "T2026_Q1" in quarters
    assert "T2026_Q2" in quarters
    # EN: Must be sorted / ES: Debe estar ordenado
    assert quarters == sorted(quarters)


# ---------------------------------------------------------------------------
# export_criteria_pdf — path return
# EN: export_criteria_pdf must return a path pointing to an existing file.
# ES: export_criteria_pdf debe devolver una ruta a un archivo existente.
# ---------------------------------------------------------------------------

def test_export_criteria_pdf_returns_existing_path(tmp_path):
    criteria_mod.save_criteria("T2026_Q1", [
        {"layer": "L1", "reason": "R1", "decision": "D1", "cdg_actividad": "CA1"},
        {"layer": "L2", "reason": "R2", "decision": "D2", "cdg_actividad": "CA2"},
    ])
    out = str(tmp_path / "T2026_Q1_criteria.pdf")
    result = criteria_mod.export_criteria_pdf("T2026_Q1", out)

    # EN: Must return a path / ES: Debe devolver una ruta
    assert result is not None
    assert isinstance(result, str)
    # EN: File must exist (pdf or html fallback) / ES: El archivo debe existir (pdf o html)
    assert pathlib.Path(result).exists(), f"Expected file at {result}"


def test_export_criteria_pdf_empty_quarter(tmp_path):
    # EN: Exporting an empty quarter must still produce a file.
    # ES: Exportar un trimestre vacío debe producir un archivo igualmente.
    out = str(tmp_path / "empty_criteria.pdf")
    result = criteria_mod.export_criteria_pdf("T2099_Q1", out)
    assert pathlib.Path(result).exists()
