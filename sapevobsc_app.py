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
        st.session_state.perspective_evaluator_vectors = weight_result.evaluator_vectors
        st.session_state.objective_weights = objective_result.project_weights
        st.success("Pesos dos objetivos/indicadores consolidados.")

    weights = st.session_state.weights
    objective_weights = st.session_state.objective_weights
    if not weights.empty:
        st.markdown("#### Pesos das perspectivas BSC")
        col1, col2 = st.columns([1.1, 1])
        with col1:
            visible_weights = weights[[column for column in ["Perspectiva", "Peso"] if column in weights.columns]]
            st.dataframe(visible_weights, use_container_width=True, hide_index=True)
        with col2:
            st.markdown(radar_svg(weights), unsafe_allow_html=True)

        evaluator_vectors = st.session_state.get("perspective_evaluator_vectors", pd.DataFrame())
        if isinstance(evaluator_vectors, pd.DataFrame) and not evaluator_vectors.empty:
            stats = calculate_consensus_stats(evaluator_vectors)
            st.markdown("#### Estatistica de consenso entre decisores")
            st.dataframe(stats.summary, use_container_width=True, hide_index=True)
            st.info(stats.interpretation)
            with st.expander("Dispersao dos pesos por perspectiva", expanded=False):
                st.dataframe(stats.dispersion, use_container_width=True, hide_index=True)
            with st.expander("Ranking individual das perspectivas por decisor", expanded=False):
                st.dataframe(stats.evaluator_rankings, use_container_width=True, hide_index=True)

    if not objective_weights.empty:
        compact_columns = [
            column
            for column in ["Objetivo estrategico", "Perspectiva dominante", "Peso SAPEVO-BSC", "Ranking objetivo"]
            if column in objective_weights.columns
        ]
        st.markdown("#### Indice estrategico dos objetivos")
        st.caption(
            "Resumo do indice consolidado dos objetivos. A maior contribuicao pode se repetir, "
            "pois indica a perspectiva com maior pontuacao relativa para cada objetivo."
        )
        compact_objectives = objective_weights[compact_columns].rename(
            columns={
                "Perspectiva dominante": "Maior contribuicao estrategica",
                "Peso SAPEVO-BSC": "Indice estrategico",
                "Ranking objetivo": "Ranking",
            }
        )
        st.dataframe(compact_objectives, use_container_width=True, hide_index=True)
        with st.expander("Matriz global objetivo x perspectiva", expanded=False):
            hidden_columns = [
                column
                for column in objective_weights.columns
                if "(%)" not in column and column not in {"Peso objetivo", "Objetivo/KPI"}
            ]
            st.dataframe(objective_weights[hidden_columns], use_container_width=True, hide_index=True)
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

    projects = project_objective_link_inputs(st.session_state.projects, weights)

    st.subheader("8. Ranking dos projetos estrategicos")
    if st.button("Consolidar ranking dos projetos", type="primary"):
        project_weights = calculate_project_weights_from_perspective_alignment(projects, weights)
        ranking = rank_projects(projects, weights, project_weights)
        st.session_state.project_weights = project_weights
        st.session_state.ranking = ranking
        st.success("Ranking dos projetos consolidado.")

    project_weights = st.session_state.project_weights
    ranking = st.session_state.ranking
    if not project_weights.empty:
        st.subheader("Indice estrategico fuzzy das acoes/projetos")
        st.caption("Cada acao/projeto recebe um indice proporcional conforme sua aderencia fuzzy as perspectivas BSC.")
        compact_project_weight_columns = [
            column
            for column in ["Projeto", "Aderencia fuzzy", "Perspectiva", "Indice estrategico"]
            if column in project_weights.columns
        ]
        st.dataframe(project_weights[compact_project_weight_columns], use_container_width=True, hide_index=True)

    if not ranking.empty:
        st.subheader("Ranking dos projetos estrategicos")
        visible_ranking = ranking.copy()
        visible_ranking = visible_ranking.rename(columns={"Peso SAPEVO-BSC": "Peso", "Indice de prioridade": "Indice"})
        ranking_columns = [
            column
            for column in ["Ranking", "Projeto", "Perspectiva", "Natureza", "Peso", "Impacto", "Probabilidade", "Classificacao I/P", "Indice"]
            if column in visible_ranking.columns
        ]
        st.dataframe(visible_ranking[ranking_columns], use_container_width=True, hide_index=True)
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
