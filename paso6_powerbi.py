"""
PASO 6 — Power BI script generators + Publish-to-Web link validation.

Power BI refresh uses PBI Desktop + MCP (Model Context Protocol).
Scripts here generate instructions for the MCP-based refresh workflow.

──────────────────────────────────────────────────────────────────────
G10: Publish-to-Web embed URL validation — API research results
──────────────────────────────────────────────────────────────────────
INVESTIGATION: Power BI Service REST API
  Endpoint:  GET https://api.powerbi.com/v1.0/myorg/reports/{reportId}/publishToWeb
  Auth:      Azure AD OAuth2 token (scope: https://analysis.windows.net/powerbi/api/.default)
  Status:    REQUIRES service account or Service Principal with admin consent.
             Not feasible for this project — no Azure AD tenant/credentials configured.

INVESTIGATION: Microsoft Fabric API
  Endpoint:  GET https://api.fabric.microsoft.com/v1/workspaces/{workspaceId}/reports/{reportId}
  Auth:      Same OAuth2 requirement.
  Status:    Same limitation — not feasible without tenant credentials.

DECISION: HTTP HEAD/GET fallback implemented.
  - "Publish to Web" embed URLs are publicly accessible iframes.
  - HTTP response code reliably indicates embed URL validity:
      200  → link valid and publicly accessible
      401/403 → requires authentication or access denied (inactive/private)
      404  → link removed or never existed
      timeout/error → network issue
  - This approach requires no credentials and works for all embed URLs.
──────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import textwrap
import urllib.parse
from typing import Optional

import requests as _requests


# ---------------------------------------------------------------------------
# SSRF mitigation  /  Mitigación de SSRF
# ---------------------------------------------------------------------------

_ALLOWED_PBI_HOSTS = {
    "app.powerbi.com",
    "app.powerbigov.us",
    "app.powerbi.de",
    "app.powerbi.cn",
}


def _is_allowed_pbi_url(url: str) -> bool:
    """Validate that URL points to a known Power BI domain.
    / Valida que la URL apunte a un dominio conocido de Power BI.
    """
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception:
        return False
    if parsed.scheme not in ("https",):
        return False
    host = parsed.hostname or ""
    if host in _ALLOWED_PBI_HOSTS:
        return True
    if host.endswith(".powerbi.com") or host.endswith(".pbidedicated.windows.net"):
        return True
    return False


def script_powerbi_refresh(p: dict) -> str:
    """Generate MCP refresh instructions for Power BI Desktop."""
    return textwrap.dedent("""\
        # PASO 6: Power BI — Actualización vía MCP
        # Power BI Refresh via MCP (Model Context Protocol)
        #
        # Prerequisitos / Prerequisites:
        #   - Power BI Desktop instalado / installed
        #   - Archivo .pbip abierto en PBI Desktop / .pbip file open in PBI Desktop
        #   - Motor AS de PBI Desktop corriendo / PBI Desktop AS engine running
        #
        # ── 1. Conectar al motor AS local / Connect to local AS engine ──
        # Use la app web: botón "Estado PBI Desktop" para ver el puerto
        # Use the web app: "Estado PBI Desktop" button to see the port
        #
        # En VS Code Copilot (MCP):
        #   connection_operations → ListLocalInstances
        #   connection_operations → Connect
        #   ConnectionString: "Provider=MSOLAP;Data Source=localhost:<PORT>"
        #
        # ── 2. Actualizar tablas / Refresh tables ──
        # En VS Code Copilot (MCP):
        #   partition_operations → Refresh
        #   TableName: "Tbl_Actvdd_m_e_data"  (o cualquier tabla)
        #   RefreshType: "Full"
        #
        # Tablas principales a actualizar:
        #   - Tbl_Actvdd_m_e_data (Tbl_Integrado.xlsx)
        #   - Tbl_Pp (Tbl_Integrado.xlsx)
        #   - Tbl_Area (AR_3_Area/0. Database_oficial)
        #   - Tbl_Actvdd_ss (Smartsheet — requiere OAuth activo en PBI Desktop)
        #
        # ── 3. Verificar resultados / Verify results ──
        # En VS Code Copilot (MCP):
        #   dax_query_operations → Execute
        #   Query: "EVALUATE ROW(\\"Rows\\", COUNTROWS('Tbl_Actvdd_m_e_data'))"
        #
        # ── 4. Guardar en PBI Desktop / Save in PBI Desktop ──
        #   Ctrl+S en Power BI Desktop
        #   Los cambios se reflejan automáticamente en archivos TMDL
        #
        print("Instrucciones generadas. Siga los pasos arriba.")
        print("Instructions generated. Follow the steps above.")
    """)


def script_arcgis_portal_data(p: dict) -> str:
    """Generate a script to extract data from ArcGIS Online portal."""
    portal_url = p.get("agol_portal_url", "")
    polygon_item_id = p.get("agol_polygon_item_id", "")
    point_item_id = p.get("agol_point_item_id", "")

    auth_line = 'gis = GIS("pro")  # Usa sesión activa de ArcGIS Pro / Uses active ArcGIS Pro session'

    item_example = ""
    if polygon_item_id:
        item_example = f'item = gis.content.get("{polygon_item_id}")  # Polígono'
    elif point_item_id:
        item_example = f'item = gis.content.get("{point_item_id}")  # Punto'
    else:
        item_example = '# item = gis.content.get("YOUR_ITEM_ID")'

    return textwrap.dedent(f"""\
        # PASO 6: Extract ArcGIS Online data for Power BI
        from arcgis.gis import GIS
        import pandas as pd

        # Connect / Conectar a AGOL
        {auth_line}
        print(f"Connected as: {{gis.properties.user.username}}")

        # Search for feature layers
        items = gis.content.search("Altiplano Resiliente", item_type="Feature Layer Collection")
        for item in items:
            print(f"  - {{item.title}} ({{item.id}})")

        # Load a specific layer by Item ID / Cargar capa por Item ID
        {item_example}
        # fl = item.layers[0]
        # df = pd.DataFrame.spatial.from_layer(fl)
        # print(f"Loaded {{len(df)}} features")
    """)


def check_publish_url(embed_url: str, timeout: int = 10) -> dict:
    """
    Verify that a Power BI "Publish to Web" embed URL is publicly accessible.

    Uses HTTP HEAD (falls back to GET) to inspect the response code.
    Power BI REST API requires OAuth2 credentials not available in this project
    (see module-level docstring for full investigation notes).

    Args:
        embed_url: The embed URL to check (e.g. https://app.powerbi.com/view?r=...)
        timeout:   HTTP request timeout in seconds.

    Returns:
        {
            "status":    "ok" | "warning" | "error",
            "http_code": int | None,
            "message":   str  (bilingual ES/EN)
        }

    # ES: Estado "ok" → enlace válido (200)
    # ES: Estado "warning" → requiere autenticación (401/403)
    # ES: Estado "error" → enlace inválido (404) o error de red
    # EN: Status "ok" → link valid (200)
    # EN: Status "warning" → requires authentication (401/403)
    # EN: Status "error" → invalid link (404) or network error
    """
    if not embed_url or not embed_url.strip():
        return {
            "status": "error",
            "http_code": None,
            "message": "URL vacía / Empty URL",
        }

    url = embed_url.strip()

    if not _is_allowed_pbi_url(url):
        return {
            "status": "error",
            "http_code": None,
            "message": "URL must be a Power BI domain (app.powerbi.com) / URL debe ser dominio Power BI",
        }

    try:
        # ES: Intentar HEAD primero (sin descargar cuerpo) / EN: Try HEAD first (no body download)
        resp = _requests.head(url, timeout=timeout, allow_redirects=True)
        # ES: Algunos servidores no admiten HEAD — usar GET como respaldo
        # EN: Some servers reject HEAD — fall back to GET with stream to avoid downloading body
        if resp.status_code in (405, 501):
            resp = _requests.get(url, timeout=timeout, allow_redirects=True, stream=True)
            resp.close()
    except _requests.exceptions.ConnectionError:
        return {
            "status": "error",
            "http_code": None,
            "message": "Error de conexión / Connection error",
        }
    except _requests.exceptions.Timeout:
        return {
            "status": "error",
            "http_code": None,
            "message": "Tiempo de espera agotado / Request timed out",
        }
    except _requests.exceptions.RequestException as exc:
        return {
            "status": "error",
            "http_code": None,
            "message": f"Error de red / Network error: {exc}",
        }

    code = resp.status_code

    if code == 200:
        return {
            "status": "ok",
            "http_code": code,
            "message": "Enlace válido / Valid link (200 OK)",
        }
    if code in (401, 403):
        return {
            "status": "warning",
            "http_code": code,
            "message": (
                f"Requiere autenticación o acceso denegado / "
                f"Requires authentication or access denied ({code})"
            ),
        }
    if code == 404:
        return {
            "status": "error",
            "http_code": code,
            "message": "Enlace inválido o eliminado / Invalid or removed link (404)",
        }
    return {
        "status": "warning",
        "http_code": code,
        "message": f"Respuesta inesperada / Unexpected response ({code})",
    }


def get_embed_url_via_api(
    report_id: str,
    group_id: Optional[str] = None,
    access_token: Optional[str] = None,
) -> dict:
    """
    Attempt to retrieve a Publish-to-Web embed URL via Power BI Service REST API.

    NOT IMPLEMENTED: Requires an Azure AD OAuth2 access token with
    Report.Read.All or Report.ReadWrite.All permission, plus admin consent
    for service principal usage.  This project has no Azure AD credentials.

    Args:
        report_id:    Power BI report GUID.
        group_id:     Workspace (group) GUID.  None → "My Workspace".
        access_token: Bearer token (Azure AD).  None → raises NotImplementedError.

    Returns:
        dict with embed URL details (not implemented — always raises).

    Raises:
        NotImplementedError: Always, until Azure AD credentials are configured.

    # ES: No implementado — requiere credenciales de Azure AD (Service Principal)
    # EN: Not implemented — requires Azure AD credentials (Service Principal)
    """
    # ES: Guardamos la lógica de URL para cuando se agreguen credenciales
    # EN: Keep URL logic so it is ready once credentials are added
    if group_id:
        endpoint = (
            f"https://api.powerbi.com/v1.0/myorg/groups/{group_id}"
            f"/reports/{report_id}/publishToWeb"
        )
    else:
        endpoint = (
            f"https://api.powerbi.com/v1.0/myorg/reports/{report_id}/publishToWeb"
        )

    raise NotImplementedError(
        "Power BI REST API requires Azure AD OAuth2 credentials (Service Principal). "
        f"Target endpoint would be: {endpoint}. "
        "Configure AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID in .env to enable."
    )


def generate_pdf_export_guide(p: dict) -> str:
    """
    Generate a step-by-step manual PDF export guide for Power BI Desktop.
    / Genera una guía de pasos para exportar PDF manualmente desde Power BI Desktop.

    Power BI Service REST API ExportToFile requires Azure AD OAuth2 credentials
    (Service Principal with admin consent) — not available in this project.
    This function generates a manual guide + optional MCP DAX verification steps.
    / La API REST de Power BI Service requiere credenciales Azure AD — no disponibles.
    Esta función genera una guía manual y pasos opcionales de verificación MCP.

    Args in p:
        report_name:  Display name of the .pbix/.pbip report (e.g. "AR_Dashboard")
        output_path:  Suggested output folder for the PDF (e.g. "C:/informes/")
        quarter:      Work quarter label shown in the guide (e.g. "T2026_Q2")
        include_mcp:  bool — include MCP DAX verification steps (default True)

    Returns:
        Multi-line guide string (Spanish/English bilingual)
    """
    report_name = p.get("report_name", "AR_Dashboard")
    output_path = p.get("output_path", "").strip() or "C:\\informes\\"
    quarter = p.get("quarter", "")
    include_mcp = p.get("include_mcp", True)

    quarter_label = f" — {quarter}" if quarter else ""

    mcp_section = ""
    if include_mcp:
        mcp_section = f"""
# ── 4. Verificar datos antes de exportar (MCP DAX) / Verify data before export (MCP DAX) ──
# En VS Code Copilot (MCP) / In VS Code Copilot (MCP):
#   dax_query_operations → Execute
#   Query: "EVALUATE ROW(\\"Filas\\", COUNTROWS('Tbl_Actvdd_m_e_data'))"
# Confirme que el conteo coincide con Smartsheet.
# Confirm the row count matches Smartsheet.
"""

    return f"""# ══════════════════════════════════════════════════════════════════════
# PASO 7: Exportar Reporte PDF desde Power BI Desktop{quarter_label}
# Export PDF Report from Power BI Desktop{quarter_label}
#
# NOTA: Power BI Service REST API (ExportToFile) requiere credenciales
# Azure AD que no están configuradas en este proyecto.
# NOTE: Power BI Service REST API (ExportToFile) requires Azure AD
# credentials not configured in this project.
# Para automatización futura: configure AZURE_CLIENT_ID, AZURE_CLIENT_SECRET,
# AZURE_TENANT_ID en .env.
# For future automation: configure AZURE_CLIENT_ID, AZURE_CLIENT_SECRET,
# AZURE_TENANT_ID in .env.
# ══════════════════════════════════════════════════════════════════════

# ── 1. Abrir el reporte / Open the report ──
# Abra Power BI Desktop y cargue: {report_name}
# Open Power BI Desktop and load: {report_name}
{mcp_section}
# ── 2. Actualizar datos si es necesario / Refresh data if needed ──
# Cinta: Inicio → Actualizar
# Ribbon: Home → Refresh

# ── 3. Exportar a PDF / Export to PDF ──
# Cinta: Archivo → Exportar → Exportar a PDF
# Ribbon: File → Export → Export to PDF
#
# Opciones recomendadas / Recommended options:
#   - Exportar páginas: Todas / Export pages: All
#   - Tamaño: A4 o Carta / Size: A4 or Letter
#
# Guardar como / Save as:
#   {output_path}{report_name}{'_' + quarter if quarter else ''}.pdf

# ── 5. Verificar el PDF / Verify the PDF ──
# Confirme que el PDF se guardó en: {output_path}
# Confirm the PDF was saved in: {output_path}
# Revise que todas las visualizaciones son correctas.
# Review that all visualizations are correct.

print("Guía de exportación PDF generada. Siga los pasos arriba.")
print("PDF export guide generated. Follow the steps above.")
"""


PASO6_SCRIPTS = {
    "powerbi_refresh":     script_powerbi_refresh,
    "arcgis_portal_data":  script_arcgis_portal_data,
}
