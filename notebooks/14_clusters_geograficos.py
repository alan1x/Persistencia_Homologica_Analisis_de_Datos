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

import matplotlib
matplotlib.use("Agg")
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import geopandas as gpd
from sklearn.cluster import DBSCAN
from pyproj import Transformer

from lib import config

REGIONES = ["CDMX", "EDOMEX"]
COLORES  = {"CDMX": "#4393c3", "EDOMEX": "#d6604d"}
_TR = Transformer.from_crs("EPSG:4326", config.CRS_METROS, always_xy=True)

_gdf_cdmx   = gpd.read_file(str(_ROOT / "Datos/Geoestadistico/CDMX/conjunto_de_datos/09mun.shp")).to_crs(config.CRS_METROS)
_gdf_edomex = gpd.read_file(str(_ROOT / "Datos/Geoestadistico/EDOMEX/conjunto_de_datos/15mun.shp")).to_crs(config.CRS_METROS)
_GDF_MUN = {"CDMX": _gdf_cdmx, "EDOMEX": _gdf_edomex}

# Umbrales de selección — 4 ejes (consistent con el scoring 25/25/25/25)
TIEMPO_UMBRAL  = 10.0   # minutos caminando a clínica más cercana
PERS_UMBRAL    = 400.0  # metros de persistencia topológica
PSIN_PCT       = 60     # percentil de sin_seguro dentro de cada ciudad
MARG_PCT       = 60     # percentil de indice_marg dentro de cada ciudad

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

    # Percentiles dentro de la región para cada eje
    p60_psin = df["pob_sin_salud"].quantile(PSIN_PCT / 100)
    p60_marg = df["indice_marg"].quantile(MARG_PCT / 100) if "indice_marg" in df.columns else 1.0

    # Criterio OR sobre los 4 ejes — basta cumplir uno para ser prioritario
    mask = (
        (df["tiempo_est_min"] > TIEMPO_UMBRAL)  |
        (df["pob_sin_salud"]  > p60_psin)       |
        (df["pers_m"]         > PERS_UMBRAL)    |
        (df["indice_marg"]    > p60_marg)
    )
    df_sel = df[mask].copy()

    # Etiqueta de eje dominante (para visualización)
    def eje_dominante(row, p60_ps, p60_mg):
        ejes = []
        if row["tiempo_est_min"] > TIEMPO_UMBRAL:  ejes.append("Tiempo")
        if row["pob_sin_salud"]  > p60_ps:         ejes.append("Sin seguro")
        if row["pers_m"]         > PERS_UMBRAL:    ejes.append("Persistencia")
        if "indice_marg" in row and row["indice_marg"] > p60_mg:
            ejes.append("Marginación")
        return " + ".join(ejes) if ejes else "—"

    df_sel["eje_dominante"] = df_sel.apply(
        lambda r: eje_dominante(r, p60_psin, p60_marg), axis=1
    )

    dfs_sel[region] = df_sel
    n_desc = len(df) - len(df_sel)

    print(f"[{region}]")
    print(f"  Total habitados:           {len(df)}")
    print(f"  Seleccionados (4 ejes OR): {len(df_sel)}  "
          f"({len(df_sel)/len(df)*100:.0f}%)")
    print(f"  Descartados:               {n_desc}  "
          f"(micro-brechas sin impacto en ningún eje)")
    print(f"  Umbral p60 sin seguro:  {p60_psin:.0f} personas")
    print(f"  Umbral p60 marginación: {p60_marg:.3f} IM")
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

# Colores de urgencia (igual que nb16)
URG_COLOR_CL = {
    "Crítico":  "#b2182b",
    "Alto":     "#e08214",
    "Moderado": "#4dac26",
    "Bajo":     "#b8e186",
}

fig, axes = plt.subplots(1, 2, figsize=(20, 10))
fig.suptitle(
    "Agrupación geográfica de huecos prioritarios (DBSCAN, radio 1.5 km)\n"
    "CRITERIO OR sobre 4 ejes: tiempo > 10 min  ·  sin seguro > p60  ·  persistencia > 400 m  ·  marginación > p60\n"
    "SELECCIONADOS (coloreados): cumplen ≥1 criterio  ·  NO PRIORITARIOS (grises con X): bajo en los 4 ejes\n"
    "Número = rank del cluster (C1 = mayor score compuesto)  ·  Contorno = urgencia (rojo=Crítico, naranja=Alto, verde=Moderado)",
    fontsize=10, fontweight="bold"
)

for ax, region in zip(axes, REGIONES):
    data    = dfs_cluster[region]
    df_hue  = data["huecos"]
    df_res  = data["resumen"]
    df_desc = dfs_all[region][~dfs_all[region]["hueco_id"].isin(df_hue["hueco_id"])]

    ax.set_facecolor("#f0f4f8")
    _GDF_MUN[region].boundary.plot(ax=ax, color="#aaaaaa", linewidth=0.8, zorder=1)

    # ── Huecos NO prioritarios: círculos grises translúcidos con borde punteado ──
    for _, row in df_desc.iterrows():
        circ = plt.Circle(
            (row["x_utm"], row["y_utm"]), row["pers_m"],
            facecolor="#d8d8d8", edgecolor="#aaaaaa",
            linewidth=1.0, linestyle=":", alpha=0.40, zorder=1
        )
        ax.add_patch(circ)
    # Marca "X" encima de cada hueco descartado
    ax.scatter(df_desc["x_utm"], df_desc["y_utm"],
               marker="x", s=20, c="#999999", linewidths=1.0,
               alpha=0.6, zorder=2, label=f"No prioritario ({len(df_desc)}): baja urgencia en los 4 ejes")

    # ── Huecos PRIORITARIOS agrupados por cluster ──
    n_clusters = df_hue["cluster_id"].nunique()
    for cl_id, sub in df_hue.groupby("cluster_id"):
        color_cl  = PALETA_CLUSTERS[cl_id % len(PALETA_CLUSTERS)]
        info      = df_res[df_res["cluster_id"] == cl_id].iloc[0]
        rank_cl   = int(info["rank_cluster"])

        for _, row in sub.iterrows():
            urg_color = URG_COLOR_CL.get(row.get("urgencia", "Moderado"), "#4dac26")
            # Relleno = color del cluster (identidad)
            circ_fill = plt.Circle(
                (row["x_utm"], row["y_utm"]), row["pers_m"],
                facecolor=color_cl, alpha=0.50, zorder=3
            )
            # Contorno = color de urgencia
            circ_edge = plt.Circle(
                (row["x_utm"], row["y_utm"]), row["pers_m"],
                facecolor="none", edgecolor=urg_color,
                linewidth=2.5, zorder=4
            )
            ax.add_patch(circ_fill)
            ax.add_patch(circ_edge)

        # Centroide del cluster: diamante con número de rank
        ax.plot(info["cx_utm"], info["cy_utm"], "D",
                color=color_cl, markersize=12,
                markeredgecolor="white", markeredgewidth=1.5, zorder=6)
        ax.text(info["cx_utm"], info["cy_utm"],
                f"C{rank_cl}", ha="center", va="center",
                fontsize=6.5, fontweight="bold", color="white", zorder=7)
        # Label con score encima del cluster
        ax.text(info["cx_utm"], info["cy_utm"] + info["pers_max"] * 1.1,
                f"C{rank_cl}  score={info['score_max']:.2f}",
                ha="center", fontsize=6, color="#333", zorder=7,
                bbox=dict(boxstyle="round,pad=0.1", facecolor="white", alpha=0.6, linewidth=0))

    ax.set_aspect("equal")
    ax.set_axis_off()
    ax.set_title(
        f"{region}  —  {len(df_hue)} huecos PRIORITARIOS → {n_clusters} clusters de inversión\n"
        f"{len(df_desc)} huecos NO prioritarios (gris con X, baja urgencia en los 4 ejes)",
        fontsize=11, fontweight="bold", color=COLORES[region]
    )

# Leyenda completa
parches_urg = [
    mpatches.Patch(facecolor="white", edgecolor=c, linewidth=2.5, label=f"Urgencia {u}")
    for u, c in URG_COLOR_CL.items() if u != "Bajo"
]
parche_noprio = mpatches.Patch(facecolor="#d8d8d8", edgecolor="#aaa",
                                linestyle=":", alpha=0.6,
                                label="No prioritario (gris): baja urgencia en los 4 ejes")
parche_cluster = plt.Line2D([0], [0], marker="D", color="w",
                             markerfacecolor="#555", markersize=11,
                             markeredgecolor="white",
                             label="Centroide cluster (C# = rank por score)")
parche_relleno = mpatches.Patch(color="#4393c3", alpha=0.5,
                                 label="Relleno = identidad del cluster (mismo color = misma decisión)")

fig.legend(
    handles=parches_urg + [parche_noprio, parche_cluster, parche_relleno],
    loc="lower center", ncol=4, fontsize=8.5,
    bbox_to_anchor=(0.5, 0.005), framealpha=0.95
)

plt.tight_layout(rect=[0, 0.07, 1, 1])
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
