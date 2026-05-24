# SAPEVO-BSC Prioritizer

Metodo multicriterio para priorizacao de projetos e acoes estrategicas com enfase em alinhamento estrategico.

Desenvolvido por David de Oliveira Costa, Doutorando em Engenharia de Computacao, 2026.

Artigo de referencia: https://www.researchgate.net/publication/390109234_SAPEVO-BSC_Multicriteria_Method

## Fluxo metodologico

1. Registrar o projeto, horizonte e visao do negocio.
2. Usar as quatro perspectivas BSC como estrutura fixa interna do metodo.
3. Definir a quantidade de acoes/projetos estrategicos e, em campo recolhido, associar cada item a uma perspectiva BSC principal.
4. Definir a quantidade de objetivos estrategicos e associar cada objetivo a uma perspectiva BSC em caixa de selecao.
5. Distribuir fuzzy o alinhamento de cada acao/projeto entre os objetivos estrategicos, com soma 1,00.
6. Cadastrar avaliadores.
7. Comparar perspectivas por escala ordinal SAPEVO-M.
8. Consolidar pesos das perspectivas e pesos globais dos objetivos.
9. Calcular o peso SAPEVO-BSC de cada acao/projeto pela particao fuzzy ponderada.
10. Avaliar impacto e probabilidade.
11. Calcular ranking de prioridade e exportar relatorio PDF.

## Formula operacional

```text
Peso do objetivo = Peso da perspectiva BSC distribuido igualmente entre os objetivos associados a essa perspectiva
Peso SAPEVO-BSC do projeto = soma(pertinencia fuzzy ao objetivo x Peso do objetivo)
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
