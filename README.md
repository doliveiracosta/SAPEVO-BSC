# SAPEVO-BSC Prioritizer

Plataforma web para priorizacao de acoes e projetos estrategicos combinando Balanced Scorecard, SAPEVO-M e matriz Impacto/Probabilidade.

Desenvolvido por David de Oliveira Costa, Doutorando em Engenharia de Computacao, 2026.

Artigo de referencia: https://www.researchgate.net/publication/390109234_SAPEVO-BSC_Multicriteria_Method

## Fluxo metodologico

1. Registrar o projeto, horizonte e visao do negocio.
2. Cadastrar objetivos estrategicos e associa-los as perspectivas BSC.
3. Cadastrar acoes/projetos estrategicos.
4. Distribuir fuzzy o alinhamento de cada acao/projeto entre os objetivos estrategicos, com soma 1,00.
5. Cadastrar avaliadores.
6. Comparar perspectivas por escala ordinal SAPEVO-M.
7. Consolidar pesos das perspectivas e pesos globais dos objetivos.
8. Calcular o peso SAPEVO-BSC de cada acao/projeto pela particao fuzzy ponderada.
9. Avaliar impacto e probabilidade.
10. Calcular ranking de prioridade e exportar relatorio PDF.

## Formula operacional

```text
Peso do objetivo = Peso da perspectiva BSC x Peso relativo normalizado do objetivo
Peso SAPEVO-BSC do projeto = soma(pertinencia fuzzy ao objetivo x Peso do objetivo)
Indice de prioridade = Peso SAPEVO-BSC do projeto x Impacto x Probabilidade
```

## Executar localmente

```bash
pip install -r requirements_sapevobsc.txt
streamlit run sapevobsc_app.py
```

## Deploy no Streamlit Cloud

- Main file path: `sapevobsc_app.py`
- Python dependencies: `requirements.txt`
