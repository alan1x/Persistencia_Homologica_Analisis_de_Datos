# %% [markdown]
# # 38 — Sensibilidad a los parámetros de F3 (acceso por calle)
#
# Las conclusiones de F4 y F5 usan una sola forma de medir el acceso: cuenca de 30 min de calle
# (2,250 m) con decaimiento gaussiano. Aquí se repite todo con cuatro combinaciones:
#
# | | gaussiano | escalones (1, 0.68, 0.22 por tercios) |
# |---|---|---|
# | **30 min (2,250 m)** | base | E30 |
# | **15 min (1,125 m)** | G15 | E15 |
#
# Se reusan los pares celda–unidad y celda–candidato por la red (hasta 2,250 m); para 15 min
# se filtran a d ≤ 1,125 m. f = A / (capacidad total / personas sin seguro), como siempre. La
# cobertura de F5 se queda en 1,125 m en todas.
#
# **Qué se mide en cada configuración**
# - Mapa: personas con f < 0.5, con f = 0 y brecha; Jaccard ponderado por personas del mapa
#   {f < 0.5} contra la base; Spearman de f. Como f < 0.5 mezcla un cambio de escala con un
#   cambio de forma, también el Jaccard con un umbral relativo (el cuantil que deja la misma
#   población baja que la base).
# - Islas: H0 sin réplicas de estabilidad. Las cuencas de las islas estables de la base (sin
#   "resto de región") se emparejan uno a uno con las de cada configuración (Jaccard ≥ 0.5).
# - F5: voraz perezoso de la brecha con K = 20, con el f y los aumentos de cada configuración
#   (mismos candidatos). Sitios a ≤ 500 m de los de la base, y **arrepentimiento**: qué
#   fracción de la reducción de brecha que logra el voraz propio logran los sitios de la base,
#   evaluados con el modelo de la configuración.
#
# **Criterios (fijados antes de correr)**
# - **Robusta:** Jaccard del mapa ≥ 0.7, ≥ 70% de la gente con acceso bajo en islas estables
#   de la base cae en islas recuperadas, y los sitios de la base logran ≥ 90% de la reducción
#   propia.
# - **Decisión robusta:** solo se cumple el criterio de F5.
# - **Frágil:** no se cumple el de F5.
# - **Veredicto global:** el del peor escenario alternativo (no un promedio). Se reporta el
#   margen a cada corte y si moverlo ±5 puntos cambiaría la etiqueta.
# - Sitios "cerca": emparejamiento uno a uno (distancia euclidiana) con pareja a ≤ 500 m.
# - Las configuraciones de 15 min responden otra pregunta (acceso a pie en 15 min). Se reportan
#   igual, pero el veredicto que importa para el paper es el de E30 (misma cuenca, otra forma).

# %%
import heapq
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
from scipy.optimize import linear_sum_assignment
from scipy.spatial import cKDTree
from scipy.stats import spearmanr

from lib import acceso, config, f4, topo_rejilla as tr, viz_eval as ve
from lib.f4 import UMBRAL_B, UMBRAL_P, TOPE

ve.aplicar()
INT = config.INTERMEDIOS_DIR
SALIDA = config.OUTPUTS_DIR / "auditoria"
FIG = config.FIGURAS_DIR
C30, C15 = 30 * 4500 / 60, 15 * 4500 / 60
K, J_MIN, CERCA = 20, 0.5, 500.0
CRIT = {"jaccard_mapa": 0.7, "recuperacion_islas": 0.7, "arrepentimiento": 0.9}
CONF = {"base": (C30, "gauss"), "E30": (C30, "escalones"), "G15": (C15, "gauss"), "E15": (C15, "escalones")}

c = pd.read_parquet(INT / "acceso_e2sfca_celdas.parquet")
XY, PSIN = c[["x", "y"]].to_numpy(), c["psin"].to_numpy()
N = len(c)
PESO = PSIN * np.where(c["alta_marg"].to_numpy(bool), 2.0, 1.0)
o = acceso.oferta()
CAP_U = o["cap"].to_numpy(float)
PROM = CAP_U.sum() / PSIN.sum()
CAP = float(np.median(CAP_U))

pu = pd.read_parquet(INT / "pares_red_unidades.parquet")
Iu, Ju, Du = pu["i"].to_numpy(), pu["j"].to_numpy(), pu["d"].to_numpy(float)
pc = pd.read_parquet(INT / "pares_red_candidatos_calle.parquet")
orden = np.argsort(pc["j"].to_numpy(), kind="stable")
Ic, Jc, Dc = (pc[k].to_numpy()[orden] for k in ("i", "j", "d"))
Dc = Dc.astype(float)
M = int(Jc.max()) + 1
CXY = pc.drop_duplicates("j").sort_values("j")[["cx", "cy"]].to_numpy()
PTR = np.searchsorted(Jc, np.arange(M + 1))

F_GUARDADO = pd.read_parquet(INT / "acceso_calle.parquet")["acceso_rel_calle"].to_numpy()

rej = tr.Rejilla(c["x"], c["y"], acceso.PASO)
act = rej.activa
reg_pob, _ = ndimage.label(rej.ras >= 0, structure=np.ones((3, 3)))
REG = np.zeros(N, int)
REG[act] = reg_pob[rej.fr[act], rej.cr[act]]


def modelo(d0, tipo):
    """f por celda y aumento de f por par candidato–celda para una configuración."""
    m = Du <= d0
    A, _ = acceso.e2sfca_pares(Iu[m], Ju[m], acceso.peso(Du[m], d0, tipo), PSIN, CAP_U, N)
    w = acceso.peso(Dc, d0, tipo)  # 0 fuera de la cuenca
    den = np.bincount(Jc, weights=PSIN[Ic] * w, minlength=M)
    delta = CAP / np.maximum(den[Jc], 1e-9) * w / PROM
    return A / PROM, delta


def brecha(f):
    return float((PESO * np.maximum(0, UMBRAL_B - f)).sum())


def con_sitios(f, delta, sel):
    s = np.concatenate([np.arange(PTR[k], PTR[k + 1]) for k in sel])
    return f + np.bincount(Ic[s], weights=delta[s], minlength=N)


def voraz(f0, delta, K):
    f = f0.copy()

    def contrib(s):
        g = f[Ic[s]]
        return PESO[Ic[s]] * (np.maximum(0, UMBRAL_B - g) - np.maximum(0, UMBRAL_B - g - delta[s]))

    g = np.bincount(Jc, weights=contrib(slice(0, len(Ic))), minlength=M)
    heap = [(-v, k) for k, v in enumerate(g) if v > 0]
    heapq.heapify(heap)
    sel = []
    while len(sel) < K and heap:
        _, k = heapq.heappop(heap)
        s = slice(PTR[k], PTR[k + 1])
        v = contrib(s).sum()
        if not heap or v >= -heap[0][0]:
            sel.append(k)
            np.add.at(f, Ic[s], delta[s])
        else:
            heapq.heappush(heap, (-v, k))
    return sel


def islas_de(f):
    """Islas finitas y aisladas (sin resto de región) con sus cuencas."""
    pares, _, cu = rej.h0(f, cuencas=True, umbral_b=UMBRAL_B, umbral_p=UMBRAL_P, tope=TOPE)
    isl = tr.islas(pares, UMBRAL_B, UMBRAL_P).reset_index(drop=True)
    cuen = f4.lista_cuencas(isl, cu)
    reg = pd.Series(REG[isl["celda"]])
    keep = np.isfinite(isl["d"].to_numpy()) | (reg.map(reg.value_counts()).to_numpy() == 1)
    return isl, cuen, keep


# %% [markdown]
# ## Base: comprobaciones y sus islas estables

# %%
MOD = {k: modelo(*v) for k, v in CONF.items()}
F_BASE = MOD["base"][0]
assert np.abs(F_BASE - F_GUARDADO).max() < 1e-4
print("celdas que cambian de lado de f < 0.5 al reconstruir:", int(((F_BASE < UMBRAL_B) != (F_GUARDADO < UMBRAL_B)).sum()))

isl_b, cuen_b, _ = islas_de(F_BASE)
guard = pd.read_parquet(INT / "islas_acceso_calle.parquet")
assert (guard["celda"].to_numpy() == isl_b["celda"].to_numpy()).all()  # mismo orden que el notebook 34
sel_b = (guard["estable"] & (guard["tipo"] != "resto de región")).to_numpy()
CUEN_EST = [cuen_b[k] for k in np.flatnonzero(sel_b)]
ASIG_B = tr.particion(CUEN_EST, N)
BAJO_B = F_BASE < UMBRAL_B
PB_ISLA = np.bincount(ASIG_B[ASIG_B >= 0], (PSIN * BAJO_B)[ASIG_B >= 0], len(CUEN_EST))
print(f"islas estables base: {len(CUEN_EST)}, gente baja en ellas: {PB_ISLA.sum():,.0f}")

SITIOS = {k: voraz(f, d, K) for k, (f, d) in MOD.items()}
s32 = pd.read_csv(SALIDA / "optimizacion_sitios_calle.csv")
s32 = s32.loc[(s32["objetivo"] == "brecha") & (s32["orden"] <= K), ["x", "y"]].to_numpy()
iguales_32 = int((cKDTree(s32).query(CXY[SITIOS["base"]])[0] < 1).sum())
print(f"sitios base iguales a los del notebook 32: {iguales_32} de {K}")


# %% [markdown]
# ## Cada configuración contra la base

# %%
def jacc_pond(a, b):
    return float(PSIN[a & b].sum() / max(PSIN[a | b].sum(), 1e-9))


def umbral_relativo(f):
    """Las celdas de peor acceso con la misma población que el mapa bajo de la base.
    Empates (por ejemplo en f = 0) se rompen por el índice de la celda."""
    o_ = np.argsort(f, kind="stable")
    k = np.searchsorted(np.cumsum(PSIN[o_]), PSIN[BAJO_B].sum())
    m = np.zeros(N, bool)
    m[o_[: k + 1]] = True
    return m


def cerca_uno_a_uno(a, b):
    d = np.hypot(*(a[:, None, :] - b[None, :, :]).transpose(2, 0, 1))
    fi, co = linear_sum_assignment(np.where(d <= CERCA, d, 1e9))
    return int((d[fi, co] <= CERCA).sum())


def etiqueta(fila, desv=0.0):
    ok = {k: fila[k] >= v + desv for k, v in CRIT.items()}
    return "robusta" if all(ok.values()) else ("decisión robusta" if ok["arrepentimiento"] else "frágil")


res = {"criterios": CRIT, "configuraciones": {k: {"cuenca_m": v[0], "decaimiento": v[1]} for k, v in CONF.items()},
       "sitios_base_iguales_nb32": iguales_32, "islas_estables_base": len(CUEN_EST)}
filas = []
for k, (f, delta) in MOD.items():
    bajo = f < UMBRAL_B
    isl, cuen, keep = islas_de(f)
    cuen_k = [cuen[i] for i in np.flatnonzero(keep)]
    Jm, fi, co, _ = tr.jaccard_emparejado(CUEN_EST, cuen_k, N, umbral=J_MIN)
    ok = fi[Jm[fi, co] >= J_MIN]
    b0 = brecha(f)
    red_propia = 1 - brecha(con_sitios(f, delta, SITIOS[k])) / b0
    red_base = 1 - brecha(con_sitios(f, delta, SITIOS["base"])) / b0
    fila = {"config": k,
            "psin_bajo": float(PSIN[bajo].sum()), "psin_cero": float(PSIN[f == 0].sum()), "brecha": b0,
            "jaccard_mapa": jacc_pond(bajo, BAJO_B), "jaccard_mapa_relativo": jacc_pond(umbral_relativo(f), BAJO_B),
            "spearman_f": float(spearmanr(f, F_BASE).statistic),
            "n_islas": int(keep.sum()), "n_b0": int((keep & (isl["b"] == 0).to_numpy()).sum()),
            "islas_base_recuperadas": int(len(ok)),
            "recuperacion_islas": float(PB_ISLA[ok].sum() / PB_ISLA.sum()),
            "media_f": float((PSIN * f).sum() / PSIN.sum()),
            "reduccion_propia": red_propia, "reduccion_sitios_base": red_base,
            "reduccion_propia_abs": red_propia * b0, "reduccion_sitios_base_abs": red_base * b0,
            "arrepentimiento": red_base / red_propia,
            "sitios_cerca_base": cerca_uno_a_uno(CXY[SITIOS["base"]], CXY[SITIOS[k]])}
    mapa = fila["jaccard_mapa"] >= CRIT["jaccard_mapa"]
    islas_ok = fila["recuperacion_islas"] >= CRIT["recuperacion_islas"]
    f5 = fila["arrepentimiento"] >= CRIT["arrepentimiento"]
    fila["veredicto"] = etiqueta(fila)
    fila["cambia_con_5pts"] = len({etiqueta(fila, d) for d in (-0.05, 0.05)} | {fila["veredicto"]}) > 1
    filas.append(fila)
    print(k, {a: (round(b, 3) if isinstance(b, float) else b) for a, b in fila.items()})

tabla = pd.DataFrame(filas).set_index("config")
res["resultados"] = tabla.to_dict(orient="index")
RANGO = ["frágil", "decisión robusta", "robusta"]
alt = tabla.drop(index="base")
res["veredicto_global"] = min(alt["veredicto"], key=RANGO.index)
res["margenes"] = {k: {c: float(alt.loc[k, c] - v) for c, v in CRIT.items()} for k in alt.index}
print("veredicto global:", res["veredicto_global"])
res["sitios"] = {k: CXY[s].tolist() for k, s in SITIOS.items()}
f4.guardar_json(res, SALIDA / "sensibilidad_f3.json")
print(tabla.round(3).T.to_string())

# %% [markdown]
# ## Figura: mapa de acceso bajo de cada configuración contra la base

# %%
RAS = rej.ras
fig, axs = plt.subplots(1, 3, figsize=(16, 6.5))
for ax, k in zip(axs, ["E30", "G15", "E15"]):
    bajo = MOD[k][0] < UMBRAL_B
    v = np.zeros(N)
    v[bajo & BAJO_B] = 1
    v[BAJO_B & ~bajo] = 2
    v[bajo & ~BAJO_B] = 3
    img = np.full(RAS.shape, np.nan)
    img[RAS >= 0] = v[RAS[RAS >= 0]]
    ax.imshow(img, origin="lower", interpolation="nearest", vmin=0, vmax=3,
              cmap=plt.matplotlib.colors.ListedColormap(["#e6e5e0", "#c9c7bf", ve.AZUL, ve.NARANJA]))
    s0, s1 = CXY[SITIOS["base"]], CXY[SITIOS[k]]
    for s, mk, col in [(s0, "o", ve.TEXTO), (s1, "x", ve.NARANJA)]:
        ax.scatter((s[:, 0] - c["x"].min()) / acceso.PASO + 1, (s[:, 1] - c["y"].min()) / acceso.PASO + 1,
                   marker=mk, s=28, facecolors="none" if mk == "o" else col, edgecolors=col if mk == "o" else None,
                   linewidths=1.2)
    t = tabla.loc[k]
    nombre = {"E30": "30 min, escalones", "G15": "15 min, gaussiano", "E15": "15 min, escalones"}[k]
    ax.set_title(f"{nombre}: {t['veredicto']}\nJaccard {t['jaccard_mapa']:.2f} · islas {t['recuperacion_islas']:.0%}"
                 f" · F5 {t['arrepentimiento']:.0%}", fontsize=10.5)
    ax.set_axis_off()
    ax.set_aspect("equal")
fig.legend(handles=[Patch(color="#c9c7bf"), Patch(color=ve.AZUL), Patch(color=ve.NARANJA),
                    plt.Line2D([], [], marker="o", ls="", mfc="none", mec=ve.TEXTO),
                    plt.Line2D([], [], marker="x", ls="", color=ve.NARANJA)],
           labels=["Bajo en ambas", "Bajo solo en la base", "Bajo solo en la configuración",
                   "Sitios F5 de la base", "Sitios F5 de la configuración"],
           loc="lower center", ncol=5, fontsize=9, frameon=False)
ve.titulo(fig, "¿Cambian las conclusiones si se mide el acceso de otra forma?",
          "Acceso bajo (f < 0.5) contra la base: 30 min de calle con decaimiento gaussiano")
fig.subplots_adjust(top=0.83, bottom=0.08, wspace=0.05)
ve.guardar(fig, FIG / "sensibilidad_f3.png")
