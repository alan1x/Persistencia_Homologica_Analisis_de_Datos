"""Construcción de complejos simpliciales y persistencia homológica (Fases 2-3)."""
import gudhi
import numpy as np
from ripser import ripser


def alpha_complex(puntos, max_alpha_square=None):
    """Construye un Alpha complex (Gudhi) sobre puntos 2D proyectados.

    El valor de filtración alpha es el radio² (m²) del circuncentro.
    max_alpha_square acota la filtración para enfocar escalas relevantes
    y limitar el costo de la persistencia.
    """
    ac = gudhi.AlphaComplex(points=puntos)
    if max_alpha_square is None:
        st = ac.create_simplex_tree()
    else:
        st = ac.create_simplex_tree(max_alpha_square=max_alpha_square)
    return st


def persistencia(simplex_tree):
    """Calcula persistencia y devuelve dict dim -> array (n,2) de (nacimiento, muerte)."""
    simplex_tree.compute_persistence()
    diags = {}
    for dim in (0, 1, 2):
        intervals = simplex_tree.persistence_intervals_in_dimension(dim)
        diags[dim] = np.asarray(intervals) if len(intervals) else np.empty((0, 2))
    return diags


def a_radio(diags):
    """Convierte diagramas en alpha (radio²) a radio en metros (sqrt)."""
    out = {}
    for dim, d in diags.items():
        if len(d) == 0:
            out[dim] = d
            continue
        r = np.sqrt(np.clip(d, 0, None))
        out[dim] = r
    return out


def resumen(diags):
    """Resumen numérico: nº de clases y persistencia máxima por dimensión."""
    res = {}
    for dim, d in diags.items():
        if len(d) == 0:
            res[dim] = {"n": 0, "max_pers": 0.0}
            continue
        finite = d[np.isfinite(d[:, 1])]
        pers = (finite[:, 1] - finite[:, 0]) if len(finite) else np.array([0.0])
        res[dim] = {"n": int(len(d)), "max_pers": float(pers.max()) if len(pers) else 0.0}
    return res


def rips_submuestra(puntos, n=500, seed=0, maxdim=1, thresh=None):
    """Vietoris-Rips sobre una submuestra (didáctico: contraste con Alpha).

    Devuelve los diagramas de ripser. thresh acota el radio máximo (m).
    """
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(puntos), size=min(n, len(puntos)), replace=False)
    sub = puntos[idx]
    kwargs = {"maxdim": maxdim}
    if thresh is not None:
        kwargs["thresh"] = thresh
    res = ripser(sub, **kwargs)
    return res["dgms"], sub
