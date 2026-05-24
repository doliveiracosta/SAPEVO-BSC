import unittest

import pandas as pd

from sapevobsc.core import build_pairwise_matrix, consolidate_sapevo_weights, rank_projects


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
                {"Projeto": "P1", "Objetivo/KPI": "ROI", "Perspectiva": "Financeira", "Impacto": "Muito alto", "Probabilidade": "Muito alto"},
                {"Projeto": "P2", "Objetivo/KPI": "NPS", "Perspectiva": "Clientes", "Impacto": "Baixo", "Probabilidade": "Baixo"},
            ]
        )
        ranking = rank_projects(projects, weights)
        self.assertEqual(ranking.iloc[0]["Projeto"], "P1")
        self.assertGreater(float(ranking.iloc[0]["Indice de prioridade"]), float(ranking.iloc[1]["Indice de prioridade"]))


if __name__ == "__main__":
    unittest.main()
