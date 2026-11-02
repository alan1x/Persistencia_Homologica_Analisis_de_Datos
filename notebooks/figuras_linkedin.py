# %% [markdown]
# # Figuras para LinkedIn — versión divulgativa (ES + EN)
#
# 3 gráficas limpias, con el objetivo enmarcado en cada una, pensadas para
# que cualquier persona (no solo data scientists) entienda los resultados.
# Se generan en español e inglés (sufijo _en):
#
#   linkedin_1_comparacion.png / _en  — ¿A quién le llegamos? (cubiertos vs no)
#   linkedin_2_mapa_cdmx.png   / _en  — Dónde construir en CDMX
#   linkedin_3_resultados.png  / _en  — Resultados de las dos ciudades + mensaje honesto
#
# Formato cuadrado/vertical a 150 dpi → se ven nítidas en el feed móvil.

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
from matplotlib.patches import FancyBboxPatch
import geopandas as gpd
from pyproj import Transformer

from lib import config

# ── Identidad visual ─────────────────────────────────────────────────────────
AZUL    = "#1f4e79"
AZUL_CL = "#2e75b6"
VERDE   = "#1b7837"   # huecos que SÍ atendemos
ROJO    = "#b2182b"   # huecos que quedan fuera
GRIS    = "#5a5a5a"
plt.rcParams["font.family"]    = "DejaVu Sans"
plt.rcParams["axes.edgecolor"] = "#cccccc"

_TR = Transformer.from_crs("EPSG:4326", config.CRS_METROS, always_xy=True)

# ── Textos por idioma ────────────────────────────────────────────────────────
STRINGS = {
    "es": {
        "suffix": "",
        "fuente": ("Fuente: DENUE 2023 · Censo 2020 · OpenStreetMap   |   "
                   "Método: Análisis Topológico de Datos + Optimización (MCLP)"),
        # Figura 1
        "f1_titulo": "¿A quién le llegan las 7 nuevas clínicas en CDMX?",
        "f1_sub": "Comparación de los huecos que SÍ atendemos (11) frente a los que quedan fuera (35)",
        "f1_metricas": [
            ("Personas sin seguro\npor hueco (promedio)", "{:,.0f}",
             "Atendemos al DOBLE de\ngente sin seguro"),
            ("Nivel de marginación\n(índice 0 a 1)", "{:.2f}",
             "Priorizamos las zonas\nmás vulnerables"),
            ("Tiempo a la clínica\nmás cercana (minutos)", "{:.1f}",
             "Los más lejanos son\nperiféricos y con poca gente"),
        ],
        "f1_xticks": ["Atendidos", "Sin\natender"],
        "f1_leg_cub": "Huecos atendidos por las 7 clínicas",
        "f1_leg_pers": "Huecos que quedan fuera (siguiente etapa)",
        # Figura 2
        "f2_titulo": "Dónde construir en la Ciudad de México",
        "f2_sub": "7 clínicas nuevas → 42,687 personas sin seguro cubiertas (44% de la población prioritaria)",
        "f2_leg": [
            "Nueva clínica propuesta",
            "Zona alcanzable caminando en 15 min",
            "Desierto de salud atendido",
            "Desierto pendiente (siguiente etapa)",
        ],
        # Figura 3
        "f3_titulo": "Resultados: priorizar con datos, no tapar todos los huecos",
        "f3_sub": "Entre cientos de vacíos, identificamos y atendemos primero los más dañinos para cada municipio",
        "f3_tarjetas": [
            ("CIUDAD DE MÉXICO", "7", "clínicas nuevas",
             "42,687", "personas sin seguro cubiertas",
             "44%", "de la población prioritaria"),
            ("ESTADO DE MÉXICO", "9", "clínicas ubicables",
             "35,868", "personas sin seguro cubiertas",
             "por zonas", "huecos demasiado dispersos\npara un solo punto óptimo"),
        ],
        "f3_mensaje": "No buscamos cobertura total: buscamos el mayor impacto posible con un presupuesto limitado.",
    },
    "en": {
        "suffix": "_en",
        "fuente": ("Source: DENUE 2023 · Census 2020 · OpenStreetMap   |   "
                   "Method: Topological Data Analysis + Optimization (MCLP)"),
        # Figure 1
        "f1_titulo": "Who do the 7 new clinics in Mexico City reach?",
        "f1_sub": "Gaps we DO address (11) vs. gaps left out (35)",
        "f1_metricas": [
            ("Uninsured people\nper gap (average)", "{:,.0f}",
             "We reach TWICE as many\nuninsured people"),
            ("Marginalization level\n(index 0 to 1)", "{:.2f}",
             "We prioritize the most\nvulnerable areas"),
            ("Time to the nearest\nclinic (minutes)", "{:.1f}",
             "The farthest ones are\nperipheral with few people"),
        ],
        "f1_xticks": ["Addressed", "Left\nout"],
        "f1_leg_cub": "Gaps addressed by the 7 clinics",
        "f1_leg_pers": "Gaps left out (next phase)",
        # Figure 2
        "f2_titulo": "Where to build in Mexico City",
        "f2_sub": "7 new clinics → 42,687 uninsured people covered (44% of the priority population)",
        "f2_leg": [
            "Proposed new clinic",
            "Area reachable on foot within 15 min",
            "Health desert addressed",
            "Pending desert (next phase)",
        ],
        # Figure 3
        "f3_titulo": "Results: prioritize with data, not plug every gap",
        "f3_sub": "Among hundreds of gaps, we identify and address the most harmful ones for each municipality first",
        "f3_tarjetas": [
            ("MEXICO CITY", "7", "new clinics",
             "42,687", "uninsured people covered",
             "44%", "of the priority population"),
            ("STATE OF MEXICO", "9", "placeable clinics",
             "35,868", "uninsured people covered",
             "by zones", "gaps too scattered\nfor a single optimum"),
        ],
        "f3_mensaje": "We don't aim for full coverage: we aim for the greatest impact with a limited budget.",
    },
}

def marco_titulo(fig, titulo, subtitulo):
    """Banda de título enmarcada arriba de la figura (el 'objetivo' del gráfico)."""
    fig.text(0.5, 0.965, titulo, ha="center", va="top",
             fontsize=20, fontweight="bold", color=AZUL)
    fig.text(0.5, 0.915, subtitulo, ha="center", va="top",
             fontsize=12.5, color=GRIS)

def pie_fuente(fig, T):
    fig.text(0.5, 0.015, T["fuente"],
             ha="center", va="bottom", fontsize=9, color="#999999")

# %% [markdown]
# ## Cargar datos

# %%
with open(str(config.INTERMEDIOS_DIR / "soluciones_mclp_red.pkl"), "rb") as f:
    pkl = pickle.load(f)
soluciones    = pkl["soluciones"]
candidatos_rd = pkl["resultados_red"]

df_prio_cdmx = pd.read_parquet(config.INTERMEDIOS_DIR / "huecos_prioritarios_CDMX.parquet")
df_all_cdmx  = pd.read_parquet(config.INTERMEDIOS_DIR / "huecos_score_CDMX.parquet")
sal_cdmx     = pd.read_parquet(config.INTERMEDIOS_DIR / "salud_CDMX.parquet")

for df in [df_prio_cdmx, df_all_cdmx]:
    x, y = _TR.transform(df["lon"].values, df["lat"].values)
    df["x_utm"], df["y_utm"] = x, y

sol7     = soluciones["CDMX"][7]
ids_prio = df_prio_cdmx["hueco_id"].astype(int).tolist()
ids_cub7 = {ids_prio[i] for i in sol7["cub_idx"]}
df_prio_cdmx["cub"] = df_prio_cdmx["hueco_id"].astype(int).isin(ids_cub7)

df_cub  = df_prio_cdmx[df_prio_cdmx["cub"]]
df_pers = df_prio_cdmx[~df_prio_cdmx["cub"]]

# Medias para la comparación (idénticas en ambos idiomas)
VALS = {
    "sin_seguro": (df_cub["pob_sin_salud"].mean(),  df_pers["pob_sin_salud"].mean()),
    "marg":       (df_cub["indice_marg"].mean(),    df_pers["indice_marg"].mean()),
    "tiempo":     (df_cub["tiempo_est_min"].mean(), df_pers["tiempo_est_min"].mean()),
}

PALETA = ["#1f4e79", "#d6604d", "#1b9e77", "#7570b3", "#e7298a", "#a6761d", "#e6ab02"]
_gdf_cdmx = gpd.read_file(
    str(_ROOT / "Datos/Geoestadistico/CDMX/conjunto_de_datos/09mun.shp")
).to_crs(config.CRS_METROS)
cands_c  = [c for c in candidatos_rd["CDMX"] if c["tiempos"]]
sel_idx7 = sol7["sel_idx"]


# %% [markdown]
# ## Figura 1 — ¿A quién le llegamos?

# %%
def figura_1(T):
    fig = plt.figure(figsize=(11, 9))
    marco_titulo(fig, T["f1_titulo"], T["f1_sub"])

    valores = [VALS["sin_seguro"], VALS["marg"], VALS["tiempo"]]
    x_centros = [0.185, 0.505, 0.825]
    axes = [fig.add_axes([xc - 0.115, 0.34, 0.23, 0.44]) for xc in x_centros]

    for ax, xc, (titulo, fmt, nota), (v_cub, v_pers) in zip(
            axes, x_centros, T["f1_metricas"], valores):
        ax.bar([0, 1], [v_cub, v_pers],
               color=[VERDE, "#bbbbbb"], width=0.62,
               edgecolor="white", linewidth=1.5, zorder=3)
        for x_, v in zip([0, 1], [v_cub, v_pers]):
            ax.text(x_, v, "  " + fmt.format(v), ha="center", va="bottom",
                    fontsize=15, fontweight="bold",
                    color=VERDE if x_ == 0 else GRIS)
        ax.set_xticks([0, 1])
        ax.set_xticklabels(T["f1_xticks"], fontsize=11.5)
        ax.set_title(titulo, fontsize=12.5, fontweight="bold", color=AZUL, pad=10)
        ax.set_ylim(0, max(v_cub, v_pers) * 1.30)
        ax.set_yticks([])
        for s in ["top", "right", "left"]:
            ax.spines[s].set_visible(False)
        fig.text(xc, 0.235, nota, ha="center", va="top",
                 fontsize=10, color=GRIS, style="italic")

    fig.legend(
        handles=[
            mpatches.Patch(color=VERDE,    label=T["f1_leg_cub"]),
            mpatches.Patch(color="#bbbbbb", label=T["f1_leg_pers"]),
        ],
        loc="lower center", ncol=2, fontsize=11, frameon=False,
        bbox_to_anchor=(0.5, 0.085),
    )
    pie_fuente(fig, T)
    ruta = config.FIGURAS_DIR / f"linkedin_1_comparacion{T['suffix']}.png"
    plt.savefig(str(ruta), dpi=150, facecolor="white")
    plt.close(fig)
    print(f"OK {ruta}")


# %% [markdown]
# ## Figura 2 — Dónde construir en CDMX

# %%
def figura_2(T):
    fig = plt.figure(figsize=(10.5, 11))
    marco_titulo(fig, T["f2_titulo"], T["f2_sub"])
    ax = fig.add_axes([0.04, 0.07, 0.92, 0.80])

    ax.set_facecolor("#f4f6f8")
    ax.hexbin(sal_cdmx["x"].values, sal_cdmx["y"].values,
              gridsize=45, cmap="Greys", alpha=0.16, zorder=1, mincnt=1)
    _gdf_cdmx.boundary.plot(ax=ax, color="#bbbbbb", linewidth=0.8, zorder=2)

    df_desc = df_all_cdmx[~df_all_cdmx["hueco_id"].isin(df_prio_cdmx["hueco_id"])]
    for _, r in df_desc.iterrows():
        ax.add_patch(plt.Circle((r["x_utm"], r["y_utm"]), r["pers_m"],
                                color="#d8d8d8", alpha=0.22, zorder=2))

    for ki, j in enumerate(sel_idx7):
        iso = cands_c[j].get("isocrona")
        if iso is None:
            continue
        col = PALETA[ki % len(PALETA)]
        gpd.GeoSeries([iso]).plot(ax=ax, color=col, alpha=0.30, zorder=3)
        gpd.GeoSeries([iso]).plot(ax=ax, color=col, alpha=0.9,
                                  facecolor="none", linewidth=2.5, zorder=4)

    for _, r in df_prio_cdmx.iterrows():
        cub = bool(r["cub"])
        ax.add_patch(plt.Circle(
            (r["x_utm"], r["y_utm"]), r["pers_m"],
            facecolor=ROJO if cub else "#c9a0a0",
            edgecolor="white" if cub else "none",
            linewidth=2.5 if cub else 0,
            alpha=0.85 if cub else 0.35, zorder=5))

    for ki, j in enumerate(sel_idx7):
        cand = cands_c[j]
        col  = PALETA[ki % len(PALETA)]
        ax.plot(cand["x_clinica"], cand["y_clinica"], "o", color=col,
                markersize=18, zorder=8, markeredgecolor="white", markeredgewidth=2.5)
        ax.text(cand["x_clinica"], cand["y_clinica"], str(ki + 1),
                ha="center", va="center", fontsize=10, fontweight="bold",
                color="white", zorder=9)

    xs = list(df_prio_cdmx["x_utm"]) + [cands_c[j]["x_clinica"] for j in sel_idx7]
    ys = list(df_prio_cdmx["y_utm"]) + [cands_c[j]["y_clinica"] for j in sel_idx7]
    margen = 5000
    ax.set_xlim(min(xs) - margen, max(xs) + margen)
    ax.set_ylim(min(ys) - margen, max(ys) + margen)
    ax.set_aspect("equal")
    ax.set_axis_off()

    leyenda = [
        mlines.Line2D([0], [0], marker="o", color="w", markerfacecolor=AZUL,
                      markersize=14, markeredgecolor="white", label=T["f2_leg"][0]),
        mpatches.Patch(facecolor=AZUL, alpha=0.18, edgecolor=AZUL, label=T["f2_leg"][1]),
        mpatches.Patch(facecolor=ROJO, edgecolor="white", linewidth=2, label=T["f2_leg"][2]),
        mpatches.Patch(facecolor="#c9a0a0", alpha=0.5, label=T["f2_leg"][3]),
    ]
    ax.legend(handles=leyenda, loc="upper left", fontsize=11, framealpha=0.95,
              borderpad=0.8, labelspacing=0.7)
    pie_fuente(fig, T)
    ruta = config.FIGURAS_DIR / f"linkedin_2_mapa_cdmx{T['suffix']}.png"
    plt.savefig(str(ruta), dpi=150, facecolor="white")
    plt.close(fig)
    print(f"OK {ruta}")


# %% [markdown]
# ## Figura 3 — Resultados de las dos ciudades

# %%
def figura_3(T):
    fig = plt.figure(figsize=(11, 9))
    marco_titulo(fig, T["f3_titulo"], T["f3_sub"])

    colores = [AZUL_CL, "#d6604d"]
    for i, (tarjeta, color) in enumerate(zip(T["f3_tarjetas"], colores)):
        ciudad, n1, l1, n2, l2, n3, l3 = tarjeta
        x0 = 0.06 + i * 0.475
        ax = fig.add_axes([x0, 0.30, 0.42, 0.50])
        ax.set_axis_off()
        ax.add_patch(FancyBboxPatch(
            (0, 0), 1, 1, boxstyle="round,pad=0.02,rounding_size=0.04",
            transform=ax.transAxes, facecolor="#f4f6f8",
            edgecolor=color, linewidth=2.2, zorder=1))
        ax.text(0.5, 0.90, ciudad, ha="center", va="top", fontsize=15,
                fontweight="bold", color=color, transform=ax.transAxes)
        ax.text(0.5, 0.70, n1, ha="center", va="center", fontsize=40,
                fontweight="bold", color=AZUL, transform=ax.transAxes)
        ax.text(0.5, 0.575, l1, ha="center", va="center", fontsize=12,
                color=GRIS, transform=ax.transAxes)
        ax.text(0.5, 0.40, n2, ha="center", va="center", fontsize=30,
                fontweight="bold", color=VERDE, transform=ax.transAxes)
        ax.text(0.5, 0.305, l2, ha="center", va="center", fontsize=11.5,
                color=GRIS, transform=ax.transAxes)
        ax.text(0.5, 0.165, n3, ha="center", va="center", fontsize=17,
                fontweight="bold", color=color, transform=ax.transAxes)
        ax.text(0.5, 0.075, l3, ha="center", va="center", fontsize=10.5,
                color=GRIS, transform=ax.transAxes)

    fig.text(0.5, 0.21, T["f3_mensaje"],
             ha="center", va="center", fontsize=12.5, fontweight="bold",
             color=AZUL, style="italic")
    pie_fuente(fig, T)
    ruta = config.FIGURAS_DIR / f"linkedin_3_resultados{T['suffix']}.png"
    plt.savefig(str(ruta), dpi=150, facecolor="white")
    plt.close(fig)
    print(f"OK {ruta}")


# %% [markdown]
# ## Generar ambas versiones

# %%
for lang in ["es", "en"]:
    T = STRINGS[lang]
    figura_1(T)
    figura_2(T)
    figura_3(T)

print("\nFiguras LinkedIn (ES + EN) generadas en outputs/figuras/")
