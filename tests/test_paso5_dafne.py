"""
Tests for paso5_dafne: G11 functions
  - place_dafne_file
  - validate_integrado_xlsx
  - get_integrado_status
"""
from __future__ import annotations

import json
import pathlib
import shutil
import tempfile

import pytest

from paso5_dafne import (
    DEFAULT_FILENAME,
    REQUIRED_SHEETS,
    get_integrado_status,
    place_dafne_file,
    validate_integrado_xlsx,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def tmp(tmp_path):
    return tmp_path


@pytest.fixture(autouse=True)
def _allow_tmp_roots(tmp_path, monkeypatch):
    """Allow tmp_path as a valid root for safe_resolve path validation."""
    import paso5_dafne
    monkeypatch.setattr(paso5_dafne, "_allowed_roots", lambda: [str(tmp_path)])


def _make_xlsx(path: pathlib.Path, sheets: list[str]) -> pathlib.Path:
    """Create a minimal xlsx at path with given sheet names."""
    import openpyxl
    wb = openpyxl.Workbook()
    for i, name in enumerate(sheets):
        if i == 0:
            ws = wb.active
            ws.title = name
        else:
            wb.create_sheet(name)
    wb.save(str(path))
    return path


# ─────────────────────────────────────────────────────────────────────────────
# place_dafne_file
# ─────────────────────────────────────────────────────────────────────────────

class TestPlaceDafneFile:
    def test_copies_file_to_dest(self, tmp):
        src = tmp / "source" / "Tbl_Integrado.xlsx"
        src.parent.mkdir()
        src.write_bytes(b"fake xlsx")
        dest_dir = tmp / "base"

        result = place_dafne_file(str(src), str(dest_dir))

        assert result["success"] is True
        assert result["error"] is None
        assert pathlib.Path(result["dest"]).exists()
        assert result["backup"] is None

    def test_creates_dest_dir_if_missing(self, tmp):
        src = tmp / "src.xlsx"
        src.write_bytes(b"xlsx")
        dest_dir = tmp / "new" / "nested"

        result = place_dafne_file(str(src), str(dest_dir))

        assert result["success"] is True
        assert dest_dir.exists()

    def test_custom_filename(self, tmp):
        src = tmp / "my.xlsx"
        src.write_bytes(b"xlsx")
        dest_dir = tmp / "base"

        result = place_dafne_file(str(src), str(dest_dir), filename="custom.xlsx")

        assert result["success"] is True
        assert pathlib.Path(result["dest"]).name == "custom.xlsx"

    def test_backup_created_when_file_exists(self, tmp):
        src = tmp / "new.xlsx"
        src.write_bytes(b"new content")
        dest_dir = tmp / "base"
        dest_dir.mkdir()
        existing = dest_dir / DEFAULT_FILENAME
        existing.write_bytes(b"old content")

        result = place_dafne_file(str(src), str(dest_dir))

        assert result["success"] is True
        assert result["backup"] is not None
        assert pathlib.Path(result["backup"]).exists()
        # ES: Verificar que el contenido nuevo está en destino / EN: New content at dest
        assert pathlib.Path(result["dest"]).read_bytes() == b"new content"

    def test_missing_source_returns_error(self, tmp):
        result = place_dafne_file(str(tmp / "nonexistent.xlsx"), str(tmp / "dest"))

        assert result["success"] is False
        assert result["error"] is not None


# ─────────────────────────────────────────────────────────────────────────────
# validate_integrado_xlsx
# ─────────────────────────────────────────────────────────────────────────────

class TestValidateIntegradoXlsx:
    def test_valid_file_with_all_required_sheets(self, tmp):
        fp = tmp / "Tbl_Integrado.xlsx"
        _make_xlsx(fp, REQUIRED_SHEETS)

        result = validate_integrado_xlsx(str(fp))

        assert result["valid"] is True
        assert result["missing_sheets"] == []
        assert result["error"] is None

    def test_missing_one_sheet(self, tmp):
        fp = tmp / "Tbl_Integrado.xlsx"
        _make_xlsx(fp, REQUIRED_SHEETS[:-1])  # omit last

        result = validate_integrado_xlsx(str(fp))

        assert result["valid"] is False
        assert REQUIRED_SHEETS[-1] in result["missing_sheets"]

    def test_missing_all_sheets(self, tmp):
        fp = tmp / "Tbl_Integrado.xlsx"
        _make_xlsx(fp, ["Sheet1"])

        result = validate_integrado_xlsx(str(fp))

        assert result["valid"] is False
        assert len(result["missing_sheets"]) == len(REQUIRED_SHEETS)

    def test_extra_sheets_produce_warning(self, tmp):
        fp = tmp / "Tbl_Integrado.xlsx"
        _make_xlsx(fp, REQUIRED_SHEETS + ["ExtraSheet"])

        result = validate_integrado_xlsx(str(fp))

        assert result["valid"] is True
        assert any("ExtraSheet" in w for w in result["warnings"])

    def test_nonexistent_file_returns_error(self, tmp):
        result = validate_integrado_xlsx(str(tmp / "missing.xlsx"))

        assert result["valid"] is False
        assert result["error"] is not None

    def test_found_sheets_listed(self, tmp):
        fp = tmp / "Tbl_Integrado.xlsx"
        _make_xlsx(fp, REQUIRED_SHEETS)

        result = validate_integrado_xlsx(str(fp))

        for sheet in REQUIRED_SHEETS:
            assert sheet in result["found_sheets"]


# ─────────────────────────────────────────────────────────────────────────────
# get_integrado_status
# ─────────────────────────────────────────────────────────────────────────────

class TestGetIntegradoStatus:
    def test_file_present(self, tmp):
        target = tmp / DEFAULT_FILENAME
        target.write_bytes(b"x" * 2048)

        result = get_integrado_status(str(tmp))

        assert result["exists"] is True
        assert result["modified_at"] is not None
        assert result["size_kb"] is not None
        assert result["size_kb"] > 0

    def test_file_absent(self, tmp):
        result = get_integrado_status(str(tmp))

        assert result["exists"] is False
        assert result["modified_at"] is None
        assert result["size_kb"] is None

    def test_custom_filename(self, tmp):
        (tmp / "custom.xlsx").write_bytes(b"data")

        result = get_integrado_status(str(tmp), filename="custom.xlsx")

        assert result["exists"] is True
