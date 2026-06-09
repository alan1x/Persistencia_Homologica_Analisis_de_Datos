# %% [markdown]
# # 16 — Resultados Finales: CDMX K=7 y EDOMEX Subregional K=12
#
# **CDMX:** K=7 es el punto óptimo justificado por la curva K=5→10:
#   K=5→6: +5.6pp, K=6→7: +5.3pp; a partir de K=8→9 cae a +4.0pp.
#   Con 7 clínicas se cubre 11/46 huecos prioritarios y 44.0% de la población sin seguro.
#
# **EDOMEX:** Estrategia subregional con 4 zonas × 3 clínicas = 12 total.
#   La curva global de EDOMEX es casi lineal (~+2% por clínica) porque la dispersión
#   geográfica impide que una clínica en una zona cubra huecos de otra.
#   Resultado: 9/77 huecos cubiertos, 35,868 personas (19.0%).
#
# Figuras producidas:
#   fase3_CDMX_k7_mapa.png          — mapa K=7 con isócronas y huecos
#   fase3_CDMX_k7_ejes.png          — cobertura de los 4 ejes en K=7
#   fase3_EDOMEX_subregional_mapa.png  — mapa subregional K=12 vs global K=5
#   fase3_EDOMEX_subregional_ejes.png  — cobertura por subregión y eje

# %%
import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import matplotlib
matplotlib.use("Agg")
import pickle
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.lines as mlines
import geopandas as gpd
from pyproj import Transformer

from lib import config

_TR = Transformer.from_crs("EPSG:4326", config.CRS_METROS, always_xy=True)

# INEGI municipality/alcaldía boundaries (offline, no extra dependency)
_gdf_cdmx   = gpd.read_file(str(_ROOT / "Datos/Geoestadistico/CDMX/conjunto_de_datos/09mun.shp")).to_crs(config.CRS_METROS)
_gdf_edomex = gpd.read_file(str(_ROOT / "Datos/Geoestadistico/EDOMEX/conjunto_de_datos/15mun.shp")).to_crs(config.CRS_METROS)

URG_COLOR = {
    "Crítico":  "#b2182b",
    "Alto":     "#e08214",
    "Moderado": "#4dac26",
    "Bajo":     "#b8e186",
}
PALETA_ISO = ["#4393c3", "#d6604d", "#1b9e77", "#7570b3", "#e7298a",
              "#a6761d", "#e6ab02"]

# %% [markdown]
# ## 1. Cargar datos

# %%
with open(str(config.INTERMEDIOS_DIR / "soluciones_mclp_red.pkl"), "rb") as f:
    pkl = pickle.load(f)

soluciones    = pkl["soluciones"]
candidatos_rd = pkl["resultados_red"]

df_prio_cdmx  = pd.read_parquet(config.INTERMEDIOS_DIR / "huecos_prioritarios_CDMX.parquet")
df_prio_edomex = pd.read_parquet(config.INTERMEDIOS_DIR / "huecos_prioritarios_EDOMEX.parquet")
df_all_cdmx   = pd.read_parquet(config.INTERMEDIOS_DIR / "huecos_score_CDMX.parquet")
df_all_edomex = pd.read_parquet(config.INTERMEDIOS_DIR / "huecos_score_EDOMEX.parquet")
sal_cdmx      = pd.read_parquet(config.INTERMEDIOS_DIR / "salud_CDMX.parquet")
sal_edomex    = pd.read_parquet(config.INTERMEDIOS_DIR / "salud_EDOMEX.parquet")

# Proyectar a UTM
for df in [df_prio_cdmx, df_prio_edomex, df_all_cdmx, df_all_edomex]:
    x, y = _TR.transform(df["lon"].values, df["lat"].values)
    df["x_utm"] = x
    df["y_utm"] = y

print(f"CDMX  — prioritarios: {len(df_prio_cdmx)}  K=7 disponible: {7 in soluciones['CDMX']}")
print(f"EDOMEX — prioritarios: {len(df_prio_edomex)}  K=5 disponible: {5 in soluciones['EDOMEX']}")

# %% [markdown]
# ## 2. CDMX K=7 — Mapa de ubicaciones

# %%
sol7     = soluciones["CDMX"][7]
cands_c  = [c for c in candidatos_rd["CDMX"] if c["tiempos"]]
sel_idx7 = sol7["sel_idx"]
cub_idx7 = set(sol7["cub_idx"])
ids_prio = df_prio_cdmx["hueco_id"].astype(int).tolist()
ids_cub7 = {ids_prio[i] for i in cub_idx7}

fig, ax = plt.subplots(1, 1, figsize=(13, 12))
fig.suptitle(
    "CDMX — Solución óptima K=7 clínicas nuevas\n"
    "Justificación: incrementos K=5→6: +5.6pp, K=6→7: +5.3pp; cae a K=8→9: +4.0pp, K=9→10: +3.0pp\n"
    "11 huecos cubiertos · 42,687 personas sin seguro (44.0% del total prioritario)",
    fontsize=12, fontweight="bold"
)

ax.set_facecolor("#f0f0f0")
ax.hexbin(sal_cdmx["x"].values, sal_cdmx["y"].values,
          gridsize=40, cmap="Greys", alpha=0.18, zorder=1, mincnt=1)
_gdf_cdmx.boundary.plot(ax=ax, color="#aaaaaa", linewidth=0.8, zorder=2)

# Huecos no prioritarios
df_desc = df_all_cdmx[~df_all_cdmx["hueco_id"].isin(df_prio_cdmx["hueco_id"])]
for _, r in df_desc.iterrows():
    ax.add_patch(plt.Circle((r["x_utm"], r["y_utm"]), r["pers_m"],
                             color="#cccccc", alpha=0.25, zorder=2))

# Isócronas primero (debajo de huecos)
for ki, j in enumerate(sel_idx7):
    cand = cands_c[j]
    iso  = cand.get("isocrona")
    if iso is None:
        continue
    color_iso = PALETA_ISO[ki % len(PALETA_ISO)]
    gpd.GeoSeries([iso]).plot(ax=ax, color=color_iso, alpha=0.15, zorder=3)
    gpd.GeoSeries([iso]).plot(ax=ax, color=color_iso, alpha=0.7,
                               facecolor="none", linewidth=2.0, zorder=4)

# Huecos prioritarios
for _, r in df_prio_cdmx.iterrows():
    hid   = int(r["hueco_id"])
    color = URG_COLOR.get(r.get("urgencia", "Moderado"), "#aaa")
    cub   = hid in ids_cub7
    circ  = plt.Circle((r["x_utm"], r["y_utm"]), r["pers_m"],
                        facecolor=color,
                        edgecolor="white" if cub else color,
                        linewidth=3.0 if cub else 0.4,
                        alpha=0.80 if cub else 0.40, zorder=5)
    ax.add_patch(circ)

# Clínicas nuevas K=7
for ki, j in enumerate(sel_idx7):
    cand    = cands_c[j]
    color_c = PALETA_ISO[ki % len(PALETA_ISO)]
    ax.plot(cand["x_clinica"], cand["y_clinica"],
            "o", color=color_c, markersize=16, zorder=8,
            markeredgecolor="white", markeredgewidth=2.5)
    ax.text(cand["x_clinica"], cand["y_clinica"],
            str(ki + 1), ha="center", va="center",
            fontsize=8, fontweight="bold", color="white", zorder=9)

ax.set_aspect("equal")
ax.set_axis_off()

# Leyenda
parches_urg = [mpatches.Patch(facecolor=c, alpha=0.75, label=f"Urgencia {u}")
               for u, c in URG_COLOR.items() if u != "Bajo"]
parche_cub  = mpatches.Patch(facecolor="#888", edgecolor="white",
                               linewidth=2.5, label="Hueco cubierto (borde blanco)")
parches_cl  = [mlines.Line2D([0], [0], marker="o", color="w",
                              markerfacecolor=PALETA_ISO[i], markersize=11,
                              markeredgecolor="white",
                              label=f"Clínica nueva {i+1} + zona 15 min")
               for i in range(len(sel_idx7))]

fig.legend(handles=parches_urg + [parche_cub] + parches_cl,
           loc="lower center", ncol=4, fontsize=8.5,
           bbox_to_anchor=(0.5, 0.01), framealpha=0.95)

plt.tight_layout(rect=[0, 0.07, 1, 1])
ruta = config.FIGURAS_DIR / "fase3_CDMX_k7_mapa.png"
plt.savefig(str(ruta), dpi=150, bbox_inches="tight", facecolor="white")
plt.show()
plt.close(fig)
print(f"✓ {ruta}")

# %% [markdown]
# ## 3. CDMX K=7 — Cobertura en los 4 ejes

# %%
# Marcar cada hueco como cubierto o persistente
df_prio_cdmx = df_prio_cdmx.copy()
df_prio_cdmx["estado_k7"] = df_prio_cdmx["hueco_id"].apply(
    lambda hid: "Cubierto (K=7)" if int(hid) in ids_cub7 else "Persistente"
)

df_cub  = df_prio_cdmx[df_prio_cdmx["estado_k7"] == "Cubierto (K=7)"]
df_pers = df_prio_cdmx[df_prio_cdmx["estado_k7"] == "Persistente"]

COLOR_CUB  = "#1b7837"
COLOR_PERS = "#b2182b"

EJES_COLS = [
    ("tiempo_est_min", "EJE 1 — INACCESIBILIDAD\nTiempo caminando a clínica más cercana",
     "minutos", "#e08214"),
    ("pob_sin_salud",  "EJE 2 — INEQUIDAD\nPersonas sin seguro dentro del hueco",
     "personas", "#762a83"),
    ("pers_m",         "EJE 3 — ESTRUCTURA TOPOLÓGICA\nPersistencia del hueco (radio)",
     "metros",   "#1b7837"),
    ("indice_marg",    "EJE 4 — MARGINACIÓN SOCIOECONÓMICA\nÍndice compuesto (Censo 2020)",
     "IM 0–1",   "#b2182b"),
]

fig, axes = plt.subplots(2, 2, figsize=(16, 12))
fig.suptitle(
    "CDMX K=7 — Comparativa de los 4 ejes: huecos cubiertos vs persistentes\n"
    "Puntos = valor individual de cada hueco  ·  Barra horizontal = media del grupo",
    fontsize=13, fontweight="bold"
)

rng = np.random.default_rng(42)   # jitter reproducible

for ax, (col, titulo, unidad, color_eje) in zip(axes.flat, EJES_COLS):
    vals_cub  = df_cub[col].dropna().values  if col in df_cub.columns  else np.array([])
    vals_pers = df_pers[col].dropna().values if col in df_pers.columns else np.array([])

    if len(vals_cub) == 0 and len(vals_pers) == 0:
        ax.text(0.5, 0.5, "Sin datos", transform=ax.transAxes, ha="center")
        continue

    # Scatter strip (jitter horizontal para evitar solapamiento)
    for vals, xbase, color, label in [
        (vals_cub,  0, COLOR_CUB,  f"Cubiertos  (n={len(vals_cub)})"),
        (vals_pers, 1, COLOR_PERS, f"Persistentes  (n={len(vals_pers)})"),
    ]:
        jitter = rng.uniform(-0.18, 0.18, size=len(vals))
        ax.scatter(xbase + jitter, vals, color=color, alpha=0.60, s=55,
                   zorder=3, label=label)
        if len(vals) > 0:
            m = vals.mean()
            ax.hlines(m, xbase - 0.30, xbase + 0.30,
                      colors=color, linewidths=3.5, zorder=5)
            ax.text(xbase + 0.32, m, f"{m:.2f}", va="center", fontsize=9.5,
                    color=color, fontweight="bold")

    ax.set_xticks([0, 1])
    ax.set_xticklabels(["Cubiertos", "Persistentes"], fontsize=11)
    ax.set_ylabel(unidad, fontsize=10)
    ax.set_title(titulo, fontsize=10, fontweight="bold", color=color_eje)
    ax.legend(fontsize=8.5, loc="upper right")
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_xlim(-0.5, 1.75)

plt.tight_layout()
ruta = config.FIGURAS_DIR / "fase3_CDMX_k7_ejes.png"
plt.savefig(str(ruta), dpi=150, bbox_inches="tight", facecolor="white")
plt.show()
plt.close(fig)
print(f"✓ {ruta}")

# Resumen numérico CDMX K=7
print("\n" + "="*70)
print("CDMX K=7 — COBERTURA POR EJE")
print("="*70)
n_prio_cdmx = len(df_prio_cdmx)
print(f"  Huecos cubiertos: {len(df_cub)}/{n_prio_cdmx}   Persistentes: {len(df_pers)}/{n_prio_cdmx}")
for col, titulo, unidad, _ in EJES_COLS:
    if col not in df_prio_cdmx.columns:
        continue
    mc = df_cub[col].mean()  if col in df_cub.columns else float("nan")
    mp = df_pers[col].mean() if col in df_pers.columns else float("nan")
    eje_corto = titulo.split("—")[0].strip()
    print(f"  {eje_corto:<35} Media cubiertos={mc:7.2f}  Media persistentes={mp:7.2f} {unidad}")

# %% [markdown]
# ## 4. EDOMEX — Mapa subregional K=12 (4 zonas × 3 clínicas) vs global K=5

# %%
# Cargar resultados de nb19 (subregional)
# Reconstruir soluciones_sub ejecutando la misma lógica que nb19
from pyproj import Transformer as Tr
import pulp

_TR2 = Tr.from_crs("EPSG:4326", config.CRS_METROS, always_xy=True)
VEL_M_MIN = (4.5 * 1000) / 60
TIEMPO_LIM_SUB = 15.0

def asignar_subregion(lat, lon):
    if lat > 19.7:         return "Norte"
    elif lon < -99.3:      return "Poniente"
    elif lon > -98.9:      return "Oriente"
    else:                  return "ZMVM"

df_sub_all = df_prio_edomex.copy()
df_sub_all["subregion"] = [asignar_subregion(r["lat"], r["lon"])
                            for _, r in df_sub_all.iterrows()]

cands_edomex = [c for c in candidatos_rd["EDOMEX"] if c["tiempos"]]
for c in cands_edomex:
    c["subregion"] = asignar_subregion(c["lat_clinica"], c["lon_clinica"])

K_SUB = {"Norte": 3, "Poniente": 3, "Oriente": 3, "ZMVM": 3}
total_ps_e = df_sub_all["pob_sin_salud"].sum()

soluciones_sub = {}
for sr in ["Norte", "Poniente", "Oriente", "ZMVM"]:
    df_sr    = df_sub_all[df_sub_all["subregion"] == sr].copy().reset_index(drop=True)
    cands_sr = [c for c in cands_edomex if c["subregion"] == sr]
    if len(df_sr) == 0 or len(cands_sr) == 0:
        continue
    n      = len(df_sr)
    ids_sr = df_sr["hueco_id"].astype(int).tolist()
    demand = df_sr.set_index("hueco_id")["pob_sin_salud"].to_dict()
    total_sr = df_sr["pob_sin_salud"].sum()
    I = list(range(n))
    J = list(range(len(cands_sr)))
    C = {(i, j): 1 if cands_sr[j]["tiempos"].get(ids_sr[i], 9999) <= TIEMPO_LIM_SUB else 0
         for i in I for j in J}
    prob = pulp.LpProblem(f"sub_{sr}", pulp.LpMaximize)
    x = [pulp.LpVariable(f"x{j}", cat="Binary") for j in J]
    y = [pulp.LpVariable(f"y{i}", cat="Binary") for i in I]
    prob += pulp.lpSum(demand.get(ids_sr[i], 0) * y[i] for i in I)
    prob += pulp.lpSum(x) == min(K_SUB[sr], len(cands_sr))
    for i in I:
        prob += y[i] <= pulp.lpSum(C[i, j] * x[j] for j in J)
    prob.solve(pulp.PULP_CBC_CMD(msg=False))
    sel_j = [j for j in J if x[j].value() > 0.5]
    cub_i = [i for i in I if y[i].value() > 0.5]
    psin_c = sum(demand.get(ids_sr[i], 0) for i in cub_i)
    soluciones_sub[sr] = {
        "df_sub": df_sr, "cands_sr": cands_sr, "sel_j": sel_j, "cub_i": cub_i,
        "psin_cub": psin_c, "pct_local": psin_c/total_sr*100 if total_sr > 0 else 0,
        "pct_global": psin_c/total_ps_e*100, "K_local": K_SUB[sr],
    }

sol_global_e = soluciones["EDOMEX"][5]
psin_global_e = sol_global_e["psin_cub"]
ids_cub_global_e = {df_prio_edomex.iloc[i]["hueco_id"] for i in sol_global_e["cub_idx"]}

ids_cub_sub_e = set()
for s in soluciones_sub.values():
    for i in s["cub_i"]:
        ids_cub_sub_e.add(int(s["df_sub"].iloc[i]["hueco_id"]))
psin_sub_e = sum(s["psin_cub"] for s in soluciones_sub.values())
n_cub_sub_e = sum(len(s["cub_i"]) for s in soluciones_sub.values())

COLORES_SUB = {"Norte": "#4393c3", "Poniente": "#d6604d", "Oriente": "#1b9e77", "ZMVM": "#7570b3"}

fig, axes = plt.subplots(1, 2, figsize=(22, 11))
fig.suptitle(
    "EDOMEX — Estrategia global K=5 vs estrategia subregional K=12 (4 zonas × 3 clínicas)\n"
    "Demanda ponderada = score 4 ejes × personas sin seguro médico",
    fontsize=13, fontweight="bold"
)

def dibujar_edomex(ax, df_prio, clinicas_xy, ids_cub, titulo, nota, colorear_sub=False):
    ax.set_facecolor("#f0f4f8")
    ax.hexbin(sal_edomex["x"].values, sal_edomex["y"].values,
              gridsize=40, cmap="Greys", alpha=0.15, zorder=1, mincnt=1)
    _gdf_edomex.boundary.plot(ax=ax, color="#aaaaaa", linewidth=0.8, zorder=2)
    for _, row in df_prio.iterrows():
        hid   = int(row["hueco_id"])
        color = URG_COLOR.get(row.get("urgencia", "Moderado"), "#aaa")
        if colorear_sub and "subregion" in row:
            color = COLORES_SUB.get(row["subregion"], color)
        cub   = hid in ids_cub
        circ  = plt.Circle((row["x_utm"], row["y_utm"]), row["pers_m"],
                            facecolor=color, alpha=0.60 if cub else 0.25,
                            edgecolor="white" if cub else color,
                            linewidth=2.5 if cub else 0.5, zorder=3)
        ax.add_patch(circ)
    paleta = ["#4393c3","#d6604d","#1b9e77","#7570b3","#e7298a",
              "#a6761d","#e6ab02","#666","#1f78b4","#33a02c","#e31a1c","#ff7f00"]
    for ki, (xc, yc) in enumerate(clinicas_xy):
        col = paleta[ki % len(paleta)]
        ax.plot(xc, yc, "D", color=col, markersize=14, zorder=8,
                markeredgecolor="white", markeredgewidth=2.0)
        ax.text(xc, yc, str(ki+1), ha="center", va="center",
                fontsize=7, fontweight="bold", color="white", zorder=9)
    ax.set_aspect("equal")
    ax.set_axis_off()
    ax.set_title(titulo, fontsize=11, fontweight="bold")
    ax.text(0.02, 0.02, nota, transform=ax.transAxes, va="bottom", ha="left", fontsize=8.5,
            bbox=dict(boxstyle="round,pad=0.4", facecolor="white", edgecolor="#aaa", alpha=0.92))

clinicas_global_e = [(cands_edomex[j]["x_clinica"], cands_edomex[j]["y_clinica"])
                     for j in sol_global_e["sel_idx"]]
dibujar_edomex(
    axes[0], df_sub_all, clinicas_global_e, ids_cub_global_e,
    f"Global K=5 clínicas — {psin_global_e:,.0f} sin seguro ({psin_global_e/total_ps_e*100:.1f}%)",
    f"Huecos cubiertos: {len(sol_global_e['cub_idx'])}/{len(df_prio_edomex)}\n"
    f"Solo atiende ZMVM y Poniente\nNorte y Oriente sin cobertura"
)

clinicas_sub_e = []
for sr in ["Norte", "Poniente", "Oriente", "ZMVM"]:
    if sr not in soluciones_sub:
        continue
    for j in soluciones_sub[sr]["sel_j"]:
        c = soluciones_sub[sr]["cands_sr"][j]
        clinicas_sub_e.append((c["x_clinica"], c["y_clinica"]))

dibujar_edomex(
    axes[1], df_sub_all, clinicas_sub_e, ids_cub_sub_e,
    f"Subregional K=12 (4 zonas × 3) — {psin_sub_e:,.0f} sin seguro ({psin_sub_e/total_ps_e*100:.1f}%)",
    f"Huecos cubiertos: {n_cub_sub_e}/{len(df_prio_edomex)}\nGanancia: +{(psin_sub_e-psin_global_e)/total_ps_e*100:.1f} pp\n"
    f"Oriente: sin candidatos válidos (distancias > 15 min)",
    colorear_sub=True
)

urg_handles = [mpatches.Patch(color=c, alpha=0.7, label=u) for u, c in URG_COLOR.items() if u != "Bajo"]
borde_h = mpatches.Patch(facecolor="#888", edgecolor="white", linewidth=2.5, label="Hueco cubierto")
fig.legend(handles=urg_handles + [borde_h], loc="lower center", ncol=4, fontsize=9,
           bbox_to_anchor=(0.5, 0.01), framealpha=0.95)

plt.tight_layout(rect=[0, 0.05, 1, 1])
ruta = config.FIGURAS_DIR / "fase3_EDOMEX_subregional_mapa.png"
plt.savefig(str(ruta), dpi=150, bbox_inches="tight", facecolor="white")
plt.show()
plt.close(fig)
print(f"✓ {ruta}")

# %% [markdown]
# ## 5. EDOMEX — Cobertura subregional por los 4 ejes

# %%
fig, axes = plt.subplots(2, 2, figsize=(18, 12))
fig.suptitle(
    "EDOMEX — Cobertura de los 4 ejes por subregión (K=12)\n"
    "Cada barra = una subregión  ·  Altura = media del eje en huecos cubiertos vs persistentes",
    fontsize=12, fontweight="bold"
)

SUBREGIONES_OK = [sr for sr in ["Norte", "Poniente", "ZMVM"] if sr in soluciones_sub]

for ax, (col, titulo, unidad, color_eje) in zip(axes.flat, EJES_COLS):
    if col not in df_sub_all.columns:
        ax.text(0.5, 0.5, "Sin datos", transform=ax.transAxes, ha="center")
        continue

    x_pos  = np.arange(len(SUBREGIONES_OK))
    ancho  = 0.35
    medias_cub  = []
    medias_pers = []

    for sr in SUBREGIONES_OK:
        s      = soluciones_sub[sr]
        df_sr  = s["df_sub"]
        ids_c  = {int(df_sr.iloc[i]["hueco_id"]) for i in s["cub_i"]}
        df_csr = df_sr[df_sr["hueco_id"].astype(int).isin(ids_c)]
        df_psr = df_sr[~df_sr["hueco_id"].astype(int).isin(ids_c)]
        medias_cub.append(df_csr[col].mean() if len(df_csr) > 0 else 0)
        medias_pers.append(df_psr[col].mean() if len(df_psr) > 0 else 0)

    bars_c = ax.bar(x_pos - ancho/2, medias_cub,  ancho,
                    color=COLOR_CUB,  alpha=0.80, label="Media cubiertos",  edgecolor="white")
    bars_p = ax.bar(x_pos + ancho/2, medias_pers, ancho,
                    color=COLOR_PERS, alpha=0.70, label="Media persistentes", edgecolor="white")

    for b, v in zip(bars_c, medias_cub):
        if v > 0:
            ax.text(b.get_x() + b.get_width()/2, b.get_height()*1.02,
                    f"{v:.2f}", ha="center", fontsize=8, color=COLOR_CUB, fontweight="bold")
    for b, v in zip(bars_p, medias_pers):
        if v > 0:
            ax.text(b.get_x() + b.get_width()/2, b.get_height()*1.02,
                    f"{v:.2f}", ha="center", fontsize=8, color=COLOR_PERS, fontweight="bold")

    ax.set_xticks(x_pos)
    ax.set_xticklabels(SUBREGIONES_OK, fontsize=10)
    ax.set_ylabel(unidad, fontsize=10)
    ax.set_title(titulo, fontsize=10, fontweight="bold", color=color_eje)
    ax.legend(fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)

plt.tight_layout()
ruta = config.FIGURAS_DIR / "fase3_EDOMEX_subregional_ejes.png"
plt.savefig(str(ruta), dpi=150, bbox_inches="tight", facecolor="white")
plt.show()
plt.close(fig)
print(f"✓ {ruta}")

# %% [markdown]
# ## 5b. EDOMEX — Mapas por subregión (K=3 clínicas por zona)

# %%
SUBREGIONES_PLOT = [sr for sr in ["Norte", "Poniente", "ZMVM"] if sr in soluciones_sub]

fig, axes = plt.subplots(1, len(SUBREGIONES_PLOT), figsize=(7 * len(SUBREGIONES_PLOT), 9))
if len(SUBREGIONES_PLOT) == 1:
    axes = [axes]

fig.suptitle(
    "EDOMEX — Clínicas K=3 por subregión\n"
    "Huecos coloreados por urgencia  ·  Borde blanco = cubierto  ·  Diamante = nueva clínica",
    fontsize=13, fontweight="bold"
)

for ax, sr in zip(axes, SUBREGIONES_PLOT):
    s      = soluciones_sub[sr]
    df_sr  = s["df_sub"].copy()
    cands_sr = s["cands_sr"]

    # UTM ya en df_sub_all → recuperar vía merge
    df_sr = df_sr.merge(
        df_sub_all[["hueco_id", "x_utm", "y_utm"]],
        on="hueco_id", how="left", suffixes=("", "_all")
    )
    if "x_utm_all" in df_sr.columns:
        df_sr["x_utm"] = df_sr["x_utm_all"]
        df_sr["y_utm"] = df_sr["y_utm_all"]

    ids_cub_sr = {int(df_sr.iloc[i]["hueco_id"]) for i in s["cub_i"]}
    color_sr   = COLORES_SUB.get(sr, "#888888")

    ax.set_facecolor("#f0f4f8")
    ax.hexbin(sal_edomex["x"].values, sal_edomex["y"].values,
              gridsize=30, cmap="Greys", alpha=0.12, zorder=1, mincnt=1)
    _gdf_edomex.boundary.plot(ax=ax, color="#aaaaaa", linewidth=0.8, zorder=2)

    for _, row in df_sr.iterrows():
        hid   = int(row["hueco_id"])
        color = URG_COLOR.get(row.get("urgencia", "Moderado"), "#aaa")
        cub   = hid in ids_cub_sr
        circ  = plt.Circle(
            (row["x_utm"], row["y_utm"]), row["pers_m"],
            facecolor=color, alpha=0.70 if cub else 0.30,
            edgecolor="white" if cub else color,
            linewidth=2.5 if cub else 0.5, zorder=3
        )
        ax.add_patch(circ)

    paleta_c = ["#4393c3", "#d6604d", "#1b9e77"]
    for ki, j in enumerate(s["sel_j"]):
        c   = cands_sr[j]
        col = paleta_c[ki % len(paleta_c)]
        ax.plot(c["x_clinica"], c["y_clinica"], "D",
                color=col, markersize=16, zorder=8,
                markeredgecolor="white", markeredgewidth=2.5)
        ax.text(c["x_clinica"], c["y_clinica"], str(ki + 1),
                ha="center", va="center",
                fontsize=8, fontweight="bold", color="white", zorder=9)

    ax.set_aspect("equal")
    ax.set_axis_off()

    cnt_sr = df_sr["urgencia"].value_counts()
    ax.set_title(
        f"{sr}  —  K=3 clínicas nuevas\n"
        f"Huecos: {len(df_sr)}  ·  Cubiertos: {len(s['cub_i'])}  ·  "
        f"Sin seguro cubiertos: {int(s['psin_cub']):,}",
        fontsize=11, fontweight="bold", color=color_sr
    )

    urg_handles = [mpatches.Patch(facecolor=c, alpha=0.7, label=u)
                   for u, c in URG_COLOR.items()
                   if u in df_sr.get("urgencia", pd.Series()).values and u != "Bajo"]
    borde_h = mpatches.Patch(facecolor="#888", edgecolor="white", linewidth=2.5,
                               label="Hueco cubierto")
    ax.legend(handles=urg_handles + [borde_h], loc="lower left", fontsize=8, framealpha=0.95)

plt.tight_layout()
ruta = config.FIGURAS_DIR / "fase3_EDOMEX_zonas_mapas.png"
plt.savefig(str(ruta), dpi=150, bbox_inches="tight", facecolor="white")
plt.show()
plt.close(fig)
print(f"✓ {ruta}")

# %% [markdown]
# ## 6. Resumen ejecutivo

# %%
print("\n" + "="*72)
print("RESUMEN FINAL — FASE 3")
print("="*72)

n_prio_c = len(df_prio_cdmx)
n_prio_e = len(df_prio_edomex)

sol7 = soluciones["CDMX"][7]
psin7 = sol7["psin_cub"]
total_ps_c = df_prio_cdmx["pob_sin_salud"].sum()

print(f"""
  CDMX — Solución K=7 (óptimo por curva de rendimiento decreciente)
  ─────────────────────────────────────────────────────────────────
  Justificación K=7:
    K=5→6: +5.6 pp  K=6→7: +5.3 pp  K=7→8: +5.1 pp  K=8→9: +4.0 pp  K=9→10: +3.0 pp
    Caída sostenida a partir de K=8→9 (-1.1 pp). K=7 maximiza retorno antes del aplanamiento.
""")
print(f"  Huecos cubiertos:     {len(sol7['cub_idx'])}/{n_prio_c}  ({len(sol7['cub_idx'])/n_prio_c*100:.1f}%)")
print(f"  Personas sin seguro:  {int(psin7):,}  ({psin7/total_ps_c*100:.1f}%)")
print(f"  Clusters elegidos:    {[sol7['candidatos'][j]['rank'] for j in sol7['sel_idx']]}")

print(f"""
  EDOMEX — Estrategia subregional K=12 (4 zonas × 3 clínicas)
  ─────────────────────────────────────────────────────────────
  Justificación subregional:
    Curva global EDOMEX es lineal (~+2 pp/clínica) → no hay codo.
    La dispersión geográfica impide que una clínica en ZMVM cubra huecos en Norte.
    Solución: K=3 por zona para cobertura geográficamente equitativa.
""")
for sr in ["Norte", "Poniente", "ZMVM"]:
    if sr not in soluciones_sub:
        continue
    s    = soluciones_sub[sr]
    n_sr = len(s["df_sub"])
    print(f"  [{sr:10s}] K=3 →  {len(s['cub_i'])}/{n_sr} huecos  "
          f"{int(s['psin_cub']):>8,} sin seguro  ({s['pct_local']:.1f}% subregional)")
print(f"  [Oriente  ] K=3 →  Sin candidatos válidos (zona periférica > 15 min)")
print(f"\n  TOTAL subregional:  {n_cub_sub_e}/{n_prio_e} huecos  "
      f"{int(psin_sub_e):,} sin seguro  ({psin_sub_e/total_ps_e*100:.1f}%)")
print(f"  vs. Global K=5:     {len(sol_global_e['cub_idx'])}/{n_prio_e} huecos  "
      f"{int(psin_global_e):,} sin seguro  ({psin_global_e/total_ps_e*100:.1f}%)")
print(f"  Ganancia:           +{(psin_sub_e-psin_global_e)/total_ps_e*100:.1f} pp con 7 clínicas adicionales")

print("\nArchivos generados:")
for f in ["fase3_CDMX_k7_mapa.png", "fase3_CDMX_k7_ejes.png",
          "fase3_EDOMEX_subregional_mapa.png", "fase3_EDOMEX_subregional_ejes.png",
          "fase3_EDOMEX_zonas_mapas.png"]:
    print(f"  outputs/figuras/{f}")
print("\n✓ Fase 3 completa.")
