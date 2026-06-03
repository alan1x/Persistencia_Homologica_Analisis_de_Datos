"""Visualización descriptiva inicial (Fase 1)."""
import matplotlib.pyplot as plt
import seaborn as sns

from . import config

sns.set_theme(style="whitegrid", context="talk")


def mapa_dispersion(df, region, ax=None):
    """Dispersión geográfica de las unidades (coords proyectadas, metros)."""
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 8))
    ax.scatter(df["x"], df["y"], s=2, alpha=0.3, c="#1f77b4")
    ax.set_title(f"{region} — unidades de salud (n={len(df):,})")
    ax.set_xlabel("x UTM 14N (m)")
    ax.set_ylabel("y UTM 14N (m)")
    ax.set_aspect("equal")
    return ax


def conteo_municipios(df, region, top=15, ax=None):
    """Top municipios por número de unidades."""
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 6))
    s = df["municipio"].value_counts().head(top)[::-1]
    ax.barh(s.index, s.values, color="#2ca02c")
    ax.set_title(f"{region} — top {top} municipios")
    ax.set_xlabel("unidades")
    return ax


def dist_personal(df, region, ax=None):
    """Distribución de personal ocupado por rango."""
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 6))
    orden = list(config.PER_OCU_MIDPOINT.keys())
    s = df["per_ocu"].value_counts().reindex(orden).fillna(0)
    ax.bar(range(len(s)), s.values, color="#ff7f0e")
    ax.set_xticks(range(len(s)))
    ax.set_xticklabels([o.replace(" personas", "") for o in s.index], rotation=45, ha="right")
    ax.set_title(f"{region} — personal ocupado")
    ax.set_ylabel("unidades")
    return ax


def panel_eda(df, region):
    """Panel 1x3 con las gráficas descriptivas; guarda en outputs/figuras."""
    fig, axes = plt.subplots(1, 3, figsize=(24, 8))
    mapa_dispersion(df, region, axes[0])
    conteo_municipios(df, region, ax=axes[1])
    dist_personal(df, region, ax=axes[2])
    fig.suptitle(f"EDA descriptiva — {region}", fontsize=22)
    fig.tight_layout()
    ruta = config.FIGURAS_DIR / f"eda_{region}.png"
    fig.savefig(ruta, dpi=110, bbox_inches="tight")
    plt.close(fig)
    return ruta
