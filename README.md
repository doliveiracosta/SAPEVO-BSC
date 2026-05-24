# SAPEVO-BSC Prioritizer

Plataforma web para priorizacao de projetos estrategicos combinando Balanced Scorecard, SAPEVO-M e matriz Impacto/Probabilidade.

Desenvolvido por David de Oliveira Costa, Doutorando em Engenharia de Computacao, 2026.

## Fluxo metodologico

1. Definir perspectivas BSC.
2. Cadastrar avaliadores.
3. Comparar perspectivas por escala ordinal SAPEVO-M.
4. Consolidar pesos das perspectivas.
5. Cadastrar projetos, objetivos ou KPIs.
6. Comparar projetos/KPIs dentro de cada perspectiva por SAPEVO-M.
7. Combinar peso da perspectiva com peso local do projeto/KPI.
8. Avaliar impacto e probabilidade.
9. Calcular ranking de prioridade e exportar relatorio PDF.

## Formula operacional

```text
Peso SAPEVO-BSC do projeto = Peso da perspectiva x Peso local do projeto/KPI
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
