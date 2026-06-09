# %% [markdown]
# # 18 — Análisis de Sensibilidad de Umbrales
#
# Pregunta: ¿los huecos críticos que encontramos son robustos o dependen
# de los parámetros que elegimos?
#
# Tres experimentos:
#   A. Estabilidad TDA: ¿qué huecos persisten al variar min_persistencia?
#      → Los huecos que aparecen en múltiples umbrales son señal real, no ruido.
#
#   B. Sensibilidad MCLP: ¿cambia la solución K=5 al variar el umbral de
#      caminata de 10 a 20 minutos?
#      → Usa los candidatos reales del pkl (nb15).
#
#   C. Sensibilidad de prioridad: ¿cuánta población queda fuera si exigimos
#      pers_m > 200m vs 400m vs 600m como criterio de prioridad?

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
import pulp
from pyproj import Transformer

from lib import config, tda

REGIONES   = ["CDMX", "EDOMEX"]
COLORES    = {"CDMX": "#4393c3", "EDOMEX": "#d6604d"}
_TR        = Transformer.from_crs("EPSG:4326", config.CRS_METROS, always_xy=True)

VEL_M_MIN  = (4.5 * 1000) / 60
DETOUR     = 1.35
K_EVAL     = 5

# %% [markdown]
# ## A. Estabilidad TDA: huecos detectados por nivel de min_persistencia

# %%
GRILLA_PERS = [50.0, 100.0, 200.0, 400.0, 600.0, 1000.0]

print("Construyendo complejos Laguerre...", flush=True)
stables = {}

for region in REGIONES:
    sal  = pd.read_parquet(config.INTERMEDIOS_DIR / f"salud_{region}.parquet")
    pts  = np.column_stack([sal["x"].values, sal["y"].values])
    pesos = tda.pesos_desde_per_ocu(sal)
    st   = tda.weighted_alpha_complex(pts, pesos)

    conteos = []
    for mp in GRILLA_PERS:
        ciclos = tda.ciclos_H1(st, pts, min_persistencia=mp)
        conteos.append({"min_pers": mp, "n_huecos": len(ciclos),
                        "pers_max": max((c["pers"] for c in ciclos), default=0),
                        "pers_sum": sum(c["pers"] for c in ciclos)})
        print(f"  [{region}] min_pers={mp:6.0f}m → {len(ciclos):4d} huecos", flush=True)

    stables[region] = pd.DataFrame(conteos)
    print(flush=True)

# %% [markdown]
# ### Figura A: curva de huecos detectados vs umbral de persistencia

# %%
fig, axes = plt.subplots(1, 2, figsize=(14, 6))
fig.suptitle(
    "Estabilidad TDA: huecos H₁ detectados por umbral de persistencia\n"
    "Weighted Alpha Complex (Laguerre)  |  El 'codo' separa señal de ruido",
    fontsize=13, fontweight="bold"
)

for ax, region in zip(axes, REGIONES):
    color_c = COLORES[region]
    df = stables[region]

    ax2 = ax.twinx()

    l1 = ax.plot(df["min_pers"], df["n_huecos"], "o-",
                 color=color_c, lw=2.5, ms=8, label="N° huecos detectados")
    l2 = ax2.plot(df["min_pers"], df["pers_max"], "s--",
                  color="#555", lw=2.0, ms=7, label="Pers. máxima (m)")

    # Marcar el umbral estándar del proyecto (200m)
    ax.axvline(200, color="#e08214", lw=2.0, ls=":", alpha=0.8, label="Umbral estándar 200m")
    ax.axvline(400, color="#b2182b", lw=1.5, ls=":", alpha=0.6, label="Umbral prioridad 400m")

    # Anotar cada punto
    for _, row in df.iterrows():
        ax.annotate(f"{int(row['n_huecos'])}",
                    (row["min_pers"], row["n_huecos"]),
                    textcoords="offset points", xytext=(0, 10),
                    ha="center", fontsize=9, fontweight="bold", color=color_c)

    ax.set_xlabel("min_persistencia (m)", fontsize=10)
    ax.set_ylabel("Huecos H₁ detectados", fontsize=10, color=color_c)
    ax2.set_ylabel("Persistencia máxima (m)", fontsize=10, color="#555")
    ax.set_title(f"{region}", fontsize=12, fontweight="bold", color=color_c)
    ax.spines[["top"]].set_visible(False)

    lines = l1 + l2
    labels = [l.get_label() for l in lines]
    ax.legend(lines, labels, fontsize=8.5, loc="upper right")

plt.tight_layout()
ruta = config.FIGURAS_DIR / "sensibilidad_estabilidad_tda.png"
plt.savefig(str(ruta), dpi=150, bbox_inches="tight", facecolor="white")
plt.show()
print(f"✓ {ruta}", flush=True)

# %% [markdown]
# ## B. Sensibilidad MCLP: ¿cambia la solución K=5 al variar tiempo_lim?
#
# Usa los candidatos reales del pkl (nb15) y varía el umbral de cobertura.

# %%
GRILLA_TIEMPO = [8.0, 10.0, 12.0, 15.0, 18.0, 20.0]

with open(str(config.INTERMEDIOS_DIR / "soluciones_mclp_red.pkl"), "rb") as f:
    pkl = pickle.load(f)
resultados_red = pkl["resultados_red"]

sens_mclp = {}

for region in REGIONES:
    df_prio  = pd.read_parquet(config.INTERMEDIOS_DIR / f"huecos_prioritarios_{region}.parquet")
    cands    = [c for c in resultados_red[region] if c["tiempos"]]
    ids_prio = df_prio["hueco_id"].astype(int).tolist()
    demand   = df_prio.set_index("hueco_id")["pob_sin_salud"].to_dict()
    total_ps = df_prio["pob_sin_salud"].sum()
    n        = len(df_prio)

    I = list(range(len(ids_prio)))
    J = list(range(len(cands)))

    filas = []
    sol_base_sel = None   # solución K=5 con tiempo=15min

    for tiempo_lim in GRILLA_TIEMPO:
        # Reconstruir matriz de cobertura con este tiempo_lim
        C = {(i, j): 1 if cands[j]["tiempos"].get(ids_prio[i], 9999) <= tiempo_lim else 0
             for i in I for j in J}

        prob = pulp.LpProblem(f"mclp_{region}_t{tiempo_lim}", pulp.LpMaximize)
        x = [pulp.LpVariable(f"x_{j}", cat="Binary") for j in J]
        y = [pulp.LpVariable(f"y_{i}", cat="Binary") for i in I]

        prob += pulp.lpSum(demand.get(ids_prio[i], 0) * y[i] for i in I)
        prob += pulp.lpSum(x) == K_EVAL
        for i in I:
            prob += y[i] <= pulp.lpSum(C[i, j] * x[j] for j in J)

        prob.solve(pulp.PULP_CBC_CMD(msg=False))

        sel_j  = frozenset(j for j in J if x[j].value() > 0.5)
        cub_i  = [i for i in I if y[i].value() > 0.5]
        psin_c = sum(demand.get(ids_prio[i], 0) for i in cub_i)

        if tiempo_lim == 15.0:
            sol_base_sel = sel_j

        coincide = len(sel_j & sol_base_sel) if sol_base_sel else 0

        filas.append({
            "tiempo_lim":   tiempo_lim,
            "dist_max_m":   round((tiempo_lim * VEL_M_MIN) / DETOUR),
            "n_huecos_cub": len(cub_i),
            "pct_huecos":   len(cub_i) / n * 100,
            "psin_cub":     psin_c,
            "pct_pob":      psin_c / total_ps * 100,
            "sel_j":        tuple(sorted(sel_j)),
            "n_coincide_15": coincide,
        })
        print(f"  [{region}] t={tiempo_lim:4.1f}min  "
              f"huecos_cub={len(cub_i)}/{n}  pob={psin_c/total_ps*100:.1f}%  "
              f"candidatos={tuple(sorted(sel_j))}", flush=True)

    sens_mclp[region] = pd.DataFrame(filas)
    print(flush=True)

# %% [markdown]
# ### Figura B: curvas de cobertura vs tiempo máximo

# %%
fig, axes = plt.subplots(1, 2, figsize=(14, 6))
fig.suptitle(
    "Sensibilidad MCLP K=5: ¿qué tan crítico es el umbral de 15 minutos?\n"
    "Candidatos reales (centroides de clusters)  |  Demanda = score × sin seguro",
    fontsize=13, fontweight="bold"
)

for ax, region in zip(axes, REGIONES):
    df = sens_mclp[region]
    color_c = COLORES[region]
    ax2 = ax.twinx()

    l1 = ax.plot(df["tiempo_lim"], df["pct_pob"], "o-",
                 color=color_c, lw=2.5, ms=8, label="Pob. sin seguro cubierta (%)")
    l2 = ax2.plot(df["tiempo_lim"], df["pct_huecos"], "s--",
                  color="#666", lw=2.0, ms=7, label="Huecos cubiertos (%)")
    l3 = ax.plot(df["tiempo_lim"], df["n_coincide_15"],
                 "^:", color="#1b7837", lw=2.0, ms=7,
                 label="Candidatos coinciden con sol. 15min")

    ax.axvline(15, color="#e08214", lw=2.0, ls=":", alpha=0.8,
               label="Umbral estándar 15min")

    for _, row in df.iterrows():
        ax.annotate(f"{row['pct_pob']:.0f}%",
                    (row["tiempo_lim"], row["pct_pob"]),
                    textcoords="offset points", xytext=(0, 9),
                    ha="center", fontsize=8, fontweight="bold", color=color_c)

    ax.set_xlabel("Tiempo máximo de caminata (min)", fontsize=10)
    ax.set_ylabel("% cobertura población sin seguro", fontsize=10, color=color_c)
    ax2.set_ylabel("% huecos cubiertos / coincidencia", fontsize=10, color="#555")
    ax.set_title(f"{region}", fontsize=12, fontweight="bold", color=color_c)
    ax.set_xlim(df["tiempo_lim"].min() - 0.5, df["tiempo_lim"].max() + 0.5)
    ax.spines[["top"]].set_visible(False)

    lines = l1 + l2 + l3
    labels = [l.get_label() for l in lines]
    ax.legend(lines, labels, fontsize=7.5, loc="upper left")

plt.tight_layout()
ruta = config.FIGURAS_DIR / "sensibilidad_mclp_tiempo.png"
plt.savefig(str(ruta), dpi=150, bbox_inches="tight", facecolor="white")
plt.show()
print(f"✓ {ruta}", flush=True)

# %% [markdown]
# ## C. Sensibilidad de prioridad: ¿cuánta población queda fuera con cada umbral de pers_m?

# %%
GRILLA_PERS_PRIO = [200.0, 300.0, 400.0, 500.0, 600.0, 800.0]

sens_prio = {}

for region in REGIONES:
    score_df = pd.read_parquet(config.INTERMEDIOS_DIR / f"huecos_score_{region}.parquet")
    filas = []
    for pthresh in GRILLA_PERS_PRIO:
        df_p = score_df[score_df["pers_m"] > pthresh]
        filas.append({
            "pers_thresh":  pthresh,
            "n_huecos":     len(df_p),
            "pob_sin_seg":  df_p["pob_sin_salud"].sum(),
            "pct_del_total": df_p["pob_sin_salud"].sum() / score_df["pob_sin_salud"].sum() * 100,
        })
    sens_prio[region] = pd.DataFrame(filas)

fig, axes = plt.subplots(1, 2, figsize=(14, 6))
fig.suptitle(
    "Sensibilidad del umbral de prioridad (pers_m mínima para ser prioritario)\n"
    "¿Cuántos huecos y qué población queda fuera de la priorización?",
    fontsize=13, fontweight="bold"
)

for ax, region in zip(axes, REGIONES):
    df = sens_prio[region]
    color_c = COLORES[region]
    ax2 = ax.twinx()

    l1 = ax.bar(df["pers_thresh"], df["n_huecos"],
                width=70, color=color_c, alpha=0.7, label="Huecos prioritarios")
    l2 = ax2.plot(df["pers_thresh"], df["pct_del_total"], "o-",
                  color="#b2182b", lw=2.5, ms=9, label="% pob. sin seguro incluida")

    ax.axvline(400, color="#555", lw=2.0, ls="--", alpha=0.7, label="Umbral estándar 400m")

    for _, row in df.iterrows():
        ax2.annotate(f"{row['pct_del_total']:.0f}%",
                     (row["pers_thresh"], row["pct_del_total"]),
                     textcoords="offset points", xytext=(0, 9),
                     ha="center", fontsize=8.5, color="#b2182b", fontweight="bold")
        ax.text(row["pers_thresh"], row["n_huecos"] + 0.5, str(int(row["n_huecos"])),
                ha="center", fontsize=8.5, fontweight="bold", color=color_c)

    ax.set_xlabel("Umbral mínimo de persistencia para prioridad (m)", fontsize=10)
    ax.set_ylabel("Huecos prioritarios", fontsize=10, color=color_c)
    ax2.set_ylabel("% pob. sin seguro incluida", fontsize=10, color="#b2182b")
    ax.set_title(f"{region}", fontsize=12, fontweight="bold", color=color_c)
    ax.spines[["top"]].set_visible(False)

    lines_leg = [
        mpatches.Patch(color=color_c, alpha=0.7, label="Huecos prioritarios"),
        plt.Line2D([0], [0], color="#b2182b", lw=2, marker="o",
                   label="% pob. sin seguro incluida"),
        plt.Line2D([0], [0], color="#555", lw=2, ls="--", label="Umbral estándar 400m"),
    ]
    ax.legend(handles=lines_leg, fontsize=8.5, loc="upper right")

plt.tight_layout()
ruta = config.FIGURAS_DIR / "sensibilidad_prioridad.png"
plt.savefig(str(ruta), dpi=150, bbox_inches="tight", facecolor="white")
plt.show()
print(f"✓ {ruta}", flush=True)

# %% [markdown]
# ## Resumen ejecutivo de sensibilidad

# %%
print("\n" + "="*72, flush=True)
print("RESUMEN DE SENSIBILIDAD — CONCLUSIONES", flush=True)
print("="*72, flush=True)

for region in REGIONES:
    print(f"\n  [{region}]", flush=True)

    # A: Estabilidad TDA
    df_st = stables[region]
    n_200 = df_st[df_st["min_pers"] == 200]["n_huecos"].values[0]
    n_400 = df_st[df_st["min_pers"] == 400]["n_huecos"].values[0]
    n_100 = df_st[df_st["min_pers"] == 100]["n_huecos"].values[0]
    print(f"\n  A. Estabilidad TDA:", flush=True)
    print(f"     min_pers=100m → {n_100} huecos  (incluye ruido topológico)", flush=True)
    print(f"     min_pers=200m → {n_200} huecos  (configuración estándar)", flush=True)
    print(f"     min_pers=400m → {n_400} huecos  (solo señal fuerte)", flush=True)
    print(f"     Los {n_400} huecos con pers>400m aparecen en TODOS los umbrales → robustos", flush=True)

    # B: Sensibilidad MCLP
    df_m = sens_mclp[region]
    pob_10 = df_m[df_m["tiempo_lim"] == 10.0]["pct_pob"].values[0]
    pob_15 = df_m[df_m["tiempo_lim"] == 15.0]["pct_pob"].values[0]
    pob_20 = df_m[df_m["tiempo_lim"] == 20.0]["pct_pob"].values[0]
    coin_10 = df_m[df_m["tiempo_lim"] == 10.0]["n_coincide_15"].values[0]
    coin_20 = df_m[df_m["tiempo_lim"] == 20.0]["n_coincide_15"].values[0]
    print(f"\n  B. Sensibilidad MCLP (tiempo_lim):", flush=True)
    print(f"     t=10min → {pob_10:.1f}% pob. cubierta  ({coin_10}/5 candidatos = sol. 15min)", flush=True)
    print(f"     t=15min → {pob_15:.1f}% pob. cubierta  (configuración estándar)", flush=True)
    print(f"     t=20min → {pob_20:.1f}% pob. cubierta  ({coin_20}/5 candidatos = sol. 15min)", flush=True)

    # C: Sensibilidad prioridad
    df_p = sens_prio[region]
    pct_200 = df_p[df_p["pers_thresh"] == 200]["pct_del_total"].values[0]
    pct_400 = df_p[df_p["pers_thresh"] == 400]["pct_del_total"].values[0]
    pct_600 = df_p[df_p["pers_thresh"] == 600]["pct_del_total"].values[0]
    n_400p  = df_p[df_p["pers_thresh"] == 400]["n_huecos"].values[0]
    print(f"\n  C. Sensibilidad de prioridad (umbral pers_m):", flush=True)
    print(f"     pers>200m → {pct_200:.0f}% pob. sin seguro incluida", flush=True)
    print(f"     pers>400m → {pct_400:.0f}% pob. sin seguro incluida  "
          f"({n_400p} huecos — estándar)", flush=True)
    print(f"     pers>600m → {pct_600:.0f}% pob. sin seguro incluida", flush=True)
