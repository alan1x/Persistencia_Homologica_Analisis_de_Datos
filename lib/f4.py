"""Piezas comunes de F4 (persistencia H0 del acceso) para recta (nb 31) y calle (nb 34).

- Extensión de una isla = su cuenca (ver `Rejilla.h0(cuencas=True)`), no la etiqueta de
  entrada del union-find, que dejaba fuera las subcuencas fundidas en la isla.
- Estabilidad: en cada réplica se emparejan las cuencas observadas con las de la réplica
  (Jaccard, uno a uno). Una isla aparece si su pareja tiene J >= 0.5. No depende de dónde cae
  el mínimo dentro de una meseta de ceros.
"""
import json
import math

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from lib import acceso, topo_rejilla as tr

UMBRAL_B, UMBRAL_P, TOPE = 0.5, 0.25, 1.0
N_REP, ESTABLE, J_MIN, RADIO_MATCH = 100, 0.8, 0.5, 500.0
RANGOS = {"0 a 5 personas": (1, 5), "6 a 10 personas": (6, 10), "11 a 30 personas": (11, 30),
          "31 a 50 personas": (31, 50), "51 a 100 personas": (51, 100), "101 a 250 personas": (101, 250),
          "251 y más personas": (251, 350)}


def lista_cuencas(isl, cuen):
    """Cuenca de cada fila de `isl` (vacía para las esenciales que contienen el mínimo de otra
    isla de la lista: son el "resto de región")."""
    mins = set(isl["celda"].tolist())
    out = []
    for c, d in zip(isl["celda"], isl["d"]):
        m = cuen.get(c, np.array([], int))
        if not np.isfinite(d) and (mins & set(m.tolist())) - {c}:
            m = np.array([], int)
        out.append(m)
    return out


def replicas_capacidad(I, J, W, psin, o, n_rep=N_REP, semilla=31):
    """Acceso relativo en cada réplica que sortea la capacidad en el rango de `per_ocu`."""
    rng = np.random.default_rng(semilla)
    lo = o["per_ocu"].map(lambda s: RANGOS[s][0]).to_numpy()
    hi = o["per_ocu"].map(lambda s: RANGOS[s][1]).to_numpy()
    for _ in range(n_rep):
        cap = rng.integers(lo, hi + 1).astype(float)
        A, _ = acceso.e2sfca_pares(I, J, W, psin, cap, len(psin))
        yield A / (cap.sum() / psin.sum())


def estabilidad(rej, xy, isl, cuen_obs, replicas):
    """Frecuencia de aparición de cada isla en las réplicas.

    Devuelve DataFrame con `frecuencia` (pareja con J >= J_MIN), `frecuencia_dist` (alguna isla
    a <= 500 m, el criterio anterior) y `j_medio`; y la lista de islas por réplica.
    """
    n = len(isl)
    ap_j, ap_d, j_sum, n_isl = np.zeros(n), np.zeros(n), np.zeros(n), []
    pts = xy[isl["celda"].to_numpy()]
    for k, f in enumerate(replicas):
        p, _, cu = rej.h0(f, cuencas=True, umbral_b=UMBRAL_B, umbral_p=UMBRAL_P, tope=TOPE)
        ir = tr.islas(p, UMBRAL_B, UMBRAL_P)
        n_isl.append(len(ir))
        Jm, fil, col, _ = tr.jaccard_emparejado(cuen_obs, lista_cuencas(ir, cu), rej.n, umbral=J_MIN)
        mejor = np.zeros(n)
        mejor[fil] = Jm[fil, col]
        ap_j += mejor >= J_MIN
        j_sum += mejor
        # <= 500 m (cKDTree excluye el borde con distance_upper_bound, por eso + 1e-6)
        d = cKDTree(xy[ir["celda"].to_numpy()]).query(pts, distance_upper_bound=RADIO_MATCH + 1e-6)[0]
        ap_d += np.isfinite(d)
        if k % 20 == 0:
            print(k, len(ir), flush=True)
    r = len(n_isl)
    return pd.DataFrame({"frecuencia": ap_j / r, "frecuencia_dist": ap_d / r, "j_medio": j_sum / r},
                        index=isl.index), n_isl


def extension(cuen, psin, bajo, alta, n):
    """Personas por isla en su territorio propio (partición: cuenca más profunda) y en la cuenca
    completa (incluye islas anidadas). Devuelve (DataFrame, asig)."""
    asig = tr.particion(cuen, n)
    k = len(cuen)
    m = asig >= 0
    propio = lambda w: np.bincount(asig[m], w[m], k)
    completo = lambda w: np.array([w[c].sum() for c in cuen])
    df = pd.DataFrame({"psin": propio(psin), "psin_bajo": propio(psin * bajo),
                       "psin_marg_alta": propio(psin * alta), "celdas": np.bincount(asig[m], minlength=k),
                       "psin_bajo_cuenca": completo(psin * bajo), "celdas_cuenca": [len(c) for c in cuen]})
    return df, asig


def limpiar(o):
    """NaN e inf a null para que el JSON sea estándar."""
    if isinstance(o, dict):
        return {k: limpiar(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [limpiar(v) for v in o]
    if isinstance(o, (np.floating, float)):
        return None if not math.isfinite(float(o)) else float(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def guardar_json(res, ruta):
    ruta.write_text(json.dumps(limpiar(res), indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
