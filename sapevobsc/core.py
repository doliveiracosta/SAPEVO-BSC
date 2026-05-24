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


def rank_projects(projects: pd.DataFrame, weights: pd.DataFrame) -> pd.DataFrame:
    if projects.empty or weights.empty:
        return pd.DataFrame()

    weight_map = dict(zip(weights["Perspectiva"], weights["Peso"]))
    rows = []
    for _, project in projects.iterrows():
        perspective = str(project.get("Perspectiva", ""))
        weight = float(weight_map.get(perspective, 0.0))
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
