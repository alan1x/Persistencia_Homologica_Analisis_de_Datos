# %% [markdown]
# # 35 — ¿Las zonas sin acceso por calle son reales o huecos de OSM?
#
# En el notebook 34, 360 de las 736 islas estables por calle nacen en b = 0: celdas sin
# ninguna unidad a 2,250 m de calle. Ahí el acceso es 0 con cualquier capacidad, así que la
# estabilidad no prueba nada. Este notebook revisa si esos ceros son lejanía real o una red
# incompleta.
#
# **Criterio fijado antes de correr.** Cada celda poblada con acceso 0 por calle se clasifica
# por la distancia en recta a la unidad más cercana:
# - **lejos de verdad:** > 2,250 m (ninguna calle podría ser más corta que la recta);
# - **zona gris:** 1,667–2,250 m (basta un rodeo algo mayor que 1.35);
# - **sospechosa:** ≤ 1,667 m (en la versión en recta sí tenía acceso). Causa, en orden:
#   anclaje > 300 m (sin calle mapeada cerca), sin camino a ninguna unidad (red
#   desconectada), rodeo > 2 (barrera o calle faltante), rodeo moderado.
#
# **Sensibilidad:** acceso híbrido = por calle, salvo en las sospechosas, que toman el valor
# en recta. Se cuentan las islas estables por calle que siguen teniendo una isla a ≤ 500 m.
# Si sobrevive ≥ 80%, los ceros dudosos no cambian la geografía de F4.

# %%
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.collections import LineCollection
from scipy import ndimage, sparse
from scipy.sparse import csgraph
from scipy.spatial import cKDTree

from lib import acceso, config, red_peatonal as rp, topo_rejilla as tr, viz_eval as ve

ve.aplicar()
INT = config.INTERMEDIOS_DIR
SALIDA = config.OUTPUTS_DIR / "auditoria"
FIG = config.FIGURAS_DIR
LIM, RECTA = 30 * 4500 / 60, 2 * acceso.RADIO_15

c = pd.read_parquet(INT / "acceso_e2sfca_celdas.parquet")
calle = pd.read_parquet(INT / "acceso_calle.parquet")
o = acceso.oferta()
XY, PSIN = c[["x", "y"]].to_numpy(), c["psin"].to_numpy()
FXY = o[["x", "y"]].to_numpy()
N = len(c)
F0, F1 = c["acceso_rel"].to_numpy(), calle["acceso_rel_calle"].to_numpy()
ANC = calle["anclaje"].to_numpy()

# %% [markdown]
# ## Distancia por calle a la unidad más cercana, sin límite

# %%
z = np.load(INT / "red_peatonal.npz")
red = rp.Red(z["xy"], z["u"], z["v"], z["largo"])
n = red.G.shape[0]
fue_nodo, fue_anc = red.anclar(FXY)
cel_nodo, _ = red.anclar(XY)
# Nodo fuente extra (índice n) unido a cada unidad con peso = su anclaje.
e = sparse.csr_matrix((np.maximum(fue_anc, 1e-3), (fue_nodo, np.zeros(len(FXY), int))), shape=(n, 1))
G = sparse.bmat([[red.G, e], [e.T, None]], format="csr")
dist = csgraph.dijkstra(G, directed=False, indices=n)
D_CALLE = dist[cel_nodo] + ANC
D_RECTA = cKDTree(FXY).query(XY)[0]

cero = (F1 == 0) & (PSIN > 0)
print("celdas con acceso 0 por calle:", cero.sum(), "personas:", round(PSIN[cero].sum()),
      "| consistencia (d_calle > 2,250):", (D_CALLE[cero] > LIM - 1).mean())
rodeo = D_CALLE / np.maximum(D_RECTA, 1)
clase = np.full(N, "", object)
clase[cero & (D_RECTA > LIM)] = "lejos de verdad"
clase[cero & (D_RECTA > RECTA) & (D_RECTA <= LIM)] = "zona gris"
sos = cero & (D_RECTA <= RECTA)
clase[sos] = "rodeo moderado"
clase[sos & (rodeo > 2)] = "rodeo > 2"
clase[sos & ~np.isfinite(D_CALLE)] = "red desconectada"
clase[sos & (ANC > 300)] = "sin calle a 300 m"
c["clase"] = clase
ORDEN = ["lejos de verdad", "zona gris", "rodeo moderado", "rodeo > 2", "red desconectada", "sin calle a 300 m"]
tab = c[cero].groupby("clase").agg(celdas=("psin", "size"), psin=("psin", "sum"),
                                   psin_marg_alta=("alta_marg", lambda s: PSIN[s.index][s.to_numpy(bool)].sum()))
tab = tab.reindex(ORDEN).fillna(0)
tab["pct_psin"] = tab["psin"] / tab["psin"].sum() * 100
print(tab.round(1).to_string())

# %% [markdown]
# ## Peso de las sospechosas dentro de las islas estables b = 0

# %%
isl = pd.read_parquet(INT / "islas_acceso_calle.parquet")
est = isl[isl["estable"] & (isl["tipo"] != "resto de región")].reset_index(drop=True)
rej = tr.Rejilla(c["x"], c["y"], acceso.PASO)
_, etiqueta = rej.h0(F1)
lab = np.where(F1 <= 1.0, etiqueta, -1)
bajo1 = F1 < 0.5
sos_bajo = np.bincount(lab[lab >= 0], (PSIN * sos * bajo1)[lab >= 0], N)
tot_bajo = np.bincount(lab[lab >= 0], (PSIN * bajo1)[lab >= 0], N)
est["psin_bajo_sospechosa"] = sos_bajo[est["celda"]]
cer = est["b"] == 0
islas_cero = {
    "n": int(cer.sum()),
    "psin_bajo": float(est.loc[cer, "psin_bajo"].sum()),
    "psin_bajo_en_sospechosas": float(est.loc[cer, "psin_bajo_sospechosa"].sum()),
    "islas_con_mayoria_sospechosa": int((est.loc[cer, "psin_bajo_sospechosa"] > 0.5 * est.loc[cer, "psin_bajo"]).sum()),
}
print(islas_cero)

# %% [markdown]
# ## Sensibilidad: acceso híbrido

# %%
FH = np.where(sos, F0, F1)
ph, _ = rej.h0(FH)
ih = tr.islas(ph)
dh = cKDTree(XY[ih["celda"]]).query(est[["x", "y"]].to_numpy())[0]
# Prueba por distancia (la fijada) y prueba por cuenca, que no depende de dónde cae el mínimo
# dentro de una meseta de ceros (ver la nota de la sección siguiente).
est["sobrevive_hibrido"] = dh <= 500
est["sobrevive_cuenca"] = rej.en_cuencas(FH, ih)[est["celda"]]
sens = {
    "islas_hibrido": len(ih),
    "cuenca_estables_calle_que_sobreviven_pct": float(est["sobrevive_cuenca"].mean() * 100),
    "cuenca_psin_bajo_en_las_que_sobreviven_pct": float(est.loc[est["sobrevive_cuenca"], "psin_bajo"].sum()
                                                        / est["psin_bajo"].sum() * 100),
    "estables_calle_que_sobreviven_pct": float(est["sobrevive_hibrido"].mean() * 100),
    "psin_bajo_en_las_que_sobreviven_pct": float(est.loc[est["sobrevive_hibrido"], "psin_bajo"].sum()
                                                 / est["psin_bajo"].sum() * 100),
    "b0_que_sobreviven_pct": float(est.loc[cer, "sobrevive_hibrido"].mean() * 100),
    "b_pos_que_sobreviven_pct": float(est.loc[~cer, "sobrevive_hibrido"].mean() * 100),
    "psin_bajo_hibrido": float(PSIN[FH < 0.5].sum()),
}
sens["geografia_robusta"] = bool(sens["estables_calle_que_sobreviven_pct"] >= 80)
print(json.dumps(sens, indent=1))

# %% [markdown]
# ## Nota de método: mesetas de ceros y comparación por cuenca
#
# Si muchas celdas valen exactamente 0, todas empatan como mínimo y cuál queda como "mínimo
# de la isla" depende solo del orden de las celdas. Comparar islas por la distancia entre
# mínimos (≤ 500 m) falla ahí: la isla sigue existiendo, pero su mínimo puede moverse
# kilómetros. 194 de las 370 islas estables en recta y 360 de las 736 por calle nacen en 0.
#
# Prueba por cuenca: la isla A reaparece en B si su mínimo cae dentro de la cuenca de alguna
# isla estable de B (la componente de {f < d} que contiene su mínimo). Se repite con ella la
# comparación recta–calle de los notebooks 33 y 34.

# %%
isl0 = pd.read_parquet(INT / "islas_acceso.parquet")
est0 = isl0[isl0["estable"] & (isl0["tipo"] != "resto de región")].reset_index(drop=True)
cub1 = rej.en_cuencas(F1, est)
cub0 = rej.en_cuencas(F0, est0)
r_en_c, c_en_r = cub1[est0["celda"]], cub0[est["celda"]]
comp_cuenca = {
    "recta_en_cuenca_calle_pct": float(r_en_c.mean() * 100),
    "psin_bajo_recta_en_esas_pct": float(est0.loc[r_en_c, "psin_bajo"].sum() / est0["psin_bajo"].sum() * 100),
    "calle_en_cuenca_recta_pct": float(c_en_r.mean() * 100),
    "psin_bajo_calle_en_esas_pct": float(est.loc[c_en_r, "psin_bajo"].sum() / est["psin_bajo"].sum() * 100),
    "por_distancia_500m_nb34": {"recta_con_estable_calle_pct": 69.5, "calle_con_estable_recta_pct": 35.7},
}
print(json.dumps(comp_cuenca, indent=1))

# %% [markdown]
# ## Grupos sospechosos más grandes

# %%
RAS, fr, cr, act = rej.ras, rej.fr, rej.cr, rej.activa
m = np.zeros(RAS.shape, bool)
m[RAS >= 0] = sos[RAS[RAS >= 0]]
g, ng = ndimage.label(m, structure=np.ones((3, 3)))
grupo = np.zeros(N, int)
grupo[act] = g[fr[act], cr[act]]
imu = acceso.marginacion_conapo()[["CVEGEO", "NOM_MUN"]].set_index("CVEGEO")["NOM_MUN"]
gr = (c[grupo > 0].assign(grupo=grupo[grupo > 0])
      .groupby("grupo").agg(psin=("psin", "sum"), celdas=("psin", "size"), x=("x", "mean"), y=("y", "mean"),
                            CVEGEO=("CVEGEO", "first"), anclaje_med=("x", lambda s: np.median(ANC[s.index])),
                            rodeo_med=("x", lambda s: np.median(rodeo[s.index])))
      .sort_values("psin", ascending=False))
gr["NOM_MUN"] = gr["CVEGEO"].map(imu)
print(gr.head(15).round(1).to_string())

res = {"criterio": "sospechosa = acceso 0 por calle y unidad a ≤ 1,667 m en recta",
       "clases": tab.round(1).to_dict(orient="index"), "islas_b0": islas_cero, "sensibilidad_hibrido": sens,
       "comparacion_recta_por_cuenca": comp_cuenca,
       "grupos_sospechosos": gr.head(15).drop(columns=["CVEGEO"]).round(1).reset_index().to_dict(orient="records")}
(SALIDA / "ceros_calle.json").write_text(json.dumps(res, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
c[["x", "y"]].assign(clase=clase, d_recta=D_RECTA, d_calle=D_CALLE).to_parquet(INT / "ceros_calle.parquet")

# %% [markdown]
# ## Figura: clases de ceros y acercamientos a los dos grupos sospechosos más grandes

# %%
COL = {"lejos de verdad": ve.GRIS, "zona gris": "#c9c7bf", "rodeo moderado": ve.AQUA, "rodeo > 2": ve.NARANJA,
       "red desconectada": ve.TEXTO, "sin calle a 300 m": ve.AZUL}
fig, axs = plt.subplots(1, 3, figsize=(17, 6.6), gridspec_kw={"width_ratios": [1, 1.2, 1.2]})
ax = axs[0]
t = tab["psin"][::-1] / 1000
ax.barh(t.index, t.values, color=[COL[k] for k in t.index], height=0.6)
for y, v in enumerate(t.values):
    ax.text(v, y, f" {v:,.0f} mil", va="center", fontsize=9)
ax.set_xlabel("Personas sin seguro (miles)")
ax.set_title("Celdas con acceso 0 por calle, por causa", fontsize=10)
ax.set_xlim(0, t.max() * 1.3)

xy_r, U, V = z["xy"], z["u"], z["v"]
for ax, (gid, fila) in zip(axs[1:], gr.head(2).iterrows()):
    sel = grupo == gid
    x0, x1 = XY[sel, 0].min() - 1500, XY[sel, 0].max() + 1500
    y0, y1 = XY[sel, 1].min() - 1500, XY[sel, 1].max() + 1500
    dentro = lambda p: (p[:, 0] > x0) & (p[:, 0] < x1) & (p[:, 1] > y0) & (p[:, 1] < y1)
    en = dentro(xy_r)
    k = en[U] & en[V]
    ax.add_collection(LineCollection(np.stack([xy_r[U[k]], xy_r[V[k]]], 1), colors=ve.GRIS, lw=0.4))
    ce = dentro(XY) & (PSIN > 0)
    ax.scatter(*XY[ce & ~cero].T, s=10, c="#e6e5e0", marker="s", lw=0, label="Con acceso por calle")
    for k2 in ORDEN:
        q = ce & (clase == k2)
        if q.any():
            ax.scatter(*XY[q].T, s=10, c=COL[k2], marker="s", lw=0, label=k2.capitalize())
    fu = dentro(FXY)
    ax.scatter(*FXY[fu].T, s=40, c=ve.TEXTO, marker="+", lw=1.2, label="Unidad de salud")
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(f"{fila['NOM_MUN']}: {fila['psin']:,.0f} personas, rodeo mediano {fila['rodeo_med']:.1f}", fontsize=10)
    ax.legend(fontsize=7.5, frameon=True, loc="lower left", markerscale=1.5)
ve.titulo(fig, "¿Acceso 0 por calle: lejanía real o red incompleta?",
          f"Sospechosa: sin unidad a 2,250 m de calle pero con una a ≤ 1,667 m en recta. "
          f"Con el acceso en recta en esas celdas, {sens['cuenca_estables_calle_que_sobreviven_pct']:.0f}% de las islas estables por calle siguen en la cuenca de una isla.")
fig.subplots_adjust(top=0.82, wspace=0.08)
ve.guardar(fig, FIG / "ceros_calle.png")
