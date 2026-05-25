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
    PROJECT_NATURES,
    RISK_CLASS_COLORS,
    SAPEVO_SCALE,
)
from sapevobsc.core import (
    build_pairwise_matrix,
    calculate_project_weights_from_objectives,
    consolidate_objective_scores_by_perspective,
    consolidate_sapevo_weights,
    impact_probability_classification,
    impact_probability_index,
    rank_projects,
    strategic_conclusion,
)
from sapevobsc.report import pdf_bytes

PAPER_URL = "https://www.researchgate.net/publication/390109234_SAPEVO-BSC_Multicriteria_Method"
ORCID_URL = "https://orcid.org/0000-0002-6138-7451"
LINKEDIN_URL = "https://linkedin.com/in/daviddeoliveiracosta"


def asset_data_uri(path: Path) -> str:
    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def asset_path(*names: str) -> Path | None:
    base = Path(__file__).resolve().parent
    search_dirs = [base / "assets", Path.cwd() / "assets", Path("assets"), base, Path.cwd()]
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
                {"Objetivo estrategico": "KPI 1"},
                {"Objetivo estrategico": "KPI 2"},
                {"Objetivo estrategico": "KPI 3"},
                {"Objetivo estrategico": "KPI 4"},
            ]
        ),
        "projects": pd.DataFrame(
            [
                {"Acao/Projeto": "P1", "Objetivo estrategico": "KPI 1", "Natureza": "Oportunidade", "Impacto": "Muito alto", "Probabilidade": "Muito alto"},
                {"Acao/Projeto": "P2", "Objetivo estrategico": "KPI 2", "Natureza": "Ameaca", "Impacto": "Alto", "Probabilidade": "Moderado"},
                {"Acao/Projeto": "P3", "Objetivo estrategico": "KPI 3", "Natureza": "Oportunidade", "Impacto": "Moderado", "Probabilidade": "Alto"},
                {"Acao/Projeto": "P4", "Objetivo estrategico": "KPI 4", "Natureza": "Ameaca", "Impacto": "Baixo", "Probabilidade": "Muito alto"},
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
        .author-links {
            display: flex;
            align-items: center;
            gap: 18px;
            margin: 0.45rem 0 0.85rem;
            color: #6b7280;
            font-size: 0.92rem;
        }
        .author-links a {
            display: inline-flex;
            align-items: center;
            gap: 7px;
            color: #6b7280;
            text-decoration: none;
        }
        .author-links a:hover { color: #2563eb; }
        .author-links img {
            width: 18px;
            height: 18px;
            object-fit: contain;
            display: inline-block;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    logo_upe = asset_path(
        "logo_upe.png",
        "logo_upe.jpg",
        "logo_upe.jpeg",
        "logo_upe.jfif",
        "download (1).jfif",
    )
    logo_poli = asset_path(
        "logo_upe_poli.png",
        "logo_poli.png",
        "download (2).png",
    )
    logo_ppgec = asset_path(
        "logo_ppgec.png",
        "download (1).png",
    )
    logo_orcid = asset_path("logo_orcid.svg", "orcid.svg", "logo_orcid.png")
    logo_linkedin = asset_path("logo_linkedin.svg", "linkedin.svg", "logo_linkedin.png")
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
    orcid_icon = f'<img src="{asset_data_uri(logo_orcid)}" alt="ORCID">' if logo_orcid else ""
    linkedin_icon = f'<img src="{asset_data_uri(logo_linkedin)}" alt="LinkedIn">' if logo_linkedin else ""
    st.markdown(
        f"""
        <div class="author-links">
            <a href="{ORCID_URL}" target="_blank">{orcid_icon}<span>Perfil academico</span></a>
            <a href="{LINKEDIN_URL}" target="_blank">{linkedin_icon}<span>Perfil profissional</span></a>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption("Metodo multicriterio para priorizacao de projetos e acoes estrategicas com enfase em alinhamento estrategico.")
    st.markdown(
        f'<div class="paper-reference"><a href="{PAPER_URL}" target="_blank">Artigo de referência: SAPEVO-BSC Multicriteria Method</a></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <details class="usage-guide">
            <summary>Como utilizar a plataforma</summary>
            <ol>
                <li>Registre o contexto, a visao do negocio e o horizonte estrategico.</li>
                <li>Cadastre os objetivos/indicadores estrategicos que serao tratados como alternativas.</li>
                <li>Cadastre os decisores/avaliadores que participarao da comparacao SAPEVO-M.</li>
                <li>Compare as perspectivas par-a-par usando a escala ordinal de -3 a +3.</li>
                <li>Para cada perspectiva BSC, compare os objetivos/indicadores entre si.</li>
                <li>Gere a matriz global objetivo x perspectiva e o ranking prioritario dos objetivos.</li>
                <li>Cadastre cada acao/projeto, vincule ao objetivo/indicador e avalie impacto/probabilidade com classe I/P calculada automaticamente.</li>
                <li>Consolide a matriz global, o ranking dos objetivos e o ranking final dos projetos.</li>
            </ol>
        </details>
        """,
        unsafe_allow_html=True,
    )


def project_inputs() -> None:
    st.subheader("1. Visao do negocio e contexto")
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
    st.subheader("2. Objetivos/indicadores estrategicos")
    st.caption("Cadastre os objetivos/indicadores que serao tratados como alternativas na matriz decisoria.")
    objectives = st.session_state.objectives.copy()
    objective_count = st.number_input(
        "Quantidade de objetivos estrategicos",
        min_value=1,
        value=max(1, len(objectives)),
        step=1,
    )
    objectives = objectives.reset_index(drop=True)
    desired_count = int(objective_count)
    if len(objectives) < desired_count:
        for index in range(len(objectives), desired_count):
            objectives.loc[index, "Objetivo estrategico"] = f"Objetivo {index + 1}"
    elif len(objectives) > desired_count:
        objectives = objectives.iloc[:desired_count].copy()

    header = st.columns([1])
    header[0].markdown("**Objetivo estrategico**")

    rows = []
    for index, row in objectives.iterrows():
        current_objective = str(row.get("Objetivo estrategico", "") or f"Objetivo {index + 1}")

        col1 = st.columns([1])[0]
        objective = col1.text_input(
            f"Objetivo estrategico {index + 1}",
            value=current_objective,
            label_visibility="collapsed",
            key=f"objective_name_{index}",
        )
        rows.append(
            {
                "Objetivo estrategico": objective,
            }
        )

    edited = pd.DataFrame(rows).dropna(how="all").fillna("").reset_index(drop=True)
    st.session_state.objectives = edited
    return edited


def perspective_inputs() -> None:
    st.session_state.perspectives = BSC_PERSPECTIVES.copy()


def evaluator_inputs() -> None:
    st.subheader("3. Decisores/avaliadores")
    count = st.number_input("Quantidade de avaliadores", min_value=1, max_value=10, value=len(st.session_state.evaluators), step=1)
    names = []
    cols = st.columns(min(3, int(count)))
    for index in range(int(count)):
        current = st.session_state.evaluators[index] if index < len(st.session_state.evaluators) else f"Avaliador {index + 1}"
        with cols[index % len(cols)]:
            names.append(st.text_input(f"Avaliador {index + 1}", current, key=f"sapevo_eval_{index}"))
    st.session_state.evaluators = names


def comparison_inputs() -> list[pd.DataFrame]:
    st.subheader("4. Comparacao SAPEVO-M das perspectivas BSC")
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
    if "Objetivo estrategico" not in projects.columns and "Objetivo/KPI" in projects.columns:
        projects["Objetivo estrategico"] = projects["Objetivo/KPI"]
    if "Objetivo estrategico" not in projects.columns:
        objectives = st.session_state.get("objectives", pd.DataFrame())
        first_objective = ""
        if isinstance(objectives, pd.DataFrame) and not objectives.empty:
            first_objective = str(objectives.iloc[0].get("Objetivo estrategico", ""))
        projects["Objetivo estrategico"] = first_objective
    if "Perspectiva" not in projects.columns:
        projects["Perspectiva"] = ""
    projects["Projeto"] = projects.get("Acao/Projeto", "")
    projects["Objetivo/KPI"] = projects.get("Objetivo estrategico", "")
    return projects


def project_objective_link_inputs(projects: pd.DataFrame, objectives: pd.DataFrame) -> pd.DataFrame:
    st.subheader("7. Acoes/projetos, objetivos e avaliacao Impacto/Probabilidade")
    st.caption("Use os pesos consolidados dos objetivos, associe cada acao/projeto ao objetivo/indicador e avalie natureza, impacto e probabilidade.")
    if objectives.empty:
        st.warning("Cadastre objetivos/indicadores antes de realizar o vinculo.")
        return projects

    objective_options = [
        str(item).strip()
        for item in objectives["Objetivo estrategico"].astype(str).tolist()
        if str(item).strip()
    ]
    if not objective_options:
        return projects

    if projects.empty:
        projects = pd.DataFrame(columns=["Acao/Projeto", "Objetivo estrategico", "Natureza", "Impacto", "Probabilidade"])
    linked = sync_project_columns(projects).reset_index(drop=True)
    if "Natureza" not in linked.columns:
        linked["Natureza"] = "Oportunidade"
    project_count = st.number_input(
        "Quantidade de acoes/projetos",
        min_value=1,
        max_value=100,
        value=max(1, len(linked)),
        step=1,
    )
    desired_count = int(project_count)
    if len(linked) < desired_count:
        for index in range(len(linked), desired_count):
            linked.loc[index, "Acao/Projeto"] = f"P{index + 1}"
            linked.loc[index, "Objetivo estrategico"] = objective_options[0]
            linked.loc[index, "Perspectiva"] = ""
            linked.loc[index, "Natureza"] = "Oportunidade"
            linked.loc[index, "Impacto"] = "Moderado"
            linked.loc[index, "Probabilidade"] = "Moderado"
    elif len(linked) > desired_count:
        linked = linked.iloc[:desired_count].copy()
    linked = sync_project_columns(linked)
    linked["Objetivo estrategico"] = linked["Objetivo estrategico"].where(
        linked["Objetivo estrategico"].isin(objective_options),
        objective_options[0],
    )
    header = st.columns([1.1, 1.7, 1.0, 1.0, 1.0, 0.85, 0.75])
    header[0].markdown("**Acao/Projeto**")
    header[1].markdown("**Objetivo/indicador estrategico**")
    header[2].markdown("**Natureza**")
    header[3].markdown("**Impacto**")
    header[4].markdown("**Probabilidade**")
    header[5].markdown("**Classe I/P**")
    header[6].markdown("**Indice I/P**")

    rows = []
    impact_options = list(IMPACT_PROBABILITY_SCALE)
    for index, row in linked.iterrows():
        project_value = str(row.get("Acao/Projeto", "") or f"P{index + 1}")
        objective_value = str(row.get("Objetivo estrategico", objective_options[0]))
        nature_value = str(row.get("Natureza", "Oportunidade"))
        impact_value = str(row.get("Impacto", "Moderado"))
        probability_value = str(row.get("Probabilidade", "Moderado"))
        if objective_value not in objective_options:
            objective_value = objective_options[0]
        if nature_value not in PROJECT_NATURES:
            nature_value = PROJECT_NATURES[0]
        if impact_value not in impact_options:
            impact_value = "Moderado"
        if probability_value not in impact_options:
            probability_value = "Moderado"

        col1, col2, col3, col4, col5, col6, col7 = st.columns([1.1, 1.7, 1.0, 1.0, 1.0, 0.85, 0.75])
        project = col1.text_input(
            f"Acao/Projeto {index + 1}",
            value=project_value,
            label_visibility="collapsed",
            key=f"project_name_{index}",
        )
        objective = col2.selectbox(
            f"Objetivo/indicador {index + 1}",
            options=objective_options,
            index=objective_options.index(objective_value),
            label_visibility="collapsed",
            key=f"project_objective_{index}",
        )
        nature = col3.selectbox(
            f"Natureza {index + 1}",
            options=PROJECT_NATURES,
            index=PROJECT_NATURES.index(nature_value),
            label_visibility="collapsed",
            key=f"project_nature_{index}",
        )
        impact = col4.selectbox(
            f"Impacto {index + 1}",
            options=impact_options,
            index=impact_options.index(impact_value),
            label_visibility="collapsed",
            key=f"project_impact_{index}",
        )
        probability = col5.selectbox(
            f"Probabilidade {index + 1}",
            options=impact_options,
            index=impact_options.index(probability_value),
            label_visibility="collapsed",
            key=f"project_probability_{index}",
        )
        classification = impact_probability_classification(nature, impact, probability)
        ip_index = round(impact_probability_index(nature, impact, probability), 4)
        color = RISK_CLASS_COLORS.get(classification, "#e5e7eb")
        col6.markdown(
            f"""
            <div style="
                background:{color};
                color:#111827;
                min-height:38px;
                border-radius:6px;
                display:flex;
                align-items:center;
                justify-content:center;
                font-weight:700;
                border:1px solid rgba(17,24,39,.12);
            ">{classification}</div>
            """,
            unsafe_allow_html=True,
        )
        col7.markdown(
            f"""
            <div style="
                min-height:38px;
                border-radius:6px;
                display:flex;
                align-items:center;
                justify-content:center;
                background:#f8fafc;
                border:1px solid #e5e7eb;
            ">{ip_index:.4f}</div>
            """,
            unsafe_allow_html=True,
        )
        rows.append(
            {
                "Acao/Projeto": project,
                "Objetivo estrategico": objective,
                "Objetivo/KPI": objective,
                "Natureza": nature,
                "Impacto": impact,
                "Probabilidade": probability,
                "Classe I/P": classification,
                "Indice I/P": ip_index,
            }
        )

    linked = pd.DataFrame(rows).dropna(how="all").fillna("").reset_index(drop=True)
    objective_weight_map = {}
    objective_weights = st.session_state.get("objective_weights", pd.DataFrame())
    if (
        isinstance(objective_weights, pd.DataFrame)
        and not objective_weights.empty
        and "Perspectiva dominante" in objective_weights.columns
    ):
        objective_weight_map = dict(zip(objective_weights["Objetivo estrategico"], objective_weights["Perspectiva dominante"]))
    linked["Perspectiva"] = linked["Objetivo estrategico"].map(objective_weight_map).fillna("")
    st.session_state.projects = linked
    return linked


def objective_comparison_inputs(objectives: pd.DataFrame) -> dict[str, list[pd.DataFrame]]:
    st.subheader("5. Comparacao SAPEVO-M dos objetivos/indicadores por perspectiva")
    st.caption("Para cada perspectiva BSC, cada decisor compara os objetivos/indicadores entre si.")
    if objectives.empty:
        st.warning("Cadastre objetivos estrategicos antes de comparar objetivos/KPIs.")
        return {}

    items = [
        str(row.get("Objetivo estrategico", "")).strip() or f"Objetivo {index + 1}"
        for index, row in objectives.reset_index(drop=True).iterrows()
    ]

    matrices_by_perspective: dict[str, list[pd.DataFrame]] = {}
    labels = list(SAPEVO_SCALE)
    reverse_scale = {value: label for label, value in SAPEVO_SCALE.items()}

    for perspective in st.session_state.perspectives:
        if not items:
            continue
        with st.expander(f"{perspective}: comparar {len(items)} objetivo(s)/indicador(es)", expanded=False):
            if len(items) == 1:
                st.info("Ha apenas um objetivo/indicador; a pontuacao local sera 100%.")
                matrices_by_perspective[perspective] = []
                continue

            evaluator_matrices = []
            for evaluator in st.session_state.evaluators:
                st.markdown(f"**{evaluator}**")
                comparisons = {}
                for i, item_i in enumerate(items):
                    for item_j in items[i + 1 :]:
                        key = f"objective_sapevo_{stable_key(evaluator, perspective, item_i, item_j)}"
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


def objective_weight_consolidation_inputs(
    objectives: pd.DataFrame,
    perspective_matrices: list[pd.DataFrame],
    objective_matrices: dict[str, list[pd.DataFrame]],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    st.subheader("6. Consolidacao dos pesos dos objetivos/indicadores")
    st.caption("Gere a matriz global objetivo x perspectiva antes de vincular projetos e avaliar impacto/probabilidade.")

    if st.button("Consolidar pesos dos objetivos", type="primary"):
        weight_result = consolidate_sapevo_weights(perspective_matrices)
        objective_result = consolidate_objective_scores_by_perspective(objectives, weight_result.weights, objective_matrices)
        st.session_state.weights = weight_result.weights
        st.session_state.objective_weights = objective_result.project_weights
        st.success("Pesos dos objetivos/indicadores consolidados.")

    weights = st.session_state.weights
    objective_weights = st.session_state.objective_weights
    if not weights.empty:
        st.markdown("#### Pesos das perspectivas BSC")
        col1, col2 = st.columns([1.1, 1])
        with col1:
            st.dataframe(weights, use_container_width=True, hide_index=True)
        with col2:
            st.markdown(radar_svg(weights), unsafe_allow_html=True)

    if not objective_weights.empty:
        st.markdown("#### Matriz global objetivo x perspectiva e ranking dos objetivos")
        st.caption("Peso final do objetivo/KPI = soma da pontuacao do objetivo em cada perspectiva multiplicada pelo peso da perspectiva.")
        st.dataframe(objective_weights, use_container_width=True, hide_index=True)
    else:
        st.info("Consolide os pesos dos objetivos para usar esses valores na etapa de projetos.")

    return weights, objective_weights


def main() -> None:
    st.set_page_config(page_title=APP_NAME, layout="wide")
    init_state()
    render_cover()

    project_inputs()
    perspective_inputs()
    objectives = objective_inputs()
    evaluator_inputs()
    perspective_matrices = comparison_inputs()
    objective_matrices = objective_comparison_inputs(objectives)
    weights, objective_weights = objective_weight_consolidation_inputs(objectives, perspective_matrices, objective_matrices)
    if weights.empty or objective_weights.empty:
        return

    projects = project_objective_link_inputs(st.session_state.projects, objectives)

    st.subheader("8. Ranking dos projetos estrategicos")
    if st.button("Consolidar ranking dos projetos", type="primary"):
        project_weights = calculate_project_weights_from_objectives(projects, objective_weights)
        ranking = rank_projects(projects, weights, project_weights)
        st.session_state.project_weights = project_weights
        st.session_state.ranking = ranking
        st.success("Ranking dos projetos consolidado.")

    project_weights = st.session_state.project_weights
    ranking = st.session_state.ranking
    if not project_weights.empty:
        st.subheader("Pesos SAPEVO-BSC das acoes/projetos")
        st.caption("Cada acao/projeto herda o peso SAPEVO-BSC do objetivo/KPI ao qual foi vinculada.")
        st.dataframe(project_weights, use_container_width=True, hide_index=True)

    if not ranking.empty:
        st.subheader("Ranking dos projetos estrategicos")
        st.dataframe(ranking, use_container_width=True, hide_index=True)
        st.info(strategic_conclusion(ranking, weights))

        report = pdf_bytes(
            project=st.session_state.project,
            projects=st.session_state.projects,
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
