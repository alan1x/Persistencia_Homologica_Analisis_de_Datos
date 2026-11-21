"""Persistencia H0 por subniveles de una función sobre una rejilla regular (fase F4).

Píxeles con 8 vecinos, como `gudhi.CubicalComplex` con celdas de dimensión máxima.
"""
import numpy as np
import pandas as pd


class Rejilla:
    def __init__(self, x, y, paso):
        x, y = np.asarray(x, float), np.asarray(y, float)
        self.n = len(x)
        self.col = np.rint((x - x.min()) / paso).astype(int)
        self.fil = np.rint((y - y.min()) / paso).astype(int)
        # Puntos fuera de los nodos de la rejilla (AGEB sin nodo) se quedan fuera.
        self.activa = np.isclose(x % paso, 0) & np.isclose(y % paso, 0)
        self.ras = np.full((self.fil.max() + 3, self.col.max() + 3), -1)  # borde vacío de 1 píxel
        self.fr, self.cr = self.fil + 1, self.col + 1
        self.ras[self.fr[self.activa], self.cr[self.activa]] = np.flatnonzero(self.activa)
        vec = np.full((self.n, 8), -1)
        k = 0
        for df in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if df == dc == 0:
                    continue
                vec[self.activa, k] = self.ras[self.fr[self.activa] + df, self.cr[self.activa] + dc]
                k += 1
        self.vecinos = [v[v >= 0].tolist() for v in vec]

    def h0(self, f, cuencas=False, umbral_b=0.5, umbral_p=0.25, tope=1.0):
        """Union-find con regla del más viejo.

        Devuelve (pares, etiqueta): pares = DataFrame con celda del mínimo, b, d (inf si no
        muere) y pers; etiqueta[i] = mínimo de la componente a la que se asignó la celda i.

        Con cuencas=True devuelve además un dict {celda del mínimo: celdas de su cuenca} para
        cada isla (b < umbral_b y d - b >= umbral_p). Cuenca = componente de {f < d} que
        contiene el mínimo, es decir, todo lo que la isla había absorbido justo antes de
        fundirse con una zona más vieja, incluidas subcuencas que no son islas y mesetas
        enteras. Para las esenciales (d = inf) se usa la componente de {f < tope}.
        """
        n = self.n
        orden = np.argsort(f, kind="stable")
        pos = np.empty(n, int)
        pos[orden] = np.arange(n)
        padre = np.full(n, -1)
        etiqueta = np.full(n, -1)
        muerte = {}
        miembros = {}
        cuen = {}
        foto_tope = None

        def raiz(a):
            r = a
            while padre[r] != r:
                r = padre[r]
            while padre[a] != r:
                padre[a], a = r, padre[a]
            return r

        for i in orden[self.activa[orden]]:
            if cuencas and foto_tope is None and f[i] >= tope:
                foto_tope = {r: np.array(m) for r, m in miembros.items() if f[r] < umbral_b}
            rs = {raiz(v) for v in self.vecinos[i] if padre[v] >= 0}
            if not rs:
                padre[i] = etiqueta[i] = i
                if cuencas:
                    miembros[i] = [i]
                continue
            viejo = min(rs, key=pos.__getitem__)
            padre[i] = etiqueta[i] = viejo
            if cuencas:
                miembros[viejo].append(i)
            for r in rs - {viejo}:
                padre[r] = viejo
                muerte[r] = f[i]
                if cuencas:
                    if f[r] < umbral_b and f[i] - f[r] >= umbral_p:
                        cuen[r] = self._conexa(r, np.array(miembros[r]), f, f[i])
                    a, b = miembros.pop(r), miembros[viejo]
                    if len(a) > len(b):
                        a, b = b, a
                    b.extend(a)
                    miembros[viejo] = b
        minimos = np.flatnonzero(etiqueta == np.arange(n))
        d = np.array([muerte.get(m, np.inf) for m in minimos])
        pares = pd.DataFrame({"celda": minimos, "b": f[minimos], "d": d})
        pares["pers"] = pares["d"] - pares["b"]
        if not cuencas:
            return pares, etiqueta
        if foto_tope is None:  # ninguna celda llega a tope
            foto_tope = {r: np.array(m) for r, m in miembros.items() if f[r] < umbral_b}
        for m in minimos[np.isinf(d) & (f[minimos] < umbral_b)]:
            # La componente de {f < tope} que contiene al mínimo es la que tenía como raíz
            # al mínimo esencial cuando el barrido llegó a tope.
            cuen[m] = foto_tope[m]
        return pares, etiqueta, cuen

    def _conexa(self, semilla, miembros, f, nivel):
        """Parte de `miembros` con f < nivel conexa a `semilla` (8 vecinos).

        Si hay empates en el nivel de muerte, otra fusión al mismo nivel puede haber unido
        antes subcuencas que solo se tocan por celdas con f == nivel; al quitarlas quedan
        separadas y no pertenecen a esta cuenca.
        """
        dentro = set(miembros[f[miembros] < nivel].tolist())
        visto, pila = {semilla}, [semilla]
        while pila:
            a = pila.pop()
            for v in self.vecinos[a]:
                if v in dentro and v not in visto:
                    visto.add(v)
                    pila.append(v)
        return np.fromiter(visto, int, len(visto))

    def cuencas(self, f, isl, tope=1.0):
        """Cuencas de las islas de `isl` sobre f y partición de las celdas entre ellas.

        Devuelve (asig, cuen): asig[i] = posición en `isl` de la cuenca más profunda (la más
        chica) que contiene la celda i, o -1. Así cada celda cuenta una vez y la unión es
        asig >= 0. cuen = lista de arreglos de celdas, una por fila de `isl` (vacía si se
        descartó). Las esenciales cuya cuenca contiene el mínimo de otra isla de `isl` se
        descartan: son el "resto de región", no una isla.
        """
        _, _, todas = self.h0(f, cuencas=True, tope=tope)
        celdas, ds = isl["celda"].to_numpy(), isl["d"].to_numpy(float)
        mins = set(celdas.tolist())
        cuen = []
        for c, d in zip(celdas, ds):
            m = todas.get(c, np.array([], int))
            if not np.isfinite(d) and len(mins & set(m.tolist()) - {c}):
                m = np.array([], int)
            cuen.append(m)
        return particion(cuen, self.n), cuen

    def en_cuencas(self, f, isl, tope=1.0):
        """Para cada celda, ¿cae dentro de la cuenca de alguna isla de `isl`?"""
        return self.cuencas(f, isl, tope)[0] >= 0


def particion(cuen, n):
    """asig[i] = índice de la cuenca más chica que contiene la celda i (las cuencas se anidan)."""
    asig = np.full(n, -1)
    for k in np.argsort([-len(m) for m in cuen], kind="stable"):
        asig[cuen[k]] = k
    return asig


def jaccard_emparejado(ca, cb, n, umbral=None):
    """Jaccard entre dos listas de cuencas y emparejamiento uno a uno.

    Sin umbral maximiza la suma de J. Con umbral maximiza primero el número de parejas con
    J >= umbral y desempata por la suma de J (maximizar solo la suma puede cambiar una pareja
    válida por dos parejas débiles). Devuelve (J, filas, cols, resumen); resumen =
    2·ΣJ / (|ca| + |cb|) del emparejamiento sin umbral (1 si coinciden celda por celda).
    """
    from scipy import sparse
    from scipy.optimize import linear_sum_assignment

    def incid(c):
        f = np.concatenate([np.full(len(m), k) for k, m in enumerate(c)]) if c else np.array([], int)
        col = np.concatenate(c) if c else np.array([], int)
        return sparse.csr_matrix((np.ones(len(col)), (f, col)), shape=(len(c), n))

    A, B = incid(ca), incid(cb)
    inter = (A @ B.T).toarray()
    ta, tb = np.array([len(m) for m in ca]), np.array([len(m) for m in cb])
    union = ta[:, None] + tb[None, :] - inter
    J = np.divide(inter, union, out=np.zeros_like(inter, dtype=float), where=union > 0)
    filas, cols = linear_sum_assignment(-J)
    resumen = 2 * J[filas, cols].sum() / max(len(ca) + len(cb), 1)
    if umbral is not None:
        peso = np.where(J >= umbral, (min(J.shape) + 1) + J, 0.0)
        filas, cols = linear_sum_assignment(-peso)
    return J, filas, cols, resumen


def islas(pares, umbral_b=0.5, umbral_p=0.25):
    return pares[(pares["b"] < umbral_b) & (pares["pers"] >= umbral_p)]
