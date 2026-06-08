"""Vectorización de diagramas de persistencia para comparación entre regiones/estados.

Técnica: Persistence Images (persim.PersistenceImager).
  - Convierte un diagrama H₁ (nube de puntos birth/death) en una imagen 2D de
    tamaño fijo (píxeles = features). Eso permite usar distancia coseno, PCA,
    clustering, etc., sobre cualquier número de regiones.

Flujo:
  1. Calcular diagramas H₁ para todas las regiones.
  2. Ajustar UN PersistenceImager sobre todos los diagramas juntos (mismo grid).
  3. Transformar cada diagrama → vector.
  4. Calcular matriz de similitud coseno entre regiones.
  5. (Opcional) PCA 2D y clustering jerárquico para visualizar grupos.
"""
import matplotlib.pyplot as plt
import numpy as np
from persim import PersistenceImager
from scipy.cluster.hierarchy import dendrogram, linkage
from scipy.spatial.distance import cosine, squareform, pdist
from sklearn.decomposition import PCA
from sklearn.preprocessing import normalize

from . import config


# ---------------------------------------------------------------------------
# Vectorización
# ---------------------------------------------------------------------------

def ajustar_imager(diags_h1_lista, pixel_size=50.0, sigma=100.0):
    """Ajusta un PersistenceImager sobre una lista de diagramas H₁ (en metros).

    Parámetros
    ----------
    diags_h1_lista : list de array (n, 2) — lista de diagramas H₁ en metros,
                     uno por región. Pueden tener distinto número de puntos.
    pixel_size     : tamaño de cada píxel en metros (resolución de la imagen).
    sigma          : ancho de la gaussiana de suavizado (metros).

    Devuelve el PersistenceImager ya ajustado.
    """
    finitos = []
    for d in diags_h1_lista:
        if len(d) == 0:
            continue
        d_fin = d[np.isfinite(d[:, 1])]
        if len(d_fin):
            finitos.append(d_fin)

    if not finitos:
        raise ValueError("Todos los diagramas están vacíos.")

    # Calcular rango real de los datos (sin padding negativo)
    todos = np.vstack(finitos)
    births = todos[:, 0]
    pers   = todos[:, 1] - todos[:, 0]

    birth_range = (float(max(0, births.min())),    float(births.max()))
    pers_range  = (float(max(0, pers.min())),      float(pers.max()))

    pimgr = PersistenceImager(
        pixel_size=pixel_size,
        birth_range=birth_range,
        pers_range=pers_range,
        kernel_params={"sigma": sigma},
    )
    pimgr.fit(finitos)
    return pimgr


def vectorizar(diag_h1, pimgr):
    """Transforma un diagrama H₁ en un vector 1D normalizado.

    Parámetros
    ----------
    diag_h1 : array (n, 2) en metros — diagrama H₁ de una región.
    pimgr   : PersistenceImager ya ajustado con ajustar_imager().

    Devuelve array 1D (n_pixels,) normalizado L2.
    """
    d_fin = diag_h1[np.isfinite(diag_h1[:, 1])] if len(diag_h1) else np.empty((0, 2))
    img = pimgr.transform([d_fin])[0]          # imagen 2D
    vec = img.flatten().astype(np.float64)
    norma = np.linalg.norm(vec)
    return vec / norma if norma > 0 else vec


# ---------------------------------------------------------------------------
# Similitud
# ---------------------------------------------------------------------------

def matriz_similitud(vectores, nombres):
    """Calcula la matriz de similitud coseno entre regiones.

    Parámetros
    ----------
    vectores : dict {nombre: vector_1D}
    nombres  : lista de nombres en el orden deseado

    Devuelve array (n, n) con similitud ∈ [0, 1] (1 = idénticos).
    """
    n = len(nombres)
    mat = np.zeros((n, n))
    for i, a in enumerate(nombres):
        for j, b in enumerate(nombres):
            if i == j:
                mat[i, j] = 1.0
            else:
                dist = cosine(vectores[a], vectores[b])
                mat[i, j] = 1.0 - dist  # similitud
    return mat


# ---------------------------------------------------------------------------
# Visualización
# ---------------------------------------------------------------------------

def plot_imagen_persistencia(pimgr, diag_h1, region, ax=None):
    """Muestra la persistence image de una región."""
    if ax is None:
        _, ax = plt.subplots(figsize=(5, 5))
    d_fin = diag_h1[np.isfinite(diag_h1[:, 1])] if len(diag_h1) else np.empty((0, 2))
    img = pimgr.transform([d_fin])[0]
    im = ax.imshow(img.T, origin="lower", cmap="hot",
                   extent=[pimgr.birth_range[0], pimgr.birth_range[1],
                           pimgr.pers_range[0], pimgr.pers_range[1]])
    ax.set_title(f"{region} — Persistence Image H₁")
    ax.set_xlabel("birth (m)")
    ax.set_ylabel("persistencia (m)")
    plt.colorbar(im, ax=ax, fraction=0.046)
    return ax


def plot_similitud(mat_sim, nombres, ax=None):
    """Heatmap de la matriz de similitud coseno."""
    if ax is None:
        _, ax = plt.subplots(figsize=(max(5, len(nombres)), max(4, len(nombres) - 1)))
    im = ax.imshow(mat_sim, vmin=0, vmax=1, cmap="YlGn")
    ax.set_xticks(range(len(nombres)))
    ax.set_yticks(range(len(nombres)))
    ax.set_xticklabels(nombres, rotation=45, ha="right")
    ax.set_yticklabels(nombres)
    for i in range(len(nombres)):
        for j in range(len(nombres)):
            ax.text(j, i, f"{mat_sim[i, j]:.3f}",
                    ha="center", va="center", fontsize=10,
                    color="black" if mat_sim[i, j] < 0.7 else "white")
    ax.set_title("Similitud coseno entre diagramas H₁")
    plt.colorbar(im, ax=ax)
    return ax


def plot_dendrograma(vectores, nombres, ax=None):
    """Dendrograma jerárquico (Ward) sobre los vectores de persistencia."""
    if ax is None:
        _, ax = plt.subplots(figsize=(max(6, len(nombres)), 4))
    mat = np.vstack([vectores[n] for n in nombres])
    Z = linkage(mat, method="ward", metric="euclidean")
    dendrogram(Z, labels=nombres, ax=ax, leaf_rotation=45)
    ax.set_title("Clustering jerárquico — diagramas H₁ (Ward)")
    ax.set_ylabel("distancia")
    return ax


def plot_pca(vectores, nombres, ax=None):
    """PCA 2D de los vectores de persistencia. Útil con ≥4 regiones."""
    if ax is None:
        _, ax = plt.subplots(figsize=(6, 6))
    mat = np.vstack([vectores[n] for n in nombres])
    if mat.shape[0] < 2:
        ax.set_title("PCA requiere ≥2 regiones")
        return ax
    n_comp = min(2, mat.shape[0])
    coords = PCA(n_components=n_comp).fit_transform(mat)
    ax.scatter(coords[:, 0], coords[:, 1] if n_comp > 1 else np.zeros(len(nombres)),
               s=120, c=range(len(nombres)), cmap="tab10", zorder=3)
    for i, nom in enumerate(nombres):
        ax.annotate(nom, (coords[i, 0],
                          coords[i, 1] if n_comp > 1 else 0),
                    textcoords="offset points", xytext=(8, 4), fontsize=11)
    ax.set_title("PCA 2D — vectores de persistencia H₁")
    ax.set_xlabel("PC1")
    ax.set_ylabel("PC2")
    ax.axhline(0, color="grey", lw=0.5)
    ax.axvline(0, color="grey", lw=0.5)
    return ax


def panel_vectorizacion(pimgr, diags_h1, vectores, nombres):
    """Panel de visualización con 2 o más regiones.

    Fila 0: scatter (birth, persistencia) por región — cada punto es un hueco H₁
    Fila 1 izq: histogramas solapados de persistencia (escala log)
    Fila 1 der: boxplot comparativo de persistencia y birth

    El mapa de imágenes (persistence image) se usa internamente para vectorizar
    y calcular similitud, pero no se muestra porque con 2 regiones de escalas muy
    distintas resulta ilegible. Se muestra en su lugar la estructura de los datos.

    Guarda en outputs/figuras/vectorizacion.png.
    """
    n = len(nombres)
    ncols = max(n, 2)
    colors = ["#d62728", "#1f77b4", "#2ca02c", "#ff7f0e"]
    fig, axes = plt.subplots(2, ncols, figsize=(7 * ncols, 13))

    # --- Fila 0: scatter birth vs persistencia por región ---
    for i, nom in enumerate(nombres):
        ax = axes[0, i]
        d = diags_h1[nom]
        births = d[:, 0] / 1000          # km
        pers   = (d[:, 1] - d[:, 0]) / 1000  # km
        sc = ax.scatter(births, pers,
                        c=pers, cmap="YlOrRd", s=60, alpha=0.8,
                        edgecolors="grey", linewidths=0.4, vmin=0)
        plt.colorbar(sc, ax=ax, label="persistencia (km)")
        ax.axhline(1.0, color="steelblue", lw=1.5, ls="--",
                   label="persistencia = 1 km")
        ax.set_title(f"{nom} — huecos H₁ ({len(d)} huecos ≥ 200 m)\n"
                     f"birth median={np.median(births)*1000:.0f} m  "
                     f"pers median={np.median(pers)*1000:.0f} m",
                     fontsize=12)
        ax.set_xlabel("birth (km): radio al que nació el hueco")
        ax.set_ylabel("persistencia (km): tamaño del hueco")
        ax.legend(fontsize=9)

    for j in range(n, ncols):
        axes[0, j].set_visible(False)

    # --- Fila 1 izq: histogramas solapados de persistencia ---
    ax_hist = axes[1, 0]
    for i, nom in enumerate(nombres):
        d = diags_h1[nom]
        pers_km = (d[:, 1] - d[:, 0]) / 1000
        ax_hist.hist(pers_km, bins=25, alpha=0.55,
                     color=colors[i % len(colors)], label=nom, edgecolor="white")
    ax_hist.set_yscale("log")
    ax_hist.axvline(1.0, color="grey", lw=1.5, ls="--", label="1 km")
    ax_hist.set_title("Distribución de persistencias H₁\n"
                      "→ barras a la derecha = huecos más grandes sin cobertura",
                      fontsize=12)
    ax_hist.set_xlabel("persistencia del hueco (km)")
    ax_hist.set_ylabel("número de huecos (escala log)")
    ax_hist.legend()

    # --- Fila 1 der: boxplot comparativo ---
    ax_box = axes[1, 1]
    datos_box = [(diags_h1[nom][:, 1] - diags_h1[nom][:, 0]) / 1000
                 for nom in nombres]
    bp = ax_box.boxplot(datos_box, labels=nombres, patch_artist=True,
                        medianprops={"color": "black", "lw": 2})
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)
    ax_box.axhline(1.0, color="grey", lw=1.5, ls="--", label="1 km")
    ax_box.set_title("Boxplot de persistencias H₁\n"
                     "→ caja más alta y con más outliers = peor cobertura",
                     fontsize=12)
    ax_box.set_ylabel("persistencia del hueco (km)")
    ax_box.legend()

    for j in range(2, ncols):
        axes[1, j].set_visible(False)

    mat_sim = matriz_similitud(vectores, nombres)
    sim_txt = " | ".join(
        f"{nombres[i]}↔{nombres[j]}: {mat_sim[i,j]:.3f}"
        for i in range(n) for j in range(i+1, n)
    )
    fig.suptitle(
        f"Análisis de huecos H₁ — cobertura de salud\n"
        f"Similitud coseno (Persistence Image): {sim_txt}",
        fontsize=14)
    fig.tight_layout()
    ruta = config.FIGURAS_DIR / "vectorizacion.png"
    fig.savefig(ruta, dpi=110, bbox_inches="tight")
    plt.close(fig)
    return ruta, mat_sim
    n = len(nombres)
    ncols = max(n, 2)
    fig, axes = plt.subplots(2, ncols, figsize=(7 * ncols, 13))

    # --- Fila 0: persistence image por región ---
    imgs = {}
    for nom in nombres:
        d_fin = diags_h1[nom]
        img = pimgr.transform([d_fin])[0]
        imgs[nom] = img

    # Usar percentil 95 como vmax para que los outliers no aplanen la escala
    todos_valores = np.concatenate([img.flatten() for img in imgs.values()])
    valores_pos = todos_valores[todos_valores > 0]
    vmax_global = float(np.percentile(valores_pos, 95)) if len(valores_pos) else 1.0

    br = pimgr.birth_range
    pr = pimgr.pers_range
    ext = [br[0]/1000, br[1]/1000, pr[0]/1000, pr[1]/1000]

    for i, nom in enumerate(nombres):
        ax = axes[0, i]
        im = ax.imshow(imgs[nom].T, origin="lower", cmap="hot",
                       extent=ext, aspect="auto",
                       vmin=0, vmax=vmax_global)
        ax.set_title(f"{nom} — densidad de huecos H₁\n"
                     f"({len(diags_h1[nom])} huecos ≥ 200 m)", fontsize=13)
        ax.set_xlabel("birth (km): radio al que nació el hueco")
        ax.set_ylabel("persistencia (km): cuánto duró el hueco")
        plt.colorbar(im, ax=ax, label="densidad")
        # Marca de referencia: 1 km de persistencia
        ax.axhline(y=1.0, color="cyan", lw=1.5, ls="--", alpha=0.8, label="> 1 km persist.")
        ax.legend(fontsize=9, loc="upper right")

    for j in range(n, ncols):
        axes[0, j].set_visible(False)

    # --- Fila 1 izq: imagen diferencia ---
    ax_diff = axes[1, 0]
    if n == 2:
        diff = imgs[nombres[0]] - imgs[nombres[1]]
        # Percentil 95 del valor absoluto para no saturar la escala
        vd = float(np.percentile(np.abs(diff[diff != 0]), 95)) if np.any(diff != 0) else 1.0
        im2 = ax_diff.imshow(diff.T, origin="lower", cmap="RdBu_r",
                              extent=ext, vmin=-vd, vmax=vd, aspect="auto")
        ax_diff.set_title(
            f"Diferencia: {nombres[0]} − {nombres[1]}\n"
            f"Rojo = más huecos en {nombres[0]} | Azul = más huecos en {nombres[1]}",
            fontsize=12)
        ax_diff.set_xlabel("birth (km)")
        ax_diff.set_ylabel("persistencia (km)")
        plt.colorbar(im2, ax=ax_diff, label="diferencia de densidad")
    else:
        mat_sim = matriz_similitud(vectores, nombres)
        plot_similitud(mat_sim, nombres, ax_diff)

    # --- Fila 1 der: histograma comparativo de persistencias ---
    ax_hist = axes[1, 1]
    colors = ["#d62728", "#1f77b4", "#2ca02c", "#ff7f0e"]
    for i, nom in enumerate(nombres):
        pers_vals = (diags_h1[nom][:, 1] - diags_h1[nom][:, 0]) / 1000  # km
        ax_hist.hist(pers_vals, bins=30, alpha=0.6,
                     color=colors[i % len(colors)], label=nom, edgecolor="white")
    ax_hist.set_yscale("log")
    ax_hist.set_title("Distribución de persistencias H₁\n"
                      "(huecos más a la derecha = zonas más grandes sin cobertura)",
                      fontsize=12)
    ax_hist.set_xlabel("persistencia (km)")
    ax_hist.set_ylabel("número de huecos (log)")
    ax_hist.legend()
    ax_hist.axvline(x=1.0, color="grey", lw=1.5, ls="--")

    for j in range(2, ncols):
        axes[1, j].set_visible(False)

    mat_sim = matriz_similitud(vectores, nombres)
    sim_txt = " | ".join(
        f"{nombres[i]}↔{nombres[j]}: {mat_sim[i,j]:.3f}"
        for i in range(n) for j in range(i+1, n)
    )
    fig.suptitle(
        f"Vectorización de persistencia H₁ — comparación entre regiones\n"
        f"Similitud coseno: {sim_txt}",
        fontsize=14)
    fig.tight_layout()
    ruta = config.FIGURAS_DIR / "vectorizacion.png"
    fig.savefig(ruta, dpi=110, bbox_inches="tight")
    plt.close(fig)
    return ruta, mat_sim
