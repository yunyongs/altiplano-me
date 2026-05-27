"""Tests for agol_connect.py — AGOL OAuth 2.0 PKCE connection module.

All tests mock the ``arcgis`` package so no real AGOL connection is needed.
"""
import os
import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

import agol_connect as ac


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_gis(username="test_user", org_name="TestOrg"):
    """Return a mock GIS instance with .properties.user.username / .name."""
    gis = MagicMock(name="MockGIS")
    gis.properties = SimpleNamespace(
        user=SimpleNamespace(username=username),
        name=org_name,
    )
    return gis


def _make_mock_feature(attrs: dict):
    """Return a mock feature with .attributes."""
    f = SimpleNamespace(attributes=attrs)
    return f


def _make_mock_item(title="Test Layer", item_id="abc123", layer_urls=None):
    """Return a mock Item with .layers list."""
    item = MagicMock(name="MockItem")
    item.title = title
    item.id = item_id
    if layer_urls is None:
        layer_urls = ["https://services.arcgis.com/abc/FeatureServer/0"]
    layers = []
    for url in layer_urls:
        fl = MagicMock(name=f"MockFL-{url}")
        fl.url = url
        layers.append(fl)
    item.layers = layers
    return item


def _simulate_oauth_session(username="test_user", org_name="TestOrg"):
    """Simulate a complete OAuth session by setting module-level state."""
    mock_gis = _make_mock_gis(username, org_name)
    ac._gis_instance = mock_gis
    ac._gis_created_at = time.time()
    ac._access_token = "fake_token"
    ac._token_expires_at = time.time() + 7200
    return mock_gis


@pytest.fixture(autouse=True)
def _clean_state():
    """Reset all module-level state before each test."""
    ac.clear_caches()
    yield
    ac.clear_caches()


# ---------------------------------------------------------------------------
# _import_arcgis
# ---------------------------------------------------------------------------

class TestImportArcgis:
    def test_returns_gis_and_featurelayer(self):
        mock_GIS = MagicMock(name="GIS")
        mock_FL = MagicMock(name="FeatureLayer")
        with patch.dict("sys.modules", {
            "arcgis": MagicMock(),
            "arcgis.gis": MagicMock(GIS=mock_GIS),
            "arcgis.features": MagicMock(FeatureLayer=mock_FL),
        }):
            GIS, FL = ac._import_arcgis()
            assert GIS is mock_GIS
            assert FL is mock_FL

    def test_raises_import_error_when_arcgis_missing(self):
        with patch.dict("sys.modules", {"arcgis": None, "arcgis.gis": None}):
            with pytest.raises(ImportError, match="arcgis package is required"):
                ac._import_arcgis()


# ---------------------------------------------------------------------------
# PKCE helpers
# ---------------------------------------------------------------------------

class TestPKCE:
    def test_generate_pkce_returns_verifier_and_challenge(self):
        verifier, challenge = ac._generate_pkce()
        assert len(verifier) >= 43
        assert len(verifier) <= 128
        assert len(challenge) > 0
        # challenge must be base64url (no + / =)
        assert "+" not in challenge
        assert "/" not in challenge
        assert "=" not in challenge

    def test_generate_pkce_unique(self):
        v1, _ = ac._generate_pkce()
        v2, _ = ac._generate_pkce()
        assert v1 != v2

    def test_challenge_is_sha256_of_verifier(self):
        import base64
        import hashlib
        verifier, challenge = ac._generate_pkce()
        expected = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode("ascii")).digest()
        ).rstrip(b"=").decode("ascii")
        assert challenge == expected


# ---------------------------------------------------------------------------
# build_authorize_url
# ---------------------------------------------------------------------------

class TestBuildAuthorizeUrl:
    ENV = {
        "ARCGIS_ORG_URL": "https://test.maps.arcgis.com",
        "ARCGIS_CLIENT_ID": "test_client_id",
    }

    def test_builds_url_with_expected_params(self):
        with patch.dict(os.environ, self.ENV, clear=False):
            result = ac.build_authorize_url("http://localhost:5000/oauth/callback")
            assert "url" in result
            assert "state" in result
            url = result["url"]
            assert "test.maps.arcgis.com/sharing/rest/oauth2/authorize" in url
            assert "client_id=test_client_id" in url
            assert "response_type=code" in url
            assert "code_challenge=" in url
            assert "code_challenge_method=S256" in url
            assert "redirect_uri=" in url

    def test_stores_state_in_oauth_state(self):
        with patch.dict(os.environ, self.ENV, clear=False):
            result = ac.build_authorize_url("http://localhost:5000/oauth/callback")
            state = result["state"]
            assert state in ac._oauth_state
            assert "code_verifier" in ac._oauth_state[state]
            assert "org_url" in ac._oauth_state[state]
            assert "client_id" in ac._oauth_state[state]

    def test_raises_without_org_url(self):
        env = {"ARCGIS_ORG_URL": "", "ARCGIS_CLIENT_ID": "x"}
        with patch.dict(os.environ, env, clear=False):
            with pytest.raises(ValueError, match="ARCGIS_ORG_URL"):
                ac.build_authorize_url("http://localhost:5000/oauth/callback")

    def test_raises_without_client_id(self):
        env = {"ARCGIS_ORG_URL": "https://x.com", "ARCGIS_CLIENT_ID": ""}
        with patch.dict(os.environ, env, clear=False):
            with pytest.raises(ValueError, match="ARCGIS_CLIENT_ID"):
                ac.build_authorize_url("http://localhost:5000/oauth/callback")

    def test_strips_trailing_slash_from_org_url(self):
        env = {"ARCGIS_ORG_URL": "https://test.maps.arcgis.com/", "ARCGIS_CLIENT_ID": "x"}
        with patch.dict(os.environ, env, clear=False):
            result = ac.build_authorize_url("http://localhost:5000/oauth/callback")
            assert "test.maps.arcgis.com//sharing" not in result["url"]
            assert "test.maps.arcgis.com/sharing" in result["url"]

    def test_explicit_params_override_env(self):
        result = ac.build_authorize_url(
            "http://localhost:5000/oauth/callback",
            org_url="https://custom.maps.arcgis.com",
            client_id="custom_client",
        )
        assert "custom.maps.arcgis.com" in result["url"]
        assert "custom_client" in result["url"]


# ---------------------------------------------------------------------------
# exchange_code
# ---------------------------------------------------------------------------

class TestExchangeCode:
    def test_exchanges_code_for_token(self):
        # Seed state
        ac._oauth_state["test_state"] = {
            "code_verifier": "verifier123",
            "org_url": "https://test.maps.arcgis.com",
            "client_id": "cid",
        }

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "access_token": "at_123",
            "refresh_token": "rt_456",
            "expires_in": 7200,
        }
        mock_resp.raise_for_status = MagicMock()

        mock_gis = _make_mock_gis()
        mock_cls = MagicMock(return_value=mock_gis)

        with (
            patch("agol_connect._requests.post", return_value=mock_resp) as mock_post,
            patch.object(ac, "_import_arcgis", return_value=(mock_cls, MagicMock())),
        ):
            info = ac.exchange_code("auth_code", "test_state", "http://localhost:5000/oauth/callback")

            # Verify token endpoint was called
            mock_post.assert_called_once()
            call_data = mock_post.call_args[1]["data"]
            assert call_data["grant_type"] == "authorization_code"
            assert call_data["code"] == "auth_code"
            assert call_data["code_verifier"] == "verifier123"
            assert call_data["client_id"] == "cid"

            # Verify GIS was created with token
            mock_cls.assert_called_once_with("https://test.maps.arcgis.com", token="at_123")

            assert info["connected"] is True
            assert info["expires_in"] == 7200

    def test_invalid_state_raises(self):
        with pytest.raises(ValueError, match="Invalid or expired"):
            ac.exchange_code("code", "bad_state", "http://localhost")

    def test_agol_error_response_raises(self):
        ac._oauth_state["s"] = {
            "code_verifier": "v",
            "org_url": "https://x.com",
            "client_id": "c",
        }
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "error": {"message": "Invalid code"},
        }
        mock_resp.raise_for_status = MagicMock()

        with patch("agol_connect._requests.post", return_value=mock_resp):
            with pytest.raises(RuntimeError, match="AGOL token error"):
                ac.exchange_code("bad_code", "s", "http://localhost")

    def test_state_consumed_after_exchange(self):
        ac._oauth_state["s"] = {
            "code_verifier": "v",
            "org_url": "https://x.com",
            "client_id": "c",
        }

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"access_token": "t", "expires_in": 100}
        mock_resp.raise_for_status = MagicMock()

        mock_gis = _make_mock_gis()
        mock_cls = MagicMock(return_value=mock_gis)

        with (
            patch("agol_connect._requests.post", return_value=mock_resp),
            patch.object(ac, "_import_arcgis", return_value=(mock_cls, MagicMock())),
        ):
            ac.exchange_code("code", "s", "http://localhost")
            assert "s" not in ac._oauth_state


# ---------------------------------------------------------------------------
# get_gis
# ---------------------------------------------------------------------------

class TestGetGis:
    def test_raises_when_not_authenticated(self):
        with pytest.raises(ValueError, match="not established"):
            ac.get_gis()

    def test_returns_gis_after_oauth(self):
        mock_gis = _simulate_oauth_session()
        gis = ac.get_gis()
        assert gis is mock_gis

    def test_returns_singleton(self):
        _simulate_oauth_session()
        gis1 = ac.get_gis()
        gis2 = ac.get_gis()
        assert gis1 is gis2

    def test_recreates_after_max_age_with_valid_token(self):
        _simulate_oauth_session()
        ac._gis_created_at = time.time() - ac._GIS_MAX_AGE - 1

        mock_gis = _make_mock_gis()
        mock_cls = MagicMock(return_value=mock_gis)
        with patch.object(ac, "_import_arcgis", return_value=(mock_cls, MagicMock())):
            gis = ac.get_gis()
            assert gis is mock_gis

    def test_raises_when_token_expired(self):
        _simulate_oauth_session()
        ac._gis_created_at = time.time() - ac._GIS_MAX_AGE - 1
        ac._token_expires_at = time.time() - 1  # token expired

        with pytest.raises(ValueError, match="expired"):
            ac.get_gis()


# ---------------------------------------------------------------------------
# resolve_layer
# ---------------------------------------------------------------------------

class TestResolveLayer:
    @pytest.fixture(autouse=True)
    def _mock_import(self):
        """Patch _import_arcgis so resolve_layer doesn't need real arcgis."""
        self._mock_FL_cls = MagicMock(name="FeatureLayerCls")
        with patch.object(ac, "_import_arcgis",
                          return_value=(MagicMock(), self._mock_FL_cls)):
            yield

    def test_resolves_item_to_feature_layer(self):
        mock_gis = _make_mock_gis()
        mock_item = _make_mock_item()
        mock_gis.content.get.return_value = mock_item

        fl, url = ac.resolve_layer("abc123", gis=mock_gis)

        mock_gis.content.get.assert_called_once_with("abc123")
        assert url == "https://services.arcgis.com/abc/FeatureServer/0"
        assert fl is mock_item.layers[0]

    def test_raises_when_item_not_found(self):
        mock_gis = _make_mock_gis()
        mock_gis.content.get.return_value = None

        with pytest.raises(LookupError, match="not found"):
            ac.resolve_layer("bad_id", gis=mock_gis)

    def test_raises_when_no_layers(self):
        mock_gis = _make_mock_gis()
        mock_item = _make_mock_item(layer_urls=[])
        mock_item.layers = []
        mock_gis.content.get.return_value = mock_item

        with pytest.raises(LookupError, match="no feature layers"):
            ac.resolve_layer("abc123", gis=mock_gis)

    def test_raises_when_layer_index_out_of_range(self):
        mock_gis = _make_mock_gis()
        mock_item = _make_mock_item()  # 1 layer
        mock_gis.content.get.return_value = mock_item

        with pytest.raises(IndexError, match="out of range"):
            ac.resolve_layer("abc123", layer_index=5, gis=mock_gis)

    def test_caches_result(self):
        mock_gis = _make_mock_gis()
        mock_item = _make_mock_item()
        mock_gis.content.get.return_value = mock_item

        ac.resolve_layer("abc123", gis=mock_gis)
        ac.resolve_layer("abc123", gis=mock_gis)

        # Only one call to gis.content.get — second was cached
        assert mock_gis.content.get.call_count == 1

    def test_cache_expires(self):
        mock_gis = _make_mock_gis()
        mock_item = _make_mock_item()
        mock_gis.content.get.return_value = mock_item

        ac.resolve_layer("abc123", gis=mock_gis)
        # Expire the cache entry
        ac._layer_cache["abc123"]["ts"] = time.time() - ac._LAYER_CACHE_TTL - 1
        ac.resolve_layer("abc123", gis=mock_gis)

        assert mock_gis.content.get.call_count == 2

    def test_second_layer_index(self):
        mock_gis = _make_mock_gis()
        mock_item = _make_mock_item(layer_urls=[
            "https://services.arcgis.com/abc/FeatureServer/0",
            "https://services.arcgis.com/abc/FeatureServer/1",
        ])
        mock_gis.content.get.return_value = mock_item

        fl, url = ac.resolve_layer("abc123", layer_index=1, gis=mock_gis)
        assert url == "https://services.arcgis.com/abc/FeatureServer/1"


# ---------------------------------------------------------------------------
# query_features
# ---------------------------------------------------------------------------

class TestQueryFeatures:
    def test_returns_plain_dicts(self):
        mock_fl = MagicMock()
        mock_result = MagicMock()
        mock_result.features = [
            _make_mock_feature({"CdgActvdd": "A001", "Area_ha": 10.5}),
            _make_mock_feature({"CdgActvdd": "A002", "Area_ha": 3.2}),
        ]
        mock_fl.query.return_value = mock_result

        records = ac.query_features(mock_fl)

        assert len(records) == 2
        assert records[0] == {"attributes": {"CdgActvdd": "A001", "Area_ha": 10.5}}
        assert records[1] == {"attributes": {"CdgActvdd": "A002", "Area_ha": 3.2}}

    def test_passes_query_params(self):
        mock_fl = MagicMock()
        mock_fl.query.return_value = MagicMock(features=[])

        ac.query_features(mock_fl, where="CdgActvdd='A001'",
                          out_fields="CdgActvdd", return_geometry=True)

        mock_fl.query.assert_called_once_with(
            where="CdgActvdd='A001'",
            out_fields="CdgActvdd",
            return_geometry=True,
        )

    def test_empty_result(self):
        mock_fl = MagicMock()
        mock_fl.query.return_value = MagicMock(features=[])

        records = ac.query_features(mock_fl)
        assert records == []


# ---------------------------------------------------------------------------
# resolve_layer_urls
# ---------------------------------------------------------------------------

class TestResolveLayerUrls:
    @pytest.fixture(autouse=True)
    def _mock_import(self):
        with patch.object(ac, "_import_arcgis",
                          return_value=(MagicMock(), MagicMock())):
            yield

    def test_resolves_both_ids(self):
        mock_gis = _make_mock_gis()

        def fake_get(item_id):
            item = _make_mock_item(item_id=item_id, layer_urls=[
                f"https://services.arcgis.com/{item_id}/FeatureServer/0",
            ])
            return item

        mock_gis.content.get.side_effect = fake_get

        urls = ac.resolve_layer_urls("poly_id", "point_id", gis=mock_gis)

        assert urls["polygon"] == "https://services.arcgis.com/poly_id/FeatureServer/0"
        assert urls["point"] == "https://services.arcgis.com/point_id/FeatureServer/0"

    def test_skips_empty_ids(self):
        mock_gis = _make_mock_gis()
        urls = ac.resolve_layer_urls("", "", gis=mock_gis)
        assert urls == {"polygon": "", "point": ""}
        mock_gis.content.get.assert_not_called()

    def test_handles_lookup_error_gracefully(self):
        mock_gis = _make_mock_gis()
        mock_gis.content.get.return_value = None  # item not found

        urls = ac.resolve_layer_urls("bad_id", gis=mock_gis)
        assert urls["polygon"] == ""


# ---------------------------------------------------------------------------
# is_connected / get_connection_info
# ---------------------------------------------------------------------------

class TestConnectionState:
    def test_not_connected_initially(self):
        assert ac.is_connected() is False

    def test_connected_after_oauth(self):
        _simulate_oauth_session()
        assert ac.is_connected() is True

    def test_not_connected_after_clear(self):
        _simulate_oauth_session()
        ac.clear_caches()
        assert ac.is_connected() is False

    def test_not_connected_after_expiry(self):
        _simulate_oauth_session()
        ac._gis_created_at = time.time() - ac._GIS_MAX_AGE - 1
        assert ac.is_connected() is False

    def test_connection_info_when_disconnected(self):
        info = ac.get_connection_info()
        assert info == {"connected": False}

    def test_connection_info_when_connected(self):
        _simulate_oauth_session(username="yun", org_name="IUCN")
        info = ac.get_connection_info()
        assert info["connected"] is True
        assert info["username"] == "yun"
        assert info["org"] == "IUCN"
        assert "age_seconds" in info


# ---------------------------------------------------------------------------
# clear_caches
# ---------------------------------------------------------------------------

class TestClearCaches:
    def test_clears_gis_instance(self):
        _simulate_oauth_session()
        ac.clear_caches()
        assert ac._gis_instance is None
        assert ac._gis_created_at == 0.0

    def test_clears_layer_cache(self):
        ac._layer_cache["test"] = {"fl": None, "url": "x", "ts": 0}
        ac.clear_caches()
        assert len(ac._layer_cache) == 0

    def test_clears_tokens(self):
        ac._access_token = "secret"
        ac._refresh_token = "refresh"
        ac._token_expires_at = time.time() + 9999
        ac.clear_caches()
        assert ac._access_token == ""
        assert ac._refresh_token == ""
        assert ac._token_expires_at == 0.0

    def test_clears_oauth_state(self):
        ac._oauth_state["test"] = {"code_verifier": "v"}
        ac.clear_caches()
        assert len(ac._oauth_state) == 0
