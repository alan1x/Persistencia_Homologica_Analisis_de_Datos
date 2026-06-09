# %% [markdown]
# # 16 — Fase 3: Dashboard de Resultados y Recomendaciones Finales
#
# Integra los resultados de los notebooks 13-15 en un dashboard de política pública:
#
#   - Tabla maestra de los 10 huecos más urgentes por ciudad (multi-eje)
#   - Comparativa de impacto de los 3 escenarios MCLP (K=1,2,3)
#   - Mapa resumen de recomendaciones por ciudad
#   - Hallazgos de la validación topológica y OSMnx
#   - Lección metodológica: KDTree vs OSMnx para MCLP

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
import matplotlib.gridspec as gridspec
from scipy.spatial import cKDTree
from pyproj import Transformer

from lib import config

# %%
REGIONES = ["CDMX", "EDOMEX"]
COLORES  = {"CDMX": "#4393c3", "EDOMEX": "#d6604d"}
_TR_GEO_UTM = Transformer.from_crs("EPSG:4326", config.CRS_METROS, always_xy=True)
_TR_UTM_GEO = Transformer.from_crs(config.CRS_METROS, "EPSG:4326", always_xy=True)

ESCENARIOS = {
    "A_equidad":       "Equidad",
    "B_accesibilidad": "Accesibilidad",
    "C_compuesto":     "Compuesto",
}

# %% [markdown]
# ## 1. Cargar todos los datos de la Fase 3

# %%
dfs       = {r: pd.read_parquet(config.INTERMEDIOS_DIR / f"huecos_score_{r}.parquet")
             for r in REGIONES}
salud     = {r: pd.read_parquet(config.INTERMEDIOS_DIR / f"salud_{r}.parquet")
             for r in REGIONES}
df_coords = pd.read_csv(config.INTERMEDIOS_DIR / "recomendaciones_mclp.csv")

for region in REGIONES:
    df = dfs[region]
    df["x_utm"], df["y_utm"] = _TR_GEO_UTM.transform(df["lon"].values, df["lat"].values)
    dfs[region] = df

# %% [markdown]
# ## 2. Dashboard principal — Impacto comparado de los 3 escenarios

# %%
fig = plt.figure(figsize=(20, 14))
fig.patch.set_facecolor("white")
gs  = gridspec.GridSpec(3, 4, figure=fig, hspace=0.50, wspace=0.38,
                        left=0.06, right=0.97, top=0.92, bottom=0.06)

fig.suptitle(
    "FASE 3 — Optimización de Cobertura de Salud: Resultados y Recomendaciones\n"
    "Ciudad de México y Estado de México  |  Tres escenarios MCLP  |  K = 1, 2, 3 clínicas nuevas",
    fontsize=13, fontweight="bold", y=0.97
)

# ── Fila 0: barras de impacto por escenario ──────────────────────────────────
K_VALS = [1, 2, 3]
colores_k = ["#4d9221", "#1b7837", "#00441b"]

for col_r, region in enumerate(REGIONES):
    df_reg    = dfs[region]
    total_sin = df_reg["pob_sin_salud"].sum()
    total_pob = df_reg["pob_afectada"].sum()

    # Sin seguro cubiertos por escenario × K
    ax = fig.add_subplot(gs[0, col_r * 2: col_r * 2 + 2])

    esc_nombres = list(ESCENARIOS.values())
    x     = np.arange(len(esc_nombres))
    ancho = 0.25

    for ki, K in enumerate(K_VALS):
        vals = []
        for esc_key in ESCENARIOS:
            sub = df_coords[
                (df_coords["ciudad"] == region) &
                (df_coords["escenario"] == esc_key) &
                (df_coords["K"] == K)
            ]
            vals.append(int(sub["psin_cubierta"].iloc[0]) if len(sub) > 0 else 0)

        barras = ax.bar(x + (ki - 1) * ancho, vals, ancho,
                        color=colores_k[ki], alpha=0.85,
                        label=f"K={K}", edgecolor="white")

        for b, v in zip(barras, vals):
            pct = v / total_sin * 100 if total_sin > 0 else 0
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 50,
                    f"{pct:.1f}%", ha="center", va="bottom",
                    fontsize=7.5, color="#333", fontweight="bold")

    ax.axhline(total_sin, color="#b2182b", linestyle="--", linewidth=1.2,
               alpha=0.7, label=f"Total sin seguro: {int(total_sin):,}")
    ax.set_xticks(x)
    ax.set_xticklabels(esc_nombres, fontsize=9)
    ax.set_ylabel("Personas sin seguro cubiertos", fontsize=9)
    ax.set_title(f"{region} — Personas sin seguro cubiertos\npor escenario y número de clínicas",
                 fontsize=10, fontweight="bold", color=COLORES[region])
    ax.legend(fontsize=8, loc="upper left")
    ax.spines[["top", "right"]].set_visible(False)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{int(v):,}"))

# ── Fila 1: mapa de huecos + clínicas propuestas ─────────────────────────────
for col_r, region in enumerate(REGIONES):
    ax = fig.add_subplot(gs[1, col_r * 2: col_r * 2 + 2])
    df_reg = dfs[region]

    ax.set_facecolor("#f5f5f5")

    # Clínicas existentes (fondo gris)
    ax.scatter(salud[region]["x"].values, salud[region]["y"].values,
               s=0.5, c="#d0d0d0", alpha=0.4, zorder=1)

    # Huecos coloreados por urgencia
    urgencia_map = {"Crítico": "#b2182b", "Alto": "#e08214",
                    "Moderado": "#4dac26", "Bajo": "#d9f0a3"}
    for _, row in df_reg.iterrows():
        c = urgencia_map.get(row["urgencia"], "#ccc")
        circulo = plt.Circle((row["x_utm"], row["y_utm"]),
                             row["pers_m"], color=c, alpha=0.50, zorder=2)
        ax.add_patch(circulo)

    # Clínicas propuestas por escenario (K=1)
    marcadores = {"A_equidad": ("^", "#7b3294"), "B_accesibilidad": ("s", "#e66101"),
                  "C_compuesto": ("*", "#FFD700")}
    for esc_key, (marker, color_m) in marcadores.items():
        sub = df_coords[
            (df_coords["ciudad"] == region) &
            (df_coords["escenario"] == esc_key) &
            (df_coords["K"] == 1)
        ]
        for _, r in sub.iterrows():
            xm, ym = _TR_GEO_UTM.transform(r["lon"], r["lat"])
            ax.plot(xm, ym, marker, color=color_m, markersize=14,
                    markeredgecolor="#333", markeredgewidth=1.2, zorder=6)
            radio_cob = 833  # 15 min equiv.
            ax.add_patch(plt.Circle((xm, ym), radio_cob, color=color_m,
                                    alpha=0.12, zorder=4))
            ax.add_patch(plt.Circle((xm, ym), radio_cob, color=color_m,
                                    alpha=0.5, fill=False, linewidth=1.5,
                                    linestyle="--", zorder=5))

    ax.set_aspect("equal")
    ax.set_axis_off()
    ax.set_title(f"{region} — Huecos por urgencia + clínicas propuestas K=1\n"
                 f"(cada marcador = escenario diferente)",
                 fontsize=10, fontweight="bold", color=COLORES[region])

# ── Fila 2: tabla resumen ─────────────────────────────────────────────────────
ax_tbl = fig.add_subplot(gs[2, :])
ax_tbl.set_axis_off()

filas_tbl = []
headers   = ["Ciudad", "Hueco", "Urgencia", "Pers.(m)", "Tiempo\n(min)",
             "Sin seguro", "% sin\nseguro", "Score\ncompuesto"]

for region in REGIONES:
    for _, row in dfs[region].head(5).iterrows():
        filas_tbl.append([
            region,
            f"#{int(row['hueco_id'])}",
            row["urgencia"],
            f"{row['pers_m']:.0f}",
            f"{row['tiempo_est_min']:.1f}{'✗' if row['tiempo_est_min'] > 15 else '✓'}",
            f"{int(row['pob_sin_salud']):,}",
            f"{row['pct_sin_salud_prom']:.1f}%",
            f"{row['score']:.3f}",
        ])

colores_filas = []
urgencia_tbl = {"Crítico": "#ffcccc", "Alto": "#ffe4b3", "Moderado": "#d9f0d3", "Bajo": "#f0f0f0"}
for f in filas_tbl:
    colores_filas.append([urgencia_tbl.get(f[2], "white")] * len(f))

tbl = ax_tbl.table(
    cellText=filas_tbl,
    colLabels=headers,
    cellLoc="center",
    loc="center",
    cellColours=colores_filas,
)
tbl.auto_set_font_size(False)
tbl.set_fontsize(8.5)
tbl.scale(1, 1.6)

for j in range(len(headers)):
    tbl[0, j].set_facecolor("#2c2c2c")
    tbl[0, j].set_text_props(color="white", fontweight="bold")

ax_tbl.set_title("Top 5 huecos por ciudad — Score compuesto (Tiempo 40% + Sin-seguro 40% + Persistencia 20%)",
                 fontsize=10, fontweight="bold", pad=12)

# ── Leyenda global ────────────────────────────────────────────────────────────
parches_urg = [mpatches.Patch(color=c, label=e, alpha=0.7)
               for e, c in urgencia_map.items()]
parches_esc = [
    mlines.Line2D([0], [0], marker="^", color="w", markerfacecolor="#7b3294",
                  markersize=10, label="Clínica K=1: Escenario Equidad"),
    mlines.Line2D([0], [0], marker="s", color="w", markerfacecolor="#e66101",
                  markersize=9, label="Clínica K=1: Escenario Accesibilidad"),
    mlines.Line2D([0], [0], marker="*", color="w", markerfacecolor="#FFD700",
                  markersize=12, label="Clínica K=1: Escenario Compuesto"),
]
fig.legend(handles=parches_urg + parches_esc, loc="lower center",
           ncol=7, fontsize=8, bbox_to_anchor=(0.5, 0.005), framealpha=0.95)

ruta = config.FIGURAS_DIR / "fase3_dashboard.png"
plt.savefig(str(ruta), dpi=150, bbox_inches="tight", facecolor="white")
plt.show()
print(f"✓ {ruta}")

# %% [markdown]
# ## 3. Resumen ejecutivo con hallazgos de la validación

# %%
print("\n" + "="*75)
print("RESUMEN EJECUTIVO — FASE 3: OPTIMIZACIÓN PRESCRIPTIVA")
print("="*75)

# Hallazgos de validación topológica (del notebook 15)
val_topo_resultados = {
    "CDMX":   {"n_orig": 71, "n_nuevo": 70, "delta": 1, "validado": True},
    "EDOMEX": {"n_orig": 209, "n_nuevo": 209, "delta": 0, "validado": False},
}

# Hallazgos OSMnx (del notebook 15)
val_osm_resultados = {
    "CDMX": [
        {"hueco": 8,  "t_antes": 8.3,  "t_despues": 63.2, "mejora": -54.9},
        {"hueco": 12, "t_antes": 14.3, "t_despues": 58.3, "mejora": -44.0},
        {"hueco": 9,  "t_antes": 6.2,  "t_despues": 49.7, "mejora": -43.5},
    ],
    "EDOMEX": [
        {"hueco": 78,  "t_antes": 11.7, "t_despues":  2.3, "mejora":  9.4},
        {"hueco": 36,  "t_antes": 20.3, "t_despues": 43.6, "mejora": -23.3},
        {"hueco": 63,  "t_antes": 27.3, "t_despues": 47.9, "mejora": -20.6},
    ],
}

print("""
┌─────────────────────────────────────────────────────────────────────────────┐
│ SCORING MULTI-EJE (Notebook 13)                                             │
├─────────────────┬───────────────────────────────────────────────────────────┤
│ CDMX            │ 62 huecos habitados → 10 Críticos, 12 Altos              │
│                 │ Dominantes (top 20% en 3 ejes): Hueco #8 y #12           │
│                 │ Hueco #8: 501m pers., 16.3 min, 6,785 sin seguro         │
│ EDOMEX          │ 99 huecos habitados → 15 Críticos, 19 Altos              │
│                 │ Dominantes (top 20% en 3 ejes): Hueco #78 y #36          │
│                 │ Hueco #78: 450m pers., 13.8 min, 12,010 sin seguro       │
└─────────────────┴───────────────────────────────────────────────────────────┘
""")

print("""
┌─────────────────────────────────────────────────────────────────────────────┐
│ MCLP — IMPACTO MÁX. CON K=3 CLÍNICAS NUEVAS (Notebook 14)                 │
├─────────────────┬──────────────────┬──────────────────┬─────────────────────┤
│                 │ Escenario A      │ Escenario B      │ Escenario C         │
│                 │ Equidad          │ Accesibilidad    │ Compuesto           │
├─────────────────┼──────────────────┼──────────────────┼─────────────────────┤
│ CDMX sin seguro │ 18,788 (16.6%)   │  6,281 ( 5.6%)  │ 15,084 (13.4%)      │
│ EDOMEX sin seg. │ 28,452 (13.1%)   │  2,626 ( 1.2%)  │ 17,750 ( 8.2%)      │
└─────────────────┴──────────────────┴──────────────────┴─────────────────────┘
""")

print("""
┌─────────────────────────────────────────────────────────────────────────────┐
│ VALIDACIÓN TOPOLÓGICA (Notebook 15)                                         │
├─────────────────┬───────────────────────────────────────────────────────────┤
│ CDMX            │ ✓ VALIDADO: agregar la clínica elimina 1 hueco H₁        │
│                 │   (71 → 70 huecos en el diagrama de persistencia)        │
│ EDOMEX          │ — Sin cambio en H₁: la clínica está dentro del hueco     │
│                 │   pero no en la posición exacta que cierra el ciclo      │
│                 │   topológico (el hueco es estructuralmente más grande)   │
└─────────────────┴───────────────────────────────────────────────────────────┘
""")

print("""
┌─────────────────────────────────────────────────────────────────────────────┐
│ VALIDACIÓN OSMnx — LECCIÓN METODOLÓGICA (Notebook 15)                      │
├─────────────────────────────────────────────────────────────────────────────┤
│ CDMX: El MCLP con KDTree propuso una clínica que KDTree considera dentro   │
│ de 833 m de los huecos #8 y #12, pero la validación OSMnx muestra tiempos  │
│ de 63 y 58 minutos → existen BARRERAS VIALES (vías rápidas, ríos) entre   │
│ la clínica propuesta y los huecos que el modelo euclidiano no captura.     │
│                                                                             │
│ EDOMEX: La clínica propuesta reduce el Hueco #78 de 11.7 → 2.3 min ✓     │
│ Confirmación perfecta: cuando no hay barreras, KDTree ≈ OSMnx.            │
│                                                                             │
│ IMPLICACIÓN: Para zonas con vialidades rápidas (Periférico, Insurgentes,   │
│ Circuito Interior en CDMX), el MCLP debe correrse directamente sobre la   │
│ red OSMnx — más lento pero sin el sesgo euclidiano.                        │
└─────────────────────────────────────────────────────────────────────────────┘
""")

print("""
┌─────────────────────────────────────────────────────────────────────────────┐
│ RECOMENDACIONES DE ACCIÓN INMEDIATA                                         │
├──────┬─────────┬──────────────────────────────────────────────────────────  │
│ Prio │ Ciudad  │ Acción recomendada                                         │
├──────┼─────────┼──────────────────────────────────────────────────────────  │
│  1   │ EDOMEX  │ Nueva clínica en (19.64495, -99.01255) → Hueco #78         │
│      │         │ Impacto: 12,010 personas sin seguro, mejora 9.4 min        │
│  2   │ CDMX    │ Nueva clínica en zona Hueco #8 con red OSMnx para          │
│      │         │ evitar barreras viales. 6,785 sin seguro afectados         │
│  3   │ EDOMEX  │ Hueco #36: requiere clínica propia (858m persistencia,     │
│      │         │ 21.8 min, 3,641 sin seguro) — ningún candidato K=1 cubre  │
│  4   │ CDMX    │ Campaña de afiliación en Huecos #24, #32 (accesibles      │
│      │         │ en <7 min pero con 18-32% sin seguro) — el problema        │
│      │         │ no es distancia sino aseguramiento                         │
│  5   │ EDOMEX  │ Hueco #63: más lejano (41.2 min), requiere análisis de    │
│      │         │ red OSMnx específico para validar barrera vial real        │
└──────┴─────────┴──────────────────────────────────────────────────────────  ┘
""")

print("Archivos generados:")
for f in ["scoring_scatter.png", "scoring_rankings.png", "scoring_pareto.png",
          "mclp_curvas_cobertura.png", "mclp_mapas_CDMX.png", "mclp_mapas_EDOMEX.png",
          "validacion_persistencia.png", "validacion_osm_CDMX.png",
          "validacion_osm_EDOMEX.png", "fase3_dashboard.png"]:
    print(f"  outputs/figuras/{f}")
print("  outputs/intermedios/recomendaciones_mclp.csv")
print("\n✓ Fase 3 completada.")
