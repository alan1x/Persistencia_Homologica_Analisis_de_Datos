# %% [markdown]
# # 31 — Persistencia de las zonas de acceso bajo (fase F4 de `PLAN_ACCESO.md`)
#
# **Entrada:** f(celda) = acceso relativo (E2SFCA ÷ promedio metropolitano, notebook 30) en
# la rejilla de 100 m. Las posiciones sin población no forman parte del complejo.
#
# **Complejo y filtración:** complejo cúbico con una celda por píxel; filtración por
# subniveles X_t = {f ≤ t}. Dos píxeles que comparten lado o esquina quedan conectados
# (8 vecinos), igual que en `gudhi.CubicalComplex` con celdas de dimensión máxima.
#
# **H0:** cada componente nace en un mínimo local (b = f del mínimo) y muere cuando se une
# con una componente más vieja (regla del más viejo), en d = f de la celda que las une.
# La persistencia es d − b. La componente más vieja de cada región conexa nunca muere.
#
# **Extensión de una componente:** la celda que entra se asigna a la componente que toca
# (si toca varias, a la más vieja). Así las celdas quedan repartidas sin repetirse. Solo se
# cuentan las celdas con f ≤ 1, es decir, por debajo del promedio.
#
# ## Criterios fijados antes de correr
#
# - **Isla:** componente de H0 con nacimiento b < 0.5 y persistencia ≥ 0.25.
# - **Estabilidad:** 100 réplicas del acceso sorteando la capacidad de cada unidad (entero
#   uniforme dentro de su rango de personal de DENUE; "0 a 5" → 1–5 y "251 y más" →
#   251–350, centrado en el valor 300 que se usa). En cada réplica, f se divide entre el
#   promedio de esa réplica. Una isla es estable si en ≥ 80% de las réplicas hay una isla
#   con su mínimo a ≤ 500 m del suyo.
# - **¿Aporta frente al umbral?** Se cuentan las zonas conexas de {f < 0.5} (8 vecinos) que
#   contienen dos o más islas estables. Si casi ninguna, la persistencia no agrega nada al
#   corte simple y así se reporta.
# - **Comprobación:** los pares (b, d) propios deben coincidir con los de
#   `gudhi.CubicalComplex`.

# %%
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import gudhi
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import ndimage
from scipy.spatial import cKDTree

from lib import acceso, config, viz_eval as ve

ve.aplicar()
SALIDA = config.OUTPUTS_DIR / "auditoria"
FIG = config.FIGURAS_DIR
UMBRAL_B, UMBRAL_P, TOPE = 0.5, 0.25, 1.0
N_REP, ESTABLE, RADIO_MATCH = 100, 0.8, 500.0
RANGOS = {"0 a 5 personas": (1, 5), "6 a 10 personas": (6, 10), "11 a 30 personas": (11, 30),
          "31 a 50 personas": (31, 50), "51 a 100 personas": (51, 100), "101 a 250 personas": (101, 250),
          "251 y más personas": (251, 350)}

c = pd.read_parquet(config.INTERMEDIOS_DIR / "acceso_e2sfca_celdas.parquet")
o = acceso.oferta()
XY, PSIN = c[["x", "y"]].to_numpy(), c["psin"].to_numpy()
N = len(c)

# Pares celda-unidad; se reproduce el acceso del notebook 30.
I, J, W = acceso.pares_e2sfca(XY, o[["x", "y"]].to_numpy(), 2 * acceso.RADIO_15)
A0, _ = acceso.e2sfca_pares(I, J, W, PSIN, o["cap"].to_numpy(float), N)
assert np.allclose(A0 * 1000, c["acceso"].to_numpy())
F0 = c["acceso_rel"].to_numpy()

# %% [markdown]
# ## Rejilla y vecinos

# %%
col = np.rint((c["x"].to_numpy() - c["x"].min()) / acceso.PASO).astype(int)
fil = np.rint((c["y"].to_numpy() - c["y"].min()) / acceso.PASO).astype(int)
en_rejilla = np.isclose(c["x"] % acceso.PASO, 0) & np.isclose(c["y"] % acceso.PASO, 0)
RAS = np.full((fil.max() + 3, col.max() + 3), -1)  # borde de 1 píxel vacío
RAS[fil[en_rejilla] + 1, col[en_rejilla] + 1] = np.flatnonzero(en_rejilla)
# Las AGEB sin nodo de rejilla se representaron con un punto interior: se quedan fuera.
print("celdas fuera de la rejilla:", (~en_rejilla).sum(), "personas:", round(PSIN[~en_rejilla].sum()))

VEC = np.full((N, 8), -1)
fr, cr = fil + 1, col + 1
k = 0
for df in (-1, 0, 1):
    for dc in (-1, 0, 1):
        if df == dc == 0:
            continue
        VEC[en_rejilla, k] = RAS[fr[en_rejilla] + df, cr[en_rejilla] + dc]
        k += 1
VEC_L = [v[v >= 0].tolist() for v in VEC]


def h0(f):
    """Persistencia H0 por subniveles con union-find.

    Devuelve (pares, etiqueta): pares = DataFrame con celda del mínimo, b y d (inf si no
    muere); etiqueta[i] = mínimo de la componente a la que se asignó la celda i.
    """
    orden = np.argsort(f, kind="stable")
    pos = np.empty(N, int)
    pos[orden] = np.arange(N)
    padre = np.full(N, -1)
    etiqueta = np.full(N, -1)
    muerte = {}

    def raiz(a):
        r = a
        while padre[r] != r:
            r = padre[r]
        while padre[a] != r:
            padre[a], a = r, padre[a]
        return r

    for i in orden[en_rejilla[orden]]:
        rs = {raiz(v) for v in VEC_L[i] if padre[v] >= 0}
        if not rs:
            padre[i] = etiqueta[i] = i
            continue
        viejo = min(rs, key=pos.__getitem__)
        padre[i] = etiqueta[i] = viejo
        for r in rs - {viejo}:
            padre[r] = viejo
            muerte[r] = f[i]
    minimos = np.flatnonzero((etiqueta == np.arange(N)))
    d = np.array([muerte.get(m, np.inf) for m in minimos])
    pares = pd.DataFrame({"celda": minimos, "b": f[minimos], "d": d})
    pares["pers"] = pares["d"] - pares["b"]
    return pares, etiqueta


def islas(pares):
    return pares[(pares["b"] < UMBRAL_B) & (pares["pers"] >= UMBRAL_P)]


pares, etiqueta = h0(F0)
isl = islas(pares).copy()
print(f"componentes: {len(pares)}, islas: {len(isl)} (esenciales: {np.isinf(isl['d']).sum()})")

# %% [markdown]
# ## Comprobación contra gudhi

# %%
GRANDE = 1e4
img = np.full(RAS.shape, GRANDE)
img[RAS >= 0] = F0[RAS[RAS >= 0]]
cc = gudhi.CubicalComplex(top_dimensional_cells=img)
dg = np.array([p for dim, p in cc.persistence(homology_coeff_field=2, min_persistence=-1) if dim == 0])
dg = dg[dg[:, 0] < GRANDE]
dg[dg[:, 1] >= GRANDE, 1] = np.inf
g_fin = dg[np.isfinite(dg[:, 1]) & (dg[:, 1] > dg[:, 0])]
g_fin = g_fin[np.lexsort((g_fin[:, 1], g_fin[:, 0]))]
p_fin = pares[np.isfinite(pares["d"]) & (pares["pers"] > 0)]
p_fin = p_fin[["b", "d"]].to_numpy()
p_fin = p_fin[np.lexsort((p_fin[:, 1], p_fin[:, 0]))]
comprob = {"pares_finitos_propio": len(p_fin), "pares_finitos_gudhi": len(g_fin),
           "esenciales_propio": int(np.isinf(pares["d"]).sum()), "esenciales_gudhi": int(np.isinf(dg[:, 1]).sum()),
           "coinciden": bool(len(p_fin) == len(g_fin) and np.allclose(p_fin, g_fin))}
print(comprob)
assert comprob["coinciden"] and comprob["esenciales_propio"] == comprob["esenciales_gudhi"]

# %% [markdown]
# ## Réplicas de capacidad

# %%
rng = np.random.default_rng(31)
lo = o["per_ocu"].map(lambda s: RANGOS[s][0]).to_numpy()
hi = o["per_ocu"].map(lambda s: RANGOS[s][1]).to_numpy()
arb_isl = cKDTree(XY[isl["celda"]])
apariciones = np.zeros(len(isl))
n_islas_rep = []
for rep in range(N_REP):
    cap = rng.integers(lo, hi + 1).astype(float)
    A, _ = acceso.e2sfca_pares(I, J, W, PSIN, cap, N)
    f = A / (cap.sum() / PSIN.sum())
    ir = islas(h0(f)[0])
    n_islas_rep.append(len(ir))
    cerca = cKDTree(XY[ir["celda"]]).query(XY[isl["celda"]], distance_upper_bound=RADIO_MATCH)[0]
    apariciones += np.isfinite(cerca)
    if rep % 20 == 0:
        print(rep, len(ir))
isl["frecuencia"] = apariciones / N_REP
isl["estable"] = isl["frecuencia"] >= ESTABLE

# %% [markdown]
# ## Extensión de cada isla y comparación con el umbral

# %%
c["isla"] = np.where(F0 <= TOPE, etiqueta, -1)
c["en_umbral"] = F0 < UMBRAL_B
mask = np.zeros(RAS.shape, bool)
mask[RAS >= 0] = F0[RAS[RAS >= 0]] < UMBRAL_B
umb, n_umb = ndimage.label(mask, structure=np.ones((3, 3)))
c["zona_umbral"] = 0
c.loc[en_rejilla, "zona_umbral"] = umb[fr[en_rejilla], cr[en_rejilla]]

g = c[c["isla"] >= 0].groupby("isla")
ext = pd.DataFrame({"psin": g["psin"].sum(), "psin_bajo": g.apply(lambda t: t.loc[t["en_umbral"], "psin"].sum()),
                    "psin_marg_alta": g.apply(lambda t: t.loc[t["alta_marg"], "psin"].sum()),
                    "celdas": g.size()})
isl = isl.join(ext, on="celda")
isl["region"] = c["region"].to_numpy()[isl["celda"]]
isl["CVEGEO"] = c["CVEGEO"].to_numpy()[isl["celda"]]
isl["zona_umbral"] = c["zona_umbral"].to_numpy()[isl["celda"]]
isl["x"], isl["y"] = XY[isl["celda"]].T

imu = acceso.marginacion_conapo()[["CVEGEO", "NOM_MUN"]]
isl = isl.merge(imu, on="CVEGEO", how="left")

# Tipo de isla. La componente que nunca muere recibe todas las celdas que entran después de
# cada unión. Si su región conexa de población tiene otras islas, su extensión es el resto
# de esa región y no una isla: se reporta aparte y no entra en el ranking ni en el mapa.
# Si es la única isla de su región (un poblado separado del resto), es una isla aislada.
reg_pob, _ = ndimage.label(RAS >= 0, structure=np.ones((3, 3)))
reg_celda = np.zeros(N, int)
reg_celda[en_rejilla] = reg_pob[fr[en_rejilla], cr[en_rejilla]]
isl["reg"] = reg_celda[isl["celda"]]
n_isl_reg = isl.groupby("reg").size()
isl["tipo"] = np.where(np.isfinite(isl["d"]), "finita",
                       np.where(isl["reg"].map(n_isl_reg) > 1, "resto de región", "aislada"))
print(isl.groupby(["tipo", "estable"]).agg(n=("celda", "size"), psin=("psin", "sum"), psin_bajo=("psin_bajo", "sum")))

est = isl[isl["estable"] & (isl["tipo"] != "resto de región")]
resto = isl[isl["tipo"] == "resto de región"]
por_zona = est.groupby("zona_umbral").size()
zonas_multi = por_zona[por_zona >= 2]
psin_zona = c[c["zona_umbral"] > 0].groupby("zona_umbral")["psin"].sum()
res = {
    "comprobacion_gudhi": comprob,
    "celdas_fuera_rejilla": int((~en_rejilla).sum()),
    "componentes_h0": len(pares),
    "islas": {"total": len(isl), "por_tipo": isl.groupby("tipo").size().to_dict(),
              "estables_por_tipo": isl[isl["estable"]].groupby("tipo").size().to_dict(),
              "estables_sin_resto": len(est)},
    "resto_de_region": resto[["NOM_MUN", "b", "frecuencia", "psin", "psin_bajo"]].round(3).to_dict(orient="records"),
    "psin_bajo": {"total": float(PSIN[F0 < UMBRAL_B].sum()), "en_islas_estables": float(est["psin_bajo"].sum()),
                  "en_resto": float(resto["psin_bajo"].sum())},
    "islas_por_replica": {"media": float(np.mean(n_islas_rep)), "min": int(min(n_islas_rep)), "max": int(max(n_islas_rep))},
    "sensibilidad_umbral_persistencia": {str(u): int(((pares["b"] < UMBRAL_B) & (pares["pers"] >= u)).sum())
                                         for u in [0.1, 0.25, 0.5, 1.0]},
    "umbral": {"zonas": int(n_umb),
               "zonas_con_isla_estable": int(len(por_zona)),
               "zonas_con_2_o_mas": int(len(zonas_multi)),
               "psin_en_zonas_con_2_o_mas": float(psin_zona.reindex(zonas_multi.index).sum()),
               "psin_en_zonas_bajo_total": float(psin_zona.sum()),
               "islas_en_zonas_con_2_o_mas": int(zonas_multi.sum())},
    "por_region": {r: {"estables": int((est["region"] == r).sum()),
                       "psin_bajo_en_estables": float(est.loc[est["region"] == r, "psin_bajo"].sum()),
                       "psin_bajo_total": float(PSIN[(F0 < UMBRAL_B) & (c["region"].to_numpy() == r)].sum())}
                   for r in ["CDMX", "EDOMEX"]},
}
cols = ["NOM_MUN", "region", "tipo", "b", "d", "pers", "frecuencia", "psin", "psin_bajo", "psin_marg_alta", "zona_umbral"]
res["islas_estables"] = est.sort_values("psin_bajo", ascending=False)[cols].replace({np.inf: None}).round(3).to_dict(orient="records")
print(json.dumps({k: v for k, v in res.items() if k != "islas_estables"}, indent=1, ensure_ascii=False))
print(est.sort_values("psin_bajo", ascending=False)[cols].head(25).to_string())
(SALIDA / "persistencia_acceso.json").write_text(json.dumps(res, indent=2, ensure_ascii=False, default=float), encoding="utf-8")

# %% [markdown]
# ## Figuras: mapa de islas y diagrama de persistencia

# %%
fig, (ax, axd) = plt.subplots(1, 2, figsize=(15, 8), gridspec_kw={"width_ratios": [1.5, 1]})
base = np.full(RAS.shape, np.nan)
base[RAS >= 0] = np.where(F0[RAS[RAS >= 0]] < UMBRAL_B, 1.0, 0.0)
ax.imshow(base, origin="lower", cmap=plt.matplotlib.colors.ListedColormap(["#e6e5e0", "#c9c7bf"]),
          interpolation="nearest")
lab = np.full(RAS.shape, -1)
lab[RAS >= 0] = c["isla"].to_numpy()[RAS[RAS >= 0]]
estab = set(est["celda"])
sel = np.isin(lab, list(estab))
cap_isla = np.where(sel, 1.0, np.nan)
ax.imshow(cap_isla, origin="lower", cmap=plt.matplotlib.colors.ListedColormap([ve.NARANJA]), interpolation="nearest")
inest = isl[~isl["estable"] & (isl["tipo"] != "resto de región")]
for t, color, mk, nom in [(est, ve.TEXTO, "o", "Mínimo de isla estable"), (inest, ve.AZUL, "x", "Mínimo de isla no estable")]:
    ax.scatter(col[t["celda"]] + 1, fil[t["celda"]] + 1, s=5, c=color, marker=mk, lw=0.6, label=nom)
ax.set_axis_off()
ax.set_aspect("equal")
ax.set_xlim(col.min() - 5, col.max() + 7)
ax.set_ylim(fil.min() - 5, fil.max() + 7)
from matplotlib.patches import Patch
h, l = ax.get_legend_handles_labels()
ax.legend(h + [Patch(color=ve.NARANJA), Patch(color="#c9c7bf")],
          l + ["Extensión de isla estable (f ≤ 1)", "Acceso bajo (f < 0.5)"], loc="lower left", fontsize=8.5, frameon=False, scatterpoints=1, markerscale=2)

fin = pares[np.isfinite(pares["d"]) & (pares["pers"] > 0)]
axd.scatter(fin["b"], fin["d"], s=4, c=ve.GRIS, lw=0, label="Pares de H0")
ef = est[np.isfinite(est["d"])]
axd.scatter(ef["b"], ef["d"], s=14, c=ve.NARANJA, lw=0, label="Islas estables")
lim = 3
axd.plot([0, lim], [0, lim], c=ve.TEXTO, lw=0.8)
axd.plot([0, lim - UMBRAL_P], [UMBRAL_P, lim], c=ve.TEXTO, lw=0.8, ls="--", label="Persistencia = 0.25")
axd.axvline(UMBRAL_B, c=ve.TEXTO, lw=0.8, ls=":", label="Nacimiento = 0.5")
axd.set_xlim(0, lim)
axd.set_ylim(0, lim)
axd.set_xlabel("Nacimiento b (acceso del mínimo)")
axd.set_ylabel("Muerte d (acceso al unirse)")
axd.set_title(f"Diagrama de H0 (pares finitos; {int(np.isinf(est['d']).sum())} islas aisladas estables no se dibujan)",
              fontsize=9.5)
axd.legend(fontsize=8.5, frameon=False, loc="lower right")
ve.titulo(fig, "Persistencia de las zonas de acceso bajo",
          f"Filtración por subniveles del acceso relativo E2SFCA. Isla: b < 0.5 y d − b ≥ 0.25; "
          f"estable si aparece en ≥ 80% de {N_REP} réplicas de capacidad.")
fig.subplots_adjust(top=0.84)
ve.guardar(fig, FIG / "persistencia_acceso.png")
