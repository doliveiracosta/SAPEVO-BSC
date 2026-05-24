# SAPEVO-BSC Prioritizer

Metodo multicriterio para priorizacao de projetos e acoes estrategicas com enfase em alinhamento estrategico.

Desenvolvido por David de Oliveira Costa, Doutorando em Engenharia de Computacao, 2026.

Artigo de referencia: https://www.researchgate.net/publication/390109234_SAPEVO-BSC_Multicriteria_Method

## Fluxo metodologico

1. Registrar o projeto, horizonte e visao do negocio.
2. Usar as quatro perspectivas BSC como estrutura fixa do metodo.
3. Cadastrar objetivos estrategicos e associa-los as perspectivas BSC.
4. Definir a quantidade de acoes/projetos estrategicos e associar cada item a uma perspectiva BSC principal.
5. Distribuir fuzzy o alinhamento de cada acao/projeto entre os objetivos estrategicos, com soma 1,00.
6. Cadastrar avaliadores.
7. Comparar perspectivas por escala ordinal SAPEVO-M.
8. Consolidar pesos das perspectivas e pesos globais dos objetivos.
9. Calcular o peso SAPEVO-BSC de cada acao/projeto pela particao fuzzy ponderada.
10. Avaliar impacto e probabilidade.
11. Calcular ranking de prioridade e exportar relatorio PDF.

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
