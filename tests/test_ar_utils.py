"""Tests for ar_utils.py — extracted pure functions from Jupyter notebooks."""
import os
import zipfile

import pytest

from ar_utils import (
    abe,
    abe_eng,
    cada_punto,
    extract_abe_hint_from_filename,
    extract_and_validate_zip,
    extract_hectares_from_filename,
    find_shapefiles,
    grants,
    id_area,
    is_c1_row_shape_zip,
    is_shape_zip_attachment,
    normalize,
    safe_resolve,
    sanitize_shapefile_basename,
    trata,
    validate_abe,
)


# ---------------------------------------------------------------------------
# trata — microcuenca classification
# ---------------------------------------------------------------------------

class TestTrata:
    @pytest.mark.parametrize("name", [
        "Balanyá", "Xequijel", "Paxocol", "Mactzul",
    ])
    def test_tratamiento_names(self, name):
        assert trata(name) == "TRATAMIENTO"

    @pytest.mark.parametrize("name", [
        "Arriquib 196", "Sepelá 154", "Samalá 166",
    ])
    def test_control_names(self, name):
        assert trata(name) == "CONTROL"

    def test_unknown_name(self):
        assert trata("Unknown") == ""

    def test_empty_string(self):
        assert trata("") == ""


# ---------------------------------------------------------------------------
# id_area
# ---------------------------------------------------------------------------

class TestIdArea:
    def test_influence(self):
        assert id_area("Influence") == 3

    def test_intervention(self):
        assert id_area("Intervention") == 2

    def test_prioritized(self):
        assert id_area("Prioritized") == 1

    def test_unknown(self):
        assert id_area("Other") == 0

    def test_empty(self):
        assert id_area("") == 0


# ---------------------------------------------------------------------------
# abe_eng — Spanish to English AbE translation
# ---------------------------------------------------------------------------

class TestAbeEng:
    @pytest.mark.parametrize("spanish,english", [
        ("Sistema Agroforestal | Cultivos anuales", "1. AFS w annual Crops"),
        ("Sistema Agroforestal | Cultivos perennes", "1. AFS w perennial Crops"),
        ("Sistema Silvopastoril", "Silvopastoril system"),
        ("Plantaciones Forestales", "2. Forest plantation"),
        ("Bosque Natural con Fines de Producción", "2. Natural forest production"),
        ("Bosque Natural con Fines de Protección", "3. Natural forest protection"),
        ("Reforestación con Fines de Restauración", "3. Natural forest restoration"),
    ])
    def test_known_translations(self, spanish, english):
        assert abe_eng(spanish) == english

    def test_unknown_returns_empty(self):
        assert abe_eng("Unknown") == ""


# ---------------------------------------------------------------------------
# abe — AbE abbreviation
# ---------------------------------------------------------------------------

class TestAbe:
    @pytest.mark.parametrize("spanish,code", [
        ("Sistema Agroforestal | Cultivos anuales", "anual"),
        ("Sistema Agroforestal | Cultivos perennes", "peren"),
        ("Sistema Silvopastoril", "silvo"),
        ("Plantaciones Forestales", "plant"),
        ("Bosque Natural con Fines de Producción", "produ"),
        ("Bosque Natural con Fines de Protección", "prote"),
        ("Reforestación con Fines de Restauración", "refor"),
    ])
    def test_known_abbreviations(self, spanish, code):
        assert abe(spanish) == code

    @pytest.mark.parametrize("spanish,code", [
        # Conservación de suelo y agua variants / variantes
        ("Sistema Agroforestal | Conservación de suelo y agua", "sueloyagua"),
        ("Conservación de suelo y agua | Sistema Agroforestal", "sueloyagua"),
    ])
    def test_suelo_y_agua_category(self, spanish, code):
        assert abe(spanish) == code

    @pytest.mark.parametrize("variant,code", [
        # Lowercase variant / Variante en minúsculas
        ("Bosque natural con fines de protección", "prote"),
        ("bosque natural con fines de producción", "produ"),
        ("sistema agroforestal | cultivos anuales", "anual"),
        # Missing accent / Sin acento
        ("Reforestacion con Fines de Restauracion", "refor"),
        ("Sistema Agroforestal | Conservacion de suelo y agua", "sueloyagua"),
        # Short/common variant / Variante corta
        ("Forestal", "plant"),
        ("Silvopastoril", "silvo"),
    ])
    def test_variant_matching(self, variant, code):
        assert abe(variant) == code

    @pytest.mark.parametrize("invalid_value", [
        # Human errors — should return "error" / Errores humanos
        "Prácticas AbE",
        "Información climática",
        "Género e inclusión social",
        "Otro",
    ])
    def test_invalid_abe_returns_error(self, invalid_value):
        assert abe(invalid_value) == "error"

    def test_unknown_returns_error(self):
        assert abe("Unknown") == "error"

    def test_none_returns_error(self):
        assert abe(None) == "error"

    def test_empty_returns_error(self):
        assert abe("") == "error"


# ---------------------------------------------------------------------------
# validate_abe
# ---------------------------------------------------------------------------

class TestValidateAbe:
    def test_valid_value(self):
        r = validate_abe("Plantaciones Forestales")
        assert r["valid"] is True
        assert r["abbr"] == "plant"
        assert r["message"] is None

    def test_valid_variant(self):
        r = validate_abe("bosque natural con fines de protección")
        assert r["valid"] is True
        assert r["abbr"] == "prote"

    def test_invalid_human_error(self):
        r = validate_abe("Prácticas AbE")
        assert r["valid"] is False
        assert r["abbr"] is None
        assert "Smartsheet" in r["message"]
        assert "Prácticas AbE" in r["message"]

    def test_empty_value(self):
        r = validate_abe("")
        assert r["valid"] is False
        assert "vacío" in r["message"]

    def test_none_value(self):
        r = validate_abe(None)
        assert r["valid"] is False


# ---------------------------------------------------------------------------
# grants
# ---------------------------------------------------------------------------

class TestGrants:
    def test_ppd(self):
        assert grants("XX-PPD-YY") == "Small Grants"

    def test_pmd(self):
        assert grants("XX-PMD-YY") == "Medium Grants"

    def test_none_returns_empty(self):
        assert grants(None) == ""

    def test_unknown_grant_type(self):
        assert grants("XX-ABC-YY") == ""

    def test_no_dash(self):
        assert grants("NODASH") == ""


# ---------------------------------------------------------------------------
# cada_punto
# ---------------------------------------------------------------------------

class TestCadaPunto:
    def test_normal_division(self):
        assert cada_punto(100, 5) == 20.0

    def test_none_parcelas(self):
        assert cada_punto(100, None) is None

    def test_zero_parcelas_raises(self):
        with pytest.raises(ZeroDivisionError):
            cada_punto(100, 0)

    def test_float_inputs(self):
        assert cada_punto(10.0, 4.0) == 2.5


# ---------------------------------------------------------------------------
# normalize
# ---------------------------------------------------------------------------

class TestNormalize:
    def test_removes_accents(self):
        assert normalize("Balanyá") == "balanya"

    def test_lowercases(self):
        assert normalize("HELLO") == "hello"

    def test_none_returns_empty(self):
        assert normalize(None) == ""

    def test_empty_string(self):
        assert normalize("") == ""

    def test_already_ascii(self):
        assert normalize("hello") == "hello"

    def test_mixed_accents(self):
        assert normalize("Sépalá") == "sepala"


# ---------------------------------------------------------------------------
# sanitize_shapefile_basename
# ---------------------------------------------------------------------------

class TestSanitizeShapefileBasename:
    def test_replaces_dots(self):
        assert sanitize_shapefile_basename("file.name") == "file_name"

    def test_replaces_special_chars(self):
        assert sanitize_shapefile_basename("file@name!") == "file_name_"

    def test_preserves_dashes(self):
        assert sanitize_shapefile_basename("file-name") == "file-name"

    def test_preserves_underscores(self):
        assert sanitize_shapefile_basename("file_name") == "file_name"

    def test_clean_name_unchanged(self):
        assert sanitize_shapefile_basename("cleanname") == "cleanname"

    def test_multiple_dots(self):
        assert sanitize_shapefile_basename("a.b.c") == "a_b_c"


# ---------------------------------------------------------------------------
# is_shape_zip_attachment
# ---------------------------------------------------------------------------

class TestIsShapeZipAttachment:
    def test_shape_zip(self):
        assert is_shape_zip_attachment("shapefile.zip") is True

    def test_shp_zip(self):
        assert is_shape_zip_attachment("data_shp.zip") is True

    def test_case_insensitive(self):
        assert is_shape_zip_attachment("SHAPE_data.ZIP") is True

    def test_non_zip(self):
        assert is_shape_zip_attachment("shapefile.rar") is False

    def test_zip_without_shape(self):
        assert is_shape_zip_attachment("data.zip") is False

    def test_empty_name(self):
        assert is_shape_zip_attachment("") is False

    def test_none(self):
        assert is_shape_zip_attachment(None) is False

    def test_abe_ha_saf(self):
        """SAF + ha pattern should be detected as shapefile ZIP."""
        assert is_shape_zip_attachment("SAF_23.60 ha.zip") is True

    def test_abe_ha_proteccion(self):
        """BNProteccion + ha pattern should be detected as shapefile ZIP."""
        assert is_shape_zip_attachment("BNProteccion 5.17 ha.zip") is True

    def test_abe_ha_plant(self):
        assert is_shape_zip_attachment("Shape_Plantacion 21.49 ha.zip") is True

    def test_ha_only_no_abe(self):
        """ha keyword alone without AbE abbreviation should NOT match."""
        assert is_shape_zip_attachment("random 3.5 ha.zip") is False

    def test_abe_no_ha(self):
        """AbE keyword alone (without ha) SHOULD match — it's a shape file."""
        assert is_shape_zip_attachment("SAF_data.zip") is True
        assert is_shape_zip_attachment("SAF_perennes_y_anuales.zip") is True
        assert is_shape_zip_attachment("SAF_Cultivos perennes.zip") is True

    def test_anexo_with_abe_keyword(self):
        """Anexo files with AbE keywords should be treated as shape files."""
        assert is_shape_zip_attachment("Anexo SAF 5.0 ha.zip") is True
        assert is_shape_zip_attachment("anexo_saf_poligonos.zip") is True

    def test_anexo_plain_excluded(self):
        """Plain anexo/annexo without AbE keywords should be excluded."""
        assert is_shape_zip_attachment("Anexos.zip") is False
        assert is_shape_zip_attachment("Annexo_report.zip") is False


# ---------------------------------------------------------------------------
# is_c1_row_shape_zip — row-aware detection for C1
# ---------------------------------------------------------------------------

class TestIsC1RowShapeZip:
    def test_filename_keyword_wins(self):
        """Filename keyword evidence alone is enough — context is ignored."""
        assert is_c1_row_shape_zip("shapefile.zip", 5, False, False) is True

    def test_non_zip_extension(self):
        assert is_c1_row_shape_zip("data.rar", 1, True, True) is False
        assert is_c1_row_shape_zip("notes.pdf", 1, True, True) is False

    def test_generic_zip_unique_with_context(self):
        """Generic ZIP name → shapefile when it is the only ZIP and the row
        has both hectares and AbE."""
        assert is_c1_row_shape_zip("data.zip", 1, True, True) is True

    def test_generic_zip_multiple_attachments(self):
        """Generic ZIP must NOT be assumed when the row has other ZIPs."""
        assert is_c1_row_shape_zip("data.zip", 2, True, True) is False

    def test_generic_zip_missing_hectares(self):
        assert is_c1_row_shape_zip("data.zip", 1, False, True) is False

    def test_generic_zip_missing_abe(self):
        assert is_c1_row_shape_zip("data.zip", 1, True, False) is False

    def test_empty_name(self):
        assert is_c1_row_shape_zip("", 1, True, True) is False

    def test_none_name(self):
        assert is_c1_row_shape_zip(None, 1, True, True) is False


# ---------------------------------------------------------------------------
# extract_hectares_from_filename — hectare value extraction from ZIP filenames
# ---------------------------------------------------------------------------

class TestExtractHectaresFromFilename:
    """Test hectare value extraction from original attachment filenames."""

    def test_saf_decimal(self):
        assert extract_hectares_from_filename("SAF_23.60 ha.zip") == 23.6

    def test_proteccion(self):
        assert extract_hectares_from_filename("BNProteccion 5.17 ha.zip") == 5.17

    def test_plantacion(self):
        assert extract_hectares_from_filename("Shape_plantacion 21.49 ha.zip") == 21.49

    def test_comma_decimal(self):
        assert extract_hectares_from_filename("SAF_9,57 ha.zip") == 9.57

    def test_no_ha(self):
        assert extract_hectares_from_filename("random_file.zip") is None

    def test_not_zip(self):
        assert extract_hectares_from_filename("SAF_23.60 ha.docx") is None

    def test_none(self):
        assert extract_hectares_from_filename(None) is None

    def test_empty(self):
        assert extract_hectares_from_filename("") is None

    def test_no_number(self):
        assert extract_hectares_from_filename("SAF_ha.zip") is None


# ---------------------------------------------------------------------------
# extract_abe_hint_from_filename — ABE hint detection from original SHP names
# ---------------------------------------------------------------------------

class TestExtractAbeHintFromFilename:
    """Test ABE abbreviation extraction from original attachment filenames."""

    def test_cs_conservacion_suelo(self):
        assert extract_abe_hint_from_filename("SHP_Q4_CS_AYUDAGT.zip") == "sueloyagua"

    def test_anual_cultivos(self):
        assert extract_abe_hint_from_filename("SHP_Q4_SAF.ANUALAYUDAGT.zip") == "anual"

    def test_peren(self):
        assert extract_abe_hint_from_filename("SHP_Q4_PERENGT.zip") == "peren"

    def test_silvo(self):
        assert extract_abe_hint_from_filename("SHP_SILVO_data.zip") == "silvo"

    def test_plant_forestal(self):
        assert extract_abe_hint_from_filename("SHP_FORESTAL_Q1.zip") == "plant"

    def test_refor(self):
        assert extract_abe_hint_from_filename("shp_REFOR_ONG.zip") == "refor"

    def test_no_hint(self):
        assert extract_abe_hint_from_filename("random_file.zip") == ""

    def test_empty_string(self):
        assert extract_abe_hint_from_filename("") == ""

    def test_none(self):
        assert extract_abe_hint_from_filename(None) == ""

    def test_case_insensitive(self):
        assert extract_abe_hint_from_filename("shp_q4_cs_ayudagt.zip") == "sueloyagua"

    def test_dots_stripped(self):
        """Dots in filename like SAF.ANUAL should not prevent matching."""
        assert extract_abe_hint_from_filename("SAF.ANUAL.shp.zip") == "anual"

    def test_no_zip_extension(self):
        """Function strips extension; non-.zip names should still work."""
        assert extract_abe_hint_from_filename("SHP_CS_data.rar") == "sueloyagua"

    def test_saf_generic_without_subtype(self):
        """SAF without a subtype keyword returns generic 'saf' hint."""
        assert extract_abe_hint_from_filename("SAF_23.60 ha.zip") == "saf"

    def test_bnp_proteccion(self):
        """BNProteccion returns 'prote' hint."""
        assert extract_abe_hint_from_filename("BNProteccion 5.17 ha.zip") == "prote"

    def test_saf_generic_small(self):
        """SAF with small ha value returns 'saf'."""
        assert extract_abe_hint_from_filename("SAF_6.57 ha.zip") == "saf"


# ---------------------------------------------------------------------------
# find_shapefiles
# ---------------------------------------------------------------------------

class TestFindShapefiles:
    def test_finds_shp_files(self, tmp_path):
        (tmp_path / "a.shp").touch()
        (tmp_path / "b.shp").touch()
        (tmp_path / "c.txt").touch()
        result = find_shapefiles(str(tmp_path))
        basenames = sorted(os.path.basename(p) for p in result)
        assert basenames == ["a.shp", "b.shp"]

    def test_empty_folder(self, tmp_path):
        assert find_shapefiles(str(tmp_path)) == []

    def test_nested_folders(self, tmp_path):
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "nested.shp").touch()
        result = find_shapefiles(str(tmp_path))
        assert len(result) == 1
        assert result[0].endswith("nested.shp")

    def test_case_insensitive_extension(self, tmp_path):
        (tmp_path / "upper.SHP").touch()
        result = find_shapefiles(str(tmp_path))
        assert len(result) == 1


# ---------------------------------------------------------------------------
# safe_resolve — path traversal protection
# ---------------------------------------------------------------------------

class TestSafeResolve:
    def test_valid_path_under_root(self, tmp_path):
        sub = tmp_path / "data"
        sub.mkdir()
        result = safe_resolve(str(sub), [str(tmp_path)])
        assert result == sub.resolve()

    def test_root_itself_is_allowed(self, tmp_path):
        result = safe_resolve(str(tmp_path), [str(tmp_path)])
        assert result == tmp_path.resolve()

    def test_path_outside_roots_raises(self, tmp_path):
        allowed = tmp_path / "allowed"
        allowed.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()
        with pytest.raises(ValueError, match="outside allowed"):
            safe_resolve(str(outside), [str(allowed)])

    def test_dotdot_traversal_raises(self, tmp_path):
        allowed = tmp_path / "allowed"
        allowed.mkdir()
        sneaky = str(allowed) + "/../outside"
        with pytest.raises(ValueError, match="outside allowed"):
            safe_resolve(sneaky, [str(allowed)])

    def test_empty_path_raises(self):
        with pytest.raises(ValueError, match="Empty path"):
            safe_resolve("", ["/tmp"])

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError, match="Empty path"):
            safe_resolve("   ", ["/tmp"])

    def test_multiple_roots(self, tmp_path):
        root_a = tmp_path / "a"
        root_b = tmp_path / "b"
        root_a.mkdir()
        root_b.mkdir()
        target = root_b / "file.txt"
        target.touch()
        result = safe_resolve(str(target), [str(root_a), str(root_b)])
        assert result == target.resolve()


# ---------------------------------------------------------------------------
# extract_and_validate_zip — ZIP-slip protection
# ---------------------------------------------------------------------------

class TestExtractAndValidateZipSlip:
    def test_normal_zip_extracts_ok(self, tmp_path):
        zip_path = tmp_path / "good.zip"
        dest = tmp_path / "out"
        dest.mkdir()
        with zipfile.ZipFile(str(zip_path), "w") as zf:
            zf.writestr("layer.shp", b"")
            zf.writestr("layer.shx", b"")
            zf.writestr("layer.dbf", b"")
            zf.writestr("layer.prj", b"")
        result = extract_and_validate_zip(str(zip_path), str(dest))
        assert result["ok"] is True

    def test_zip_with_traversal_rejected(self, tmp_path):
        zip_path = tmp_path / "evil.zip"
        dest = tmp_path / "out"
        dest.mkdir()
        with zipfile.ZipFile(str(zip_path), "w") as zf:
            zf.writestr("../../../etc/passwd", b"hacked")
        result = extract_and_validate_zip(str(zip_path), str(dest))
        assert result["ok"] is False
        assert any("escapes" in e for e in result["errors"])


# ---------------------------------------------------------------------------
# stream_download_to_file — streaming download helper
# ---------------------------------------------------------------------------

class TestStreamDownloadToFile:
    def test_writes_chunks_to_disk(self, tmp_path, monkeypatch):
        """stream_download_to_file writes chunks to disk."""
        from ar_utils import stream_download_to_file
        import requests

        class FakeResponse:
            status_code = 200
            def raise_for_status(self): pass
            def iter_content(self, chunk_size=8192):
                yield b"chunk1"
                yield b"chunk2"

        monkeypatch.setattr(requests, "get", lambda *a, **kw: FakeResponse())
        dest = tmp_path / "out.zip"
        assert stream_download_to_file("http://example.com/f.zip", str(dest))
        assert dest.read_bytes() == b"chunk1chunk2"

    def test_raises_on_http_error(self, tmp_path, monkeypatch):
        """stream_download_to_file raises HTTPError on non-2xx status."""
        from ar_utils import stream_download_to_file
        import requests

        class FakeResponse:
            status_code = 404
            def raise_for_status(self):
                raise requests.HTTPError(response=self)
            def iter_content(self, chunk_size=8192):
                return iter([])

        monkeypatch.setattr(requests, "get", lambda *a, **kw: FakeResponse())
        dest = tmp_path / "out.zip"
        with pytest.raises(requests.HTTPError):
            stream_download_to_file("http://example.com/missing.zip", str(dest))
