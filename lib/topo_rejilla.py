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

    def h0(self, f):
        """Union-find con regla del más viejo.

        Devuelve (pares, etiqueta): pares = DataFrame con celda del mínimo, b, d (inf si no
        muere) y pers; etiqueta[i] = mínimo de la componente a la que se asignó la celda i.
        """
        n = self.n
        orden = np.argsort(f, kind="stable")
        pos = np.empty(n, int)
        pos[orden] = np.arange(n)
        padre = np.full(n, -1)
        etiqueta = np.full(n, -1)
        muerte = {}

        def raiz(a):
            r = a
            while padre[r] != r:
                r = padre[r]
            while padre[a] != r:
                padre[a], a = r, padre[a]
            return r

        for i in orden[self.activa[orden]]:
            rs = {raiz(v) for v in self.vecinos[i] if padre[v] >= 0}
            if not rs:
                padre[i] = etiqueta[i] = i
                continue
            viejo = min(rs, key=pos.__getitem__)
            padre[i] = etiqueta[i] = viejo
            for r in rs - {viejo}:
                padre[r] = viejo
                muerte[r] = f[i]
        minimos = np.flatnonzero(etiqueta == np.arange(n))
        d = np.array([muerte.get(m, np.inf) for m in minimos])
        pares = pd.DataFrame({"celda": minimos, "b": f[minimos], "d": d})
        pares["pers"] = pares["d"] - pares["b"]
        return pares, etiqueta


    def en_cuencas(self, f, isl, tope=1.0):
        """Para cada celda, ¿cae dentro de la cuenca de alguna isla de `isl`?

        Cuenca = componente de {f < d} que contiene el mínimo de la isla: su territorio justo
        antes de fusionarse. Para islas esenciales se usa {f < tope}, y se descartan si esa
        cuenca contiene el mínimo de otra isla (son el "resto de región", no una isla).
        Sirve para comparar islas cuando el mínimo cae en una meseta (p. ej. acceso = 0) y su
        ubicación exacta es arbitraria.
        """
        from scipy import ndimage

        val = np.full(self.ras.shape, np.inf)
        val[self.ras >= 0] = f[self.ras[self.ras >= 0]]
        cubre = np.zeros(self.ras.shape, bool)
        mins = set(isl["celda"])
        for celda, d in zip(isl["celda"], isl["d"]):
            lab, _ = ndimage.label(val < (d if np.isfinite(d) else tope), structure=np.ones((3, 3)))
            k = lab[self.fr[celda], self.cr[celda]]
            if k == 0:
                continue
            reg = lab == k
            if not np.isfinite(d) and any(reg[self.fr[m], self.cr[m]] for m in mins - {celda}):
                continue
            cubre |= reg
        out = np.zeros(self.n, bool)
        out[self.activa] = cubre[self.fr[self.activa], self.cr[self.activa]]
        return out


def islas(pares, umbral_b=0.5, umbral_p=0.25):
    return pares[(pares["b"] < umbral_b) & (pares["pers"] >= umbral_p)]
