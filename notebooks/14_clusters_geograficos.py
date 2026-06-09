# %% [markdown]
# # 14 — Fase 3: Selección y Agrupación Geográfica de Huecos Prioritarios
#
# Antes de optimizar ubicaciones, necesitamos responder:
# ¿En cuáles de los 161 huecos tiene sentido invertir?
#
# **Criterio de selección (basta cumplir UNO de los tres):**
#   - Tiempo > 10 min: el acceso es genuinamente problemático
#   - Sin seguro > p60: alto retorno social de una clínica nueva
#   - Persistencia > 400 m: vacío estructural real en la red
#
# Los huecos que no cumplen ninguno son micro-brechas con clínicas cercanas
# y poca población desprotegida — una clínica nueva no movería la aguja.
#
# **Agrupación DBSCAN:**
# Huecos geográficamente cercanos (≤ 1.5 km entre sí) se resuelven
# con la misma clínica nueva. Un cluster = una decisión de inversión.

# %%
import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from sklearn.cluster import DBSCAN
from pyproj import Transformer

from lib import config

REGIONES = ["CDMX", "EDOMEX"]
COLORES  = {"CDMX": "#4393c3", "EDOMEX": "#d6604d"}
_TR = Transformer.from_crs("EPSG:4326", config.CRS_METROS, always_xy=True)

# Umbrales de selección
TIEMPO_UMBRAL  = 10.0   # minutos
PERS_UMBRAL    = 400.0  # metros de persistencia
PSIN_PCT       = 60     # percentil de sin_seguro dentro de cada ciudad

# DBSCAN: huecos a ≤ 1500 m entre sí forman un cluster
DBSCAN_EPS     = 1500   # metros
DBSCAN_MIN_PTS = 1      # cada hueco está en algún cluster (no hay ruido)

# %% [markdown]
# ## 1. Filtrar huecos prioritarios

# %%
dfs_sel = {}
dfs_all = {}

for region in REGIONES:
    df = pd.read_parquet(config.INTERMEDIOS_DIR / f"huecos_score_{region}.parquet")
    df["x_utm"], df["y_utm"] = _TR.transform(df["lon"].values, df["lat"].values)
    dfs_all[region] = df.copy()

    # Percentil 60 de sin_seguro dentro de la región
    p60_psin = df["pob_sin_salud"].quantile(PSIN_PCT / 100)

    # Criterio OR: basta cumplir uno
    mask = (
        (df["tiempo_est_min"] > TIEMPO_UMBRAL)  |
        (df["pob_sin_salud"]  > p60_psin)       |
        (df["pers_m"]         > PERS_UMBRAL)
    )
    df_sel = df[mask].copy()

    # Etiqueta de eje dominante (para visualización)
    def eje_dominante(row, p60):
        ejes = []
        if row["tiempo_est_min"] > TIEMPO_UMBRAL: ejes.append("Tiempo")
        if row["pob_sin_salud"]  > p60:           ejes.append("Sin seguro")
        if row["pers_m"]         > PERS_UMBRAL:   ejes.append("Persistencia")
        return " + ".join(ejes) if ejes else "—"

    df_sel["eje_dominante"] = df_sel.apply(
        lambda r: eje_dominante(r, p60_psin), axis=1
    )

    dfs_sel[region] = df_sel
    n_desc = len(df) - len(df_sel)

    print(f"[{region}]")
    print(f"  Total habitados:      {len(df)}")
    print(f"  Seleccionados (MCLP): {len(df_sel)}  "
          f"({len(df_sel)/len(df)*100:.0f}%)")
    print(f"  Descartados:          {n_desc}  "
          f"(bajo en los 3 ejes — micro-brechas sin impacto)")
    print(f"  Umbral p60 sin seguro: {p60_psin:.0f} personas")
    print()

# %% [markdown]
# ## 2. DBSCAN — agrupar huecos cercanos

# %%
dfs_cluster = {}

for region in REGIONES:
    df = dfs_sel[region].copy()
    coords = df[["x_utm", "y_utm"]].values

    db = DBSCAN(eps=DBSCAN_EPS, min_samples=DBSCAN_MIN_PTS,
                metric="euclidean").fit(coords)
    df["cluster_id"] = db.labels_

    # Calcular centroide y score promedio de cada cluster
    resumen = df.groupby("cluster_id").agg(
        n_huecos       = ("hueco_id",        "count"),
        cx_utm         = ("x_utm",           "mean"),
        cy_utm         = ("y_utm",           "mean"),
        psin_total     = ("pob_sin_salud",   "sum"),
        pob_total      = ("pob_afectada",    "sum"),
        score_max      = ("score",           "max"),
        score_mean     = ("score",           "mean"),
        pers_max       = ("pers_m",          "max"),
        tiempo_max     = ("tiempo_est_min",  "max"),
    ).reset_index()

    # Urgencia del cluster = urgencia del hueco más crítico en él
    resumen = resumen.sort_values("score_max", ascending=False).reset_index(drop=True)
    resumen["rank_cluster"] = resumen.index + 1

    dfs_cluster[region] = {"huecos": df, "resumen": resumen}

    n_cl = len(resumen)
    print(f"[{region}]  {len(df)} huecos → {n_cl} clusters")
    print(f"  Cluster más urgente: {resumen.iloc[0]['n_huecos']} huecos, "
          f"score_max={resumen.iloc[0]['score_max']:.3f}, "
          f"psin={int(resumen.iloc[0]['psin_total']):,}")
    print()

# %% [markdown]
# ## 3. Mapa de clusters por ciudad

# %%
PALETA_CLUSTERS = plt.cm.tab20.colors   # hasta 20 colores distintos

fig, axes = plt.subplots(1, 2, figsize=(18, 9))
fig.suptitle(
    "Huecos prioritarios agrupados por proximidad geográfica (DBSCAN, radio 1.5 km)\n"
    "Cada color = un cluster = una decisión de inversión potencial",
    fontsize=13, fontweight="bold"
)

for ax, region in zip(axes, REGIONES):
    data    = dfs_cluster[region]
    df_hue  = data["huecos"]
    df_res  = data["resumen"]
    df_desc = dfs_all[region][~dfs_all[region]["hueco_id"].isin(df_hue["hueco_id"])]

    ax.set_facecolor("#f5f5f5")

    # Huecos descartados (gris pequeño)
    ax.scatter(df_desc["x_utm"], df_desc["y_utm"],
               s=15, c="#d0d0d0", alpha=0.5, zorder=1,
               label=f"Descartados ({len(df_desc)})")

    # Huecos seleccionados, coloreados por cluster
    n_clusters = df_hue["cluster_id"].nunique()
    for cl_id, sub in df_hue.groupby("cluster_id"):
        color = PALETA_CLUSTERS[cl_id % len(PALETA_CLUSTERS)]
        # Círculos proporcionales a persistencia
        for _, row in sub.iterrows():
            circ = plt.Circle((row["x_utm"], row["y_utm"]),
                              row["pers_m"], color=color,
                              alpha=0.55, zorder=2)
            ax.add_patch(circ)
        # Centroide del cluster
        info = df_res[df_res["cluster_id"] == cl_id].iloc[0]
        ax.plot(info["cx_utm"], info["cy_utm"], "o",
                color=color, markersize=9, markeredgecolor="#333",
                markeredgewidth=1.0, zorder=4)
        # Número de rank del cluster
        ax.text(info["cx_utm"], info["cy_utm"] + info["pers_max"] * 0.6,
                f"C{int(info['rank_cluster'])}",
                fontsize=7, ha="center", color="#222", fontweight="bold", zorder=5)

    ax.set_aspect("equal")
    ax.set_axis_off()
    ax.set_title(
        f"{region}  —  {len(df_hue)} huecos prioritarios → {n_clusters} clusters\n"
        f"(gris = {len(df_desc)} huecos descartados por baja urgencia en los 3 ejes)",
        fontsize=11, fontweight="bold", color=COLORES[region]
    )

# Leyenda
parches = [
    mpatches.Patch(color="#d0d0d0", alpha=0.6, label="Hueco descartado (bajo en 3 ejes)"),
    mpatches.Patch(color="#888", alpha=0.6, label="Hueco prioritario (cada color = cluster)"),
    plt.Line2D([0], [0], marker="o", color="w", markerfacecolor="#888",
               markersize=9, markeredgecolor="#333", label="Centroide del cluster"),
]
fig.legend(handles=parches, loc="lower center", ncol=3, fontsize=9,
           bbox_to_anchor=(0.5, 0.005), framealpha=0.95)

plt.tight_layout(rect=[0, 0.04, 1, 1])
ruta = config.FIGURAS_DIR / "clusters_geograficos.png"
plt.savefig(str(ruta), dpi=150, bbox_inches="tight", facecolor="white")
plt.show()
print(f"✓ {ruta}")

# %% [markdown]
# ## 4. Tabla resumen de clusters

# %%
print("\n" + "="*70)
print("RESUMEN DE CLUSTERS — CANDIDATOS A NUEVA CLÍNICA")
print("="*70)

for region in REGIONES:
    res = dfs_cluster[region]["resumen"]
    print(f"\n  [{region}]  {len(res)} clusters")
    print(f"  {'Cl':>3}  {'Huecos':>6}  {'Score':>6}  {'Pers.máx':>9}  "
          f"{'T.máx':>7}  {'Sin seguro':>10}  {'Pob.total':>9}")
    print(f"  {'—'*60}")
    for _, r in res.iterrows():
        print(f"  {int(r['rank_cluster']):3d}  "
              f"{int(r['n_huecos']):6d}  "
              f"{r['score_max']:6.3f}  "
              f"{r['pers_max']:9.0f}m  "
              f"{r['tiempo_max']:6.1f}m  "
              f"{int(r['psin_total']):>10,}  "
              f"{int(r['pob_total']):>9,}")

# %% [markdown]
# ## 5. Guardar para el siguiente notebook

# %%
from pyproj import Transformer
_TR_UTM_GEO = Transformer.from_crs(config.CRS_METROS, "EPSG:4326", always_xy=True)

for region in REGIONES:
    res = dfs_cluster[region]["resumen"].copy()
    lons, lats = _TR_UTM_GEO.transform(res["cx_utm"].values, res["cy_utm"].values)
    res["lat_centroide"] = lats
    res["lon_centroide"] = lons

    ruta_h = config.INTERMEDIOS_DIR / f"huecos_prioritarios_{region}.parquet"
    ruta_c = config.INTERMEDIOS_DIR / f"clusters_{region}.parquet"
    dfs_cluster[region]["huecos"].to_parquet(str(ruta_h), index=False)
    res.to_parquet(str(ruta_c), index=False)
    print(f"✓ {ruta_h}  ({len(dfs_cluster[region]['huecos'])} huecos)")
    print(f"✓ {ruta_c}  ({len(res)} clusters)")
