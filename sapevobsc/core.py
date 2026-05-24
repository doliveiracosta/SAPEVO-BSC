"""Core SAPEVO-BSC calculations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd

from .constants import IMPACT_PROBABILITY_SCALE


@dataclass(frozen=True)
class WeightResult:
    weights: pd.DataFrame
    evaluator_vectors: pd.DataFrame


@dataclass(frozen=True)
class ProjectWeightResult:
    project_weights: pd.DataFrame
    evaluator_vectors: dict[str, pd.DataFrame]


def normalize_positive(values: pd.Series) -> pd.Series:
    """Convert ordinal net scores into positive normalized weights."""
    if values.empty:
        return values
    if float(values.max()) == float(values.min()):
        return pd.Series([1.0 / len(values)] * len(values), index=values.index)

    positive = values - values.min() + 1.0
    total = positive.sum()
    if total == 0:
        return pd.Series([1.0 / len(values)] * len(values), index=values.index)
    return positive / total


def build_pairwise_matrix(items: list[str], comparisons: dict[tuple[str, str], int]) -> pd.DataFrame:
    matrix = pd.DataFrame(0.0, index=items, columns=items)
    for i, item_i in enumerate(items):
        for item_j in items[i + 1 :]:
            value = float(comparisons.get((item_i, item_j), 0))
            matrix.loc[item_i, item_j] = value
            matrix.loc[item_j, item_i] = -value
    return matrix


def evaluator_weight_vector(matrix: pd.DataFrame) -> pd.Series:
    net_scores = matrix.sum(axis=1)
    return normalize_positive(net_scores)


def consolidate_sapevo_weights(matrices: Iterable[pd.DataFrame]) -> WeightResult:
    vectors = []
    for index, matrix in enumerate(matrices, start=1):
        vector = evaluator_weight_vector(matrix)
        vector.name = f"Avaliador {index}"
        vectors.append(vector)

    if not vectors:
        return WeightResult(pd.DataFrame(columns=["Perspectiva", "Peso"]), pd.DataFrame())

    evaluator_vectors = pd.concat(vectors, axis=1).fillna(0.0)
    consolidated = evaluator_vectors.mean(axis=1)
    consolidated = consolidated / consolidated.sum() if consolidated.sum() else consolidated

    weights = (
        consolidated.rename("Peso")
        .reset_index()
        .rename(columns={"index": "Perspectiva"})
        .sort_values("Peso", ascending=False)
        .reset_index(drop=True)
    )
    weights["Peso (%)"] = (100 * weights["Peso"]).round(2)
    return WeightResult(weights=weights, evaluator_vectors=evaluator_vectors)


def project_label(row: pd.Series) -> str:
    project = str(row.get("Projeto", "")).strip()
    objective = str(row.get("Objetivo/KPI", "")).strip()
    if project and objective:
        return f"{project} - {objective}"
    return project or objective


def consolidate_project_weights(
    projects: pd.DataFrame,
    perspective_weights: pd.DataFrame,
    matrices_by_perspective: dict[str, list[pd.DataFrame]],
) -> ProjectWeightResult:
    """Consolidate local SAPEVO-M weights for projects/KPIs within each BSC perspective."""
    if projects.empty or perspective_weights.empty:
        return ProjectWeightResult(pd.DataFrame(), {})

    perspective_map = dict(zip(perspective_weights["Perspectiva"], perspective_weights["Peso"]))
    evaluator_vectors_by_perspective: dict[str, pd.DataFrame] = {}
    rows = []

    for perspective, group in projects.groupby("Perspectiva", dropna=False):
        perspective = str(perspective)
        group = group.reset_index(drop=True)
        labels = [project_label(row) or f"Item {index + 1}" for index, row in group.iterrows()]
        matrices = matrices_by_perspective.get(perspective, [])

        if len(labels) <= 1:
            local_weights = pd.Series([1.0], index=labels)
            evaluator_vectors = pd.DataFrame({"Peso local": local_weights})
        else:
            valid_matrices = [matrix for matrix in matrices if not matrix.empty]
            if valid_matrices:
                result = consolidate_sapevo_weights(valid_matrices)
                local_weights = result.weights.set_index("Perspectiva")["Peso"].reindex(labels).fillna(0.0)
                evaluator_vectors = result.evaluator_vectors
            else:
                local_weights = pd.Series([1.0 / len(labels)] * len(labels), index=labels)
                evaluator_vectors = pd.DataFrame({"Peso local": local_weights})

        evaluator_vectors_by_perspective[perspective] = evaluator_vectors
        perspective_weight = float(perspective_map.get(perspective, 0.0))

        for index, row in group.iterrows():
            label = labels[index]
            local_weight = float(local_weights.get(label, 0.0))
            global_weight = perspective_weight * local_weight
            rows.append(
                {
                    "Projeto": row.get("Projeto", ""),
                    "Objetivo/KPI": row.get("Objetivo/KPI", ""),
                    "Projeto/KPI": label,
                    "Perspectiva": perspective,
                    "Peso perspectiva": round(perspective_weight, 6),
                    "Peso local SAPEVO-M": round(local_weight, 6),
                    "Peso SAPEVO-BSC": round(global_weight, 6),
                    "Peso SAPEVO-BSC (%)": round(100 * global_weight, 2),
                }
            )

    project_weights = pd.DataFrame(rows).sort_values(
        ["Peso SAPEVO-BSC", "Projeto/KPI"],
        ascending=[False, True],
    )
    return ProjectWeightResult(project_weights=project_weights.reset_index(drop=True), evaluator_vectors=evaluator_vectors_by_perspective)


def scale_value(label: str) -> float:
    return float(IMPACT_PROBABILITY_SCALE.get(label, 0.0))


THREAT_MATRIX = {
    "Muito alto": {"Muito baixo": "Media", "Baixo": "Media", "Moderado": "Alta", "Alto": "Alta", "Muito alto": "Alta"},
    "Alto": {"Muito baixo": "Baixa", "Baixo": "Media", "Moderado": "Media", "Alto": "Alta", "Muito alto": "Alta"},
    "Moderado": {"Muito baixo": "Baixa", "Baixo": "Baixa", "Moderado": "Media", "Alto": "Alta", "Muito alto": "Alta"},
    "Baixo": {"Muito baixo": "Baixa", "Baixo": "Baixa", "Moderado": "Media", "Alto": "Media", "Muito alto": "Alta"},
    "Muito baixo": {"Muito baixo": "Baixa", "Baixo": "Baixa", "Moderado": "Baixa", "Alto": "Baixa", "Muito alto": "Media"},
}

OPPORTUNITY_MATRIX = {
    "Muito alto": {"Muito alto": "Baixa", "Alto": "Baixa", "Moderado": "Baixa", "Baixo": "Media", "Muito baixo": "Media"},
    "Alto": {"Muito alto": "Baixa", "Alto": "Baixa", "Moderado": "Media", "Baixo": "Media", "Muito baixo": "Alta"},
    "Moderado": {"Muito alto": "Baixa", "Alto": "Baixa", "Moderado": "Media", "Baixo": "Alta", "Muito baixo": "Alta"},
    "Baixo": {"Muito alto": "Baixa", "Alto": "Media", "Moderado": "Media", "Baixo": "Alta", "Muito baixo": "Alta"},
    "Muito baixo": {"Muito alto": "Media", "Alto": "Alta", "Moderado": "Alta", "Baixo": "Alta", "Muito baixo": "Alta"},
}


def impact_probability_classification(nature: str, impact: str, probability: str) -> str:
    matrix = THREAT_MATRIX if str(nature).lower().startswith("ame") else OPPORTUNITY_MATRIX
    return matrix.get(probability, {}).get(impact, "Baixa")


def rank_projects(projects: pd.DataFrame, weights: pd.DataFrame, project_weights: pd.DataFrame | None = None) -> pd.DataFrame:
    if projects.empty or weights.empty:
        return pd.DataFrame()

    weight_map = dict(zip(weights["Perspectiva"], weights["Peso"]))
    project_weight_map = {}
    if project_weights is not None and not project_weights.empty:
        project_weight_map = {
            (str(row.get("Projeto", "")), str(row.get("Objetivo/KPI", "")), str(row.get("Perspectiva", ""))): float(row.get("Peso SAPEVO-BSC", 0.0))
            for _, row in project_weights.iterrows()
        }

    rows = []
    for _, project in projects.iterrows():
        perspective = str(project.get("Perspectiva", ""))
        fallback_weight = float(weight_map.get(perspective, 0.0))
        weight = project_weight_map.get(
            (str(project.get("Projeto", "")), str(project.get("Objetivo/KPI", "")), perspective),
            fallback_weight,
        )
        impact = scale_value(str(project.get("Impacto", "")))
        probability = scale_value(str(project.get("Probabilidade", "")))
        index = weight * impact * probability
        rows.append(
            {
                "Projeto": project.get("Projeto", ""),
                "Objetivo/KPI": project.get("Objetivo/KPI", ""),
                "Perspectiva": perspective,
                "Natureza": project.get("Natureza", "Oportunidade"),
                "Peso SAPEVO-BSC": round(weight, 6),
                "Impacto": project.get("Impacto", ""),
                "Probabilidade": project.get("Probabilidade", ""),
                "Classificacao I/P": impact_probability_classification(
                    str(project.get("Natureza", "Oportunidade")),
                    str(project.get("Impacto", "")),
                    str(project.get("Probabilidade", "")),
                ),
                "Impacto (valor)": impact,
                "Probabilidade (valor)": probability,
                "Indice de prioridade": round(index, 8),
            }
        )

    ranking = pd.DataFrame(rows).sort_values(
        ["Indice de prioridade", "Projeto"],
        ascending=[False, True],
    )
    ranking["Ranking"] = range(1, len(ranking) + 1)
    return ranking.reset_index(drop=True)


def strategic_conclusion(ranking: pd.DataFrame, weights: pd.DataFrame) -> str:
    if ranking.empty:
        return "Nao ha projetos suficientes para gerar conclusao consultiva."

    top = ranking.iloc[0]
    leading_perspective = weights.iloc[0]["Perspectiva"] if not weights.empty else top["Perspectiva"]
    avg_index = float(ranking["Indice de prioridade"].mean())
    top_index = float(top["Indice de prioridade"])

    if top_index >= avg_index * 1.5:
        intensity = "fortemente concentrada"
    elif top_index >= avg_index * 1.15:
        intensity = "moderadamente concentrada"
    else:
        intensity = "distribuida"

    return (
        f"A priorizacao indica uma carteira {intensity}, com maior peso estrategico associado a "
        f"{leading_perspective}. O projeto mais prioritario e {top['Projeto']}, vinculado a "
        f"{top['Perspectiva']}, combinando peso SAPEVO-BSC, impacto e probabilidade."
    )
