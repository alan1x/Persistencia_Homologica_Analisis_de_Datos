# %% [markdown]
# # 17 — Validación Topológica: ¿Se cierran los huecos con K=5 clínicas?
#
# Cierre del análisis TDA: el mismo método que encontró los huecos verifica
# si las 5 clínicas propuestas los cierran topológicamente.
#
# Definición de "cierre topológico":
#   Un hueco H₁ con centroide c y radio de persistencia r queda cerrado
#   cuando una nueva clínica cae a distancia d < r de c.
#   Esto garantiza que el nuevo punto triangula el interior del loop vacío,
#   convirtiendo el 1-ciclo en frontera de un 2-simplex.
#
# Pipeline:
#   1. Cargar huecos prioritarios (ciclos H₁ ya calculados en fase 2)
#   2. Cargar K=5 clínicas propuestas (recomendaciones_fase3.csv)
#   3. Para cada hueco: distancia al vecino nuevo más cercano
#   4. Clasificar: cerrado (d < r) | parcialmente cerrado (d < 2r) | persistente
#   5. Visualizar: mapa, diagrama de persistencia, barras comparativas

# %%
import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.lines as mlines
from scipy.spatial import cKDTree
from pyproj import Transformer

from lib import config, tda

REGIONES      = ["CDMX", "EDOMEX"]
K_NUEVO       = 5
PER_OCU_NUEVO = 20.0   # tamaño de nueva clínica: radio ≈ 184m, peso = 184² m²
MIN_PERS      = 200.0

_TR = Transformer.from_crs("EPSG:4326", config.CRS_METROS, always_xy=True)
COLORES = {"CDMX": "#4393c3", "EDOMEX": "#d6604d"}

URG_COLOR = {
    "Crítico":  "#b2182b",
    "Alto":     "#e08214",
    "Moderado": "#4dac26",
}

# %% [markdown]
# ## 1. Cargar datos

# %%
nuevas_all = pd.read_csv(config.INTERMEDIOS_DIR / "recomendaciones_fase3.csv")
nuevas_all = nuevas_all[nuevas_all["K"] == K_NUEVO].copy()

datos = {}

for region in REGIONES:
    # Huecos prioritarios con sus centroides y radios de persistencia
    df_prio = pd.read_parquet(config.INTERMEDIOS_DIR / f"huecos_prioritarios_{region}.parquet")

    # Convertir centroides de huecos a UTM
    x_h, y_h = _TR.transform(df_prio["lon"].values, df_prio["lat"].values)
    df_prio = df_prio.copy()
    df_prio["x_utm"] = x_h
    df_prio["y_utm"] = y_h

    # Nuevas clínicas K=5 para esta región
    nv = nuevas_all[nuevas_all["ciudad"] == region].copy()
    x_nv, y_nv = _TR.transform(nv["lon"].values, nv["lat"].values)
    pts_nv = np.column_stack([x_nv, y_nv])

    # Distancia de cada hueco a la nueva clínica más cercana
    tree = cKDTree(pts_nv)
    pts_huecos = np.column_stack([df_prio["x_utm"].values, df_prio["y_utm"].values])
    dists, idx_cerca = tree.query(pts_huecos, k=1)

    df_prio["dist_nueva"] = dists
    df_prio["idx_clinica"] = idx_cerca

    # Clasificación topológica
    # Cerrado: nueva clínica dentro del radio del hueco → triangulación interna
    # Parcial: clínica entre 1× y 2× el radio → accesible pero no cierra topología
    # Persistente: clínica a más de 2× el radio
    df_prio["estado"] = "Persistente"
    df_prio.loc[df_prio["dist_nueva"] < df_prio["pers_m"] * 2, "estado"] = "Parcial"
    df_prio.loc[df_prio["dist_nueva"] < df_prio["pers_m"],      "estado"] = "Cerrado"

    datos[region] = {
        "df_prio": df_prio,
        "pts_nv": pts_nv,
        "nv": nv,
    }

    # --- Resumen rápido ---
    cnt = df_prio["estado"].value_counts()
    print(f"\n[{region}]  {len(df_prio)} huecos prioritarios  |  K={K_NUEVO} clínicas nuevas")
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
# ## 2. Diagrama de persistencia — huecos prioritarios coloreados por estado

# %%
fig, axes = plt.subplots(1, 2, figsize=(16, 7))
fig.suptitle(
    "Diagrama de Persistencia H₁ — Huecos Prioritarios\n"
    "¿Cuáles quedan topológicamente cerrados con K=5 clínicas nuevas?",
    fontsize=13, fontweight="bold"
)

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

for ax, region in zip(axes, REGIONES):
    df = datos[region]["df_prio"]
    color_ciudad = COLORES[region]

    lim = df["pers_m"].max() * 1.12

    # Diagonal (birth == death, persistencia cero)
    ax.plot([0, lim], [0, lim], "k--", lw=0.8, alpha=0.4)

    # Graficar cada hueco
    for estado in ["Persistente", "Parcial", "Cerrado"]:
        sub = df[df["estado"] == estado]
        if sub.empty:
            continue
        ax.scatter(sub["pers_m"] * 0.0,   # birth aproximado = 0 para simplificar
                   sub["pers_m"],
                   s=80,
                   color=ESTADO_COLOR[estado],
                   marker=ESTADO_MARKER[estado],
                   alpha=0.85,
                   label=f"{estado} ({len(sub)})",
                   zorder=3)

    # Eje Y = persistencia (radio del hueco en metros)
    ax.set_xlim(-lim * 0.05, lim * 0.5)
    ax.set_ylim(0, lim)
    ax.set_xlabel("Birth ≈ 0 (se muestran apilados para claridad)", fontsize=9)
    ax.set_ylabel("Persistencia — radio del hueco (m)", fontsize=10)
    ax.set_title(f"{region}", fontsize=12, fontweight="bold", color=color_ciudad)
    ax.legend(fontsize=9, loc="upper right")
    ax.spines[["top", "right"]].set_visible(False)

    # Umbral mínimo de persistencia
    ax.axhline(MIN_PERS, color="#aaaaaa", lw=1.2, ls=":", label="min_pers=200m")
    ax.text(lim * 0.48, MIN_PERS + lim * 0.01, "min_pers", ha="right",
            fontsize=8, color="#aaa")

plt.tight_layout()
ruta = config.FIGURAS_DIR / "validacion_persistencia.png"
plt.savefig(str(ruta), dpi=150, bbox_inches="tight", facecolor="white")
plt.show()
print(f"✓ {ruta}", flush=True)

# %% [markdown]
# ## 3. Barras: distribución por urgencia y estado

# %%
fig, axes = plt.subplots(1, 2, figsize=(16, 7))
fig.suptitle(
    "Estado topológico de los huecos prioritarios tras K=5 clínicas nuevas\n"
    "Por nivel de urgencia y región",
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
    ax.set_title(f"{region}", fontsize=12, fontweight="bold", color=color_ciudad)
    ax.legend(fontsize=9, title="Estado", title_fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)

plt.tight_layout()
ruta = config.FIGURAS_DIR / "validacion_impacto.png"
plt.savefig(str(ruta), dpi=150, bbox_inches="tight", facecolor="white")
plt.show()
print(f"✓ {ruta}", flush=True)

# %% [markdown]
# ## 4. Mapa: huecos prioritarios con estado topológico y nuevas clínicas

# %%
fig, axes = plt.subplots(1, 2, figsize=(20, 10))
fig.suptitle(
    f"Validación topológica — K={K_NUEVO} clínicas nuevas\n"
    "Radio del círculo = persistencia del hueco en metros  |  "
    "Verde = cerrado  |  Naranja = parcial  |  Rojo = persistente",
    fontsize=13, fontweight="bold"
)

for ax, region in zip(axes, REGIONES):
    color_ciudad = COLORES[region]
    df = datos[region]["df_prio"]
    pts_nv = datos[region]["pts_nv"]

    ax.set_facecolor("#f0f4f8")

    # Dibujar huecos por estado (más críticos encima)
    for estado in ["Cerrado", "Parcial", "Persistente"]:
        sub = df[df["estado"] == estado]
        col = ESTADO_COLOR[estado]
        zord = {"Cerrado": 4, "Parcial": 5, "Persistente": 6}[estado]

        for _, row in sub.iterrows():
            # Círculo de radio = persistencia (escala geográfica real del hueco)
            circ = plt.Circle(
                (row["x_utm"], row["y_utm"]),
                row["pers_m"],
                facecolor=col, alpha=0.45,
                edgecolor=col, linewidth=1.5,
                zorder=zord
            )
            ax.add_patch(circ)

            # Línea al centroide de la clínica más cercana
            if estado in ("Cerrado", "Parcial"):
                idx_c = int(row["idx_clinica"])
                xc, yc = pts_nv[idx_c]
                ax.plot([row["x_utm"], xc], [row["y_utm"], yc],
                        color=col, lw=1.0, alpha=0.4, zorder=3)

    # Nuevas clínicas (diamantes grandes numeradas)
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
    ax.set_title(
        f"{region} — {len(df)} huecos prioritarios\n"
        f"Cerrados: {cnt.get('Cerrado', 0)}  |  "
        f"Parciales: {cnt.get('Parcial', 0)}  |  "
        f"Persistentes: {cnt.get('Persistente', 0)}",
        fontsize=11, fontweight="bold", color=color_ciudad
    )

    # Leyenda
    handles = [
        mpatches.Patch(color=ESTADO_COLOR["Cerrado"],     alpha=0.7,
                       label=f"Cerrado  ({cnt.get('Cerrado', 0)})  — clínica dentro del hueco"),
        mpatches.Patch(color=ESTADO_COLOR["Parcial"],     alpha=0.7,
                       label=f"Parcial  ({cnt.get('Parcial', 0)})  — clínica entre 1×–2× radio"),
        mpatches.Patch(color=ESTADO_COLOR["Persistente"], alpha=0.7,
                       label=f"Persistente  ({cnt.get('Persistente', 0)})  — requiere más intervención"),
        mlines.Line2D([0], [0], marker="D", color="w",
                      markerfacecolor=color_ciudad, markersize=12,
                      markeredgecolor="white",
                      label=f"{K_NUEVO} clínicas nuevas propuestas"),
    ]
    ax.legend(handles=handles, loc="lower left", fontsize=8.5, framealpha=0.95)

plt.tight_layout()
ruta = config.FIGURAS_DIR / "validacion_mapa.png"
plt.savefig(str(ruta), dpi=150, bbox_inches="tight", facecolor="white")
plt.show()
print(f"✓ {ruta}", flush=True)

# %% [markdown]
# ## 5. Resumen ejecutivo final

# %%
print("\n" + "="*72, flush=True)
print("VALIDACIÓN TOPOLÓGICA — RESUMEN FINAL", flush=True)
print("="*72, flush=True)

for region in REGIONES:
    df = datos[region]["df_prio"]
    cnt = df["estado"].value_counts()
    n   = len(df)

    pers_max_antes  = df["pers_m"].max()
    pers_max_desp   = df[df["estado"] == "Persistente"]["pers_m"].max() if cnt.get("Persistente", 0) > 0 else 0
    pers_tot_antes  = df["pers_m"].sum()
    pers_tot_desp   = df[df["estado"] == "Persistente"]["pers_m"].sum()

    pct_cerrado = cnt.get("Cerrado", 0) / n * 100
    pct_parcial = cnt.get("Parcial", 0) / n * 100

    print(f"\n  [{region}]  {n} huecos prioritarios  |  K={K_NUEVO} clínicas nuevas")
    print(f"  {'—'*60}")
    print(f"  Cerrados topológicamente: {cnt.get('Cerrado', 0):3d}/{n}  ({pct_cerrado:.0f}%)", flush=True)
    print(f"  Parcialmente cubiertos:   {cnt.get('Parcial', 0):3d}/{n}  ({pct_parcial:.0f}%)", flush=True)
    print(f"  Persistentes:             {cnt.get('Persistente', 0):3d}/{n}  "
          f"({100-pct_cerrado-pct_parcial:.0f}%)", flush=True)
    print(f"  Pers. máx persistente:    {pers_max_desp:.0f} m  "
          f"(antes: {pers_max_antes:.0f} m)", flush=True)
    print(f"  Pers. total persistente:  {pers_tot_desp:.0f} m  "
          f"(antes: {pers_tot_antes:.0f} m, reducción: "
          f"{(pers_tot_antes-pers_tot_desp)/pers_tot_antes*100:.1f}%)", flush=True)
