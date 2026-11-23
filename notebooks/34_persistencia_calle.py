# %% [markdown]
# # 34 — Persistencia del acceso por calle (F4 sobre la red de F6, versión principal)
#
# Mismo procedimiento que el notebook 31, con las piezas comunes en `lib/f4.py`:
#
# - **Filtración:** subniveles de `acceso_rel_calle` en la rejilla de 100 m, 8 vecinos.
# - **Isla:** b < 0.5 y persistencia ≥ 0.25.
# - **Extensión:** la cuenca de la isla, {f < d} conexa al mínimo (incluye las subcuencas que
#   se fundieron en ella). Para totales cada celda va a la cuenca más profunda que la contiene.
# - **Estabilidad:** 100 réplicas sorteando la capacidad de cada unidad en su rango de
#   `per_ocu`. Una isla aparece en una réplica si su cuenca se empareja (uno a uno) con una
#   de la réplica con Jaccard ≥ 0.5; es estable si aparece en ≥ 80% de las réplicas.
#   Como referencia se guarda el criterio anterior (alguna isla a ≤ 500 m).
# - **Tipos:** finita / aislada / resto de región, igual que en F4.
#
# **Comparación con la línea recta:** emparejamiento de cuencas estables contra estables
# (Jaccard), en ambos sentidos, más el Jaccard de los dos mapas de umbral {f < 0.5} como
# referencia descriptiva. La prueba contra un modelo nulo queda para otro notebook.

# %%
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

from lib import acceso, config, f4, red_peatonal as rp, topo_rejilla as tr, viz_eval as ve
from lib.f4 import UMBRAL_B, UMBRAL_P, TOPE, N_REP, ESTABLE, J_MIN

ve.aplicar()
INT = config.INTERMEDIOS_DIR
SALIDA = config.OUTPUTS_DIR / "auditoria"
FIG = config.FIGURAS_DIR
LIM = 30 * 4500 / 60  # 2,250 m de calle, como en el notebook 33

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
# Distancias guardadas en float32: tolerancia relativa, porque con CLUES hay celdas con f de
# cientos (unidades rurales con poca demanda alrededor) donde el error absoluto crece.
assert np.allclose(A / (o["cap"].sum() / PSIN.sum()), F, rtol=1e-4, atol=1e-4)

rej = tr.Rejilla(c["x"], c["y"], acceso.PASO)
pares, etiqueta, CUEN = rej.h0(F, cuencas=True, umbral_b=UMBRAL_B, umbral_p=UMBRAL_P, tope=TOPE)
isl = tr.islas(pares, UMBRAL_B, UMBRAL_P).reset_index(drop=True)
cuen_isl = f4.lista_cuencas(isl, CUEN)
print(f"componentes: {len(pares)}, islas: {len(isl)} (esenciales: {np.isinf(isl['d']).sum()})")

# %% [markdown]
# ## Réplicas de capacidad

# %%
est_df, n_islas_rep = f4.estabilidad(rej, XY, isl, cuen_isl, f4.replicas_capacidad(I, J, W, PSIN, o))
isl = isl.join(est_df)
isl["estable"] = isl["frecuencia"] >= ESTABLE

# %% [markdown]
# ## Extensión, tipo y zonas de umbral

# %%
RAS, fr, cr, act = rej.ras, rej.fr, rej.cr, rej.activa
alta = c["alta_marg"].to_numpy(bool)
bajo = F < UMBRAL_B
mask = np.zeros(RAS.shape, bool)
mask[RAS >= 0] = bajo[RAS[RAS >= 0]]
umb, n_umb = ndimage.label(mask, structure=np.ones((3, 3)))
zona = np.zeros(N, int)
zona[act] = umb[fr[act], cr[act]]

reg_pob, _ = ndimage.label(RAS >= 0, structure=np.ones((3, 3)))
reg_celda = np.zeros(N, int)
reg_celda[act] = reg_pob[fr[act], cr[act]]
isl["reg"] = reg_celda[isl["celda"]]
n_isl_reg = isl.groupby("reg").size()
isl["tipo"] = np.where(np.isfinite(isl["d"]), "finita",
                       np.where(isl["reg"].map(n_isl_reg) > 1, "resto de región", "aislada"))
isl["region"] = c["region"].to_numpy()[isl["celda"]]
isl["CVEGEO"] = c["CVEGEO"].to_numpy()[isl["celda"]]
isl["zona_umbral"] = zona[isl["celda"]]
isl["x"], isl["y"] = XY[isl["celda"]].T
isl = isl.merge(acceso.marginacion_conapo()[["CVEGEO", "NOM_MUN"]], on="CVEGEO", how="left")

# Totales con las cuencas de las islas estables (sin "resto"): cada celda cuenta una vez.
sel = (isl["estable"] & (isl["tipo"] != "resto de región")).to_numpy()
est = isl[sel].reset_index(drop=True)
cuen_est = [cuen_isl[k] for k in np.flatnonzero(sel)]
ext, ASIG = f4.extension(cuen_est, PSIN, bajo, alta, N)
est = est.join(ext)
print(isl.groupby(["tipo", "estable"]).size())
resto = isl[isl["tipo"] == "resto de región"]
por_zona = est.groupby("zona_umbral").size()
zonas_multi = por_zona[por_zona >= 2]
psin_zona = pd.Series(np.bincount(zona[zona > 0], PSIN[zona > 0]), dtype=float)

# %% [markdown]
# ## Comparación con la línea recta (cuencas estables contra estables)

# %%
F0 = c["acceso_rel"].to_numpy()
isl0 = pd.read_parquet(INT / "islas_acceso.parquet")
est0 = isl0[isl0["estable"] & (isl0["tipo"] != "resto de región")].reset_index(drop=True)
_, _, CUEN0 = rej.h0(F0, cuencas=True, umbral_b=UMBRAL_B, umbral_p=UMBRAL_P, tope=TOPE)
cuen_est0 = f4.lista_cuencas(est0, CUEN0)
Jm, fil, col, resumen = tr.jaccard_emparejado(cuen_est0, cuen_est, N, umbral=J_MIN)
par0, par1 = np.zeros(len(est0)), np.zeros(len(est))
par0[fil], par1[col] = Jm[fil, col], Jm[fil, col]
# Gente con acceso bajo en el territorio propio de cada isla en recta (sin doble conteo de anidadas).
ASIG0 = tr.particion(cuen_est0, N)
u0, u1 = ASIG0 >= 0, ASIG >= 0
pb0 = np.bincount(ASIG0[u0], (PSIN * (F0 < UMBRAL_B))[u0], len(est0))


def jac(a, b):
    return float((a & b).sum() / max((a | b).sum(), 1))


comp = {
    "estables_recta": len(est0), "estables_calle": len(est),
    "jaccard_emparejado_resumen": float(resumen),
    "recta_con_pareja_j05_pct": float((par0 >= J_MIN).mean() * 100),
    "calle_con_pareja_j05_pct": float((par1 >= J_MIN).mean() * 100),
    "psin_bajo_recta_en_islas_con_pareja_pct": float(pb0[par0 >= J_MIN].sum() / pb0.sum() * 100),
    "jaccard_union_cuencas": jac(u0, u1),
    "referencia_jaccard_umbral_f05": jac(F0 < UMBRAL_B, bajo),
}
est["j_pareja_recta"] = par1
print(comp)

res = {
    "definiciones": {"extension": "cuenca {f < d} conexa al mínimo; partición por la cuenca más profunda",
                     "estable": f"pareja con Jaccard >= {J_MIN} en >= {ESTABLE:.0%} de {N_REP} réplicas de capacidad"},
    "componentes_h0": len(pares),
    "islas": {"total": len(isl), "por_tipo": isl.groupby("tipo").size().to_dict(),
              "estables_por_tipo": isl[isl["estable"]].groupby("tipo").size().to_dict(),
              "estables_sin_resto": len(est),
              "estables_b0": int((est["b"] == 0).sum()),
              "estables_criterio_distancia_500m": int(((isl["frecuencia_dist"] >= ESTABLE)
                                                       & (isl["tipo"] != "resto de región")).sum())},
    "islas_por_replica": {"media": float(np.mean(n_islas_rep)), "min": int(min(n_islas_rep)), "max": int(max(n_islas_rep))},
    "psin_bajo": {"total": float(PSIN[bajo].sum()), "en_islas_estables": float(est["psin_bajo"].sum()),
                  "en_islas_estables_b0": float(est.loc[est["b"] == 0, "psin_bajo"].sum())},
    "resto_de_region": resto[["NOM_MUN", "b", "frecuencia"]].round(3).to_dict(orient="records"),
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
cols = ["NOM_MUN", "region", "tipo", "b", "d", "pers", "frecuencia", "j_medio", "psin", "psin_bajo",
        "psin_bajo_cuenca", "psin_marg_alta", "j_pareja_recta"]
res["islas_estables"] = est.sort_values("psin_bajo", ascending=False)[cols].round(3).to_dict(orient="records")
print({k: v for k, v in res.items() if k not in ("islas_estables", "resto_de_region")})
print(est.sort_values("psin_bajo", ascending=False)[cols].head(20).to_string())
isl[["celda", "x", "y", "b", "d", "pers", "frecuencia", "frecuencia_dist", "j_medio", "estable", "tipo",
     "NOM_MUN", "region"]].to_parquet(INT / "islas_acceso_calle.parquet")
np.save(INT / "asig_cuencas_calle.npy", ASIG)
# Huella que liga ASIG con su acceso y sus islas, en orden; 32 y 35 la comprueban.
(INT / "asig_cuencas_calle.huella").write_text(rp.huella(F, est["celda"].to_numpy()))
f4.guardar_json(res, SALIDA / "persistencia_calle.json")

# %% [markdown]
# ## Figura: islas estables por calle y su correspondencia con la línea recta

# %%
fig, (ax, axd) = plt.subplots(1, 2, figsize=(15, 8), gridspec_kw={"width_ratios": [1.5, 1]})
base = np.full(RAS.shape, np.nan)
base[RAS >= 0] = np.where(bajo[RAS[RAS >= 0]], 1.0, 0.0)
ax.imshow(base, origin="lower", cmap=plt.matplotlib.colors.ListedColormap(["#e6e5e0", "#c9c7bf"]), interpolation="nearest")
cub = np.full(RAS.shape, np.nan)
cub[RAS >= 0] = np.where(ASIG[RAS[RAS >= 0]] >= 0, 1.0, np.nan)
ax.imshow(cub, origin="lower", cmap=plt.matplotlib.colors.ListedColormap([ve.NARANJA]), interpolation="nearest")
col, fil = rej.col, rej.fil
for t, color, mk, nom in [(est[est["j_pareja_recta"] >= J_MIN], ve.TEXTO, "o", "Estable por calle, con pareja en recta (J ≥ 0.5)"),
                          (est[est["j_pareja_recta"] < J_MIN], ve.AZUL, "o", "Estable por calle, sin pareja")]:
    ax.scatter(col[t["celda"]] + 1, fil[t["celda"]] + 1, s=6, c=color, marker=mk, lw=0, label=nom)
perd = est0[par0 < J_MIN]
cel0 = cKDTree(XY).query(perd[["x", "y"]].to_numpy())[1]
ax.scatter(col[cel0] + 1, fil[cel0] + 1, s=10, c=ve.AQUA, marker="x", lw=0.8, label="Estable en recta que se pierde")
ax.set_axis_off()
ax.set_aspect("equal")
ax.set_xlim(col.min() - 5, col.max() + 7)
ax.set_ylim(fil.min() - 5, fil.max() + 7)
h, l = ax.get_legend_handles_labels()
ax.legend(h + [Patch(color=ve.NARANJA), Patch(color="#c9c7bf")],
          l + ["Cuenca de isla estable", "Acceso bajo por calle (f < 0.5)"], loc="lower left",
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
          f"{len(est)} islas estables por calle; {comp['recta_con_pareja_j05_pct']:.0f}% de las {len(est0)} estables "
          f"en línea recta tienen pareja por calle con Jaccard ≥ 0.5.")
fig.subplots_adjust(top=0.84)
ve.guardar(fig, FIG / "persistencia_calle.png")
