# %% [markdown]
# # 17 — Validación Topológica: ¿Se cierran los huecos con K óptimo?
#
# CDMX:   K=7  clínicas  (K óptimo con ganancia marginal > 5 pp)
# EDOMEX: K=12 clínicas  (estrategia subregional: 4 zonas × 3 clínicas)
#
# Definición de cierre topológico:
#   Un hueco H₁ con centroide c y radio de persistencia r queda cerrado
#   cuando una nueva clínica cae a distancia d < r de c.
#   Esto garantiza que el nuevo punto triangula el interior del loop vacío,
#   convirtiendo el 1-ciclo en frontera de un 2-simplex.
#
# Clasificación:
#   Cerrado     : d < pers_m           — clínica dentro del radio topológico
#   Parcial     : pers_m ≤ d < 2×pers_m — clínica accesible pero no cierra
#   Persistente : d ≥ 2×pers_m         — requiere intervención adicional

# %%
import matplotlib
matplotlib.use("Agg")
import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import pickle
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.lines as mlines
from scipy.spatial import cKDTree
from pyproj import Transformer

from lib import config, tda

REGIONES  = ["CDMX", "EDOMEX"]
K_CDMX    = 7
K_EDOMEX  = 12   # 4 zonas × 3 clínicas
MIN_PERS  = 200.0

_TR = Transformer.from_crs("EPSG:4326", config.CRS_METROS, always_xy=True)
COLORES = {"CDMX": "#4393c3", "EDOMEX": "#d6604d"}

URG_COLOR = {
    "Crítico":  "#b2182b",
    "Alto":     "#e08214",
    "Moderado": "#4dac26",
}

ESTADO_COLOR = {
    "Cerrado":     "#1b7837",
    "Parcial":     "#f6a623",
    "Persistente": "#d6604d",
}
ESTADO_MARKER = {
    "Cerrado":     "v",
    "Parcial":     "D",
    "Persistente": "o",
}

# %% [markdown]
# ## 1. Cargar clínicas propuestas por región

# %%
# CDMX: K=7 desde resultados MCLP con red real
with open(str(config.INTERMEDIOS_DIR / "soluciones_mclp_red.pkl"), "rb") as f:
    pkl_mclp = pickle.load(f)

sol_cdmx  = pkl_mclp["soluciones"]["CDMX"][K_CDMX]
cands_cdmx = pkl_mclp["resultados_red"]["CDMX"]
clinicas_cdmx = np.array([
    [cands_cdmx[j]["x_clinica"], cands_cdmx[j]["y_clinica"]]
    for j in sol_cdmx["sel_idx"]
])
print(f"CDMX  K={K_CDMX}: {len(clinicas_cdmx)} clínicas  "
      f"(psin_cub={sol_cdmx['psin_cub']:,}  huecos_cub={len(sol_cdmx['cub_idx'])})")

# EDOMEX: K=12 subregional
with open(str(config.INTERMEDIOS_DIR / "clinicas_subregionales_EDOMEX.pkl"), "rb") as f:
    pkl_sub = pickle.load(f)

clinicas_edomex = np.array([
    [c["x_clinica"], c["y_clinica"]]
    for c in pkl_sub["clinicas_sub"]
])
print(f"EDOMEX K={K_EDOMEX}: {len(clinicas_edomex)} clínicas efectivas  "
      f"(Oriente sin candidatos → K efectivo = {len(clinicas_edomex)})")
print(f"  psin_cub={pkl_sub['psin_sub']:,}  huecos_cub={pkl_sub['n_cub_sub']}")

# Mapear región → array de clínicas
pts_clinicas = {"CDMX": clinicas_cdmx, "EDOMEX": clinicas_edomex}

# %% [markdown]
# ## 2. Calcular cierre topológico por hueco

# %%
datos = {}

for region in REGIONES:
    df_prio = pd.read_parquet(config.INTERMEDIOS_DIR / f"huecos_prioritarios_{region}.parquet")
    x_h, y_h = _TR.transform(df_prio["lon"].values, df_prio["lat"].values)
    df_prio = df_prio.copy()
    df_prio["x_utm"] = x_h
    df_prio["y_utm"] = y_h

    pts_nv = pts_clinicas[region]
    tree   = cKDTree(pts_nv)
    pts_huecos = np.column_stack([df_prio["x_utm"].values, df_prio["y_utm"].values])
    dists, idx_cerca = tree.query(pts_huecos, k=1)

    df_prio["dist_nueva"]   = dists
    df_prio["idx_clinica"]  = idx_cerca

    df_prio["estado"] = "Persistente"
    df_prio.loc[df_prio["dist_nueva"] < df_prio["pers_m"] * 2, "estado"] = "Parcial"
    df_prio.loc[df_prio["dist_nueva"] < df_prio["pers_m"],     "estado"] = "Cerrado"

    datos[region] = {"df_prio": df_prio, "pts_nv": pts_nv}

    cnt = df_prio["estado"].value_counts()
    K_label = f"K={K_CDMX}" if region == "CDMX" else f"K={K_EDOMEX} subregional"
    print(f"\n[{region}]  {len(df_prio)} huecos prioritarios  |  {K_label}")
    print(f"  Cerrado topológicamente:  {cnt.get('Cerrado', 0):3d}  "
          f"(nueva clínica < pers_m del centroide del hueco)")
    print(f"  Parcialmente cubierto:    {cnt.get('Parcial', 0):3d}  "
          f"(nueva clínica entre 1× y 2× pers_m)")
    print(f"  Persistente:              {cnt.get('Persistente', 0):3d}  "
          f"(nueva clínica a > 2× pers_m → requiere más intervención)")

    top3 = df_prio[df_prio["estado"] == "Persistente"].nlargest(3, "pers_m")
    if not top3.empty:
        print(f"\n  Top 3 huecos más urgentes que persisten:")
        for _, row in top3.iterrows():
            print(f"    pers={row['pers_m']:.0f}m  dist_nueva={row['dist_nueva']:.0f}m  "
                  f"urgencia={row['urgencia']}")

# %% [markdown]
# ## 3. Diagrama de persistencia — huecos coloreados por estado

# %%
fig, axes = plt.subplots(1, 2, figsize=(16, 7))
fig.suptitle(
    "Diagrama de Persistencia H₁ — Huecos Prioritarios\n"
    "CDMX K=7  ·  EDOMEX K=12 subregional (4 zonas × 3 clínicas)",
    fontsize=13, fontweight="bold"
)

for ax, region in zip(axes, REGIONES):
    df = datos[region]["df_prio"]
    color_ciudad = COLORES[region]
    lim = df["pers_m"].max() * 1.12

    ax.plot([0, lim], [0, lim], "k--", lw=0.8, alpha=0.4)

    for estado in ["Persistente", "Parcial", "Cerrado"]:
        sub = df[df["estado"] == estado]
        if sub.empty:
            continue
        ax.scatter(sub["pers_m"] * 0.0,
                   sub["pers_m"],
                   s=80,
                   color=ESTADO_COLOR[estado],
                   marker=ESTADO_MARKER[estado],
                   alpha=0.85,
                   label=f"{estado} ({len(sub)})",
                   zorder=3)

    ax.set_xlim(-lim * 0.05, lim * 0.5)
    ax.set_ylim(0, lim)
    ax.set_xlabel("Birth ≈ 0 (apilados para claridad)", fontsize=9)
    ax.set_ylabel("Persistencia — radio del hueco (m)", fontsize=10)
    K_label = f"K={K_CDMX}" if region == "CDMX" else f"K={K_EDOMEX} subregional"
    ax.set_title(f"{region}  —  {K_label}", fontsize=12, fontweight="bold", color=color_ciudad)
    ax.legend(fontsize=9, loc="upper right")
    ax.spines[["top", "right"]].set_visible(False)

    ax.axhline(MIN_PERS, color="#aaaaaa", lw=1.2, ls=":", label="min_pers=200m")
    ax.text(lim * 0.48, MIN_PERS + lim * 0.01, "min_pers", ha="right",
            fontsize=8, color="#aaa")

plt.tight_layout()
ruta = config.FIGURAS_DIR / "validacion_persistencia.png"
plt.savefig(str(ruta), dpi=150, bbox_inches="tight", facecolor="white")
plt.show()
print(f"✓ {ruta}", flush=True)

# %% [markdown]
# ## 4. Barras: distribución por urgencia y estado

# %%
fig, axes = plt.subplots(1, 2, figsize=(16, 7))
fig.suptitle(
    "Estado topológico de los huecos prioritarios tras la intervención óptima\n"
    "CDMX K=7  ·  EDOMEX K=12 subregional",
    fontsize=13, fontweight="bold"
)

for ax, region in zip(axes, REGIONES):
    df = datos[region]["df_prio"]
    color_ciudad = COLORES[region]

    urgencias = [u for u in ["Crítico", "Alto", "Moderado"] if u in df["urgencia"].values]
    estados   = ["Cerrado", "Parcial", "Persistente"]
    colores_e = [ESTADO_COLOR[e] for e in estados]

    x     = np.arange(len(urgencias))
    ancho = 0.25

    for i, (estado, col_e) in enumerate(zip(estados, colores_e)):
        vals = [len(df[(df["urgencia"] == u) & (df["estado"] == estado)]) for u in urgencias]
        bars = ax.bar(x + (i - 1) * ancho, vals, ancho, color=col_e, alpha=0.82,
                      label=estado, edgecolor="white")
        for b, v in zip(bars, vals):
            if v > 0:
                ax.text(b.get_x() + b.get_width()/2, b.get_height() + 0.1,
                        str(v), ha="center", va="bottom", fontsize=9, fontweight="bold",
                        color=col_e)

    ax.set_xticks(x)
    ax.set_xticklabels(urgencias, fontsize=11)
    ax.set_ylabel("Número de huecos", fontsize=10)
    K_label = f"K={K_CDMX}" if region == "CDMX" else f"K={K_EDOMEX} sub."
    ax.set_title(f"{region}  —  {K_label}", fontsize=12, fontweight="bold", color=color_ciudad)
    ax.legend(fontsize=9, title="Estado", title_fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)

plt.tight_layout()
ruta = config.FIGURAS_DIR / "validacion_impacto.png"
plt.savefig(str(ruta), dpi=150, bbox_inches="tight", facecolor="white")
plt.show()
print(f"✓ {ruta}", flush=True)

# %% [markdown]
# ## 5. Mapa: huecos con estado topológico y nuevas clínicas

# %%
fig, axes = plt.subplots(1, 2, figsize=(20, 10))
fig.suptitle(
    "Validación topológica — CDMX K=7  ·  EDOMEX K=12 subregional\n"
    "Radio del círculo = persistencia del hueco  |  "
    "Verde = cerrado  |  Naranja = parcial  |  Rojo = persistente",
    fontsize=13, fontweight="bold"
)

for ax, region in zip(axes, REGIONES):
    color_ciudad = COLORES[region]
    df   = datos[region]["df_prio"]
    pts_nv = datos[region]["pts_nv"]

    ax.set_facecolor("#f0f4f8")

    for estado in ["Cerrado", "Parcial", "Persistente"]:
        sub  = df[df["estado"] == estado]
        col  = ESTADO_COLOR[estado]
        zord = {"Cerrado": 4, "Parcial": 5, "Persistente": 6}[estado]

        for _, row in sub.iterrows():
            circ = plt.Circle(
                (row["x_utm"], row["y_utm"]),
                row["pers_m"],
                facecolor=col, alpha=0.45,
                edgecolor=col, linewidth=1.5,
                zorder=zord
            )
            ax.add_patch(circ)

            if estado in ("Cerrado", "Parcial"):
                idx_c = int(row["idx_clinica"])
                xc, yc = pts_nv[idx_c]
                ax.plot([row["x_utm"], xc], [row["y_utm"], yc],
                        color=col, lw=1.0, alpha=0.4, zorder=3)

    for i, (xn, yn) in enumerate(pts_nv):
        ax.plot(xn, yn, "D", color=color_ciudad,
                markersize=14, zorder=9,
                markeredgecolor="white", markeredgewidth=2.0)
        ax.text(xn, yn, str(i + 1),
                ha="center", va="center",
                fontsize=7, fontweight="bold", color="white", zorder=10)

    ax.set_aspect("equal")
    ax.set_axis_off()

    cnt = df["estado"].value_counts()
    K_label = f"K={K_CDMX}" if region == "CDMX" else f"K={K_EDOMEX} subregional"
    ax.set_title(
        f"{region} — {len(df)} huecos prioritarios  ·  {K_label}\n"
        f"Cerrados: {cnt.get('Cerrado', 0)}  |  "
        f"Parciales: {cnt.get('Parcial', 0)}  |  "
        f"Persistentes: {cnt.get('Persistente', 0)}",
        fontsize=11, fontweight="bold", color=color_ciudad
    )

    handles = [
        mpatches.Patch(color=ESTADO_COLOR["Cerrado"],     alpha=0.7,
                       label=f"Cerrado  ({cnt.get('Cerrado', 0)})  — clínica dentro del radio"),
        mpatches.Patch(color=ESTADO_COLOR["Parcial"],     alpha=0.7,
                       label=f"Parcial  ({cnt.get('Parcial', 0)})  — clínica entre 1×–2× radio"),
        mpatches.Patch(color=ESTADO_COLOR["Persistente"], alpha=0.7,
                       label=f"Persistente  ({cnt.get('Persistente', 0)})  — requiere más inversión"),
        mlines.Line2D([0], [0], marker="D", color="w",
                      markerfacecolor=color_ciudad, markersize=12,
                      markeredgecolor="white",
                      label=f"{len(pts_nv)} clínicas nuevas propuestas"),
    ]
    ax.legend(handles=handles, loc="lower left", fontsize=8.5, framealpha=0.95)

plt.tight_layout()
ruta = config.FIGURAS_DIR / "validacion_mapa.png"
plt.savefig(str(ruta), dpi=150, bbox_inches="tight", facecolor="white")
plt.show()
print(f"✓ {ruta}", flush=True)

# %% [markdown]
# ## 6. Resumen ejecutivo final

# %%
print("\n" + "="*72, flush=True)
print("VALIDACIÓN TOPOLÓGICA — RESUMEN FINAL", flush=True)
print("="*72, flush=True)

for region in REGIONES:
    df  = datos[region]["df_prio"]
    cnt = df["estado"].value_counts()
    n   = len(df)
    K_label = f"K={K_CDMX}" if region == "CDMX" else f"K={K_EDOMEX} subregional"
    K_real  = len(datos[region]["pts_nv"])

    pers_max_antes = df["pers_m"].max()
    pers_max_desp  = df[df["estado"] == "Persistente"]["pers_m"].max() if cnt.get("Persistente", 0) > 0 else 0
    pers_tot_antes = df["pers_m"].sum()
    pers_tot_desp  = df[df["estado"] == "Persistente"]["pers_m"].sum()

    pct_cerrado = cnt.get("Cerrado", 0) / n * 100
    pct_parcial = cnt.get("Parcial", 0) / n * 100

    print(f"\n  [{region}]  {n} huecos prioritarios  |  {K_label} ({K_real} efectivas)")
    print(f"  {'—'*60}")
    print(f"  Cerrados topológicamente: {cnt.get('Cerrado', 0):3d}/{n}  ({pct_cerrado:.0f}%)")
    print(f"  Parcialmente cubiertos:   {cnt.get('Parcial', 0):3d}/{n}  ({pct_parcial:.0f}%)")
    print(f"  Persistentes:             {cnt.get('Persistente', 0):3d}/{n}  "
          f"({100-pct_cerrado-pct_parcial:.0f}%)")
    print(f"  Pers. máx persistente:    {pers_max_desp:.0f} m  (antes: {pers_max_antes:.0f} m)")
    print(f"  Pers. total persistente:  {pers_tot_desp:.0f} m  "
          f"(antes: {pers_tot_antes:.0f} m, reducción: "
          f"{(pers_tot_antes-pers_tot_desp)/pers_tot_antes*100:.1f}%)")
