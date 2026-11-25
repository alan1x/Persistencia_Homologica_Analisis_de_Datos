# %% [markdown]
# # 41 — ¿Cuántas unidades convienen? (F8.3 de `PLAN_ACCESO.md`)
#
# El notebook 32 elige sitios con K fijo (20). Aquí se trazan las curvas de K = 1 a 500 para
# decir **cuántas** unidades hacen falta y si conviene más abrir nuevas o ampliar las que hay.
# Todo va por calle (versión principal desde F6) y con la oferta CLUES con médicos (F8.1).
#
# ## Soluciones (todas con el voraz perezoso del 32)
#
# 1. **Llegar a los peores (brecha):** Σ peso · max(0, 0.5 − f), con f relativo al promedio
#    metropolitano actual (fijo) y peso ×2 en AGEB de marginación Alta o Muy alta.
# 2. **Cobertura ponderada (MCLP):** gente sin unidad a ≤ 1,125 m de calle que quedaría con una,
#    con el mismo peso ×2 del 32; se reporta también en personas.
# 3. **Mixta:** α · p-mediana + (1 − α) · brecha, normalizadas por su mejor valor con K = 20,
#    como en el 32. **α se fija antes de las curvas:** en la rejilla α = 0, 0.1, …, 1 con
#    K = 20, el α cuyo par (ganancia p-mediana, ganancia brecha), normalizado por el mejor de
#    cada uno, queda más cerca de (1, 1).
# 4. **Ampliar las saturadas (principal de la cuarta opción):** cada paso agrega la misma
#    capacidad a una unidad actual **saturada** (razón médicos / demanda por debajo de la
#    mediana), con **tope de 3 ampliaciones por sede**. En E2SFCA eso sube f en la cuenca de la
#    unidad en CAP · w / demanda, con sus pares por calle. Sensibilidad: ampliar cualquiera,
#    sin tope.
#
# Unidad nueva y ampliación suman la misma capacidad por paso: **CAP = mediana de médicos de
# las unidades actuales** (la del 32). Así, K pasos son K × CAP médicos en ambos casos; la
# diferencia es que la nueva requiere un inmueble. Las candidatas nuevas son las del 32 por
# calle (nodos de 500 m y mínimos de islas estables, `pares_red_candidatos_calle.parquet`).
#
# ## "Cuántas convienen", fijado antes de correr
#
# Para cada solución, sobre su curva de brecha restante:
# - **K de rendimientos decrecientes:** el primer K desde el cual la ganancia marginal en
#   brecha, **promediada en los 10 pasos siguientes**, queda por debajo del **10%** de la del
#   primer paso (sensibilidad: 25%). Es el primer paso de baja ganancia, no el último que se
#   recomienda financiar.
# - **K25 y K50:** el K que reduce la brecha 25% y 50%.
# - **K de prioridad:** el K que saca de acceso bajo (f ≥ 0.5) a la mitad de la gente con
#   prioridad (acceso bajo y marginación Alta o Muy alta, como en el 30b y el 39).
# - El voraz se detiene antes si ya nada gana. Se reporta el K efectivo; si una meta no se
#   alcanza, "> K efectivo" y lo logrado al final.
# - **Abrir frente a ampliar:** se comparan los médicos que cada una necesita para K25 y K50.
#   No se dice cuál "conviene": eso requiere costos de inmueble y de plantilla, que no se
#   tienen. Si ninguna llega, la comparación queda indeterminada.
#
# **Sensibilidad:** curva de brecha con CAP = P75 de las actuales. **Validación:** cota de
# Minoux de la brecha con unidades nuevas en K = 20, 100 y 500.
#
# **Límite:** el promedio metropolitano queda fijo (estándar de hoy). Con 500 unidades la
# oferta crece mucho, así que la curva mide distancia al estándar actual, no al promedio nuevo.
# Se reporta cuánto crece la oferta (médicos agregados / actuales) en cada meta.
#
# *Ajustes tras la crítica de Codex, antes de correr:* K efectivo y metas no alcanzadas
# explícitas; pares celda–sitio únicos; ampliación limitada a saturadas con tope (irrestricta
# como sensibilidad); rendimientos con caída sostenida; MCLP como cobertura ponderada; sin
# veredicto de "conviene"; cota de Minoux en la misma corrida; menos memoria al leer pares.

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

from lib import acceso, config, f4, viz_eval as ve

ve.aplicar()
T0 = time.time()
INT = config.INTERMEDIOS_DIR
SALIDA = config.OUTPUTS_DIR / "auditoria"
FIG = config.FIGURAS_DIR
CUENCA, R15 = 30 * 4500 / 60, 15 * 4500 / 60  # 2,250 y 1,125 m de calle
UMBRAL, K_MAX, K_ALFA = 0.5, 500, 20
FRAC_REND, FRAC_REND_SENS, VENTANA = 0.10, 0.25, 10
TOPE_SEDE = 3
ALFAS = np.round(np.arange(0, 1.01, 0.1), 1)


def reloj(msg):
    print(f"[{(time.time() - T0) / 60:5.1f} min] {msg}", flush=True)


c = pd.read_parquet(INT / "acceso_e2sfca_celdas.parquet")
o = acceso.oferta()
XY, PSIN = c[["x", "y"]].to_numpy(), c["psin"].to_numpy()
N = len(c)
ALTA = c["alta_marg"].to_numpy(bool)
PESO = PSIN * np.where(ALTA, 2.0, 1.0)
CAPS = o["cap"].to_numpy(float)
PROM = CAPS.sum() / PSIN.sum()
CAP, CAP75 = float(np.median(CAPS)), float(np.quantile(CAPS, 0.75))
F0 = pd.read_parquet(INT / "acceso_calle.parquet")["acceso_rel_calle"].to_numpy()

# Pares de las unidades actuales (notebook 33) y comprobación contra el F guardado.
pu = pd.read_parquet(INT / "pares_red_unidades.parquet")
Io, Jo, Do = pu["i"].to_numpy(), pu["j"].to_numpy(), pu["d"].to_numpy(float)
Wo = acceso.peso(Do, CUENCA)
Ao, Ro = acceso.e2sfca_pares(Io, Jo, Wo, PSIN, CAPS, N)
assert np.allclose(Ao / PROM, F0, rtol=1e-4, atol=1e-4)
D0 = np.full(N, np.inf)
np.minimum.at(D0, Io, Do)
PRIOR = (F0 < UMBRAL) & ALTA
print(f"oferta {acceso.fuente_oferta()}: {len(o)} unidades; CAP = {CAP:g} médicos (P75 {CAP75:g}); "
      f"prioridad: {PSIN[PRIOR].sum():,.0f} personas")


class Pares:
    """Pares celda–sitio ordenados por sitio, con el aumento de f por unidad de capacidad."""

    def __init__(self, i, j, w, dist):
        orden = np.argsort(j, kind="stable")
        self.I, self.J, self.W, self.DIST = i[orden], j[orden], w[orden], dist[orden]
        self.M = int(self.J.max()) + 1
        self.PTR = np.searchsorted(self.J, np.arange(self.M + 1))
        den = np.bincount(self.J, weights=PSIN[self.I] * self.W, minlength=self.M)
        self.D1 = self.W / np.maximum(den[self.J], 1e-9) / PROM  # aumento de f por 1 médico

    def tramo(self, k):
        return slice(self.PTR[k], self.PTR[k + 1])


pc = pd.read_parquet(INT / "pares_red_candidatos_calle.parquet", columns=["i", "j", "d"])
for nom, (i_, j_) in {"candidatas": (pc["i"], pc["j"]), "unidades": (pu["i"], pu["j"])}.items():
    assert not pd.DataFrame({"i": i_, "j": j_}).duplicated().any(), f"pares repetidos en {nom}"
dc = pc["d"].to_numpy(float)
NUEVAS = Pares(pc["i"].to_numpy(), pc["j"].to_numpy(), acceso.peso(dc, CUENCA), dc)
del pc, dc
AMPLIA = Pares(Io, Jo, Wo, Do)
# Saturada: razón médicos / demanda ponderada por debajo de la mediana de las unidades actuales.
SATURADA = Ro < np.median(Ro[Ro > 0])
reloj(f"candidatas nuevas: {NUEVAS.M:,}; unidades para ampliar: {AMPLIA.M:,}")

# %% [markdown]
# ## Objetivos y voraz

# %%
class Brecha:
    def __init__(self, P, cap, peso=PESO):
        self.P, self.d, self.peso, self.f = P, P.D1 * cap, peso, F0.copy()

    def contrib(self, s):
        i, f = self.P.I[s], self.f[self.P.I[s]]
        return self.peso[i] * (np.maximum(0, UMBRAL - f) - np.maximum(0, UMBRAL - f - self.d[s]))

    def aplicar(self, k):
        s = self.P.tramo(k)
        self.f[self.P.I[s]] += self.d[s]  # en un sitio cada celda aparece una vez


class Cobertura:
    def __init__(self, P):
        self.P, self.cub = P, D0 <= R15

    def contrib(self, s):
        return np.where((self.P.DIST[s] <= R15) & ~self.cub[self.P.I[s]], PESO[self.P.I[s]], 0.0)

    def aplicar(self, k):
        s = self.P.tramo(k)
        self.cub[self.P.I[s][self.P.DIST[s] <= R15]] = True


class PMediana:
    def __init__(self, P):
        self.P, self.dist = P, np.minimum(D0, CUENCA)

    def contrib(self, s):
        return PESO[self.P.I[s]] * np.maximum(0, self.dist[self.P.I[s]] - self.P.DIST[s])

    def aplicar(self, k):
        s = self.P.tramo(k)
        np.minimum.at(self.dist, self.P.I[s], self.P.DIST[s])


class Mixta:
    def __init__(self, P, a, z_pm, z_br):
        self.pm, self.br, self.a, self.z = PMediana(P), Brecha(P, CAP), a, (z_pm, z_br)

    def contrib(self, s):
        return self.a * self.pm.contrib(s) / self.z[0] + (1 - self.a) * self.br.contrib(s) / self.z[1]

    def aplicar(self, k):
        self.pm.aplicar(k)
        self.br.aplicar(k)


def voraz(obj, P, K, repetir=False, permitidos=None, tope=1, cotas=()):
    """Voraz perezoso. Con `repetir`, un sitio puede elegirse hasta `tope` veces (ampliaciones);
    la ganancia vieja sigue siendo cota superior porque la brecha cerrada es cóncava en f.
    `cotas`: K donde se calcula la cota de Minoux (solo sin repetición) en la misma corrida."""
    g = np.bincount(P.J, weights=obj.contrib(slice(0, len(P.I))), minlength=P.M)
    if permitidos is not None:
        g = np.where(permitidos, g, 0.0)
    heap = [(-v, k) for k, v in enumerate(g) if v > 0]
    heapq.heapify(heap)
    sel, gan, usos, cot = [], [], np.zeros(P.M, int), {}
    while len(sel) < K and heap:
        _, k = heapq.heappop(heap)
        v = obj.contrib(P.tramo(k)).sum()
        if v <= 0:
            continue
        if not heap or v >= -heap[0][0]:
            sel.append(k)
            gan.append(v)
            obj.aplicar(k)
            usos[k] += 1
            if repetir and usos[k] < tope:
                heapq.heappush(heap, (-v, k))
            if len(sel) in cotas and not repetir:
                kk = len(sel)
                gk = np.bincount(P.J, weights=obj.contrib(slice(0, len(P.I))), minlength=P.M)
                gk[usos > 0] = 0.0
                tot = float(np.sum(gan))
                extra = float(np.partition(gk, -kk)[-kk:].sum())
                cot[kk] = {"ganancia": tot, "cota": tot + extra, "razon": tot / (tot + extra)}
        else:
            heapq.heappush(heap, (-v, k))
    return sel, np.array(gan), cot


# %% [markdown]
# ## Seguimiento de las curvas (mismas medidas para todas las soluciones)

# %%
def curva(sel, P, cap):
    """Por paso: brecha restante, gente que sale de acceso bajo, prioridad que sale, cobertura nueva."""
    f, cub = F0.copy(), D0 <= R15
    d = P.D1 * cap
    br = float((PESO * np.maximum(0, UMBRAL - f)).sum())
    filas = []
    sale = sale_p = cob = 0.0
    for paso, k in enumerate(sel, 1):
        s = P.tramo(k)
        i = P.I[s]
        viejo, nuevo = f[i], f[i] + d[s]
        br += float((PESO[i] * (np.maximum(0, UMBRAL - nuevo) - np.maximum(0, UMBRAL - viejo))).sum())
        cruza = (viejo < UMBRAL) & (nuevo >= UMBRAL) & (F0[i] < UMBRAL)
        sale += float(PSIN[i][cruza].sum())
        sale_p += float(PSIN[i][cruza & PRIOR[i]].sum())
        f[i] = nuevo
        if P is NUEVAS:
            nc = i[(P.DIST[s] <= R15) & ~cub[i]]
            cob += float(PSIN[nc].sum())
            cub[nc] = True
        filas.append((paso, br, sale, sale_p, cob))
    return pd.DataFrame(filas, columns=["K", "brecha", "sale_bajo", "sale_prioridad", "cobertura_nueva"])


BR0 = float((PESO * np.maximum(0, UMBRAL - F0)).sum())
PRIOR0 = float(PSIN[PRIOR].sum())

# %% [markdown]
# ## α de la mixta (fijado con K = 20, antes de las curvas)

# %%
s_pm, g_pm, _ = voraz(PMediana(NUEVAS), NUEVAS, K_ALFA)
s_br, g_br, _ = voraz(Brecha(NUEVAS, CAP), NUEVAS, K_ALFA)
Z_PM, Z_BR = g_pm.sum(), g_br.sum()
assert Z_PM > 0 and Z_BR > 0, "sin ganancia con K = 20: la mixta no se puede normalizar"


def gan_pm_br(sel):
    pm, br = PMediana(NUEVAS), Brecha(NUEVAS, CAP)
    a = b = 0.0
    for k in sel:
        a += pm.contrib(NUEVAS.tramo(k)).sum()
        b += br.contrib(NUEVAS.tramo(k)).sum()
        pm.aplicar(k)
        br.aplicar(k)
    return a / Z_PM, b / Z_BR


frontera = []
for a in ALFAS:
    sel, _, _ = voraz(Mixta(NUEVAS, a, Z_PM, Z_BR), NUEVAS, K_ALFA)
    x, y = gan_pm_br(sel)
    frontera.append({"alfa": float(a), "pm_norm": x, "brecha_norm": y, "dist_utopia": float(np.hypot(1 - x, 1 - y))})
frontera = pd.DataFrame(frontera)
ALFA = float(frontera.sort_values(["dist_utopia", "alfa"]).iloc[0]["alfa"])  # empate: el α menor
print(frontera.round(3).to_string())
reloj(f"α de la mixta: {ALFA}")

# %% [markdown]
# ## Curvas de K = 1 a 500

# %%
sol = {}
s_, g_, MINOUX = voraz(Brecha(NUEVAS, CAP), NUEVAS, K_MAX, cotas=(20, 100, 500))
sol["brecha"] = (s_, g_)
reloj("brecha")
sol["mclp"] = voraz(Cobertura(NUEVAS), NUEVAS, K_MAX)[:2]
reloj("MCLP")
sol["mixta"] = voraz(Mixta(NUEVAS, ALFA, Z_PM, Z_BR), NUEVAS, K_MAX)[:2]
reloj("mixta")
sol["ampliar"] = voraz(Brecha(AMPLIA, CAP), AMPLIA, K_MAX, repetir=True, permitidos=SATURADA, tope=TOPE_SEDE)[:2]
reloj("ampliar saturadas")
sol["ampliar_libre"] = voraz(Brecha(AMPLIA, CAP), AMPLIA, K_MAX, repetir=True, tope=K_MAX)[:2]
reloj("ampliar cualquiera")
sol["brecha_p75"] = voraz(Brecha(NUEVAS, CAP75), NUEVAS, K_MAX)[:2]
reloj("brecha con CAP P75")

DEF = {"brecha": (NUEVAS, CAP), "mclp": (NUEVAS, CAP), "mixta": (NUEVAS, CAP),
       "ampliar": (AMPLIA, CAP), "ampliar_libre": (AMPLIA, CAP), "brecha_p75": (NUEVAS, CAP75)}
curvas = {n: curva(sol[n][0], *DEF[n]) for n in sol}


def primer_k(cond):
    k = np.flatnonzero(cond)
    return int(k[0]) + 1 if len(k) else None


def cuantas(n):
    cv, cap = curvas[n], DEF[n][1]
    if not len(cv):
        return {"pasos_efectivos": 0, "nota": "el voraz no encontró ninguna ganancia"}
    red = 1 - cv["brecha"].to_numpy() / BR0
    # Ganancia marginal en brecha medida sobre la curva (igual para todas las soluciones),
    # promediada en los VENTANA pasos siguientes para exigir una caída sostenida.
    marg = -np.diff(np.r_[BR0, cv["brecha"].to_numpy()])
    sost = pd.Series(marg[::-1]).rolling(VENTANA, min_periods=1).mean().to_numpy()[::-1]

    def meta(k):
        return {"k": k if k is not None else f"> {len(cv)}", "alcanzada": k is not None,
                "medicos": k * cap if k is not None else None,
                "oferta_agregada_pct": k * cap / CAPS.sum() * 100 if k is not None else None}

    k20 = min(20, len(cv)) - 1
    return {
        "pasos_efectivos": len(cv), "medicos_por_paso": cap,
        "rendimientos_10pct": meta(primer_k(sost < FRAC_REND * marg[0]) if marg[0] > 0 else None),
        "rendimientos_25pct": meta(primer_k(sost < FRAC_REND_SENS * marg[0]) if marg[0] > 0 else None),
        "brecha_25": meta(primer_k(red >= 0.25)), "brecha_50": meta(primer_k(red >= 0.50)),
        "prioridad_mitad": meta(primer_k(cv["sale_prioridad"].to_numpy() >= 0.5 * PRIOR0)),
        "al_final": {"K": len(cv), "reduccion_brecha": float(red[-1]), "sale_bajo": float(cv["sale_bajo"].iat[-1]),
                     "sale_prioridad": float(cv["sale_prioridad"].iat[-1]),
                     "sale_prioridad_pct": float(cv["sale_prioridad"].iat[-1] / PRIOR0 * 100),
                     "cobertura_nueva_personas": float(cv["cobertura_nueva"].iat[-1]),
                     "oferta_agregada_pct": len(cv) * cap / CAPS.sum() * 100},
        "en_K20": {"K": k20 + 1, "reduccion_brecha": float(red[k20])},
    }


res_k = {n: cuantas(n) for n in sol}
METAS = ["rendimientos_10pct", "rendimientos_25pct", "brecha_25", "brecha_50", "prioridad_mitad"]
print(pd.DataFrame({n: {"pasos": v["pasos_efectivos"], **{m: v[m]["k"] for m in METAS if m in v}}
                    for n, v in res_k.items()}).T.to_string())

# Ampliaciones: cuántas unidades distintas y cuántas saturadas.
amp_sel = np.array(sol["ampliar"][0])
amp = {"unidades_distintas": int(len(np.unique(amp_sel))),
       "max_ampliaciones_una_unidad": int(np.bincount(amp_sel).max()) if len(amp_sel) else 0,
       "pasos_en_saturadas_pct": float(SATURADA[amp_sel].mean() * 100) if len(amp_sel) else float("nan")}
print(amp)


def abrir_vs_ampliar(m):
    a, b = res_k["brecha"].get(m, {}), res_k["ampliar"].get(m, {})
    if not (a.get("alcanzada") or b.get("alcanzada")):
        return {"resultado": "indeterminada: ninguna llega"}
    return {"medicos_abrir": a.get("medicos"), "medicos_ampliar_saturadas": b.get("medicos"),
            "llega_abrir": a.get("alcanzada"), "llega_ampliar": b.get("alcanzada")}


comparacion = {m: abrir_vs_ampliar(m) for m in ("brecha_25", "brecha_50")}
print("abrir frente a ampliar:", comparacion)
minoux = MINOUX
print("Minoux:", minoux)

res = {
    "capacidad": {"cap_mediana": CAP, "cap_p75": CAP75, "unidades_actuales": len(o)},
    "linea_base": {"brecha": BR0, "psin_bajo": float(PSIN[F0 < UMBRAL].sum()), "psin_prioridad": PRIOR0},
    "alfa_mixta": ALFA, "frontera_k20": frontera.round(4).to_dict(orient="records"),
    "cuantas": res_k, "ampliar": amp, "abrir_vs_ampliar": comparacion,
    "minoux_brecha": minoux, "minutos": (time.time() - T0) / 60,
}
f4.guardar_json(res, SALIDA / "cuantas_unidades.json")
pd.concat({n: cv for n, cv in curvas.items()}, names=["solucion"]).reset_index(level=0).to_csv(
    SALIDA / "cuantas_unidades_curvas.csv", index=False)

# %% [markdown]
# ## Sitios elegidos y primer K por cuadro (para las gráficas del video, notebook 44)
#
# - `cuantas_unidades_sitios.csv`: por solución, el orden en que el voraz eligió cada sitio y su
#   coordenada (candidata nueva, o unidad actual en «ampliar»).
# - `cuantas_unidades_celdas.parquet`: por cuadro y solución, el primer K en que sale de acceso
#   bajo y el primer K en que queda con una unidad a ≤ 15 min de calle (−1 = nunca en 500 pasos).
#   Con esto el mapa de cualquier K se pinta sin recalcular.

# %%
_pc = pd.read_parquet(INT / "pares_red_candidatos_calle.parquet", columns=["j", "cx", "cy"]).drop_duplicates("j")
CAND_XY = np.full((NUEVAS.M, 2), np.nan)
CAND_XY[_pc["j"].to_numpy()] = _pc[["cx", "cy"]].to_numpy()
del _pc
VIDEO = ["brecha", "mixta", "mclp", "ampliar"]


def primeros_k(sel, P, cap):
    f, cub = F0.copy(), D0 <= R15
    k_sale = np.full(N, -1, np.int32)
    k_cub = np.full(N, -1, np.int32)
    d = P.D1 * cap
    for paso, k in enumerate(sel, 1):
        s = P.tramo(k)
        i = P.I[s]
        f[i] += d[s]
        nuevo = i[(f[i] >= UMBRAL) & (F0[i] < UMBRAL) & (k_sale[i] < 0)]
        k_sale[nuevo] = paso
        if P is NUEVAS:
            nc = i[(P.DIST[s] <= R15) & ~cub[i]]
            k_cub[nc] = paso
            cub[nc] = True
    return k_sale, k_cub


filas, celdas = [], {}
for n in VIDEO:
    P, cap = DEF[n]
    sel = np.asarray(sol[n][0])
    xy = CAND_XY[sel] if P is NUEVAS else o[["x", "y"]].to_numpy()[sel]
    assert np.isfinite(xy).all()
    if P is NUEVAS:  # una coordenada por sitio, sin repetidos
        assert len(np.unique(sel)) == len(sel) and len(np.unique(xy, axis=0)) == len(sel), n
    else:  # ampliar: tope de 3 por sede
        assert np.bincount(sel).max() <= TOPE_SEDE
    assert len(sel) == len(curvas[n])  # orden 1…K igual a la curva
    filas.append(pd.DataFrame({"solucion": n, "orden": np.arange(1, len(sel) + 1), "candidato_id": sel,
                               "x": xy[:, 0], "y": xy[:, 1], "medicos": cap}))
    ks, kc = primeros_k(sel, P, cap)
    celdas[f"k_sale_{n}"] = ks
    if P is NUEVAS:
        celdas[f"k_cub15_{n}"] = kc
    # Métricas reconstruidas desde el primer K por cuadro = curva, en K = 49 y en los cruces de ¼ y ½.
    cv = curvas[n].set_index("K")
    for K in {49, res_k[n]["brecha_25"]["k"], res_k[n]["brecha_50"]["k"]}:
        if not isinstance(K, (int, np.integer)) or K > len(cv):
            continue
        sale = (ks > 0) & (ks <= K)
        assert np.isclose(PSIN[sale].sum(), cv.at[K, "sale_bajo"], rtol=1e-9), (n, K)
        assert np.isclose(PSIN[sale & PRIOR].sum(), cv.at[K, "sale_prioridad"], rtol=1e-9), (n, K)
        assert cv.at[K, "sale_prioridad"] <= cv.at[K, "sale_bajo"]
        if P is NUEVAS:
            assert np.isclose(PSIN[(kc > 0) & (kc <= K)].sum(), cv.at[K, "cobertura_nueva"], rtol=1e-9), (n, K)
sitios = pd.concat(filas, ignore_index=True)
sitios.to_csv(SALIDA / "cuantas_unidades_sitios.csv", index=False)
pd.DataFrame({"x": c["x"].to_numpy(), "y": c["y"].to_numpy(), **celdas}).to_parquet(
    INT / "cuantas_unidades_celdas.parquet")
print(sitios.groupby("solucion").size().to_dict())

# %% [markdown]
# ## Figura: brecha cerrada y gente que sale de acceso bajo, según K

# %%
ETQ = {"brecha": ("Llegar a los peores (brecha)", ve.AZUL, "-"),
       "mixta": (f"Mixta (α = {ALFA:g})", ve.AQUA, "-"),
       "mclp": ("Cobertura ponderada (MCLP)", ve.GRIS, "-"),
       "ampliar": (f"Ampliar saturadas (≤ {TOPE_SEDE} por sede)", ve.NARANJA, "-"),
       "ampliar_libre": ("Ampliar cualquiera, sin tope", ve.NARANJA, ":"),
       "brecha_p75": (f"Brecha con {CAP75:g} médicos por unidad", ve.AZUL, ":")}
fig, axs = plt.subplots(1, 2, figsize=(15, 6.2))
for n, (et, col, ls) in ETQ.items():
    cv = curvas[n]
    axs[0].plot(cv["K"], (1 - cv["brecha"] / BR0) * 100, color=col, ls=ls, lw=2, label=et)
    axs[1].plot(cv["K"], cv["sale_prioridad"] / PRIOR0 * 100, color=col, ls=ls, lw=2, label=et)
for ax, nivel in ((axs[0], (25, 50)), (axs[1], (50,))):
    for y in nivel:
        ax.axhline(y, color=ve.REJILLA, lw=1, zorder=0)
for n in ("brecha", "ampliar"):
    for clave, y in (("brecha_25", 25), ("brecha_50", 50)):
        k = res_k[n].get(clave, {}).get("k")
        if isinstance(k, (int, np.integer)):
            axs[0].plot(k, y, "o", color=ETQ[n][1], ms=6)
            axs[0].annotate(f"K = {k}", (k, y), textcoords="offset points", xytext=(6, -12), fontsize=8)
axs[0].set_xlabel(f"Pasos K (cada uno suma {CAP:g} médicos; la curva punteada, {CAP75:g})")
axs[0].set_ylabel("Brecha cerrada (%)")
axs[0].set_title("Brecha cerrada según cuántas unidades se agregan", fontsize=10)
axs[0].legend(fontsize=8, frameon=False, loc="upper left")
axs[1].set_xlabel("Pasos K")
axs[1].set_ylabel("Gente con prioridad que sale de acceso bajo (%)")
axs[1].set_title("Prioridad: acceso bajo y marginación Alta o Muy alta", fontsize=10)
for ax in axs:
    ax.set_xlim(0, K_MAX)
    ax.set_ylim(0, None)
kb = res_k["brecha"]
ve.titulo(fig, "¿Cuántas unidades convienen?",
          f"Brecha con unidades nuevas: 25% con K = {kb['brecha_25']['k']}, 50% con K = {kb['brecha_50']['k']}; "
          f"rendimientos decrecientes (ganancia < 10% de la primera) desde K = {kb['rendimientos_10pct']['k']}. "
          f"Por calle, a 30 min.")
fig.subplots_adjust(top=0.83, wspace=0.18)
ve.guardar(fig, FIG / "cuantas_unidades.png")
reloj("listo")
