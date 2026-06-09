# %% [markdown]
# # 17b — Sensibilidad K=5→10: curvas de rendimiento decreciente
#
# Pregunta: ¿vale la pena invertir más allá de K=5?
# Re-corremos el MCLP para K=6,7,8,9,10 con los mismos candidatos
# y medimos la curva de cierre topológico + cobertura poblacional.

# %%
import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import pickle
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import pulp
from scipy.spatial import cKDTree
from pyproj import Transformer

from lib import config

REGIONES   = ["CDMX", "EDOMEX"]
K_RANGO    = list(range(5, 11))
TIEMPO_LIM = 15.0
COLORES    = {"CDMX": "#4393c3", "EDOMEX": "#d6604d"}

_TR = Transformer.from_crs("EPSG:4326", config.CRS_METROS, always_xy=True)

# %% [markdown]
# ## 1. Cargar candidatos MCLP y huecos prioritarios

# %%
with open(str(config.INTERMEDIOS_DIR / "soluciones_mclp_red.pkl"), "rb") as f:
    pkl = pickle.load(f)
resultados_red = pkl["resultados_red"]

huecos_prio = {}
for region in REGIONES:
    df = pd.read_parquet(config.INTERMEDIOS_DIR / f"huecos_prioritarios_{region}.parquet")
    x_h, y_h = _TR.transform(df["lon"].values, df["lat"].values)
    df = df.copy()
    df["x_utm"] = x_h
    df["y_utm"] = y_h
    huecos_prio[region] = df

# %% [markdown]
# ## 2. MCLP para cada K y test de cierre topológico

# %%
def clasificar_cierre(df_prio, pts_nuevas):
    """Para cada hueco prioritario, distancia a clínica nueva más cercana → estado."""
    tree = cKDTree(pts_nuevas)
    pts_h = np.column_stack([df_prio["x_utm"].values, df_prio["y_utm"].values])
    dists, _ = tree.query(pts_h, k=1)
    df = df_prio.copy()
    df["dist_nueva"] = dists
    df["estado"] = "Persistente"
    df.loc[df["dist_nueva"] < df["pers_m"] * 2, "estado"] = "Parcial"
    df.loc[df["dist_nueva"] < df["pers_m"],      "estado"] = "Cerrado"
    return df


curvas = {}

for region in REGIONES:
    df_prio  = huecos_prio[region]
    cands    = [c for c in resultados_red[region] if c["tiempos"]]
    n        = len(df_prio)
    ids_prio = df_prio["hueco_id"].astype(int).tolist()
    demand   = df_prio.set_index("hueco_id")["pob_sin_salud"].to_dict()
    total_ps = df_prio["pob_sin_salud"].sum()

    I = list(range(len(ids_prio)))
    J = list(range(len(cands)))
    C = {(i, j): 1 if cands[j]["tiempos"].get(ids_prio[i], 9999) <= TIEMPO_LIM else 0
         for i in I for j in J}

    pts_cands = np.array([[c["x_clinica"], c["y_clinica"]] for c in cands])

    filas = []
    for K in K_RANGO:
        if K > len(cands):
            break

        prob = pulp.LpProblem(f"mclp_{region}_K{K}", pulp.LpMaximize)
        x = [pulp.LpVariable(f"x_{j}", cat="Binary") for j in J]
        y = [pulp.LpVariable(f"y_{i}", cat="Binary") for i in I]

        prob += pulp.lpSum(demand.get(ids_prio[i], 0) * y[i] for i in I)
        prob += pulp.lpSum(x) == K
        for i in I:
            prob += y[i] <= pulp.lpSum(C[i, j] * x[j] for j in J)

        prob.solve(pulp.PULP_CBC_CMD(msg=False))

        sel_j   = [j for j in J if x[j].value() > 0.5]
        cub_i   = [i for i in I if y[i].value() > 0.5]
        psin_c  = sum(demand.get(ids_prio[i], 0) for i in cub_i)
        pts_sel = pts_cands[sel_j]

        df_k  = clasificar_cierre(df_prio, pts_sel)
        cnt_k = df_k["estado"].value_counts()

        n_c = cnt_k.get("Cerrado",     0)
        n_p = cnt_k.get("Parcial",     0)
        n_r = cnt_k.get("Persistente", 0)

        filas.append({
            "K":              K,
            "n_cerrado":      n_c,
            "n_parcial":      n_p,
            "n_persistente":  n_r,
            "pct_cerrado":    n_c / n * 100,
            "pct_parcial":    n_p / n * 100,
            "pct_persistente": n_r / n * 100,
            "pct_efectivo":   (n_c + n_p) / n * 100,
            "psin_cub":       psin_c,
            "pct_psin":       psin_c / total_ps * 100,
            "n_mclp":         len(cub_i),
            "pct_mclp":       len(cub_i) / n * 100,
        })
        print(f"  [{region}] K={K}  cerrados={n_c}/{n}  pob={psin_c/total_ps*100:.1f}%", flush=True)

    curvas[region] = pd.DataFrame(filas)
    print(flush=True)

# %% [markdown]
# ## 3. Figura principal: curvas de rendimiento decreciente

# %%
fig, axes = plt.subplots(2, 2, figsize=(16, 12))
fig.suptitle(
    "Sensibilidad K=5→10: ¿cuándo se agotan los beneficios?\n"
    "Cierre topológico de huecos prioritarios y cobertura poblacional",
    fontsize=13, fontweight="bold"
)

for col, region in enumerate(REGIONES):
    cur     = curvas[region]
    color_c = COLORES[region]
    Ks      = cur["K"].values

    # --- Panel superior: áreas apiladas de cierre ---
    ax_top = axes[0][col]
    base   = np.zeros(len(Ks))

    for estado, col_e, key in [
        ("Cerrado",     "#1b7837", "pct_cerrado"),
        ("Parcial",     "#f6a623", "pct_parcial"),
        ("Persistente", "#d6604d", "pct_persistente"),
    ]:
        vals = cur[key].values
        ax_top.fill_between(Ks, base, base + vals,
                            color=col_e, alpha=0.75, label=estado)
        # Etiqueta en la zona verde (cerrados) si es suficientemente alta
        if key == "pct_cerrado":
            for k_val, b, v in zip(Ks, base, vals):
                if v > 4:
                    ax_top.text(k_val, b + v / 2, f"{v:.0f}%",
                                ha="center", va="center",
                                fontsize=8.5, fontweight="bold", color="white")
        base += vals

    ax_top.set_xlim(Ks[0] - 0.3, Ks[-1] + 0.3)
    ax_top.set_ylim(0, 100)
    ax_top.set_xticks(Ks)
    ax_top.set_xlabel("K — clínicas nuevas", fontsize=10)
    ax_top.set_ylabel("% huecos prioritarios", fontsize=10)
    ax_top.set_title(f"{region} — Cierre topológico",
                     fontsize=11, fontweight="bold", color=color_c)
    ax_top.legend(fontsize=8.5, loc="upper left")
    ax_top.spines[["top", "right"]].set_visible(False)

    # --- Panel inferior: curvas de cobertura ---
    ax_bot = axes[1][col]

    ax_bot.plot(Ks, cur["pct_psin"],    "o-",
                color=color_c, lw=2.5, ms=8,
                label="Pob. sin seguro cubierta (%)")
    ax_bot.plot(Ks, cur["pct_mclp"],    "s--",
                color="#666", lw=2.0, ms=7,
                label="Huecos con acceso ≤15 min (%)")
    ax_bot.plot(Ks, cur["pct_cerrado"], "^:",
                color="#1b7837", lw=2.0, ms=7,
                label="Huecos cerrados topológ. (%)")
    ax_bot.plot(Ks, cur["pct_efectivo"],"D-.",
                color="#762a83", lw=2.0, ms=7,
                label="Cerrado + Parcial (%)")

    # Anotar población cubierta
    for _, row in cur.iterrows():
        ax_bot.annotate(f"{row['pct_psin']:.0f}%",
                        (row["K"], row["pct_psin"]),
                        textcoords="offset points", xytext=(0, 9),
                        ha="center", fontsize=8, color=color_c, fontweight="bold")

    # Línea vertical en el codo (mayor incremento marginal)
    dpsin = np.diff(cur["pct_psin"].values)
    if len(dpsin) > 0:
        codo_i = int(np.argmax(dpsin))
        codo_K = Ks[codo_i]
        ax_bot.axvline(codo_K, color="#aaa", lw=1.5, ls="--", alpha=0.7)
        ax_bot.text(codo_K + 0.1, 5, f"Mayor salto\nK={codo_K}",
                    ha="left", fontsize=8, color="#777")

    ax_bot.set_xlim(Ks[0] - 0.3, Ks[-1] + 0.3)
    ax_bot.set_ylim(0, 108)
    ax_bot.set_xticks(Ks)
    ax_bot.set_xlabel("K — clínicas nuevas", fontsize=10)
    ax_bot.set_ylabel("% cubierto", fontsize=10)
    ax_bot.set_title(f"{region} — Curvas de cobertura",
                     fontsize=11, fontweight="bold", color=color_c)
    ax_bot.legend(fontsize=8, loc="lower right")
    ax_bot.spines[["top", "right"]].set_visible(False)

plt.tight_layout()
ruta = config.FIGURAS_DIR / "validacion_curva_k.png"
plt.savefig(str(ruta), dpi=150, bbox_inches="tight", facecolor="white")
plt.show()
print(f"✓ {ruta}", flush=True)

# %% [markdown]
# ## 4. Tabla resumen ejecutivo

# %%
print("\n" + "="*80, flush=True)
print("ANÁLISIS K=5→10 — TABLA COMPARATIVA", flush=True)
print("="*80, flush=True)

for region in REGIONES:
    cur = curvas[region]
    n   = int(cur["n_cerrado"].iloc[0] + cur["n_parcial"].iloc[0]
              + cur["n_persistente"].iloc[0])
    print(f"\n  [{region}]  {n} huecos prioritarios", flush=True)
    print(f"  {'K':>3}  {'Cerrados':>16}  {'Parciales':>14}  "
          f"{'Persistentes':>16}  {'Pob. sin seguro':>16}  Δpob", flush=True)
    print(f"  {'—'*80}", flush=True)

    prev_psin = None
    for _, row in cur.iterrows():
        K   = int(row["K"])
        delta = ""
        if prev_psin is not None:
            d = row["pct_psin"] - prev_psin
            delta = f"(+{d:.1f}%)"
        prev_psin = row["pct_psin"]
        print(f"  {K:3d}  "
              f"{int(row['n_cerrado']):3d} ({row['pct_cerrado']:5.1f}%)    "
              f"{int(row['n_parcial']):3d} ({row['pct_parcial']:4.1f}%)  "
              f"{int(row['n_persistente']):3d} ({row['pct_persistente']:5.1f}%)  "
              f"{row['pct_psin']:14.1f}%  {delta}", flush=True)

print("""
  Definiciones:
    Cerrado    = nueva clínica dentro del radio de persistencia (r) del hueco → cierre topológico
    Parcial    = clínica entre 1x y 2x el radio → acceso mejorado, topología persiste
    Persistente= clínica a mas de 2x el radio → requiere intervencion adicional
    Δpob       = incremento marginal en poblacion sin seguro cubierta al pasar de K-1 a K
""", flush=True)
