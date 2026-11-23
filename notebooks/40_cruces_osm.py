# %% [markdown]
# # 40 — ¿Los ceros sospechosos por calle se arreglan corrigiendo OSM? (F8.2 de `PLAN_ACCESO.md`)
#
# El notebook 35 marca como **sospechosas** las celdas con acceso 0 por calle que tienen una
# unidad a ≤ 1,667 m en recta, y su chequeo híbrido (darles el acceso en recta) ya no pasa con
# CLUES: sobrevive el 76% de las islas estables por calle. Pero el híbrido supone que **todo**
# cero sospechoso es un error de la red. Aquí, en vez de suponerlo, se corrige la red con los
# defectos típicos de OSM y se mide cuánto cambian los ceros y las islas.
#
# Un diagnóstico previo en las 10 zonas sospechosas más grandes (2026-11-23, fuera del
# repositorio) agregó todos los enlaces candidatos y el rodeo mediano casi no bajó en 6 de 10.
# Este notebook lo hace en todas las zonas, con la regla fijada abajo.
#
# ## Regla de corrección, fijada antes de correr (escenario permisivo)
#
# Dominio: nodos de la red a ≤ 2,250 m en recta de alguna celda sospechosa (ningún camino de
# ≤ 2,250 m de calle desde esas celdas sale de ahí). Dentro del dominio se agregan:
#
# 1. **Cruces sin nodo:** dos segmentos que se cruzan sin compartir extremo. Se agrega un nodo
#    en la intersección, unido a los cuatro extremos.
# 2. **Casi-uniones:** un nodo sin salida (grado 1) a ≤ 20 m de un segmento que no le toca, si
#    por la red el punto proyectado le queda a > 300 m (vía cualquiera de los extremos, o sin
#    camino). Se agrega un nodo en la proyección unido al nodo sin salida; por nodo, solo el
#    candidato elegible más cercano.
# 3. Cada arista se parte en **todos** sus puntos nuevos, ordenados a lo largo (dos cruces en
#    la misma calle quedan unidos entre sí, no solo a los extremos).
# 4. **Anclajes fijos:** celdas y unidades se anclan a los mismos nodos que en el 33, para
#    medir solo el efecto de los enlaces nuevos.
#
# Es un **escenario permisivo a propósito** (cubre solo estos dos defectos). La red guardada no trae etiquetas de puente, túnel,
# capa, barda ni río, así que se conectan también cruces legítimos a desnivel (puentes,
# pasos a desnivel) y sin salidas junto a una barda. Si ni así cambia la geografía, los
# defectos de OSM no la explican. Si cambia, no se concluye que fueran errores: haría falta
# reextraer con etiquetas para separarlos.
#
# No se buscan uniones en T con nodo de grado > 1, extremos duplicados con otro id ni tramos
# que la extracción dejó fuera (etiquetas no caminables); quedan como límite.
#
# *Ajustes tras la crítica de Codex, antes de correr:* partir aristas en todos sus puntos;
# anclajes fijos; distancia de red a la proyección y no a los extremos; aristas que tocan el
# dominio (no solo las que caen dentro); fracción del híbrido indefinida si la diferencia es
# ≤ 0; grafo base sin árboles y liberación de memoria antes de armar la red corregida.
#
# ## Medidas y criterio
#
# - Mismo E2SFCA por calle que el 33 (2,250 m, gaussiano, capacidad CLUES, promedio
#   metropolitano = capacidad total / demanda total, sin cambiar).
# - Se reportan: gente con acceso 0 y con acceso bajo antes y después; cuántas celdas
#   sospechosas ganan acceso; qué fracción de la diferencia base → híbrido del 35 cierra la
#   corrección (`frac_hibrido_cerrada`, en gente con acceso bajo; indefinida si esa diferencia es ≤ 0).
# - **Criterio (el mismo del 35):** las islas estables por calle sobreviven si su cuenca se
#   empareja uno a uno (Jaccard ≥ 0.5) con una isla del acceso corregido. Si sobrevive ≥ 80%,
#   **los defectos de OSM no cambian la geografía de F4**, y la falla del híbrido se lee como
#   un supuesto demasiado generoso, no como red rota.

# %%
import heapq
import json
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shapely
from matplotlib.collections import LineCollection
from scipy.spatial import cKDTree

from lib import acceso, config, f4, red_peatonal as rp, topo_rejilla as tr, viz_eval as ve

ve.aplicar()
T0 = time.time()
INT = config.INTERMEDIOS_DIR
SALIDA = config.OUTPUTS_DIR / "auditoria"
FIG = config.FIGURAS_DIR
LIM = 30 * 4500 / 60  # 2,250 m
CASI, LEJOS_RED = 20.0, 300.0
SOSPECHOSAS = {"rodeo moderado", "rodeo > 2", "red desconectada", "sin calle a 300 m"}


def reloj(msg):
    print(f"[{(time.time() - T0) / 60:5.1f} min] {msg}", flush=True)


c = pd.read_parquet(INT / "acceso_e2sfca_celdas.parquet")
calle = pd.read_parquet(INT / "acceso_calle.parquet")
ceros = pd.read_parquet(INT / "ceros_calle.parquet")
assert np.allclose(ceros[["x", "y"]].to_numpy(), c[["x", "y"]].to_numpy())
o = acceso.oferta()
XY, PSIN = c[["x", "y"]].to_numpy(), c["psin"].to_numpy()
FXY, CAP = o[["x", "y"]].to_numpy(), o["cap"].to_numpy(float)
N = len(c)
PROM = CAP.sum() / PSIN.sum()
F0, F1 = c["acceso_rel"].to_numpy(), calle["acceso_rel_calle"].to_numpy()
CLASE = ceros["clase"].astype(str).to_numpy()
SOS = np.isin(CLASE, list(SOSPECHOSAS))
print(f"celdas sospechosas: {SOS.sum():,}, personas: {PSIN[SOS].sum():,.0f}")

z = np.load(INT / "red_peatonal.npz")
XYN, U, V, L = z["xy"], z["u"].astype(np.int64), z["v"].astype(np.int64), z["largo"]
NN = len(XYN)

# %% [markdown]
# ## Dominio y candidatos

# %%
from scipy import sparse
from scipy.sparse import csgraph

# Grafo base sin árboles (CSR, aristas repetidas: la más corta), para distancias locales.
a_, b_ = np.minimum(U, V), np.maximum(U, V)
e_ = pd.DataFrame({"a": a_, "b": b_, "l": L}).groupby(["a", "b"], as_index=False)["l"].min()
ea, eb, el = e_["a"].to_numpy(), e_["b"].to_numpy(), np.maximum(e_["l"].to_numpy(), 1e-3)
del a_, b_, e_
G = sparse.csr_matrix((np.r_[el, el], (np.r_[ea, eb], np.r_[eb, ea])), shape=(NN, NN))
grado = np.diff(G.indptr)

# Anclajes fijos: los del notebook 33 (componentes de ≥ 1,000 nodos de la red base).
_, comp = csgraph.connected_components(G, directed=False)
util = np.flatnonzero(np.bincount(comp)[comp] >= 1000)
arbol_util = cKDTree(XYN[util])
d_, k_ = arbol_util.query(XY)
CEL_NODO, CEL_ANC = util[k_], d_
d_, k_ = arbol_util.query(FXY)
FUE_NODO, FUE_ANC = util[k_], d_
del arbol_util, comp, util
assert np.allclose(CEL_ANC, np.load(INT / "anclaje_celdas.npy"), atol=1e-3), "anclajes distintos a los del 33"

arbol_sos = cKDTree(XY[SOS])
dom = np.isfinite(arbol_sos.query(XYN, distance_upper_bound=LIM)[0])
del arbol_sos
seg = np.flatnonzero(dom[ea] | dom[eb])  # aristas que tocan el dominio
SA, SB = ea[seg], eb[seg]
reloj(f"dominio: {dom.sum():,} nodos, {len(seg):,} segmentos")


def dist_red(s, destinos, limite):
    """Dijkstra desde s con corte; distancia a cada destino (inf si > limite)."""
    falta, out = set(destinos), {}
    vis, h = set(), [(0.0, s)]
    while h and falta:
        d, x = heapq.heappop(h)
        if x in vis:
            continue
        vis.add(x)
        if x in falta:
            out[x] = d
            falta.discard(x)
        for k in range(G.indptr[x], G.indptr[x + 1]):
            y, nd = G.indices[k], d + G.data[k]
            if nd <= limite and y not in vis:
                heapq.heappush(h, (nd, y))
    return np.array([out.get(t, np.inf) for t in destinos])


lineas = shapely.linestrings(np.stack([XYN[SA], XYN[SB]], axis=1))
arbol_seg = shapely.STRtree(lineas)

# Puntos nuevos sobre aristas: (índice en seg, posición 0-1 a lo largo, id de nodo).
sobre_seg, pos_seg, id_seg = [], [], []
extra_xy = []


def nodo_nuevo(xy_):
    extra_xy.append(xy_)
    return NN + len(extra_xy) - 1


# 1. Cruces sin nodo compartido (puntos coincidentes = un solo nodo).
p, q = arbol_seg.query(lineas, predicate="crosses")
k = p < q
p, q = p[k], q[k]
k = ~((SA[p] == SA[q]) | (SA[p] == SB[q]) | (SB[p] == SA[q]) | (SB[p] == SB[q]))
p, q = p[k], q[k]
pt = shapely.intersection(lineas[p], lineas[q])
k = shapely.get_type_id(pt) == 0
p, q, pt = p[k], q[k], pt[k]
XC = shapely.get_coordinates(pt)
clave, inv = np.unique(np.round(XC, 2), axis=0, return_inverse=True)
inv = inv.ravel()
ids_c = np.array([nodo_nuevo(xy_) for xy_ in clave], dtype=np.int64).reshape(-1)
for s_ in (p, q):
    sobre_seg.append(s_)
    pos_seg.append(shapely.line_locate_point(lineas[s_], pt, normalized=True))
    id_seg.append(ids_c[inv])
n_cruces = len(clave)
reloj(f"cruces sin nodo: {len(p):,} pares de segmentos, {n_cruces:,} puntos")
del pt

# 2. Casi-uniones: nodo sin salida a ≤ CASI m de un segmento que no le toca y a > LEJOS_RED m
#    por la red del punto proyectado; por nodo, el candidato elegible más cercano.
sin_salida = np.flatnonzero(dom & (grado == 1))
ip, iq = arbol_seg.query(shapely.points(XYN[sin_salida]), predicate="dwithin", distance=CASI)
nodo = sin_salida[ip]
k = (SA[iq] != nodo) & (SB[iq] != nodo)
nodo, iq = nodo[k], iq[k]
pts_n = shapely.points(XYN[nodo])
tpos = shapely.line_locate_point(lineas[iq], pts_n, normalized=True)
proy = shapely.get_coordinates(shapely.line_interpolate_point(lineas[iq], tpos, normalized=True))
dseg = np.hypot(*(proy - XYN[nodo]).T)
reloj(f"sin salida en el dominio: {len(sin_salida):,}; pares con segmento ajeno a ≤ {CASI:.0f} m: {len(nodo):,}")
cu_nodo, cu_seg, cu_t, cu_xy = [], [], [], []
orden = np.argsort(nodo, kind="stable")
cortes = np.flatnonzero(np.diff(nodo[orden])) + 1
for g in np.split(orden, cortes):
    if not len(g):
        continue
    n_ = int(nodo[g[0]])
    sa_, sb_ = SA[iq[g]], SB[iq[g]]
    ext = np.unique(np.r_[sa_, sb_])
    dmap = dict(zip(ext.tolist(), dist_red(n_, ext.tolist(), LEJOS_RED + CASI + 1e-6)))
    da = np.array([dmap[x] for x in sa_.tolist()]) + np.hypot(*(XYN[sa_] - proy[g]).T)
    db = np.array([dmap[x] for x in sb_.tolist()]) + np.hypot(*(XYN[sb_] - proy[g]).T)
    ok = np.minimum(da, db) > LEJOS_RED
    if ok.any():
        m_ = g[ok][np.argmin(dseg[g[ok]])]
        cu_nodo.append(n_)
        cu_seg.append(iq[m_])
        cu_t.append(tpos[m_])
        cu_xy.append(proy[m_])
cu_nodo, cu_seg, cu_t = np.array(cu_nodo, np.int64), np.array(cu_seg, np.int64), np.array(cu_t, float)
ids_p = np.array([nodo_nuevo(xy_) for xy_ in cu_xy], dtype=np.int64).reshape(-1)
sobre_seg.append(cu_seg)
pos_seg.append(cu_t)
id_seg.append(ids_p)
n_casi = len(cu_nodo)
reloj(f"casi-uniones (a > {LEJOS_RED:.0f} m por red): {n_casi:,}")
del lineas, arbol_seg, pts_n

# %% [markdown]
# ## Red corregida: cada arista se parte en todos sus puntos nuevos, en orden

# %%
XY2 = np.vstack([XYN, np.array(extra_xy).reshape(-1, 2)])
sobre_seg, pos_seg, id_seg = np.concatenate(sobre_seg), np.concatenate(pos_seg), np.concatenate(id_seg)
t_ = pd.DataFrame({"s": sobre_seg, "t": pos_seg, "id": id_seg}).drop_duplicates(["s", "id"]).sort_values(["s", "t"])
partidas = t_["s"].unique()
nu, nv = [cu_nodo], [ids_p]  # unión del nodo sin salida a su proyección
for s_, gr_ in t_.groupby("s", sort=False):
    cadena = np.r_[SA[s_], gr_["id"].to_numpy(), SB[s_]]
    nu.append(cadena[:-1])
    nv.append(cadena[1:])
nu, nv = np.concatenate(nu).astype(np.int64), np.concatenate(nv).astype(np.int64)
quitar = np.zeros(len(ea), bool)
quitar[seg[partidas]] = True
U2, V2 = np.r_[ea[~quitar], nu], np.r_[eb[~quitar], nv]
L2 = np.r_[el[~quitar], np.hypot(*(XY2[nu] - XY2[nv]).T)]
del G, t_
red2 = rp.Red(XY2, U2, V2, L2)
reloj("red corregida lista; Dijkstra desde las unidades (anclajes fijos del 33)")
I2, J2, D2, _ = red2.pares(XY, FXY, LIM, anclas=(CEL_NODO, CEL_ANC, FUE_NODO, FUE_ANC))
A2, _ = acceso.e2sfca_pares(I2, J2, acceso.peso(D2, LIM), PSIN, CAP, N)
F2 = A2 / PROM
reloj("E2SFCA corregido")
del red2

# Comprobación: los pares guardados del 33 reproducen el F por calle.
p0 = pd.read_parquet(INT / "pares_red_unidades.parquet")
A1, _ = acceso.e2sfca_pares(p0["i"].to_numpy(), p0["j"].to_numpy(), acceso.peso(p0["d"].to_numpy(float), LIM),
                            PSIN, CAP, N)
assert np.allclose(A1 / PROM, F1, rtol=1e-4, atol=1e-4)
# Agregar aristas solo acorta caminos, pero f puede bajar en algunas celdas (la unidad reparte
# su capacidad entre más gente). Se reporta.
print(f"celdas donde f baja: {(F2 < F1 - 1e-6).sum():,}; personas: {PSIN[F2 < F1 - 1e-6].sum():,.0f}")

FH = np.where(SOS, F0, F1)  # híbrido del notebook 35


def resumen(F):
    return {"psin_cero": float(PSIN[F == 0].sum()), "psin_bajo": float(PSIN[F < 0.5].sum()),
            "psin_cero_sospechosas": float(PSIN[SOS & (F == 0)].sum())}


base, corr, hib = resumen(F1), resumen(F2), resumen(FH)
dif_hib = base["psin_bajo"] - hib["psin_bajo"]
frac_hib = (base["psin_bajo"] - corr["psin_bajo"]) / dif_hib if dif_hib > 0 else float("nan")
ganan = SOS & (F2 > 0)
por_clase = (pd.DataFrame({"clase": CLASE[SOS], "psin": PSIN[SOS], "gana": ganan[SOS]})
             .assign(psin_gana=lambda d: d.psin * d.gana).groupby("clase")[["psin", "psin_gana"]].sum())
por_clase["pct_gana"] = por_clase["psin_gana"] / por_clase["psin"] * 100
print(pd.DataFrame({"base": base, "corregida": corr, "hibrido_35": hib}).round(0).to_string())
print(por_clase.round(1).to_string())
print(f"fracción de la diferencia base → híbrido cerrada por la corrección: {frac_hib:.1%}")

# %% [markdown]
# ## Islas: ¿sobreviven las estables por calle?

# %%
rej = tr.Rejilla(c["x"], c["y"], acceso.PASO)
isl = pd.read_parquet(INT / "islas_acceso_calle.parquet")
est = isl[isl["estable"] & (isl["tipo"] != "resto de región")].reset_index(drop=True)
_, _, CUEN1 = rej.h0(F1, cuencas=True)
p2, _, CUEN2 = rej.h0(F2, cuencas=True)
i2 = tr.islas(p2)
Jm, fil, col, jres = tr.jaccard_emparejado(f4.lista_cuencas(est, CUEN1), f4.lista_cuencas(i2, CUEN2), N,
                                           umbral=f4.J_MIN)
jpar = np.zeros(len(est))
jpar[fil] = Jm[fil, col]
est["sobrevive"] = jpar >= f4.J_MIN
cer = (est["b"] == 0).to_numpy()
islas = {
    "estables_calle": len(est), "islas_corregida": len(i2),
    "jaccard_emparejado_resumen": float(jres),
    "sobreviven_pct": float(est["sobrevive"].mean() * 100),
    "b0_sobreviven_pct": float(est.loc[cer, "sobrevive"].mean() * 100),
    "b_pos_sobreviven_pct": float(est.loc[~cer, "sobrevive"].mean() * 100),
}
islas["geografia_robusta_a_osm"] = bool(islas["sobreviven_pct"] >= 80)
print(json.dumps(islas, indent=1))

res = {
    "regla": {"dominio_m": LIM, "casi_union_m": CASI, "lejos_por_red_m": LEJOS_RED,
              "nota": "escenario permisivo: sin etiquetas de puente, túnel ni barda"},
    "candidatos": {"nodos_dominio": int(dom.sum()), "segmentos_dominio": int(len(seg)),
                   "cruces_sin_nodo": int(n_cruces), "sin_salida_dominio": int(len(sin_salida)), "casi_uniones": int(n_casi)},
    "acceso": {"base": base, "corregida": corr, "hibrido_35": hib, "frac_hibrido_cerrada": float(frac_hib),
               "sospechosas_por_clase": por_clase.round(1).to_dict(orient="index"),
               "psin_sospechosas": float(PSIN[SOS].sum()), "psin_sospechosas_que_ganan": float(PSIN[ganan].sum())},
    "islas": islas,
    "minutos": (time.time() - T0) / 60,
}
f4.guardar_json(res, SALIDA / "cruces_osm.json")

# %% [markdown]
# ## Figura: ceros antes y después, y la zona sospechosa más grande con los enlaces agregados

# %%
gr = json.load(open(SALIDA / "ceros_calle.json", encoding="utf-8"))["grupos_sospechosos"][0]
fig, axs = plt.subplots(1, 2, figsize=(15, 6.8), gridspec_kw={"width_ratios": [1, 1.3]})
ax = axs[0]
etq = ["Acceso 0\n(todas)", "Acceso 0\n(sospechosas)", "Acceso bajo\n(f < 0.5)"]
cl = ["psin_cero", "psin_cero_sospechosas", "psin_bajo"]
xs = np.arange(len(cl))
for d, (nom, r, col_) in enumerate([("Red base", base, ve.GRIS), ("Red corregida (escenario permisivo)", corr, ve.AZUL),
                                    ("Híbrido del 35", hib, ve.NARANJA)]):
    v = [r[k] / 1e6 for k in cl]
    ax.bar(xs + (d - 1) * 0.27, v, 0.25, color=col_, label=nom)
    for x_, v_ in zip(xs + (d - 1) * 0.27, v):
        ax.text(x_, v_, f"{v_:.2f}", ha="center", va="bottom", fontsize=8)
ax.set_xticks(xs, etq)
ax.set_ylabel("Personas sin seguro (millones)")
ax.legend(fontsize=8, frameon=False)
ax.set_title("Gente por estado de acceso", fontsize=10)

ax = axs[1]
x0, y0, R = gr["x"], gr["y"], 2500
dentro = lambda P: (np.abs(P[:, 0] - x0) < R) & (np.abs(P[:, 1] - y0) < R)
en = dentro(XYN)
k = en[U] & en[V]
ax.add_collection(LineCollection(np.stack([XYN[U[k]], XYN[V[k]]], 1), colors=ve.GRIS, lw=0.35))
cu_en = dentro(XYN[cu_nodo])
ax.add_collection(LineCollection(np.stack([XYN[cu_nodo[cu_en]], XY2[ids_p[cu_en]]], 1), colors=ve.AZUL, lw=2))
cr_en = dentro(XY2[ids_c])
ax.scatter(*XY2[ids_c[cr_en]].T, s=14, facecolors="none", edgecolors=ve.AZUL, lw=1,
           label=f"Cruce sin nodo, conectado ({cr_en.sum()})")
nuevos = cu_en
ce = dentro(XY) & (PSIN > 0)
ax.scatter(*XY[ce & SOS & (F2 == 0)].T, s=9, c=ve.NARANJA, marker="s", lw=0, label="Sospechosa, sigue en 0")
ax.scatter(*XY[ce & SOS & (F2 > 0)].T, s=9, c=ve.AQUA, marker="s", lw=0, label="Sospechosa, gana acceso")
fu = dentro(FXY)
ax.scatter(*FXY[fu].T, s=50, c=ve.TEXTO, marker="+", lw=1.3, label="Unidad de salud")
ax.plot([], [], c=ve.AZUL, lw=1.6, label=f"Casi-unión agregada ({nuevos.sum()})")
ax.set_xlim(x0 - R, x0 + R)
ax.set_ylim(y0 - R, y0 + R)
ax.set_aspect("equal")
ax.set_xticks([])
ax.set_yticks([])
ax.legend(fontsize=8, loc="lower left", frameon=True)
ax.set_title(f"{gr['NOM_MUN']}: zona sospechosa más grande", fontsize=10)
ve.titulo(fig, "¿Corregir OSM devuelve el acceso a los ceros sospechosos?",
          f"Escenario permisivo: {n_cruces:,} cruces sin nodo y {n_casi:,} casi-uniones agregados. "
          f"Sobreviven {islas['sobreviven_pct']:.0f}% de las islas estables por calle; "
          f"la corrección cierra {frac_hib:.0%} de la diferencia con el híbrido del 35.")
fig.subplots_adjust(top=0.83, wspace=0.08)
ve.guardar(fig, FIG / "cruces_osm.png")
reloj("listo")
