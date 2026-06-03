# %% [markdown]
# # 03 — Persistencia homológica
#
# Calculamos la persistencia del Alpha complex e interpretamos las
# características topológicas (liga investigación **Grupos_Homologia**):
#
# - **H₀** (β₀): componentes conexas → fragmentación / agrupamiento de unidades.
# - **H₁** (β₁): ciclos/huecos → **zonas sin cobertura** rodeadas de servicios.
# - **H₂** (β₂): cavidades → ~0 en datos planos (esperado).
#
# Comparamos CDMX vs EDOMEX con distancias **bottleneck** y **Wasserstein**.

# %%
import sys
sys.path.insert(0, "..")
import numpy as np
import pandas as pd
from lib import data, tda, viz_tda, config

# %%
diags_r = {}
for region in ["CDMX", "EDOMEX"]:
    df = pd.read_parquet(config.INTERMEDIOS_DIR / f"salud_{region}.parquet")
    st = tda.alpha_complex(data.puntos(df))
    dr = tda.a_radio(tda.persistencia(st))
    diags_r[region] = dr
    ruta = viz_tda.panel_persistencia(dr, st, region)
    res = tda.resumen({d: dr[d] ** 2 for d in dr})  # resumen en alpha
    print(f"{region}: figura {ruta.name}")

# %% [markdown]
# ## Comparación cuantitativa CDMX vs EDOMEX (H₁)
# Filtramos clases con persistencia ≥ 200 m para que las distancias sean
# tratables y representen huecos reales (no ruido de escala fina).

# %%
def filtra(d, minp=200):
    d = d[np.isfinite(d[:, 1])]
    return d[(d[:, 1] - d[:, 0]) >= minp]

A = {1: filtra(diags_r["CDMX"][1])}
B = {1: filtra(diags_r["EDOMEX"][1])}
print("H1 persistente: CDMX", len(A[1]), "| EDOMEX", len(B[1]))
print(viz_tda.comparar_regiones(A, B, "CDMX", "EDOMEX", dim=1))

# %% [markdown]
# **Lectura:** EDOMEX presenta muchos más huecos persistentes (zonas habitadas
# sin servicios de salud cercanos) y de mayor radio que CDMX. Las distancias
# bottleneck/Wasserstein cuantifican esa diferencia estructural de cobertura.
