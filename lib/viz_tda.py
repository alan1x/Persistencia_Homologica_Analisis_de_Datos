"""Visualización de persistencia: diagramas, barcodes, curvas de Betti, comparación."""
import matplotlib.pyplot as plt
import numpy as np
from persim import plot_diagrams, bottleneck, wasserstein

from . import config


def _persim_list(diags_radio):
    """Convierte dict dim->array a lista [H0,H1,H2] para persim (radio en m)."""
    return [diags_radio.get(d, np.empty((0, 2))) for d in (0, 1, 2)]


def diagrama_persistencia(diags_radio, region, ax=None):
    """Diagrama de persistencia (escala radio en metros)."""
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 8))
    plot_diagrams(_persim_list(diags_radio), labels=["H0", "H1", "H2"], ax=ax)
    ax.set_title(f"{region} — diagrama de persistencia (m)")
    return ax


def barcode(diags_radio, region, dim=1, max_barras=40, ax=None):
    """Código de barras de una dimensión (las clases más persistentes)."""
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 8))
    d = diags_radio.get(dim, np.empty((0, 2)))
    if len(d) == 0:
        ax.set_title(f"{region} — H{dim}: sin clases")
        return ax
    finite = d[np.isfinite(d[:, 1])]
    pers = finite[:, 1] - finite[:, 0]
    orden = np.argsort(pers)[::-1][:max_barras]
    barras = finite[orden]
    for i, (b, m) in enumerate(barras):
        ax.plot([b, m], [i, i], lw=2, color="#d62728")
    ax.set_title(f"{region} — barcode H{dim} (top {len(barras)})")
    ax.set_xlabel("radio (m)")
    ax.set_ylabel("clases")
    return ax


def curva_betti(simplex_tree, region, dims=(0, 1), n=200, ax=None):
    """Curva de Betti vs radio (m) a partir de la persistencia del simplex tree."""
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 6))
    pers = simplex_tree.persistence()  # lista (dim, (birth, death)) en alpha
    radios = {}
    for dim in dims:
        pts = [(np.sqrt(max(b, 0)), np.sqrt(m) if np.isfinite(m) else np.inf)
               for (dd, (b, m)) in pers if dd == dim]
        radios[dim] = pts
    todos = [v for pts in radios.values() for (b, m) in pts for v in (b, m) if np.isfinite(v)]
    rmax = max(todos) if todos else 1.0
    grid = np.linspace(0, rmax, n)
    for dim in dims:
        betti = [sum(1 for (b, m) in radios[dim] if b <= r < m) for r in grid]
        ax.plot(grid, betti, label=f"$\\beta_{dim}$")
    ax.set_title(f"{region} — curvas de Betti")
    ax.set_xlabel("radio (m)")
    ax.set_ylabel("Betti")
    ax.legend()
    return ax


def panel_persistencia(diags_radio, simplex_tree, region):
    """Panel: diagrama + barcode H1 + curvas de Betti. Guarda figura."""
    fig, axes = plt.subplots(1, 3, figsize=(24, 8))
    diagrama_persistencia(diags_radio, region, axes[0])
    barcode(diags_radio, region, dim=1, ax=axes[1])
    curva_betti(simplex_tree, region, ax=axes[2])
    fig.suptitle(f"Persistencia homológica — {region}", fontsize=22)
    fig.tight_layout()
    ruta = config.FIGURAS_DIR / f"persistencia_{region}.png"
    fig.savefig(ruta, dpi=110, bbox_inches="tight")
    plt.close(fig)
    return ruta


def comparar_regiones(diagsA_radio, diagsB_radio, nombreA, nombreB, dim=1):
    """Distancias bottleneck y Wasserstein entre dos regiones en una dimensión."""
    A = diagsA_radio.get(dim, np.empty((0, 2)))
    B = diagsB_radio.get(dim, np.empty((0, 2)))
    A = A[np.isfinite(A[:, 1])]
    B = B[np.isfinite(B[:, 1])]
    return {
        "dim": dim,
        "bottleneck": float(bottleneck(A, B)),
        "wasserstein": float(wasserstein(A, B)),
        f"n_{nombreA}": len(A),
        f"n_{nombreB}": len(B),
    }
