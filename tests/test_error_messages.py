"""Tests for S3 friendly error catalog and friendly_error() helper."""
import pytest


def test_friendly_error_basic():
    from app import friendly_error
    err = friendly_error("ss_401")
    assert err["title"] == "Token de Smartsheet inválido"
    assert err["severity"] == "error"
    assert err["error_code"] == "ss_401"
    assert err["message"]
    assert err["action"]


def test_friendly_error_with_path_param():
    from app import friendly_error
    err = friendly_error("folder_not_found", path="C:\\AR\\Data")
    assert "C:\\AR\\Data" in err["message"]
    assert err["severity"] == "error"



def test_friendly_error_with_name_param():
    from app import friendly_error
    err = friendly_error("zip_invalid", name="actividad_001.zip")
    assert "actividad_001.zip" in err["message"]


def test_friendly_error_unknown_code_fallback():
    from app import friendly_error
    err = friendly_error("nonexistent_code")
    assert err["title"] == "Error inesperado"
    assert err["error_code"] == "nonexistent_code"


def test_friendly_error_all_codes_have_required_fields():
    """All catalog codes must have required fields; skip codes with required params."""
    from app import ERROR_MESSAGES
    import string
    for code, tmpl in ERROR_MESSAGES.items():
        for field in ("title", "message", "action", "severity"):
            assert field in tmpl, f"{code} missing {field}"
        assert tmpl["severity"] in ("error", "warn"), f"{code} bad severity"
        # Verify no unexpected format fields by checking structure only
        for field in ("title", "message", "action"):
            assert isinstance(tmpl[field], str), f"{code}.{field} must be str"


def test_friendly_error_severity_values():
    from app import friendly_error
    assert friendly_error("ss_429")["severity"] == "warn"
    assert friendly_error("ss_401")["severity"] == "error"
    assert friendly_error("no_folder")["severity"] == "warn"
    assert friendly_error("gdb_not_found")["severity"] == "error"


@pytest.mark.parametrize("code", [
    "ss_401", "ss_403", "ss_404", "ss_429", "ss_network",
    "no_token", "no_sheet_id", "no_folder",
"gdb_not_found", "agol_auth", "powerbi_no_license",
    "arcpy_not_configured", "arcpy_timeout",
    "network_error", "unknown",
])
def test_friendly_error_no_params_codes(code):
    from app import friendly_error
    err = friendly_error(code)
    assert err["title"]
    assert err["message"]
