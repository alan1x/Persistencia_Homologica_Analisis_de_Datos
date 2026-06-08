# %% [markdown]
# # 06 — Geolocalización de huecos H₁ (Mejora 1)
#
# Convierte los ciclos persistentes de H₁ en **círculos geolocalizados** sobre
# un mapa real (Folium). Cada círculo rojo representa una zona rodeada de
# servicios de salud pero sin ninguno adentro. El radio del círculo es
# proporcional a la persistencia del hueco.
#
# **Cómo leer el mapa:**
# - Círculo grande = hueco de gran radio → zona amplia sin cobertura.
# - Círculo más opaco = más persistente (el hueco sobrevive a más escalas).
# - Click en cada círculo → popup con birth, death y persistencia en metros.

# %%
import sys
from pathlib import Path
# Funciona tanto si se corre desde la raíz del proyecto como desde notebooks/
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import pandas as pd
from lib import data, tda, geo, config

# %%
MIN_PERS = 200  # metros — umbral mínimo de persistencia para considerar un hueco real

resultados = {}

for region in ["CDMX", "EDOMEX"]:
    print(f"\n{'='*50}")
    print(f"Procesando {region}...")

    # Cargar datos limpios
    df = pd.read_parquet(config.INTERMEDIOS_DIR / f"salud_{region}.parquet")
    P = data.puntos(df)

    # Construir Alpha complex y calcular persistencia
    print(f"  Construyendo Alpha complex ({len(P):,} puntos)...")
    st = tda.alpha_complex(P)

    # Extraer ciclos H₁ con persistencia >= MIN_PERS
    print(f"  Extrayendo ciclos H₁ (min_pers={MIN_PERS} m)...")
    ciclos = tda.ciclos_H1(st, P, min_persistencia=MIN_PERS)
    print(f"  Huecos encontrados: {len(ciclos)}")

    if ciclos:
        print(f"  Top 5 huecos más persistentes:")
        for i, c in enumerate(ciclos[:5]):
            print(f"    {i+1}. persistencia={c['pers']:.0f} m  "
                  f"birth={c['birth']:.0f} m  death={c['death']:.0f} m")

    resultados[region] = {"df": df, "ciclos": ciclos}

# %%
# --- Generar mapas ---
for region, datos in resultados.items():
    df = datos["df"]
    ciclos = datos["ciclos"]

    if not ciclos:
        print(f"{region}: sin ciclos para mapear.")
        continue

    print(f"\nGenerando mapa {region} ({len(ciclos)} huecos)...")
    mapa = geo.mapa_huecos(df, ciclos, region)
    ruta = geo.guardar_mapa(mapa, region)
    print(f"  Guardado: {ruta}")

print("\nListo. Abre los HTML en outputs/figuras/ para explorar los mapas.")
