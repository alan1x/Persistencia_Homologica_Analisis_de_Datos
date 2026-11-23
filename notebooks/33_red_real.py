# %% [markdown]
# # 33 — Distancias por calle (fase F6 de `PLAN_ACCESO.md`, parte A: caminata)
#
# Hasta F5 la distancia era la línea recta, con cuenca de 1,667 m (30 min a 4.5 km/h con
# rodeo de 1.35). Aquí se mide por la red peatonal de OpenStreetMap, con cuenca de 2,250 m
# de calle (los mismos 30 min) y se repiten F3, F4 y F5.
#
# **Distancia celda–unidad:** anclaje de la unidad a su nodo + camino más corto + anclaje de
# la celda. Solo se ancla a componentes de la red con ≥ 1,000 nodos.
#
# **Pasos pesados (con caché, para poder reanudar):**
# 1. Descargar `mexico-latest.osm.pbf` de Geofabrik a `Datos/OSM/`.
# 2. Extraer las vías caminables de CDMX y EDOMEX → `outputs/intermedios/red_peatonal.npz`.
# 3. Dijkstra local desde las 1,290 unidades y los ~13 mil candidatos de F5 →
#    `outputs/intermedios/pares_red_*.parquet`.
#
# ## Criterios fijados antes de correr
#
# - **Rodeo:** el 1.35 es válido si la mediana de (distancia por calle ÷ recta), en pares
#   a ≥ 300 m en línea recta, cae entre 1.25 y 1.45.
# - **Robustez:** las conclusiones se sostienen si (a) ≥ 80% de las personas con acceso bajo
#   en línea recta siguen con acceso bajo por calle y (b) ≥ 80% de las islas estables de F4
#   tienen una isla por calle con su mínimo a ≤ 500 m. Si no, la versión por calle pasa a
#   ser la principal.
# - **F5:** brecha con K = 20 (capacidad nueva = mediana y percentil 75 de las actuales;
#   14 y 40 personas con DENUE). Se reportan los sitios que se repiten a
#   ≤ 500 m y cuánto rinden por calle los sitios elegidos en línea recta frente a los
#   elegidos por calle.
# - **Celdas sin calle cerca:** las que quedan a > 300 m de la red se cuentan y se reportan.

# %%
import heapq
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
from pyproj import Transformer
from scipy.sparse import csgraph
from scipy.spatial import cKDTree
from scipy.stats import spearmanr

from lib import acceso, config, f4, red_peatonal as rp, viz_eval as ve

ve.aplicar()
T0 = time.time()
INT = config.INTERMEDIOS_DIR
SALIDA = config.OUTPUTS_DIR / "auditoria"
FIG = config.FIGURAS_DIR
PRUEBA = os.environ.get("RED_PRUEBA")  # ruta a un .npz sintético para probar sin descargar
SUF = "_prueba" if PRUEBA else ""
LIM = 30 * 4500 / 60  # 2,250 m de calle = 30 min
RECTA = 2 * acceso.RADIO_15  # 1,667 m
UMBRAL, K = 0.5, 20


def reloj(msg):
    print(f"[{(time.time() - T0) / 60:5.1f} min] {msg}", flush=True)


c = pd.read_parquet(INT / "acceso_e2sfca_celdas.parquet")
o = acceso.oferta()
XY, PSIN = c[["x", "y"]].to_numpy(), c["psin"].to_numpy()
N = len(c)
PESO = PSIN * np.where(c["alta_marg"].to_numpy(bool), 2.0, 1.0)
F0 = c["acceso_rel"].to_numpy()
PROM = o["cap"].sum() / PSIN.sum()
FXY = o[["x", "y"]].to_numpy()

# Candidatos de F5, construidos igual que en el notebook 32
isl0 = pd.read_parquet(INT / "islas_acceso.parquet")
est0 = isl0[isl0["estable"] & (isl0["tipo"] != "resto de región")].reset_index(drop=True)
nodo = np.isclose(c["x"] % 500, 0) & np.isclose(c["y"] % 500, 0)
CXY = np.unique(np.vstack([XY[nodo], est0[["x", "y"]].to_numpy()]), axis=0)

# %% [markdown]
# ## 1–3. Red y pares (pesado; con caché)

# %%
ruta_red = Path(PRUEBA) if PRUEBA else INT / "red_peatonal.npz"
m = 3000  # margen de 3 km alrededor de las celdas y las unidades
todo = np.vstack([XY, FXY])
lon, lat = Transformer.from_crs(config.CRS_METROS, config.CRS_GEO, always_xy=True).transform(
    [todo[:, 0].min() - m, todo[:, 0].max() + m], [todo[:, 1].min() - m, todo[:, 1].max() + m])
BBOX = (lon[0], lat[0], lon[1], lat[1])
RUTA_PBF = config.DATOS_DIR / "OSM" / "mexico-latest.osm.pbf"
# Identidad del PBF (tamaño y fecha) + reglas + caja: si cambia cualquiera, se vuelve a extraer.
ID_PBF = (RUTA_PBF.stat().st_size, int(RUTA_PBF.stat().st_mtime)) if RUTA_PBF.exists() else None
HRED = rp.huella(rp.huella_reglas(BBOX), ID_PBF)
# La red guardada solo se usa si se extrajo con las mismas reglas y la misma caja.
def _huella_guardada(ruta):
    with np.load(ruta) as zz:
        return str(zz["huella"]) if "huella" in zz.files else ""


vigente = ruta_red.exists() and (bool(PRUEBA) or _huella_guardada(ruta_red) == HRED)
if not vigente:
    pbf = rp.descargar_pbf(RUTA_PBF)
    reloj("PBF listo")
    xy_red, u, v, largo = rp.extraer_red(pbf, BBOX)
    np.savez_compressed(ruta_red, xy=xy_red, u=u, v=v, largo=largo, huella=HRED)
    reloj("red extraída")
z = np.load(ruta_red)
red = rp.Red(z["xy"], z["u"], z["v"], z["largo"])
HGRAFO = rp.huella(z["xy"], z["u"], z["v"], z["largo"])  # identidad del grafo efectivo (también en pruebas)
reloj("red cargada")


def pares_cache(nombre, fxy):
    """Pares por calle con caché. La huella cubre red, celdas, fuentes (en orden) y cuenca:
    si algo cambia, se recalcula en vez de reutilizar distancias de otra configuración."""
    ruta = INT / f"pares_red_{nombre}{SUF}.parquet"
    ruta_h = ruta.with_suffix(".huella")
    h = rp.huella(HGRAFO, XY, np.asarray(fxy, float), LIM)
    if ruta.exists() and ruta_h.exists() and ruta_h.read_text() == h:
        p = pd.read_parquet(ruta)
        return p["i"].to_numpy(), p["j"].to_numpy(), p["d"].to_numpy()
    reloj(f"Dijkstra desde {len(fxy):,} {nombre}")
    i, j, d, anc = red.pares(XY, fxy, LIM)
    pd.DataFrame({"i": i.astype(np.int32), "j": j.astype(np.int32), "d": d.astype(np.float32)}).to_parquet(ruta)
    np.save(INT / f"anclaje_celdas{SUF}.npy", anc)
    ruta_h.write_text(h)
    return i, j, d


Iu, Ju, Du = pares_cache("unidades", FXY)
Ic, Jc, Dc = pares_cache("candidatos", CXY)
ANC = np.load(INT / f"anclaje_celdas{SUF}.npy")
reloj("pares listos")

# %% [markdown]
# ## Rodeo real frente al 1.35

# %%
lon_c, _ = Transformer.from_crs(config.CRS_METROS, config.CRS_GEO, always_xy=True).transform(XY[:, 0], XY[:, 1])
ZONA = np.where(c["region"] == "CDMX", "CDMX", np.where(lon_c < -99.3, "EDOMEX poniente (Toluca)", "EDOMEX resto"))
recta_u = np.hypot(*(XY[Iu] - FXY[Ju]).T)
lejos = recta_u >= 300
rodeo_cens = Du[lejos] / recta_u[lejos]  # censurado: solo pares que ya caben en 2,250 m de calle

# Rodeo sin censura: la muestra se elige por distancia en recta (300–1,667 m) y la distancia
# por calle se mide sin corte. Así no se excluyen por construcción los rodeos grandes.
rng_r = np.random.default_rng(33)
cel_nodo, _ = red.anclar(XY)
fue_nodo, fue_anc = red.anclar(FXY)
arbol_c = cKDTree(XY)
rq, cq, zq = [], [], []
UQ = rng_r.choice(len(FXY), 200, replace=False)
uq = []
for j in UQ:
    cel = np.asarray(arbol_c.query_ball_point(FXY[j], RECTA), dtype=int)
    rr = np.hypot(*(XY[cel] - FXY[j]).T)
    cel, rr = cel[(rr >= 300) & (PSIN[cel] > 0)], rr[(rr >= 300) & (PSIN[cel] > 0)]
    dist = csgraph.dijkstra(red.G, directed=False, indices=fue_nodo[j])  # sin límite
    rq.append(rr)
    uq.append(np.full(len(rr), j))
    cq.append(dist[cel_nodo[cel]] + ANC[cel] + fue_anc[j])
    zq.append(ZONA[cel])
rq, cq, zq, uq = np.concatenate(rq), np.concatenate(cq), np.concatenate(zq), np.concatenate(uq)
conec = np.isfinite(cq)
fuera_calle_pct = float((cq > LIM).mean() * 100)  # incluye pares sin camino
rodeo = cq[conec] / rq[conec]  # solo pares conectados; la desconexión se reporta aparte
rq, zq, uq, cq = rq[conec], zq[conec], uq[conec], cq[conec]
med_unidad = pd.Series(rodeo).groupby(uq).median()
bandas = [300, 600, 1000, 1400, RECTA]
res = {
    "red": {"nodos": int(len(z["xy"])), "aristas": int(len(z["u"]))},
    "anclaje": {"celdas_mas_300m": int((ANC > 300).sum()), "psin_mas_300m": float(PSIN[ANC > 300].sum()),
                "mediana_m": float(np.median(ANC))},
    "rodeo": {"muestra": "200 unidades al azar; celdas pobladas a 300–1,667 m en recta; Dijkstra sin límite",
              "pares_conectados": int(len(rq)), "sin_camino_pct": float((~conec).mean() * 100),
              "mediana_de_medianas_por_unidad": float(med_unidad.median()),
              "mediana": float(np.median(rodeo)), "p25": float(np.percentile(rodeo, 25)),
              "p75": float(np.percentile(rodeo, 75)), "p90": float(np.percentile(rodeo, 90)),
              "por_banda_recta_m": {f"{a:.0f}-{b:.0f}": float(np.median(rodeo[(rq >= a) & (rq < b)]))
                                    for a, b in zip(bandas[:-1], bandas[1:])},
              "por_zona": {zn: float(np.median(rodeo[zq == zn])) for zn in np.unique(ZONA)},
              "valido_1_35": bool(1.25 <= np.median(rodeo) <= 1.45),
              # Con el supuesto 1.35 estos pares caben en la cuenca (recta <= 1,667 m); ¿cuántos no
              # caben por calle (> 2,250 m)?
              "en_cuenca_recta_fuera_por_calle_pct": fuera_calle_pct,
              "censurado_referencia": {"mediana": float(np.median(rodeo_cens)),
                                       "nota": "pares que ya caben en 2,250 m de calle; sesgado a la baja"}},
}
print(json.dumps(res, indent=1, ensure_ascii=False))

# %% [markdown]
# ## F3 por calle

# %%
Wu = acceso.peso(Du, LIM)
A, _ = acceso.e2sfca_pares(Iu, Ju, Wu, PSIN, o["cap"].to_numpy(float), N)
F1 = A / PROM
b0, b1 = F0 < UMBRAL, F1 < UMBRAL
sin1 = np.bincount(Iu, minlength=N) == 0
pob = PSIN > 0
res["f3"] = {
    "spearman": float(spearmanr(F0[pob], F1[pob]).statistic),
    "psin_bajo_recta": float(PSIN[b0].sum()), "psin_bajo_calle": float(PSIN[b1].sum()),
    "siguen_bajo_pct": float(PSIN[b0 & b1].sum() / PSIN[b0].sum() * 100),
    "nuevos_bajo": float(PSIN[~b0 & b1].sum()), "salen_bajo": float(PSIN[b0 & ~b1].sum()),
    "psin_sin_acceso_calle": float(PSIN[sin1].sum()),
    "por_region": {r: {"pct_bajo_recta": float(PSIN[b0 & (c["region"] == r)].sum() / PSIN[c["region"] == r].sum() * 100),
                       "pct_bajo_calle": float(PSIN[b1 & (c["region"] == r)].sum() / PSIN[c["region"] == r].sum() * 100)}
                   for r in ["CDMX", "EDOMEX"]},
}
print(json.dumps(res["f3"], indent=1))

# %% [markdown]
# ## F4 por calle
#
# Se hace completa en el notebook 34 (cuencas, estabilidad por Jaccard y comparación con la
# recta). La regla original de este notebook (≥ 80% de islas a ≤ 500 m) dependía de un mínimo
# arbitrario en las mesetas de ceros; quedó reemplazada (decisión en `PLAN_ACCESO.md`, F6).

# %% [markdown]
# ## Comparación de F5: voraz de brecha con los candidatos de la recta
#
# No es la salida principal de F5 por calle: esa es `optimizacion_calle.json` (notebook 32
# con `DISTANCIA=calle`, candidatos de las islas por calle). Aquí solo se mide cuánto rinden
# por calle los sitios elegidos en recta frente a un voraz por calle con los mismos candidatos.

# %%
M = len(CXY)
o_c = np.argsort(Jc, kind="stable")
Ic, Jc, Dc = Ic[o_c], Jc[o_c], Dc[o_c]
Wc = acceso.peso(Dc, LIM)
PTR = np.searchsorted(Jc, np.arange(M + 1))
DEN = np.bincount(Jc, weights=PSIN[Ic] * Wc, minlength=M)


def voraz_brecha(f0, delta, k):
    f = f0.copy()

    def contrib(s):
        fi = f[Ic[s]]
        return PESO[Ic[s]] * (np.maximum(0, UMBRAL - fi) - np.maximum(0, UMBRAL - fi - delta[s]))

    g = np.bincount(Jc, weights=contrib(slice(0, len(Ic))), minlength=M)
    heap = [(-v, j) for j, v in enumerate(g) if v > 0]
    heapq.heapify(heap)
    sel = []
    while len(sel) < k and heap:
        _, j = heapq.heappop(heap)
        s = slice(PTR[j], PTR[j + 1])
        v = contrib(s).sum()
        if not heap or v >= -heap[0][0]:
            sel.append(j)
            np.add.at(f, Ic[s], delta[s])
        else:
            heapq.heappush(heap, (-v, j))
    return sel


def brecha(f0, delta, sel):
    s = np.concatenate([np.arange(PTR[j], PTR[j + 1]) for j in sel])
    f = f0 + np.bincount(Ic[s], weights=delta[s], minlength=N)
    return float((PESO * np.maximum(0, UMBRAL - f)).sum())


sitios0 = pd.read_csv(SALIDA / "optimizacion_sitios.csv")
s0 = sitios0[(sitios0["objetivo"] == "brecha") & (sitios0["orden"] <= K)][["x", "y"]].to_numpy()
idx0 = cKDTree(CXY).query(s0)[1]  # sitios elegidos en línea recta (capacidad mediana)
base = float((PESO * np.maximum(0, UMBRAL - F1)).sum())
res["f5"] = {"brecha_base_calle": base}
# Unidad nueva: mediana de las actuales; grande: percentil 75 (14 y 40 personas con DENUE).
CAP_N, CAP_G = float(o["cap"].median()), float(o["cap"].quantile(0.75))
for nombre, cap in [("mediana", CAP_N), ("p75", CAP_G)]:
    delta = cap / np.maximum(DEN[Jc], 1e-9) * Wc / PROM
    sel = voraz_brecha(F1, delta, K)
    r = {"capacidad": cap, "reduccion_calle_optimo": 1 - brecha(F1, delta, sel) / base}
    if nombre == "mediana":
        r["reduccion_calle_con_sitios_recta"] = 1 - brecha(F1, delta, idx0) / base
        r["sitios_iguales_500m"] = int((cKDTree(CXY[sel]).query(s0)[0] <= 500).sum())
        SEL14 = sel
    res["f5"][f"cap_{nombre}"] = r
print(json.dumps(res["f5"], indent=1))
res["minutos"] = (time.time() - T0) / 60
f4.guardar_json(res, SALIDA / f"red_real{SUF}.json")
c[["x", "y"]].assign(acceso_rel_calle=F1, anclaje=ANC).to_parquet(INT / f"acceso_calle{SUF}.parquet")

# %% [markdown]
# ## Figura

# %%
fig, (ax, ah) = plt.subplots(1, 2, figsize=(15, 7.5), gridspec_kw={"width_ratios": [1.5, 1]})
CLASES = [("Acceso bajo en ambas", b0 & b1, "#c9c7bf"), ("Solo por calle (nuevo bajo)", ~b0 & b1, ve.NARANJA),
          ("Solo en línea recta (sale de bajo)", b0 & ~b1, ve.AZUL)]
ax.scatter(XY[~b0 & ~b1, 0], XY[~b0 & ~b1, 1], s=0.15, c="#ecebe6", lw=0, rasterized=True)
for nom, m, col in CLASES:
    ax.scatter(XY[m, 0], XY[m, 1], s=0.3, c=col, lw=0, rasterized=True, label=f"{nom}: {PSIN[m].sum() / 1000:,.0f} mil")
ax.scatter(*CXY[SEL14].T, s=40, c=ve.TEXTO, edgecolor=ve.FONDO, lw=1, zorder=3, label="Sitios de la brecha por calle (K = 20)")
ax.set_aspect("equal")
ax.set_axis_off()
from matplotlib.lines import Line2D
hs = [Line2D([], [], ls="", marker="s", ms=7, c=col, label=f"{nom}: {PSIN[m].sum() / 1000:,.0f} mil") for nom, m, col in CLASES]
hs.append(Line2D([], [], ls="", marker="o", ms=7, c=ve.TEXTO, label="Sitios de la brecha por calle (K = 20)"))
ax.legend(handles=hs, loc="lower left", fontsize=8.5, frameon=False)
ah.hist(np.clip(rodeo, 1, 3), bins=80, color=ve.AZUL, alpha=0.85)
ah.axvline(1.35, c=ve.TEXTO, lw=1, ls="--")
ah.annotate("1.35 supuesto", (1.35, ah.get_ylim()[1] * 0.92), xytext=(-6, 0), textcoords="offset points", fontsize=9, ha="right")
ah.axvline(np.median(rodeo), c=ve.NARANJA, lw=1.5)
ah.annotate(f"mediana real {np.median(rodeo):.2f}", (np.median(rodeo), ah.get_ylim()[1] * 0.82), xytext=(6, 0),
            textcoords="offset points", fontsize=9)
ah.set_xlabel("Calle ÷ línea recta (pares a ≥ 300 m)")
ah.set_ylabel("Pares celda–unidad")
ah.set_title("Rodeo real", fontsize=10.5)
ve.titulo(fig, "Acceso medido por calle frente a línea recta",
          f"Red peatonal de OpenStreetMap, cuenca de 2,250 m de calle (30 min). "
          f"{res['f3']['siguen_bajo_pct']:.0f}% de las personas con acceso bajo en línea recta siguen igual por calle.")
fig.subplots_adjust(top=0.84)
ve.guardar(fig, FIG / f"red_real{SUF}.png")
reloj("listo")
