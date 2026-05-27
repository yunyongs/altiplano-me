"""
PASO 3 — Cleaning Criteria manager.

Records the decisions made by the Coordinator during the cleaning meeting
and allows exporting them as PDF for team sharing.

ES: Registra los criterios de limpieza acordados en la reunión de coordinación
    y permite exportarlos como PDF para compartir con el equipo.
"""
from __future__ import annotations

import json
import os
import pathlib
from datetime import datetime
from typing import Any

# EN: Criteria are stored under data/criteria/<quarter>_criteria.json
# ES: Los criterios se guardan en data/criteria/<trimestre>_criteria.json
_DATA_DIR = pathlib.Path(__file__).parent / "data" / "criteria"


def _ensure_data_dir() -> None:
    """Create data/criteria/ if it does not exist."""
    # EN: Auto-create the storage directory on first use.
    # ES: Crea el directorio de almacenamiento automáticamente si no existe.
    os.makedirs(_DATA_DIR, exist_ok=True)


def _criteria_path(quarter: str) -> pathlib.Path:
    """Return the JSON file path for a given quarter."""
    # EN: Sanitize quarter name to be safe as a filename component.
    # ES: Sanitiza el nombre del trimestre para usarlo como parte del nombre de archivo.
    safe = quarter.replace("/", "_").replace("\\", "_").replace("..", "")
    return _DATA_DIR / f"{safe}_criteria.json"


# ---------------------------------------------------------------------------
# Core CRUD
# ---------------------------------------------------------------------------

def save_criteria(quarter: str, entries: list[dict]) -> dict:
    """
    Persist criteria entries for a given quarter.

    EN: Overwrites the existing criteria file for the quarter.
    ES: Sobreescribe el archivo de criterios existente para el trimestre.

    Args:
        quarter:  Quarter identifier, e.g. "T2026_Q1"
                  / Identificador de trimestre, ej. "T2026_Q1"
        entries:  List of criterion dicts (see JSON schema in docstring)
                  / Lista de dicts de criterios

    Returns:
        Saved data dict / Datos guardados como dict
    """
    _ensure_data_dir()
    # EN: Re-number entries sequentially so IDs are always clean after edits.
    # ES: Re-numera los registros secuencialmente para mantener IDs limpios.
    for i, entry in enumerate(entries, start=1):
        entry.setdefault("id", i)
        entry.setdefault("recorded_at", datetime.now().isoformat(timespec="seconds"))
        entry.setdefault("recorded_by", "coordinator")

    data = {
        "quarter": quarter,
        "recorded_at": datetime.now().isoformat(timespec="seconds"),
        "entries": entries,
    }
    path = _criteria_path(quarter)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data


def load_criteria(quarter: str) -> dict:
    """
    Load criteria for a given quarter.

    EN: Returns an empty structure if no file exists yet.
    ES: Devuelve una estructura vacía si aún no existe el archivo.

    Returns:
        {"quarter": ..., "recorded_at": ..., "entries": [...]}
    """
    path = _criteria_path(quarter)
    if not path.exists():
        return {"quarter": quarter, "recorded_at": None, "entries": []}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def add_criterion(quarter: str, entry: dict) -> dict:
    """
    Append a single criterion to the quarter's list.

    EN: Loads the existing list, appends the new entry, saves, and returns.
    ES: Carga la lista existente, agrega la nueva entrada, guarda y retorna.

    Returns:
        The newly added entry with its assigned ID.
        / La entrada recién agregada con su ID asignado.
    """
    data = load_criteria(quarter)
    entries = data.get("entries", [])
    new_id = max((e.get("id", 0) for e in entries), default=0) + 1
    entry["id"] = new_id
    entry.setdefault("recorded_at", datetime.now().isoformat(timespec="seconds"))
    entry.setdefault("recorded_by", "coordinator")
    entries.append(entry)
    save_criteria(quarter, entries)
    return entry


def list_criteria_quarters() -> list[str]:
    """
    Return a sorted list of quarters that have saved criteria files.

    ES: Devuelve una lista ordenada de trimestres con archivos de criterios guardados.
    """
    _ensure_data_dir()
    quarters = []
    for f in _DATA_DIR.glob("*_criteria.json"):
        # EN: Strip the "_criteria" suffix to recover the quarter name.
        # ES: Quita el sufijo "_criteria" para recuperar el nombre del trimestre.
        quarters.append(f.stem.replace("_criteria", ""))
    return sorted(quarters)


# ---------------------------------------------------------------------------
# PDF Export
# ---------------------------------------------------------------------------

def export_criteria_pdf(quarter: str, output_path: str) -> str:
    """
    Export the criteria list for a quarter to a PDF file.

    EN: Uses fpdf2 if available, otherwise generates an HTML file and
        instructs the user to print it from the browser.
    ES: Usa fpdf2 si está disponible; si no, genera un HTML para imprimir
        desde el navegador.

    Args:
        quarter:      Quarter identifier / Identificador de trimestre
        output_path:  Destination PDF (or HTML) path / Ruta de destino

    Returns:
        Absolute path of the generated file / Ruta absoluta del archivo generado
    """
    data = load_criteria(quarter)
    entries = data.get("entries", [])

    try:
        from fpdf import FPDF  # type: ignore
        return _export_pdf_fpdf(quarter, entries, output_path)
    except ImportError:
        pass

    try:
        from reportlab.lib.pagesizes import A4  # type: ignore
        from reportlab.platypus import SimpleDocTemplate  # type: ignore
        return _export_pdf_reportlab(quarter, entries, output_path)
    except ImportError:
        pass

    # EN: Fallback — generate a printable HTML file the user can print to PDF.
    # ES: Alternativa — genera un HTML imprimible que el usuario puede imprimir como PDF.
    html_path = output_path.replace(".pdf", ".html")
    _export_html(quarter, entries, html_path)
    return html_path


def _export_pdf_fpdf(quarter: str, entries: list[dict], output_path: str) -> str:
    """PDF generation using fpdf2. / Generación de PDF con fpdf2."""
    from fpdf import FPDF  # type: ignore

    pdf = FPDF()
    pdf.add_page()

    # EN: Title section / Sección de título
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(0, 63, 110)  # AR Blue
    pdf.cell(0, 10, f"Criterios de Limpieza - {quarter}", ln=True)

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(0, 6, f"Altiplano Resiliente | Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True)
    pdf.ln(4)

    # EN: Table header / Encabezado de tabla
    col_w = [10, 30, 55, 55, 30, 10]
    headers = ["#", "Capa", "Razón / Reason", "Decisión / Decision", "CdgActvdd", "Por"]
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(0, 63, 110)   # AR Blue
    pdf.set_text_color(255, 255, 255)
    for w, h in zip(col_w, headers):
        pdf.cell(w, 7, h, border=1, fill=True)
    pdf.ln()

    # EN: Table rows / Filas de tabla
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(15, 23, 42)
    for entry in entries:
        pdf.set_fill_color(240, 247, 255)
        vals = [
            str(entry.get("id", "")),
            entry.get("layer", "")[:18],
            entry.get("reason", "")[:38],
            entry.get("decision", "")[:38],
            entry.get("cdg_actividad", "")[:18],
            entry.get("recorded_by", "")[:8],
        ]
        fill = True
        for w, v in zip(col_w, vals):
            pdf.cell(w, 6, v, border=1, fill=fill)
        pdf.ln()

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    pdf.output(output_path)
    return os.path.abspath(output_path)


def _export_pdf_reportlab(quarter: str, entries: list[dict], output_path: str) -> str:
    """PDF generation using reportlab. / Generación de PDF con reportlab."""
    from reportlab.lib import colors  # type: ignore
    from reportlab.lib.pagesizes import A4  # type: ignore
    from reportlab.lib.styles import getSampleStyleSheet  # type: ignore
    from reportlab.platypus import (Paragraph, SimpleDocTemplate,  # type: ignore
                                    Spacer, Table, TableStyle)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    doc = SimpleDocTemplate(output_path, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    # EN: Title / Título
    title_style = styles["Heading1"]
    title_style.textColor = colors.HexColor("#003f6e")
    story.append(Paragraph(f"Criterios de Limpieza — {quarter}", title_style))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        f"Altiplano Resiliente | Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        styles["Normal"],
    ))
    story.append(Spacer(1, 10))

    # EN: Data table / Tabla de datos
    table_data = [["#", "Capa", "Razón / Reason", "Decisión / Decision", "CdgActvdd", "Por"]]
    for entry in entries:
        table_data.append([
            str(entry.get("id", "")),
            entry.get("layer", ""),
            entry.get("reason", ""),
            entry.get("decision", ""),
            entry.get("cdg_actividad", ""),
            entry.get("recorded_by", ""),
        ])

    tbl = Table(table_data, colWidths=[20, 60, 120, 120, 80, 40])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#003f6e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#e0ecf5"), colors.white]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#003f6e")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(tbl)

    doc.build(story)
    return os.path.abspath(output_path)


def _export_html(quarter: str, entries: list[dict], html_path: str) -> None:
    """
    HTML fallback export for browser-based printing to PDF.

    ES: Alternativa HTML para impresión como PDF desde el navegador.
    """
    rows_html = ""
    for entry in entries:
        rows_html += (
            f"<tr>"
            f"<td>{entry.get('id','')}</td>"
            f"<td>{entry.get('layer','')}</td>"
            f"<td>{entry.get('reason','')}</td>"
            f"<td>{entry.get('decision','')}</td>"
            f"<td>{entry.get('cdg_actividad','')}</td>"
            f"<td>{entry.get('recorded_by','')}</td>"
            f"<td>{entry.get('recorded_at','')[:10]}</td>"
            f"</tr>\n"
        )

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Criterios de Limpieza — {quarter}</title>
<style>
  body {{ font-family: 'Helvetica Neue', Arial, sans-serif; padding: 24px; color: #0f172a; }}
  h1 {{ color: #003f6e; }}
  p.meta {{ color: #475569; font-size: 0.85em; margin-top: -8px; }}
  table {{ border-collapse: collapse; width: 100%; margin-top: 16px; font-size: 0.85em; }}
  th {{ background: #003f6e; color: #fff; padding: 6px 8px; text-align: left; }}
  td {{ padding: 5px 8px; border-bottom: 1px solid #e2e8f0; }}
  tr:nth-child(even) {{ background: #e0ecf5; }}
  @media print {{ body {{ padding: 8px; }} }}
</style>
</head>
<body>
<h1>Criterios de Limpieza — {quarter}</h1>
<p class="meta">Altiplano Resiliente &nbsp;|&nbsp;
   Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
<table>
  <thead>
    <tr>
      <th>#</th><th>Capa / Layer</th><th>Razón / Reason</th>
      <th>Decisión / Decision</th><th>CdgActvdd</th>
      <th>Por / By</th><th>Fecha</th>
    </tr>
  </thead>
  <tbody>
{rows_html}  </tbody>
</table>
<p style="color:#475569;font-size:0.8em;margin-top:20px;">
  Para guardar como PDF: Archivo → Imprimir → Guardar como PDF /
  To save as PDF: File → Print → Save as PDF
</p>
</body>
</html>"""

    os.makedirs(os.path.dirname(html_path) or ".", exist_ok=True)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
