"""Public Streamlit app for SAPEVO-BSC strategic prioritization."""

from __future__ import annotations

import base64
import hashlib
import mimetypes
from pathlib import Path

import pandas as pd
import streamlit as st

from sapevobsc.constants import (
    APP_NAME,
    APP_OWNER_LABEL,
    APP_SUBTITLE,
    BSC_PERSPECTIVES,
    IMPACT_PROBABILITY_SCALE,
    PROBABILITY_DISPLAY,
    PROJECT_NATURES,
    RISK_CLASS_COLORS,
    SAPEVO_LABEL_BY_VALUE,
    SAPEVO_SCALE,
)
from sapevobsc.core import (
    OPPORTUNITY_MATRIX,
    THREAT_MATRIX,
    build_pairwise_matrix,
    compute_objective_weights,
    consolidate_fuzzy_project_weights,
    consolidate_sapevo_weights,
    project_label,
    rank_projects,
    strategic_conclusion,
)
from sapevobsc.report import pdf_bytes

PAPER_URL = "https://www.researchgate.net/publication/390109234_SAPEVO-BSC_Multicriteria_Method"


def asset_data_uri(path: Path) -> str:
    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def asset_path(*names: str) -> Path | None:
    base = Path(__file__).resolve().parent
    search_dirs = [base / "assets", Path.cwd() / "assets", Path("assets")]
    for directory in search_dirs:
        for name in names:
            candidate = directory / name
            if candidate.exists():
                return candidate
    return None


def init_state() -> None:
    defaults = {
        "project": {
            "Projeto": "Priorizacao estrategica SAPEVO-BSC",
            "Organizacao": "",
            "Responsavel": "",
            "Horizonte estrategico": "12 meses",
            "Visao do negocio": "",
        },
        "perspectives": BSC_PERSPECTIVES.copy(),
        "evaluators": ["Avaliador 1", "Avaliador 2", "Avaliador 3"],
        "objectives": pd.DataFrame(
            [
                {"Objetivo estrategico": "Aumentar rentabilidade", "Perspectiva": "Financeira", "Peso relativo": 1.0, "Descricao": "Elevar retorno e sustentabilidade financeira"},
                {"Objetivo estrategico": "Melhorar satisfacao do cliente", "Perspectiva": "Clientes", "Peso relativo": 1.0, "Descricao": "Ampliar qualidade percebida e fidelizacao"},
                {"Objetivo estrategico": "Otimizar processos internos", "Perspectiva": "Processos Internos", "Peso relativo": 1.0, "Descricao": "Reduzir gargalos e aumentar eficiencia operacional"},
                {"Objetivo estrategico": "Desenvolver capacidades organizacionais", "Perspectiva": "Aprendizado e Crescimento", "Peso relativo": 1.0, "Descricao": "Fortalecer pessoas, tecnologia e aprendizagem"},
            ]
        ),
        "projects": pd.DataFrame(
            [
                {"Acao/Projeto": "P1", "Natureza": "Oportunidade", "Impacto": "Muito alto", "Probabilidade": "Muito alto"},
                {"Acao/Projeto": "P2", "Natureza": "Ameaca", "Impacto": "Alto", "Probabilidade": "Moderado"},
                {"Acao/Projeto": "P3", "Natureza": "Oportunidade", "Impacto": "Moderado", "Probabilidade": "Alto"},
                {"Acao/Projeto": "P4", "Natureza": "Ameaca", "Impacto": "Baixo", "Probabilidade": "Muito alto"},
            ]
        ),
        "weights": pd.DataFrame(),
        "objective_weights": pd.DataFrame(),
        "fuzzy_alignment": pd.DataFrame(),
        "project_weights": pd.DataFrame(),
        "ranking": pd.DataFrame(),
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def render_cover() -> None:
    st.markdown(
        """
        <style>
        .institutional-logos {
            display: flex;
            align-items: center;
            gap: 22px;
            margin: 0.2rem 0 1rem;
        }
        .institutional-logos img {
            object-fit: contain;
            width: auto;
            display: block;
        }
        .institutional-logos .logo-upe { height: 52px; }
        .institutional-logos .logo-poli { height: 54px; }
        .institutional-logos .logo-ppgec { height: 48px; }
        .institutional-logo-fallback {
            min-width: 86px;
            height: 42px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            border: 1px solid #d1d5db;
            border-radius: 6px;
            color: #374151;
            font-weight: 700;
            font-size: 0.82rem;
            background: #f9fafb;
        }
        .usage-guide {
            margin: 0.2rem 0 1.1rem;
            color: #4b5563;
            font-size: 0.94rem;
        }
        .usage-guide summary {
            cursor: pointer;
            color: #6b7280;
            text-decoration: none;
            width: fit-content;
            list-style: none;
        }
        .usage-guide summary::-webkit-details-marker { display: none; }
        .usage-guide ol { margin: 0.75rem 0 0; padding-left: 1.25rem; line-height: 1.45; }
        .usage-guide li { margin-bottom: 0.42rem; }
        .paper-reference a {
            color: #6b7280;
            text-decoration: none;
            font-size: 0.92rem;
        }
        .paper-reference a:hover { color: #2563eb; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    logo_upe = asset_path("logo_upe.png", "logo_upe.jpg", "logo_upe.jpeg", "logo_upe.jfif")
    logo_poli = asset_path("logo_upe_poli.png", "logo_poli.png")
    logo_ppgec = asset_path("logo_ppgec.png")
    logo_items = []
    if logo_upe:
        logo_items.append(f'<img class="logo-upe" src="{asset_data_uri(logo_upe)}" alt="UPE">')
    else:
        logo_items.append('<span class="institutional-logo-fallback">UPE</span>')
    if logo_poli:
        logo_items.append(f'<img class="logo-poli" src="{asset_data_uri(logo_poli)}" alt="POLI">')
    else:
        logo_items.append('<span class="institutional-logo-fallback">POLI</span>')
    if logo_ppgec:
        logo_items.append(f'<img class="logo-ppgec" src="{asset_data_uri(logo_ppgec)}" alt="PPGEC">')
    else:
        logo_items.append('<span class="institutional-logo-fallback">PPGEC</span>')
    st.markdown(f'<div class="institutional-logos">{"".join(logo_items)}</div>', unsafe_allow_html=True)

    st.title(APP_NAME)
    st.markdown(f"### {APP_SUBTITLE}")
    st.markdown(f"**{APP_OWNER_LABEL}**")
    st.caption("Metodo multicriterio para priorizacao de projetos estrategicos com BSC, SAPEVO-M e matriz Impacto/Probabilidade.")
    st.markdown(
        f'<div class="paper-reference"><a href="{PAPER_URL}" target="_blank">Artigo de referência: SAPEVO-BSC Multicriteria Method</a></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <details class="usage-guide">
            <summary>Como utilizar a plataforma</summary>
            <ol>
                <li>Preencha os dados do projeto, incluindo a visão do negócio.</li>
                <li>Cadastre os objetivos estratégicos, seus pesos relativos e suas perspectivas BSC.</li>
                <li>Cadastre ações/projetos estratégicos.</li>
                <li>Distribua fuzzy o alinhamento de cada ação/projeto entre os objetivos, garantindo soma 1,00.</li>
                <li>Cadastre os avaliadores que participarão da comparação SAPEVO-M.</li>
                <li>Compare as perspectivas par-a-par usando a escala ordinal de -3 a +3.</li>
                <li>Avalie impacto e probabilidade de cada projeto.</li>
                <li>Consolide para obter pesos compostos, ranking e relatório PDF.</li>
            </ol>
        </details>
        """,
        unsafe_allow_html=True,
    )


def project_inputs() -> None:
    st.subheader("Projeto")
    project = st.session_state.project
    col1, col2 = st.columns(2)
    with col1:
        project["Projeto"] = st.text_input("Projeto", project.get("Projeto", ""))
        project["Organizacao"] = st.text_input("Organizacao", project.get("Organizacao", ""))
    with col2:
        project["Responsavel"] = st.text_input("Responsavel", project.get("Responsavel", ""))
        project["Horizonte estrategico"] = st.text_input("Horizonte estrategico", project.get("Horizonte estrategico", "12 meses"))
    project["Visao do negocio"] = st.text_area("Visao do negocio", project.get("Visao do negocio", ""), height=90)
    st.session_state.project = project


def objective_inputs() -> pd.DataFrame:
    st.subheader("Objetivos estrategicos")
    st.caption("Cadastre os objetivos que traduzem a visao do negocio e associe cada um a uma perspectiva BSC.")
    objectives = st.session_state.objectives.copy()
    if "Perspectiva" not in objectives.columns:
        objectives["Perspectiva"] = st.session_state.perspectives[0] if st.session_state.perspectives else ""
    if "Peso relativo" not in objectives.columns:
        objectives["Peso relativo"] = 1.0
    edited = st.data_editor(
        objectives,
        use_container_width=True,
        num_rows="dynamic",
        hide_index=True,
        column_config={
            "Objetivo estrategico": st.column_config.TextColumn("Objetivo estrategico", required=True),
            "Perspectiva": st.column_config.SelectboxColumn("Perspectiva BSC", options=st.session_state.perspectives, required=True),
            "Peso relativo": st.column_config.NumberColumn("Peso relativo", min_value=0.0, step=0.1, format="%.2f"),
            "Descricao": st.column_config.TextColumn("Descricao"),
        },
    )
    edited = edited.dropna(how="all").fillna("")
    st.session_state.objectives = edited
    return edited


def perspective_inputs() -> None:
    st.subheader("Perspectivas BSC")
    st.caption("Use uma perspectiva por linha. O padrão segue o Balanced Scorecard.")
    value = st.text_area("Perspectivas", "\n".join(st.session_state.perspectives), height=130)
    perspectives = [line.strip() for line in value.splitlines() if line.strip()]
    if perspectives:
        st.session_state.perspectives = perspectives


def evaluator_inputs() -> None:
    st.subheader("Avaliadores")
    count = st.number_input("Quantidade de avaliadores", min_value=1, max_value=10, value=len(st.session_state.evaluators), step=1)
    names = []
    cols = st.columns(min(3, int(count)))
    for index in range(int(count)):
        current = st.session_state.evaluators[index] if index < len(st.session_state.evaluators) else f"Avaliador {index + 1}"
        with cols[index % len(cols)]:
            names.append(st.text_input(f"Avaliador {index + 1}", current, key=f"sapevo_eval_{index}"))
    st.session_state.evaluators = names


def comparison_inputs() -> list[pd.DataFrame]:
    st.subheader("Comparacao SAPEVO-M das perspectivas BSC")
    st.caption("Primeiro ciclo SAPEVO-M: define o peso estrategico das perspectivas BSC.")
    perspectives = st.session_state.perspectives
    if len(perspectives) < 2:
        st.warning("Informe ao menos duas perspectivas.")
        return []

    matrices = []
    labels = list(SAPEVO_SCALE)
    reverse_scale = {value: label for label, value in SAPEVO_SCALE.items()}
    for evaluator in st.session_state.evaluators:
        comparisons = {}
        with st.expander(evaluator, expanded=evaluator == st.session_state.evaluators[0]):
            for i, item_i in enumerate(perspectives):
                for item_j in perspectives[i + 1 :]:
                    key = f"sapevo_{evaluator}_{item_i}_{item_j}"
                    label = st.select_slider(
                        f"{item_i} em relacao a {item_j}",
                        options=labels,
                        value=reverse_scale[0],
                        key=key,
                    )
                    comparisons[(item_i, item_j)] = SAPEVO_SCALE[label]
            matrices.append(build_pairwise_matrix(perspectives, comparisons))
    return matrices


def stable_key(*parts: object) -> str:
    raw = "|".join(str(part) for part in parts)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def sync_project_columns(projects: pd.DataFrame) -> pd.DataFrame:
    projects = projects.copy()
    if "Acao/Projeto" not in projects.columns and "Projeto" in projects.columns:
        projects["Acao/Projeto"] = projects["Projeto"]
    projects["Projeto"] = projects.get("Acao/Projeto", "")
    return projects


def project_table_inputs() -> pd.DataFrame:
    st.subheader("Acoes e projetos estrategicos")
    st.caption("Cadastre as acoes/projetos. O alinhamento aos objetivos sera definido na particao fuzzy da etapa seguinte.")
    st.session_state.projects = sync_project_columns(st.session_state.projects)
    if "Natureza" not in st.session_state.projects.columns:
        st.session_state.projects["Natureza"] = "Oportunidade"
    edited = st.data_editor(
        st.session_state.projects[
            ["Acao/Projeto", "Natureza", "Impacto", "Probabilidade"]
        ],
        use_container_width=True,
        num_rows="dynamic",
        hide_index=True,
        column_config={
            "Acao/Projeto": st.column_config.TextColumn("Acao/Projeto", required=True),
            "Natureza": st.column_config.SelectboxColumn("Natureza", options=PROJECT_NATURES),
            "Impacto": st.column_config.SelectboxColumn("Impacto", options=list(IMPACT_PROBABILITY_SCALE)),
            "Probabilidade": st.column_config.SelectboxColumn("Probabilidade", options=list(IMPACT_PROBABILITY_SCALE)),
        },
    )
    edited = sync_project_columns(edited.dropna(how="all").fillna(""))
    st.session_state.projects = edited
    return edited


def fuzzy_alignment_inputs(projects: pd.DataFrame, objectives: pd.DataFrame) -> pd.DataFrame:
    st.subheader("Particao fuzzy entre objetivos estrategicos")
    st.caption("Distribua a contribuicao de cada acao/projeto entre os objetivos. A soma de cada linha deve ser 1,00.")

    if projects.empty or objectives.empty:
        st.warning("Cadastre acoes/projetos e objetivos estrategicos antes de preencher a particao fuzzy.")
        return pd.DataFrame()

    project_names = [str(item).strip() for item in projects["Acao/Projeto"].astype(str).tolist() if str(item).strip()]
    objective_names = [str(item).strip() for item in objectives["Objetivo estrategico"].astype(str).tolist() if str(item).strip()]
    if not project_names or not objective_names:
        return pd.DataFrame()

    previous = st.session_state.fuzzy_alignment.copy() if not st.session_state.fuzzy_alignment.empty else pd.DataFrame()
    previous_map = {}
    if not previous.empty and "Acao/Projeto" in previous.columns:
        for _, row in previous.iterrows():
            previous_map[str(row.get("Acao/Projeto", ""))] = row

    rows = []
    for project in project_names:
        row = {"Acao/Projeto": project}
        previous_row = previous_map.get(project)
        for index, objective in enumerate(objective_names):
            if previous_row is not None and objective in previous_row:
                value = previous_row.get(objective, 0.0)
            else:
                value = 1.0 if index == 0 else 0.0
            row[objective] = float(value or 0.0)
        rows.append(row)

    alignment = pd.DataFrame(rows)
    edited = st.data_editor(
        alignment,
        use_container_width=True,
        hide_index=True,
        disabled=["Acao/Projeto"],
        column_config={
            "Acao/Projeto": st.column_config.TextColumn("Acao/Projeto"),
            **{
                objective: st.column_config.NumberColumn(objective, min_value=0.0, max_value=1.0, step=0.05, format="%.2f")
                for objective in objective_names
            },
        },
    )
    edited[objective_names] = edited[objective_names].apply(pd.to_numeric, errors="coerce").fillna(0.0).clip(0.0, 1.0)
    edited["Soma"] = edited[objective_names].sum(axis=1).round(4)
    invalid = edited[(edited["Soma"] - 1.0).abs() > 0.001]
    if invalid.empty:
        st.success("Particao fuzzy valida: todas as acoes/projetos somam 1,00.")
    else:
        st.warning("Ajuste a particao fuzzy: cada acao/projeto deve somar 1,00. O calculo normaliza automaticamente, mas a entrada ideal e fechar 100%.")
        st.dataframe(edited[["Acao/Projeto", "Soma"]], use_container_width=True, hide_index=True)

    st.session_state.fuzzy_alignment = edited.drop(columns=["Soma"])
    return st.session_state.fuzzy_alignment


def project_comparison_inputs(projects: pd.DataFrame) -> dict[str, list[pd.DataFrame]]:
    st.subheader("Comparacao SAPEVO-M dos projetos/KPIs")
    st.caption("Segundo ciclo SAPEVO-M: compara os projetos ou KPIs dentro de cada perspectiva BSC.")
    if projects.empty:
        st.warning("Cadastre projetos antes de comparar projetos/KPIs.")
        return {}

    labels_by_perspective = {}
    for perspective, group in projects.groupby("Perspectiva", dropna=False):
        labels = [project_label(row) or f"Item {index + 1}" for index, row in group.reset_index(drop=True).iterrows()]
        if labels:
            labels_by_perspective[str(perspective)] = labels

    matrices_by_perspective: dict[str, list[pd.DataFrame]] = {}
    labels = list(SAPEVO_SCALE)
    reverse_scale = {value: label for label, value in SAPEVO_SCALE.items()}

    for perspective in st.session_state.perspectives:
        items = labels_by_perspective.get(perspective, [])
        if not items:
            continue
        with st.expander(f"{perspective}: {len(items)} projeto(s)/KPI(s)", expanded=False):
            if len(items) == 1:
                st.info("Ha apenas um projeto/KPI nesta perspectiva; o peso local sera 100%.")
                matrices_by_perspective[perspective] = []
                continue

            evaluator_matrices = []
            for evaluator in st.session_state.evaluators:
                st.markdown(f"**{evaluator}**")
                comparisons = {}
                for i, item_i in enumerate(items):
                    for item_j in items[i + 1 :]:
                        key = f"project_sapevo_{stable_key(evaluator, perspective, item_i, item_j)}"
                        label = st.select_slider(
                            f"{item_i} em relacao a {item_j}",
                            options=labels,
                            value=reverse_scale[0],
                            key=key,
                        )
                        comparisons[(item_i, item_j)] = SAPEVO_SCALE[label]
                evaluator_matrices.append(build_pairwise_matrix(items, comparisons))
            matrices_by_perspective[perspective] = evaluator_matrices

    return matrices_by_perspective


def render_impact_probability_matrix() -> None:
    st.subheader("Matriz Impacto/Probabilidade")
    st.caption("Classificacao operacional usada para interpretar ameacas e oportunidades.")
    probability_order = ["Muito alto", "Alto", "Moderado", "Baixo", "Muito baixo"]
    threat_impacts = ["Muito baixo", "Baixo", "Moderado", "Alto", "Muito alto"]
    opportunity_impacts = ["Muito alto", "Alto", "Moderado", "Baixo", "Muito baixo"]

    header_cells = (
        '<th class="ip-side"></th>'
        '<th class="ip-threat" colspan="5">Ameacas</th>'
        '<th class="ip-opportunity" colspan="5">Oportunidades</th>'
    )
    rows = [f"<tr>{header_cells}</tr>"]
    for probability in probability_order:
        cells = [f'<th class="ip-prob">{PROBABILITY_DISPLAY[probability]}</th>']
        for impact in threat_impacts:
            label = THREAT_MATRIX[probability][impact]
            cells.append(f'<td style="background:{RISK_CLASS_COLORS[label]}">{label}</td>')
        for impact in opportunity_impacts:
            label = OPPORTUNITY_MATRIX[probability][impact]
            cells.append(f'<td style="background:{RISK_CLASS_COLORS[label]}">{label}</td>')
        rows.append(f"<tr>{''.join(cells)}</tr>")

    impact_row = ['<th class="ip-side"></th>']
    for impact in threat_impacts + opportunity_impacts:
        impact_row.append(f"<th>{impact}</th>")
    rows.append(f"<tr>{''.join(impact_row)}</tr>")

    st.markdown(
        f"""
        <style>
        .ip-matrix-wrap {{
            overflow-x: auto;
            margin: 0.25rem 0 1.25rem;
        }}
        .ip-matrix {{
            border-collapse: collapse;
            min-width: 980px;
            text-align: center;
            font-size: 0.84rem;
        }}
        .ip-matrix th, .ip-matrix td {{
            border: 1px solid #111827;
            padding: 12px 10px;
            min-width: 84px;
        }}
        .ip-matrix .ip-threat {{
            background: #ff4d57;
            color: #ffffff;
            font-weight: 700;
        }}
        .ip-matrix .ip-opportunity {{
            background: #0b62a4;
            color: #ffffff;
            font-weight: 700;
        }}
        .ip-matrix .ip-prob {{
            background: #f8fafc;
            font-weight: 700;
        }}
        .ip-matrix-caption {{
            background: #dbeafe;
            color: #111827;
            font-weight: 700;
            text-align: center;
            padding: 8px;
            min-width: 980px;
        }}
        </style>
        <div class="ip-matrix-wrap">
            <table class="ip-matrix">{''.join(rows)}</table>
            <div class="ip-matrix-caption">Impacto</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def radar_svg(weights: pd.DataFrame) -> str:
    if weights.empty:
        return ""
    size = 320
    center = size / 2
    radius = 115
    rows = weights.sort_values("Perspectiva").reset_index(drop=True)
    max_weight = max(float(rows["Peso"].max()), 0.0001)
    points = []
    axes = []
    labels = []
    import math

    for idx, row in rows.iterrows():
        angle = -math.pi / 2 + 2 * math.pi * idx / len(rows)
        outer_x = center + radius * math.cos(angle)
        outer_y = center + radius * math.sin(angle)
        value_radius = radius * float(row["Peso"]) / max_weight
        x = center + value_radius * math.cos(angle)
        y = center + value_radius * math.sin(angle)
        points.append(f"{x:.1f},{y:.1f}")
        axes.append(f'<line x1="{center}" y1="{center}" x2="{outer_x:.1f}" y2="{outer_y:.1f}" stroke="#cbd5e1" stroke-width="1" />')
        labels.append(f'<text x="{outer_x:.1f}" y="{outer_y:.1f}" font-size="10" fill="#374151">{row["Perspectiva"]}</text>')

    return f"""
    <svg viewBox="0 0 {size} {size}" width="100%" height="330" role="img">
        <circle cx="{center}" cy="{center}" r="{radius}" fill="none" stroke="#e5e7eb" />
        {''.join(axes)}
        <polygon points="{' '.join(points)}" fill="#60a5fa55" stroke="#2563eb" stroke-width="2" />
        {''.join(labels)}
    </svg>
    """


def main() -> None:
    st.set_page_config(page_title=APP_NAME, layout="wide")
    init_state()
    render_cover()

    project_inputs()
    perspective_inputs()
    objectives = objective_inputs()
    projects = project_table_inputs()
    fuzzy_alignment = fuzzy_alignment_inputs(projects, objectives)
    evaluator_inputs()
    perspective_matrices = comparison_inputs()
    render_impact_probability_matrix()

    if st.button("Consolidar SAPEVO-BSC", type="primary"):
        weight_result = consolidate_sapevo_weights(perspective_matrices)
        objective_weights = compute_objective_weights(objectives, weight_result.weights)
        project_weights = consolidate_fuzzy_project_weights(projects, objective_weights, fuzzy_alignment)
        ranking = rank_projects(projects, weight_result.weights, project_weights)
        st.session_state.weights = weight_result.weights
        st.session_state.objective_weights = objective_weights
        st.session_state.project_weights = project_weights
        st.session_state.ranking = ranking
        st.success("Consolidacao realizada.")

    weights = st.session_state.weights
    objective_weights = st.session_state.objective_weights
    project_weights = st.session_state.project_weights
    ranking = st.session_state.ranking
    if not weights.empty:
        st.divider()
        st.subheader("Pesos consolidados das perspectivas")
        col1, col2 = st.columns([1.1, 1])
        with col1:
            st.dataframe(weights, use_container_width=True, hide_index=True)
        with col2:
            st.markdown(radar_svg(weights), unsafe_allow_html=True)

    if not objective_weights.empty:
        st.subheader("Pesos globais dos objetivos estrategicos")
        st.caption("Peso objetivo = peso da perspectiva BSC x peso relativo normalizado do objetivo dentro da perspectiva.")
        st.dataframe(objective_weights, use_container_width=True, hide_index=True)

    if not project_weights.empty:
        st.subheader("Pesos SAPEVO-BSC das acoes/projetos")
        st.caption("Peso final = soma das pertinencias fuzzy da acao/projeto ponderadas pelos pesos globais dos objetivos.")
        st.dataframe(project_weights, use_container_width=True, hide_index=True)

    if not ranking.empty:
        st.subheader("Ranking dos projetos estrategicos")
        st.dataframe(ranking, use_container_width=True, hide_index=True)
        st.info(strategic_conclusion(ranking, weights))

        report = pdf_bytes(
            project=st.session_state.project,
            objectives=st.session_state.objectives,
            objective_weights=objective_weights,
            weights=weights,
            project_weights=project_weights,
            ranking=ranking,
        )
        st.download_button(
            "Baixar relatorio PDF",
            data=report,
            file_name="relatorio_sapevo_bsc.pdf",
            mime="application/pdf",
            type="primary",
        )


if __name__ == "__main__":
    main()
