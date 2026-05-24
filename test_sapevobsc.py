import unittest

import pandas as pd

from sapevobsc.core import (
    build_pairwise_matrix,
    compute_objective_weights,
    consolidate_fuzzy_project_weights,
    consolidate_project_weights,
    consolidate_sapevo_weights,
    impact_probability_classification,
    impact_probability_index,
    rank_projects,
)


class SAPEVOBSCTests(unittest.TestCase):
    def test_weights_sum_to_one(self):
        items = ["Financeira", "Clientes", "Processos Internos"]
        matrix = build_pairwise_matrix(
            items,
            {
                ("Financeira", "Clientes"): 2,
                ("Financeira", "Processos Internos"): 1,
                ("Clientes", "Processos Internos"): -1,
            },
        )
        result = consolidate_sapevo_weights([matrix])
        self.assertAlmostEqual(float(result.weights["Peso"].sum()), 1.0)
        self.assertEqual(result.weights.iloc[0]["Perspectiva"], "Financeira")

    def test_project_ranking_uses_weight_impact_probability(self):
        weights = pd.DataFrame(
            {
                "Perspectiva": ["Financeira", "Clientes"],
                "Peso": [0.7, 0.3],
                "Peso (%)": [70, 30],
            }
        )
        projects = pd.DataFrame(
            [
                {"Projeto": "P1", "Objetivo/KPI": "ROI", "Perspectiva": "Financeira", "Natureza": "Oportunidade", "Impacto": "Muito alto", "Probabilidade": "Muito alto"},
                {"Projeto": "P2", "Objetivo/KPI": "NPS", "Perspectiva": "Clientes", "Natureza": "Ameaca", "Impacto": "Baixo", "Probabilidade": "Baixo"},
            ]
        )
        ranking = rank_projects(projects, weights)
        self.assertEqual(ranking.iloc[0]["Projeto"], "P1")
        self.assertIn(ranking.iloc[0]["Classificacao I/P"], {"Baixa", "Media", "Alta"})
        self.assertGreater(float(ranking.iloc[0]["Indice de prioridade"]), float(ranking.iloc[1]["Indice de prioridade"]))

    def test_project_weights_combine_perspective_and_local_weight(self):
        perspective_weights = pd.DataFrame(
            {
                "Perspectiva": ["Financeira"],
                "Peso": [0.8],
                "Peso (%)": [80],
            }
        )
        projects = pd.DataFrame(
            [
                {"Projeto": "P1", "Objetivo/KPI": "ROI", "Perspectiva": "Financeira", "Natureza": "Oportunidade", "Impacto": "Muito alto", "Probabilidade": "Muito alto"},
                {"Projeto": "P2", "Objetivo/KPI": "Margem", "Perspectiva": "Financeira", "Natureza": "Oportunidade", "Impacto": "Alto", "Probabilidade": "Alto"},
            ]
        )
        matrix = build_pairwise_matrix(["P1 - ROI", "P2 - Margem"], {("P1 - ROI", "P2 - Margem"): 3})
        result = consolidate_project_weights(projects, perspective_weights, {"Financeira": [matrix]})

        self.assertAlmostEqual(float(result.project_weights["Peso SAPEVO-BSC"].sum()), 0.8)
        self.assertEqual(result.project_weights.iloc[0]["Projeto"], "P1")

    def test_fuzzy_objective_partition_weights_project(self):
        perspective_weights = pd.DataFrame(
            {
                "Perspectiva": ["Financeira", "Clientes"],
                "Peso": [0.7, 0.3],
                "Peso (%)": [70, 30],
            }
        )
        objectives = pd.DataFrame(
            [
                {"Objetivo estrategico": "ObjX", "Perspectiva": "Financeira"},
                {"Objetivo estrategico": "ObjY", "Perspectiva": "Clientes"},
            ]
        )
        projects = pd.DataFrame(
            [
                {"Acao/Projeto": "P1", "Natureza": "Oportunidade", "Impacto": "Muito alto", "Probabilidade": "Muito alto"},
            ]
        )
        alignment = pd.DataFrame([{"Acao/Projeto": "P1", "ObjX": 0.1, "ObjY": 0.9}])
        objective_weights = compute_objective_weights(objectives, perspective_weights)
        project_weights = consolidate_fuzzy_project_weights(projects, objective_weights, alignment)

        expected = 0.1 * 0.7 + 0.9 * 0.3
        self.assertAlmostEqual(float(project_weights.iloc[0]["Peso SAPEVO-BSC"]), expected, places=6)

    def test_impact_probability_inverts_for_opportunities(self):
        threat_class = impact_probability_classification("Ameaca", "Muito alto", "Muito alto")
        opportunity_class = impact_probability_classification("Oportunidade", "Muito alto", "Muito alto")

        self.assertEqual(threat_class, "Alta")
        self.assertEqual(opportunity_class, "Baixa")
        self.assertGreater(
            impact_probability_index("Ameaca", "Muito alto", "Muito alto"),
            impact_probability_index("Oportunidade", "Muito alto", "Muito alto"),
        )


if __name__ == "__main__":
    unittest.main()
