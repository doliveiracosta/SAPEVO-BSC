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
    projects: pd.DataFrame | None = None,
    objectives: pd.DataFrame | None = None,
    objective_weights: pd.DataFrame | None = None,
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

    if projects is not None and not projects.empty:
        story.append(paragraph("2. Acoes/projetos identificados", "Heading1"))
        project_rows = [["Acao/Projeto", "Objetivo/KPI", "Natureza", "Impacto", "Probabilidade", "Classe I/P"]]
        for _, row in projects.iterrows():
            project_rows.append(
                [
                    row.get("Acao/Projeto", row.get("Projeto", "")),
                    row.get("Objetivo estrategico", row.get("Objetivo/KPI", "")),
                    row.get("Natureza", ""),
                    row.get("Impacto", ""),
                    row.get("Probabilidade", ""),
                    row.get("Classe I/P", ""),
                ]
            )
        story.append(table(project_rows, [2.5 * cm, 4.2 * cm, 2.0 * cm, 2.3 * cm, 2.3 * cm, 2.4 * cm]))
        story.append(Spacer(1, 10))

    if objectives is not None and not objectives.empty:
        story.append(paragraph("3. Objetivos/indicadores estrategicos", "Heading1"))
        objective_rows = [["Objetivo/indicador estrategico"]]
        for _, row in objectives.iterrows():
            objective_rows.append(
                [
                    row.get("Objetivo estrategico", ""),
                ]
            )
        story.append(table(objective_rows, [15.7 * cm]))
        story.append(Spacer(1, 10))

    story.append(paragraph("4. Pesos das perspectivas BSC", "Heading1"))
    weight_rows = [["Perspectiva", "Peso", "Peso (%)"]]
    for _, row in weights.iterrows():
        weight_rows.append([row["Perspectiva"], f"{float(row['Peso']):.4f}", f"{float(row['Peso (%)']):.2f}%"])
    story.append(table(weight_rows, [7 * cm, 4 * cm, 4.7 * cm]))
    story.append(Spacer(1, 10))

    if objective_weights is not None and not objective_weights.empty:
        story.append(paragraph("5. Matriz global e pesos dos objetivos/KPIs", "Heading1"))
        perspective_columns = [
            column
            for column in objective_weights.columns
            if column not in {
                "Objetivo estrategico",
                "Objetivo/KPI",
                "Perspectiva dominante",
                "Peso perspectiva",
                "Peso local SAPEVO-M",
                "Peso local objetivo",
                "Peso SAPEVO-BSC",
                "Peso objetivo",
                "Peso SAPEVO-BSC (%)",
                "Peso objetivo (%)",
                "Ranking objetivo",
                "Descricao",
            }
        ]
        objective_weight_rows = [["Objetivo/KPI", *perspective_columns, "Peso final", "Rank"]]
        for _, row in objective_weights.iterrows():
            objective_weight_rows.append(
                [
                    row.get("Objetivo estrategico", ""),
                    *[f"{float(row.get(column, 0.0)):.4f}" for column in perspective_columns],
                    f"{float(row.get('Peso SAPEVO-BSC', row.get('Peso objetivo', 0.0))):.4f}",
                    row.get("Ranking objetivo", ""),
                ]
            )
        dynamic_width = 15.7 * cm / max(1, len(objective_weight_rows[0]))
        story.append(table(objective_weight_rows, [dynamic_width] * len(objective_weight_rows[0])))
        story.append(Spacer(1, 10))

    if project_weights is not None and not project_weights.empty:
        story.append(paragraph("6. Pesos SAPEVO-BSC das acoes/projetos", "Heading1"))
        project_weight_rows = [["Acao/Projeto", "Objetivo/KPI vinculado", "Perspectiva", "Peso final"]]
        for _, row in project_weights.iterrows():
            project_weight_rows.append(
                [
                    row["Projeto"],
                    row["Objetivo/KPI"],
                    row["Perspectiva"],
                    f"{float(row['Peso SAPEVO-BSC']):.4f}",
                ]
            )
        story.append(table(project_weight_rows, [3.2 * cm, 5.8 * cm, 4.0 * cm, 2.7 * cm]))
        story.append(Spacer(1, 10))

    story.append(paragraph("7. Ranking de projetos", "Heading1"))
    rank_rows = [["Rank", "Acao/Projeto", "Objetivo", "Natureza", "Classe I/P", "Indice I/P", "Indice"]]
    for _, row in ranking.iterrows():
        rank_rows.append(
            [
                int(row["Ranking"]),
                row["Projeto"],
                row.get("Objetivo/KPI", ""),
                row.get("Natureza", ""),
                row.get("Classificacao I/P", ""),
                f"{float(row.get('Indice I/P', 0.0)):.4f}",
                f"{float(row['Indice de prioridade']):.6f}",
            ]
        )
    story.append(table(rank_rows, [1.0 * cm, 2.8 * cm, 3.8 * cm, 1.9 * cm, 1.8 * cm, 1.7 * cm, 2.1 * cm]))
    story.append(Spacer(1, 10))

    story.append(paragraph("8. Conclusao consultiva", "Heading1"))
    story.append(paragraph(strategic_conclusion(ranking, weights)))
    doc.build(story)


def pdf_bytes(**kwargs) -> bytes:
    buffer = BytesIO()
    write_pdf_report(buffer, **kwargs)
    return buffer.getvalue()
