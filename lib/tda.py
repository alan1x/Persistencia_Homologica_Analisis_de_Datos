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


def pesos_desde_per_ocu(df, radio_base=50.0, factor=30.0):
    """Calcula los pesos (radio^2) para el Weighted Alpha Complex.
    
    El radio de la unidad médica crece sublinealmente (sqrt) con el personal ocupado.
    - Consultorio chico (per_ocu=2.5) -> radio_base + factor * sqrt(2.5) ~ 97m
    - Hospital grande (per_ocu=1000)  -> radio_base + factor * sqrt(1000) ~ 998m
    """
    per_ocu = df["per_ocu_num"].fillna(0).values
    radios = radio_base + factor * np.sqrt(per_ocu)
    return radios ** 2


def weighted_alpha_complex(puntos, pesos):
    """Construye un Weighted Alpha complex (Laguerre) con Gudhi.
    
    Requiere que los pesos sean un array de numpy de dimensión 1.
    """
    ac = gudhi.AlphaComplex(points=puntos, weights=pesos)
    st = ac.create_simplex_tree()
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


def ciclos_H1(simplex_tree, puntos_xy, min_persistencia=200.0):
    """Extrae las clases H₁ persistentes usando persistence_pairs() (funciona con Alpha complex).

    Para cada par (birth_simplex, death_simplex) de dimensión 1:
      - birth_simplex = arista [v1, v2] que crea el hueco
      - death_simplex = triángulo [v1, v2, v3] que rellena el hueco
      - centroide = promedio de los 3 vértices del triángulo de muerte

    Devuelve lista de dicts ordenada de mayor a menor persistencia:
        'birth', 'death', 'pers'  → en metros (sqrt del valor alpha)
        'centroide'               → (cx, cy) en metros UTM
        'aristas'                 → array (1, 2, 2) con la arista de nacimiento
    """
    simplex_tree.compute_persistence()
    pairs = simplex_tree.persistence_pairs()

    ciclos = []
    for birth_simplex, death_simplex in pairs:
        # H₁: birth = arista (2 vértices), death = triángulo (3 vértices)
        if len(birth_simplex) != 2 or len(death_simplex) != 3:
            continue

        birth_alpha = simplex_tree.filtration(list(birth_simplex))
        death_alpha = simplex_tree.filtration(list(death_simplex))

        if not np.isfinite(death_alpha):
            continue

        birth_m = float(np.sqrt(max(birth_alpha, 0)))
        death_m = float(np.sqrt(max(death_alpha, 0)))
        pers = death_m - birth_m

        if pers < min_persistencia:
            continue

        # Centroide: promedio de los 3 vértices del triángulo de muerte
        pts_muerte = puntos_xy[list(death_simplex)]
        cx, cy = float(pts_muerte[:, 0].mean()), float(pts_muerte[:, 1].mean())

        # Arista de nacimiento para visualización
        p1, p2 = puntos_xy[birth_simplex[0]], puntos_xy[birth_simplex[1]]

        ciclos.append({
            "birth": birth_m,
            "death": death_m,
            "pers": pers,
            "centroide": (cx, cy),
            "aristas": np.array([[p1, p2]]),
        })

    ciclos.sort(key=lambda c: c["pers"], reverse=True)
    return ciclos


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
