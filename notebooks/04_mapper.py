# %% [markdown]
# # 04 — Mapper
#
# Complemento a la persistencia (liga investigación propia **Mapper**). Mapper
# resume los datos como una **red**: nodos = clusters de unidades, aristas =
# clusters que comparten unidades. Lens = coordenadas proyectadas (esqueleto
# espacial); clustering por cubo con DBSCAN; color = personal ocupado.

# %%
import sys
sys.path.insert(0, "..")
import pandas as pd
from lib import data, mapper_viz, config

# %%
for region in ["CDMX", "EDOMEX"]:
    df = pd.read_parquet(config.INTERMEDIOS_DIR / f"salud_{region}.parquet")
    P = data.puntos(df)
    color = df["per_ocu_num"].fillna(3).to_numpy()
    ruta, n_nodos, n_aristas = mapper_viz.construir_mapper(P, color, region)
    print(f"{region}: {ruta.name} | nodos={n_nodos} aristas={n_aristas}")

# %% [markdown]
# **Lectura:** EDOMEX genera un grafo más fragmentado (más nodos, menor
# conectividad relativa) → cobertura más dispersa y discontinua que CDMX. Abrir
# los HTML en `outputs/figuras/` para explorar interactivamente.
