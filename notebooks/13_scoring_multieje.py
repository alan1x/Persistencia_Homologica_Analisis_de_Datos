# %% [markdown]
# # 13 — Fase 3: Scoring Multi-Eje de los Huecos Habitados (4 Dimensiones)
#
# Combina cuatro ejes para producir un ranking unificado que guiará la
# optimización de ubicaciones (MCLP) en la Fase 3:
#
#   Eje 1 — Inaccesibilidad:  tiempo estimado caminando a clínica (KDTree)
#   Eje 2 — Inequidad:        personas sin seguro médico dentro del hueco
#   Eje 3 — Estructura:       persistencia topológica del hueco
#   Eje 4 — Marginación:      índice compuesto desde variables censales INEGI
#
# Pesos iguales (25% cada eje) para evitar sesgos teóricos.
# El índice de marginación (IM) se construye desde huecos_censal sin datos externos:
#   IM = 0.35×pct_sin_salud + 0.25×escolaridad_def + 0.25×pob_mayor_pct + 0.15×densidad_psin

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
from lib.marginacion import calcular_indice

# %%
REGIONES    = ["CDMX", "EDOMEX"]
VELOCIDAD   = 4.5
DETOUR      = 1.35
TIEMPO_LIM  = 15
TOP_N_TABLA = 15

_VEL_M_MIN = (VELOCIDAD * 1000) / 60
_TR        = Transformer.from_crs("EPSG:4326", config.CRS_METROS, always_xy=True)

# Pesos del score compuesto — 4 ejes iguales
W_TIEMPO   = 0.25
W_PSINDER  = 0.25
W_PERS     = 0.25
W_MARG     = 0.25

COLORES = {"CDMX": "#4393c3", "EDOMEX": "#d6604d"}

# %% [markdown]
# ## 1. Cargar datos, calcular tiempo y construir score 4 ejes

# %%
def rank_pct(series):
    """Rango percentil [0,1] — mayor valor = mayor urgencia."""
    return series.rank(pct=True)

dfs = {}

for region in REGIONES:
    df = pd.read_parquet(config.INTERMEDIOS_DIR / f"huecos_censal_{region}.parquet")
    df["ciudad"] = region
    df = df[df["pob_afectada"] > 0].copy()

    # Tiempo estimado con KDTree
    clinicas = pd.read_parquet(config.INTERMEDIOS_DIR / f"salud_{region}.parquet")
    tree     = cKDTree(clinicas[["x", "y"]].values)
    xs, ys   = _TR.transform(df["lon"].values, df["lat"].values)
    dists, _ = tree.query(np.column_stack([xs, ys]))
    df["x_utm"]          = xs
    df["y_utm"]          = ys
    df["dist_eucl_m"]    = dists
    df["tiempo_est_min"] = dists * DETOUR / _VEL_M_MIN

    # Eje 4: índice de marginación (lib/marginacion.py)
    df["indice_marg"] = calcular_indice(df).values
    df["indice_marg"] = df["indice_marg"].fillna(df["indice_marg"].median())

    # Rangos percentiles (0 = menos urgente, 1 = más urgente)
    df["rank_tiempo"]  = rank_pct(df["tiempo_est_min"])
    df["rank_psinder"] = rank_pct(df["pob_sin_salud"])
    df["rank_pers"]    = rank_pct(df["pers_m"])
    df["rank_marg"]    = rank_pct(df["indice_marg"])

    # Score compuesto 4 ejes (pesos iguales)
    df["score"] = (W_TIEMPO  * df["rank_tiempo"]
                 + W_PSINDER * df["rank_psinder"]
                 + W_PERS    * df["rank_pers"]
                 + W_MARG    * df["rank_marg"])
    df["score_norm"] = rank_pct(df["score"])

    # Urgencia calibrada en percentiles 75/50/25
    p75 = df["score_norm"].quantile(0.75)
    p50 = df["score_norm"].quantile(0.50)
    p25 = df["score_norm"].quantile(0.25)

    def etiqueta(s):
        if s >= p75: return "Crítico"
        if s >= p50: return "Alto"
        if s >= p25: return "Moderado"
        return "Bajo"
    df["urgencia"] = df["score_norm"].apply(etiqueta)

    df = df.sort_values("score", ascending=False).reset_index(drop=True)
    dfs[region] = df

    n_crit = (df["urgencia"] == "Crítico").sum()
    n_alto = (df["urgencia"] == "Alto").sum()
    print(f"[{region}]  {len(df)} huecos habitados  |  "
          f"Crítico: {n_crit}  |  Alto: {n_alto}  |  "
          f"IM_medio: {df['indice_marg'].mean():.3f}  |  "
          f"Score máx: {df['score'].max():.3f}")

# Exportar para notebooks siguientes
for region in REGIONES:
    ruta = config.INTERMEDIOS_DIR / f"huecos_score_{region}.parquet"
    dfs[region].to_parquet(str(ruta), index=False)
    print(f"  ✓ {ruta}")

# %% [markdown]
# ## 2. Scatter principal: 4 dimensiones de urgencia

# %%
fig, axes = plt.subplots(1, 2, figsize=(17, 8))
fig.suptitle(
    "Huecos de cobertura de salud — Score compuesto de 4 ejes (25% cada uno)\n"
    "EJE X: Inaccesibilidad (tiempo caminando)  ·  EJE Y: Inequidad (personas sin seguro)\n"
    "TAMAÑO DEL CÍRCULO: Estructura topológica (persistencia en metros)  ·  "
    "COLOR: Score final (incluye los 4 ejes: acceso + inequidad + persistencia + marginación)",
    fontsize=11, fontweight="bold"
)

cmap = plt.cm.RdYlGn_r

for ax, region in zip(axes, REGIONES):
    df    = dfs[region]
    sizes = np.clip(df["pers_m"] / 8, 30, 600)
    sc    = ax.scatter(
        df["tiempo_est_min"], df["pob_sin_salud"],
        c=df["score_norm"], cmap=cmap, vmin=0, vmax=1,
        s=sizes, alpha=0.80, edgecolors="white", linewidths=0.5, zorder=3
    )

    ax.axvline(TIEMPO_LIM, color="#555", linestyle="--", linewidth=1.5, alpha=0.7,
               label=f"Límite accesibilidad: {TIEMPO_LIM} min")

    psinder_med = df["pob_sin_salud"].median()
    ax.axhline(psinder_med, color="#aaa", linestyle=":", linewidth=1.0, alpha=0.6,
               label=f"Mediana sin seguro: {int(psinder_med):,}")
    ax.fill_betweenx(
        [psinder_med, df["pob_sin_salud"].max() * 1.08],
        TIEMPO_LIM, df["tiempo_est_min"].max() * 1.08,
        color="#d6604d", alpha=0.07, zorder=1
    )
    ax.text(TIEMPO_LIM + 0.3, psinder_med * 1.05,
            "Zona crítica:\nInaccesible + Alta inequidad",
            fontsize=8, color="#b2182b", fontweight="bold", alpha=0.8)

    for _, row in df.head(5).iterrows():
        ax.annotate(
            f"#{int(row['hueco_id'])}  IM={row['indice_marg']:.2f}",
            xy=(row["tiempo_est_min"], row["pob_sin_salud"]),
            xytext=(row["tiempo_est_min"] + 0.5, row["pob_sin_salud"] + 30),
            fontsize=7.5, color="#333",
            arrowprops=dict(arrowstyle="-", color="#bbb", lw=0.7),
        )

    n_crit = (df["urgencia"] == "Crítico").sum()
    ax.set_title(
        f"{region}  —  {len(df)} huecos habitados  |  {n_crit} críticos\n"
        f"IM medio = {df['indice_marg'].mean():.3f}  "
        f"(Eje 4: marginación socioeconómica)",
        fontsize=10, fontweight="bold", color=COLORES[region]
    )
    ax.set_xlabel("EJE 1 — Inaccesibilidad: tiempo caminando a clínica más cercana (min)",
                  fontsize=10)
    ax.set_ylabel("EJE 2 — Inequidad: personas sin seguro médico en el hueco", fontsize=10)
    ax.legend(fontsize=8.5, loc="upper left")
    ax.spines[["top", "right"]].set_visible(False)

cb = fig.colorbar(sc, ax=axes, shrink=0.7, pad=0.02)
cb.set_label(
    "Score compuesto 4 ejes (0 = baja urgencia  →  1 = máxima urgencia)\n"
    "= 25% acceso + 25% inequidad + 25% persistencia (EJE 3) + 25% marginación (EJE 4)",
    fontsize=8.5
)

# Leyenda de tamaño (Eje 3 — persistencia topológica)
for tam, etiq in [(50, "Pers.~200m"), (200, "Pers.~800m"), (500, "Pers.~5000m")]:
    axes[1].scatter([], [], s=tam, color="#aaa", alpha=0.7, label=etiq)
axes[1].legend(
    title="EJE 3 — Estructura topológica\n(tamaño del círculo = persistencia)",
    fontsize=8, title_fontsize=8.5, loc="upper left"
)

plt.tight_layout()
ruta = config.FIGURAS_DIR / "scoring_scatter.png"
plt.savefig(str(ruta), dpi=150, bbox_inches="tight", facecolor="white")
plt.show()
print(f"✓ {ruta}")

# %% [markdown]
# ## 3. Rankings por eje — 4 ejes, comparativa visual

# %%
fig, axes = plt.subplots(4, 2, figsize=(17, 20))
fig.suptitle("Top 10 huecos por eje de urgencia — CDMX vs EDOMEX (4 dimensiones)",
             fontsize=13, fontweight="bold")

EJES = [
    ("tiempo_est_min", "EJE 1 — INACCESIBILIDAD\nTiempo caminando a clínica más cercana",      "minutos",  "#e08214"),
    ("pob_sin_salud",  "EJE 2 — INEQUIDAD\nPersonas sin seguro médico dentro del hueco",        "personas", "#762a83"),
    ("pers_m",         "EJE 3 — ESTRUCTURA TOPOLÓGICA\nPersistencia del hueco (radio en metros)", "metros", "#1b7837"),
    ("indice_marg",    "EJE 4 — MARGINACIÓN SOCIOECONÓMICA\nÍndice compuesto (Censo INEGI 2020)", "IM 0–1", "#b2182b"),
]

urgencia_map = {"Crítico": "#b2182b", "Alto": "#e08214",
                "Moderado": "#4d9221", "Bajo": "#aaa"}

for fila, (col, titulo, unidad, _color_eje) in enumerate(EJES):
    for j, region in enumerate(REGIONES):
        ax     = axes[fila][j]
        df_top = dfs[region].nlargest(10, col).reset_index(drop=True)

        barras = ax.barh(range(len(df_top)), df_top[col],
                         color=COLORES[region], alpha=0.80, edgecolor="white")
        for i, (_, row) in enumerate(df_top.iterrows()):
            barras[i].set_facecolor(urgencia_map.get(row["urgencia"], COLORES[region]))

        for i, (_, row) in enumerate(df_top.iterrows()):
            ax.text(row[col] * 1.01, i,
                    f"  score: {row['score']:.2f}",
                    va="center", fontsize=8, color="#444")

        yticks = [f"#{int(r['hueco_id'])}  {r['urgencia']}" for _, r in df_top.iterrows()]
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

parches = [mpatches.Patch(color=c, label=e) for e, c in urgencia_map.items()]
fig.legend(handles=parches, title="Urgencia compuesta", loc="lower center",
           ncol=4, fontsize=9, bbox_to_anchor=(0.5, 0.005))

plt.tight_layout(rect=[0, 0.03, 1, 1])
ruta = config.FIGURAS_DIR / "scoring_rankings.png"
plt.savefig(str(ruta), dpi=150, bbox_inches="tight", facecolor="white")
plt.show()
print(f"✓ {ruta}")

# %% [markdown]
# ## 4. Mapa de Pareto: huecos que dominan en 2+ de los 4 ejes

# %%
fig, axes = plt.subplots(1, 2, figsize=(16, 7))
fig.suptitle(
    "Frontera de Pareto — Huecos urgentes en 2+ ejes de los 4\n"
    "(punto en cuadrante superior-derecho = urgente en AMBOS ejes mostrados)",
    fontsize=12, fontweight="bold"
)

for ax, region in zip(axes, REGIONES):
    df = dfs[region].copy()
    df["n_ejes_top"] = (
        (df["rank_tiempo"]  >= 0.80).astype(int) +
        (df["rank_psinder"] >= 0.80).astype(int) +
        (df["rank_pers"]    >= 0.80).astype(int) +
        (df["rank_marg"]    >= 0.80).astype(int)
    )

    colores_n = {0: "#d0d0d0", 1: "#fdae61", 2: "#f46d43", 3: "#d73027", 4: "#a50026"}
    tamanios  = {0: 25, 1: 55, 2: 100, 3: 200, 4: 320}

    for n_ejes in [0, 1, 2, 3, 4]:
        sub = df[df["n_ejes_top"] == n_ejes]
        if len(sub) == 0:
            continue
        label_s = "s" if n_ejes != 1 else ""
        ax.scatter(sub["rank_tiempo"], sub["rank_psinder"],
                   c=colores_n[n_ejes],
                   s=sub["pers_m"] / 5 + tamanios[n_ejes],
                   alpha=0.85, edgecolors="white", linewidths=0.5, zorder=n_ejes + 2,
                   label=f"Top en {n_ejes} eje{label_s} ({len(sub)})")

    for _, row in df[df["n_ejes_top"] >= 3].iterrows():
        ax.annotate(f"#{int(row['hueco_id'])}",
                    xy=(row["rank_tiempo"], row["rank_psinder"]),
                    xytext=(row["rank_tiempo"] + 0.01, row["rank_psinder"] + 0.01),
                    fontsize=8, color="#333",
                    arrowprops=dict(arrowstyle="-", color="#bbb", lw=0.5))

    ax.axvline(0.80, color="#aaa", linestyle="--", linewidth=1.0, alpha=0.7)
    ax.axhline(0.80, color="#aaa", linestyle="--", linewidth=1.0, alpha=0.7)
    ax.fill_between([0.80, 1.02], 0.80, 1.02, color="#a50026", alpha=0.05)
    ax.text(0.82, 0.82, "Crítico\nen 2+ ejes", fontsize=8,
            color="#a50026", fontweight="bold")

    ax.set_xlim(0, 1.02)
    ax.set_ylim(0, 1.02)
    ax.set_xlabel("Rango percentil — Inaccesibilidad (tiempo)", fontsize=10)
    ax.set_ylabel("Rango percentil — Inequidad (sin seguro)", fontsize=10)
    ax.set_title(f"{region}  —  Frontera de Pareto (4 ejes)",
                 fontsize=11, fontweight="bold", color=COLORES[region])
    ax.legend(fontsize=8.5, framealpha=0.9)
    ax.spines[["top", "right"]].set_visible(False)

plt.tight_layout()
ruta = config.FIGURAS_DIR / "scoring_pareto.png"
plt.savefig(str(ruta), dpi=150, bbox_inches="tight", facecolor="white")
plt.show()
print(f"✓ {ruta}")

# %% [markdown]
# ## 5. Contribución del eje de marginación: cambios de ranking

# %%
fig, axes = plt.subplots(1, 2, figsize=(16, 7))
fig.suptitle(
    "Impacto del índice de marginación sobre la priorización\n"
    "Flechas: huecos que suben ↑ (más urgentes) o bajan ↓ al incluir el 4.° eje",
    fontsize=12, fontweight="bold"
)

for ax, region in zip(axes, REGIONES):
    df = dfs[region].copy()

    # Score de referencia con 3 ejes (pesos originales 40/40/20)
    df["score3"] = (0.40 * df["rank_tiempo"]
                  + 0.40 * df["rank_psinder"]
                  + 0.20 * df["rank_pers"])
    df["rank3"] = df["score3"].rank(ascending=False, method="min").fillna(0).astype(int)
    df["rank4"] = df["score"].rank(ascending=False, method="min").fillna(0).astype(int)
    df["delta"] = df["rank3"] - df["rank4"]   # positivo = sube con IM

    top = df.nsmallest(15, "rank4").sort_values("rank4")
    ys  = np.arange(len(top))

    ax.barh(ys, top["score3"] / top["score3"].max(),
            color="#cccccc", alpha=0.8, label="Score 3 ejes (ref.)", height=0.4)
    ax.barh(ys + 0.4, top["score"] / top["score"].max(),
            color=COLORES[region], alpha=0.75, label="Score 4 ejes", height=0.4)

    for y, (_, row) in zip(ys + 0.2, top.iterrows()):
        delta = int(row["delta"])
        if abs(delta) >= 2:
            col_a = "#1b7837" if delta > 0 else "#b2182b"
            sym   = f"↑{delta}" if delta > 0 else f"↓{abs(delta)}"
            ax.text(1.02, y, sym, va="center", ha="left",
                    fontsize=9, fontweight="bold", color=col_a,
                    transform=ax.get_yaxis_transform())

    ax.set_yticks(ys + 0.2)
    ax.set_yticklabels([f"#{int(r['hueco_id'])}  IM={r['indice_marg']:.2f}"
                        for _, r in top.iterrows()], fontsize=8.5)
    ax.invert_yaxis()
    ax.set_xlabel("Score normalizado (relativo al máximo)", fontsize=10)
    ax.set_title(f"{region} — Impacto del 4.° eje (marginación)",
                 fontsize=10, fontweight="bold", color=COLORES[region])
    ax.set_xlim(0, 1.18)
    ax.legend(fontsize=9, loc="lower right")
    ax.spines[["top", "right"]].set_visible(False)

plt.tight_layout()
ruta = config.FIGURAS_DIR / "scoring_impacto_marginacion.png"
plt.savefig(str(ruta), dpi=150, bbox_inches="tight", facecolor="white")
plt.show()
print(f"✓ {ruta}")

# %% [markdown]
# ## 6. Tabla maestra de ranking

# %%
print("\n" + "="*90)
print("TABLA MAESTRA — TOP 15 HUECOS POR SCORE COMPUESTO (4 EJES, PESOS IGUALES 25%)")
print("="*90)

for region in REGIONES:
    df = dfs[region].head(TOP_N_TABLA)
    print(f"\n  [{region}]")
    print(f"  {'#':>3}  {'Urgencia':>9}  {'Pers(m)':>8}  {'Tiempo':>7}  "
          f"{'Sin seguro':>10}  {'%':>5}  {'IM':>5}  {'Score':>6}")
    print(f"  {'—'*75}")
    for _, row in df.iterrows():
        acceso = "✗" if row["tiempo_est_min"] > TIEMPO_LIM else "✓"
        print(f"  {int(row['hueco_id']):3d}  "
              f"{str(row['urgencia']):>9s}  "
              f"{row['pers_m']:8.0f}  "
              f"{row['tiempo_est_min']:6.1f}m{acceso}  "
              f"{int(row['pob_sin_salud']):>10,}  "
              f"{row['pct_sin_salud_prom']:5.1f}%  "
              f"{row['indice_marg']:5.3f}  "
              f"{row['score']:.3f}")

# Huecos dominantes en los 4 ejes
print(f"\n{'='*90}")
print("HUECOS DOMINANTES — Top 20% en los 4 ejes simultáneamente (máxima prioridad)")
print("="*90)
for region in REGIONES:
    df     = dfs[region]
    df_dom = df[
        (df["rank_tiempo"]  >= 0.80) &
        (df["rank_psinder"] >= 0.80) &
        (df["rank_pers"]    >= 0.80) &
        (df["rank_marg"]    >= 0.80)
    ]
    if len(df_dom) == 0:
        print(f"\n  [{region}]  Sin huecos dominantes en los 4 ejes")
    else:
        print(f"\n  [{region}]  {len(df_dom)} huecos dominantes en los 4 ejes:")
        for _, row in df_dom.iterrows():
            print(f"    #{int(row['hueco_id']):3d}  {row['pers_m']:.0f}m  "
                  f"{row['tiempo_est_min']:.1f}min  "
                  f"{int(row['pob_sin_salud']):,} sin seguro  "
                  f"IM={row['indice_marg']:.3f}  score={row['score']:.3f}")

# Impacto de la marginación
print(f"\n{'='*90}")
print("IMPACTO DEL 4.° EJE — Huecos que suben ≥3 posiciones al incluir marginación")
print("="*90)
for region in REGIONES:
    df_c = dfs[region].copy()
    df_c["score3"] = (0.40 * df_c["rank_tiempo"]
                    + 0.40 * df_c["rank_psinder"]
                    + 0.20 * df_c["rank_pers"])
    df_c["rank3"] = df_c["score3"].rank(ascending=False, method="min").fillna(0).astype(int)
    df_c["rank4"] = df_c["score"].rank(ascending=False, method="min").fillna(0).astype(int)
    df_c["delta"] = df_c["rank3"] - df_c["rank4"]

    sube = df_c[df_c["delta"] >= 3].sort_values("delta", ascending=False)
    print(f"\n  [{region}]  {len(sube)} huecos suben ≥3 posiciones:")
    for _, r in sube.head(5).iterrows():
        print(f"    #{int(r['hueco_id'])}: rank {int(r['rank3'])} → {int(r['rank4'])} "
              f"(↑{int(r['delta'])})  IM={r['indice_marg']:.3f}  "
              f"escol_def={(12.0-r['graproes_prom']):.1f}yr")

print("\n✓ Datos exportados:")
for region in REGIONES:
    print(f"  outputs/intermedios/huecos_score_{region}.parquet")
print("✓ Figuras:")
for fig_name in ["scoring_scatter.png", "scoring_rankings.png",
                  "scoring_pareto.png", "scoring_impacto_marginacion.png"]:
    print(f"  outputs/figuras/{fig_name}")
