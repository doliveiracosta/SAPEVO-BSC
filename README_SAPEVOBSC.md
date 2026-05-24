# SAPEVO-BSC Prioritizer

Metodo multicriterio para priorizacao de projetos e acoes estrategicas com enfase em alinhamento estrategico.

Desenvolvido por David de Oliveira Costa, Doutorando em Engenharia de Computacao, 2026.

Artigo de referencia: https://www.researchgate.net/publication/390109234_SAPEVO-BSC_Multicriteria_Method

## Fluxo metodologico

1. Registrar o projeto, horizonte e visao do negocio.
2. Usar as quatro perspectivas BSC como estrutura fixa interna do metodo.
3. Definir a quantidade de objetivos estrategicos/KPIs e associar cada objetivo a uma perspectiva BSC.
4. Definir a quantidade de acoes/projetos estrategicos e vincular cada item a um objetivo estrategico/KPI.
5. Cadastrar avaliadores.
6. Comparar perspectivas por escala ordinal SAPEVO-M.
7. Comparar objetivos/KPIs dentro de cada perspectiva por escala ordinal SAPEVO-M.
8. Consolidar pesos das perspectivas e pesos SAPEVO-BSC dos objetivos/KPIs.
9. Avaliar impacto e probabilidade das acoes/projetos.
10. Calcular ranking de prioridade e exportar relatorio PDF.

## Formula operacional

```text
Peso do objetivo/KPI = Peso da perspectiva BSC x Peso local SAPEVO-M do objetivo/KPI na perspectiva
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
