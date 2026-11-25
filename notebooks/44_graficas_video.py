"""Gráficas del video de la serie Videos Ciencia de Datos (esquema en
`../Videos Ciencia de Datos/esquemas/persistencia.md`).

Estilo fijo del esquema: vertical 1080×1920, fondo oscuro, una idea y una cifra por gráfica, y
la «Paleta del video» (un color = un significado en todo el video; ver PALETA abajo). Las
animaciones (🎬) salen como GIF con Pillow (no hay ffmpeg en el entorno) y su último cuadro
también como PNG.

Cada cifra se lee de `outputs/auditoria/*.json` o se recalcula de los intermedios y se
comprueba contra el JSON (los `assert` de abajo). Nada se escribe a mano.

Uso:  .venv/Scripts/python.exe notebooks/44_graficas_video.py [nombre ...]
"""
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import animation, patheffects
from matplotlib.collections import LineCollection
from matplotlib.colors import LinearSegmentedColormap, ListedColormap, PowerNorm
from matplotlib.patches import FancyBboxPatch, Polygon
from matplotlib.transforms import Affine2D
from scipy import sparse
from scipy.sparse import csgraph
from scipy.spatial import cKDTree

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from lib import acceso  # noqa: E402

AUD = RAIZ / "outputs" / "auditoria"
INT = RAIZ / "outputs" / "intermedios"
OUT = RAIZ / "outputs" / "video"
OUT.mkdir(parents=True, exist_ok=True)

# ── Paleta del video ──────────────────────────────────────────────────────────
# Un color = un significado en todas las gráficas (esquema, «Paleta del video»).
FONDO = "#1a1a19"       # superficie oscura
SILUETA = "#383834"     # gris: fondo de mapa, zona sin dato, referencia
CALLE = "#46463f"       # gris: calles
TXT = "#f0efec"
TXT2 = "#c3c2b7"
TXT3 = "#8f8e86"
GRIS = "#6f6e68"        # gris: serie de referencia (nulo, a pie, parte de la gente)
BAJO = "#e66767"        # rojo: acceso bajo (y nada más)
AZUL = "#3987e5"        # azul: acceso suficiente, en marcas pequeñas
SUF = "#24456f"         # azul: acceso suficiente, en áreas grandes del mapa
CLIN = TXT              # blanco: clínicas que existen hoy
VERDE = "#58D6A9"       # verde: lo que se agrega (clínicas nuevas, transporte, mejora).
#                         Menta y no verde puro: contra el rojo separa ΔE 12.2 con deuteranopía
#                         (#0ca30c daba 7.1). Siempre va con forma o etiqueta además del color.
NEUTRO = "#B8B8B0"      # gris claro: rutas y alcance por calle (referencia, no es un valor)
AMBAR = LinearSegmentedColormap.from_list(  # ámbar, oscuro → blanco: cuánta gente hay
    "ambar", ["#241a0e", "#6b420c", "#c27c10", "#f2b544", "#fff4dc"])
GRADOS = ["Muy bajo", "Bajo", "Medio", "Alto", "Muy alto"]
# Morado por grado de marginación. El esquema pide «claro → oscuro», pero sobre fondo oscuro lo
# oscuro desaparece; aquí va de oscuro (muy baja) a claro (muy alta), para que destaque la
# marginación alta, que es la que importa en C y en la conclusión 3.
MORADO = ["#3b2c5e", "#5a43a0", "#7d62d1", "#a993ec", "#e2d9ff"]
PERSONAS = PowerNorm(0.5, vmin=0, vmax=100, clip=True)   # escala de gente: raíz, tope 100+

plt.rcParams.update({
    "font.family": "Segoe UI", "figure.facecolor": FONDO, "axes.facecolor": FONDO,
    "savefig.facecolor": FONDO, "text.color": TXT, "axes.labelcolor": TXT2,
    "xtick.color": TXT3, "ytick.color": TXT3, "axes.edgecolor": CALLE,
    "font.size": 20,
})
W, H, DPI = 9, 16, 120   # 1080 × 1920
FUENTE = "CLUES 2026 · Censo 2020 · CONAPO 2020 · OpenStreetMap"

# El barrio común de los zooms (p1_02, p1_03b, D, E) y el cuadro que se sigue (p1_03c, p1_03d).
BARRIO = (493200, 498800, 2138700, 2144300)          # 5.6 × 5.6 km
NOMBRE_BARRIO = "Iztapalapa, alrededor del Peñón Viejo"
CUADRO = (497000.0, 2142100.0)


def cargar(nombre):
    return json.loads((AUD / f"{nombre}.json").read_text(encoding="utf-8"))


def mill(x, dec=2):
    return f"{x / 1e6:.{dec}f} M"


def mil(x):
    return f"{x / 1e3:,.0f} mil"


def lienzo(cifra, titulo, nota=None, sub=None):
    """Figura vertical con la cifra arriba, el título debajo y la nota al pie."""
    fig = plt.figure(figsize=(W, H), dpi=DPI)
    fig.text(0.06, 0.935, cifra, fontsize=84, fontweight="bold", color=TXT, va="top")
    fig.text(0.06, 0.835, titulo, fontsize=27, color=TXT, va="top", linespacing=1.3)
    fig.sub = fig.text(0.06, 0.735, sub or "", fontsize=21, color=TXT2, va="top", linespacing=1.35)
    pie = (nota + "\n" if nota else "") + FUENTE
    fig.text(0.06, 0.03, pie, fontsize=13, color=TXT3, va="bottom", linespacing=1.4)
    return fig


def lienzo_pregunta(pregunta, respuesta, nota=None):
    """Escenarios: el título es la pregunta en palabras simples y debajo va la respuesta."""
    fig = plt.figure(figsize=(W, H), dpi=DPI)
    fig.text(0.06, 0.955, pregunta, fontsize=46, fontweight="bold", va="top", linespacing=1.1)
    y = 0.955 - 0.05 * (pregunta.count(chr(10)) + 1) - 0.035
    fig.resp = fig.text(0.06, y, respuesta, fontsize=23, color=TXT, va="top", linespacing=1.3)
    pie = (nota + "\n" if nota else "") + FUENTE
    fig.text(0.06, 0.03, pie, fontsize=12.5, color=TXT3, va="bottom", linespacing=1.4)
    return fig


def guardar(fig, nombre):
    fig.savefig(OUT / f"{nombre}.png", dpi=DPI)
    plt.close(fig)
    print("  ->", nombre + ".png")


def guardar_anim(fig, actualizar, n, nombre, fps=20):
    an = animation.FuncAnimation(fig, actualizar, frames=n, blit=False)
    an.save(OUT / f"{nombre}.gif", writer=animation.PillowWriter(fps=fps), dpi=DPI)
    actualizar(n - 1)
    fig.savefig(OUT / f"{nombre}.png", dpi=DPI)
    plt.close(fig)
    print("  ->", nombre + ".gif / .png")


def leyenda(fig, x, y, items, dy=0.028, fs=17):
    """Leyenda de cuadritos con texto en tinta (el color va en la marca, no en el texto)."""
    for k, (col, txt) in enumerate(items):
        fig.text(x, y - k * dy, "■", color=col, fontsize=fs + 5, va="top")
        fig.text(x + 0.04, y - k * dy, txt, color=TXT2, fontsize=fs, va="top")


# ── Datos comunes ─────────────────────────────────────────────────────────────
CEL = pd.read_parquet(INT / "acceso_e2sfca_celdas.parquet")
_cal = pd.read_parquet(INT / "acceso_calle.parquet")
assert (CEL.x.values == _cal.x.values).all() and (CEL.y.values == _cal.y.values).all()
CEL["f"] = _cal["acceso_rel_calle"].to_numpy()
X0, Y0 = CEL.x.min(), CEL.y.min()
CI = ((CEL.x - X0) / 100).round().astype(int).to_numpy()
CJ = ((CEL.y - Y0) / 100).round().astype(int).to_numpy()
NX, NY = CI.max() + 1, CJ.max() + 1
EXT = (X0 - 50, X0 + NX * 100 - 50, Y0 - 50, Y0 + NY * 100 - 50)
PSIN = CEL.psin.to_numpy()
OF = acceso.oferta()
GRADO_I = CEL.grado.astype(object).map({g: i for i, g in enumerate(GRADOS)}).fillna(-1).astype(int).to_numpy()
_PARES = None


def pares():
    """Pares celda–clínica por calle (≤ 2,250 m), de `pares_red_unidades.parquet`."""
    global _PARES
    if _PARES is None:
        _PARES = pd.read_parquet(INT / "pares_red_unidades.parquet")
    return _PARES


def raster(valores):
    r = np.full((NY, NX), np.nan)
    r[CJ, CI] = valores
    return r


def mapa(ax, clases, colores, ventana=None):
    """Mapa de clases enteras (0, 1, …) sobre la rejilla; NaN = fuera de la zona."""
    ax.imshow(raster(clases), origin="lower", extent=EXT, cmap=ListedColormap(colores),
              vmin=-0.5, vmax=len(colores) - 0.5, interpolation="nearest")
    encuadre(ax, ventana)


def encuadre(ax, ventana=None):
    ax.set_aspect("equal")
    ax.axis("off")
    if ventana:
        ax.set_xlim(ventana[0], ventana[1])
        ax.set_ylim(ventana[2], ventana[3])


def mapa_gente(ax, ventana=None):
    ax.imshow(raster(PSIN), origin="lower", extent=EXT, cmap=AMBAR, norm=PERSONAS, interpolation="nearest")
    encuadre(ax, ventana)


def mapa_marginacion(ax, ventana=None):
    mapa(ax, GRADO_I + 1, [SILUETA] + MORADO, ventana)


def en_ventana(x, y, v):
    return (x >= v[0]) & (x <= v[1]) & (y >= v[2]) & (y <= v[3])


def clinicas(ax, ventana, hueco=True, escala=14, etiquetas=False):
    """Clínicas de hoy en blanco (círculo hueco, tamaño = médicos)."""
    m = en_ventana(OF.x.values, OF.y.values, ventana)
    o = OF[m]
    if hueco:
        ax.scatter(o.x, o.y, s=60 + escala * o.cap, facecolors="none", edgecolors=CLIN, linewidths=2.4, zorder=6)
    else:
        ax.scatter(o.x, o.y, s=60 + escala * o.cap, c=CLIN, edgecolors=FONDO, linewidths=1.5, zorder=6)
    return o


def escala_km(ax, v, km=1, color=TXT):
    x0, y0 = v[0] + 300, v[2] + 300
    ax.plot([x0, x0 + km * 1000], [y0, y0], color=color, lw=3, zorder=7)
    ax.text(x0 + km * 500, y0 + 140, f"{km} km", ha="center", color=color, fontsize=17, zorder=7)


def recuadro(ax, v, color=TXT, lw=2):
    ax.add_patch(plt.Rectangle((v[0], v[2]), v[1] - v[0], v[3] - v[2], fill=False, ec=color, lw=lw, zorder=8))


def red_local(cx, cy, R):
    """Subgrafo de la red peatonal en una caja de lado 2R alrededor de (cx, cy)."""
    z = np.load(INT / "red_peatonal.npz")
    xy, u, v, L = z["xy"], z["u"], z["v"], z["largo"]
    m = (np.abs(xy[:, 0] - cx) < R) & (np.abs(xy[:, 1] - cy) < R)
    idx = np.flatnonzero(m)
    pos = -np.ones(len(xy), int)
    pos[idx] = np.arange(len(idx))
    e = m[u] & m[v]
    a, b, l = pos[u[e]], pos[v[e]], np.maximum(L[e], 1e-3)
    G = sparse.csr_matrix((np.r_[l, l], (np.r_[a, b], np.r_[b, a])), shape=(len(idx),) * 2)
    _, comp = csgraph.connected_components(G, directed=False)
    ok = np.flatnonzero(comp == np.bincount(comp).argmax())
    return xy[idx], a, b, G, ok


def nodo(xy, ok, p):
    return ok[cKDTree(xy[ok]).query(p)[1]]


def ruta(xy, G, s, t):
    _, pred = csgraph.dijkstra(G, directed=False, indices=s, return_predecessors=True)
    c = [t]
    while c[-1] != s:
        c.append(pred[c[-1]])
    return xy[np.array(c[::-1])]


def celda(xy):
    k = np.flatnonzero((CEL.x.values == xy[0]) & (CEL.y.values == xy[1]))
    assert len(k) == 1
    return int(k[0])


def desglose_cuadro(k):
    """E2SFCA de un cuadro, paso a paso, recalculado desde los pares y comprobado contra el pipeline."""
    p = pares()
    ref = OF.cap.sum() / PSIN.sum()
    w = acceso.peso(p.d.values, 2250)
    D = np.bincount(p.j.values, weights=PSIN[p.i.values] * w, minlength=len(OF))   # demanda ponderada
    R = np.divide(OF.cap.values, D, out=np.zeros(len(OF)), where=D > 0)
    q = p[p.i == k].copy()
    q["w"] = acceso.peso(q.d.values, 2250)
    q["med"] = OF.cap.values[q.j]
    q["demanda"] = D[q.j]
    q["gente_alcance"] = [PSIN[p.i.values[p.j.values == j]].sum() for j in q.j]
    q["aporte_mil"] = R[q.j] * q.w * 1000
    q["min"] = q.d / 75            # 4.5 km/h = 75 m por minuto
    q["nombre"] = OF.nom_estab.values[q.j]
    A = q.aporte_mil.sum() / 1000
    assert abs(A / ref - CEL.f.values[k]) < 1e-6, (A / ref, CEL.f.values[k])
    return q.sort_values("d"), A * 1000, ref * 1000


# ══ Parte 1 ═══════════════════════════════════════════════════════════════════
def p1_00_gancho():
    tp = cargar("transporte_publico")["acceso"]["calle_33"]
    cero = PSIN[CEL.f.values == 0].sum()
    assert abs(cero - tp["psin_cero"]) < 1
    fig = lienzo(mill(cero), "personas sin seguro médico no tienen\nuna clínica pública a 30 min caminando",
                 nota="Clínica pública = primer nivel de IMSS-Bienestar y SSA. Sin seguro = sin afiliación (Censo).")
    ax = fig.add_axes([0.02, 0.10, 0.96, 0.62])
    mapa(ax, (CEL.f.values == 0).astype(int), [SILUETA, BAJO])
    guardar(fig, "p1_00_gancho")


def p1_01_clinicas():
    n, med = len(OF), OF.cap.sum()
    assert n == cargar("acceso_e2sfca")["unidades"] == 898 and med == 4668
    rng = np.random.default_rng(1)
    orden = rng.permutation(n)
    fig = lienzo(f"{n}", "clínicas públicas de primer nivel\n(catálogo oficial CLUES)",
                 nota="Tamaño del punto = médicos de la unidad (Recursos en Salud 2025).")
    cont = fig.texts[0]
    sub = fig.sub
    sub.set_fontsize(24)
    ax = fig.add_axes([0.02, 0.10, 0.96, 0.62])
    mapa(ax, np.zeros(len(CEL), int), [SILUETA])
    xs, ys, ss = OF.x.values[orden], OF.y.values[orden], 6 + 9 * OF.cap.values[orden]
    sc = ax.scatter([], [], s=[], c=CLIN, alpha=0.9, edgecolors=FONDO, linewidths=0.4)
    N_APAR, N_FIN = 60, 25

    def act(k):
        m = min(n, int(np.ceil(n * min(1, (k + 1) / N_APAR))))
        sc.set_offsets(np.c_[xs[:m], ys[:m]])
        sc.set_sizes(ss[:m])
        cont.set_text(f"{m}")
        sub.set_text(f"{OF.cap.values[orden][:m].sum():,.0f} médicos")
    guardar_anim(fig, act, N_APAR + N_FIN, "p1_01_clinicas")


def _zona_y_barrio(fig, dibujar, leyenda_items, titulo_barrio):
    """Arriba la zona completa con el recuadro del barrio; abajo el zoom al barrio."""
    ax = fig.add_axes([0.0, 0.44, 0.62, 0.32])
    dibujar(ax, None)
    recuadro(ax, BARRIO, lw=2.2)
    leyenda(fig, 0.63, 0.735, leyenda_items)
    fig.text(0.06, 0.425, titulo_barrio, fontsize=21, fontweight="bold", va="top")
    az = fig.add_axes([0.06, 0.085, 0.88, 0.315])
    dibujar(az, BARRIO)
    recuadro(az, BARRIO, lw=2.2)
    escala_km(az, BARRIO)
    return ax, az


def p1_02_gente():
    tot = PSIN.sum()
    assert abs(tot - cargar("acceso_e2sfca")["Total"]["psin"]) < 1
    q25, q50, q90 = np.percentile(PSIN[PSIN > 0], [25, 50, 90])
    ejemplos = [round(q25), round(q50), round(q90)]      # 5, 14 y 59 personas por cuadro
    fig = lienzo(mill(tot, 1), "personas sin seguro médico, repartidas\nen cuadros de 100 × 100 m",
                 nota="Cada zona del Censo 2020 (AGEB urbana) se reparte por igual entre sus cuadros: son estimaciones,\n"
                      "no domicilios. Ejemplos de la leyenda: cuartil bajo, mediana y percentil 90 de los cuadros.")
    _, az = _zona_y_barrio(
        fig, mapa_gente,
        [(AMBAR(PERSONAS(e)), f"{e} personas") for e in ejemplos] + [(AMBAR(1.0), "100 o más")],
        f"Zoom: {NOMBRE_BARRIO}")
    fig.text(0.63, 0.735 - 4 * 0.028 - 0.01, "por cuadro", color=TXT3, fontsize=15, va="top")
    o = clinicas(az, BARRIO)
    fig.text(0.94, 0.425, f"○ = clínica ({len(o)})", color=TXT2, fontsize=17, va="top", ha="right")
    guardar(fig, "p1_02_gente")
    return ejemplos


def p1_03_calles():
    """Área a 30 min por calle desde una clínica, contra el círculo de 2.25 km."""
    p = pares()
    arbol = cKDTree(CEL[["x", "y"]].values)
    # Parte de la gente dentro del círculo de 2.25 km que de verdad está a ≤ 2.25 km por calle.
    # Se muestra la clínica de CDMX (con ≥ 1,400 celdas en el círculo) más cercana a la mediana.
    por_j = p.groupby("j").i.apply(np.asarray)
    cand = []
    for j in range(len(OF)):
        dentro = np.asarray(arbol.query_ball_point(OF[["x", "y"]].values[j], 2250), dtype=int)
        if not len(dentro) or PSIN[dentro].sum() == 0:
            continue
        alc = por_j.get(j, np.array([], int))
        cand.append((j, PSIN[alc].sum() / PSIN[dentro].sum(), len(dentro), OF.region.values[j]))
    cand = pd.DataFrame(cand, columns=["j", "frac", "celdas", "region"])
    med_todas = float(cand.frac.median())
    cdmx = cand[(cand.region == "CDMX") & (cand.celdas >= 1400)]
    j = int(cdmx.iloc[(cdmx.frac - cdmx.frac.median()).abs().argmin()].j)
    frac = float(cand.set_index("j").frac[j])
    fx, fy = OF.x.values[j], OF.y.values[j]
    xy, a, b, G, ok = red_local(fx, fy, 3200)
    s = nodo(xy, ok, (fx, fy))
    d = csgraph.dijkstra(G, directed=False, indices=s, limit=2400)
    de = np.maximum(d[a], d[b])
    segs = np.stack([xy[a], xy[b]], axis=1)
    fig = lienzo("30 min", "caminando son 2.25 km… por las calles,\nno en línea recta",
                 nota=f"Red peatonal de OpenStreetMap a 4.5 km/h. Clínica: {OF.nom_estab.values[j]}.\n"
                      f"Mediana de las {len(cand)} clínicas: por calle se alcanza el {med_todas * 100:.0f}% de la gente del círculo.",
                 sub="")
    sub = fig.sub
    ax = fig.add_axes([0.02, 0.09, 0.96, 0.62])
    ax.add_collection(LineCollection(segs, colors=CALLE, linewidths=0.6))
    lc = LineCollection(segs[:0], colors=NEUTRO, linewidths=1.4)
    ax.add_collection(lc)
    circ = plt.Circle((fx, fy), 0, fill=False, ec=TXT, lw=2, ls=(0, (4, 3)))
    ax.add_patch(circ)
    ax.plot(fx, fy, "o", ms=20, mfc="none", mec=CLIN, mew=3, zorder=5)
    ax.set_xlim(fx - 2700, fx + 2700); ax.set_ylim(fy - 4800, fy + 4800)
    ax.set_aspect("equal"); ax.axis("off")
    ax.text(fx, fy - 2250 - 260, "círculo ingenuo de 2.25 km", ha="center", va="top", color=TXT, fontsize=19)
    N, FIN = 60, 30

    def act(k):
        t = 2250 * min(1, (k + 1) / N)
        lc.set_segments(segs[de <= t])
        circ.set_radius(t)
        mins = int(round(30 * t / 2250))
        sub.set_text(f"Por calle se alcanza el {frac * 100:.0f}% de la gente\nque cabe en el círculo"
                     if k >= N else f"{mins} min")
    guardar_anim(fig, act, N + FIN, "p1_03_calles")
    return frac, med_todas




def p1_03c_capas():
    """Las capas apiladas en perspectiva sobre el mismo barrio, cayendo en un solo cuadro."""
    k = celda(CUADRO)
    cx, cy = CUADRO
    L = 3500   # 35 cuadros: incluye las dos clínicas que alcanza el cuadro
    v = (cx - L / 2, cx + L / 2, cy - L / 2, cy + L / 2)
    fig = plt.figure(figsize=(W, H), dpi=DPI)
    fig.text(0.06, 0.955, "Todo se junta\nen cada cuadro", fontsize=50, fontweight="bold", va="top", linespacing=1.1)
    fig.text(0.06, 0.80, "Calles, gente y médicos dan el acceso de cada cuadro.\n"
             "La marginación no entra al cálculo: sirve para decidir\na quién atender primero.",
             fontsize=20, color=TXT2, va="top", linespacing=1.35)
    fig.text(0.06, 0.03, f"{NOMBRE_BARRIO}: 3.5 × 3.5 km alrededor del cuadro que se sigue en la siguiente gráfica.\n"
             + FUENTE, fontsize=12.5, color=TXT3, va="bottom", linespacing=1.4)
    ax = fig.add_axes([0.0, 0.08, 1.0, 0.62])
    ax.set_xlim(-0.05, 2.0); ax.set_ylim(-0.08, 2.12); ax.axis("off")
    SK, SY = 0.42, 0.30   # perspectiva: inclinación y aplastamiento

    def T(off):
        return Affine2D(np.array([[1, SK, 0], [0, SY, off], [0, 0, 1]])) + ax.transData

    def uv(x, y):
        return (np.asarray(x) - v[0]) / L, (np.asarray(y) - v[2]) / L

    capas = [("clínicas\n(n.º = médicos)", 1.70), ("gente\nsin seguro", 1.22), ("calles", 0.74),
             ("marginación\n(para priorizar)", 0.0)]
    # v empieza en un borde de cuadro (centros en múltiplos de 100): 35 cuadros exactos
    i0 = int(round((v[0] + 50 - X0) / 100)); i1 = i0 + int(L / 100)
    j0 = int(round((v[2] + 50 - Y0) / 100)); j1 = j0 + int(L / 100)
    ext01 = (0, 1, 0, 1)
    uc, vc = uv(cx, cy)
    for nombre, off in capas:
        t = T(off)
        ax.add_patch(Polygon([(0, 0), (1, 0), (1, 1), (0, 1)], closed=True, fc="#222220", ec=TXT3, lw=1.2,
                             transform=t, zorder=1))
        if nombre.startswith("gente"):
            ax.imshow(raster(PSIN)[j0:j1, i0:i1], origin="lower", extent=ext01, cmap=AMBAR, norm=PERSONAS,
                      interpolation="nearest", transform=t, zorder=2)
        elif nombre.startswith("marginación"):
            ax.imshow((raster(GRADO_I + 1))[j0:j1, i0:i1], origin="lower", extent=ext01,
                      cmap=ListedColormap([SILUETA] + MORADO), vmin=-0.5, vmax=5.5,
                      interpolation="nearest", transform=t, zorder=2)
        elif nombre == "calles":
            xy, a, b, _, _ = red_local(cx, cy, L / 2)
            u0, v0 = uv(xy[:, 0], xy[:, 1])
            segs = np.stack([np.c_[u0[a], v0[a]], np.c_[u0[b], v0[b]]], axis=1)
            dentro = ((segs >= 0) & (segs <= 1)).all(axis=(1, 2))
            ax.add_collection(LineCollection(segs[dentro], colors=NEUTRO, linewidths=0.5, transform=t, zorder=2))
        else:
            o = OF[en_ventana(OF.x.values, OF.y.values, v)]
            uo, vo = uv(o.x.values, o.y.values)
            ax.scatter(uo, vo, s=90 + 30 * o.cap, facecolors="none", edgecolors=CLIN, linewidths=2.2,
                       transform=t, zorder=3)
            for a_, b_, m_ in zip(uo, vo, o.cap):
                ax.text(a_ + 0.03, b_ + 0.05, f"{m_:.0f}", fontsize=14, color=TXT, transform=t, zorder=4)
        # el cuadro que se sigue, en la misma posición de cada capa
        ax.add_patch(Polygon([(uc - .03, vc - .03), (uc + .03, vc - .03), (uc + .03, vc + .03), (uc - .03, vc + .03)],
                             closed=True, fill=False, ec=TXT, lw=2.6, transform=t, zorder=5))
        ax.text(1 + SK + 0.03, off + SY / 2, nombre, fontsize=18, color=TXT2, va="center", ha="left")
    # línea que cae por todas las capas hasta el cuadro de abajo
    xs = uc + SK * vc
    ax.plot([xs, xs], [capas[-1][1] + SY * vc, capas[0][1] + SY * vc], color=TXT, lw=1.6, ls=(0, (3, 3)), zorder=6)
    ax.plot([xs], [capas[-1][1] + SY * vc], "s", ms=12, color=TXT, zorder=7)
    guardar(fig, "p1_03c_capas")




def p1_04a_esquema_acceso():
    """Dibujo ilustrativo (no datos): la misma clínica con mucha o poca gente alrededor."""
    e2 = cargar("acceso_e2sfca")
    ref = e2["promedio_metropolitano_por_1000"]
    assert abs(ref - e2["Total"]["capacidad"] / e2["Total"]["psin"] * 1000) < 1e-9 and round(ref, 2) == 0.64
    POR_PUNTO, MED = 50, 3
    casos = [(12000, 0.51), (1500, 0.175)]   # (personas, y0 del panel)
    fig = plt.figure(figsize=(W, H), dpi=DPI)
    fig.text(0.06, 0.955, "Tener una clínica\ncerca no basta", fontsize=50, fontweight="bold", va="top",
             linespacing=1.1)
    fig.text(0.06, 0.815, "importa cuánta gente compite por sus médicos", fontsize=23, color=TXT2, va="top")
    fig.text(0.06, 0.03, f"Ejemplo ilustrativo. El promedio de la zona es {ref:.2f} médicos por cada mil;\n"
             f"acceso bajo es menos de la mitad ({ref / 2:.2f}). Cada punto = {POR_PUNTO} personas.\n" + FUENTE,
             fontsize=12.5, color=TXT3, va="bottom", linespacing=1.4)
    rng = np.random.default_rng(4)
    for gente, y0 in casos:
        tasa = MED / gente * 1000
        bajo = tasa < ref / 2
        col = BAJO if bajo else AZUL
        ax = fig.add_axes([0.02, y0, 0.54, 0.24])
        n = gente // POR_PUNTO
        r = np.sqrt(rng.uniform(0.04, 1, n)) * 0.92
        th = rng.uniform(0, 2 * np.pi, n)
        ax.scatter(r * np.cos(th), r * np.sin(th), s=34, c=col, linewidths=0, alpha=0.95)
        ax.add_patch(plt.Circle((0, 0), 1, fill=False, ec=TXT3, lw=1.8, ls=(0, (4, 3))))
        ax.plot(0, 0, "o", ms=26, mfc="none", mec=CLIN, mew=4, zorder=5)
        ax.set_xlim(-1.08, 1.08); ax.set_ylim(-1.08, 1.08); ax.set_aspect("equal"); ax.axis("off")
        fig.text(0.60, y0 + 0.205, f"{MED} médicos\n{gente:,} personas", fontsize=24, va="top", linespacing=1.3)
        fig.text(0.60, y0 + 0.115, f"{tasa:g}", fontsize=52, fontweight="bold", color=col, va="top")
        fig.text(0.60, y0 + 0.045, "médicos por\ncada mil", fontsize=19, color=TXT2, va="top", linespacing=1.3)
        fig.text(0.60, y0 - 0.005, "acceso bajo" if bajo else "acceso suficiente", fontsize=19,
                 fontweight="bold", color=TXT, va="top")
    fig.text(0.06, 0.13, "○ = clínica · círculo punteado = 30 min caminando.", fontsize=15, color=TXT3, va="top")
    guardar(fig, "p1_04a_esquema_acceso")


def p1_04_acceso():
    ent = cargar("entregables_calle")
    ref = cargar("acceso_e2sfca")["promedio_metropolitano_por_1000"]
    bajo = PSIN[CEL.f.values < 0.5].sum()
    assert abs(bajo - cargar("red_real")["f3"]["psin_bajo_calle"]) < 1
    fig = lienzo(mill(bajo), "personas tienen acceso bajo:\nmenos de la mitad de los médicos\nque les tocarían",
                 sub=f"CDMX {ent['CDMX']['pct_bajo']:.0f}%   ·   Edomex {ent['EDOMEX']['pct_bajo']:.0f}%",
                 nota="Acceso = médicos a 30 min por calle, divididos entre toda la gente que compite por ellos\n"
                      f"(E2SFCA). Bajo = menos de la mitad del promedio de la zona ({ref:.2f} médicos por mil).")
    fig.sub.set_y(0.705)
    ax = fig.add_axes([0.02, 0.10, 0.96, 0.58])
    mapa(ax, (CEL.f.values < 0.5).astype(int), [SUF, BAJO])
    fig.text(0.06, 0.665, "■", color=BAJO, fontsize=22, va="top")
    fig.text(0.10, 0.665, "acceso bajo", color=TXT2, fontsize=19, va="top")
    fig.text(0.40, 0.665, "■", color=SUF, fontsize=22, va="top")
    fig.text(0.44, 0.665, "acceso suficiente", color=TXT2, fontsize=19, va="top")
    guardar(fig, "p1_04_acceso")


def p1_05_topologia():
    """El agua sube por el mapa de acceso: las zonas bajo el agua son las islas de mal acceso."""
    pc = cargar("persistencia_calle")
    asig = np.load(INT / "asig_cuencas_calle.npy")
    n_isl = pc["islas"]["estables_sin_resto"]
    frac = pc["psin_bajo"]["en_islas_estables"] / pc["psin_bajo"]["total"]
    assert n_isl == 760 and asig.max() == 759
    v = (495000, 520000, 2122000, 2166000)
    yp = 2140500
    fila = CEL[(CEL.y == yp) & CEL.x.between(v[0], v[1])].sort_values("x")
    fig = plt.figure(figsize=(W, H), dpi=DPI)
    t_cif = fig.text(0.06, 0.95, "", fontsize=72, fontweight="bold", va="top")
    t_tit = fig.text(0.06, 0.865, "el mapa como terreno: al subir el agua\nse forman islas de mal acceso",
                     fontsize=25, va="top", linespacing=1.3)
    fig.text(0.06, 0.03, "Persistencia H₀ de la superficie de acceso (filtración por subniveles).\n"
             "Isla = nace con acceso < 0.5 y dura ≥ 0.25; estable en 100 réplicas de capacidad.\n" + FUENTE,
             fontsize=12.5, color=TXT3, va="bottom", linespacing=1.4)
    axp = fig.add_axes([0.08, 0.60, 0.88, 0.17])
    fx = fila.x.values / 1000
    fv = np.minimum(fila.f.values, 1.6)
    axp.fill_between(fx, fv, -0.05, color="#3d3c37", step="mid")
    agua = [axp.fill_between(fx, 0, 0, color=BAJO, alpha=0.8, step="mid")]
    nivel = axp.axhline(0, color=TXT, lw=1.5, ls=(0, (4, 3)))
    axp.set_ylim(-0.05, 1.6); axp.set_xlim(fx.min(), fx.max())
    axp.set_yticks([0, 0.5, 1]); axp.set_yticklabels(["0", "½", "1"], fontsize=16)
    axp.set_xticks([])
    for s in ["top", "right", "bottom"]:
        axp.spines[s].set_visible(False)
    axp.set_ylabel("acceso", fontsize=17)
    axm = fig.add_axes([0.02, 0.10, 0.96, 0.48])
    img = axm.imshow(raster(np.zeros(len(CEL))), origin="lower", extent=EXT,
                     cmap=ListedColormap(["#3d3c37", BAJO]), vmin=-0.5, vmax=1.5, interpolation="nearest")
    axm.axhline(yp, color=TXT, lw=1, ls=(0, (2, 3)), alpha=0.7)
    encuadre(axm, v)
    N, FIN = 70, 35
    f_all = CEL.f.values
    est = (asig >= 0).astype(float)

    def act(k):
        t = 0.5 * min(1, (k + 1) / N)
        agua[0].remove()
        agua[0] = axp.fill_between(fx, np.minimum(fv, t), np.where(fv < t, t, np.minimum(fv, t)),
                                   where=fv < t, color=BAJO, alpha=0.85, step="mid")
        nivel.set_ydata([t, t])
        if k < N:
            img.set_data(raster((f_all < t).astype(float)))
            t_cif.set_text(f"nivel {t:.2f}")
        else:
            img.set_data(raster(est))
            t_cif.set_text(f"{n_isl} islas")
            t_tit.set_text(f"estables en toda la zona, con el {frac * 100:.0f}% de la\ngente con acceso bajo "
                           "(aquí, el oriente)")
    guardar_anim(fig, act, N + FIN, "p1_05_topologia")


# ══ Parte 2 · Escenarios ═════════════════════════════════════════════════════
# Regla del esquema: el título es la pregunta en palabras simples, debajo la respuesta en una
# línea y la imagen es concreta. Sin histogramas, sin «p», sin «brecha» sin definir.
def p2_A_reubicar():
    """🎬 999 ciudades imaginarias: cada reacomodo cae como un punto en una pila."""
    no = cargar("nulo_oferta")
    s1 = no["S1"]["psin_bajo"]
    sims = pd.read_parquet(INT / "nulo_oferta_S1_clues.parquet").psin_bajo.values
    s2 = pd.read_parquet(INT / "nulo_oferta_S2_clues.parquet").psin_bajo.values
    assert len(sims) == no["n_sim"]["S1"] == 999 and abs(np.median(sims) - s1["mediana_nulo"]) < 1
    assert abs(np.median(s2) - no["S2"]["psin_bajo"]["mediana_nulo"]) < 1
    hoy, hoy_orig = s1["observado"], no["redondeo"]["real"]["psin_bajo"]
    ganan = int((sims <= hoy).sum())
    assert ganan == 0 and (sims <= hoy_orig).sum() == 0      # ningún reacomodo le gana a hoy
    fig = lienzo_pregunta("¿Y si las clínicas\nestuvieran mejor puestas?",
                          f"Las movimos {len(sims)} veces. Ningún reacomodo\ndejó a menos gente con acceso bajo que hoy.",
                          nota="Cada punto: las mismas clínicas y médicos de cada municipio, puestas al azar dentro de él, con más\n"
                               f"probabilidad donde vive más gente sin seguro. «Hoy» usa las clínicas ajustadas a la misma rejilla de\n"
                               f"500 m ({mill(hoy)}; sin ajustar, {mill(hoy_orig)}). Repartidas parejo (200 veces): {mill(np.median(s2))}.")
    ax = fig.add_axes([0.08, 0.15, 0.86, 0.52])
    ancho = 10000
    lo = 3.15e6
    b = np.floor((sims - lo) / ancho).astype(int)
    rng = np.random.default_rng(7)
    orden = rng.permutation(len(sims))
    pila = np.zeros(b.max() + 2, int)
    pos = np.zeros((len(sims), 2))
    for i in orden:                       # posición final de cada punto en su columna
        pos[i] = (lo + (b[i] + 0.5) * ancho, pila[b[i]])
        pila[b[i]] += 1
    alto = pila.max() + 4
    ax.set_xlim(3.15e6, 3.86e6); ax.set_ylim(-1.5, alto)
    ax.set_xticks([3.2e6, 3.4e6, 3.6e6, 3.8e6]); ax.set_xticklabels(["3.2 M", "3.4 M", "3.6 M", "3.8 M"], fontsize=18)
    ax.set_yticks([])
    for s in ["top", "right", "left"]:
        ax.spines[s].set_visible(False)
    ax.set_xlabel("personas con acceso bajo  (más a la izquierda = mejor)", fontsize=18)
    sc = ax.scatter([], [], s=26, c=GRIS, linewidths=0)
    hoy_pt = ax.scatter([hoy], [0], s=420, c=CLIN, edgecolors=FONDO, linewidths=2, zorder=5, visible=False)
    hoy_tx = ax.text(hoy, 4, "", ha="center", va="bottom", fontsize=22, fontweight="bold", color=TXT)
    cuenta = ax.text(3.86e6, alto - 1, "", ha="right", va="top", fontsize=20, color=TXT2)
    ax.text(np.median(sims), -1.2, "", fontsize=1)
    N, FIN = 60, 40

    def act(k):
        m = min(len(sims), int(len(sims) * min(1, (k + 1) / N)))
        sel = orden[:m]
        sc.set_offsets(pos[sel])
        cuenta.set_text(f"{m} ciudades imaginarias")
        if k >= N:
            hoy_pt.set_visible(True)
            hoy_tx.set_text(f"hoy\n{mill(hoy)}")
            fig.resp.set_text(f"Las movimos {len(sims)} veces. Ningún reacomodo ({ganan} de {len(sims)})\n"
                              "dejó a menos gente con acceso bajo que hoy.\nLo que falta no es acomodo: son clínicas.")
    guardar_anim(fig, act, N + FIN, "p2_A_reubicar")
    return ganan, float(sims.min()), hoy, hoy_orig


def p2_B_abrir_ampliar():
    cu = cargar("cuantas_unidades")
    cur = pd.read_csv(AUD / "cuantas_unidades_curvas.csv")
    base = cu["linea_base"]["brecha"]
    ab, am = cu["abrir_vs_ampliar"]["brecha_25"]["medicos_abrir"], cu["abrir_vs_ampliar"]["brecha_25"]["medicos_ampliar_saturadas"]
    k25 = cu["cuantas"]["brecha"]["brecha_25"]["k"]
    k50 = cu["cuantas"]["brecha"]["brecha_50"]["k"]
    assert (k25, ab, am, k50) == (49, 147.0, 696.0, 130) and not cu["abrir_vs_ampliar"]["brecha_50"]["llega_ampliar"]
    curvas = {}
    for sol in ["brecha", "ampliar"]:
        c = cur[cur.solucion == sol].sort_values("K")
        curvas[sol] = (np.r_[0, c.K.values * 3], np.r_[0, 100 * (1 - c.brecha.values / base)])
    fig = lienzo_pregunta("¿Abrir clínicas nuevas\no ampliar las que hay?",
                          f"Para quitar una cuarta parte de la falta de acceso:\nabrir {k25} clínicas ({ab:.0f} médicos) "
                          f"o ampliar con {am:.0f}.\nLas nuevas llegan a donde no hay ninguna; ampliar\n"
                          "solo ayuda a quien ya tenía una cerca.",
                          nota="Falta de acceso = cuánto le falta a cada persona para llegar al umbral de acceso bajo, sumado por\n"
                               "persona y con peso doble en marginación alta (no es «número de personas»). Abrir: sedes de 3 médicos\n"
                               f"elegidas una por una; con {k50} se quita la mitad. Ampliar: +3 médicos a una unidad saturada.\n"
                               "Cuenta médicos, no costos.")
    ax = fig.add_axes([0.13, 0.17, 0.80, 0.43])
    for y in [25, 50]:
        ax.axhline(y, color=CALLE, lw=1.2)
        ax.text(1495, y + 1, f"{y}%", color=TXT3, fontsize=17, ha="right", va="bottom")
    l1, = ax.plot([], [], color=VERDE, lw=4.5, solid_capstyle="round")
    l2, = ax.plot([], [], color=GRIS, lw=4, ls=(0, (6, 3)))
    t1 = ax.text(255, 70, "", color=TXT, fontsize=22, fontweight="bold", ha="left")
    t2 = ax.text(1050, 33, "", color=TXT2, fontsize=22, fontweight="bold", ha="left")
    p1, = ax.plot([], [], "o", color=VERDE, ms=13, mec=FONDO, mew=2)
    p2, = ax.plot([], [], "o", color=GRIS, ms=13, mec=FONDO, mew=2)
    ax.set_xlim(0, 1500); ax.set_ylim(0, 100)
    ax.set_xlabel("médicos agregados", fontsize=19)
    ax.set_ylabel("falta de acceso quitada (%)", fontsize=19)
    ax.tick_params(labelsize=17)
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    N, FIN = 70, 30

    def act(k):
        lim = 1500 * min(1, (k + 1) / N)
        for (x, y), ln in zip(curvas.values(), [l1, l2]):
            m = x <= lim
            ln.set_data(x[m], y[m])
        t1.set_text("abrir" if lim >= 400 else "")
        t2.set_text("ampliar" if lim >= 1050 else "")
        p1.set_data([ab] if lim >= ab else [], [25] if lim >= ab else [])
        p2.set_data([am] if lim >= am else [], [25] if lim >= am else [])
    guardar_anim(fig, act, N + FIN, "p2_B_abrir_ampliar")


def p2_C_prioridad():
    oc = cargar("optimizacion_calle")
    sit = pd.read_csv(AUD / "optimizacion_sitios_calle.csv")
    ev = oc["evaluacion"]
    mc, br = ev["cobertura"]["20"], ev["brecha"]["20"]
    red = oc["criterio"]["reduccion_brecha"]
    sinp = oc["brecha_sin_peso_marginacion"]
    pts = {o: sit[(sit.objetivo == o) & (sit.orden <= 20)] for o in ["cobertura", "brecha"]}
    iguales = int(sum(np.hypot(*(pts["brecha"][["x", "y"]].values - r).T).min() <= 500
                      for r in pts["cobertura"][["x", "y"]].values))
    assert iguales == 5 and sinp["sitios_iguales_500m"] == 4
    fig = lienzo_pregunta("20 clínicas nuevas:\n¿a quién primero?",
                          f"Cada opción elige otros lugares: solo {iguales} de 20 coinciden.",
                          nota="Sedes de 3 médicos elegidas una por una; las dos opciones dan peso doble a la marginación alta.\n"
                               f"Sin ese peso, «los que están peor» saca del acceso bajo a solo "
                               f"{sinp['evaluacion']['salen_de_bajo_psin'] / 1e3:.1f} mil personas.\n"
                               "Falta de acceso = lo que le falta a cada persona para el umbral, sumado.")
    v = (494000, 520000, 2126000, 2152000)
    fuera = {o: int((~en_ventana(p.x.values, p.y.values, v)).sum()) for o, p in pts.items()}
    textos = {"cobertura": ("Llegar a\nmás gente", mc, red["cobertura"]),
              "brecha": ("Llegar a los\nque están peor", br, red["brecha"])}
    for o, y0 in [("cobertura", 0.41), ("brecha", 0.09)]:
        ax = fig.add_axes([0.02, y0, 0.55, 0.31])
        mapa(ax, (CEL.f.values < 0.5).astype(int), [SUF, BAJO], ventana=v)
        p = pts[o]
        ax.scatter(p.x, p.y, marker="*", s=700, c=VERDE, edgecolors=FONDO, linewidths=2, zorder=5)
        t, e, rb = textos[o]
        fig.text(0.60, y0 + 0.29, t, fontsize=26, fontweight="bold", va="top", linespacing=1.15)
        fig.text(0.60, y0 + 0.205, mil(e["salen_de_bajo_psin"]), fontsize=36, fontweight="bold", va="top")
        fig.text(0.60, y0 + 0.16, "salen del acceso bajo", fontsize=17, color=TXT2, va="top")
        fig.text(0.60, y0 + 0.12, f"{100 * e['salen_de_bajo_alta_marg_psin'] / e['salen_de_bajo_psin']:.0f}% de ellos "
                 f"en\nmarginación alta\nfalta de acceso: −{100 * rb:.1f}%", fontsize=17, color=TXT2, va="top",
                 linespacing=1.35)
        if fuera[o]:
            fig.text(0.60, y0 + 0.005, f"+{fuera[o]} estrellas fuera del recuadro", fontsize=13.5, color=TXT3)
    leyenda(fig, 0.06, 0.79, [(BAJO, "acceso bajo antes de abrir"), (SUF, "acceso suficiente")], dy=0.026, fs=16)
    fig.add_artist(plt.Line2D([0.575], [0.781], marker="*", ms=24, color=VERDE, mec=FONDO, mew=1.5,
                              transform=fig.transFigure))
    fig.text(0.60, 0.79, "clínica nueva", color=TXT2, fontsize=16, va="top")
    guardar(fig, "p2_C_prioridad")
    return iguales, fuera




def p2_E_horizonte():
    """Un solo mapa del barrio con lo que queda a 15 min y lo que solo queda a 30."""
    sf = cargar("sensibilidad_f3")["resultados"]
    p = pares()
    ref = OF.cap.sum() / PSIN.sum()
    q = p[p.d <= 1125]
    A, _ = acceso.e2sfca_pares(q.i.values, q.j.values, acceso.peso(q.d.values, 1125), PSIN, OF.cap.values, len(CEL))
    f15 = A / ref
    assert abs(PSIN[f15 == 0].sum() - sf["G15"]["psin_cero"]) < 1
    assert abs(PSIN[CEL.f.values == 0].sum() - sf["base"]["psin_cero"]) < 1
    dmin = np.full(len(CEL), np.inf)
    np.minimum.at(dmin, p.i.values, p.d.values)
    # «alcanza una clínica» = acceso > 0 en cada horizonte (no basta d ≤ d0: en d = d0 el peso es 0)
    clase = np.where(f15 > 0, 2, np.where(CEL.f.values > 0, 1, 0))
    mb = en_ventana(CEL.x.values, CEL.y.values, BARRIO)
    cero30, cero15 = PSIN[mb & (CEL.f.values == 0)].sum(), PSIN[mb & (f15 == 0)].sum()
    fig = lienzo_pregunta("¿Qué es «cerca»?",
                          f"Si «cerca» son 15 minutos y no 30, la gente sin\nninguna clínica pública al alcance pasa de "
                          f"{mill(sf['base']['psin_cero'])}\na {mill(sf['G15']['psin_cero'])}.",
                          nota="Mismas clínicas y mismo modelo; solo cambia cuánto se camina por calle (2,250 m o 1,125 m).\n"
                               f"En este barrio, sin clínica: {cero30 / 1e3:.1f} mil a 30 min y {cero15 / 1e3:.1f} mil a 15 min. "
                               f"Acceso bajo, otra medida:\n{mill(sf['base']['psin_bajo'])} a 30 min y {mill(sf['G15']['psin_bajo'])} a 15 min.")
    ax = fig.add_axes([0.10, 0.27, 0.80, 0.45])
    mapa(ax, clase, ["#2b2b28", "#6a6962", "#c9c8bf"], BARRIO)
    clinicas(ax, BARRIO, hueco=False, escala=10)
    escala_km(ax, BARRIO)
    leyenda(fig, 0.06, 0.25, [("#c9c8bf", "alcanza una clínica en 15 min"), ("#6a6962", "solo en 30 min"),
                              ("#2b2b28", "ninguna ni en 30 min")], dy=0.028, fs=17)
    fig.text(0.06, 0.155, NOMBRE_BARRIO + " · ● = clínica", fontsize=15, color=TXT3, va="top")
    guardar(fig, "p2_E_horizonte")
    return cero30, cero15


# ══ Parte 3 · Conclusiones ═══════════════════════════════════════════════════
CASO_RODEO = (475600.0, 2139700.0)   # Álvaro Obregón, barrancas del poniente


def p3_2_rodeo():
    cz = pd.read_parquet(INT / "ceros_calle.parquet")
    k = celda(CASO_RODEO)
    assert CEL.f.values[k] == 0
    j = cKDTree(OF[["x", "y"]].values).query(CASO_RODEO)[1]
    ux, uy = OF.x.values[j], OF.y.values[j]
    recta = np.hypot(ux - CASO_RODEO[0], uy - CASO_RODEO[1])
    assert abs(recta - cz.d_recta.values[k]) < 1
    cx, cy = (CASO_RODEO[0] + ux) / 2, (CASO_RODEO[1] + uy) / 2
    xy, a, b, G, ok = red_local(cx, cy, 5000)
    s, t = nodo(xy, ok, CASO_RODEO), nodo(xy, ok, (ux, uy))
    dist = csgraph.dijkstra(G, directed=False, indices=s)
    P = ruta(xy, G, s, t)
    largo = dist[t] + np.hypot(*(xy[s] - CASO_RODEO)) + np.hypot(*(xy[t] - (ux, uy)))
    acum = np.r_[0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]
    caja = (P[:, 0].min() - 500, P[:, 0].max() + 500, P[:, 1].min() - 500, P[:, 1].max() + 500)
    ancho, alto = caja[1] - caja[0], caja[3] - caja[2]
    if alto / ancho < 1.55:   # forzar vertical
        extra = (1.55 * ancho - alto) / 2
        caja = (caja[0], caja[1], caja[2] - extra, caja[3] + extra)
    else:
        extra = (alto / 1.55 - ancho) / 2
        caja = (caja[0] - extra, caja[1] + extra, caja[2], caja[3])
    fig = lienzo(f"{recta:.0f} m", "en línea recta a la clínica…",
                 sub="", nota=f"Álvaro Obregón, CDMX. Clínica: {OF.nom_estab.values[j]}. Ruta más corta por la red\n"
                              f"peatonal de OpenStreetMap. La clínica más cercana por calle queda a "
                              f"{cz.d_calle.values[k] / 1000:.1f} km: más de 30 min.")
    sub = fig.sub
    ax = fig.add_axes([0.02, 0.09, 0.96, 0.57])
    segs = np.stack([xy[a], xy[b]], axis=1)
    ax.add_collection(LineCollection(segs, colors=CALLE, linewidths=0.7))
    ax.plot([CASO_RODEO[0], ux], [CASO_RODEO[1], uy], color=TXT, lw=2.5, ls=(0, (4, 3)))
    linea, = ax.plot([], [], color=NEUTRO, lw=4.5, solid_capstyle="round")
    ax.plot(*CASO_RODEO, "o", ms=20, color=BAJO, mec=FONDO, mew=2.5, zorder=6)
    ax.plot(ux, uy, "o", ms=22, mfc="none", mec=CLIN, mew=3.5, zorder=6)
    ax.text(CASO_RODEO[0] - 150, CASO_RODEO[1], "casa", color=TXT, fontsize=20, ha="right", va="center", fontweight="bold")
    ax.text(ux + 170, uy, "clínica", color=TXT, fontsize=20, ha="left", va="center", fontweight="bold")
    ax.set_xlim(caja[0], caja[1]); ax.set_ylim(caja[2], caja[3]); ax.set_aspect("equal"); ax.axis("off")
    N, FIN = 80, 35

    def act(k2):
        l = acum[-1] * min(1, (k2 + 1) / N)
        m = acum <= l
        linea.set_data(P[m, 0], P[m, 1])
        sub.set_text(f"…y {l / 1000 * largo / acum[-1]:.1f} km por calle" +
                     ("\nNo hay calle que cruce: hay que rodear." if k2 >= N else ""))
    guardar_anim(fig, act, N + FIN, "p3_2_rodeo")
    return recta, largo, cz.d_calle.values[k], OF.nom_estab.values[j]




def p3_4_nulo():
    ne = cargar("nulo_espacial")
    obs = ne["observado"]["frac_bajo_en_islas"] * 100
    sims = pd.read_parquet(INT / "nulo_espacial_N2_clues.parquet").frac_bajo_en_islas.values * 100
    med = ne["N2"]["frac_bajo_en_islas"]["mediana_nulo"] * 100
    assert abs(np.median(sims) - med) < 1e-6
    sec = ne["N2"]["secundarios"]["n_islas"]
    fig = lienzo(f"{obs:.0f}% vs {med:.0f}%",
                 "de la gente con acceso bajo cae en islas:\nen el mapa real y en un mapa al azar",
                 sub=f"Las islas ordenan dónde actuar, pero no prueban\nnada solas. Lo que sí es propio del mapa real:\n"
                     f"está más partido ({sec['observado']} islas contra {sec['mediana_nulo']:.0f}).",
                 nota="Nulo espacial N2: 999 mapas al azar con los mismos ceros, la misma distribución de\n"
                      "valores y la misma correlación espacial hasta 2 km. Las 990 islas, no solo las estables.")
    ax = fig.add_axes([0.10, 0.14, 0.84, 0.44])
    ax.hist(sims, bins=np.linspace(80, 97, 52), color=GRIS, edgecolor=FONDO, linewidth=1.5)
    ax.axvline(obs, color=TXT, lw=4)
    top = ax.get_ylim()[1]
    ax.text(obs - 0.3, top * 0.92, "real", color=TXT, fontsize=24, fontweight="bold", ha="right")
    ax.text(med + 1.6, top * 0.80, "mapas\nal azar", color=TXT2, fontsize=19)
    ax.set_xticks([80, 85, 90, 95]); ax.set_xticklabels(["80%", "85%", "90%", "95%"], fontsize=18)
    ax.set_yticks([])
    for s in ["top", "right", "left"]:
        ax.spines[s].set_visible(False)
    guardar(fig, "p3_4_nulo")


# ══ Ronda 3: más imagen, menos texto ═════════════════════════════════════════
# Regla del esquema: arriba como mucho una cifra o una pregunta corta; etiquetas de una a tres
# palabras; contar con cosas (figuritas, puntos, cuadros) y no con barras; las fuentes, chicas.
def lienzo_tiktok(nota=None):
    """Figura vertical con un solo eje 0–9 × 0–16 (unidades = pulgadas) y la nota chica al pie."""
    fig = plt.figure(figsize=(W, H), dpi=DPI)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off")
    fig.text(0.06, 0.02, (nota + "\n" if nota else "") + FUENTE, fontsize=12, color=TXT3, va="bottom",
             linespacing=1.4)
    return fig, ax


def cifra_arriba(fig, txt="", etiqueta=""):
    """La única cifra grande de arriba y su etiqueta corta."""
    c = fig.text(0.06, 0.955, txt, fontsize=96, fontweight="bold", color=TXT, va="top")
    e = fig.text(0.065, 0.865, etiqueta, fontsize=28, color=TXT2, va="top")
    return c, e


def figura(ax, x, y, h, color, z=5, alpha=1.0):
    """Figurita de persona (cabeza + torso) de alto h, con los pies en y."""
    r = h * 0.18
    cab = plt.Circle((x, y + h - r), r, fc=color, ec="none", zorder=z, alpha=alpha)
    tor = FancyBboxPatch((x - h * 0.21, y), h * 0.42, h * 0.56, boxstyle=f"round,pad=0,rounding_size={h * 0.17}",
                         fc=color, ec="none", zorder=z, alpha=alpha)
    ax.add_patch(cab); ax.add_patch(tor)
    return cab, tor


def suave(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def lineas_gtfs():
    """Trazos (shapes) del GTFS del transporte que usó el análisis, en metros UTM 14N."""
    import zipfile
    from pyproj import Transformer
    nombre = cargar("transporte_publico")["datos"]["gtfs"]
    z = zipfile.ZipFile(RAIZ / "Datos" / "GTFS" / nombre)
    sh = pd.read_csv(z.open("shapes.txt")).sort_values(["shape_id", "shape_pt_sequence"])
    tr = pd.read_csv(z.open("trips.txt"))[["route_id", "shape_id"]].drop_duplicates("shape_id")
    ag = tr.merge(pd.read_csv(z.open("routes.txt"))[["route_id", "agency_id"]]).set_index("shape_id").agency_id
    x, y = Transformer.from_crs(4326, 32614, always_xy=True).transform(sh.shape_pt_lon.values, sh.shape_pt_lat.values)
    sh["x"], sh["y"] = x, y
    st = pd.read_csv(z.open("stops.txt"))
    sx, sy = Transformer.from_crs(4326, 32614, always_xy=True).transform(st.stop_lon.values, st.stop_lat.values)
    orden = ["METRO", "TL", "MB", "TROLE", "CBB", "SUB", "INTERURBANO", "RTP", "CC", "PUMABUS", "SEMOVI"]
    lin = [(ag.get(s, "?"), g[["x", "y"]].to_numpy()) for s, g in sh.groupby("shape_id")]
    lin.sort(key=lambda t: orden.index(t[0]) if t[0] in orden else len(orden))
    return lin, np.c_[sx, sy]


def _cuadro_y_clinicas():
    """El cuadro de Peñón Viejo, su desglose E2SFCA comprobado y las dos clínicas que alcanza."""
    k = celda(CUADRO)
    q, A_mil, ref_mil = desglose_cuadro(k)
    assert abs(ref_mil - cargar("acceso_e2sfca")["promedio_metropolitano_por_1000"]) < 1e-9
    assert CEL.f.values[k] < 0.5 and CEL.grado.values[k] in ("Alto", "Muy alto") and len(q) == 2
    return k, q, A_mil, ref_mil


def _mil_puntos(j):
    """Gente a ≤ 30 min por calle de la clínica j, en puntos de mil personas.

    Se ordenan los cuadros por distancia por calle y el punto n cae en el cuadro donde la suma de
    gente cruza (n + ½) mil: así los puntos reproducen cuánta gente hay y a qué distancia vive."""
    p = pares()
    pj = p[p.j == j].sort_values("d")
    acum = np.cumsum(PSIN[pj.i.values])
    total = acum[-1]
    n = int(round(total / 1000))
    pos = np.searchsorted(acum, (np.arange(n) + 0.5) * total / n)
    return pj, total, pj.i.values[pos], pj.d.values[pos]


def p1_03b_marginacion():
    """Dos estados: marginación alta o muy alta en morado, todo lo demás en gris; se encienden por zona."""
    eq = cargar("equidad_transporte")["veredicto"]["total"]
    con = GRADO_I >= 0
    alta_c = GRADO_I >= 3
    alta = PSIN[alta_c].sum() / PSIN[con].sum() * 100
    assert abs(alta - eq["alta_muy_alta_pct_gente"]) < 1e-6
    fig, ax = lienzo_tiktok("Morado = marginación alta o muy alta (CONAPO 2020, por zona del Censo). "
                            "El porcentaje cuenta\npersonas sin seguro, no superficie del mapa.")
    c, e = cifra_arriba(fig, "", "marginación alta")
    axm = fig.add_axes([0.02, 0.09, 0.96, 0.70])
    img = axm.imshow(raster(np.zeros(len(CEL))), origin="lower", extent=EXT, cmap=ListedColormap([SILUETA, MORADO[3]]),
                     vmin=-0.5, vmax=1.5, interpolation="nearest")
    encuadre(axm)
    # Se encienden zona por zona (AGEB) en orden al azar; la cifra sube con la gente encendida.
    zonas = CEL.CVEGEO.values
    unicas = pd.unique(zonas[alta_c])
    rng = np.random.default_rng(3)
    turno = dict(zip(unicas, rng.permutation(len(unicas))))
    t_cel = np.array([turno.get(z_, -1) if a_ else -1 for z_, a_ in zip(zonas, alta_c)])
    INI, SUBE, FIN = 10, 40, 25

    def act(fr):
        t = suave((fr - INI) / SUBE)
        on = alta_c & (t_cel < t * len(unicas)) if t < 1 else alta_c
        img.set_data(raster(on.astype(float)))
        pct = PSIN[on].sum() / PSIN[con].sum() * 100
        c.set_text(f"{pct:.0f}%" if fr >= INI else "")
    guardar_anim(fig, act, INI + SUBE + FIN, "p1_03b_marginacion", fps=15)
    return round(alta, 1)


def p1_03d1_alcance():
    """Quién compite por la clínica: su mancha de 30 min por calle se llena de gente."""
    k, q, _, _ = _cuadro_y_clinicas()
    c1 = q.iloc[0]
    j = int(c1.j)
    pj, total, cel_p, d_p = _mil_puntos(j)
    assert abs(total - c1.gente_alcance) < 1e-6
    ox, oy = OF.x.values[j], OF.y.values[j]
    xs, ys = CEL.x.values[pj.i.values], CEL.y.values[pj.i.values]
    v = (xs.min() - 300, xs.max() + 300, ys.min() - 300, ys.max() + 300)
    rect = [0.02, 0.09, 0.96, 0.72]
    ratio = rect[3] * H / (rect[2] * W)
    cx_, cy_ = (v[0] + v[1]) / 2, (v[2] + v[3]) / 2
    hx = max(v[1] - v[0], (v[3] - v[2]) / ratio) / 2
    v = (cx_ - hx, cx_ + hx, cy_ - hx * ratio, cy_ + hx * ratio)
    fig, _ = lienzo_tiktok("Un punto = mil personas sin seguro que viven a 30 min o menos de la clínica, por calle.")
    c, e = cifra_arriba(fig, "", "")
    ax = fig.add_axes(rect)
    xy, a, b, G, ok = red_local(cx_, cy_, hx * ratio + 200)
    ax.add_collection(LineCollection(np.stack([xy[a], xy[b]], axis=1), colors=CALLE, linewidths=0.6, zorder=1))
    d_cel = np.full(len(CEL), np.inf)
    d_cel[pj.i.values] = pj.d.values
    mancha = ax.imshow(raster(np.zeros(len(CEL))), origin="lower", extent=EXT,
                       cmap=ListedColormap([(0, 0, 0, 0), NEUTRO]), vmin=-0.5, vmax=1.5, alpha=0.30,
                       interpolation="nearest", zorder=2)
    P = ruta(xy, G, nodo(xy, ok, CUADRO), nodo(xy, ok, (ox, oy)))
    ax.plot(P[:, 0], P[:, 1], color=TXT, lw=3, zorder=4)
    ax.add_patch(plt.Rectangle((CUADRO[0] - 50, CUADRO[1] - 50), 100, 100, fc=AMBAR(0.85), ec=TXT, lw=2, zorder=8))
    ax.plot(ox, oy, "o", ms=26, mfc=FONDO, mec=CLIN, mew=4, zorder=7)
    ax.text(CUADRO[0] + 140, CUADRO[1] - 260, f"{c1['min']:.0f} min", fontsize=26, fontweight="bold", color=TXT,
            zorder=9, bbox=dict(fc=FONDO, ec="none", alpha=0.8, pad=3))
    pts = ax.scatter(CEL.x.values[cel_p], CEL.y.values[cel_p], s=150, c=[AMBAR(0.8)], edgecolors=FONDO,
                     linewidths=1.2, zorder=6)
    encuadre(ax, v)
    INI, CRECE, FIN = 15, 60, 30

    def act(fr):
        r = 2250 * suave((fr - INI) / CRECE)
        mancha.set_data(raster((d_cel <= r).astype(float)))
        vis = d_p <= r
        pts.set_alpha(None)
        pts.set_facecolors([AMBAR(0.8) if s_ else (0, 0, 0, 0) for s_ in vis])
        pts.set_edgecolors([FONDO if s_ else (0, 0, 0, 0) for s_ in vis])
        gente = PSIN[pj.i.values[pj.d.values <= r]].sum()
        c.set_text(mil(gente) if fr >= INI else "")
        e.set_text("personas" if fr >= INI else "")
    guardar_anim(fig, act, INI + CRECE + FIN, "p1_03d1_alcance", fps=15)
    return mil(total), len(cel_p)


def p1_03d2_cuentas():
    """Ya sin mapa: cómo se juntan médicos, gente y distancia en el acceso del cuadro (paso 2 del E2SFCA)."""
    k, q, A_mil, ref_mil = _cuadro_y_clinicas()
    c1, c2 = q.iloc[0], q.iloc[1]
    _, total1, _, d_p = _mil_puntos(int(c1.j))
    w_p = acceso.peso(d_p, 2250)
    # Los 48 puntos encogidos por su peso suman casi la demanda ponderada real (23 mil).
    assert abs(w_p.sum() * total1 / len(d_p) - c1.demanda) / c1.demanda < 0.02, (w_p.sum(), c1.demanda)
    n2 = int(round(c2.demanda / 1000))
    razon = c2.aporte_mil / c1.aporte_mil     # lo que aporta la de 30 min frente a la de 1 min
    fig, ax = lienzo_tiktok(
        f"Cada punto = mil personas; lejos de la clínica cuentan menos (peso por distancia, gaussiano a 30 min).\n"
        f"Clínica de {c1['min']:.0f} min: {c1.med:.0f} médicos, {c1.demanda:,.0f} personas ponderadas. "
        f"Clínica de {c2['min']:.0f} min: {c2.med:.0f} médicos,\n{c2.demanda:,.0f} ponderadas, y a ese cuadro "
        f"le llega con peso {c2.w:.3f}. Acceso = {c1.aporte_mil:.4f} + {c2.aporte_mil:.4f} = {A_mil:.3f} "
        f"médicos por mil.")
    c, e = cifra_arriba(fig, "", "")
    C1, C2, R1 = np.array([2.9, 9.9]), np.array([7.0, 10.7]), 2.0
    CEL_XY = np.array([4.5, 4.9])
    ang = np.deg2rad(np.arange(len(d_p)) * 137.508)
    rad = 0.75 + d_p / 2250 * (R1 - 0.75)
    px, py = C1[0] + rad * np.cos(ang), C1[1] + rad * np.sin(ang)
    ang2 = np.deg2rad(np.arange(n2) * 137.508)
    rad2 = 0.75 + np.sqrt((np.arange(n2) + 0.5) / n2) * 0.7
    p2x, p2y = C2[0] + rad2 * np.cos(ang2), C2[1] + rad2 * np.sin(ang2)
    S0 = 170
    T = dict(aparece=0, encoge=20, medicos=55, otra=72, viaje=95, suma=125, prior=145, fin=185)

    def clinica(C, n_med, alpha):
        ax.add_patch(plt.Circle(C, 0.58, fc=FONDO, ec=CLIN, lw=4, zorder=6, alpha=alpha))
        for i in range(n_med):
            figura(ax, C[0] + (i - (n_med - 1) / 2) * 0.32, C[1] - 0.25, 0.5, CLIN, z=7, alpha=alpha)

    def act(fr):
        for a_ in list(ax.patches) + list(ax.collections) + list(ax.texts) + list(ax.lines):
            a_.remove()
        t_enc = suave((fr - T["encoge"]) / 30)
        a_med = suave((fr - T["medicos"]) / 10)
        a_otra = suave((fr - T["otra"]) / 12)
        t_via = suave((fr - T["viaje"]) / 25)
        llegado = fr >= T["suma"]
        # clínica de 1 min y su gente
        ax.scatter(px, py, s=S0 * (1 - t_enc + t_enc * w_p), c=[AMBAR(0.8)], edgecolors=FONDO, linewidths=1,
                   zorder=4, alpha=suave((fr + 1) / 12))
        clinica(C1, int(c1.med), max(a_med, 0.35))
        if fr >= T["aparece"]:
            ax.text(C1[0], C1[1] - R1 - 0.45, f"{c1['min']:.0f} min", ha="center", fontsize=26, fontweight="bold",
                    color=TXT)
        # clínica de 30 min y su gente (ya ponderada)
        if a_otra > 0:
            ax.scatter(p2x, p2y, s=S0, c=[AMBAR(0.8)], edgecolors=FONDO, linewidths=1, zorder=4, alpha=a_otra)
            clinica(C2, int(c2.med), a_otra)
            ax.text(C2[0], C2[1] - 1.95, f"{c2['min']:.0f} min", ha="center", fontsize=26, fontweight="bold",
                    color=TXT, alpha=a_otra)
        # el cuadro y lo que le llega de cada clínica: misma flecha, ficha del tamaño de su aporte
        col = BAJO if llegado else AMBAR(0.85)
        ax.add_patch(plt.Rectangle(CEL_XY - 0.45, 0.9, 0.9, fc=col, ec=TXT, lw=2.5, zorder=8))
        if t_via > 0:
            for C, apo in [(C1, 1.0), (C2, razon)]:
                ini = C + (CEL_XY - C) / np.linalg.norm(CEL_XY - C) * 0.65
                fin = CEL_XY + (C - CEL_XY) / np.linalg.norm(C - CEL_XY) * 0.6
                ax.plot([ini[0], fin[0]], [ini[1], fin[1]], color=NEUTRO, lw=3, zorder=3)
                if not llegado:
                    pos = ini + (fin - ini) * t_via
                    ax.scatter([pos[0]], [pos[1]], s=1300 * apo, c=[VERDE], edgecolors=FONDO, linewidths=1.5,
                               zorder=9)
        # cifra de arriba: gente → gente ponderada → acceso
        if fr < T["encoge"]:
            c.set_text(mil(total1)); e.set_text("personas")
        elif fr < T["suma"]:
            c.set_text(mil(total1 - (total1 - c1.demanda) * t_enc)); e.set_text("contando la distancia")
        else:
            c.set_text(f"{A_mil:.2f}"); e.set_text("médicos por mil")
        if llegado:   # la regla: 0 a 0.7 médicos por mil, con la línea de acceso bajo (la mitad del promedio)
            y0, x0, x1, top = 2.45, 1.0, 8.0, 0.7
            esc = (x1 - x0) / top
            ax.add_patch(FancyBboxPatch((x0, y0 - 0.14), x1 - x0, 0.28, boxstyle="round,pad=0,rounding_size=0.1",
                                        fc=SILUETA, ec="none", zorder=3))
            ax.add_patch(FancyBboxPatch((x0, y0 - 0.14), A_mil * esc, 0.28, boxstyle="round,pad=0,rounding_size=0.1",
                                        fc=BAJO, ec="none", zorder=4))
            xm = x0 + ref_mil / 2 * esc
            ax.plot([xm, xm], [y0 - 0.32, y0 + 0.32], color=TXT, lw=3, zorder=5)
            ax.text(xm, y0 + 0.45, f"{ref_mil / 2:.2f}", ha="center", fontsize=22, color=TXT)
            ax.text(xm - 0.1, y0 - 0.65, "acceso bajo", ha="right", fontsize=20, color=TXT2)
        if fr >= T["prior"]:
            ax.text(CEL_XY[0] + 0.75, CEL_XY[1] + 0.15, "marginación alta", fontsize=24, color=FONDO,
                    fontweight="bold", va="center", bbox=dict(boxstyle="round,pad=0.35", fc=MORADO[3], ec="none"),
                    zorder=10)
            ax.text(CEL_XY[0] + 0.75, CEL_XY[1] - 0.75, "prioridad", fontsize=34, fontweight="bold", color=TXT,
                    va="center", zorder=10)
    guardar_anim(fig, act, T["fin"], "p1_03d2_cuentas", fps=15)
    return dict(c2=c2.nombre, med=c2.med, min=round(c2['min'], 1), demanda=round(c2.demanda),
                gente=round(c2.gente_alcance), peso=round(c2.w, 4), aporte_rel=round(razon, 4), A=round(A_mil, 4))


def p1_03e_todos_los_cuadros():
    """De un cuadro a todos: tres saltos de cámara, y los cuadros se pintan rojo o azul hasta el mapa de p1_04."""
    k = celda(CUADRO)
    n_tot = len(CEL)
    assert n_tot == len(_cal) == len(pd.read_parquet(INT / "acceso_transporte_clues.parquet", columns=["x"]))
    bajo = PSIN[CEL.f.values < 0.5].sum()
    assert abs(bajo - cargar("red_real")["f3"]["psin_bajo_calle"]) < 1
    fig, _ = lienzo_tiktok("Un cuadro = 100 × 100 m. Rojo = acceso bajo; azul = suficiente (igual que la siguiente gráfica).")
    c, e = cifra_arriba(fig, "", "")
    rect = [0.02, 0.10, 0.96, 0.58]          # el mismo eje que p1_04_acceso, para que el corte sea continuo
    ax = fig.add_axes(rect)
    clase = 1 + (CEL.f.values < 0.5).astype(int)
    img = ax.imshow(raster(np.zeros(len(CEL))), origin="lower", extent=EXT, cmap=ListedColormap([SILUETA, SUF, BAJO]),
                    vmin=-0.5, vmax=2.5, interpolation="nearest")
    ax.add_patch(plt.Rectangle((CUADRO[0] - 50, CUADRO[1] - 50), 100, 100, fill=False, ec=TXT, lw=2.5, zorder=5))
    encuadre(ax)
    ax.set_xlim(EXT[0], EXT[1]); ax.set_ylim(EXT[2], EXT[3])
    ratio = (EXT[3] - EXT[2]) / (EXT[1] - EXT[0])
    cheb = np.maximum(np.abs(CEL.x.values - CUADRO[0]), np.abs(CEL.y.values - CUADRO[1]))
    hE = (EXT[1] - EXT[0]) / 2
    cE = np.array([(EXT[0] + EXT[1]) / 2, (EXT[2] + EXT[3]) / 2])
    c0 = np.array(CUADRO)
    vistas = [500, 3000, 12000, hE]          # semiancho de la vista en cada salto
    QUIETO, MUEVE = 12, 18

    def estado(fr):
        """(semiancho de la vista, radio pintado) en el cuadro fr."""
        i, r = divmod(max(fr - QUIETO, 0), MUEVE + QUIETO)
        if i >= len(vistas) - 1:
            return hE, np.inf, 1.0
        t = suave(r / MUEVE)
        h = np.exp(np.log(vistas[i]) + (np.log(vistas[i + 1]) - np.log(vistas[i])) * t)
        # Lo pintado crece más lento que la cámara, para que se vea el borde avanzar.
        ultimo = i == len(vistas) - 2
        r0 = 0 if i == 0 else vistas[i] * 0.92
        r1 = 2e5 if ultimo else vistas[i + 1] * 0.92
        return h, r0 + (r1 - r0) * t ** 2, (t if ultimo else 0.0)

    N = QUIETO + (len(vistas) - 1) * (MUEVE + QUIETO) + 20

    def act(fr):
        h, rp, s = estado(fr)
        cc = c0 + (cE - c0) * s           # la cámara sigue centrada en el cuadro hasta el último salto
        ax.set_xlim(cc[0] - h, cc[0] + h); ax.set_ylim(cc[1] - h * ratio, cc[1] + h * ratio)
        pint = cheb <= max(rp, 0)
        img.set_data(raster(np.where(pint, clase, 0)))
        n = int(pint.sum())
        c.set_text(f"{n:,}" if n < 1000 else mil(n))
        e.set_text("cuadro" if n == 1 else "cuadros")
    guardar_anim(fig, act, N, "p1_03e_todos_los_cuadros", fps=15)
    return n_tot, int((PSIN > 0).sum())


def p2_D1_transporte_barrio():
    """El barrio a pie; se dibuja el transporte y los cuadros que salen del acceso bajo se vuelven verdes."""
    a = cargar("transporte_publico")
    t = pd.read_parquet(INT / "acceso_transporte_clues.parquet")
    assert (t.x.values == CEL.x.values).all()
    fp, ft = t.acceso_rel_pie_r5.values, t.acceso_rel_transporte.values
    cd = (CEL.region == "CDMX").values
    assert abs(100 * PSIN[cd & (fp < .5)].sum() / PSIN[cd].sum() - a["acceso"]["pie_r5"]["pct_bajo_CDMX"]) < 1e-6
    mb = en_ventana(CEL.x.values, CEL.y.values, BARRIO)
    sale, entra = mb & (fp < .5) & (ft >= .5), mb & (fp >= .5) & (ft < .5)
    lin, paradas = lineas_gtfs()
    v = BARRIO
    M = 400
    dentro = [P for _, P in lin if en_ventana(P[:, 0], P[:, 1], (v[0] - M, v[1] + M, v[2] - M, v[3] + M)).any()]
    par = paradas[en_ventana(paradas[:, 0], paradas[:, 1], v)]
    # Los cuadros cambian de color del más cercano a una parada al más lejano.
    dist = cKDTree(par).query(CEL[["x", "y"]].values)[0] if len(par) else np.zeros(len(CEL))
    idx = np.flatnonzero(sale | entra)
    idx = idx[np.argsort(dist[idx])]
    fig, _ = lienzo_tiktok(f"Verde = sale del acceso bajo con el transporte. Hay {mil(PSIN[entra].sum())} personas que "
                           "entran (rojo nuevo): el transporte\ntambién trae más gente a sus clínicas. Mismo motor (r5py) "
                           "a pie y con transporte.\n" + f"{NOMBRE_BARRIO}. Líneas: GTFS de la CDMX.")
    c, e = cifra_arriba(fig, "", "")
    ax = fig.add_axes([0.02, 0.09, 0.96, 0.72])
    base = (fp < .5).astype(int)
    img = ax.imshow(raster(base), origin="lower", extent=EXT, cmap=ListedColormap([SUF, BAJO, VERDE]),
                    vmin=-0.5, vmax=2.5, interpolation="nearest", zorder=1)
    clinicas(ax, v, escala=6)
    lc = LineCollection([], colors=VERDE, linewidths=1.8, zorder=4,
                        path_effects=[patheffects.Stroke(linewidth=3.6, foreground=FONDO), patheffects.Normal()])
    ax.add_collection(lc)
    encuadre(ax, v)
    escala_km(ax, v)
    INI, DIBUJA, PAUSA, CAMBIA, FIN = 12, 25, 8, 40, 30

    def act(fr):
        td = suave((fr - INI) / DIBUJA)
        lc.set_segments([P[: max(2, int(len(P) * td))] for P in dentro] if td > 0 else [])
        tc = suave((fr - INI - DIBUJA - PAUSA) / CAMBIA)
        hechos = idx[: int(round(tc * len(idx)))]
        cl = base.copy()
        cl[hechos] = np.where(sale[hechos], 2, 1)
        img.set_data(raster(cl))
        ya = PSIN[hechos[sale[hechos]]].sum()
        c.set_text(mil(ya) if tc > 0 else "")
        e.set_text("personas" if tc > 0 else "")
    guardar_anim(fig, act, INI + DIBUJA + PAUSA + CAMBIA + FIN, "p2_D1_transporte_barrio", fps=15)
    return PSIN[sale].sum(), PSIN[entra].sum(), len(dentro)


def p2_D2_transporte_ciudad():
    """Toda la zona con la red de transporte que hay en los datos: densa en la CDMX, casi vacía en el Edomex."""
    a = cargar("transporte_publico")
    pie, tp = a["acceso"]["pie_r5"], a["acceso"]["transporte_r5"]
    lin, _ = lineas_gtfs()
    fig, _ = lienzo_tiktok("Acceso bajo a pie y con transporte, calculados en el mismo motor (r5py). Red: GTFS de la CDMX\n"
                           "(Metro, Metrobús, RTP, Trolebús, Tren Ligero, Cablebús, Suburbano…). Sin Mexibús, Mexicable "
                           "ni combis:\nen el Edomex la red está incompleta en los datos, no ausente en la realidad.")
    t_cd = fig.text(0.06, 0.955, "", fontsize=60, fontweight="bold", color=TXT, va="top")
    t_ed = fig.text(0.06, 0.875, "", fontsize=60, fontweight="bold", color=TXT, va="top")
    ax = fig.add_axes([0.02, 0.10, 0.96, 0.68])
    cd = (CEL.region == "CDMX").values
    # Edomex con rayas: «datos parciales»
    raya = ((CI + CJ) % 6 < 2) & ~cd
    # La vista recorta los cuadros sueltos de la orilla para que el mapa se vea más grande.
    v = (np.percentile(CEL.x, 1), np.percentile(CEL.x, 99.5), np.percentile(CEL.y, 0.5), np.percentile(CEL.y, 99))
    mapa(ax, np.where(cd, 1, np.where(raya, 2, 0)), [SILUETA, "#4f4f49", "#5c5c55"], v)
    lc = LineCollection([], colors=VERDE, linewidths=0.9, zorder=4)
    ax.add_collection(lc)
    ex = CEL.x.values[~cd]; ey = CEL.y.values[~cd]
    ax.text(np.percentile(ex, 88), np.percentile(ey, 93), "Edomex:\ndatos parciales", fontsize=19, color=TXT2,
            ha="center", va="center", zorder=6, bbox=dict(fc=FONDO, ec="none", alpha=0.75, pad=3))
    INI, DIBUJA, CD, ED, FIN = 8, 40, 20, 20, 30

    def act(fr):
        td = suave((fr - INI) / DIBUJA)
        lc.set_segments([P for _, P in lin[: int(round(td * len(lin)))]])
        tc = suave((fr - INI - DIBUJA) / CD)
        v1, v2 = pie["pct_bajo_CDMX"], tp["pct_bajo_CDMX"]
        t_cd.set_text(f"CDMX  {v1:.0f}% → {v1 + (v2 - v1) * tc:.0f}%" if fr >= INI else "")
        te = fr >= INI + DIBUJA + CD
        w1, w2 = pie["pct_bajo_EDOMEX"], tp["pct_bajo_EDOMEX"]
        t_ed.set_text(f"Edomex  {w1:.0f}% → {w2:.0f}%" if te else "")
    guardar_anim(fig, act, INI + DIBUJA + CD + ED + FIN, "p2_D2_transporte_ciudad", fps=15)
    return (round(pie["pct_bajo_CDMX"], 1), round(tp["pct_bajo_CDMX"], 1),
            round(pie["pct_bajo_EDOMEX"], 1), round(tp["pct_bajo_EDOMEX"], 1), len(lin))


def p3_3_equidad():
    """100 figuritas (22 moradas) y 100 fichas de mejora en dos bandejas: solo 3 van al lado morado."""
    ver = cargar("equidad_transporte")["veredicto"]["total"]
    n_mor = int(round(ver["alta_muy_alta_pct_gente"]))
    n_gan = int(round(ver["alta_muy_alta_pct_ganancias"]))
    assert (n_mor, n_gan) == (22, 3)
    fig, ax = lienzo_tiktok(f"Cada figura = 1% de la gente sin seguro; morado = marginación alta o muy alta "
                            f"({ver['alta_muy_alta_pct_gente']:.1f}%).\nCada ficha = 1% de lo que sube el acceso con el "
                            f"transporte público ({ver['alta_muy_alta_pct_ganancias']:.1f}% les llega a ellos).\n"
                            "El transporte no crea médicos: mueve el acceso de lugar.")
    c, e = cifra_arriba(fig, "", "")
    SP, X0g, Y0g = 0.7, 1.35, 12.3
    gx = X0g + (np.arange(100) // 10) * SP          # por columnas: los 22 morados quedan juntos a la izquierda
    gy = Y0g - (np.arange(100) % 10) * SP
    xl, xr = X0g - SP / 2, X0g + 9.5 * SP
    xm = xl + (xr - xl) * n_mor / 100
    YB, HB, FS = 1.9, 2.9, 0.36
    destino = np.zeros(100, bool)
    destino[np.round((np.arange(n_gan) + 0.5) * 100 / n_gan).astype(int)] = True   # las 3 que van al lado morado
    slot = np.zeros(100, int)
    slot[destino] = np.arange(n_gan)
    slot[~destino] = np.arange(100 - n_gan)

    def lugar(i):
        if destino[i]:
            x0, w = xl, xm - xl
        else:
            x0, w = xm, xr - xm
        porfila = max(1, int((w - 0.1) // FS))
        f_, cc = divmod(slot[i], porfila)
        return x0 + 0.05 + FS / 2 + cc * FS, YB + 0.05 + FS / 2 + f_ * FS

    T = dict(gente=0, morado=15, caen=40, fin=40 + 100 + 8 + 30)

    def act(fr):
        for a_ in list(ax.patches) + list(ax.collections) + list(ax.texts) + list(ax.lines):
            a_.remove()
        tm = suave((fr - T["morado"]) / 12)
        for i in range(100):
            col = MORADO[3] if (i < n_mor and tm > 0.5) else GRIS
            figura(ax, gx[i], gy[i] - 0.28, 0.56, col, alpha=suave((fr + 1) / 10))
        if tm > 0.5:
            ax.text((xl + xm) / 2, Y0g + 0.75, f"{n_mor}%", ha="center", fontsize=34, fontweight="bold", color=TXT)
        # dos bandejas, divididas en el mismo punto que la gente
        for x0, x1 in [(xl, xm - 0.06), (xm + 0.06, xr)]:
            ax.add_patch(FancyBboxPatch((x0, YB), x1 - x0, HB, boxstyle="round,pad=0,rounding_size=0.12",
                                        fill=False, ec=TXT3, lw=2, zorder=2))
        if fr >= T["caen"]:
            ax.text((xl + xr) / 2, YB + HB + 0.35, "mejora de acceso", ha="center", fontsize=24, color=TXT2)
        xs, ys = [], []
        for i in range(100):
            t0 = T["caen"] + i
            if fr < t0:
                continue
            x, y = lugar(i)
            tt = suave((fr - t0) / 6)
            xs.append(x); ys.append(YB + HB + 0.4 + (y - YB - HB - 0.4) * tt)
        if xs:
            ax.scatter(xs, ys, s=150, c=[VERDE], edgecolors=FONDO, linewidths=1, zorder=5)
        listo = fr >= T["caen"] + 100 + 6
        if listo:
            ax.text((xl + xm) / 2, YB + HB - 0.75, f"{n_gan}%", ha="center", fontsize=34, fontweight="bold", color=TXT)
        c.set_text(f"{n_mor}% · {n_gan}%" if listo else (f"{n_mor}%" if tm > 0.5 else ""))
    guardar_anim(fig, act, T["fin"], "p3_3_equidad", fps=15)
    return n_mor, n_gan


TODAS = [p1_00_gancho, p1_01_clinicas, p1_02_gente, p1_03_calles, p1_03b_marginacion, p1_03c_capas,
         p1_03d1_alcance, p1_03d2_cuentas, p1_03e_todos_los_cuadros, p1_04a_esquema_acceso, p1_04_acceso,
         p1_05_topologia, p2_A_reubicar, p2_B_abrir_ampliar, p2_C_prioridad, p2_D1_transporte_barrio,
         p2_D2_transporte_ciudad, p2_E_horizonte, p3_2_rodeo, p3_3_equidad, p3_4_nulo]

if __name__ == "__main__":
    pedidas = set(sys.argv[1:])
    for fn in TODAS:
        if not pedidas or fn.__name__ in pedidas:
            print(fn.__name__)
            r = fn()
            if r is not None:
                print("   ", r)
