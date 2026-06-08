"""Bifiltración por densidad: cruza los huecos H₁ con la densidad local de actividad.

Sin datos de censo, usamos la densidad de unidades económicas (DENUE) como
proxy de densidad urbana/poblacional. La hipótesis es:
    mayor densidad de servicios ≈ mayor densidad de población

La bifiltración agrega una segunda dimensión al análisis:
  - Eje 1 (ya existente): radio de filtración geográfico (alpha complex)
  - Eje 2 (nuevo): densidad local de unidades en el centroide del hueco

Esto permite separar:
  "Hueco en zona densa" → falla de cobertura real, acción urgente
  "Hueco en zona dispersa" → vacío natural/rural, menor prioridad

Implementación:
  KDE gaussiana 2D sobre las coordenadas UTM de las unidades de salud.
  Se evalúa en el centroide de cada hueco H₁.
  El bandwidth se selecciona automáticamente (Scott's rule) o se puede
  fijar en metros para interpretabilidad.
"""
import numpy as np
import pandas as pd
from scipy.stats import gaussian_kde
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from . import config

# Etiquetas de prioridad combinando persistencia + densidad
PRIORIDAD_CRUZADA = {
    ("alta", "alta"):  {"label": "CRÍTICO: zona densa sin cobertura",
                        "color": "#a50026", "prioridad": 1},
    ("alta", "baja"):  {"label": "Alerta: zona activa con hueco grande",
                        "color": "#d73027", "prioridad": 2},
    ("baja", "alta"):  {"label": "Moderado: zona densa, hueco menor",
                        "color": "#f46d43", "prioridad": 3},
    ("baja", "baja"):  {"label": "Bajo: zona rural/dispersa",
                        "color": "#74add1", "prioridad": 4},
}


def estimar_densidad_kde(puntos_xy, bandwidth=None):
    """Ajusta un KDE 2D gaussiano sobre las coordenadas UTM de las unidades.

    Parámetros
    ----------
    puntos_xy : array (N, 2) — coordenadas x, y en metros (UTM 14N)
    bandwidth : float o None — bandwidth en metros. Si None usa Scott's rule.

    Devuelve la función kde (callable: kde(xy) → densidad)
    """
    # gaussian_kde trabaja con columnas como observaciones (2, N)
    kde = gaussian_kde(puntos_xy.T, bw_method=bandwidth)
    return kde


def densidad_en_centroides(centroides_xy, kde):
    """Evalúa la densidad KDE en una lista de centroides.

    Parámetros
    ----------
    centroides_xy : array (M, 2) — centroides de los huecos en UTM metros
    kde           : objeto gaussian_kde ya ajustado

    Devuelve array (M,) con la densidad estimada en cada centroide.
    """
    return kde(centroides_xy.T)


def clasificar_bifiltracion(ciclos, kde, umbral_pers=500.0, percentil_densidad=50):
    """Clasifica cada hueco H₁ según persistencia Y densidad local.

    Parámetros
    ----------
    ciclos            : lista de dicts de tda.ciclos_H1()
    kde               : gaussian_kde ajustado sobre las unidades de salud
    umbral_pers       : float (m) — persistencia mínima para "hueco grande"
    percentil_densidad: int — percentil de densidad para umbral alto/bajo

    Devuelve DataFrame con columnas:
        birth_m, death_m, pers_m, cx, cy, densidad,
        nivel_pers, nivel_densidad, label, color, prioridad
    """
    if not ciclos:
        return pd.DataFrame()

    centroides = np.array([c["centroide"] for c in ciclos])
    densidades = densidad_en_centroides(centroides, kde)
    umbral_den = float(np.percentile(densidades, percentil_densidad))

    rows = []
    for c, dens in zip(ciclos, densidades):
        nivel_pers = "alta" if c["pers"] >= umbral_pers else "baja"
        nivel_den  = "alta" if dens >= umbral_den else "baja"
        info = PRIORIDAD_CRUZADA[(nivel_pers, nivel_den)]
        rows.append({
            "birth_m":       c["birth"],
            "death_m":       c["death"],
            "pers_m":        c["pers"],
            "cx":            c["centroide"][0],
            "cy":            c["centroide"][1],
            "densidad":      float(dens),
            "nivel_pers":    nivel_pers,
            "nivel_densidad": nivel_den,
            "label":         info["label"],
            "color":         info["color"],
            "prioridad":     info["prioridad"],
        })

    df = pd.DataFrame(rows).sort_values("prioridad")
    return df


def panel_bifiltracion(df_bf, puntos_xy, region, umbral_pers=500.0):
    """Panel de 4 gráficas interpretativas para la bifiltración.

    A: scatter (persistencia, densidad) coloreado por categoría
    B: mapa de calor de densidad KDE con huecos superpuestos
    C: barras de conteo por categoría
    D: scatter geográfico (x, y) coloreado por prioridad

    Guarda en outputs/figuras/bifiltracion_{region}.png
    """
    fig, axes = plt.subplots(2, 2, figsize=(16, 14))
    cat_items = [
        mpatches.Patch(color=v["color"], label=f"[{v['prioridad']}] {v['label']}")
        for v in PRIORIDAD_CRUZADA.values()
    ]

    # ----- A: scatter persistencia vs densidad -----
    ax = axes[0, 0]
    for lbl, info in PRIORIDAD_CRUZADA.items():
        sub = df_bf[df_bf["label"] == info["label"]]
        if len(sub) == 0:
            continue
        ax.scatter(sub["pers_m"] / 1000, sub["densidad"] * 1e6,
                   c=info["color"], s=70, alpha=0.85,
                   edgecolors="white", linewidths=0.5, label=info["label"])
    ax.axvline(umbral_pers / 1000, color="grey", ls="--", lw=1.2)
    umb_den = df_bf["densidad"].median() * 1e6
    ax.axhline(umb_den, color="grey", ls="--", lw=1.2)
    ax.set_xlabel("persistencia del hueco (km)", fontsize=11)
    ax.set_ylabel("densidad local de servicios (×10⁻⁶)", fontsize=11)
    ax.set_title(f"{region} — Bifiltración: persistencia × densidad\n"
                 "Cuadrante sup-der = zona urbana sin cobertura (crítico)", fontsize=11)
    ax.legend(fontsize=8, loc="upper right")

    # Anotar cuadrantes
    ax.text(0.02, 0.97, "← pers baja", transform=ax.transAxes,
            fontsize=8, color="grey", va="top")
    ax.text(0.98, 0.97, "pers alta →", transform=ax.transAxes,
            fontsize=8, color="grey", va="top", ha="right")
    ax.text(0.02, 0.52, "densidad alta ↑", transform=ax.transAxes,
            fontsize=8, color="grey", rotation=90, va="center")

    # ----- B: mapa de calor KDE con huecos -----
    ax = axes[0, 1]
    # Grid para el mapa de calor
    margin = 5000
    xmin, xmax = puntos_xy[:, 0].min() - margin, puntos_xy[:, 0].max() + margin
    ymin, ymax = puntos_xy[:, 1].min() - margin, puntos_xy[:, 1].max() + margin
    nx, ny = 80, 80
    xi = np.linspace(xmin, xmax, nx)
    yi = np.linspace(ymin, ymax, ny)
    XX, YY = np.meshgrid(xi, yi)
    grid_pts = np.vstack([XX.ravel(), YY.ravel()])

    kde_obj = estimar_densidad_kde(puntos_xy)
    ZZ = kde_obj(grid_pts).reshape(ny, nx)
    # Normalizar al percentil 95 para no saturar
    vmax = float(np.percentile(ZZ[ZZ > 0], 95)) if np.any(ZZ > 0) else ZZ.max()
    ax.imshow(ZZ, extent=[xmin/1000, xmax/1000, ymin/1000, ymax/1000],
              origin="lower", cmap="YlOrRd", vmin=0, vmax=vmax, aspect="auto",
              alpha=0.7)

    # Superponer huecos coloreados por prioridad
    for _, row in df_bf.iterrows():
        ax.scatter(row["cx"] / 1000, row["cy"] / 1000,
                   c=row["color"], s=max(20, row["pers_m"] / 80),
                   edgecolors="white", linewidths=0.5, zorder=5, alpha=0.9)

    ax.set_xlabel("x UTM (km)", fontsize=11)
    ax.set_ylabel("y UTM (km)", fontsize=11)
    ax.set_title(f"{region} — Densidad de servicios (fondo)\n"
                 "con huecos H₁ superpuestos (tamaño ∝ persistencia)", fontsize=11)

    # ----- C: barras de conteo por categoría -----
    ax = axes[1, 0]
    labels_ord = [v["label"] for v in sorted(PRIORIDAD_CRUZADA.values(),
                                              key=lambda x: x["prioridad"])]
    colors_ord = [v["color"] for v in sorted(PRIORIDAD_CRUZADA.values(),
                                              key=lambda x: x["prioridad"])]
    conteos = [len(df_bf[df_bf["label"] == lbl]) for lbl in labels_ord]
    y_pos = np.arange(len(labels_ord))
    bars = ax.barh(y_pos, conteos, color=colors_ord, edgecolor="white", height=0.6)
    ax.set_yticks(y_pos)
    ax.set_yticklabels([f"[{i+1}] {l}" for i, l in enumerate(labels_ord)], fontsize=9)
    ax.set_xlabel("número de huecos", fontsize=11)
    ax.set_title(f"{region} — Conteo por categoría de bifiltración\n"
                 "(persistencia + densidad local)", fontsize=11)
    for bar, v in zip(bars, conteos):
        if v > 0:
            ax.text(bar.get_width() + 0.2, bar.get_y() + bar.get_height()/2,
                    str(v), va="center", fontsize=10)
    ax.invert_yaxis()

    # ----- D: tabla de acción por prioridad -----
    ax = axes[1, 1]
    ax.axis("off")
    ax.text(0.5, 1.0, f"PLAN DE ACCIÓN — {region}",
            transform=ax.transAxes, ha="center", va="top",
            fontsize=13, fontweight="bold")

    acciones = {
        "CRÍTICO: zona densa sin cobertura":
            "→ Abrir unidad de salud dentro del hueco.\n  Zona urbana con demanda real y sin oferta.",
        "Alerta: zona activa con hueco grande":
            "→ Ampliar cobertura móvil o satélite.\n  Actividad económica presente, servicio lejano.",
        "Moderado: zona densa, hueco menor":
            "→ Monitorear. Hueco pequeño en zona activa.\n  Potencial futuro si la zona crece.",
        "Bajo: zona rural/dispersa":
            "→ Baja prioridad de inversión fija.\n  Evaluar cobertura móvil o telemedicina.",
    }

    y = 0.88
    for i, (lbl, accion) in enumerate(acciones.items()):
        info = next(v for v in PRIORIDAD_CRUZADA.values() if v["label"] == lbl)
        n = len(df_bf[df_bf["label"] == lbl])
        ax.add_patch(mpatches.FancyBboxPatch(
            (0.01, y - 0.10), 0.97, 0.13,
            boxstyle="round,pad=0.01",
            facecolor=info["color"], alpha=0.12,
            transform=ax.transAxes, clip_on=False))
        ax.text(0.04, y, f"[{info['prioridad']}] {lbl}  (n={n})",
                transform=ax.transAxes, fontsize=10,
                fontweight="bold", color=info["color"], va="top")
        ax.text(0.04, y - 0.05, accion,
                transform=ax.transAxes, fontsize=8.5,
                color="#333", va="top")
        y -= 0.21

    fig.suptitle(
        f"Bifiltración topológica — {region}\n"
        "Huecos H₁ cruzados con densidad local de actividad (proxy de población)",
        fontsize=14, y=1.01)
    fig.tight_layout()
    ruta = config.FIGURAS_DIR / f"bifiltracion_{region}.png"
    fig.savefig(ruta, dpi=120, bbox_inches="tight")
    plt.close(fig)
    return ruta
