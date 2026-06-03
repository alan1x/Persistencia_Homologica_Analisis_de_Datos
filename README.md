# Análisis de Datos Económicos Geolocalizados con Persistencia Homológica

TDA sobre el DENUE (INEGI) para el sector **salud (SCIAN 62)**, comparando
**CDMX vs EDOMEX**: complejos Alpha, persistencia homológica y Mapper.

## Estructura

```
src/
  lib/         # pipeline reutilizable
    config.py      # rutas, columnas, CRS, parámetros
    data.py        # carga / limpieza / proyección DENUE
    eda.py         # visualización descriptiva (Fase 1)
    tda.py         # Alpha complex + persistencia + Rips (Fases 2-3)
    viz_tda.py     # diagramas, barcodes, Betti, comparación de regiones
    mapper_viz.py  # Mapper / KeplerMapper (Fase 3b)
  notebooks/   # 01_limpieza_eda ... 05_conclusiones (.py percent + .ipynb)
  outputs/
    intermedios/   # parquet de datos limpios por región
    figuras/       # PNG (EDA, persistencia) + HTML (Mapper)
reporte/       # reporte.md con hallazgos
```

## Setup

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv -r requirements.txt
```

## Ejecutar

```bash
# Pipeline completo vía notebooks (genera parquet + figuras)
cd notebooks
uv run jupyter nbconvert --to notebook --execute --inplace *.ipynb

# O editar/correr interactivo
uv run jupyter lab
```

Los notebooks se versionan como `.py` (jupytext, formato percent) y `.ipynb`.
Editar el `.py` y regenerar: `uv run jupytext --to notebook *.py`.

## Resultados clave

- CDMX 21,585 / EDOMEX 30,787 unidades de salud limpias.
- EDOMEX presenta ~3× más huecos H₁ persistentes (zonas sin cobertura) que CDMX.
- Ver `reporte/reporte.md`.
