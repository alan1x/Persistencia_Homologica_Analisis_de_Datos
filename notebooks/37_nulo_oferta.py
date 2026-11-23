# %% [markdown]
# # 37 — Nulo de la oferta: ¿la ubicación actual de las unidades deja más gente con acceso bajo?
#
# El notebook 36 mostró que la profundidad de las islas no supera a un relieve aleatorio, pero
# que hay muchas más islas que nacen con acceso > 0 (bolsas entre unidades). Aquí la pregunta
# es de política: **dada la misma oferta (mismas unidades, mismas capacidades, mismo número
# por municipio), ¿la ubicación actual deja más gente con acceso bajo que una regla simple?**
#
# ## Diseño
#
# - **Sitios:** los nodos de 500 m con población de F5 (12,922), con pares por calle ya
#   calculados (cuenca de 2,250 m). No se usan los mínimos de islas como sitios: salen del f
#   observado.
# - **Observado comparable:** cada unidad real se mueve a su nodo más cercano de su municipio
#   (mediana 200 m) y se recalcula E2SFCA sumando capacidad por nodo. Las réplicas se comparan
#   contra este observado redondeado, no contra el real; el efecto del redondeo se reporta.
# - **S1, principal (regla que sigue la demanda):** cada unidad conserva capacidad y municipio
#   y cae en un nodo de su municipio con probabilidad ∝ personas sin seguro a ≤ 1,125 m por
#   calle del nodo. 999 réplicas.
# - **S2, referencia (regla ciega):** igual, pero uniforme entre los nodos del municipio.
#   200 réplicas.
# - **S1 con oferta abierta (sensibilidad):** sin las unidades de seguridad social
#   (`acceso.oferta(abierta=True)`, 1,149 unidades, 76% de la capacidad), con su propio
#   observado redondeado y su propio promedio. 200 réplicas.
# - Varias unidades pueden caer en el mismo nodo (se suma la capacidad, que en E2SFCA es
#   equivalente). Se reporta cuántos nodos distintos se ocupan, en el observado y en el nulo.
# - Pendiente: estratos de macrozonas en lugar de municipios.
# - La normalización es el promedio metropolitano (capacidad total / demanda total), igual en
#   todas las réplicas, así que el umbral f < 0.5 es el mismo.
#
# ## Criterios fijados antes de correr
#
# - **Principal (único confirmatorio):** personas sin seguro con f < 0.5. Una cola,
#   p = (1 + #{S1 ≥ obs}) / (n + 1). La ubicación actual es **peor que la regla** si p ≤ 0.05 y
#   el exceso sobre la mediana de S1 es ≥ 100 mil personas (~3% de la gente con acceso bajo).
#   Simétrico para **mejor**; si no, **compatible**. Se reporta el percentil del observado.
# - **Discretización:** si el cambio por redondeo (real → nodo) es de magnitud parecida a la
#   distancia entre el observado y el P95, el veredicto se marca como dependiente del redondeo.
# - **Secundarios** (percentil y p de dos colas): personas con f = 0, brecha
#   Σ psin·max(0, 0.5 − f), islas con b = 0 y con b > 0, fracción de la gente con acceso bajo en
#   cuencas de islas.
# - **Mapa:** "acceso bajo atribuible a la ubicación" = celdas con f < 0.5 en el observado
#   redondeado y en menos del 20% de las réplicas de S1. Se reporta cuánta gente es.

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
from scipy.spatial import cKDTree

from lib import acceso, config, f4, topo_rejilla as tr, viz_eval as ve
from lib.f4 import UMBRAL_B, UMBRAL_P, TOPE

ve.aplicar()
INT = config.INTERMEDIOS_DIR
SALIDA = config.OUTPUTS_DIR / "auditoria"
FIG = config.FIGURAS_DIR
N_SIM = {"S1": int(os.environ.get("N_SIM1", 999)), "S2": int(os.environ.get("N_SIM2", 200)),
         "S1_abierta": int(os.environ.get("N_SIM3", 200))}
CUENCA, R15 = 30 * 4500 / 60, 15 * 4500 / 60
ATRIB = 0.2
DIF_MIN = 100_000

c = pd.read_parquet(INT / "acceso_e2sfca_celdas.parquet", columns=["x", "y", "psin", "CVEGEO"])
F_REAL = pd.read_parquet(INT / "acceso_calle.parquet")["acceso_rel_calle"].to_numpy()
XY, PSIN = c[["x", "y"]].to_numpy(), c["psin"].to_numpy()
N = len(c)

pc = pd.read_parquet(INT / "pares_red_candidatos_calle.parquet")
I, J, D = pc["i"].to_numpy(), pc["j"].to_numpy(), pc["d"].to_numpy(float)
W = acceso.peso(D, CUENCA)
M = int(J.max()) + 1
CXY = pc.drop_duplicates("j").sort_values("j")[["cx", "cy"]].to_numpy()
assert len(CXY) == M
NODO = np.isclose(CXY[:, 0] % 500, 0) & np.isclose(CXY[:, 1] % 500, 0)
arbol = cKDTree(XY)
MUN_C = c["CVEGEO"].str[:5].to_numpy()
MUN_NODO = MUN_C[arbol.query(CXY)[1]]
DEM15 = np.bincount(J[D <= R15], PSIN[I[D <= R15]], M)


class Oferta:
    """Unidades, su municipio, su nodo redondeado y los grupos (unidades, nodos) por municipio."""

    def __init__(self, o):
        self.o, self.cap = o, o["cap"].to_numpy(float)
        self.prom = self.cap.sum() / PSIN.sum()
        mun = MUN_C[arbol.query(o[["x", "y"]].to_numpy())[1]]
        self.snap, self.dsnap, self.grupos = np.empty(len(o), int), np.empty(len(o)), []
        for m in np.unique(mun):
            cand = np.flatnonzero(NODO & (MUN_NODO == m))
            if len(cand) == 0:  # regla fijada: municipio sin nodos -> todos los nodos
                cand = np.flatnonzero(NODO)
            u = np.flatnonzero(mun == m)
            d, k = cKDTree(CXY[cand]).query(o[["x", "y"]].to_numpy()[u])
            self.snap[u], self.dsnap[u] = cand[k], d
            self.grupos.append((u, cand))

    def acceso(self, sitio):
        A, _ = acceso.e2sfca_pares(I, J, W, PSIN, np.bincount(sitio, self.cap, M), N)
        return A / self.prom

    def sortear(self, rng, pesos):
        sitio = np.empty(len(self.o), int)
        for u, nodos in self.grupos:
            p = None if pesos is None else pesos[nodos] / pesos[nodos].sum()
            sitio[u] = rng.choice(nodos, size=len(u), p=p)
        return sitio


OF = {"base": Oferta(acceso.oferta())}
if acceso.fuente_oferta() == "denue":  # con CLUES la oferta ya es "abierta" (F8.1)
    OF["abierta"] = Oferta(acceso.oferta(abierta=True))
print(f"nodos: {NODO.sum()}, desplazamiento mediano {np.median(OF['base'].dsnap):.0f} m")

rej = tr.Rejilla(c["x"], c["y"], acceso.PASO)
act = rej.activa
reg_pob, _ = ndimage.label(rej.ras >= 0, structure=np.ones((3, 3)))
REG = np.zeros(N, int)
REG[act] = reg_pob[rej.fr[act], rej.cr[act]]


def resumen(f, sitio=None):
    pares, _, cu = rej.h0(f, cuencas=True, umbral_b=UMBRAL_B, umbral_p=UMBRAL_P, tope=TOPE)
    isl = tr.islas(pares, UMBRAL_B, UMBRAL_P).reset_index(drop=True)
    cuen = f4.lista_cuencas(isl, cu)
    reg = pd.Series(REG[isl["celda"]])
    fin = np.isfinite(isl["d"].to_numpy())
    keep = fin | (reg.map(reg.value_counts()).to_numpy() == 1)
    isl = isl[keep].reset_index(drop=True)
    asig = tr.particion([cuen[k] for k in np.flatnonzero(keep)], N)
    bajo = f < UMBRAL_B
    pb = PSIN * bajo
    fin = np.isfinite(isl["d"].to_numpy())
    b0 = (isl["b"] == 0).to_numpy()
    out = {"psin_bajo": float(pb.sum()), "psin_cero": float(PSIN[f == 0].sum()),
           "brecha": float((PSIN * np.maximum(0, UMBRAL_B - f)).sum()),
           "n_islas": len(isl), "n_b0": int((fin & b0).sum()), "n_bpos": int((fin & ~b0).sum()),
           "n_esenciales": int((~fin).sum()),
           "frac_bajo_en_islas": float(pb[asig >= 0].sum() / max(pb.sum(), 1e-9))}
    if sitio is not None:
        out["nodos_ocupados"] = int(len(np.unique(sitio)))
    return out


OBS = {k: resumen(of.acceso(of.snap), of.snap) for k, of in OF.items()}
F_OBS = OF["base"].acceso(OF["base"].snap)
real = resumen(F_REAL)
print("observado redondeado", OBS["base"])
print("real", real)


# %% [markdown]
# ## Réplicas (con puntos de control cada 50)

# %%
SIM, FREC_BAJO = {}, {}
ESC = {"S1": ("base", DEM15 + 1e-9, 371), "S2": ("base", None, 372), "S1_abierta": ("abierta", DEM15 + 1e-9, 373)}
ESC = {k: v for k, v in ESC.items() if v[0] in OF}
SUF = acceso.sufijo_oferta()  # puntos de control separados por fuente de oferta
for k, (nof, pesos, semilla) in ESC.items():
    of = OF[nof]
    ruta_f, ruta_b = INT / f"nulo_oferta_{k}{SUF}.parquet", INT / f"nulo_oferta_bajo_{k}{SUF}.npy"
    filas, cuenta = [], np.zeros(N, np.int32)
    if ruta_f.exists() and ruta_b.exists():
        filas, cuenta = pd.read_parquet(ruta_f).to_dict(orient="records"), np.load(ruta_b)
        print(k, "retoma desde", len(filas), flush=True)

    def guardar():
        pd.DataFrame(filas).to_parquet(ruta_f)
        np.save(ruta_b, cuenta)

    t = time.time()
    for s in range(len(filas), N_SIM[k]):
        sitio = of.sortear(np.random.default_rng([semilla, s]), pesos)
        f = of.acceso(sitio)
        filas.append(resumen(f, sitio))
        cuenta += f < UMBRAL_B
        if s % 50 == 49:
            guardar()
        if s % 50 == 0 or s < 3:
            r = filas[-1]
            print(k, s, f"{time.time() - t:.0f} s", round(r["psin_bajo"]), r["n_bpos"], r["n_b0"], flush=True)
    guardar()
    SIM[k] = pd.DataFrame(filas)
    FREC_BAJO[k] = cuenta / len(filas)

# %% [markdown]
# ## Contraste

# %%
VARS = ["psin_bajo", "psin_cero", "brecha", "n_b0", "n_bpos", "n_islas", "frac_bajo_en_islas", "nodos_ocupados"]


def contraste(x, o_):
    x = np.asarray(x)
    sup, inf = (1 + (x >= o_).sum()) / (len(x) + 1), (1 + (x <= o_).sum()) / (len(x) + 1)
    return {"observado": o_, "mediana_nulo": float(np.median(x)), "p5": float(np.quantile(x, 0.05)),
            "p95": float(np.quantile(x, 0.95)), "percentil_observado": float((x < o_).mean() * 100),
            "p_superior": float(sup), "p_inferior": float(inf), "p_dos_colas": float(min(1.0, 2 * min(sup, inf)))}


res = {"criterios": {"principal": f"una cola p <= 0.05 y diferencia >= {DIF_MIN} personas frente a la mediana de S1",
                     "atribuible": f"f < 0.5 en el observado y en < {ATRIB:.0%} de las réplicas de S1"},
       "redondeo": {"desplazamiento_mediano_m": float(np.median(OF["base"].dsnap)), "desplazamiento_p90_m": float(np.quantile(OF["base"].dsnap, 0.9)),
                    "real": real, "redondeado": OBS["base"], "abierta_redondeado": OBS.get("abierta"),
                    "jaccard_bajo_real_vs_redondeado": float(((F_REAL < 0.5) & (F_OBS < 0.5)).sum()
                                                             / ((F_REAL < 0.5) | (F_OBS < 0.5)).sum())},
       "n_sim": N_SIM}
for k, d in SIM.items():
    ob = OBS[ESC[k][0]]
    res[k] = {v: contraste(d[v], ob[v]) for v in VARS}
    p = res[k]["psin_bajo"]
    dif = ob["psin_bajo"] - p["mediana_nulo"]
    res[k]["exceso_psin_bajo"] = dif
    res[k]["veredicto"] = ("peor" if p["p_superior"] <= 0.05 and dif >= DIF_MIN else
                           "mejor" if p["p_inferior"] <= 0.05 and -dif >= DIF_MIN else "compatible")
cambio_redondeo = OBS["base"]["psin_bajo"] - real["psin_bajo"]
dist_p95 = OBS["base"]["psin_bajo"] - res["S1"]["psin_bajo"]["p95"]
res["redondeo"]["cambio_psin_bajo"] = cambio_redondeo
res["redondeo"]["distancia_obs_a_p95_S1"] = dist_p95
res["redondeo"]["veredicto_depende_del_redondeo"] = bool(abs(cambio_redondeo) >= 0.5 * abs(dist_p95))
obs = OBS["base"]

bajo_obs = F_OBS < UMBRAL_B
atrib = bajo_obs & (FREC_BAJO["S1"] < ATRIB)
estruct = bajo_obs & (FREC_BAJO["S1"] >= 0.8)
res["atribuible_ubicacion"] = {"psin": float(PSIN[atrib].sum()), "pct_del_bajo": float(PSIN[atrib].sum() / PSIN[bajo_obs].sum() * 100),
                               "psin_bajo_en_80pct_o_mas_de_replicas": float(PSIN[estruct].sum())}
print(json.dumps({k: v for k, v in res.items() if k != "redondeo"}, indent=1, ensure_ascii=False))
f4.guardar_json(res, SALIDA / "nulo_oferta.json")
np.save(INT / f"nulo_oferta_frec_bajo_S1{SUF}.npy", FREC_BAJO["S1"])

# %% [markdown]
# ## Figura

# %%
fig = plt.figure(figsize=(15, 8))
gs = fig.add_gridspec(2, 2, width_ratios=[1, 1.5])
for i, (v, nom, esc) in enumerate([("psin_bajo", "Personas sin seguro con acceso bajo (millones)", 1e6),
                                   ("n_bpos", "Islas que nacen con acceso > 0", 1)]):
    ax = fig.add_subplot(gs[i, 0])
    for k, col in [("S1", ve.GRIS), ("S2", ve.AZUL)]:
        ax.hist(SIM[k][v] / esc, bins=40, color=col, alpha=0.6 if k == "S2" else 1, lw=0,
                label={"S1": "S1: sigue la demanda", "S2": "S2: uniforme"}[k])
    ax.axvline(obs[v] / esc, c=ve.NARANJA, lw=2, label="Ubicación actual")
    ax.set_title(nom, fontsize=10.5, loc="left")
    ax.set_ylabel("réplicas")
    if i == 0:
        ax.legend(fontsize=9, frameon=False)
ax = fig.add_subplot(gs[:, 1])
RAS = rej.ras
v = np.full(N, np.nan)
v[bajo_obs] = 1.0
v[atrib] = 2.0
img = np.full(RAS.shape, np.nan)
img[RAS >= 0] = v[RAS[RAS >= 0]]
ax.imshow(np.where(np.isnan(img) & (RAS >= 0), 0.0, img), origin="lower", interpolation="nearest",
          cmap=plt.matplotlib.colors.ListedColormap(["#e6e5e0", "#c9c7bf", ve.NARANJA]), vmin=0, vmax=2)
ax.legend(handles=[Patch(color=ve.NARANJA), Patch(color="#c9c7bf")],
          labels=[f"Acceso bajo atribuible a la ubicación ({res['atribuible_ubicacion']['psin'] / 1e3:,.0f} mil)",
                  "Acceso bajo también con la regla"], loc="lower left", fontsize=9)
ax.set_axis_off()
ax.set_aspect("equal")
r1 = res["S1"]["psin_bajo"]
ve.titulo(fig, "¿La ubicación actual de las unidades deja más gente con acceso bajo que una regla simple?",
          f"Misma oferta y mismo número de unidades por municipio. Actual: {obs['psin_bajo'] / 1e6:.2f} M con acceso bajo; "
          f"regla que sigue la demanda: {r1['mediana_nulo'] / 1e6:.2f} M (percentil del actual: {r1['percentil_observado']:.0f}).")
fig.subplots_adjust(top=0.86, hspace=0.4)
ve.guardar(fig, FIG / "nulo_oferta.png")
