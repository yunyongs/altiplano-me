"""AGOL authenticated connection via OAuth 2.0 PKCE and feature-layer resolution.

/ Conexión autenticada a AGOL mediante OAuth 2.0 PKCE y resolución de capas.

This module centralises all ArcGIS Online interactions so that:
1. Authentication uses OAuth 2.0 Authorization Code + PKCE (no passwords).
2. Feature Layer URLs are resolved by Item ID, not hardcoded.
3. Queries run through the authenticated session -> works with
   non-public (licensed) layers.

The operator provides Organisation URL and Client ID via the dashboard UI.
Values in .env (ARCGIS_ORG_URL, ARCGIS_CLIENT_ID) serve as fallback defaults.
"""
from __future__ import annotations

import base64
import hashlib
import logging
import os
import secrets
import threading
import time
from typing import Any
from urllib.parse import urlencode

import requests as _requests

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# GIS singleton - created once, reused across requests
# ---------------------------------------------------------------------------
_gis_lock = threading.Lock()
_gis_instance = None          # type: Any  (arcgis.gis.GIS or None)
_gis_created_at: float = 0.0
_GIS_MAX_AGE = 3600           # re-authenticate every 60 min

# OAuth2 PKCE state
_oauth_state: dict[str, dict[str, str]] = {}  # state -> {code_verifier, org_url, client_id}
_access_token: str = ""
_refresh_token: str = ""
_token_expires_at: float = 0.0

# ---------------------------------------------------------------------------
# Layer URL cache - Item ID -> resolved URL (rarely changes)
# ---------------------------------------------------------------------------
_layer_cache: dict[str, dict] = {}   # item_id -> {"url": str, "ts": float}
_LAYER_CACHE_TTL = 1800              # 30 min

REDIRECT_PATH = "/oauth/callback"


def _import_arcgis():
    """Lazy import so the module can be loaded even without arcgis."""
    try:
        from arcgis.gis import GIS               # noqa: F811
        from arcgis.features import FeatureLayer  # noqa: F811
        return GIS, FeatureLayer
    except ImportError as exc:
        raise ImportError(
            "arcgis package is required.  "
            "Install:  pip install arcgis\n"
            "/ Se requiere el paquete arcgis.  "
            "Instalar: pip install arcgis"
        ) from exc


# ── OAuth 2.0 PKCE helpers ───────────────────────────────────────────────

def _generate_pkce() -> tuple[str, str]:
    """Generate PKCE code_verifier and code_challenge (S256).

    Returns (code_verifier, code_challenge).
    """
    code_verifier = secrets.token_urlsafe(64)[:128]
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return code_verifier, code_challenge


def build_authorize_url(
    redirect_uri: str,
    org_url: str | None = None,
    client_id: str | None = None,
    expiration: int = 20160,
) -> dict:
    """Build the AGOL OAuth2 authorize URL with PKCE challenge.

    Returns {url, state} where state is used to match the callback.
    """
    org_url = (org_url or os.getenv("ARCGIS_ORG_URL", "")).rstrip("/")
    client_id = client_id or os.getenv("ARCGIS_CLIENT_ID", "")

    if not org_url:
        raise ValueError(
            "Organization URL is required. Enter it in the dashboard or set ARCGIS_ORG_URL in .env.\n"
            "/ Se requiere URL de organización. Ingréselo en el panel o configure ARCGIS_ORG_URL en .env."
        )
    if not client_id:
        raise ValueError(
            "ARCGIS_CLIENT_ID must be set in .env. "
            "Register an OAuth app in AGOL → Content → New Item → Application, "
            "add http://localhost:5000/oauth/callback as redirect URI, "
            "then copy the Client ID to .env.\n"
            "/ Se requiere ARCGIS_CLIENT_ID en .env. "
            "Registre una app OAuth en AGOL → Contenido → Nuevo elemento → Aplicación, "
            "agregue http://localhost:5000/oauth/callback como URI de redirección, "
            "luego copie el Client ID al .env."
        )

    code_verifier, code_challenge = _generate_pkce()
    state = secrets.token_urlsafe(32)

    _oauth_state[state] = {
        "code_verifier": code_verifier,
        "org_url": org_url,
        "client_id": client_id,
    }

    authorize_endpoint = f"{org_url}/sharing/rest/oauth2/authorize"
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "expiration": expiration,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "state": state,
    }
    url = f"{authorize_endpoint}?{urlencode(params)}"
    return {"url": url, "state": state}


def exchange_code(
    code: str,
    state: str,
    redirect_uri: str,
) -> dict:
    """Exchange authorization code for access token via AGOL token endpoint.

    Returns connection info dict with {connected, username, org, ...}.
    """
    global _access_token, _refresh_token, _token_expires_at  # noqa: PLW0603

    pending = _oauth_state.pop(state, None)
    if pending is None:
        raise ValueError("Invalid or expired OAuth state parameter.")

    code_verifier = pending["code_verifier"]
    org_url = pending["org_url"]
    client_id = pending["client_id"]

    token_endpoint = f"{org_url}/sharing/rest/oauth2/token"
    resp = _requests.post(token_endpoint, data={
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "code_verifier": code_verifier,
    }, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    if "error" in data:
        raise RuntimeError(
            f"AGOL token error: {data.get('error', {}).get('message', data)}"
        )

    _access_token = data.get("access_token", "")
    _refresh_token = data.get("refresh_token", "")
    expires_in = data.get("expires_in", 7200)
    _token_expires_at = time.time() + expires_in

    # Create GIS session with token
    _create_gis_from_token(org_url)

    info = get_connection_info()
    info["expires_in"] = expires_in
    return info


def _create_gis_from_token(org_url: str | None = None):
    """Create GIS singleton from the stored access token."""
    global _gis_instance, _gis_created_at  # noqa: PLW0603

    org_url = org_url or os.getenv("ARCGIS_ORG_URL", "").rstrip("/")

    if not _access_token:
        raise ValueError("No access token available. Authenticate first.")

    with _gis_lock:
        GIS, _ = _import_arcgis()
        log.info("[AGOL] Creating GIS session with OAuth token @ %s", org_url)
        _gis_instance = GIS(org_url, token=_access_token)
        _gis_created_at = time.time()
        log.info("[AGOL] Authenticated via OAuth - user: %s, org: %s",
                 _gis_instance.properties.user.username,
                 _gis_instance.properties.name)


# ── Public API ────────────────────────────────────────────────────────────

def get_gis(*, force: bool = False):
    """Return an authenticated GIS singleton (thread-safe).

    The GIS session must be established via OAuth2 first
    (build_authorize_url -> exchange_code).
    The connection is re-created when *force=True* or after
    ``_GIS_MAX_AGE`` seconds to keep the token fresh.

    / Devuelve una conexion GIS autenticada (singleton thread-safe).
    """
    global _gis_instance, _gis_created_at  # noqa: PLW0603

    with _gis_lock:
        if _gis_instance is None:
            raise ValueError(
                "AGOL session not established. Click 'Conectar AGOL' "
                "in the dashboard to authenticate via OAuth.\n"
                "/ Sesion AGOL no establecida. Haga clic en 'Conectar AGOL' "
                "para autenticarse via OAuth."
            )

        age = time.time() - _gis_created_at
        if not force and age < _GIS_MAX_AGE:
            return _gis_instance

    # Outside lock: token may still be valid - recreate GIS
    if _access_token and time.time() < _token_expires_at:
        _create_gis_from_token()
        return _gis_instance

    raise ValueError(
        "AGOL token expired. Please re-authenticate via the dashboard.\n"
        "/ Token AGOL expirado. Reautentíquese en el dashboard."
    )


def resolve_layer(
    item_id: str,
    layer_index: int = 0,
    *,
    gis=None,
):
    """Resolve an AGOL Item ID to a FeatureLayer object.

    Returns ``(feature_layer, url_str)``.  The result is cached for
    ``_LAYER_CACHE_TTL`` seconds so repeated calls are free.

    / Resuelve un Item ID de AGOL a un objeto FeatureLayer.
    """
    cached = _layer_cache.get(item_id)
    if cached and (time.time() - cached["ts"]) < _LAYER_CACHE_TTL:
        log.debug("[AGOL] Layer cache HIT for item %s", item_id)
        return cached["fl"], cached["url"]

    if gis is None:
        gis = get_gis()

    _, FeatureLayer = _import_arcgis()

    item = gis.content.get(item_id)
    if item is None:
        raise LookupError(
            f"AGOL item '{item_id}' not found or not accessible.\n"
            f"/ El item AGOL '{item_id}' no existe o no tiene acceso."
        )

    layers = item.layers
    if not layers:
        raise LookupError(
            f"AGOL item '{item_id}' ({item.title}) has no feature layers.\n"
            f"/ El item '{item_id}' ({item.title}) no tiene capas."
        )
    if layer_index >= len(layers):
        raise IndexError(
            f"Layer index {layer_index} out of range "
            f"(item has {len(layers)} layers).\n"
            f"/ Indice de capa {layer_index} fuera de rango."
        )

    fl = layers[layer_index]
    url = fl.url
    log.info("[AGOL] Resolved item %s -> %s (layer %d: %s)",
             item_id, url, layer_index, item.title)

    _layer_cache[item_id] = {"fl": fl, "url": url, "ts": time.time()}
    return fl, url


def query_features(
    feature_layer,
    where: str = "1=1",
    out_fields: str = "CdgActvdd,Area_ha",
    return_geometry: bool = False,
) -> list[dict]:
    """Execute a query on a FeatureLayer using the authenticated session.

    Returns a plain list of feature dicts ``[{attributes: {...}}, ...]``
    compatible with the existing ``_features_to_records()`` in app.py.

    Benefits over raw ``requests.post()``:
    • Token is included automatically.
    • Pagination (exceededTransferLimit) is handled by the SDK.
    • Retries on transient 498/499 token errors.

    / Ejecuta una consulta en un FeatureLayer con sesión autenticada.
    """
    result = feature_layer.query(
        where=where,
        out_fields=out_fields,
        return_geometry=return_geometry,
    )
    # result is a FeatureSet; convert to plain dicts
    return [{"attributes": f.attributes} for f in result.features]


def resolve_layer_urls(
    polygon_item_id: str | None = None,
    point_item_id: str | None = None,
    *,
    gis=None,
) -> dict[str, str]:
    """Convenience: resolve both polygon and point item IDs at once.

    Returns ``{"polygon": url_or_empty, "point": url_or_empty}``.
    """
    polygon_item_id = polygon_item_id or os.getenv("AGOL_POLYGON_ITEM_ID", "")
    point_item_id = point_item_id or os.getenv("AGOL_POINT_ITEM_ID", "")

    if gis is None:
        gis = get_gis()

    urls: dict[str, str] = {"polygon": "", "point": ""}

    for label, item_id in [("polygon", polygon_item_id), ("point", point_item_id)]:
        if not item_id:
            continue
        try:
            _, url = resolve_layer(item_id, gis=gis)
            urls[label] = url
        except (LookupError, IndexError) as exc:
            log.warning("[AGOL] Could not resolve %s item %s: %s",
                        label, item_id, exc)

    return urls


# ── Connection state ─────────────────────────────────────────────────────

def is_connected() -> bool:
    """Return True if a GIS session is active and not expired."""
    with _gis_lock:
        if _gis_instance is None:
            return False
        return (time.time() - _gis_created_at) < _GIS_MAX_AGE


def get_token() -> str:
    """Return the current OAuth access token if still valid, else empty string.

    Unlike ``is_connected()`` this does NOT require a GIS instance —
    the raw token is sufficient for REST-based feature queries.
    """
    if _access_token and time.time() < _token_expires_at:
        return _access_token
    return ""


def get_connection_info() -> dict:
    """Return current connection status for the dashboard."""
    with _gis_lock:
        if _gis_instance is None:
            return {"connected": False}
        age = time.time() - _gis_created_at
        try:
            user = _gis_instance.properties.user.username
            org = _gis_instance.properties.name
        except Exception:
            user = "?"
            org = "?"
        return {
            "connected": age < _GIS_MAX_AGE,
            "username": user,
            "org": org,
            "age_seconds": int(age),
            "max_age": _GIS_MAX_AGE,
        }


# ── Cache management ─────────────────────────────────────────────────────

def clear_caches():
    """Reset GIS singleton, layer cache, and OAuth tokens."""
    global _gis_instance, _gis_created_at  # noqa: PLW0603
    global _access_token, _refresh_token, _token_expires_at  # noqa: PLW0603
    with _gis_lock:
        _gis_instance = None
        _gis_created_at = 0.0
    _access_token = ""
    _refresh_token = ""
    _token_expires_at = 0.0
    _oauth_state.clear()
    _layer_cache.clear()
