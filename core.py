"""Core SAPEVO-BSC calculations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd

from .constants import IMPACT_PROBABILITY_CLASS_VALUES, IMPACT_PROBABILITY_SCALE


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


def project_name(row: pd.Series) -> str:
    return str(row.get("Projeto", row.get("Acao/Projeto", ""))).strip()


def objective_name(row: pd.Series) -> str:
    return str(row.get("Objetivo/KPI", row.get("Objetivo estrategico", ""))).strip()


def project_label(row: pd.Series) -> str:
    project = project_name(row)
    objective = objective_name(row)
    if project and objective:
        return f"{project} - {objective}"
    return project or objective


def compute_objective_weights(objectives: pd.DataFrame, perspective_weights: pd.DataFrame) -> pd.DataFrame:
    """Calculate global objective weights from BSC perspective weights and local objective weights."""
    if objectives.empty or perspective_weights.empty:
        return pd.DataFrame()

    objective_rows = objectives.copy().fillna("")
    perspective_map = dict(zip(perspective_weights["Perspectiva"], perspective_weights["Peso"]))
    rows = []
    for perspective, group in objective_rows.groupby("Perspectiva", dropna=False):
        perspective = str(perspective)
        local_weights = pd.Series([1.0 / len(group)] * len(group), index=group.index)
        perspective_weight = float(perspective_map.get(perspective, 0.0))

        for index, row in group.iterrows():
            local_weight = float(local_weights.loc[index])
            global_weight = perspective_weight * local_weight
            rows.append(
                {
                    "Objetivo estrategico": str(row.get("Objetivo estrategico", "")),
                    "Perspectiva": perspective,
                    "Peso perspectiva": round(perspective_weight, 6),
                    "Peso local objetivo": round(local_weight, 6),
                    "Peso objetivo": round(global_weight, 6),
                    "Peso objetivo (%)": round(100 * global_weight, 2),
                }
            )

    return pd.DataFrame(rows).sort_values("Peso objetivo", ascending=False).reset_index(drop=True)


def consolidate_objective_sapevo_weights(
    objectives: pd.DataFrame,
    perspective_weights: pd.DataFrame,
    matrices_by_perspective: dict[str, list[pd.DataFrame]],
) -> ProjectWeightResult:
    """Consolidate local SAPEVO-M weights for objectives/KPIs within each BSC perspective."""
    if objectives.empty or perspective_weights.empty:
        return ProjectWeightResult(pd.DataFrame(), {})

    objective_rows = objectives.copy().fillna("")
    perspective_map = dict(zip(perspective_weights["Perspectiva"], perspective_weights["Peso"]))
    evaluator_vectors_by_perspective: dict[str, pd.DataFrame] = {}
    rows = []

    for perspective, group in objective_rows.groupby("Perspectiva", dropna=False):
        perspective = str(perspective)
        group = group.reset_index(drop=True)
        labels = [
            objective_name(row) or f"Objetivo {index + 1}"
            for index, row in group.iterrows()
        ]
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
                    "Objetivo estrategico": label,
                    "Objetivo/KPI": label,
                    "Perspectiva": perspective,
                    "Descricao": str(row.get("Descricao", "")),
                    "Peso perspectiva": round(perspective_weight, 6),
                    "Peso local SAPEVO-M": round(local_weight, 6),
                    "Peso local objetivo": round(local_weight, 6),
                    "Peso SAPEVO-BSC": round(global_weight, 6),
                    "Peso objetivo": round(global_weight, 6),
                    "Peso SAPEVO-BSC (%)": round(100 * global_weight, 2),
                    "Peso objetivo (%)": round(100 * global_weight, 2),
                }
            )

    objective_weights = pd.DataFrame(rows).sort_values(
        ["Peso SAPEVO-BSC", "Objetivo estrategico"],
        ascending=[False, True],
    )
    return ProjectWeightResult(
        project_weights=objective_weights.reset_index(drop=True),
        evaluator_vectors=evaluator_vectors_by_perspective,
    )


def calculate_project_weights_from_objectives(
    projects: pd.DataFrame,
    objective_weights: pd.DataFrame,
) -> pd.DataFrame:
    """Assign each project/action the SAPEVO-BSC weight of its linked objective/KPI."""
    if projects.empty or objective_weights.empty:
        return pd.DataFrame()

    weight_map = {
        str(row.get("Objetivo estrategico", row.get("Objetivo/KPI", ""))): row
        for _, row in objective_weights.iterrows()
    }
    fallback_weight = float(objective_weights["Peso SAPEVO-BSC"].mean()) if "Peso SAPEVO-BSC" in objective_weights else 0.0
    rows = []

    for _, project in projects.iterrows():
        name = project_name(project)
        objective = objective_name(project)
        objective_row = weight_map.get(objective)
        if objective_row is not None:
            perspective = str(objective_row.get("Perspectiva", project.get("Perspectiva", "")))
            perspective_weight = float(objective_row.get("Peso perspectiva", 0.0))
            local_weight = float(objective_row.get("Peso local SAPEVO-M", objective_row.get("Peso local objetivo", 0.0)))
            final_weight = float(objective_row.get("Peso SAPEVO-BSC", objective_row.get("Peso objetivo", 0.0)))
        else:
            perspective = str(project.get("Perspectiva", ""))
            perspective_weight = 0.0
            local_weight = 0.0
            final_weight = fallback_weight

        rows.append(
            {
                "Projeto": name,
                "Objetivo/KPI": objective,
                "Projeto/KPI": name,
                "Perspectiva": perspective,
                "Peso perspectiva": round(perspective_weight, 6),
                "Peso local SAPEVO-M": round(local_weight, 6),
                "Peso SAPEVO-BSC": round(final_weight, 6),
                "Peso SAPEVO-BSC (%)": round(100 * final_weight, 2),
            }
        )

    return pd.DataFrame(rows).sort_values(
        ["Peso SAPEVO-BSC", "Projeto"],
        ascending=[False, True],
    ).reset_index(drop=True)


def normalize_fuzzy_alignment(alignment: pd.DataFrame, objective_names: list[str]) -> pd.DataFrame:
    if alignment.empty:
        return alignment

    normalized = alignment.copy()
    for objective in objective_names:
        if objective not in normalized.columns:
            normalized[objective] = 0.0
        normalized[objective] = pd.to_numeric(normalized[objective], errors="coerce").fillna(0.0).clip(0.0, 1.0)

    row_sums = normalized[objective_names].sum(axis=1)
    for index, total in row_sums.items():
        if float(total) > 0:
            normalized.loc[index, objective_names] = normalized.loc[index, objective_names] / float(total)
    return normalized


def consolidate_fuzzy_project_weights(
    projects: pd.DataFrame,
    objective_weights: pd.DataFrame,
    alignment: pd.DataFrame,
) -> pd.DataFrame:
    """Calculate project weights by fuzzy membership in strategic objectives."""
    if projects.empty or objective_weights.empty or alignment.empty:
        return pd.DataFrame()

    objective_names = objective_weights["Objetivo estrategico"].astype(str).tolist()
    normalized_alignment = normalize_fuzzy_alignment(alignment, objective_names)
    objective_weight_map = dict(zip(objective_weights["Objetivo estrategico"], objective_weights["Peso objetivo"]))
    objective_perspective_map = dict(zip(objective_weights["Objetivo estrategico"], objective_weights["Perspectiva"]))
    objective_perspective_weight_map = dict(zip(objective_weights["Objetivo estrategico"], objective_weights["Peso perspectiva"]))

    rows = []
    for _, project in projects.iterrows():
        name = project_name(project)
        match = normalized_alignment[normalized_alignment["Acao/Projeto"].astype(str) == name]
        memberships = match.iloc[0] if not match.empty else pd.Series(dtype=object)
        contributions = {
            objective: float(memberships.get(objective, 0.0)) * float(objective_weight_map.get(objective, 0.0))
            for objective in objective_names
        }
        final_weight = sum(contributions.values())
        dominant_objective = max(contributions, key=contributions.get) if contributions else objective_name(project)
        dominant_perspective = str(objective_perspective_map.get(dominant_objective, project.get("Perspectiva", "")))

        rows.append(
            {
                "Projeto": name,
                "Objetivo/KPI": dominant_objective,
                "Projeto/KPI": name,
                "Perspectiva": dominant_perspective,
                "Peso perspectiva": round(float(objective_perspective_weight_map.get(dominant_objective, 0.0)), 6),
                "Peso local SAPEVO-M": round(float(memberships.get(dominant_objective, 0.0) if not memberships.empty else 0.0), 6),
                "Peso SAPEVO-BSC": round(final_weight, 6),
                "Peso SAPEVO-BSC (%)": round(100 * final_weight, 2),
                "Objetivo dominante": dominant_objective,
                "Particao fuzzy": "; ".join(
                    f"{objective}: {float(memberships.get(objective, 0.0)):.2f}"
                    for objective in objective_names
                    if float(memberships.get(objective, 0.0)) > 0
                ),
            }
        )

    return pd.DataFrame(rows).sort_values("Peso SAPEVO-BSC", ascending=False).reset_index(drop=True)


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
                    "Projeto": project_name(row),
                    "Objetivo/KPI": objective_name(row),
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


def impact_probability_index(nature: str, impact: str, probability: str) -> float:
    classification = impact_probability_classification(nature, impact, probability)
    return float(IMPACT_PROBABILITY_CLASS_VALUES.get(classification, 0.0))


def rank_projects(projects: pd.DataFrame, weights: pd.DataFrame, project_weights: pd.DataFrame | None = None) -> pd.DataFrame:
    if projects.empty or weights.empty:
        return pd.DataFrame()

    weight_map = dict(zip(weights["Perspectiva"], weights["Peso"]))
    project_weight_map = {}
    project_weight_by_name = {}
    project_meta_by_name = {}
    if project_weights is not None and not project_weights.empty:
        project_weight_map = {
            (str(row.get("Projeto", "")), str(row.get("Objetivo/KPI", "")), str(row.get("Perspectiva", ""))): float(row.get("Peso SAPEVO-BSC", 0.0))
            for _, row in project_weights.iterrows()
        }
        project_weight_by_name = {
            str(row.get("Projeto", "")): float(row.get("Peso SAPEVO-BSC", 0.0))
            for _, row in project_weights.iterrows()
        }
        project_meta_by_name = {
            str(row.get("Projeto", "")): {
                "Objetivo/KPI": str(row.get("Objetivo/KPI", "")),
                "Perspectiva": str(row.get("Perspectiva", "")),
            }
            for _, row in project_weights.iterrows()
        }

    rows = []
    for _, project in projects.iterrows():
        name = project_name(project)
        meta = project_meta_by_name.get(name, {})
        perspective = str(meta.get("Perspectiva", project.get("Perspectiva", "")))
        fallback_weight = float(weight_map.get(perspective, 0.0))
        weight = project_weight_map.get(
            (name, objective_name(project), perspective),
            project_weight_by_name.get(name, fallback_weight),
        )
        impact = scale_value(str(project.get("Impacto", "")))
        probability = scale_value(str(project.get("Probabilidade", "")))
        nature = str(project.get("Natureza", "Oportunidade"))
        ip_class = impact_probability_classification(
            nature,
            str(project.get("Impacto", "")),
            str(project.get("Probabilidade", "")),
        )
        ip_index = impact_probability_index(
            nature,
            str(project.get("Impacto", "")),
            str(project.get("Probabilidade", "")),
        )
        index = weight * ip_index
        rows.append(
            {
                "Projeto": name,
                "Objetivo/KPI": meta.get("Objetivo/KPI", objective_name(project)),
                "Perspectiva": perspective,
                "Natureza": nature,
                "Peso SAPEVO-BSC": round(weight, 6),
                "Impacto": project.get("Impacto", ""),
                "Probabilidade": project.get("Probabilidade", ""),
                "Classificacao I/P": ip_class,
                "Indice I/P": round(ip_index, 6),
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
        f"{leading_perspective}. A acao/projeto mais prioritaria e {top['Projeto']}, associada ao "
        f"objetivo estrategico {top.get('Objetivo/KPI', '')} e vinculada a {top['Perspectiva']}, "
        f"combinando peso SAPEVO-BSC, impacto e probabilidade."
    )
