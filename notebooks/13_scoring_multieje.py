# %% [markdown]
# # 13 — Fase 3: Scoring Multi-Eje de los 161 Huecos Habitados
#
# Combina los tres ejes calculados en fases anteriores para producir
# un ranking unificado que guiará la optimización de ubicaciones:
#
#   Eje 1 — Inaccesibilidad:  tiempo estimado caminando a clínica (Fase 2B / KDTree)
#   Eje 2 — Inequidad:        personas sin seguro médico dentro del hueco (Fase 1E)
#   Eje 3 — Estructura:       persistencia topológica del hueco (Fase 1A)
#
# Cada hueco recibe un rango normalizado [0,1] en cada eje y un score compuesto.
# Pesos: 40% tiempo, 40% sin-seguro, 20% persistencia.
# Los huecos que aparecen en el top de múltiples ejes son candidatos
# prioritarios para la Fase 3 de optimización (MCLP).

# %%
import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from scipy.spatial import cKDTree
from pyproj import Transformer

from lib import config

# %%
REGIONES    = ["CDMX", "EDOMEX"]
VELOCIDAD   = 4.5          # km/h peatonal
DETOUR      = 1.35         # factor de desvío euclidiana → red real
TIEMPO_LIM  = 15           # minutos — umbral de accesibilidad aceptable
TOP_N_TABLA = 15           # filas en las tablas de ranking

_VEL_M_MIN  = (VELOCIDAD * 1000) / 60
_TR         = Transformer.from_crs("EPSG:4326", config.CRS_METROS, always_xy=True)

# Pesos del score compuesto (suman 1)
W_TIEMPO    = 0.40
W_PSINDER   = 0.40
W_PERS      = 0.20

COLORES = {"CDMX": "#4393c3", "EDOMEX": "#d6604d"}

# %% [markdown]
# ## 1. Cargar datos: huecos censales + tiempo estimado (KDTree)

# %%
def rank_norm(series):
    """Rango percentil normalizado [0,1] — mayor valor = mayor urgencia."""
    return series.rank(pct=True)

dfs = {}

for region in REGIONES:
    # Huecos con datos censales (Fase 1E)
    df = pd.read_parquet(config.INTERMEDIOS_DIR / f"huecos_censal_{region}.parquet")
    df["ciudad"] = region

    # Filtrar solo habitados
    df = df[df["pob_afectada"] > 0].copy()

    # Recalcular tiempo estimado con KDTree (Fase 2B — no requiere internet)
    clinicas = pd.read_parquet(config.INTERMEDIOS_DIR / f"salud_{region}.parquet")
    tree     = cKDTree(clinicas[["x", "y"]].values)
    xs, ys   = _TR.transform(df["lon"].values, df["lat"].values)
    dists, _ = tree.query(np.column_stack([xs, ys]))
    df["x_utm"]          = xs
    df["y_utm"]          = ys
    df["dist_eucl_m"]    = dists
    df["tiempo_est_min"] = dists * DETOUR / _VEL_M_MIN

    # Tres ejes — rangos normalizados (0=menos urgente, 1=más urgente)
    df["rank_tiempo"]   = rank_norm(df["tiempo_est_min"])
    df["rank_psinder"]  = rank_norm(df["pob_sin_salud"])
    df["rank_pers"]     = rank_norm(df["pers_m"])

    # Score compuesto
    df["score"] = (W_TIEMPO * df["rank_tiempo"]
                   + W_PSINDER * df["rank_psinder"]
                   + W_PERS   * df["rank_pers"])
    df["score_norm"] = rank_norm(df["score"])   # percentil final 0→1

    # Etiqueta de urgencia
    def etiqueta(s):
        if s >= 0.85: return "Crítico"
        if s >= 0.65: return "Alto"
        if s >= 0.40: return "Moderado"
        return "Bajo"
    df["urgencia"] = df["score_norm"].apply(etiqueta)

    df = df.sort_values("score", ascending=False).reset_index(drop=True)
    dfs[region] = df

    n_crit = (df["urgencia"] == "Crítico").sum()
    n_alto = (df["urgencia"] == "Alto").sum()
    print(f"[{region}]  {len(df)} huecos habitados  |  "
          f"Crítico: {n_crit}  |  Alto: {n_alto}  |  "
          f"Score máx: {df['score'].max():.3f}")

# Exportar para notebooks siguientes
for region in REGIONES:
    ruta = config.INTERMEDIOS_DIR / f"huecos_score_{region}.parquet"
    dfs[region].to_parquet(str(ruta), index=False)
    print(f"  ✓ {ruta}")

# %% [markdown]
# ## 2. Scatter principal: Inaccesibilidad × Inequidad × Estructura

# %%
fig, axes = plt.subplots(1, 2, figsize=(17, 8))
fig.suptitle(
    "Huecos de cobertura de salud — Tres dimensiones de urgencia\n"
    "Eje X = tiempo caminando  ·  Eje Y = personas sin seguro  ·  "
    "Tamaño = persistencia topológica  ·  Color = score compuesto",
    fontsize=12, fontweight="bold"
)

cmap = plt.cm.RdYlGn_r   # verde=bajo, rojo=crítico

for ax, region in zip(axes, REGIONES):
    df    = dfs[region]
    color = COLORES[region]

    # Tamaño de burbuja proporcional a persistencia
    sizes = np.clip(df["pers_m"] / 8, 30, 600)
    sc    = ax.scatter(
        df["tiempo_est_min"], df["pob_sin_salud"],
        c=df["score_norm"], cmap=cmap, vmin=0, vmax=1,
        s=sizes, alpha=0.80, edgecolors="white", linewidths=0.5, zorder=3
    )

    # Línea de límite de accesibilidad
    ax.axvline(TIEMPO_LIM, color="#555", linestyle="--", linewidth=1.5, alpha=0.7,
               label=f"Límite {TIEMPO_LIM} min")

    # Sombrear cuadrante crítico (derecha-arriba)
    psinder_med = df["pob_sin_salud"].median()
    ax.axhline(psinder_med, color="#aaa", linestyle=":", linewidth=1.0, alpha=0.6)
    ax.fill_betweenx(
        [psinder_med, df["pob_sin_salud"].max() * 1.08],
        TIEMPO_LIM, df["tiempo_est_min"].max() * 1.08,
        color="#d6604d", alpha=0.07, zorder=1
    )
    ax.text(TIEMPO_LIM + 0.3, psinder_med * 1.05,
            "Inaccesible\n+ Desprotegido", fontsize=8, color="#b2182b",
            fontweight="bold", alpha=0.8)

    # Etiquetar top 5 del score compuesto
    for _, row in df.head(5).iterrows():
        ax.annotate(
            f"#{int(row['hueco_id'])}",
            xy=(row["tiempo_est_min"], row["pob_sin_salud"]),
            xytext=(row["tiempo_est_min"] + 0.5, row["pob_sin_salud"] + 30),
            fontsize=8, color="#333",
            arrowprops=dict(arrowstyle="-", color="#bbb", lw=0.7),
        )

    n_crit = (df["urgencia"] == "Crítico").sum()
    ax.set_title(f"{region}  —  {len(df)} huecos habitados  |  {n_crit} críticos",
                 fontsize=11, fontweight="bold", color=COLORES[region])
    ax.set_xlabel("Tiempo estimado a clínica más cercana (min)", fontsize=10)
    ax.set_ylabel("Personas sin seguro médico en el hueco", fontsize=10)
    ax.legend(fontsize=8.5)
    ax.spines[["top", "right"]].set_visible(False)

# Colorbar global
cb = fig.colorbar(sc, ax=axes, shrink=0.7, pad=0.02)
cb.set_label("Score de urgencia (0 = bajo  →  1 = crítico)", fontsize=9)

# Leyenda de tamaños
for tam, etiq in [(50, "200m"), (200, "800m"), (500, "5000m")]:
    ax.scatter([], [], s=tam, color="#aaa", alpha=0.7, label=f"Pers. {etiq}")
axes[1].legend(title="Persistencia", fontsize=8, title_fontsize=8.5, loc="upper left")

plt.tight_layout()
ruta = config.FIGURAS_DIR / "scoring_scatter.png"
plt.savefig(str(ruta), dpi=150, bbox_inches="tight", facecolor="white")
plt.show()
print(f"✓ {ruta}")

# %% [markdown]
# ## 3. Rankings por eje — comparativa visual

# %%
fig, axes = plt.subplots(3, 2, figsize=(17, 16))
fig.suptitle("Top 10 huecos por eje de urgencia — CDMX vs EDOMEX",
             fontsize=13, fontweight="bold")

EJES = [
    ("tiempo_est_min", "Eje 1 — Inaccesibilidad\n(tiempo caminando a clínica)", "min", "#e08214"),
    ("pob_sin_salud",  "Eje 2 — Inequidad\n(personas sin seguro médico)",        "pers.", "#762a83"),
    ("pers_m",         "Eje 3 — Estructura\n(persistencia topológica del hueco)", "metros", "#1b7837"),
]

for fila, (col, titulo, unidad, color_eje) in enumerate(EJES):
    for j, region in enumerate(REGIONES):
        ax     = axes[fila][j]
        df_top = dfs[region].nlargest(10, col).reset_index(drop=True)
        color  = COLORES[region]

        barras = ax.barh(range(len(df_top)), df_top[col],
                         color=color, alpha=0.80, edgecolor="white")

        # Colorear por urgencia compuesta
        urgencia_map = {"Crítico": "#b2182b", "Alto": "#e08214",
                        "Moderado": "#4d9221", "Bajo": "#aaa"}
        for i, (_, row) in enumerate(df_top.iterrows()):
            barras[i].set_facecolor(urgencia_map.get(row["urgencia"], color))

        # Anotación del score compuesto
        for i, (_, row) in enumerate(df_top.iterrows()):
            ax.text(row[col] * 1.01, i,
                    f"  score: {row['score']:.2f}",
                    va="center", fontsize=8, color="#444")

        yticks = [f"#{int(r['hueco_id'])}  {r['urgencia']}"
                  for _, r in df_top.iterrows()]
        ax.set_yticks(range(len(df_top)))
        ax.set_yticklabels(yticks, fontsize=8.5)
        ax.invert_yaxis()

        if fila == 0:
            ax.axvline(TIEMPO_LIM, color="#b2182b", linestyle="--",
                       linewidth=1.5, alpha=0.8, label=f"Límite {TIEMPO_LIM} min")
            ax.legend(fontsize=8)

        ax.set_title(f"{titulo}\n{region}", fontsize=10, fontweight="bold",
                     color=COLORES[region])
        ax.set_xlabel(unidad, fontsize=9)
        ax.spines[["top", "right"]].set_visible(False)

# Leyenda de colores de urgencia
parches = [mpatches.Patch(color=c, label=e)
           for e, c in urgencia_map.items()]
fig.legend(handles=parches, title="Urgencia compuesta", loc="lower center",
           ncol=4, fontsize=9, bbox_to_anchor=(0.5, 0.005))

plt.tight_layout(rect=[0, 0.03, 1, 1])
ruta = config.FIGURAS_DIR / "scoring_rankings.png"
plt.savefig(str(ruta), dpi=150, bbox_inches="tight", facecolor="white")
plt.show()
print(f"✓ {ruta}")

# %% [markdown]
# ## 4. Mapa de Pareto: huecos que dominan en múltiples ejes

# %%
fig, axes = plt.subplots(1, 2, figsize=(16, 7))
fig.suptitle(
    "Frontera de Pareto — Huecos que son urgentes en más de un eje\n"
    "(punto en cuadrante superior-derecho = urgente en AMBOS ejes mostrados)",
    fontsize=12, fontweight="bold"
)

for ax, region in zip(axes, REGIONES):
    df = dfs[region]

    # Contar en cuántos top-20% de cada eje está cada hueco
    top20 = int(len(df) * 0.20) + 1
    df["n_ejes_top"] = (
        (df["rank_tiempo"]  >= 0.80).astype(int) +
        (df["rank_psinder"] >= 0.80).astype(int) +
        (df["rank_pers"]    >= 0.80).astype(int)
    )

    colores_n = {0: "#d0d0d0", 1: "#fdae61", 2: "#f46d43", 3: "#a50026"}
    tamanios  = {0: 30, 1: 60, 2: 120, 3: 220}

    for n_ejes in [0, 1, 2, 3]:
        sub = df[df["n_ejes_top"] == n_ejes]
        if len(sub) == 0:
            continue
        ax.scatter(sub["rank_tiempo"], sub["rank_psinder"],
                   c=colores_n[n_ejes], s=sub["pers_m"] / 5 + tamanios[n_ejes],
                   alpha=0.85, edgecolors="white", linewidths=0.5, zorder=n_ejes + 2,
                   label=f"Top en {n_ejes} eje{'s' if n_ejes != 1 else ''} ({len(sub)})")

    # Etiquetar dominantes (top en 2+ ejes)
    for _, row in df[df["n_ejes_top"] >= 2].iterrows():
        ax.annotate(f"#{int(row['hueco_id'])}",
                    xy=(row["rank_tiempo"], row["rank_psinder"]),
                    xytext=(row["rank_tiempo"] + 0.01, row["rank_psinder"] + 0.01),
                    fontsize=8, color="#333",
                    arrowprops=dict(arrowstyle="-", color="#bbb", lw=0.5))

    # Líneas de percentil 80
    ax.axvline(0.80, color="#aaa", linestyle="--", linewidth=1.0, alpha=0.7)
    ax.axhline(0.80, color="#aaa", linestyle="--", linewidth=1.0, alpha=0.7)
    ax.fill_between([0.80, 1.02], 0.80, 1.02, color="#a50026", alpha=0.05)
    ax.text(0.82, 0.82, "Crítico\nen 2+ ejes", fontsize=8,
            color="#a50026", fontweight="bold")

    ax.set_xlim(0, 1.02)
    ax.set_ylim(0, 1.02)
    ax.set_xlabel("Rango percentil — Inaccesibilidad (tiempo)", fontsize=10)
    ax.set_ylabel("Rango percentil — Inequidad (sin seguro)", fontsize=10)
    ax.set_title(f"{region}  —  Frontera de Pareto",
                 fontsize=11, fontweight="bold", color=COLORES[region])
    ax.legend(fontsize=8.5, framealpha=0.9)
    ax.spines[["top", "right"]].set_visible(False)

plt.tight_layout()
ruta = config.FIGURAS_DIR / "scoring_pareto.png"
plt.savefig(str(ruta), dpi=150, bbox_inches="tight", facecolor="white")
plt.show()
print(f"✓ {ruta}")

# %% [markdown]
# ## 5. Tabla maestra de ranking

# %%
print("\n" + "="*80)
print("TABLA MAESTRA — TOP 15 HUECOS POR SCORE COMPUESTO")
print(f"Pesos: Tiempo={W_TIEMPO:.0%}  Sin-seguro={W_PSINDER:.0%}  Persistencia={W_PERS:.0%}")
print("="*80)

cols_display = ["hueco_id", "urgencia", "pers_m", "tiempo_est_min",
                "pob_sin_salud", "pct_sin_salud_prom", "pob_afectada", "score"]

for region in REGIONES:
    df = dfs[region].head(TOP_N_TABLA)
    print(f"\n  [{region}]")
    print(f"  {'#':>3}  {'Urgencia':>9}  {'Pers(m)':>8}  {'Tiempo':>7}  "
          f"{'Sin seguro':>10}  {'%':>5}  {'Pob.total':>9}  {'Score':>6}")
    print(f"  {'—'*72}")
    for _, row in df.iterrows():
        acceso = "✗" if row["tiempo_est_min"] > TIEMPO_LIM else "✓"
        print(f"  {int(row['hueco_id']):3d}  "
              f"{str(row['urgencia']):>9s}  "
              f"{row['pers_m']:8.0f}  "
              f"{row['tiempo_est_min']:6.1f}m{acceso}  "
              f"{int(row['pob_sin_salud']):>10,}  "
              f"{row['pct_sin_salud_prom']:5.1f}%  "
              f"{int(row['pob_afectada']):>9,}  "
              f"{row['score']:.3f}")

# Huecos que aparecen en el top-20% de los 3 ejes simultáneamente
print(f"\n{'='*80}")
print("HUECOS DOMINANTES — Top 20% en los 3 ejes simultáneamente (máxima prioridad)")
print("="*80)
for region in REGIONES:
    df    = dfs[region]
    df_dom = df[
        (df["rank_tiempo"]  >= 0.80) &
        (df["rank_psinder"] >= 0.80) &
        (df["rank_pers"]    >= 0.80)
    ]
    if len(df_dom) == 0:
        print(f"\n  [{region}]  Sin huecos dominantes en los 3 ejes")
    else:
        print(f"\n  [{region}]  {len(df_dom)} huecos dominantes:")
        for _, row in df_dom.iterrows():
            print(f"    #{int(row['hueco_id']):3d}  {row['pers_m']:.0f}m  "
                  f"{row['tiempo_est_min']:.1f}min  "
                  f"{int(row['pob_sin_salud']):,} sin seguro  "
                  f"score={row['score']:.3f}")

print("\n✓ Datos exportados:")
for region in REGIONES:
    print(f"  outputs/intermedios/huecos_score_{region}.parquet")
print("✓ Figuras:")
print("  outputs/figuras/scoring_scatter.png")
print("  outputs/figuras/scoring_rankings.png")
print("  outputs/figuras/scoring_pareto.png")
