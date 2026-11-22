# %% [markdown]
# # 36 — Nulo espacial para las islas de acceso bajo (F4, por calle)
#
# **Pregunta.** Las islas de F4 (persistencia H0 del acceso por calle) concentran al 81% de la
# gente con acceso bajo. ¿Es estructura, o lo daría cualquier superficie suave con la misma
# distribución de valores y la misma autocorrelación? Con 2.58 M de esa gente en islas que
# nacen en 0 (sin unidad alcanzable), la estabilidad ante la capacidad no responde esto.
#
# ## Dos nulos (diseño revisado con Codex)
#
# - **N2, principal: ceros fijos + gradiente urbano.** Las celdas con acceso 0 se quedan donde
#   están (la falta de cobertura es un hecho de la red, no se sortea). Los valores positivos se
#   reordenan con una cópula gaussiana: puntajes normales = tendencia amplia (suavizado
#   gaussiano σ = 5 km de los puntajes observados) + residuo simulado con la autocorrelación
#   del residuo observado. Pregunta: dado dónde no hay cobertura y el gradiente centro-periferia,
#   ¿el relieve local del acceso positivo hace las cuencas más profundas o más pobladas que un
#   relieve aleatorio?
#   - **Agregado tras la prueba de humo (3 simulaciones):** sin más, N2 ponía valores altos
#     junto a los ceros (acantilados que el acceso real no tiene, porque baja continuo hasta 0
#     en el borde de la cuenca) y daba 692 islas con b = 0 contra 409 observadas. Ahora la
#     tendencia incluye la rampa: el puntaje medio por distancia al cero más cercano (franjas
#     de 100 m hasta 3 km), más el suavizado amplio del resto. Los criterios no cambian.
# - **N1, referencia: estacionario.** Un solo campo con la autocorrelación de f (mezcla de dos
#   Matérn) reordena todos los valores, ceros incluidos. Es más fácil de rechazar: no conserva
#   el gradiente urbano ni la forma de los ceros. Solo descriptivo.
#
# La autocorrelación se calibra por simulación, pasando por la misma transformación de rangos.
# En el nulo se usan **todas** las islas (sin "resto de región"), no solo las estables ante la
# capacidad, porque el nulo no tiene réplicas de capacidad. Lo observado se mide igual.
#
# ## Criterios fijados antes de correr
#
# - **Ajuste:** el correlograma simulado (promedio) queda a ±0.05 del observado en desfases
#   ≤ 2 km. Si no, el resultado se marca como descriptivo.
# - **Estadístico principal:** fracción de la gente con acceso bajo (f < 0.5, denominador de
#   cada mapa) que vive en la unión de cuencas de islas. p = (1 + #{nulo ≥ obs}) / (n + 1),
#   n = 999 en N2. **Las islas son estructura** si p ≤ 0.05 y el exceso sobre la mediana del
#   nulo es ≥ 5 puntos porcentuales. Se reporta el exceso en personas y por nacimiento (b = 0,
#   b > 0).
# - **Por isla (finitas):** una isla es significativa si su persistencia supera el percentil
#   97.5 del máximo por réplica de su clase de nacimiento (b = 0 o b > 0; Bonferroni sobre las
#   dos clases, error de familia ≈ 5%). Las esenciales (aisladas, muerte infinita) van aparte.
#   Se reporta la gente con acceso bajo en islas estables y significativas.
#   - **Agregado tras la prueba de humo:** el corte por máximo quedó en ~17.6 (casi la isla más
#     profunda del mapa), así que no tiene poder. Criterio principal por isla: valor p contra
#     las persistencias finitas del nulo agrupadas por clase, p = (1 + #{nulo ≥ obs}) / (M + 1),
#     y Benjamini–Hochberg con FDR 5% dentro de cada clase. El del máximo queda como estricto.
# - **Secundarios:** número de islas, número con b = 0, persistencia total finita; p de dos
#   colas.

# %%
import json
import os
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch
from scipy import ndimage

from lib import acceso, config, f4, nulo, topo_rejilla as tr, viz_eval as ve
from lib.f4 import UMBRAL_B, UMBRAL_P, TOPE

ve.aplicar()
INT = config.INTERMEDIOS_DIR
SALIDA = config.OUTPUTS_DIR / "auditoria"
FIG = config.FIGURAS_DIR
N_SIM = {"N2": int(os.environ.get("N_SIM2", 999)), "N1": int(os.environ.get("N_SIM1", 200))}
SIGMA_TEND = 50  # celdas = 5 km
H = nulo.DESFASES * acceso.PASO
AJUSTE_LAG, AJUSTE_TOL = 20, 0.05

c = pd.read_parquet(INT / "acceso_e2sfca_celdas.parquet", columns=["x", "y", "psin"])
F = pd.read_parquet(INT / "acceso_calle.parquet")["acceso_rel_calle"].to_numpy()
PSIN = c["psin"].to_numpy()
N = len(c)
rej = tr.Rejilla(c["x"], c["y"], acceso.PASO)
act = rej.activa
reg_pob, _ = ndimage.label(rej.ras >= 0, structure=np.ones((3, 3)))
REG = np.zeros(N, int)
REG[act] = reg_pob[rej.fr[act], rej.cr[act]]


def resumen(f):
    """Islas de f (sin resto de región) y sus estadísticos."""
    pares, _, cu = rej.h0(f, cuencas=True, umbral_b=UMBRAL_B, umbral_p=UMBRAL_P, tope=TOPE)
    isl = tr.islas(pares, UMBRAL_B, UMBRAL_P).reset_index(drop=True)
    cuen = f4.lista_cuencas(isl, cu)
    reg = REG[isl["celda"]]
    n_reg = pd.Series(reg).map(pd.Series(reg).value_counts()).to_numpy()
    fin = np.isfinite(isl["d"].to_numpy())
    keep = fin | (n_reg == 1)
    isl = isl[keep].reset_index(drop=True)
    cuen = [cuen[k] for k in np.flatnonzero(keep)]
    asig = tr.particion(cuen, N)
    bajo = f < UMBRAL_B
    pb = PSIN * bajo
    en = asig >= 0
    b0 = (isl["b"] == 0).to_numpy()
    por_isla = np.bincount(asig[en], pb[en], len(isl))
    fin = np.isfinite(isl["d"].to_numpy())
    pers = isl["pers"].to_numpy()
    return {
        "frac_bajo_en_islas": float(pb[en].sum() / pb.sum()),
        "psin_bajo_en_islas": float(pb[en].sum()),
        "psin_bajo_en_islas_b0": float(por_isla[b0].sum()),
        "psin_bajo_en_islas_bpos": float(por_isla[~b0].sum()),
        "n_islas": len(isl), "n_b0": int(b0.sum()), "n_esenciales": int((~fin).sum()),
        "pers_total_finita": float(pers[fin].sum()),
        "max_pers_b0": float(pers[fin & b0].max(initial=0)),
        "max_pers_bpos": float(pers[fin & ~b0].max(initial=0)),
    }, isl, por_isla


obs, ISL, PB_ISL = resumen(F)
print(obs)

# %% [markdown]
# ## Ajuste de la autocorrelación

# %%
ORDEN_TODO = np.sort(F[act])
POS = act & (F > 0)
ORDEN_POS = np.sort(F[POS])


def suavizar(v, m, s=SIGMA_TEND):
    G, M = np.zeros(rej.ras.shape), np.zeros(rej.ras.shape)
    G[rej.fr[m], rej.cr[m]], M[rej.fr[m], rej.cr[m]] = v[m], 1.0
    a, b = ndimage.gaussian_filter(G, s), ndimage.gaussian_filter(M, s)
    out = np.zeros(len(v))
    out[m] = a[rej.fr[m], rej.cr[m]] / b[rej.fr[m], rej.cr[m]]
    return out


# N1: todo f
Z1 = nulo.puntajes_normales(F)
R1 = nulo.correlograma(rej, Z1)


def f_n1(gen, rng):
    fs = F.copy()
    fs[act] = nulo.a_marginal(gen.campo(rng), ORDEN_TODO, act)[act]
    return fs


# N2: positivos, tendencia + residuo
Z2 = np.zeros(N)
Z2[POS] = nulo.puntajes_normales(F[POS])
CERO = np.ones(rej.ras.shape, bool)
CERO[rej.fr[act & (F == 0)], rej.cr[act & (F == 0)]] = False
DIST0 = np.zeros(N)
DIST0[act] = ndimage.distance_transform_edt(CERO)[rej.fr[act], rej.cr[act]] * acceso.PASO
FRANJA = np.minimum(np.ceil(DIST0 / acceso.PASO), 30).astype(int)  # 1..30 (30 = ≥ 3 km)
RAMPA_TAB = pd.Series(Z2[POS]).groupby(FRANJA[POS]).mean()
RAMPA = np.zeros(N)
RAMPA[POS] = RAMPA_TAB.reindex(FRANJA[POS]).to_numpy()
TEND = np.where(POS, RAMPA + suavizar(Z2 - RAMPA, POS), 0.0)
RES = np.where(POS, Z2 - TEND, np.nan)
S_RES = float(np.nanstd(RES))
R2 = nulo.correlograma(rej, np.where(POS, Z2, np.nan))


def f_n2(gen, rng):
    x = gen.campo(rng)
    x = (x - x[POS].mean()) / x[POS].std()
    fs = F.copy()
    fs[POS] = nulo.a_marginal(TEND + S_RES * x, ORDEN_POS, POS)[POS]
    return fs


def z_n1(gen, rng):
    return nulo.puntajes_normales(f_n1(gen, rng))


def z_n2(gen, rng):
    fs = f_n2(gen, rng)
    v = np.full(N, np.nan)
    v[POS] = nulo.puntajes_normales(fs[POS])
    return v


t = time.time()
AJ = {"N1": nulo.calibrar(rej, acceso.PASO, nulo.ajustar_mezcla(H, R1), z_n1, R1),
      "N2": nulo.calibrar(rej, acceso.PASO, nulo.ajustar_mezcla(H, nulo.correlograma(rej, RES)), z_n2, R2)}
OBJ = {"N1": R1, "N2": R2}
for k, a in AJ.items():
    dif = np.abs(np.array(a["correlograma_simulado"]) - OBJ[k])[nulo.DESFASES <= AJUSTE_LAG]
    a["dif_max_hasta_2km"] = float(dif.max())
    a["ajuste_ok"] = bool(dif.max() <= AJUSTE_TOL)
    print(k, {q: v for q, v in a.items() if q != "correlograma_simulado"})
print(f"calibración: {time.time() - t:.0f} s")

# %% [markdown]
# ## Simulaciones

# %%
# Puntos de control cada 50 simulaciones: si el proceso se corta, retoma donde iba. Cada
# simulación tiene su propia semilla (semilla, s), así que retomar da lo mismo que no cortar.
SIM, PERS_SIM = {}, {}
for k, simular, semilla in [("N2", f_n2, 361), ("N1", f_n1, 362)]:
    a = AJ[k]
    gen = nulo.Generador(rej, acceso.PASO, a["w"], a["rho1"], a["rho2"], a["nu"], hilos=1)
    ruta_f, ruta_p = INT / f"nulo_espacial_{k}.parquet", INT / f"nulo_pers_{k}.npy"
    filas, pers_k = [], []
    if ruta_f.exists() and ruta_p.exists():
        filas = pd.read_parquet(ruta_f).to_dict(orient="records")
        pp = np.load(ruta_p)
        pers_k = [pp[pp[:, 0] == s, 1:] for s in range(len(filas))]
        print(k, "retoma desde", len(filas), flush=True)

    def guardar():
        pd.DataFrame(filas).to_parquet(ruta_f)
        np.save(ruta_p, np.vstack([np.c_[np.full(len(x), s), x] for s, x in enumerate(pers_k)]))

    t = time.time()
    for s in range(len(filas), N_SIM[k]):
        r, isl_s, _ = resumen(simular(gen, np.random.default_rng([semilla, s])))
        filas.append(r)
        q = isl_s[np.isfinite(isl_s["d"])]
        pers_k.append(np.c_[q["b"].to_numpy() == 0, q["pers"].to_numpy()])
        if s % 50 == 49:
            guardar()
        if s % 50 == 0 or s < 3:
            print(k, s, f"{time.time() - t:.0f} s", round(r["frac_bajo_en_islas"], 3), r["n_islas"], r["n_b0"], flush=True)
    filas, pers_k = filas[: N_SIM[k]], pers_k[: N_SIM[k]]
    guardar()
    SIM[k] = pd.DataFrame(filas)
    PERS_SIM[k] = np.vstack(pers_k)

# %% [markdown]
# ## Contraste

# %%
SEC = ["n_islas", "n_b0", "pers_total_finita"]


def p_sup(x, o):
    return float((1 + (x >= o).sum()) / (len(x) + 1))


def p_dos(x, o):
    return float(min(1.0, 2 * min(p_sup(x, o), float((1 + (x <= o).sum()) / (len(x) + 1)))))


res = {"rampa_por_franja_100m": RAMPA_TAB.round(3).to_dict(), "criterios": {"ajuste": f"correlograma simulado a ±{AJUSTE_TOL} del observado hasta {AJUSTE_LAG * 100} m",
                     "principal": "p <= 0.05 y exceso >= 5 puntos sobre la mediana del nulo (N2)",
                     "por_isla": "BH FDR 5% por clase con p contra persistencias nulas agrupadas; estricto: "
                                 "persistencia > P97.5 del máximo por réplica de su clase"},
       "observado": obs, "ajuste": AJ, "n_sim": N_SIM}
for k, d in SIM.items():
    x = d["frac_bajo_en_islas"].to_numpy()
    med = float(np.median(x))
    res[k] = {
        "frac_bajo_en_islas": {"observado": obs["frac_bajo_en_islas"], "mediana_nulo": med,
                               "p2_5": float(np.quantile(x, 0.025)), "p97_5": float(np.quantile(x, 0.975)),
                               "p": p_sup(x, obs["frac_bajo_en_islas"]),
                               "exceso_puntos": (obs["frac_bajo_en_islas"] - med) * 100},
        "exceso_personas": obs["psin_bajo_en_islas"] - float(d["psin_bajo_en_islas"].median()),
        "exceso_personas_b0": obs["psin_bajo_en_islas_b0"] - float(d["psin_bajo_en_islas_b0"].median()),
        "exceso_personas_bpos": obs["psin_bajo_en_islas_bpos"] - float(d["psin_bajo_en_islas_bpos"].median()),
        "secundarios": {s: {"observado": obs[s], "mediana_nulo": float(d[s].median()),
                            "p2_5": float(d[s].quantile(0.025)), "p97_5": float(d[s].quantile(0.975)),
                            "p_dos_colas": p_dos(d[s].to_numpy(), obs[s])} for s in SEC},
        "corte_pers_b0": float(d["max_pers_b0"].quantile(0.975)),
        "corte_pers_bpos": float(d["max_pers_bpos"].quantile(0.975)),
    }
    fr = res[k]["frac_bajo_en_islas"]
    res[k]["estructura"] = bool(fr["p"] <= 0.05 and fr["exceso_puntos"] >= 5)
    if not AJ[k]["ajuste_ok"]:
        res[k]["nota"] = "ajuste fuera de tolerancia: resultado descriptivo"

# Significancia por isla (N2) y cruce con las estables ante capacidad (notebook 34)
fin = np.isfinite(ISL["d"].to_numpy())
b0 = (ISL["b"] == 0).to_numpy()
corte = np.where(b0, res["N2"]["corte_pers_b0"], res["N2"]["corte_pers_bpos"])
ISL["significativa_max"] = fin & (ISL["pers"].to_numpy() > corte)


def bh(p, q=0.05):
    o = np.argsort(p)
    ok = p[o] <= q * np.arange(1, len(p) + 1) / len(p)
    out = np.zeros(len(p), bool)
    if ok.any():
        out[o[: np.flatnonzero(ok).max() + 1]] = True
    return out


ISL["p_isla"] = np.nan
ISL["significativa"] = False
PS = PERS_SIM["N2"]
for clase in (True, False):
    m = fin & (b0 == clase)
    nul = np.sort(PS[PS[:, 0] == clase, 1])
    pv = (1 + len(nul) - np.searchsorted(nul, ISL.loc[m, "pers"].to_numpy(), side="left")) / (len(nul) + 1)
    ISL.loc[m, "p_isla"] = pv
    ISL.loc[m, "significativa"] = bh(pv)
ISL["psin_bajo"] = PB_ISL
estc = pd.read_parquet(INT / "islas_acceso_calle.parquet")
estc = estc[estc["estable"] & (estc["tipo"] != "resto de región")].reset_index(drop=True)
ISL["estable"] = ISL["celda"].isin(estc["celda"])
assert ISL["estable"].sum() == len(estc)
g = ISL.assign(clase=np.where(~fin, "esencial", np.where(b0, "b0", "bpos")))
res["por_isla_N2"] = {
    cl: {"islas": int(len(t)), "significativas": int(t["significativa"].sum()),
         "significativas_max": int(t["significativa_max"].sum()),
         "estables_y_significativas_max": int((t["estable"] & t["significativa_max"]).sum()),
         "estables": int(t["estable"].sum()), "estables_y_significativas": int((t["estable"] & t["significativa"]).sum()),
         "psin_bajo": float(t["psin_bajo"].sum()),
         "psin_bajo_estables_y_significativas": float(t.loc[t["estable"] & t["significativa"], "psin_bajo"].sum())}
    for cl, t in g.groupby("clase")}
res["por_isla_N2"]["nota"] = ("psin_bajo por territorio propio en la partición de todas las islas; puede diferir "
                              "de persistencia_calle.json, que parte solo entre las estables")
print(json.dumps({k: v for k, v in res.items() if k != "ajuste"}, indent=1, ensure_ascii=False))
ISL[["celda", "b", "d", "pers", "p_isla", "significativa", "significativa_max", "estable", "psin_bajo"]].to_parquet(INT / "islas_nulo_calle.parquet")
f4.guardar_json(res, SALIDA / "nulo_espacial.json")

# %% [markdown]
# ## Figura

# %%
fig = plt.figure(figsize=(15, 8))
gs = fig.add_gridspec(2, 2, width_ratios=[1, 1.5])
for i, k in enumerate(["N2", "N1"]):
    ax = fig.add_subplot(gs[i, 0])
    x = SIM[k]["frac_bajo_en_islas"] * 100
    ax.hist(x, bins=40, color=ve.GRIS, lw=0)
    ax.axvline(obs["frac_bajo_en_islas"] * 100, c=ve.NARANJA, lw=2)
    ax.set_title({"N2": "N2 (principal): ceros fijos + gradiente urbano",
                  "N1": "N1 (referencia): estacionario"}[k], fontsize=10.5, loc="left")
    ax.set_xlabel("% de la gente con acceso bajo dentro de cuencas de islas")
    ax.set_ylabel("simulaciones")
    fr = res[k]["frac_bajo_en_islas"]
    ax.text(0.02, 0.95, f"observado {fr['observado'] * 100:.0f}%  ·  nulo {fr['mediana_nulo'] * 100:.0f}%  ·  p = {fr['p']:.3f}",
            transform=ax.transAxes, va="top", fontsize=9.5)
ax = fig.add_subplot(gs[:, 1])
RAS = rej.ras
base = np.full(RAS.shape, np.nan)
base[RAS >= 0] = np.where(F[RAS[RAS >= 0]] < UMBRAL_B, 1.0, 0.0)
ax.imshow(base, origin="lower", cmap=plt.matplotlib.colors.ListedColormap(["#e6e5e0", "#c9c7bf"]), interpolation="nearest")
col, fil = rej.col, rej.fil
nb = res["N2"]["secundarios"]
for t, color, nom in [(ISL[ISL["estable"] & (ISL["b"] > 0)], ve.NARANJA, "Estable, nace con acceso > 0 (aquí está el exceso sobre el nulo)"),
                      (ISL[ISL["estable"] & (ISL["b"] == 0)], ve.AZUL, "Estable, nace en 0 (sin unidad alcanzable)")]:
    ax.scatter(col[t["celda"]] + 1, fil[t["celda"]] + 1, s=7, c=color, lw=0, label=nom)
ax.legend(handles=ax.get_legend_handles_labels()[0] + [Patch(color="#c9c7bf")],
          labels=ax.get_legend_handles_labels()[1] + ["Acceso bajo (f < 0.5)"], loc="lower left", fontsize=9)
ax.set_axis_off()
ax.set_aspect("equal")
ax.set_xlim(col.min() - 5, col.max() + 7)
ax.set_ylim(fil.min() - 5, fil.max() + 7)
ve.titulo(fig, "¿Las islas de acceso bajo son estructura o relieve aleatorio?",
          "Izquierda: la fracción en cuencas no supera al nulo. Derecha: mínimos de las islas estables por clase de "
          f"nacimiento; ninguna isla es más profunda que el azar (BH 5%), pero hay {obs['n_islas']} islas contra "
          f"{nb['n_islas']['mediana_nulo']:.0f} en el nulo.")
fig.subplots_adjust(top=0.86, hspace=0.45)
ve.guardar(fig, FIG / "nulo_espacial.png")
