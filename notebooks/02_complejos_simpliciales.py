# %% [markdown]
# # 02 — Construcción de complejos simpliciales
#
# Por el volumen (~21k–31k puntos) usamos **Alpha complex** (Gudhi): subcomplejo
# de la triangulación de Delaunay, exacto y eficiente en 2D. El valor de
# filtración α es el radio² del circuncentro; en escala física, radio = √α (m).
#
# Liga investigación propia **Alpha_Complexes_Voronoi**: el Alpha complex se
# obtiene de la teselación de Voronoi / Delaunay y coincide con el complejo de
# Čech restringido a esa triangulación.
#
# A modo didáctico, se contrasta con un **Vietoris-Rips** sobre una submuestra.

# %%
import sys
sys.path.insert(0, "..")
import pandas as pd
from lib import data, tda, config

# %%
sts = {}
for region in ["CDMX", "EDOMEX"]:
    df = pd.read_parquet(config.INTERMEDIOS_DIR / f"salud_{region}.parquet")
    P = data.puntos(df)
    st = tda.alpha_complex(P)
    sts[region] = st
    print(f"{region}: {P.shape[0]:,} puntos -> {st.num_simplices():,} símplices")

# %% [markdown]
# ## Contraste didáctico: Vietoris-Rips sobre submuestra (500 pts)

# %%
df = pd.read_parquet(config.INTERMEDIOS_DIR / "salud_CDMX.parquet")
dgms, sub = tda.rips_submuestra(data.puntos(df), n=500, thresh=2000)
print("Rips submuestra: H0", dgms[0].shape, "H1", dgms[1].shape)

# %% [markdown]
# **Lectura:** Alpha escala a decenas de miles de puntos sin explotar (≈6·N
# símplices), mientras Rips es inviable sobre todo el conjunto y solo se usa
# sobre submuestra. Por eso el análisis principal usa Alpha.
