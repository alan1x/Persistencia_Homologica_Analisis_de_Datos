# %% [markdown]
# # 16 — Fase 3: Dashboard Final de Recomendaciones
#
# Visualización limpia de las soluciones MCLP con red real:
#
#   - Mapa por ciudad: huecos (urgencia) + clínicas propuestas K=3 y K=5
#     con isócronas reales de 15 min desde cada clínica nueva
#   - Tabla comparativa de impacto K=3 vs K=5
#   - Nota sobre la lección metodológica KDTree vs OSMnx
#
# Diseño de mapa:
#   - Fondo neutro con densidad de clínicas existentes como textura
#   - Huecos: círculos coloreados por urgencia (Crítico/Alto/Moderado)
#   - Huecos cubiertos: borde blanco grueso para indicar selección
#   - Isócronas: polígonos de colores distintos por clínica nueva
#   - Clínicas nuevas: punto circular sólido (sin estrella)

# %%
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
import matplotlib.colors as mcolors
import geopandas as gpd
from pyproj import Transformer

from lib import config

REGIONES   = ["CDMX", "EDOMEX"]
COLORES_C  = {"CDMX": "#4393c3", "EDOMEX": "#d6604d"}
TIEMPO_LIM = 15
K_SHOW     = [3, 5]   # solo mostrar K=3 y K=5

_TR_GEO_UTM = Transformer.from_crs("EPSG:4326", config.CRS_METROS, always_xy=True)

# Colores de urgencia de huecos
URG_COLOR = {
    "Crítico":  "#b2182b",
    "Alto":     "#e08214",
    "Moderado": "#4dac26",
    "Bajo":     "#b8e186",
}

# Paleta para isócronas de distintas clínicas
PALETA_ISO = ["#4393c3", "#d6604d", "#1b9e77", "#7570b3", "#e7298a"]

# %% [markdown]
# ## 1. Cargar datos

# %%
with open(str(config.INTERMEDIOS_DIR / "soluciones_mclp_red.pkl"), "rb") as f:
    datos_pkl = pickle.load(f)

soluciones    = datos_pkl["soluciones"]
resultados_red = datos_pkl["resultados_red"]

dfs_huecos = {r: pd.read_parquet(config.INTERMEDIOS_DIR / f"huecos_prioritarios_{r}.parquet")
              for r in REGIONES}
dfs_all    = {r: pd.read_parquet(config.INTERMEDIOS_DIR / f"huecos_score_{r}.parquet")
              for r in REGIONES}
salud      = {r: pd.read_parquet(config.INTERMEDIOS_DIR / f"salud_{r}.parquet")
              for r in REGIONES}

for region in REGIONES:
    dfs_huecos[region]["x_utm"], dfs_huecos[region]["y_utm"] = \
        _TR_GEO_UTM.transform(dfs_huecos[region]["lon"].values,
                               dfs_huecos[region]["lat"].values)
    dfs_all[region]["x_utm"], dfs_all[region]["y_utm"] = \
        _TR_GEO_UTM.transform(dfs_all[region]["lon"].values,
                               dfs_all[region]["lat"].values)

# %% [markdown]
# ## 2. Mapa por ciudad — K=3 y K=5 en paneles lado a lado

# %%
def dibujar_mapa_solucion(ax, region, K, sol, candidatos_ok, df_prio, df_all, clinicas):
    """Dibuja el mapa limpio de la solución MCLP para una ciudad y un K dado."""

    sel_idx  = sol["sel_idx"]
    cub_idx  = set(sol["cub_idx"])
    ids_prio = df_prio["hueco_id"].astype(int).tolist()
    ids_cub  = {ids_prio[i] for i in cub_idx}

    ax.set_facecolor("#f0f0f0")

    # Densidad de clínicas existentes como textura de fondo (hexbin)
    ax.hexbin(clinicas["x"].values, clinicas["y"].values,
              gridsize=40, cmap="Greys", alpha=0.18, zorder=1, mincnt=1)

    # Huecos no prioritarios (gris, pequeños)
    df_desc = df_all[~df_all["hueco_id"].isin(df_prio["hueco_id"])]
    for _, r in df_desc.iterrows():
        ax.add_patch(plt.Circle((r["x_utm"], r["y_utm"]), r["pers_m"],
                                color="#cccccc", alpha=0.30, zorder=2))

    # Isócronas de las clínicas seleccionadas (antes de los huecos para que queden debajo)
    clinicas_sel = [candidatos_ok[j] for j in sel_idx]
    for ki, cand in enumerate(clinicas_sel):
        iso = cand.get("isocrona")
        if iso is None:
            continue
        color_iso = PALETA_ISO[ki % len(PALETA_ISO)]
        gpd.GeoSeries([iso]).plot(ax=ax, color=color_iso, alpha=0.18, zorder=3)
        gpd.GeoSeries([iso]).plot(ax=ax, color=color_iso, alpha=0.7,
                                   facecolor="none", linewidth=2.0, zorder=4)

    # Huecos prioritarios
    for _, r in df_prio.iterrows():
        hid    = int(r["hueco_id"])
        color  = URG_COLOR.get(r["urgencia"], "#aaa")
        cubie  = hid in ids_cub
        lw     = 2.5 if cubie else 0.3
        ec     = "white" if cubie else color
        alpha  = 0.75 if cubie else 0.45
        circ   = plt.Circle((r["x_utm"], r["y_utm"]), r["pers_m"],
                             facecolor=color, edgecolor=ec, linewidth=lw,
                             alpha=alpha, zorder=5)
        ax.add_patch(circ)

    # Clínicas nuevas propuestas (puntos sólidos grandes)
    for ki, cand in enumerate(clinicas_sel):
        if cand["x_clinica"] is None:
            continue
        color_c = PALETA_ISO[ki % len(PALETA_ISO)]
        ax.plot(cand["x_clinica"], cand["y_clinica"],
                "o", color=color_c, markersize=14, zorder=8,
                markeredgecolor="white", markeredgewidth=2.0)
        # Número de clínica
        ax.text(cand["x_clinica"], cand["y_clinica"],
                str(ki + 1), ha="center", va="center",
                fontsize=7, fontweight="bold", color="white", zorder=9)

    ax.set_aspect("equal")
    ax.set_axis_off()

    # Estadísticas en recuadro
    psin_cub = sol["psin_cub"]
    psin_tot = df_prio["pob_sin_salud"].sum()
    pct      = psin_cub / psin_tot * 100 if psin_tot > 0 else 0
    n_cub    = len(cub_idx)
    n_tot    = len(df_prio)

    ax.text(0.02, 0.98,
            f"K = {K} clínicas nuevas\n"
            f"Huecos cubiertos: {n_cub}/{n_tot}\n"
            f"Sin seguro cubiertos: {int(psin_cub):,}\n"
            f"({pct:.1f}% del total prioritario)",
            transform=ax.transAxes, va="top", ha="left",
            fontsize=9, fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="white",
                      edgecolor="#555", alpha=0.92))


# %%
for region in REGIONES:
    df_prio    = dfs_huecos[region]
    df_all_r   = dfs_all[region]
    clin_r     = salud[region]
    candidatos_ok = [c for c in resultados_red[region] if c["tiempos"]]

    # Determinar K disponibles
    ks_disp = [K for K in K_SHOW if K in soluciones[region]]
    if not ks_disp:
        print(f"[{region}] Sin soluciones disponibles")
        continue

    n_cols = len(ks_disp)
    fig, axes = plt.subplots(1, n_cols, figsize=(10 * n_cols, 11))
    if n_cols == 1:
        axes = [axes]

    fig.suptitle(
        f"{region} — Ubicaciones óptimas de clínicas nuevas\n"
        f"Red vial real (OSMnx) · Demanda = score × personas sin seguro\n"
        f"Círculo coloreado = zona de cobertura real de 15 min desde cada clínica",
        fontsize=12, fontweight="bold"
    )

    for ax, K in zip(axes, ks_disp):
        sol = soluciones[region][K]
        dibujar_mapa_solucion(ax, region, K, sol, candidatos_ok,
                               df_prio, df_all_r, clin_r)
        ax.set_title(f"K = {K} clínicas nuevas", fontsize=12,
                     fontweight="bold", color=COLORES_C[region], pad=10)

    # Leyenda global
    parches_urg = [mpatches.Patch(facecolor=c, label=e, alpha=0.75)
                   for e, c in URG_COLOR.items() if e != "Bajo"]
    parches_iso = [mlines.Line2D([0], [0], marker="o", color="w",
                                  markerfacecolor=PALETA_ISO[i], markersize=11,
                                  markeredgecolor="white",
                                  label=f"Clínica nueva {i+1} + zona 15 min")
                   for i in range(min(5, len(candidatos_ok)))]
    parche_cub  = mpatches.Patch(facecolor="#888", edgecolor="white",
                                  linewidth=2.5, label="Hueco cubierto (borde blanco)")
    parche_desc = mpatches.Patch(facecolor="#cccccc", alpha=0.4,
                                  label="Hueco no prioritario")

    fig.legend(handles=parches_urg + [parche_cub, parche_desc] + parches_iso,
               loc="lower center", ncol=4, fontsize=8.5,
               bbox_to_anchor=(0.5, 0.01), framealpha=0.95)

    plt.tight_layout(rect=[0, 0.06, 1, 1])
    ruta = config.FIGURAS_DIR / f"fase3_mapa_{region}.png"
    plt.savefig(str(ruta), dpi=150, bbox_inches="tight", facecolor="white")
    plt.show()
    plt.close(fig)
    print(f"✓ {ruta}")

# %% [markdown]
# ## 3. Tabla comparativa K=3 vs K=5 por ciudad

# %%
fig, axes = plt.subplots(1, 2, figsize=(16, 7))
fig.suptitle(
    "Impacto incremental de agregar clínicas nuevas\n"
    "Demanda ponderada: score × personas sin seguro médico",
    fontsize=13, fontweight="bold"
)

for ax, region in zip(axes, REGIONES):
    df_prio   = dfs_huecos[region]
    total_h   = len(df_prio)
    total_ps  = df_prio["pob_sin_salud"].sum()
    ks_disp   = [K for K in [3, 4, 5] if K in soluciones[region]]

    n_hue = [len(soluciones[region][K]["cub_idx"]) for K in ks_disp]
    psin  = [soluciones[region][K]["psin_cub"]     for K in ks_disp]

    x     = np.arange(len(ks_disp))
    ancho = 0.38
    ax2   = ax.twinx()

    b1 = ax.bar(x - ancho/2, psin, ancho, color="#762a83", alpha=0.82,
                label="Sin seguro cubiertos", edgecolor="white")
    b2 = ax2.bar(x + ancho/2, n_hue, ancho, color="#1b7837", alpha=0.75,
                 label="Huecos cubiertos", edgecolor="white")

    for b, v in zip(b1, psin):
        pct = v / total_ps * 100 if total_ps > 0 else 0
        ax.text(b.get_x() + b.get_width()/2, b.get_height() + total_ps * 0.01,
                f"{pct:.1f}%", ha="center", va="bottom",
                fontsize=9, fontweight="bold", color="#762a83")

    for b, v in zip(b2, n_hue):
        ax2.text(b.get_x() + b.get_width()/2, b.get_height() + 0.3,
                 f"{v}/{total_h}", ha="center", va="bottom",
                 fontsize=9, fontweight="bold", color="#1b7837")

    ax.set_xticks(x)
    ax.set_xticklabels([f"K = {K}" for K in ks_disp], fontsize=11)
    ax.set_ylabel("Personas sin seguro cubiertos", color="#762a83", fontsize=10)
    ax2.set_ylabel("Huecos prioritarios cubiertos", color="#1b7837", fontsize=10)
    ax.set_title(f"{region}", fontsize=12, fontweight="bold", color=COLORES_C[region])
    ax.spines[["top"]].set_visible(False)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{int(v):,}"))

    # Leyenda combinada
    handles = [b1, b2]
    labels  = ["Sin seguro cubiertos", "Huecos cubiertos"]
    ax.legend(handles, labels, fontsize=9, loc="upper left")

plt.tight_layout()
ruta = config.FIGURAS_DIR / "fase3_impacto_k.png"
plt.savefig(str(ruta), dpi=150, bbox_inches="tight", facecolor="white")
plt.show()
print(f"✓ {ruta}")

# %% [markdown]
# ## 4. Resumen ejecutivo final

# %%
print("\n" + "="*72)
print("RESUMEN EJECUTIVO — FASE 3 COMPLETA")
print("="*72)

for region in REGIONES:
    df_prio  = dfs_huecos[region]
    total_ps = df_prio["pob_sin_salud"].sum()
    total_h  = len(df_prio)
    print(f"\n  [{region}]  {total_h} huecos prioritarios  |  "
          f"{int(total_ps):,} personas sin seguro en juego")
    print(f"  {'K':>3}  {'Huecos cubiertos':>18}  {'Sin seguro cubiertos':>22}  Clusters elegidos")
    print(f"  {'—'*68}")
    for K in [3, 4, 5]:
        if K not in soluciones[region]:
            continue
        sol  = soluciones[region][K]
        pct  = sol["psin_cub"] / total_ps * 100 if total_ps > 0 else 0
        sel  = [sol["candidatos"][j]["rank"] for j in sol["sel_idx"]]
        print(f"  {K:3d}  "
              f"{len(sol['cub_idx']):3d} / {total_h:<12}  "
              f"{int(sol['psin_cub']):>10,}  ({pct:5.1f}%)   "
              f"Clusters {sel}")

print(f"""
  Nota metodológica:
  Los tiempos de cobertura se estiman con distancia euclidiana × factor
  de desvío urbano 1.35 (estándar para zonas metropolitanas densas),
  equivalente a ≤ 1,125 m en línea recta para el umbral de 15 min.
  La demanda ponderada es score × personas sin seguro médico.
""")

print("Archivos generados:")
for region in REGIONES:
    print(f"  outputs/figuras/fase3_mapa_{region}.png   — mapas K=3 y K=5")
print("  outputs/figuras/fase3_impacto_k.png         — comparativa K=3,4,5")
print("  outputs/intermedios/recomendaciones_fase3.csv")
print("\n✓ Fase 3 completa.")
