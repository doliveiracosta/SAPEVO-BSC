# SAPEVO-BSC Prioritizer

Metodo multicriterio para priorizacao de projetos e acoes estrategicas com enfase em alinhamento estrategico.

Desenvolvido por David de Oliveira Costa, Doutorando em Engenharia de Computacao, 2026.

Artigo de referencia: https://www.researchgate.net/publication/390109234_SAPEVO-BSC_Multicriteria_Method

## Fluxo metodologico

1. Registrar o projeto, horizonte e visao do negocio.
2. Identificar as acoes/projetos que precisam ser executados.
3. Definir os objetivos/indicadores estrategicos que serao tratados como alternativas.
4. Cadastrar decisores/avaliadores.
5. Comparar perspectivas BSC por escala ordinal SAPEVO-M.
6. Para cada perspectiva BSC, comparar os objetivos/indicadores por escala ordinal SAPEVO-M.
7. Vincular cada acao/projeto ao objetivo/indicador estrategico correspondente e avaliar impacto/probabilidade com classe I/P calculada automaticamente.
8. Gerar a matriz global objetivo x perspectiva, calcular o peso final de cada objetivo, calcular o ranking de prioridade e exportar relatorio PDF.

## Formula operacional

```text
Matriz global = pontuacao SAPEVO-M de cada objetivo/KPI em cada perspectiva BSC
Peso do objetivo/KPI = soma(pontuacao do objetivo na perspectiva x peso da perspectiva)
Peso SAPEVO-BSC do projeto = Peso SAPEVO-BSC do objetivo/KPI vinculado ao projeto
Indice I/P = valor da classe obtida na matriz Impacto/Probabilidade
Indice de prioridade = Peso SAPEVO-BSC do projeto x Indice I/P
```

Na matriz I/P, ameacas e oportunidades possuem leituras inversas: em ameacas, maior impacto/probabilidade aumenta a criticidade; em oportunidades, a orientacao segue a matriz invertida do metodo.

## Executar localmente

```bash
pip install -r requirements_sapevobsc.txt
streamlit run sapevobsc_app.py
```

## Deploy no Streamlit Cloud

- Main file path: `sapevobsc_app.py`
- Python dependencies: `requirements.txt`
