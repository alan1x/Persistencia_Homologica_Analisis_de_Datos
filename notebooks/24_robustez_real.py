# %% [markdown]
# # 24 — Robustez de verdad: perturbar los datos, no el filtro
#
# El notebook 21 cambia el umbral sobre un mismo diagrama. Un hueco con persistencia
# ≥ 600 m pasa por definición los filtros de 100, 200 y 400 m, así que su 100% no
# puede fallar. Aquí se cambian los **datos** y se vuelve a calcular todo:
#
# 1. **Eliminación:** se quita al azar una fracción de establecimientos. Representa
#    omisiones del DENUE y negocios cerrados. Quitar puntos tiende a mantener huecos,
#    así que es la prueba más fácil de pasar.
# 2. **Ruido:** cada coordenada se mueve con ruido gaussiano de desviación σ. Con σ
#    chico imita el error de geocodificación. Con σ grande funciona como **modelo
#    nulo**: conserva la densidad a gran escala y borra la estructura fina.
#
# Un hueco original "sobrevive" a una réplica si esta tiene un hueco con persistencia
# ≥ 200 m a menos de max(100 m, media muerte) de su centro.

# %%
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.spatial import cKDTree

from lib import config, huecos, viz_eval as ve

ve.aplicar()
INT = config.INTERMEDIOS_DIR
SALIDA = config.OUTPUTS_DIR / "auditoria"
SALIDA.mkdir(exist_ok=True)
REGIONES = ["CDMX", "EDOMEX"]
ELIMINAR = [0.05, 0.10, 0.20, 0.30]
SIGMAS = [10, 25, 50, 100, 250, 500, 1000]
N_REP = 40
COLOR = {"CDMX": ve.AZUL, "EDOMEX": ve.NARANJA}


def replica(P, base, tipo, valor, semilla):
    rng = np.random.default_rng(semilla)
    if tipo == "eliminar":
        Q = P[rng.random(len(P)) >= valor]
    else:
        Q = P + rng.normal(0, valor, P.shape)
    h = huecos.extraer_huecos(huecos.complejo(Q), Q, 200)
    if len(h) == 0:
        return 0, np.zeros(len(base), bool), np.zeros(len(base)), 0.0
    d, i = cKDTree(h[["cx", "cy"]].values).query(base[["cx", "cy"]].values)
    vivo = d < np.maximum(100.0, base["death"].values / 2)
    pers = np.where(vivo, h["pers"].values[i], 0.0)
    return len(h), vivo, pers, float(h["pers"].max())


# %%
resumen, por_hueco = [], {}
for r in REGIONES:
    sal = pd.read_parquet(INT / f"salud_{r}.parquet")
    P = sal[["x", "y"]].to_numpy()
    base = huecos.extraer_huecos(huecos.complejo(P), P, 200)
    pr = pd.read_parquet(INT / f"huecos_prioritarios_{r}.parquet")
    prio = np.isin(base["pers"].round(3), pr["pers_m"].round(3))
    t = base.drop(columns="par").copy()
    t["prioritario"] = prio
    esc = [("eliminar", v) for v in ELIMINAR] + [("ruido", v) for v in SIGMAS]
    for tipo, val in esc:
        out = Parallel(n_jobs=6)(delayed(replica)(P, base, tipo, val, 1000 * i + int(val * 100))
                                 for i in range(N_REP))
        n = np.array([o[0] for o in out])
        vivo = np.array([o[1] for o in out])
        maximos = np.array([o[3] for o in out])
        pers = np.array([o[2] for o in out])
        col = f"{tipo}_{val}"
        t[f"sobrevive_{col}"] = vivo.mean(axis=0)
        fila = {
            "region": r, "tipo": tipo, "valor": val, "huecos_base": len(base),
            "huecos_media": n.mean(), "huecos_p5": np.percentile(n, 5), "huecos_p95": np.percentile(n, 95),
            "sobrevive_todos": vivo.mean(), "sobrevive_prioritarios": vivo[:, prio].mean(),
            "prio_estables_80": int((vivo[:, prio].mean(axis=0) >= 0.8).sum()),
            "n_prio": int(prio.sum()), "pers_max_media": maximos.mean(),
            "pers_max_p95": np.percentile(maximos, 95),
        }
        resumen.append(fila)
        print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in fila.items()}, flush=True)
    # Prueba nula: ¿qué huecos superan a la mayor persistencia que produce la densidad sola?
    nulo = [x for x in resumen if x["region"] == r and x["tipo"] == "ruido" and x["valor"] == 1000][0]
    t["supera_nulo"] = t["pers"] > nulo["pers_max_p95"]
    por_hueco[r] = t
    t.to_csv(SALIDA / f"robustez_real_{r}.csv", index=False)

df = pd.DataFrame(resumen)
df.to_csv(SALIDA / "robustez_real_resumen.csv", index=False)
extra = {r: {"huecos": len(por_hueco[r]), "prioritarios": int(por_hueco[r]["prioritario"].sum()),
             "superan_nulo": int(por_hueco[r]["supera_nulo"].sum()),
             "prio_superan_nulo": int((por_hueco[r]["supera_nulo"] & por_hueco[r]["prioritario"]).sum())}
         for r in REGIONES}
(SALIDA / "robustez_real_nulo.json").write_text(json.dumps(extra, indent=2), encoding="utf-8")
print(json.dumps(extra, indent=2))

# %% [markdown]
# ## Figura 1: supervivencia de los huecos prioritarios

# %%
fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), sharey=True)
for r in REGIONES:
    s = df[(df.region == r) & (df.tipo == "eliminar")]
    axes[0].plot(s.valor * 100, s.sobrevive_prioritarios * 100, color=COLOR[r], lw=2, marker="o", ms=6, label=r)
    s = df[(df.region == r) & (df.tipo == "ruido")]
    axes[1].plot(s.valor, s.sobrevive_prioritarios * 100, color=COLOR[r], lw=2, marker="o", ms=6, label=r)
axes[0].set_xlabel("Establecimientos eliminados (%)")
axes[0].set_ylabel("Huecos prioritarios que sobreviven (%)")
axes[0].set_title("Quitar establecimientos")
axes[0].legend(loc="lower left")
axes[1].set_xscale("log")
axes[1].set_xticks(SIGMAS)
axes[1].set_xticklabels(SIGMAS)
axes[1].minorticks_off()
axes[1].set_xlabel("Ruido en las coordenadas, σ (m)")
axes[1].set_title("Mover coordenadas")
axes[0].set_ylim(0, 104)
ve.titulo(fig, "Resisten datos incompletos; el ruido grande los borra",
          f"Promedio de {N_REP} réplicas por escenario, recalculando la persistencia en cada una.")
fig.tight_layout(rect=(0, 0, 1, 0.91))
ve.guardar(fig, config.FIGURAS_DIR / "robustez_real_supervivencia.png")

# %% [markdown]
# ## Figura 2: cuántos huecos produce la densidad sola

# %%
fig, ax = plt.subplots(figsize=(9, 5))
for r in REGIONES:
    s = df[(df.region == r) & (df.tipo == "ruido")]
    ax.plot(s.valor, s.huecos_media, color=COLOR[r], lw=2, marker="o", ms=6, label=r)
    ax.fill_between(s.valor, s.huecos_p5, s.huecos_p95, color=COLOR[r], alpha=0.15, lw=0)
    ax.axhline(s.huecos_base.iloc[0], color=COLOR[r], lw=1, ls="--")
ax.set_xscale("log")
ax.set_xticks(SIGMAS)
ax.set_xticklabels(SIGMAS)
ax.minorticks_off()
ax.set_ylim(0)
ax.set_xlabel("Ruido en las coordenadas, σ (m)")
ax.set_ylabel("Huecos con persistencia ≥ 200 m")
ax.legend(loc="upper left")
ve.titulo(fig, "¿Cuántos huecos quedan al borrar la estructura fina?",
          "La línea punteada es el dato real; la banda va del percentil 5 al 95.")
fig.tight_layout(rect=(0, 0, 1, 0.91))
ve.guardar(fig, config.FIGURAS_DIR / "robustez_real_nulo.png")
