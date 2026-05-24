# SAPEVO-BSC Prioritizer

Plataforma web para priorizacao de projetos estrategicos combinando Balanced Scorecard, SAPEVO-M e matriz Impacto/Probabilidade.

Desenvolvido por David de Oliveira Costa, Doutorando em Engenharia de Computacao, 2026.

## Fluxo metodologico

1. Definir perspectivas BSC.
2. Cadastrar avaliadores.
3. Comparar perspectivas por escala ordinal SAPEVO-M.
4. Consolidar pesos das perspectivas.
5. Cadastrar projetos, objetivos ou KPIs.
6. Avaliar impacto e probabilidade.
7. Calcular ranking de prioridade.
8. Exportar relatorio PDF.

## Formula operacional

```text
Indice de prioridade = Peso SAPEVO-BSC x Impacto x Probabilidade
```

## Executar localmente

```bash
pip install -r requirements_sapevobsc.txt
streamlit run sapevobsc_app.py
```

## Deploy no Streamlit Cloud

- Main file path: `sapevobsc_app.py`
- Python dependencies: `requirements_sapevobsc.txt`

