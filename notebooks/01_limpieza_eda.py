# %% [markdown]
# # 01 — Limpieza, preprocesamiento y EDA descriptiva
#
# Sector analizado: **SCIAN 62 (Servicios de salud y asistencia social)**.
# Se procesan **CDMX** y **EDOMEX** en paralelo para comparar.
#
# Pasos: carga (Latin-1) → filtro de sector → limpieza de coordenadas →
# proyección a metros (UTM 14N) → visualización descriptiva.

# %%
import sys
sys.path.insert(0, "..")
import pandas as pd
from lib import data, eda, config

# %% [markdown]
# ## Carga y preparación
# `data.preparar` ejecuta todo el pipeline. Se cachea a parquet para reuso.

# %%
dfs = {}
for region in ["CDMX", "EDOMEX"]:
    df = data.preparar(region)
    df.to_parquet(config.INTERMEDIOS_DIR / f"salud_{region}.parquet")
    dfs[region] = df
    print(f"{region}: {len(df):,} unidades | "
          f"{df['municipio'].nunique()} municipios | "
          f"{df['codigo_act'].nunique()} actividades")

# %% [markdown]
# ## Visualización descriptiva (mapa, municipios, personal ocupado)

# %%
for region, df in dfs.items():
    ruta = eda.panel_eda(df, region)
    print("figura:", ruta)

# %% [markdown]
# **Lectura:** los consultorios dentales y de medicina general dominan el sector
# (unidades de 0–5 personas). CDMX concentra alta densidad en delegaciones
# centrales; EDOMEX se reparte en muchos más municipios con densidad despareja.
