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
from matplotlib import animation
from matplotlib.collections import LineCollection
from matplotlib.colors import LinearSegmentedColormap, ListedColormap, PowerNorm
from matplotlib.patches import Polygon
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


def p1_03b_marginacion():
    eq = cargar("equidad_transporte")["veredicto"]["total"]
    con = GRADO_I >= 0
    parte = {g: PSIN[GRADO_I == i].sum() / PSIN[con].sum() * 100 for i, g in enumerate(GRADOS)}
    alta = parte["Alto"] + parte["Muy alto"]
    assert abs(alta - eq["alta_muy_alta_pct_gente"]) < 1e-6
    fig = lienzo(f"{alta:.0f}%", "de la gente sin seguro vive en zonas\nde marginación alta o muy alta",
                 nota="Índice de marginación urbana de CONAPO 2020, uno por zona del Censo (AGEB). Las líneas del zoom\n"
                      "son los límites de esas zonas. El porcentaje cuenta personas, no superficie del mapa.")
    _, az = _zona_y_barrio(
        fig, mapa_marginacion,
        [(MORADO[i], f"{g} · {parte[g]:.0f}%") for i, g in reversed(list(enumerate(GRADOS)))] + [(SILUETA, "sin dato")],
        f"Zoom: {NOMBRE_BARRIO}")
    # Límites de AGEB dentro del zoom: aristas entre cuadros vecinos de distinta AGEB.
    m = en_ventana(CEL.x.values, CEL.y.values, BARRIO)
    s = CEL[m]
    clave = dict(zip(zip(s.x, s.y), s.CVEGEO))
    segs = []
    for (x, y), cv in clave.items():
        for dx, dy in [(100, 0), (0, 100)]:
            otro = clave.get((x + dx, y + dy))
            if otro is not None and otro != cv:
                if dx:
                    segs.append([(x + 50, y - 50), (x + 50, y + 50)])
                else:
                    segs.append([(x - 50, y + 50), (x + 50, y + 50)])
    az.add_collection(LineCollection(segs, colors=FONDO, linewidths=1.1, zorder=5))
    guardar(fig, "p1_03b_marginacion")
    return {g: round(v, 1) for g, v in parte.items()}


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


def p1_03d_un_cuadro():
    """Se sigue un cuadro real, paso a paso, hasta su acceso y su prioridad."""
    k = celda(CUADRO)
    q, A_mil, ref_mil = desglose_cuadro(k)
    assert abs(ref_mil - cargar("acceso_e2sfca")["promedio_metropolitano_por_1000"]) < 1e-9
    assert CEL.f.values[k] < 0.5 and CEL.grado.values[k] in ("Alto", "Muy alto")
    gente = PSIN[k]
    c1, c2 = q.iloc[0], q.iloc[-1]
    xs = [CUADRO[0]] + list(OF.x.values[q.j]); ys = [CUADRO[1]] + list(OF.y.values[q.j])
    v = (min(xs) - 900, max(xs) + 900, min(ys) - 1300, max(ys) + 1300)
    alto = (v[1] - v[0]) * 1.12
    v = (v[0], v[1], (v[2] + v[3]) / 2 - alto / 2, (v[2] + v[3]) / 2 + alto / 2)
    xy, a, b, G, ok = red_local((v[0] + v[1]) / 2, (v[2] + v[3]) / 2, 3600)
    s = nodo(xy, ok, CUADRO)
    rutas = [ruta(xy, G, s, nodo(xy, ok, (OF.x.values[j], OF.y.values[j]))) for j in q.j]
    fig = plt.figure(figsize=(W, H), dpi=DPI)
    t_paso = fig.text(0.06, 0.955, "", fontsize=20, color=TXT3, va="top")
    t_tit = fig.text(0.06, 0.925, "", fontsize=34, fontweight="bold", va="top", linespacing=1.15)
    t_det = fig.text(0.06, 0.80, "", fontsize=21, color=TXT2, va="top", linespacing=1.35)
    fig.text(0.06, 0.03, "Acceso E2SFCA a 30 min por calle. La demanda de cada clínica suma a la gente a su alcance,\n"
             "contando más a quien vive más cerca. Un cuadro = 100 × 100 m; su gente es una estimación del Censo.\n"
             + FUENTE, fontsize=12, color=TXT3, va="bottom", linespacing=1.4)
    ax = fig.add_axes([0.02, 0.10, 0.96, 0.58])
    segs = np.stack([xy[a], xy[b]], axis=1)
    ax.add_collection(LineCollection(segs, colors=CALLE, linewidths=0.6, zorder=1))
    # gente que comparte la clínica cercana (paso 3): cuadros que la alcanzan, brillo = peso × gente
    p = pares()
    pj = p[p.j == c1.j]
    peso = PSIN[pj.i.values] * acceso.peso(pj.d.values, 2250)
    val = np.full(len(CEL), np.nan)
    val[pj.i.values] = peso
    img = ax.imshow(raster(val), origin="lower", extent=EXT, cmap=AMBAR, norm=PowerNorm(0.5, 0, np.nanpercentile(peso, 98)),
                    interpolation="nearest", alpha=0.0, zorder=2)
    lineas = [ax.plot([], [], color=NEUTRO, lw=4, solid_capstyle="round", zorder=4)[0] for _ in rutas]
    for j, row in zip(q.j, q.itertuples()):
        ax.plot(OF.x.values[j], OF.y.values[j], "o", ms=16 + 2 * row.med, mfc="none", mec=CLIN, mew=3, zorder=6)
    et = [ax.text(OF.x.values[j] + 160, OF.y.values[j] + 160, "", fontsize=17, color=TXT, zorder=7,
                  bbox=dict(fc=FONDO, ec="none", alpha=0.75, pad=2)) for j in q.j]
    cuad = plt.Rectangle((CUADRO[0] - 50, CUADRO[1] - 50), 100, 100, fc=AMBAR(0.85), ec=TXT, lw=2, zorder=8)
    ax.add_patch(cuad)
    anillo = plt.Circle(CUADRO, 230, fill=False, ec=MORADO[4], lw=4, zorder=9, visible=False)
    ax.add_patch(anillo)
    encuadre(ax, v)
    escala_km(ax, v)
    axb = fig.add_axes([0.10, 0.665, 0.82, 0.05]); axb.axis("off"); axb.set_visible(False)
    pasos = [
        ("Aquí viven\n{:.0f} personas sin seguro".format(gente),
         f"Un cuadro de 100 × 100 m en {NOMBRE_BARRIO.split(',')[0]}."),
        (f"Por calle alcanzan\n{len(q)} clínicas",
         "\n".join(f"{r.nombre.title().replace(' De ', ' de ')}: {r.min:.0f} min" for r in q.itertuples())),
        (f"La más cercana tiene\n{c1.med:.0f} médicos para mucha gente",
         f"Su demanda equivale a unas {c1.demanda / 1000:.0f} mil personas\n(ponderada: cuenta más quien vive más cerca)."),
        (f"Acceso de este cuadro:\n{A_mil:.2f} médicos por cada mil",
         f"El promedio de la zona es {ref_mil:.2f}; menos de {ref_mil / 2:.2f} es acceso bajo.\n"
         f"La clínica a {c2['min']:.0f} min casi no aporta: queda en el límite."),
        ("Marginación alta:\nprioridad",
         f"Acceso bajo y grado de marginación «{CEL.grado.values[k]}» (CONAPO).\n"
         "Así entra en las cuentas de «a quién primero» (escenario C)."),
    ]
    POR = 45
    N = POR * len(pasos)

    def act(fr):
        i = min(fr // POR, len(pasos) - 1)
        t = (fr % POR + 1) / (POR * 0.6)
        t_paso.set_text(f"Un cuadro, paso a paso · {i + 1} de {len(pasos)}")
        t_tit.set_text(pasos[i][0])
        t_det.set_text(pasos[i][1])
        for n_, (ln, P) in enumerate(zip(lineas, rutas)):
            if i == 1:
                acum = np.r_[0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]
                m = acum <= acum[-1] * min(1, t)
                ln.set_data(P[m, 0], P[m, 1])
            elif i > 1:
                ln.set_data(P[:, 0], P[:, 1])
            else:
                ln.set_data([], [])
            r = q.iloc[n_]
            et[n_].set_text(f"{r['med']:.0f} médicos · {r['min']:.0f} min" if i >= 1 else "")
        img.set_alpha(0.75 if i == 2 else 0.0)
        cuad.set_facecolor(BAJO if i >= 3 else AMBAR(0.85))
        anillo.set_visible(i >= 4)
        if i >= 3:
            axb.set_visible(True); axb.cla(); axb.axis("off")
            axb.set_xlim(0, 0.8); axb.set_ylim(0, 1)
            axb.barh(0.5, 0.8, 0.35, color=SILUETA)
            axb.barh(0.5, A_mil / 1000 * 1000, 0.35, color=BAJO)
            for xv, lab in [(ref_mil / 2, "mitad"), (ref_mil, "promedio")]:
                axb.plot([xv, xv], [0.15, 0.85], color=TXT, lw=2)
                axb.text(xv, 1.0, f"{lab} {xv:.2f}", ha="center", va="bottom", fontsize=14, color=TXT2)
            axb.text(A_mil + 0.01, 0.5, f"{A_mil:.2f}", va="center", fontsize=16, color=TXT, fontweight="bold")
        else:
            axb.set_visible(False)
    guardar_anim(fig, act, N, "p1_03d_un_cuadro", fps=15)
    return q[["nombre", "med", "min", "demanda", "gente_alcance", "aporte_mil"]].round(3).to_dict("records"), A_mil


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


def p2_D_transporte():
    a = cargar("transporte_publico")
    pie, tp = a["acceso"]["pie_r5"], a["acceso"]["transporte_r5"]
    t = pd.read_parquet(INT / "acceso_transporte_clues.parquet")
    assert (t.x.values == CEL.x.values).all()
    fp, ft = t.acceso_rel_pie_r5.values, t.acceso_rel_transporte.values
    cd = (CEL.region == "CDMX").values
    assert abs(100 * PSIN[cd & (fp < .5)].sum() / PSIN[cd].sum() - pie["pct_bajo_CDMX"]) < 1e-6
    assert abs(100 * PSIN[cd & (ft < .5)].sum() / PSIN[cd].sum() - tp["pct_bajo_CDMX"]) < 1e-6
    sale = (fp < .5) & (ft >= .5)
    mb = en_ventana(CEL.x.values, CEL.y.values, BARRIO)
    sale_barrio = PSIN[mb & sale].sum()
    fig = lienzo_pregunta("¿Y el transporte\npúblico?",
                          f"En la CDMX el acceso bajo pasa de {pie['pct_bajo_CDMX']:.0f}% a {tp['pct_bajo_CDMX']:.0f}%.\n"
                          "En el Edomex casi no cambia: faltan datos" + chr(10) + "de su transporte.",
                          nota="Ambos casos calculados en el mismo motor (r5py), puerta a puerta, 30 min; por eso la CDMX\n"
                               "parte de 27% y no del 28% de la red de calles propia. Metro, Metrobús, RTP, Tren Ligero y\n"
                               "trolebús (GTFS de SEMOVI); sin Mexibús, Mexicable ni combis.")
    for x0, f, tit, verde in [(0.02, fp, "a pie", False), (0.51, ft, "a pie + transporte", True)]:
        ax = fig.add_axes([x0, 0.385, 0.47, 0.30])
        clase = (f < .5).astype(int)
        cols = [SUF, BAJO]
        if verde:
            clase = np.where(sale, 2, clase)
            cols = [SUF, BAJO, VERDE]
        mapa(ax, clase, cols, BARRIO)
        clinicas(ax, BARRIO, escala=6)
        fig.text(x0 + 0.235, 0.70, tit, ha="center", fontsize=21, fontweight="bold", va="top")
    escala_km(fig.axes[-1], BARRIO)
    leyenda(fig, 0.06, 0.37, [(BAJO, "acceso bajo"), (SUF, "acceso suficiente"),
                              (VERDE, f"sale del acceso bajo ({mil(sale_barrio)} en este barrio)")], dy=0.026, fs=16)
    fig.text(0.06, 0.29, NOMBRE_BARRIO + " · ○ = clínica", fontsize=15, color=TXT3, va="top")
    ax = fig.add_axes([0.24, 0.12, 0.72, 0.15])
    ys = np.array([1, 0])
    h = 0.36
    for y, reg, nom in zip(ys, ["CDMX", "EDOMEX"], ["CDMX", "Edomex"]):
        v1, v2 = pie[f"pct_bajo_{reg}"], tp[f"pct_bajo_{reg}"]
        ax.barh(y + h / 2, v1, h, color=GRIS)
        ax.barh(y - h / 2, v2, h, color=VERDE)
        ax.text(v1 + 1, y + h / 2, f"{v1:.0f}% a pie", va="center", fontsize=15, color=TXT2)
        ax.text(v2 + 1, y - h / 2, f"{v2:.0f}% + transporte", va="center", fontsize=15, color=TXT, fontweight="bold")
        ax.text(-2, y, nom, ha="right", va="center", fontsize=19, color=TXT)
    ax.set_xlim(0, 85); ax.axis("off")
    guardar(fig, "p2_D_transporte")
    return sale_barrio


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


def p3_3_equidad():
    eq = cargar("equidad_transporte")
    g = pd.DataFrame(eq["por_grado"]["total"])
    ver = eq["veredicto"]["total"]
    fig = lienzo(f"{ver['alta_muy_alta_pct_gente']:.0f}% · {ver['alta_muy_alta_pct_ganancias']:.0f}%",
                 "los más marginados son el 22% de la gente\ny reciben el 3% de lo que gana el\nacceso con el transporte público",
                 nota="Ganancia = acceso que sube al agregar el transporte, sumado por persona. El transporte no\n"
                      "crea médicos: mueve el acceso de lugar. Marginación urbana CONAPO 2020 por AGEB.")
    ax = fig.add_axes([0.26, 0.15, 0.70, 0.48])
    y = np.arange(len(g))[::-1]
    h = 0.36
    ax.barh(y + h / 2 + 0.01, g.pct_gente, h, color=GRIS)
    ax.barh(y - h / 2 - 0.01, g.pct_ganancias, h, color=VERDE)
    for yy, a, b in zip(y, g.pct_gente, g.pct_ganancias):
        ax.text(a + 0.8, yy + h / 2 + 0.01, f"{a:.0f}%", va="center", fontsize=18, color=TXT2)
        ax.text(b + 0.8, yy - h / 2 - 0.01, f"{b:.0f}%", va="center", fontsize=18, color=TXT, fontweight="bold")
    ax.set_yticks(y); ax.set_yticklabels(g.grado, fontsize=20, color=TXT)
    ax.tick_params(axis="y", length=0)
    ax.set_xlim(0, 60); ax.set_xticks([])
    for s in ["top", "right", "bottom"]:
        ax.spines[s].set_visible(False)
    ax.text(0, len(g) - 0.3, "■", color=GRIS, fontsize=20)
    ax.text(2.6, len(g) - 0.3, "parte de la gente", color=TXT2, fontsize=18)
    ax.text(30, len(g) - 0.3, "■", color=VERDE, fontsize=20)
    ax.text(32.6, len(g) - 0.3, "parte de lo que gana", color=TXT2, fontsize=18)
    fig.text(0.06, 0.66, "grado de marginación", fontsize=16, color=TXT3)
    guardar(fig, "p3_3_equidad")


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


TODAS = [p1_00_gancho, p1_01_clinicas, p1_02_gente, p1_03_calles, p1_03b_marginacion, p1_03c_capas,
         p1_03d_un_cuadro, p1_04a_esquema_acceso, p1_04_acceso, p1_05_topologia,
         p2_A_reubicar, p2_B_abrir_ampliar, p2_C_prioridad, p2_D_transporte, p2_E_horizonte,
         p3_2_rodeo, p3_3_equidad, p3_4_nulo]

if __name__ == "__main__":
    pedidas = set(sys.argv[1:])
    for fn in TODAS:
        if not pedidas or fn.__name__ in pedidas:
            print(fn.__name__)
            r = fn()
            if r is not None:
                print("   ", r)
