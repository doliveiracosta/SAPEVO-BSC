import unittest

import pandas as pd

from sapevobsc.core import build_pairwise_matrix, consolidate_project_weights, consolidate_sapevo_weights, rank_projects


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


if __name__ == "__main__":
    unittest.main()
