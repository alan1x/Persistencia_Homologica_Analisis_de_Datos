# %% [markdown]
# # 32 — Dónde abrir unidades nuevas: varios objetivos (fase F5 de `PLAN_ACCESO.md`)
#
# Se agregan K unidades públicas de primer nivel a las 1,290 actuales, que se quedan fijas.
#
# - **Capacidad de cada unidad nueva:** la mediana de las actuales (14 personas ocupadas).
# - **Peso de cada persona sin seguro:** ×2 si su AGEB tiene marginación Alta o Muy alta
#   (CONAPO 2020). Como contraste se corre la brecha sin ese peso.
# - **Candidatos:** nodos poblados de una rejilla de 500 m, más los mínimos de las islas
#   estables de F4 (sin las de tipo "resto de región"). Todos los objetivos eligen de aquí.
#
# ## Objetivos
#
# 1. **Cobertura (MCLP):** personas que hoy no tienen unidad a ≤ 833 m y quedarían con una.
# 2. **p-mediana truncada:** distancia promedio a la unidad más cercana, contando como
#    1,667 m (la cuenca) cualquier distancia mayor.
# 3. **Peor 10%:** el 10% de las personas (ponderadas) con peor acceso hoy. Se maximiza su
#    acceso promedio truncado en 0.5, para que no convenga cargar todo en unas cuantas celdas.
# 4. **Brecha E2SFCA:** Σ peso · max(0, 0.5 − f), con f = acceso relativo al promedio
#    metropolitano actual (fijo, como estándar).
#
# En el E2SFCA la razón de una unidad depende solo de la demanda en su cuenca, así que una
# unidad nueva suma R·w(d) a las celdas cercanas sin cambiar a las demás. Los cuatro
# objetivos son submodulares y se resuelven con el algoritmo voraz perezoso.
#
# ## Criterios fijados antes de correr
#
# - **Principal:** brecha E2SFCA con K = 20.
# - **La brecha "gana"** si con K = 20 reduce la brecha al menos 10% más que la solución del
#   MCLP (en términos relativos) y conserva al menos el 90% de la cobertura del MCLP.
# - **Isla atendida:** el acceso en su mínimo sube 0.25 o más.
# - **Validación:**
#   - MCLP con K = 10 contra el óptimo exacto (PuLP/CBC);
#   - cota superior de cada solución voraz (cota de Minoux: valor + suma de las K mejores
#     ganancias marginales al final);
#   - 200 conjuntos aleatorios de K = 20;
#   - 100 réplicas de la capacidad actual (como en F4), reportando con qué frecuencia
#     reaparece cada sitio de la brecha a ≤ 500 m.
# - **Frontera:** α · p-mediana + (1 − α) · brecha, cada una normalizada por su mejor valor
#   con K = 20, con α de 0 a 1.
#
# ## Versión por calle (`DISTANCIA=calle`)
#
# Desde F6 la versión principal mide por la red peatonal de OSM (decisión en
# `PLAN_ACCESO.md`). Con `DISTANCIA=calle`:
# - se usan el acceso por calle de hoy y las islas estables por calle (notebook 34);
# - la cobertura es ≤ 1,125 m de calle (15 min) y la cuenca, 2,250 m (30 min);
# - los candidatos son los nodos de 500 m más los mínimos de las islas estables por calle,
#   con pares por la red (caché en `pares_red_candidatos_calle.parquet`);
# - las salidas llevan el sufijo `_calle` y se comparan los sitios con los de la recta.
# Los criterios son los mismos.

# %%
import heapq
import json
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pulp
from scipy.spatial import cKDTree

from lib import acceso, config, viz_eval as ve

ve.aplicar()
SALIDA = config.OUTPUTS_DIR / "auditoria"
FIG = config.FIGURAS_DIR
INT = config.INTERMEDIOS_DIR
CALLE = os.environ.get("DISTANCIA", "recta") == "calle"
SUF = "_calle" if CALLE else ""
if CALLE:
    CUENCA, R15 = 30 * 4500 / 60, 15 * 4500 / 60  # 2,250 y 1,125 m de calle
else:
    CUENCA, R15 = 2 * acceso.RADIO_15, acceso.RADIO_15
UMBRAL, K_MAIN, K_MAX, KS = 0.5, 20, 50, [5, 10, 20, 50]
RANGOS = {"0 a 5 personas": (1, 5), "6 a 10 personas": (6, 10), "11 a 30 personas": (11, 30),
          "31 a 50 personas": (31, 50), "51 a 100 personas": (51, 100), "101 a 250 personas": (101, 250),
          "251 y más personas": (251, 350)}

c = pd.read_parquet(INT / "acceso_e2sfca_celdas.parquet")
o = acceso.oferta()
isl = pd.read_parquet(INT / f"islas_acceso{SUF}.parquet")
isl = isl[isl["estable"] & (isl["tipo"] != "resto de región")].reset_index(drop=True)
XY, PSIN = c[["x", "y"]].to_numpy(), c["psin"].to_numpy()
N = len(c)
ALTA = c["alta_marg"].to_numpy(bool)
PESO = PSIN * np.where(ALTA, 2.0, 1.0)
if CALLE:
    F0 = pd.read_parquet(INT / "acceso_calle.parquet")["acceso_rel_calle"].to_numpy()
    pu = pd.read_parquet(INT / "pares_red_unidades.parquet")
    Io, Jo, Do = pu["i"].to_numpy(), pu["j"].to_numpy(), pu["d"].to_numpy(float)
    Wo = acceso.peso(Do, CUENCA)
    D0 = np.full(N, np.inf)
    np.minimum.at(D0, Io, Do)
else:
    F0 = c["acceso_rel"].to_numpy()
    D0 = c["d_min"].to_numpy()
    Io, Jo, Wo = acceso.pares_e2sfca(XY, o[["x", "y"]].to_numpy(), CUENCA)
PROM = o["cap"].sum() / PSIN.sum()
CAP = float(o["cap"].median())
print(f"capacidad nueva: {CAP}, unidades actuales: {len(o)}")

# %% [markdown]
# ## Candidatos y pares candidato–celda

# %%
nodo = np.isclose(c["x"] % 500, 0) & np.isclose(c["y"] % 500, 0)
CXY = np.vstack([XY[nodo], isl[["x", "y"]].to_numpy()])
CXY = np.unique(CXY, axis=0)
M = len(CXY)
if CALLE:
    ruta = INT / "pares_red_candidatos_calle.parquet"
    if not ruta.exists():
        from lib import red_peatonal as rp

        z = np.load(INT / "red_peatonal.npz")
        i_, j_, d_, _ = rp.Red(z["xy"], z["u"], z["v"], z["largo"]).pares(XY, CXY, CUENCA, cada=2000)
        pd.DataFrame({"i": i_.astype(np.int32), "j": j_.astype(np.int32), "d": d_.astype(np.float32),
                      "cx": CXY[j_, 0], "cy": CXY[j_, 1]}).to_parquet(ruta)
    pc = pd.read_parquet(ruta)
    assert np.allclose(pc[["cx", "cy"]].to_numpy(), CXY[pc["j"].to_numpy()])  # mismos candidatos
    I, J, DIST = pc["i"].to_numpy(), pc["j"].to_numpy(), pc["d"].to_numpy(float)
    W = acceso.peso(DIST, CUENCA)
    orden = np.argsort(J, kind="stable")
    I, J, W, DIST = I[orden], J[orden], W[orden], DIST[orden]
else:
    I, J, W = acceso.pares_e2sfca(XY, CXY, CUENCA)
    orden = np.argsort(J, kind="stable")
    I, J, W = I[orden], J[orden], W[orden]
    DIST = np.hypot(*(XY[I] - CXY[J]).T)
PTR = np.searchsorted(J, np.arange(M + 1))
DEN = np.bincount(J, weights=PSIN[I] * W, minlength=M)
DELTA = CAP / np.maximum(DEN[J], 1e-9) * W / PROM  # aumento de f en la celda I por el candidato J
print(f"candidatos: {M}, pares: {len(I):,}")

# Peor 10% de hoy, ponderado
o_f = np.argsort(F0, kind="stable")
S10 = np.zeros(N, bool)
S10[o_f[: np.searchsorted(np.cumsum(PESO[o_f]) / PESO.sum(), 0.10) + 1]] = True


# %% [markdown]
# ## Objetivos y algoritmo voraz

# %%
class Cobertura:
    nombre = "Cobertura (MCLP)"

    def __init__(self, peso=PESO, d0=D0):
        self.peso, self.cub = peso, d0 <= R15

    def contrib(self, s):
        return np.where((DIST[s] <= R15) & ~self.cub[I[s]], self.peso[I[s]], 0.0)

    def aplicar(self, k):
        s = slice(PTR[k], PTR[k + 1])
        self.cub[I[s][DIST[s] <= R15]] = True


class PMediana:
    nombre = "p-mediana"

    def __init__(self, peso=PESO, d0=D0):
        self.peso, self.d = peso, np.minimum(d0, CUENCA)

    def contrib(self, s):
        return self.peso[I[s]] * np.maximum(0, self.d[I[s]] - DIST[s])

    def aplicar(self, k):
        s = slice(PTR[k], PTR[k + 1])
        np.minimum.at(self.d, I[s], DIST[s])


class Brecha:
    nombre = "Brecha E2SFCA"

    def __init__(self, peso=PESO, f0=F0, mascara=None, delta=DELTA):
        self.peso = peso if mascara is None else np.where(mascara, peso, 0.0)
        self.f, self.delta = f0.copy(), delta

    def contrib(self, s):
        f = self.f[I[s]]
        return self.peso[I[s]] * (np.maximum(0, UMBRAL - f) - np.maximum(0, UMBRAL - f - self.delta[s]))

    def aplicar(self, k):
        s = slice(PTR[k], PTR[k + 1])
        np.add.at(self.f, I[s], self.delta[s])


class Peor10(Brecha):
    nombre = "Peor 10%"

    def __init__(self, delta=DELTA):
        super().__init__(mascara=S10, delta=delta)


class Combinado:
    def __init__(self, a, z_pm, z_br):
        self.pm, self.br, self.a, self.z = PMediana(), Brecha(), a, (z_pm, z_br)

    def contrib(self, s):
        return self.a * self.pm.contrib(s) / self.z[0] + (1 - self.a) * self.br.contrib(s) / self.z[1]

    def aplicar(self, k):
        self.pm.aplicar(k)
        self.br.aplicar(k)


def ganancias(obj):
    return np.bincount(J, weights=obj.contrib(slice(0, len(I))), minlength=M)


def voraz(obj, K):
    """Voraz perezoso. Devuelve los sitios, la ganancia acumulada y la cota de Minoux."""
    g = ganancias(obj)
    heap = [(-v, k) for k, v in enumerate(g) if v > 0]
    heapq.heapify(heap)
    sel, total = [], 0.0
    while len(sel) < K and heap:
        _, k = heapq.heappop(heap)
        v = obj.contrib(slice(PTR[k], PTR[k + 1])).sum()
        if not heap or v >= -heap[0][0]:
            sel.append(k)
            total += v
            obj.aplicar(k)
        else:
            heapq.heappush(heap, (-v, k))
    resto = np.sort(ganancias(obj))[::-1][:K]
    return sel, total, total + resto.sum()


# %% [markdown]
# ## Evaluación cruzada

# %%
ISL_CELDA = isl["celda"].to_numpy()


def evaluar(sel, delta=DELTA):
    sel = list(sel)
    s = np.concatenate([np.arange(PTR[k], PTR[k + 1]) for k in sel]) if sel else np.array([], int)
    f = F0 + np.bincount(I[s], weights=delta[s], minlength=N)
    d = np.minimum(D0, CUENCA)
    np.minimum.at(d, I[s], DIST[s])
    cub = D0 <= R15
    nuevo = np.zeros(N, bool)
    nuevo[I[s][DIST[s] <= R15]] = True
    nuevo &= ~cub
    bajo0, bajo1 = F0 < UMBRAL, f < UMBRAL
    return {
        "cobertura_nueva_peso": float(PESO[nuevo].sum()),
        "cobertura_nueva_psin": float(PSIN[nuevo].sum()),
        "distancia_media_m": float((PESO * d).sum() / PESO.sum()),
        "brecha": float((PESO * np.maximum(0, UMBRAL - f)).sum()),
        "peor10_acceso_medio": float((PESO[S10] * np.minimum(f[S10], UMBRAL)).sum() / PESO[S10].sum()),
        "salen_de_bajo_psin": float(PSIN[bajo0 & ~bajo1].sum()),
        "salen_de_bajo_alta_marg_psin": float(PSIN[bajo0 & ~bajo1 & ALTA].sum()),
        "islas_atendidas": int(((f - F0)[ISL_CELDA] >= 0.25).sum()),
    }


BASE = evaluar([])
print(json.dumps(BASE, indent=1))

OBJ = {"cobertura": Cobertura, "pmediana": PMediana, "peor10": Peor10, "brecha": Brecha}
sol, cota = {}, {}
for n, cls in OBJ.items():
    sel, tot, ub = voraz(cls(), K_MAX)
    sol[n] = sel
    sel20, tot20, ub20 = voraz(cls(), K_MAIN)
    assert sel20 == sel[:K_MAIN]
    cota[n] = {"ganancia": tot20, "cota_superior": ub20, "razon": tot20 / ub20}
    print(n, cota[n])

tabla = {n: {K: evaluar(s[:K]) for K in KS} for n, s in sol.items()}
res = {"capacidad_nueva": CAP, "candidatos": M, "linea_base": BASE, "cota_minoux_K20": cota,
       "personas_peor10": float(PSIN[S10].sum()), "islas_estables": len(isl), "evaluacion": tabla}
t20 = pd.DataFrame({n: tabla[n][K_MAIN] for n in sol}).T
print(t20.round(1).to_string())

# %% [markdown]
# ## Criterio principal: ¿gana la brecha frente al MCLP?

# %%
red = {n: 1 - tabla[n][K_MAIN]["brecha"] / BASE["brecha"] for n in sol}
cob_ratio = tabla["brecha"][K_MAIN]["cobertura_nueva_peso"] / tabla["cobertura"][K_MAIN]["cobertura_nueva_peso"]
res["criterio"] = {"reduccion_brecha": red, "brecha_vs_mclp_reduccion_relativa": red["brecha"] / red["cobertura"] - 1,
                   "cobertura_brecha_vs_mclp": cob_ratio,
                   "brecha_gana": bool(red["brecha"] >= 1.10 * red["cobertura"] and cob_ratio >= 0.90)}
print(res["criterio"])

# %% [markdown]
# ## Validación: MCLP exacto (K = 10), aleatorios y réplicas

# %%
m = (DIST <= R15) & (D0[I] > R15) & (PESO[I] > 0)
firmas = pd.DataFrame({"i": I[m], "j": J[m]}).groupby("i")["j"].apply(tuple)
grupo = pd.DataFrame({"firma": firmas.values, "peso": PESO[firmas.index]}).groupby("firma")["peso"].sum()
prob = pulp.LpProblem("mclp", pulp.LpMaximize)
usados = sorted({j for f in grupo.index for j in f})
x = {j: pulp.LpVariable(f"x{j}", cat="Binary") for j in usados}
y = [pulp.LpVariable(f"y{n}", 0, 1) for n in range(len(grupo))]
prob += pulp.lpSum(p * v for p, v in zip(grupo.values, y))
prob += pulp.lpSum(x.values()) == 10
for v, f in zip(y, grupo.index):
    prob += v <= pulp.lpSum(x[j] for j in f)
prob.solve(pulp.PULP_CBC_CMD(msg=False, timeLimit=600))
exacto = pulp.value(prob.objective)
voraz10 = evaluar(sol["cobertura"][:10])["cobertura_nueva_peso"]
res["mclp_exacto_K10"] = {"estado": pulp.LpStatus[prob.status], "exacto": exacto, "voraz": voraz10,
                          "razon": voraz10 / exacto, "firmas": len(grupo)}
print(res["mclp_exacto_K10"])

rng = np.random.default_rng(32)
alea = [1 - evaluar(rng.choice(M, K_MAIN, replace=False))["brecha"] / BASE["brecha"] for _ in range(200)]
res["aleatorio_K20_reduccion_brecha"] = {"media": float(np.mean(alea)), "p95": float(np.percentile(alea, 95)),
                                         "max": float(np.max(alea))}
print(res["aleatorio_K20_reduccion_brecha"])

# Réplicas de la capacidad actual: cambia f de hoy y el promedio de referencia.
lo = o["per_ocu"].map(lambda s: RANGOS[s][0]).to_numpy()
hi = o["per_ocu"].map(lambda s: RANGOS[s][1]).to_numpy()
principal = CXY[sol["brecha"][:K_MAIN]]
arb = cKDTree(principal)
aparece = np.zeros(K_MAIN)
for _ in range(100):
    cap = rng.integers(lo, hi + 1).astype(float)
    prom = cap.sum() / PSIN.sum()
    A, _ = acceso.e2sfca_pares(Io, Jo, Wo, PSIN, cap, N)
    s_rep, _, _ = voraz(Brecha(f0=A / prom, delta=DELTA * PROM / prom), K_MAIN)
    dist = cKDTree(CXY[s_rep]).query(principal)[0]
    aparece += dist <= 500
res["robustez_sitios_brecha"] = {"frecuencia": (aparece / 100).tolist(),
                                 "sitios_en_80pct_o_mas": int((aparece >= 80).sum())}
print(res["robustez_sitios_brecha"])

# Sin el peso de marginación
s_sin, _, _ = voraz(Brecha(peso=PSIN), K_MAIN)
d_sin = cKDTree(CXY[s_sin]).query(principal)[0]
res["brecha_sin_peso_marginacion"] = {"sitios_iguales_500m": int((d_sin <= 500).sum()),
                                      "evaluacion": evaluar(s_sin)}
print(res["brecha_sin_peso_marginacion"]["sitios_iguales_500m"])

# %% [markdown]
# ## Sensibilidad: unidades de 40 personas
#
# Cobertura y p-mediana no dependen de la capacidad, así que eligen los mismos sitios y solo
# cambia su evaluación. Peor 10% y brecha se vuelven a optimizar.

# %%
CAP40 = 40.0
DELTA40 = DELTA * CAP40 / CAP
sol40 = {"cobertura": sol["cobertura"], "pmediana": sol["pmediana"],
         "peor10": voraz(Peor10(delta=DELTA40), K_MAX)[0], "brecha": voraz(Brecha(delta=DELTA40), K_MAX)[0]}
tabla40 = {n: {K: evaluar(s[:K], DELTA40) for K in KS} for n, s in sol40.items()}
mismos = {n: int((cKDTree(CXY[sol40[n][:K_MAIN]]).query(CXY[sol[n][:K_MAIN]])[0] <= 500).sum()) for n in ["peor10", "brecha"]}
red40 = {n: 1 - tabla40[n][K_MAIN]["brecha"] / BASE["brecha"] for n in sol40}
cob40 = tabla40["brecha"][K_MAIN]["cobertura_nueva_peso"] / tabla40["cobertura"][K_MAIN]["cobertura_nueva_peso"]
res["capacidad_40"] = {"evaluacion": tabla40, "sitios_iguales_a_cap14_K20": mismos,
                       "criterio": {"reduccion_brecha": red40, "cobertura_brecha_vs_mclp": cob40,
                                    "brecha_gana": bool(red40["brecha"] >= 1.10 * red40["cobertura"] and cob40 >= 0.90)}}
print(pd.DataFrame({n: tabla40[n][K_MAIN] for n in sol40}).T.round(1).to_string())
print(mismos, res["capacidad_40"]["criterio"])
for n in sol40:
    print(n, [(K, round((1 - tabla40[n][K]["brecha"] / BASE["brecha"]) * 100, 1), round(tabla40[n][K]["salen_de_bajo_psin"] / 1000, 1),
               tabla40[n][K]["islas_atendidas"]) for K in KS])

# %% [markdown]
# ## Frontera eficiencia–equidad (K = 20)

# %%
z_pm, z_br = cota["pmediana"]["ganancia"], cota["brecha"]["ganancia"]
frontera = []
for a in np.round(np.linspace(0, 1, 11), 2):
    s_a, _, _ = voraz(Combinado(a, z_pm, z_br), K_MAIN)
    e = evaluar(s_a)
    frontera.append({"alfa": float(a), "distancia_media_m": e["distancia_media_m"],
                     "reduccion_brecha": 1 - e["brecha"] / BASE["brecha"], "islas_atendidas": e["islas_atendidas"]})
res["frontera_K20"] = frontera
print(pd.DataFrame(frontera).round(3).to_string())

sitios = pd.concat([pd.DataFrame({"objetivo": n, "orden": np.arange(1, K_MAX + 1), "x": CXY[s][:, 0], "y": CXY[s][:, 1]})
                    for n, s in sol.items()], ignore_index=True)
sitios.to_csv(SALIDA / f"optimizacion_sitios{SUF}.csv", index=False)
if CALLE:
    # Sitios por calle frente a los de la recta: cuántos de los K = 20 se repiten a ≤ 500 m.
    s0 = pd.read_csv(SALIDA / "optimizacion_sitios.csv")
    res["sitios_iguales_a_recta_K20_500m"] = {
        n: int((cKDTree(s0.loc[(s0["objetivo"] == n) & (s0["orden"] <= K_MAIN), ["x", "y"]].to_numpy())
                .query(CXY[sol[n][:K_MAIN]])[0] <= 500).sum()) for n in sol}
    print(res["sitios_iguales_a_recta_K20_500m"])
(SALIDA / f"optimizacion{SUF}.json").write_text(json.dumps(res, indent=2, ensure_ascii=False, default=float), encoding="utf-8")

# %% [markdown]
# ## Figuras

# %%
NOMBRE = {"cobertura": "Cobertura (MCLP)", "pmediana": "p-mediana", "peor10": "Peor 10%", "brecha": "Brecha E2SFCA"}
COLOR = {"cobertura": ve.AZUL, "pmediana": ve.GRIS, "peor10": ve.AQUA, "brecha": ve.NARANJA}

fig, axes = plt.subplots(2, 2, figsize=(13, 12.5))
bajo = F0 < UMBRAL
for ax, (n, s) in zip(axes.ravel(), sol.items()):
    ax.scatter(XY[~bajo, 0], XY[~bajo, 1], s=0.15, c="#e6e5e0", lw=0, rasterized=True)
    ax.scatter(XY[bajo, 0], XY[bajo, 1], s=0.15, c="#c9c7bf", lw=0, rasterized=True)
    p = CXY[s[:K_MAIN]]
    ax.scatter(p[:, 0], p[:, 1], s=46, c=ve.NARANJA, edgecolor=ve.FONDO, lw=1.2, zorder=3)
    e = tabla[n][K_MAIN]
    ax.set_title(f"{NOMBRE[n]}\nbrecha −{(1 - e['brecha'] / BASE['brecha']) * 100:.1f}% · "
                 f"{e['salen_de_bajo_psin'] / 1000:,.0f} mil salen de acceso bajo · "
                 f"{e['islas_atendidas']} islas atendidas", fontsize=10)
    ax.set_aspect("equal")
    ax.set_axis_off()
ve.titulo(fig, f"Dónde abrir {K_MAIN} unidades según cada objetivo" + (" (distancias por calle)" if CALLE else ""),
          f"Unidades de {CAP:.0f} personas. Gris oscuro: acceso bajo hoy (f < 0.5). "
          "Personas en marginación Alta o Muy alta pesan ×2.")
fig.subplots_adjust(top=0.86, hspace=0.14, wspace=0.02)
ve.guardar(fig, FIG / f"optimizacion_mapas{SUF}.png")

fig, (a1, a2) = plt.subplots(1, 2, figsize=(14, 6))
fr = pd.DataFrame(frontera)
a1.plot(fr["distancia_media_m"], fr["reduccion_brecha"] * 100, c=ve.TEXTO, lw=1.5, marker="o", ms=5, zorder=2)
for _, r in fr.iloc[[0, 5, 10]].iterrows():
    a1.annotate(f"α = {r['alfa']:g}", (r["distancia_media_m"], r["reduccion_brecha"] * 100), textcoords="offset points",
                xytext=(8, 4), fontsize=9)
for n in sol:
    e = tabla[n][K_MAIN]
    a1.scatter(e["distancia_media_m"], (1 - e["brecha"] / BASE["brecha"]) * 100, s=70, c=COLOR[n], zorder=3,
               edgecolor=ve.FONDO, lw=1.2, label=NOMBRE[n])
a1.set_xlabel(f"Distancia media a la unidad más cercana (m{' por calle' if CALLE else ''}, truncada en {CUENCA:,.0f})")
a1.set_ylabel("Reducción de la brecha (%)")
a1.set_title(f"Frontera con K = {K_MAIN}: α·p-mediana + (1 − α)·brecha", fontsize=10.5)
a1.legend(fontsize=9, frameon=False)
for n in sol:
    a2.plot(KS, [(1 - tabla[n][K]["brecha"] / BASE["brecha"]) * 100 for K in KS], c=COLOR[n], lw=2, marker="o", ms=5,
            label=NOMBRE[n])
a2.axhline(res["aleatorio_K20_reduccion_brecha"]["p95"] * 100, c=ve.TEXTO, lw=0.8, ls=":")
a2.annotate("p95 de 200 conjuntos aleatorios (K = 20)", (5, res["aleatorio_K20_reduccion_brecha"]["p95"] * 100),
            textcoords="offset points", xytext=(0, 4), fontsize=8.5)
a2.set_xscale("log")
a2.set_xticks(KS, [str(k) for k in KS])
a2.set_xlabel("Unidades nuevas K")
a2.set_ylabel("Reducción de la brecha (%)")
a2.set_title("Cuánto cierra la brecha cada objetivo", fontsize=10.5)
a2.legend(fontsize=9, frameon=False)
ve.titulo(fig, "Eficiencia contra equidad al abrir unidades nuevas" + (" (por calle)" if CALLE else ""),
          "Brecha: Σ peso · max(0, 0.5 − acceso relativo). Distancia y brecha ponderadas con ×2 en marginación alta.")
fig.subplots_adjust(top=0.82, wspace=0.25)
ve.guardar(fig, FIG / f"optimizacion_frontera{SUF}.png")

fig, axes = plt.subplots(1, 3, figsize=(16, 5.5))
for ax, (clave, etiqueta) in zip(axes, [("brecha", "Reducción de la brecha (%)"),
                                       ("salen_de_bajo_psin", "Personas que salen de acceso bajo (miles)"),
                                       ("islas_atendidas", f"Islas de F4 atendidas (de {len(isl)})")]):
    for n in sol:
        for tab, ls, cap in [(tabla, "--", CAP), (tabla40, "-", CAP40)]:
            v = [tab[n][K][clave] for K in KS]
            v = [(1 - x / BASE["brecha"]) * 100 for x in v] if clave == "brecha" else (
                [x / 1000 for x in v] if clave == "salen_de_bajo_psin" else v)
            ax.plot(KS, v, c=COLOR[n], ls=ls, lw=2 if ls == "-" else 1.3, marker="o", ms=4,
                    label=f"{NOMBRE[n]} ({cap:.0f})")
    ax.set_xscale("log")
    ax.set_xticks(KS, [str(k) for k in KS])
    ax.set_xlabel("Unidades nuevas K")
    ax.set_title(etiqueta, fontsize=10.5)
axes[0].legend(fontsize=8, frameon=False, ncol=1)
ve.titulo(fig, "Unidades de 40 personas frente a unidades de 14" + (" (por calle)" if CALLE else ""),
          "Línea continua: 40 personas por unidad. Punteada: 14 (la mediana actual). Mismos candidatos y mismos pesos.")
fig.subplots_adjust(top=0.8, wspace=0.22)
ve.guardar(fig, FIG / f"optimizacion_capacidad40{SUF}.png")
