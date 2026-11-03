"""Estilo común de las figuras de evaluación (notebooks 22 en adelante)."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

FONDO = "#fcfcfb"
TEXTO = "#0b0b0b"
TEXTO_2 = "#52514e"
REJILLA = "#e6e5e0"
GRIS = "#a9a8a2"
AZUL = "#2a78d6"
NARANJA = "#eb6834"
AQUA = "#1baf7a"


def aplicar():
    plt.rcParams.update({
        "figure.facecolor": FONDO, "axes.facecolor": FONDO, "savefig.facecolor": FONDO,
        "font.family": "DejaVu Sans", "font.size": 10.5,
        "text.color": TEXTO, "axes.labelcolor": TEXTO_2,
        "xtick.color": TEXTO_2, "ytick.color": TEXTO_2,
        "axes.edgecolor": GRIS, "axes.linewidth": 0.8,
        "axes.grid": True, "grid.color": REJILLA, "grid.linewidth": 0.8,
        "axes.axisbelow": True, "axes.spines.top": False, "axes.spines.right": False,
        "axes.titlesize": 11.5, "axes.titleweight": "bold", "axes.titlelocation": "left",
        "legend.frameon": False,
    })


def titulo(fig, texto, sub=None):
    fig.suptitle(texto, x=0.01, ha="left", fontsize=14, fontweight="bold", color=TEXTO)
    if sub:
        fig.text(0.01, 0.925, sub, ha="left", va="top", fontsize=10.5, color=TEXTO_2)


def guardar(fig, ruta):
    fig.savefig(ruta, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("figura:", ruta)
