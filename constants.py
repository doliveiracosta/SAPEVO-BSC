"""Constants for the SAPEVO-BSC prioritizer."""

APP_NAME = "SAPEVO-BSC Prioritizer"
APP_SUBTITLE = "Priorizacao estrategica com SAPEVO-BSC"
APP_OWNER = "David de Oliveira Costa"
APP_OWNER_LABEL = f"Desenvolvido por {APP_OWNER}, Doutorando em Engenharia de Computacao, 2026."

BSC_PERSPECTIVES = [
    "Financeira",
    "Clientes",
    "Processos Internos",
    "Aprendizado e Crescimento",
]

PROJECT_NATURES = ["Ameaca", "Oportunidade"]

SAPEVO_SCALE = {
    "Absolutamente pior": -3,
    "Muito pior": -2,
    "Pior": -1,
    "Equivalente": 0,
    "Melhor": 1,
    "Muito melhor": 2,
    "Absolutamente melhor": 3,
}

SAPEVO_LABEL_BY_VALUE = {value: label for label, value in SAPEVO_SCALE.items()}

IMPACT_PROBABILITY_SCALE = {
    "Muito baixo": 0.03,
    "Baixo": 0.11,
    "Moderado": 0.19,
    "Alto": 0.26,
    "Muito alto": 0.38,
}

PROBABILITY_DISPLAY = {
    "Muito baixo": "10%",
    "Baixo": "30%",
    "Moderado": "50%",
    "Alto": "70%",
    "Muito alto": "90%",
}

RISK_CLASS_COLORS = {
    "Baixa": "#a8d08d",
    "Media": "#ffd966",
    "Alta": "#ff7c80",
}
