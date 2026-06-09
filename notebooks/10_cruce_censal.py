# %% [markdown]
# # 10 — Cruce Censal: Huecos topológicos × Datos demográficos (Fase 1)
#
# Los notebooks anteriores identifican huecos H₁ como zonas sin cobertura
# de salud, pero dicen solo *dónde están* y *qué tan grandes son*.
#
# Este notebook da el salto de "análisis topológico puro" a
# **inteligencia accionable** cruzando cada hueco con los datos del
# **Censo de Población y Vivienda 2020** (INEGI) a nivel AGEB.
#
# Para cada hueco ahora sabremos:
# - **Cuántas personas** viven dentro (población afectada)
# - **Cuántas no tienen seguro médico** (PSINDER)
# - **Cuántos adultos mayores** hay (P_60YMAS)
# - **Nivel educativo** promedio (GRAPROES)
# - Un **índice de prioridad compuesto** de 0 a 100
#
# Esto permite pasar de "hay un hueco topológico" a
# "este hueco afecta a 25,000 personas sin seguro médico, prioridad CRÍTICA".

# %%
import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import numpy as np
import pandas as pd
from lib import data, tda, censo, config

# %%
REGIONES = ["CDMX", "EDOMEX"]
MIN_PERS = 200.0  # metros — umbral mínimo de persistencia

resultados = {}

# %% [markdown]
# ## 1. Construir AGEBs enriquecidas con Censo 2020

# %%
for region in REGIONES:
    print(f"\n{'='*60}")
    print(f"  CARGANDO DATOS CENSALES — {region}")
    print(f"{'='*60}")

    gdf_ageb = censo.construir_ageb_enriquecido(region)

    # Estadísticas generales del Censo
    pob_total = gdf_ageb["POBTOT"].sum()
    pob_sin = gdf_ageb["PSINDER"].sum()
    pct_sin = pob_sin / pob_total * 100 if pob_total > 0 else 0
    n_agebs = len(gdf_ageb)

    print(f"\n  Resumen censal {region}:")
    print(f"    AGEBs urbanas:           {n_agebs:,}")
    print(f"    Población total:         {int(pob_total):,}")
    print(f"    Sin seguro médico:       {int(pob_sin):,} ({pct_sin:.1f}%)")
    if "P_60YMAS" in gdf_ageb.columns:
        pob_60 = gdf_ageb["P_60YMAS"].sum()
        print(f"    Adultos mayores (60+):   {int(pob_60):,}")
    if "GRAPROES" in gdf_ageb.columns:
        mask = gdf_ageb["GRAPROES"].notna() & (gdf_ageb["POBTOT"] > 0)
        if mask.any():
            graproes_prom = (
                (gdf_ageb.loc[mask, "GRAPROES"] * gdf_ageb.loc[mask, "POBTOT"]).sum()
                / gdf_ageb.loc[mask, "POBTOT"].sum()
            )
            print(f"    Escolaridad promedio:    {graproes_prom:.2f} años")

    resultados[region] = {"gdf_ageb": gdf_ageb}

# %% [markdown]
# ## 2. Calcular huecos topológicos H₁ y cruzar con Censo

# %%
for region in REGIONES:
    print(f"\n{'='*60}")
    print(f"  CRUCE TOPOLÓGICO × CENSAL — {region}")
    print(f"{'='*60}")

    # Cargar datos de salud preprocesados
    df = pd.read_parquet(config.INTERMEDIOS_DIR / f"salud_{region}.parquet")
    P = data.puntos(df)

    # Alpha complex y ciclos H₁
    print(f"  Alpha complex ({len(P):,} puntos)...")
    st = tda.alpha_complex(P)
    ciclos = tda.ciclos_H1(st, P, min_persistencia=MIN_PERS)
    print(f"  Huecos H₁ (pers ≥ {MIN_PERS}m): {len(ciclos)}")

    # Cruce espacial con AGEBs censales
    print(f"  Cruzando huecos con AGEBs censales...")
    gdf_ageb = resultados[region]["gdf_ageb"]
    df_cruce = censo.cruzar_huecos_con_censo(
        ciclos, gdf_ageb, region, min_persistencia=MIN_PERS
    )

    # Índice de prioridad compuesto
    df_prioridad = censo.calcular_indice_prioridad(df_cruce)

    resultados[region]["df"] = df
    resultados[region]["P"] = P
    resultados[region]["ciclos"] = ciclos
    resultados[region]["df_cruce"] = df_cruce
    resultados[region]["df_prioridad"] = df_prioridad

# %% [markdown]
# ## 3. Resultados: Ranking de huecos por prioridad censal

# %%
for region in REGIONES:
    df_pri = resultados[region]["df_prioridad"]

    print(f"\n{'='*60}")
    print(f"  RANKING DE PRIORIDAD — {region}")
    print(f"{'='*60}")

    # Resumen por nivel de prioridad
    print(f"\n  Distribución por nivel de prioridad:")
    for nivel in ["Crítico", "Alto", "Moderado", "Bajo"]:
        sub = df_pri[df_pri["nivel_prioridad"] == nivel]
        if len(sub) == 0:
            print(f"    {nivel:12s}: 0 huecos")
            continue
        pob = sub["pob_afectada"].sum()
        sin = sub["pob_sin_salud"].sum()
        print(f"    {nivel:12s}: {len(sub):3d} huecos  |  "
              f"Población: {int(pob):>8,}  |  Sin seguro: {int(sin):>7,}")

    # Top 10 huecos más críticos
    print(f"\n  Top 10 huecos con mayor prioridad:")
    print(f"  {'#':>3s}  {'Prioridad':>9s}  {'Nivel':>9s}  {'Pers(m)':>8s}  "
          f"{'Población':>10s}  {'Sin seguro':>10s}  {'%':>5s}  {'60+':>6s}  {'Esc.':>5s}")
    print(f"  {'—'*85}")

    for _, row in df_pri.head(10).iterrows():
        print(f"  {int(row['hueco_id']):3d}  "
              f"{row['indice_prioridad']:9.1f}  "
              f"{str(row['nivel_prioridad']):>9s}  "
              f"{row['pers_m']:8.0f}  "
              f"{int(row['pob_afectada']):>10,}  "
              f"{int(row['pob_sin_salud']):>10,}  "
              f"{row['pct_sin_salud_prom']:5.1f}  "
              f"{int(row['pob_60_mas']):>6,}  "
              f"{row['graproes_prom']:>5}")

# %% [markdown]
# ## 4. Comparación entre regiones

# %%
print(f"\n{'='*60}")
print("  COMPARACIÓN CENSAL: CDMX vs EDOMEX")
print(f"{'='*60}\n")

metricas = []
for region in REGIONES:
    df_pri = resultados[region]["df_prioridad"]
    metricas.append({
        "Región": region,
        "Huecos totales": len(df_pri),
        "Huecos Críticos": len(df_pri[df_pri["nivel_prioridad"] == "Crítico"]),
        "Huecos Altos": len(df_pri[df_pri["nivel_prioridad"] == "Alto"]),
        "Población total afectada": int(df_pri["pob_afectada"].sum()),
        "Población sin seguro": int(df_pri["pob_sin_salud"].sum()),
        "Pob. 60+ afectada": int(df_pri["pob_60_mas"].sum()),
        "Hueco peor (pers m)": f"{df_pri['pers_m'].max():.0f}",
        "Hueco peor (pob)": f"{int(df_pri['pob_afectada'].max()):,}",
    })

df_comp = pd.DataFrame(metricas).T
df_comp.columns = df_comp.iloc[0]
df_comp = df_comp.iloc[1:]
print(df_comp.to_string())

# %% [markdown]
# ## 5. Generar mapas interactivos enriquecidos

# %%
for region in REGIONES:
    print(f"\n  Generando mapa censal {region}...")
    mapa = censo.mapa_huecos_censales(
        resultados[region]["df_prioridad"],
        resultados[region]["gdf_ageb"],
        resultados[region]["df"],
        region,
    )
    censo.guardar_mapa_censal(mapa, region)

# %% [markdown]
# ## 6. Guardar resultados intermedios

# %%
for region in REGIONES:
    ruta = config.INTERMEDIOS_DIR / f"huecos_censal_{region}.parquet"
    resultados[region]["df_prioridad"].to_parquet(str(ruta), index=False)
    print(f"  Guardado: {ruta}")

print("\n✓ Cruce censal completado. Los huecos ahora tienen contexto demográfico real.")
print("  Los mapas interactivos están en outputs/figuras/huecos_censal_*.html")
