# %% [markdown]
# # 34 — Persistencia del acceso por calle (F4 repetida sobre la red de F6)
#
# En el notebook 33 solo 78% de las islas estables en línea recta reaparecieron por calle
# (criterio: 80%), así que la versión por calle pasa a ser la principal. Aquí se le aplica
# a esa versión el mismo procedimiento completo de F4 (notebook 31):
#
# - **Filtración:** subniveles de `acceso_rel_calle` en la rejilla de 100 m, 8 vecinos.
# - **Isla:** b < 0.5 y persistencia ≥ 0.25.
# - **Estabilidad:** 100 réplicas sorteando la capacidad de cada unidad en su rango de
#   `per_ocu` de DENUE; estable si en ≥ 80% de las réplicas hay una isla a ≤ 500 m.
# - **Tipos:** finita / aislada / resto de región, igual que en F4.
#
# **Comparación justa con la línea recta (fijada antes de correr):** ahora se comparan
# estables con estables, en ambos sentidos: qué parte de las estables en recta tiene una
# estable por calle a ≤ 500 m, y al revés.

# %%
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch
from scipy import ndimage
from scipy.spatial import cKDTree

from lib import acceso, config, topo_rejilla as tr, viz_eval as ve

ve.aplicar()
INT = config.INTERMEDIOS_DIR
SALIDA = config.OUTPUTS_DIR / "auditoria"
FIG = config.FIGURAS_DIR
UMBRAL_B, UMBRAL_P, TOPE = 0.5, 0.25, 1.0
N_REP, ESTABLE, RADIO_MATCH = 100, 0.8, 500.0
LIM = 30 * 4500 / 60  # 2,250 m de calle, como en el notebook 33
RANGOS = {"0 a 5 personas": (1, 5), "6 a 10 personas": (6, 10), "11 a 30 personas": (11, 30),
          "31 a 50 personas": (31, 50), "51 a 100 personas": (51, 100), "101 a 250 personas": (101, 250),
          "251 y más personas": (251, 350)}

c = pd.read_parquet(INT / "acceso_e2sfca_celdas.parquet")
calle = pd.read_parquet(INT / "acceso_calle.parquet")
assert np.allclose(calle[["x", "y"]].to_numpy(), c[["x", "y"]].to_numpy())
o = acceso.oferta()
XY, PSIN = c[["x", "y"]].to_numpy(), c["psin"].to_numpy()
N = len(c)
F = calle["acceso_rel_calle"].to_numpy()

p = pd.read_parquet(INT / "pares_red_unidades.parquet")
I, J = p["i"].to_numpy(), p["j"].to_numpy()
W = acceso.peso(p["d"].to_numpy(float), LIM)
A, _ = acceso.e2sfca_pares(I, J, W, PSIN, o["cap"].to_numpy(float), N)
assert np.abs(A / (o["cap"].sum() / PSIN.sum()) - F).max() < 1e-4  # distancias guardadas en float32

rej = tr.Rejilla(c["x"], c["y"], acceso.PASO)
pares, etiqueta = rej.h0(F)
isl = tr.islas(pares, UMBRAL_B, UMBRAL_P).copy()
print(f"componentes: {len(pares)}, islas: {len(isl)} (esenciales: {np.isinf(isl['d']).sum()})")

# %% [markdown]
# ## Réplicas de capacidad

# %%
rng = np.random.default_rng(31)
lo = o["per_ocu"].map(lambda s: RANGOS[s][0]).to_numpy()
hi = o["per_ocu"].map(lambda s: RANGOS[s][1]).to_numpy()
apariciones = np.zeros(len(isl))
n_islas_rep = []
for rep in range(N_REP):
    cap = rng.integers(lo, hi + 1).astype(float)
    A, _ = acceso.e2sfca_pares(I, J, W, PSIN, cap, N)
    ir = tr.islas(rej.h0(A / (cap.sum() / PSIN.sum()))[0], UMBRAL_B, UMBRAL_P)
    n_islas_rep.append(len(ir))
    cerca = cKDTree(XY[ir["celda"]]).query(XY[isl["celda"]], distance_upper_bound=RADIO_MATCH)[0]
    apariciones += np.isfinite(cerca)
    if rep % 20 == 0:
        print(rep, len(ir), flush=True)
isl["frecuencia"] = apariciones / N_REP
isl["estable"] = isl["frecuencia"] >= ESTABLE

# %% [markdown]
# ## Extensión, tipo y zonas de umbral (igual que F4)

# %%
RAS, fr, cr, act = rej.ras, rej.fr, rej.cr, rej.activa
alta = c["alta_marg"].to_numpy(bool)
c["isla"] = np.where(F <= TOPE, etiqueta, -1)
bajo = F < UMBRAL_B
mask = np.zeros(RAS.shape, bool)
mask[RAS >= 0] = bajo[RAS[RAS >= 0]]
umb, n_umb = ndimage.label(mask, structure=np.ones((3, 3)))
zona = np.zeros(N, int)
zona[act] = umb[fr[act], cr[act]]

m = c["isla"].to_numpy() >= 0
lab = c["isla"].to_numpy()[m]
ext = pd.DataFrame({"psin": np.bincount(lab, PSIN[m], N), "psin_bajo": np.bincount(lab, (PSIN * bajo)[m], N),
                    "psin_marg_alta": np.bincount(lab, (PSIN * alta)[m], N), "celdas": np.bincount(lab, minlength=N)})
isl = isl.join(ext, on="celda")
isl["region"] = c["region"].to_numpy()[isl["celda"]]
isl["CVEGEO"] = c["CVEGEO"].to_numpy()[isl["celda"]]
isl["zona_umbral"] = zona[isl["celda"]]
isl["x"], isl["y"] = XY[isl["celda"]].T
isl = isl.merge(acceso.marginacion_conapo()[["CVEGEO", "NOM_MUN"]], on="CVEGEO", how="left")

reg_pob, _ = ndimage.label(RAS >= 0, structure=np.ones((3, 3)))
reg_celda = np.zeros(N, int)
reg_celda[act] = reg_pob[fr[act], cr[act]]
isl["reg"] = reg_celda[isl["celda"]]
n_isl_reg = isl.groupby("reg").size()
isl["tipo"] = np.where(np.isfinite(isl["d"]), "finita",
                       np.where(isl["reg"].map(n_isl_reg) > 1, "resto de región", "aislada"))
print(isl.groupby(["tipo", "estable"]).agg(n=("celda", "size"), psin_bajo=("psin_bajo", "sum")))

est = isl[isl["estable"] & (isl["tipo"] != "resto de región")].reset_index(drop=True)
resto = isl[isl["tipo"] == "resto de región"]
por_zona = est.groupby("zona_umbral").size()
zonas_multi = por_zona[por_zona >= 2]
psin_zona = pd.Series(np.bincount(zona[zona > 0], PSIN[zona > 0]), dtype=float)

# %% [markdown]
# ## Comparación estable contra estable con la línea recta

# %%
isl0 = pd.read_parquet(INT / "islas_acceso.parquet")
est0 = isl0[isl0["estable"] & (isl0["tipo"] != "resto de región")].reset_index(drop=True)
d01 = cKDTree(est[["x", "y"]].to_numpy()).query(est0[["x", "y"]].to_numpy())[0]
d10 = cKDTree(est0[["x", "y"]].to_numpy()).query(est[["x", "y"]].to_numpy())[0]
comp = {
    "estables_recta": len(est0), "estables_calle": len(est),
    "recta_con_estable_calle_pct": float((d01 <= RADIO_MATCH).mean() * 100),
    "psin_bajo_recta_en_esas_pct": float(est0.loc[d01 <= RADIO_MATCH, "psin_bajo"].sum() / est0["psin_bajo"].sum() * 100),
    "calle_con_estable_recta_pct": float((d10 <= RADIO_MATCH).mean() * 100),
    "psin_bajo_calle_en_esas_pct": float(est.loc[d10 <= RADIO_MATCH, "psin_bajo"].sum() / est["psin_bajo"].sum() * 100),
}
est["en_recta"] = d10 <= RADIO_MATCH
print(json.dumps(comp, indent=1))

res = {
    "componentes_h0": len(pares),
    "islas": {"total": len(isl), "por_tipo": isl.groupby("tipo").size().to_dict(),
              "estables_por_tipo": isl[isl["estable"]].groupby("tipo").size().to_dict(),
              "estables_sin_resto": len(est)},
    "islas_por_replica": {"media": float(np.mean(n_islas_rep)), "min": int(min(n_islas_rep)), "max": int(max(n_islas_rep))},
    "psin_bajo": {"total": float(PSIN[bajo].sum()), "en_islas_estables": float(est["psin_bajo"].sum()),
                  "en_resto": float(resto["psin_bajo"].sum())},
    "resto_de_region": resto[["NOM_MUN", "b", "frecuencia", "psin", "psin_bajo"]].round(3).to_dict(orient="records"),
    "umbral": {"zonas": int(n_umb), "zonas_con_isla_estable": int(len(por_zona)),
               "zonas_con_2_o_mas": int(len(zonas_multi)),
               "psin_en_zonas_con_2_o_mas": float(psin_zona.reindex(zonas_multi.index).sum()),
               "psin_en_zonas_bajo_total": float(psin_zona.sum()),
               "islas_en_zonas_con_2_o_mas": int(zonas_multi.sum())},
    "por_region": {r: {"estables": int((est["region"] == r).sum()),
                       "psin_bajo_en_estables": float(est.loc[est["region"] == r, "psin_bajo"].sum())}
                   for r in ["CDMX", "EDOMEX"]},
    "comparacion_recta": comp,
}
cols = ["NOM_MUN", "region", "tipo", "b", "d", "pers", "frecuencia", "psin", "psin_bajo", "psin_marg_alta", "en_recta"]
res["islas_estables"] = est.sort_values("psin_bajo", ascending=False)[cols].replace({np.inf: None}).round(3).to_dict(orient="records")
print(json.dumps({k: v for k, v in res.items() if k not in ("islas_estables", "resto_de_region")}, indent=1, ensure_ascii=False))
print(est.sort_values("psin_bajo", ascending=False)[cols].head(20).to_string())
isl[["celda", "x", "y", "b", "d", "pers", "frecuencia", "estable", "tipo", "NOM_MUN", "region", "psin_bajo"]].to_parquet(
    INT / "islas_acceso_calle.parquet")
(SALIDA / "persistencia_calle.json").write_text(json.dumps(res, indent=2, ensure_ascii=False, default=float), encoding="utf-8")

# %% [markdown]
# ## Figura: islas estables por calle y su correspondencia con la línea recta

# %%
fig, (ax, axd) = plt.subplots(1, 2, figsize=(15, 8), gridspec_kw={"width_ratios": [1.5, 1]})
base = np.full(RAS.shape, np.nan)
base[RAS >= 0] = np.where(bajo[RAS[RAS >= 0]], 1.0, 0.0)
ax.imshow(base, origin="lower", cmap=plt.matplotlib.colors.ListedColormap(["#e6e5e0", "#c9c7bf"]), interpolation="nearest")
labr = np.full(RAS.shape, -1)
labr[RAS >= 0] = c["isla"].to_numpy()[RAS[RAS >= 0]]
sel = np.where(np.isin(labr, est["celda"].to_numpy()), 1.0, np.nan)
ax.imshow(sel, origin="lower", cmap=plt.matplotlib.colors.ListedColormap([ve.NARANJA]), interpolation="nearest")
col, fil = rej.col, rej.fil
for t, color, mk, nom in [(est[est["en_recta"]], ve.TEXTO, "o", "Estable por calle, también en recta"),
                          (est[~est["en_recta"]], ve.AZUL, "o", "Estable por calle, nueva")]:
    ax.scatter(col[t["celda"]] + 1, fil[t["celda"]] + 1, s=6, c=color, marker=mk, lw=0, label=nom)
perd = est0[d01 > RADIO_MATCH]
cel0 = cKDTree(XY).query(perd[["x", "y"]].to_numpy())[1]
ax.scatter(col[cel0] + 1, fil[cel0] + 1, s=10, c=ve.AQUA, marker="x", lw=0.8, label="Estable en recta que se pierde")
ax.set_axis_off()
ax.set_aspect("equal")
ax.set_xlim(col.min() - 5, col.max() + 7)
ax.set_ylim(fil.min() - 5, fil.max() + 7)
h, l = ax.get_legend_handles_labels()
ax.legend(h + [Patch(color=ve.NARANJA), Patch(color="#c9c7bf")],
          l + ["Extensión de isla estable (f ≤ 1)", "Acceso bajo por calle (f < 0.5)"], loc="lower left",
          fontsize=8.5, frameon=False, scatterpoints=1, markerscale=2)

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
axd.set_title(f"Diagrama de H0 por calle ({int(np.isinf(est['d']).sum())} islas aisladas estables no se dibujan)", fontsize=9.5)
axd.legend(fontsize=8.5, frameon=False, loc="lower right")
ve.titulo(fig, "Persistencia de las zonas de acceso bajo, distancias por calle",
          f"{len(est)} islas estables por calle; {comp['recta_con_estable_calle_pct']:.0f}% de las {len(est0)} estables "
          f"en línea recta tienen una estable por calle a ≤ 500 m.")
fig.subplots_adjust(top=0.84)
ve.guardar(fig, FIG / "persistencia_calle.png")
