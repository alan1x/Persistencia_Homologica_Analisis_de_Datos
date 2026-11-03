"""Huecos H1 con geometría exacta, para validar y comparar diagramas.

`tda.ciclos_H1` guarda el baricentro del triángulo de muerte, y eso basta para
ubicar un hueco a grandes rasgos. Para seguir un hueco entre dos complejos hacen
falta tres datos más, que aquí sí se conservan:

- la identidad del par (arista de nacimiento, triángulo de muerte);
- el centro exacto del disco vacío (circuncentro del triángulo de muerte);
- el radio de ese disco, que es la muerte y no la persistencia.
"""
import gudhi
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree


def complejo(puntos, pesos=None):
    """Simplex tree de Alpha (pesos=None) o de Alpha ponderado (pesos = radio²)."""
    if pesos is None:
        return gudhi.AlphaComplex(points=puntos).create_simplex_tree()
    return gudhi.AlphaComplex(points=puntos, weights=pesos).create_simplex_tree()


def centro_radical(tri, pesos=None):
    """Centro del disco del triángulo. Con pesos es el centro radical (Laguerre)."""
    origen = tri[0]
    a, b = tri[1] - origen, tri[2] - origen
    wa = 0.0 if pesos is None else pesos[1] - pesos[0]
    wb = 0.0 if pesos is None else pesos[2] - pesos[0]
    M = 2 * np.array([a, b])
    v = np.array([a @ a - wa, b @ b - wb])
    return origen + np.linalg.solve(M, v)


def extraer_huecos(st, puntos, min_pers=200.0, pesos=None):
    """DataFrame con los pares H1 finitos de persistencia >= min_pers (metros).

    Con pesos, la filtración puede ser negativa. `recortado` marca los pares cuyo
    nacimiento se recortó a 0 antes de sacar la raíz, igual que en `ciclos_H1`.
    """
    st.compute_persistence()
    filas = []
    for nac, mue in st.persistence_pairs():
        if len(nac) != 2 or len(mue) != 3:
            continue
        b, d = st.filtration(list(nac)), st.filtration(list(mue))
        if not np.isfinite(d):
            continue
        b_m, d_m = np.sqrt(max(b, 0.0)), np.sqrt(max(d, 0.0))
        if d_m - b_m < min_pers:
            continue
        tri = puntos[list(mue)]
        w = None if pesos is None else pesos[list(mue)]
        cx, cy = centro_radical(tri, w)
        bx, by = tri.mean(axis=0)
        filas.append({
            "par": (tuple(sorted(nac)), tuple(sorted(mue))),
            "birth": b_m, "death": d_m, "pers": d_m - b_m,
            "cx": cx, "cy": cy, "bx": bx, "by": by,
            "recortado": b < 0,
        })
    cols = ["par", "birth", "death", "pers", "cx", "cy", "bx", "by", "recortado"]
    return (pd.DataFrame(filas, columns=cols)
            .sort_values("pers", ascending=False).reset_index(drop=True))


def seguir_hueco(hueco, despues, pares_despues):
    """Compara un hueco original con el diagrama posterior.

    Devuelve (estado, persistencia_residual). La zona del hueco es su disco vacío
    original: cualquier hueco posterior centrado ahí se considera su residuo.

    - intacto: el mismo par de símplices sigue en el diagrama;
    - modificado: el par cambió, pero queda un hueco >= umbral centrado en el disco
      (puede ser menor o mayor: una clínica nueva puede partir un hueco o cambiar sus vecinos);
    - cerrado: dentro del disco ya no queda ningún hueco >= umbral.
    """
    if hueco["par"] in pares_despues:
        return "intacto", hueco["pers"]
    if len(despues) == 0:
        return "cerrado", 0.0
    d = np.hypot(despues["cx"].values - hueco["cx"], despues["cy"].values - hueco["cy"])
    dentro = despues[d < hueco["death"]]
    if len(dentro) == 0:
        return "cerrado", 0.0
    return "modificado", float(dentro["pers"].max())
