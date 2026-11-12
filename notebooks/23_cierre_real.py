# %% [markdown]
# # 23 — ¿Las clínicas propuestas cierran los huecos? Medición directa
#
# `17_validacion_topologica.py` decide con una regla de distancia (d < pers) y calcula
# la reducción sumando la persistencia de los huecos que no llama persistentes. Aquí
# se agregan las clínicas a la nube de puntos, se recalcula la persistencia y se
# compara hueco por hueco.
#
# Se usa el Alpha clásico porque de ahí salen los huecos prioritarios (notebook 22).
#
# Comparaciones con el mismo número de clínicas:
# - **MCLP:** la solución del reporte (7 en CDMX, 8 en EDOMEX).
# - **Al azar:** K candidatos del mismo MCLP, elegidos al azar.
# - **Topológica:** una clínica en el centro del disco vacío de los K huecos prioritarios
#   más persistentes.
#
# Cerrar huecos no es lo que optimiza el MCLP, así que también se mide lo que sí persigue:
# personas sin seguro a menos de 833 m y distancia a la clínica más cercana dentro de los
# discos vacíos, ponderada por esas personas.

# %%
import json
import pickle
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
N_AZAR = 100
COLOR_ESTADO = {"intacto": ve.GRIS, "modificado": ve.NARANJA, "cerrado": ve.AZUL}
RADIO_COBERTURA = 15 * (4500 / 60) / 1.35  # 833 m: 15 min, 4.5 km/h, rodeo 1.35

# %%
pk = pickle.load(open(INT / "soluciones_mclp_red.pkl", "rb"))
sub = pickle.load(open(INT / "clinicas_subregionales_EDOMEX.pkl", "rb"))
c7 = pk["resultados_red"]["CDMX"]
CLINICAS = {
    "CDMX": np.array([[c7[j]["x_clinica"], c7[j]["y_clinica"]] for j in pk["soluciones"]["CDMX"][7]["sel_idx"]]),
    "EDOMEX": np.array([[c["x_clinica"], c["y_clinica"]] for c in sub["clinicas_sub"]]),
}
CANDIDATOS = {r: np.array([[c["x_clinica"], c["y_clinica"]] for c in pk["resultados_red"][r]]) for r in REGIONES}


def rejillas(pp, paso=50.0):
    """Puntos cada `paso` metros dentro del disco vacío de cada hueco."""
    out = []
    for _, h in pp.iterrows():
        n = int(h["death"] // paso) + 1
        ej = np.arange(-n, n + 1) * paso
        xx, yy = np.meshgrid(ej, ej)
        dentro = xx ** 2 + yy ** 2 <= h["death"] ** 2
        out.append(np.column_stack([xx[dentro] + h["cx"], yy[dentro] + h["cy"]]))
    return out


def efecto_personas(P, nuevas, centros, psin, grids):
    """Cobertura (<833 m) y distancia media ponderada por personas sin seguro."""
    d = cKDTree(nuevas).query(centros)[0]
    arbol = cKDTree(np.vstack([P, nuevas]))
    media = np.array([arbol.query(g)[0].mean() for g in grids])
    return {"psin_cubiertos": float(psin[d <= RADIO_COBERTURA].sum()),
            "dist_media_m": float((media * psin).sum() / psin.sum())}


def medir(P, base, prio_mask, nuevas):
    """Recalcula con las clínicas nuevas y sigue cada hueco."""
    Pn = np.vstack([P, nuevas])
    des = huecos.extraer_huecos(huecos.complejo(Pn), Pn, 200)
    pares = set(des["par"])
    seg = [huecos.seguir_hueco(h, des, pares) for _, h in base.iterrows()]
    t = base.copy()
    t["estado"] = [s[0] for s in seg]
    t["pers_despues"] = [s[1] for s in seg]
    pr = t[prio_mask]
    return t, {
        "huecos_total_antes": len(base), "huecos_total_despues": len(des),
        "pers_total_antes": float(base["pers"].sum()), "pers_total_despues": float(des["pers"].sum()),
        "prio_cerrados": int((pr["estado"] == "cerrado").sum()),
        "prio_modificados": int((pr["estado"] == "modificado").sum()),
        "prio_mas_chicos": int(((pr["estado"] == "modificado") & (pr["pers_despues"] < pr["pers"])).sum()),
        "prio_intactos": int((pr["estado"] == "intacto").sum()),
        "prio_pers_antes": float(pr["pers"].sum()),
        "prio_pers_despues": float(pr["pers_despues"].sum()),
        "prio_reduccion_pct": float((1 - pr["pers_despues"].sum() / pr["pers"].sum()) * 100),
    }


# %%
resultados, tablas, azar = {}, {}, {}
for r in REGIONES:
    sal = pd.read_parquet(INT / f"salud_{r}.parquet")
    P = sal[["x", "y"]].to_numpy()
    base = huecos.extraer_huecos(huecos.complejo(P), P, 200)
    pr = pd.read_parquet(INT / f"huecos_prioritarios_{r}.parquet")
    prio_mask = np.isin(base["pers"].round(3), pr["pers_m"].round(3))
    assert prio_mask.sum() == len(pr), (prio_mask.sum(), len(pr))
    K = len(CLINICAS[r])

    tabla, mclp = medir(P, base, prio_mask, CLINICAS[r])

    # Efecto sobre personas: mismos centros y mismas personas que usa el reporte
    prk = pr.assign(k=pr["pers_m"].round(3)).set_index("k")
    psin = prk.loc[base.loc[prio_mask, "pers"].round(3), "pob_sin_salud"].to_numpy(float)
    centros = base.loc[prio_mask, ["bx", "by"]].to_numpy()
    grids = rejillas(base[prio_mask])
    dist_antes = np.array([cKDTree(P).query(g)[0].mean() for g in grids])
    dist_base = float((dist_antes * psin).sum() / psin.sum())
    mclp["personas"] = efecto_personas(P, CLINICAS[r], centros, psin, grids)
    mclp["personas"]["psin_total"] = float(psin.sum())
    mclp["personas"]["dist_media_antes_m"] = dist_base

    # Regla del reporte, igual que en el notebook 17
    d, _ = cKDTree(CLINICAS[r]).query(tabla[["bx", "by"]].values)
    tabla["regla"] = np.where(d < tabla["pers"], "Cerrado",
                              np.where(d < 2 * tabla["pers"], "Parcial", "Persistente"))
    pp = tabla[prio_mask]
    mclp["regla_cerrados"] = int((pp["regla"] == "Cerrado").sum())
    mclp["regla_parciales"] = int((pp["regla"] == "Parcial").sum())
    mclp["regla_persistentes"] = int((pp["regla"] == "Persistente").sum())
    mclp["regla_reduccion_pct"] = float(
        (1 - pp.loc[pp["regla"] == "Persistente", "pers"].sum() / pp["pers"].sum()) * 100)
    mclp["cruce_regla_vs_real"] = pd.crosstab(pp["regla"], pp["estado"]).to_dict()

    # Exacto: ¿alguna clínica nueva cae dentro del disco vacío del hueco?
    dc, _ = cKDTree(CLINICAS[r]).query(pp[["cx", "cy"]].values)
    mclp["prio_clinica_dentro_disco_vacio"] = int((dc < pp["death"]).sum())

    # Línea base topológica
    top = pp.nlargest(K, "pers")[["cx", "cy"]].to_numpy()
    _, topo = medir(P, base, prio_mask, top)
    topo["personas"] = efecto_personas(P, top, centros, psin, grids)

    # Línea base al azar, entre los mismos candidatos
    rng = np.random.default_rng(23)
    sorteos = [rng.choice(len(CANDIDATOS[r]), K, replace=False) for _ in range(N_AZAR)]
    az = Parallel(n_jobs=6)(
        delayed(lambda s: medir(P, base, prio_mask, CANDIDATOS[r][s])[1])(s) for s in sorteos)
    az_p = [efecto_personas(P, CANDIDATOS[r][s], centros, psin, grids) for s in sorteos]

    resultados[r] = {"K": K, "mclp": mclp, "topologica": topo,
                     "azar_reduccion_media": float(np.mean([a["prio_reduccion_pct"] for a in az])),
                     "azar_reduccion_p5": float(np.percentile([a["prio_reduccion_pct"] for a in az], 5)),
                     "azar_reduccion_p95": float(np.percentile([a["prio_reduccion_pct"] for a in az], 95)),
                     "azar_cerrados_media": float(np.mean([a["prio_cerrados"] for a in az])),
                     "azar_psin_media": float(np.mean([a["psin_cubiertos"] for a in az_p])),
                     "azar_psin_p95": float(np.percentile([a["psin_cubiertos"] for a in az_p], 95)),
                     "azar_dist_media": float(np.mean([a["dist_media_m"] for a in az_p]))}
    tablas[r] = pp
    azar[r] = [a["prio_reduccion_pct"] for a in az]
    azar[r + "_psin"] = [a["psin_cubiertos"] for a in az_p]
    print(r, json.dumps(resultados[r], indent=1, ensure_ascii=False, default=str), flush=True)
    pp.drop(columns="par").to_csv(SALIDA / f"cierre_real_{r}.csv", index=False)

(SALIDA / "cierre_real.json").write_text(
    json.dumps(resultados, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

# %% [markdown]
# ## Figura 1: antes y después, hueco por hueco

# %%
fig, axes = plt.subplots(1, 2, figsize=(12, 5.6))
for ax, r in zip(axes, REGIONES):
    t = tablas[r]
    lim = t["pers"].max() * 1.06
    ax.plot([0, lim], [0, lim], color=ve.GRIS, lw=1, ls="--")
    for est, col in COLOR_ESTADO.items():
        s = t[t["estado"] == est]
        ax.scatter(s["pers"], s["pers_despues"], s=46, color=col, edgecolor=ve.FONDO, lw=1,
                   label=f"{est.capitalize()} ({len(s)})", zorder=3 if est != "intacto" else 2)
    ax.set_xlim(150, lim)
    ax.set_ylim(-30, lim)
    ax.set_xlabel("Persistencia antes (m)")
    ax.set_ylabel("Persistencia después (m)")
    ax.set_title(f"{r}: {resultados[r]['K']} clínicas, {len(t)} huecos prioritarios")
    ax.legend(loc="upper left")
ve.titulo(fig, "La mayoría de los huecos prioritarios no cambia",
          "Medido al recalcular la persistencia con las clínicas propuestas. "
          "Sobre la diagonal, el hueco sigue igual; en cero, se cerró.")
fig.tight_layout(rect=(0, 0, 1, 0.91))
ve.guardar(fig, config.FIGURAS_DIR / "cierre_real_antes_despues.png")

# %% [markdown]
# ## Figura 2: MCLP frente a las dos líneas base

# %%
fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
for ax, r in zip(axes, REGIONES):
    ax.hist(azar[r], bins=18, color=ve.GRIS, edgecolor=ve.FONDO, lw=1)
    m = resultados[r]["mclp"]["prio_reduccion_pct"]
    t = resultados[r]["topologica"]["prio_reduccion_pct"]
    g = resultados[r]["mclp"]["regla_reduccion_pct"]
    ymax = ax.get_ylim()[1]
    marcas = sorted([(m, ve.AZUL, "MCLP"), (t, ve.AQUA, "Topológica"), (g, ve.NARANJA, "Regla del reporte")])
    for i, (val, col, txt) in enumerate(marcas):
        ax.axvline(val, color=col, lw=2.2)
        ax.text(val, ymax * (1.01 + 0.09 * (i % 2)), f"{txt}: {val:.1f}%", color=ve.TEXTO_2,
                ha="center", va="bottom", fontsize=9.5)
    ax.set_xlabel("Reducción de la persistencia total en huecos prioritarios (%)")
    ax.set_ylabel("Sorteos al azar")
    ax.set_title(r, pad=44)
    ax.grid(axis="x", visible=False)
ve.titulo(fig, "En persistencia, el MCLP no supera al azar",
          f"En gris, {N_AZAR} selecciones al azar con el mismo número de clínicas.")
fig.tight_layout(rect=(0, 0, 1, 0.9))
ve.guardar(fig, config.FIGURAS_DIR / "cierre_real_lineas_base.png")

# %% [markdown]
# ## Figura 3: lo que el MCLP sí optimiza

# %%
fig, axes = plt.subplots(1, 2, figsize=(12, 4.2))
for ax, r in zip(axes, REGIONES):
    v = np.array(azar[r + "_psin"]) / 1000
    ax.hist(v, bins=18, color=ve.GRIS, edgecolor=ve.FONDO, lw=1)
    m = resultados[r]["mclp"]["personas"]["psin_cubiertos"] / 1000
    t = resultados[r]["topologica"]["personas"]["psin_cubiertos"] / 1000
    ymax = ax.get_ylim()[1]
    for val, col, txt in sorted([(m, ve.AZUL, "MCLP"), (t, ve.AQUA, "Topológica")]):
        ax.axvline(val, color=col, lw=2.2)
        ax.text(val, ymax * 1.01, f"{txt}: {val:.1f} mil", color=ve.TEXTO_2, ha="center", va="bottom", fontsize=9.5)
    ax.set_xlabel("Personas sin seguro a menos de 833 m (miles)")
    ax.set_ylabel("Sorteos al azar")
    ax.set_title(r, pad=24)
    ax.grid(axis="x", visible=False)
ve.titulo(fig, "Comparación en personas alcanzadas",
          "Mismas clínicas y mismos sorteos que la figura anterior.")
fig.tight_layout(rect=(0, 0, 1, 0.89))
ve.guardar(fig, config.FIGURAS_DIR / "cierre_real_personas.png")
