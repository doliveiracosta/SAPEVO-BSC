"""PDF export for SAPEVO-BSC reports."""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import BinaryIO
from xml.sax.saxutils import escape

import pandas as pd

from .constants import APP_NAME, APP_OWNER_LABEL
from .core import strategic_conclusion


def write_pdf_report(
    output: str | BinaryIO,
    *,
    project: dict,
    weights: pd.DataFrame,
    project_weights: pd.DataFrame | None = None,
    ranking: pd.DataFrame,
) -> None:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(output, pagesize=A4, rightMargin=1.5 * cm, leftMargin=1.5 * cm)
    story = []

    def paragraph(text: object, style: str = "Normal") -> Paragraph:
        return Paragraph(escape(str(text)), styles[style])

    def table(rows: list[list[object]], widths: list[float]) -> Table:
        wrapped = [[paragraph(value) for value in row] for row in rows]
        t = Table(wrapped, colWidths=widths, repeatRows=1)
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111827")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#9ca3af")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        return t

    story.append(paragraph(APP_NAME, "Title"))
    story.append(paragraph("Relatorio consultivo de priorizacao estrategica", "Heading2"))
    story.append(paragraph(APP_OWNER_LABEL))
    story.append(paragraph(f"Data de geracao: {datetime.now().strftime('%d/%m/%Y %H:%M')}"))
    story.append(Spacer(1, 10))

    story.append(paragraph("1. Projeto", "Heading1"))
    rows = [["Campo", "Valor"]]
    for key, value in project.items():
        rows.append([key, value])
    story.append(table(rows, [4 * cm, 11.7 * cm]))
    story.append(Spacer(1, 10))

    story.append(paragraph("2. Pesos das perspectivas BSC", "Heading1"))
    weight_rows = [["Perspectiva", "Peso", "Peso (%)"]]
    for _, row in weights.iterrows():
        weight_rows.append([row["Perspectiva"], f"{float(row['Peso']):.4f}", f"{float(row['Peso (%)']):.2f}%"])
    story.append(table(weight_rows, [7 * cm, 4 * cm, 4.7 * cm]))
    story.append(Spacer(1, 10))

    if project_weights is not None and not project_weights.empty:
        story.append(paragraph("3. Pesos SAPEVO-BSC dos projetos/KPIs", "Heading1"))
        project_weight_rows = [["Projeto/KPI", "Perspectiva", "Peso local", "Peso final"]]
        for _, row in project_weights.iterrows():
            project_weight_rows.append(
                [
                    row["Projeto/KPI"],
                    row["Perspectiva"],
                    f"{float(row['Peso local SAPEVO-M']):.4f}",
                    f"{float(row['Peso SAPEVO-BSC']):.4f}",
                ]
            )
        story.append(table(project_weight_rows, [5.7 * cm, 4.4 * cm, 2.8 * cm, 2.8 * cm]))
        story.append(Spacer(1, 10))

    story.append(paragraph("4. Ranking de projetos", "Heading1"))
    rank_rows = [["Rank", "Projeto", "Perspectiva", "Natureza", "Classe I/P", "Indice"]]
    for _, row in ranking.iterrows():
        rank_rows.append(
            [
                int(row["Ranking"]),
                row["Projeto"],
                row["Perspectiva"],
                row.get("Natureza", ""),
                row.get("Classificacao I/P", ""),
                f"{float(row['Indice de prioridade']):.6f}",
            ]
        )
    story.append(table(rank_rows, [1.2 * cm, 4.2 * cm, 4.0 * cm, 2.1 * cm, 2.1 * cm, 2.1 * cm]))
    story.append(Spacer(1, 10))

    story.append(paragraph("5. Conclusao consultiva", "Heading1"))
    story.append(paragraph(strategic_conclusion(ranking, weights)))
    doc.build(story)


def pdf_bytes(**kwargs) -> bytes:
    buffer = BytesIO()
    write_pdf_report(buffer, **kwargs)
    return buffer.getvalue()
