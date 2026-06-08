# %% [markdown]
# # 09 — Bifiltración: persistencia × densidad (Mejora 3)
#
# Los huecos H₁ del notebook 08 muestran zonas sin cobertura, pero no
# distinguen entre zonas sin cobertura con MUCHA gente (problema real)
# y zonas sin cobertura porque están despobladas (no urgente).
#
# Agregamos una segunda dimensión de filtración: la **densidad local de
# actividad económica** (KDE sobre las unidades DENUE), que sirve como
# proxy de densidad poblacional.
#
# Resultado: cada hueco queda clasificado en 4 categorías de acción real.

# %%
import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import numpy as np
import pandas as pd
from lib import data, tda, densidad, config

# %%
REGIONES     = ["CDMX", "EDOMEX"]
MIN_PERS     = 200.0   # metros — umbral mínimo para considerar hueco real
UMBRAL_PERS  = 500.0   # metros — umbral para "hueco grande" en la bifiltración

resultados = {}

for region in REGIONES:
    print(f"\n{'='*55}\n{region}")

    df = pd.read_parquet(config.INTERMEDIOS_DIR / f"salud_{region}.parquet")
    P  = data.puntos(df)

    # 1. Alpha complex y ciclos H₁
    print(f"  Alpha complex ({len(P):,} puntos)...")
    st = tda.alpha_complex(P)
    ciclos = tda.ciclos_H1(st, P, min_persistencia=MIN_PERS)
    print(f"  Huecos H₁: {len(ciclos)}")

    # 2. KDE sobre las unidades de salud
    print(f"  Estimando densidad KDE...")
    kde = densidad.estimar_densidad_kde(P)

    # 3. Clasificación bifiltrada
    df_bf = densidad.clasificar_bifiltracion(
        ciclos, kde,
        umbral_pers=UMBRAL_PERS,
        percentil_densidad=50,
    )

    print(f"\n  Resultados de bifiltración (pers_umbral={UMBRAL_PERS} m):")
    for prioridad in range(1, 5):
        sub = df_bf[df_bf["prioridad"] == prioridad]
        if len(sub) == 0:
            continue
        label = sub["label"].iloc[0]
        print(f"    [{prioridad}] {label}: {len(sub)} huecos")
        if prioridad <= 2 and len(sub) > 0:
            top = sub.nlargest(3, "pers_m")
            for _, row in top.iterrows():
                print(f"         pers={row['pers_m']/1000:.2f} km  "
                      f"densidad={row['densidad']*1e6:.2f}×10⁻⁶")

    resultados[region] = {"df": df, "P": P, "ciclos": ciclos, "df_bf": df_bf}

# %%
# --- Generar paneles ---
for region, res in resultados.items():
    print(f"\nGenerando panel {region}...")
    ruta = densidad.panel_bifiltracion(
        res["df_bf"], res["P"], region, umbral_pers=UMBRAL_PERS
    )
    print(f"  Guardado: {ruta}")

# %%
# --- Comparación entre regiones ---
print("\n" + "="*55)
print("COMPARACIÓN BIFILTRACIÓN — CDMX vs EDOMEX")
print("="*55)

from lib.densidad import PRIORIDAD_CRUZADA
for prioridad in range(1, 5):
    label = next(v["label"] for v in PRIORIDAD_CRUZADA.values()
                 if v["prioridad"] == prioridad)
    linea = f"  [{prioridad}] {label:42s}"
    for region in REGIONES:
        n = len(resultados[region]["df_bf"][
            resultados[region]["df_bf"]["prioridad"] == prioridad])
        linea += f"  {region}: {n:3d}"
    print(linea)

print("\nNota: Los huecos de prioridad [1] y [2] son los candidatos reales")
print("para nuevas unidades de salud o extensión de cobertura.")
