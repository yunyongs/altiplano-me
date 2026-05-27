"""Tests for paso1_quarterly.py — quarterly folder structure and shapefile placement."""
import os
import struct
import zipfile
import tempfile
import pytest

from paso1_quarterly import (
    create_quarterly_structure,
    current_quarter,
    place_shapefile,
    quarter_options,
)


# ---------------------------------------------------------------------------
# current_quarter / quarter_options
# ---------------------------------------------------------------------------

class TestCurrentQuarter:
    def test_format(self):
        q = current_quarter()
        # EN: Must match "T{year}_Q{1-4}"  /  ES: Debe coincidir con "T{año}_Q{1-4}"
        import re
        assert re.match(r"^T\d{4}_Q[1-4]$", q), f"Unexpected format: {q}"

    def test_quarter_options_length(self):
        opts = quarter_options(n_past=4)
        assert len(opts) == 6  # 4 past + current + 1 future (default n_future=1)

    def test_quarter_options_keys(self):
        opts = quarter_options(n_past=2)
        for opt in opts:
            assert "value" in opt
            assert "label" in opt
            assert opt["value"].startswith("T")


# ---------------------------------------------------------------------------
# create_quarterly_structure
# ---------------------------------------------------------------------------

class TestCreateQuarterlyStructure:
    def test_creates_correct_path(self, tmp_path):
        folder = create_quarterly_structure(str(tmp_path), "T2026_Q2", "C1")
        expected = tmp_path / "T2026_Q2" / "C1"
        assert os.path.isdir(folder)
        assert os.path.abspath(str(expected)) == folder

    def test_idempotent(self, tmp_path):
        # EN: Calling twice should not raise  /  ES: Llamar dos veces no debe lanzar error
        create_quarterly_structure(str(tmp_path), "T2026_Q2", "C1")
        folder = create_quarterly_structure(str(tmp_path), "T2026_Q2", "C1")
        assert os.path.isdir(folder)

    def test_all_components(self, tmp_path):
        for comp in ("C1", "C2", "C3"):
            folder = create_quarterly_structure(str(tmp_path), "T2026_Q1", comp)
            assert os.path.isdir(folder)
            assert comp in folder

    def test_empty_quarter_raises(self, tmp_path):
        with pytest.raises(ValueError):
            create_quarterly_structure(str(tmp_path), "", "C1")

    def test_empty_component_raises(self, tmp_path):
        with pytest.raises(ValueError):
            create_quarterly_structure(str(tmp_path), "T2026_Q1", "")

    def test_sanitizes_special_chars(self, tmp_path):
        # EN: Should not create invalid folder names
        folder = create_quarterly_structure(str(tmp_path), "T2026/Q1", "C 1")
        assert os.path.isdir(folder)


# ---------------------------------------------------------------------------
# place_shapefile — helpers
# ---------------------------------------------------------------------------

def _make_zip(dest_dir: str, zip_name: str, files: list[str]) -> str:
    """Create a ZIP with the given file names (empty content)."""
    zip_path = os.path.join(dest_dir, zip_name)
    with zipfile.ZipFile(zip_path, "w") as zf:
        for fname in files:
            zf.writestr(fname, b"")
    return zip_path


def _shp_header(shape_type: int = 5) -> bytes:
    """Return a minimal 100-byte .shp file header with the given shape type."""
    buf = bytearray(100)
    # File code 9994 at byte 0 (big-endian)
    struct.pack_into(">i", buf, 0, 9994)
    # File length in 16-bit words at byte 24 (big-endian) — 50 = 100/2
    struct.pack_into(">i", buf, 24, 50)
    # Version 1000 at byte 28 (little-endian)
    struct.pack_into("<i", buf, 28, 1000)
    # Shape type at byte 32 (little-endian)
    struct.pack_into("<i", buf, 32, shape_type)
    return bytes(buf)


def _make_shp_zip(dest_dir: str, zip_name: str, basename: str,
                  shape_type: int = 5) -> str:
    """Create a ZIP with a minimal valid shapefile (shp+shx+dbf+prj)."""
    zip_path = os.path.join(dest_dir, zip_name)
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr(f"{basename}.shp", _shp_header(shape_type))
        zf.writestr(f"{basename}.shx", b"")
        zf.writestr(f"{basename}.dbf", b"")
        zf.writestr(f"{basename}.prj", b"")
    return zip_path


# ---------------------------------------------------------------------------
# place_shapefile — C1/C3 (identifier = CODIGO)
# ---------------------------------------------------------------------------

class TestPlaceShapefileC1:
    def test_extracts_to_identifier_subfolder(self, tmp_path):
        zip_path = _make_shp_zip(str(tmp_path), "241014_C1_ROM_a.zip",
                                 "241014_C1_ROM_a", shape_type=5)

        result = place_shapefile(zip_path, str(tmp_path), "241014_C1_ROM_a", "C1",
                                 abe_value="Plantaciones Forestales")

        assert result["ok"] is True
        assert result["component"] == "C1"
        assert result["shp_count"] == 1
        # Folder should be the -Shapes subfolder
        expected_shapes = tmp_path / "241014_C1_ROM_a" / "241014_C1_ROM_a-Shapes"
        assert os.path.isdir(result["folder"])
        assert os.path.abspath(str(expected_shapes)) == result["folder"]
        # Renamed files should exist
        assert "241014_C1_ROM_a-plant_polygon.shp" in result["files"]

    def test_c3_same_as_c1(self, tmp_path):
        zip_path = _make_shp_zip(str(tmp_path), "code_c3.zip", "act_c3", shape_type=1)
        result = place_shapefile(zip_path, str(tmp_path), "act_c3", "C3",
                                 abe_value="Sistema Silvopastoril")
        assert result["ok"] is True
        assert result["component"] == "C3"
        assert "act_c3-silvo_point.shp" in result["files"]

    def test_no_shp_returns_not_ok(self, tmp_path):
        zip_path = _make_zip(str(tmp_path), "nodata.zip", ["readme.txt"])
        result = place_shapefile(zip_path, str(tmp_path), "nodata", "C1")
        assert result["ok"] is False
        assert len(result["errors"]) > 0


# ---------------------------------------------------------------------------
# place_shapefile — C2 (identifier = CONTRATO_ORG_QUARTER)
# ---------------------------------------------------------------------------

class TestPlaceShapefileC2:
    def test_c2_identifier_used_as_subfolder(self, tmp_path):
        identifier = "AR-PPD-001_ONG_Sur_T2026Q1"
        zip_path = _make_shp_zip(str(tmp_path), identifier + ".zip",
                                 "area", shape_type=5)

        result = place_shapefile(zip_path, str(tmp_path), identifier, "C2",
                                 abe_value="Reforestación con Fines de Restauración")

        assert result["ok"] is True
        assert result["component"] == "C2"
        safe_id = "AR-PPD-001_ONG_Sur_T2026Q1"
        assert safe_id in result["folder"]
        assert "Shapes" in result["folder"]

    def test_files_list_populated(self, tmp_path):
        zip_path = _make_shp_zip(str(tmp_path), "c2.zip", "poly", shape_type=5)
        result = place_shapefile(zip_path, str(tmp_path), "c2_id", "C2",
                                 abe_value="Plantaciones Forestales")
        # Renamed files should be in the list
        assert any(f.endswith(".shp") for f in result["files"])
        assert any(f.endswith(".dbf") for f in result["files"])

    def test_unknown_abe_fallback(self, tmp_path):
        """When no abe_value and no DBF field, abbreviation is 'unknown'."""
        zip_path = _make_shp_zip(str(tmp_path), "c2_unk.zip", "unk", shape_type=1)
        result = place_shapefile(zip_path, str(tmp_path), "c2_unk", "C2")
        assert result["ok"] is True
        assert "c2_unk-unknown_point.shp" in result["files"]

    def test_multi_shp_same_folder(self, tmp_path):
        """Two SHP ZIPs with the same identifier share one folder.

        Simulates C2 with multiple attachments (e.g. anual + sueloyagua).
        Both should coexist in the same -Shapes subfolder.
        / Dos ZIP SHP con el mismo identificador comparten una carpeta.
        """
        identifier = "AR-PPD-050_AYUDA-GT_2025-Q4"
        # First ZIP: "anual" type (polygon)
        zip1 = _make_shp_zip(str(tmp_path), "shp_anual.zip",
                             "anual_data", shape_type=5)
        r1 = place_shapefile(zip1, str(tmp_path), identifier, "C2",
                             abe_value="Sistema Agroforestal | Cultivos anuales")
        assert r1["ok"] is True
        folder1 = r1["folder"]

        # Second ZIP: "sueloyagua" type (polygon)
        zip2 = _make_shp_zip(str(tmp_path), "shp_cs.zip",
                             "cs_data", shape_type=5)
        r2 = place_shapefile(zip2, str(tmp_path), identifier, "C2",
                             abe_value="Sistema Agroforestal | Conservación de suelo y agua")
        assert r2["ok"] is True
        folder2 = r2["folder"]

        # Both should be in the SAME -Shapes folder
        assert folder1 == folder2

        # Both SHP files should exist in that folder
        all_shps = [f for f in os.listdir(folder1) if f.endswith(".shp")]
        assert len(all_shps) == 2
        # One should contain "anual", the other "sueloyagua"
        shp_names = " ".join(all_shps)
        assert "anual" in shp_names
        assert "sueloyagua" in shp_names

    def test_orig_names_stores_zip_name(self, tmp_path):
        """_orig_names.json should store zip_name from orig_att_name parameter.

        When multiple ZIPs come from same summary row, each shapefile must
        track which original attachment it came from.
        """
        identifier = "AR-PPD-013_JEPLE_2025-Q1"
        zip1 = _make_shp_zip(str(tmp_path), "saf1.zip",
                              "parcels_saf1", shape_type=5)
        r1 = place_shapefile(zip1, str(tmp_path), identifier, "C2",
                             abe_value="Sistema Agroforestal | Cultivos perennes",
                             orig_att_name="SAF_23.60 ha.zip")
        assert r1["ok"]
        import json
        orig_path = os.path.join(r1["folder"], "_orig_names.json")
        assert os.path.isfile(orig_path)
        with open(orig_path, "r", encoding="utf-8") as f:
            orig_map = json.load(f)
        # At least one entry should have the new format with zip_name
        for k, v in orig_map.items():
            assert isinstance(v, dict), f"Expected dict, got {type(v)}: {v}"
            assert v.get("zip_name") == "SAF_23.60 ha.zip"
            assert "orig" in v

    def test_duplicate_zip_skips_second_copy(self, tmp_path):
        """Re-extracting the same ZIP must NOT create a second -origStem copy.

        Before the fix, running place_shapefile twice with identical content
        created both ID-abe_polygon.shp AND ID-abe-origStem_polygon.shp.
        Now the second call should be a no-op for that shapefile.
        """
        identifier = "AR-PPD-026_ACODIMAM_2025-Q1"
        zip1 = _make_shp_zip(str(tmp_path), "cs_data.zip",
                              "Conservacion_de_Suelos__Poligonos", shape_type=5)
        r1 = place_shapefile(zip1, str(tmp_path), identifier, "C2",
                             abe_value="Sistema Agroforestal | Conservación de suelo y agua")
        assert r1["ok"]

        # Second call with identical content
        zip2 = _make_shp_zip(str(tmp_path), "cs_data2.zip",
                              "Conservacion_de_Suelos__Poligonos", shape_type=5)
        r2 = place_shapefile(zip2, str(tmp_path), identifier, "C2",
                             abe_value="Sistema Agroforestal | Conservación de suelo y agua")
        assert r2["ok"]

        all_shps = [f for f in os.listdir(r2["folder"]) if f.endswith(".shp")]
        assert len(all_shps) == 1, f"Expected 1 shapefile but got {len(all_shps)}: {all_shps}"


# ---------------------------------------------------------------------------
# place_shapefile — bad ZIP
# ---------------------------------------------------------------------------

class TestPlaceShapefileZipSlip:
    def test_zip_with_traversal_rejected(self, tmp_path):
        """ZIP containing ../../../etc/passwd must be rejected."""
        zip_path = tmp_path / "evil.zip"
        with zipfile.ZipFile(str(zip_path), "w") as zf:
            zf.writestr("../../../etc/passwd", b"hacked")
        result = place_shapefile(str(zip_path), str(tmp_path), "evil_id", "C1")
        assert result["ok"] is False
        assert any("escapes" in e for e in result["errors"])


class TestPlaceShapefileBadZip:
    def test_corrupted_zip(self, tmp_path):
        bad_zip = tmp_path / "bad.zip"
        bad_zip.write_bytes(b"not a zip file")
        result = place_shapefile(str(bad_zip), str(tmp_path), "bad_id", "C1")
        assert result["ok"] is False
        assert result["errors"]
