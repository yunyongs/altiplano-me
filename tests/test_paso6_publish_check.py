"""
Tests for paso6_powerbi.check_publish_url() and get_embed_url_via_api().

check_publish_url() performs an HTTP HEAD/GET to verify that a Power BI
"Publish to Web" embed URL is publicly accessible.  All HTTP calls are mocked.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from paso6_powerbi import check_publish_url, get_embed_url_via_api, _is_allowed_pbi_url


SAMPLE_URL = "https://app.powerbi.com/view?r=eyJrIjoiABC123"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _mock_response(status_code: int) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.close = MagicMock()
    return resp


# ─────────────────────────────────────────────────────────────────────────────
# check_publish_url — return dict structure
# ─────────────────────────────────────────────────────────────────────────────

class TestCheckPublishUrlStructure:
    """Result always has status, http_code, and message keys."""

    def test_returns_dict_with_required_keys(self):
        with patch("paso6_powerbi._requests.head", return_value=_mock_response(200)):
            result = check_publish_url(SAMPLE_URL)
        assert isinstance(result, dict)
        assert "status" in result
        assert "http_code" in result
        assert "message" in result

    def test_status_values_are_valid(self):
        with patch("paso6_powerbi._requests.head", return_value=_mock_response(200)):
            result = check_publish_url(SAMPLE_URL)
        assert result["status"] in ("ok", "warning", "error")

    def test_empty_url_returns_error_without_request(self):
        with patch("paso6_powerbi._requests.head") as mock_head:
            result = check_publish_url("")
        mock_head.assert_not_called()
        assert result["status"] == "error"
        assert result["http_code"] is None

    def test_whitespace_only_url_returns_error(self):
        result = check_publish_url("   ")
        assert result["status"] == "error"
        assert result["http_code"] is None


# ─────────────────────────────────────────────────────────────────────────────
# check_publish_url — HTTP 200
# ─────────────────────────────────────────────────────────────────────────────

class TestCheckPublishUrl200:
    def test_status_ok(self):
        with patch("paso6_powerbi._requests.head", return_value=_mock_response(200)):
            result = check_publish_url(SAMPLE_URL)
        assert result["status"] == "ok"
        assert result["http_code"] == 200

    def test_message_contains_200(self):
        with patch("paso6_powerbi._requests.head", return_value=_mock_response(200)):
            result = check_publish_url(SAMPLE_URL)
        assert "200" in result["message"]


# ─────────────────────────────────────────────────────────────────────────────
# check_publish_url — HTTP 404
# ─────────────────────────────────────────────────────────────────────────────

class TestCheckPublishUrl404:
    def test_status_error(self):
        with patch("paso6_powerbi._requests.head", return_value=_mock_response(404)):
            result = check_publish_url(SAMPLE_URL)
        assert result["status"] == "error"
        assert result["http_code"] == 404

    def test_message_contains_404(self):
        with patch("paso6_powerbi._requests.head", return_value=_mock_response(404)):
            result = check_publish_url(SAMPLE_URL)
        assert "404" in result["message"]


# ─────────────────────────────────────────────────────────────────────────────
# check_publish_url — HTTP 401 / 403
# ─────────────────────────────────────────────────────────────────────────────

class TestCheckPublishUrlAuth:
    @pytest.mark.parametrize("code", [401, 403])
    def test_status_warning(self, code):
        with patch("paso6_powerbi._requests.head", return_value=_mock_response(code)):
            result = check_publish_url(SAMPLE_URL)
        assert result["status"] == "warning"
        assert result["http_code"] == code

    @pytest.mark.parametrize("code", [401, 403])
    def test_message_contains_code(self, code):
        with patch("paso6_powerbi._requests.head", return_value=_mock_response(code)):
            result = check_publish_url(SAMPLE_URL)
        assert str(code) in result["message"]


# ─────────────────────────────────────────────────────────────────────────────
# check_publish_url — ConnectionError
# ─────────────────────────────────────────────────────────────────────────────

class TestCheckPublishUrlConnectionError:
    def test_connection_error_returns_error_status(self):
        import requests as req_lib
        with patch(
            "paso6_powerbi._requests.head",
            side_effect=req_lib.exceptions.ConnectionError("unreachable"),
        ):
            result = check_publish_url(SAMPLE_URL)
        assert result["status"] == "error"
        assert result["http_code"] is None

    def test_timeout_returns_error_status(self):
        import requests as req_lib
        with patch(
            "paso6_powerbi._requests.head",
            side_effect=req_lib.exceptions.Timeout("timed out"),
        ):
            result = check_publish_url(SAMPLE_URL)
        assert result["status"] == "error"
        assert result["http_code"] is None


# ─────────────────────────────────────────────────────────────────────────────
# check_publish_url — HEAD 405 fallback to GET
# ─────────────────────────────────────────────────────────────────────────────

class TestCheckPublishUrlHeadFallback:
    def test_405_falls_back_to_get(self):
        head_resp = _mock_response(405)
        get_resp = _mock_response(200)
        with (
            patch("paso6_powerbi._requests.head", return_value=head_resp),
            patch("paso6_powerbi._requests.get", return_value=get_resp),
        ):
            result = check_publish_url(SAMPLE_URL)
        assert result["status"] == "ok"
        assert result["http_code"] == 200


# ─────────────────────────────────────────────────────────────────────────────
# get_embed_url_via_api — always raises NotImplementedError
# ─────────────────────────────────────────────────────────────────────────────

class TestGetEmbedUrlViaApi:
    def test_raises_not_implemented(self):
        with pytest.raises(NotImplementedError):
            get_embed_url_via_api(report_id="abc123")

    def test_raises_with_group_id(self):
        with pytest.raises(NotImplementedError):
            get_embed_url_via_api(report_id="abc123", group_id="grp456")

    def test_error_message_mentions_azure(self):
        with pytest.raises(NotImplementedError, match="Azure AD"):
            get_embed_url_via_api(report_id="abc123")


# ─────────────────────────────────────────────────────────────────────────────
# _is_allowed_pbi_url — SSRF mitigation
# ─────────────────────────────────────────────────────────────────────────────

class TestIsAllowedPbiUrl:
    @pytest.mark.parametrize("url", [
        "https://app.powerbi.com/view?r=eyJr",
        "https://app.powerbigov.us/view?r=abc",
        "https://app.powerbi.de/view?r=xyz",
        "https://app.powerbi.cn/view?r=123",
        "https://wabi-us-east2.powerbi.com/embed",
        "https://something.pbidedicated.windows.net/embed",
    ])
    def test_allowed_urls(self, url):
        assert _is_allowed_pbi_url(url) is True

    @pytest.mark.parametrize("url", [
        "http://app.powerbi.com/view?r=abc",   # HTTP not HTTPS
        "https://localhost/view",
        "https://127.0.0.1/view",
        "https://evil.com/view",
        "https://app.powerbi.com.evil.com/view",
        "ftp://app.powerbi.com/view",
        "",
    ])
    def test_rejected_urls(self, url):
        assert _is_allowed_pbi_url(url) is False


# ─────────────────────────────────────────────────────────────────────────────
# check_publish_url — SSRF rejection via check_publish_url
# ─────────────────────────────────────────────────────────────────────────────

class TestCheckPublishUrlSSRF:
    def test_localhost_rejected(self):
        result = check_publish_url("http://localhost:8080/admin")
        assert result["status"] == "error"
        assert "Power BI domain" in result["message"]

    def test_internal_ip_rejected(self):
        result = check_publish_url("https://192.168.1.1/secret")
        assert result["status"] == "error"

    def test_valid_pbi_url_not_blocked(self):
        with patch("paso6_powerbi._requests.head", return_value=_mock_response(200)):
            result = check_publish_url(SAMPLE_URL)
        assert result["status"] == "ok"
