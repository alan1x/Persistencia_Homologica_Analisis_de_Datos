"""Nulo espacial para F4: campos gaussianos con la autocorrelación de f y su misma distribución.

- `puntajes_normales`: f -> z por rangos (empates al rango medio).
- `correlograma`: correlación de z a lo largo de filas y columnas del ráster, por desfase.
- `matern`: correlación Matérn; `ajustar_mezcla`: mezcla de dos Matérn (corto y largo alcance),
  porque la tendencia urbana deja una cola larga que una sola Matérn no captura.
- `campo`: síntesis espectral por FFT en el ráster con relleno (sin envolver la correlación).
- `a_marginal`: reordena los valores observados según los rangos del campo (cópula gaussiana):
  la distribución de f (incluidos los ceros) queda idéntica, solo cambia dónde cae cada valor.
"""
import numpy as np
from scipy import fft as sfft, optimize, special, stats

DESFASES = np.array([1, 2, 3, 5, 8, 12, 16, 20, 25, 30, 40, 50, 70, 100])  # en celdas


def puntajes_normales(f):
    return stats.norm.ppf((stats.rankdata(f) - 0.5) / len(f))


def correlograma(rej, v, desfases=DESFASES):
    G = np.full(rej.ras.shape, np.nan)
    G[rej.fr[rej.activa], rej.cr[rej.activa]] = v[rej.activa]
    out = []
    for L in desfases:
        a = np.concatenate([G[:, :-L].ravel(), G[:-L, :].ravel()])
        b = np.concatenate([G[:, L:].ravel(), G[L:, :].ravel()])
        m = np.isfinite(a) & np.isfinite(b)
        out.append(np.corrcoef(a[m], b[m])[0, 1])
    return np.array(out)


def matern(h, rho, nu):
    h = np.asarray(h, float)
    if np.isinf(nu):
        return np.exp(-h ** 2 / (2 * rho ** 2))
    u = np.sqrt(2 * nu) * np.maximum(h, 1e-12) / rho
    return 2 ** (1 - nu) / special.gamma(nu) * u ** nu * special.kv(nu, u)


def mezcla(h, w, r1, r2, nu):
    return w * matern(h, r1, nu) + (1 - w) * matern(h, r2, nu)


def ajustar_mezcla(h, r, nu=1.0):
    """Ajusta w, rho1 < rho2 (mismas unidades que h) por mínimos cuadrados."""
    obj = lambda p: ((mezcla(h, p[0], p[1], p[2], nu) - r) ** 2).sum()
    mejor = None
    for r1 in [500, 1000, 2000]:
        for r2 in [5000, 15000, 40000]:
            s = optimize.minimize(obj, [0.7, r1, r2], bounds=[(0.01, 1), (100, 8000), (2000, 2e5)])
            if mejor is None or s.fun < mejor.fun:
                mejor = s
    w, r1, r2 = mejor.x
    return {"w": float(w), "rho1": float(r1), "rho2": float(r2), "nu": nu, "sse": float(mejor.fun)}


def _espectro(forma, paso, rho, nu):
    ky = np.fft.fftfreq(forma[0], paso)
    kx = np.fft.rfftfreq(forma[1], paso)
    k2 = ky[:, None] ** 2 + kx[None, :] ** 2
    if np.isinf(nu):
        s = np.exp(-2 * np.pi ** 2 * rho ** 2 * k2)
    else:
        s = (2 * nu / rho ** 2 + 4 * np.pi ** 2 * k2) ** (-(nu + 1))
    return s / s.sum()


class Generador:
    """Campos con correlación `mezcla(h, w, rho1, rho2, nu)` sobre las celdas activas de `rej`.
    Devuelve z estandarizado sobre las celdas activas."""

    def __init__(self, rej, paso, w, rho1, rho2, nu=1.0, hilos=1):
        self.rej, self.hilos = rej, hilos
        comps = [(w, rho1), (1 - w, rho2)]
        comps = [(p, r) for p, r in comps if p > 1e-3]
        # relleno: 3 alcances del componente más largo, para que la envoltura no se note
        pad = int(min(3 * max(r for _, r in comps) / paso, 2500))
        self.forma = tuple(sfft.next_fast_len(n + pad, real=True) for n in rej.ras.shape)
        self.amp = np.sqrt(sum(p * _espectro(self.forma, paso, r, nu) for p, r in comps))

    def campo(self, rng):
        shp = self.amp.shape
        ruido = rng.standard_normal(shp) + 1j * rng.standard_normal(shp)
        g = sfft.irfft2(self.amp * ruido, s=self.forma, workers=self.hilos)
        r = self.rej
        z = np.zeros(len(r.fr))
        v = g[r.fr[r.activa], r.cr[r.activa]]
        z[r.activa] = (v - v.mean()) / v.std()
        return z


def calibrar(rej, paso, p, simular, objetivo, desfases=DESFASES, max_lag=30, n=2, semilla=7):
    """Escala los alcances (y prueba nu 0.5 / 1) para que el correlograma simulado, ya pasado por
    la transformación de rangos (`simular(gen, rng)` -> puntajes normales del f simulado),
    se parezca al observado hasta `max_lag` celdas."""
    sel = desfases <= max_lag
    mejor = None
    for nu in (0.5, 1.0):
        for lam in (0.9, 1.0, 1.15, 1.3, 1.5, 1.75):
            gen = Generador(rej, paso, p["w"], lam * p["rho1"], lam * p["rho2"], nu)
            rng = np.random.default_rng(semilla)
            r = np.mean([correlograma(rej, simular(gen, rng), desfases) for _ in range(n)], axis=0)
            sse = float(((r - objetivo)[sel] ** 2).sum())
            if mejor is None or sse < mejor[0]:
                mejor = (sse, nu, lam, r)
    sse, nu, lam, r = mejor
    return {**p, "nu": nu, "escala": lam, "rho1": lam * p["rho1"], "rho2": lam * p["rho2"],
            "sse_simulado": sse, "correlograma_simulado": r.tolist()}


def a_marginal(z, valores_ordenados, activa):
    """Asigna a cada celda activa el valor observado del mismo rango que su z."""
    out = np.full(len(z), np.nan)
    idx = np.flatnonzero(activa)
    out[idx[np.argsort(z[idx], kind="stable")]] = valores_ordenados
    return out
