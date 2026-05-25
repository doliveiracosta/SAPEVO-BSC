"""Core SAPEVO-BSC calculations."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
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


@dataclass(frozen=True)
class ConsensusStats:
    summary: pd.DataFrame
    dispersion: pd.DataFrame
    evaluator_rankings: pd.DataFrame
    interpretation: str


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


def classify_kendall_w(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "Indisponivel"
    if value >= 0.75:
        return "Alto consenso"
    if value >= 0.50:
        return "Consenso moderado"
    if value >= 0.25:
        return "Baixo consenso"
    return "Consenso muito baixo"


def classify_spearman(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "Indisponivel"
    if value >= 0.75:
        return "Alta convergencia ordinal"
    if value >= 0.50:
        return "Convergencia moderada"
    if value >= 0.25:
        return "Convergencia baixa"
    return "Convergencia muito baixa"


def kendall_w_from_rankings(rankings: pd.DataFrame) -> float | None:
    """Calculate Kendall's W for evaluator rankings.

    Rows are criteria/perspectives and columns are evaluators. Lower rank means higher priority.
    The implementation uses average ranks and the classic W formulation, which is adequate as a
    compact consensus diagnostic for this app.
    """
    rankings = rankings.dropna(axis=1, how="all").dropna(axis=0, how="all")
    n_items, n_evaluators = rankings.shape
    if n_items < 2 or n_evaluators < 2:
        return None

    rank_sums = rankings.sum(axis=1)
    mean_rank_sum = rank_sums.mean()
    s_value = ((rank_sums - mean_rank_sum) ** 2).sum()
    denominator = (n_evaluators**2) * (n_items**3 - n_items)
    if denominator == 0:
        return None
    return float((12 * s_value) / denominator)


def mean_pairwise_spearman(rankings: pd.DataFrame) -> float | None:
    rankings = rankings.dropna(axis=1, how="all").dropna(axis=0, how="all")
    if rankings.shape[1] < 2 or rankings.shape[0] < 2:
        return None

    values = []
    for first, second in combinations(rankings.columns, 2):
        correlation = rankings[first].corr(rankings[second], method="pearson")
        if not pd.isna(correlation):
            values.append(float(correlation))
    if not values:
        return None
    return float(sum(values) / len(values))


def calculate_consensus_stats(evaluator_vectors: pd.DataFrame) -> ConsensusStats:
    """Create statistical consensus diagnostics for BSC perspective weights."""
    if evaluator_vectors.empty:
        return ConsensusStats(pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), "Sem dados suficientes para analise estatistica.")

    vectors = evaluator_vectors.copy().fillna(0.0)
    rankings = vectors.rank(axis=0, ascending=False, method="average")
    kendall_w = kendall_w_from_rankings(rankings)
    spearman_mean = mean_pairwise_spearman(rankings)

    dispersion = pd.DataFrame(
        {
            "Perspectiva": vectors.index.astype(str),
            "Peso medio": vectors.mean(axis=1).round(6).values,
            "Desvio padrao": vectors.std(axis=1, ddof=0).round(6).values,
        }
    )
    dispersion["Coeficiente de variacao"] = dispersion.apply(
        lambda row: round(float(row["Desvio padrao"]) / float(row["Peso medio"]), 6)
        if float(row["Peso medio"]) > 0
        else 0.0,
        axis=1,
    )
    dispersion["Peso medio (%)"] = (100 * dispersion["Peso medio"]).round(2)
    dispersion["CV (%)"] = (100 * dispersion["Coeficiente de variacao"]).round(2)
    dispersion = dispersion.sort_values("Desvio padrao", ascending=False).reset_index(drop=True)

    if not dispersion.empty:
        most_divergent = str(dispersion.iloc[0]["Perspectiva"])
        avg_divergence = float(dispersion["Desvio padrao"].mean())
    else:
        most_divergent = ""
        avg_divergence = 0.0

    summary_rows = [
        {
            "Indicador": "Kendall W",
            "Valor": round(kendall_w, 4) if kendall_w is not None else None,
            "Classificacao": classify_kendall_w(kendall_w),
            "Leitura": "Concordancia global entre decisores sobre a ordem das perspectivas.",
        },
        {
            "Indicador": "Spearman medio",
            "Valor": round(spearman_mean, 4) if spearman_mean is not None else None,
            "Classificacao": classify_spearman(spearman_mean),
            "Leitura": "Similaridade media das ordenacoes entre pares de decisores.",
        },
        {
            "Indicador": "Divergencia media",
            "Valor": round(avg_divergence, 4),
            "Classificacao": "Dispersao dos pesos",
            "Leitura": "Desvio padrao medio dos pesos atribuidos as perspectivas.",
        },
        {
            "Indicador": "Perspectiva mais divergente",
            "Valor": most_divergent,
            "Classificacao": "Maior dispersao",
            "Leitura": "Perspectiva BSC com maior diferenca de leitura entre decisores.",
        },
    ]
    summary = pd.DataFrame(summary_rows)

    ranking_table = rankings.reset_index().rename(columns={"index": "Perspectiva"})
    interpretation = consensus_interpretation(kendall_w, spearman_mean, most_divergent)
    return ConsensusStats(
        summary=summary,
        dispersion=dispersion,
        evaluator_rankings=ranking_table,
        interpretation=interpretation,
    )


def consensus_interpretation(kendall_w: float | None, spearman_mean: float | None, most_divergent: str) -> str:
    consensus_label = classify_kendall_w(kendall_w).lower()
    spearman_label = classify_spearman(spearman_mean).lower()
    if kendall_w is None:
        return "Ha apenas um decisor ou dados insuficientes; a analise de consenso entre avaliadores nao foi calculada."

    return (
        f"A analise estatistica indica {consensus_label} entre os decisores nas perspectivas BSC, "
        f"com {spearman_label} entre as ordenacoes individuais. A perspectiva com maior dispersao foi "
        f"{most_divergent}, recomendando atencao gerencial na validacao dos pesos consolidados."
    )


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


def consolidate_objective_scores_by_perspective(
    objectives: pd.DataFrame,
    perspective_weights: pd.DataFrame,
    matrices_by_perspective: dict[str, list[pd.DataFrame]],
) -> ProjectWeightResult:
    """Create the global objective x BSC perspective matrix and final objective priorities."""
    if objectives.empty or perspective_weights.empty:
        return ProjectWeightResult(pd.DataFrame(), {})

    objective_labels = [
        objective_name(row) or f"Objetivo {index + 1}"
        for index, row in objectives.reset_index(drop=True).iterrows()
    ]
    perspectives = perspective_weights["Perspectiva"].astype(str).tolist()
    perspective_weight_map = dict(zip(perspective_weights["Perspectiva"], perspective_weights["Peso"]))
    evaluator_vectors_by_perspective: dict[str, pd.DataFrame] = {}
    score_matrix = pd.DataFrame(0.0, index=objective_labels, columns=perspectives)

    for perspective in perspectives:
        matrices = matrices_by_perspective.get(perspective, [])
        valid_matrices = [matrix for matrix in matrices if not matrix.empty]
        if len(objective_labels) <= 1:
            evaluator_vectors = pd.DataFrame({"Peso local": pd.Series([1.0], index=objective_labels)})
            local_scores = pd.Series([1.0], index=objective_labels)
        elif valid_matrices:
            vectors = []
            for index, matrix in enumerate(valid_matrices, start=1):
                vector = evaluator_weight_vector(matrix).reindex(objective_labels).fillna(0.0)
                vector.name = f"Avaliador {index}"
                vectors.append(vector)
            evaluator_vectors = pd.concat(vectors, axis=1).fillna(0.0)
            local_scores = evaluator_vectors.mean(axis=1)
        else:
            local_scores = pd.Series([1.0 / len(objective_labels)] * len(objective_labels), index=objective_labels)
            evaluator_vectors = pd.DataFrame({"Peso local": local_scores})

        evaluator_vectors_by_perspective[perspective] = evaluator_vectors
        score_matrix[perspective] = local_scores.reindex(objective_labels).fillna(0.0)

    rows = []
    for objective in objective_labels:
        final_weight = 0.0
        best_perspective = ""
        best_local_score = -1.0
        row = {
            "Objetivo estrategico": objective,
            "Objetivo/KPI": objective,
        }
        for perspective in perspectives:
            local_score = float(score_matrix.loc[objective, perspective])
            perspective_weight = float(perspective_weight_map.get(perspective, 0.0))
            row[perspective] = round(local_score, 6)
            final_weight += local_score * perspective_weight
            if local_score > best_local_score:
                best_local_score = local_score
                best_perspective = perspective
        row["Perspectiva dominante"] = best_perspective
        row["Peso SAPEVO-BSC"] = round(final_weight, 6)
        row["Peso objetivo"] = round(final_weight, 6)
        row["Peso SAPEVO-BSC (%)"] = round(100 * final_weight, 2)
        row["Peso objetivo (%)"] = round(100 * final_weight, 2)
        rows.append(row)

    objective_weights = pd.DataFrame(rows).sort_values(
        ["Peso SAPEVO-BSC", "Objetivo estrategico"],
        ascending=[False, True],
    )
    objective_weights["Ranking objetivo"] = range(1, len(objective_weights) + 1)
    return ProjectWeightResult(
        project_weights=objective_weights.reset_index(drop=True),
        evaluator_vectors=evaluator_vectors_by_perspective,
    )


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


def calculate_project_weights_from_perspective_alignment(
    projects: pd.DataFrame,
    perspective_weights: pd.DataFrame,
) -> pd.DataFrame:
    """Calculate project strategic index from fuzzy adherence to BSC perspectives."""
    if projects.empty or perspective_weights.empty:
        return pd.DataFrame()

    weight_map = {
        str(row.get("Perspectiva", "")): float(row.get("Peso", 0.0))
        for _, row in perspective_weights.iterrows()
    }
    perspective_names = list(weight_map)
    rows = []

    for _, project in projects.iterrows():
        name = project_name(project)
        memberships = {}
        for perspective in perspective_names:
            raw_value = project.get(f"Aderencia - {perspective}", 0.0)
            memberships[perspective] = max(0.0, min(1.0, float(raw_value or 0.0)))

        total_membership = sum(memberships.values())
        if total_membership > 0:
            normalized_memberships = {
                perspective: value / total_membership
                for perspective, value in memberships.items()
            }
        else:
            normalized_memberships = {
                perspective: 1.0 / len(perspective_names)
                for perspective in perspective_names
            }

        strategic_index = sum(
            normalized_memberships[perspective] * weight_map[perspective]
            for perspective in perspective_names
        )
        dominant_perspective = max(normalized_memberships, key=normalized_memberships.get) if normalized_memberships else ""

        row = {
            "Projeto": name,
            "Objetivo/KPI": objective_name(project),
            "Projeto/KPI": name,
            "Perspectiva": dominant_perspective,
            "Peso perspectiva": round(float(weight_map.get(dominant_perspective, 0.0)), 6),
            "Peso local SAPEVO-M": round(float(normalized_memberships.get(dominant_perspective, 0.0)), 6),
            "Peso SAPEVO-BSC": round(strategic_index, 6),
            "Indice estrategico": round(strategic_index, 6),
            "Aderencia fuzzy": "; ".join(
                f"{perspective}: {normalized_memberships[perspective]:.2f}"
                for perspective in perspective_names
                if normalized_memberships[perspective] > 0
            ),
        }
        for perspective in perspective_names:
            row[perspective] = round(normalized_memberships[perspective], 6)
        rows.append(row)

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
